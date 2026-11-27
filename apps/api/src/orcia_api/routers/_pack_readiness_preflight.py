"""PackSlotReadinessGuard preflight for Assistant & Governed MCP (`Story 31.7`, `<= 100 L`)."""

from __future__ import annotations

import re
from typing import Any

from fastapi import Request

from orcia_api.dependencies import get_agents_and_skills_service, get_workspace_packs_service
from orcia_core.packs import PinnedPackManifestEntry, parse_qualified_entity_ref

_REF_TOKEN_RE = re.compile(r"(?:^|\s)([@/][a-zA-Z0-9_.-]+(?:/[a-zA-Z0-9_.-]+)?)")


def _extract_referenced_pack_slugs(
    request: Request,
    *,
    prompt_text: str,
    entity_refs: tuple[str, ...],
) -> tuple[str, ...]:
    """Collect explicit or catalog-backed `pack_slug` values from prompt/entity refs."""
    pack_slugs: list[str] = []
    seen: set[str] = set()
    candidates = [*entity_refs, *_REF_TOKEN_RE.findall(prompt_text or "")]

    for raw in candidates:
        cleaned = raw.strip()
        if not cleaned:
            continue
        parsed = parse_qualified_entity_ref(cleaned)
        if parsed.is_qualified and not parsed.is_workspace_scope and parsed.pack_slug:
            if parsed.pack_slug not in seen:
                seen.add(parsed.pack_slug)
                pack_slugs.append(parsed.pack_slug)
        elif ":" in cleaned and not cleaned.startswith(("http:", "https:")):
            prefix = cleaned.split(":", 1)[0].strip().lstrip("@/").lower()
            if prefix and prefix not in seen:
                seen.add(prefix)
                pack_slugs.append(prefix)

    svc = get_agents_and_skills_service(request)
    bare_tokens = {c.strip().lstrip("@/").lower() for c in candidates if c.strip()}
    if bare_tokens:
        recs: tuple[Any, ...] = (*svc.agents, *svc.skills)
        for rec in recs:
            pslug = (rec.pack_slug or "").strip().lower()
            if not pslug or pslug in seen:
                continue
            eid = getattr(rec, "agent_id", getattr(rec, "skill_id", "")).lower()
            if rec.slug.lower() in bare_tokens or eid in bare_tokens:
                seen.add(pslug)
                pack_slugs.append(pslug)
    return tuple(pack_slugs)


async def enforce_pack_slot_readiness_preflight(
    request: Request,
    *,
    workspace_id: str | None,
    prompt_text: str = "",
    entity_refs: tuple[str, ...] = (),
) -> list[PinnedPackManifestEntry]:
    """Fail closed (`422 ERR_PACK_SLOT_UNBOUND`) when active/invoked slots are unbound."""
    packs_svc = get_workspace_packs_service(request)
    if not packs_svc.has_engine():
        return []
    inst = str(request.url.path)
    pack_slugs = _extract_referenced_pack_slugs(
        request, prompt_text=prompt_text, entity_refs=entity_refs
    )
    pinned: list[PinnedPackManifestEntry] = []
    for pslug in pack_slugs:
        pinned = await packs_svc.enforce_run_start_readiness(
            workspace_id=workspace_id,
            workflow_pack_id=pslug,
            instance=inst,
        )
    if not pack_slugs and workspace_id and workspace_id.strip():
        pinned = await packs_svc.enforce_run_start_readiness(
            workspace_id=workspace_id,
            workflow_pack_id=None,
            instance=inst,
        )
    return pinned


__all__ = ["enforce_pack_slot_readiness_preflight"]
