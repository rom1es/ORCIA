"""Hexagonal Ports for Turn Registry, Streams & Rate Limiting (`AD-25`).

Pure Python Protocols — zero external framework or SDK imports.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Literal, Protocol, runtime_checkable

AssistantTurnStatus = Literal["IDLE", "RUNNING", "COMPLETED", "STOPPED", "ERROR"]


@dataclass(frozen=True, slots=True)
class AssistantTurnRecord:
    """Authoritative shared state for an assistant turn indexed by `(workspace, user, turn_id)`."""

    turn_id: str
    workspace_id: str
    user_id: str
    status: AssistantTurnStatus
    user_prompt: str
    assembled_system_prompt: str
    thinking_text: str = ""
    streamed_text: str = ""
    started_at_ms: float = 0.0
    elapsed_ms: float = 0.0
    error_message: str | None = None
    error_code: str | None = None
    trace_id: str = ""
    speed_mode: str = "SPEED_1_FAST"
    model_id: str = "assistant-router"
    inference_tier: str | None = None
    effort: str = "balanced"
    input_tokens: int = 0
    output_tokens: int = 0
    usage_source: str = "estimated"
    stopped_by_user_id: str | None = None
    thread_id: str | None = None
    parent_turn_id: str | None = None
    citation_map: dict[str, Any] = field(default_factory=dict)
    prompt_assembly_latency_ms: float = 0.0


@dataclass(frozen=True, slots=True)
class AssistantTurnStreamEvent:
    """Single ordered SSE v2 event persisted in a bounded Redis Stream."""

    cursor: str
    seq: int
    event: str
    data: dict[str, Any] = field(default_factory=dict)


@runtime_checkable
class AssistantTurnRegistryPort(Protocol):
    """Port for `(workspace_id, user_id, turn_id)` turn metadata, liveness, and stop signals."""

    async def register_turn(self, record: AssistantTurnRecord, *, ttl_seconds: int = 3600) -> None:
        """Persist a new turn record and index it under `(workspace_id, user_id, turn_id)`."""
        ...

    async def update_turn(self, record: AssistantTurnRecord, *, ttl_seconds: int = 1800) -> None:
        """Update an existing turn record without overwriting concurrent tabs."""
        ...

    async def get_turn(
        self, workspace_id: str, user_id: str, turn_id: str
    ) -> AssistantTurnRecord | None:
        """Fetch a turn record verifying `(workspace_id, user_id)` ownership."""
        ...

    async def get_turn_by_id(self, turn_id: str) -> AssistantTurnRecord | None:
        """Fetch a turn record by `turn_id` for cross-worker stream/stop authorization."""
        ...

    async def list_active_turns(
        self, workspace_id: str, user_id: str
    ) -> tuple[AssistantTurnRecord, ...]:
        """List active or recent turns for `(workspace_id, user_id)` ordered newest-first."""
        ...

    async def get_latest_turn(self, workspace_id: str, user_id: str) -> AssistantTurnRecord | None:
        """Return the most recent turn for `(workspace_id, user_id)`."""
        ...

    async def refresh_liveness(self, turn_id: str, *, ttl_seconds: int = 15) -> None:
        """Create or refresh the task liveness key with TTL."""
        ...

    async def is_live(self, turn_id: str) -> bool:
        """Return True when the active worker liveness key still exists."""
        ...

    async def clear_liveness(self, turn_id: str) -> None:
        """Remove the liveness key once the turn exits cleanly."""
        ...

    async def request_stop(
        self, turn_id: str, *, stopped_by_user_id: str, ttl_seconds: int = 300
    ) -> None:
        """Publish a cross-worker stop signal for `turn_id`."""
        ...

    async def is_stop_requested(self, turn_id: str) -> str | None:
        """Return `stopped_by_user_id` if a stop signal was requested for `turn_id`."""
        ...


@runtime_checkable
class AssistantTurnStreamPort(Protocol):
    """Port for bounded cursor-reattachable Redis Streams event buffering."""

    async def append_event(
        self,
        turn_id: str,
        *,
        event: str,
        data: dict[str, Any],
        maxlen: int = 1000,
        ttl_seconds: int | None = None,
    ) -> str:
        """Append an event to the turn stream and return its monotonic cursor ID."""
        ...

    async def read_events(
        self,
        turn_id: str,
        *,
        after_cursor: str = "0-0",
        block_ms: int = 0,
        count: int = 200,
    ) -> tuple[AssistantTurnStreamEvent, ...]:
        """Read stream events strictly after `after_cursor` without duplicates."""
        ...

    async def set_stream_ttl(self, turn_id: str, ttl_seconds: int = 1800) -> None:
        """Apply post-completion TTL to the turn's event stream."""
        ...


@runtime_checkable
class AssistantRateLimiterPort(Protocol):
    """Port for Redis sliding-window rate limiting and per-user concurrency semaphores."""

    async def check_and_record_turn_rate(
        self,
        user_id: str,
        workspace_id: str,
        *,
        window_seconds: int,
        max_requests: int,
    ) -> tuple[bool, int]:
        """Return `(allowed, retry_after_seconds)` for the `(workspace_id, user_id)` window."""
        ...

    async def acquire_concurrency_slot(
        self,
        user_id: str,
        *,
        limit: int,
        ttl_seconds: int = 180,
    ) -> str | None:
        """Acquire a per-user concurrency slot returning a lease token or `None` when full."""
        ...

    async def release_concurrency_slot(self, user_id: str, lease_token: str) -> None:
        """Release a previously acquired per-user concurrency slot."""
        ...


@runtime_checkable
class ThreadTurnLockPort(Protocol):
    """Port for distributed thread turn mutex (`SET lock:thread:<thread_id> NX EX`, `AD-4`)."""

    async def acquire_async(
        self,
        *,
        thread_id: str,
        user_id: str,
        ttl_seconds: int = 60,
    ) -> tuple[str, str]:
        """Acquire atomic thread turn lock returning `(lock_key, lock_token)` or raising."""
        ...

    async def release_async(
        self,
        *,
        thread_id: str,
        user_id: str,
        token: str | None = None,
    ) -> bool:
        """Atomically release thread turn lock only if held by `(user_id, token)`."""
        ...


__all__ = [
    "AssistantRateLimiterPort",
    "AssistantTurnRecord",
    "AssistantTurnRegistryPort",
    "AssistantTurnStatus",
    "AssistantTurnStreamEvent",
    "AssistantTurnStreamPort",
    "ThreadTurnLockPort",
]
