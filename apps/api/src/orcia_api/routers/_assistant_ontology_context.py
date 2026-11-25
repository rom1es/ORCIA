"""PG18 Ontology Scope Resolution & Query-Aware Ranking for Assistant Turns (`Story 26.5`)."""

from __future__ import annotations

import asyncio
from typing import Any

from fastapi import Request

from orcia_api.dependencies._assistant_guards import resolve_assistant_workspace_uuid
from orcia_api.dependencies._core_providers import (
    get_configured_db_engine,
    get_ontology_and_rag_services,
)
from orcia_api.routers._ontology_promotions_helpers import (
    load_ontology_topology,
    resolve_dynamic_ontology_scopes,
)
from orcia_core.observability.logging import get_logger
from orcia_core.ontology import OntologyGovernanceService, load_ontology_governance_service_pg
from orcia_core.ontology.context_ranker import (
    RankedOntologyConcept,
    format_ranked_ontology_summary,
    rank_ontology_with_optional_embedding_async,
)
from orcia_core.ports.embedding import EmbeddingPort

logger = get_logger("orcia.assistant.context")


async def resolve_ranked_pg18_ontology_for_turn(
    request: Request,
    *,
    workspace_id: str,
    user_prompt: str,
    hat: str,
    embedding_port: EmbeddingPort | None = None,
    resolved_ws_uuid: str | None = None,
) -> tuple[
    tuple[RankedOntologyConcept, ...],
    tuple[Any, ...],
    tuple[dict[str, Any], ...],
    tuple[dict[str, Any], ...],
    str | None,
]:
    """Load PG18 ontology & topology concurrently, resolve scopes, and rank concepts."""
    engine = get_configured_db_engine(request)
    ont_svc: OntologyGovernanceService | None = None
    ent_scope = "scope-global"
    dom_scope = ""
    team_chain: tuple[str, ...] = ()
    ws_scope = workspace_id

    if engine is not None:
        try:
            if resolved_ws_uuid is None:
                ont_svc, (_, org_units, workspaces), resolved_ws_uuid = await asyncio.gather(
                    load_ontology_governance_service_pg(engine),
                    load_ontology_topology(request, fixture=False),
                    resolve_assistant_workspace_uuid(request, workspace_id),
                )
            else:
                ont_svc, (_, org_units, workspaces) = await asyncio.gather(
                    load_ontology_governance_service_pg(engine),
                    load_ontology_topology(request, fixture=False),
                )
            ws_key = resolved_ws_uuid or workspace_id
            target_ws = ws_key if ws_key != "GLOBAL" else workspace_id
            ent_scope, dom_scope, team_chain, ws_scope, _ = resolve_dynamic_ontology_scopes(
                "3_WORKSPACE", target_ws, org_units, workspaces
            )
            if not ws_scope:
                ws_scope = target_ws
        except Exception as exc:
            logger.warning("assistant_pg18_ontology_load_fallback", error_type=type(exc).__name__)
            ont_svc = None

    if ont_svc is None or not ont_svc.concepts:
        fallback_gov, _, _ = get_ontology_and_rag_services(request)
        if ont_svc is None or fallback_gov.concepts:
            ont_svc = fallback_gov

    if not ont_svc.concepts:
        return (), (), (), (), None

    for scope_candidate in (ws_scope, workspace_id) if ws_scope != workspace_id else (ws_scope,):
        ranked = await rank_ontology_with_optional_embedding_async(
            ont_svc,
            workspace_id=scope_candidate,
            query_text=user_prompt,
            active_hat=hat,
            embedding_port=embedding_port,
            enterprise_scope_id=ent_scope,
            domain_scope_id=dom_scope,
            team_chain_scope_ids=team_chain,
        )
        if ranked.selected_concepts:
            break
    concepts_dicts, axioms_dicts, summary = format_ranked_ontology_summary(ranked)
    return ranked.selected_concepts, ranked.applicable_axioms, concepts_dicts, axioms_dicts, summary
