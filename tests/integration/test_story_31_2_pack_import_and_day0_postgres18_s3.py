"""Layer 2 PG18 + SeaweedFS S3 integration test for Story 31.2 (`create_app()`, <= 300 L)."""

from __future__ import annotations

import base64
import importlib.util
import io
import os
import shutil
import subprocess
import sys
import tempfile
import time
import zipfile
from collections.abc import Iterator
from pathlib import Path
from uuid import UUID

import pytest
import sqlalchemy as sa
import yaml
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine
from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import wait_for_logs
from uuid_utils import uuid7

os.environ["TESTCONTAINERS_RYUK_DISABLED"] = "true"
REPO_ROOT = Path(__file__).resolve().parents[2]


def _run_alembic_head(pg_url: str) -> None:
    alembic_bin = str(Path(sys.executable).with_name("alembic"))
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "PYTHONPATH": os.environ.get("PYTHONPATH", ""),
        "DATABASE_URL": pg_url,
        "ORCIA_ENV_FILE": str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"),
    }
    subprocess.run(
        [alembic_bin, "-c", "infra/migrations/alembic.ini", "upgrade", "head"],
        cwd=REPO_ROOT,
        env=env,
        check=True,
    )


@pytest.fixture(scope="module")
def pg18_and_seaweed_urls() -> Iterator[tuple[str, str]]:
    """Start ephemeral PG18 (`/tmp` Unix socket) + SeaweedFS S3 (`chrislusf/seaweedfs:4.17`)."""
    sock_dir = Path(tempfile.mkdtemp(prefix="orcia_31_2_pg18_"))
    sock_dir.chmod(0o777)
    pg_box = (
        DockerContainer("pgvector/pgvector:pg18")
        .with_env("POSTGRES_USER", "orcia")
        .with_env("POSTGRES_PASSWORD", "orcia_dev_secret")
        .with_env("POSTGRES_DB", "orcia")
        .with_volume_mapping(str(sock_dir), "/var/run/postgresql", "rw")
    )
    s3_box = (
        DockerContainer("chrislusf/seaweedfs:4.17")
        .with_command("server -s3 -s3.port=9000 -ip.bind=0.0.0.0 -dir=/tmp")
        .with_env("AWS_ACCESS_KEY_ID", "orcia_seaweed")
        .with_env("AWS_SECRET_ACCESS_KEY", "orcia_seaweed_secret")  # pragma: allowlist secret
        .with_exposed_ports(9000)
    )
    try:
        with pg_box as pg, s3_box as s3:
            for _ in range(150):
                out_b, err_b = pg.get_logs()
                logs = (out_b + err_b).decode("utf-8", errors="ignore")
                if (
                    logs.count("database system is ready to accept connections") >= 2
                    and (sock_dir / ".s.PGSQL.5432").exists()
                ):
                    break
                time.sleep(0.2)
            wait_for_logs(s3, "Start Seaweed S3 API Server", timeout=30)
            s3_url = f"http://127.0.0.1:{int(s3.get_exposed_port(9000))}"
            pg_auth = "orcia:orcia_dev_secret"  # pragma: allowlist secret
            pg_url = f"postgresql+asyncpg://{pg_auth}@/orcia?host={sock_dir}"
            _run_alembic_head(pg_url)
            yield pg_url, s3_url
    finally:
        shutil.rmtree(sock_dir, ignore_errors=True)


def _build_pack_zip(
    *, slug: str, version: str, scope_id: str, agent_body: str = "Verify compliance rules."
) -> bytes:
    buf = io.BytesIO()
    apm = yaml.safe_dump(
        {
            "name": slug,
            "version": version,
            "description": "Integration pack",
            "x-orcia": {
                "slug": slug,
                "bundle_kind": "IMPORTED",
                "scope_type": "WORKSPACE",
                "scope_id": scope_id,
                "status": "PUBLISHED",
            },
        }
    )
    agent = (
        "---\nname: Compliance Bot\ndescription: Checks PR\n"
        "x-orcia:\n  posture: PRODUCER\n  human_partner_role: TECH_LEAD\n"
        "---\n" + agent_body + "\n"
    )
    skill = (
        "---\nname: Compliance Check\ndescription: Check\n"
        "x-orcia:\n  command_handle: /compliance-check\n---\nInspect.\n"
    )
    glossary = yaml.safe_dump({"terms": [{"key": "SLA", "label": "SLA", "definition": "Target"}]})
    policy = (
        "---\npolicy_key: git-ro\nuri_pattern: git://repo/*\n"
        "connector_scheme: git\nrequired_role: DEVELOPER\nsla_hours: 8\n---\nProcedure.\n"
    )
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{slug}/apm.yml", apm)
        zf.writestr(f"{slug}/agents/compliance-bot.agent.md", agent)
        zf.writestr(f"{slug}/skills/compliance-check/SKILL.md", skill)
        zf.writestr(f"{slug}/ontology/glossary.yaml", glossary)
        zf.writestr(f"{slug}/policies/git-ro.policy.md", policy)
    return buf.getvalue()


@pytest.mark.asyncio
async def test_story_31_2_day0_seed_import_cas_conflict_and_delete_postgres18_s3(
    pg18_and_seaweed_urls: tuple[str, str], monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify Day-0 boot seeding, HTTP->PG18+SeaweedFS import, 409 conflicts, delete & reset."""
    pg_url, s3_url = pg18_and_seaweed_urls
    monkeypatch.setenv("DATABASE_URL", pg_url)
    monkeypatch.setenv("S3_ENDPOINT_URL", s3_url)
    monkeypatch.setenv("ORCIA_ENV", "local")
    monkeypatch.setenv("ORCIA_ENV_FILE", str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"))
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    monkeypatch.setenv("ORCIA_JWT_SIGNING_SECRET", "orcia-31-2-jwt-secret-0001")
    monkeypatch.setenv("ORCIA_PASSTHROUGH_MASTER_KEY", "orcia-31-2-vault-key-0001")
    monkeypatch.setenv("ORCIA_ENABLE_PG_SESSION_MAKER", "1")

    from orcia_api.main import create_app

    app = create_app()
    assert app.dependency_overrides == {}
    engine = create_async_engine(pg_url)
    try:
        async with (
            app.router.lifespan_context(app),
            AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
        ):
            packs_resp = await client.get("/api/v1/packs")
            assert packs_resp.status_code == 200
            packs = packs_resp.json()["packs"]
            assert {p["slug"] for p in packs} >= {"sdlc", "orcia-docs"}
            sdlc_pack = next(p for p in packs if p["slug"] == "sdlc")
            assert sdlc_pack["bundle_kind"] == "SYSTEM"
            assert sdlc_pack["cas_object_key"] is not None

            ag_resp = await client.get("/api/v1/agents-and-skills")
            assert ag_resp.status_code == 200
            ag_ids = {a["agent_id"] for a in ag_resp.json()["agents"]}
            assert {"sdlc:agent-us", "orcia-docs:redacteur-documentation-orcia"} <= ag_ids
            assert len((await client.get("/api/v1/vsm")).json()["items"]) >= 1

            ws_id = str(uuid7())
            adm_id = str(uuid7())
            async with engine.begin() as conn:
                ou_id = (
                    await conn.execute(sa.text("SELECT id FROM org_units LIMIT 1"))
                ).scalar_one()
                await conn.execute(
                    sa.text(
                        "INSERT INTO workspaces "
                        "(id, slug, name, owner_org_unit_id, visibility_mode) "
                        "VALUES (:id, 'ws-31-2', 'WS 31.2', :ou, 'STANDARD')"
                    ),
                    {"id": UUID(ws_id), "ou": ou_id},
                )
                await conn.execute(
                    sa.text(
                        "INSERT INTO users (id, email, display_name, auth_mode, "
                        "human_profile_archetype, platform_role, primary_org_unit_id) "
                        "VALUES (:uid, 'admin312@orcia.test', 'Admin 31.2', 'LOCAL', "
                        "'ARCHITECT', 'PLATFORM_ADMIN', :ou)"
                    ),
                    {"uid": UUID(adm_id), "ou": ou_id},
                )
            adm_tok = app.state.auth_service.jwt_manager.issue_token_pair(
                user_id=adm_id,
                email="admin312@orcia.test",
                role="PLATFORM_ADMIN",
                org_unit_id=str(ou_id),
                archetype="ARCHITECT",
                auth_mode="LOCAL",
            ).access_token
            adm_h = {"Authorization": f"Bearer {adm_tok}"}

            zip_v1 = _build_pack_zip(slug="fin-audit", version="1.0.0", scope_id=ws_id)
            imp_resp = await client.post(
                "/api/v1/packs/import",
                headers=adm_h,
                json={
                    "zip_base64": base64.b64encode(zip_v1).decode("ascii"),
                    "scope_type": "WORKSPACE",
                    "scope_id": ws_id,
                },
            )
            assert imp_resp.status_code == 200, imp_resp.text
            imp_data = imp_resp.json()
            bid = imp_data["bundle_id"]
            assert imp_data["cas_object_key"].startswith("packs/fin-audit/1.0.0/")
            assert await app.state.pack_cas_storage.head_archive_zip(imp_data["cas_object_key"])

            async with engine.connect() as conn:
                for tbl, exp in (
                    ("catalog_items", 2),
                    ("ontology_concepts", 1),
                    ("permission_broker_policies", 1),
                ):
                    q = f"SELECT COUNT(*) FROM {tbl} WHERE pack_bundle_id = CAST(:b AS uuid)"
                    assert int((await conn.execute(sa.text(q), {"b": bid})).scalar_one()) == exp

            zip_diff = _build_pack_zip(
                slug="fin-audit", version="1.0.0", scope_id=ws_id, agent_body="Modified body"
            )
            conflict = await client.post(
                "/api/v1/packs/import",
                headers=adm_h,
                json={"zip_base64": base64.b64encode(zip_diff).decode("ascii")},
            )
            assert conflict.status_code == 409
            assert conflict.json()["error_code"] == "ERR_PACK_VERSION_CONFLICT"

            sys_del = await client.delete(f"/api/v1/packs/{sdlc_pack['bundle_id']}", headers=adm_h)
            assert sys_del.status_code == 403
            assert sys_del.json()["error_code"] == "ERR_PACK_SYSTEM_DELETE_FORBIDDEN"

            async with engine.begin() as conn:
                await conn.execute(
                    sa.text(
                        "INSERT INTO workspace_pack_activations "
                        "(id, workspace_id, pack_bundle_id, pack_slug, "
                        "priority_order, is_active, activated_by) "
                        "VALUES (:id, :ws, :bid, 'fin-audit', 1, TRUE, 'test')"
                    ),
                    {"id": UUID(str(uuid7())), "ws": UUID(ws_id), "bid": UUID(bid)},
                )
            pin_del = await client.delete(f"/api/v1/packs/{bid}", headers=adm_h)
            assert pin_del.status_code == 409
            assert pin_del.json()["error_code"] == "ERR_RESOURCE_PINNED_BY_ACTIVE_RUNS"

            async with engine.begin() as conn:
                await conn.execute(
                    sa.text(
                        "UPDATE workspace_pack_activations "
                        "SET is_active = FALSE, priority_order = NULL "
                        "WHERE pack_bundle_id = :bid"
                    ),
                    {"bid": UUID(bid)},
                )
            assert (await client.delete(f"/api/v1/packs/{bid}", headers=adm_h)).status_code == 200
            async with engine.connect() as conn:
                q = "SELECT COUNT(*) FROM catalog_items WHERE pack_bundle_id = CAST(:b AS uuid)"
                assert int((await conn.execute(sa.text(q), {"b": bid})).scalar_one()) == 0

            reset_path = (
                REPO_ROOT / "infra" / "scripts" / "maintenance" / "09_reset_db_first_boot.py"
            )
            spec = importlib.util.spec_from_file_location("reset_31_2", reset_path)
            assert spec is not None and spec.loader is not None
            reset_mod = importlib.util.module_from_spec(spec)
            sys.modules["reset_31_2"] = reset_mod
            spec.loader.exec_module(reset_mod)
            report = await reset_mod.reset_database_to_first_boot(engine, apply_changes=True)
            assert report.committed is True
            async with engine.connect() as conn:
                cnt_q = "SELECT COUNT(*) FROM catalog_items WHERE pack_bundle_id IS NOT NULL"
                assert int((await conn.execute(sa.text(cnt_q))).scalar_one()) >= 10
    finally:
        await engine.dispose()
