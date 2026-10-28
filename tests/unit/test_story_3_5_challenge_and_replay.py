"""Story 3.5: Inter-Step Upstream Challenge (`What-If`) & Targeted Step Replay tests.

Covers:
- Alembic migration `0016_story_3_5` (`upstream_challenges`) against a real PostgreSQL 18 container
  (`testcontainers-python`).
- Upstream Challenge `What-If Impact Preview` (`ImpactSimulatorService`, DAG traversal,
  `ProfileSemanticTranslator` for `PM_PO` / `Hélène`, Outbox `HumanArbitrationRequested`, `v1.1`
  upstream revision, `FR-7`, `AD-7`, `AD-19`, `UX-DR7`).
- Targeted Replay from Step $N$ and Intra-Sub-Workflow Step $k$ (`FR-16`, `FR-30`, `AD-2`, `AD-18`)
  with `0` upstream re-execution, `0` upstream tokens consumed, `run-lock.json` (`SHA-256`)
  preservation, and `SUPERSEDED`/`ACTIVE` branching.
- Property-based `hypothesis` verification that no existing snapshot in `AppendOnlyBlackboardStore`
  is ever mutated or deleted across arbitrary Replay branches.
"""

from __future__ import annotations

import copy
import os
import shutil
import time
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from hypothesis import given, settings
from hypothesis import strategies as st
from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import wait_for_logs

from orcia_api.main import create_app
from orcia_core.blackboard.models import StepExecutionEntity
from orcia_core.blackboard.store import AppendOnlyBlackboardStore

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_story_3_5_migration_0016_real_postgres_container(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify migration 0016 creates `upstream_challenges` on PostgreSQL 18."""
    monkeypatch.setenv("TESTCONTAINERS_RYUK_DISABLED", "true")
    suffix = f"tc_3_5_{os.getpid()}_{int(time.time() * 1000) % 100000}"
    sock_dir = REPO_ROOT / ".pytest_cache" / suffix
    sock_dir.mkdir(parents=True, exist_ok=True)
    sock_dir.chmod(0o777)

    pg_container = (
        DockerContainer("pgvector/pgvector:pg18")
        .with_env("POSTGRES_USER", "orcia")
        .with_env("POSTGRES_PASSWORD", "orcia_dev_secret")
        .with_env("POSTGRES_DB", "orcia")
        .with_volume_mapping(str(sock_dir), "/var/run/postgresql", "rw")
    )
    try:
        with pg_container as pg:
            wait_for_logs(pg, "database system is ready to accept connections", timeout=30)
            sock_file = sock_dir / ".s.PGSQL.5432"
            for _ in range(40):
                if sock_file.exists():
                    break
                time.sleep(0.2)

            creds = "orcia:orcia_dev_secret"  # pragma: allowlist secret
            sync_url = f"postgresql+psycopg://{creds}@/orcia?host={sock_dir}"
            monkeypatch.setenv("DATABASE_URL", sync_url)
            alembic_cfg = Config(str(REPO_ROOT / "infra" / "migrations" / "alembic.ini"))
            alembic_cfg.set_main_option("script_location", str(REPO_ROOT / "infra" / "migrations"))
            alembic_cfg.set_main_option("sqlalchemy.url", sync_url)

            engine = sa.create_engine(sync_url)
            for _ in range(30):
                try:
                    with engine.connect() as c:
                        c.execute(sa.text("SELECT 1"))
                    break
                except Exception:
                    time.sleep(0.2)

            command.upgrade(alembic_cfg, "0016_story_3_5")

            with engine.begin() as conn:
                tables = set(
                    conn.execute(
                        sa.text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
                    ).scalars()
                )
                assert "upstream_challenges" in tables

            command.downgrade(alembic_cfg, "0015_story_3_4")
            command.upgrade(alembic_cfg, "0016_story_3_5")
            engine.dispose()
    finally:
        shutil.rmtree(sock_dir, ignore_errors=True)


def test_story_3_5_upstream_challenge_what_if_and_outbox_notification() -> None:
    """Verify Upstream Challenge What-If preview, PM translation, v1.1 revision & Outbox event."""
    app = create_app()
    client = TestClient(app)

    init_resp = client.post(
        "/api/v1/orchestration/runs/instantiate?persona_key=marc",
        json={
            "workflow_uri": "orcia://workflows/claims-engineering-delivery",
            "workspace_id": "0192c4e0-0000-7000-8000-000000000201",
        },
    )
    assert init_resp.status_code == 200
    run_id = init_resp.json()["run"]["id"]

    # Execute Step 0 and Step 1
    for sk in ("frame-architecture-intent", "delegate-remediation-subworkflow"):
        resp = client.post(
            "/api/v1/orchestration/runs/steps/execute?persona_key=marc",
            json={"run_id": run_id, "step_key": sk},
        )
        assert resp.status_code == 200

    # 1. Preview Upstream Challenge from Step 1 ('delegate-remediation-subworkflow') against Step 0
    preview_resp = client.post(
        f"/api/v1/orchestration/runs/{run_id}/steps/delegate-remediation-subworkflow/challenge/preview?persona_key=marc",
        json={
            "target_upstream_step_key": "frame-architecture-intent",
            "challenged_section_key": "fx_rate_guarantee_rule",
            "challenge_reason": (
                "La garantie FX 48h du PRD contredit le contrat API partenaire v3 (max 15 min)."
            ),
            "target_profile_archetype": "PM_BUSINESS",
        },
    )
    assert preview_resp.status_code == 200
    prev = preview_resp.json()["preview"]
    assert prev["invalidated_downstream_step_keys"] == [
        "frame-architecture-intent",
        "delegate-remediation-subworkflow",
        "post-deploy-verification",
    ]
    assert (
        "frame-architecture-intent:fx_rate_guarantee_rule" in prev["invalidated_artifact_sections"]
    )
    assert len(prev["invalidated_ontology_axiom_keys"]) >= 1
    assert "PM_BUSINESS" in prev["translated_summary"]

    # 2. Submit Upstream Challenge with v1.1 revision -> enqueues Outbox notification
    submit_resp = client.post(
        f"/api/v1/orchestration/runs/{run_id}/steps/delegate-remediation-subworkflow/challenge?persona_key=marc",
        json={
            "target_upstream_step_key": "frame-architecture-intent",
            "challenged_section_key": "fx_rate_guarantee_rule",
            "challenge_reason": (
                "La garantie FX 48h du PRD contredit le contrat API partenaire v3 (max 15 min)."
            ),
            "target_profile_archetype": "PM_BUSINESS",
            "proposed_upstream_revision": "Garantie de taux FX Spot 15 minutes (v1.1 validée)",
        },
    )
    assert submit_resp.status_code == 200
    chal = submit_resp.json()["challenge"]
    assert chal["status"] == "RESOLVED_REVISED"
    assert chal["revised_artifact_version"] == "v1.1"
    assert chal["outbox_event_id"]


def test_story_3_5_targeted_replay_step_n_and_intra_sub_workflow() -> None:
    """Verify Replay from Step N and Intra-Sub-Workflow Step k reuse 1..N-1 snapshots (0 tokens)."""
    app = create_app()
    client = TestClient(app)

    init_resp = client.post(
        "/api/v1/orchestration/runs/instantiate?persona_key=marc",
        json={
            "workflow_uri": "orcia://workflows/claims-engineering-delivery",
            "workspace_id": "0192c4e0-0000-7000-8000-000000000201",
        },
    )
    run_id = init_resp.json()["run"]["id"]
    expected_lock_sha = init_resp.json()["run"]["run_lock"]["manifest_sha256"]

    # Execute Step 0, Step 1 (SUB_WORKFLOW), and Step 2 (POST_ACTION_VERIFICATION)
    s0 = client.post(
        "/api/v1/orchestration/runs/steps/execute?persona_key=marc",
        json={"run_id": run_id, "step_key": "frame-architecture-intent"},
    )
    assert s0.status_code == 200
    snap_step0_id = s0.json()["committed_snapshot"]["id"]

    s1 = client.post(
        "/api/v1/orchestration/runs/steps/execute?persona_key=marc",
        json={"run_id": run_id, "step_key": "delegate-remediation-subworkflow"},
    )
    assert s1.status_code == 200
    snap_step1_old_id = s1.json()["committed_snapshot"]["id"]

    s2 = client.post(
        "/api/v1/orchestration/runs/steps/execute?persona_key=marc",
        json={"run_id": run_id, "step_key": "post-deploy-verification"},
    )
    assert s2.status_code == 200
    snap_step2_old_id = s2.json()["committed_snapshot"]["id"]

    # Trigger Intra-Sub-Workflow Replay at Step 1 ('delegate-remediation-subworkflow')
    replay_resp = client.post(
        f"/api/v1/runs/{run_id}/steps/delegate-remediation-subworkflow/replay?persona_key=marc",
        json={
            "sub_workflow_step_key": "implement-code-fix",
            "revised_section_payload": {"fx_rate_window_minutes": 15},
        },
    )
    assert replay_resp.status_code == 200
    rep = replay_resp.json()["replay"]
    assert rep["upstream_steps_reexecuted_count"] == 0
    assert rep["upstream_tokens_consumed"] == 0
    assert rep["run_lock_sha256"] == expected_lock_sha
    # Parent Step 0 snapshot AND child Step 0 ('declare-remediation-intent') snapshot are reused
    assert snap_step0_id in rep["reused_upstream_snapshot_ids"]
    assert len(rep["reused_upstream_snapshot_ids"]) == 2
    assert snap_step1_old_id in rep["superseded_snapshot_ids"]
    assert snap_step2_old_id in rep["superseded_snapshot_ids"]
    assert len(rep["new_active_snapshot_ids"]) >= 2

    # Verify old snapshots are marked SUPERSEDED and never mutated in AppendOnlyBlackboardStore
    store = app.state.orchestration_service.engine.blackboard
    assert store.get_effective_branch_status(snap_step0_id) == "ACTIVE"
    assert store.get_effective_branch_status(snap_step1_old_id) == "SUPERSEDED"
    assert store.get_effective_branch_status(snap_step2_old_id) == "SUPERSEDED"


@settings(max_examples=25)
@given(
    num_steps=st.integers(min_value=2, max_value=5),
    replay_index=st.integers(min_value=0, max_value=4),
)
def test_story_3_5_hypothesis_blackboard_replay_never_mutates_existing_snapshots(
    num_steps: int,
    replay_index: int,
) -> None:
    """Property-based test proving existing snapshots are never mutated or deleted on Replay."""
    target_idx = replay_index % num_steps
    store = AppendOnlyBlackboardStore()
    run_id = "run-hyp-001"
    step_keys = [f"step-{i}" for i in range(num_steps)]

    for i, sk in enumerate(step_keys):
        store.register_step_execution(
            StepExecutionEntity(
                id=f"exec-{i}",
                step_execution_key=f"exec-key-{i}",
                run_id=run_id,
                step_key=sk,
                step_index=i,
                step_type="AGENT",
                execution_mode="INTERACTIVE_COACHING",
                status="PENDING",
            )
        )
        store.save_step_draft(
            run_id,
            sk,
            status="EXECUTING_AGENT",
            draft_artifact={"step": sk, "revision": "v1.0"},
        )
        parent_id = store.get_active_snapshots(run_id)[-1].id if i > 0 else None
        store.commit_step_snapshot(run_id, sk, parent_snapshot_id=parent_id)

    before_all = copy.deepcopy(store.list_all_snapshots(run_id))
    active_before = store.get_active_snapshots(run_id)
    to_supersede = tuple(sn.id for idx, sn in enumerate(active_before) if idx >= target_idx)
    store.supersede_snapshots(to_supersede)

    for i in range(target_idx, num_steps):
        sk = step_keys[i]
        store.save_step_draft(
            run_id,
            sk,
            status="EXECUTING_AGENT",
            draft_artifact={"step": sk, "revision": "v1.1"},
        )
        active_now = store.get_active_snapshots(run_id)
        parent_id = active_now[-1].id if active_now else None
        store.commit_step_snapshot(
            run_id,
            sk,
            parent_snapshot_id=parent_id,
            superseded_snapshot_ids=to_supersede if i == target_idx else (),
        )

    after_all = store.list_all_snapshots(run_id)
    assert len(after_all) == len(before_all) + (num_steps - target_idx)
    # Every previously committed snapshot object is 100% unchanged
    for idx, orig in enumerate(before_all):
        assert after_all[idx] == orig
        expected_status = "SUPERSEDED" if idx >= target_idx else "ACTIVE"
        assert store.get_effective_branch_status(orig.id) == expected_status


def test_story_3_5_challenge_and_replay_validation_edges() -> None:
    """Verify validation errors (422) on invalid upstream challenges and non-SUB_WORKFLOW replay."""
    app = create_app()
    client = TestClient(app)

    init_resp = client.post(
        "/api/v1/orchestration/runs/instantiate?persona_key=marc",
        json={
            "workflow_uri": "orcia://workflows/claims-engineering-delivery",
            "workspace_id": "0192c4e0-0000-7000-8000-000000000201",
        },
    )
    run_id = init_resp.json()["run"]["id"]

    # Challenging a downstream step from an upstream step is rejected with 422
    bad_dir = client.post(
        f"/api/v1/orchestration/runs/{run_id}/steps/frame-architecture-intent/challenge/preview?persona_key=marc",
        json={
            "target_upstream_step_key": "post-deploy-verification",
            "challenged_section_key": "logs",
            "challenge_reason": "Tentative invalide de challenge vers l'aval.",
        },
    )
    assert bad_dir.status_code == 422

    # Sub-workflow replay on a non-SUB_WORKFLOW step is rejected with 422
    bad_sub = client.post(
        f"/api/v1/orchestration/runs/{run_id}/steps/frame-architecture-intent/replay?persona_key=marc",
        json={"sub_workflow_step_key": "implement-code-fix"},
    )
    assert bad_sub.status_code == 422
