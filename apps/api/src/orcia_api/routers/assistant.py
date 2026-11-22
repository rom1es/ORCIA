"""FastAPI Router for Story 3.3: 5-Node Assistant Agent DAG & Workflow Composer."""

from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse

from orcia_api.dependencies import get_assistant_service, get_optional_embedding_port
from orcia_api.dependencies._assistant_guards import (
    enforce_assistant_workspace_guard,
    prepare_server_source_uri_authorizer,
)
from orcia_api.routers._assistant_context_assembly import resolve_ranked_pg18_ontology_for_turn
from orcia_api.routers.assistant_llm_bridge import ensure_active_chat_model_if_live
from orcia_api.routers.auth import PROBLEM_RESPONSES, resolve_request_user
from orcia_api.schemas.assistant import (
    AssistantChatRequest,
    AssistantChatResponse,
    AssistantNodeTraceSchemaItem,
    AssistantSaveAndLaunchRequest,
    AssistantSaveAndLaunchResponse,
    AssistantWorkflowProposalSchemaItem,
    PromptLayerBlockSchemaItem,
    XyFlowEdgeSchemaItem,
    XyFlowNodeSchemaItem,
)
from orcia_core.orchestration.assistant_agent import AssistantTurnResult, AssistantWorkflowProposal
from orcia_core.ports.embedding import EmbeddingPort

router = APIRouter(prefix="/api/v1/assistant", tags=["assistant-agent"])


def _serialize_proposal(
    proposal: AssistantWorkflowProposal | None,
) -> AssistantWorkflowProposalSchemaItem | None:
    if proposal is None:
        return None
    return AssistantWorkflowProposalSchemaItem(
        proposal_id=proposal.proposal_id,
        workflow_uri=proposal.workflow_uri,
        title=proposal.title,
        description=proposal.description,
        execution_regime=proposal.execution_regime,
        manifest_yaml=proposal.manifest_yaml,
        nodes=[
            XyFlowNodeSchemaItem(
                id=n.id,
                position_x=n.position_x,
                position_y=n.position_y,
                label=n.label,
                step_type=n.step_type,
                human_authored_required=n.human_authored_required,
            )
            for n in proposal.nodes
        ],
        edges=[
            XyFlowEdgeSchemaItem(
                id=e.id,
                source=e.source,
                target=e.target,
                animated=e.animated,
            )
            for e in proposal.edges
        ],
    )


def _attach_embedding_port(service: Any, port: EmbeddingPort | None) -> None:
    if port is None:
        return
    vstore = getattr(service, "_vector_store", None)
    if vstore is not None:
        if getattr(vstore, "_embedding_port", None) is None:
            vstore._embedding_port = port
        rag = getattr(vstore, "_rag", None)
        if rag is not None and getattr(rag, "_embedding_port", None) is None:
            rag._embedding_port = port


def _serialize_turn(turn: AssistantTurnResult) -> AssistantChatResponse:
    pa = turn.assembled_prompt.profile_adaptation
    return AssistantChatResponse(
        turn_id=turn.turn_id,
        workflow_uri=turn.workflow_uri,
        workspace_id=turn.workspace_id,
        human_profile_archetype=turn.human_profile_archetype,
        register_label=pa.register_label,
        vocabulary_tier=pa.vocabulary_tier,
        highlighted_indicators=list(pa.highlighted_indicators),
        intent=turn.intent,
        response_text=turn.response_text,
        first_token_latency_ms=turn.first_token_latency_ms,
        constitutional_sha256=turn.assembled_prompt.constitutional_sha256,
        cited_uris=list(turn.assembled_prompt.cited_uris),
        stale_warnings=list(turn.assembled_prompt.stale_warnings),
        node_traces=[
            AssistantNodeTraceSchemaItem(
                node_id=tr.node_id,
                node_order=tr.node_order,
                status=tr.status,
                duration_ms=tr.duration_ms,
                summary=tr.summary,
                output_metadata=dict(tr.output_metadata),
            )
            for tr in turn.node_traces
        ],
        prompt_layers=[
            PromptLayerBlockSchemaItem(
                layer_id=layer.layer_id,
                layer_order=layer.layer_order,
                immutable=layer.immutable,
                content_sha256=layer.content_sha256,
            )
            for layer in turn.assembled_prompt.layers
        ],
        workflow_proposal=_serialize_proposal(turn.workflow_proposal),
    )


@router.post(
    "/chat",
    response_model=AssistantChatResponse,
    summary="Execute a 5-node conversational turn with `orcia://system/workflows/assistant-agent`",
    responses=PROBLEM_RESPONSES,
)
async def assistant_chat_turn(
    payload: AssistantChatRequest,
    request: Request,
    _embedding_port: Annotated[EmbeddingPort | None, Depends(get_optional_embedding_port)],
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> AssistantChatResponse:
    """Execute the 5-node Assistant Agent DAG and 5-layer `AssistantHarness` (`Story 3.3`)."""
    user = resolve_request_user(request, persona_key=persona_key)
    await enforce_assistant_workspace_guard(request, user, payload.workspace_id, require_write=True)
    await ensure_active_chat_model_if_live(request, workspace_id=payload.workspace_id)
    profile = payload.human_profile_archetype or user.human_profile_archetype
    svc = get_assistant_service(request)
    _attach_embedding_port(svc, _embedding_port)
    uri_authorizer = await prepare_server_source_uri_authorizer(
        request, user, workspace_id=payload.workspace_id
    )
    _, _, concepts_dicts, axioms_dicts, _ = await resolve_ranked_pg18_ontology_for_turn(
        request,
        workspace_id=payload.workspace_id,
        user_prompt=payload.user_prompt,
        hat=profile,
        embedding_port=_embedding_port,
    )
    turn = await svc.run_conversation_turn_async(
        workspace_id=payload.workspace_id,
        user_prompt=payload.user_prompt,
        human_profile_archetype=profile,
        allowed_datasource_aliases=frozenset(payload.allowed_datasource_aliases),
        ontology_concepts=concepts_dicts,
        ontology_axioms=axioms_dicts,
        embedding_available=_embedding_port is not None,
        source_uri_authorizer=uri_authorizer,
    )
    return _serialize_turn(turn)


@router.post(
    "/chat/stream",
    summary="Stream a 5-node Assistant Agent conversational turn via SSE (`< 1.5 s` first token)",
    responses={
        **PROBLEM_RESPONSES,
        200: {"content": {"text/event-stream": {"schema": {"type": "object"}}}},
    },
)
async def assistant_chat_stream(
    payload: AssistantChatRequest,
    request: Request,
    _embedding_port: Annotated[EmbeddingPort | None, Depends(get_optional_embedding_port)],
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> StreamingResponse:
    """Stream SSE events (`node_trace`, `token`, `workflow_proposal`, `done`) (`NFR-PERF-1`)."""
    user = resolve_request_user(request, persona_key=persona_key)
    await enforce_assistant_workspace_guard(request, user, payload.workspace_id, require_write=True)
    await ensure_active_chat_model_if_live(request, workspace_id=payload.workspace_id)
    profile = payload.human_profile_archetype or user.human_profile_archetype
    service = get_assistant_service(request)
    _attach_embedding_port(service, _embedding_port)
    uri_authorizer = await prepare_server_source_uri_authorizer(
        request, user, workspace_id=payload.workspace_id
    )
    _, _, concepts_dicts, axioms_dicts, _ = await resolve_ranked_pg18_ontology_for_turn(
        request,
        workspace_id=payload.workspace_id,
        user_prompt=payload.user_prompt,
        hat=profile,
        embedding_port=_embedding_port,
    )

    async def _event_generator() -> AsyncIterator[str]:
        async for evt in service.stream_conversation_turn_sse_async(
            workspace_id=payload.workspace_id,
            user_prompt=payload.user_prompt,
            human_profile_archetype=profile,
            allowed_datasource_aliases=frozenset(payload.allowed_datasource_aliases),
            ontology_concepts=concepts_dicts,
            ontology_axioms=axioms_dicts,
            embedding_available=_embedding_port is not None,
            source_uri_authorizer=uri_authorizer,
        ):
            event_name = evt["event"]
            data_json = json.dumps(evt["data"], ensure_ascii=False)
            yield f"event: {event_name}\ndata: {data_json}\n\n"

    return StreamingResponse(_event_generator(), media_type="text/event-stream")


@router.post(
    "/workflows/save-and-launch",
    response_model=AssistantSaveAndLaunchResponse,
    summary="Save a composed Workflow-as-Code manifest in the Workspace and launch its real run",
    responses=PROBLEM_RESPONSES,
)
async def assistant_save_and_launch_workflow(
    payload: AssistantSaveAndLaunchRequest,
    request: Request,
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> AssistantSaveAndLaunchResponse:
    """Register and execute a composed workflow via `orcia.step_executors` (`FR-11`, `UJ-10`)."""
    user = resolve_request_user(request, persona_key=persona_key)
    await enforce_assistant_workspace_guard(request, user, payload.workspace_id, require_write=True)
    result = await get_assistant_service(request).save_and_launch_workflow_async(
        user,
        workspace_id=payload.workspace_id,
        manifest_yaml=payload.manifest_yaml,
    )
    return AssistantSaveAndLaunchResponse(
        workflow_uri=result.workflow_uri,
        version=result.version,
        run_id=result.run_id,
        execution_regime=result.execution_regime,
        run_status=result.run_status,
        executed_step_keys=list(result.executed_step_keys),
        snapshot_count=result.snapshot_count,
    )
