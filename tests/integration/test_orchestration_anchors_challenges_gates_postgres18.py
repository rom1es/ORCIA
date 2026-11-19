"""Vertical HTTP -> PG18 + Redis 7.4 integration tests for orchestration, gates, and kill-switch."""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Iterator
from pathlib import Path
from urllib.parse import quote_plus
from uuid import UUID

import pytest
import sqlalchemy as sa
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine
from testcontainers.postgres import PostgresContainer
from testcontainers.redis import RedisContainer

REPO_ROOT = Path(__file__).resolve().parents[2]
DB_NAME = "orcia_orch_gates_pg18"
DB_USER = "orcia"
DB_PASSWORD = "orcia_orch_gates_pg18_pw"  # pragma: allowlist secret


@pytest.fixture(scope="module")
def infra_urls() -> Iterator[tuple[str, str]]:
    """Start real PostgreSQL 18 + pgvector and Redis 7.4 containers and migrate Alembic head."""
    with (
        PostgresContainer(
            "pgvector/pgvector:pg18", username=DB_USER, password=DB_PASSWORD, dbname=DB_NAME
        ) as pg,
        RedisContainer("redis:7.4-alpine") as redis_box,
    ):
        pg_url = (
            f"postgresql+asyncpg://{DB_USER}:{quote_plus(DB_PASSWORD)}"
            f"@127.0.0.1:{pg.get_exposed_port(5432)}/{DB_NAME}"
        )
        redis_host = redis_box.get_container_host_ip()
        redis_port = int(redis_box.get_exposed_port(6379))
        redis_url = f"redis://{redis_host}:{redis_port}/0"
        env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "PYTHONPATH": os.environ.get("PYTHONPATH", ""),
            "DATABASE_URL": pg_url,
            "ORCIA_ENV_FILE": str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"),
        }
        alembic_bin = str(Path(sys.executable).with_name("alembic"))
        subprocess.run(
            [alembic_bin, "-c", "infra/migrations/alembic.ini", "upgrade", "head"],
            cwd=REPO_ROOT,
            env=env,
            check=True,
        )
        yield pg_url, redis_url


@pytest.mark.asyncio
async def test_orchestration_anchors_challenges_gates_and_kill_switch_persist_in_postgres18(
    infra_urls: tuple[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify Composition Root HTTP -> PG18 persistence, append-only snapshots, and cold reload."""
    pg_url, redis_url = infra_urls
    monkeypatch.setenv("DATABASE_URL", pg_url)
    monkeypatch.setenv("REDIS_URL", redis_url)
    monkeypatch.setenv("ORCIA_ENV_FILE", str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"))
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    monkeypatch.setenv("ORCIA_JWT_SIGNING_SECRET", "orcia-orch-gates-pg18-jwt-secret-0001")
    monkeypatch.setenv("ORCIA_PASSTHROUGH_MASTER_KEY", "orcia-orch-gates-pg18-vault-key-0001")
    monkeypatch.setenv("ORCIA_ENABLE_PG_SESSION_MAKER", "1")
    monkeypatch.delenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", raising=False)

    from orcia_api.main import create_app

    engine = create_async_engine(pg_url)
    try:
        # Phase 1: Real Composition Root lifespan without dependency_overrides or app.state.*
        app1 = create_app()
        async with (
            app1.router.lifespan_context(app1),
            AsyncClient(transport=ASGITransport(app=app1), base_url="http://test") as client1,
        ):
            assert getattr(app1.state, "dbos_uow", None) is not None
            assert getattr(app1.state, "gate_repository", None) is not None

            # 0. Bootstrap Day-0 admin and real UUIDv7 workspace
            r_first = await client1.post(
                "/api/v1/bootstrap/welcome-setup/first-admin",
                json={
                    "email": "admin.orch@orcia.ia",
                    "display_name": "Admin Orchestration",
                    "password": "OrciaAdmin!2026",  # pragma: allowlist secret
                    "orcia_env": "local",
                },
            )
            assert r_first.status_code == 200, r_first.text
            admin_token = r_first.json()["access_token"]
            auth_headers = {"Authorization": f"Bearer {admin_token}"}

            r_ws = await client1.post(
                "/api/v1/workspaces",
                headers=auth_headers,
                json={
                    "name": "Espace Orchestration PG18",
                    "slug": "espace-orchestration-pg18",
                    "visibility_mode": "STANDARD",
                    "lifecycle_phase": "BUILD",
                },
            )
            assert r_ws.status_code == 201, r_ws.text
            ws_id = r_ws.json()["id"]
            UUID(ws_id)

            # 1. Instantiate workflow run -> workflow_runs + run_lock_manifests
            r_inst = await client1.post(
                "/api/v1/orchestration/runs/instantiate",
                headers=auth_headers,
                json={
                    "workflow_uri": "orcia://workflows/claims-engineering-delivery",
                    "workspace_id": ws_id,
                },
            )
            assert r_inst.status_code == 200, r_inst.text
            run_id = r_inst.json()["run"]["id"]
            run_lock_sha = r_inst.json()["run"]["run_lock"]["manifest_sha256"]
            UUID(run_id)
            assert run_lock_sha

            # 2. Sign human anchor -> human_anchor_signatures
            anchor_text = (
                "Architecture hexagonale stricte avec ports dédiés et persistance PostgreSQL 18."
            )
            r_anchor = await client1.post(
                "/api/v1/orchestration/runs/anchors/sign",
                headers=auth_headers,
                json={
                    "run_id": run_id,
                    "step_key": "frame-architecture-intent",
                    "section_key": "human_architecture_intent",
                    "content_text": anchor_text,
                    "signature_text": "Admin Orchestration",
                    "author_type": "HUMAN",
                },
            )
            assert r_anchor.status_code == 200, r_anchor.text
            anchor_sha = r_anchor.json()["signature"]["content_sha256"]
            assert len(anchor_sha) == 64

            # 3. Execute & commit initial step snapshot -> blackboard_snapshots (#1)
            r_exec = await client1.post(
                "/api/v1/orchestration/runs/steps/execute",
                headers=auth_headers,
                json={
                    "run_id": run_id,
                    "step_key": "frame-architecture-intent",
                    "commit_immediately": True,
                    "require_human_anchor": True,
                    "cost_usd": 0.15,
                },
            )
            assert r_exec.status_code == 200, r_exec.text
            initial_snap_id = r_exec.json()["committed_snapshot"]["id"]
            async with engine.connect() as pre_conn:
                pre_snaps = (
                    (
                        await pre_conn.execute(
                            sa.text(
                                "SELECT id::text, branch_status FROM blackboard_snapshots "
                                "WHERE run_id = CAST(:id AS uuid) ORDER BY created_at ASC, id ASC"
                            ),
                            {"id": run_id},
                        )
                    )
                    .mappings()
                    .all()
                )
            assert len(pre_snaps) == 1
            pg_initial_snap_id = str(pre_snaps[0]["id"])

            # 4. Submit upstream challenge -> upstream_challenges
            r_chal = await client1.post(
                f"/api/v1/orchestration/runs/{run_id}/steps/delegate-remediation-subworkflow/challenge",
                headers=auth_headers,
                json={
                    "target_upstream_step_key": "frame-architecture-intent",
                    "challenged_section_key": "human_architecture_intent",
                    "challenge_reason": (
                        "Contrainte API partenaire v3 exigeant une fenêtre maximale de 15 minutes."
                    ),
                    "target_profile_archetype": "PM_BUSINESS",
                },
            )
            assert r_chal.status_code == 200, r_chal.text
            challenge_id = r_chal.json()["challenge"]["id"]

            # 5. Replay from upstream step -> append-only new snapshot in blackboard_snapshots (#2)
            r_replay = await client1.post(
                f"/api/v1/orchestration/runs/{run_id}/steps/frame-architecture-intent/replay",
                headers=auth_headers,
                json={"sub_workflow_step_key": None},
            )
            assert r_replay.status_code == 200, r_replay.text
            replay_json = r_replay.json()["replay"]
            assert initial_snap_id in replay_json["superseded_snapshot_ids"]
            assert len(replay_json["new_active_snapshot_ids"]) >= 1

            # 6. Deterministic gate evaluation -> gate_evaluations (DETERMINISTIC)
            step_exec_id = r_exec.json()["step_execution"]["id"]
            r_det = await client1.post(
                "/api/v1/gates/deterministic/evaluate",
                headers=auth_headers,
                json={
                    "workspace_id": ws_id,
                    "run_id": run_id,
                    "step_execution_id": step_exec_id,
                    "step_key": "frame-architecture-intent",
                    "artifact_payload": {"summary": "Spécification OpenAPI 3.1 conforme."},
                    "required_sections": ["summary"],
                },
            )
            assert r_det.status_code == 200, r_det.text
            assert r_det.json()["evaluation"]["status"] == "PASS"

            r_det_fail = await client1.post(
                "/api/v1/gates/deterministic/evaluate",
                headers=auth_headers,
                json={
                    "workspace_id": ws_id,
                    "run_id": run_id,
                    "step_execution_id": step_exec_id,
                    "step_key": "frame-architecture-intent",
                    "artifact_payload": {"summary": "Partiel"},
                    "required_sections": ["summary", "security_controls"],
                    "raise_on_failure": False,
                },
            )
            assert r_det_fail.status_code == 200, r_det_fail.text
            assert r_det_fail.json()["evaluation"]["status"] == "FAIL"

            # 6b. Human arbitration escalation & resolution -> human_arbitration_requests
            r_arb_req = await client1.post(
                f"/api/v1/orchestration/runs/{run_id}/steps/frame-architecture-intent/arbitration",
                headers=auth_headers,
                json={
                    "question_title": "Arbitrage fenêtre contractuelle",
                    "context_summary": "Choix entre fenêtre 15 min et verrou 48h.",
                    "tie_break_policy": "PAUSE_AND_ESCALATE",
                    "options_matrix": [
                        {
                            "option_key": "OPT_A",
                            "title": "Option A 15 min",
                            "pros": ["Conforme API v3"],
                            "cons": ["Fenêtre courte"],
                            "si_impact": "Faible",
                            "finops_impact": "0.02 USD",
                            "recommended": True,
                        },
                        {
                            "option_key": "OPT_B",
                            "title": "Option B 48h",
                            "pros": ["Confort"],
                            "cons": ["Hors contrat v3"],
                            "si_impact": "Élevé",
                            "finops_impact": "0.18 USD",
                            "recommended": False,
                        },
                    ],
                },
            )
            assert r_arb_req.status_code == 200, r_arb_req.text
            arb_id = r_arb_req.json()["arbitration"]["id"]

            r_arb_res = await client1.post(
                f"/api/v1/orchestration/runs/{run_id}/steps/frame-architecture-intent/arbitration/resolve",
                headers=auth_headers,
                json={
                    "arbitration_id": arb_id,
                    "selected_option_key": "OPT_A",
                    "human_justification": "Option conforme au contrat API v3.",
                },
            )
            assert r_arb_res.status_code == 200, r_arb_res.text
            assert r_arb_res.json()["arbitration"]["status"] == "RESOLVED_BY_HUMAN"

            # 7. Adaptive Human Gate -> gate_evaluations (HUMAN) + chunk_approvals
            large_section = " ".join(["validation"] * 560)
            r_h_eval = await client1.post(
                "/api/v1/gates/human/evaluate",
                headers=auth_headers,
                json={
                    "workspace_id": ws_id,
                    "run_id": run_id,
                    "step_execution_id": step_exec_id,
                    "step_key": "frame-architecture-intent",
                    "policy": "mandatory_full",
                    "deterministic_status": "PASS",
                    "agentic_score": 0.94,
                    "ontology_conflicts": 0,
                    "stale_warnings": 0,
                    "artifact_payload": {
                        "sections": [
                            {
                                "chunk_key": "sec-architecture",
                                "title": "Architecture",
                                "content": large_section,
                            },
                            {
                                "chunk_key": "sec-security",
                                "title": "Sécurité",
                                "content": large_section,
                            },
                        ]
                    },
                },
            )
            assert r_h_eval.status_code == 200, r_h_eval.text
            human_eval_id = r_h_eval.json()["evaluation"]["id"]

            r_insp = await client1.post(
                f"/api/v1/gates/human/{human_eval_id}/inspect-hypotheses",
                headers=auth_headers,
            )
            assert r_insp.status_code == 200, r_insp.text

            r_c1 = await client1.post(
                f"/api/v1/gates/human/{human_eval_id}/chunks/sec-architecture/decide",
                headers=auth_headers,
                json={"action": "APPROVE"},
            )
            assert r_c1.status_code == 200, r_c1.text

            r_c2 = await client1.post(
                f"/api/v1/gates/human/{human_eval_id}/chunks/sec-security/decide",
                headers=auth_headers,
                json={
                    "action": "CO_EDIT",
                    "co_edited_content": f"{large_section} controle_humain_signe",
                },
            )
            assert r_c2.status_code == 200, r_c2.text

            r_fin = await client1.post(
                f"/api/v1/gates/human/{human_eval_id}/finalize",
                headers=auth_headers,
                json={
                    "review_duration_ms": 3200,
                    "explicit_hypotheses_confirmation": True,
                },
            )
            assert r_fin.status_code == 200, r_fin.text
            assert r_fin.json()["evaluation"]["status"] == "PASS"
            assert r_fin.json()["evaluation"]["fast_approval_warning"] is True

            # 7b. Gate evaluation on synthetic run_id/step_id exercises auto-parent creation in PG18
            from orcia_kernel.ids import new_uuid7_str

            synth_run_id = new_uuid7_str()
            synth_step_id = new_uuid7_str()
            r_synth_gate = await client1.post(
                "/api/v1/gates/human/evaluate",
                headers=auth_headers,
                json={
                    "workspace_id": ws_id,
                    "run_id": synth_run_id,
                    "step_execution_id": synth_step_id,
                    "step_key": "step-synth-gate",
                    "policy": "mandatory_full",
                    "artifact_payload": {"summary": "Synthétique PG18"},
                },
            )
            assert r_synth_gate.status_code == 200, r_synth_gate.text
            assert await app1.state.gate_repository.get_human_evaluation(new_uuid7_str()) is None
            assert (
                len(
                    await app1.state.gate_repository.list_gate_evaluations(
                        run_id=run_id, gate_type="DETERMINISTIC"
                    )
                )
                >= 2
            )

            # 8. Autonomous run -> emergency-stop -> invalidate-and-restore keeps kill-switch state
            r_sp = await client1.post(
                "/api/v1/settings/iam/accounts",
                headers=auth_headers,
                json={
                    "principal_id": "sp-orch-pg18",
                    "display_name": "Robot Orchestration PG18",
                    "account_kind": "SERVICE_PRINCIPAL",
                    "roles": ["TEAM_LEAD"],
                    "team_ids": [ws_id],
                },
            )
            assert r_sp.status_code in (200, 201), r_sp.text
            sp_id = r_sp.json()["id"]

            r_contract = await client1.post(
                f"/api/v1/workspaces/{ws_id}/workflows/wf-01-qualification-prd/autonomy-contract",
                headers=auth_headers,
                json={
                    "workflow_version": "1.0.0",
                    "criticality": "STANDARD",
                    "service_principal_id": sp_id,
                },
            )
            assert r_contract.status_code == 201, r_contract.text

            r_auto_run = await client1.post(
                f"/api/v1/workspaces/{ws_id}/workflows/wf-01-qualification-prd/runs/autonomous",
                headers=auth_headers,
                json={
                    "criticality": "STANDARD",
                    "actions": [],
                    "estimated_cost_usd": 0.05,
                    "force_post_hoc_sample": True,
                },
            )
            assert r_auto_run.status_code == 201, r_auto_run.text
            auto_run_id = r_auto_run.json()["run_id"]

            r_stop = await client1.post(
                f"/api/v1/runs/{auto_run_id}/emergency-stop",
                headers=auth_headers,
                json={"reason": "Arrêt d'urgence test intégration", "suspend_trigger": False},
            )
            assert r_stop.status_code == 200, r_stop.text
            assert r_stop.json()["status"] == "KILL_SWITCH_STOPPED"

            r_rollback = await client1.post(
                f"/api/v1/runs/{auto_run_id}/invalidate-and-restore",
                headers=auth_headers,
                json={"comment": "Invalidation post-hoc après arrêt d'urgence"},
            )
            assert r_rollback.status_code == 200, r_rollback.text
            assert r_rollback.json()["status"] == "KILL_SWITCH_STOPPED"

        # Phase 2: Direct SQL SELECT verification against PostgreSQL 18
        async with engine.connect() as conn:
            wf_row = (
                (
                    await conn.execute(
                        sa.text(
                            "SELECT id::text, status FROM workflow_runs "
                            "WHERE id = CAST(:id AS uuid)"
                        ),
                        {"id": run_id},
                    )
                )
                .mappings()
                .one()
            )
            assert wf_row["id"] == run_id

            auto_row = (
                (
                    await conn.execute(
                        sa.text(
                            "SELECT id::text, status FROM workflow_runs "
                            "WHERE id = CAST(:id AS uuid)"
                        ),
                        {"id": auto_run_id},
                    )
                )
                .mappings()
                .one()
            )
            assert auto_row["status"] == "KILL_SWITCH_STOPPED"

            lock_row = (
                (
                    await conn.execute(
                        sa.text(
                            "SELECT run_id::text, manifest_sha256 "
                            "FROM run_lock_manifests WHERE run_id = CAST(:id AS uuid)"
                        ),
                        {"id": run_id},
                    )
                )
                .mappings()
                .one()
            )
            assert lock_row["manifest_sha256"] == run_lock_sha

            anchor_row = (
                (
                    await conn.execute(
                        sa.text(
                            "SELECT section_key, content_text, "
                            "TRIM(content_sha256) AS sha, char_length "
                            "FROM human_anchor_signatures "
                            "WHERE run_id = CAST(:id AS uuid) "
                            "AND section_key = 'human_architecture_intent'"
                        ),
                        {"id": run_id},
                    )
                )
                .mappings()
                .one()
            )
            assert anchor_row["section_key"] == "human_architecture_intent"
            assert anchor_row["content_text"] == anchor_text
            assert anchor_row["sha"] == anchor_sha
            assert int(anchor_row["char_length"]) >= 30

            chal_row = (
                (
                    await conn.execute(
                        sa.text(
                            "SELECT id::text, target_upstream_step_key, status "
                            "FROM upstream_challenges WHERE id = CAST(:id AS uuid)"
                        ),
                        {"id": challenge_id},
                    )
                )
                .mappings()
                .one()
            )
            assert chal_row["target_upstream_step_key"] == "frame-architecture-intent"
            assert chal_row["status"] == "REPLAYED"

            snap_rows = (
                (
                    await conn.execute(
                        sa.text(
                            "SELECT id::text, branch_status FROM blackboard_snapshots "
                            "WHERE run_id = CAST(:id AS uuid) ORDER BY created_at ASC, id ASC"
                        ),
                        {"id": run_id},
                    )
                )
                .mappings()
                .all()
            )
            # Append-only trigger respected: original snapshot preserved + new snapshot inserted
            assert len(snap_rows) >= 2
            assert str(snap_rows[0]["id"]) == pg_initial_snap_id
            assert any(
                r["branch_status"] == "ACTIVE" and str(r["id"]) != pg_initial_snap_id
                for r in snap_rows
            )

            gate_rows = (
                (
                    await conn.execute(
                        sa.text(
                            "SELECT id::text, gate_type, status, fast_approval_warning "
                            "FROM gate_evaluations WHERE run_id = CAST(:id AS uuid)"
                        ),
                        {"id": run_id},
                    )
                )
                .mappings()
                .all()
            )
            assert any(
                r["gate_type"] == "DETERMINISTIC" and r["status"] == "PASS" for r in gate_rows
            )
            assert any(
                r["gate_type"] == "DETERMINISTIC" and r["status"] == "FAIL" for r in gate_rows
            )
            human_row = next(r for r in gate_rows if r["gate_type"] == "HUMAN")
            assert human_row["status"] == "PASS"
            assert human_row["fast_approval_warning"] is True

            chunk_rows = (
                (
                    await conn.execute(
                        sa.text(
                            "SELECT chunk_key, status FROM chunk_approvals "
                            "WHERE gate_evaluation_id = CAST(:id AS uuid)"
                        ),
                        {"id": human_eval_id},
                    )
                )
                .mappings()
                .all()
            )
            chunk_statuses = {str(r["chunk_key"]): str(r["status"]) for r in chunk_rows}
            assert chunk_statuses == {"sec-architecture": "APPROVED", "sec-security": "CO_EDITED"}

        # Phase 3: Cold restart with a brand new create_app() instance & empty RAM
        app2 = create_app()
        async with (
            app2.router.lifespan_context(app2),
            AsyncClient(transport=ASGITransport(app=app2), base_url="http://test") as client2,
        ):
            r_login = await client2.post(
                "/api/v1/auth/login/local",
                json={
                    "email": "admin.orch@orcia.ia",
                    "password": "OrciaAdmin!2026",  # pragma: allowlist secret
                },
            )
            assert r_login.status_code == 200, r_login.text
            cold_headers = {"Authorization": f"Bearer {r_login.json()['access_token']}"}

            r_bb = await client2.get(
                f"/api/v1/orchestration/runs/{run_id}/blackboard",
                headers=cold_headers,
            )
            assert r_bb.status_code == 200, r_bb.text

            r_orch_state = await client2.get("/api/v1/orchestration/state", headers=cold_headers)
            assert r_orch_state.status_code == 200, r_orch_state.text
            cold_run_ids = {r["id"] for r in r_orch_state.json()["runs"]}
            assert run_id in cold_run_ids
            bb_data = r_bb.json()
            assert len(bb_data["active_snapshots"]) >= 1
            step_frame = next(
                s
                for s in bb_data["step_executions"]
                if s["step_key"] == "frame-architecture-intent"
            )
            anchors = (step_frame.get("draft_artifact") or {}).get("human_anchors") or {}
            assert anchors["human_architecture_intent"]["content_sha256"] == anchor_sha

            r_cold_inspect = await client2.post(
                f"/api/v1/gates/human/{human_eval_id}/inspect-hypotheses",
                headers=cold_headers,
            )
            assert r_cold_inspect.status_code == 200, r_cold_inspect.text

            r_det_list = await client2.get(
                "/api/v1/gates/evaluations",
                params={"run_id": run_id},
                headers=cold_headers,
            )
            assert r_det_list.status_code == 200, r_det_list.text
            assert len(r_det_list.json()["evaluations"]) >= 2

            r_human_list = await client2.get(
                "/api/v1/gates/human/evaluations",
                params={"workspace_id": ws_id},
                headers=cold_headers,
            )
            assert r_human_list.status_code == 200, r_human_list.text
            rehydrated_eval = next(
                e for e in r_human_list.json()["evaluations"] if e["id"] == human_eval_id
            )
            assert rehydrated_eval["status"] == "PASS"
            assert rehydrated_eval["fast_approval_warning"] is True
            assert len(rehydrated_eval["chunks"]) == 2

            r_auto_list = await client2.get(
                f"/api/v1/workspaces/{ws_id}/autonomous-runs",
                headers=cold_headers,
            )
            assert r_auto_list.status_code == 200, r_auto_list.text
            rehydrated_auto = next(
                r for r in r_auto_list.json()["runs"] if r["run_id"] == auto_run_id
            )
            assert rehydrated_auto["run_status"] == "KILL_SWITCH_STOPPED"
    finally:
        await engine.dispose()
