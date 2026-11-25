"""Story 29.2 (Layer 1a) — Unit tests for PATCH /api/v1/workspaces/{id} & isolation."""

from __future__ import annotations

import pytest
from httpx import ASGITransport, AsyncClient
from tests.unit.fakes.fake_embedding import FakeDeterministicEmbeddingAdapter

from orcia_api.dependencies import get_embedding_port, require_rag_available
from orcia_api.main import create_app
from orcia_core.ontology import can_read_ontology_item, can_write_ontology_level
from orcia_core.permissions.models import (
    OrgUnitNode,
    UserIdentity,
    WorkspaceEntity,
    WorkspaceMembershipEntity,
)


def _make_local_app(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setenv("ORCIA_ENV_FILE", "/nonexistent/.env")
    monkeypatch.delenv("DATABASE_URL", raising=False)
    monkeypatch.delenv("ORCIA_ENABLE_PG_SESSION_MAKER", raising=False)
    monkeypatch.setenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", "1")
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    monkeypatch.setenv("ORCIA_ENV", "local")
    return create_app()


@pytest.mark.asyncio
async def test_patch_workspace_scoped_rbac_self_lockout_and_private_lock(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """TEAM_LEAD/BU_DIRECTOR/ADMIN can PATCH team spaces; OBSERVER/cross-team/PRIVATE locked."""
    app = _make_local_app(monkeypatch)
    auth_svc = app.state.auth_service
    root_id = "0192c4e0-0000-7000-8000-000000000001"
    bu_a_id = "0195f292-0000-7000-8000-000000000010"
    team_a_id = "0195f292-0000-7000-8000-000000000011"
    team_b_id = "0195f292-0000-7000-8000-000000000012"
    ws_team_a_id = "0195f292-0000-7000-8000-000000000201"
    ws_priv_id = "0195f292-0000-7000-8000-000000000202"

    def _mk_user(uid: str, email: str, name: str, role: str, ou: str) -> UserIdentity:
        return UserIdentity(
            id=uid,
            email=email,
            display_name=name,
            auth_mode="LOCAL",
            human_profile_archetype="TECH_LEAD",
            platform_role=role,  # type: ignore[arg-type]
            primary_org_unit_id=ou,
            roles=(role,),
        )

    lead_a = _mk_user(
        "0195f292-0000-7000-8000-000000000301",
        "lead.a@orcia.test",
        "Lead A",
        "TEAM_LEAD",
        team_a_id,
    )  # noqa: E501
    teammate_a = _mk_user(
        "0195f292-0000-7000-8000-000000000302",
        "dev.a@orcia.test",
        "Dev A",
        "CONTRIBUTOR",
        team_a_id,
    )  # noqa: E501
    lead_b = _mk_user(
        "0195f292-0000-7000-8000-000000000303",
        "lead.b@orcia.test",
        "Lead B",
        "TEAM_LEAD",
        team_b_id,
    )  # noqa: E501
    bu_dir = _mk_user(
        "0195f292-0000-7000-8000-000000000304", "dir.a@orcia.test", "Dir A", "BU_DIRECTOR", bu_a_id
    )  # noqa: E501
    for u in (lead_a, teammate_a, lead_b, bu_dir):
        auth_svc.register_user(u)

    auth_svc.evaluator.replace_org_units(
        (
            OrgUnitNode(id=root_id, slug="global", name="Global", unit_type="ENTERPRISE"),
            OrgUnitNode(
                id=bu_a_id,
                slug="bu-a",
                name="BU A",
                unit_type="BU",
                parent_id=root_id,
                lead_user_ids=(bu_dir.id,),
            ),  # noqa: E501
            OrgUnitNode(
                id=team_a_id,
                slug="team-a",
                name="Team A",
                unit_type="TEAM",
                parent_id=bu_a_id,
                lead_user_ids=(lead_a.id,),
                member_user_ids=(teammate_a.id,),
            ),  # noqa: E501
            OrgUnitNode(
                id=team_b_id,
                slug="team-b",
                name="Team B",
                unit_type="TEAM",
                parent_id=root_id,
                lead_user_ids=(lead_b.id,),
            ),  # noqa: E501
        )
    )
    auth_svc.evaluator.upsert_workspace(
        WorkspaceEntity(
            id=ws_team_a_id,
            slug="ws-team-a",
            name="Workspace Team A",
            owner_org_unit_id=team_a_id,
            visibility_mode="STANDARD",
        )
    )
    auth_svc.evaluator.upsert_workspace(
        WorkspaceEntity(
            id=ws_priv_id,
            slug=f"personal-{lead_a.id}",
            name="Espace personnel — Lead A",
            owner_org_unit_id=team_a_id,
            visibility_mode="CONFIDENTIAL_RESTRICTED",
            personal_owner_user_id=lead_a.id,
            ui_visibility_mode="PRIVATE_USER",
        )
    )

    lead_a_tok = auth_svc._issue_for_user(lead_a, "LOCAL", None).access_token
    dev_a_tok = auth_svc._issue_for_user(teammate_a, "LOCAL", None).access_token
    lead_b_tok = auth_svc._issue_for_user(lead_b, "LOCAL", None).access_token
    bu_dir_tok = auth_svc._issue_for_user(bu_dir, "LOCAL", None).access_token

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        # 1. Cross-team TEAM_LEAD & non-lead CONTRIBUTOR rejected with 403 ERR_SCOPE_ACCESS_DENIED
        for bad_tok in (lead_b_tok, dev_a_tok):
            r_403 = await client.patch(
                f"/api/v1/workspaces/{ws_team_a_id}",
                headers={"Authorization": f"Bearer {bad_tok}"},
                json={"visibility_mode": "CONFIDENTIAL_RESTRICTED"},
            )
            assert r_403.status_code == 403
            assert r_403.json()["error_code"] == "ERR_SCOPE_ACCESS_DENIED"

        # 2. READ_ONLY_OBSERVER header rejected with 403 ERR_OBSERVER_MODE_READ_ONLY
        r_obs = await client.patch(
            f"/api/v1/workspaces/{ws_team_a_id}",
            headers={
                "Authorization": f"Bearer {lead_a_tok}",
                "X-Orcia-Access-Mode": "READ_ONLY_OBSERVER",
            },
            json={"lifecycle_phase": "RUN"},
        )
        assert r_obs.status_code == 403
        assert r_obs.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"

        # 3. Subtree BU_DIRECTOR allowed on STANDARD team workspace
        r_bu = await client.patch(
            f"/api/v1/workspaces/{ws_team_a_id}",
            headers={"Authorization": f"Bearer {bu_dir_tok}"},
            json={"lifecycle_phase": "MIGRATION"},
        )
        assert r_bu.status_code == 200
        assert r_bu.json()["lifecycle_phase"] == "MIGRATION"

        # 4. In-place visibility transition on PRIVATE_USER / personal-* rejected with 403
        r_priv = await client.patch(
            f"/api/v1/workspaces/{ws_priv_id}",
            headers={"Authorization": f"Bearer {lead_a_tok}"},
            json={"visibility_mode": "STANDARD"},
        )
        assert r_priv.status_code == 403
        assert r_priv.json()["error_code"] == "ERR_PRIVATE_WORKSPACE_VISIBILITY_LOCKED"

        # 5. Owning TEAM_LEAD sets CONFIDENTIAL_RESTRICTED + self-lockout guard
        r_conf = await client.patch(
            f"/api/v1/workspaces/{ws_team_a_id}",
            headers={"Authorization": f"Bearer {lead_a_tok}"},
            json={"visibility_mode": "CONFIDENTIAL_RESTRICTED"},
        )
        assert r_conf.status_code == 200
        assert r_conf.json()["visibility_mode"] == "CONFIDENTIAL_RESTRICTED"
        assert auth_svc.evaluator.resolve_workspace_access(lead_a, ws_team_a_id) is not None
        assert auth_svc.evaluator.resolve_workspace_access(teammate_a, ws_team_a_id) is None
        assert auth_svc.evaluator.resolve_workspace_access(bu_dir, ws_team_a_id) is None


def test_ontology_3_workspace_confidential_and_private_isolation() -> None:
    """Ontology 3_WORKSPACE / 4_WORKSPACE blocks non-member PLATFORM_ADMIN & teammates."""
    team = OrgUnitNode(
        id="team-onto",
        slug="team-onto",
        name="Team Onto",
        unit_type="TEAM",
        lead_user_ids=("lead-1",),
        member_user_ids=("dev-1",),
    )  # noqa: E501
    ws_conf = WorkspaceEntity(
        id="ws-conf",
        slug="ws-conf",
        name="Conf",
        owner_org_unit_id="team-onto",
        visibility_mode="CONFIDENTIAL_RESTRICTED",
    )  # noqa: E501
    ws_priv = WorkspaceEntity(
        id="ws-priv",
        slug="personal-lead-1",
        name="Personal",
        owner_org_unit_id="team-onto",
        visibility_mode="CONFIDENTIAL_RESTRICTED",
        personal_owner_user_id="lead-1",
        ui_visibility_mode="PRIVATE_USER",
    )  # noqa: E501
    admin = UserIdentity(
        id="admin-1",
        email="admin@orcia.test",
        display_name="Admin",
        auth_mode="LOCAL",
        human_profile_archetype="SECOPS",
        platform_role="PLATFORM_ADMIN",
        primary_org_unit_id="team-onto",
        roles=("PLATFORM_ADMIN",),
    )  # noqa: E501
    dev = UserIdentity(
        id="dev-1",
        email="dev@orcia.test",
        display_name="Dev",
        auth_mode="LOCAL",
        human_profile_archetype="DEVELOPER",
        platform_role="CONTRIBUTOR",
        primary_org_unit_id="team-onto",
        roles=("CONTRIBUTOR",),
    )  # noqa: E501
    lead = UserIdentity(
        id="lead-1",
        email="lead@orcia.test",
        display_name="Lead",
        auth_mode="LOCAL",
        human_profile_archetype="TECH_LEAD",
        platform_role="TEAM_LEAD",
        primary_org_unit_id="team-onto",
        roles=("TEAM_LEAD",),
    )  # noqa: E501
    memberships = (
        WorkspaceMembershipEntity(
            id="mem-1",
            workspace_id="ws-conf",
            role="TEAM_LEAD",
            access_mode="CONTRIBUTOR_ACTION_REQUIRED",
            user_id="lead-1",
        ),
    )  # noqa: E501
    for ws_id in ("ws-conf", "ws-priv"):
        args = ("3_WORKSPACE", ws_id, (team,), (ws_conf, ws_priv), memberships)
        for u, expected in ((admin, False), (dev, False), (lead, True)):
            assert can_read_ontology_item(u, *args) is expected
            assert can_write_ontology_level(u, *args) is expected


@pytest.mark.asyncio
async def test_rag_search_and_datasources_block_non_member_confidential_access(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """POST /rag/search and datasources reject non-member PLATFORM_ADMIN & teammates."""
    app = _make_local_app(monkeypatch)
    fake_emb = FakeDeterministicEmbeddingAdapter()
    app.state.embedding_port = fake_emb
    app.dependency_overrides[get_embedding_port] = lambda: fake_emb
    app.dependency_overrides[require_rag_available] = lambda: fake_emb
    ws_conf_id = "0192c4e0-0000-7000-8000-000000000203"

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        for persona in ("karim", "nadia", "claire"):
            r_rag = await client.post(
                f"/api/v1/ontology-rag/rag/search?persona_key={persona}",
                json={"workspace_id": ws_conf_id, "query_text": "confidential secret", "top_k": 3},
            )
            assert r_rag.status_code == 403
            assert r_rag.json()["error_code"] == "ERR_SCOPE_ACCESS_DENIED"

            r_ds = await client.get(
                f"/api/v1/workspaces/{ws_conf_id}/datasources",
                params={"persona": persona},
            )
            assert r_ds.status_code == 403
            assert r_ds.json()["error_code"] == "ERR_SCOPE_ACCESS_DENIED"

        # Explicit member (marc) succeeds on both
        r_rag_ok = await client.post(
            "/api/v1/ontology-rag/rag/search?persona_key=marc",
            json={"workspace_id": ws_conf_id, "query_text": "confidential", "top_k": 3},
        )
        assert r_rag_ok.status_code == 200
