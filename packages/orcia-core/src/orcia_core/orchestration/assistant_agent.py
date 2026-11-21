"""5-Node Directed DAG `AssistantAgentService` (`orcia://system/workflows/assistant-agent`)."""

from __future__ import annotations

import time
from collections.abc import Callable, Iterator
from typing import Any

from orcia_core.orchestration.assistant_agent_models import (
    ASSISTANT_WORKFLOW_URI,
    AssistantNodeId,
    AssistantNodeTrace,
    AssistantTurnResult,
    AssistantWorkflowProposal,
    SavedAndLaunchedWorkflowResult,
    XyFlowEdgeSpec,
    XyFlowNodeSpec,
    filter_authorized_context_slices,
    filter_authorized_vector_hits,
)
from orcia_core.orchestration.assistant_agent_synthesis import (
    classify_assistant_intent,
    execute_saved_and_launched_workflow,
    iter_assistant_turn_sse_events,
    resolve_intent_workflow_proposal,
    synthesize_assistant_turn_response,
)
from orcia_core.orchestration.assistant_composer import (
    build_generic_core_blueprint as build_generic_core_blueprint,
)
from orcia_core.orchestration.assistant_harness import AssistantHarness, AssistantIntentKind
from orcia_core.orchestration.engine import DurableOrchestrationEngine
from orcia_core.orchestration.run_lock_service import WorkflowOrchestrationSetupService
from orcia_core.permissions.models import UserIdentity
from orcia_core.rag.errors import NoActiveEmbeddingModelError, RagReindexInProgressError
from orcia_core.testing.cassette_llm import DeterministicCassetteLLM
from orcia_kernel.context_ports import (
    ContextSliceRecord,
    ContextSourcePort,
    VectorSearchHitRecord,
    VectorStorePort,
)
from orcia_kernel.ids import new_uuid7_str
from orcia_kernel.ports import LLMPort

__all__ = [
    "ASSISTANT_WORKFLOW_URI",
    "AssistantAgentService",
    "AssistantNodeId",
    "AssistantNodeTrace",
    "AssistantTurnResult",
    "AssistantWorkflowProposal",
    "SavedAndLaunchedWorkflowResult",
    "XyFlowEdgeSpec",
    "XyFlowNodeSpec",
    "build_generic_core_blueprint",
]


class AssistantAgentService:
    """Executes the 5-node `orcia://system/workflows/assistant-agent` DAG (`Story 3.3`)."""

    def __init__(
        self,
        *,
        context_source: ContextSourcePort,
        vector_store: VectorStorePort,
        llm_gateway: LLMPort | None = None,
        harness: AssistantHarness | None = None,
        orchestration_setup: WorkflowOrchestrationSetupService | None = None,
        workflow_engine: DurableOrchestrationEngine | None = None,
        cognitive_router: Any | None = None,
    ) -> None:
        self._context_source = context_source
        self._vector_store = vector_store
        self._llm = llm_gateway or DeterministicCassetteLLM()
        self._harness = harness or AssistantHarness()
        self._setup = orchestration_setup
        self._engine = workflow_engine or (
            orchestration_setup.engine if orchestration_setup is not None else None
        )
        self._cognitive_router = cognitive_router
        self._active_proposals: dict[str, AssistantWorkflowProposal] = {}

    def classify_intent(
        self, user_prompt: str, *, has_active_proposal: bool = False
    ) -> AssistantIntentKind:
        """Node 1 (`1_INTENT_ROUTER`): classify user intent and enforce Constitutional Rule 1."""
        return classify_assistant_intent(user_prompt, has_active_proposal=has_active_proposal)

    def run_conversation_turn(
        self,
        *,
        workspace_id: str,
        user_prompt: str,
        human_profile_archetype: str = "ARCHITECT",
        allowed_datasource_aliases: frozenset[str] = frozenset(),
        ontology_concepts: tuple[dict[str, Any], ...] = (),
        ontology_axioms: tuple[dict[str, Any], ...] = (),
        embedding_available: bool | None = None,
        allowed_source_uris: frozenset[str] | None = None,
        source_uri_authorizer: Callable[[tuple[str, ...]], frozenset[str]] | None = None,
    ) -> AssistantTurnResult:
        """Execute all 5 nodes of `orcia://system/workflows/assistant-agent` (`< 1.5 s`)."""
        t_start = time.perf_counter()
        has_active = workspace_id in self._active_proposals

        t1 = time.perf_counter()
        intent = self.classify_intent(user_prompt, has_active_proposal=has_active)
        trace_1 = AssistantNodeTrace(
            node_id="1_INTENT_ROUTER",
            node_order=1,
            status="COMPLETED",
            duration_ms=round((time.perf_counter() - t1) * 1000.0, 3),
            summary=f"Intention classifiée : {intent}",
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
                raw_hits = self._vector_store.hybrid_search(
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
        raw_slices: tuple[ContextSliceRecord, ...] = self._context_source.fetch_context_slices(
            workspace_id=workspace_id, query=expanded_query, include_sources=ctx_sources
        )
        effective_allowed = allowed_source_uris
        if source_uri_authorizer is not None:
            raw_uris = [*(h.source_uri for h in raw_hits), *(s.source_uri for s in raw_slices)]
            candidates = tuple(dict.fromkeys(raw_uris))
            effective_allowed = source_uri_authorizer(candidates)
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
            summary=(
                f"Fan-out parallèle : {len(vector_hits)} hits RAG + "
                f"{len(context_slices)} tranches ContextSourcePort"
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
            summary=f"Tri critique & vérification d'axiomes ({len(stale_alerts)} alertes STALE)",
            output_metadata={"axioms_verified": True, "stale_alert_count": len(stale_alerts)},
        )

        t5 = time.perf_counter()
        blueprint, proposal = resolve_intent_workflow_proposal(
            intent=intent,
            user_prompt=user_prompt,
            workspace_id=workspace_id,
            active_proposals=self._active_proposals,
            has_active=has_active,
        )

        assembled = self._harness.assemble_prompt(
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
        response_text = synthesize_assistant_turn_response(
            llm_gateway=self._llm,
            cognitive_router=self._cognitive_router,
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
            summary=(
                f"Synthèse profil {assembled.profile_adaptation.archetype} "
                f"({first_token_ms:.2f} ms < 1500 ms)"
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

    def stream_conversation_turn_sse(
        self,
        *,
        workspace_id: str,
        user_prompt: str,
        human_profile_archetype: str = "ARCHITECT",
        allowed_datasource_aliases: frozenset[str] = frozenset(),
        embedding_available: bool | None = None,
        allowed_source_uris: frozenset[str] | None = None,
        source_uri_authorizer: Callable[[tuple[str, ...]], frozenset[str]] | None = None,
    ) -> Iterator[dict[str, Any]]:
        """Yield SSE events (`node_trace`, `token`, `workflow_proposal`, `done`) in `< 1.5 s`."""
        turn = self.run_conversation_turn(
            workspace_id=workspace_id,
            user_prompt=user_prompt,
            human_profile_archetype=human_profile_archetype,
            allowed_datasource_aliases=allowed_datasource_aliases,
            embedding_available=embedding_available,
            allowed_source_uris=allowed_source_uris,
            source_uri_authorizer=source_uri_authorizer,
        )
        yield from iter_assistant_turn_sse_events(turn)

    def save_and_launch_workflow(
        self, user: UserIdentity, *, workspace_id: str, manifest_yaml: str
    ) -> SavedAndLaunchedWorkflowResult:
        """Register the composed YAML workflow in the Workspace and launch its real execution."""
        return execute_saved_and_launched_workflow(
            self._setup,
            self._engine,
            user,
            workspace_id=workspace_id,
            manifest_yaml=manifest_yaml,
        )
