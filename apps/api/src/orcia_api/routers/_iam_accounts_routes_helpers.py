"""Helper utilities for IAM accounts router serialization & evaluator refresh (`Story 17.3`)."""

from __future__ import annotations

import os

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_api.routers._org_units_helpers import sync_evaluator_from_summaries
from orcia_api.schemas.iam_accounts import IamAccountResponse
from orcia_core.bootstrap import list_org_units_from_postgres18
from orcia_core.observability.logging import get_current_trace_id, get_logger
from orcia_core.permissions import AuthAndOrganizationService, IamAccountRecord

logger = get_logger("orcia.api.iam_accounts.helpers")


def resolve_trace_id(request: Request) -> str:
    return str(getattr(request.state, "trace_id", None) or get_current_trace_id())


def is_pg_sync_enabled() -> bool:
    return os.environ.get("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC") != "1"


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
