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

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse

from orcia_api.dependencies import (
    get_assistant_citation_and_v5_guard_service,
    get_assistant_folders_and_sharing_service,
    get_assistant_governance_service,
    get_assistant_three_speed_router_service,
)
from orcia_api.routers.assistant_llm_bridge import invoke_configured_llm_for_assistant_turn
from orcia_api.routers.auth import resolve_request_user
from orcia_api.schemas.assistant import (
    ArtifactCardActionRequest,
    ArtifactCardActionResponse,
    AssembledLayerPreviewSchemaItem,
    AssistantFolderSchemaItem,
    AssistantGovernanceViewResponse,
    AssistantHistorySearchHitSchemaItem,
    AssistantStudioGraphStateSchemaItem,
    AssistantStudioNodeSchemaItem,
    AssistantThreadSchemaItem,
    AssistantWorkspaceOverviewResponse,
    ConfigureFolderSharingRequest,
    ConfigureFolderSharingResponse,
    CreateAssistantThreadRequest,
    CreateOrUpdateAssistantFolderRequest,
    EvidenceGlossaryCitationSchemaItem,
    EvidenceSourceCitationSchemaItem,
    EvidenceToolCitationSchemaItem,
    FolderShareGrantSchemaItem,
    InvalidatePromptCacheRequest,
    InvalidatePromptCacheResponse,
    LaunchProcessFromFolderRequest,
    LaunchProcessFromFolderResponse,
    ResetAssistantStudioGraphRequest,
    SaveAssistantStudioGraphRequest,
    SendCollaborativeThreadTurnRequest,
    SendCollaborativeThreadTurnResponse,
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
from orcia_core.orchestration.assistant_folders_and_sharing import (
    AssistantFoldersAndSharingService,
    FolderShareGrant,
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

router = APIRouter(prefix="/api/v1/assistant", tags=["assistant-workspace"])

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
FoldersSharingDep = Annotated[
    AssistantFoldersAndSharingService, Depends(get_assistant_folders_and_sharing_service)
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
    request: Request,
    user: CurrentUserDep,
    router_svc: ThreeSpeedRouterDep,
) -> ThreeSpeedTurnResponse:
    """Execute a 3-Speed conversational turn (`⚡ Rapide`, `@Agent / /Skill`, `🧠 Approfondi`)."""
    effective_deep_audit = payload.deep_audit_pill_active or payload.thinking_effort == "deep"
    effective_speed = payload.requested_speed
    if effective_speed is None and payload.thinking_effort == "deep":
        effective_speed = "SPEED_3_DEEP_AUDIT"
    elif effective_speed is None and payload.thinking_effort == "balanced":
        effective_speed = "SPEED_2_AGENT_TOOLS"

    live_outcome = invoke_configured_llm_for_assistant_turn(
        request,
        user_prompt=payload.user_prompt,
        hat=payload.hat or user.human_profile_archetype or "PLATFORM_ADMIN",
        speed_mode=effective_speed or "SPEED_1_FAST",
        requested_tier=payload.requested_tier,
        thinking_effort=payload.thinking_effort,
    )
    turn = router_svc.execute_three_speed_turn(
        user,
        workspace_id=payload.workspace_id,
        user_prompt=payload.user_prompt,
        hat=payload.hat,
        requested_speed=effective_speed,
        deep_audit_pill_active=effective_deep_audit,
        llm_response_override=live_outcome.response_text if live_outcome is not None else None,
        llm_step_label_override=live_outcome.step_label if live_outcome is not None else None,
        llm_latency_ms_override=live_outcome.latency_ms if live_outcome is not None else None,
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
    request: Request,
    user: CurrentUserDep,
    router_svc: ThreeSpeedRouterDep,
) -> StreamingResponse:
    """Stream SSE events (`cache_status`, `step_progress`, `token`, `done`) (`Story 10.2`)."""

    def _generate() -> Iterator[str]:
        effective_deep_audit = payload.deep_audit_pill_active or payload.thinking_effort == "deep"
        effective_speed = payload.requested_speed
        if effective_speed is None and payload.thinking_effort == "deep":
            effective_speed = "SPEED_3_DEEP_AUDIT"
        elif effective_speed is None and payload.thinking_effort == "balanced":
            effective_speed = "SPEED_2_AGENT_TOOLS"

        live_outcome = invoke_configured_llm_for_assistant_turn(
            request,
            user_prompt=payload.user_prompt,
            hat=payload.hat or user.human_profile_archetype or "PLATFORM_ADMIN",
            speed_mode=effective_speed or "SPEED_1_FAST",
            requested_tier=payload.requested_tier,
            thinking_effort=payload.thinking_effort,
        )
        for evt in router_svc.stream_three_speed_turn_sse(
            user,
            workspace_id=payload.workspace_id,
            user_prompt=payload.user_prompt,
            hat=payload.hat,
            requested_speed=effective_speed,
            deep_audit_pill_active=effective_deep_audit,
            llm_response_override=live_outcome.response_text if live_outcome is not None else None,
            llm_step_label_override=live_outcome.step_label if live_outcome is not None else None,
            llm_latency_ms_override=live_outcome.latency_ms if live_outcome is not None else None,
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


@router.post("/folders", response_model=AssistantFolderSchemaItem)
def create_or_update_assistant_folder_endpoint(
    payload: CreateOrUpdateAssistantFolderRequest,
    user: CurrentUserDep,
    folders_svc: FoldersSharingDep,
) -> AssistantFolderSchemaItem:
    """Create or update a thematic `📁 Dossier` (`📌 Notes du dossier`, Layer 5 continuity)."""
    record = folders_svc.create_or_update_folder(
        workspace_id=payload.workspace_id,
        user=user,
        title=payload.title,
        pinned_notes_markdown=payload.pinned_notes_markdown,
        working_attachments_uris=payload.working_attachments_uris,
        consolidated_summary=payload.consolidated_summary,
        evidence_tags=payload.evidence_tags,
        has_restricted_sources=payload.has_restricted_sources,
        folder_id=payload.folder_id,
    )
    layer5 = folders_svc.build_layer5_folder_memory_injection(
        workspace_id=payload.workspace_id,
        folder_id=record.folder_id,
    )
    return AssistantFolderSchemaItem(
        folder_id=record.folder_id,
        workspace_id=record.workspace_id,
        owner_user_id=record.owner_user_id,
        title=record.title,
        pinned_notes_markdown=record.pinned_notes_markdown,
        working_attachments_uris=list(record.working_attachments_uris),
        consolidated_summary=record.consolidated_summary,
        evidence_tags=list(record.evidence_tags),
        has_restricted_sources=record.has_restricted_sources,
        visibility_mode=record.visibility_mode,
        shares=[
            FolderShareGrantSchemaItem(
                grantee_user_id=g.grantee_user_id,
                access_role=g.access_role,
            )
            for g in record.shares
        ],
        assembled_layer5_prompt_block=layer5.assembled_layer5_prompt_block,
    )


@router.post("/threads", response_model=AssistantThreadSchemaItem)
def create_assistant_thread_endpoint(
    payload: CreateAssistantThreadRequest,
    user: CurrentUserDep,
    folders_svc: FoldersSharingDep,
) -> AssistantThreadSchemaItem:
    """Create a discussion thread inside a `📁 Dossier` (`Story 10.4`)."""
    thread = folders_svc.create_thread_in_folder(
        workspace_id=payload.workspace_id,
        user=user,
        title=payload.title,
        folder_id=payload.folder_id,
        initial_summary=payload.initial_summary,
    )
    return AssistantThreadSchemaItem(
        thread_id=thread.thread_id,
        workspace_id=thread.workspace_id,
        folder_id=thread.folder_id,
        creator_user_id=thread.creator_user_id,
        title=thread.title,
        thread_summary=thread.thread_summary,
        turn_count=thread.turn_count,
        last_author_user_id=thread.last_author_user_id,
        last_author_passthrough_identity=thread.last_author_passthrough_identity,
    )


@router.post("/folders/{folder_id}/share", response_model=ConfigureFolderSharingResponse)
def configure_folder_sharing_endpoint(
    folder_id: str,
    payload: ConfigureFolderSharingRequest,
    user: CurrentUserDep,
    folders_svc: FoldersSharingDep,
) -> ConfigureFolderSharingResponse:
    """Configure folder visibility (`🔒 Privé | 👥 Partagé | 📦 Espace`) confined to Workspace."""
    outcome = folders_svc.configure_folder_sharing(
        workspace_id=payload.workspace_id,
        folder_id=folder_id,
        owner_user=user,
        visibility_mode=payload.visibility_mode,
        shares=[
            FolderShareGrant(
                grantee_user_id=s.grantee_user_id,
                access_role=s.access_role,
            )
            for s in payload.shares
        ],
        outside_workspace_user_ids=payload.outside_workspace_user_ids,
    )
    return ConfigureFolderSharingResponse(
        folder_id=outcome.folder_id,
        workspace_id=outcome.workspace_id,
        visibility_mode=outcome.visibility_mode,
        shares=[
            FolderShareGrantSchemaItem(
                grantee_user_id=s.grantee_user_id,
                access_role=s.access_role,
            )
            for s in outcome.shares
        ],
        has_restricted_sources=outcome.has_restricted_sources,
        restricted_sources_warning=outcome.restricted_sources_warning,
    )


@router.post("/folders/{folder_id}/launch-process", response_model=LaunchProcessFromFolderResponse)
def launch_process_from_folder_endpoint(
    folder_id: str,
    payload: LaunchProcessFromFolderRequest,
    user: CurrentUserDep,
    folders_svc: FoldersSharingDep,
) -> LaunchProcessFromFolderResponse:
    """Pre-fill a Process contract in 1 click (`☍ Lancer un Processus à partir de ce dossier →`)."""
    prep = folders_svc.prepare_workflow_launch_from_folder(
        workspace_id=payload.workspace_id,
        folder_id=folder_id,
        user=user,
        target_workflow_uri=payload.target_workflow_uri,
    )
    return LaunchProcessFromFolderResponse(
        folder_id=prep.folder_id,
        workspace_id=prep.workspace_id,
        workflow_uri=prep.workflow_uri,
        initiated_by_user_id=prep.initiated_by_user_id,
        passthrough_identity=prep.passthrough_identity,
        prefilled_contract_inputs=prep.prefilled_contract_inputs,
    )


@router.post("/threads/{thread_id}/turns", response_model=SendCollaborativeThreadTurnResponse)
def send_collaborative_thread_turn_endpoint(
    thread_id: str,
    payload: SendCollaborativeThreadTurnRequest,
    user: CurrentUserDep,
    folders_svc: FoldersSharingDep,
) -> SendCollaborativeThreadTurnResponse:
    """Execute a turn in a shared thread under Redis turn lock (`NX EX 60`)."""
    outcome = folders_svc.send_collaborative_thread_turn(
        workspace_id=payload.workspace_id,
        thread_id=thread_id,
        sender_user=user,
        message_text=payload.message_text,
        release_lock_after_turn=payload.release_lock_after_turn,
    )
    return SendCollaborativeThreadTurnResponse(
        thread_id=outcome.thread_id,
        folder_id=outcome.folder_id,
        workspace_id=outcome.workspace_id,
        redis_lock_key=outcome.redis_lock_key,
        lock_holder_user_id=outcome.lock_holder_user_id,
        lock_ttl_seconds=outcome.lock_ttl_seconds,
        sse_presence_banner=outcome.sse_presence_banner,
        author_user_id=outcome.author_user_id,
        author_passthrough_identity=outcome.author_passthrough_identity,
        folder_creator_user_id=outcome.folder_creator_user_id,
        layer5_memory_injected=outcome.layer5_memory_injected,
        assembled_layer5_preview=outcome.assembled_layer5_preview,
        assistant_reply_markdown=outcome.assistant_reply_markdown,
    )


@router.get(
    "/workspaces/{workspace_id}/overview", response_model=AssistantWorkspaceOverviewResponse
)
def get_assistant_workspace_overview_endpoint(
    workspace_id: str,
    folders_svc: FoldersSharingDep,
    active_folder_id: str | None = Query(default=None),
    search_query: str = Query(default=""),
) -> AssistantWorkspaceOverviewResponse:
    """Return the 3-tab `Mon Assistant` workspace overview (`💬`, `📁`, `🕘`) (`Story 10.4`)."""
    overview = folders_svc.get_workspace_overview(
        workspace_id=workspace_id,
        active_folder_id=active_folder_id,
        search_query=search_query,
    )
    return AssistantWorkspaceOverviewResponse(
        workspace_id=overview.workspace_id,
        tabs=list(overview.tabs),
        active_folder_pill_label=overview.active_folder_pill_label,
        folders_count=overview.folders_count,
        folders=[
            AssistantFolderSchemaItem(
                folder_id=f.folder_id,
                workspace_id=f.workspace_id,
                owner_user_id=f.owner_user_id,
                title=f.title,
                pinned_notes_markdown=f.pinned_notes_markdown,
                working_attachments_uris=list(f.working_attachments_uris),
                consolidated_summary=f.consolidated_summary,
                evidence_tags=list(f.evidence_tags),
                has_restricted_sources=f.has_restricted_sources,
                visibility_mode=f.visibility_mode,
                shares=[
                    FolderShareGrantSchemaItem(
                        grantee_user_id=g.grantee_user_id,
                        access_role=g.access_role,
                    )
                    for g in f.shares
                ],
                assembled_layer5_prompt_block=folders_svc.build_layer5_folder_memory_injection(
                    workspace_id=workspace_id,
                    folder_id=f.folder_id,
                ).assembled_layer5_prompt_block,
            )
            for f in overview.folders
        ],
        threads=[
            AssistantThreadSchemaItem(
                thread_id=t.thread_id,
                workspace_id=t.workspace_id,
                folder_id=t.folder_id,
                creator_user_id=t.creator_user_id,
                title=t.title,
                thread_summary=t.thread_summary,
                turn_count=t.turn_count,
                last_author_user_id=t.last_author_user_id,
                last_author_passthrough_identity=t.last_author_passthrough_identity,
            )
            for t in overview.threads
        ],
        history_hits=[
            AssistantHistorySearchHitSchemaItem(
                item_id=h.item_id,
                item_kind=h.item_kind,
                title=h.title,
                snippet=h.snippet,
                folder_id=h.folder_id,
            )
            for h in overview.history_hits
        ],
    )
