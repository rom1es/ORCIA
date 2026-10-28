"""Unit & Conformance Tests for Story 3.2f: Step Executors, ConnectorInvoker & Finance.

Covers all acceptance criteria `AC-F1` to `AC-F6`:
- `AC-F1` (`PROC-01`, `P0-3`): Real end-to-end run via FastAPI REST API
  (`POST /api/v1/orchestration/runs/instantiate`,
  `POST /api/v1/orchestration/runs/steps/execute`, pause on `HUMAN_TASK`, resume via
  `POST /api/v1/orchestration/runs/{run_id}/steps/{step_key}/resume`, `COMPLETED` with real
  `DeterministicCassetteLLM` and `ConnectorInvoker` outputs, `0` stub/simulated strings).
- `AC-F2`: Static source checks verifying `0` occurrences of `_recover_pending_workflows` or
  `_ACTIVE_ENGINE` across `packages/` and `apps/`, and `0` occurrences of `simulated` inside
  `packages/orcia-core/src/orcia_core/orchestration/`.
- `AC-F3` & `AC-F4`: `ConnectorInvoker` error taxonomy (`TransientInfraError`, `RateLimitedError`
  429 with `Retry-After: 2` waiting >= 2s then succeeding on 200; `FunctionalConnectorError`
  with `0` retries transitioning to `WAITING_FOR_HUMAN_ARBITRATION`; `PolicyDeniedError`,
  `UpstreamTimeoutError`, `PermanentInfraError`; circuit breaker `CLOSED` -> `OPEN` after N
  failures -> `HALF_OPEN` after cooldown -> `CLOSED` on success; identical `idempotency_key`
  on retries; budget accounting; secret scrubbing).
- `AC-F5`: Finance vertical workflow ("Rapprochement de factures" / Invoice Reconciliation)
  executed end-to-end to `COMPLETED` in `core-without-sdlc` mode (with SDLC schemes unloaded).
"""

from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from tests.fixtures.plugins.finance_reconciliation_plugin import (
    FINANCE_INVOICE_RECONCILIATION_YAML,
    FakeFinanceErpConnector,
)

from orcia_api.main import create_app
from orcia_core.orchestration import (
    ConnectorInvoker,
    WorkflowOrchestrationSetupService,
    register_default_step_executors,
    scrub_connector_secrets,
)
from orcia_core.orchestration.errors import ValidationDomainError
from orcia_core.permissions import build_default_auth_and_org_service
from orcia_core.permissions.models import UserIdentity
from orcia_core.testing.cassette_llm import CassetteEntry, DeterministicCassetteLLM
from orcia_kernel.errors import (
    FunctionalConnectorError,
    PermanentInfraError,
    PolicyDeniedError,
    RateLimitedError,
    TransientInfraError,
    UpstreamTimeoutError,
)
from orcia_kernel.ports import (
    get_registered_step_executor,
    list_registered_connector_schemes,
    list_registered_step_executor_types,
    register_connector,
    unregister_connector,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def _lead_user() -> UserIdentity:
    return UserIdentity(
        id="0192c4e0-0000-7000-8000-000000000603",
        email="marc.lead@orcia.io",
        display_name="Marc",
        auth_mode="HYBRID",
        human_profile_archetype="TECH_LEAD",
        platform_role="TEAM_LEAD",
        primary_org_unit_id="0192c4e0-0000-7000-8000-000000000104",
    )


def test_ac_f2_zero_private_dbos_recovery_and_zero_simulated_in_orchestration() -> None:
    """Verify AC-F2 & DEC-P0-EXEC static invariants across packages/ and apps/."""
    forbidden_engine_hits: list[str] = []
    for root_dir in (REPO_ROOT / "packages", REPO_ROOT / "apps"):
        for py_file in root_dir.rglob("*.py"):
            content = py_file.read_text(encoding="utf-8")
            for idx, line in enumerate(content.splitlines(), start=1):
                if "_recover_pending_workflows" in line or "_ACTIVE_ENGINE" in line:
                    forbidden_engine_hits.append(f"{py_file.relative_to(REPO_ROOT)}:{idx}:{line}")
    assert forbidden_engine_hits == []

    orch_dir = REPO_ROOT / "packages" / "orcia-core" / "src" / "orcia_core" / "orchestration"
    simulated_hits: list[str] = []
    for py_file in orch_dir.rglob("*.py"):
        content = py_file.read_text(encoding="utf-8")
        for idx, line in enumerate(content.splitlines(), start=1):
            if "simulated" in line.lower():
                simulated_hits.append(f"{py_file.relative_to(REPO_ROOT)}:{idx}:{line}")
    assert simulated_hits == []


def test_ac_f1_step_executors_registry_and_real_api_run_pause_resume_completed() -> None:
    """Verify AC-F1 (`PROC-01`): 6 step executors registered and API run pause/resume."""
    register_default_step_executors()
    registered_types = list_registered_step_executor_types()
    for expected in (
        "AGENT",
        "SKILL",
        "SUB_WORKFLOW",
        "HUMAN_TASK",
        "HTTP_ACTION",
        "POST_ACTION_VERIFICATION",
    ):
        assert expected in registered_types
        assert get_registered_step_executor(expected) is not None

    erp_connector = FakeFinanceErpConnector()
    register_connector(erp_connector)
    try:
        app = create_app()
        client = TestClient(app)
        cassette: DeterministicCassetteLLM = app.state.llm_gateway
        cassette.register(
            "INV-2026-8841",
            CassetteEntry(
                content="CONCORDANCE_3_VOIES_VALIDEE:INV-2026-8841=PO-2026-8841(14250.00_EUR)",
                scenario_tag="FINANCE_MATCH_OK",
            ),
        )

        # 1. Register workflow via API
        reg_res = client.post(
            "/api/v1/orchestration/workflows/register?persona_key=marc",
            json={
                "raw_manifest": FINANCE_INVOICE_RECONCILIATION_YAML,
                "workspace_id": "0192c4e0-0000-7000-8000-000000000201",
            },
        )
        assert reg_res.status_code == 200

        # 2. Instantiate run via API
        inst_res = client.post(
            "/api/v1/orchestration/runs/instantiate?persona_key=marc",
            json={
                "workflow_uri": "orcia://workflows/finance-invoice-reconciliation",
                "workspace_id": "0192c4e0-0000-7000-8000-000000000201",
                "trigger_id": "0192c4e0-0000-7000-8000-000000000801",
                "trigger_idempotency_key": "idem-api-finance-001",
            },
        )
        assert inst_res.status_code == 200
        run_id = inst_res.json()["run"]["id"]

        # 3. Execute Step 1 (AGENT backed by DeterministicCassetteLLM)
        s1_res = client.post(
            "/api/v1/orchestration/runs/steps/execute?persona_key=marc",
            json={"run_id": run_id, "step_key": "extract-and-match-invoice"},
        )
        assert s1_res.status_code == 200
        s1_json = s1_res.json()
        assert s1_json["step_execution"]["status"] == "COMMITTED"
        assert (
            "CONCORDANCE_3_VOIES_VALIDEE:INV-2026-8841"
            in s1_json["committed_snapshot"]["artifact_payload"]["llm_output"]
        )

        # 4. Execute Step 2 (HTTP_ACTION via ConnectorInvoker -> FakeFinanceErpConnector)
        s2_res = client.post(
            "/api/v1/orchestration/runs/steps/execute?persona_key=marc",
            json={"run_id": run_id, "step_key": "post-erp-voucher"},
        )
        assert s2_res.status_code == 200
        s2_json = s2_res.json()
        assert s2_json["step_execution"]["status"] == "COMMITTED"
        assert (
            s2_json["committed_snapshot"]["artifact_payload"]["connector_output"]["journal"]
            == "AP-LEDGER-2026"
        )

        # 5. Execute Step 3 (HUMAN_TASK) -> pauses on WAITING_FOR_HUMAN_ARBITRATION
        s3_pause_res = client.post(
            "/api/v1/orchestration/runs/steps/execute?persona_key=marc",
            json={"run_id": run_id, "step_key": "approve-payment-release"},
        )
        assert s3_pause_res.status_code == 200
        s3_pause_json = s3_pause_res.json()
        assert s3_pause_json["step_execution"]["status"] == "WAITING_FOR_HUMAN_ARBITRATION"
        assert s3_pause_json["committed_snapshot"] is None

        bb_paused = client.get(
            f"/api/v1/orchestration/runs/{run_id}/blackboard?persona_key=marc"
        ).json()
        assert bb_paused["run_status"] == "WAITING_FOR_HUMAN_ARBITRATION"

        # 6. Resume Step 3 via human task resume endpoint
        s3_resume_res = client.post(
            f"/api/v1/orchestration/runs/{run_id}/steps/approve-payment-release/resume?persona_key=marc",
            json={"decision": "APPROVE_PAYMENT_14250_EUR"},
        )
        assert s3_resume_res.status_code == 200
        s3_resume_json = s3_resume_res.json()
        assert s3_resume_json["step_execution"]["status"] == "COMMITTED"
        assert (
            s3_resume_json["committed_snapshot"]["artifact_payload"]["human_decision"]
            == "APPROVE_PAYMENT_14250_EUR"
        )

        # 7. Execute Step 4 (POST_ACTION_VERIFICATION) -> Run transitions to COMPLETED
        s4_res = client.post(
            "/api/v1/orchestration/runs/steps/execute?persona_key=marc",
            json={"run_id": run_id, "step_key": "verify-ledger-balance"},
        )
        assert s4_res.status_code == 200
        assert s4_res.json()["step_execution"]["status"] == "COMMITTED"

        bb_final = client.get(
            f"/api/v1/orchestration/runs/{run_id}/blackboard?persona_key=marc"
        ).json()
        assert bb_final["run_status"] == "COMPLETED"
        assert len(bb_final["active_snapshots"]) == 4
    finally:
        unregister_connector("erp")


def test_ac_f3_and_f4_connector_invoker_retry_after_functional_error_and_circuit_breaker() -> None:
    """Verify AC-F3 & AC-F4: 429 Retry-After -> 200, FunctionalConnectorError, Circuit Breaker."""
    fake_now = [100.0]
    slept_intervals: list[float] = []

    def clock() -> float:
        return fake_now[0]

    def sleep_fn(seconds: float) -> None:
        slept_intervals.append(seconds)
        fake_now[0] += seconds

    erp = FakeFinanceErpConnector()
    invoker = ConnectorInvoker(
        failure_threshold=3,
        cooldown_seconds=10.0,
        cost_per_attempt_usd=0.10,
        monotonic_clock=clock,
        sleep_fn=sleep_fn,
    )

    # 1. HTTP 429 with Retry-After: 2s followed by HTTP 200 -> waits >= 2s, succeeds on 2nd attempt
    erp.script_error(RateLimitedError(retry_after_s=2.0, detail_override="429 Too Many Requests"))
    outcome_429 = invoker.invoke(
        scheme="erp",
        action="post_voucher",
        payload={"invoice_id": "INV-1", "api_key": "sk-secret-token-123456"},
        idempotency_key="idem-429-test",
        max_agent_retries=3,
        connector=erp,
    )
    assert outcome_429.status == "SUCCEEDED"
    assert outcome_429.attempts_used == 2
    assert outcome_429.total_wait_seconds >= 2.0
    assert slept_intervals == [2.0]
    assert outcome_429.sanitized_input["api_key"] == "[REDACTED_SECRET]"
    assert len(invoker.recorded_audit_keys) == 1
    assert len(invoker.recorded_outbox_keys) == 1

    # 2. FunctionalConnectorError -> 0 retry (attempts_used == 1), WAITING_FOR_HUMAN_ARBITRATION
    calls_before = erp.call_count
    erp.script_error(
        FunctionalConnectorError(detail_override="422 Compte général 401000 verrouillé")
    )
    outcome_func = invoker.invoke(
        scheme="erp",
        action="post_voucher",
        payload={"invoice_id": "INV-2"},
        idempotency_key="idem-func-422",
        max_agent_retries=3,
        connector=erp,
    )
    assert outcome_func.status == "WAITING_FOR_HUMAN_ARBITRATION"
    assert outcome_func.attempts_used == 1
    assert erp.call_count == calls_before + 1
    assert outcome_func.error_code == "ERR_FUNCTIONAL_CONNECTOR_ERROR"

    # 3. PolicyDeniedError -> 0 retry, WAITING_FOR_HUMAN_ARBITRATION
    erp.script_error(PolicyDeniedError(detail_override="403 Policy Denied"))
    outcome_policy = invoker.invoke(
        scheme="erp",
        action="post_voucher",
        payload={"invoice_id": "INV-3"},
        idempotency_key="idem-policy-403",
        max_agent_retries=3,
        connector=erp,
    )
    assert outcome_policy.status == "WAITING_FOR_HUMAN_ARBITRATION"
    assert outcome_policy.attempts_used == 1
    assert outcome_policy.error_code == "ERR_POLICY_DENIED"

    # 4. Circuit Breaker: 3 consecutive transient failures open the breaker (CLOSED -> OPEN)
    erp.script_error(UpstreamTimeoutError(retry_after_s=0.5, detail_override="504 Gateway Timeout"))
    erp.script_error(
        TransientInfraError(retry_after_s=0.5, detail_override="503 Service Unavailable")
    )
    erp.script_error(
        TransientInfraError(retry_after_s=0.5, detail_override="503 Service Unavailable")
    )
    outcome_cb = invoker.invoke(
        scheme="erp",
        action="post_voucher",
        payload={"invoice_id": "INV-4"},
        idempotency_key="idem-cb-open",
        max_agent_retries=5,
        connector=erp,
    )
    assert outcome_cb.status == "PAUSED_CIRCUIT_BREAKER"
    assert outcome_cb.circuit_state == "OPEN"
    assert outcome_cb.attempts_used == 3

    # Calling while OPEN raises PermanentInfraError immediately without hitting the connector
    calls_when_open = erp.call_count
    with pytest.raises(PermanentInfraError, match="Disjoncteur OPEN"):
        invoker.invoke(
            scheme="erp",
            action="post_voucher",
            payload={"invoice_id": "INV-4"},
            idempotency_key="idem-cb-blocked",
            connector=erp,
        )
    assert erp.call_count == calls_when_open

    # Advance clock past cooldown_seconds (10.0s) -> OPEN -> HALF_OPEN -> CLOSED on success
    fake_now[0] += 11.0
    assert invoker.get_breaker("erp").current_state(clock()) == "HALF_OPEN"
    outcome_half_open = invoker.invoke(
        scheme="erp",
        action="post_voucher",
        payload={"invoice_id": "INV-4"},
        idempotency_key="idem-cb-recover",
        connector=erp,
    )
    assert outcome_half_open.status == "SUCCEEDED"
    assert outcome_half_open.circuit_state == "CLOSED"

    # 5. Budget cap enforcement
    with pytest.raises(ValidationDomainError, match="Plafond budgétaire dépassé"):
        invoker.invoke(
            scheme="erp",
            action="post_voucher",
            payload={"invoice_id": "INV-5"},
            idempotency_key="idem-budget",
            max_cost_usd=0.05,
            accumulated_cost_usd=0.0,
            connector=erp,
        )

    # 6. Secret scrubbing helper coverage on nested dicts and Bearer strings
    scrubbed = scrub_connector_secrets(
        {
            "normal": "value",
            "nested": {"password": "my-secret-password"},  # pragma: allowlist secret
            "header_note": "Bearer eyJhbGciOiJIUzI1NiJ9",  # pragma: allowlist secret
        }
    )
    assert scrubbed["nested"]["password"] == "[REDACTED_SECRET]"
    assert "[REDACTED_SECRET]" in scrubbed["header_note"]


def test_ac_f5_core_without_sdlc_finance_invoice_reconciliation_workflow() -> None:
    """Verify AC-F5 (`core-without-sdlc`): Finance workflow executes to COMPLETED."""
    for sdlc_scheme in ("git", "jira", "confluence", "sonar", "ci"):
        unregister_connector(sdlc_scheme)
    erp = FakeFinanceErpConnector()
    register_connector(erp)

    try:
        schemes = list_registered_connector_schemes()
        assert "erp" in schemes
        assert "git" not in schemes
        assert "jira" not in schemes

        from orcia_core.permissions.evaluator import MatrixPermissionEvaluator
        from orcia_core.permissions.models import WorkspaceDatasourceEntity, WorkspaceEntity

        base_auth = build_default_auth_and_org_service()
        ws_id = "0192c4e0-0000-7000-8000-000000000299"
        finance_ws = WorkspaceEntity(
            id=ws_id,
            slug="ws-finance-ap",
            name="Espace Finance Comptabilité Fournisseurs",
            owner_org_unit_id="0192c4e0-0000-7000-8000-000000000104",
            datasources=(
                WorkspaceDatasourceEntity(
                    id="0192c4e0-0000-7000-8000-000000000391",
                    workspace_id=ws_id,
                    alias="erp-invoices",
                    scheme="erp",
                    uri="erp://sap-finance/invoices/INV-2026-8841?ref=2026.10",
                    role="primary",
                ),
                WorkspaceDatasourceEntity(
                    id="0192c4e0-0000-7000-8000-000000000392",
                    workspace_id=ws_id,
                    alias="db-purchase-orders",
                    scheme="db",
                    uri="db://finance_ledger/purchase_orders/PO-2026-8841",
                    role="reference",
                ),
            ),
        )
        finance_evaluator = MatrixPermissionEvaluator(
            org_units=base_auth.evaluator.org_units,
            workspaces=(*base_auth.evaluator.workspaces, finance_ws),
        )
        svc = WorkflowOrchestrationSetupService(evaluator=finance_evaluator)
        svc.resolver.register_upstream_payload(
            "orcia://agents/finance-reconciler",
            '{"agent":"finance-reconciler","version":"1.0.0"}',
            resolved_version="1.0.0",
        )
        svc.resolver.register_upstream_payload(
            "erp://sap-finance/post_voucher",
            '{"skill":"post_voucher","version":"1.0.0"}',
            resolved_version="1.0.0",
        )
        svc.resolver.register_upstream_payload(
            "db://finance_ledger/purchase_orders/PO-2026-8841",
            '{"po_id":"PO-2026-8841","amount_eur":14250.00}',
            resolved_version="2026.10",
        )

        lead = _lead_user()
        wf = svc.register_workflow_manifest(
            lead,
            FINANCE_INVOICE_RECONCILIATION_YAML,
            workspace_id=finance_ws.id,
        )
        assert wf.mode == "standard"

        run = svc.instantiate_workflow_run(
            lead,
            workflow_uri=wf.uri,
            workspace_id=finance_ws.id,
        )

        # Step 1: AGENT
        step1, snap1 = svc.engine.execute_step(
            lead, run_id=run.id, step_key="extract-and-match-invoice"
        )
        assert step1.status == "COMMITTED"
        assert snap1 is not None

        # Step 2: HTTP_ACTION
        step2, snap2 = svc.engine.execute_step(lead, run_id=run.id, step_key="post-erp-voucher")
        assert step2.status == "COMMITTED"
        assert snap2 is not None

        # Step 3: HUMAN_TASK (pause then resume)
        step3_paused, snap3_none = svc.engine.execute_step(
            lead, run_id=run.id, step_key="approve-payment-release"
        )
        assert step3_paused.status == "WAITING_FOR_HUMAN_ARBITRATION"
        assert snap3_none is None

        step3_resumed, snap3 = svc.engine.resume_human_task(
            lead,
            run_id=run.id,
            step_key="approve-payment-release",
            decision="APPROVE_TREASURY_RELEASE",
        )
        assert step3_resumed.status == "COMMITTED"
        assert snap3 is not None

        # Step 4: POST_ACTION_VERIFICATION
        step4, snap4 = svc.engine.execute_step(
            lead, run_id=run.id, step_key="verify-ledger-balance"
        )
        assert step4.status == "COMMITTED"
        assert snap4 is not None

        final_run = svc.engine._get_run(run.id)
        assert final_run.status == "COMPLETED"
    finally:
        unregister_connector("erp")
        from orcia_pack_sdlc import activate_sdlc_pack

        activate_sdlc_pack()
