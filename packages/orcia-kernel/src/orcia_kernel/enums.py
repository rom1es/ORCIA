"""Universal cross-domain enumerations and Literal types (`AD-19`, `Story 3.2a`).

Shared by `blackboard`, `orchestration`, `gates`, `permissions` and `audit_finops` without
creating circular dependencies between sibling domains.
"""

from __future__ import annotations

from typing import Literal

SupportedLocale = Literal["fr", "en"]
DEFAULT_LOCALE: SupportedLocale = "fr"

WorkflowStepType = Literal[
    "AGENT",
    "SKILL",
    "SUB_WORKFLOW",
    "POST_ACTION_VERIFICATION",
]

WorkflowCriticality = Literal[
    "LOW_ROUTINE",
    "MEDIUM_STANDARD",
    "HIGH_CRITICAL",
]

WorkflowExecutionRegime = Literal[
    "INTERACTIVE_COACHING",
    "BACKGROUND_FAST_PATH",
    "AUTONOMOUS_CONTRACT",
]

TieBreakPolicy = Literal[
    "PAUSE_AND_ESCALATE",
    "ONTOLOGY_AXIOM_FIRST",
    "DEFER_AND_CONTINUE_WITH_ASSUMPTION",
]

StepExecutionStatus = Literal[
    "PENDING",
    "WAITING_FOR_HUMAN_ANCHOR",
    "EXECUTING_AGENT",
    "WAITING_FOR_HUMAN_ARBITRATION",
    "EVALUATING_GATES",
    "WAITING_FOR_HUMAN_GATE",
    "COMMITTED",
    "CHALLENGED_REWIND",
    "FAILED",
]

# Canonical alias referenced in AD-19 / Story 3.2a
StepExecutionState = StepExecutionStatus

MemlogMarkerType = Literal[
    "REASONING",
    "ASSUMPTION",
    "BUG_CODE_SUSPECTED",
    "DOC_OBSOLETE_SUSPECTED",
    "FEEDBACK_RETRY",
    "SUB_WORKFLOW_OUTPUT",
]

SnapshotBranchStatus = Literal["ACTIVE", "SUPERSEDED"]

OutboxEventStatus = Literal["PENDING", "PUBLISHED", "FAILED"]

SandboxExecutionTier = Literal["TIER_1_WASM", "TIER_2_CONTAINER"]

ExecutionMode = Literal["COACHING", "FAST_PATH"]

__all__ = [
    "DEFAULT_LOCALE",
    "ExecutionMode",
    "MemlogMarkerType",
    "OutboxEventStatus",
    "SandboxExecutionTier",
    "SnapshotBranchStatus",
    "StepExecutionState",
    "StepExecutionStatus",
    "SupportedLocale",
    "TieBreakPolicy",
    "WorkflowCriticality",
    "WorkflowExecutionRegime",
    "WorkflowStepType",
]
