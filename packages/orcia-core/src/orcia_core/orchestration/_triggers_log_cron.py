"""Pure-Python CRON matcher, Self-Trigger Guard & LogSinkAnomalyScanner (`Story 7.2`, `AD-23`).

Zero framework or external SDK imports; zero SDLC domain vocabulary (`AD-19`, `AD-20`).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime

from orcia_core.observability.fingerprint import (
    compute_error_fingerprint_sha256,
    extract_top_frame,
)
from orcia_core.orchestration.models import WorkflowTriggerEntity
from orcia_core.permissions.errors import ValidationDomainError
from orcia_core.ports.log_sink import LogEntry, LogQuery, LogSinkQueryPort


def _parse_cron_field(expr: str, min_val: int, max_val: int) -> set[int]:
    """Parse one 5-field CRON component (`*`, `*/n`, `a-b`, `a,b`) into integer values."""
    values: set[int] = set()
    for part in expr.split(","):
        token = part.strip()
        if not token:
            raise ValidationDomainError(detail_override=f"Invalid empty CRON field: {expr!r}")
        step = 1
        if "/" in token:
            base, step_str = token.split("/", 1)
            step = int(step_str)
            if step <= 0:
                raise ValidationDomainError(detail_override=f"Invalid CRON step: {expr!r}")
        else:
            base = token
        if base == "*":
            start, end = min_val, max_val
        elif "-" in base:
            lo_str, hi_str = base.split("-", 1)
            start, end = int(lo_str), int(hi_str)
        else:
            val = int(base)
            start, end = val, val
        if start < min_val or end > max_val or start > end:
            raise ValidationDomainError(detail_override=f"Out-of-range CRON field: {expr!r}")
        values.update(range(start, end + 1, step))
    return values


def validate_cron_expr(cron_expr: str) -> None:
    """Validate a standard 5-field CRON expression (`min hour dom month dow`)."""
    parts = [p for p in cron_expr.strip().split() if p]
    if len(parts) != 5:
        raise ValidationDomainError(
            detail_override=(
                f"CRON expression must have exactly 5 fields (got {len(parts)}): {cron_expr!r}"
            )
        )
    ranges = ((0, 59), (0, 23), (1, 31), (1, 12), (0, 6))
    try:
        for part, (lo, hi) in zip(parts, ranges, strict=True):
            _parse_cron_field(part, lo, hi)
    except ValueError as exc:
        raise ValidationDomainError(detail_override=f"Invalid CRON syntax: {cron_expr!r}") from exc


def cron_matches_timestamp(cron_expr: str, dt: datetime) -> bool:
    """Return `True` if 5-field `cron_expr` matches UTC datetime `dt` (minute granularity)."""
    validate_cron_expr(cron_expr)
    parts = [p for p in cron_expr.strip().split() if p]
    minute_set = _parse_cron_field(parts[0], 0, 59)
    hour_set = _parse_cron_field(parts[1], 0, 23)
    dom_set = _parse_cron_field(parts[2], 1, 31)
    month_set = _parse_cron_field(parts[3], 1, 12)
    dow_set = _parse_cron_field(parts[4], 0, 6)
    utc_dt = dt.astimezone(UTC)
    cron_dow = (utc_dt.weekday() + 1) % 7
    return (
        utc_dt.minute in minute_set
        and utc_dt.hour in hour_set
        and utc_dt.day in dom_set
        and utc_dt.month in month_set
        and cron_dow in dow_set
    )


@dataclass(frozen=True, slots=True)
class SelfTriggerVerdict:
    """Evaluation verdict of the anti-loop Self-Trigger Guard (`Story 7.2`)."""

    blocked: bool
    reason: str = ""
    origin_run_id: str | None = None


def evaluate_self_trigger_guard(
    *,
    trigger: WorkflowTriggerEntity,
    contract_service_principal_id: str | None = None,
    headers: dict[str, str] | None = None,
    payload: dict[str, object] | None = None,
) -> SelfTriggerVerdict:
    """Detect recursive events emitted by ORCIA itself or the trigger's own service account."""
    norm_headers = {k.lower().strip(): str(v).strip() for k, v in (headers or {}).items()}
    body = payload or {}

    origin_run_id = (
        norm_headers.get("x-orcia-origin-run-id")
        or str(body.get("origin_run_id") or body.get("x-orcia-origin-run-id") or "").strip()
    )
    if origin_run_id:
        return SelfTriggerVerdict(
            blocked=True,
            reason="Origin marker x-orcia-origin-run-id detected",
            origin_run_id=origin_run_id,
        )

    origin_sp = (
        norm_headers.get("x-orcia-service-principal-id")
        or str(
            body.get("origin_service_principal")
            or body.get("actor_account_id")
            or body.get("service_principal_id")
            or ""
        ).strip()
    )
    expected_sp = (contract_service_principal_id or trigger.service_principal_id or "").strip()
    if origin_sp and expected_sp and origin_sp == expected_sp:
        return SelfTriggerVerdict(
            blocked=True,
            reason=f"Event actor matches trigger service account ({origin_sp})",
            origin_run_id=None,
        )

    actor_type = str(body.get("actor_type") or "").strip().upper()
    if actor_type == "SERVICE_PRINCIPAL" and origin_sp:
        return SelfTriggerVerdict(
            blocked=True,
            reason=f"Event emitted by platform service account ({origin_sp})",
            origin_run_id=None,
        )

    return SelfTriggerVerdict(blocked=False)


@dataclass(frozen=True, slots=True)
class DetectedLogAnomaly:
    """Deterministic log anomaly grouped by SHA-256 fingerprint & cooldown time bucket."""

    trigger_id: str
    fingerprint: str
    idempotency_key: str
    service: str
    error_count: int
    sample_message: str


class LogSinkAnomalyScanner:
    """Queries `LogSinkQueryPort` (`AD-23`) to convert log spikes into idempotent trigger keys."""

    def __init__(self, log_sink: LogSinkQueryPort) -> None:
        self._log_sink = log_sink

    async def scan_trigger(
        self,
        trigger: WorkflowTriggerEntity,
        *,
        now_utc: datetime | None = None,
        min_error_count: int = 1,
    ) -> list[DetectedLogAnomaly]:
        """Query matching ERROR logs and deduplicate within `cooldown_window_seconds`."""
        now = now_utc or datetime.now(UTC)
        window = max(60, trigger.cooldown_window_seconds or 300)
        entries: list[LogEntry] = await self._log_sink.query_logs(
            LogQuery(
                service=trigger.log_sink_service,
                level="ERROR",
                workspace_id=trigger.workspace_id,
                search_text=trigger.log_sink_query_text,
                since_seconds=window,
                limit=50,
            )
        )
        if not entries:
            return []

        bucket = int(now.timestamp()) // window
        grouped: dict[str, tuple[LogEntry, int]] = {}
        for entry in entries:
            fp = entry.fingerprint or compute_error_fingerprint_sha256(
                entry.service,
                str(entry.ctx.get("exception_type") or "RuntimeError"),
                extract_top_frame(entry.exception or entry.message),
            )
            if fp not in grouped:
                cnt = await self._log_sink.count_errors(
                    fp,
                    window,
                    service=entry.service,
                )
                grouped[fp] = (entry, max(cnt, 1))

        anomalies: list[DetectedLogAnomaly] = []
        for fp, (sample, count) in grouped.items():
            if count < max(1, min_error_count):
                continue
            anomalies.append(
                DetectedLogAnomaly(
                    trigger_id=trigger.id,
                    fingerprint=fp,
                    idempotency_key=f"logsink:{fp}:{bucket}",
                    service=sample.service,
                    error_count=count,
                    sample_message=sample.message[:240],
                )
            )
        return anomalies


__all__ = [
    "DetectedLogAnomaly",
    "LogSinkAnomalyScanner",
    "SelfTriggerVerdict",
    "cron_matches_timestamp",
    "evaluate_self_trigger_guard",
    "validate_cron_expr",
]
