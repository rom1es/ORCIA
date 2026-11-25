"""Story 29.2 (Layer 1a) — Unit tests for P0 backend security hardening."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock
from uuid import UUID

import pytest
from starlette.requests import Request

from orcia_api.main import create_app
from orcia_api.routers._bootstrap_evaluator_sync import sync_setup_snapshot_to_evaluator
from orcia_api.routers._ontology_promotions_helpers import compute_writable_options
from orcia_core.bootstrap import FirstPlatformAdminRecord, PlatformSetupSnapshotRecord
from orcia_core.bootstrap._internal.sql_platform_setup_relational_sync import (
    sync_relational_tables_on_postgres18,
)
from orcia_core.ontology._promotion_permissions import (
    assert_can_review_promotion,
    can_review_promotion_target,
)
from orcia_core.permissions.errors import ScopeAccessDeniedError
from orcia_core.permissions.models import (
    OrgUnitNode,
    UserIdentity,
    WorkspaceEntity,
    WorkspaceMembershipEntity,
)
from orcia_core.rag._internal.sql_federated_search import load_federated_search_candidates_pg18
from orcia_core.rag.two_speed_search import (
    FederatedSearchCandidate,
    TwoSpeedFederatedSearchService,
)


def _user(uid: str, role: str, ou: str = "ou-1", *, roles: tuple[str, ...] = ()) -> UserIdentity:
    return UserIdentity(
        id=uid,
        email=f"{uid}@orcia.test",
        display_name=uid,
        auth_mode="LOCAL",
        human_profile_archetype="TECH_LEAD",
        platform_role=role,  # type: ignore[arg-type]
        primary_org_unit_id=ou,
        roles=roles or (role,),
    )


@pytest.mark.asyncio
async def test_setup_sync_and_bootstrap_evaluator_never_inject_admin_into_confidential() -> None:
    """P0-1: setup relational sync & evaluator sync skip admin auto-membership on restricted WS."""
    ws_conf_id = "0195f292-0000-7000-8000-000000001101"
    ws_priv_id = "0195f292-0000-7000-8000-000000001102"
    ws_std_id = "0195f292-0000-7000-8000-000000001103"
    admin_id = "0195f292-0000-7000-8000-000000001201"
    other_owner_id = "0195f292-0000-7000-8000-000000001202"

    executed_inserts: list[tuple[str, dict[str, Any]]] = []

    async def _fake_exec(stmt: Any, params: dict[str, Any] | None = None) -> MagicMock:
        sql = str(stmt)
        res = MagicMock()
        if "INSERT INTO workspace_memberships" in sql:
            executed_inserts.append((sql, dict(params or {})))
        if "SELECT id FROM users" in sql:
            res.fetchall.return_value = [(UUID(admin_id),)]
        elif "RETURNING id" in sql and "INSERT INTO workspaces" in sql:
            res.first.return_value = (UUID(str((params or {})["id"])),)
        elif "RETURNING id" in sql:
            res.first.return_value = (UUID("0192c4e0-0000-7000-8000-000000000101"),)
        else:
            res.first.return_value = None
            res.fetchall.return_value = []
        return res

    conn = AsyncMock()
    conn.execute.side_effect = _fake_exec
    await sync_relational_tables_on_postgres18(
        conn,
        org_units=[],
        workspaces=[
            {
                "workspaceId": ws_conf_id,
                "name": "Conf WS",
                "slug": "conf-ws",
                "visibilityMode": "CONFIDENTIAL_RESTRICTED",
            },
            {
                "workspaceId": ws_std_id,
                "name": "Std WS",
                "slug": "std-ws",
                "visibilityMode": "STANDARD",
            },
        ],
        llm_tiers=[],
    )
    inserted_ws_ids = {str(p["ws_id"]) for _, p in executed_inserts}
    assert ws_std_id in inserted_ws_ids
    assert ws_conf_id not in inserted_ws_ids

    app = create_app()
    auth_svc = app.state.auth_service
    admin_user = _user(admin_id, "PLATFORM_ADMIN")
    auth_svc.register_user(admin_user)
    req = Request({"type": "http", "app": app, "headers": [], "path": "/"})
    snap = PlatformSetupSnapshotRecord(
        first_admin_initialized=True,
        org_units=[{"id": "ou-1", "slug": "ou-1", "name": "OU 1", "level": "TEAM"}],
        workspaces=[
            {
                "workspaceId": ws_conf_id,
                "name": "Conf Snap WS",
                "slug": "conf-snap-ws",
                "visibilityMode": "CONFIDENTIAL_RESTRICTED",
            },
            {
                "workspaceId": ws_priv_id,
                "name": "Priv Snap WS",
                "slug": "priv-snap-ws",
                "visibilityMode": "PRIVATE_USER",
                "personalOwnerUserId": other_owner_id,
            },
        ],
    )
    first_admin = FirstPlatformAdminRecord(
        user_id=admin_id,
        email=admin_user.email,
        display_name="Admin",
        platform_role="PLATFORM_ADMIN",
        orcia_env="local",
        sql_lock_statement="SELECT 1",
    )
    sync_setup_snapshot_to_evaluator(req, snap, first_admin)
    assert auth_svc.evaluator.resolve_workspace_access(admin_user, ws_conf_id) is None
    assert auth_svc.evaluator.resolve_workspace_access(admin_user, ws_priv_id) is None


@pytest.mark.asyncio
async def test_federated_search_sql_and_two_speed_service_restrict_confidential() -> None:
    """P0-2: SQL enforces relational visibility_mode & TwoSpeed service checks restricted WS."""
    executed: list[str] = []

    class _FakeConn:
        async def execute(self, stmt: Any, params: dict[str, Any] | None = None) -> MagicMock:
            sql = str(stmt)
            executed.append(sql)
            r = MagicMock()
            if "FROM pg_tables" in sql:
                r.fetchall.return_value = [
                    ("catalog_items",),
                    ("workspaces",),
                    ("workspace_memberships",),
                ]
            else:
                r.fetchall.return_value = []
            return r

    await load_federated_search_candidates_pg18(
        _FakeConn(),  # type: ignore[arg-type]
        user_id="admin-1",
        user_role="PLATFORM_ADMIN",
    )
    cat_sql = next(s for s in executed if "FROM catalog_items" in s)
    ws_sql = next(s for s in executed if "FROM workspaces" in s)
    assert "ci_ws.visibility_mode = 'STANDARD'" in cat_sql
    assert "w.visibility_mode = 'STANDARD'" in ws_sql
    assert (
        "COALESCE(w.settings_jsonb->>'ui_visibility_mode', w.visibility_mode) = 'STANDARD'"
        not in ws_sql
    )

    svc = TwoSpeedFederatedSearchService(
        candidates=(
            FederatedSearchCandidate(
                item_id="conf-item",
                family="FOLDERS_DISCUSSIONS",
                title="Secret Merger Plan",
                snippet="Confidential",
                workspace_id="ws-conf",
                screen_route="/spaces",
                deep_link_uri="/workspaces/ws-conf",
                visibility_mode="CONFIDENTIAL_RESTRICTED",
            ),
        )
    )
    denied = svc.execute_search(
        query="Merger",
        scope="ALL_WORKSPACES",
        user_id="admin-1",
        user_role="PLATFORM_ADMIN",
        authorized_workspace_ids=(),
        restricted_workspace_ids=("ws-conf",),
        include_speed2=False,
    )
    assert denied.hits == ()
    allowed = svc.execute_search(
        query="Merger",
        scope="ALL_WORKSPACES",
        user_id="member-1",
        user_role="CONTRIBUTOR",
        authorized_workspace_ids=("ws-conf",),
        restricted_workspace_ids=("ws-conf",),
        include_speed2=False,
    )
    assert [h.item_id for h in allowed.hits] == ["conf-item"]


def test_promotion_permissions_and_writable_options_respect_confidential_membership() -> None:
    """P0-4: non-member PLATFORM_ADMIN cannot decide confidential promotions; members can write."""
    ou = OrgUnitNode(id="team-1", slug="team-1", name="Team 1", unit_type="TEAM")
    ws_conf = WorkspaceEntity(
        id="ws-conf",
        slug="ws-conf",
        name="Conf",
        owner_org_unit_id="team-1",
        visibility_mode="CONFIDENTIAL_RESTRICTED",
    )
    admin = _user("admin-1", "PLATFORM_ADMIN", "team-1")
    member = _user("member-1", "CONTRIBUTOR", "team-1")
    memberships = (
        WorkspaceMembershipEntity(
            id="m-1",
            workspace_id="ws-conf",
            role="CONTRIBUTOR",
            access_mode="CONTRIBUTOR_ACTION_REQUIRED",
            user_id="member-1",
        ),
    )
    assert not can_review_promotion_target(
        admin, "4_WORKSPACE", "ws-conf", (ou,), (ws_conf,), memberships
    )
    assert not can_review_promotion_target(
        admin, "3_TEAM", "team-1", (ou,), (ws_conf,), memberships, source_scope_id="ws-conf"
    )
    with pytest.raises(ScopeAccessDeniedError):
        assert_can_review_promotion(admin, "4_WORKSPACE", "ws-conf", (ou,), (ws_conf,), memberships)
    _, opts = compute_writable_options(member, (ou,), (ws_conf,), memberships)
    assert any(o.scope_id == "ws-conf" and o.level == "4_WORKSPACE" for o in opts)
