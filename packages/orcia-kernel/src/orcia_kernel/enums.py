"""Universal cross-domain enumerations, Literal types & marker registry (`AD-19`, `AD-20`).

Shared by `blackboard`, `orchestration`, `gates`, `permissions` and `audit_finops` without
creating circular dependencies between sibling domains or leaking SDLC vocabulary into Kernel.
"""

from __future__ import annotations

import re
import threading
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

CoreMemlogMarkerType = Literal[
    "REASONING",
    "ASSUMPTION",
    "FEEDBACK_RETRY",
    "SUB_WORKFLOW_OUTPUT",
    "core.reasoning",
    "core.assumption",
    "core.feedback_retry",
    "core.sub_workflow_output",
]

# Open namespaced string (`<namespace>.<marker>` or registered core/pack alias, `AD-20`, `AC-E2`)
MemlogMarkerType = str

NAMESPACED_MARKER_RE = re.compile(r"^[a-z][a-z0-9_]*\.[a-z][a-z0-9_]*$")

_MARKER_LOCK = threading.Lock()
_REGISTERED_MEMLOG_MARKERS: set[str] = {
    "REASONING",
    "ASSUMPTION",
    "FEEDBACK_RETRY",
    "SUB_WORKFLOW_OUTPUT",
    "core.reasoning",
    "core.assumption",
    "core.feedback_retry",
    "core.sub_workflow_output",
    "core.divergence_suspected",
}
_MEMLOG_MARKER_ALIASES: dict[str, str] = {
    "REASONING": "core.reasoning",
    "ASSUMPTION": "core.assumption",
    "FEEDBACK_RETRY": "core.feedback_retry",
    "SUB_WORKFLOW_OUTPUT": "core.sub_workflow_output",
}


def register_memlog_marker(canonical_marker: str, *, legacy_aliases: tuple[str, ...] = ()) -> None:
    """Register a namespaced `<namespace>.<marker>` and optional legacy aliases (`AD-20`)."""
    norm = canonical_marker.strip()
    if not NAMESPACED_MARKER_RE.match(norm):
        raise ValueError(
            f"Memlog marker {canonical_marker!r} must match '<namespace>.<marker>' format."
        )
    with _MARKER_LOCK:
        _REGISTERED_MEMLOG_MARKERS.add(norm)
        for alias in legacy_aliases:
            clean_alias = alias.strip()
            if clean_alias:
                _REGISTERED_MEMLOG_MARKERS.add(clean_alias)
                _MEMLOG_MARKER_ALIASES[clean_alias] = norm


def is_valid_memlog_marker(marker: str) -> bool:
    """Return True if `marker` is registered or matches `<namespace>.<marker>`."""
    cleaned = marker.strip()
    with _MARKER_LOCK:
        if cleaned in _REGISTERED_MEMLOG_MARKERS:
            return True
    return bool(NAMESPACED_MARKER_RE.match(cleaned))


def normalize_memlog_marker(marker: str) -> str:
    """Return canonical `<namespace>.<marker>` if `marker` is a registered alias, else `marker`."""
    cleaned = marker.strip()
    with _MARKER_LOCK:
        return _MEMLOG_MARKER_ALIASES.get(cleaned, cleaned)


def list_registered_memlog_markers() -> frozenset[str]:
    """Return immutable snapshot of registered memlog markers and aliases."""
    with _MARKER_LOCK:
        return frozenset(_REGISTERED_MEMLOG_MARKERS)


SnapshotBranchStatus = Literal["ACTIVE", "SUPERSEDED"]

OutboxEventStatus = Literal["PENDING", "PUBLISHED", "FAILED"]

SandboxExecutionTier = Literal["TIER_1_WASM", "TIER_2_CONTAINER"]

ExecutionMode = Literal["COACHING", "FAST_PATH"]

__all__ = [
    "CoreMemlogMarkerType",
    "DEFAULT_LOCALE",
    "ExecutionMode",
    "MemlogMarkerType",
    "NAMESPACED_MARKER_RE",
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
    "is_valid_memlog_marker",
    "list_registered_memlog_markers",
    "normalize_memlog_marker",
    "register_memlog_marker",
]
