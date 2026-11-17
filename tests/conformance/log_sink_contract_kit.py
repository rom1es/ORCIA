"""Reusable Contract Test Kit for `LogSinkQueryPort` implementations (`AD-23`, `Story 7.0b`).

Validates perfect substitutability across `FakeInMemoryLogSinkAdapter`,
`ElasticsearchLogSinkAdapter` (OpenSearch / Elasticsearch), and future `LokiLogSinkAdapter`
(`OBS-LOGSINK-LOKI-01`).
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from orcia_core.observability.fingerprint import compute_error_fingerprint_sha256
from orcia_core.ports.log_sink import LogEntry, LogQuery, LogSinkQueryPort


def build_contract_seed_entries(now: datetime | None = None) -> tuple[list[LogEntry], str, str]:
    """Build deterministic ECS log entries for `LogSinkContractTestKit`."""
    ref = (now or datetime.now(UTC)).astimezone(UTC)
    fp_db = compute_error_fingerprint_sha256("api", "ConnectionError", "sql_repo.py:fetch")
    fp_other = compute_error_fingerprint_sha256("worker", "ValueError", "runner.py:step")

    entries = [
        LogEntry(
            timestamp=(ref - timedelta(seconds=30)).isoformat().replace("+00:00", "Z"),
            level="error",
            service="api",
            logger="orcia.api.db",
            message="Database pool exhausted while querying runs",
            trace_id="0192c4e0000070008000000000000001",
            span_id="00f067aa0ba902b1",
            exception="ConnectionError: pool exhausted",
            fingerprint=fp_db,
            workspace_id="ws-alpha",
            run_id="run-101",
            ctx={"error_fingerprint_sha256": fp_db, "attempt": 1},
        ),
        LogEntry(
            timestamp=(ref - timedelta(seconds=10)).isoformat().replace("+00:00", "Z"),
            level="error",
            service="api",
            logger="orcia.api.db",
            message="Database pool exhausted while querying runs (retry)",
            trace_id="0192c4e0000070008000000000000002",
            span_id="00f067aa0ba902b2",
            exception="ConnectionError: pool exhausted",
            fingerprint=fp_db,
            workspace_id="ws-alpha",
            run_id="run-102",
            ctx={"error_fingerprint_sha256": fp_db, "attempt": 2},
        ),
        LogEntry(
            timestamp=(ref - timedelta(seconds=20)).isoformat().replace("+00:00", "Z"),
            level="warning",
            service="api",
            logger="orcia.api.db",
            message="Slow query warning with same fingerprint ignored in error count",
            trace_id="0192c4e0000070008000000000000003",
            span_id="00f067aa0ba902b3",
            fingerprint=fp_db,
            workspace_id="ws-alpha",
            run_id="run-101",
            ctx={"error_fingerprint_sha256": fp_db},
        ),
        LogEntry(
            timestamp=(ref - timedelta(seconds=7200)).isoformat().replace("+00:00", "Z"),
            level="error",
            service="api",
            logger="orcia.api.db",
            message="Expired error outside 5-minute window",
            trace_id="0192c4e0000070008000000000000004",
            span_id="00f067aa0ba902b4",
            exception="ConnectionError: old",
            fingerprint=fp_db,
            workspace_id="ws-alpha",
            run_id="run-099",
            ctx={"error_fingerprint_sha256": fp_db},
        ),
        LogEntry(
            timestamp=(ref - timedelta(seconds=5)).isoformat().replace("+00:00", "Z"),
            level="critical",
            service="worker",
            logger="orcia.worker.runner",
            message="Critical failure in step execution",
            trace_id="0192c4e0000070008000000000000005",
            span_id="00f067aa0ba902b5",
            exception="ValueError: bad state",
            fingerprint=fp_other,
            workspace_id="ws-beta",
            run_id="run-201",
            ctx={"error_fingerprint_sha256": fp_other},
        ),
    ]
    return entries, fp_db, fp_other


class LogSinkContractTestKit:
    """Shared contract test suite verifying any `LogSinkQueryPort` implementation."""

    async def verify_healthcheck(self, sink: LogSinkQueryPort) -> None:
        assert isinstance(sink, LogSinkQueryPort)
        assert await sink.healthcheck() is True

    async def verify_query_logs(
        self,
        sink: LogSinkQueryPort,
        *,
        fp_db: str,
    ) -> None:
        # 1. Service + level + window filter + descending order
        api_errors = await sink.query_logs(
            LogQuery(service="api", level="error", since_seconds=300, limit=10)
        )
        assert len(api_errors) == 2
        assert api_errors[0].trace_id == "0192c4e0000070008000000000000002"
        assert api_errors[1].trace_id == "0192c4e0000070008000000000000001"
        assert api_errors[0].fingerprint == fp_db

        # 2. Limit clamping
        limited = await sink.query_logs(LogQuery(service="api", level="error", limit=1))
        assert len(limited) == 1

        # 3. Fingerprint + run_id + workspace_id + search_text filtering
        by_run = await sink.query_logs(
            LogQuery(workspace_id="ws-alpha", run_id="run-101", level="error")
        )
        assert len(by_run) == 1
        assert by_run[0].trace_id == "0192c4e0000070008000000000000001"

        by_text = await sink.query_logs(LogQuery(search_text="Critical failure", limit=10))
        assert len(by_text) == 1
        assert by_text[0].service == "worker"

    async def verify_count_errors(
        self,
        sink: LogSinkQueryPort,
        *,
        fp_db: str,
        fp_other: str,
    ) -> None:
        # Only 2 error/critical records for fp_db in last 300s (warning and 7200s-old excluded)
        recent_db_count = await sink.count_errors(fp_db, 300, service="api")
        assert recent_db_count == 2

        # Service filter excludes worker's fp_other when querying service="api"
        assert await sink.count_errors(fp_other, 300, service="api") == 0
        assert await sink.count_errors(fp_other, 300, service="worker") == 1

    async def run_all(
        self,
        sink: LogSinkQueryPort,
        *,
        fp_db: str,
        fp_other: str,
    ) -> None:
        """Execute full contract verification suite on `sink`."""
        await self.verify_healthcheck(sink)
        await self.verify_query_logs(sink, fp_db=fp_db)
        await self.verify_count_errors(sink, fp_db=fp_db, fp_other=fp_other)
