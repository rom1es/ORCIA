"""Unit tests for Story 6.1 core models & provenance (`AD-20`, `AD-24.6`)."""

from __future__ import annotations

import importlib.util
import uuid
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

from orcia_core.audit_finops.errors import AuditRunNotFoundError
from orcia_core.audit_finops.models import (
    AuditLedgerEntry,
    AuditLedgerFilterParams,
    AuditProvenanceSummary,
)
from orcia_core.audit_finops.provenance_exporter import ProvenanceExporterService


def test_alembic_migration_story_6_1_upgrade_downgrade() -> None:
    """Verify migration 20261116_0601 is valid, reversible, and executes expected DDL."""
    mig_path = Path("infra/migrations/versions/20261116_0601_story_6_1_audit_ledger_append_only.py")
    spec = importlib.util.spec_from_file_location("mig_6_1", mig_path)
    assert spec is not None and spec.loader is not None
    mig_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mig_mod)

    assert mig_mod.revision == "20261116_0601"
    assert mig_mod.down_revision == "20261115_2359"

    mock_op = MagicMock()
    mig_mod.op = mock_op

    # Test upgrade
    mig_mod.upgrade()
    assert mock_op.execute.call_count >= 4
    upgrade_sql = " ".join(str(call[0][0]) for call in mock_op.execute.call_args_list)
    assert "CREATE TABLE IF NOT EXISTS audit_ledger" in upgrade_sql
    assert "prevent_audit_ledger_mutation" in upgrade_sql
    assert "ERR_AUDIT_LEDGER_IMMUTABLE" in upgrade_sql
    assert "AdminConnectionTested" in upgrade_sql
    assert "BudgetCircuitTripped" in upgrade_sql

    mock_op.reset_mock()

    # Test downgrade
    mig_mod.downgrade()
    assert mock_op.execute.call_count >= 3
    downgrade_sql = " ".join(str(call[0][0]) for call in mock_op.execute.call_args_list)
    assert "DROP TRIGGER IF EXISTS prevent_audit_ledger_mutation ON audit_ledger" in downgrade_sql
    assert "DROP FUNCTION IF EXISTS prevent_audit_ledger_mutation()" in downgrade_sql
    assert "DROP TABLE IF EXISTS audit_ledger" in downgrade_sql


def test_audit_ledger_entry_and_filter_models() -> None:
    """Verify domain models instantiation and properties."""
    entry_id = str(uuid.uuid4())
    source_evt_id = str(uuid.uuid4())
    entry = AuditLedgerEntry(
        id=entry_id,
        source_event_id=source_evt_id,
        workspace_id="ws-demo",
        actor_type="ADMIN_CONNECTION_TEST",
        actor_id="admin-1",
        actor_display_name="Romain Admin",
        actor_email="admin@orcia.local",
        event_type="AdminConnectionTested",
        summary="Test de connecteur SDLC validé",
        latency_ms=120,
        cost_usd=0.0005,
        input_tokens=150,
        output_tokens=50,
        metadata={"target": "mcp_github"},
    )
    assert entry.id == entry_id
    assert entry.source_event_id == source_evt_id
    assert entry.actor_type == "ADMIN_CONNECTION_TEST"
    assert entry.cost_usd == 0.0005

    filters = AuditLedgerFilterParams(
        actor_query="romain",
        limit=100,
        time_window="24H",
    )
    assert filters.actor_query == "romain"
    assert filters.limit == 100
    assert filters.time_window == "24H"


@pytest.mark.asyncio
async def test_provenance_exporter_summary_and_export_aligned() -> None:
    """Verify provenance exporter computes alignment, metrics and formats JSON/MD."""
    mock_sink = AsyncMock()
    run_id = str(uuid.uuid4())
    step_id = str(uuid.uuid4())
    expected_sha = (
        "abcdef1234567890abcdef1234567890"  # pragma: allowlist secret
        "abcdef1234567890abcdef1234567890"  # pragma: allowlist secret
    )

    entries = [
        AuditLedgerEntry(
            id=str(uuid.uuid4()),
            source_event_id=str(uuid.uuid4()),
            workspace_id="ws-1",
            run_id=run_id,
            step_execution_id=step_id,
            actor_type="AGENT",
            actor_id="agent-analyst",
            actor_display_name="Amelia Dev",
            event_type="StepCompleted",
            summary="Étape 1 complétée avec succès",
            input_tokens=1000,
            output_tokens=500,
            cost_usd=0.003,
            run_lock_sha256=expected_sha,
            cas_references=["seaweedfs://blobs/sha256-spec"],
        ),
        AuditLedgerEntry(
            id=str(uuid.uuid4()),
            source_event_id=str(uuid.uuid4()),
            workspace_id="ws-1",
            run_id=run_id,
            step_execution_id=step_id,
            actor_type="GATE",
            actor_id="gate-evaluator",
            actor_display_name="Gate Evaluator",
            event_type="GateEvaluated",
            summary="Gate passed",
            input_tokens=200,
            output_tokens=100,
            cost_usd=0.0006,
            run_lock_sha256=expected_sha,
            cas_references=["seaweedfs://blobs/sha256-rep"],
        ),
    ]

    mock_sink.get_run_provenance_entries.return_value = entries
    mock_sink.get_run_lock_manifest_sha.return_value = expected_sha

    service = ProvenanceExporterService(ledger_service=mock_sink)

    # 1. Summary
    summary = await service.get_provenance_summary(run_id)
    assert isinstance(summary, AuditProvenanceSummary)
    assert summary.run_id == run_id
    assert summary.is_run_lock_aligned is True
    assert summary.total_events == 2
    assert summary.total_input_tokens == 1200
    assert summary.total_output_tokens == 600
    assert round(summary.total_cost_usd, 4) == 0.0036

    # 2. JSON Export
    json_export = await service.export_dossier(run_id, export_format="json")
    assert json_export.format == "json"
    assert json_export.run_id == run_id
    assert json_export.entries_count == 2
    import json

    parsed_json = json.loads(json_export.content)
    assert parsed_json["certification"]["is_run_lock_aligned"] is True
    assert len(parsed_json["events_timeline"]) == 2

    # 3. Markdown Export
    md_export = await service.export_dossier(run_id, export_format="md")
    assert md_export.format == "md"
    assert f"# Dossier de Provenance & d'Audit Immuable — Exécution `{run_id}`" in md_export.content
    assert "CONFORME (100 % ALIGNÉ)" in md_export.content
    assert "seaweedfs://blobs/sha256-spec" in md_export.content


@pytest.mark.asyncio
async def test_provenance_exporter_divergence_detected() -> None:
    """Verify that provenance exporter detects run_lock SHA divergence."""
    mock_sink = AsyncMock()
    run_id = str(uuid.uuid4())
    entry = AuditLedgerEntry(
        id=str(uuid.uuid4()),
        source_event_id=str(uuid.uuid4()),
        workspace_id="ws-1",
        run_id=run_id,
        actor_type="AGENT",
        actor_id="amelia",
        event_type="StepCompleted",
        summary="Drifted run",
        run_lock_sha256="sha-original",
    )
    mock_sink.get_run_provenance_entries.return_value = [entry]
    mock_sink.get_run_lock_manifest_sha.return_value = "sha-tampered-differently"

    service = ProvenanceExporterService(ledger_service=mock_sink)
    summary = await service.get_provenance_summary(run_id)
    assert summary.is_run_lock_aligned is False

    md_export = await service.export_dossier(run_id, export_format="md")
    assert "ALERTE : DIVERGENCE DÉTECTÉE" in md_export.content


@pytest.mark.asyncio
async def test_provenance_exporter_not_found_raises() -> None:
    """Verify that exporting an unknown run_id raises AuditRunNotFoundError."""
    mock_sink = AsyncMock()
    mock_sink.get_run_provenance_entries.return_value = []
    service = ProvenanceExporterService(ledger_service=mock_sink)

    unknown_id = str(uuid.uuid4())
    with pytest.raises(AuditRunNotFoundError):
        await service.get_provenance_summary(unknown_id)
