"""Autonomous Supervision, Post-Hoc Audit & Emergency Stop Domain Events (`Story 7.4`, `AD-18`).

Pure kernel module — zero framework or business domain dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass

from orcia_core.kernel._events_base import DomainEvent
from orcia_core.kernel.ids import new_uuid7_str


@dataclass(frozen=True, slots=True)
class PostHocSampleSelected(DomainEvent):
    """Published when an autonomous run is sampled (`10-20%`) for post-hoc quality audit."""

    contract_id: str = ""
    sampling_rate: float = 0.15

    @classmethod
    def create(
        cls,
        *,
        audit_id: str,
        run_id: str,
        workspace_id: str,
        contract_id: str,
        workflow_id: str,
        sampling_rate: float = 0.15,
        scope_path: str = "GLOBAL",
        trace_id: str = "00000000000000000000000000000000",
    ) -> PostHocSampleSelected:
        return cls(
            event_id=new_uuid7_str(),
            event_type="PostHocSampleSelected",
            aggregate_type="autonomous_post_hoc_audit",
            aggregate_id=audit_id,
            run_id=run_id,
            workspace_id=workspace_id,
            payload={
                "audit_id": audit_id,
                "run_id": run_id,
                "contract_id": contract_id,
                "workflow_id": workflow_id,
                "sampling_rate": sampling_rate,
                "scope_path": scope_path,
                "actor_id": "system",
                "actor_type": "SYSTEM",
            },
            trace_id=trace_id,
            contract_id=contract_id,
            sampling_rate=sampling_rate,
        )


@dataclass(frozen=True, slots=True)
class KillSwitchActivated(DomainEvent):
    """Published when a human triggers an emergency stop (`KILL_SWITCH_STOPPED`, `Story 7.4`)."""

    actor_user_id: str = ""
    reason: str = ""
    trigger_suspended: bool = False

    @classmethod
    def create(
        cls,
        *,
        run_id: str,
        workspace_id: str,
        workflow_id: str,
        actor_user_id: str,
        reason: str = "",
        trigger_id: str | None = None,
        trigger_suspended: bool = False,
        scope_path: str = "GLOBAL",
        trace_id: str = "00000000000000000000000000000000",
    ) -> KillSwitchActivated:
        return cls(
            event_id=new_uuid7_str(),
            event_type="KillSwitchActivated",
            aggregate_type="workflow_run",
            aggregate_id=run_id,
            run_id=run_id,
            workspace_id=workspace_id,
            payload={
                "run_id": run_id,
                "workflow_id": workflow_id,
                "reason": reason,
                "trigger_id": trigger_id,
                "trigger_suspended": trigger_suspended,
                "scope_path": scope_path,
                "actor_id": actor_user_id,
                "actor_type": "USER",
            },
            trace_id=trace_id,
            actor_user_id=actor_user_id,
            reason=reason,
            trigger_suspended=trigger_suspended,
        )


@dataclass(frozen=True, slots=True)
class AutonomousArtifactRolledBack(DomainEvent):
    """Published when an autonomous deliverable or help article is restored to `@v(N-1)`."""

    actor_user_id: str = ""
    restored_version: str = ""
    help_resource_id: str | None = None

    @classmethod
    def create(
        cls,
        *,
        run_id: str,
        workspace_id: str,
        workflow_id: str,
        actor_user_id: str,
        restored_version: str = "1.0.0",
        help_resource_id: str | None = None,
        comment: str = "",
        scope_path: str = "GLOBAL",
        trace_id: str = "00000000000000000000000000000000",
    ) -> AutonomousArtifactRolledBack:
        return cls(
            event_id=new_uuid7_str(),
            event_type="AutonomousArtifactRolledBack",
            aggregate_type="workflow_run",
            aggregate_id=run_id,
            run_id=run_id,
            workspace_id=workspace_id,
            payload={
                "run_id": run_id,
                "workflow_id": workflow_id,
                "restored_version": restored_version,
                "help_resource_id": help_resource_id,
                "comment": comment,
                "scope_path": scope_path,
                "actor_id": actor_user_id,
                "actor_type": "USER",
            },
            trace_id=trace_id,
            actor_user_id=actor_user_id,
            restored_version=restored_version,
            help_resource_id=help_resource_id,
        )
