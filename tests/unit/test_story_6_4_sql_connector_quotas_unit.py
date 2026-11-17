"""Unit tests for `SqlConnectorQuotaGuardService` & SQL quota helpers (`Story 6.4`)."""

from __future__ import annotations

from datetime import UTC, datetime
from decimal import Decimal
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from sqlalchemy.exc import ProgrammingError

from orcia_core.audit_finops._internal.sql_connector_circuit import (
    reset_connector_circuit_sql,
    trip_connector_circuit_sql,
    upsert_connector_quota_config_sql,
)
from orcia_core.audit_finops._internal.sql_connector_quotas import (
    fetch_connector_quota_sql,
    list_connector_quotas_sql,
    record_connector_usage_sql,
)
from orcia_core.audit_finops._internal.sql_connector_quotas_helpers import (
    row_to_connector_quota_record,
    safe_uuid,
)
from orcia_core.audit_finops.connector_quota_service import SqlConnectorQuotaGuardService
from orcia_core.kernel._finops_audit_events import ConnectorCircuitTripped
from orcia_core.kernel.ids import new_uuid7_str
from orcia_core.ports.finops_telemetry import SanitizedRemoteUsage
from orcia_kernel.errors import ResourceNotFoundError, ValidationDomainError


def _sample_row(**overrides: Any) -> dict[str, Any]:
    base: dict[str, Any] = {
        "id": new_uuid7_str(),
        "connector_key": "mcp-ocr",
        "display_name": "OCR Externe",
        "service_kind": "MCP_SERVER",
        "scope_type": "GLOBAL",
        "scope_id": None,
        "valuation_mode": "NATIVE_TELEMETRY",
        "max_reported_cost_per_call_eur": Decimal("5.000000"),
        "fixed_cost_per_call_eur": Decimal("0.000000"),
        "unit_tariff_eur": Decimal("0.050000"),
        "default_unit_name": "pages_ocr",
        "max_daily_calls": 100,
        "max_monthly_cost_eur": Decimal("50.000000"),
        "daily_calls_count": 20,
        "monthly_cost_usd": Decimal("10.000000"),
        "total_remote_tokens": 500,
        "total_business_units": Decimal("120.000000"),
        "circuit_state": "CLOSED",
        "anomaly_count": 0,
        "consecutive_anomalies": 0,
        "last_latency_ms": 145,
        "last_tripped_reason": None,
        "last_tripped_at": None,
        "last_invoked_at": datetime.now(UTC),
    }
    base.update(overrides)
    return base


def _mock_engine_with_rows(rows: list[dict[str, Any]] | None = None) -> AsyncMock:
    conn = AsyncMock()
    res = MagicMock()
    mappings = MagicMock()
    row_list = rows if rows is not None else [_sample_row()]
    mappings.first.return_value = row_list[0] if row_list else None
    mappings.one.return_value = row_list[0] if row_list else _sample_row()
    mappings.all.return_value = row_list
    res.mappings.return_value = mappings
    conn.execute = AsyncMock(return_value=res)

    ctx = AsyncMock()
    ctx.__aenter__ = AsyncMock(return_value=conn)
    ctx.__aexit__ = AsyncMock(return_value=None)

    engine = MagicMock()
    engine.connect.return_value = ctx
    engine.begin.return_value = ctx
    return engine


def test_row_mapper_and_safe_uuid() -> None:
    assert safe_uuid(None) is None
    assert safe_uuid("not-a-uuid") is None
    uid = new_uuid7_str()
    assert str(safe_uuid(uid)) == uid

    rec_monthly = row_to_connector_quota_record(_sample_row())
    assert rec_monthly.monthly_cost_eur == Decimal("9.20")
    assert rec_monthly.quota_used_pct == Decimal("18.40")

    rec_daily = row_to_connector_quota_record(
        _sample_row(max_monthly_cost_eur=None, max_daily_calls=50, daily_calls_count=25)
    )
    assert rec_daily.quota_used_pct == Decimal("50.00")


@pytest.mark.asyncio
async def test_service_without_engine_and_error_guards() -> None:
    svc = SqlConnectorQuotaGuardService(engine=None)
    dec = await svc.evaluate_call_allowed("mcp-ocr")
    assert dec.is_allowed is True
    assert dec.circuit_state == "CLOSED"
    assert await svc.list_remote_services() == []
    await svc.record_call_usage(
        "mcp-ocr",
        SanitizedRemoteUsage(
            input_tokens=0,
            output_tokens=0,
            cost_usd=0.0,
            cost_eur=0.0,
            cost_source="EXTERNAL_REPORTED",
            native_metric_type="calls",
            native_metric_value=1.0,
            native_currency=None,
            reported_by_remote=True,
            is_anomaly_capped=False,
        ),
    )
    with pytest.raises(ValidationDomainError):
        await svc.update_connector_quota(connector_key="   ")
    with pytest.raises(ValidationDomainError):
        await svc.update_connector_quota(connector_key="mcp-ocr")
    with pytest.raises(ResourceNotFoundError):
        await svc.reset_circuit(connector_key="mcp-ocr")


@pytest.mark.asyncio
async def test_sql_repositories_and_service_transitions() -> None:
    engine_ok = _mock_engine_with_rows([_sample_row()])
    svc = SqlConnectorQuotaGuardService(engine=engine_ok)

    dec_ok = await svc.evaluate_call_allowed("mcp-ocr")
    assert dec_ok.is_allowed is True

    # Already CIRCUIT_OPEN
    svc_open = SqlConnectorQuotaGuardService(
        engine=_mock_engine_with_rows([_sample_row(circuit_state="CIRCUIT_OPEN")])
    )
    dec_open = await svc_open.evaluate_call_allowed("mcp-ocr")
    assert dec_open.is_allowed is False
    assert dec_open.circuit_state == "CIRCUIT_OPEN"

    # Daily call limit reached -> trips circuit and emits outbox event
    svc_daily = SqlConnectorQuotaGuardService(
        engine=_mock_engine_with_rows([_sample_row(daily_calls_count=100, max_daily_calls=100)])
    )
    dec_daily = await svc_daily.evaluate_call_allowed("mcp-ocr", scope_type="WORKSPACE")
    assert dec_daily.is_allowed is False
    assert dec_daily.circuit_state == "CIRCUIT_OPEN"
    assert len(svc_daily.collected_outbox_events) == 1

    # Monthly cost limit reached -> trips circuit
    svc_monthly = SqlConnectorQuotaGuardService(
        engine=_mock_engine_with_rows(
            [
                _sample_row(
                    monthly_cost_usd=Decimal("60.000000"), max_monthly_cost_eur=Decimal("50.000000")
                )
            ]
        )
    )
    dec_monthly = await svc_monthly.evaluate_call_allowed("mcp-ocr")
    assert dec_monthly.is_allowed is False

    # Not found row -> allowed
    svc_empty = SqlConnectorQuotaGuardService(engine=_mock_engine_with_rows([]))
    dec_empty = await svc_empty.evaluate_call_allowed("unknown-conn")
    assert dec_empty.is_allowed is True

    # CRUD & usage recording with mocked engine
    ws_id = new_uuid7_str()
    await list_connector_quotas_sql(engine_ok, scope_type="WORKSPACE", scope_id=ws_id)
    await svc.list_remote_services(scope_type="WORKSPACE", scope_id=ws_id)
    await svc.update_connector_quota(connector_key="mcp-ocr", display_name="OCR")
    await svc.reset_circuit(connector_key="mcp-ocr", target_state="CLOSED", actor_id="admin-1")

    usage_capped = SanitizedRemoteUsage(
        input_tokens=100,
        output_tokens=50,
        cost_usd=5.434783,
        cost_eur=5.0,
        cost_source="EXTERNAL_REPORTED",
        native_metric_type="pages_ocr",
        native_metric_value=12.0,
        native_currency="EUR",
        reported_by_remote=True,
        is_anomaly_capped=True,
        original_reported_cost_eur=99.0,
    )
    engine_trip = _mock_engine_with_rows(
        [_sample_row(daily_calls_count=100, max_daily_calls=100, consecutive_anomalies=3)]
    )
    await record_connector_usage_sql(
        engine_trip, connector_key="mcp-ocr", usage=usage_capped, latency_ms=210
    )
    await svc.record_call_usage("mcp-ocr", usage_capped, latency_ms=210)
    await trip_connector_circuit_sql(
        engine_ok,
        connector_key="mcp-ocr",
        reason="cap",
        event=ConnectorCircuitTripped.create(connector_id="mcp-ocr", reason="cap"),
    )


@pytest.mark.asyncio
async def test_sql_repositories_handle_db_errors_gracefully() -> None:
    err_ctx = AsyncMock()
    err_ctx.__aenter__ = AsyncMock(side_effect=RuntimeError("db offline"))
    err_ctx.__aexit__ = AsyncMock(return_value=None)
    err_engine = MagicMock()
    err_engine.connect.return_value = err_ctx
    assert await fetch_connector_quota_sql(err_engine, "mcp-ocr") is None
    assert await list_connector_quotas_sql(err_engine) == []

    prog_ctx = AsyncMock()
    prog_ctx.__aenter__ = AsyncMock(side_effect=ProgrammingError("stmt", {}, Exception("no table")))
    prog_ctx.__aexit__ = AsyncMock(return_value=None)
    prog_engine = MagicMock()
    prog_engine.begin.return_value = prog_ctx
    with pytest.raises(ValidationDomainError):
        await upsert_connector_quota_config_sql(prog_engine, connector_key="mcp-ocr")
    assert (
        await reset_connector_circuit_sql(
            prog_engine,
            connector_key="mcp-ocr",
            target_state="CLOSED",
            actor_id="u1",
            trace_id="t1",
        )
        is None
    )
