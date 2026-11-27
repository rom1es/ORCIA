"""Unit tests for Story 7.2 — Triggers, Factorized HMAC, Self-Trigger Guard & Opt-In Help."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

import pytest

from orcia_core.kernel.errors import FunctionalConnectorError, TransientConnectorError
from orcia_core.kernel.events import WorkflowPublished
from orcia_core.kernel.log_sink_ports import LogEntry, LogQuery
from orcia_core.orchestration import (
    CreateTriggerCommand,
    TriggerDispatcherService,
    UpdateTriggerCommand,
)
from orcia_core.orchestration._triggers_log_cron import cron_matches_timestamp
from orcia_core.permissions import (
    AutonomyContractService,
    HierarchicalRbacService,
    IamAccountRecord,
    SignAutonomyContractCommand,
    compute_webhook_hmac_sha256,
    verify_webhook_hmac_sha256,
)
from orcia_core.permissions.errors import (
    AutonomyContractRequiredForTriggerError,
    TriggerCircuitOpenError,
)
from orcia_core.permissions.models import UserIdentity
from orcia_core.permissions.secret_hint import SecretInputSpec
from orcia_worker.outbox_relay import OutboxEventBus
from orcia_worker.roles import main as worker_roles_main
from orcia_worker.trigger_dispatcher_daemon import serve_trigger_dispatcher_daemon


class _FakeLogSink:
    def __init__(self, entries: list[LogEntry]) -> None:
        self._entries = entries

    async def query_logs(self, query: LogQuery) -> list[LogEntry]:
        return [
            e
            for e in self._entries
            if (query.service is None or e.service == query.service)
            and (query.level is None or e.level == query.level)
        ]

    async def count_errors(
        self, fingerprint: str, window_seconds: int, *, service: str | None = None
    ) -> int:
        del fingerprint, window_seconds, service
        return len(self._entries)

    async def healthcheck(self) -> bool:
        return True


class _FakeHelpService:
    def __init__(self) -> None:
        self.calls: list[dict[str, Any]] = []

    async def generate_and_attach_help(self, **kwargs: Any) -> Any:
        self.calls.append(kwargs)
        return type("Res", (), {"article_id": kwargs["article_id"]})()


async def _setup_signed_contract() -> tuple[AutonomyContractService, str, str]:
    rbac = HierarchicalRbacService()
    contracts = AutonomyContractService(rbac_service=rbac)
    ws_id = "0195f000-0000-7000-8000-000000000301"
    wf_id = "wf-01-qualification"
    signer = UserIdentity(
        id="0195f000-0000-7000-8000-000000000203",
        email="marc@orcia.local",
        display_name="Marc",
        auth_mode="local",
        human_profile_archetype="TECH_LEAD",
        platform_role="TEAM_LEAD",
        primary_org_unit_id="0195f000-0000-7000-8000-000000000103",
    )
    sp = IamAccountRecord(
        id="0195f000-0000-7000-8000-000000007101",
        principal_id="sp-auto-docs",
        display_name="SP Auto Docs",
        email=None,
        account_kind="SERVICE_PRINCIPAL",
        auth_source="LOCAL",
        roles=("TEAM_LEAD",),
        team_ids=(ws_id,),
        status="ACTIVE",
    )
    await contracts.sign_contract(
        SignAutonomyContractCommand(
            workspace_id=ws_id,
            workflow_id=wf_id,
            workflow_version="1.0.0",
            workflow_sha256="a" * 64,
            criticality="LOW_NON_CRITICAL",
            service_principal_id=sp.id,
            allowed_read_sources=("catalog:read",),
            allowed_write_actions=("help_article:publish",),
            max_cost_per_run_usd=5.0,
        ),
        signer=signer,
        service_principal=sp,
        allowed_scope_ids=[ws_id],
    )
    return contracts, ws_id, wf_id


def test_factorized_webhook_hmac_sha256_constant_time() -> None:
    body = b'{"event":"push","delivery_key":"d-1"}'
    secret = "whsec-story-7-2-shared-secret"  # pragma: allowlist secret
    sig = compute_webhook_hmac_sha256(body, secret)
    assert sig.startswith("sha256=")
    assert verify_webhook_hmac_sha256(body, secret, sig) is True
    assert verify_webhook_hmac_sha256(body, secret, sig.removeprefix("sha256=")) is True
    assert verify_webhook_hmac_sha256(body, secret, "sha256=" + "0" * 64) is False
    assert verify_webhook_hmac_sha256(body, secret, None) is False


@pytest.mark.asyncio
async def test_trigger_requires_active_contract_and_enforces_triple_idempotency() -> None:
    rbac = HierarchicalRbacService()
    contracts_empty = AutonomyContractService(rbac_service=rbac)
    disp_empty = TriggerDispatcherService(contract_service=contracts_empty)
    with pytest.raises(AutonomyContractRequiredForTriggerError):
        await disp_empty.create_trigger(
            CreateTriggerCommand(
                workspace_id="ws-1",
                workflow_id="wf-1",
                trigger_type="MANUAL_AUTONOMOUS",
            )
        )

    contracts, ws_id, wf_id = await _setup_signed_contract()
    dispatcher = TriggerDispatcherService(contract_service=contracts)
    trig = await dispatcher.create_trigger(
        CreateTriggerCommand(
            workspace_id=ws_id,
            workflow_id=wf_id,
            trigger_type="WEBHOOK",
            webhook_secret=SecretInputSpec(
                action="set",
                plaintext_value="whsec-unit-test-123456",  # pragma: allowlist secret
            ),
        )
    )
    assert trig.webhook_secret_configured is True
    assert trig.webhook_secret_masked_hint == "••••••••3456"

    first = await dispatcher.dispatch_trigger(trigger_id=trig.id, idempotency_key="deliv-1")
    dup = await dispatcher.dispatch_trigger(trigger_id=trig.id, idempotency_key="deliv-1")
    assert first.dispatched is True
    assert first.outcome == "DISPATCHED"
    assert first.dbos_workflow_id == f"{trig.id}:deliv-1"
    assert dup.dispatched is False
    assert dup.outcome == "DUPLICATE_SUPPRESSED"


@pytest.mark.asyncio
async def test_self_trigger_guard_blocks_loop_and_emits_outbox() -> None:
    contracts, ws_id, wf_id = await _setup_signed_contract()
    dispatcher = TriggerDispatcherService(contract_service=contracts)
    trig = await dispatcher.create_trigger(
        CreateTriggerCommand(workspace_id=ws_id, workflow_id=wf_id, trigger_type="WEBHOOK")
    )

    blocked_by_header = await dispatcher.dispatch_trigger(
        trigger_id=trig.id,
        idempotency_key="loop-1",
        headers={"X-Orcia-Origin-Run-Id": "run-abc-123"},
    )
    assert blocked_by_header.dispatched is False
    assert blocked_by_header.outcome == "SELF_TRIGGER_BLOCKED"

    blocked_by_sp = await dispatcher.dispatch_trigger(
        trigger_id=trig.id,
        idempotency_key="loop-2",
        payload={"actor_account_id": trig.service_principal_id},
    )
    assert blocked_by_sp.dispatched is False
    assert blocked_by_sp.outcome == "SELF_TRIGGER_BLOCKED"
    assert sum(1 for e in dispatcher.outbox_events if e.event_type == "SelfTriggerBlocked") == 2


@pytest.mark.asyncio
async def test_transient_retry_vs_functional_circuit_breaker_and_sse() -> None:
    contracts, ws_id, wf_id = await _setup_signed_contract()
    dispatcher = TriggerDispatcherService(contract_service=contracts)
    trig = await dispatcher.create_trigger(
        CreateTriggerCommand(
            workspace_id=ws_id,
            workflow_id=wf_id,
            trigger_type="MANUAL_AUTONOMOUS",
            max_consecutive_failures=3,
        )
    )

    # 1. TransientConnectorError is retried and succeeds -> consecutive_failures stays 0
    transient_calls = 0

    async def _flaky_then_ok() -> dict[str, Any]:
        nonlocal transient_calls
        transient_calls += 1
        if transient_calls == 1:
            raise TransientConnectorError(retry_after_s=0.0, detail_override="HTTP 503 temporary")
        return {"ok": True}

    ok_res = await dispatcher.dispatch_trigger(
        trigger_id=trig.id, idempotency_key="transient-ok", execution_fn=_flaky_then_ok
    )
    assert ok_res.dispatched is True
    assert ok_res.attempts == 2
    assert transient_calls == 2

    # 2. FunctionalConnectorError is NOT retried and opens CIRCUIT_OPEN after 3 failures
    func_calls = 0

    async def _always_functional_err() -> dict[str, Any]:
        nonlocal func_calls
        func_calls += 1
        raise FunctionalConnectorError(detail_override="Business validation failed")

    for i in range(3):
        out = await dispatcher.dispatch_trigger(
            trigger_id=trig.id,
            idempotency_key=f"func-err-{i}",
            execution_fn=_always_functional_err,
        )
        if i < 2:
            assert out.outcome == "FAILED_FUNCTIONAL"
            assert out.attempts == 1
        else:
            assert out.outcome == "CIRCUIT_OPEN"

    assert func_calls == 3  # zero retries on functional error
    sse_events = dispatcher.sse_broker.list_recent_events(workspace_id=ws_id)
    circuit_sse = [e for e in sse_events if e.event_name == "TriggerCircuitOpened"]
    assert len(circuit_sse) == 1
    assert circuit_sse[0].dispatch_latency_ms < 500.0

    with pytest.raises(TriggerCircuitOpenError):
        await dispatcher.dispatch_trigger(trigger_id=trig.id, idempotency_key="blocked-open")

    reset = await dispatcher.reset_circuit(workspace_id=ws_id, trigger_id=trig.id)
    assert reset.status == "ACTIVE"
    assert reset.consecutive_failures == 0


@pytest.mark.asyncio
async def test_log_sink_scanner_cron_and_optin_workflow_published() -> None:
    contracts, ws_id, wf_id = await _setup_signed_contract()
    sink = _FakeLogSink(
        [
            LogEntry(
                timestamp="2026-11-17T10:00:00Z",
                level="ERROR",
                service="api",
                logger="orcia.api",
                message="ZeroDivisionError: division by zero",
                exception='File "app.py", line 12, in compute\nZeroDivisionError',
                workspace_id=ws_id,
            )
        ]
    )
    dispatcher = TriggerDispatcherService(contract_service=contracts, log_sink=sink)

    # LOG_SINK_ALERT + cooldown deduplication
    log_trig = await dispatcher.create_trigger(
        CreateTriggerCommand(
            workspace_id=ws_id,
            workflow_id=wf_id,
            trigger_type="LOG_SINK_ALERT",
            log_sink_service="api",
            cooldown_window_seconds=300,
        )
    )
    now = datetime(2026, 11, 17, 10, 1, 0, tzinfo=UTC)
    scan1 = await dispatcher.scan_log_sink_triggers(workspace_id=ws_id, now_utc=now)
    scan2 = await dispatcher.scan_log_sink_triggers(workspace_id=ws_id, now_utc=now)
    assert len(scan1) == 1 and scan1[0].dispatched is True
    assert len(scan2) == 1 and scan2[0].outcome == "DUPLICATE_SUPPRESSED"

    # CRON evaluation
    cron_trig = await dispatcher.create_trigger(
        CreateTriggerCommand(
            workspace_id=ws_id,
            workflow_id=wf_id,
            trigger_type="CRON",
            cron_expr="*/5 * * * *",
        )
    )
    assert cron_matches_timestamp("*/5 * * * *", datetime(2026, 11, 17, 10, 5, tzinfo=UTC))
    cron_outcomes = await dispatcher.evaluate_cron_triggers(
        workspace_id=ws_id, now_utc=datetime(2026, 11, 17, 10, 5, tzinfo=UTC)
    )
    assert len(cron_outcomes) == 1 and cron_outcomes[0].trigger_id == cron_trig.id

    # OUTBOX_EVENT Opt-In (`auto_help_on_publish=False` by default at Day-0 -> 0 help call)
    outbox_trig = await dispatcher.create_trigger(
        CreateTriggerCommand(
            workspace_id=ws_id,
            workflow_id=wf_id,
            trigger_type="OUTBOX_EVENT",
            auto_help_on_publish=False,
        )
    )
    assert outbox_trig.auto_help_on_publish is False
    help_svc = _FakeHelpService()
    pub_evt_1 = WorkflowPublished.create(
        workflow_id=wf_id, workspace_id=ws_id, version="1.0.1", title="Qualification"
    )
    res_off = await dispatcher.handle_workflow_published(pub_evt_1, help_service=help_svc)
    assert res_off == []
    assert len(help_svc.calls) == 0

    # Enable explicit opt-in -> executes generate-and-attach-help once per version
    await dispatcher.update_trigger(
        workspace_id=ws_id,
        trigger_id=outbox_trig.id,
        cmd=UpdateTriggerCommand(auto_help_on_publish=True),
    )
    res_on = await dispatcher.handle_workflow_published(pub_evt_1, help_service=help_svc)
    assert len(res_on) == 1 and res_on[0].dispatched is True
    assert len(help_svc.calls) == 1
    assert log_trig.id != outbox_trig.id

    # OutboxEventBus triggers_outbox subscriber + daemon once
    bus = OutboxEventBus()
    assert bus.publish_idempotent(pub_evt_1) >= 1
    assert len(bus.workflow_published_queue) == 1
    assert await serve_trigger_dispatcher_daemon(once=True) == 0


def test_worker_role_trigger_dispatcher_cli_once(monkeypatch: pytest.MonkeyPatch) -> None:
    import sys

    monkeypatch.delitem(sys.modules, "orcia_worker.docling_indexer", raising=False)
    assert worker_roles_main(["--role", "trigger-dispatcher", "--serve", "--once"]) == 0
