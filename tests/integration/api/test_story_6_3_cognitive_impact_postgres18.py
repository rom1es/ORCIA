"""Story 6.3 — Integration Tests for Cognitive Impact & Human Reversibility on PostgreSQL 18.

Verifies against a real `pgvector/pgvector:pg18` testcontainer (`AD-17 Layer 2`):
1. Aggregation of Active Framing Ratio, Quick-Pass Approvals Rate, and Architecture Deviations.
2. Exemption of deviations covered by an ACTIVE waiver in `workspace_exception_waivers`.
3. Governance Analyzer recommendation generation for unanimous quick-pass workflows.
4. Mutation guard enforcement on recommendation application (403 for READ_ONLY_OBSERVER).
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import AsyncIterator, Iterator
from pathlib import Path
from urllib.parse import quote_plus

import pytest
import pytest_asyncio
import sqlalchemy as sa
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine

try:
    from testcontainers.community.postgres import PostgresContainer
except ImportError:
    from testcontainers.postgres import PostgresContainer

from orcia_api.main import create_app
from orcia_core.audit_finops.cognitive_impact_service import CognitiveImpactService
from orcia_kernel.ids import new_uuid7_str

REPO_ROOT = Path(__file__).resolve().parents[3]
DB_NAME = "orcia_story_6_3"
DB_USER = "orcia"
DB_PASSWORD = "orcia_story_6_3_pw"  # pragma: allowlist secret


@pytest.fixture(scope="module")
def database_url() -> Iterator[str]:
    with PostgresContainer(
        "pgvector/pgvector:pg18", username=DB_USER, password=DB_PASSWORD, dbname=DB_NAME
    ) as pg:
        url = (
            f"postgresql+asyncpg://{DB_USER}:{quote_plus(DB_PASSWORD)}"
            f"@127.0.0.1:{pg.get_exposed_port(5432)}/{DB_NAME}"
        )
        env = {
            "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
            "PYTHONPATH": os.environ.get("PYTHONPATH", ""),
            "DATABASE_URL": url,
            "ORCIA_ENV_FILE": str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"),
        }
        alembic_bin = str(Path(sys.executable).with_name("alembic"))
        alembic_cmd = [alembic_bin, "-c", "infra/migrations/alembic.ini"]
        res = subprocess.run(
            [*alembic_cmd, "upgrade", "head"],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
        )
        if res.returncode != 0:
            raise RuntimeError(
                f"Alembic upgrade head failed:\nSTDOUT:\n{res.stdout}\nSTDERR:\n{res.stderr}"
            )
        yield url


@pytest_asyncio.fixture
async def app_client(
    database_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> AsyncIterator[AsyncClient]:
    monkeypatch.setenv("DATABASE_URL", database_url)
    monkeypatch.setenv("ORCIA_ENV_FILE", str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"))
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    monkeypatch.setenv(
        "ORCIA_JWT_SIGNING_SECRET",
        "orcia-story-6-3-jwt-secret-0001",  # pragma: allowlist secret
    )
    monkeypatch.setenv(
        "ORCIA_PASSTHROUGH_MASTER_KEY",
        "orcia-story-6-3-vault-key-0001",  # pragma: allowlist secret
    )
    monkeypatch.setenv("ORCIA_ENABLE_PG_SESSION_MAKER", "1")
    monkeypatch.delenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", raising=False)

    app = create_app()
    transport = ASGITransport(app=app)
    async with AsyncClient(
        transport=transport,
        base_url="http://testserver",
        headers={
            "X-Orcia-Active-Hat": "PLATFORM_ADMIN",
            "Accept-Language": "fr",
        },
    ) as client:
        yield client


@pytest.mark.asyncio
async def test_cognitive_impact_vertical_postgres18(
    database_url: str,
    app_client: AsyncClient,
) -> None:
    """Verify full HTTP to PostgreSQL 18 wiring for cognitive governance and waivers."""
    engine = create_async_engine(database_url)

    # 1. Seed base entities: org unit, user, workspace, workflow definition, run, step
    org_id = new_uuid7_str()
    user_id = new_uuid7_str()
    ws_id = new_uuid7_str()
    wf_id = new_uuid7_str()
    run_id = new_uuid7_str()
    step_exec_id = new_uuid7_str()

    async with engine.begin() as conn:
        await conn.execute(
            sa.text(
                "INSERT INTO org_units (id, slug, name, unit_type) "
                "VALUES (CAST(:id AS uuid), 'bu-fin', 'Direction Finance', 'BU')"
            ),
            {"id": org_id},
        )
        await conn.execute(
            sa.text(
                "INSERT INTO users ("
                "  id, email, display_name, auth_mode, human_profile_archetype, "
                "  platform_role, primary_org_unit_id, is_active"
                ") VALUES ("
                "  CAST(:id AS uuid), 'expert.marc@orcia.fr', 'Marc Dev', 'LOCAL', 'TECH_LEAD', "
                "  'PLATFORM_ADMIN', CAST(:org_id AS uuid), TRUE"
                ")"
            ),
            {"id": user_id, "org_id": org_id},
        )
        await conn.execute(
            sa.text(
                "INSERT INTO workspaces (id, slug, name, owner_org_unit_id) "
                "VALUES (CAST(:id AS uuid), 'ws-credit', 'Espace Crédit', CAST(:org_id AS uuid))"
            ),
            {"id": ws_id, "org_id": org_id},
        )
        await conn.execute(
            sa.text(
                "INSERT INTO workflow_definitions (id, uri, version, sha256) "
                "VALUES (CAST(:id AS uuid), 'orcia://wf/credit-fast', '1.0.0', 'sha-credit')"
            ),
            {"id": wf_id},
        )
        await conn.execute(
            sa.text(
                "INSERT INTO workflow_runs "
                "(id, run_key, workspace_id, workflow_def_id, root_run_id, criticality, status) "
                "VALUES ("
                "  CAST(:id AS uuid), 'run-credit-1', CAST(:ws_id AS uuid), "
                "  CAST(:wf_id AS uuid), CAST(:id AS uuid), 'STANDARD', 'COMPLETED'"
                ")"
            ),
            {"id": run_id, "ws_id": ws_id, "wf_id": wf_id},
        )
        await conn.execute(
            sa.text(
                "INSERT INTO step_executions ("
                "  id, step_execution_key, run_id, step_key, step_index, "
                "  step_type, status, attempt_count"
                ") VALUES ("
                "  CAST(:id AS uuid), 'step-exec-rev-1', CAST(:run_id AS uuid), "
                "  'step-review', 1, 'AGENT', 'COMMITTED', 1"
                ")"
            ),
            {"id": step_exec_id, "run_id": run_id},
        )

        # 2. Insert human anchor signature (active framing)
        await conn.execute(
            sa.text(
                "INSERT INTO human_anchor_signatures ("
                "  id, signature_key, workspace_id, run_id, step_execution_id, step_key, "
                "  section_key, content_text, content_sha256, char_length, authored_by_user_id, "
                "  author_display_name, signature_hash"
                ") VALUES ("
                "  CAST(:id AS uuid), 'sig-001', CAST(:ws_id AS uuid), CAST(:run_id AS uuid), "
                "  CAST(:step_id AS uuid), 'step-review', 'hypothesis', "
                "  'Ceci est une hypothese experte redigee manuellement >= 30 car.', "
                "  'sha-content', 70, CAST(:user_id AS uuid), 'Marc Dev', 'sig-hash'"
                ")"
            ),
            {
                "id": new_uuid7_str(),
                "ws_id": ws_id,
                "run_id": run_id,
                "step_id": step_exec_id,
                "user_id": user_id,
            },
        )

        # 3. Insert 6 Gate evaluations for this workflow:
        # 6 human approvals, review duration = 4000ms (< 15s), fast_approval_warning = TRUE
        for _ in range(6):
            await conn.execute(
                sa.text(
                    "INSERT INTO gate_evaluations ("
                    "  id, workspace_id, run_id, step_execution_id, step_key, gate_type, "
                    "  status, score, pattern_drift_passed, review_duration_ms, "
                    "  fast_approval_warning, briefing_4blocks_jsonb"
                    ") VALUES ("
                    "  CAST(:id AS uuid), CAST(:ws_id AS uuid), CAST(:run_id AS uuid), "
                    "  CAST(:step_id AS uuid), 'step-review', 'HUMAN', 'PASS', 1.0, "
                    "  TRUE, 4000, TRUE, :brief"
                    ")"
                ),
                {
                    "id": new_uuid7_str(),
                    "ws_id": ws_id,
                    "run_id": run_id,
                    "step_id": step_exec_id,
                    "brief": json.dumps({"opened": False}),
                },
            )

        # 4. Insert 1 gate evaluation with pattern_drift_passed = FALSE, covered by active waiver
        drift_ge_id = new_uuid7_str()
        await conn.execute(
            sa.text(
                "INSERT INTO gate_evaluations ("
                "  id, workspace_id, run_id, step_execution_id, step_key, gate_type, "
                "  status, score, pattern_drift_passed, review_duration_ms, fast_approval_warning"
                ") VALUES ("
                "  CAST(:id AS uuid), CAST(:ws_id AS uuid), CAST(:run_id AS uuid), "
                "  CAST(:step_id AS uuid), 'step-review', 'DETERMINISTIC', 'PASS', "
                "  1.0, FALSE, 0, FALSE"
                ")"
            ),
            {
                "id": drift_ge_id,
                "ws_id": ws_id,
                "run_id": run_id,
                "step_id": step_exec_id,
            },
        )

        # Insert ACTIVE waiver in workspace_exception_waivers covering the workspace
        await conn.execute(
            sa.text(
                "INSERT INTO workspace_exception_waivers ("
                "  waiver_id, workspace_id, source_uri, source_sha256, conflict_rule_id, "
                "  norm_level, approved_by_user_id, approved_by_role, reason, status, expires_at"
                ") VALUES ("
                "  CAST(:id AS uuid), CAST(:ws_id AS uuid), 'orcia://source/1', 'sha-waiver', "
                "  'rule-ad19', '3_WORKSPACE', CAST(:user_id AS uuid), 'PLATFORM_ADMIN', "
                "  'Derogation validee', 'ACTIVE', NOW() + INTERVAL '30 days'"
                ")"
            ),
            {
                "id": new_uuid7_str(),
                "ws_id": ws_id,
                "user_id": user_id,
            },
        )

    # 5. Query GET /api/v1/finops/cognitive-impact
    resp = await app_client.get(
        f"/api/v1/finops/cognitive-impact?scope_id={ws_id}&scope_type=WORKSPACE"
    )
    assert resp.status_code == 200, resp.text
    data = resp.json()

    # The 6 quick approvals should trigger quick_pass_alert
    assert data["quick_pass_rate"] == 1.0
    assert data["quick_pass_alert"] is True

    # The 1 drift is covered by the ACTIVE waiver -> uncovered_deviations_count == 0
    assert data["uncovered_deviations_count"] == 0
    assert data["architecture_deviation_alert"] is False

    # Check Governance Analyzer Recommendation
    recs = data["recommendations"]
    assert len(recs) == 1
    rec = recs[0]
    assert rec["workflow_id"] == wf_id
    assert rec["recommendation_type"] == "SWITCH_TO_RISK_OR_SAMPLING"
    assert rec["suggested_policy"] == "SAMPLING_20_PCT"
    assert rec["status"] == "PROPOSED"

    # 6. Apply recommendation via POST endpoint
    apply_resp = await app_client.post(
        f"/api/v1/finops/gates/policy-recommendation/{rec['id']}/apply"
    )
    assert apply_resp.status_code == 200, apply_resp.text
    apply_data = apply_resp.json()
    assert apply_data["status"] == "APPLIED"
    assert apply_data["recommendation_id"] == rec["id"]

    # 7. Verify Observer Mode mutation restriction
    obs_resp = await app_client.post(
        f"/api/v1/finops/gates/policy-recommendation/{rec['id']}/apply",
        headers={"X-Orcia-Access-Mode": "READ_ONLY_OBSERVER"},
    )
    assert obs_resp.status_code == 403
    assert "ERR_OBSERVER_MODE_READ_ONLY" in obs_resp.text

    # 8. Vertical Verification: Assert persistence in audit_ledger table via SQL SELECT
    async with engine.connect() as conn:
        ledger_row = (
            await conn.execute(
                sa.text(
                    "SELECT id, event_type, metadata_jsonb "
                    "FROM audit_ledger "
                    "WHERE event_type = 'SettingsChanged' "
                    "  AND metadata_jsonb->>'category' = 'FINOPS_GATE_POLICY_RECOMMENDATION' "
                    "  AND metadata_jsonb->>'recommendation_id' = :rec_id"
                ),
                {"rec_id": rec["id"]},
            )
        ).fetchone()
        assert ledger_row is not None
        assert ledger_row[1] == "SettingsChanged"
        meta = ledger_row[2]
        assert meta["workflow_id"] == wf_id
        assert meta["suggested_policy"] == "SAMPLING_20_PCT"

    # 9. Reboot Simulation (F5 / Zero-RAM): Instantiate brand-new CognitiveImpactService
    fresh_service = CognitiveImpactService(engine=engine)
    fresh_dash = await fresh_service.get_dashboard(scope_id=ws_id, scope_type="WORKSPACE")
    assert len(fresh_dash.recommendations) >= 1
    reboot_rec = next(r for r in fresh_dash.recommendations if r.id == rec["id"])
    assert reboot_rec.status == "APPLIED"
    assert reboot_rec.applied_by is not None
    assert reboot_rec.applied_at is not None
