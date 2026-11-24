"""Story 17.3, 17.6 & 20.1 — IAM Accounts Directory & Temp Passwords (`/api/v1/settings/iam/*`).

Exposes:
- `GET    /api/v1/settings/iam/role-matrix` (`WRITE_ONLY_NEVER_READABLE`, closed 7 official roles)
- `GET    /api/v1/settings/iam/accounts`    (auto-syncs Day-0 admin with `PLATFORM_ADMIN + SECOPS`)
- `POST   /api/v1/settings/iam/accounts`    (`PLATFORM_ADMIN` / `SECOPS` only, with anti-escalation)
- `POST   /api/v1/settings/iam/accounts/{account_id}/temporary-password`
- `PATCH  /api/v1/settings/iam/accounts/{account_id}` (`422 ERR_ADMIN_LOCKOUT_PREVENTED`)
- `DELETE /api/v1/settings/iam/accounts/{account_id}` (`422 ERR_ADMIN_LOCKOUT_PREVENTED`)
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, Path, Query, Request

from orcia_api.dependencies import (
    get_accostage_service,
    get_auth_service,
    get_iam_accounts_service,
    get_or_create_shared_db_engine,
)
from orcia_api.locales._router_locale_messages import get_router_copy
from orcia_api.routers._auth_token_issuer import resolve_request_user
from orcia_api.routers._iam_accounts_passwords import (
    enforce_iam_accounts_mutation_access,
    enforce_iam_accounts_read_access,
    reset_temporary_password_for_account,
)
from orcia_api.routers._iam_accounts_routes_helpers import (
    execute_create_iam_account,
    execute_delete_iam_account,
    execute_update_iam_account,
)
from orcia_api.routers._iam_accounts_routes_helpers import (
    is_pg_sync_enabled as _pg_enabled,
)
from orcia_api.routers._iam_accounts_routes_helpers import (
    resolve_trace_id as _trace,
)
from orcia_api.routers._iam_accounts_routes_helpers import (
    serialize_iam_account as _serialize_account,
)
from orcia_api.routers._org_units_audit import record_governance_audit_event
from orcia_api.schemas.iam_accounts import (
    IamAccountCreateRequest,
    IamAccountDeleteResponse,
    IamAccountPatchRequest,
    IamAccountResponse,
    IamAccountsListResponse,
    RoleMatrixEntryResponse,
    RoleMatrixResponse,
)
from orcia_api.schemas.iam_password_models import TemporaryPasswordProvisionResponse
from orcia_api.schemas.problem_details import ProblemDetails
from orcia_core.bootstrap import sync_and_list_iam_accounts_from_postgres18
from orcia_core.observability.logging import get_logger
from orcia_core.permissions import (
    IamAccountRecord,
    IamAccountsGovernanceService,
    list_native_role_matrix,
)
from orcia_core.permissions.errors import OrciaDomainError

logger = get_logger("orcia.api.iam_accounts")

IAM_ACCOUNTS_PROBLEM_RESPONSES: dict[int | str, dict[str, Any]] = {
    400: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
    401: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
    403: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
    404: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
    409: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
    422: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
}

router = APIRouter(
    prefix="/api/v1/settings/iam",
    tags=["iam-accounts"],
    responses=IAM_ACCOUNTS_PROBLEM_RESPONSES,
)


@router.get(
    "/role-matrix",
    response_model=RoleMatrixResponse,
    summary="Return the native 7-role permission matrix (`WRITE_ONLY_NEVER_READABLE`)",
)
async def get_iam_role_matrix(request: Request) -> RoleMatrixResponse:
    resolve_request_user(request)
    entries = [
        RoleMatrixEntryResponse(
            role=d.role,
            natural_scope=d.natural_scope,
            native_verbs=list(d.native_verbs),
            resource_permissions={k: list(v) for k, v in d.resource_permissions.items()},
            secret_visibility=d.secret_visibility,
        )
        for d in list_native_role_matrix()
    ]
    return RoleMatrixResponse(
        secret_visibility_policy="WRITE_ONLY_NEVER_READABLE",  # pragma: allowlist secret
        roles=entries,
        trace_id=_trace(request),
    )


@router.get(
    "/accounts",
    response_model=IamAccountsListResponse,
    summary="List IAM human & service accounts with automatic Day-0 admin synchronization",
)
async def list_iam_accounts(
    request: Request,
    iam_svc: Annotated[IamAccountsGovernanceService, Depends(get_iam_accounts_service)],
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> IamAccountsListResponse:
    enforce_iam_accounts_read_access(request, persona_key)
    accounts: list[IamAccountRecord] | None = None
    if _pg_enabled():
        try:
            engine = get_or_create_shared_db_engine(request)
            accounts = await sync_and_list_iam_accounts_from_postgres18(engine)
        except OrciaDomainError:
            raise
        except Exception as exc:
            logger.warning("iam_accounts_list_pg_fallback", error_type=type(exc).__name__)
            accounts = None
    if accounts is None:
        first_admin = get_accostage_service(request).first_admin
        accounts = iam_svc.ensure_day0_admin_account(
            email=first_admin.email if first_admin else None,
            display_name=first_admin.display_name if first_admin else None,
        )
    return IamAccountsListResponse(
        accounts=[_serialize_account(a) for a in accounts],
        trace_id=_trace(request),
    )


@router.post(
    "/accounts",
    response_model=IamAccountResponse,
    summary="Create a human user or technical `SERVICE_PRINCIPAL` in the IAM directory",
)
async def create_iam_account(
    payload: IamAccountCreateRequest,
    request: Request,
    iam_svc: Annotated[IamAccountsGovernanceService, Depends(get_iam_accounts_service)],
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> IamAccountResponse:
    caller = enforce_iam_accounts_mutation_access(request, persona_key)
    return await execute_create_iam_account(request, payload, caller, iam_svc)


@router.post(
    "/accounts/{account_id}/temporary-password",
    response_model=TemporaryPasswordProvisionResponse,
    summary="Reset temporary password on a human IAM account and return invitation",
)
async def reset_iam_account_temporary_password(
    account_id: Annotated[str, Path(min_length=1, max_length=128)],
    request: Request,
    iam_svc: Annotated[IamAccountsGovernanceService, Depends(get_iam_accounts_service)],
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> TemporaryPasswordProvisionResponse:
    caller = enforce_iam_accounts_mutation_access(request, persona_key)
    auth_svc = get_auth_service(request)
    engine = get_or_create_shared_db_engine(request) if _pg_enabled() else None
    res = await reset_temporary_password_for_account(
        account_id=account_id,
        iam_svc=iam_svc,
        auth_svc=auth_svc,
        engine=engine,
        trace_id=_trace(request),
        instance=str(request.url.path),
    )
    await record_governance_audit_event(
        request,
        actor=caller,
        event_type="IAM_ACCOUNT_UPDATED",
        summary=get_router_copy().iam_pw_reset.format(principal_id=res.principal_id),
        scope_path="GLOBAL",
        metadata={"principal_id": res.principal_id},
    )
    return res


@router.patch(
    "/accounts/{account_id}",
    response_model=IamAccountResponse,
    summary="Update roles, teams, display name or status with deterministic anti-lockout",
)
async def update_iam_account(
    payload: IamAccountPatchRequest,
    request: Request,
    iam_svc: Annotated[IamAccountsGovernanceService, Depends(get_iam_accounts_service)],
    account_id: Annotated[str, Path(min_length=1, max_length=128)],
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> IamAccountResponse:
    caller = enforce_iam_accounts_mutation_access(request, persona_key)
    return await execute_update_iam_account(request, account_id, payload, caller, iam_svc)


@router.delete(
    "/accounts/{account_id}",
    response_model=IamAccountDeleteResponse,
    summary="Delete an IAM account with deterministic anti-lockout (`422` if last active admin)",
)
async def delete_iam_account(
    request: Request,
    iam_svc: Annotated[IamAccountsGovernanceService, Depends(get_iam_accounts_service)],
    account_id: Annotated[str, Path(min_length=1, max_length=128)],
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> IamAccountDeleteResponse:
    caller = enforce_iam_accounts_mutation_access(request, persona_key)
    return await execute_delete_iam_account(request, account_id, caller, iam_svc)
