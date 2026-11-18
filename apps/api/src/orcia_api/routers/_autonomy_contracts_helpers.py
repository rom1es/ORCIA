"""Helper adapters and serialization for Autonomy Contracts router (`MAJOR-05`)."""

from __future__ import annotations

from typing import Any

import sqlalchemy as sa
from fastapi import Request

from orcia_api.routers._finops_scope_guards import sync_evaluator_topology_from_pg
from orcia_api.schemas.autonomy_contracts import AutonomyContractResponse
from orcia_connectors.protocol import (
    ConnectorHealthStatus,
    OrciaConnectorProtocol,
    SignedApprovalToken,
    WritePreviewCard,
    compute_payload_sha256,
    verify_signed_approval_token,
)
from orcia_core.observability.logging import get_current_trace_id, get_logger
from orcia_core.permissions import (
    AuthAndOrganizationService,
    AutonomyContract,
    IamAccountRecord,
    IamAccountsGovernanceService,
)

logger = get_logger("orcia.api.autonomy_contracts")


class InternalCatalogActionAdapter(OrciaConnectorProtocol):
    """In-process `catalog` connector adapter validating `SignedApprovalToken` signatures."""

    connector_type = "catalog"

    async def healthcheck(self) -> ConnectorHealthStatus:
        """Report local adapter availability."""
        return ConnectorHealthStatus(connector_type=self.connector_type, ok=True, latency_ms=1)

    async def read(self, resource_uri: str, query: dict[str, Any] | None = None) -> dict[str, Any]:
        """Read-only catalog probe."""
        del query
        return {"resource_uri": resource_uri, "status": "ok"}

    async def preview_write(self, action: str, payload: dict[str, Any]) -> WritePreviewCard:
        """Return canonical SHA-256 preview card for a catalog write action."""
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
        """Verify Permission Broker signature before acknowledging the write."""
        verify_signed_approval_token(approval_token, action=action, payload=payload)
        return {"committed": True, "action": action, "preview_id": approval_token.preview_id}


def trace_id_from_request(request: Request) -> str:
    """Resolve current W3C `trace_id` from request state or OTel context."""
    return str(getattr(request.state, "trace_id", None) or get_current_trace_id())


def serialize_autonomy_contract(c: AutonomyContract) -> AutonomyContractResponse:
    """Map domain `AutonomyContract` onto OpenAPI `AutonomyContractResponse`."""
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


async def resolve_workspace_scope_ids(
    request: Request,
    auth_svc: AuthAndOrganizationService,
    ws_uuid: str,
    raw_workspace_id: str | None = None,
) -> list[str]:
    """Resolve `ws_uuid`, optional setup key, owning org unit, and ancestor org unit UUIDs."""
    await sync_evaluator_topology_from_pg(request, auth_svc)
    scope_ids: list[str] = [ws_uuid]
    if raw_workspace_id and raw_workspace_id.strip() and raw_workspace_id.strip() != ws_uuid:
        scope_ids.append(raw_workspace_id.strip())
    ws = auth_svc.evaluator.get_workspace(ws_uuid)
    if ws is not None and ws.owner_org_unit_id:
        scope_ids.append(ws.owner_org_unit_id)
        scope_ids.extend(auth_svc.evaluator.get_ancestor_org_unit_ids(ws.owner_org_unit_id))
    engine = getattr(request.app.state, "db_engine", None)
    if engine is not None:
        try:
            async with engine.connect() as conn:
                row = (
                    await conn.execute(
                        sa.text(
                            "SELECT owner_org_unit_id::text FROM workspaces "
                            "WHERE id = CAST(:ws_id AS uuid)"
                        ),
                        {"ws_id": ws_uuid},
                    )
                ).fetchone()
                if row and row[0]:
                    owner_id = str(row[0])
                    scope_ids.append(owner_id)
                    scope_ids.extend(auth_svc.evaluator.get_ancestor_org_unit_ids(owner_id))
        except Exception as exc:
            logger.warning("resolve_workspace_scope_ids_pg_fallback", error=str(exc))
    return list(dict.fromkeys(scope_ids))


async def load_iam_accounts_merged(
    request: Request, iam_svc: IamAccountsGovernanceService
) -> list[IamAccountRecord]:
    """Merge in-memory and PostgreSQL 18 `iam_accounts` records."""
    from orcia_core.bootstrap import sync_and_list_iam_accounts_from_postgres18

    by_id: dict[str, IamAccountRecord] = {acc.id: acc for acc in iam_svc.list_accounts()}
    engine = getattr(request.app.state, "db_engine", None)
    if engine is not None:
        try:
            pg_accounts = await sync_and_list_iam_accounts_from_postgres18(engine)
            for acc in pg_accounts:
                by_id[acc.id] = acc
        except Exception as exc:
            logger.warning("load_iam_accounts_pg_fallback", error=str(exc))
    return list(by_id.values())
