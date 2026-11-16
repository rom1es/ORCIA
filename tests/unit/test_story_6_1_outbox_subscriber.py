"""Unit tests for Story 6.1 AuditLedgerOutboxSubscriber and DEC-SEC-01 scrubbing (`AD-20`)."""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from unittest.mock import AsyncMock

import pytest

from orcia_core.audit_finops.outbox_subscriber import (
    AuditLedgerOutboxSubscriber,
    scrub_sensitive_dict,
)
from orcia_core.kernel.events import (
    AdminConnectionTested,
    DomainEvent,
    StepCompleted,
)


def test_scrub_sensitive_dict_redacts_credentials() -> None:
    """Verify DEC-SEC-01 scrubbing wipes api keys, tokens, passwords and auth headers."""
    raw = {
        "provider": "ollama",
        "api_key": "sk-super-secret-key-12345",  # pragma: allowlist secret
        "nested": {
            "token": "ghp_" + "topsecretpattoken9999",  # pragma: allowlist secret
            "password": "mypassword123",  # pragma: allowlist secret
            "safe_param": "temperature=0.7",
            "authorization": "Bearer " + "eyJhbGciOi...",  # pragma: allowlist secret
        },
        "public_model": "qwen2.5:7b",
    }
    scrubbed = scrub_sensitive_dict(raw)
    assert scrubbed["provider"] == "ollama"
    assert scrubbed["public_model"] == "qwen2.5:7b"
    assert scrubbed["api_key"] == "[REDACTED_SECRET]"
    assert isinstance(scrubbed["nested"], dict)
    assert scrubbed["nested"]["safe_param"] == "temperature=0.7"
    assert scrubbed["nested"]["token"] == "[REDACTED_SECRET]"
    assert scrubbed["nested"]["password"] == "[REDACTED_SECRET]"
    assert scrubbed["nested"]["authorization"] == "[REDACTED_SECRET]"


@pytest.mark.asyncio
async def test_subscriber_step_completed_event() -> None:
    """Verify StepCompleted domain event is mapped to AuditLedgerEntry and recorded."""
    mock_sink = AsyncMock()
    subscriber = AuditLedgerOutboxSubscriber(sink=mock_sink)

    run_id = str(uuid.uuid4())
    step_id = str(uuid.uuid4())

    event = StepCompleted.create(
        step_execution_id=step_id,
        run_id=run_id,
        workspace_id="ws-123",
        step_key="compile_starlark",
        step_status="COMMITTED",
        cost_usd=0.0039,
    )

    await subscriber.on_domain_event(event)

    assert mock_sink.record_entry.call_count == 1
    recorded = mock_sink.record_entry.call_args[0][0]
    assert recorded.source_event_id == event.event_id
    assert recorded.run_id == run_id
    assert recorded.step_execution_id == step_id
    assert recorded.event_type == "StepCompleted"
    assert recorded.cost_usd == 0.0039


@pytest.mark.asyncio
async def test_subscriber_admin_connection_tested_event_with_scrubbing() -> None:
    """Verify AdminConnectionTested event records run_id=None and scrubs sensitive fields."""
    mock_sink = AsyncMock()
    subscriber = AuditLedgerOutboxSubscriber(sink=mock_sink)

    event = AdminConnectionTested.create(
        actor_id="admin-1",
        target_type="llm",
        target_id="deepseek-r1",
        protocol="HTTP",
        test_status="SUCCESS",
        latency_ms=45,
        workspace_id="ws-root",
        metadata={
            "secret_token_used": (  # pragma: allowlist secret
                "sk-canary-secret-should-never-leak-9988"
            ),
        },
    )

    await subscriber.on_domain_event(event)

    assert mock_sink.record_entry.call_count == 1
    recorded = mock_sink.record_entry.call_args[0][0]
    assert recorded.source_event_id == event.event_id
    assert recorded.run_id is None
    assert recorded.actor_type == "ADMIN_CONNECTION_TEST"
    assert recorded.event_type == "AdminConnectionTested"
    assert recorded.latency_ms == 45
    # Verify DEC-SEC-01: secret_token_used is scrubbed in metadata
    assert recorded.metadata.get("secret_token_used") == "[REDACTED_SECRET]"
    assert "sk-canary-secret" not in str(recorded.metadata)


@pytest.mark.asyncio
async def test_subscriber_ignores_unmapped_events_gracefully() -> None:
    """Verify that subscriber does not throw or record entries for unrelated domain events."""
    mock_sink = AsyncMock()
    subscriber = AuditLedgerOutboxSubscriber(sink=mock_sink)

    @dataclass(frozen=True, slots=True)
    class UnrelatedEvent(DomainEvent):
        pass

    event = UnrelatedEvent(
        event_id=str(uuid.uuid4()),
        event_type="SomethingElse",
        aggregate_type="test",
        aggregate_id="123",
        run_id=None,
        workspace_id=None,
        payload={},
        trace_id="00000000000000000000000000000000",
    )
    await subscriber.on_domain_event(event)

    assert mock_sink.record_entry.call_count == 0


@pytest.mark.asyncio
async def test_subscriber_covers_all_auditable_event_types() -> None:
    """Verify subscriber handles GateEvaluated, ArtifactProduced, and alerts."""
    mock_sink = AsyncMock()
    subscriber = AuditLedgerOutboxSubscriber(sink=mock_sink)

    event_types = [
        ("GateEvaluated", {"gate_key": "security_gate", "decision": "APPROVED"}),
        ("ArtifactProduced", {"artifact_id": "art-1", "artifact_type": "json"}),
        ("RunTerminated", {"final_status": "COMPLETED"}),
        ("SettingsChanged", {"category": "llm", "key": "model", "scope_level": "GLOBAL"}),
        ("BudgetCircuitTripped", {"trip_reason": "budget ceiling hit"}),
        ("BudgetOverrideApproved", {"override_amount_usd": 50.0}),
        ("RemoteUsageAnomalyCapped", {"connector_id": "conn-1"}),
        ("ConnectorCircuitTripped", {"connector_id": "conn-1", "reason": "rate limit"}),
    ]

    for etype, payload in event_types:
        evt = DomainEvent(
            event_id=str(uuid.uuid4()),
            event_type=etype,
            aggregate_type="test",
            aggregate_id="123",
            run_id=str(uuid.uuid4()),
            workspace_id="ws-1",
            payload=payload,
            trace_id="00000000000000000000000000000000",
        )
        await subscriber.on_domain_event(evt)

    assert mock_sink.record_entry.call_count == len(event_types)


@pytest.mark.asyncio
async def test_subscriber_handles_sink_exception_gracefully() -> None:
    """Verify subscriber catches sink exceptions without crashing outbox processor."""
    mock_sink = AsyncMock()
    mock_sink.record_entry.side_effect = RuntimeError("DB connection dropped")
    subscriber = AuditLedgerOutboxSubscriber(sink=mock_sink)

    evt = DomainEvent(
        event_id=str(uuid.uuid4()),
        event_type="StepCompleted",
        aggregate_type="step",
        aggregate_id="step-1",
        run_id=str(uuid.uuid4()),
        workspace_id="ws-1",
        payload={"step_key": "step_a"},
        trace_id="00000000000000000000000000000000",
    )
    # Should log error and re-raise to trigger outbox retry
    with pytest.raises(RuntimeError, match="DB connection dropped"):
        await subscriber.on_domain_event(evt)
    assert mock_sink.record_entry.call_count == 1
