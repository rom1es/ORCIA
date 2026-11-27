"""Pack zip, PG18 container & topology fixtures for Story 31.4 integration tests (`<= 250 L`)."""

from __future__ import annotations

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
from typing import Any

import pytest
import sqlalchemy as sa
import yaml
from testcontainers.core.container import DockerContainer

REPO_ROOT = Path(__file__).resolve().parents[2]


def run_alembic_head(pg_url: str) -> None:
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
    sock_dir = Path(tempfile.mkdtemp(prefix="orcia_31_4_pg18_"))
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
            run_alembic_head(pg_url)
            yield pg_url
    finally:
        shutil.rmtree(sock_dir, ignore_errors=True)


def build_slot_pack_zip(
    *,
    slug: str,
    version: str,
    scope_id: str,
    slots: list[dict[str, Any]],
    with_workflow: bool = False,
) -> bytes:
    """Build an APM-superset `.zip` bundle with declared connector slots & optional workflow."""
    buf = io.BytesIO()
    apm = yaml.safe_dump(
        {
            "name": slug,
            "version": version,
            "description": f"Story 31.4 test pack {slug}",
            "x-orcia": {
                "id": f"orcia-pack-{slug}",
                "slug": slug,
                "bundle_kind": "IMPORTED",
                "scope_type": "WORKSPACE",
                "scope_id": scope_id,
                "status": "PUBLISHED",
                "connector_slots": slots,
            },
        }
    )
    agent = (
        "---\nname: Delivery Bot\ndescription: Slot guarded agent\n"
        "x-orcia:\n  posture: PRODUCER\n  human_partner_role: TECH_LEAD\n"
        "---\nExecute governed delivery step.\n"
    )
    wf_yaml = yaml.safe_dump(
        {
            "id": f"wf-{slug}",
            "slug": f"wf-{slug}",
            "title": f"Workflow {slug}",
            "version": "1.0.0",
            "status": "published",
            "pack_id": f"orcia-pack-{slug}",
            "orchestration_type": "deterministic_dbos",
            "execution_mode": "native_orcia",
            "sub_steps": [
                {
                    "id": "step-1",
                    "name": "Produce Draft",
                    "short_label": "Draft",
                    "step_executor_type": "program_executor",
                    "trigger_condition_label": "Start",
                    "role_description": "Draft producer",
                    "instruction_prompt_or_ref": f"@{slug}/delivery-bot",
                    "output_description": "Draft output",
                    "requires_human_checkpoint": True,
                    "checkpoint_label": "Approve Draft",
                }
            ],
        }
    )
    with zipfile.ZipFile(buf, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.writestr(f"{slug}/apm.yml", apm)
        zf.writestr(f"{slug}/agents/delivery-bot.agent.md", agent)
        if with_workflow:
            zf.writestr(f"{slug}/workflows/wf-{slug}.yaml", wf_yaml)
    return buf.getvalue()


async def seed_story_31_4_topology(
    eng: Any,
    *,
    org_id: str,
    ws_a: str,
    ws_b: str,
    admin_id: str,
    ds_a_id: str,
    ds_b_id: str,
    ec_id: str,
) -> None:
    """Seed org_unit, 2 workspaces, admin user, 2 datasources & 1 enterprise connector."""
    async with eng.begin() as conn:
        await conn.execute(
            sa.text(
                "INSERT INTO org_units (id, slug, name, unit_type, parent_id) "
                "VALUES (CAST(:id AS uuid), 'bu-31-4', 'BU 31.4', 'BU', NULL) "
                "ON CONFLICT (slug) DO NOTHING"
            ),
            {"id": org_id},
        )
        for ws_id, slug, name in (
            (ws_a, "ws-31-4-a", "Workspace 31.4 A"),
            (ws_b, "ws-31-4-b", "Workspace 31.4 B"),
        ):
            await conn.execute(
                sa.text(
                    "INSERT INTO workspaces (id, slug, name, owner_org_unit_id, visibility_mode) "
                    "VALUES (CAST(:id AS uuid), :slug, :name, CAST(:org AS uuid), 'STANDARD')"
                ),
                {"id": ws_id, "slug": slug, "name": name, "org": org_id},
            )
        await conn.execute(
            sa.text(
                "INSERT INTO users (id, email, display_name, auth_mode, human_profile_archetype, "
                "platform_role, primary_org_unit_id) VALUES (CAST(:id AS uuid), "
                "'admin314@orcia.test', 'Admin 31.4', 'LOCAL', 'ARCHITECT', "
                "'PLATFORM_ADMIN', CAST(:org AS uuid))"
            ),
            {"id": admin_id, "org": org_id},
        )
        for ds_id, ws_id, alias, uri in (
            (ds_a_id, ws_a, "repo-a", "git://github.com/orcia/repo-a"),
            (ds_b_id, ws_b, "repo-b", "git://github.com/orcia/repo-b"),
        ):
            await conn.execute(
                sa.text(
                    "INSERT INTO workspace_datasources "
                    "(id, workspace_id, alias, scheme, uri, role) "
                    "VALUES (CAST(:id AS uuid), CAST(:ws AS uuid), :alias, 'git', :uri, 'ACTIVE')"
                ),
                {"id": ds_id, "ws": ws_id, "alias": alias, "uri": uri},
            )
        await conn.execute(
            sa.text(
                "INSERT INTO enterprise_connectors (id, connector_kind, name, base_url, "
                "auth_mode, enabled) VALUES (CAST(:id AS uuid), 'GITLAB', 'GitLab Bridge 31.4', "
                "'https://gitlab.orcia.test', 'PERSONAL_ACCESS_TOKEN', TRUE)"
            ),
            {"id": ec_id},
        )


async def seed_story_31_4_hardening_extras(
    eng: Any,
    *,
    org_id: str,
    ws_a: str,
    obs_id: str,
    ds_db_id: str,
) -> None:
    """Seed observer user with PG18 `READ_ONLY_OBSERVER` membership and a `db` datasource."""
    from uuid_utils import uuid7

    async with eng.begin() as conn:
        await conn.execute(
            sa.text(
                "INSERT INTO users (id, email, display_name, auth_mode, human_profile_archetype, "
                "platform_role, primary_org_unit_id) VALUES (CAST(:uid AS uuid), "
                "'obs314@orcia.test', 'Observer 31.4', 'LOCAL', 'ARCHITECT', 'CONTRIBUTOR', "
                "CAST(:org AS uuid))"
            ),
            {"uid": obs_id, "org": org_id},
        )
        await conn.execute(
            sa.text(
                "INSERT INTO workspace_memberships (id, workspace_id, user_id, role, access_mode) "
                "VALUES (CAST(:mid AS uuid), CAST(:ws AS uuid), CAST(:uid AS uuid), "
                "'CONTRIBUTOR', 'READ_ONLY_OBSERVER')"
            ),
            {"mid": str(uuid7()), "ws": ws_a, "uid": obs_id},
        )
        await conn.execute(
            sa.text(
                "INSERT INTO workspace_datasources (id, workspace_id, alias, scheme, uri, role) "
                "VALUES (CAST(:id AS uuid), CAST(:ws AS uuid), 'db-a', 'db', 'db://pg', 'ACTIVE')"
            ),
            {"id": ds_db_id, "ws": ws_a},
        )


def build_dummy_lock_for_p01_test(run_id: str, ws_a: str, org_id: str) -> Any:
    """Build a minimal `RecursiveRunLockManifest` to test `ON CONFLICT DO NOTHING` (`P0-1`)."""
    from orcia_core.orchestration._run_lock_helpers import assemble_recursive_run_lock
    from orcia_core.orchestration.models import WorkflowAsCodeDefinition
    from orcia_core.permissions.models import WorkspaceEntity

    wf = WorkflowAsCodeDefinition(
        id="w",
        workspace_id=ws_a,
        uri="orcia://packs/alpha-pack/wf",
        title="W",
        description="d",
        version="1.0.0",
        criticality="STANDARD",
        execution_regime="INTERACTIVE_COACHING",
        tie_break_policy="ONTOLOGY_AXIOM_FIRST",
        mode="standard",
        adaptive_gate_policy="BALANCED",
        max_cost_usd=1.0,
        scalars={},
        datasources=(),
        rules=(),
        facts=(),
        steps=(),
        sha256="a" * 64,
    )
    return assemble_recursive_run_lock(
        run_id=run_id.removeprefix("run-"),
        workspace=WorkspaceEntity(id=ws_a, slug="ws-31-4-a", name="A", owner_org_unit_id=org_id),
        wf=wf,
        effective_workflow_sha256="b" * 64,
        applied_override_keys=(),
        kb_snapshot_hash="c" * 64,
        sorted_sources=(),
        sub_locks=(),
    )


__all__ = [
    "REPO_ROOT",
    "build_dummy_lock_for_p01_test",
    "build_slot_pack_zip",
    "pg18_url",
    "run_alembic_head",
    "seed_story_31_4_hardening_extras",
    "seed_story_31_4_topology",
]
