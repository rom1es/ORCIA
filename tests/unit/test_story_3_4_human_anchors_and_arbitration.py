"""Story 3.4: Mandatory Human-Led Anchors, Systematic Arbitration & `tie_break_policy` tests.

Covers:
- Alembic migration `0015_story_3_4` (`human_anchor_signatures` & `human_arbitration_requests`)
  against a real PostgreSQL 18 container (`testcontainers-python`).
- Mandatory Human-Led Anchor (`>= 30` chars, `author_type="AGENT"` rejection with
  `HTTP 422 ERR_HUMAN_ANCHOR_REQUIRED`, Socratic refusal on `"Remplis-le pour moi"`, `FR-4`).
- `request_human_arbitration(options_matrix)` across `PAUSE_AND_ESCALATE` (+ Outbox event
  `HumanArbitrationRequested`), `ONTOLOGY_AXIOM_FIRST`, and `DEFER_AND_CONTINUE_WITH_ASSUMPTION`
  (`FR-5`, `FR-29`, `AD-3`, `AD-18`, `UX-DR6`).
- Immediate step resumption upon `resolve_human_arbitration` (`DBOS.send` / `resume_human_task`).
"""

from __future__ import annotations

import os
import shutil
import time
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient
from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import wait_for_logs

from orcia_api.main import create_app

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_story_3_4_migration_0015_real_postgres_container(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify migration 0015 creates `human_anchor_signatures` and `human_arbitration_requests`."""
    monkeypatch.setenv("TESTCONTAINERS_RYUK_DISABLED", "true")
    suffix = f"tc_3_4_{os.getpid()}_{int(time.time() * 1000) % 100000}"
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

            command.upgrade(alembic_cfg, "0015_story_3_4")

            with engine.begin() as conn:
                tables = set(
                    conn.execute(
                        sa.text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
                    ).scalars()
                )
                assert "human_anchor_signatures" in tables
                assert "human_arbitration_requests" in tables

            command.downgrade(alembic_cfg, "0014_story_3_2e")
            command.upgrade(alembic_cfg, "0015_story_3_4")
            engine.dispose()
    finally:
        shutil.rmtree(sock_dir, ignore_errors=True)


def test_story_3_4_mandatory_human_anchor_and_agent_rejection() -> None:
    """Verify `human_authored_required: true` blocks execution until >= 30 chars human signature."""
    client = TestClient(create_app())

    init_resp = client.post(
        "/api/v1/orchestration/runs/instantiate?persona_key=marc",
        json={
            "workflow_uri": "orcia://workflows/claims-engineering-delivery",
            "workspace_id": "0192c4e0-0000-7000-8000-000000000201",
        },
    )
    assert init_resp.status_code == 200
    run_id = init_resp.json()["run"]["id"]

    # 1. Executing human_authored_required: true step with require_human_anchor=True fails with 422
    exec_locked = client.post(
        "/api/v1/orchestration/runs/steps/execute?persona_key=marc",
        json={
            "run_id": run_id,
            "step_key": "frame-architecture-intent",
            "require_human_anchor": True,
        },
    )
    assert exec_locked.status_code == 422
    assert exec_locked.json()["error_code"] == "ERR_HUMAN_ANCHOR_REQUIRED"

    # 2. Agent identity attempting to sign or write the anchor is rejected with 422
    agent_sign = client.post(
        "/api/v1/orchestration/runs/anchors/sign?persona_key=marc",
        json={
            "run_id": run_id,
            "step_key": "frame-architecture-intent",
            "section_key": "human_architecture_intent",
            "content_text": (
                "Texte généré automatiquement par un agent de plus de trente caractères."
            ),
            "signature_text": "AgentBot",
            "author_type": "AGENT",
        },
    )
    assert agent_sign.status_code == 422
    assert agent_sign.json()["error_code"] == "ERR_HUMAN_ANCHOR_REQUIRED"

    # 3. Short text (< 30 chars) is rejected with 422 ERR_HUMAN_ANCHOR_REQUIRED
    short_sign = client.post(
        "/api/v1/orchestration/runs/anchors/sign?persona_key=marc",
        json={
            "run_id": run_id,
            "step_key": "frame-architecture-intent",
            "section_key": "human_architecture_intent",
            "content_text": "Trop court (< 30 car.)",
            "signature_text": "Marc",
            "author_type": "HUMAN",
        },
    )
    assert short_sign.status_code == 422
    assert short_sign.json()["error_code"] == "ERR_HUMAN_ANCHOR_REQUIRED"

    # 4. Observer role is rejected with 403 ERR_OBSERVER_MODE_READ_ONLY
    obs_sign = client.post(
        "/api/v1/orchestration/runs/anchors/sign?persona_key=claire",
        json={
            "run_id": run_id,
            "step_key": "frame-architecture-intent",
            "section_key": "human_architecture_intent",
            "content_text": (
                "Justification d'architecture rédigée par un humain dépassant trente caractères."
            ),
            "signature_text": "Claire",
        },
    )
    assert obs_sign.status_code == 403
    assert obs_sign.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"

    # 5. Valid human anchor (>= 30 chars) signs and unlocks step execution
    valid_sign = client.post(
        "/api/v1/orchestration/runs/anchors/sign?persona_key=marc",
        json={
            "run_id": run_id,
            "step_key": "frame-architecture-intent",
            "section_key": "human_architecture_intent",
            "content_text": (
                "Invariants d'architecture : isolation hexagonale stricte et contrat OpenAPI 3.1 "
                "sans dérive (0-diff) avec plafond FinOps à 15 USD."
            ),
            "signature_text": "Marc Tech Lead",
            "author_type": "HUMAN",
        },
    )
    assert valid_sign.status_code == 200
    sig_body = valid_sign.json()["signature"]
    assert sig_body["char_length"] >= 30
    assert len(sig_body["content_sha256"]) == 64

    exec_unlocked = client.post(
        "/api/v1/orchestration/runs/steps/execute?persona_key=marc",
        json={
            "run_id": run_id,
            "step_key": "frame-architecture-intent",
            "require_human_anchor": True,
        },
    )
    assert exec_unlocked.status_code == 200
    assert exec_unlocked.json()["step_execution"]["status"] == "COMMITTED"

    # 6. Asking Assistant "Remplis-le pour moi" triggers Layer 1 Socratic refusal (FR-4)
    socratic_resp = client.post(
        "/api/v1/assistant/chat?persona_key=marc",
        json={
            "workspace_id": "0192c4e0-0000-7000-8000-000000000201",
            "user_prompt": "Remplis-le pour moi sur la section human_authored_required",
            "human_profile_archetype": "ARCHITECT",
        },
    )
    assert socratic_resp.status_code == 200
    assert socratic_resp.json()["intent"] == "HUMAN_ANCHOR_WRITE_REFUSAL"
    assert "human_authored_required: true" in socratic_resp.json()["response_text"]


def test_story_3_4_arbitration_pause_and_escalate_outbox_and_resolve() -> None:
    """Verify `PAUSE_AND_ESCALATE` pauses step, emits Outbox event, and resumes on human choice."""
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

    arb_resp = client.post(
        f"/api/v1/orchestration/runs/{run_id}/steps/frame-architecture-intent/arbitration?persona_key=marc",
        json={
            "question_title": "Garantie de taux FX : Taux Spot 15 min vs Taux Bloqué 48h",
            "context_summary": "Deux options équivalentes identifiées par l'Agent Exécuteur.",
            "tie_break_policy": "PAUSE_AND_ESCALATE",
            "options_matrix": [
                {
                    "option_key": "OPT_A_SPOT_15M",
                    "title": "Option A — Taux Spot 15 min",
                    "pros": ["Compatible API partenaire v3"],
                    "cons": ["Fenêtre client 15 min"],
                    "si_impact": "1 microservice impacté",
                    "finops_impact": "0.02 USD / run",
                    "recommended": True,
                },
                {
                    "option_key": "OPT_B_LOCK_48H",
                    "title": "Option B — Taux Bloqué 48h",
                    "pros": ["Confort client 48h"],
                    "cons": ["Incompatible API v3"],
                    "si_impact": "3 systèmes centraux impactés",
                    "finops_impact": "0.18 USD / run",
                    "recommended": False,
                },
            ],
        },
    )
    assert arb_resp.status_code == 200
    arb_data = arb_resp.json()
    assert arb_data["arbitration"]["status"] == "PENDING"
    assert arb_data["arbitration"]["outbox_event_id"] is not None
    assert arb_data["step_execution"]["status"] == "WAITING_FOR_HUMAN_ARBITRATION"
    arb_id = arb_data["arbitration"]["id"]

    # Resolve arbitration as human -> records in Blackboard and resumes step to COMMITTED
    resolve_resp = client.post(
        f"/api/v1/orchestration/runs/{run_id}/steps/frame-architecture-intent/arbitration/resolve?persona_key=marc",
        json={
            "arbitration_id": arb_id,
            "selected_option_key": "OPT_A_SPOT_15M",
            "human_justification": "Alignement immédiat avec le contrat OpenAPI v3 du partenaire.",
        },
    )
    assert resolve_resp.status_code == 200
    res_body = resolve_resp.json()
    assert res_body["arbitration"]["status"] == "RESOLVED_BY_HUMAN"
    assert res_body["arbitration"]["selected_option_key"] == "OPT_A_SPOT_15M"
    assert res_body["step_execution"]["status"] == "COMMITTED"
    assert res_body["committed_snapshot"] is not None


def test_story_3_4_tie_break_policies_ontology_axiom_and_defer_assumption() -> None:
    """Verify `ONTOLOGY_AXIOM_FIRST` and `DEFER_AND_CONTINUE_WITH_ASSUMPTION` policies."""
    client = TestClient(create_app())

    # 1. ONTOLOGY_AXIOM_FIRST with immutable ontology concept ('concept-l1-strategic-asset')
    init_resp = client.post(
        "/api/v1/orchestration/runs/instantiate?persona_key=marc",
        json={
            "workflow_uri": "orcia://workflows/claims-engineering-delivery",
            "workspace_id": "0192c4e0-0000-7000-8000-000000000201",
        },
    )
    run_id = init_resp.json()["run"]["id"]

    axiom_resp = client.post(
        f"/api/v1/orchestration/runs/{run_id}/steps/frame-architecture-intent/arbitration?persona_key=marc",
        json={
            "question_title": "Schéma d'audit pour Actif Stratégique",
            "tie_break_policy": "ONTOLOGY_AXIOM_FIRST",
            "options_matrix": [
                {
                    "option_key": "OPT_COMPLIANT_ASSET_SCHEMA",
                    "title": "Option conforme à l'axiome L1 Actif Stratégique",
                    "pros": ["Respecte IMMUTABLE_SCHEMA"],
                    "cons": ["Plus strict"],
                    "si_impact": "0 dette",
                    "finops_impact": "0.01 USD",
                    "recommended": True,
                    "ontology_concept_key": "concept-l1-strategic-asset",
                },
                {
                    "option_key": "OPT_UNVALIDATED_SCHEMA",
                    "title": "Option sans propriétaires déclarés",
                    "pros": ["Rapide"],
                    "cons": ["Non conforme"],
                    "si_impact": "Dette",
                    "finops_impact": "0.01 USD",
                },
            ],
        },
    )
    assert axiom_resp.status_code == 200
    ax_body = axiom_resp.json()["arbitration"]
    assert ax_body["status"] == "RESOLVED_BY_AXIOM"
    assert ax_body["selected_option_key"] == "OPT_COMPLIANT_ASSET_SCHEMA"
    assert ax_body["resolved_by_axiom_key"] == "axiom-l1-strategic-asset-immutable-schema"

    # 2. DEFER_AND_CONTINUE_WITH_ASSUMPTION on non-critical sub-workflow logs [ASSUMPTION]
    fast_run_resp = client.post(
        "/api/v1/orchestration/runs/instantiate?persona_key=marc",
        json={
            "workflow_uri": "orcia://workflows/sub-verify-regression-suite",
            "workspace_id": "0192c4e0-0000-7000-8000-000000000201",
        },
    )
    fast_run_id = fast_run_resp.json()["run"]["id"]

    defer_resp = client.post(
        f"/api/v1/orchestration/runs/{fast_run_id}/steps/run-sandbox-tests/arbitration?persona_key=marc",
        json={
            "question_title": "Seuil de parallélisme de la suite de tests",
            "tie_break_policy": "DEFER_AND_CONTINUE_WITH_ASSUMPTION",
            "options_matrix": [
                {
                    "option_key": "OPT_4_WORKERS",
                    "title": "4 workers parallèles",
                    "pros": ["Stable"],
                    "cons": ["Standard"],
                    "si_impact": "Faible",
                    "finops_impact": "0.01 USD",
                    "recommended": True,
                },
                {
                    "option_key": "OPT_8_WORKERS",
                    "title": "8 workers parallèles",
                    "pros": ["Plus rapide"],
                    "cons": ["RAM plus élevée"],
                    "si_impact": "Moyen",
                    "finops_impact": "0.03 USD",
                },
            ],
        },
    )
    assert defer_resp.status_code == 200
    defer_body = defer_resp.json()
    assert defer_body["arbitration"]["status"] == "DEFERRED_WITH_ASSUMPTION"
    assert defer_body["arbitration"]["selected_option_key"] == "OPT_4_WORKERS"
    memlog_markers = [m["marker_type"] for m in defer_body["step_execution"]["step_memlog"]]
    assert "ASSUMPTION" in memlog_markers
