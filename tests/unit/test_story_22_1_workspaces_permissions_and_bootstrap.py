"""Story 22.1 (Couche 1a) — Unit tests for UUIDv7 workspaces, PLATFORM_ADMIN access & PG sync."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from starlette.requests import Request

from orcia_api.dependencies.portal_and_assistant import get_accostage_service
from orcia_api.main import create_app
from orcia_core.bootstrap._internal.sql_platform_setup_relational_sync import (
    sync_relational_tables_on_postgres18,
)
from orcia_core.bootstrap._internal.sql_workspaces import (
    create_workspace_on_postgres18,
    resolve_exact_workspace_slug,
)
from orcia_core.bootstrap.errors import InvalidBootstrapTokenError
from orcia_core.permissions import (
    MatrixPermissionEvaluator,
    OrgUnitNode,
    UserIdentity,
    WorkspaceEntity,
)
from orcia_core.permissions.errors import ValidationDomainError

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_matrix_evaluator_platform_admin_standard_vs_confidential_vs_observer() -> None:
    """PLATFORM_ADMIN -> CONTRIBUTOR on STANDARD, None on CONFIDENTIAL_RESTRICTED."""
    root = OrgUnitNode(
        id="0192c4e0-0000-7000-8000-000000000001",
        slug="global",
        name="Global",
        unit_type="GLOBAL",
    )
    team = OrgUnitNode(
        id="0192c4e0-0000-7000-8000-000000000102",
        slug="team-compta",
        name="Équipe Compta",
        unit_type="TEAM",
        parent_id=root.id,
    )
    ws_standard = WorkspaceEntity(
        id="0195f000-0000-7000-8000-000000000001",
        slug="espace-e2e-compta",
        name="Espace E2E Comptabilité",
        owner_org_unit_id=team.id,
        visibility_mode="STANDARD",
    )
    ws_confidential = WorkspaceEntity(
        id="0195f000-0000-7000-8000-000000000002",
        slug="espace-confidentiel",
        name="Espace Confidentiel",
        owner_org_unit_id=team.id,
        visibility_mode="CONFIDENTIAL_RESTRICTED",
    )
    evaluator = MatrixPermissionEvaluator(
        org_units=[root, team],
        workspaces=[ws_standard, ws_confidential],
        memberships=[],
    )

    admin = UserIdentity(
        id="0195f000-0000-7000-8000-000000000900",
        email="admin@orcia.fr",
        display_name="Admin Plateforme",
        auth_mode="LOCAL",
        human_profile_archetype="TECH_LEAD",
        platform_role="PLATFORM_ADMIN",
        primary_org_unit_id=root.id,
        roles=("PLATFORM_ADMIN",),
    )
    observer = UserIdentity(
        id="0195f000-0000-7000-8000-000000000901",
        email="observer@orcia.fr",
        display_name="Observateur",
        auth_mode="LOCAL",
        human_profile_archetype="OBSERVER",
        platform_role="OBSERVER",
        primary_org_unit_id=team.id,
        roles=("OBSERVER",),
    )

    std_access = evaluator.resolve_workspace_access(admin, ws_standard.id)
    assert std_access is not None
    assert std_access.effective_role == "PLATFORM_ADMIN"
    assert std_access.access_mode == "CONTRIBUTOR_ACTION_REQUIRED"
    assert std_access.access_origin == "GLOBAL_ADMIN"
    assert std_access.finops_visible is True

    conf_access = evaluator.resolve_workspace_access(admin, ws_confidential.id)
    assert conf_access is None

    obs_access = evaluator.resolve_workspace_access(observer, ws_standard.id)
    assert obs_access is not None
    assert obs_access.effective_role == "OBSERVER"
    assert obs_access.access_mode == "READ_ONLY_OBSERVER"


@pytest.mark.asyncio
async def test_sql_platform_setup_relational_sync_preserves_exact_slug() -> None:
    """sync_relational_tables_on_postgres18 must preserve exact ws.slug (`espace-e2e-compta`)."""
    executed_calls: list[tuple[str, dict[str, object] | None]] = []
    ws_uuid = UUID("0195f000-0000-7000-8000-000000000011")

    async def _fake_execute(stmt: object, params: dict[str, object] | None = None) -> MagicMock:
        sql_text = str(stmt)
        executed_calls.append((sql_text, params))
        res = MagicMock()
        if "SELECT id FROM org_units WHERE parent_id IS NULL" in sql_text:
            res.first.return_value = (UUID("0192c4e0-0000-7000-8000-000000000001"),)
        elif "INSERT INTO workspaces" in sql_text:
            res.first.return_value = (ws_uuid,)
        elif "SELECT id FROM users" in sql_text:
            res.fetchall.return_value = [(UUID("0195f000-0000-7000-8000-000000000900"),)]
        else:
            res.first.return_value = None
            res.fetchall.return_value = []
        return res

    conn = AsyncMock()
    conn.execute.side_effect = _fake_execute

    await sync_relational_tables_on_postgres18(
        conn,
        org_units=[],
        workspaces=[
            {
                "workspaceId": str(ws_uuid),
                "name": "Espace E2E Comptabilité",
                "slug": "espace-e2e-compta",
                "visibilityMode": "STANDARD",
                "lifecyclePhase": "BUILD",
            }
        ],
        llm_tiers=[],
    )

    ws_inserts = [
        params
        for sql_text, params in executed_calls
        if "INSERT INTO workspaces" in sql_text and params is not None
    ]
    assert len(ws_inserts) == 1
    assert ws_inserts[0]["id"] == ws_uuid
    assert ws_inserts[0]["slug"] == "espace-e2e-compta"
    assert ws_inserts[0]["name"] == "Espace E2E Comptabilité"


def test_get_accostage_service_reads_env_and_refuses_default_secret_outside_local(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """get_accostage_service reads ORCIA_ENV/ORCIA_BOOTSTRAP_TOKEN & refuses default in prod."""
    monkeypatch.setenv("ORCIA_ENV", "production")
    monkeypatch.delenv("ORCIA_BOOTSTRAP_TOKEN", raising=False)
    app_prod = create_app()
    req_prod = Request({"type": "http", "app": app_prod, "headers": [], "path": "/"})
    svc_prod = get_accostage_service(req_prod)
    assert svc_prod.orcia_env == "production"
    assert svc_prod.expected_bootstrap_token is None
    with pytest.raises(InvalidBootstrapTokenError):
        svc_prod._verify_bootstrap_token("orcia-day0-bootstrap-token", instance="/api/v1/bootstrap")

    monkeypatch.setenv("ORCIA_ENV", "staging")
    monkeypatch.setenv("ORCIA_BOOTSTRAP_TOKEN", "custom-staging-secret-2026")
    app_staging = create_app()
    req_staging = Request({"type": "http", "app": app_staging, "headers": [], "path": "/"})
    svc_staging = get_accostage_service(req_staging)
    assert svc_staging.orcia_env == "staging"
    assert svc_staging.expected_bootstrap_token == "custom-staging-secret-2026"
    verified_env = svc_staging._verify_bootstrap_token(
        "custom-staging-secret-2026", instance="/api/v1/bootstrap"
    )
    assert verified_env == "staging"


def test_no_orcia_disable_pg_bootstrap_sync_in_packages_or_apps() -> None:
    """ORCIA_DISABLE_PG_BOOTSTRAP_SYNC must be completely purged from packages/ and apps/."""
    offenders: list[str] = []
    for root_name in ("packages", "apps"):
        root_dir = REPO_ROOT / root_name
        for file_path in root_dir.rglob("*"):
            if not file_path.is_file():
                continue
            rel = file_path.relative_to(REPO_ROOT).as_posix()
            if (
                "node_modules/" in rel
                or "/dist/" in rel
                or "/__pycache__/" in rel
                or "/src/generated/" in rel
                or file_path.suffix not in {".py", ".ts", ".tsx"}
            ):
                continue
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            if "ORCIA_DISABLE_PG_BOOTSTRAP_SYNC" in content:
                offenders.append(rel)
    assert offenders == [], f"Obsolete bypass flag found in: {offenders}"


def test_resolve_exact_workspace_slug_preserves_and_validates() -> None:
    """resolve_exact_workspace_slug preserves valid slug, derives fallback, and rejects bad."""
    assert resolve_exact_workspace_slug("espace-e2e-compta", "Ignored") == "espace-e2e-compta"
    assert (
        resolve_exact_workspace_slug(None, "Espace Comptabilité 2026") == "espace-comptabilit-2026"
    )
    with pytest.raises(ValidationDomainError):
        resolve_exact_workspace_slug("INVALID SLUG!", "Name")
    with pytest.raises(ValidationDomainError):
        resolve_exact_workspace_slug(None, "a")


@pytest.mark.asyncio
async def test_create_workspace_on_postgres18_updates_snapshot_and_validates() -> None:
    """create_workspace_on_postgres18 validates name/slug and updates platform_settings JSONB."""
    executed_sql: list[str] = []
    ws_id_holder: list[UUID] = []

    class _FakeBeginCtx:
        def __init__(self, conn: AsyncMock) -> None:
            self._conn = conn

        async def __aenter__(self) -> AsyncMock:
            return self._conn

        async def __aexit__(self, *args: object) -> None:
            return None

    async def _fake_exec(stmt: object, params: dict[str, object] | None = None) -> MagicMock:
        sql_text = str(stmt)
        executed_sql.append(sql_text)
        res = MagicMock()
        if "SELECT id FROM workspaces WHERE slug" in sql_text:
            res.first.return_value = None
        elif "SELECT id FROM org_units WHERE parent_id IS NULL" in sql_text:
            res.first.return_value = (UUID("0192c4e0-0000-7000-8000-000000000001"),)
        elif "SELECT id, name FROM org_units WHERE slug" in sql_text:
            res.first.return_value = (UUID("0192c4e0-0000-7000-8000-000000000102"), "Équipe Compta")
        elif "INSERT INTO workspaces" in sql_text and params is not None:
            ws_uuid = params["id"]
            assert isinstance(ws_uuid, UUID)
            ws_id_holder.append(ws_uuid)
            res.first.return_value = (ws_uuid,)
        elif "SELECT id, platform_role FROM users" in sql_text:
            res.first.return_value = (
                UUID("0195f000-0000-7000-8000-000000000900"),
                "PLATFORM_ADMIN",
            )
        elif "SELECT id FROM users" in sql_text:
            res.fetchall.return_value = [(UUID("0195f000-0000-7000-8000-000000000900"),)]
        elif "SELECT value_jsonb FROM platform_settings" in sql_text:
            res.first.return_value = ('{"workspaces": []}',)
        else:
            res.first.return_value = None
            res.fetchall.return_value = []
        return res

    fake_conn = AsyncMock()
    fake_conn.execute.side_effect = _fake_exec
    fake_engine = MagicMock()
    fake_engine.begin.return_value = _FakeBeginCtx(fake_conn)

    rec = await create_workspace_on_postgres18(
        fake_engine,
        name="Espace E2E Comptabilité",
        slug="espace-e2e-compta",
        visibility_mode="STANDARD",
        lifecycle_phase="INVALID_FALLBACK",
        owner_org_unit_id="team-compta",
        creator_user_id="0195f000-0000-7000-8000-000000000900",
    )
    assert rec.slug == "espace-e2e-compta"
    assert rec.lifecycle_phase == "BUILD"
    assert any("UPDATE platform_settings" in s for s in executed_sql)

    with pytest.raises(ValidationDomainError):
        await create_workspace_on_postgres18(fake_engine, name="   ")

    # Duplicate slug check
    async def _dup_exec(stmt: object, params: dict[str, object] | None = None) -> MagicMock:
        res = MagicMock()
        if "SELECT id FROM workspaces WHERE slug" in str(stmt):
            res.first.return_value = (UUID("0195f000-0000-7000-8000-000000000011"),)
        return res

    fake_conn.execute.side_effect = _dup_exec
    with pytest.raises(ValidationDomainError):
        await create_workspace_on_postgres18(fake_engine, name="Dup", slug="espace-e2e-compta")
