"""Prompt Layer Marker Sanitization, History Roles & Adaptive Steps (`Story 26.1`)."""

from __future__ import annotations

import re

from fastapi import Request

from orcia_api.locales._assistant_sanitization_locales import (
    CODE_INTENT_RE,
    DECISION_INTENT_RE,
    DOC_INTENT_RE,
    STEP_TEMPLATES_BY_LOCALE,
)
from orcia_core.observability.logging import get_logger

ALLOWED_CLIENT_HISTORY_ROLES: frozenset[str] = frozenset({"user", "assistant"})

_LAYER_OR_CONSTITUTIONAL_TAG_RE = re.compile(
    r"\[((?:"
    r"LAYER|CONSTITUTIONAL|ONTOLOGY|HUMAN_PROFILE|ADAPTATION|"
    r"FEDERATED_CONTEXT_FANOUT|CONVERSATIONAL_INTENT|"
    r"SERVER_EVIDENCE_TABLE|TABLE_PREUVES_SERVEUR|"
    r"NO_HUMAN_ANCHOR_WRITE|NO_GATE_SELF_APPROVAL|"
    r"EXPLICIT_PROVENANCE_URI|STALE_WARNING"
    r")(?:[_\s:=-]+[^\]]*)?)\]",
    re.IGNORECASE,
)


def sanitize_prompt_layer_markers(text: str | None) -> str:
    """Escape `[LAYER_*]` and `[CONSTITUTIONAL_*]` delimiter tags in untrusted text."""
    if not text:
        return ""
    return _LAYER_OR_CONSTITUTIONAL_TAG_RE.sub(r"(escaped:\1)", text.strip())


def resolve_request_locale(request: Request | None, explicit_locale: str | None = None) -> str:
    """Resolve UI locale (`fr`, `en`, `es`) from explicit parameter or HTTP `Accept-Language`."""
    raw = (explicit_locale or "").strip().lower()
    if not raw and request is not None:
        raw = str(request.headers.get("accept-language") or "").strip().lower()
    primary = raw.split(",")[0].split(";")[0].strip()
    if primary.startswith("en"):
        return "en"
    if primary.startswith("es"):
        return "es"
    return "fr"


def detect_adaptive_thinking_steps_for_question(
    user_prompt: str,
    *,
    locale: str = "fr",
) -> tuple[tuple[str, str], ...]:
    """Return 3 adaptive thinking step `(title, intermediate_summary)` pairs in `locale`."""
    lang = (
        locale
        if locale in STEP_TEMPLATES_BY_LOCALE
        else ("en" if locale.startswith("en") else "fr")
    )
    templates = STEP_TEMPLATES_BY_LOCALE[lang]
    if CODE_INTENT_RE.search(user_prompt):
        return templates["code"]
    if DOC_INTENT_RE.search(user_prompt):
        return templates["doc"]
    if DECISION_INTENT_RE.search(user_prompt):
        return templates["decision"]
    return templates["default"]


def resolve_active_pack_key_from_request(
    request: Request | None,
    workspace_id: str,
) -> str | None:
    """Resolve the genuinely active domain pack key from workspace or platform context."""
    state = getattr(getattr(request, "app", None), "state", None)
    if state is None:
        return None
    studio_svc = getattr(state, "studio_and_packs_service", None)
    if studio_svc is not None and hasattr(studio_svc, "list_packs"):
        try:
            packs = list(studio_svc.list_packs())
            ws_match = next(
                (p.pack_key for p in packs if p.status == "ACTIVE" and p.scope_id == workspace_id),
                None,
            )
            if ws_match:
                return str(ws_match)
            global_match = next(
                (p.pack_key for p in packs if p.status == "ACTIVE" and p.scope_level == "GLOBAL"),
                None,
            )
            if global_match:
                return str(global_match)
        except Exception as exc:
            get_logger("orcia.assistant.context").warning(
                "assistant_studio_pack_resolution_skipped", error_type=type(exc).__name__
            )
    bundles = getattr(state, "declarative_pack_bundles", None)
    if isinstance(bundles, dict) and bundles:
        if "orcia-pack-sdlc" in bundles:
            return "orcia-pack-sdlc"
        return str(sorted(bundles.keys())[0])
    return None
