"""Unit tests for Story 25.3: zero RAM demo run, strict PG18 run sync & blackboard governance."""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any
from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from orcia_api.main import create_app
from orcia_api.routers import _orchestration_sql_hydration as sql_hydration
from orcia_core.orchestration import build_default_orchestration_setup_service
from orcia_core.permissions.models import UserIdentity


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


def test_build_default_orchestration_setup_service_starts_with_zero_runs() -> None:
    """Story 25.3: `build_default_orchestration_setup_service()` must start with 0 RAM demo runs."""
    svc = build_default_orchestration_setup_service()
    assert svc.runs == ()
    assert list(svc._runs_by_id.keys()) == []

    client = TestClient(create_app())
    state_resp = client.get("/api/v1/orchestration/state?persona_key=marc")
    assert state_resp.status_code == 200
    body = state_resp.json()
    assert body["runs"] == []
    assert len(body["workflows"]) >= 1


async def test_hydrate_orchestration_runs_from_sql_purges_stale_ram_runs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Story 25.3: `hydrate_orchestration_runs_from_sql` removes runs absent from PG18."""
    svc = build_default_orchestration_setup_service()
    lead = _lead_user()
    run_stale = svc.instantiate_workflow_run(
        lead,
        workflow_uri="orcia://workflows/claims-engineering-delivery",
        workspace_id="0192c4e0-0000-7000-8000-000000000201",
        trigger_id="trg-stale",
        trigger_idempotency_key="idem-stale",
    )
    run_kept = svc.instantiate_workflow_run(
        lead,
        workflow_uri="orcia://workflows/claims-engineering-delivery",
        workspace_id="0192c4e0-0000-7000-8000-000000000201",
        trigger_id="trg-kept",
        trigger_idempotency_key="idem-kept",
    )
    assert len(svc.runs) == 2

    fake_uow = object()
    fake_request: Any = SimpleNamespace(
        app=SimpleNamespace(state=SimpleNamespace(dbos_uow=fake_uow))
    )
    mock_list_sql = AsyncMock(return_value=(run_kept,))
    monkeypatch.setattr(sql_hydration, "list_workflow_runs_with_locks_sql", mock_list_sql)

    await sql_hydration.hydrate_orchestration_runs_from_sql(fake_request, svc)

    assert [r.id for r in svc.runs] == [run_kept.id]
    assert run_stale.id not in svc._runs_by_id
    assert ("trg-stale", "idem-stale") not in svc._idempotency_index
    assert ("trg-kept", "idem-kept") in svc._idempotency_index

    # When PG18 returns empty (e.g. after pnpm db:reset), 0 runs remain in RAM
    monkeypatch.setattr(
        sql_hydration, "list_workflow_runs_with_locks_sql", AsyncMock(return_value=())
    )
    await sql_hydration.hydrate_orchestration_runs_from_sql(fake_request, svc)
    assert svc.runs == ()
    assert svc._idempotency_index == {}


def test_blackboard_endpoint_exposes_real_pending_arbitrations_and_human_anchors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Story 25.3: `GET /runs/{run_id}/blackboard` exposes pending_arbitrations & human_anchors."""
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "1")
    client = TestClient(create_app())

    inst_res = client.post(
        "/api/v1/orchestration/runs/instantiate?persona_key=marc",
        json={
            "workflow_uri": "orcia://workflows/claims-engineering-delivery",
            "workspace_id": "0192c4e0-0000-7000-8000-000000000201",
        },
    )
    assert inst_res.status_code == 200
    run_id = inst_res.json()["run"]["id"]

    # Initially: 0 pending arbitrations, 0 signed human anchors
    bb0 = client.get(f"/api/v1/orchestration/runs/{run_id}/blackboard?persona_key=marc")
    assert bb0.status_code == 200
    assert bb0.json()["pending_arbitrations"] == []
    assert bb0.json()["human_anchors"] == []

    # Sign human anchor -> exposed in `human_anchors`
    sign_res = client.post(
        "/api/v1/orchestration/runs/anchors/sign?persona_key=marc",
        json={
            "run_id": run_id,
            "step_key": "frame-architecture-intent",
            "section_key": "human_architecture_intent",
            "content_text": (
                "Architecture hexagonale stricte et découpage domaine sans dépendance circulaire."
            ),
            "signature_text": "Marc TechLead",
            "author_type": "HUMAN",
        },
    )
    assert sign_res.status_code == 200

    bb1 = client.get(f"/api/v1/orchestration/runs/{run_id}/blackboard?persona_key=marc")
    assert bb1.status_code == 200
    assert len(bb1.json()["human_anchors"]) == 1
    assert bb1.json()["human_anchors"][0]["section_key"] == "human_architecture_intent"
    assert bb1.json()["pending_arbitrations"] == []

    # Request arbitration with real options -> exposed in `pending_arbitrations`
    arb_res = client.post(
        f"/api/v1/orchestration/runs/{run_id}/steps/frame-architecture-intent/arbitration?persona_key=marc",
        json={
            "question_title": "Stratégie de partitionnement Outbox",
            "context_summary": "Volume élevé détecté sur le bus d'événements.",
            "tie_break_policy": "PAUSE_AND_ESCALATE",
            "options_matrix": [
                {
                    "option_key": "OPT_PG_LISTEN",
                    "title": "PostgreSQL LISTEN/NOTIFY + Outbox",
                    "pros": ["Latence faible"],
                    "cons": ["Couplage PG"],
                    "si_impact": "Nul",
                    "finops_impact": "0 $/mois",
                    "recommended": True,
                },
                {
                    "option_key": "OPT_POLL_5S",
                    "title": "Polling SQL 5s",
                    "pros": ["Simple"],
                    "cons": ["Latence 5s"],
                    "si_impact": "Faible",
                    "finops_impact": "0 $/mois",
                    "recommended": False,
                },
            ],
        },
    )
    assert arb_res.status_code == 200
    arb_id = arb_res.json()["arbitration"]["id"]

    bb2 = client.get(f"/api/v1/orchestration/runs/{run_id}/blackboard?persona_key=marc")
    assert bb2.status_code == 200
    pending = bb2.json()["pending_arbitrations"]
    assert len(pending) == 1
    assert pending[0]["id"] == arb_id
    assert [o["option_key"] for o in pending[0]["options_matrix"]] == [
        "OPT_PG_LISTEN",
        "OPT_POLL_5S",
    ]

    # Resolve arbitration -> `pending_arbitrations` becomes empty
    res_arb = client.post(
        f"/api/v1/orchestration/runs/{run_id}/steps/frame-architecture-intent/arbitration/resolve?persona_key=marc",
        json={
            "arbitration_id": arb_id,
            "selected_option_key": "OPT_PG_LISTEN",
            "human_justification": "Option optimale en latence et coût nul.",
        },
    )
    assert res_arb.status_code == 200

    bb3 = client.get(f"/api/v1/orchestration/runs/{run_id}/blackboard?persona_key=marc")
    assert bb3.status_code == 200
    assert bb3.json()["pending_arbitrations"] == []
    assert len(bb3.json()["human_anchors"]) == 1
