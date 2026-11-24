"""Deterministic Tier-1 validator `validate_help_article` (`Story 11.5`, `MAJOR-05`)."""

from __future__ import annotations

import json
import re
import time
from typing import Any, Literal

from orcia_core.orchestration._help_article_models import (
    DEFAULT_KNOWN_ROUTES,
    KNOWN_ORCIA_UI_COMPONENTS,
    HelpArticleValidationReport,
)
from orcia_core.orchestration._help_docs_locales import (
    HELP_MANDATORY_SECTIONS,
    HELP_VALIDATOR_VIOLATIONS,
)
from orcia_kernel.enums import DEFAULT_LOCALE

_MANDATORY_SECTIONS_FR: tuple[str, str, str] = HELP_MANDATORY_SECTIONS["fr"]
_MANDATORY_SECTIONS_EN: tuple[str, str, str] = HELP_MANDATORY_SECTIONS["en"]

_SECRET_LEAK_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"\bpat_mcp_[A-Za-z0-9_-]{8,}"),
    re.compile(r"\bsk-[A-Za-z0-9_-]{12,}"),
    re.compile(r"(?:secret|vault|kms)://[^\s\"')]+"),
    re.compile("-----BEGIN " + r"[A-Z ]*PRIVATE KEY-----"),  # pragma: allowlist secret
    re.compile(r"\bBearer\s+eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"),
)

_UI_COMPONENT_REF_RE = re.compile(r"`<([A-Z][A-Za-z0-9]+)\s*/?>`|`@orcia/ui:([A-Z][A-Za-z0-9]+)`")


def parse_frontmatter_and_body(markdown_text: str) -> tuple[dict[str, Any], str]:
    """Parse YAML frontmatter dictionary and markdown body from a `HelpArticle`."""
    text = markdown_text.strip()
    meta: dict[str, Any] = {}
    body = text
    if not text.startswith("---"):
        return meta, body
    parts = text.split("---", 2)
    if len(parts) < 3:
        return meta, body
    fm_raw = parts[1].strip()
    body = parts[2].strip()
    current_list_key: str | None = None
    for line in fm_raw.splitlines():
        s = line.strip()
        if not s:
            continue
        if s.startswith("- ") and current_list_key is not None:
            lst = meta.setdefault(current_list_key, [])
            if isinstance(lst, list):
                lst.append(s[2:].strip().strip("\"'"))
            continue
        if ":" in s:
            current_list_key = None
            k, v = s.split(":", 1)
            key = k.strip()
            val = v.strip()
            if not val:
                current_list_key = key
                meta[key] = []
            elif val.startswith("[") and val.endswith("]"):
                try:
                    meta[key] = json.loads(val)
                except ValueError:
                    meta[key] = [x.strip().strip("\"'") for x in val[1:-1].split(",") if x.strip()]
            else:
                meta[key] = val.strip("\"'")
    return meta, body


class HelpArticleDeterministicValidator:
    """Tier 1 deterministic validator `validate_help_article` (`< 5 s`)."""

    def __init__(
        self,
        *,
        known_routes: set[str] | frozenset[str] | None = None,
        known_ui_components: set[str] | frozenset[str] | None = None,
    ) -> None:
        self._known_routes = set(known_routes or DEFAULT_KNOWN_ROUTES)
        self._known_ui_components = set(known_ui_components or KNOWN_ORCIA_UI_COMPONENTS)

    def validate_help_article(
        self,
        *,
        markdown_text: str,
        lang: Literal["fr", "en"] = "fr",
        extra_allowed_routes: list[str] | None = None,
        known_glossary_terms: list[str] | None = None,
    ) -> HelpArticleValidationReport:
        """Validate `HelpArticle` Markdown in `< 5 s` across all 3 deterministic checks."""
        t0 = time.perf_counter()
        meta, body = parse_frontmatter_and_body(markdown_text)
        article_id = str(meta.get("id", "unknown-help-article"))
        violations: list[str] = []

        allowed_routes = self._known_routes | set(extra_allowed_routes or [])
        bound_routes = meta.get("bound_routes", [])
        if not isinstance(bound_routes, list) or not bound_routes:
            bound_routes_valid = False
            violations.append("Frontmatter 'bound_routes' est vide ou absent.")
        else:
            unknown_routes = [
                r
                for r in bound_routes
                if not str(r).startswith("/") or str(r) not in allowed_routes
            ]
            bound_routes_valid = len(unknown_routes) == 0
            if unknown_routes:
                violations.append(f"Routes inconnues dans bound_routes : {unknown_routes}")

        mandatory_sections = _MANDATORY_SECTIONS_FR if lang == "fr" else _MANDATORY_SECTIONS_EN
        missing_sections = [sec for sec in mandatory_sections if sec not in body]
        has_anchors = "{#" in body or "## 1." in body and "#" in body
        cited_components: list[str] = []
        for m in _UI_COMPONENT_REF_RE.finditer(body):
            comp = m.group(1) or m.group(2)
            if comp:
                cited_components.append(comp)
        unknown_components = [c for c in cited_components if c not in self._known_ui_components]
        ui_components_and_sections_valid = (
            len(missing_sections) == 0 and has_anchors and len(unknown_components) == 0
        )
        msg_map = HELP_VALIDATOR_VIOLATIONS[DEFAULT_LOCALE]
        if missing_sections:
            violations.append(msg_map["missing_sections"].format(sections=missing_sections))
        if unknown_components:
            violations.append(msg_map["unknown_components"].format(components=unknown_components))

        glossary_terms = meta.get("glossary_terms", [])
        glossary_ok = isinstance(glossary_terms, list)
        if glossary_ok and known_glossary_terms:
            known_lower = {t.lower() for t in known_glossary_terms}
            unaligned = [t for t in glossary_terms if str(t).lower() not in known_lower]
            if unaligned:
                glossary_ok = False
                violations.append(msg_map["unknown_glossary"].format(terms=unaligned))

        secret_hits: list[str] = []
        for pat in _SECRET_LEAK_PATTERNS:
            found = pat.findall(markdown_text)
            if found:
                secret_hits.extend(found)
        glossary_and_zero_secret_valid = glossary_ok and len(secret_hits) == 0
        if secret_hits:
            violations.append(msg_map["secret_leak"])

        elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 3)
        passed = (
            bound_routes_valid
            and ui_components_and_sections_valid
            and glossary_and_zero_secret_valid
        )
        return HelpArticleValidationReport(
            article_id=article_id,
            lang=lang,
            passed=passed,
            bound_routes_valid=bound_routes_valid,
            ui_components_and_sections_valid=ui_components_and_sections_valid,
            glossary_and_zero_secret_valid=glossary_and_zero_secret_valid,
            elapsed_ms=elapsed_ms,
            violations=tuple(violations),
        )
