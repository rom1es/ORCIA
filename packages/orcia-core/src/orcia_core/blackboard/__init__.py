"""Bounded Context 2: Blackboard (Immutable JSONB Snapshots, Step Memlog & Lexical Isolation)."""

from __future__ import annotations

from orcia_core.blackboard._internal.sql_blackboard_queries import (
    list_active_workspace_blackboard_snapshots_pg,
)
from orcia_core.blackboard.models import (
    BackgroundAuditConsolidatedReport,
    BlackboardSnapshotEntity,
    HydratedStepContext,
    MemlogMarkerType,
    SnapshotBranchStatus,
    StepExecutionEntity,
    StepExecutionStatus,
    StepMemlogEntry,
)
from orcia_core.blackboard.store import AppendOnlyBlackboardStore

DOMAIN_NAME: str = "blackboard"

__all__ = [
    "DOMAIN_NAME",
    "AppendOnlyBlackboardStore",
    "BackgroundAuditConsolidatedReport",
    "BlackboardSnapshotEntity",
    "HydratedStepContext",
    "MemlogMarkerType",
    "SnapshotBranchStatus",
    "StepExecutionEntity",
    "StepExecutionStatus",
    "StepMemlogEntry",
    "list_active_workspace_blackboard_snapshots_pg",
]
