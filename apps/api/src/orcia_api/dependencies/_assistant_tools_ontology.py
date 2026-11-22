"""Workspace-Scoped Ontology Lookup & Visibility Helpers (`Story 26.6b`)."""

from __future__ import annotations

from typing import Any

from fastapi import Request

from orcia_api.dependencies._core_providers import (
    get_auth_service,
    get_configured_db_engine,
    get_ontology_and_rag_services,
)
from orcia_api.dependencies._rag_availability_guards import get_optional_embedding_port
from orcia_core.observability.logging import get_logger
from orcia_core.ontology import (
    OntologyGovernanceService,
    find_org_unit,
    load_ontology_governance_service_pg,
    load_org_and_workspaces_context,
)
from orcia_core.ontology.context_ranker import (
    format_ranked_ontology_summary,
    rank_ontology_with_optional_embedding_async,
)
from orcia_core.permissions.models import OrgUnitNode, UserIdentity, WorkspaceEntity

logger = get_logger("orcia.api.dependencies.assistant_tools.ontology")


def is_record_visible_in_workspace(
    record: Any,
    *,
    ws_uuid: str,
    ws_slug: str,
    user: UserIdentity | None,
) -> bool:
    """Enforce workspace, `PRIVATE` owner, and `visibility_scope` isolation on skills/agents."""
    if not getattr(record, "enabled_in_workspace", True):
        return False
    vis = str(getattr(record, "visibility_scope", "TEAM") or "TEAM").strip().upper()
    owner_ws = getattr(record, "owner_workspace_id", None)
    owner_uid = getattr(record, "owner_user_id", None)
    if owner_ws and owner_ws not in {ws_uuid, ws_slug}:
        return False
    if vis == "PRIVATE":
        if user is None or not user.id or user.id == "u-anonymous":
            return False
        if owner_uid and owner_uid != user.id:
            return False
    return True


def _resolve_workspace_slug_and_hierarchy(
    request: Request,
    workspace_id: str,
    org_units: tuple[OrgUnitNode, ...],
    workspaces: tuple[WorkspaceEntity, ...],
) -> tuple[str, str, str, tuple[str, ...], frozenset[str]]:
    evaluator = get_auth_service(request).evaluator
    ws = evaluator.get_workspace(workspace_id)
    if ws is None:
        ws = next((w for w in workspaces if w.id == workspace_id or w.slug == workspace_id), None)
    target_ws = ws.id if ws is not None else workspace_id
    ws_slug = ws.slug if ws is not None else workspace_id
    by_id = {u.id: u for u in org_units}
    dom_scope = ""
    team_chain: list[str] = []
    cur = find_org_unit(org_units, ws.owner_org_unit_id) if ws is not None else None
    visited: set[str] = set()
    while cur is not None and cur.id not in visited and len(visited) < 32:
        visited.add(cur.id)
        if cur.unit_type in ("TEAM", "SUB_TEAM"):
            team_chain.append(cur.id)
        elif cur.unit_type in ("BU", "TRIBE") and not dom_scope:
            dom_scope = cur.id
        cur = by_id.get(cur.parent_id) if cur.parent_id else None
    allowed_scopes = frozenset(
        s for s in ("scope-global", target_ws, workspace_id, ws_slug, dom_scope, *team_chain) if s
    )
    return target_ws, ws_slug, dom_scope, tuple(team_chain), allowed_scopes


async def run_workspace_ontology_lookup(
    request: Request,
    *,
    ws_id: str,
    query: str,
    level: str | None,
) -> list[dict[str, Any]]:
    """Resolve effective L1-L4 ontology concepts strictly scoped to workspace & ancestors."""
    engine = get_configured_db_engine(request)
    evaluator = get_auth_service(request).evaluator
    org_units = tuple(evaluator.org_units)
    workspaces = tuple(evaluator.workspaces)
    ont_svc: OntologyGovernanceService | None = None
    if engine is not None:
        try:
            ont_svc = await load_ontology_governance_service_pg(engine)
            org_units, workspaces = await load_org_and_workspaces_context(engine)
        except Exception as exc:
            logger.warning("tool_ontology_pg_load_fallback", error_type=type(exc).__name__)
    if ont_svc is None or not ont_svc.concepts:
        ont_svc, _, _ = get_ontology_and_rag_services(request)
    target_ws, _, dom_scope, team_chain, allowed_scopes = _resolve_workspace_slug_and_hierarchy(
        request, ws_id, org_units, workspaces
    )
    ranked = await rank_ontology_with_optional_embedding_async(
        ont_svc,
        workspace_id=target_ws,
        query_text=query or "ontology",
        active_hat="ARCHITECT",
        embedding_port=await get_optional_embedding_port(request),
        enterprise_scope_id="scope-global",
        domain_scope_id=dom_scope,
        team_chain_scope_ids=team_chain,
    )
    concepts_dicts, axioms_dicts, _ = format_ranked_ontology_summary(ranked)
    items = [*concepts_dicts, *axioms_dicts]
    if not items:
        items = [
            {
                "canonical_term": c.canonical_term,
                "level": c.level,
                "definition": c.definition_text,
            }
            for c in ont_svc.concepts
            if c.level == "1_ENTERPRISE" or c.scope_id in allowed_scopes
        ]
    if level:
        norm_lvl = level.strip().upper()
        items = [it for it in items if norm_lvl in str(it.get("level", "")).upper()]
    return items[:12]


__all__ = ["is_record_visible_in_workspace", "run_workspace_ontology_lookup"]
