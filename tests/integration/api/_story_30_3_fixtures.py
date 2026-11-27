"""Container & topology fixtures for Story 30.3 PG18 + Redis tests (`<= 140 L`)."""

from __future__ import annotations

import importlib.util
import os
import shutil
import sys
import tempfile
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine
from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import wait_for_logs
from uuid_utils import uuid7

os.environ["TESTCONTAINERS_RYUK_DISABLED"] = "true"

REPO_ROOT = Path(__file__).resolve().parents[3]
SEEDED_WS_ID = "0192c4e0-0000-7000-8000-000000000201"
CONF_WS_ID = "0192c4e0-0000-7000-8000-000000000203"
FORBIDDEN_WS_ID = "0195f000-0000-7000-8000-000000009999"


def prepare_sock_dir(prefix: str) -> Path:
    target = Path(tempfile.mkdtemp(prefix=f"orcia_{prefix}_"))
    target.chmod(0o777)
    return target


def load_reset_script() -> Any:
    script_path = REPO_ROOT / "infra" / "scripts" / "maintenance" / "09_reset_db_first_boot.py"
    spec = importlib.util.spec_from_file_location("reset_db_first_boot_30_3", script_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def pg18_and_redis74_urls() -> Iterator[tuple[str, str]]:
    """Spin up ephemeral PostgreSQL 18 (`pgvector:pg18`) and Redis 7.4 containers."""
    pg_sock_dir = prepare_sock_dir("pg18")
    rd_sock_dir = prepare_sock_dir("rd74")
    rd_sock_path = rd_sock_dir / "redis.sock"
    pg_container = (
        DockerContainer("pgvector/pgvector:pg18")
        .with_env("POSTGRES_USER", "orcia")
        .with_env("POSTGRES_PASSWORD", "orcia_dev_secret")
        .with_env("POSTGRES_DB", "orcia")
        .with_volume_mapping(str(pg_sock_dir), "/var/run/postgresql", "rw")
    )
    redis_container = (
        DockerContainer("redis:7.4.2-alpine")
        .with_volume_mapping(str(rd_sock_dir), "/sock", "rw")
        .with_command("redis-server --unixsocket /sock/redis.sock --unixsocketperm 777 --port 6379")
    )
    try:
        with pg_container as pg, redis_container as rc:
            wait_for_logs(pg, "database system is ready to accept connections", timeout=30)
            wait_for_logs(rc, "Ready to accept connections", timeout=20)
            for _ in range(40):
                if (pg_sock_dir / ".s.PGSQL.5432").exists() and rd_sock_path.exists():
                    break
                time.sleep(0.15)
            pg_auth = "orcia:orcia_dev_secret"  # pragma: allowlist secret
            pg_url = f"postgresql+asyncpg://{pg_auth}@/orcia?host={pg_sock_dir}"
            yield pg_url, f"unix://{rd_sock_path}"
    finally:
        shutil.rmtree(pg_sock_dir, ignore_errors=True)
        shutil.rmtree(rd_sock_dir, ignore_errors=True)


async def seed_story_30_3_topology(engine: AsyncEngine) -> None:
    """Seed org_units, users, workspaces, and memberships in PG18."""
    async with engine.begin() as conn:
        ou_uuid = UUID("0192c4e0-0000-7000-8000-000000000101")
        other_ou_uuid = UUID("0192c4e0-0000-7000-8000-000000000102")
        marc_uuid = UUID("0192c4e0-0000-7000-8000-000000000603")
        nadia_uuid = UUID("0192c4e0-0000-7000-8000-000000000604")
        await conn.execute(
            sa.text(
                "INSERT INTO org_units (id, slug, name, unit_type) "
                "VALUES (:id, 'ou-30-3', 'Product 30.3', 'TEAM'), "
                "(:other_id, 'ou-30-3-other', 'Other 30.3', 'TEAM') "
                "ON CONFLICT (id) DO NOTHING;"
            ),
            {"id": ou_uuid, "other_id": other_ou_uuid},
        )
        await conn.execute(
            sa.text(
                "INSERT INTO users (id, email, display_name, auth_mode, "
                "human_profile_archetype, platform_role, primary_org_unit_id, is_active) "
                "VALUES (:marc_id, 'marc.lead@orcia.io', 'Marc', 'HYBRID', "
                "'TEAM_LEAD', 'CONTRIBUTOR', :ou_id, TRUE), "
                "(:nadia_id, 'nadia.dev@orcia.io', 'Nadia', 'LOCAL', "
                "'DEVELOPER', 'CONTRIBUTOR', :other_ou_id, TRUE) "
                "ON CONFLICT (id) DO NOTHING;"
            ),
            {
                "marc_id": marc_uuid,
                "nadia_id": nadia_uuid,
                "ou_id": ou_uuid,
                "other_ou_id": other_ou_uuid,
            },
        )
        await conn.execute(
            sa.text("UPDATE org_units SET lead_user_id = :lead_id WHERE id = :id;"),
            {"id": ou_uuid, "lead_id": str(marc_uuid)},
        )
        await conn.execute(
            sa.text(
                "INSERT INTO workspaces (id, slug, name, owner_org_unit_id, visibility_mode) "
                "VALUES (:id, 'ws-30-3', 'Workspace 30.3', :ou_id, 'STANDARD'), "
                "(:conf_id, 'ws-30-3-conf', 'Confidential 30.3', :ou_id, "
                "'CONFIDENTIAL_RESTRICTED'), "
                "(:fid, 'ws-30-3-forbidden', 'Forbidden WS', :other_ou_id, 'STANDARD') "
                "ON CONFLICT (id) DO NOTHING;"
            ),
            {
                "id": UUID(SEEDED_WS_ID),
                "conf_id": UUID(CONF_WS_ID),
                "ou_id": ou_uuid,
                "fid": UUID(FORBIDDEN_WS_ID),
                "other_ou_id": other_ou_uuid,
            },
        )
        await conn.execute(
            sa.text(
                "INSERT INTO workspace_memberships "
                "(id, workspace_id, user_id, role, access_mode) "
                "VALUES (:m_pay, :ws_id, :marc_id, 'TEAM_LEAD', "
                "'CONTRIBUTOR_ACTION_REQUIRED'), "
                "(:m_conf, :conf_id, :marc_id, 'TEAM_LEAD', 'CONTRIBUTOR_ACTION_REQUIRED'), "
                "(:m_obs, :ws_id, :nadia_id, 'OBSERVER', 'READ_ONLY_OBSERVER') "
                "ON CONFLICT DO NOTHING;"
            ),
            {
                "m_pay": UUID("0195f000-0000-7000-8000-000000003039"),
                "m_conf": UUID("0195f000-0000-7000-8000-000000003040"),
                "m_obs": UUID("0195f000-0000-7000-8000-000000003041"),
                "ws_id": UUID(SEEDED_WS_ID),
                "conf_id": UUID(CONF_WS_ID),
                "marc_id": marc_uuid,
                "nadia_id": nadia_uuid,
            },
        )


async def activate_system_packs_with_slots_in_ws(
    engine: AsyncEngine,
    *,
    workspace_id: str,
    include_orcia_docs: bool = False,
) -> None:
    """Bind `sdlc` required slots to workspace datasources and activate system packs."""
    ws_uuid = UUID(workspace_id)
    slot_defs = (
        ("jira-tracker", "jira", "jira://jira.internal/P1"),
        ("confluence-kb", "confluence", "https://wiki.internal/P1"),
        ("git-repo", "git", "https://git.internal/org/repo.git"),
    )
    async with engine.begin() as conn:
        bundles = (
            await conn.execute(
                sa.text(
                    "SELECT id, slug FROM declarative_pack_bundles "
                    "WHERE slug IN ('sdlc', 'orcia-docs') AND status = 'PUBLISHED'"
                )
            )
        ).fetchall()
        bundle_by_slug = {str(r[1]): r[0] for r in bundles}
        for slot_key, scheme, uri in slot_defs:
            ds_id = UUID(str(uuid7()))
            await conn.execute(
                sa.text(
                    "INSERT INTO workspace_datasources "
                    "(id, workspace_id, alias, scheme, uri, role, execution_identity) "
                    "VALUES (:id, :ws, :alias, :scheme, :uri, 'primary', 'passthrough') "
                    "ON CONFLICT DO NOTHING"
                ),
                {
                    "id": ds_id,
                    "ws": ws_uuid,
                    "alias": f"{slot_key}-{str(ws_uuid)[:8]}",
                    "scheme": scheme,
                    "uri": uri,
                },  # noqa: E501
            )
            await conn.execute(
                sa.text(
                    "INSERT INTO workspace_pack_slot_bindings "
                    "(id, workspace_id, pack_bundle_id, pack_slug, slot_key, target_kind, "
                    "target_id, bound_datasource_id, connector_scheme, bound_by) "
                    "VALUES (:id, :ws, :bid, 'sdlc', :skey, 'WORKSPACE_DATASOURCE', "
                    ":tid, :ds_id, :scheme, 'test')"
                ),
                {
                    "id": UUID(str(uuid7())),
                    "ws": ws_uuid,
                    "bid": bundle_by_slug["sdlc"],
                    "skey": slot_key,
                    "tid": str(ds_id),
                    "ds_id": ds_id,
                    "scheme": scheme,
                },
            )
        slugs = ["sdlc", "orcia-docs"] if include_orcia_docs else ["sdlc"]
        for prio, pslug in enumerate(slugs, start=1):
            if pslug not in bundle_by_slug:
                continue
            await conn.execute(
                sa.text(
                    "INSERT INTO workspace_pack_activations "
                    "(id, workspace_id, pack_bundle_id, pack_slug, priority_order, "
                    "is_active, activated_by) VALUES (:id, :ws, :bid, :pslug, :prio, TRUE, 'test')"
                ),
                {
                    "id": UUID(str(uuid7())),
                    "ws": ws_uuid,
                    "bid": bundle_by_slug[pslug],
                    "pslug": pslug,
                    "prio": prio,
                },
            )


async def seed_workspace_for_16_3(engine: AsyncEngine) -> str:
    """Seed org_unit, workspace, and activate `sdlc` + `orcia-docs` for Story 16.3 runs."""
    ou_id, ws_id = UUID(str(uuid7())), UUID(str(uuid7()))
    async with engine.begin() as conn:
        await conn.execute(
            sa.text(
                "INSERT INTO org_units (id, slug, name, unit_type) "
                "VALUES (:id, 'ou-16-3', 'Team 16.3', 'TEAM') ON CONFLICT DO NOTHING"
            ),
            {"id": ou_id},
        )
        await conn.execute(
            sa.text(
                "INSERT INTO workspaces (id, slug, name, owner_org_unit_id, visibility_mode) "
                "VALUES (:id, 'ws-16-3', 'Workspace 16.3', :ou, 'STANDARD') ON CONFLICT DO NOTHING"  # noqa: E501
            ),
            {"id": ws_id, "ou": ou_id},
        )
    await activate_system_packs_with_slots_in_ws(
        engine, workspace_id=str(ws_id), include_orcia_docs=True
    )
    return str(ws_id)
