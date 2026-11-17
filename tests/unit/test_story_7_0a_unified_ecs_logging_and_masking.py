"""Unit tests for Story 7.0a: unified 12-factor JSON stdout ECS logging & rotation."""

from __future__ import annotations

import json
import logging
from pathlib import Path

import pytest

from orcia_core.observability.logging import (
    bind_trace_context,
    clear_sensitive_secret_values,
    clear_trace_context,
    configure_logging,
    configure_structlog,
    get_logger,
    register_sensitive_secret_value,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def _parse_single_json_lines(raw_stdout: str) -> list[dict[str, object]]:
    lines = [line for line in raw_stdout.splitlines() if line.strip()]
    assert lines, "Expected at least one JSON log line on stdout"
    return [json.loads(line) for line in lines]


def test_unified_stdout_single_line_json_ecs_across_loggers(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify 1 line = 1 valid ECS JSON object on stdout and 0 raw stderr output across loggers."""
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    clear_trace_context()
    configure_logging(service="api", env="staging", version="1.2.3")
    bind_trace_context(
        "0192c4e0000070008000000000000099",
        workspace_id="ws-123",
        run_id="run-456",
        step_id="step-789",
    )

    get_logger("orcia.api.test").info("api.request.handled", user_role="TEAM_LEAD", latency_ms=12)
    logging.getLogger("uvicorn.access").info('127.0.0.1:50000 - "GET /api/v1/runs HTTP/1.1" 200')
    logging.getLogger("dramatiq").warning("dramatiq.retry scheduled attempt=%d", 2)
    logging.getLogger("sqlalchemy.engine").info("SELECT 1")
    logging.getLogger("dbos").info("dbos workflow resumed")

    captured = capsys.readouterr()
    assert captured.err == ""
    records = _parse_single_json_lines(captured.out)
    assert len(records) == 5

    required_keys = {
        "timestamp",
        "level",
        "logger",
        "message",
        "service",
        "env",
        "version",
        "trace_id",
        "span_id",
        "workspace_id",
        "run_id",
        "step_id",
        "ctx",
    }
    for rec in records:
        assert required_keys.issubset(rec.keys())
        assert str(rec["timestamp"]).endswith("Z") or "+00:00" in str(rec["timestamp"])
        assert rec["service"] == "api"
        assert rec["env"] == "staging"
        assert rec["version"] == "1.2.3"
        assert rec["trace_id"] == "0192c4e0000070008000000000000099"
        assert rec["span_id"]
        assert rec["workspace_id"] == "ws-123"
        assert rec["run_id"] == "run-456"
        assert rec["step_id"] == "step-789"
        assert isinstance(rec["ctx"], dict)

    structlog_rec = records[0]
    assert structlog_rec["logger"] == "orcia.api.test"
    assert structlog_rec["message"] == "api.request.handled"
    assert structlog_rec["ctx"] == {"user_role": "TEAM_LEAD", "latency_ms": 12}

    assert records[1]["logger"] == "uvicorn.access"
    assert records[2]["logger"] == "dramatiq"
    assert records[2]["message"] == "dramatiq.retry scheduled attempt=2"
    assert records[3]["logger"] == "sqlalchemy.engine"
    assert records[4]["logger"] == "dbos"
    clear_trace_context()


def test_exception_serialized_as_single_line_json_field_no_stderr(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify Python exceptions & tracebacks serialize into JSON `exception` with 0 stderr."""
    clear_trace_context()
    configure_logging(service="worker")

    try:
        raise RuntimeError("Boom during execution with Bearer super_secret_jwt_123")
    except RuntimeError:
        logging.getLogger("dbos").exception("worker.step.failed")
        get_logger("orcia.worker.test").exception("structlog.step.failed")

    captured = capsys.readouterr()
    assert captured.err == ""
    records = _parse_single_json_lines(captured.out)
    assert len(records) == 2

    for rec in records:
        assert rec["level"] == "error"
        exc_text = str(rec.get("exception", ""))
        assert "RuntimeError" in exc_text
        assert "super_secret_jwt_123" not in exc_text
        assert "[REDACTED_SECRET]" in exc_text


def test_dynamic_log_level_from_env_and_default(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify LOG_LEVEL env var dynamically filters logs (default INFO on invalid/absent)."""
    clear_trace_context()

    monkeypatch.setenv("LOG_LEVEL", "WARNING")
    configure_logging(service="api")
    log = get_logger("orcia.level")
    log.debug("hidden debug")
    log.info("hidden info")
    log.warning("visible warning")
    log.error("visible error")
    recs = _parse_single_json_lines(capsys.readouterr().out)
    assert [r["message"] for r in recs] == ["visible warning", "visible error"]

    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    configure_logging(service="api")
    log.debug("now visible debug")
    recs_dbg = _parse_single_json_lines(capsys.readouterr().out)
    assert [r["message"] for r in recs_dbg] == ["now visible debug"]

    monkeypatch.setenv("LOG_LEVEL", "NOT_A_VALID_LEVEL")
    configure_logging(service="api")
    log.debug("filtered by default info")
    log.info("kept by default info")
    recs_def = _parse_single_json_lines(capsys.readouterr().out)
    assert [r["message"] for r in recs_def] == ["kept by default info"]


def test_health_probe_filter_drops_200_and_keeps_500_and_other_routes(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify /api/v1/health and /ready regular 200 probes are filtered while 500s are kept."""
    clear_trace_context()
    configure_logging(service="api", log_level="INFO")
    access_logger = logging.getLogger("uvicorn.access")

    access_logger.info('127.0.0.1:42000 - "GET /api/v1/health HTTP/1.1" 200')
    access_logger.info('%s - "%s %s HTTP/%s" %d', "127.0.0.1:42000", "GET", "/ready", "1.1", 200)
    access_logger.info('127.0.0.1:42000 - "GET /api/v1/health HTTP/1.1" 500')
    access_logger.info('%s - "%s %s HTTP/%s" %d', "127.0.0.1:42000", "GET", "/ready", "1.1", 503)
    access_logger.info('127.0.0.1:42000 - "GET /api/v1/workspaces HTTP/1.1" 200')

    captured = capsys.readouterr()
    assert captured.err == ""
    recs = _parse_single_json_lines(captured.out)
    messages = [str(r["message"]) for r in recs]
    assert len(messages) == 3
    assert any("/api/v1/health" in m and "500" in m for m in messages)
    assert any("/ready" in m and "503" in m for m in messages)
    assert any("/api/v1/workspaces" in m for m in messages)


def test_configure_structlog_alias_remains_backward_compatible(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify `configure_structlog()` aliases `configure_logging(service='api')`."""
    clear_sensitive_secret_values()
    register_sensitive_secret_value("CANARY_ALIAS_SECRET_9876")
    configure_structlog()
    get_logger("orcia.alias").info(
        "alias.ok",
        secret_note="leak CANARY_ALIAS_SECRET_9876",  # pragma: allowlist secret
    )
    recs = _parse_single_json_lines(capsys.readouterr().out)
    assert recs[0]["service"] == "api"
    assert "CANARY_ALIAS_SECRET_9876" not in json.dumps(recs[0])
    clear_sensitive_secret_values()


def test_manage_py_bounded_50mb_log_rotation(tmp_path: Path) -> None:
    """Verify `scripts/manage.py` uses RotatingFileHandler bounded at 50 MiB and rotates."""
    import scripts.manage as manage_script

    assert manage_script.MAX_LOCAL_LOG_BYTES == 50 * 1024 * 1024
    log_path = tmp_path / "api.log"
    log_path.write_bytes(b"X" * 2048)

    handler = manage_script.create_bounded_log_handler(
        log_path,
        max_bytes=1024,
        backup_count=3,
    )
    try:
        assert handler.maxBytes == 1024
        assert handler.backupCount == 3
    finally:
        handler.close()

    rotated_backup = tmp_path / "api.log.1"
    assert rotated_backup.is_file()
    assert rotated_backup.stat().st_size == 2048
    assert log_path.stat().st_size == 0


def test_web_package_json_has_no_unused_pino_dependency() -> None:
    """Verify `pino` was removed from `apps/web/package.json`."""
    pkg = json.loads((REPO_ROOT / "apps" / "web" / "package.json").read_text(encoding="utf-8"))
    assert "pino" not in pkg.get("dependencies", {})
    assert "pino" not in pkg.get("devDependencies", {})


def test_worker_roles_and_explicit_message_ecs_normalization(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify worker role CLI configures logging and explicit `message=` keeps `ctx.event`."""
    from orcia_worker.roles import main as roles_main

    clear_trace_context()
    monkeypatch.setenv("ORCIA_WORKER_ROLE", "worker-indexing")
    monkeypatch.setenv("ORCIA_ENV", "production")
    monkeypatch.setenv("ORCIA_VERSION", "2.4.0")
    assert roles_main(["--role", "worker-indexing"]) == 0

    get_logger("orcia.worker.test").info(
        "worker.indexed",
        message="Indexed repository",
        ctx={"repo": "ORCIA"},
    )
    recs = _parse_single_json_lines(capsys.readouterr().out)
    assert recs[0]["service"] == "worker-indexing"
    assert recs[0]["env"] == "production"
    assert recs[0]["version"] == "2.4.0"
    assert recs[0]["message"] == "Indexed repository"
    assert recs[0]["ctx"] == {"repo": "ORCIA", "event": "worker.indexed"}
    assert recs[0]["trace_id"] is None
    assert recs[0]["span_id"] is None


def test_reenables_loggers_disabled_by_external_fileconfig(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify `configure_logging` re-enables loggers disabled by `disable_existing_loggers`."""
    for name in ("uvicorn.access", "dramatiq", "dbos", "sqlalchemy.engine"):
        logging.getLogger(name).disabled = True

    configure_logging(service="api", log_level="INFO")
    logging.getLogger("uvicorn.access").info('127.0.0.1 - "GET /api/v1/items HTTP/1.1" 200')
    logging.getLogger("dramatiq").info("dramatiq.ready")
    logging.getLogger("dbos").info("dbos.ready")
    logging.getLogger("sqlalchemy.engine").info("SELECT 42")

    recs = _parse_single_json_lines(capsys.readouterr().out)
    assert len(recs) == 4


def test_ecs_formatter_edge_cases_otel_fallback_and_filter(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify env/version fallback, allowlist scrubbing, OTel span fallback, and dict filter."""
    from opentelemetry import context as otel_context
    from opentelemetry import trace as otel_trace
    from opentelemetry.trace import NonRecordingSpan, SpanContext, TraceFlags, set_span_in_context

    from orcia_core.observability._internal.ecs_formatter import (
        HealthProbeLogFilter,
        resolve_environment,
        scrub_sensitive_dict,
    )
    from orcia_core.observability.logging import _DynamicStdoutStream, ensure_logging_configured

    monkeypatch.delenv("ORCIA_ENV", raising=False)
    monkeypatch.delenv("ENVIRONMENT", raising=False)
    monkeypatch.delenv("ENV", raising=False)
    assert resolve_environment() == "development"
    monkeypatch.setenv("ENVIRONMENT", "qa")
    assert resolve_environment() == "qa"

    scrubbed = scrub_sensitive_dict(
        {"keep": "ok", "drop": "ignored", "items": ["Bearer tok_1", {"secret": "x"}, 42]},
        allowed_keys=frozenset({"keep", "items"}),
    )
    assert scrubbed["keep"] == "ok"
    assert "drop" not in scrubbed
    assert scrubbed["items"] == ["[REDACTED_SECRET]", {"secret": "[REDACTED_SECRET]"}, 42]

    probe_filter = HealthProbeLogFilter()
    rec_dict_200 = logging.LogRecord(
        name="uvicorn.access",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg={"path": "/api/v1/health", "status": 200},
        args=(),
        exc_info=None,
    )
    rec_dict_500 = logging.LogRecord(
        name="uvicorn.access",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg={"path": "/ready", "status_code": 500},
        args=(),
        exc_info=None,
    )
    rec_warn = logging.LogRecord(
        name="uvicorn.access",
        level=logging.WARNING,
        pathname=__file__,
        lineno=1,
        msg="GET /api/v1/health",
        args=(),
        exc_info=None,
    )
    assert probe_filter.filter(rec_dict_200) is False
    assert probe_filter.filter(rec_dict_500) is True
    assert probe_filter.filter(rec_warn) is True

    clear_trace_context()
    configure_logging(service="api", log_level="INFO")
    span_ctx = SpanContext(
        trace_id=0x4BF92F3577B34DA6A3CE929D0E0E4736,
        span_id=0x00F067AA0BA902B7,
        is_remote=False,
        trace_flags=TraceFlags(TraceFlags.SAMPLED),
    )
    token = otel_context.attach(set_span_in_context(NonRecordingSpan(span_ctx)))
    try:
        get_logger("orcia.otel").info("otel.fallback")
    finally:
        otel_context.detach(token)

    recs = _parse_single_json_lines(capsys.readouterr().out)
    assert recs[0]["trace_id"] == "4bf92f3577b34da6a3ce929d0e0e4736"
    assert recs[0]["span_id"] == "00f067aa0ba902b7"

    proxy = _DynamicStdoutStream()
    assert isinstance(proxy.isatty(), bool)
    assert proxy.encoding
    assert otel_trace is not None

    import orcia_core.observability.logging as logging_mod

    logging_mod._LOGGING_CONFIGURED = False
    ensure_logging_configured(service="worker")
    assert logging_mod._LOGGING_CONFIGURED is True
