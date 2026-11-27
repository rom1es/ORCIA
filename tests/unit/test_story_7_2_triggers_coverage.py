"""Additional unit & repository-branch coverage tests for Story 7.2 triggers."""

from __future__ import annotations

from dataclasses import replace
from datetime import UTC, datetime
from typing import Any

import pytest

from orcia_core.kernel.errors import PolicyDeniedError, TransientConnectorError
from orcia_core.kernel.log_sink_ports import LogEntry, LogQuery
from orcia_core.orchestration import (
    CreateTriggerCommand,
    TriggerDispatcherService,
    UpdateTriggerCommand,
    WorkflowTriggerEntity,
)
from orcia_core.orchestration._triggers_log_cron import (
    LogSinkAnomalyScanner,
    cron_matches_timestamp,
    evaluate_self_trigger_guard,
    validate_cron_expr,
)
from orcia_core.orchestration._triggers_runtime_ports import (
    DbosSetWorkflowIdDispatcher,
    RedisTriggerIdempotencyLockAdapter,
    run_with_error_taxonomy,
)
from orcia_core.permissions import (
    AutonomyContractService,
    HierarchicalRbacService,
    IamAccountRecord,
    SignAutonomyContractCommand,
    compute_webhook_hmac_sha256,
)
from orcia_core.permissions.errors import (
    TriggerDuplicateKeyError,
    TriggerNotFoundError,
    ValidationDomainError,
    WebhookSignatureInvalidError,
)
from orcia_core.permissions.models import UserIdentity
from orcia_core.permissions.secret_hint import SecretInputSpec
from orcia_kernel.ids import new_uuid7_str


class _EmptyLogSink:
    async def query_logs(self, query: LogQuery) -> list[LogEntry]:
        del query
        return []

    async def count_errors(
        self, fingerprint: str, window_seconds: int, *, service: str | None = None
    ) -> int:
        del fingerprint, window_seconds, service
        return 0

    async def healthcheck(self) -> bool:
        return True


class _SingleLogSink:
    def __init__(self, count: int = 1) -> None:
        self._count = count

    async def query_logs(self, query: LogQuery) -> list[LogEntry]:
        del query
        return [
            LogEntry(
                timestamp="2026-11-17T10:00:00Z",
                level="ERROR",
                service="api",
                logger="orcia.api",
                message="Boom",
                workspace_id=new_uuid7_str(),
            )
        ]

    async def count_errors(
        self, fingerprint: str, window_seconds: int, *, service: str | None = None
    ) -> int:
        del fingerprint, window_seconds, service
        return self._count

    async def healthcheck(self) -> bool:
        return True


class _FakeAsyncRedis:
    def __init__(self) -> None:
        self._keys: set[str] = set()

    async def set(self, key: str, value: str, *, nx: bool = False, ex: int = 0) -> bool:
        del value, ex
        if nx and key in self._keys:
            return False
        self._keys.add(key)
        return True


async def _make_contracts() -> tuple[AutonomyContractService, str, str]:
    rbac = HierarchicalRbacService()
    ws_id = new_uuid7_str()
    wf_id = f"orcia://workflows/cov-{ws_id[:8]}"
    lead_id = new_uuid7_str()
    sp_id = new_uuid7_str()
    svc = AutonomyContractService(rbac_service=rbac)
    signer = UserIdentity(
        id=lead_id,
        email="lead-cov@orcia.test",
        display_name="Lead",
        auth_mode="local",
        human_profile_archetype="TECH_LEAD",
        platform_role="TEAM_LEAD",
        primary_org_unit_id=ws_id,
    )
    sp = IamAccountRecord(
        id=sp_id,
        principal_id="sp-cov-auto",
        display_name="SP Cov",
        email=None,
        account_kind="SERVICE_PRINCIPAL",
        auth_source="LOCAL",
        roles=("TEAM_LEAD",),
        team_ids=(ws_id,),
        status="ACTIVE",
    )
    await svc.sign_contract(
        SignAutonomyContractCommand(
            workspace_id=ws_id,
            workflow_id=wf_id,
            workflow_version="1.0.0",
            workflow_sha256="b" * 64,
            criticality="LOW_NON_CRITICAL",
            service_principal_id=sp.id,
            allowed_read_sources=("catalog:read",),
            allowed_write_actions=("help_article:publish",),
            max_cost_per_run_usd=15.0,
        ),
        signer=signer,
        service_principal=sp,
        allowed_scope_ids=[ws_id],
    )
    return svc, ws_id, wf_id


def test_cron_validation_edges_and_anomaly_scanner() -> None:
    validate_cron_expr("0,30 9-17 * 1-12 1-5")
    assert cron_matches_timestamp("0,30 9-17 * 1-12 0-6", datetime(2026, 11, 17, 9, 30, tzinfo=UTC))

    for bad in ("* * *", "0,,5 * * * *", "*/0 * * * *", "65 * * * *", "10-5 * * * *", "x * * * *"):
        with pytest.raises(ValidationDomainError):
            validate_cron_expr(bad)


@pytest.mark.asyncio
async def test_log_sink_scanner_empty_and_min_count_and_sp_guard() -> None:
    ws_id = new_uuid7_str()
    trig = WorkflowTriggerEntity(
        id=new_uuid7_str(),
        trigger_key="trg-cov",
        workspace_id=ws_id,
        workflow_def_id=ws_id,
        trigger_type="LOG_SINK_ALERT",
        workflow_id="wf-cov",
    )
    assert await LogSinkAnomalyScanner(_EmptyLogSink()).scan_trigger(trig) == []
    assert (
        await LogSinkAnomalyScanner(_SingleLogSink(count=1)).scan_trigger(trig, min_error_count=5)
        == []
    )

    verdict = evaluate_self_trigger_guard(
        trigger=trig,
        payload={"actor_type": "SERVICE_PRINCIPAL", "origin_service_principal": "sp:any"},
    )
    assert verdict.blocked is True
    assert evaluate_self_trigger_guard(trigger=trig).blocked is False


@pytest.mark.asyncio
async def test_runtime_ports_redis_and_error_taxonomy() -> None:
    lock = RedisTriggerIdempotencyLockAdapter(redis_client=_FakeAsyncRedis())
    assert lock.build_key("t1", "k1") == "lock:trigger:t1:k1"
    assert await lock.try_acquire(trigger_id="t1", idempotency_key="k1") is True
    assert await lock.try_acquire(trigger_id="t1", idempotency_key="k1") is False

    dbos = DbosSetWorkflowIdDispatcher()
    trig = WorkflowTriggerEntity(
        id="t1",
        trigger_key="tk",
        workspace_id="w1",
        workflow_def_id="d1",
        trigger_type="WEBHOOK",
        workflow_id="wf1",
    )
    res = await dbos.dispatch(
        dbos_workflow_id="t1:k1",
        trigger=trig,
        run_id="r1",
        idempotency_key="k1",
        payload={"a": 1},
    )
    assert res["dbos_workflow_id"] == "t1:k1"

    async def _always_transient() -> dict[str, Any]:
        raise TransientConnectorError(retry_after_s=0.0, detail_override="503")

    with pytest.raises(TransientConnectorError):
        await run_with_error_taxonomy(_always_transient, max_transient_retries=1)

    async def _policy_denied() -> dict[str, Any]:
        raise PolicyDeniedError(detail_override="denied")

    with pytest.raises(PolicyDeniedError):
        await run_with_error_taxonomy(_policy_denied, max_transient_retries=2)


@pytest.mark.asyncio
async def test_dispatcher_crud_limits_pause_and_repo_delegation() -> None:
    contracts, ws_id, wf_id = await _make_contracts()
    dispatcher = TriggerDispatcherService(contract_service=contracts)

    with pytest.raises(ValidationDomainError):
        await dispatcher.create_trigger(
            CreateTriggerCommand(workspace_id=ws_id, workflow_id=wf_id, trigger_type="CRON")
        )

    wh_secret = "whsec_cov_secret_123456"  # pragma: allowlist secret
    trig = await dispatcher.create_trigger(
        CreateTriggerCommand(
            workspace_id=ws_id,
            workflow_id=wf_id,
            trigger_type="WEBHOOK",
            trigger_key="unique-k",
            max_runs_per_hour=2,
            max_daily_cost_usd=0.10,
            webhook_secret=SecretInputSpec(action="replace", plaintext_value=wh_secret),
        )
    )
    with pytest.raises(TriggerDuplicateKeyError):
        await dispatcher.create_trigger(
            CreateTriggerCommand(
                workspace_id=ws_id,
                workflow_id=wf_id,
                trigger_type="WEBHOOK",
                trigger_key="unique-k",
            )
        )

    raw_body = b'{"event":"push"}'
    valid_sig = compute_webhook_hmac_sha256(raw_body, wh_secret)
    _, is_new_1 = await dispatcher.verify_webhook_request(
        trigger_id=trig.id, raw_body=raw_body, signature_header=valid_sig, delivery_key="d1"
    )
    _, is_new_2 = await dispatcher.verify_webhook_request(
        trigger_id=trig.id, raw_body=raw_body, signature_header=valid_sig, delivery_key="d1"
    )
    assert is_new_1 is True and is_new_2 is False

    with pytest.raises(WebhookSignatureInvalidError):
        await dispatcher.verify_webhook_request(
            trigger_id=trig.id, raw_body=raw_body, signature_header="sha256=bad", delivery_key="d2"
        )

    assert len(await dispatcher.list_active_by_type("WEBHOOK")) == 1
    paused = await dispatcher.update_trigger(
        workspace_id=ws_id,
        trigger_id=trig.id,
        cmd=UpdateTriggerCommand(
            status="PAUSED",
            webhook_secret=SecretInputSpec(action="clear"),
            max_runs_per_hour=5,
            max_daily_cost_usd=0.06,
        ),
    )
    assert paused.status == "PAUSED"
    assert paused.webhook_secret_configured is False
    paused_res = await dispatcher.dispatch_trigger(trigger_id=trig.id, idempotency_key="while-p")
    assert paused_res.outcome == "PAUSED"

    # Signature provided when no secret configured -> invalid
    with pytest.raises(WebhookSignatureInvalidError):
        await dispatcher.verify_webhook_request(
            trigger_id=trig.id, raw_body=raw_body, signature_header=valid_sig, delivery_key="d3"
        )

    # Re-activate and trip max_daily_cost_usd
    await dispatcher.update_trigger(
        workspace_id=ws_id, trigger_id=trig.id, cmd=UpdateTriggerCommand(status="ACTIVE")
    )
    ok_res = await dispatcher.dispatch_trigger(
        trigger_id=trig.id, idempotency_key="cost-1", estimated_cost_usd=0.05
    )
    assert ok_res.dispatched is True
    cost_trip = await dispatcher.dispatch_trigger(
        trigger_id=trig.id, idempotency_key="cost-2", estimated_cost_usd=0.05
    )
    assert cost_trip.outcome == "CIRCUIT_OPEN"
    no_raise_open = await dispatcher.dispatch_trigger(
        trigger_id=trig.id, idempotency_key="cost-3", raise_on_circuit_open=False
    )
    assert no_raise_open.outcome == "CIRCUIT_OPEN"

    with pytest.raises(TriggerNotFoundError):
        await dispatcher.update_trigger(
            workspace_id="other-ws", trigger_id=trig.id, cmd=UpdateTriggerCommand(status="ACTIVE")
        )
    with pytest.raises(TriggerNotFoundError):
        await dispatcher.reset_circuit(workspace_id="other-ws", trigger_id=trig.id)
    with pytest.raises(TriggerNotFoundError):
        await dispatcher.delete_trigger(workspace_id="other-ws", trigger_id=trig.id)

    await dispatcher.delete_trigger(workspace_id=ws_id, trigger_id=trig.id)
    with pytest.raises(TriggerNotFoundError):
        await dispatcher.get_trigger(trig.id)


@pytest.mark.asyncio
async def test_dispatcher_repo_delegation_paths() -> None:
    contracts, ws_id, wf_id = await _make_contracts()

    class _FakeRepo:
        def __init__(self) -> None:
            self.saved: dict[str, tuple[WorkflowTriggerEntity, str | None]] = {}
            self.events: list[Any] = []
            self.fail_count = 0

        async def list_triggers(
            self, *, workspace_id: str, workflow_id: str | None = None
        ) -> list[WorkflowTriggerEntity]:
            return [
                e
                for e, _ in self.saved.values()
                if e.workspace_id == workspace_id
                and (workflow_id is None or e.workflow_id == workflow_id)
            ]

        async def list_active_triggers(
            self, *, trigger_type: Any = None
        ) -> list[WorkflowTriggerEntity]:
            return [
                e
                for e, _ in self.saved.values()
                if e.status == "ACTIVE" and (trigger_type is None or e.trigger_type == trigger_type)
            ]

        async def get_trigger(
            self, trigger_id: str
        ) -> tuple[WorkflowTriggerEntity, str | None] | None:
            return self.saved.get(trigger_id)

        async def save_trigger(
            self,
            trigger: WorkflowTriggerEntity,
            *,
            encrypted_secret: str | None = None,
            clear_secret: bool = False,
        ) -> WorkflowTriggerEntity:
            prev = self.saved.get(trigger.id, (trigger, None))[1]
            self.saved[trigger.id] = (trigger, None if clear_secret else (encrypted_secret or prev))
            return trigger

        async def delete_trigger(self, *, workspace_id: str, trigger_id: str) -> None:
            del workspace_id
            self.saved.pop(trigger_id, None)

        async def record_webhook_delivery(self, *, trigger_id: str, delivery_key: str) -> bool:
            del trigger_id, delivery_key
            return True

        async def count_runs_last_hour(self, *, trigger_id: str) -> int:
            del trigger_id
            return 0

        async def sum_daily_cost_usd(self, *, trigger_id: str) -> float:
            del trigger_id
            return 0.0

        async def create_idempotent_trigger_run(self, **kwargs: Any) -> bool:
            return kwargs["idempotency_key"] != "sql-dup"

        async def mark_trigger_fired(self, *, trigger_id: str) -> WorkflowTriggerEntity | None:
            return self.saved[trigger_id][0]

        async def record_trigger_failure(
            self, *, trigger_id: str, max_consecutive_failures: int
        ) -> tuple[int, bool]:
            del trigger_id
            self.fail_count += 1
            return self.fail_count, self.fail_count >= max_consecutive_failures

        async def set_trigger_status(
            self, *, trigger_id: str, status: Any, consecutive_failures: int | None = None
        ) -> WorkflowTriggerEntity:
            ent, sec = self.saved[trigger_id]
            updated = replace(
                ent,
                status=status,
                consecutive_failures=(
                    consecutive_failures
                    if consecutive_failures is not None
                    else ent.consecutive_failures
                ),
            )
            self.saved[trigger_id] = (updated, sec)
            return updated

        async def publish_outbox_event(self, event: Any) -> None:
            self.events.append(event)

    repo = _FakeRepo()
    dispatcher = TriggerDispatcherService(contract_service=contracts, repository=repo)  # type: ignore[arg-type]
    trig = await dispatcher.create_trigger(
        CreateTriggerCommand(workspace_id=ws_id, workflow_id=wf_id, trigger_type="WEBHOOK")
    )
    assert len(await dispatcher.list_triggers(workspace_id=ws_id)) == 1
    assert len(await dispatcher.list_active_by_type("WEBHOOK")) == 1
    await dispatcher.update_trigger(
        workspace_id=ws_id, trigger_id=trig.id, cmd=UpdateTriggerCommand(status="ACTIVE")
    )
    _, is_new = await dispatcher.verify_webhook_request(
        trigger_id=trig.id, raw_body=b"{}", signature_header=None, delivery_key="dk-1"
    )
    assert is_new is True
    dup = await dispatcher.dispatch_trigger(trigger_id=trig.id, idempotency_key="sql-dup")
    assert dup.outcome == "DUPLICATE_SUPPRESSED"
    ok = await dispatcher.dispatch_trigger(trigger_id=trig.id, idempotency_key="ok-1")
    assert ok.dispatched is True
    await dispatcher.reset_circuit(workspace_id=ws_id, trigger_id=trig.id)
    await dispatcher.delete_trigger(workspace_id=ws_id, trigger_id=trig.id)
