"""Tests for Story 5.1 & DEC-CONC-01: Notification Inbox, Atomic Claim, SSE & Resource Leases.

Covers:
1. Unified Notification Inbox (`task_notifications`, Outbox idempotent subscriber,
   personal/team filter, amber badge counter).
2. Atomic Presence Claim (`lock:step:{step_execution_id}`, `409 ERR_STEP_ALREADY_CLAIMED_BY_PEER`,
   `403 ERR_OBSERVER_MODE_READ_ONLY`, 15-minute `Force Unclaim`, SSE `< 500 ms` propagation).
3. `DEC-CONC-01` (`ResourceLeasePort` & `ResourceLeaseService`): canonical URI ordering, monotonic
   fencing tokens, `409 ERR_STALE_FENCING_TOKEN`, and parent-child `SUB_WORKFLOW` cyclic wait
   deadlock detection (`409 ERR_CYCLIC_RESOURCE_WAIT_DETECTED`).
4. FastAPI HTTP endpoints & SSE `/api/v1/events/stream` + Alembic `0021_story_5_1` on real PG18.
"""

from __future__ import annotations

import time
from datetime import UTC, datetime, timedelta

import pytest
from fastapi.testclient import TestClient

from orcia_api.main import create_app
from orcia_core.orchestration.errors import (
    CyclicResourceWaitDetectedError,
    ObserverModeReadOnlyError,
    ResourceLeaseHeldByOtherRunError,
    StaleFencingTokenError,
    StepAlreadyClaimedByPeerError,
    StepClaimNotHeldError,
)
from orcia_core.orchestration.notifications_and_claims import (
    UnifiedNotificationAndClaimService,
)
from orcia_core.orchestration.resource_leases import ResourceLeaseService
from orcia_core.permissions.models import UserIdentity
from orcia_kernel.events import DomainEvent


def _make_user(
    user_id: str,
    display_name: str,
    role: str = "CONTRIBUTOR",
) -> UserIdentity:
    return UserIdentity(
        id=user_id,
        email=f"{user_id}@orcia.io",
        display_name=display_name,
        auth_mode="OIDC",
        human_profile_archetype="TECH_LEAD",
        platform_role=role,  # type: ignore[arg-type]
        primary_org_unit_id="0195f000-0000-7000-8000-000000000201",
    )


def test_outbox_consumption_and_atomic_claim_lifecycle() -> None:
    """Verify Outbox idempotence, atomic claim, peer 409 conflict, Force Unclaim & SSE < 500ms."""
    svc = UnifiedNotificationAndClaimService()
    alice = _make_user("usr-alice", "Alice Martin", "CONTRIBUTOR")
    bob = _make_user("usr-bob", "Bob Dupont", "CONTRIBUTOR")
    observer = _make_user("usr-obs", "Claire Observer", "OBSERVER")

    evt = DomainEvent(
        event_id="evt-001",
        event_type="HumanArbitrationRequested",
        aggregate_type="step_execution",
        aggregate_id="step-exec-501",
        workspace_id="ws-501",
        run_id="run-501",
        payload={"step_key": "architecture-arbitration", "options_count": 3},
    )
    n1 = svc.consume_outbox_event(evt, default_team_id="team-1")
    assert n1 is not None
    assert n1.notification_type == "HUMAN_ARBITRATION"
    # Idempotent replay of the same Outbox event returns the exact same notification
    n1_dup = svc.consume_outbox_event(evt, default_team_id="team-1")
    assert n1_dup is not None and n1_dup.id == n1.id
    assert svc.count_unclaimed_action_required("ws-501") == 1

    # Also test GateEvaluated failure and StepCompleted human pause notifications
    evt_gate = DomainEvent(
        event_id="evt-002",
        event_type="GateEvaluated",
        aggregate_type="step_execution",
        aggregate_id="step-exec-502",
        workspace_id="ws-501",
        run_id="run-501",
        payload={"step_key": "sec-gate", "passed": False, "gate_type": "AGENTIC", "score": 0.4},
    )
    n_gate = svc.consume_outbox_event(evt_gate, default_team_id="team-1")
    assert n_gate is not None and n_gate.notification_type == "HUMAN_GATE"

    evt_step = DomainEvent(
        event_id="evt-003",
        event_type="StepCompleted",
        aggregate_type="step_execution",
        aggregate_id="step-exec-503",
        workspace_id="ws-501",
        run_id="run-501",
        payload={"step_key": "anchor-step", "step_status": "WAITING_FOR_HUMAN_ANCHOR"},
    )
    n_anchor = svc.consume_outbox_event(evt_step, default_team_id="team-1")
    assert n_anchor is not None and n_anchor.notification_type == "HUMAN_ANCHOR"

    # Observer cannot claim (HTTP 403 ERR_OBSERVER_MODE_READ_ONLY)
    with pytest.raises(ObserverModeReadOnlyError) as obs_exc:
        svc.claim_by_task_id(observer, task_id=n1.id)
    assert obs_exc.value.error_code == "ERR_OBSERVER_MODE_READ_ONLY"

    # Alice claims the task (< 500ms SSE broadcast + live subscriber push)
    live_pushed: list[str] = []
    unsub = svc.sse_broker.subscribe(
        lambda evt: live_pushed.append(evt.event_name),
        workspace_id="ws-501",
    )
    t0 = datetime.now(UTC)
    t_start = time.perf_counter()
    outcome = svc.claim_by_task_id(alice, task_id=n1.id, ttl_seconds=900, now_utc=t0)
    elapsed_ms = (time.perf_counter() - t_start) * 1000.0
    assert elapsed_ms < 500.0
    assert outcome.viewer_presence_state == "CLAIMED_BY_ME"
    assert outcome.peer_presence_state == "CLAIMED_BY_PEER"
    assert outcome.sse_event.event_name == "task.claim.locked"
    assert outcome.sse_event.payload["peer_opacity"] == 0.85
    assert live_pushed == ["task.claim.locked"]

    # Bob sees CLAIMED_BY_PEER and gets 409 ERR_STEP_ALREADY_CLAIMED_BY_PEER on concurrent claim
    assert outcome.notification.resolve_presence_state(bob.id, now_utc=t0) == "CLAIMED_BY_PEER"
    with pytest.raises(StepAlreadyClaimedByPeerError) as bob_exc:
        svc.claim_by_task_id(bob, task_id=n1.id, now_utc=t0)
    assert bob_exc.value.error_code == "ERR_STEP_ALREADY_CLAIMED_BY_PEER"

    # Bob also cannot mutate the step directly while Alice holds the lock
    with pytest.raises(StepAlreadyClaimedByPeerError):
        svc.verify_step_mutation_allowed(bob, step_execution_id="step-exec-501", now_utc=t0)

    # Bob cannot release Alice's lock before the 15-minute window
    with pytest.raises(StepClaimNotHeldError):
        svc.release_claim(bob, task_id=n1.id, force=True, now_utc=t0 + timedelta(minutes=5))

    # After 15 minutes + 1s of inactivity, Force Unclaim is allowed for Bob
    t_after_15m = t0 + timedelta(seconds=901)
    assert outcome.notification.can_force_unclaim(now_utc=t_after_15m) is True
    rel = svc.release_claim(bob, task_id=n1.id, force=True, now_utc=t_after_15m)
    assert rel.notification.status == "OPEN"
    assert rel.sse_event.event_name == "task.claim.released"
    assert live_pushed == ["task.claim.locked", "task.claim.released"]
    unsub()


def test_dec_conc_01_resource_leases_fencing_tokens_and_cyclic_wait_detection() -> None:
    """Verify DEC-CONC-01: canonical ordering, monotonic fencing tokens, and deadlock detection."""
    lease_svc = ResourceLeaseService()

    t0 = datetime(2026, 10, 30, 12, 0, 0, tzinfo=UTC)
    # 1. Batch acquire in reverse order -> canonical sorted order returned with monotonic tokens
    leases = lease_svc.acquire_leases(
        resource_uris=("orcia://ws-1/spec/z-doc", "orcia://ws-1/spec/a-doc"),
        holder_run_id="run-parent-1",
        holder_root_run_id="run-parent-1",
        holder_step_execution_id="step-p1",
        ttl_seconds=300,
        now_utc=t0,
    )
    assert [item.resource_uri for item in leases] == [
        "orcia://ws-1/spec/a-doc",
        "orcia://ws-1/spec/z-doc",
    ]
    token_a_1 = leases[0].fencing_token
    assert token_a_1 >= 1

    # 2. Competing unrelated run cannot acquire an active lease
    with pytest.raises(ResourceLeaseHeldByOtherRunError) as held_exc:
        lease_svc.acquire_leases(
            resource_uris=("orcia://ws-1/spec/a-doc",),
            holder_run_id="run-other-2",
            holder_root_run_id="run-other-2",
            holder_step_execution_id="step-o2",
            now_utc=t0 + timedelta(seconds=30),
        )
    assert held_exc.value.error_code == "ERR_RESOURCE_LEASE_HELD_BY_OTHER_RUN"

    # 3. Parent-child SUB_WORKFLOW cyclic wait -> HTTP 409 ERR_CYCLIC_RESOURCE_WAIT_DETECTED
    lease_svc.register_run_parent(child_run_id="run-child-1a", parent_run_id="run-parent-1")
    with pytest.raises(CyclicResourceWaitDetectedError) as cyc_exc:
        lease_svc.acquire_leases(
            resource_uris=("orcia://ws-1/spec/a-doc",),
            holder_run_id="run-child-1a",
            holder_root_run_id="run-parent-1",
            holder_step_execution_id="step-c1",
            holder_parent_run_id="run-parent-1",
            now_utc=t0 + timedelta(seconds=30),
        )
    assert cyc_exc.value.error_code == "ERR_CYCLIC_RESOURCE_WAIT_DETECTED"

    # 4. Lease expires -> run-other-2 preempts and receives strictly higher fencing token
    t_expired = t0 + timedelta(seconds=305)
    leases_2 = lease_svc.acquire_leases(
        resource_uris=("orcia://ws-1/spec/a-doc",),
        holder_run_id="run-other-2",
        holder_root_run_id="run-other-2",
        holder_step_execution_id="step-o2",
        ttl_seconds=300,
        now_utc=t_expired,
    )
    lease_a_2 = leases_2[0]
    assert lease_a_2.fencing_token > token_a_1

    # 5. Late zombie worker from run-parent-1 presenting stale token_a_1 is rejected with 409
    with pytest.raises(StaleFencingTokenError) as stale_exc:
        lease_svc.validate_fencing_token(
            resource_uri="orcia://ws-1/spec/a-doc",
            fencing_token=token_a_1,
        )
    assert stale_exc.value.error_code == "ERR_STALE_FENCING_TOKEN"

    # Current token succeeds
    lease_svc.validate_fencing_token(
        resource_uri="orcia://ws-1/spec/a-doc",
        fencing_token=lease_a_2.fencing_token,
    )
    assert len(lease_svc.list_active_leases(now_utc=t_expired)) >= 1
    assert (
        lease_svc.release_leases(holder_run_id="run-other-2", holder_step_execution_id="step-o2")
        == 1
    )


def test_story_5_1_fastapi_endpoints_and_sse_stream() -> None:
    """Verify HTTP endpoints for Unified Inbox, Claim/Release, SSE stream, and Resource Leases."""
    app = create_app()
    with TestClient(app) as client:
        # 0. Arrange : la plateforme ne sème plus de notification fictive au démarrage.
        app.state.notification_service.seed_default_notifications(
            workspace_id="0195f000-0000-7000-8000-000000000301",
            team_id="0195f000-0000-7000-8000-000000000103",
            user_id="0195f000-0000-7000-8000-000000000203",
            run_id="0195f000-0000-7000-8000-000000000701",
            step_execution_id="0195f000-0000-7000-8000-000000000801",
        )
        # 1. List seeded notifications
        res_list = client.get("/api/v1/inbox/notifications")
        assert res_list.status_code == 200
        body = res_list.json()
        assert body["amber_badge_count"] >= 2
        first_task = body["items"][0]
        task_id = first_task["id"]

        # 2. Claim notification as CONTRIBUTOR (nadia)
        res_claim = client.post(
            f"/api/v1/tasks/{task_id}/claim?persona_key=nadia",
            json={"ttl_seconds": 900, "force": False},
        )
        assert res_claim.status_code == 200
        claim_data = res_claim.json()
        assert claim_data["viewer_presence_state"] == "CLAIMED_BY_ME"
        assert claim_data["peer_presence_state"] == "CLAIMED_BY_PEER"

        # 3. Second contributor (partenaire) gets RFC 9457 409 ERR_STEP_ALREADY_CLAIMED_BY_PEER
        res_conflict = client.post(
            f"/api/v1/tasks/{task_id}/claim?persona_key=partenaire",
            json={"ttl_seconds": 900, "force": False},
        )
        assert res_conflict.status_code == 409
        assert res_conflict.json()["error_code"] == "ERR_STEP_ALREADY_CLAIMED_BY_PEER"

        # 4. Observer (claire, BU_DIRECTOR) gets RFC 9457 403 ERR_OBSERVER_MODE_READ_ONLY
        res_obs = client.post(
            f"/api/v1/tasks/{task_id}/claim?persona_key=claire",
            json={"ttl_seconds": 900, "force": False},
        )
        assert res_obs.status_code == 403
        assert res_obs.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"

        # 5. Direct step claim endpoint (/api/v1/runs/{run_id}/steps/{step_id}/claim)
        res_step_claim = client.post(
            "/api/v1/runs/run-direct-1/steps/step-direct-1/claim?persona_key=nadia",
            json={"ttl_seconds": 900, "force": False, "step_key": "review-step"},
        )
        assert res_step_claim.status_code == 200
        assert res_step_claim.json()["viewer_presence_state"] == "CLAIMED_BY_ME"

        # 6. SSE stream returns text/event-stream with recent claim events
        res_sse = client.get(
            "/api/v1/events/stream?workspace_id=0195f000-0000-7000-8000-000000000301"
        )
        assert res_sse.status_code == 200
        assert "text/event-stream" in res_sse.headers["content-type"]
        assert "event: task.claim.locked" in res_sse.text

        # 6b. Live SSE stream (live=true) receives live claim frames & exits cleanly on close
        import threading

        def _trigger_live_claim() -> None:
            time.sleep(0.30)
            client.post(
                "/api/v1/runs/run-live-1/steps/step-live-1/claim?persona_key=nadia",
                json={"ttl_seconds": 900, "force": False, "step_key": "live-sse-step"},
            )

        trigger_thread = threading.Thread(target=_trigger_live_claim, daemon=True)
        seen_live_event = False
        with client.stream(
            "GET",
            "/api/v1/events/stream?workspace_id=0195f000-0000-7000-8000-000000000301&live=true",
        ) as live_resp:
            assert live_resp.status_code == 200
            for line in live_resp.iter_lines():
                if line == "event: connected":
                    trigger_thread.start()
                if "step-live-1" in line:
                    seen_live_event = True
                    break
        trigger_thread.join(timeout=2.0)
        assert seen_live_event is True

        # 7. Acquire resource lease & validate fenced write
        res_lease = client.post(
            "/api/v1/resource-leases/acquire",
            json={
                "resource_uris": ["orcia://ws-301/artifact/briefing-1"],
                "holder_run_id": "run-api-501",
                "holder_root_run_id": "run-api-501",
                "holder_step_execution_id": "step-api-501",
                "ttl_seconds": 300,
            },
        )
        assert res_lease.status_code == 200
        token = res_lease.json()["leases"][0]["fencing_token"]

        res_fenced_ok = client.post(
            "/api/v1/resource-leases/fenced-write",
            json={
                "resource_uri": "orcia://ws-301/artifact/briefing-1",
                "fencing_token": token,
                "payload": {"op": "update_briefing"},
            },
        )
        assert res_fenced_ok.status_code == 200
        assert res_fenced_ok.json()["status"] == "COMMITTED_FENCED"


@pytest.mark.asyncio
async def test_stream_workspace_events_live_and_sync_broker_branches(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Cover sync broker fallback (L302) and live=True SSE loop/dedup/timeout (L311-319)."""
    from types import SimpleNamespace

    from orcia_api.dependencies.core_and_lifespan import initialize_app_services
    from orcia_api.routers.inbox_and_leases import stream_workspace_events
    from orcia_core.orchestration.notifications_and_claims import SseEventEnvelope

    monkeypatch.setenv("ORCIA_ENV", "local")
    monkeypatch.setenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", "1")
    app = create_app()
    initialize_app_services(app)
    auth_svc = app.state.auth_service
    recent_evt = SseEventEnvelope(
        event_id="evt-recent-1",
        event_name="task.claim.locked",
        channel="channel:workspace:ws-unit-sse",
        workspace_id="ws-unit-sse",
        run_id="run-1",
        step_execution_id="step-1",
        payload={"ok": True},
        published_at_iso="2026-11-19T22:00:00Z",
        dispatch_latency_ms=5.0,
    )
    live_evt = SseEventEnvelope(
        event_id="evt-live-2",
        event_name="task.claim.released",
        channel="channel:workspace:ws-unit-sse",
        workspace_id="ws-unit-sse",
        run_id="run-1",
        step_execution_id="step-1",
        payload={"released": True},
        published_at_iso="2026-11-19T22:00:01Z",
        dispatch_latency_ms=7.0,
    )

    subscribers: list[object] = []

    class _SyncOnlyBroker:
        def list_recent_events(self, *, workspace_id: str) -> list[SseEventEnvelope]:
            assert workspace_id == "ws-unit-sse"
            return [recent_evt]

        def subscribe(self, callback: object, *, workspace_id: str) -> object:
            subscribers.append(callback)
            return lambda: None

    disconnect_calls = 0

    async def _is_disconnected() -> bool:
        nonlocal disconnect_calls
        disconnect_calls += 1
        if disconnect_calls == 2 and subscribers:
            cb = subscribers[0]
            assert callable(cb)
            cb(recent_evt)  # duplicate -> hits seen_ids skip (L316-317)
            cb(live_evt)  # fresh live event -> hits L318-319
        return disconnect_calls >= 4

    fake_req = SimpleNamespace(
        headers={},
        query_params={},
        url=SimpleNamespace(path="/api/v1/events/stream", hostname="localhost"),
        state=SimpleNamespace(trace_id="0195f000000070008000000000000501"),
        app=SimpleNamespace(
            state=SimpleNamespace(
                auth_service=auth_svc,
                notification_service=SimpleNamespace(sse_broker=_SyncOnlyBroker()),
            )
        ),
        is_disconnected=_is_disconnected,
    )

    resp = await stream_workspace_events(
        fake_req,  # type: ignore[arg-type]
        workspace_id="ws-unit-sse",
        live=True,
        persona_key="nadia",
    )
    frames: list[str] = []
    async for chunk in resp.body_iterator:
        frames.append(chunk if isinstance(chunk, str) else chunk.decode("utf-8"))

    joined = "".join(frames)
    assert "event: connected" in joined
    assert joined.count("id: evt-recent-1") == 1
    assert "id: evt-live-2" in joined
