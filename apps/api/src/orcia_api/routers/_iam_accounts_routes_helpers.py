"""Helpers for IAM accounts router serialization & PG/memory ops (`Story 17.3` & `20.1`)."""

from __future__ import annotations

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_api.dependencies import (
    get_accostage_service,
    get_auth_service,
    get_or_create_shared_db_engine,
)
from orcia_api.locales._router_locale_messages import get_router_copy
from orcia_api.routers._iam_accounts_audit import (
    execute_delete_iam_account,
    first_org_unit_id,
    resync_iam_account_and_audit,
)
from orcia_api.routers._iam_accounts_passwords import (
    enforce_iam_anti_escalation,
    provision_human_temporary_password,
)
from orcia_api.routers._org_units_helpers import sync_evaluator_from_summaries
from orcia_api.schemas.iam_accounts import (
    IamAccountCreateRequest,
    IamAccountPatchRequest,
    IamAccountResponse,
)
from orcia_core.bootstrap import (
    create_iam_account_on_postgres18,
    list_org_units_from_postgres18,
    sync_and_list_iam_accounts_from_postgres18,
    update_iam_account_on_postgres18,
)
from orcia_core.observability.logging import get_current_trace_id, get_logger
from orcia_core.permissions import (
    AuthAndOrganizationService,
    IamAccountRecord,
    IamAccountsGovernanceService,
    UserIdentity,
)
from orcia_core.permissions.errors import OrciaDomainError

logger = get_logger("orcia.api.iam_accounts.helpers")


def resolve_trace_id(request: Request) -> str:
    return str(getattr(request.state, "trace_id", None) or get_current_trace_id())


def is_pg_sync_enabled() -> bool:
    from orcia_api.dependencies._core_providers import is_pg_runtime_active

    return is_pg_runtime_active()


def serialize_iam_account(
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
        led_bu_ids=list(acc.led_bu_ids),
        led_team_ids=list(acc.led_team_ids),
        ontology_led_bu_ids=list(acc.ontology_led_bu_ids),
    )


async def refresh_evaluator_org_units_from_pg(
    auth_svc: AuthAndOrganizationService,
    engine: AsyncEngine | None,
) -> None:
    """Reload all org units from PostgreSQL 18 into `auth_svc.evaluator`."""
    if engine is None or not is_pg_sync_enabled():
        return
    try:
        summaries = await list_org_units_from_postgres18(engine)
        sync_evaluator_from_summaries(auth_svc.evaluator, summaries)
    except Exception as exc:
        logger.warning("refresh_evaluator_org_units_from_pg_error", error=str(exc))


async def execute_create_iam_account(
    request: Request,
    payload: IamAccountCreateRequest,
    caller: UserIdentity,
    iam_svc: IamAccountsGovernanceService,
) -> IamAccountResponse:
    """Create IAM account (PG18 first, memory fallback), provision temp password & audit."""
    enforce_iam_anti_escalation(caller, next_roles=payload.roles, instance=str(request.url.path))
    auth_svc = get_auth_service(request)
    created: IamAccountRecord | None = None
    if is_pg_sync_enabled():
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
                led_bu_ids=payload.led_bu_ids,
                led_team_ids=payload.led_team_ids,
                ontology_led_bu_ids=payload.ontology_led_bu_ids,
                instance=str(request.url.path),
            )
            await refresh_evaluator_org_units_from_pg(auth_svc, engine)
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
            led_bu_ids=payload.led_bu_ids,
            led_team_ids=payload.led_team_ids,
            ontology_led_bu_ids=payload.ontology_led_bu_ids,
            instance=str(request.url.path),
        )

    temp_pw: str | None = None
    if created.account_kind == "HUMAN" and created.email:
        shared_engine = get_or_create_shared_db_engine(request) if is_pg_sync_enabled() else None
        temp_pw = await provision_human_temporary_password(
            account_id=created.id,
            email=created.email,
            display_name=created.display_name,
            roles=created.roles,
            auth_svc=auth_svc,
            engine=shared_engine,
            primary_org_unit_id=first_org_unit_id(created),
        )

    await resync_iam_account_and_audit(
        request,
        auth_svc,
        caller,
        account=created,
        event_type="IAM_ACCOUNT_CREATED",
        summary=get_router_copy().iam_created.format(principal_id=created.principal_id),
        sync_teams=bool(created.team_ids),
    )
    return serialize_iam_account(created, temporary_password=temp_pw)


async def execute_update_iam_account(
    request: Request,
    account_id: str,
    payload: IamAccountPatchRequest,
    caller: UserIdentity,
    iam_svc: IamAccountsGovernanceService,
) -> IamAccountResponse:
    """Update IAM account with anti-escalation, B1 org sync, auth resync, and audit."""
    auth_svc = get_auth_service(request)
    email_provided = "email" in payload.model_fields_set
    updated: IamAccountRecord | None = None
    if is_pg_sync_enabled():
        try:
            engine = get_or_create_shared_db_engine(request)
            existing = await sync_and_list_iam_accounts_from_postgres18(engine)
            match = next((a for a in existing if a.id == account_id.strip()), None)
            if match is not None and payload.roles is not None:
                enforce_iam_anti_escalation(
                    caller,
                    existing_roles=match.roles,
                    next_roles=payload.roles,
                    instance=str(request.url.path),
                )
            updated = await update_iam_account_on_postgres18(
                engine,
                account_id,
                display_name=payload.display_name,
                email=payload.email,
                email_provided=email_provided,
                roles=payload.roles,
                team_ids=payload.team_ids,
                status=payload.status,
                led_bu_ids=payload.led_bu_ids,
                led_team_ids=payload.led_team_ids,
                ontology_led_bu_ids=payload.ontology_led_bu_ids,
                instance=str(request.url.path),
            )
            await refresh_evaluator_org_units_from_pg(auth_svc, engine)
        except OrciaDomainError:
            raise
        except Exception as exc:
            logger.warning("iam_accounts_update_pg_fallback", error_type=type(exc).__name__)
            updated = None
    if updated is None:
        match = next((a for a in iam_svc.list_accounts() if a.id == account_id.strip()), None)
        if match is not None and payload.roles is not None:
            enforce_iam_anti_escalation(
                caller,
                existing_roles=match.roles,
                next_roles=payload.roles,
                instance=str(request.url.path),
            )
        updated = iam_svc.update_account(
            account_id,
            display_name=payload.display_name,
            email=payload.email,
            email_provided=email_provided,
            roles=payload.roles,
            team_ids=payload.team_ids,
            status=payload.status,
            led_bu_ids=payload.led_bu_ids,
            led_team_ids=payload.led_team_ids,
            ontology_led_bu_ids=payload.ontology_led_bu_ids,
            instance=str(request.url.path),
        )
    await resync_iam_account_and_audit(
        request,
        auth_svc,
        caller,
        account=updated,
        event_type="IAM_ACCOUNT_UPDATED",
        summary=get_router_copy().iam_updated.format(principal_id=updated.principal_id),
        sync_teams=payload.team_ids is not None,
    )
    return serialize_iam_account(updated)


__all__ = [
    "execute_create_iam_account",
    "execute_delete_iam_account",
    "execute_update_iam_account",
    "is_pg_sync_enabled",
    "refresh_evaluator_org_units_from_pg",
    "resolve_trace_id",
    "serialize_iam_account",
]
