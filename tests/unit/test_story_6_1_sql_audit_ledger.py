"""Unit tests for SqlAuditLedgerService and row mapping (`Story 6.1`)."""

from __future__ import annotations

import json
import uuid
from datetime import UTC, datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from orcia_core.audit_finops._internal.sql_audit_ledger import (
    SqlAuditLedgerService,
    _parse_row_to_entry,
)
from orcia_core.audit_finops.models import AuditLedgerFilterParams
from orcia_core.ports.finops_telemetry import FinopsCostLedgerEntry


def test_row_to_entry_complete_mapping() -> None:
    """Verify _row_to_entry accurately parses all DB columns into domain model."""
    entry_id = str(uuid.uuid4())
    source_evt_id = str(uuid.uuid4())
    run_id = str(uuid.uuid4())
    now = datetime.now(UTC)

    row = {
        "id": entry_id,
        "source_event_id": source_evt_id,
        "workspace_id": str(uuid.uuid4()),
        "org_unit_id": str(uuid.uuid4()),
        "scope_path": "Direction/Direction Produit",
        "run_id": run_id,
        "root_run_id": run_id,
        "step_execution_id": str(uuid.uuid4()),
        "actor_type": "AGENT",
        "actor_id": "amelia",
        "actor_display_name": "Amelia Dev",
        "actor_email": "amelia@orcia.local",
        "event_type": "StepCompleted",
        "summary": "Étape terminée",
        "model_id": "qwen2.5-coder",
        "inference_tier": "HEAVY",
        "effort": "HIGH",
        "input_tokens": 1200,
        "output_tokens": 300,
        "cost_usd": 0.0035,
        "cost_source": "INTERNAL_VERIFIED",
        "native_metric_type": "tok",
        "native_metric_value": 1500.0,
        "native_currency": "USD",
        "reported_by_remote": False,
        "latency_ms": 420,
        "trace_id": "00000000000000000000000000000001",
        "run_lock_sha256": "sha256-abc",
        "pre_prompt_sha256": "sha256-def",
        "workflow_contract_sha256": "sha256-ghi",
        "cas_references_jsonb": ["seaweedfs://blobs/sha-1"],
        "metadata_jsonb": {"step": "build"},
        "created_at": now,
    }

    entry = _parse_row_to_entry(row)
    assert entry.id == entry_id
    assert entry.source_event_id == source_evt_id
    assert entry.actor_display_name == "Amelia Dev"
    assert entry.input_tokens == 1200
    assert entry.output_tokens == 300
    assert entry.cost_usd == 0.0035
    assert entry.cas_references == ["seaweedfs://blobs/sha-1"]
    assert entry.metadata == {"step": "build"}


def test_row_to_entry_minimal_mapping() -> None:
    """Verify _row_to_entry handles rows with optional/null fields."""
    entry_id = str(uuid.uuid4())
    source_evt_id = str(uuid.uuid4())

    row = {
        "id": entry_id,
        "source_event_id": source_evt_id,
        "workspace_id": None,
        "org_unit_id": None,
        "scope_path": None,
        "run_id": None,
        "root_run_id": None,
        "step_execution_id": None,
        "actor_type": None,
        "actor_id": None,
        "actor_display_name": None,
        "actor_email": None,
        "event_type": None,
        "summary": None,
        "model_id": None,
        "inference_tier": None,
        "effort": None,
        "input_tokens": None,
        "output_tokens": None,
        "cost_usd": None,
        "cost_source": None,
        "native_metric_type": None,
        "native_metric_value": None,
        "native_currency": None,
        "reported_by_remote": None,
        "latency_ms": None,
        "trace_id": None,
        "run_lock_sha256": None,
        "pre_prompt_sha256": None,
        "workflow_contract_sha256": None,
        "cas_references_jsonb": json.dumps(["cas-blob"]),
        "metadata_jsonb": json.dumps({"note": "ok"}),
        "created_at": None,
    }

    entry = _parse_row_to_entry(row)
    assert entry.id == entry_id
    assert entry.source_event_id == source_evt_id
    assert entry.scope_path == "GLOBAL"
    assert entry.actor_type == "USER"
    assert entry.cost_usd == 0.0
    assert entry.cas_references == ["cas-blob"]
    assert entry.metadata == {"note": "ok"}


@pytest.mark.asyncio
async def test_sql_audit_ledger_record_entry_with_mock_conn() -> None:
    """Verify record_entry executes parameterised INSERT with ON CONFLICT."""
    mock_conn = AsyncMock()
    mock_result = MagicMock()
    service = SqlAuditLedgerService()
    entry = FinopsCostLedgerEntry(
        id=str(uuid.uuid4()),
        source_event_id=str(uuid.uuid4()),
        workspace_id=str(uuid.uuid4()),
        actor_type="ADMIN_CONNECTION_TEST",
        actor_id="admin-1",
        actor_display_name="Romain Admin",
        event_type="AdminConnectionTested",
        summary="Test de connexion MCP GitHub",
        cost_usd=0.0,
        latency_ms=88,
        trace_id="00000000000000000000000000000000",
    )
    mock_result.fetchone.return_value = [entry.id]
    mock_conn.execute.return_value = mock_result

    rec_id = await service.record_entry(entry, conn=mock_conn)
    assert rec_id == entry.id
    assert mock_conn.execute.call_count == 1
    call_sql = str(mock_conn.execute.call_args[0][0])
    assert "INSERT INTO audit_ledger" in call_sql
    assert "ON CONFLICT (source_event_id) DO NOTHING" in call_sql


@pytest.mark.asyncio
async def test_sql_audit_ledger_list_entries_with_filters() -> None:
    """Verify list_entries dynamically constructs WHERE clauses and returns entries."""
    mock_conn = AsyncMock()
    mock_engine = MagicMock()
    mock_engine.connect.return_value.__aenter__.return_value = mock_conn

    entry_id = str(uuid.uuid4())
    mock_row = {
        "id": entry_id,
        "source_event_id": str(uuid.uuid4()),
        "workspace_id": None,
        "org_unit_id": None,
        "scope_path": "GLOBAL",
        "run_id": None,
        "root_run_id": None,
        "step_execution_id": None,
        "actor_type": "USER",
        "actor_id": "u-1",
        "actor_display_name": "Romain",
        "actor_email": "romain@orcia.local",
        "event_type": "SettingsChanged",
        "summary": "Paramètre modifié",
        "model_id": None,
        "inference_tier": None,
        "effort": None,
        "input_tokens": 0,
        "output_tokens": 0,
        "cost_usd": 0.0,
        "cost_source": "INTERNAL_VERIFIED",
        "native_metric_type": None,
        "native_metric_value": None,
        "native_currency": None,
        "reported_by_remote": False,
        "latency_ms": 10,
        "trace_id": "00000000000000000000000000000000",
        "run_lock_sha256": None,
        "pre_prompt_sha256": None,
        "workflow_contract_sha256": None,
        "cas_references_jsonb": [],
        "metadata_jsonb": {},
        "created_at": datetime.now(UTC),
    }

    # First call: count, Second call: rows
    mock_count_res = MagicMock()
    mock_count_res.scalar_one.return_value = 1
    mock_rows_res = MagicMock()
    mock_rows_res.mappings.return_value.all.return_value = [mock_row]

    mock_conn.execute.side_effect = [mock_count_res, mock_rows_res]

    service = SqlAuditLedgerService(engine=mock_engine)
    filters = AuditLedgerFilterParams(
        scope_path="GLOBAL",
        actor_query="romain",
        event_type="SettingsChanged",
        time_window="24H",
        limit=50,
        offset=0,
    )

    entries, total = await service.list_entries(params=filters)
    assert total == 1
    assert len(entries) == 1
    assert entries[0].id == entry_id
    assert mock_conn.execute.call_count == 2


@pytest.mark.asyncio
async def test_sql_audit_ledger_get_run_provenance_and_manifest_sha() -> None:
    """Verify get_run_provenance_entries and get_run_lock_manifest_sha execution."""
    mock_conn = AsyncMock()
    mock_engine = MagicMock()
    mock_engine.connect.return_value.__aenter__.return_value = mock_conn

    run_id = str(uuid.uuid4())
    mock_row = {
        "id": str(uuid.uuid4()),
        "source_event_id": str(uuid.uuid4()),
        "workspace_id": None,
        "org_unit_id": None,
        "scope_path": "GLOBAL",
        "run_id": run_id,
        "root_run_id": None,
        "step_execution_id": None,
        "actor_type": "AGENT",
        "actor_id": "amelia",
        "actor_display_name": "Amelia",
        "actor_email": None,
        "event_type": "StepCompleted",
        "summary": "OK",
        "model_id": None,
        "inference_tier": None,
        "effort": None,
        "input_tokens": 100,
        "output_tokens": 50,
        "cost_usd": 0.001,
        "cost_source": "INTERNAL_VERIFIED",
        "native_metric_type": None,
        "native_metric_value": None,
        "native_currency": None,
        "reported_by_remote": False,
        "latency_ms": 20,
        "trace_id": "00000000000000000000000000000000",
        "run_lock_sha256": "manifest-sha-999",
        "pre_prompt_sha256": None,
        "workflow_contract_sha256": None,
        "cas_references_jsonb": [],
        "metadata_jsonb": {},
        "created_at": datetime.now(UTC),
    }

    mock_rows_res = MagicMock()
    mock_rows_res.mappings.return_value.all.return_value = [mock_row]

    mock_sha_res = MagicMock()
    mock_sha_res.fetchone.return_value = ["manifest-sha-999"]

    mock_conn.execute.side_effect = [mock_rows_res, mock_sha_res]

    service = SqlAuditLedgerService(engine=mock_engine)
    entries = await service.get_run_provenance_entries(run_id)
    assert len(entries) == 1
    assert entries[0].run_id == run_id

    sha = await service.get_run_lock_manifest_sha(run_id)
    assert sha == "manifest-sha-999"


@pytest.mark.asyncio
async def test_sql_audit_ledger_fallbacks_no_engine() -> None:
    """Verify fallback behavior when service runs without DB engine and without conn."""
    service = SqlAuditLedgerService(engine=None)
    entry = FinopsCostLedgerEntry(
        source_event_id=str(uuid.uuid4()),
        actor_type="USER",
        actor_id="u1",
        event_type="StepCompleted",
        summary="Test fallback",
        cost_usd=0.0,
        trace_id="00000000000000000000000000000000",
    )
    rec_id = await service.record_entry(entry)
    assert rec_id is not None

    entries, total = await service.list_entries(AuditLedgerFilterParams())
    assert entries == []
    assert total == 0

    prov = await service.get_run_provenance_entries(str(uuid.uuid4()))
    assert prov == []

    sha = await service.get_run_lock_manifest_sha(str(uuid.uuid4()))
    assert sha is None

    # Invalid UUID string
    assert await service.get_run_lock_manifest_sha("not-a-uuid", conn=AsyncMock()) is None


@pytest.mark.asyncio
async def test_sql_audit_ledger_record_entry_on_conflict_fallback() -> None:
    """Verify record_entry handles ON CONFLICT DO NOTHING by looking up existing ID."""
    mock_conn = AsyncMock()
    mock_insert_res = MagicMock()
    mock_insert_res.fetchone.return_value = None  # Conflict: nothing inserted
    existing_id = str(uuid.uuid4())
    mock_lookup_res = MagicMock()
    mock_lookup_res.fetchone.return_value = [existing_id]

    mock_conn.execute.side_effect = [mock_insert_res, mock_lookup_res]

    service = SqlAuditLedgerService()
    entry = FinopsCostLedgerEntry(
        id=str(uuid.uuid4()),
        source_event_id=str(uuid.uuid4()),
        actor_type="AGENT",
        actor_id="amelia",
        event_type="StepCompleted",
        summary="Retried step",
        cost_usd=0.0,
        trace_id="00000000000000000000000000000000",
    )
    res_id = await service.record_entry(entry, conn=mock_conn)
    assert res_id == existing_id
    assert mock_conn.execute.call_count == 2


@pytest.mark.asyncio
async def test_sql_audit_ledger_list_entries_all_filters() -> None:
    """Verify all WHERE branches (workspace, actor_type, actor_id, run_id, dates, time_windows)."""
    mock_conn = AsyncMock()
    mock_count = MagicMock()
    mock_count.scalar_one.return_value = 0
    mock_rows = MagicMock()
    mock_rows.mappings.return_value.all.return_value = []
    mock_conn.execute.side_effect = [mock_count, mock_rows] * 3

    service = SqlAuditLedgerService()

    # 1. 1H window with dates and specific ids
    p1 = AuditLedgerFilterParams(
        workspace_id=str(uuid.uuid4()),
        actor_type="AGENT",
        actor_id="amelia",
        run_id=str(uuid.uuid4()),
        time_window="1H",
        date_from="2026-11-01",
        date_to="2026-11-02",
    )
    await service.list_entries(p1, conn=mock_conn)

    # 2. 7D window
    p2 = AuditLedgerFilterParams(time_window="7D")
    await service.list_entries(p2, conn=mock_conn)

    # 3. 30D window
    p3 = AuditLedgerFilterParams(time_window="30D")
    await service.list_entries(p3, conn=mock_conn)
