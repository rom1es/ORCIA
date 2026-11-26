"""Layer 2 PG18 integration test for Story 31.3 (`create_app()`, `--no-cov`, `<= 300 L`)."""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
import tempfile
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
import sqlalchemy as sa
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine
from testcontainers.core.container import DockerContainer
from tests.integration._story_31_3_pack_fixture import build_overlapping_pack_zip
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
def pg18_url() -> Iterator[str]:
    """Start ephemeral PG18 (`/tmp` Unix socket) and run Alembic migrations."""
    sock_dir = Path(tempfile.mkdtemp(prefix="orcia_31_3_pg18_"))
    sock_dir.chmod(0o777)
    pg_box = (
        DockerContainer("pgvector/pgvector:pg18")
        .with_env("POSTGRES_USER", "orcia")
        .with_env("POSTGRES_PASSWORD", "orcia_dev_secret")
        .with_env("POSTGRES_DB", "orcia")
        .with_volume_mapping(str(sock_dir), "/var/run/postgresql", "rw")
    )
    try:
        with pg_box as pg:
            for _ in range(150):
                out_b, err_b = pg.get_logs()
                logs = (out_b + err_b).decode("utf-8", errors="ignore")
                if (
                    logs.count("database system is ready to accept connections") >= 2
                    and (sock_dir / ".s.PGSQL.5432").exists()
                ):
                    break
                time.sleep(0.2)
            pg_auth = "orcia:orcia_dev_secret"  # pragma: allowlist secret
            pg_url = f"postgresql+asyncpg://{pg_auth}@/orcia?host={sock_dir}"
            _run_alembic_head(pg_url)
            yield pg_url
    finally:
        shutil.rmtree(sock_dir, ignore_errors=True)


async def _seed_pg_topology(eng: Any, org_id: str, ws_id: str, admin_id: str) -> None:
    async with eng.begin() as conn:
        await conn.execute(
            sa.text(
                "INSERT INTO org_units (id, slug, name, unit_type, parent_id) "
                "VALUES (CAST(:id AS uuid), 'bu-31-3', 'BU 31.3', 'BU', NULL) "
                "ON CONFLICT (slug) DO NOTHING"
            ),
            {"id": org_id},
        )
        await conn.execute(
            sa.text(
                "INSERT INTO workspaces (id, slug, name, owner_org_unit_id, visibility_mode) "
                "VALUES (CAST(:id AS uuid), 'ws-31-3', 'Workspace 31.3', "
                "CAST(:org AS uuid), 'STANDARD')"
            ),
            {"id": ws_id, "org": org_id},
        )
        await conn.execute(
            sa.text(
                "INSERT INTO users (id, email, display_name, auth_mode, human_profile_archetype, "
                "platform_role, primary_org_unit_id) VALUES (CAST(:id AS uuid), "
                "'admin313@orcia.test', 'Admin 31.3', 'LOCAL', 'ARCHITECT', "
                "'PLATFORM_ADMIN', CAST(:org AS uuid))"
            ),
            {"id": admin_id, "org": org_id},
        )


@pytest.mark.asyncio
async def test_story_31_3_qualified_namespacing_and_flat_ontology_pg18(
    pg18_url: str, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify overlapping pack coexistence, DEFERRABLE priority swap, and workspace override."""
    monkeypatch.setenv("DATABASE_URL", pg18_url)
    monkeypatch.setenv("ORCIA_ENABLE_PG_SESSION_MAKER", "1")
    monkeypatch.setenv("ORCIA_ENV_FILE", str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"))

    org_id, ws_id, admin_id = str(uuid7()), str(uuid7()), str(uuid7())
    eng = create_async_engine(pg18_url)
    await _seed_pg_topology(eng, org_id, ws_id, admin_id)

    from orcia_api.main import create_app

    app = create_app()
    assert app.dependency_overrides == {}
    async with (
        app.router.lifespan_context(app),
        AsyncClient(
            transport=ASGITransport(app=app),
            base_url="http://test",
            headers={"X-Orcia-Persona": "karim"},
        ) as client,
    ):
        for slug, defn, instr_txt in (
            ("sdlc", "SDLC Release Gate Definition", "SDLC release checklist."),
            ("legal-audit", "Legal Audit Gate Definition", "Legal sign-off checklist."),
        ):
            zip_bytes = build_overlapping_pack_zip(slug=slug, definition=defn, instr_text=instr_txt)
            resp = await client.post(
                "/api/v1/packs/import",
                files={"file": (f"{slug}.zip", zip_bytes, "application/zip")},
                data={"scope_type": "WORKSPACE", "scope_id": ws_id},
            )
            assert resp.status_code == 200, resp.text

        async with eng.begin() as conn:
            bundles = (
                await conn.execute(
                    sa.text(
                        "SELECT id::text, slug FROM declarative_pack_bundles "
                        "WHERE slug IN ('sdlc', 'legal-audit') AND scope_id = :ws"
                    ),
                    {"ws": ws_id},
                )
            ).fetchall()
            by_slug = {str(r[1]): str(r[0]) for r in bundles}
            for pslug, prio in (("sdlc", 1), ("legal-audit", 2)):
                await conn.execute(
                    sa.text(
                        "INSERT INTO workspace_pack_activations "
                        "(id, workspace_id, pack_bundle_id, pack_slug, priority_order, "
                        "is_active, activated_by) VALUES (CAST(:id AS uuid), "
                        "CAST(:ws AS uuid), CAST(:bid AS uuid), :pslug, :prio, TRUE, 'admin')"
                    ),
                    {
                        "id": str(uuid7()),
                        "ws": ws_id,
                        "bid": by_slug[pslug],
                        "pslug": pslug,
                        "prio": prio,
                    },
                )

        # 1. Both overlapping pack entities coexist with qualified_ref & is_colliding
        list_res = await client.get("/api/v1/agents-and-skills", params={"workspace_id": ws_id})
        assert list_res.status_code == 200
        ag_by_id = {a["agent_id"]: a for a in list_res.json()["agents"]}
        assert ag_by_id["sdlc:reviewer"]["qualified_ref"] == "@sdlc/reviewer"
        assert ag_by_id["legal-audit:reviewer"]["qualified_ref"] == "@legal-audit/reviewer"
        assert ag_by_id["sdlc:reviewer"]["is_colliding"] is True

        # 2. Bare resolve picks priority 1; strict=true returns 409; qualified succeeds
        r_unq = await client.get(
            "/api/v1/agents-and-skills/resolve",
            params={"ref": "@reviewer", "kind": "agent", "workspace_id": ws_id},
        )
        assert r_unq.status_code == 200 and r_unq.json()["pack_slug"] == "sdlc"
        r_409 = await client.get(
            "/api/v1/agents-and-skills/resolve",
            params={
                "ref": "@reviewer",
                "kind": "agent",
                "workspace_id": ws_id,
                "strict_disambiguation": "true",
            },
        )
        assert r_409.status_code == 409
        r_qual = await client.get(
            "/api/v1/agents-and-skills/resolve",
            params={"ref": "legal-audit:reviewer", "kind": "agent", "workspace_id": ws_id},
        )
        assert r_qual.status_code == 200 and r_qual.json()["entity_id"] == "legal-audit:reviewer"

        # 3. Flat ontology + DNA + instructions resolve sdlc (priority 1)
        eff_url = "/api/v1/ontology-rag/ontology/effective"
        ont_1 = await client.get(eff_url, params={"workspace_id": ws_id})
        assert ont_1.status_code == 200
        d1 = ont_1.json()
        assert {c["canonical_term"]: c for c in d1["concepts"]}["Release Gate"][
            "pack_slug"
        ] == "sdlc"
        assert d1["instructions"][0]["pack_slug"] == "sdlc"
        assert d1["dna_mechanisms"][0]["pack_slug"] == "sdlc"

        # 4. Atomic DEFERRABLE priority swap -> legal-audit becomes priority 1
        async with eng.begin() as conn:
            await conn.execute(
                sa.text(
                    "UPDATE workspace_pack_activations SET priority_order = "
                    "CASE WHEN pack_slug = 'legal-audit' THEN 1 ELSE 2 END "
                    "WHERE workspace_id = CAST(:ws AS uuid)"
                ),
                {"ws": ws_id},
            )
        r_swapped = await client.get(
            "/api/v1/agents-and-skills/resolve",
            params={"ref": "/compliance-check", "kind": "skill", "workspace_id": ws_id},
        )
        assert r_swapped.status_code == 200 and r_swapped.json()["pack_slug"] == "legal-audit"
        ont_2 = await client.get(eff_url, params={"workspace_id": ws_id})
        d2 = ont_2.json()
        assert {c["canonical_term"]: c for c in d2["concepts"]}["Release Gate"][
            "pack_slug"
        ] == "legal-audit"
        assert d2["instructions"][0]["pack_slug"] == "legal-audit"

        # 5. Workspace override (pack_bundle_id IS NULL) beats priority-1 pack term
        async with eng.begin() as conn:
            await conn.execute(
                sa.text(
                    "INSERT INTO ontology_concepts (id, concept_key, canonical_term, level, "
                    "scope_id, definition_text, snapshot_branch_status, pack_bundle_id) "
                    "VALUES (CAST(:id AS uuid), :ck, 'Release Gate', '3_WORKSPACE', :ws, "
                    "'Workspace Override Gate', 'ACTIVE', NULL)"
                ),
                {"id": str(uuid7()), "ck": f"ws:{ws_id}:release-gate", "ws": ws_id},
            )
        ont_3 = await client.get(eff_url, params={"workspace_id": ws_id})
        g3 = {c["canonical_term"]: c for c in ont_3.json()["concepts"]}["Release Gate"]
        assert g3["definition_text"] == "Workspace Override Gate" and g3["pack_bundle_id"] is None

        async with eng.connect() as conn:
            cnt = (
                await conn.execute(
                    sa.text(
                        "SELECT COUNT(*) FROM ontology_concepts "
                        "WHERE canonical_term = 'Release Gate' AND pack_bundle_id IS NOT NULL"
                    )
                )
            ).scalar_one()
            assert cnt == 2 and UUID(ws_id)
    await eng.dispose()
