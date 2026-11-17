"""Autonomy Contracts Router (`/api/v1/workspaces/{workspace_id}/workflows/{workflow_id}/*`)."""

from __future__ import annotations

import hashlib
import os
from typing import Annotated, Any

import sqlalchemy as sa
from fastapi import APIRouter, Depends, Path, Request

from orcia_api.dependencies import (
    get_audit_ledger_service,
    get_auth_service,
    get_autonomous_supervision_service,
    get_autonomy_contract_service,
    get_hierarchical_rbac_service,
    get_iam_accounts_service,
)
from orcia_api.routers._finops_scope_guards import (
    resolve_workspace_uuid_or_setup_key,
    sync_evaluator_topology_from_pg,
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
from orcia_connectors.protocol import (
    ConnectorHealthStatus,
    OrciaConnectorProtocol,
    SignedApprovalToken,
    WritePreviewCard,
    compute_payload_sha256,
    verify_signed_approval_token,
)
from orcia_core.audit_finops import SqlAuditLedgerService
from orcia_core.bootstrap import (
    persist_autonomous_run_outcome_on_postgres18,
    sync_and_list_iam_accounts_from_postgres18,
)
from orcia_core.observability.logging import get_current_trace_id, get_logger
from orcia_core.orchestration.autonomous_supervision import AutonomousSupervisionService
from orcia_core.permissions import (
    AuthAndOrganizationService,
    AutonomyContract,
    AutonomyContractService,
    HierarchicalRbacService,
    IamAccountRecord,
    IamAccountsGovernanceService,
    SignAutonomyContractCommand,
    is_service_principal_scoped_to_workspace,
)
from orcia_core.permissions.errors import (
    AutonomyContractNotFoundError,
    ObserverModeReadOnlyError,
)
from orcia_core.permissions.models import UserIdentity

logger = get_logger("orcia.api.autonomy_contracts")

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


class _InternalCatalogActionAdapter(OrciaConnectorProtocol):
    connector_type = "catalog"

    async def healthcheck(self) -> ConnectorHealthStatus:
        return ConnectorHealthStatus(connector_type=self.connector_type, ok=True, latency_ms=1)

    async def read(self, resource_uri: str, query: dict[str, Any] | None = None) -> dict[str, Any]:
        del query
        return {"resource_uri": resource_uri, "status": "ok"}

    async def preview_write(self, action: str, payload: dict[str, Any]) -> WritePreviewCard:
        return WritePreviewCard(
            connector_type=self.connector_type,
            target_resource_uri=f"catalog://{action}",
            action_summary=action,
            diff_or_payload_preview=payload,
            payload_sha256=compute_payload_sha256(action, payload),
        )

    async def execute_write(
        self, approval_token: SignedApprovalToken, action: str, payload: dict[str, Any]
    ) -> dict[str, Any]:
        verify_signed_approval_token(approval_token, action=action, payload=payload)
        return {"committed": True, "action": action, "preview_id": approval_token.preview_id}


def _trace(request: Request) -> str:
    return str(getattr(request.state, "trace_id", None) or get_current_trace_id())


def _serialize_contract(c: AutonomyContract) -> AutonomyContractResponse:
    return AutonomyContractResponse(
        id=c.id,
        workspace_id=c.workspace_id,
        workflow_id=c.workflow_id,
        workflow_version=c.workflow_version,
        workflow_sha256=c.workflow_sha256,
        criticality=c.criticality,
        service_principal_id=c.service_principal_id,
        allowed_read_sources=list(c.allowed_read_sources),
        allowed_write_actions=list(c.allowed_write_actions),
        max_cost_per_run_usd=c.max_cost_per_run_usd,
        tie_break_policy=c.tie_break_policy,
        post_hoc_sampling_rate=c.post_hoc_sampling_rate,
        status=c.status,
        signed_by_user_id=c.signed_by_user_id,
        signed_by_role=c.signed_by_role,
        signature_sha256=c.signature_sha256,
        signed_at_iso=c.signed_at_iso,
        revoked_at_iso=c.revoked_at_iso,
        revoked_by_user_id=c.revoked_by_user_id,
    )


async def _resolve_workspace_scope_ids(
    request: Request,
    auth_svc: AuthAndOrganizationService,
    workspace_id: str,
    raw_workspace_id: str | None = None,
) -> list[str]:
    scope_ids: list[str] = [workspace_id]
    if raw_workspace_id and raw_workspace_id != workspace_id:
        scope_ids.append(raw_workspace_id)
    ws = auth_svc.evaluator.get_workspace(workspace_id)
    if ws is not None and ws.owner_org_unit_id:
        scope_ids.append(ws.owner_org_unit_id)
        scope_ids.extend(auth_svc.evaluator.get_ancestor_org_unit_ids(ws.owner_org_unit_id))
    engine = getattr(request.app.state, "db_engine", None)
    if engine is not None and os.environ.get("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC") != "1":
        try:
            async with engine.connect() as conn:
                row = (
                    await conn.execute(
                        sa.text(
                            "SELECT owner_org_unit_id::text FROM workspaces "
                            "WHERE id = CAST(:ws_id AS uuid)"
                        ),
                        {"ws_id": workspace_id},
                    )
                ).fetchone()
                if row and row[0]:
                    scope_ids.append(str(row[0]))
        except Exception as exc:
            logger.warning("resolve_workspace_scope_ids_pg_fallback", error=str(exc))
    return list(dict.fromkeys(scope_ids))


async def _load_iam_accounts(
    request: Request, iam_svc: IamAccountsGovernanceService
) -> list[IamAccountRecord]:
    by_id: dict[str, IamAccountRecord] = {acc.id: acc for acc in iam_svc.list_accounts()}
    engine = getattr(request.app.state, "db_engine", None)
    if engine is not None and os.environ.get("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC") != "1":
        try:
            pg_accounts = await sync_and_list_iam_accounts_from_postgres18(engine)
            for acc in pg_accounts:
                by_id[acc.id] = acc
        except Exception as exc:
            logger.warning("load_iam_accounts_pg_fallback", error=str(exc))
    return list(by_id.values())


async def _enforce_not_observer(
    request: Request,
    user: UserIdentity,
    auth_svc: AuthAndOrganizationService,
    workspace_id: str,
) -> None:
    instance = str(request.url.path)
    if (
        request.headers.get("X-Orcia-Access-Mode", "").strip().upper() == "READ_ONLY_OBSERVER"
        or user.platform_role == "OBSERVER"
    ):
        raise ObserverModeReadOnlyError(instance=instance)
    await sync_evaluator_topology_from_pg(request, auth_svc)
    ws = auth_svc.evaluator.get_workspace(workspace_id)
    is_admin = user.platform_role == "PLATFORM_ADMIN" or "PLATFORM_ADMIN" in user.roles
    if ws is not None and is_admin and ws.visibility_mode != "CONFIDENTIAL_RESTRICTED":
        return
    ws_access = auth_svc.evaluator.resolve_workspace_access(user, workspace_id)
    if ws_access is not None and ws_access.access_mode == "READ_ONLY_OBSERVER":
        raise ObserverModeReadOnlyError(instance=instance)


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
    del user
    ws_uuid = resolve_workspace_uuid_or_setup_key(workspace_id, "workspace_id")
    await sync_evaluator_topology_from_pg(request, auth_svc)
    active = await svc.get_active_contract(workspace_id=ws_uuid, workflow_id=workflow_id)
    history = await svc.list_contracts(workspace_id=ws_uuid, workflow_id=workflow_id)
    scope_ids = await _resolve_workspace_scope_ids(request, auth_svc, ws_uuid, workspace_id)
    accounts = await _load_iam_accounts(request, iam_svc)
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
        active_contract=_serialize_contract(active) if active is not None else None,
        history=[_serialize_contract(c) for c in history],
        eligible_service_principals=eligible,
        trace_id=_trace(request),
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
    await _enforce_not_observer(request, user, auth_svc, ws_uuid)
    scope_ids = await _resolve_workspace_scope_ids(request, auth_svc, ws_uuid, workspace_id)
    accounts = await _load_iam_accounts(request, iam_svc)
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
            scope_path=body.scope_path,
        ),
        signer=user,
        service_principal=sp,
        allowed_scope_ids=scope_ids,
        trace_id=_trace(request),
        instance=str(request.url.path),
    )
    return _serialize_contract(contract)


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
    auth_svc: Annotated[AuthAndOrganizationService, Depends(get_auth_service)],
    body: RevokeAutonomyContractRequest | None = None,
) -> AutonomyContractResponse:
    ws_uuid = resolve_workspace_uuid_or_setup_key(workspace_id, "workspace_id")
    await _enforce_not_observer(request, user, auth_svc, ws_uuid)
    revoked = await svc.revoke_contract(
        workspace_id=ws_uuid,
        workflow_id=workflow_id,
        actor=user,
        scope_path=body.scope_path if body is not None else "GLOBAL",
        trace_id=_trace(request),
        instance=str(request.url.path),
    )
    return _serialize_contract(revoked)


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
    auth_svc: Annotated[AuthAndOrganizationService, Depends(get_auth_service)],
    audit_sink: Annotated[SqlAuditLedgerService, Depends(get_audit_ledger_service)],
    supervision_svc: Annotated[
        AutonomousSupervisionService, Depends(get_autonomous_supervision_service)
    ],
) -> AutonomousRunExecutionResponse:
    ws_uuid = resolve_workspace_uuid_or_setup_key(workspace_id, "workspace_id")
    await _enforce_not_observer(request, user, auth_svc, ws_uuid)
    contract = await svc.get_active_contract(workspace_id=ws_uuid, workflow_id=workflow_id)
    if contract is None:
        raise AutonomyContractNotFoundError(instance=str(request.url.path))

    catalog_adapter = _InternalCatalogActionAdapter()
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
            workspace_id=workspace_id, workflow_id=workflow_id
        ),
        kill_switch_check_fn=supervision_svc.is_run_stopped,
        connector_invoker=getattr(request.app.state, "connector_invoker", None),
        connectors_by_scheme={"catalog": catalog_adapter, "orcia": catalog_adapter},
        trace_id=_trace(request),
        scope_path=body.scope_path,
    )
    engine = getattr(request.app.state, "db_engine", None)
    if engine is not None and os.environ.get("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC") != "1":
        await persist_autonomous_run_outcome_on_postgres18(
            engine,
            run_id=outcome.run_id,
            workspace_id=workspace_id,
            workflow_id=workflow_id,
            workflow_version=contract.workflow_version,
            status=outcome.status,
            event=events[0] if events else None,
            audit_sink=audit_sink,
        )
    await supervision_svc.register_autonomous_run(
        run_id=outcome.run_id,
        workspace_id=workspace_id,
        workflow_id=workflow_id,
        contract_id=contract.id,
        status=outcome.status,
        trace_id=_trace(request),
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
        trace_id=_trace(request),
    )
