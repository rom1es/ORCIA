"""Vertical Composition Root integration test verifying zero RAM silos on PostgreSQL 18 + Redis."""

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
DB_NAME = "orcia_comp_root_zero_ram"
DB_USER = "orcia"
DB_PASSWORD = "orcia_comp_root_zero_ram_pw"  # pragma: allowlist secret


@pytest.fixture(scope="module")
def infra_urls() -> Iterator[tuple[str, str]]:
    """Start ephemeral PostgreSQL 18 + pgvector and Redis 7.4 containers migrated to head."""
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
async def test_real_composition_root_persists_all_critical_flows_without_ram_silos(
    infra_urls: tuple[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Boot `create_app()` via lifespan without overrides or `app.state` tampering."""
    pg_url, redis_url = infra_urls
    monkeypatch.setenv("DATABASE_URL", pg_url)
    monkeypatch.setenv("REDIS_URL", redis_url)
    monkeypatch.setenv("ORCIA_ENV_FILE", str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"))
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    monkeypatch.setenv("ORCIA_JWT_SIGNING_SECRET", "orcia-comp-root-jwt-secret-0001")
    monkeypatch.setenv("ORCIA_PASSTHROUGH_MASTER_KEY", "orcia-comp-root-vault-key-0001")
    monkeypatch.setenv("ORCIA_ENABLE_PG_SESSION_MAKER", "1")
    monkeypatch.delenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", raising=False)

    from orcia_api.main import create_app

    engine = create_async_engine(pg_url)
    try:
        app1 = create_app()
        assert app1.dependency_overrides == {}

        async with (
            app1.router.lifespan_context(app1),
            AsyncClient(transport=ASGITransport(app=app1), base_url="http://test") as client1,
        ):
            assert getattr(app1.state, "db_engine", None) is not None
            assert getattr(app1.state, "session_maker", None) is not None
            assert getattr(app1.state, "dbos_uow", None) is not None

            # 0. Bootstrap Day-0 admin with real JWT Bearer auth
            r_first = await client1.post(
                "/api/v1/bootstrap/welcome-setup/first-admin",
                json={
                    "email": "admin.comproot@orcia.ia",
                    "display_name": "Admin Composition Root",
                    "password": "OrciaAdmin!2026",  # pragma: allowlist secret
                    "orcia_env": "local",
                },
            )
            assert r_first.status_code == 200, r_first.text
            admin_token = r_first.json()["access_token"]
            auth_headers = {"Authorization": f"Bearer {admin_token}"}

            # 1. workspaces
            r_ws = await client1.post(
                "/api/v1/workspaces",
                headers=auth_headers,
                json={
                    "name": "Espace Composition Root",
                    "slug": "espace-composition-root",
                    "visibility_mode": "STANDARD",
                    "lifecycle_phase": "BUILD",
                },
            )
            assert r_ws.status_code == 201, r_ws.text
            ws_id = r_ws.json()["id"]
            UUID(ws_id)

            # 2. assistant_folders
            r_folder = await client1.post(
                "/api/v1/assistant/folders",
                headers=auth_headers,
                json={
                    "workspace_id": ws_id,
                    "title": "Dossier Sans Silo RAM",
                    "pinned_notes_markdown": "Note persistée en PG18",
                    "consolidated_summary": "Résumé PG18",
                },
            )
            assert r_folder.status_code == 200, r_folder.text
            folder_id = r_folder.json()["folder_id"]

            # 3 & 4. Instantiate & execute workflow step -> task_notifications + gate_evaluations
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

            r_anchor = await client1.post(
                "/api/v1/orchestration/runs/anchors/sign",
                headers=auth_headers,
                json={
                    "run_id": run_id,
                    "step_key": "frame-architecture-intent",
                    "section_key": "human_architecture_intent",
                    "content_text": "Validation PG18 sans silo mémoire.",
                    "signature_text": "Admin Composition Root",
                    "author_type": "HUMAN",
                },
            )
            assert r_anchor.status_code == 200, r_anchor.text

            r_exec = await client1.post(
                "/api/v1/orchestration/runs/steps/execute",
                headers=auth_headers,
                json={
                    "run_id": run_id,
                    "step_key": "frame-architecture-intent",
                    "commit_immediately": True,
                    "require_human_anchor": True,
                    "cost_usd": 0.12,
                },
            )
            assert r_exec.status_code == 200, r_exec.text
            step_exec_id = r_exec.json()["step_execution"]["id"]

            r_claim = await client1.post(
                f"/api/v1/runs/{run_id}/steps/{step_exec_id}/claim",
                headers=auth_headers,
                json={
                    "workspace_id": ws_id,
                    "step_key": "frame-architecture-intent",
                },
            )
            assert r_claim.status_code == 200, r_claim.text
            notification_id = r_claim.json()["notification"]["id"]

            r_gate = await client1.post(
                "/api/v1/gates/deterministic/evaluate",
                headers=auth_headers,
                json={
                    "workspace_id": ws_id,
                    "run_id": run_id,
                    "step_execution_id": step_exec_id,
                    "step_key": "frame-architecture-intent",
                    "artifact_payload": {"summary": "OK"},
                    "required_sections": ["summary"],
                },
            )
            assert r_gate.status_code == 200, r_gate.text
            gate_eval_id = r_gate.json()["evaluation"]["id"]

            # 5. declarative_pack_bundles
            r_packs = await client1.get("/api/v1/packs", headers=auth_headers)
            assert r_packs.status_code == 200, r_packs.text
            assert len(r_packs.json()["packs"]) >= 2

            # 6. wizard_sessions
            r_wiz = await client1.post(
                "/api/v1/wizards/sessions",
                headers=auth_headers,
                json={
                    "wizard_type": "sdlc_tech_lead",
                    "scope_id": ws_id,
                },
            )
            assert r_wiz.status_code == 200, r_wiz.text
            wizard_id = r_wiz.json()["id"]

            # 7. permission_broker_tickets
            r_broker = await client1.post(
                "/api/v1/permissions/broker/check-access",
                headers=auth_headers,
                json={
                    "target_uri": "git://gitlab.internal/platform/core-repo",
                    "execution_identity": "passthrough",
                    "step_key": "fetch_repo",
                    "step_number": 1,
                    "workspace_id": ws_id,
                    "simulated_upstream_status": 403,
                    "raise_on_denied": False,
                },
            )
            assert r_broker.status_code == 200, r_broker.text
            ticket_id = r_broker.json()["ticket"]["id"]

            # 8. catalog_items (contextual help)
            r_help = await client1.get(
                "/api/v1/help/resolve",
                headers=auth_headers,
                params={"route": "/finops", "lang": "fr", "pack": "core"},
            )
            assert r_help.status_code == 200, r_help.text
            help_resource_id = r_help.json()["active_article"]["resource_id"]

        # Direct PostgreSQL 18 SQL verification across all 8 critical tables
        async with engine.connect() as conn:
            ws_count = (
                await conn.execute(
                    sa.text("SELECT COUNT(*) FROM workspaces WHERE id = CAST(:id AS uuid)"),
                    {"id": ws_id},
                )
            ).scalar_one()
            folder_count = (
                await conn.execute(
                    sa.text(
                        "SELECT COUNT(*) FROM assistant_folders WHERE folder_id = CAST(:id AS uuid)"
                    ),
                    {"id": folder_id},
                )
            ).scalar_one()
            notif_count = (
                await conn.execute(
                    sa.text("SELECT COUNT(*) FROM task_notifications WHERE id = CAST(:id AS uuid)"),
                    {"id": notification_id},
                )
            ).scalar_one()
            gate_count = (
                await conn.execute(
                    sa.text("SELECT COUNT(*) FROM gate_evaluations WHERE id = CAST(:id AS uuid)"),
                    {"id": gate_eval_id},
                )
            ).scalar_one()
            pack_count = (
                await conn.execute(sa.text("SELECT COUNT(*) FROM declarative_pack_bundles"))
            ).scalar_one()
            wizard_count = (
                await conn.execute(
                    sa.text("SELECT COUNT(*) FROM wizard_sessions WHERE id = CAST(:id AS uuid)"),
                    {"id": wizard_id},
                )
            ).scalar_one()
            ticket_count = (
                await conn.execute(
                    sa.text(
                        "SELECT COUNT(*) FROM permission_broker_tickets "
                        "WHERE id = CAST(:id AS uuid)"
                    ),
                    {"id": ticket_id},
                )
            ).scalar_one()
            help_count = (
                await conn.execute(
                    sa.text(
                        "SELECT COUNT(*) FROM catalog_items "
                        "WHERE resource_id = :rid AND item_type = 'HELP_ARTICLE'"
                    ),
                    {"rid": help_resource_id},
                )
            ).scalar_one()

        assert ws_count == 1
        assert folder_count == 1
        assert notif_count == 1
        assert gate_count == 1
        assert pack_count >= 2
        assert wizard_count == 1
        assert ticket_count == 1
        assert help_count >= 1

        # Phase 2: Cold restart on a brand-new FastAPI app via lifespan (zero RAM carried over)
        app2 = create_app()
        assert app2.dependency_overrides == {}
        async with (
            app2.router.lifespan_context(app2),
            AsyncClient(transport=ASGITransport(app=app2), base_url="http://test") as client2,
        ):
            r_ws_list = await client2.get("/api/v1/workspaces", headers=auth_headers)
            assert r_ws_list.status_code == 200
            assert any(item["id"] == ws_id for item in r_ws_list.json()["workspaces"])

            r_overview = await client2.get(
                f"/api/v1/assistant/workspaces/{ws_id}/overview",
                headers=auth_headers,
            )
            assert r_overview.status_code == 200
            assert any(f["folder_id"] == folder_id for f in r_overview.json()["folders"])

            r_wiz_list = await client2.get("/api/v1/wizards", headers=auth_headers)
            assert r_wiz_list.status_code == 200
            assert any(item["id"] == wizard_id for item in r_wiz_list.json()["sessions"])

            r_broker_state = await client2.get(
                "/api/v1/permissions/broker/state",
                headers=auth_headers,
            )
            assert r_broker_state.status_code == 200
            assert any(t["id"] == ticket_id for t in r_broker_state.json()["tickets"])

            r_inbox = await client2.get(
                "/api/v1/inbox/notifications",
                headers=auth_headers,
                params={"workspace_id": ws_id},
            )
            assert r_inbox.status_code == 200
            assert any(n["id"] == notification_id for n in r_inbox.json()["items"])

            r_packs2 = await client2.get("/api/v1/packs", headers=auth_headers)
            assert r_packs2.status_code == 200
            assert len(r_packs2.json()["packs"]) >= 2

            r_help2 = await client2.get(
                "/api/v1/help/resolve",
                headers=auth_headers,
                params={"route": "/finops", "lang": "fr", "pack": "core"},
            )
            assert r_help2.status_code == 200
            assert r_help2.json()["active_article"]["resource_id"] == help_resource_id
    finally:
        await engine.dispose()
