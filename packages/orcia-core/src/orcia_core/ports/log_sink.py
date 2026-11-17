"""Hexagonal `LogSinkQueryPort` interface and models (`AD-19`, `AD-23`, `Story 7.0b`).

Strictly pure Python Protocol and dataclasses: zero framework, SDK, or HTTP client imports.
"""

from __future__ import annotations

from orcia_core.kernel.log_sink_ports import (
    MAX_LOG_QUERY_LIMIT,
    LogEntry,
    LogQuery,
    LogSinkQueryPort,
    NoopLogSinkAdapter,
)

__all__ = [
    "MAX_LOG_QUERY_LIMIT",
    "LogEntry",
    "LogQuery",
    "LogSinkQueryPort",
    "NoopLogSinkAdapter",
]
