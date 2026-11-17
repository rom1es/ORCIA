"""Autonomy Contracts Router (`/api/v1/workspaces/{workspace_id}/workflows/{workflow_id}/*`)."""

from __future__ import annotations

import hashlib
import os
from decimal import Decimal
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Path, Request

from orcia_api.dependencies import (
    get_audit_ledger_service,
    get_auth_service,
    get_autonomous_supervision_service,
    get_autonomy_contract_service,
    get_hierarchical_rbac_service,
    get_iam_accounts_service,
)
from orcia_api.routers._autonomy_contracts_helpers import (
    InternalCatalogActionAdapter,
    load_iam_accounts_merged,
    resolve_workspace_scope_ids,
    serialize_autonomy_contract,
    trace_id_from_request,
)
from orcia_api.routers._finops_auth_guards import (
    enforce_workspace_governed_mutation,
    resolve_finops_read_scope,
)
from orcia_api.routers._finops_scope_guards import (
    resolve_workspace_uuid_or_setup_key,
)
from orcia_api.routers.auth import resolve_request_user
from orcia_api.schemas.autonomy_contracts import (
    AutonomousRunExecutionResponse,
    AutonomyContractResponse,
    AutonomyContractStateResponse,
    EligibleServicePrincipalItem,
    RevokeAutonomyContractRequest,
    SignAutonomyContractRequest,
    StartAutonomousRunRequest,
)
from orcia_api.schemas.problem_details import ProblemDetails
from orcia_connectors.autonomous_runner import (
    AutonomousActionRequest,
    AutonomousGateInput,
    execute_autonomous_contract_run,
)
from orcia_core.audit_finops import SqlAuditLedgerService
from orcia_core.bootstrap import persist_autonomous_run_outcome_on_postgres18
from orcia_core.orchestration.autonomous_supervision import AutonomousSupervisionService
from orcia_core.permissions import (
    AuthAndOrganizationService,
    AutonomyContractService,
    HierarchicalRbacService,
    IamAccountsGovernanceService,
    SignAutonomyContractCommand,
    is_service_principal_scoped_to_workspace,
)
from orcia_core.permissions.errors import AutonomyContractNotFoundError
from orcia_core.permissions.models import UserIdentity

PROBLEM_RESPONSES: dict[int | str, dict[str, Any]] = {
    401: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
    403: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
    404: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
    422: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
}

router = APIRouter(
    prefix="/api/v1/workspaces/{workspace_id}/workflows",
    tags=["autonomy-contracts"],
    responses=PROBLEM_RESPONSES,
)

_CONTRACT_GOVERNOR_ROLES = ("PLATFORM_ADMIN", "BU_DIRECTOR", "BU_LEAD", "TEAM_LEAD")


@router.get("/{workflow_id:path}/autonomy-contract", response_model=AutonomyContractStateResponse)
async def get_autonomy_contract_state(
    request: Request,
    workspace_id: Annotated[str, Path(min_length=1)],
    workflow_id: Annotated[str, Path(min_length=1)],
    user: Annotated[UserIdentity, Depends(resolve_request_user)],
    svc: Annotated[AutonomyContractService, Depends(get_autonomy_contract_service)],
    auth_svc: Annotated[AuthAndOrganizationService, Depends(get_auth_service)],
    iam_svc: Annotated[IamAccountsGovernanceService, Depends(get_iam_accounts_service)],
    rbac_svc: Annotated[HierarchicalRbacService, Depends(get_hierarchical_rbac_service)],
) -> AutonomyContractStateResponse:
    ws_uuid = resolve_workspace_uuid_or_setup_key(workspace_id, "workspace_id")
    await resolve_finops_read_scope(request, user, "WORKSPACE", ws_uuid)
    active = await svc.get_active_contract(workspace_id=ws_uuid, workflow_id=workflow_id)
    history = await svc.list_contracts(workspace_id=ws_uuid, workflow_id=workflow_id)
    scope_ids = await resolve_workspace_scope_ids(
        request, auth_svc, ws_uuid, raw_workspace_id=workspace_id
    )
    accounts = await load_iam_accounts_merged(request, iam_svc)
    eligible = [
        EligibleServicePrincipalItem(
            id=acc.id,
            principal_id=acc.principal_id,
            display_name=acc.display_name,
            roles=list(acc.roles),
            team_ids=list(acc.team_ids),
            status=acc.status,
        )
        for acc in accounts
        if is_service_principal_scoped_to_workspace(
            acc, workspace_id=ws_uuid, allowed_scope_ids=scope_ids, rbac_service=rbac_svc
        )
    ]
    return AutonomyContractStateResponse(
        workspace_id=ws_uuid,
        workflow_id=workflow_id,
        active_contract=serialize_autonomy_contract(active) if active is not None else None,
        history=[serialize_autonomy_contract(c) for c in history],
        eligible_service_principals=eligible,
        trace_id=trace_id_from_request(request),
    )


@router.post(
    "/{workflow_id:path}/autonomy-contract",
    response_model=AutonomyContractResponse,
    status_code=201,
)
async def sign_autonomy_contract(
    request: Request,
    workspace_id: Annotated[str, Path(min_length=1)],
    workflow_id: Annotated[str, Path(min_length=1)],
    body: SignAutonomyContractRequest,
    user: Annotated[UserIdentity, Depends(resolve_request_user)],
    svc: Annotated[AutonomyContractService, Depends(get_autonomy_contract_service)],
    auth_svc: Annotated[AuthAndOrganizationService, Depends(get_auth_service)],
    iam_svc: Annotated[IamAccountsGovernanceService, Depends(get_iam_accounts_service)],
) -> AutonomyContractResponse:
    ws_uuid = resolve_workspace_uuid_or_setup_key(workspace_id, "workspace_id")
    derived_scope = await enforce_workspace_governed_mutation(
        request, user, ws_uuid, allowed_roles=_CONTRACT_GOVERNOR_ROLES
    )
    scope_ids = await resolve_workspace_scope_ids(
        request, auth_svc, ws_uuid, raw_workspace_id=workspace_id
    )
    accounts = await load_iam_accounts_merged(request, iam_svc)
    sp = next((a for a in accounts if a.id == body.service_principal_id), None)
    wf_sha = (
        body.workflow_sha256.strip()
        or hashlib.sha256(f"{workflow_id}:{body.workflow_version}".encode()).hexdigest()
    )
    contract = await svc.sign_contract(
        SignAutonomyContractCommand(
            workspace_id=ws_uuid,
            workflow_id=workflow_id,
            workflow_version=body.workflow_version,
            workflow_sha256=wf_sha,
            criticality=body.criticality,
            service_principal_id=body.service_principal_id,
            allowed_read_sources=tuple(body.allowed_read_sources),
            allowed_write_actions=tuple(body.allowed_write_actions),
            max_cost_per_run_usd=body.max_cost_per_run_usd,
            tie_break_policy=body.tie_break_policy,
            post_hoc_sampling_rate=body.post_hoc_sampling_rate,
            scope_path=derived_scope,
        ),
        signer=user,
        service_principal=sp,
        allowed_scope_ids=scope_ids,
        trace_id=trace_id_from_request(request),
        instance=str(request.url.path),
    )
    return serialize_autonomy_contract(contract)


@router.post(
    "/{workflow_id:path}/autonomy-contract/revoke",
    response_model=AutonomyContractResponse,
)
async def revoke_autonomy_contract(
    request: Request,
    workspace_id: Annotated[str, Path(min_length=1)],
    workflow_id: Annotated[str, Path(min_length=1)],
    user: Annotated[UserIdentity, Depends(resolve_request_user)],
    svc: Annotated[AutonomyContractService, Depends(get_autonomy_contract_service)],
    body: RevokeAutonomyContractRequest | None = None,
) -> AutonomyContractResponse:
    del body
    ws_uuid = resolve_workspace_uuid_or_setup_key(workspace_id, "workspace_id")
    derived_scope = await enforce_workspace_governed_mutation(
        request, user, ws_uuid, allowed_roles=_CONTRACT_GOVERNOR_ROLES
    )
    revoked = await svc.revoke_contract(
        workspace_id=ws_uuid,
        workflow_id=workflow_id,
        actor=user,
        scope_path=derived_scope,
        trace_id=trace_id_from_request(request),
        instance=str(request.url.path),
    )
    return serialize_autonomy_contract(revoked)


@router.post(
    "/{workflow_id:path}/runs/autonomous",
    response_model=AutonomousRunExecutionResponse,
    status_code=201,
)
async def start_autonomous_run(
    request: Request,
    workspace_id: Annotated[str, Path(min_length=1)],
    workflow_id: Annotated[str, Path(min_length=1)],
    body: StartAutonomousRunRequest,
    user: Annotated[UserIdentity, Depends(resolve_request_user)],
    svc: Annotated[AutonomyContractService, Depends(get_autonomy_contract_service)],
    audit_sink: Annotated[SqlAuditLedgerService, Depends(get_audit_ledger_service)],
    supervision_svc: Annotated[
        AutonomousSupervisionService, Depends(get_autonomous_supervision_service)
    ],
) -> AutonomousRunExecutionResponse:
    ws_uuid = resolve_workspace_uuid_or_setup_key(workspace_id, "workspace_id")
    derived_scope = await enforce_workspace_governed_mutation(request, user, ws_uuid)
    contract = await svc.get_active_contract(workspace_id=ws_uuid, workflow_id=workflow_id)
    if contract is None:
        raise AutonomyContractNotFoundError(instance=str(request.url.path))

    catalog_adapter = InternalCatalogActionAdapter()
    trace_id = trace_id_from_request(request)
    outcome, events = await execute_autonomous_contract_run(
        contract=contract,
        criticality=body.criticality,
        actions=[
            AutonomousActionRequest(
                action_key=a.action_key,
                scheme=a.scheme,
                payload=a.payload,
                secret_ref_uri=a.secret_ref_uri,
            )
            for a in body.actions
        ],
        gates=AutonomousGateInput(
            deterministic_passed=body.deterministic_passed,
            agentic_score=body.agentic_score,
            fact_verification_score=body.fact_verification_score,
            ontology_conflicts=body.ontology_conflicts,
            stale_warnings=body.stale_warnings,
            estimated_cost_usd=body.estimated_cost_usd,
            help_article_markdown=body.help_article_markdown,
            help_article_lang=body.help_article_lang,
        ),
        contract_refresh_fn=lambda: svc.get_active_contract(
            workspace_id=ws_uuid, workflow_id=workflow_id
        ),
        kill_switch_check_fn=supervision_svc.is_run_stopped,
        connector_invoker=getattr(request.app.state, "connector_invoker", None),
        connectors_by_scheme={"catalog": catalog_adapter, "orcia": catalog_adapter},
        secret_provider=getattr(request.app.state, "secret_provider", None),
        trace_id=trace_id,
        scope_path=derived_scope,
    )
    engine = getattr(request.app.state, "db_engine", None)
    if engine is not None and os.environ.get("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC") != "1":
        await persist_autonomous_run_outcome_on_postgres18(
            engine,
            run_id=outcome.run_id,
            workspace_id=ws_uuid,
            workflow_id=workflow_id,
            workflow_version=contract.workflow_version,
            status=outcome.status,
            event=events[0] if events else None,
            audit_sink=audit_sink,
        )
    await supervision_svc.register_autonomous_run(
        run_id=outcome.run_id,
        workspace_id=ws_uuid,
        workflow_id=workflow_id,
        contract_id=contract.id,
        status=outcome.status,
        cost_usd=Decimal(str(body.estimated_cost_usd)),
        force_post_hoc_sample=body.force_post_hoc_sample,
        trace_id=trace_id,
    )
    return AutonomousRunExecutionResponse(
        run_id=outcome.run_id,
        workspace_id=outcome.workspace_id,
        workflow_id=outcome.workflow_id,
        contract_id=outcome.contract_id,
        status=outcome.status,
        escalation_reason=outcome.escalation_reason,
        issued_token_preview_ids=[t.preview_id for t in outcome.issued_tokens],
        executed_actions=outcome.executed_actions,
        trace_id=trace_id,
    )
