"""5-Node Directed DAG `AssistantAgentService` (`orcia://system/workflows/assistant-agent`)."""

from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Callable, Iterator
from typing import Any

from orcia_core.orchestration._assistant_agent_nodes import execute_assistant_nodes_async
from orcia_core.orchestration.assistant_agent_models import (
    ASSISTANT_WORKFLOW_URI,
    AssistantNodeId,
    AssistantNodeTrace,
    AssistantTurnResult,
    AssistantWorkflowProposal,
    XyFlowEdgeSpec,
    XyFlowNodeSpec,
)
from orcia_core.orchestration.assistant_agent_synthesis import (
    classify_assistant_intent,
    iter_assistant_turn_sse_events,
    iter_assistant_turn_sse_events_async,
)
from orcia_core.orchestration.assistant_composer import (
    build_generic_core_blueprint as build_generic_core_blueprint,
)
from orcia_core.orchestration.assistant_harness import AssistantHarness, AssistantIntentKind
from orcia_core.orchestration.engine import DurableOrchestrationEngine
from orcia_core.orchestration.run_lock_service import WorkflowOrchestrationSetupService
from orcia_kernel.context_ports import ContextSourcePort, VectorStorePort
from orcia_kernel.ports import LLMPort

__all__ = [
    "ASSISTANT_WORKFLOW_URI",
    "AssistantAgentService",
    "AssistantNodeId",
    "AssistantNodeTrace",
    "AssistantTurnResult",
    "AssistantWorkflowProposal",
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
        self._llm: LLMPort | None = llm_gateway
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

    async def run_conversation_turn_async(
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
        """Execute all 5 nodes of `assistant-agent` asynchronously without event-loop blocking."""
        return await execute_assistant_nodes_async(
            harness=self._harness,
            context_source=self._context_source,
            vector_store=self._vector_store,
            llm_gateway=self._llm,
            cognitive_router=self._cognitive_router,
            active_proposals=self._active_proposals,
            classify_fn=self.classify_intent,
            workspace_id=workspace_id,
            user_prompt=user_prompt,
            human_profile_archetype=human_profile_archetype,
            allowed_datasource_aliases=allowed_datasource_aliases,
            ontology_concepts=ontology_concepts,
            ontology_axioms=ontology_axioms,
            embedding_available=embedding_available,
            allowed_source_uris=allowed_source_uris,
            source_uri_authorizer=source_uri_authorizer,
        )

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
        """Synchronous wrapper for non-async tests; forbids blocking an active event loop."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(
                self.run_conversation_turn_async(
                    workspace_id=workspace_id,
                    user_prompt=user_prompt,
                    human_profile_archetype=human_profile_archetype,
                    allowed_datasource_aliases=allowed_datasource_aliases,
                    ontology_concepts=ontology_concepts,
                    ontology_axioms=ontology_axioms,
                    embedding_available=embedding_available,
                    allowed_source_uris=allowed_source_uris,
                    source_uri_authorizer=source_uri_authorizer,
                )
            )
        raise RuntimeError(
            "AssistantAgentService.run_conversation_turn() cannot run inside an active loop; "
            "await run_conversation_turn_async() instead."
        )

    async def stream_conversation_turn_sse_async(
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
    ) -> AsyncIterator[dict[str, Any]]:
        """Yield SSE events (`node_trace`, `token`, `workflow_proposal`, `done`) asynchronously."""
        turn = await self.run_conversation_turn_async(
            workspace_id=workspace_id,
            user_prompt=user_prompt,
            human_profile_archetype=human_profile_archetype,
            allowed_datasource_aliases=allowed_datasource_aliases,
            ontology_concepts=ontology_concepts,
            ontology_axioms=ontology_axioms,
            embedding_available=embedding_available,
            allowed_source_uris=allowed_source_uris,
            source_uri_authorizer=source_uri_authorizer,
        )
        async for evt in iter_assistant_turn_sse_events_async(turn):
            yield evt

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
        """Synchronous SSE iterator for non-async callers."""
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
