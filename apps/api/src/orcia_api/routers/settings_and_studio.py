"""FastAPI router for Epic 8: Settings Hub (`/api/v1/settings/*`), RBAC 6-Verbs, LLM Tiers,
Connectors/Ingestion, Studio Governance & Durable DBOS Wizards (`Stories 8.1..8.6`, `AD-21`).
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Header, Query, Request, Response

from orcia_api.dependencies import (
    get_auth_service,
    get_cognitive_router_service,
    get_connector_hub_service,
    get_durable_wizard_service,
    get_hierarchical_rbac_service,
    get_platform_settings_service,
    get_studio_and_pack_service,
)
from orcia_api.schemas.problem_details import ProblemDetails
from orcia_api.schemas.settings_and_studio import (
    CognitiveRoutingOutcomeResponse,
    ConnectorTestConnectionResponse,
    DelegateGrantRequest,
    DemoWorkspaceProvisionResponse,
    DocumentIngestionRequest,
    DocumentIngestionResponse,
    EvaluateResourceAccessRequest,
    ExecuteTierRoutingRequest,
    InferenceAttemptResponse,
    LlmTierMappingResponse,
    OutboxReplayRequest,
    OutboxReplayResponse,
    PatchPlatformSettingRequest,
    PlatformSettingResponse,
    RagReciprocityResponse,
    ResourceDiscoveryResponse,
    RolePermissionGrantResponse,
    SecretStatusResponse,
    StudioDryRunRequest,
    StudioDryRunResponse,
    WizardAdvanceStepRequest,
    WizardSessionRequest,
    WizardSessionResponse,
)
from orcia_core.bootstrap import DurableOnboardingWizardService
from orcia_core.orchestration import (
    CognitiveModelRouterService,
    PinRemovalMode,
    ResolvedInferenceTier,
    WorkflowStudioAndPackService,
)
from orcia_core.permissions import (
    AuthAndOrganizationService,
    HierarchicalRbacService,
    PlatformSettingRecord,
    PlatformSettingsService,
    SecretInputSpec,
)
from orcia_core.rag import ConnectorHubAndIngestionService

EPIC8_PROBLEM_RESPONSES: dict[int | str, dict[str, Any]] = {
    400: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
    401: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
    403: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
    404: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
    409: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
    412: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
    422: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
    428: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
}

router = APIRouter(
    prefix="/api/v1",
    tags=["settings-and-studio"],
    responses=EPIC8_PROBLEM_RESPONSES,
)


def _to_setting_response(rec: PlatformSettingRecord) -> PlatformSettingResponse:
    return PlatformSettingResponse(
        id=rec.id,
        scope_level=rec.scope_level,
        scope_id=rec.scope_id,
        category=rec.category,
        key=rec.key,
        value_jsonb=rec.value_jsonb,
        secret_status=SecretStatusResponse(
            configured=rec.secret_status.configured,
            fingerprint=rec.secret_status.fingerprint,
            updated_at=rec.secret_status.updated_at,
            updated_by=rec.secret_status.updated_by,
        ),
        version=rec.version,
        etag=rec.etag,
        updated_at=rec.updated_at,
        updated_by=rec.updated_by,
    )


@router.post("/settings/iam/evaluate", response_model=ResourceDiscoveryResponse)
def evaluate_rbac_resource(
    payload: EvaluateResourceAccessRequest,
    request: Request,
    rbac: Annotated[HierarchicalRbacService, Depends(get_hierarchical_rbac_service)],
) -> ResourceDiscoveryResponse:
    """Evaluate 6-verb RBAC/ABAC access on a resource (`Story 8.1`)."""
    outcome = rbac.evaluate_resource_access(
        subject_id=payload.subject_id,
        subject_type=payload.subject_type,
        roles=tuple(payload.roles),
        scope_path=payload.scope_path,
        title=payload.title,
        context=payload.context,
        require_secret_read=payload.require_secret_read,
        require_execute=payload.require_execute,
        instance=str(request.url.path),
    )
    return ResourceDiscoveryResponse(
        scope_path=outcome.scope_path,
        title=outcome.title,
        allowed_verbs=list(outcome.allowed_verbs),
        locked=outcome.locked,
        reason=outcome.reason,
        can_request_access=outcome.can_request_access,
        secret_config_visible=outcome.secret_config_visible,
    )


@router.post("/settings/iam/grants", response_model=list[RolePermissionGrantResponse])
def delegate_rbac_grants(
    payload: DelegateGrantRequest,
    request: Request,
    auth: Annotated[AuthAndOrganizationService, Depends(get_auth_service)],
    rbac: Annotated[HierarchicalRbacService, Depends(get_hierarchical_rbac_service)],
) -> list[RolePermissionGrantResponse]:
    """Delegate a subset of held permissions (`grant` confinement, `Story 8.1`)."""
    delegator = auth.resolve_user(persona_key=payload.actor_persona)
    grants = rbac.delegate_grant(
        delegator,
        subject_type=payload.subject_type,
        subject_id=payload.subject_id,
        scope_path=payload.scope_path,
        verbs=tuple(payload.verbs),
        effect=payload.effect,
        inheritance_block=payload.inheritance_block,
        conditions=payload.conditions,
        hidden_when_unauthorized=payload.hidden_when_unauthorized,
        workspace_id=payload.workspace_id,
        instance=str(request.url.path),
    )
    return [
        RolePermissionGrantResponse(
            id=g.id,
            subject_type=g.subject_type,
            subject_id=g.subject_id,
            scope_path=g.scope_path,
            verb=g.verb,
            effect=g.effect,
            inheritance_block=g.inheritance_block,
            conditions=g.conditions,
            hidden_when_unauthorized=g.hidden_when_unauthorized,
            granted_by_user_id=g.granted_by_user_id,
            created_at_iso=g.created_at_iso,
        )
        for g in grants
    ]


@router.get("/settings/entries", response_model=list[PlatformSettingResponse])
def list_platform_settings(
    settings_svc: Annotated[PlatformSettingsService, Depends(get_platform_settings_service)],
) -> list[PlatformSettingResponse]:
    """List versioned platform settings with `ETag` and `SecretStatus` (`Story 8.3`)."""
    return [_to_setting_response(s) for s in settings_svc.list_settings()]


@router.patch("/settings/entries", response_model=PlatformSettingResponse)
def patch_platform_setting(
    payload: PatchPlatformSettingRequest,
    request: Request,
    response: Response,
    auth: Annotated[AuthAndOrganizationService, Depends(get_auth_service)],
    settings_svc: Annotated[PlatformSettingsService, Depends(get_platform_settings_service)],
    if_match: Annotated[str | None, Header(alias="If-Match")] = None,
) -> PlatformSettingResponse:
    """Mutate a versioned platform setting enforcing `If-Match` (`428`/`412`, `Story 8.3`)."""
    actor = auth.resolve_user(persona_key=payload.actor_persona)
    sec_in = (
        SecretInputSpec(
            action=payload.secret_input.action,
            plaintext_value=payload.secret_input.plaintext_value,
        )
        if payload.secret_input is not None
        else None
    )
    updated = settings_svc.patch_setting(
        actor,
        scope_level=payload.scope_level,
        scope_id=payload.scope_id,
        category=payload.category,
        key=payload.key,
        value_jsonb=payload.value_jsonb,
        if_match=if_match,
        secret_input=sec_in,
        instance=str(request.url.path),
    )
    response.headers["ETag"] = updated.etag
    return _to_setting_response(updated)


@router.post("/admin/outbox/replays", response_model=OutboxReplayResponse)
def replay_outbox_events(
    payload: OutboxReplayRequest,
    request: Request,
    auth: Annotated[AuthAndOrganizationService, Depends(get_auth_service)],
    settings_svc: Annotated[PlatformSettingsService, Depends(get_platform_settings_service)],
) -> OutboxReplayResponse:
    """Trigger bounded Outbox replay (`<= 500` events, `dry_run: true` default, `Story 8.3`)."""
    actor = auth.resolve_user(persona_key=payload.actor_persona)
    outcome = settings_svc.replay_outbox_events(
        actor,
        consumer_name=payload.consumer_name,
        event_ids=tuple(payload.event_ids),
        max_events=payload.max_events,
        dry_run=payload.dry_run,
        instance=str(request.url.path),
    )
    return OutboxReplayResponse(
        consumer_name=outcome.consumer_name,
        dry_run=outcome.dry_run,
        scanned_count=outcome.scanned_count,
        replayed_count=outcome.replayed_count,
        event_ids=list(outcome.event_ids),
    )


@router.get("/settings/ai-models/mappings", response_model=list[LlmTierMappingResponse])
def list_llm_tier_mappings(
    router_svc: Annotated[CognitiveModelRouterService, Depends(get_cognitive_router_service)],
) -> list[LlmTierMappingResponse]:
    """List workspace cognitive tier mappings (`Story 8.2`)."""
    return [
        LlmTierMappingResponse(
            id=m.id,
            scope_level=m.scope_level,
            scope_id=m.scope_id,
            inference_tier=m.inference_tier,
            effort=m.effort,
            provider_slug=m.provider_slug,
            model_family=m.model_family,
            model_name=m.model_name,
            max_tokens_budget=m.max_tokens_budget,
            max_cost_usd=m.max_cost_usd,
            fallback_order=m.fallback_order,
            is_active=m.is_active,
            draining=m.draining,
        )
        for m in router_svc.list_mappings()
    ]


@router.post("/settings/ai-models/route", response_model=CognitiveRoutingOutcomeResponse)
async def execute_cognitive_tier_route(
    payload: ExecuteTierRoutingRequest,
    router_svc: Annotated[CognitiveModelRouterService, Depends(get_cognitive_router_service)],
) -> CognitiveRoutingOutcomeResponse:
    """Execute cognitive tier routing and `auto` escalation (`Story 8.2`)."""

    def _gate_fn(_content: str, tier: ResolvedInferenceTier) -> tuple[bool, str]:
        if payload.fail_simple_tier_gate and tier == "simple":
            return False, "Simple tier deterministic schema gate failed"
        return True, ""

    outcome = await router_svc.execute_with_tier_routing(
        run_id=payload.run_id,
        step_execution_id=payload.step_execution_id,
        scope_id=payload.scope_id,
        system_prompt=payload.system_prompt,
        user_prompt=payload.user_prompt,
        inference_tier=payload.inference_tier,
        effort=payload.effort,
        evaluator_model_family=payload.evaluator_model_family,
        deterministic_gate_fn=_gate_fn,
    )
    return CognitiveRoutingOutcomeResponse(
        run_id=outcome.run_id,
        step_execution_id=outcome.step_execution_id,
        requested_tier=outcome.requested_tier,
        final_resolved_tier=outcome.final_resolved_tier,
        effort=outcome.effort,
        response_content=outcome.response_content,
        model_family=outcome.model_family,
        model_name=outcome.model_name,
        attempts=[
            InferenceAttemptResponse(
                id=a.id,
                attempt_index=a.attempt_index,
                requested_tier=a.requested_tier,
                resolved_tier=a.resolved_tier,
                effort=a.effort,
                model_family=a.model_family,
                model_name=a.model_name,
                deterministic_gate_passed=a.deterministic_gate_passed,
                failure_reason=a.failure_reason,
                cost_usd=a.cost_usd,
                idempotency_key=a.idempotency_key,
            )
            for a in outcome.attempts
        ],
        total_cost_usd=outcome.total_cost_usd,
        paused_budget_exceeded=outcome.paused_budget_exceeded,
    )


@router.delete("/settings/ai-models/mappings/{mapping_id}")
def delete_or_drain_llm_mapping(
    mapping_id: str,
    request: Request,
    router_svc: Annotated[CognitiveModelRouterService, Depends(get_cognitive_router_service)],
    mode: Annotated[PinRemovalMode, Query()] = "reject",
    actor_role: Annotated[str, Query()] = "PLATFORM_ADMIN",
) -> dict[str, str]:
    """Delete or drain an LLM tier mapping (`409 ERR_RESOURCE_PINNED_BY_ACTIVE_RUNS`)."""
    res = router_svc.delete_or_drain_mapping(
        mapping_id, mode=mode, actor_role=actor_role, instance=str(request.url.path)
    )
    return {"status": "DRAINING" if res is not None and res.draining else "DELETED"}


@router.post(
    "/settings/connectors/{connector_id}/test-connection",
    response_model=ConnectorTestConnectionResponse,
)
def test_connector_connection_endpoint(
    connector_id: str,
    request: Request,
    auth: Annotated[AuthAndOrganizationService, Depends(get_auth_service)],
    hub_svc: Annotated[ConnectorHubAndIngestionService, Depends(get_connector_hub_service)],
    actor_persona: Annotated[str, Query()] = "marc",
) -> ConnectorTestConnectionResponse:
    """Fail-fast DBOS connector connection test (`< 5 s`, `Story 8.4`)."""
    actor = auth.resolve_user(persona_key=actor_persona)
    res = hub_svc.test_connector_connection(actor, connector_id, instance=str(request.url.path))
    return ConnectorTestConnectionResponse(
        connector_id=res.connector_id,
        scheme=res.scheme,
        uri=res.uri,
        status=res.status,
        latency_ms=res.latency_ms,
        timeout_budget_ms=res.timeout_budget_ms,
        diagnostic_message=res.diagnostic_message,
        tested_at_iso=res.tested_at_iso,
    )


@router.post("/settings/connectors/ingest", response_model=DocumentIngestionResponse)
def ingest_document_endpoint(
    payload: DocumentIngestionRequest,
    request: Request,
    auth: Annotated[AuthAndOrganizationService, Depends(get_auth_service)],
    hub_svc: Annotated[ConnectorHubAndIngestionService, Depends(get_connector_hub_service)],
) -> DocumentIngestionResponse:
    """Run guarded document ingestion (`C0-C3`, `0 char` OCR, PII arbitration, `Story 8.4`)."""
    actor = auth.resolve_user(persona_key=payload.actor_persona)
    rep = hub_svc.ingest_document_with_guardrails(
        actor,
        workspace_id=payload.workspace_id,
        uri=payload.uri,
        title=payload.title,
        raw_extracted_text=payload.raw_extracted_text,
        classification=payload.classification,
        pii_decision=payload.pii_decision,
        instance=str(request.url.path),
    )
    return DocumentIngestionResponse(
        document_id=rep.document_id,
        workspace_id=rep.workspace_id,
        uri=rep.uri,
        title=rep.title,
        classification=rep.classification,
        status=rep.status,
        extracted_char_count=rep.extracted_char_count,
        pii_detected=rep.pii_detected,
        pii_categories=list(rep.pii_categories),
        arbitration_options=list(rep.arbitration_options),
        pseudonymized=rep.pseudonymized,
        audit_derogation_recorded=rep.audit_derogation_recorded,
        indexed_chunk_id=rep.indexed_chunk_id,
    )


@router.post(
    "/settings/connectors/documents/{document_id}/verify-reciprocity",
    response_model=RagReciprocityResponse,
)
def verify_rag_reciprocity_endpoint(
    document_id: str,
    request: Request,
    hub_svc: Annotated[ConnectorHubAndIngestionService, Depends(get_connector_hub_service)],
) -> RagReciprocityResponse:
    """1-click RAG reciprocity check (`Vérifier qu'il répond`, `Story 8.4`)."""
    res = hub_svc.verify_rag_reciprocity(document_id, instance=str(request.url.path))
    return RagReciprocityResponse(
        document_id=res.document_id,
        uri=res.uri,
        passed=res.passed,
        control_query=res.control_query,
        response_markdown=res.response_markdown,
        cited_uri=res.cited_uri,
        cited_chunk_id=res.cited_chunk_id,
    )


@router.post("/studio/revisions/{revision_id}/dry-run", response_model=StudioDryRunResponse)
def studio_what_if_dry_run_endpoint(
    revision_id: str,
    payload: StudioDryRunRequest,
    request: Request,
    studio_svc: Annotated[WorkflowStudioAndPackService, Depends(get_studio_and_pack_service)],
) -> StudioDryRunResponse:
    """Execute isolated Studio *What-If* dry-run (`▷ Tester`, `Story 8.5`)."""
    res = studio_svc.run_what_if_dry_run(
        revision_id,
        input_values=payload.input_values,
        preview_markdown_output=payload.preview_markdown_output,
        instance=str(request.url.path),
    )
    return StudioDryRunResponse(
        revision_id=res.revision_id,
        workflow_uri=res.workflow_uri,
        version=res.version,
        executed_steps=list(res.executed_steps),
        skipped_layers=list(res.skipped_layers),
        deterministic_structure_gate_passed=res.deterministic_structure_gate_passed,
        missing_markdown_sections=list(res.missing_markdown_sections),
        external_writes_count=res.external_writes_count,
    )


@router.post("/wizards/sessions", response_model=WizardSessionResponse)
def start_or_resume_wizard_endpoint(
    payload: WizardSessionRequest,
    request: Request,
    auth: Annotated[AuthAndOrganizationService, Depends(get_auth_service)],
    wizard_svc: Annotated[DurableOnboardingWizardService, Depends(get_durable_wizard_service)],
) -> WizardSessionResponse:
    """Start or resume a 5-step durable DBOS onboarding wizard (`Story 8.6`)."""
    actor = auth.resolve_user(persona_key=payload.actor_persona)
    rec = wizard_svc.start_or_resume_wizard(
        actor,
        wizard_type=payload.wizard_type,
        scope_id=payload.scope_id,
        instance=str(request.url.path),
    )
    return WizardSessionResponse(
        id=rec.id,
        wizard_type=rec.wizard_type,
        user_id=rec.user_id,
        scope_id=rec.scope_id,
        current_step_index=rec.current_step_index,
        total_steps=rec.total_steps,
        dbos_workflow_id=rec.dbos_workflow_id,
        status=rec.status,
        completed_steps=list(rec.completed_steps),
        rag_reciprocity_verified=rec.rag_reciprocity_verified,
        state_jsonb=rec.state_jsonb,
    )


@router.post("/wizards/sessions/{session_id}/steps", response_model=WizardSessionResponse)
def save_wizard_step_endpoint(
    session_id: str,
    payload: WizardAdvanceStepRequest,
    request: Request,
    auth: Annotated[AuthAndOrganizationService, Depends(get_auth_service)],
    wizard_svc: Annotated[DurableOnboardingWizardService, Depends(get_durable_wizard_service)],
) -> WizardSessionResponse:
    """Save step state (`SecretRef` only) and advance step in durable DBOS wizard (`Story 8.6`)."""
    actor = auth.resolve_user(persona_key=payload.actor_persona)
    sec_in = (
        SecretInputSpec(
            action=payload.secret_input.action,
            plaintext_value=payload.secret_input.plaintext_value,
        )
        if payload.secret_input is not None
        else None
    )
    rec = wizard_svc.save_step_and_advance(
        actor,
        session_id,
        step_index=payload.step_index,
        step_payload=payload.step_payload,
        secret_input=sec_in,
        instance=str(request.url.path),
    )
    return WizardSessionResponse(
        id=rec.id,
        wizard_type=rec.wizard_type,
        user_id=rec.user_id,
        scope_id=rec.scope_id,
        current_step_index=rec.current_step_index,
        total_steps=rec.total_steps,
        dbos_workflow_id=rec.dbos_workflow_id,
        status=rec.status,
        completed_steps=list(rec.completed_steps),
        rag_reciprocity_verified=rec.rag_reciprocity_verified,
        state_jsonb=rec.state_jsonb,
    )


@router.post("/wizards/demo-workspace", response_model=DemoWorkspaceProvisionResponse)
def provision_demo_workspace_endpoint(
    request: Request,
    auth: Annotated[AuthAndOrganizationService, Depends(get_auth_service)],
    wizard_svc: Annotated[DurableOnboardingWizardService, Depends(get_durable_wizard_service)],
    actor_persona: Annotated[Literal["karim", "claire", "marc", "nadia"], Query()] = "marc",
) -> DemoWorkspaceProvisionResponse:
    """Provision the Zero Empty-State Demo Workspace (`0` plaintext secrets, `Story 8.6`)."""
    actor = auth.resolve_user(persona_key=actor_persona)
    res = wizard_svc.provision_zero_empty_state_demo(actor, instance=str(request.url.path))
    return DemoWorkspaceProvisionResponse(
        workspace_id=res.workspace_id,
        workspace_slug=res.workspace_slug,
        workspace_name=res.workspace_name,
        ontology_concepts_seeded=res.ontology_concepts_seeded,
        kb_documents_indexed=res.kb_documents_indexed,
        published_workflow_uri=res.published_workflow_uri,
        rag_reciprocity_verified=res.rag_reciprocity_verified,
        plaintext_secrets_count=res.plaintext_secrets_count,
    )
