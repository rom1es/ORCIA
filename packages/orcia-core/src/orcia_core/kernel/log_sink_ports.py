"""Pure hexagonal `LogSinkQueryPort` contract, models, and `NoopLogSinkAdapter` (`AD-23`).

Zero external SDK or framework imports (`AD-19` Contract 3). Shared across `orcia_core.ports`
and `orcia_core.observability`.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Protocol, runtime_checkable

MAX_LOG_QUERY_LIMIT: int = 200


@dataclass(frozen=True, slots=True)
class LogQuery:
    """Bounded read query against the configured ORCIA log sink (`AD-23`)."""

    service: str | None = None
    level: str | None = None
    workspace_id: str | None = None
    run_id: str | None = None
    search_text: str | None = None
    fingerprint: str | None = None
    since_seconds: int | None = None
    limit: int = 50

    def __post_init__(self) -> None:
        if self.limit < 1:
            raise ValueError("LogQuery.limit must be >= 1")
        if self.limit > MAX_LOG_QUERY_LIMIT:
            object.__setattr__(self, "limit", MAX_LOG_QUERY_LIMIT)
        if self.since_seconds is not None and self.since_seconds < 0:
            raise ValueError("LogQuery.since_seconds must be >= 0")


@dataclass(frozen=True, slots=True)
class LogEntry:
    """Normalized ECS log entry returned by `LogSinkQueryPort` (`AD-23`)."""

    timestamp: str
    level: str
    service: str
    logger: str
    message: str
    trace_id: str | None = None
    span_id: str | None = None
    exception: str | None = None
    fingerprint: str | None = None
    ctx: dict[str, Any] = field(default_factory=dict)
    workspace_id: str | None = None
    run_id: str | None = None


@runtime_checkable
class LogSinkQueryPort(Protocol):
    """Hexagonal read port decoupling ORCIA from Elasticsearch, OpenSearch, or Loki (`AD-23`)."""

    async def query_logs(self, query: LogQuery) -> list[LogEntry]:
        """Query structured log entries matching `query` filters ordered newest-first."""
        ...

    async def count_errors(
        self,
        fingerprint: str,
        window_seconds: int,
        *,
        service: str | None = None,
    ) -> int:
        """Count error/critical events matching `fingerprint` over the trailing `window_seconds`."""
        ...

    async def healthcheck(self) -> bool:
        """Return `True` when the configured log sink backend is reachable and healthy."""
        ...


class NoopLogSinkAdapter:
    """Null-object adapter active when `LOG_SINK_BACKEND=none` (`AD-23`)."""

    async def query_logs(self, query: LogQuery) -> list[LogEntry]:
        del query
        return []

    async def count_errors(
        self,
        fingerprint: str,
        window_seconds: int,
        *,
        service: str | None = None,
    ) -> int:
        del fingerprint, window_seconds, service
        return 0

    async def healthcheck(self) -> bool:
        return True


__all__ = [
    "MAX_LOG_QUERY_LIMIT",
    "LogEntry",
    "LogQuery",
    "LogSinkQueryPort",
    "NoopLogSinkAdapter",
]
