"""In-memory test fake for `LogSinkQueryPort` (`AD-17`, `AD-23`, `Story 7.0b`).

Lives exclusively under `tests/unit/fakes/` — never imported in production code.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from orcia_core.ports.log_sink import LogEntry, LogQuery, LogSinkQueryPort


def _parse_iso_utc(raw: str) -> datetime:
    cleaned = raw.strip()
    if cleaned.endswith("Z"):
        cleaned = f"{cleaned[:-1]}+00:00"
    dt = datetime.fromisoformat(cleaned)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=UTC)
    return dt.astimezone(UTC)


class FakeInMemoryLogSinkAdapter(LogSinkQueryPort):
    """Deterministic in-memory `LogSinkQueryPort` for unit and conformance tests."""

    def __init__(
        self,
        entries: list[LogEntry] | None = None,
        *,
        healthy: bool = True,
        clock_now: datetime | None = None,
    ) -> None:
        self._entries: list[LogEntry] = list(entries or [])
        self.healthy = healthy
        self._clock_now = clock_now

    def add_entry(self, entry: LogEntry) -> None:
        """Append a log entry into the in-memory sink."""
        self._entries.append(entry)

    def extend(self, entries: list[LogEntry]) -> None:
        """Append multiple log entries into the in-memory sink."""
        self._entries.extend(entries)

    def _now(self) -> datetime:
        return self._clock_now or datetime.now(UTC)

    async def healthcheck(self) -> bool:
        return self.healthy

    async def query_logs(self, query: LogQuery) -> list[LogEntry]:
        now = self._now()
        cutoff = (
            now - timedelta(seconds=query.since_seconds)
            if query.since_seconds is not None
            else None
        )
        matched: list[LogEntry] = []
        for entry in self._entries:
            if query.service and entry.service != query.service:
                continue
            if query.level and entry.level.lower() != query.level.lower():
                continue
            entry_ws = entry.workspace_id or entry.ctx.get("workspace_id")
            if query.workspace_id and entry_ws != query.workspace_id:
                continue
            entry_run = entry.run_id or entry.ctx.get("run_id")
            if query.run_id and entry_run != query.run_id:
                continue
            entry_fp = entry.fingerprint or entry.ctx.get("error_fingerprint_sha256")
            if query.fingerprint and entry_fp != query.fingerprint:
                continue
            if query.search_text:
                haystack = f"{entry.message}\n{entry.exception or ''}".lower()
                if query.search_text.lower() not in haystack:
                    continue
            if cutoff is not None and _parse_iso_utc(entry.timestamp) < cutoff:
                continue
            matched.append(entry)

        matched.sort(key=lambda item: _parse_iso_utc(item.timestamp), reverse=True)
        return matched[: min(query.limit, 200)]

    async def count_errors(
        self,
        fingerprint: str,
        window_seconds: int,
        *,
        service: str | None = None,
    ) -> int:
        cutoff = self._now() - timedelta(seconds=window_seconds)
        count = 0
        for entry in self._entries:
            if entry.level.lower() not in ("error", "critical"):
                continue
            if service and entry.service != service:
                continue
            entry_fp = entry.fingerprint or entry.ctx.get("error_fingerprint_sha256")
            if entry_fp != fingerprint:
                continue
            if _parse_iso_utc(entry.timestamp) >= cutoff:
                count += 1
        return count


__all__ = ["FakeInMemoryLogSinkAdapter"]
