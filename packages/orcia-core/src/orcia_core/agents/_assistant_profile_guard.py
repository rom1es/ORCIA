"""Structural `ExecutionProfile` isolation helpers (`Story 26.6b`, `AD-25`, `H-29`).

Ensures `ReflexiveWriteGatePort` / `ConnectorReflexiveWriteGateAdapter` cannot be bound,
reached, or invoked under `execution_profile == 'ASSISTANT'`.
"""

from __future__ import annotations

from orcia_core.agents.errors import PolicyDeniedError
from orcia_core.agents.reflexive_schemas import ExecutionProfile, ReflexiveSessionSnapshot
from orcia_core.ports.reflexive_runtime_ports import ReflexiveWriteGatePort


def assert_assistant_profile_write_gate_unreachable(
    execution_profile: ExecutionProfile,
    write_gate: ReflexiveWriteGatePort | None,
) -> None:
    """Reject binding a write gate when runtime profile is `ASSISTANT`."""
    if execution_profile == "ASSISTANT" and write_gate is not None:
        raise PolicyDeniedError(
            detail_override=(
                "ERR_ASSISTANT_WRITE_GATE_FORBIDDEN: Write gate adapter cannot be bound under "
                "execution_profile='ASSISTANT'."
            )
        )


def assert_profile_allows_write_action(execution_profile: ExecutionProfile) -> None:
    """Reject direct write preview/resume transitions when profile is `ASSISTANT`."""
    if execution_profile == "ASSISTANT":
        raise PolicyDeniedError(
            detail_override=(
                "ERR_ASSISTANT_WRITE_GATE_FORBIDDEN: External write previews are structurally "
                "forbidden under execution_profile='ASSISTANT'. Use CONTINUE_IN_PROCESS."
            )
        )


def resolve_effective_write_gate(
    runtime_profile: ExecutionProfile,
    snapshot: ReflexiveSessionSnapshot,
    write_gate: ReflexiveWriteGatePort | None,
) -> ReflexiveWriteGatePort | None:
    """Return `None` and reject write gate access whenever profile is `ASSISTANT`."""
    assert_profile_allows_write_action(runtime_profile)
    assert_profile_allows_write_action(snapshot.execution_profile)
    return write_gate


__all__ = [
    "assert_assistant_profile_write_gate_unreachable",
    "assert_profile_allows_write_action",
    "resolve_effective_write_gate",
]
