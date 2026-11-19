"""Security tests for human-anchor authorship enforcement and READ_ONLY_OBSERVER rejection."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient

from orcia_api.dependencies import get_autonomous_supervision_service, initialize_app_services
from orcia_api.main import create_app
from orcia_core.permissions import UserIdentity


@pytest.mark.asyncio
async def test_agent_identity_rejected_on_human_anchor_and_observer_blocked_on_mutations(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Enforce 422 ERR_HUMAN_ANCHOR_REQUIRED for agent callers and 403 OBSERVER on all mutations."""
    monkeypatch.setenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", "1")
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    app = create_app()
    initialize_app_services(app)

    auth_svc = app.state.auth_service
    obs_user = UserIdentity(
        id="0195f000-0000-7000-8000-000000008099",
        email="observer.orch@orcia.ia",
        display_name="Observateur Orchestration",
        auth_mode="LOCAL",
        human_profile_archetype="OBSERVER",
        platform_role="OBSERVER",
        primary_org_unit_id="0192c4e0-0000-7000-8000-000000000001",
        roles=("OBSERVER",),
    )
    auth_svc.register_user(obs_user)
    obs_token = auth_svc.jwt_manager.issue_token_pair(
        user_id=obs_user.id,
        email=obs_user.email,
        role=obs_user.platform_role,
        org_unit_id=obs_user.primary_org_unit_id,
        archetype=obs_user.human_profile_archetype,
        auth_mode=obs_user.auth_mode,
    ).access_token

    ws_id = "0192c4e0-0000-7000-8000-000000000201"
    auto_run_id = "0195f000-0000-7000-8000-000000008450"
    from starlette.requests import Request

    dummy_req = Request({"type": "http", "app": app, "headers": [], "path": "/"})
    sup_svc = get_autonomous_supervision_service(dummy_req)
    await sup_svc.register_autonomous_run(
        run_id=auto_run_id,
        workspace_id=ws_id,
        workflow_id="wf-01-qualification-prd",
        contract_id="0195f000-0000-7000-8000-000000008401",
        status="COMMITTED_AUTONOMOUS",
    )

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r_inst = await client.post(
            "/api/v1/orchestration/runs/instantiate",
            params={"persona_key": "karim"},
            json={
                "workflow_uri": "orcia://workflows/claims-engineering-delivery",
                "workspace_id": ws_id,
            },
        )
        assert r_inst.status_code == 200, r_inst.text
        run_id = r_inst.json()["run"]["id"]

        r_gate_eval = await client.post(
            "/api/v1/gates/human/evaluate",
            params={"persona_key": "karim"},
            json={
                "workspace_id": ws_id,
                "run_id": run_id,
                "step_execution_id": "0195f000-0000-7000-8000-000000008801",
                "step_key": "frame-architecture-intent",
                "policy": "mandatory_full",
                "deterministic_status": "PASS",
                "agentic_score": 0.94,
                "ontology_conflicts": 0,
                "stale_warnings": 0,
                "artifact_payload": {
                    "sections": [
                        {
                            "chunk_key": "sec-arch",
                            "title": "Architecture",
                            "content": "Contenu initial pour validation par découpage.",
                        }
                    ]
                },
            },
        )
        assert r_gate_eval.status_code == 200, r_gate_eval.text
        eval_id = r_gate_eval.json()["evaluation"]["id"]

        # 1. Agent identity signing a human anchor -> HTTP 422 ERR_HUMAN_ANCHOR_REQUIRED
        r_agent_anchor = await client.post(
            "/api/v1/orchestration/runs/anchors/sign",
            params={"persona_key": "karim"},
            json={
                "run_id": run_id,
                "step_key": "frame-architecture-intent",
                "section_key": "human_architecture_intent",
                "content_text": (
                    "Contenu généré automatiquement par un agent dépassant 30 caractères."
                ),
                "signature_text": "AgentBot",
                "author_type": "AGENT",
            },
        )
        assert r_agent_anchor.status_code == 422
        assert r_agent_anchor.headers["content-type"].startswith("application/problem+json")
        assert r_agent_anchor.json()["error_code"] == "ERR_HUMAN_ANCHOR_REQUIRED"

        # 2. Both OBSERVER JWT and X-Orcia-Access-Mode: READ_ONLY_OBSERVER -> 403
        mutation_requests: list[tuple[str, dict[str, object]]] = [
            (
                "/api/v1/orchestration/runs/anchors/sign",
                {
                    "run_id": run_id,
                    "step_key": "frame-architecture-intent",
                    "section_key": "human_architecture_intent",
                    "content_text": "Intention humaine valide dépassant trente caractères.",
                    "signature_text": "Observateur",
                    "author_type": "HUMAN",
                },
            ),
            (
                f"/api/v1/orchestration/runs/{run_id}/steps/delegate-remediation-subworkflow/challenge",
                {
                    "target_upstream_step_key": "frame-architecture-intent",
                    "challenged_section_key": "human_architecture_intent",
                    "challenge_reason": "Tentative de contestation en mode lecture seule.",
                    "target_profile_archetype": "PM_BUSINESS",
                },
            ),
            (
                f"/api/v1/orchestration/runs/{run_id}/steps/frame-architecture-intent/replay",
                {"sub_workflow_step_key": None},
            ),
            (
                "/api/v1/gates/human/evaluate",
                {
                    "workspace_id": ws_id,
                    "run_id": run_id,
                    "step_execution_id": "0195f000-0000-7000-8000-000000008802",
                    "step_key": "frame-architecture-intent",
                    "policy": "mandatory_full",
                    "artifact_payload": {"summary": "test"},
                },
            ),
            (f"/api/v1/gates/human/{eval_id}/inspect-hypotheses", {}),
            (
                f"/api/v1/gates/human/{eval_id}/chunks/sec-arch/decide",
                {"action": "APPROVE"},
            ),
            (
                f"/api/v1/gates/human/{eval_id}/finalize",
                {"review_duration_ms": 20000, "explicit_hypotheses_confirmation": True},
            ),
            (
                f"/api/v1/runs/{auto_run_id}/emergency-stop",
                {"reason": "Tentative observateur", "suspend_trigger": False},
            ),
            (
                f"/api/v1/runs/{auto_run_id}/invalidate-and-restore",
                {"comment": "Tentative rollback observateur"},
            ),
        ]

        for obs_params, obs_headers in (
            ({}, {"Authorization": f"Bearer {obs_token}"}),
            ({"persona_key": "karim"}, {"X-Orcia-Access-Mode": "READ_ONLY_OBSERVER"}),
        ):
            for path, body in mutation_requests:
                res = await client.post(path, params=obs_params, headers=obs_headers, json=body)
                assert res.status_code == 403, (
                    f"Expected 403 on {path}, got {res.status_code}: {res.text}"
                )
                assert res.headers["content-type"].startswith("application/problem+json")
                assert res.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"
