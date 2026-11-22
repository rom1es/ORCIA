"""Real PG18 Federated Context Assembly & `R6` Latency Benchmark (`Story 26.5`)."""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

from fastapi import Request

from orcia_api.dependencies._assistant_guards import (
    prepare_server_source_uri_authorizer,
    resolve_assistant_workspace_uuid,
)
from orcia_api.dependencies._core_providers import (
    get_configured_db_engine,
    get_ontology_and_rag_services,
)
from orcia_api.routers._ontology_promotions_helpers import (
    load_ontology_topology,
    resolve_dynamic_ontology_scopes,
)
from orcia_api.routers.ontology_rag_helpers import build_sql_rag_repo_from_request
from orcia_core.blackboard import list_active_workspace_blackboard_snapshots_pg
from orcia_core.observability.logging import get_logger
from orcia_core.ontology import (
    OntologyGovernanceService,
    load_ontology_governance_service_pg,
)
from orcia_core.ontology.context_ranker import (
    RankedOntologyConcept,
    build_websearch_or_query,
    format_ranked_ontology_summary,
    rank_ontology_with_optional_embedding_async,
)
from orcia_core.orchestration.assistant_citations_models import EvidenceTable
from orcia_core.orchestration.assistant_evidence_table import (
    build_server_evidence_table_for_turn,
    evidence_table_to_citation_map_dict,
)
from orcia_core.permissions.models import UserIdentity
from orcia_core.ports.embedding import EmbeddingPort
from orcia_core.rag._context_adapters_helpers import build_blackboard_slices
from orcia_core.rag.errors import NoActiveEmbeddingModelError, RagReindexInProgressError

logger = get_logger("orcia.assistant.context")


@dataclass(frozen=True, slots=True)
class AssembledTurnContext:
    """Real PG18 ontology, federated RAG/Blackboard `EvidenceTable`, and `R6` timing."""

    assembled_5_layers_prompt: str | None
    ontology_summary: str | None
    federated_evidence_summary: str | None
    evidence_table: EvidenceTable | None
    citation_map_dict: dict[str, Any]
    assembly_latency_ms: float
    ontology_concepts: tuple[dict[str, Any], ...] = ()
    ontology_axioms: tuple[dict[str, Any], ...] = ()


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


async def assemble_real_workspace_context_for_turn_async(
    request: Request,
    *,
    workspace_id: str,
    user_id: str,
    hat: str,
    user_prompt: str = "",
    user: UserIdentity | None = None,
    embedding_port: EmbeddingPort | None = None,
    locale: str = "fr",
) -> AssembledTurnContext:
    """Assemble Mode A, PG18 ontology, PG18 RAG/Blackboard `EvidenceTable` with `perf_counter`."""
    t_total = time.perf_counter()
    engine = get_configured_db_engine(request)
    ws_uuid = (
        await resolve_assistant_workspace_uuid(request, workspace_id) if engine else workspace_id
    )
    ws_uuid = workspace_id if ws_uuid == "GLOBAL" else ws_uuid

    async def _fetch_mode_a() -> tuple[str | None, float]:
        t0 = time.perf_counter()
        text: str | None = None
        try:
            from orcia_api.dependencies import get_assistant_three_speed_router_service

            router_svc = get_assistant_three_speed_router_service(request)
            cached = await router_svc.get_or_assemble_cached_prompt_async(
                workspace_id=workspace_id, user_id=user_id, hat=hat, locale=locale
            )
            text = cached.assembled_prompt_text
        except Exception as exc:
            logger.warning(
                "assistant_5_layer_prompt_resolution_fallback", error_type=type(exc).__name__
            )
        return text, round((time.perf_counter() - t0) * 1000.0, 3)

    async def _fetch_ontology() -> tuple[Any, ...]:
        t1 = time.perf_counter()
        try:
            res: tuple[Any, ...] = await resolve_ranked_pg18_ontology_for_turn(
                request,
                workspace_id=workspace_id,
                user_prompt=user_prompt,
                hat=hat,
                embedding_port=embedding_port,
                resolved_ws_uuid=ws_uuid,
            )
        except Exception as exc:
            logger.warning(
                "assistant_ontology_l1_l4_resolution_fallback", error_type=type(exc).__name__
            )
            res = ((), (), (), (), None)
        return *res, round((time.perf_counter() - t1) * 1000.0, 3)

    async def _fetch_blackboard() -> tuple[list[Any], float]:
        t3 = time.perf_counter()
        slices: list[Any] = []
        if engine is not None:
            try:
                snaps = await list_active_workspace_blackboard_snapshots_pg(
                    engine, workspace_id=ws_uuid
                )
                slices = build_blackboard_slices(snaps, workspace_id=ws_uuid, uri_filter=set())
            except Exception as exc:
                logger.warning("assistant_pg18_blackboard_fallback", error_type=type(exc).__name__)
        return slices, round((time.perf_counter() - t3) * 1000.0, 3)

    async def _fetch_authorizer() -> Callable[[tuple[str, ...]], frozenset[str]] | None:
        if user is None:
            return None
        return await prepare_server_source_uri_authorizer(request, user, workspace_id=workspace_id)

    (
        (assembled_text, mode_a_ms),
        (
            ranked_concepts,
            ranked_axioms,
            concepts_dicts,
            axioms_dicts,
            ontology_summary,
            ontology_ms,
        ),
        (bb_slices, blackboard_ms),
        authorizer,
    ) = await asyncio.gather(
        _fetch_mode_a(), _fetch_ontology(), _fetch_blackboard(), _fetch_authorizer()
    )

    t2 = time.perf_counter()
    rag_hits: tuple[Any, ...] = ()
    sql_rag_repo = build_sql_rag_repo_from_request(request)
    expanded_terms = [rc.concept.canonical_term for rc in ranked_concepts]
    expanded_query = f"{user_prompt} {' '.join(expanded_terms)}".strip()
    rag_websearch_query = build_websearch_or_query(user_prompt, expanded_terms)
    if sql_rag_repo is not None and rag_websearch_query:
        query_emb: tuple[float, ...] | None = None
        if embedding_port is not None:
            try:
                query_emb = tuple(await embedding_port.embed_query(expanded_query))
            except (NoActiveEmbeddingModelError, RagReindexInProgressError):
                query_emb = None
        try:
            rag_hits = await sql_rag_repo.search_hybrid_rrf(
                workspace_id=ws_uuid,
                query_text=rag_websearch_query,
                query_embedding=query_emb,
                limit=5,
            )
        except Exception as exc:
            logger.warning("assistant_pg18_rag_search_fallback", error_type=type(exc).__name__)
    rag_ms = round((time.perf_counter() - t2) * 1000.0, 3)

    candidate_uris = tuple(
        dict.fromkeys([*(h.source_uri for h in rag_hits), *(s.source_uri for s in bb_slices)])
    )
    allowed_uris: frozenset[str] | None = (
        authorizer(candidate_uris)
        if candidate_uris and authorizer is not None
        else (
            frozenset(u for u in candidate_uris if u.startswith(f"orcia://blackboard/{ws_uuid}/"))
            if candidate_uris and user is None
            else None
        )
    )

    evidence_res = build_server_evidence_table_for_turn(
        rag_hits=rag_hits,
        context_slices=bb_slices,
        ontology_concepts=ranked_concepts,
        ontology_axioms=ranked_axioms,
        allowed_source_uris=allowed_uris,
        locale=locale,
    )
    total_ms = round((time.perf_counter() - t_total) * 1000.0, 3)
    logger.info(
        "assistant_prompt_assembly_benchmarked",
        workspace_id=workspace_id,
        assembly_latency_ms=total_ms,
        mode_a_ms=mode_a_ms,
        ontology_ms=ontology_ms,
        rag_ms=rag_ms,
        blackboard_ms=blackboard_ms,
        embedding_active=embedding_port is not None,
        rag_hit_count=len(rag_hits),
        blackboard_slice_count=len(bb_slices),
        evidence_source_count=len(evidence_res.evidence_table.sources),
    )
    return AssembledTurnContext(
        assembled_5_layers_prompt=assembled_text,
        ontology_summary=ontology_summary,
        federated_evidence_summary=evidence_res.layer4_markdown or None,
        evidence_table=evidence_res.evidence_table,
        citation_map_dict=evidence_table_to_citation_map_dict(evidence_res.evidence_table),
        assembly_latency_ms=total_ms,
        ontology_concepts=concepts_dicts,
        ontology_axioms=axioms_dicts,
    )


__all__ = [
    "AssembledTurnContext",
    "assemble_real_workspace_context_for_turn_async",
    "resolve_ranked_pg18_ontology_for_turn",
]
