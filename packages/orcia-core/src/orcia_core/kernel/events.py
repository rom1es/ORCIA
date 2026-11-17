"""Immutable Domain Events for the Transactional Outbox (`domain_events_outbox`, `AD-12`, `AD-19`).

Pure kernel module — zero framework or business domain dependencies.
All event classes are re-exported here for public backward-compatible use.
"""

from __future__ import annotations

from orcia_core.kernel._datasource_rag_events import (
    DatasourceFreshnessEvaluated,
    DatasourceSyncRequested,
    EmbeddingReindexCompleted,
    EmbeddingReindexFailed,
    EmbeddingReindexStarted,
)
from orcia_core.kernel._events_base import DomainEvent
from orcia_core.kernel._finops_audit_events import (
    AdminConnectionTested,
    BudgetCircuitTripped,
    BudgetOverrideApproved,
    ConnectorCircuitTripped,
    RemoteUsageAnomalyCapped,
)
from orcia_core.kernel._governance_events import (
    AccessRequested,
    AutonomousContractRevoked,
    AutonomousContractSigned,
    AutonomousEscalated,
    PermissionGranted,
    PermissionRevoked,
    SelfTriggerBlocked,
    SettingsChanged,
    TriggerCircuitOpened,
    TriggerFired,
    WorkflowPublished,
)
from orcia_core.kernel._orchestration_events import (
    ArtifactProduced,
    GateEvaluated,
    HumanArbitrationRequested,
    RunTerminated,
    StepCompleted,
)

__all__ = [
    "AccessRequested",
    "AdminConnectionTested",
    "ArtifactProduced",
    "AutonomousContractRevoked",
    "AutonomousContractSigned",
    "AutonomousEscalated",
    "BudgetCircuitTripped",
    "BudgetOverrideApproved",
    "ConnectorCircuitTripped",
    "DatasourceFreshnessEvaluated",
    "DatasourceSyncRequested",
    "DomainEvent",
    "EmbeddingReindexCompleted",
    "EmbeddingReindexFailed",
    "EmbeddingReindexStarted",
    "GateEvaluated",
    "HumanArbitrationRequested",
    "PermissionGranted",
    "PermissionRevoked",
    "RemoteUsageAnomalyCapped",
    "RunTerminated",
    "SelfTriggerBlocked",
    "SettingsChanged",
    "StepCompleted",
    "TriggerCircuitOpened",
    "TriggerFired",
    "WorkflowPublished",
]
