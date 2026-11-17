"""Unit tests for isolated per-connector quota & circuit breaker (`Story 6.4`, `AD-12`, `AD-19`)."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

import pytest
from tests.unit.fakes.fake_connector_quota_guard import FakeConnectorQuotaGuard

from orcia_core.audit_finops.remote_usage_sanitizer import RemoteUsageSanitizer
from orcia_core.permissions.connector_invoker import ConnectorInvoker
from orcia_core.permissions.errors import ConnectorCircuitOpenError
from orcia_kernel.errors import OrciaDomainError, TransientInfraError
from orcia_kernel.ports import ConnectorInvokeResult, ConnectorPort

REPO_ROOT = Path(__file__).resolve().parents[2]


class _FakeRemoteConnector(ConnectorPort):
    def __init__(self, scheme_name: str, output_payload: dict[str, Any]) -> None:
        self._scheme = scheme_name
        self._output = output_payload
        self.calls: int = 0

    @property
    def scheme(self) -> str:
        return self._scheme

    def invoke(
        self,
        action: str,
        payload: dict[str, Any],
        idempotency_key: str,
    ) -> ConnectorInvokeResult:
        _ = (action, payload, idempotency_key)
        self.calls += 1
        return ConnectorInvokeResult(
            scheme=self._scheme,
            action=action,
            output=dict(self._output),
            idempotency_key=idempotency_key,
            replayed_from_idempotency_cache=False,
            status="SUCCEEDED",
        )

    def map_error(self, exc: Exception) -> OrciaDomainError:
        return TransientInfraError(detail_override=str(exc))


@pytest.mark.asyncio
async def test_connector_circuit_open_is_isolated_from_other_connectors_and_llms() -> None:
    guard = FakeConnectorQuotaGuard()
    guard.configure("mcp-ocr", max_daily_calls=2, max_monthly_cost_eur=10.0)
    guard.configure("mcp-search", max_daily_calls=10, max_monthly_cost_eur=10.0)
    # Also simulate litellm entry in guard to verify internal LLM ignores external connector breaker
    guard.configure("litellm", max_daily_calls=0, circuit_state="CIRCUIT_OPEN")

    sanitizer = RemoteUsageSanitizer()
    invoker = ConnectorInvoker(
        quota_guard=guard,
        usage_sanitizer=sanitizer,
        max_reported_cost_per_call_eur=5.0,
    )

    ocr_conn = _FakeRemoteConnector(
        "mcp",
        {
            "_meta": {
                "usage": {
                    "unit_count": 5,
                    "unit_name": "pages_ocr",
                    "cost": 0.25,
                    "currency": "EUR",
                }
            }
        },
    )
    search_conn = _FakeRemoteConnector(
        "mcp",
        {
            "_meta": {
                "usage": {
                    "unit_count": 1,
                    "unit_name": "recherches_web",
                    "cost": 0.05,
                    "currency": "EUR",
                }
            }
        },
    )
    llm_conn = _FakeRemoteConnector(
        "litellm",
        {"choices": [{"message": {"content": "Reponse interne OK"}}]},
    )

    # 2 calls to mcp-ocr succeed and exhaust daily limit (2/2 -> CIRCUIT_OPEN)
    out1 = await invoker.invoke_async(
        scheme="mcp",
        connector_key="mcp-ocr",
        action="extract_pages",
        payload={"doc": "a.pdf"},
        idempotency_key="k1",
        connector=ocr_conn,
    )
    out2 = await invoker.invoke_async(
        scheme="mcp",
        connector_key="mcp-ocr",
        action="extract_pages",
        payload={"doc": "b.pdf"},
        idempotency_key="k2",
        connector=ocr_conn,
    )
    assert out1.status == "SUCCEEDED"
    assert out2.status == "SUCCEEDED"
    assert guard.states["mcp-ocr"].circuit_state == "CIRCUIT_OPEN"

    # 3rd call to mcp-ocr is rejected with ConnectorCircuitOpenError WITHOUT hitting ocr_conn
    calls_before_block = ocr_conn.calls
    with pytest.raises(ConnectorCircuitOpenError) as exc_info:
        await invoker.invoke_async(
            scheme="mcp",
            connector_key="mcp-ocr",
            action="extract_pages",
            payload={"doc": "c.pdf"},
            idempotency_key="k3",
            connector=ocr_conn,
        )
    assert exc_info.value.error_code == "ERR_CONNECTOR_CIRCUIT_OPEN"
    assert exc_info.value.http_status == 503
    assert ocr_conn.calls == calls_before_block

    # Another external connector (mcp-search) remains completely unaffected!
    out_search = await invoker.invoke_async(
        scheme="mcp",
        connector_key="mcp-search",
        action="query",
        payload={"q": "orcia"},
        idempotency_key="k4",
        connector=search_conn,
    )
    assert out_search.status == "SUCCEEDED"
    assert search_conn.calls == 1

    # Internal LLM gateway (scheme='litellm' / is_internal_llm=True) remains completely unaffected!
    out_llm = await invoker.invoke_async(
        scheme="litellm",
        action="chat.completions",
        payload={"prompt": "bonjour"},
        idempotency_key="k5",
        connector=llm_conn,
        is_internal_llm=True,
    )
    assert out_llm.status == "SUCCEEDED"
    assert llm_conn.calls == 1


def test_alembic_migration_6_4_and_reset_script_registration() -> None:
    mig_path = (
        REPO_ROOT
        / "infra"
        / "migrations"
        / "versions"
        / "20261116_0604_story_6_4_remote_connector_quotas_and_telemetry.py"
    )
    assert mig_path.exists()
    spec = importlib.util.spec_from_file_location("mig_6_4", mig_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    assert mod.revision == "20261116_0604"
    assert mod.down_revision == "20261116_0602"
    src = mig_path.read_text(encoding="utf-8")
    assert "finops_connector_quotas" in src
    assert "CIRCUIT_OPEN" in src
    assert "NATIVE_TELEMETRY" in src
    assert "DROP TABLE IF EXISTS finops_connector_quotas" in src

    reset_path = REPO_ROOT / "infra" / "scripts" / "maintenance" / "09_reset_db_first_boot.py"
    reset_src = reset_path.read_text(encoding="utf-8")
    assert '"finops_connector_quotas"' in reset_src
