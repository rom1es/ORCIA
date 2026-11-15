"""Story 17.3 & 17.6 — IAM Accounts Directory & Temporary Passwords (`/api/v1/settings/iam/*`).

Exposes:
- `GET    /api/v1/settings/iam/role-matrix` (`WRITE_ONLY_NEVER_READABLE`, closed 6 official roles)
- `GET    /api/v1/settings/iam/accounts`    (auto-syncs Day-0 admin with `PLATFORM_ADMIN + SECOPS`)
- `POST   /api/v1/settings/iam/accounts`    (generates 12-char temp password for human users)
- `POST   /api/v1/settings/iam/accounts/{account_id}/temporary-password` (regenerates temp password)
- `PATCH  /api/v1/settings/iam/accounts/{account_id}` (`422 ERR_ADMIN_LOCKOUT_PREVENTED`)
- `DELETE /api/v1/settings/iam/accounts/{account_id}` (`422 ERR_ADMIN_LOCKOUT_PREVENTED`)
"""

from __future__ import annotations

import os
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Path, Query, Request

from orcia_api.dependencies import (
    get_accostage_service,
    get_auth_service,
    get_iam_accounts_service,
    get_or_create_shared_db_engine,
)
from orcia_api.routers._auth_pg_helpers import sync_auth_service_user_by_email_from_pg
from orcia_api.routers._iam_accounts_passwords import (
    cleanup_or_disable_linked_user_on_postgres18,
    enforce_iam_accounts_mutation_access,
    provision_human_temporary_password,
    reset_temporary_password_for_account,
    sync_in_memory_team_memberships,
)
from orcia_api.routers.auth import resolve_request_user
from orcia_api.schemas.iam_accounts import (
    IamAccountCreateRequest,
    IamAccountDeleteResponse,
    IamAccountPatchRequest,
    IamAccountResponse,
    IamAccountsListResponse,
    RoleMatrixEntryResponse,
    RoleMatrixResponse,
)
from orcia_api.schemas.iam_password_models import (
    TemporaryPasswordProvisionResponse,
)
from orcia_api.schemas.problem_details import ProblemDetails
from orcia_core.bootstrap import (
    create_iam_account_on_postgres18,
    delete_iam_account_on_postgres18,
    sync_and_list_iam_accounts_from_postgres18,
    update_iam_account_on_postgres18,
)
from orcia_core.observability.logging import get_current_trace_id, get_logger
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


def _trace(request: Request) -> str:
    return str(getattr(request.state, "trace_id", None) or get_current_trace_id())


def _pg_enabled() -> bool:
    return os.environ.get("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC") != "1"


def _serialize_account(
    acc: IamAccountRecord, temporary_password: str | None = None
) -> IamAccountResponse:
    return IamAccountResponse(
        id=acc.id,
        principal_id=acc.principal_id,
        display_name=acc.display_name,
        email=acc.email,
        account_kind=acc.account_kind,
        auth_source=acc.auth_source,
        roles=list(acc.roles),
        team_ids=list(acc.team_ids),
        status=acc.status,
        temporary_password=temporary_password,
        created_at_iso=acc.created_at_iso,
        updated_at_iso=acc.updated_at_iso,
    )


@router.get(
    "/role-matrix",
    response_model=RoleMatrixResponse,
    summary="Return the native 6-role permission matrix (`WRITE_ONLY_NEVER_READABLE`)",
)
async def get_iam_role_matrix(request: Request) -> RoleMatrixResponse:
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
    effective_persona = persona_key or request.headers.get("x-orcia-persona", "").strip() or None
    resolve_request_user(request, persona_key=effective_persona)
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
    enforce_iam_accounts_mutation_access(request, persona_key)
    auth_svc = get_auth_service(request)
    created: IamAccountRecord | None = None
    if _pg_enabled():
        try:
            engine = get_or_create_shared_db_engine(request)
            await sync_and_list_iam_accounts_from_postgres18(engine)
            created = await create_iam_account_on_postgres18(
                engine,
                principal_id=payload.principal_id,
                display_name=payload.display_name,
                email=payload.email,
                account_kind=payload.account_kind,
                auth_source=payload.auth_source,
                roles=payload.roles,
                team_ids=payload.team_ids,
                status=payload.status,
                instance=str(request.url.path),
            )
        except OrciaDomainError:
            raise
        except Exception as exc:
            logger.warning("iam_accounts_create_pg_fallback", error_type=type(exc).__name__)
            created = None
    if created is None:
        first_admin = get_accostage_service(request).first_admin
        iam_svc.ensure_day0_admin_account(
            email=first_admin.email if first_admin else None,
            display_name=first_admin.display_name if first_admin else None,
        )
        created = iam_svc.create_account(
            principal_id=payload.principal_id,
            display_name=payload.display_name,
            email=payload.email,
            account_kind=payload.account_kind,
            auth_source=payload.auth_source,
            roles=payload.roles,
            team_ids=payload.team_ids,
            status=payload.status,
            instance=str(request.url.path),
        )

    temp_pw: str | None = None
    if created.account_kind == "HUMAN" and created.email:
        shared_engine = get_or_create_shared_db_engine(request) if _pg_enabled() else None
        temp_pw = await provision_human_temporary_password(
            account_id=created.id,
            email=created.email,
            display_name=created.display_name,
            roles=created.roles,
            auth_svc=auth_svc,
            engine=shared_engine,
        )

    if created.team_ids:
        sync_in_memory_team_memberships(auth_svc.evaluator, created.principal_id, created.team_ids)
    if created.email:
        await sync_auth_service_user_by_email_from_pg(request, auth_svc, created.email)
    if created.principal_id and created.principal_id != created.email:
        await sync_auth_service_user_by_email_from_pg(request, auth_svc, created.principal_id)
    return _serialize_account(created, temporary_password=temp_pw)


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
    enforce_iam_accounts_mutation_access(request, persona_key)
    auth_svc = get_auth_service(request)
    engine = get_or_create_shared_db_engine(request) if _pg_enabled() else None
    return await reset_temporary_password_for_account(
        account_id=account_id,
        iam_svc=iam_svc,
        auth_svc=auth_svc,
        engine=engine,
        trace_id=_trace(request),
        instance=str(request.url.path),
    )


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
    enforce_iam_accounts_mutation_access(request, persona_key)
    auth_svc = get_auth_service(request)
    email_provided = "email" in payload.model_fields_set
    updated: IamAccountRecord | None = None
    if _pg_enabled():
        try:
            engine = get_or_create_shared_db_engine(request)
            updated = await update_iam_account_on_postgres18(
                engine,
                account_id,
                display_name=payload.display_name,
                email=payload.email,
                email_provided=email_provided,
                roles=payload.roles,
                team_ids=payload.team_ids,
                status=payload.status,
                instance=str(request.url.path),
            )
        except OrciaDomainError:
            raise
        except Exception as exc:
            logger.warning("iam_accounts_update_pg_fallback", error_type=type(exc).__name__)
            updated = None
    if updated is None:
        updated = iam_svc.update_account(
            account_id,
            display_name=payload.display_name,
            email=payload.email,
            email_provided=email_provided,
            roles=payload.roles,
            team_ids=payload.team_ids,
            status=payload.status,
            instance=str(request.url.path),
        )
    if payload.team_ids is not None:
        sync_in_memory_team_memberships(auth_svc.evaluator, updated.principal_id, updated.team_ids)
    if updated.email:
        await sync_auth_service_user_by_email_from_pg(request, auth_svc, updated.email)
    if updated.principal_id and updated.principal_id != updated.email:
        await sync_auth_service_user_by_email_from_pg(request, auth_svc, updated.principal_id)
    return _serialize_account(updated)


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
    enforce_iam_accounts_mutation_access(request, persona_key)
    auth_svc = get_auth_service(request)
    deleted_id: str | None = None
    deleted_principal: str | None = None
    deleted_email: str | None = None
    if _pg_enabled():
        try:
            engine = get_or_create_shared_db_engine(request)
            existing = await sync_and_list_iam_accounts_from_postgres18(engine)
            match = next((a for a in existing if a.id == account_id.strip()), None)
            deleted_principal = match.principal_id if match else None
            deleted_email = match.email if match else None
            deleted_id = await delete_iam_account_on_postgres18(
                engine, account_id, instance=str(request.url.path)
            )
            if deleted_principal or deleted_email:
                await cleanup_or_disable_linked_user_on_postgres18(
                    engine,
                    principal_id=deleted_principal,
                    email=deleted_email,
                )
        except OrciaDomainError:
            raise
        except Exception as exc:
            logger.warning("iam_accounts_delete_pg_fallback", error_type=type(exc).__name__)
            deleted_id = None
    if deleted_id is None:
        match = next((a for a in iam_svc.list_accounts() if a.id == account_id), None)
        deleted_principal = match.principal_id if match else None
        deleted_email = match.email if match else None
        deleted_id = iam_svc.delete_account(account_id, instance=str(request.url.path))
    if deleted_principal:
        sync_in_memory_team_memberships(auth_svc.evaluator, deleted_principal, (), remove_all=True)
        auth_svc.unregister_user(deleted_principal)
        await sync_auth_service_user_by_email_from_pg(request, auth_svc, deleted_principal)
    if deleted_email and deleted_email != deleted_principal:
        auth_svc.unregister_user(deleted_email)
        await sync_auth_service_user_by_email_from_pg(request, auth_svc, deleted_email)
    return IamAccountDeleteResponse(deleted_id=deleted_id, trace_id=_trace(request))
