"""Assistant Harness Lifecycle Domain Events for the Transactional Outbox (`Story 26.4a`, `H-22`).

Pure kernel module — zero framework or business domain dependencies.
"""

from __future__ import annotations

from dataclasses import dataclass

from orcia_core.kernel._events_base import DomainEvent
from orcia_core.kernel.ids import new_uuid7_str


@dataclass(frozen=True, slots=True)
class AssistantTurnStarted(DomainEvent):
    """Published when an assistant turn enters execution (`Story 26.4a`)."""

    user_id: str = ""
    speed_mode: str = "SPEED_1_FAST"

    @classmethod
    def create(
        cls,
        *,
        turn_id: str,
        workspace_id: str | None,
        user_id: str,
        speed_mode: str = "SPEED_1_FAST",
        trace_id: str = "00000000000000000000000000000000",
    ) -> AssistantTurnStarted:
        return cls(
            event_id=new_uuid7_str(),
            event_type="AssistantTurnStarted",
            aggregate_type="assistant_turn",
            aggregate_id=turn_id,
            run_id=None,
            workspace_id=workspace_id,
            payload={
                "turn_id": turn_id,
                "user_id": user_id,
                "speed_mode": speed_mode,
            },
            trace_id=trace_id,
            user_id=user_id,
            speed_mode=speed_mode,
        )


@dataclass(frozen=True, slots=True)
class AssistantTurnCompleted(DomainEvent):
    """Published when an assistant turn completes streaming (`Story 26.4a`)."""

    user_id: str = ""
    speed_mode: str = "SPEED_1_FAST"
    input_tokens: int = 0
    output_tokens: int = 0

    @classmethod
    def create(
        cls,
        *,
        turn_id: str,
        workspace_id: str | None,
        user_id: str,
        speed_mode: str = "SPEED_1_FAST",
        input_tokens: int = 0,
        output_tokens: int = 0,
        trace_id: str = "00000000000000000000000000000000",
    ) -> AssistantTurnCompleted:
        return cls(
            event_id=new_uuid7_str(),
            event_type="AssistantTurnCompleted",
            aggregate_type="assistant_turn",
            aggregate_id=turn_id,
            run_id=None,
            workspace_id=workspace_id,
            payload={
                "turn_id": turn_id,
                "user_id": user_id,
                "speed_mode": speed_mode,
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
            },
            trace_id=trace_id,
            user_id=user_id,
            speed_mode=speed_mode,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
        )


@dataclass(frozen=True, slots=True)
class AssistantTurnStopped(DomainEvent):
    """Published when an assistant turn is cancelled by a user stop request (`Story 26.4a`)."""

    user_id: str = ""
    stopped_by_user_id: str = ""

    @classmethod
    def create(
        cls,
        *,
        turn_id: str,
        workspace_id: str | None,
        user_id: str,
        stopped_by_user_id: str,
        trace_id: str = "00000000000000000000000000000000",
    ) -> AssistantTurnStopped:
        return cls(
            event_id=new_uuid7_str(),
            event_type="AssistantTurnStopped",
            aggregate_type="assistant_turn",
            aggregate_id=turn_id,
            run_id=None,
            workspace_id=workspace_id,
            payload={
                "turn_id": turn_id,
                "user_id": user_id,
                "stopped_by_user_id": stopped_by_user_id,
            },
            trace_id=trace_id,
            user_id=user_id,
            stopped_by_user_id=stopped_by_user_id,
        )


@dataclass(frozen=True, slots=True)
class AssistantTurnFailed(DomainEvent):
    """Published when an assistant turn fails during execution (`Story 26.4a`)."""

    user_id: str = ""
    error_code: str = "ERR_INTERNAL_SERVER_ERROR"

    @classmethod
    def create(
        cls,
        *,
        turn_id: str,
        workspace_id: str | None,
        user_id: str,
        error_code: str,
        trace_id: str = "00000000000000000000000000000000",
    ) -> AssistantTurnFailed:
        return cls(
            event_id=new_uuid7_str(),
            event_type="AssistantTurnFailed",
            aggregate_type="assistant_turn",
            aggregate_id=turn_id,
            run_id=None,
            workspace_id=workspace_id,
            payload={
                "turn_id": turn_id,
                "user_id": user_id,
                "error_code": error_code,
            },
            trace_id=trace_id,
            user_id=user_id,
            error_code=error_code,
        )


__all__ = [
    "AssistantTurnCompleted",
    "AssistantTurnFailed",
    "AssistantTurnStarted",
    "AssistantTurnStopped",
]
