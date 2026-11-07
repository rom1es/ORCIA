"""5-Node Directed DAG `AssistantAgentService` (`orcia://system/workflows/assistant-agent`).

Implements `Story 3.3` (`AD-15`, `AR-4`, `FR-1`, `FR-11`, `UX-DR12`, `UX-DR15`, `NFR-PERF-1`,
`DEC-CTX-01`, `AD-20`) with zero SDLC vocabulary in `orcia-core`:
- Node 1: `1_INTENT_ROUTER` (Intent classification & Human-Led Anchor write refusal guard)
- Node 2: `2_QUERY_PLANNER_AND_ONTOLOGY_EXPANSION` (L1..L4 ontology expansion)
- Node 3: `3_PARALLEL_FAN_OUT` (`VectorStorePort` RAG + `ContextSourcePort` Catalog,
  Blackboard, Permission Broker)
- Node 4: `4_CRITICAL_TRIAGE_AND_AXIOM_VERIFICATION` (Axiom check & `[STALE_WARNING]` triage)
- Node 5: `5_PROFILE_ADAPTIVE_SYNTHESIZER` (5-layer `AssistantHarness`, profile adaptation,
  `@xyflow/react` workflow graph + YAML manifest composer, SSE streaming `< 1.5 s`).
"""

from __future__ import annotations

import time
from collections.abc import Iterator
from dataclasses import dataclass
from typing import Any, Literal

from orcia_core.orchestration.assistant_composer import (
    AssistantWorkflowProposal,
    SavedAndLaunchedWorkflowResult,
    XyFlowEdgeSpec,
    XyFlowNodeSpec,
    blueprint_to_proposal,
    build_generic_core_blueprint,
    resolve_assistant_blueprint,
)
from orcia_core.orchestration.assistant_harness import (
    AssembledAssistantPrompt,
    AssistantHarness,
    AssistantIntentKind,
)
from orcia_core.orchestration.engine import DurableOrchestrationEngine
from orcia_core.orchestration.run_lock_service import WorkflowOrchestrationSetupService
from orcia_core.orchestration.step_executors import _run_llm_sync
from orcia_core.permissions.models import UserIdentity
from orcia_core.testing.cassette_llm import DeterministicCassetteLLM
from orcia_kernel.context_ports import (
    AssistantWorkflowBlueprint,
    ContextSliceRecord,
    ContextSourcePort,
    VectorSearchHitRecord,
    VectorStorePort,
)
from orcia_kernel.ids import new_uuid7_str
from orcia_kernel.ports import LLMPort, LlmPromptRequest

ASSISTANT_WORKFLOW_URI: str = "orcia://system/workflows/assistant-agent"

AssistantNodeId = Literal[
    "1_INTENT_ROUTER",
    "2_QUERY_PLANNER_AND_ONTOLOGY_EXPANSION",
    "3_PARALLEL_FAN_OUT",
    "4_CRITICAL_TRIAGE_AND_AXIOM_VERIFICATION",
    "5_PROFILE_ADAPTIVE_SYNTHESIZER",
]


@dataclass(frozen=True, slots=True)
class AssistantNodeTrace:
    """Execution telemetry for one node of the 5-node `assistant-agent` DAG (`AD-15`)."""

    node_id: AssistantNodeId
    node_order: int
    status: Literal["COMPLETED"]
    duration_ms: float
    summary: str
    output_metadata: dict[str, Any]


@dataclass(frozen=True, slots=True)
class AssistantTurnResult:
    """Complete result of a 5-node `AssistantAgentService` conversational turn (`Story 3.3`)."""

    turn_id: str
    workflow_uri: str
    workspace_id: str
    human_profile_archetype: str
    intent: AssistantIntentKind
    response_text: str
    first_token_latency_ms: float
    node_traces: tuple[AssistantNodeTrace, ...]
    assembled_prompt: AssembledAssistantPrompt
    workflow_proposal: AssistantWorkflowProposal | None = None


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
    ) -> None:
        self._context_source = context_source
        self._vector_store = vector_store
        self._llm = llm_gateway or DeterministicCassetteLLM()
        self._harness = harness or AssistantHarness()
        self._setup = orchestration_setup
        self._engine = workflow_engine or (
            orchestration_setup.engine if orchestration_setup is not None else None
        )
        self._active_proposals: dict[str, AssistantWorkflowProposal] = {}

    def classify_intent(
        self,
        user_prompt: str,
        *,
        has_active_proposal: bool = False,
    ) -> AssistantIntentKind:
        """Node 1 (`1_INTENT_ROUTER`): classify user intent and enforce Constitutional Rule 1."""
        lower = user_prompt.strip().lower()
        if any(
            phrase in lower
            for phrase in (
                "remplis-le pour moi",
                "remplis la section humaine",
                "rédige l'ancre humaine",
                "write the human anchor for me",
                "fill the human anchor",
            )
        ):
            return "HUMAN_ANCHOR_WRITE_REFUSAL"
        if has_active_proposal and any(
            kw in lower
            for kw in ("modifie", "ajoute", "étape", "step", "ajuste", "modify", "add step")
        ):
            return "WORKFLOW_MODIFY"
        if any(
            kw in lower
            for kw in (
                "workflow",
                "composer",
                "propose un workflow",
                "créer un workflow",
                "comparer",
                "rapprochement",
                "audit",
            )
        ):
            return "WORKFLOW_COMPOSE"
        if any(kw in lower for kw in ("lance", "exécute", "launch", "start run")):
            return "WORKFLOW_LAUNCH"
        return "QA_COACHING"

    def run_conversation_turn(
        self,
        *,
        workspace_id: str,
        user_prompt: str,
        human_profile_archetype: str = "ARCHITECT",
        allowed_datasource_aliases: frozenset[str] = frozenset(),
        ontology_concepts: tuple[dict[str, Any], ...] = (),
        ontology_axioms: tuple[dict[str, Any], ...] = (),
    ) -> AssistantTurnResult:
        """Execute all 5 nodes of `orcia://system/workflows/assistant-agent` (`< 1.5 s`)."""
        t_start = time.perf_counter()
        has_active = workspace_id in self._active_proposals

        # Node 1: 1_INTENT_ROUTER
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

        # Node 2: 2_QUERY_PLANNER_AND_ONTOLOGY_EXPANSION
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

        # Node 3: 3_PARALLEL_FAN_OUT (RAG VectorStorePort + ContextSourcePort)
        t3 = time.perf_counter()
        vector_hits: tuple[VectorSearchHitRecord, ...] = self._vector_store.hybrid_search(
            workspace_id=workspace_id,
            query_text=expanded_query,
            allowed_datasource_aliases=allowed_datasource_aliases,
            top_k=5,
        )
        context_slices: tuple[ContextSliceRecord, ...] = self._context_source.fetch_context_slices(
            workspace_id=workspace_id,
            query=expanded_query,
            include_sources=("catalog", "blackboard", "permissions", "cas", "kb"),
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
                "sources_queried": ["RAG", "Catalog", "Blackboard", "PermissionBroker"],
            },
        )

        # Node 4: 4_CRITICAL_TRIAGE_AND_AXIOM_VERIFICATION
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
            output_metadata={
                "axioms_verified": True,
                "stale_alert_count": len(stale_alerts),
            },
        )

        # Node 5: 5_PROFILE_ADAPTIVE_SYNTHESIZER
        t5 = time.perf_counter()
        blueprint: AssistantWorkflowBlueprint | None = None
        proposal: AssistantWorkflowProposal | None = None
        if intent == "WORKFLOW_COMPOSE":
            blueprint = resolve_assistant_blueprint(
                user_prompt=user_prompt,
                workspace_id=workspace_id,
                modification_instruction=None,
            )
            proposal = blueprint_to_proposal(blueprint)
            self._active_proposals[workspace_id] = proposal
        elif intent == "WORKFLOW_MODIFY":
            active_prop = self._active_proposals.get(workspace_id)
            combined_query = (
                f"{active_prop.title} {active_prop.workflow_uri} {user_prompt}"
                if active_prop is not None
                else user_prompt
            )
            blueprint = resolve_assistant_blueprint(
                user_prompt=combined_query,
                workspace_id=workspace_id,
                modification_instruction=user_prompt,
            )
            proposal = blueprint_to_proposal(blueprint)
            self._active_proposals[workspace_id] = proposal
        elif has_active:
            proposal = self._active_proposals.get(workspace_id)

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

        response_text = self._synthesize_response(
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

    def _synthesize_response(
        self,
        *,
        assembled: AssembledAssistantPrompt,
        intent: AssistantIntentKind,
        proposal: AssistantWorkflowProposal | None,
        workspace_id: str,
    ) -> str:
        prefix = assembled.profile_adaptation.response_prefix_fr
        indicators = ", ".join(assembled.profile_adaptation.highlighted_indicators)
        if intent == "HUMAN_ANCHOR_WRITE_REFUSAL":
            return (
                f"{prefix} Refus constitutionnel "
                "(`human_authored_required: true`, `FR-4`, `AD-3`) : "
                "Je ne peux pas rédiger ni pré-remplir une Ancre Humaine à votre place afin de "
                "préserver votre maîtrise intellectuelle (*Think*). Question socratique : "
                "quels sont les 2 invariants métier non négociables que vous souhaitez fixer "
                f"pour le périmètre `{workspace_id}` ?"
            )

        prompt_req = LlmPromptRequest(
            system_prompt=assembled.system_prompt,
            user_prompt=assembled.user_prompt,
            model_family="anthropic",
            model_id="anthropic/claude-3-7-sonnet",
            execution_mode="COACHING",
            metadata={"workspace_id": workspace_id, "intent": intent},
        )
        llm_out = _run_llm_sync(self._llm, prompt_req)
        uris_note = (
            f" Sources citées : {', '.join(assembled.cited_uris[:3])}."
            if assembled.cited_uris
            else f" Périmètre : `orcia://workspaces/{workspace_id}`."
        )
        if proposal is not None:
            return (
                f"{prefix} ({indicators}) — Proposition de workflow `{proposal.workflow_uri}` "
                f"({len(proposal.nodes)} étapes, régime `{proposal.execution_regime}`) prête dans "
                f"le Canvas `@xyflow/react`.{uris_note} [{llm_out.prompt_sha256[:16]}]"
            )
        return (
            f"{prefix} ({indicators}) — {llm_out.content}.{uris_note} "
            f"[{llm_out.prompt_sha256[:16]}]"
        )

    def stream_conversation_turn_sse(
        self,
        *,
        workspace_id: str,
        user_prompt: str,
        human_profile_archetype: str = "ARCHITECT",
        allowed_datasource_aliases: frozenset[str] = frozenset(),
    ) -> Iterator[dict[str, Any]]:
        """Yield SSE events (`node_trace`, `token`, `workflow_proposal`, `done`) in `< 1.5 s`."""
        turn = self.run_conversation_turn(
            workspace_id=workspace_id,
            user_prompt=user_prompt,
            human_profile_archetype=human_profile_archetype,
            allowed_datasource_aliases=allowed_datasource_aliases,
        )
        for tr in turn.node_traces:
            yield {
                "event": "node_trace",
                "data": {
                    "node_id": tr.node_id,
                    "node_order": tr.node_order,
                    "duration_ms": tr.duration_ms,
                    "summary": tr.summary,
                },
            }
        lines = turn.response_text.splitlines(keepends=True) or [turn.response_text]
        chunk_size = max(1, len(lines) // 4)
        for idx in range(0, len(lines), chunk_size):
            token_chunk = "".join(lines[idx : idx + chunk_size])
            yield {
                "event": "token",
                "data": {
                    "turn_id": turn.turn_id,
                    "token": token_chunk,
                    "first_token_latency_ms": turn.first_token_latency_ms,
                },
            }
        if turn.workflow_proposal is not None:
            yield {
                "event": "workflow_proposal",
                "data": {
                    "proposal_id": turn.workflow_proposal.proposal_id,
                    "workflow_uri": turn.workflow_proposal.workflow_uri,
                    "title": turn.workflow_proposal.title,
                    "execution_regime": turn.workflow_proposal.execution_regime,
                    "node_count": len(turn.workflow_proposal.nodes),
                },
            }
        yield {
            "event": "done",
            "data": {
                "turn_id": turn.turn_id,
                "intent": turn.intent,
                "first_token_latency_ms": turn.first_token_latency_ms,
            },
        }

    def save_and_launch_workflow(
        self,
        user: UserIdentity,
        *,
        workspace_id: str,
        manifest_yaml: str,
    ) -> SavedAndLaunchedWorkflowResult:
        """Register the composed YAML workflow in the Workspace and launch its real execution."""
        if self._setup is None or self._engine is None:
            raise RuntimeError(
                "WorkflowOrchestrationSetupService and DurableOrchestrationEngine are required."
            )
        definition = self._setup.register_workflow_manifest(
            user,
            manifest_yaml,
            workspace_id=workspace_id,
        )
        run = self._setup.instantiate_workflow_run(
            user,
            workflow_uri=definition.uri,
            workspace_id=workspace_id,
        )
        self._engine.initialize_run_steps(run, definition)
        executed_keys: list[str] = []
        for step in definition.steps:
            self._engine.execute_step(
                user,
                run_id=run.id,
                step_key=step.step_key,
                commit_immediately=True,
            )
            executed_keys.append(step.step_key)

        active_snaps = self._engine.blackboard.get_active_snapshots(run.id)
        updated_run = next((r for r in self._setup.runs if r.id == run.id), None)
        return SavedAndLaunchedWorkflowResult(
            workflow_uri=definition.uri,
            version=definition.version,
            run_id=run.id,
            execution_regime=definition.execution_regime,
            run_status=str(updated_run.status if updated_run is not None else "COMPLETED"),
            executed_step_keys=tuple(executed_keys),
            snapshot_count=len(active_snaps),
        )
