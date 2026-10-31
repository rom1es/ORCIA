"""Epic 10 Router — `Mon Assistant` All-in-One (`Stories 10.1..10.4`).

Exposes:
- `GET /api/v1/assistant/governance` (`Story 10.1` Mode A 3 tabs + Mode B Studio graph)
- `PUT /api/v1/assistant/governance/mode-a/user` (`Story 10.1` Tab 1 `👤 Mes préférences`)
- `PUT /api/v1/assistant/governance/mode-a/workspace` (`Story 10.1` Tab 2 `📦 Espace` + MCP)
- `POST /api/v1/assistant/governance/mode-b/save` (`Story 10.1` Mode B Studio save)
- `POST /api/v1/assistant/governance/mode-b/reset` (`Story 10.1` Mode B 1-click reset)
"""

from __future__ import annotations

import json
from collections.abc import Iterator
from typing import Annotated

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from orcia_api.dependencies import (
    get_assistant_citation_and_v5_guard_service,
    get_assistant_governance_service,
    get_assistant_three_speed_router_service,
)
from orcia_api.routers.auth import resolve_request_user
from orcia_api.schemas.assistant import (
    ArtifactCardActionRequest,
    ArtifactCardActionResponse,
    AssembledLayerPreviewSchemaItem,
    AssistantGovernanceViewResponse,
    AssistantStudioGraphStateSchemaItem,
    AssistantStudioNodeSchemaItem,
    EvidenceGlossaryCitationSchemaItem,
    EvidenceSourceCitationSchemaItem,
    EvidenceToolCitationSchemaItem,
    InvalidatePromptCacheRequest,
    InvalidatePromptCacheResponse,
    ResetAssistantStudioGraphRequest,
    SaveAssistantStudioGraphRequest,
    ThreeSpeedStepProgressSchemaItem,
    ThreeSpeedTurnRequest,
    ThreeSpeedTurnResponse,
    UpdateUserLayerPreferencesRequest,
    UpdateWorkspaceLayerSettingsRequest,
    UserLayerPreferencesSchemaItem,
    VerifyAndFilterCitationsRequest,
    VerifyAndFilterCitationsResponse,
    WorkspaceLayerSettingsSchemaItem,
)
from orcia_core.orchestration.assistant_citations_and_v5_guard import (
    AssistantCitationAndV5GuardService,
    RawGlossaryCandidate,
    RawSourceCandidate,
    RawToolOutputCandidate,
)
from orcia_core.orchestration.assistant_governance import (
    AssistantFourLevelGovernanceService,
    AssistantStudioGraphState,
    AssistantStudioNodeSpec,
    UserLayerPreferences,
    WorkspaceLayerSettings,
)
from orcia_core.orchestration.assistant_three_speed_router import (
    AssistantThreeSpeedRouterService,
)
from orcia_core.permissions.models import UserIdentity

router = APIRouter(prefix="/api/v1/assistant", tags=["assistant-epic10"])

CurrentUserDep = Annotated[UserIdentity, Depends(resolve_request_user)]
GovernanceServiceDep = Annotated[
    AssistantFourLevelGovernanceService, Depends(get_assistant_governance_service)
]
ThreeSpeedRouterDep = Annotated[
    AssistantThreeSpeedRouterService, Depends(get_assistant_three_speed_router_service)
]
CitationGuardDep = Annotated[
    AssistantCitationAndV5GuardService, Depends(get_assistant_citation_and_v5_guard_service)
]


def _to_user_prefs_schema(prefs: UserLayerPreferences) -> UserLayerPreferencesSchemaItem:
    return UserLayerPreferencesSchemaItem(
        user_id=prefs.user_id,
        workspace_id=prefs.workspace_id,
        response_tone=prefs.response_tone,
        favorite_format=prefs.favorite_format,
        default_hat=prefs.default_hat,
        personal_instructions=prefs.personal_instructions,
        sha256=prefs.sha256,
    )


def _to_workspace_settings_schema(
    ws: WorkspaceLayerSettings,
) -> WorkspaceLayerSettingsSchemaItem:
    return WorkspaceLayerSettingsSchemaItem(
        workspace_id=ws.workspace_id,
        workspace_instructions=ws.workspace_instructions,
        default_checked_sources=list(ws.default_checked_sources),
        recommended_agents=list(ws.recommended_agents),
        arbitration_policy=ws.arbitration_policy,
        welcome_suggestions=list(ws.welcome_suggestions),
        mcp_expose_assistant=ws.mcp_expose_assistant,
        mcp_frozen_by_upper_layer=ws.mcp_frozen_by_upper_layer,
        mcp_frozen_origin=ws.mcp_frozen_origin,
        mcp_endpoint_url=ws.mcp_endpoint_url,
        mcp_tool_name=ws.mcp_tool_name,
        mcp_ide_config_json=ws.mcp_ide_config_json,
        sha256=ws.sha256,
    )


def _to_studio_graph_schema(
    st: AssistantStudioGraphState,
) -> AssistantStudioGraphStateSchemaItem:
    return AssistantStudioGraphStateSchemaItem(
        workflow_uri=st.workflow_uri,
        scope_level=st.scope_level,
        scope_id=st.scope_id,
        ai_pre_prompt=st.ai_pre_prompt,
        nodes=[
            AssistantStudioNodeSchemaItem(
                node_id=n.node_id,
                title=n.title,
                node_order=n.node_order,
                is_harness_boundary=n.is_harness_boundary,
                locked_by=n.locked_by,
                enabled=n.enabled,
                sub_layers_count=n.sub_layers_count,
                enabled_sub_layers=list(n.enabled_sub_layers),
                sub_agent_uri=n.sub_agent_uri,
            )
            for n in st.nodes
        ],
        override_key=st.override_key,
        sha256=st.sha256,
    )


@router.get("/governance", response_model=AssistantGovernanceViewResponse)
def get_assistant_governance_endpoint(
    user: CurrentUserDep,
    svc: GovernanceServiceDep,
    workspace_id: Annotated[str, Query()] = "ws-claims-alpha",
    pack_key: Annotated[str, Query()] = "orcia-pack-sdlc",
) -> AssistantGovernanceViewResponse:
    """Return Mode A (3 tabs) & Mode B (Studio graph) governance state (`Story 10.1`)."""
    view = svc.get_governance_view(user, workspace_id=workspace_id, pack_key=pack_key)
    return AssistantGovernanceViewResponse(
        workspace_id=view.workspace_id,
        can_edit_workspace_layer=view.can_edit_workspace_layer,
        can_open_studio_mode_b=view.can_open_studio_mode_b,
        user_preferences=_to_user_prefs_schema(view.user_preferences),
        workspace_settings=_to_workspace_settings_schema(view.workspace_settings),
        assembled_layers=[
            AssembledLayerPreviewSchemaItem(
                layer_number=layer.layer_number,
                layer_code=layer.layer_code,
                label=layer.label,
                immutable=layer.immutable,
                origin_badge=layer.origin_badge,
                content=layer.content,
                sha256=layer.sha256,
            )
            for layer in view.assembled_layers
        ],
        studio_graph=_to_studio_graph_schema(view.studio_graph),
    )


@router.put("/governance/mode-a/user", response_model=UserLayerPreferencesSchemaItem)
def update_user_layer_preferences_endpoint(
    payload: UpdateUserLayerPreferencesRequest,
    user: CurrentUserDep,
    svc: GovernanceServiceDep,
    router_svc: ThreeSpeedRouterDep,
) -> UserLayerPreferencesSchemaItem:
    """Update Tab 1 (`👤 Mes préférences — Couche 5 USER`) (`Story 10.1`)."""
    updated = svc.update_user_preferences(
        user,
        workspace_id=payload.workspace_id,
        response_tone=payload.response_tone,
        favorite_format=payload.favorite_format,
        default_hat=payload.default_hat,
        personal_instructions=payload.personal_instructions,
    )
    router_svc.invalidate_prompt_cache(
        workspace_id=payload.workspace_id,
        reason="OVERRIDE_UPDATED",
        user_id=user.id,
    )
    return _to_user_prefs_schema(updated)


@router.put("/governance/mode-a/workspace", response_model=WorkspaceLayerSettingsSchemaItem)
def update_workspace_layer_settings_endpoint(
    payload: UpdateWorkspaceLayerSettingsRequest,
    user: CurrentUserDep,
    svc: GovernanceServiceDep,
    router_svc: ThreeSpeedRouterDep,
) -> WorkspaceLayerSettingsSchemaItem:
    """Update Tab 2 (`📦 Réglages de l'Espace — Couche 4 WORKSPACE`) (`Story 10.1`)."""
    updated = svc.update_workspace_settings(
        user,
        workspace_id=payload.workspace_id,
        workspace_instructions=payload.workspace_instructions,
        default_checked_sources=tuple(payload.default_checked_sources),
        recommended_agents=tuple(payload.recommended_agents),
        arbitration_policy=payload.arbitration_policy,
        welcome_suggestions=(
            tuple(payload.welcome_suggestions) if payload.welcome_suggestions is not None else None
        ),
        mcp_expose_assistant=payload.mcp_expose_assistant,
    )
    router_svc.invalidate_prompt_cache(
        workspace_id=payload.workspace_id,
        reason="SETTINGS_CHANGED",
    )
    return _to_workspace_settings_schema(updated)


@router.post("/governance/mode-b/save", response_model=AssistantStudioGraphStateSchemaItem)
def save_assistant_studio_graph_endpoint(
    payload: SaveAssistantStudioGraphRequest,
    user: CurrentUserDep,
    svc: GovernanceServiceDep,
    router_svc: ThreeSpeedRouterDep,
) -> AssistantStudioGraphStateSchemaItem:
    """Save Mode B Studio graph override (`TEAM` or `WORKSPACE`) (`🔒 AssistantHarness`)."""
    saved = svc.save_studio_graph_override(
        user,
        scope_level=payload.scope_level,
        scope_id=payload.scope_id,
        ai_pre_prompt=payload.ai_pre_prompt,
        nodes=tuple(
            AssistantStudioNodeSpec(
                node_id=n.node_id,
                title=n.title,
                node_order=n.node_order,
                is_harness_boundary=n.is_harness_boundary,
                locked_by=n.locked_by,
                enabled=n.enabled,
                sub_layers_count=n.sub_layers_count,
                enabled_sub_layers=tuple(n.enabled_sub_layers),
                sub_agent_uri=n.sub_agent_uri,
            )
            for n in payload.nodes
        ),
    )
    router_svc.invalidate_prompt_cache(
        workspace_id=payload.scope_id,
        reason="OVERRIDE_UPDATED",
    )
    return _to_studio_graph_schema(saved)


@router.post("/governance/mode-b/reset", response_model=AssistantStudioGraphStateSchemaItem)
def reset_assistant_studio_graph_endpoint(
    payload: ResetAssistantStudioGraphRequest,
    user: CurrentUserDep,
    svc: GovernanceServiceDep,
    router_svc: ThreeSpeedRouterDep,
) -> AssistantStudioGraphStateSchemaItem:
    """Reset Mode B Studio override in 1 click (`↺ Réinitialiser`) (`Story 10.1`)."""
    restored = svc.reset_studio_graph_override(
        user,
        scope_level=payload.scope_level,
        scope_id=payload.scope_id,
    )
    router_svc.invalidate_prompt_cache(
        workspace_id=payload.scope_id,
        reason="OVERRIDE_UPDATED",
    )
    return _to_studio_graph_schema(restored)


@router.post("/three-speed/turn", response_model=ThreeSpeedTurnResponse)
def execute_three_speed_turn_endpoint(
    payload: ThreeSpeedTurnRequest,
    user: CurrentUserDep,
    router_svc: ThreeSpeedRouterDep,
) -> ThreeSpeedTurnResponse:
    """Execute a 3-Speed conversational turn (`⚡ Rapide`, `@Agent / /Skill`, `🧠 Approfondi`)."""
    turn = router_svc.execute_three_speed_turn(
        user,
        workspace_id=payload.workspace_id,
        user_prompt=payload.user_prompt,
        hat=payload.hat,
        requested_speed=payload.requested_speed,
        deep_audit_pill_active=payload.deep_audit_pill_active,
    )
    return ThreeSpeedTurnResponse(
        turn_id=turn.turn_id,
        workspace_id=turn.workspace_id,
        user_id=turn.user_id,
        hat=turn.hat,
        speed_mode=turn.speed_mode,
        cache_key=turn.cache_key,
        cache_hit=turn.cache_hit,
        cache_lookup_ms=turn.cache_lookup_ms,
        nodes_1_to_4_deterministic_ms=turn.nodes_1_to_4_deterministic_ms,
        ttft_ms=turn.ttft_ms,
        intermediate_llm_calls=turn.intermediate_llm_calls,
        invoked_targets=list(turn.invoked_targets),
        step_progress=[
            ThreeSpeedStepProgressSchemaItem(
                step_code=st.step_code,
                label=st.label,
                duration_ms=st.duration_ms,
                status=st.status,
                connector_or_lens=st.connector_or_lens,
            )
            for st in turn.step_progress
        ],
        response_text=turn.response_text,
        assembled_prompt_sha256=turn.assembled_prompt_sha256,
        deep_audit_lenses=list(turn.deep_audit_lenses),
    )


@router.post("/three-speed/stream")
def stream_three_speed_turn_endpoint(
    payload: ThreeSpeedTurnRequest,
    user: CurrentUserDep,
    router_svc: ThreeSpeedRouterDep,
) -> StreamingResponse:
    """Stream SSE events (`cache_status`, `step_progress`, `token`, `done`) (`Story 10.2`)."""

    def _generate() -> Iterator[str]:
        for evt in router_svc.stream_three_speed_turn_sse(
            user,
            workspace_id=payload.workspace_id,
            user_prompt=payload.user_prompt,
            hat=payload.hat,
            requested_speed=payload.requested_speed,
            deep_audit_pill_active=payload.deep_audit_pill_active,
        ):
            event_name = evt["event"]
            data_json = json.dumps(evt["data"], ensure_ascii=False)
            yield f"event: {event_name}\ndata: {data_json}\n\n"

    return StreamingResponse(_generate(), media_type="text/event-stream")


@router.post("/three-speed/invalidate-cache", response_model=InvalidatePromptCacheResponse)
def invalidate_prompt_cache_endpoint(
    payload: InvalidatePromptCacheRequest,
    user: CurrentUserDep,
    router_svc: ThreeSpeedRouterDep,
) -> InvalidatePromptCacheResponse:
    """Invalidate Redis 5-layer prompt cache (`SETTINGS_CHANGED` / `OVERRIDE_UPDATED`)."""
    outcome = router_svc.invalidate_prompt_cache(
        workspace_id=payload.workspace_id,
        reason=payload.reason,
        user_id=payload.user_id,
    )
    return InvalidatePromptCacheResponse(
        workspace_id=outcome.workspace_id,
        reason=outcome.reason,
        invalidated_keys_count=outcome.invalidated_keys_count,
        outbox_event_id=outcome.outbox_event_id,
    )


@router.post("/citations/verify-turn", response_model=VerifyAndFilterCitationsResponse)
def verify_and_filter_citations_endpoint(
    payload: VerifyAndFilterCitationsRequest,
    user: CurrentUserDep,
    citation_svc: CitationGuardDep,
) -> VerifyAndFilterCitationsResponse:
    """Build Evidence Table (`REFERENCE > ACTIVE`), filter `READ_SOURCE` & strip phantom tags."""
    table = citation_svc.build_evidence_table(
        sources=tuple(
            RawSourceCandidate(
                uri=s.uri,
                title=s.title,
                authority_tier=s.authority_tier,
                freshness=s.freshness,
                snippet=s.snippet,
                line_start=s.line_start,
                line_end=s.line_end,
                relevance_score=s.relevance_score,
            )
            for s in payload.sources
        ),
        glossary_items=tuple(
            RawGlossaryCandidate(
                term_or_axiom_id=g.term_or_axiom_id,
                label=g.label,
                ontology_level=g.ontology_level,
                definition=g.definition,
            )
            for g in payload.glossary_items
        ),
        tool_outputs=tuple(
            RawToolOutputCandidate(
                tool_name=t.tool_name,
                connector_uri=t.connector_uri,
                summary=t.summary,
            )
            for t in payload.tool_outputs
        ),
    )
    if payload.reader_allowed_source_uris is not None:
        table = citation_svc.filter_citation_map_for_reader(
            user,
            evidence_table=table,
            reader_allowed_source_uris=frozenset(payload.reader_allowed_source_uris),
        )
    verified = citation_svc.verify_and_sanitize_citations(
        response_text=payload.response_text,
        evidence_table=table,
        workspace_id=payload.workspace_id,
        user_id=user.id,
    )
    return VerifyAndFilterCitationsResponse(
        sanitized_text=verified.sanitized_text,
        valid_tags=list(verified.valid_tags),
        stripped_phantom_tags=list(verified.stripped_phantom_tags),
        verification_duration_ms=verified.verification_duration_ms,
        audit_id=verified.audit_entry.audit_id if verified.audit_entry is not None else None,
        sources=[
            EvidenceSourceCitationSchemaItem(
                tag=s.tag,
                index=s.index,
                uri=s.uri,
                title=s.title,
                authority_tier=s.authority_tier,
                freshness=s.freshness,
                snippet=s.snippet,
                line_start=s.line_start,
                line_end=s.line_end,
                restricted_access=s.restricted_access,
                display_pill=s.display_pill,
                request_access_uri=s.request_access_uri,
            )
            for s in table.sources
        ],
        glossary_items=[
            EvidenceGlossaryCitationSchemaItem(
                tag=g.tag,
                index=g.index,
                term_or_axiom_id=g.term_or_axiom_id,
                label=g.label,
                ontology_level=g.ontology_level,
                definition=g.definition,
            )
            for g in table.glossary_items
        ],
        tool_outputs=[
            EvidenceToolCitationSchemaItem(
                tag=t.tag,
                index=t.index,
                tool_name=t.tool_name,
                connector_uri=t.connector_uri,
                summary=t.summary,
            )
            for t in table.tool_outputs
        ],
        footer_summary_line=table.footer_summary_line,
        citation_map_emitted_at_ms=table.citation_map_emitted_at_ms,
    )


@router.post("/artifacts/action", response_model=ArtifactCardActionResponse)
def execute_artifact_card_action_endpoint(
    payload: ArtifactCardActionRequest,
    user: CurrentUserDep,
    citation_svc: CitationGuardDep,
) -> ArtifactCardActionResponse:
    """Execute a Structured Artifact Card action, enforcing Verrou V5 (`AD-15`)."""
    outcome = citation_svc.execute_artifact_card_action(
        user,
        workspace_id=payload.workspace_id,
        action_type=payload.action_type,
        artifact_title=payload.artifact_title,
        artifact_content=payload.artifact_content,
        cited_tags=tuple(payload.cited_tags),
        target_uri=payload.target_uri,
    )
    return ArtifactCardActionResponse(
        action_id=outcome.action_id,
        workspace_id=outcome.workspace_id,
        action_type=outcome.action_type,
        artifact_title=outcome.artifact_title,
        artifact_version_tag=outcome.artifact_version_tag,
        draft_uri=outcome.draft_uri,
        process_launch_prefill=outcome.process_launch_prefill,
    )
