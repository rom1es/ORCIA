"""SQLAlchemy 2.1 Asyncio OpenTelemetry span & W3C `trace_id` instrumentation (`ARCH-P9`)."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_core.observability.logging import get_current_trace_context


@dataclass(frozen=True, slots=True)
class SqlQueryTelemetrySpan:
    """Recorded OpenTelemetry SQL query execution span correlated by `trace_id`."""

    trace_id: str
    span_id: str
    statement_prefix: str
    duration_ms: float


class SqlAlchemyOtelInstrumenter:
    """Attaches SQLAlchemy cursor hooks to capture W3C `trace_id`-correlated SQL spans."""

    def __init__(self, max_recorded_spans: int = 500) -> None:
        self._max_spans = max_recorded_spans
        self._spans: list[SqlQueryTelemetrySpan] = []

    @property
    def recorded_spans(self) -> tuple[SqlQueryTelemetrySpan, ...]:
        return tuple(self._spans)

    def clear(self) -> None:
        self._spans.clear()

    def instrument_engine(self, engine: AsyncEngine | sa.Engine) -> None:
        sync_engine = engine.sync_engine if isinstance(engine, AsyncEngine) else engine

        @sa.event.listens_for(sync_engine, "before_cursor_execute")
        def _before_cursor_execute(
            conn: Any,
            _cursor: Any,
            _statement: str,
            _parameters: Any,
            _context: Any,
            _executemany: bool,
        ) -> None:
            conn.info.setdefault("orcia_otel_q_start", []).append(time.perf_counter())

        @sa.event.listens_for(sync_engine, "after_cursor_execute")
        def _after_cursor_execute(
            conn: Any,
            _cursor: Any,
            statement: str,
            _parameters: Any,
            _context: Any,
            _executemany: bool,
        ) -> None:
            starts: list[float] = conn.info.get("orcia_otel_q_start", [])
            start_t = starts.pop() if starts else time.perf_counter()
            duration_ms = round((time.perf_counter() - start_t) * 1000.0, 3)
            ctx = get_current_trace_context()
            span = SqlQueryTelemetrySpan(
                trace_id=ctx.trace_id,
                span_id=ctx.span_id,
                statement_prefix=statement.strip()[:80],
                duration_ms=duration_ms,
            )
            if len(self._spans) >= self._max_spans:
                self._spans.pop(0)
            self._spans.append(span)
