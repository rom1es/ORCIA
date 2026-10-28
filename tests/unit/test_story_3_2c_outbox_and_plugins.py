"""Unit tests for Story 3.2c: Transactional Outbox, OutboxRelayPort & Python entry_points."""

from __future__ import annotations

import inspect
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest

from orcia_core.bootstrap.plugin_registry import PluginRegistryService
from orcia_core.orchestration._internal.outbox_repository import SqlDomainEventsOutboxRepository
from orcia_kernel.events import (
    ArtifactProduced,
    GateEvaluated,
    HumanArbitrationRequested,
    RunTerminated,
    StepCompleted,
)
from orcia_worker.outbox_relay import (
    DbosOutboxRelay,
    DramatiqOutboxRelay,
    OutboxEventBus,
    _dbos_outbox_relay_step,
    dbos_outbox_relay_workflow,
    outbox_relay_actor,
)


def test_plugin_registry_discovers_uri_resolvers_and_llm_gateways() -> None:
    """Verify `PluginRegistryService` discovers `orcia.uri_resolvers` and `orcia.llm_gateways`."""
    resolvers = PluginRegistryService.discover_uri_resolvers()
    assert set(resolvers.keys()) == {"git", "jira", "confluence", "db", "nexus", "orcia"}
    assert resolvers["git"].scheme == "git"
    assert resolvers["git"].supports_cas_pinning is True
    assert resolvers["db"].scheme == "db"

    gateways = PluginRegistryService.discover_llm_gateways()
    assert set(gateways.keys()) == {"litellm", "cassette"}
    litellm_inst = gateways["litellm"]()
    cassette_inst = gateways["cassette"]()
    assert hasattr(litellm_inst, "complete")
    assert hasattr(cassette_inst, "complete")


def test_outbox_event_bus_and_both_outbox_relay_implementations() -> None:
    """Verify `OutboxEventBus`, `DramatiqOutboxRelay`, and `DbosOutboxRelay` idempotency (`C3`)."""
    bus = OutboxEventBus()
    evt_step = StepCompleted.create(
        step_execution_id="0192c4e0-0000-7000-8000-000000000911",
        run_id="0192c4e0-0000-7000-8000-000000000901",
        workspace_id="0192c4e0-0000-7000-8000-000000000201",
        step_key="frame-architecture-intent",
        cost_usd=0.25,
        trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
    )
    evt_art = ArtifactProduced.create(
        snapshot_id="0192c4e0-0000-7000-8000-000000000912",
        run_id="0192c4e0-0000-7000-8000-000000000901",
        workspace_id="0192c4e0-0000-7000-8000-000000000201",
        artifact_cas_key="cas/sha256/abc",
        artifact_sha256="a" * 64,
        trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
    )

    dramatiq_relay = DramatiqOutboxRelay(event_bus=bus)
    dramatiq_relay.enqueue_in_transaction(evt_step)
    dramatiq_relay.enqueue_in_transaction(evt_step)  # idempotent duplicate enqueue
    dramatiq_relay.enqueue_in_transaction(evt_art)

    relayed = dramatiq_relay.relay_pending_batch(batch_size=10)
    assert relayed == 2
    assert dramatiq_relay.relay_pending_batch(batch_size=10) == 0

    # Re-publishing the exact same event to the bus delivers 0 duplicates
    assert bus.publish_idempotent(evt_step) == 0
    assert len(bus.audit_finops_ledger) == 2
    assert len(bus.ontology_extraction_queue) == 1
    assert len(bus.sse_published_messages) == 2

    # DbosOutboxRelay implementation
    bus2 = OutboxEventBus()
    dbos_relay = DbosOutboxRelay(event_bus=bus2)
    evt_gate = GateEvaluated.create(
        gate_evaluation_id="0192c4e0-0000-7000-8000-000000000913",
        run_id="0192c4e0-0000-7000-8000-000000000901",
        workspace_id="0192c4e0-0000-7000-8000-000000000201",
        gate_type="DETERMINISTIC",
        passed=True,
    )
    evt_term = RunTerminated.create(
        run_id="0192c4e0-0000-7000-8000-000000000901",
        workspace_id="0192c4e0-0000-7000-8000-000000000201",
        final_status="COMPLETED",
        total_cost_usd=0.50,
    )
    evt_arb = HumanArbitrationRequested.create(
        arbitration_id="0192c4e0-0000-7000-8000-000000000914",
        run_id="0192c4e0-0000-7000-8000-000000000901",
        workspace_id="0192c4e0-0000-7000-8000-000000000201",
        step_key="step-1",
    )
    dbos_relay.enqueue_in_transaction(evt_gate)
    dbos_relay.enqueue_in_transaction(evt_gate)
    dbos_relay.enqueue_in_transaction(evt_term)
    dbos_relay.enqueue_in_transaction(evt_arb)
    assert dbos_relay.relay_pending_batch(batch_size=10) == 3
    assert len(bus2.audit_finops_ledger) == 3

    assert outbox_relay_actor.fn(10) == 0
    assert inspect.unwrap(_dbos_outbox_relay_step)(10) == 0
    assert callable(inspect.unwrap(dbos_outbox_relay_workflow))


@pytest.mark.asyncio
async def test_sql_domain_events_outbox_repository_unit_paths() -> None:
    """Exercise unit paths of `SqlDomainEventsOutboxRepository`."""
    mock_session = AsyncMock()
    evt = StepCompleted.create(
        step_execution_id="0192c4e0-0000-7000-8000-000000000911",
        run_id="0192c4e0-0000-7000-8000-000000000901",
        workspace_id="0192c4e0-0000-7000-8000-000000000201",
        step_key="step-1",
        cost_usd=0.25,
        trace_id="4bf92f3577b34da6a3ce929d0e0e4736",
    )
    row_dict = {
        "event_id": evt.event_id,
        "event_type": evt.event_type,
        "aggregate_type": evt.aggregate_type,
        "aggregate_id": evt.aggregate_id,
        "run_id": evt.run_id,
        "workspace_id": evt.workspace_id,
        "payload_jsonb": '{"step_key":"step-1","step_status":"COMMITTED","cost_usd":0.25}',
        "trace_id": evt.trace_id,
        "status": "PENDING",
        "attempts": 0,
    }
    mock_result = MagicMock()
    mock_result.mappings.return_value.all.return_value = [row_dict]
    mock_session.execute.return_value = mock_result

    class FakeUoW:
        @asynccontextmanager
        async def session_scope(self) -> AsyncIterator[Any]:
            yield mock_session

    repo = SqlDomainEventsOutboxRepository(FakeUoW())  # type: ignore[arg-type]
    await repo.enqueue_event(evt)
    bus = OutboxEventBus()
    relayed = await repo.claim_and_relay_pending_batch(
        batch_size=10,
        subscriber_fn=bus.publish_idempotent_async,
    )
    assert relayed == 1
    assert len(bus.audit_finops_ledger) == 1

    listed = await repo.list_events_by_run(evt.run_id or "")
    assert len(listed) == 1
    assert listed[0].event_id == evt.event_id
