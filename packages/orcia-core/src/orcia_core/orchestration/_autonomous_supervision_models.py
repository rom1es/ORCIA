"""Read/Outcome models for Autonomous Run Supervision (`Story 7.4`)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
from decimal import Decimal
from typing import Any

from orcia_core.catalog.contextual_help import (
    ContextualHelpResolutionService,
    build_help_redis_cache_key,
)
from orcia_core.kernel.errors import ResourceNotFoundError
from orcia_core.kernel.ids import new_uuid7_str
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
            title=f"Contrôle qualité par échantillonnage : {wf_short}",
            summary=f"Dossier sélectionné automatiquement ({trigger_label}).",
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
        title=f"Escalade requise : {wf_short}",
        summary=f"L'exécution sous contrat ({trigger_label}) attend une décision humaine.",
    )


def restore_help_in_memory_and_flush_redis(
    *,
    help_service: ContextualHelpResolutionService | None,
    redis_client: Any | None,
    help_resource_id: str | None,
) -> str:
    """Restore `@v(N-1)` in `ContextualHelpResolutionService` and delete Redis `help:route:*`."""
    restored_ver = "1.0.0"
    if not help_resource_id or help_service is None:
        return restored_ver
    try:
        restored_art = help_service.rollback_to_previous_version(help_resource_id)
        restored_ver = restored_art.version
        if redis_client is not None:
            pack = restored_art.pack_name or "core"
            for rt in restored_art.bound_routes:
                redis_client.delete(build_help_redis_cache_key(rt, pack, restored_art.lang))
    except ResourceNotFoundError:
        pass
    return restored_ver


def resolve_run_context(
    run_id: str,
    mem: AutonomousRunSupervisionItem | None,
    pg_row: dict[str, Any] | None,
) -> tuple[str, str, str, str | None]:
    """Extract `(workspace_id, workflow_id, contract_id, trigger_id)` or raise 404."""
    if mem is not None:
        return mem.workspace_id, mem.workflow_id, mem.contract_id, mem.trigger_id
    if pg_row is None:
        raise ResourceNotFoundError(detail_override=f"Exécution introuvable : {run_id}")
    return (
        str(pg_row["workspace_id"]),
        str(pg_row["workflow_uri"]),
        str(pg_row["contract_id"] or ""),
        str(pg_row["trigger_id"]) if pg_row.get("trigger_id") else None,
    )


def map_pg_row_to_supervision_item(row: dict[str, Any]) -> AutonomousRunSupervisionItem:
    """Project a PostgreSQL row dictionary onto `AutonomousRunSupervisionItem`."""
    uri = str(row["workflow_uri"])
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
