"""Unit tests for Story 7.0b: LogSinkQueryPort, ElasticsearchLogSinkAdapter & OTel tracing."""

from __future__ import annotations

import ast
import json
from pathlib import Path

import httpx
import pytest
import yaml  # type: ignore[import-untyped]
from fastapi import FastAPI
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import SimpleSpanProcessor, SpanExportResult
from opentelemetry.sdk.trace.export.in_memory_span_exporter import InMemorySpanExporter

from orcia_api.dependencies import get_log_sink_port, initialize_app_services
from orcia_core.observability import (
    ElasticsearchLogSinkAdapter,
    build_log_sink_from_env,
    compute_error_fingerprint_sha256,
    configure_logging,
    configure_tracing,
    extract_top_frame,
    get_logger,
    instrument_runtime,
    shutdown_tracing,
)
from orcia_core.observability.errors import (
    LogSinkQueryFailedError,
    UnsafeLogSinkUrlError,
    UnsupportedLogSinkBackendError,
)
from orcia_core.ports.log_sink import LogEntry, LogQuery, LogSinkQueryPort, NoopLogSinkAdapter

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_error_fingerprint_sha256_is_deterministic_and_normalizes_frames() -> None:
    """Verify `compute_error_fingerprint_sha256` format and frame normalization (AD-23 D5/D7)."""
    tb_pod1 = (
        "Traceback (most recent call last):\n"
        '  File "/app/packages/orcia-core/src/orcia_core/rag/service.py", line 42, in search\n'
        '  File "/app/packages/orcia-core/src/orcia_core/rag/_internal/sql_repository.py", '
        "line 118, in query_vectors\n"
        "ConnectionError: pool timeout at 0x7f9a1bc04010\n"
    )
    tb_pod2 = (
        "Traceback (most recent call last):\n"
        '  File "/workspace/packages/orcia-core/src/orcia_core/rag/_internal/sql_repository.py", '
        "line 125, in query_vectors\n"
        "ConnectionError: pool timeout at 0x7f1122334455\n"
    )

    frame1 = extract_top_frame(tb_pod1)
    frame2 = extract_top_frame(tb_pod2)
    assert frame1 == frame2
    assert "sql_repository.py:query_vectors" in frame1

    fp1 = compute_error_fingerprint_sha256("API", "ConnectionError", frame1)
    fp2 = compute_error_fingerprint_sha256("api", "ConnectionError", frame2)
    assert fp1 == fp2
    assert fp1.startswith("sha256:")
    assert len(fp1) == 7 + 64
    assert extract_top_frame(None) == "unknown"
    assert extract_top_frame("RuntimeError at 0xdeadbeef   occurred\nsecond line") == (
        "RuntimeError at 0xADDR occurred"
    )


@pytest.mark.parametrize(
    "bad_url",
    [
        "",
        "ftp://opensearch.local:9200",
        "http://user:pass@opensearch.local:9200",  # pragma: allowlist secret
        "http://169.254.169.254/latest/meta-data/",
        "http://[fe80::1]:9200/",
        "http://metadata.google.internal/",
        "http://100.100.100.200/",
        "http://0.0.0.0:9200/",
    ],
)
def test_log_sink_adapter_rejects_ssrf_and_invalid_urls(bad_url: str) -> None:
    """Verify `ElasticsearchLogSinkAdapter` enforces SSRF guard on `base_url`."""
    with pytest.raises(UnsafeLogSinkUrlError):
        ElasticsearchLogSinkAdapter(bad_url)


@pytest.mark.parametrize(
    "good_url",
    [
        "http://localhost:9200",
        "http://opensearch.orcia.local:9200",
        "https://logs.corp.internal:9200",
    ],
)
def test_log_sink_adapter_allows_legitimate_local_and_internal_urls(good_url: str) -> None:
    """Verify `ElasticsearchLogSinkAdapter` permits localhost, `.local` and `.internal`."""
    adapter = ElasticsearchLogSinkAdapter(good_url)
    assert isinstance(adapter, LogSinkQueryPort)


async def test_elasticsearch_adapter_logs_and_handles_upstream_failures(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Verify upstream errors are logged cleanly via structlog (no silent except)."""
    configure_logging(service="api", log_level="WARNING")

    def failing_handler(request: httpx.Request) -> httpx.Response:
        if request.url.path == "/_cluster/health":
            raise httpx.ConnectError("connection refused", request=request)
        return httpx.Response(503, json={"error": "cluster_unavailable"})

    async with httpx.AsyncClient(transport=httpx.MockTransport(failing_handler)) as client:
        adapter = ElasticsearchLogSinkAdapter(
            "http://opensearch.orcia.local:9200",
            http_client=client,
        )
        assert await adapter.healthcheck() is False
        with pytest.raises(LogSinkQueryFailedError):
            await adapter.query_logs(LogQuery(service="api"))
        with pytest.raises(LogSinkQueryFailedError):
            await adapter.count_errors("sha256:" + "a" * 64, 300)

    lines = [json.loads(line) for line in capsys.readouterr().out.splitlines() if line.strip()]
    assert len(lines) >= 3
    assert any(rec["message"] == "log_sink_healthcheck_failed" for rec in lines)
    assert any(rec["message"] == "log_sink_query_failed" for rec in lines)

    # HTTP 503 healthcheck + client_factory + invalid index_pattern + negative window_seconds
    def status_503_handler(_request: httpx.Request) -> httpx.Response:
        return httpx.Response(503, json={"status": "red"})

    adapter_factory = ElasticsearchLogSinkAdapter(
        "http://opensearch.orcia.local:9200",
        client_factory=lambda: httpx.AsyncClient(transport=httpx.MockTransport(status_503_handler)),
    )
    assert await adapter_factory.healthcheck() is False
    with pytest.raises(ValueError, match="window_seconds"):
        await adapter_factory.count_errors("sha256:" + "a" * 64, -1)
    with pytest.raises(ValueError, match="index pattern"):
        ElasticsearchLogSinkAdapter("http://opensearch.orcia.local:9200", index_pattern="../bad")
    with pytest.raises(ValueError, match="limit"):
        LogQuery(limit=0)
    assert LogQuery(limit=999).limit == 200


def test_build_log_sink_from_env_selection_and_composition_root(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify Composition Root selects Noop/Elasticsearch and rejects unsupported Loki."""
    monkeypatch.delenv("LOG_SINK_BACKEND", raising=False)
    monkeypatch.delenv("ORCIA_LOG_SINK_URL", raising=False)
    assert isinstance(build_log_sink_from_env(), NoopLogSinkAdapter)

    monkeypatch.setenv("LOG_SINK_BACKEND", "none")
    assert isinstance(build_log_sink_from_env(), NoopLogSinkAdapter)

    monkeypatch.setenv("LOG_SINK_BACKEND", "elasticsearch")
    monkeypatch.setenv("ORCIA_LOG_SINK_URL", "http://opensearch.orcia.local:9200")
    monkeypatch.setenv("ORCIA_LOG_SINK_INDEX", "orcia-prod-*")
    es_sink = build_log_sink_from_env()
    assert isinstance(es_sink, ElasticsearchLogSinkAdapter)

    monkeypatch.setenv("LOG_SINK_BACKEND", "loki")
    with pytest.raises(UnsupportedLogSinkBackendError):
        build_log_sink_from_env()

    monkeypatch.setenv("LOG_SINK_BACKEND", "elasticsearch")
    monkeypatch.delenv("ORCIA_LOG_SINK_URL", raising=False)
    with pytest.raises(UnsupportedLogSinkBackendError):
        build_log_sink_from_env()

    monkeypatch.setenv("LOG_SINK_BACKEND", "unknown-driver")
    with pytest.raises(UnsupportedLogSinkBackendError):
        build_log_sink_from_env()

    # FastAPI Composition Root wiring
    monkeypatch.setenv("LOG_SINK_BACKEND", "elasticsearch")
    monkeypatch.setenv("ORCIA_LOG_SINK_URL", "http://opensearch.orcia.local:9200")
    app = FastAPI()
    initialize_app_services(app)
    assert isinstance(app.state.log_sink, ElasticsearchLogSinkAdapter)

    class _FakeReq:
        def __init__(self, target_app: FastAPI) -> None:
            self.app = target_app

    assert get_log_sink_port(_FakeReq(app)) is app.state.log_sink  # type: ignore[arg-type]


def test_otel_tracing_config_and_structlog_span_correlation(
    capsys: pytest.CaptureFixture[str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify `OTEL_TRACES_EXPORTER=none`, real `TracerProvider` correlation & runtime."""
    monkeypatch.setattr(
        OTLPSpanExporter,
        "export",
        lambda self, spans: SpanExportResult.SUCCESS,
    )
    monkeypatch.setattr(OTLPSpanExporter, "shutdown", lambda self: None)
    monkeypatch.setenv("OTEL_TRACES_EXPORTER", "none")
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    assert configure_tracing(service_name="api") is None
    assert capsys.readouterr().out == ""

    monkeypatch.setenv("OTEL_TRACES_EXPORTER", "otlp")
    monkeypatch.setenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector.orcia.local:4318")
    provider = configure_tracing(service_name="orcia-api-test", set_global=False)
    assert isinstance(provider, TracerProvider)
    exporter = InMemorySpanExporter()
    provider.add_span_processor(SimpleSpanProcessor(exporter))

    from orcia_core.observability.logging import bind_trace_context, clear_trace_context

    configure_logging(service="api", log_level="INFO")
    tracer = provider.get_tracer("orcia.test")
    with tracer.start_as_current_span("workflow.step.run") as span:
        span_ctx = span.get_span_context()
        expected_trace_id = f"{span_ctx.trace_id:032x}"
        expected_span_id = f"{span_ctx.span_id:016x}"
        bound = bind_trace_context(
            workspace_id="ws-otel",
            run_id="run-otel",
            step_id="step-otel",
        )
        assert bound.trace_id == expected_trace_id
        assert bound.span_id == expected_span_id
        get_logger("orcia.tracing.test").info("step.executed", step_key="analyze")
        clear_trace_context()

    lines = [json.loads(line) for line in capsys.readouterr().out.splitlines() if line.strip()]
    assert len(lines) == 1
    assert lines[0]["trace_id"] == expected_trace_id
    assert lines[0]["span_id"] == expected_span_id
    assert lines[0]["workspace_id"] == "ws-otel"
    assert lines[0]["run_id"] == "run-otel"
    assert lines[0]["step_id"] == "step-otel"
    finished = exporter.get_finished_spans()
    assert len(finished) == 1
    assert finished[0].attributes is not None
    assert finished[0].attributes.get("orcia.workspace_id") == "ws-otel"

    from opentelemetry import trace as otel_trace
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor

    import orcia_core.observability.tracing as tracing_mod

    saved_httpx_instrumented = tracing_mod._HTTPX_INSTRUMENTED
    saved_global = tracing_mod._GLOBAL_TRACER_PROVIDER
    saved_otel_provider = getattr(otel_trace, "_TRACER_PROVIDER", None)
    saved_set_once_done = otel_trace._TRACER_PROVIDER_SET_ONCE._done

    app = FastAPI()
    try:
        flags = instrument_runtime(app=app, instrument_httpx=True)
        assert flags["fastapi"] is True
        assert flags["httpx"] is True
        assert instrument_runtime(app=app, instrument_httpx=True)["fastapi"] is True
        shutdown_tracing(None)
        monkeypatch.setenv("OTEL_EXPORTER_OTLP_TRACES_TIMEOUT", "100")
        shutdown_tracing(provider)

        # Test global tracer provider idempotency cleanly (saving/restoring OTel globals)
        tracing_mod._GLOBAL_TRACER_PROVIDER = None
        otel_trace._TRACER_PROVIDER = None
        otel_trace._TRACER_PROVIDER_SET_ONCE._done = False
        g1 = configure_tracing(service_name="api-global", exporter_mode="console", set_global=True)
        g2 = configure_tracing(
            service_name="api-global-2", exporter_mode="console", set_global=True
        )
        assert g1 is not None and g2 is g1
    finally:
        shutdown_tracing()
        tracing_mod._GLOBAL_TRACER_PROVIDER = saved_global
        otel_trace._TRACER_PROVIDER = saved_otel_provider
        otel_trace._TRACER_PROVIDER_SET_ONCE._done = saved_set_once_done
        if not saved_httpx_instrumented:
            HTTPXClientInstrumentor().uninstrument()
        tracing_mod._HTTPX_INSTRUMENTED = saved_httpx_instrumented
        FastAPIInstrumentor.uninstrument_app(app)

    # Edge cases: console exporter, unsupported exporter, otlp without endpoint, /v1/traces suffix
    monkeypatch.delenv("OTEL_TRACES_EXPORTER", raising=False)
    monkeypatch.delenv("OTEL_EXPORTER_OTLP_ENDPOINT", raising=False)
    assert configure_tracing(service_name="api") is None
    assert configure_tracing(service_name="api", exporter_mode="otlp", otlp_endpoint="") is None
    assert (
        configure_tracing(service_name="api", exporter_mode="unsupported", otlp_endpoint="") is None
    )

    console_provider = configure_tracing(
        service_name="api-console", exporter_mode="console", set_global=False
    )
    assert isinstance(console_provider, TracerProvider)
    shutdown_tracing(console_provider)

    otlp_explicit = configure_tracing(
        service_name="api-otlp-path",
        otlp_endpoint="http://otel.orcia.local:4318/v1/traces",
        set_global=False,
    )
    assert isinstance(otlp_explicit, TracerProvider)
    shutdown_tracing(otlp_explicit)

    # Test shutdown_tracing error resilience without silent except
    class _BrokenProvider:
        def shutdown(self) -> None:
            raise RuntimeError("boom")

    shutdown_tracing(_BrokenProvider())  # type: ignore[arg-type]

    # Test SQLAlchemy engine instrumentation idempotently without opening a connection
    import sqlalchemy as sa

    dummy_engine = sa.create_engine("postgresql+psycopg://localhost:5433/orcia")
    try:
        sa_flags = instrument_runtime(engine=dummy_engine, instrument_httpx=False)
        assert sa_flags["sqlalchemy"] is True
        sa_flags_2 = instrument_runtime(engine=dummy_engine, instrument_httpx=False)
        assert sa_flags_2["sqlalchemy"] is True
    finally:
        dummy_engine.dispose()


def test_ad23_reversibility_invariants_no_otel_log_exporter_and_compose_profiles() -> None:
    """Verify AD-23: zero OTLPLogExporter/LoggerProvider in Python and Compose profiles present."""
    src_roots = (
        REPO_ROOT / "packages" / "orcia-core" / "src",
        REPO_ROOT / "packages" / "orcia-connectors" / "src",
        REPO_ROOT / "apps" / "api" / "src",
        REPO_ROOT / "apps" / "worker" / "src",
    )
    forbidden = ("OTLPLogExporter", "LoggerProvider", "LoggingInstrumentor")
    for root in src_roots:
        for py_file in root.rglob("*.py"):
            content = py_file.read_text(encoding="utf-8")
            tree = ast.parse(content, filename=str(py_file))
            for node in ast.walk(tree):
                if isinstance(node, ast.Name) and node.id in forbidden:
                    pytest.fail(f"{py_file} references forbidden OTel log class {node.id}")
                if isinstance(node, ast.alias) and node.name in forbidden:
                    pytest.fail(f"{py_file} imports forbidden OTel log class {node.name}")

    # Verify ports/log_sink.py has zero SDK imports (Contract 3)
    log_sink_port_path = (
        REPO_ROOT / "packages" / "orcia-core" / "src" / "orcia_core" / "ports" / "log_sink.py"
    )
    port_tree = ast.parse(log_sink_port_path.read_text(encoding="utf-8"))
    for node in ast.walk(port_tree):
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            mod = node.module if isinstance(node, ast.ImportFrom) else node.names[0].name
            assert mod is not None
            assert not mod.startswith(("httpx", "opentelemetry", "fastapi", "sqlalchemy"))

    # Verify docker-compose.yml profiles & json-file rotation
    compose = yaml.safe_load(
        (REPO_ROOT / "infra" / "docker" / "docker-compose.yml").read_text(encoding="utf-8")
    )
    services = compose["services"]
    assert "opensearch" in services
    assert "logs-elastic" in services["opensearch"]["profiles"]
    assert "loki" in services
    assert "logs-loki" in services["loki"]["profiles"]
    assert "grafana" in services
    assert set(services["grafana"]["profiles"]) >= {"logs-elastic", "logs-loki"}
    for app_svc in (
        "api",
        "worker-orchestration",
        "worker-indexing",
        "trigger-dispatcher",
        "sandbox-runner",
    ):
        assert services[app_svc]["logging"]["driver"] == "json-file"
        assert services[app_svc]["logging"]["options"]["max-size"] == "50m"
        assert services[app_svc]["logging"]["options"]["max-file"] == "3"

    # Verify LogEntry dataclass contract fields
    sample = LogEntry(
        timestamp="2026-11-17T08:00:00Z",
        level="info",
        service="api",
        logger="orcia",
        message="ok",
    )
    assert sample.ctx == {}
