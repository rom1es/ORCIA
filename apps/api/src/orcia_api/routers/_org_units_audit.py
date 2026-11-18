"""Story 20.1 — Governance Audit Helpers (`ORG_UNIT_*`, `IAM_ACCOUNT_*`) for `audit_ledger`."""

from __future__ import annotations

from uuid import UUID

from fastapi import Request

from orcia_api.dependencies import get_audit_ledger_service
from orcia_core.observability.logging import get_current_trace_id, get_logger
from orcia_core.permissions import UserIdentity
from orcia_core.ports.finops_telemetry import FinopsCostLedgerEntry
from orcia_kernel.ids import new_uuid7_str

logger = get_logger("orcia.api.org_units.audit")


def _safe_uuid_str(raw: str | None) -> str | None:
    if not raw:
        return None
    try:
        return str(UUID(str(raw).strip()))
    except (ValueError, TypeError):
        return None


async def record_governance_audit_event(
    request: Request,
    *,
    actor: UserIdentity,
    event_type: str,
    summary: str,
    org_unit_id: str | None = None,
    scope_path: str = "GLOBAL",
    metadata: dict[str, object] | None = None,
) -> None:
    """Persist an immutable governance audit entry (`ORG_UNIT_*`, `IAM_ACCOUNT_*`) into ledger."""
    trace_id = str(getattr(request.state, "trace_id", None) or get_current_trace_id())
    entry = FinopsCostLedgerEntry(
        id=new_uuid7_str(),
        source_event_id=new_uuid7_str(),
        actor_type="USER",
        actor_id=actor.id,
        actor_display_name=actor.display_name,
        actor_email=actor.email,
        event_type=event_type,
        summary=summary,
        trace_id=trace_id,
        workspace_id=None,
        org_unit_id=_safe_uuid_str(org_unit_id),
        scope_path=scope_path or "GLOBAL",
        metadata=metadata or {},
    )
    from orcia_api.dependencies._core_providers import get_configured_db_engine

    audit_svc = get_audit_ledger_service(request)
    engine = get_configured_db_engine(request)
    if engine is None:
        await audit_svc.record_entry(entry)
        return
    try:
        async with engine.begin() as conn:
            await audit_svc.record_entry(entry, conn=conn)
    except Exception as exc:
        logger.warning(
            "governance_audit_record_skipped",
            event_type=event_type,
            error_type=type(exc).__name__,
        )


__all__ = ["record_governance_audit_event"]
