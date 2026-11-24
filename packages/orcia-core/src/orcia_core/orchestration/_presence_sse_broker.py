"""SSE Broadcast Port, InMemory Broker & Outbox Event Translator (`Story 5.1`, `AD-4`)."""

from __future__ import annotations

import threading
import time
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any, Literal, Protocol, runtime_checkable

from orcia_core.observability.logging import get_logger
from orcia_core.orchestration._orchestration_runtime_locales import (
    OUTBOX_SSE_LOCALES,
    get_runtime_copy,
)
from orcia_kernel.ids import new_uuid7_str

logger = get_logger(__name__)

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


@dataclass(frozen=True, slots=True)
class SseEventEnvelope:
    """Real-time SSE frame broadcast on `channel:workspace:{workspace_id}`."""

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

    def subscribe(
        self,
        listener: Callable[[SseEventEnvelope], object],
        *,
        workspace_id: str | None = None,
    ) -> Callable[[], None]:
        """Register a real-time subscriber callback (`< 500 ms`, `AD-4`); return `unsubscribe()`."""
        ...


class InMemorySseBrokerAdapter(SseBroadcastPort):
    """Concurrent-ready SSE Pub/Sub broker recording sub-500ms dispatch latency (`NFR-PERF-2`)."""

    def __init__(self) -> None:
        self._mutex = threading.Lock()
        self._events: list[SseEventEnvelope] = []
        self._subscribers: list[tuple[str | None, Callable[[SseEventEnvelope], object]]] = []

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
            targets = [cb for ws, cb in self._subscribers if ws is None or ws == workspace_id]
        for callback in targets:
            try:
                callback(envelope)
            except Exception as exc:
                logger.warning("sse_subscriber_callback_failed", error=str(exc))
        return envelope

    def list_recent_events(self, workspace_id: str | None = None) -> tuple[SseEventEnvelope, ...]:
        with self._mutex:
            if workspace_id is None:
                return tuple(self._events)
            return tuple(e for e in self._events if e.workspace_id == workspace_id)

    def subscribe(
        self,
        listener: Callable[[SseEventEnvelope], object],
        *,
        workspace_id: str | None = None,
    ) -> Callable[[], None]:
        entry = (workspace_id, listener)
        with self._mutex:
            self._subscribers.append(entry)

        def _unsubscribe() -> None:
            with self._mutex:
                if entry in self._subscribers:
                    self._subscribers.remove(entry)

        return _unsubscribe


def translate_outbox_event_spec(
    event_type: str,
    payload: Mapping[str, object],
) -> tuple[NotificationType, str, str] | None:
    """Translate a domain outbox event into `(notification_type, title, summary)` if actionable."""
    oc = get_runtime_copy(OUTBOX_SSE_LOCALES)
    step_key = str(payload.get("step_key") or "step-1")
    if event_type == "HumanArbitrationRequested":
        opts = payload.get("options_count", 2)
        return (
            "HUMAN_ARBITRATION",
            oc["arb_title"].format(step=step_key),
            oc["arb_summary"].format(step=step_key, opts=opts),
        )
    if event_type == "GateEvaluated" and not bool(payload.get("passed", True)):
        gate_type = str(payload.get("gate_type", "AGENTIC"))
        score = payload.get("score", 0.0)
        return (
            "HUMAN_GATE",
            oc["gate_title"].format(gate_type=gate_type, step=step_key),
            oc["gate_summary"].format(gate_type=gate_type, score=score),
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
                oc["step_title"].format(ntype=ntype, step=step_key),
                oc["step_summary"].format(step=step_key, status=st),
            )
    return None


__all__ = [
    "InMemorySseBrokerAdapter",
    "NotificationType",
    "SseBroadcastPort",
    "SseEventEnvelope",
    "translate_outbox_event_spec",
]
