"""Read/Outcome models for Autonomous Run Supervision (`Story 7.4`)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from orcia_core.kernel.errors import ResourceNotFoundError
from orcia_core.kernel.ids import new_uuid7_str
from orcia_core.orchestration._orchestration_runtime_locales import (
    SUPERVISION_LOCALES,
    get_runtime_copy,
)
from orcia_core.orchestration.presence_and_sse import TaskNotificationEntity


@dataclass(frozen=True, slots=True)
class AutonomousRunSupervisionItem:
    """Read projection of an autonomous workflow run for supervision UI (`UX-DR17`)."""

    run_id: str
    workspace_id: str
    workflow_id: str
    workflow_title: str
    trigger_id: str | None
    trigger_label: str
    trigger_type: str
    trigger_status: str
    run_status: str
    post_hoc_status: str
    contract_id: str
    cost_usd: float
    created_at_iso: str
    help_resource_id: str | None = None
    previous_version_available: bool = False


@dataclass(frozen=True, slots=True)
class EmergencyStopOutcome:
    """Outcome of executing an emergency stop (`KILL_SWITCH_STOPPED`)."""

    run_id: str
    workspace_id: str
    status: str
    trigger_suspended: bool
    sse_dispatch_latency_ms: float


@dataclass(frozen=True, slots=True)
class InvalidateAndRestoreOutcome:
    """Outcome of invalidating an autonomous run & restoring `@v(N-1)`."""

    run_id: str
    workspace_id: str
    status: str
    restored_version: str
    help_resource_id: str | None
    redis_cache_invalidated_ms: float
    sse_dispatch_latency_ms: float


def build_autonomous_notification(
    *,
    workspace_id: str,
    run_id: str,
    workflow_id: str,
    trigger_label: str,
    kind: str,
) -> TaskNotificationEntity:
    """Create a priority notification for autonomous escalation or post-hoc sampling."""
    sc = get_runtime_copy(SUPERVISION_LOCALES)
    wf_short = workflow_id.rsplit("/", 1)[-1]
    if kind == "POST_HOC_AUDIT_SAMPLE":
        return TaskNotificationEntity(
            id=new_uuid7_str(),
            workspace_id=workspace_id,
            target_team_id=None,
            target_user_id=None,
            run_id=run_id,
            step_execution_id=run_id,
            step_key="post-hoc-audit",
            notification_type="POST_HOC_AUDIT_SAMPLE",
            scope_kind="TEAM",
            title=sc["audit_title"].format(wf=wf_short),
            summary=sc["audit_summary"].format(trigger=trigger_label),
        )
    return TaskNotificationEntity(
        id=new_uuid7_str(),
        workspace_id=workspace_id,
        target_team_id=None,
        target_user_id=None,
        run_id=run_id,
        step_execution_id=run_id,
        step_key="autonomous-escalation",
        notification_type="AUTONOMOUS_ESCALATION",
        scope_kind="TEAM",
        title=sc["esc_title"].format(wf=wf_short),
        summary=sc["esc_summary"].format(trigger=trigger_label),
    )


def resolve_run_context(
    run_id: str,
    mem: AutonomousRunSupervisionItem | None,
    pg_row: dict[str, Any] | None,
) -> tuple[str, str, str, str | None]:
    """Extract `(workspace_id, workflow_id, contract_id, trigger_id)` or raise 404."""
    if pg_row is not None:
        return (
            str(pg_row["workspace_id"]),
            str(pg_row["workflow_uri"]),
            str(pg_row["contract_id"] or ""),
            str(pg_row["trigger_id"]) if pg_row.get("trigger_id") else None,
        )
    if mem is not None:
        return mem.workspace_id, mem.workflow_id, mem.contract_id, mem.trigger_id
    raise ResourceNotFoundError(
        detail_code="ERR_AUTONOMOUS_RUN_NOT_FOUND",
        detail_params={"run_id": run_id},
    )


def map_pg_row_to_supervision_item(row: dict[str, Any]) -> AutonomousRunSupervisionItem:
    """Project a PostgreSQL row dictionary onto `AutonomousRunSupervisionItem`."""
    uri = str(row["workflow_uri"])
    help_res = row.get("help_resource_id")
    return AutonomousRunSupervisionItem(
        run_id=str(row["run_id"]),
        workspace_id=str(row["workspace_id"]),
        workflow_id=uri,
        workflow_title=uri.rsplit("/", 1)[-1] or uri,
        trigger_id=str(row["trigger_id"]) if row.get("trigger_id") else None,
        trigger_label=str(row["trigger_label"]),
        trigger_type=str(row["trigger_type"]),
        trigger_status=str(row["trigger_status"]),
        run_status=str(row["run_status"]),
        post_hoc_status=str(row["post_hoc_status"]),
        contract_id=str(row["contract_id"]),
        cost_usd=float(row["cost_usd"]),
        created_at_iso=str(row["created_at_iso"]),
        help_resource_id=str(help_res) if help_res else None,
        previous_version_available=bool(row.get("previous_version_available", False)),
    )


def make_registered_supervision_item(
    *,
    run_id: str,
    workspace_id: str,
    workflow_id: str,
    contract_id: str,
    status: str,
    trigger_id: str | None,
    trigger_label: str,
    trigger_type: str,
    trigger_status: str,
    post_hoc_status: str,
    cost_usd: Decimal,
    help_resource_id: str | None,
) -> AutonomousRunSupervisionItem:
    """Build an `AutonomousRunSupervisionItem` for in-memory registration."""
    return AutonomousRunSupervisionItem(
        run_id=run_id,
        workspace_id=workspace_id,
        workflow_id=workflow_id,
        workflow_title=workflow_id.rsplit("/", 1)[-1] or workflow_id,
        trigger_id=trigger_id,
        trigger_label=trigger_label,
        trigger_type=trigger_type,
        trigger_status=trigger_status,
        run_status=status,
        post_hoc_status=post_hoc_status,
        contract_id=contract_id,
        cost_usd=float(cost_usd),
        created_at_iso=datetime.now(UTC).isoformat().replace("+00:00", "Z"),
        help_resource_id=help_resource_id,
        previous_version_available=help_resource_id is not None,
    )


def resolve_help_id_from_context(
    explicit_help_id: str | None,
    mem: AutonomousRunSupervisionItem | None,
    pg_row: dict[str, Any] | None,
) -> str | None:
    """Pick explicit help resource ID, else PG18 row value, else in-memory state."""
    if explicit_help_id:
        return explicit_help_id
    if pg_row is not None and pg_row.get("help_resource_id"):
        return str(pg_row["help_resource_id"])
    return mem.help_resource_id if mem is not None else None
