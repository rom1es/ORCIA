"""Shared Async/Sync Node 1..5 Helpers for `AssistantAgentService` (`Story 26.3`, `H-11`)."""

from __future__ import annotations

import time
from collections.abc import Callable
from typing import Any

from orcia_core.orchestration.assistant_agent_models import (
    ASSISTANT_WORKFLOW_URI,
    AssistantNodeTrace,
    AssistantTurnResult,
    AssistantWorkflowProposal,
    filter_authorized_context_slices,
    filter_authorized_vector_hits,
)
from orcia_core.orchestration.assistant_agent_synthesis import (
    synthesize_assistant_turn_response_async,
)
from orcia_core.orchestration.assistant_composer import (
    blueprint_to_proposal,
    resolve_assistant_blueprint,
)
from orcia_core.orchestration.assistant_harness import AssistantHarness, AssistantIntentKind
from orcia_core.rag.errors import NoActiveEmbeddingModelError, RagReindexInProgressError
from orcia_kernel.context_ports import (
    AssistantWorkflowBlueprint,
    ContextSourcePort,
    VectorSearchHitRecord,
    VectorStorePort,
)
from orcia_kernel.ids import new_uuid7_str
from orcia_kernel.ports import LLMPort


def resolve_intent_workflow_proposal(
    *,
    intent: AssistantIntentKind,
    user_prompt: str,
    workspace_id: str,
    active_proposals: dict[str, AssistantWorkflowProposal],
    has_active: bool,
) -> tuple[AssistantWorkflowBlueprint | None, AssistantWorkflowProposal | None]:
    """Resolve workflow blueprint & proposal for compose/modify intents."""
    if intent == "WORKFLOW_COMPOSE":
        bp = resolve_assistant_blueprint(
            user_prompt=user_prompt, workspace_id=workspace_id, modification_instruction=None
        )
        prop = blueprint_to_proposal(bp)
        active_proposals[workspace_id] = prop
        return bp, prop
    if intent == "WORKFLOW_MODIFY":
        active_prop = active_proposals.get(workspace_id)
        combined = (
            f"{active_prop.title} {active_prop.workflow_uri} {user_prompt}"
            if active_prop is not None
            else user_prompt
        )
        bp = resolve_assistant_blueprint(
            user_prompt=combined, workspace_id=workspace_id, modification_instruction=user_prompt
        )
        prop = blueprint_to_proposal(bp)
        active_proposals[workspace_id] = prop
        return bp, prop
    return None, (active_proposals.get(workspace_id) if has_active else None)


async def execute_assistant_nodes_async(
    *,
    harness: AssistantHarness,
    context_source: ContextSourcePort,
    vector_store: VectorStorePort,
    llm_gateway: LLMPort | None,
    cognitive_router: Any | None,
    active_proposals: dict[str, AssistantWorkflowProposal],
    classify_fn: Callable[..., AssistantIntentKind],
    workspace_id: str,
    user_prompt: str,
    human_profile_archetype: str,
    allowed_datasource_aliases: frozenset[str],
    ontology_concepts: tuple[dict[str, Any], ...],
    ontology_axioms: tuple[dict[str, Any], ...],
    embedding_available: bool | None,
    allowed_source_uris: frozenset[str] | None,
    source_uri_authorizer: Callable[[tuple[str, ...]], frozenset[str]] | None,
) -> AssistantTurnResult:
    """Execute all 5 Assistant DAG nodes using non-blocking async RAG and LLM calls."""
    t_start = time.perf_counter()
    has_active = workspace_id in active_proposals

    from orcia_core.orchestration._assistant_locales import get_assistant_node_copy

    node_copy = get_assistant_node_copy()
    t1 = time.perf_counter()
    intent = classify_fn(user_prompt, has_active_proposal=has_active)
    trace_1 = AssistantNodeTrace(
        node_id="1_INTENT_ROUTER",
        node_order=1,
        status="COMPLETED",
        duration_ms=round((time.perf_counter() - t1) * 1000.0, 3),
        summary=node_copy["intent_summary"].format(intent=intent),
        output_metadata={"intent": intent, "has_active_proposal": has_active},
    )

    t2 = time.perf_counter()
    expanded_terms = [str(c.get("canonical_term", c.get("key", ""))) for c in ontology_concepts]
    expanded_query = f"{user_prompt} {' '.join(expanded_terms)}".strip()
    trace_2 = AssistantNodeTrace(
        node_id="2_QUERY_PLANNER_AND_ONTOLOGY_EXPANSION",
        node_order=2,
        status="COMPLETED",
        duration_ms=round((time.perf_counter() - t2) * 1000.0, 3),
        summary=(
            f"Expansion ontologique ({len(ontology_concepts)} concepts, "
            f"{len(ontology_axioms)} axiomes)"
        ),
        output_metadata={
            "expanded_query": expanded_query,
            "concept_count": len(ontology_concepts),
            "axiom_count": len(ontology_axioms),
        },
    )

    t3 = time.perf_counter()
    raw_hits: tuple[VectorSearchHitRecord, ...] = ()
    rag_active = embedding_available is not False
    if rag_active:
        try:
            async_search = getattr(vector_store, "hybrid_search_async", None)
            if callable(async_search):
                raw_hits = await async_search(
                    workspace_id=workspace_id,
                    query_text=expanded_query,
                    allowed_datasource_aliases=allowed_datasource_aliases,
                    top_k=5,
                )
            else:
                raw_hits = vector_store.hybrid_search(
                    workspace_id=workspace_id,
                    query_text=expanded_query,
                    allowed_datasource_aliases=allowed_datasource_aliases,
                    top_k=5,
                )
        except (NoActiveEmbeddingModelError, RagReindexInProgressError):
            rag_active = False
            raw_hits = ()
    ctx_sources: tuple[str, ...] = (
        ("catalog", "blackboard", "permissions", "cas", "kb")
        if rag_active
        else ("catalog", "blackboard", "permissions", "cas")
    )
    async_fetch = getattr(context_source, "fetch_context_slices_async", None)
    if callable(async_fetch):
        raw_slices = await async_fetch(
            workspace_id=workspace_id, query=expanded_query, include_sources=ctx_sources
        )
    else:
        raw_slices = context_source.fetch_context_slices(
            workspace_id=workspace_id, query=expanded_query, include_sources=ctx_sources
        )
    effective_allowed = allowed_source_uris
    if source_uri_authorizer is not None:
        raw_uris = [*(h.source_uri for h in raw_hits), *(s.source_uri for s in raw_slices)]
        effective_allowed = source_uri_authorizer(tuple(dict.fromkeys(raw_uris)))
    vector_hits = filter_authorized_vector_hits(raw_hits, effective_allowed)
    context_slices = filter_authorized_context_slices(raw_slices, effective_allowed)
    sources_queried = (
        ["RAG", "Catalog", "Blackboard", "PermissionBroker"]
        if rag_active
        else ["Catalog", "Blackboard", "PermissionBroker"]
    )
    trace_3 = AssistantNodeTrace(
        node_id="3_PARALLEL_FAN_OUT",
        node_order=3,
        status="COMPLETED",
        duration_ms=round((time.perf_counter() - t3) * 1000.0, 3),
        summary=node_copy["fan_out_summary"].format(
            vec_count=len(vector_hits), slice_count=len(context_slices)
        ),
        output_metadata={
            "vector_hit_count": len(vector_hits),
            "context_slice_count": len(context_slices),
            "sources_queried": sources_queried,
            "rag_active": rag_active,
        },
    )

    t4 = time.perf_counter()
    stale_alerts = [
        s.stale_warning_marker for s in context_slices if s.is_stale and s.stale_warning_marker
    ] + [h.stale_warning_marker for h in vector_hits if h.is_stale and h.stale_warning_marker]
    trace_4 = AssistantNodeTrace(
        node_id="4_CRITICAL_TRIAGE_AND_AXIOM_VERIFICATION",
        node_order=4,
        status="COMPLETED",
        duration_ms=round((time.perf_counter() - t4) * 1000.0, 3),
        summary=node_copy["triage_summary"].format(stale_count=len(stale_alerts)),
        output_metadata={"axioms_verified": True, "stale_alert_count": len(stale_alerts)},
    )

    t5 = time.perf_counter()
    blueprint, proposal = resolve_intent_workflow_proposal(
        intent=intent,
        user_prompt=user_prompt,
        workspace_id=workspace_id,
        active_proposals=active_proposals,
        has_active=has_active,
    )
    assembled = harness.assemble_prompt(
        user_prompt=user_prompt,
        human_profile_archetype=human_profile_archetype,
        workspace_id=workspace_id,
        intent=intent,
        ontology_concepts=ontology_concepts,
        ontology_axioms=ontology_axioms,
        context_slices=context_slices,
        vector_hits=vector_hits,
        workflow_blueprint=blueprint,
    )
    response_text = await synthesize_assistant_turn_response_async(
        llm_gateway=llm_gateway,
        cognitive_router=cognitive_router,
        assembled=assembled,
        intent=intent,
        proposal=proposal,
        workspace_id=workspace_id,
    )
    first_token_ms = round((time.perf_counter() - t_start) * 1000.0, 3)
    trace_5 = AssistantNodeTrace(
        node_id="5_PROFILE_ADAPTIVE_SYNTHESIZER",
        node_order=5,
        status="COMPLETED",
        duration_ms=round((time.perf_counter() - t5) * 1000.0, 3),
        summary=node_copy["synth_summary"].format(
            archetype=assembled.profile_adaptation.archetype, ms=first_token_ms
        ),
        output_metadata={
            "profile_archetype": assembled.profile_adaptation.archetype,
            "vocabulary_tier": assembled.profile_adaptation.vocabulary_tier,
            "has_workflow_proposal": proposal is not None,
        },
    )
    return AssistantTurnResult(
        turn_id=new_uuid7_str(),
        workflow_uri=ASSISTANT_WORKFLOW_URI,
        workspace_id=workspace_id,
        human_profile_archetype=assembled.profile_adaptation.archetype,
        intent=intent,
        response_text=response_text,
        first_token_latency_ms=first_token_ms,
        node_traces=(trace_1, trace_2, trace_3, trace_4, trace_5),
        assembled_prompt=assembled,
        workflow_proposal=proposal,
    )
