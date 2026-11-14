"""FastAPI router for Epic 8 & Story 17.3: Settings Hub (`/api/v1/settings/*`), RBAC 6-Verbs
SecOps Grants (`GET/POST/DELETE /settings/iam/grants`), LLM Tiers & Connectors (`AD-21`).

Studio Dry-Run & Durable Wizards were extracted to `studio_and_wizards.py` (`< 400`-line hygiene).
"""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Header, Path, Query, Request, Response

from orcia_api.dependencies import (
    get_auth_service,
    get_cognitive_router_service,
    get_connector_hub_service,
    get_hierarchical_rbac_service,
    get_or_create_shared_db_engine,
    get_platform_settings_service,
)
from orcia_api.routers._settings_helpers import (
    SETTINGS_PROBLEM_RESPONSES,
    enforce_not_observer_mode,
    is_pg_bootstrap_enabled,
    serialize_grant,
    to_llm_mapping_response,
    to_routing_outcome_response,
    to_setting_response,
)
from orcia_api.routers.auth import resolve_request_user
from orcia_api.schemas.settings_and_studio import (
    CognitiveRoutingOutcomeResponse,
    ConnectorTestConnectionResponse,
    DelegateGrantRequest,
    DocumentIngestionRequest,
    DocumentIngestionResponse,
    EvaluateResourceAccessRequest,
    ExecuteTierRoutingRequest,
    GrantDeleteResponse,
    LlmTierMappingResponse,
    OutboxReplayRequest,
    OutboxReplayResponse,
    PatchPlatformSettingRequest,
    PlatformSettingResponse,
    RagReciprocityResponse,
    ResourceDiscoveryResponse,
    RolePermissionGrantResponse,
)
from orcia_core.bootstrap import (
    create_iam_grants_on_postgres18,
    delete_iam_grant_on_postgres18,
    list_iam_grants_from_postgres18,
)
from orcia_core.observability.logging import get_current_trace_id, get_logger
from orcia_core.orchestration import (
    CognitiveModelRouterService,
    PinRemovalMode,
    ResolvedInferenceTier,
)
from orcia_core.permissions import (
    AuthAndOrganizationService,
    HierarchicalRbacService,
    PlatformSettingsService,
    SecretInputSpec,
)
from orcia_core.permissions.errors import OrciaDomainError
from orcia_core.rag import ConnectorHubAndIngestionService

logger = get_logger("orcia.api.settings")

router = APIRouter(
    prefix="/api/v1",
    tags=["settings-and-studio"],
    responses=SETTINGS_PROBLEM_RESPONSES,
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


@router.get("/settings/iam/grants", response_model=list[RolePermissionGrantResponse])
async def list_rbac_grants(
    request: Request,
    rbac: Annotated[HierarchicalRbacService, Depends(get_hierarchical_rbac_service)],
    scope_path: Annotated[str | None, Query(max_length=512)] = None,
) -> list[RolePermissionGrantResponse]:
    """List SecOps RBAC/ABAC exceptions and isolation rules (`Story 17.3`)."""
    if is_pg_bootstrap_enabled():
        try:
            engine = get_or_create_shared_db_engine(request)
            pg_grants = await list_iam_grants_from_postgres18(engine)
            if pg_grants:
                rbac.replace_grants(tuple(pg_grants))
                items = rbac.list_grants(scope_path=scope_path)
                return [serialize_grant(g) for g in items]
        except OrciaDomainError:
            raise
        except Exception as exc:
            logger.warning("iam_grants_list_pg_fallback", error_type=type(exc).__name__)
    return [serialize_grant(g) for g in rbac.list_grants(scope_path=scope_path)]


@router.post("/settings/iam/grants", response_model=list[RolePermissionGrantResponse])
async def delegate_rbac_grants(
    payload: DelegateGrantRequest,
    request: Request,
    rbac: Annotated[HierarchicalRbacService, Depends(get_hierarchical_rbac_service)],
) -> list[RolePermissionGrantResponse]:
    """Delegate a subset of held permissions or isolate scope (`Story 8.1`, `Story 17.3`)."""
    enforce_not_observer_mode(request)
    delegator = resolve_request_user(request, persona_key=payload.actor_persona)
    grants = rbac.delegate_grant(
        delegator,
        subject_type=payload.subject_type,
        subject_id=payload.subject_id,
        scope_path=payload.scope_path,
        verbs=tuple(payload.verbs),
        effect=payload.effect,
        inheritance_block=payload.inheritance_block,
        resource_kind=payload.resource_kind,
        conditions=payload.conditions,
        hidden_when_unauthorized=payload.hidden_when_unauthorized,
        workspace_id=payload.workspace_id,
        instance=str(request.url.path),
    )
    if is_pg_bootstrap_enabled():
        try:
            engine = get_or_create_shared_db_engine(request)
            grants = await create_iam_grants_on_postgres18(engine, grants)
        except OrciaDomainError:
            raise
        except Exception as exc:
            logger.warning("iam_grants_create_pg_fallback", error_type=type(exc).__name__)
    return [serialize_grant(g) for g in grants]


@router.delete("/settings/iam/grants/{grant_id}", response_model=GrantDeleteResponse)
async def revoke_rbac_grant_endpoint(
    grant_id: Annotated[str, Path(min_length=1, max_length=128)],
    request: Request,
    rbac: Annotated[HierarchicalRbacService, Depends(get_hierarchical_rbac_service)],
    actor_persona: Annotated[str, Query(min_length=1, max_length=64)] = "karim",
) -> GrantDeleteResponse:
    """Revoke an IAM exception / isolation rule (`Story 17.3`)."""
    enforce_not_observer_mode(request)
    actor = resolve_request_user(request, persona_key=actor_persona)
    deleted_id: str | None = None
    if is_pg_bootstrap_enabled():
        try:
            engine = get_or_create_shared_db_engine(request)
            deleted_id = await delete_iam_grant_on_postgres18(
                engine, grant_id, instance=str(request.url.path)
            )
            if any(g.id == grant_id for g in rbac.list_grants()):
                rbac.revoke_grant(actor, grant_id, instance=str(request.url.path))
        except OrciaDomainError:
            raise
        except Exception as exc:
            logger.warning("iam_grants_delete_pg_fallback", error_type=type(exc).__name__)
            deleted_id = None
    if deleted_id is None:
        revoked = rbac.revoke_grant(actor, grant_id, instance=str(request.url.path))
        deleted_id = revoked.id
    trace_id = str(getattr(request.state, "trace_id", None) or get_current_trace_id())
    return GrantDeleteResponse(deleted_id=deleted_id, trace_id=trace_id)


@router.get("/settings/entries", response_model=list[PlatformSettingResponse])
def list_platform_settings(
    settings_svc: Annotated[PlatformSettingsService, Depends(get_platform_settings_service)],
) -> list[PlatformSettingResponse]:
    """List versioned platform settings with `ETag` and `SecretStatus` (`Story 8.3`)."""
    return [to_setting_response(s) for s in settings_svc.list_settings()]


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
    return to_setting_response(updated)


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
    return [to_llm_mapping_response(m) for m in router_svc.list_mappings()]


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
    return to_routing_outcome_response(outcome)


@router.delete("/settings/ai-models/mappings/{mapping_id}")
def delete_or_drain_llm_mapping(
    mapping_id: Annotated[str, Path(min_length=1, max_length=128)],
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
    connector_id: Annotated[str, Path(min_length=1, max_length=128)],
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
    document_id: Annotated[str, Path(min_length=1, max_length=128)],
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
