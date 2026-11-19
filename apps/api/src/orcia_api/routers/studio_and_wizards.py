"""FastAPI router for Studio Dry-Run & Durable Onboarding Wizards (`Stories 8.5..8.6`, `22.5`).

Extracted from `settings_and_studio.py` (`Story 17.3` `< 350`-line modularity hygiene).
"""

from __future__ import annotations

from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Path, Query, Request

from orcia_api.dependencies import (
    get_durable_wizard_service,
    get_studio_and_pack_service,
)
from orcia_api.routers._auth_pg_helpers import rehydrate_bearer_subject_from_pg_if_missing
from orcia_api.routers._settings_helpers import enforce_not_observer_mode
from orcia_api.routers.auth import resolve_request_user
from orcia_api.schemas.problem_details import ProblemDetails
from orcia_api.schemas.settings_and_studio import (
    DemoWorkspaceProvisionResponse,
    StudioDryRunRequest,
    StudioDryRunResponse,
    WizardAdvanceStepRequest,
    WizardSessionRequest,
    WizardSessionResponse,
    WizardSessionsListResponse,
    WizardStepBackRequest,
)
from orcia_core.bootstrap import DurableOnboardingWizardService, WizardSessionRecord
from orcia_core.observability.logging import get_current_trace_id
from orcia_core.orchestration import WorkflowStudioAndPackService
from orcia_core.permissions import SecretInputSpec, UserIdentity

STUDIO_WIZARDS_PROBLEM_RESPONSES: dict[int | str, dict[str, Any]] = {
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
    tags=["studio-and-wizards"],
    responses=STUDIO_WIZARDS_PROBLEM_RESPONSES,
)


async def _resolve_wizard_actor(
    request: Request,
    *,
    persona_key: str | None = None,
) -> UserIdentity:
    if request.headers.get("Authorization"):
        await rehydrate_bearer_subject_from_pg_if_missing(request)
    return resolve_request_user(request, persona_key=persona_key)


def _serialize_wizard_session(rec: WizardSessionRecord) -> WizardSessionResponse:
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


@router.post("/studio/revisions/{revision_id}/dry-run", response_model=StudioDryRunResponse)
def studio_what_if_dry_run_endpoint(
    revision_id: Annotated[str, Path(min_length=1, max_length=128)],
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


@router.get("/wizards", response_model=WizardSessionsListResponse)
async def list_wizard_sessions_endpoint(
    request: Request,
    wizard_svc: Annotated[DurableOnboardingWizardService, Depends(get_durable_wizard_service)],
    persona_key: Annotated[str | None, Query(min_length=1, max_length=64)] = None,
) -> WizardSessionsListResponse:
    """List durable onboarding wizard sessions for the authenticated user (`Story 22.5`)."""
    trace_id: str = getattr(request.state, "trace_id", None) or get_current_trace_id()
    actor = await _resolve_wizard_actor(request, persona_key=persona_key)
    sessions = await wizard_svc.list_sessions_for_user_async(actor)
    return WizardSessionsListResponse(
        sessions=[_serialize_wizard_session(rec) for rec in sessions],
        trace_id=trace_id,
    )


@router.get("/wizards/sessions/{session_id}", response_model=WizardSessionResponse)
async def get_wizard_session_endpoint(
    session_id: Annotated[str, Path(min_length=1, max_length=128)],
    request: Request,
    wizard_svc: Annotated[DurableOnboardingWizardService, Depends(get_durable_wizard_service)],
    persona_key: Annotated[str | None, Query(min_length=1, max_length=64)] = None,
) -> WizardSessionResponse:
    """Fetch a durable onboarding wizard session by ID (`Story 22.5`)."""
    await _resolve_wizard_actor(request, persona_key=persona_key)
    rec = await wizard_svc.get_session_async(session_id, instance=str(request.url.path))
    return _serialize_wizard_session(rec)


@router.post("/wizards/sessions", response_model=WizardSessionResponse)
async def start_or_resume_wizard_endpoint(
    payload: WizardSessionRequest,
    request: Request,
    wizard_svc: Annotated[DurableOnboardingWizardService, Depends(get_durable_wizard_service)],
) -> WizardSessionResponse:
    """Start or resume a 5-step durable DBOS onboarding wizard (`Story 8.6`, `22.5`)."""
    enforce_not_observer_mode(request)
    actor = await _resolve_wizard_actor(request, persona_key=payload.actor_persona)
    rec = await wizard_svc.start_or_resume_wizard_async(
        actor,
        wizard_type=payload.wizard_type,
        scope_id=payload.scope_id,
        instance=str(request.url.path),
    )
    return _serialize_wizard_session(rec)


@router.post("/wizards/sessions/{session_id}/steps", response_model=WizardSessionResponse)
async def save_wizard_step_endpoint(
    session_id: Annotated[str, Path(min_length=1, max_length=128)],
    payload: WizardAdvanceStepRequest,
    request: Request,
    wizard_svc: Annotated[DurableOnboardingWizardService, Depends(get_durable_wizard_service)],
) -> WizardSessionResponse:
    """Save step state (`SecretRef` only) and advance or step back (`Story 8.6`, `22.5`)."""
    enforce_not_observer_mode(request)
    actor = await _resolve_wizard_actor(request, persona_key=payload.actor_persona)
    sec_in = (
        SecretInputSpec(
            action=payload.secret_input.action,
            plaintext_value=payload.secret_input.plaintext_value,
        )
        if payload.secret_input is not None
        else None
    )
    rec = await wizard_svc.save_step_and_advance_async(
        actor,
        session_id,
        step_index=payload.step_index,
        step_payload=payload.step_payload,
        secret_input=sec_in,
        step_back=payload.step_back,
        instance=str(request.url.path),
    )
    return _serialize_wizard_session(rec)


@router.post("/wizards/sessions/{session_id}/step-back", response_model=WizardSessionResponse)
async def step_back_wizard_endpoint(
    session_id: Annotated[str, Path(min_length=1, max_length=128)],
    payload: WizardStepBackRequest,
    request: Request,
    wizard_svc: Annotated[DurableOnboardingWizardService, Depends(get_durable_wizard_service)],
) -> WizardSessionResponse:
    """Step back to the previous wizard step while preserving all entered inputs (`REM-15`)."""
    enforce_not_observer_mode(request)
    actor = await _resolve_wizard_actor(request, persona_key=payload.actor_persona)
    rec = await wizard_svc.save_step_and_advance_async(
        actor,
        session_id,
        step_index=payload.step_index,
        step_payload=payload.step_payload,
        step_back=True,
        instance=str(request.url.path),
    )
    return _serialize_wizard_session(rec)


@router.post("/wizards/demo-workspace", response_model=DemoWorkspaceProvisionResponse)
async def provision_demo_workspace_endpoint(
    request: Request,
    wizard_svc: Annotated[DurableOnboardingWizardService, Depends(get_durable_wizard_service)],
    actor_persona: Annotated[Literal["karim", "claire", "marc", "nadia"], Query()] = "marc",
) -> DemoWorkspaceProvisionResponse:
    """Provision the Zero Empty-State Demo Workspace (`0` plaintext secrets, `Story 8.6`)."""
    enforce_not_observer_mode(request)
    actor = await _resolve_wizard_actor(request, persona_key=actor_persona)
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
