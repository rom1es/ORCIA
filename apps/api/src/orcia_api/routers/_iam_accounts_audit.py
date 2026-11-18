"""Story 20.1 — IAM Accounts Deletion, Auth Resync & Audit Helpers (`_iam_accounts_audit`)."""

from __future__ import annotations

from fastapi import Request

from orcia_api.dependencies import get_auth_service, get_or_create_shared_db_engine
from orcia_api.routers._auth_pg_helpers import sync_auth_service_user_by_email_from_pg
from orcia_api.routers._iam_accounts_passwords import (
    cleanup_or_disable_linked_user_on_postgres18,
    enforce_iam_anti_escalation,
    sync_in_memory_team_memberships,
)
from orcia_api.routers._org_units_audit import record_governance_audit_event
from orcia_api.schemas.iam_accounts import IamAccountDeleteResponse
from orcia_core.bootstrap import (
    delete_iam_account_on_postgres18,
    sync_and_list_iam_accounts_from_postgres18,
)
from orcia_core.observability.logging import get_logger
from orcia_core.permissions import (
    AuthAndOrganizationService,
    IamAccountRecord,
    IamAccountsGovernanceService,
    UserIdentity,
)
from orcia_core.permissions.errors import OrciaDomainError

logger = get_logger("orcia.api.iam_accounts.audit")


def first_org_unit_id(rec: IamAccountRecord) -> str | None:
    """Return first linked org unit ID on an `IamAccountRecord` for audit attribution."""
    for seq in (rec.team_ids, rec.led_team_ids, rec.led_bu_ids, rec.ontology_led_bu_ids):
        if seq:
            return seq[0]
    return None


async def resync_iam_account_and_audit(
    request: Request,
    auth_svc: AuthAndOrganizationService,
    caller: UserIdentity,
    *,
    account: IamAccountRecord,
    event_type: str,
    summary: str,
    sync_teams: bool = False,
) -> None:
    """Resync evaluator team memberships, auth user cache, and record audit entry."""
    if sync_teams:
        sync_in_memory_team_memberships(auth_svc.evaluator, account.principal_id, account.team_ids)
    if account.email:
        await sync_auth_service_user_by_email_from_pg(request, auth_svc, account.email)
    if account.principal_id and account.principal_id != account.email:
        await sync_auth_service_user_by_email_from_pg(request, auth_svc, account.principal_id)
    await record_governance_audit_event(
        request,
        actor=caller,
        event_type=event_type,
        summary=summary,
        org_unit_id=first_org_unit_id(account),
        scope_path="GLOBAL",
        metadata={"principal_id": account.principal_id, "roles": list(account.roles)},
    )


async def execute_delete_iam_account(
    request: Request,
    account_id: str,
    caller: UserIdentity,
    iam_svc: IamAccountsGovernanceService,
) -> IamAccountDeleteResponse:
    """Delete IAM account with anti-escalation, user cleanup, auth resync, and audit."""
    from orcia_api.routers._iam_accounts_routes_helpers import (
        is_pg_sync_enabled,
        refresh_evaluator_org_units_from_pg,
        resolve_trace_id,
    )

    auth_svc = get_auth_service(request)
    deleted_id: str | None = None
    deleted_principal: str | None = None
    deleted_email: str | None = None
    deleted_org_unit_id: str | None = None
    if is_pg_sync_enabled():
        try:
            engine = get_or_create_shared_db_engine(request)
            existing = await sync_and_list_iam_accounts_from_postgres18(engine)
            match = next((a for a in existing if a.id == account_id.strip()), None)
            if match is not None:
                enforce_iam_anti_escalation(
                    caller,
                    existing_roles=match.roles,
                    is_delete=True,
                    instance=str(request.url.path),
                )
            deleted_principal = match.principal_id if match else None
            deleted_email = match.email if match else None
            deleted_org_unit_id = first_org_unit_id(match) if match else None
            deleted_id = await delete_iam_account_on_postgres18(
                engine, account_id, instance=str(request.url.path)
            )
            if deleted_principal or deleted_email:
                await cleanup_or_disable_linked_user_on_postgres18(
                    engine, principal_id=deleted_principal, email=deleted_email
                )
            await refresh_evaluator_org_units_from_pg(auth_svc, engine)
        except OrciaDomainError:
            raise
        except Exception as exc:
            logger.warning("iam_accounts_delete_pg_fallback", error_type=type(exc).__name__)
            deleted_id = None
    if deleted_id is None:
        match = next((a for a in iam_svc.list_accounts() if a.id == account_id), None)
        if match is not None:
            enforce_iam_anti_escalation(
                caller,
                existing_roles=match.roles,
                is_delete=True,
                instance=str(request.url.path),
            )
        deleted_principal = match.principal_id if match else None
        deleted_email = match.email if match else None
        deleted_org_unit_id = first_org_unit_id(match) if match else None
        deleted_id = iam_svc.delete_account(account_id, instance=str(request.url.path))
    if deleted_principal:
        sync_in_memory_team_memberships(auth_svc.evaluator, deleted_principal, (), remove_all=True)
        auth_svc.unregister_user(deleted_principal)
        await sync_auth_service_user_by_email_from_pg(request, auth_svc, deleted_principal)
    if deleted_email and deleted_email != deleted_principal:
        auth_svc.unregister_user(deleted_email)
        await sync_auth_service_user_by_email_from_pg(request, auth_svc, deleted_email)
    await record_governance_audit_event(
        request,
        actor=caller,
        event_type="IAM_ACCOUNT_DELETED",
        summary=f"Suppression du compte IAM '{deleted_principal or account_id}'",
        org_unit_id=deleted_org_unit_id,
        scope_path="GLOBAL",
        metadata={"deleted_id": deleted_id, "principal_id": deleted_principal},
    )
    return IamAccountDeleteResponse(deleted_id=deleted_id, trace_id=resolve_trace_id(request))
