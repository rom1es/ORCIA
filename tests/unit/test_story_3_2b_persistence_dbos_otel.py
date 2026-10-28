"""Unit tests for Story 3.2b: SeaweedFS CAS, LiteLLM, OpenTelemetry, SQL Repos & DBOS Engine."""

from __future__ import annotations

import hashlib
import inspect
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from opentelemetry import trace as otel_trace
from sqlalchemy.ext.asyncio import create_async_engine

from orcia_core.blackboard.models import StepExecutionEntity, StepMemlogEntry
from orcia_core.bootstrap._internal.litellm_adapter import LiteLLMAdapter
from orcia_core.catalog._internal.seaweedfs_adapter import (
    SeaweedFsObjectStorageAdapter,
    SeaweedFsS3HttpBackend,
)
from orcia_core.observability._internal.otel_sqlalchemy import SqlAlchemyOtelInstrumenter
from orcia_core.observability.logging import (
    bind_trace_context,
    clear_trace_context,
    get_current_trace_context,
)
from orcia_core.orchestration import build_default_orchestration_setup_service
from orcia_core.orchestration._internal.dbos_engine import (
    DbosDurableWorkflowEngine,
    _execute_durable_step,
    _orcia_durable_run_workflow,
    _require_bound_runtime,
)
from orcia_core.orchestration._internal.sql_repository import SqlOrchestrationRepository
from orcia_core.orchestration.errors import ResourceNotFoundError
from orcia_core.rag._internal.sql_repository import SqlHybridRagRepository
from orcia_core.testing.cassette_llm import DeterministicCassetteLLM
from orcia_kernel.errors import ModelOrthogonalityViolationError
from orcia_kernel.ports import LlmPromptRequest
from orcia_worker.dbos_workflow_runner import (
    _dbos_step_execution,
    dbos_step_runner_workflow,
    execute_step_runner_job,
)


def test_seaweedfs_s3_http_backend_and_cas_adapter() -> None:
    """Verify SeaweedFS AWS SigV4 HTTP backend and CAS adapter (`ARCH-P6`)."""
    store: dict[str, bytes] = {}

    def handler(request: httpx.Request) -> httpx.Response:
        assert "Authorization" in request.headers
        assert request.headers["Authorization"].startswith("AWS4-HMAC-SHA256 Credential=")
        assert "x-amz-content-sha256" in request.headers
        path = request.url.path
        if request.method == "PUT":
            store[path] = request.read()
            return httpx.Response(200)
        if request.method == "GET":
            if path not in store:
                return httpx.Response(404)
            return httpx.Response(200, content=store[path])
        if request.method == "HEAD":
            return httpx.Response(200 if path in store else 404)
        return httpx.Response(405)

    client = httpx.Client(transport=httpx.MockTransport(handler))
    backend = SeaweedFsS3HttpBackend(
        endpoint_url="http://seaweedfs:8333",
        access_key="orcia_key",
        secret_key="orcia_secret",  # pragma: allowlist secret
        http_client=client,
    )
    adapter = SeaweedFsObjectStorageAdapter(backend=backend, bucket_name="orcia-cas")
    payload = b'{"hello":"seaweedfs"}'
    digest = hashlib.sha256(payload).hexdigest()

    stored = adapter.put_bytes(
        cas_key=digest,
        sha256=digest,
        source_uri="git://repo/file.json",
        content_bytes=payload,
    )
    assert stored.cas_key == f"cas/{digest}"
    assert backend.head_key("orcia-cas", stored.cas_key) is True
    assert backend.head_key("orcia-cas", "cas/missing") is False

    fetched = adapter.get_bytes(stored.cas_key)
    assert fetched is not None
    assert fetched.content_bytes == payload
    assert adapter.get_bytes("cas/missing") is None

    with pytest.raises(ValueError, match="CAS SHA-256 mismatch"):
        adapter.put_bytes(
            cas_key="cas/bad",
            sha256="f" * 64,
            source_uri="git://repo/file.json",
            content_bytes=payload,
        )

    store[f"/orcia-cas/{stored.cas_key}"] = b"corrupted"
    with pytest.raises(ValueError, match="Corrupted CAS object"):
        adapter.get_bytes(stored.cas_key)


@pytest.mark.asyncio
async def test_litellm_adapter_orthogonality_cassette_and_http_gateway() -> None:
    """Verify LiteLLMAdapter orthogonality (`AD-10`), cassette fallback, and HTTP gateway."""
    cassette = DeterministicCassetteLLM()
    adapter_cassette = LiteLLMAdapter(fallback_cassette=cassette)

    req_valid = LlmPromptRequest(
        model_family="openai",
        model_id="openai/gpt-4.1",
        system_prompt="You are an evaluator.",
        user_prompt="Evaluate artifact.",
        executor_model_family="anthropic",
    )
    res_cassette = await adapter_cassette.complete(req_valid)
    assert res_cassette.model_family == "openai"

    req_same_family = LlmPromptRequest(
        model_family="anthropic",
        model_id="anthropic/claude-3-5-haiku",
        system_prompt="You are an evaluator.",
        user_prompt="Evaluate artifact.",
        executor_model_family="anthropic",
    )
    with pytest.raises(ModelOrthogonalityViolationError):
        await adapter_cassette.complete(req_same_family)

    def llm_handler(request: httpx.Request) -> httpx.Response:
        assert request.headers["Authorization"] == "Bearer sk-test"
        assert "X-Trace-Id" in request.headers
        return httpx.Response(
            200,
            json={
                "choices": [{"message": {"content": '{"verdict":"PASS"}'}}],
                "usage": {"prompt_tokens": 20, "completion_tokens": 10},
            },
        )

    live_client = httpx.AsyncClient(transport=httpx.MockTransport(llm_handler))
    live_adapter = LiteLLMAdapter(
        base_url="http://litellm:4000/v1",
        api_key="sk-test",  # pragma: allowlist secret
        http_client=live_client,
    )
    live_res = await live_adapter.complete(req_valid)
    assert live_res.content == '{"verdict":"PASS"}'
    assert live_res.scenario_tag == "LITELLM_GATEWAY"
    assert live_res.input_tokens == 20
    assert live_res.output_tokens == 10
    await live_client.aclose()


def test_opentelemetry_trace_context_and_sqlalchemy_instrumenter() -> None:
    """Verify W3C trace_id propagation in OpenTelemetry SpanContext and SQLAlchemy hooks."""
    ctx = bind_trace_context("4bf92f3577b34da6a3ce929d0e0e4736")
    assert ctx.trace_id == "4bf92f3577b34da6a3ce929d0e0e4736"
    assert len(ctx.span_id) == 16
    assert ctx.traceparent == f"00-{ctx.trace_id}-{ctx.span_id}-01"

    active_span = otel_trace.get_current_span()
    span_ctx = active_span.get_span_context()
    assert span_ctx.is_valid is True
    assert f"{span_ctx.trace_id:032x}" == "4bf92f3577b34da6a3ce929d0e0e4736"

    ctx_inherited = bind_trace_context(
        None,
        workspace_id="ws-1",
        run_id="run-1",
        step_id="step-1",
    )
    assert ctx_inherited.trace_id == "4bf92f3577b34da6a3ce929d0e0e4736"
    assert get_current_trace_context().trace_id == "4bf92f3577b34da6a3ce929d0e0e4736"

    instrumenter = SqlAlchemyOtelInstrumenter(max_recorded_spans=1)
    dummy_url = "postgresql+asyncpg://orcia:orcia@localhost:5432/orcia"  # pragma: allowlist secret
    engine = create_async_engine(dummy_url)
    instrumenter.instrument_engine(engine)

    fake_conn = MagicMock()
    fake_conn.info = {}
    engine.sync_engine.dispatch.before_cursor_execute(fake_conn, None, "SELECT 1", (), None, False)
    engine.sync_engine.dispatch.after_cursor_execute(fake_conn, None, "SELECT 1", (), None, False)
    engine.sync_engine.dispatch.before_cursor_execute(fake_conn, None, "SELECT 2", (), None, False)
    engine.sync_engine.dispatch.after_cursor_execute(fake_conn, None, "SELECT 2", (), None, False)
    assert len(instrumenter.recorded_spans) == 1
    assert instrumenter.recorded_spans[0].trace_id == "4bf92f3577b34da6a3ce929d0e0e4736"
    assert instrumenter.recorded_spans[0].statement_prefix == "SELECT 2"

    instrumenter.clear()
    assert len(instrumenter.recorded_spans) == 0
    clear_trace_context()


@pytest.mark.asyncio
async def test_sql_repositories_and_dbos_engine_unit_paths() -> None:
    """Exercise unit error branches and row-mapping helpers on SqlOrchestrationRepository & Rag."""
    vec_str = SqlHybridRagRepository.format_halfvec_literal((0.5, -0.25), dim=4)
    assert vec_str == "[0.500000,-0.250000,0.000000,0.000000]"

    with pytest.raises(RuntimeError, match="is not launched"):
        _require_bound_runtime()

    engine = DbosDurableWorkflowEngine(
        system_database_url="postgresql://localhost/orcia",
        application_database_url="postgresql+asyncpg://localhost/orcia",
    )
    with pytest.raises(RuntimeError, match="must be launched before accessing uow"):
        _ = engine.uow
    with pytest.raises(RuntimeError, match="must be launched before accessing repository"):
        _ = engine.repository
    await engine.shutdown()

    mock_session = AsyncMock()
    mock_result = MagicMock()
    mock_result.fetchone.return_value = None
    mock_result.mappings.return_value.all.return_value = []
    mock_session.execute.return_value = mock_result

    class FakeUoW:
        @asynccontextmanager
        async def session_scope(self) -> AsyncIterator[Any]:
            yield mock_session

    repo = SqlOrchestrationRepository(FakeUoW())  # type: ignore[arg-type]
    await repo.upsert_workflow_run(
        run_id="0192c4e0-0000-7000-8000-000000000901",
        run_key="run-unit-1",
        workspace_id="0192c4e0-0000-7000-8000-000000000201",
        workflow_def_id="0192c4e0-0000-7000-8000-000000000501",
        parent_run_id=None,
        parent_step_execution_id=None,
        root_run_id="0192c4e0-0000-7000-8000-000000000901",
        nesting_depth=0,
        execution_regime="INTERACTIVE_COACHING",
        criticality="STANDARD",
        trigger_id=None,
        trigger_idempotency_key=None,
        status="INITIALIZED",
        initiated_by_user_id=None,
        execution_identity_mode="passthrough",
        budget_max_usd=10.0,
    )
    await repo.update_run_status("0192c4e0-0000-7000-8000-000000000901", "RUNNING")
    with pytest.raises(ResourceNotFoundError, match="introuvable en base SQL"):
        await repo.get_run_status("0192c4e0-0000-7000-8000-000000009999")

    mock_result.fetchone.return_value = ("RUNNING",)
    assert await repo.get_run_status("0192c4e0-0000-7000-8000-000000000901") == "RUNNING"

    step_entity = StepExecutionEntity(
        id="0192c4e0-0000-7000-8000-000000000902",
        step_execution_key="stepexec-unit-1",
        run_id="0192c4e0-0000-7000-8000-000000000901",
        step_key="step-1",
        step_index=0,
        step_type="AGENT",
        execution_mode="INTERACTIVE_COACHING",
        status="EXECUTING_AGENT",
        draft_artifact={"a": 1},
        step_memlog=(
            StepMemlogEntry(
                entry_id="m1",
                step_key="step-1",
                marker_type="REASONING",
                summary="s",
                details="d",
            ),
        ),
    )
    await repo.upsert_step_execution(step_entity)
    snap = await repo.append_snapshot(
        run_id=step_entity.run_id,
        step_execution_id=step_entity.id,
        step_key="step-1",
        branch_status="ACTIVE",
        artifact_payload={"a": 1},
        memlog_summary=step_entity.step_memlog,
    )
    assert snap.branch_status == "ACTIVE"

    mapped_step = SqlOrchestrationRepository._row_to_step_entity(
        {
            "id": step_entity.id,
            "step_execution_key": step_entity.step_execution_key,
            "run_id": step_entity.run_id,
            "step_key": "step-1",
            "step_index": 0,
            "step_type": "AGENT",
            "execution_mode": "INTERACTIVE_COACHING",
            "status": "COMMITTED",
            "attempt_count": 1,
            "max_agent_retries": 3,
            "draft_artifact_jsonb": '{"a":1}',
            "draft_cas_key": None,
            "step_memlog_jsonb": (
                '[{"entry_id":"m1","step_key":"step-1","marker_type":"REASONING",'
                '"summary":"s","details":"d","source_uris":[]}]'
            ),
            "hydrated_input_uris_jsonb": '["orcia://uri"]',
            "child_run_id": None,
            "committed_snapshot_id": snap.id,
            "cost_usd": 0.25,
        }
    )
    assert mapped_step.status == "COMMITTED"

    mapped_snap = SqlOrchestrationRepository._row_to_snapshot_entity(
        {
            "id": snap.id,
            "snapshot_key": snap.snapshot_key,
            "run_id": snap.run_id,
            "step_execution_id": snap.step_execution_id,
            "parent_snapshot_id": None,
            "step_key": "step-1",
            "branch_status": "ACTIVE",
            "artifact_payload_jsonb": '{"a":1}',
            "artifact_cas_key": snap.artifact_cas_key,
            "artifact_sha256": snap.artifact_sha256,
            "memlog_summary_jsonb": "[]",
            "superseded_snapshot_ids_jsonb": "[]",
        },
        "ACTIVE",
    )
    assert mapped_snap.id == snap.id

    svc = build_default_orchestration_setup_service()
    run_id = svc.runs[0].id
    res1 = execute_step_runner_job(
        run_id=run_id,
        step_key="frame-architecture-intent",
        trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
        orchestration_service=svc,
    )
    assert res1.already_committed is False
    res2 = execute_step_runner_job(
        run_id=run_id,
        step_key="frame-architecture-intent",
        trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
        orchestration_service=svc,
    )
    assert res2.already_committed is True

    raw_step = inspect.unwrap(_dbos_step_execution)
    raw_wf = inspect.unwrap(dbos_step_runner_workflow)
    assert callable(raw_step)
    assert callable(raw_wf)
    assert callable(inspect.unwrap(_execute_durable_step))
    assert callable(inspect.unwrap(_orcia_durable_run_workflow))
