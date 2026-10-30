"""Presence Lock (`lock:step:{step_id}` NX EX 900) & SSE Broadcast Ports (`Story 5.1`, `AD-4`).

Extracted to keep `notifications_and_claims.py` and `presence_and_sse.py` each under `300` lines.
"""

from __future__ import annotations

import threading
import time
from collections.abc import Mapping
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from typing import Any, Literal, Protocol, runtime_checkable

from orcia_kernel.ids import new_uuid7_str

NotificationType = Literal[
    "HUMAN_GATE",
    "HUMAN_ARBITRATION",
    "HUMAN_ANCHOR",
    "UPSTREAM_CHALLENGE",
    "PERMISSION_ALERT",
    "STALE_WARNING",
    "AUTONOMOUS_ESCALATION",
    "POST_HOC_AUDIT_SAMPLE",
]
NotificationScopeKind = Literal["PERSONAL", "TEAM"]
NotificationStatus = Literal["OPEN", "CLAIMED", "RESOLVED"]
ClaimPresenceState = Literal["UNCLAIMED", "CLAIMED_BY_ME", "CLAIMED_BY_PEER"]

DEFAULT_CLAIM_TTL_SECONDS = 900  # 15 minutes (`AD-4`, `UX-DR9`)


@dataclass(frozen=True, slots=True)
class StepPresenceLockRecord:
    """Atomic Redis/in-memory presence lock (`lock:step:{step_execution_id}`, `AD-4`)."""

    lock_key: str
    step_execution_id: str
    holder_user_id: str
    holder_display_name: str
    acquired_at_iso: str
    expires_at_iso: str
    ttl_seconds: int = DEFAULT_CLAIM_TTL_SECONDS


@runtime_checkable
class StepPresenceLockPort(Protocol):
    """Hexagonal port for `SET lock:step:{step_execution_id} {user_id} NX EX 900` (`AD-4`)."""

    def try_acquire(
        self,
        *,
        step_execution_id: str,
        user_id: str,
        display_name: str,
        ttl_seconds: int = DEFAULT_CLAIM_TTL_SECONDS,
        force: bool = False,
        now_utc: datetime | None = None,
    ) -> tuple[bool, StepPresenceLockRecord]:
        """Attempt atomic lock acquisition; return `(acquired, current_record)`."""
        ...

    def get_lock(
        self, step_execution_id: str, *, now_utc: datetime | None = None
    ) -> StepPresenceLockRecord | None:
        """Return active non-expired lock record for `step_execution_id` or `None`."""
        ...

    def release(self, *, step_execution_id: str, user_id: str, force: bool = False) -> bool:
        """Release the lock if held by `user_id` (or unconditionally when `force=True`)."""
        ...


class InMemoryStepPresenceLockAdapter(StepPresenceLockPort):
    """Thread-safe atomic `SET NX EX 900` adapter for unit tests."""

    def __init__(self) -> None:
        self._mutex = threading.Lock()
        self._locks: dict[str, StepPresenceLockRecord] = {}

    @staticmethod
    def canonical_key(step_execution_id: str) -> str:
        return f"lock:step:{step_execution_id.strip()}"

    def try_acquire(
        self,
        *,
        step_execution_id: str,
        user_id: str,
        display_name: str,
        ttl_seconds: int = DEFAULT_CLAIM_TTL_SECONDS,
        force: bool = False,
        now_utc: datetime | None = None,
    ) -> tuple[bool, StepPresenceLockRecord]:
        now = now_utc or datetime.now(UTC)
        key = self.canonical_key(step_execution_id)
        eff_ttl = max(1, int(ttl_seconds))
        with self._mutex:
            existing = self._locks.get(key)
            if existing is not None:
                exp_dt = datetime.fromisoformat(existing.expires_at_iso)
                if exp_dt > now and not force and existing.holder_user_id != user_id:
                    return False, existing
            record = StepPresenceLockRecord(
                lock_key=key,
                step_execution_id=step_execution_id.strip(),
                holder_user_id=user_id,
                holder_display_name=display_name,
                acquired_at_iso=now.isoformat(),
                expires_at_iso=(now + timedelta(seconds=eff_ttl)).isoformat(),
                ttl_seconds=eff_ttl,
            )
            self._locks[key] = record
            return True, record

    def get_lock(
        self, step_execution_id: str, *, now_utc: datetime | None = None
    ) -> StepPresenceLockRecord | None:
        now = now_utc or datetime.now(UTC)
        key = self.canonical_key(step_execution_id)
        with self._mutex:
            existing = self._locks.get(key)
            if existing is None:
                return None
            if datetime.fromisoformat(existing.expires_at_iso) <= now:
                self._locks.pop(key, None)
                return None
            return existing

    def release(self, *, step_execution_id: str, user_id: str, force: bool = False) -> bool:
        key = self.canonical_key(step_execution_id)
        with self._mutex:
            existing = self._locks.get(key)
            if existing is None:
                return False
            if not force and existing.holder_user_id != user_id:
                return False
            self._locks.pop(key, None)
            return True


@dataclass(frozen=True, slots=True)
class SseEventEnvelope:
    """Immutable SSE message published to `channel:workspace:{ws_id}` (`AD-4`, `< 500 ms`)."""

    event_id: str
    event_name: str
    channel: str
    workspace_id: str
    run_id: str
    step_execution_id: str
    payload: dict[str, Any]
    published_at_iso: str
    dispatch_latency_ms: float


@runtime_checkable
class SseBroadcastPort(Protocol):
    """Port for Redis Pub/Sub & FastAPI `/api/v1/events/stream` SSE broadcasting (`AD-4`)."""

    def publish(
        self,
        *,
        workspace_id: str,
        event_name: str,
        run_id: str,
        step_execution_id: str,
        payload: dict[str, Any],
    ) -> SseEventEnvelope:
        """Broadcast an SSE event on `channel:workspace:{workspace_id}` in `< 500 ms`."""
        ...

    def list_recent_events(self, workspace_id: str | None = None) -> tuple[SseEventEnvelope, ...]:
        """Return recent SSE events for inspection and streaming."""
        ...


class InMemorySseBrokerAdapter(SseBroadcastPort):
    """Thread-safe SSE Pub/Sub broker recording sub-500ms dispatch latency (`NFR-PERF-2`)."""

    def __init__(self) -> None:
        self._mutex = threading.Lock()
        self._events: list[SseEventEnvelope] = []

    def publish(
        self,
        *,
        workspace_id: str,
        event_name: str,
        run_id: str,
        step_execution_id: str,
        payload: dict[str, Any],
    ) -> SseEventEnvelope:
        t0 = time.perf_counter()
        channel = f"channel:workspace:{workspace_id}"
        now_iso = datetime.now(UTC).isoformat()
        latency_ms = round(max(0.5, (time.perf_counter() - t0) * 1000.0), 3)
        envelope = SseEventEnvelope(
            event_id=new_uuid7_str(),
            event_name=event_name,
            channel=channel,
            workspace_id=workspace_id,
            run_id=run_id,
            step_execution_id=step_execution_id,
            payload=dict(payload),
            published_at_iso=now_iso,
            dispatch_latency_ms=latency_ms,
        )
        with self._mutex:
            self._events.append(envelope)
        return envelope

    def list_recent_events(self, workspace_id: str | None = None) -> tuple[SseEventEnvelope, ...]:
        with self._mutex:
            if workspace_id is None:
                return tuple(self._events)
            return tuple(e for e in self._events if e.workspace_id == workspace_id)


@dataclass(frozen=True, slots=True)
class TaskNotificationEntity:
    """Immutable unified notification row (`task_notifications`, `FR-2`, `UX-DR9`)."""

    id: str
    workspace_id: str
    target_team_id: str | None
    target_user_id: str | None
    run_id: str
    step_execution_id: str
    step_key: str
    notification_type: NotificationType
    scope_kind: NotificationScopeKind
    title: str
    summary: str
    status: NotificationStatus = "OPEN"
    claimed_by_user_id: str | None = None
    claimed_by_display_name: str | None = None
    claimed_at: str | None = None
    lock_expires_at: str | None = None
    source_event_id: str | None = None
    created_at: str = field(default_factory=lambda: datetime.now(UTC).isoformat())

    def resolve_presence_state(
        self, viewer_user_id: str, *, now_utc: datetime | None = None
    ) -> ClaimPresenceState:
        """Compute `UNCLAIMED | CLAIMED_BY_ME | CLAIMED_BY_PEER` for `viewer_user_id` (`UX-DR9`)."""
        if not self.claimed_by_user_id or self.status != "CLAIMED":
            return "UNCLAIMED"
        if self.lock_expires_at:
            now = now_utc or datetime.now(UTC)
            if datetime.fromisoformat(self.lock_expires_at) <= now:
                return "UNCLAIMED"
        if self.claimed_by_user_id == viewer_user_id:
            return "CLAIMED_BY_ME"
        return "CLAIMED_BY_PEER"

    def can_force_unclaim(self, *, now_utc: datetime | None = None) -> bool:
        """Return True if the 15-minute (`900 s`) inactivity window has elapsed (`UX-DR9`)."""
        if not self.lock_expires_at:
            return False
        now = now_utc or datetime.now(UTC)
        return datetime.fromisoformat(self.lock_expires_at) <= now


@dataclass(frozen=True, slots=True)
class ClaimActionOutcome:
    """Result of claiming or releasing a notification / step execution (`AD-4`, `NFR-PERF-2`)."""

    notification: TaskNotificationEntity
    lock_record: StepPresenceLockRecord | None
    sse_event: SseEventEnvelope
    viewer_presence_state: ClaimPresenceState
    peer_presence_state: ClaimPresenceState


def translate_outbox_event_spec(
    event_type: str,
    payload: Mapping[str, object],
) -> tuple[NotificationType, str, str] | None:
    """Translate a domain outbox event into `(notification_type, title, summary)` if actionable."""
    step_key = str(payload.get("step_key") or "step-1")
    if event_type == "HumanArbitrationRequested":
        opts = payload.get("options_count", 2)
        return (
            "HUMAN_ARBITRATION",
            f"⚖️ Arbitrage Humain requis sur '{step_key}'",
            f"L'étape '{step_key}' attend un arbitrage humain entre {opts} options.",
        )
    if event_type == "GateEvaluated" and not bool(payload.get("passed", True)):
        gate_type = str(payload.get("gate_type", "AGENTIC"))
        score = payload.get("score", 0.0)
        return (
            "HUMAN_GATE",
            f"🛡️ Escalade Gate ({gate_type}) sur '{step_key}'",
            f"La Gate {gate_type} a signalé un écart (score={score}).",
        )
    if event_type == "StepCompleted":
        st = str(payload.get("step_status", ""))
        if st in (
            "WAITING_FOR_HUMAN_GATE",
            "WAITING_FOR_HUMAN_ARBITRATION",
            "WAITING_FOR_HUMAN_ANCHOR",
        ):
            ntype: NotificationType = (
                "HUMAN_ANCHOR"
                if st == "WAITING_FOR_HUMAN_ANCHOR"
                else "HUMAN_ARBITRATION"
                if st == "WAITING_FOR_HUMAN_ARBITRATION"
                else "HUMAN_GATE"
            )
            return (
                ntype,
                f"Action humaine requise ({ntype}) sur '{step_key}'",
                f"L'étape '{step_key}' est en pause ({st}).",
            )
    return None


__all__ = [
    "ClaimActionOutcome",
    "ClaimPresenceState",
    "DEFAULT_CLAIM_TTL_SECONDS",
    "InMemorySseBrokerAdapter",
    "InMemoryStepPresenceLockAdapter",
    "NotificationScopeKind",
    "NotificationStatus",
    "NotificationType",
    "SseBroadcastPort",
    "SseEventEnvelope",
    "StepPresenceLockPort",
    "StepPresenceLockRecord",
    "TaskNotificationEntity",
    "translate_outbox_event_spec",
]
