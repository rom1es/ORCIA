"""Layer 2 PG18 Migration (`20261126_311`) & `SqlPackBundleV2Repository` integration test."""

from __future__ import annotations

import hashlib
import os
import shutil
import subprocess
import sys
import tempfile
import time
from collections.abc import Iterator
from pathlib import Path
from uuid import UUID

import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from testcontainers.core.container import DockerContainer
from uuid_utils import uuid7

from orcia_core.packs import (
    LoadedPackBundleV2,
    PackBundleKind,
    PackDnaMechanismSpec,
    PackManifestV2,
    PackScopeType,
    PackSourceOrigin,
    ResourcePinnedByActiveRunsError,
    SqlPackBundleV2Repository,
)

os.environ["TESTCONTAINERS_RYUK_DISABLED"] = "true"
REPO_ROOT = Path(__file__).resolve().parents[3]


def _prepare_tmp_sock_dir() -> Path:
    target = Path(tempfile.mkdtemp(prefix="orcia_31_1_pg18_"))
    target.chmod(0o777)
    return target


def _run_alembic(pg_url: str, *args: str) -> None:
    alembic_bin = str(Path(sys.executable).with_name("alembic"))
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "PYTHONPATH": os.environ.get("PYTHONPATH", ""),
        "DATABASE_URL": pg_url,
        "ORCIA_ENV_FILE": str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"),
    }
    subprocess.run(
        [alembic_bin, "-c", "infra/migrations/alembic.ini", *args],
        cwd=REPO_ROOT,
        env=env,
        check=True,
    )


@pytest.fixture(scope="module")
def pg18_url() -> Iterator[str]:
    """Start ephemeral PG18 over a `/tmp` Unix socket and run `alembic upgrade head`."""
    sock_dir = _prepare_tmp_sock_dir()
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
                stdout_b, stderr_b = pg.get_logs()
                logs = (stdout_b + stderr_b).decode("utf-8", errors="ignore")
                if (
                    logs.count("database system is ready to accept connections") >= 2
                    and (sock_dir / ".s.PGSQL.5432").exists()
                ):
                    break
                time.sleep(0.2)
            pg_auth = "orcia:orcia_dev_secret"  # pragma: allowlist secret
            url = f"postgresql+asyncpg://{pg_auth}@/orcia?host={sock_dir}"
            _run_alembic(url, "upgrade", "head")
            yield url
    finally:
        shutil.rmtree(sock_dir, ignore_errors=True)


async def _seed_workspaces(engine: AsyncEngine) -> tuple[str, str]:
    ou_id = str(uuid7())
    ws_a, ws_b = str(uuid7()), str(uuid7())
    async with engine.begin() as conn:
        await conn.execute(
            sa.text(
                "INSERT INTO org_units (id, slug, name, unit_type) "
                "VALUES (:id, 'ou-31-1', 'OU', 'TEAM')"
            ),
            {"id": ou_id},
        )
        for idx, ws_id in (("a", ws_a), ("b", ws_b)):
            await conn.execute(
                sa.text(
                    "INSERT INTO workspaces (id, slug, name, owner_org_unit_id, visibility_mode) "
                    "VALUES (:id, :slug, :name, :ou_id, 'STANDARD')"
                ),
                {"id": ws_id, "slug": f"ws-31-1-{idx}", "name": f"WS {idx}", "ou_id": ou_id},
            )
    return ws_a, ws_b


def _make_bundle(
    *, slug: str, version: str, scope_id: str, mech_payload: bool = False
) -> LoadedPackBundleV2:
    mechs = []
    if mech_payload:
        mechs.append(
            PackDnaMechanismSpec(
                mechanism_slug="title-check",
                name="Title Check",
                starlark_source=(
                    "def evaluate(p):\n"
                    "    orcia_sys.assert_rule(\n"
                    "        rule_id='R', condition=bool(p.get('ok')), message='m'\n"
                    "    )\n"
                ),
                source_sha256=hashlib.sha256(b"title-check").hexdigest(),
                passing_test_payload={"ok": True},
                failing_test_payload={"ok": False},
            )
        )
    return LoadedPackBundleV2(
        manifest=PackManifestV2(
            id=f"orcia-pack-{slug}",
            slug=slug,
            name=f"Pack {slug}",
            version=version,
            bundle_kind=PackBundleKind.IMPORTED,
            scope_type=PackScopeType.WORKSPACE,
            scope_id=scope_id,
            source_origin=PackSourceOrigin.APM_ZIP,
        ),
        archive_sha256=hashlib.sha256(f"{slug}:{version}:{scope_id}".encode()).hexdigest(),
        manifest_yaml=f"name: {slug}\nversion: {version}\n",
        dna_mechanisms=mechs,
    )


@pytest.mark.asyncio
async def test_story_31_1_pg18_migration_constraints_repo_and_downgrade(pg18_url: str) -> None:
    """Verify 20261126_311 DDL constraints, triggers, repo CRUD, and clean downgrade/upgrade."""
    engine = create_async_engine(pg18_url)
    try:
        async with engine.connect() as conn:
            scheme = (
                await conn.execute(
                    sa.text("SELECT id::text FROM connector_schemes WHERE scheme = 'pack'")
                )
            ).scalar_one()
        assert scheme == "0192c4e0-0000-7000-8000-00000000c008"

        ws_a, ws_b = await _seed_workspaces(engine)
        repo = SqlPackBundleV2Repository(engine)

        await repo.upsert_bundle_v2(
            _make_bundle(slug="demo-pack", version="1.0.0", scope_id=ws_a, mech_payload=True),
            cas_object_key="cas/ws-a-100",
        )
        await repo.upsert_bundle_v2(
            _make_bundle(slug="demo-pack", version="1.1.0", scope_id=ws_a),
            cas_object_key="cas/ws-a-110",
        )
        await repo.upsert_bundle_v2(
            _make_bundle(slug="demo-pack", version="1.0.0", scope_id=ws_b),
            cas_object_key="cas/ws-b-100",
        )

        ws_a_rows = await repo.list_bundles_v2(scope_type=PackScopeType.WORKSPACE, scope_id=ws_a)
        assert {r["version"] for r in ws_a_rows} == {"1.0.0", "1.1.0"}
        ws_b_rows = await repo.list_bundles_v2(scope_type=PackScopeType.WORKSPACE, scope_id=ws_b)
        assert len(ws_b_rows) == 1

        b1_id = str(next(r["id"] for r in ws_a_rows if r["version"] == "1.0.0"))
        b2_id = str(next(r["id"] for r in ws_a_rows if r["version"] == "1.1.0"))
        loaded = await repo.get_bundle_v2(b1_id)
        assert loaded is not None and loaded["cas_object_key"] == "cas/ws-a-100"
        mechs = await repo.list_dna_mechanisms(pack_bundle_id=b1_id)
        assert len(mechs) == 1
        assert mechs[0].passing_test_payload == {"ok": True}
        assert mechs[0].failing_test_payload == {"ok": False}

        # Typed FK CHECK guard on pack_draft_memberships
        with pytest.raises(sa.exc.IntegrityError):
            async with engine.begin() as conn:
                await conn.execute(
                    sa.text(
                        "INSERT INTO pack_draft_memberships "
                        "(id, draft_bundle_id, entity_type, entity_id, entity_slug) "
                        "VALUES (:id, :bid, 'WORKFLOW_V2', 'wf-1', 'wf-1')"
                    ),
                    {"id": str(uuid7()), "bid": b1_id},
                )

        # Cross-workspace activation trigger guard
        with pytest.raises(sa.exc.DBAPIError, match="Cross-workspace pack activation forbidden"):
            async with engine.begin() as conn:
                await conn.execute(
                    sa.text(
                        "INSERT INTO workspace_pack_activations "
                        "(id, workspace_id, pack_bundle_id, pack_slug, priority_order, is_active, activated_by) "  # noqa: E501
                        "VALUES (:id, :ws, :bid, 'demo-pack', 1, TRUE, 'admin')"
                    ),
                    {"id": str(uuid7()), "ws": UUID(ws_b), "bid": UUID(b1_id)},
                )

        # DEFERRABLE INITIALLY DEFERRED priority swap inside one transaction
        act1_id, act2_id = str(uuid7()), str(uuid7())
        async with engine.begin() as conn:
            await conn.execute(
                sa.text(
                    "INSERT INTO workspace_pack_activations "
                    "(id, workspace_id, pack_bundle_id, pack_slug, priority_order, is_active, activated_by) "  # noqa: E501
                    "VALUES (:id, :ws, :bid, :slug, :prio, TRUE, 'admin')"
                ),
                [
                    {"id": act1_id, "ws": ws_a, "bid": b1_id, "slug": "pack-1", "prio": 1},
                    {"id": act2_id, "ws": ws_a, "bid": b2_id, "slug": "pack-2", "prio": 2},
                ],
            )
            await conn.execute(
                sa.text("UPDATE workspace_pack_activations SET priority_order = 2 WHERE id = :id"),
                {"id": act1_id},
            )
            await conn.execute(
                sa.text("UPDATE workspace_pack_activations SET priority_order = 1 WHERE id = :id"),
                {"id": act2_id},
            )

        # Active bundle deletion fails; deactivated bundle deletion succeeds cleanly
        with pytest.raises(ResourcePinnedByActiveRunsError):
            await repo.delete_bundle(b1_id)

        async with engine.begin() as conn:
            await conn.execute(
                sa.text(
                    "UPDATE workspace_pack_activations "
                    "SET is_active = FALSE, priority_order = NULL WHERE id = :id"
                ),
                {"id": act2_id},
            )
        await repo.delete_bundle(b2_id)
        assert await repo.get_bundle_v2(b2_id) is None

        # Downgrade 20261125_303 and re-upgrade head
        _run_alembic(pg18_url, "downgrade", "20261125_303")
        async with engine.connect() as conn:
            has_tbl = (
                await conn.execute(sa.text("SELECT to_regclass('public.pack_draft_memberships')"))
            ).scalar()
            has_pack_scheme = (
                await conn.execute(sa.text("SELECT 1 FROM connector_schemes WHERE scheme = 'pack'"))
            ).scalar()
        assert has_tbl is None
        assert has_pack_scheme is None

        _run_alembic(pg18_url, "upgrade", "head")
        async with engine.connect() as conn:
            restored_tbl = (
                await conn.execute(
                    sa.text("SELECT to_regclass('public.workspace_pack_activations')")
                )  # noqa: E501
            ).scalar()
        assert restored_tbl is not None
    finally:
        await engine.dispose()
