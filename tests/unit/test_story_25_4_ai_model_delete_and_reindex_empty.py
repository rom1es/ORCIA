"""Unit tests for Story 25.4: AI Model delete guards and empty corpus counts."""

from __future__ import annotations

from contextlib import asynccontextmanager
from dataclasses import dataclass
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient
from tests.unit.fakes.in_memory_reindex import default_in_memory_reindex_manager

from orcia_api.main import create_app
from orcia_api.routers._ai_models_reindex_helpers import _row_to_status_response
from orcia_core.orchestration._internal._sql_ai_model_delete_guards import (
    ACTIVE_WORKFLOW_RUN_STATUSES,
    delete_or_drain_ai_model_mapping_pg18,
    evaluate_ai_model_delete_impact_pg18,
)
from orcia_core.orchestration._internal.sql_ai_model_mutations import (
    _parse_iso_to_dt,
    create_ai_model_mapping_pg18,
    update_ai_model_mapping_pg18,
)
from orcia_core.orchestration.ai_models_errors import LastTierModelInUseError
from orcia_core.orchestration.ai_models_records import AiModelMappingRecord
from orcia_core.orchestration.errors import (
    ObserverModeReadOnlyError,
    ResourcePinnedByActiveRunsError,
)
from orcia_core.permissions.crypto import PassthroughVaultCipher
from orcia_core.permissions.secret_hint import SecretInputSpec, SecretStatusView
from orcia_core.rag._internal.sql_reindex_jobs import count_indexed_corpus_pg18
from orcia_core.rag.errors import RagReindexInProgressError
from orcia_core.rag.models import RagReindexJobRecord
from orcia_core.rag.reindex import check_rag_operational_on_conn, execute_rag_reindex_job


def _sample_mapping(
    *,
    mapping_id: str = "0195f000-0000-7000-8000-000000000101",
    inference_tier: str = "medium",
    model_name: str = "claude-3-7-sonnet",
    draining: bool = False,
    is_active: bool = True,
) -> AiModelMappingRecord:
    return AiModelMappingRecord(
        id=mapping_id,
        scope_level="GLOBAL",
        scope_id="0195f000-0000-7000-8000-000000000001",
        display_name="Test Model",
        inference_tier=inference_tier,  # type: ignore[arg-type]
        effort="balanced",
        provider_slug="anthropic",
        model_family="Anthropic",
        model_name=model_name,
        fallback_model_name=None,
        endpoint_uri="https://api.anthropic.com/v1",
        auth_mode="none_local",
        protocol_mode="openai_compatible",
        env_var_name=None,
        encrypted_api_key=None,
        secret_status=SecretStatusView(
            configured=False,
            fingerprint=None,
            masked_hint=None,
            updated_at=None,
            updated_by=None,
        ),
        fallback_order=1,
        is_active=is_active,
        draining=draining,
        health_status="OPERATIONAL",
        last_latency_ms=42,
        last_tested_at=None,
        created_at="2026-11-20T00:00:00Z",
        updated_at="2026-11-20T00:00:00Z",
    )


@dataclass
class _FakeResult:
    scalar_value: Any = None
    rows: list[tuple[Any, ...]] | None = None
    first_row: tuple[Any, ...] | None = None

    def scalar_one_or_none(self) -> Any:
        return self.scalar_value

    def fetchall(self) -> list[tuple[Any, ...]]:
        return self.rows or []

    def first(self) -> tuple[Any, ...] | None:
        return self.first_row


def _make_fake_conn(
    *,
    other_active_count: int = 0,
    active_run_rows: list[tuple[Any, ...]] | None = None,
    raise_on_runs_query: bool = False,
) -> tuple[MagicMock, list[str]]:
    executed_sql: list[str] = []

    @asynccontextmanager
    async def _begin_nested():
        yield None

    async def _execute(stmt: Any, params: dict[str, Any] | None = None) -> _FakeResult:
        sql_text = str(stmt)
        executed_sql.append(sql_text)
        if "FROM workspace_llm_tier_mappings" in sql_text and "COUNT(*)" in sql_text:
            return _FakeResult(scalar_value=other_active_count)
        if "FROM workflow_runs wr" in sql_text:
            if raise_on_runs_query:
                raise RuntimeError("transient sql error")
            return _FakeResult(rows=active_run_rows or [])
        return _FakeResult()

    conn = MagicMock()
    conn.begin_nested = _begin_nested
    conn.execute = AsyncMock(side_effect=_execute)
    return conn, executed_sql


@pytest.mark.asyncio
async def test_delete_impact_ignores_static_workflow_definitions_and_allows_last_model_deletion(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Static workflow_definitions_v2 containing tier name ('medium') must never block deletion."""
    mapping = _sample_mapping(inference_tier="medium")
    monkeypatch.setattr(
        "orcia_core.orchestration._internal._sql_ai_model_delete_guards.get_ai_model_mapping_pg18",
        AsyncMock(return_value=mapping),
    )

    conn, executed_sql = _make_fake_conn(other_active_count=0, active_run_rows=[])

    impact = await evaluate_ai_model_delete_impact_pg18(conn, mapping.id)
    assert impact.is_last_active_for_tier is True
    assert impact.dependent_workflows_count == 0
    assert impact.pinned_active_runs_count == 0
    # Must never query static workflow_definitions_v2 with ILIKE
    assert all("workflow_definitions_v2" not in sql for sql in executed_sql)
    assert all("ILIKE" not in sql.upper() for sql in executed_sql)

    deleted = await delete_or_drain_ai_model_mapping_pg18(
        conn, mapping.id, mode="reject", actor_role="PLATFORM_ADMIN"
    )
    assert deleted is None
    assert any("DELETE FROM workspace_llm_tier_mappings" in sql for sql in executed_sql)


@pytest.mark.asyncio
async def test_delete_guard_blocks_with_409_only_when_active_or_paused_run_pins_model(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Only active/paused workflow_runs joined with inference_attempts trigger 409 blocking."""
    mapping = _sample_mapping(inference_tier="medium")
    drained_mapping = _sample_mapping(inference_tier="medium", draining=True, is_active=False)
    get_mock = AsyncMock(
        side_effect=[mapping, mapping, mapping, mapping, drained_mapping, mapping, mapping]
    )
    monkeypatch.setattr(
        "orcia_core.orchestration._internal._sql_ai_model_delete_guards.get_ai_model_mapping_pg18",
        get_mock,
    )

    # 1. Last active model for tier + active/paused workflow_run -> LastTierModelInUseError (409)
    conn_last, executed_sql = _make_fake_conn(
        other_active_count=0,
        active_run_rows=[("run-active-1", "wf-def-1"), ("run-active-1", None)],
    )
    impact = await evaluate_ai_model_delete_impact_pg18(conn_last, mapping.id)
    assert impact.pinned_active_runs_count == 1
    assert impact.dependent_workflows_count == 1
    assert impact.pinned_run_ids == ("run-active-1",)
    assert impact.dependent_workflow_ids == ("wf-def-1",)
    assert any(
        all(status in sql for status in ("INITIALIZED", "RUNNING", "PAUSED"))
        for sql in executed_sql
        if "FROM workflow_runs wr" in sql
    )
    assert "PAUSED" in ACTIVE_WORKFLOW_RUN_STATUSES

    with pytest.raises(LastTierModelInUseError) as exc_last:
        await delete_or_drain_ai_model_mapping_pg18(conn_last, mapping.id, mode="reject")
    assert exc_last.value.http_status == 409

    # 2. Not last active model for tier + pinned active run -> ResourcePinnedByActiveRunsError (409)
    conn_other, _ = _make_fake_conn(
        other_active_count=1,
        active_run_rows=[("run-active-2", "wf-def-2")],
    )
    with pytest.raises(ResourcePinnedByActiveRunsError) as exc_pinned:
        await delete_or_drain_ai_model_mapping_pg18(conn_other, mapping.id, mode="reject")
    assert exc_pinned.value.http_status == 409

    # 3. Drain mode transitions to draining=TRUE, is_active=FALSE
    drained = await delete_or_drain_ai_model_mapping_pg18(conn_other, mapping.id, mode="drain")
    assert drained is not None
    assert drained.draining is True
    assert drained.is_active is False

    # 4. Observer role always raises 403
    with pytest.raises(ObserverModeReadOnlyError):
        await delete_or_drain_ai_model_mapping_pg18(
            conn_other, mapping.id, mode="force", actor_role="OBSERVER"
        )

    # 5. Force mode deletes despite pinned run
    forced = await delete_or_drain_ai_model_mapping_pg18(conn_other, mapping.id, mode="force")
    assert forced is None


@pytest.mark.asyncio
async def test_delete_impact_handles_runs_query_failure_gracefully(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mapping = _sample_mapping(inference_tier="simple")
    monkeypatch.setattr(
        "orcia_core.orchestration._internal._sql_ai_model_delete_guards.get_ai_model_mapping_pg18",
        AsyncMock(return_value=mapping),
    )
    conn, _ = _make_fake_conn(other_active_count=0, raise_on_runs_query=True)

    impact = await evaluate_ai_model_delete_impact_pg18(conn, mapping.id)
    assert impact.pinned_active_runs_count == 0
    assert impact.dependent_workflows_count == 0


@pytest.mark.asyncio
async def test_count_indexed_corpus_pg18_and_status_response_counts() -> None:
    """count_indexed_corpus_pg18 and _row_to_status_response expose chunk and doc counts."""
    conn_empty = MagicMock()
    conn_empty.execute = AsyncMock(return_value=_FakeResult(first_row=None))
    assert await count_indexed_corpus_pg18(conn_empty) == (0, 0)

    conn_zero = MagicMock()
    conn_zero.execute = AsyncMock(return_value=_FakeResult(first_row=(0, 0)))
    assert await count_indexed_corpus_pg18(conn_zero) == (0, 0)

    conn_populated = MagicMock()
    conn_populated.execute = AsyncMock(return_value=_FakeResult(first_row=(42, 7)))
    assert await count_indexed_corpus_pg18(conn_populated) == (42, 7)

    idle_resp = _row_to_status_response(None, indexed_chunks_count=0, indexed_documents_count=0)
    assert idle_resp.status == "IDLE"
    assert idle_resp.indexed_chunks_count == 0
    assert idle_resp.indexed_documents_count == 0

    job = RagReindexJobRecord(
        id="0195f000-0000-7000-8000-000000000999",
        target_model_id="0195f000-0000-7000-8000-000000000888",
        target_model_name="text-embedding-3-small",
        status="COMPLETED",
        total_chunks=42,
        processed_chunks=42,
        progress_percentage=100,
        error_message=None,
        created_at="2026-11-20T00:00:00Z",
        started_at="2026-11-20T00:00:01Z",
        completed_at="2026-11-20T00:00:05Z",
        updated_at="2026-11-20T00:00:05Z",
        created_by="admin",
        cancelled_by_job_id=None,
    )
    job_resp = _row_to_status_response(job, indexed_chunks_count=42, indexed_documents_count=7)
    assert job_resp.status == "COMPLETED"
    assert job_resp.indexed_chunks_count == 42
    assert job_resp.indexed_documents_count == 7


def test_reindex_status_endpoint_exposes_zero_counts_on_empty_corpus() -> None:
    default_in_memory_reindex_manager.clear()
    app = create_app()
    app.state.reindex_manager = default_in_memory_reindex_manager
    client = TestClient(app)

    res = client.get("/api/v1/settings/ai-models/reindex-status")
    assert res.status_code == 200
    body = res.json()
    assert body["status"] == "IDLE"
    assert body["indexed_chunks_count"] == 0
    assert body["indexed_documents_count"] == 0


@pytest.mark.asyncio
async def test_sql_ai_model_mutations_embedding_and_parse_iso_branches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    assert _parse_iso_to_dt(None) is None
    assert _parse_iso_to_dt("not-an-iso") is None
    assert _parse_iso_to_dt("2026-11-20T10:00:00Z") is not None

    emb_mapping = AiModelMappingRecord(
        id="0195f000-0000-7000-8000-000000000202",
        scope_level="GLOBAL",
        scope_id="0195f000-0000-7000-8000-000000000001",
        display_name="OpenAI Embedding",
        inference_tier="simple",
        effort="balanced",
        provider_slug="openai",
        model_family="OpenAI",
        model_name="text-embedding-3-small",
        fallback_model_name=None,
        endpoint_uri="https://api.openai.com/v1",
        auth_mode="none_local",
        protocol_mode="openai_compatible",
        usage="embedding",
        env_var_name=None,
        encrypted_api_key=None,
        secret_status=SecretStatusView(
            configured=False,
            fingerprint=None,
            masked_hint=None,
            updated_at=None,
            updated_by=None,
        ),
        fallback_order=2,
        is_active=True,
        draining=False,
        health_status="OPERATIONAL",
        last_latency_ms=10,
        last_tested_at=None,
        created_at="2026-11-20T00:00:00Z",
        updated_at="2026-11-20T00:00:00Z",
    )
    monkeypatch.setattr(
        "orcia_core.orchestration._internal.sql_ai_model_mutations.get_ai_model_mapping_pg18",
        AsyncMock(return_value=emb_mapping),
    )

    executed_sql: list[str] = []

    async def _exec(stmt: Any, params: dict[str, Any] | None = None) -> MagicMock:
        sql_text = str(stmt)
        executed_sql.append(sql_text)
        res = MagicMock()
        res.scalar.return_value = 2
        return res

    conn = MagicMock()
    conn.execute = AsyncMock(side_effect=_exec)
    cipher = PassthroughVaultCipher(master_key=b"0" * 32)

    created = await create_ai_model_mapping_pg18(
        conn,
        cipher=cipher,
        scope_level="GLOBAL",
        scope_id="0195f000-0000-7000-8000-000000000001",
        display_name="OpenAI Embedding",
        inference_tier="simple",
        effort="balanced",
        provider_slug="openai",
        model_family="OpenAI",
        model_name="text-embedding-3-small",
        endpoint_uri="https://api.openai.com/v1",
        auth_mode="none_local",
        protocol_mode="openai_compatible",
        usage="embedding",
    )
    assert created.usage == "embedding"
    assert any(
        "UPDATE workspace_llm_tier_mappings SET is_active = FALSE" in s for s in executed_sql
    )

    updated = await update_ai_model_mapping_pg18(
        conn,
        emb_mapping.id,
        cipher=cipher,
        display_name="OpenAI Embedding Updated",
        usage="embedding",
        is_active=True,
        secret_input=SecretInputSpec(action="keep"),
    )
    assert updated.id == emb_mapping.id


@pytest.mark.asyncio
async def test_rag_reindex_failed_check_and_exception_recovery(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    failed_job = RagReindexJobRecord(
        id="job-fail-1",
        target_model_id="mod-1",
        target_model_name="text-embedding-3-small",
        status="FAILED",
        total_chunks=10,
        processed_chunks=3,
        progress_percentage=30,
        error_message="Provider timeout",
    )
    monkeypatch.setattr(
        "orcia_core.rag.reindex.get_active_reindex_job_pg18",
        AsyncMock(return_value=None),
    )
    monkeypatch.setattr(
        "orcia_core.rag.reindex.get_latest_reindex_job_pg18",
        AsyncMock(return_value=failed_job),
    )
    with pytest.raises(RagReindexInProgressError) as exc:
        await check_rag_operational_on_conn(MagicMock())
    assert "Provider timeout" in str(exc.value)

    @asynccontextmanager
    async def _begin():
        yield MagicMock()

    engine = MagicMock()
    engine.begin = _begin

    monkeypatch.setattr(
        "orcia_core.rag.reindex.get_reindex_job_by_id_pg18",
        AsyncMock(side_effect=RuntimeError("db connection lost")),
    )
    monkeypatch.setattr(
        "orcia_core.rag.reindex.fail_reindex_job_pg18",
        AsyncMock(return_value=failed_job),
    )
    embedding_port = MagicMock()
    res = await execute_rag_reindex_job(
        engine=engine,
        job_id="job-fail-1",
        target_model_id="mod-1",
        embedding_port=embedding_port,
    )
    assert res.status == "FAILED"
