"""Story 29.2 (Layer 2 PG18) — Scoped PATCH /workspaces/{id} & CONFIDENTIAL_RESTRICTED isolation."""

from __future__ import annotations

import pytest
import sqlalchemy as sa
from httpx import ASGITransport, AsyncClient
from tests.integration.api._story_29_2_pg18_boot import (
    boot_real_app_pg18,
    setup_org_and_users_pg18,
)

from orcia_kernel.ids import new_uuid7_str


@pytest.mark.asyncio
async def test_story_29_2_patch_workspace_and_confidential_isolation_pg18(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Real PG18 Composition Root: TEAM_LEAD PATCH, isolation, promotions & CC sync."""
    async with (
        boot_real_app_pg18(monkeypatch) as (app, engine),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
    ):
        ctx = await setup_org_and_users_pg18(client)
        admin_hdrs = {"Authorization": f"Bearer {ctx['admin_tok']}"}
        lead_a_hdrs = {"Authorization": f"Bearer {ctx['lead_a_tok']}"}
        dev_a_hdrs = {"Authorization": f"Bearer {ctx['dev_a_tok']}"}
        lead_b_hdrs = {"Authorization": f"Bearer {ctx['lead_b_tok']}"}
        team_a_id = ctx["team_a_id"]
        lead_a_id = ctx["lead_a_id"]
        dev_a_id = ctx["dev_a_id"]

        # Lead A creates a STANDARD workspace in Team A
        r_ws = await client.post(
            "/api/v1/workspaces",
            headers=lead_a_hdrs,
            json={
                "name": "Espace Team A",
                "slug": "ws-team-a-292",
                "visibility_mode": "STANDARD",
                "lifecycle_phase": "BUILD",
                "owner_org_unit_id": team_a_id,
            },
        )
        assert r_ws.status_code == 201, r_ws.text
        ws_id = r_ws.json()["id"]

        # Cross-team Lead B & non-lead Dev A rejected with 403 ERR_SCOPE_ACCESS_DENIED
        for hdrs in (lead_b_hdrs, dev_a_hdrs):
            r_403 = await client.patch(
                f"/api/v1/workspaces/{ws_id}",
                headers=hdrs,
                json={"visibility_mode": "CONFIDENTIAL_RESTRICTED"},
            )
            assert r_403.status_code == 403
            assert r_403.json()["error_code"] == "ERR_SCOPE_ACCESS_DENIED"

        # Lead A transitions workspace to CONFIDENTIAL_RESTRICTED via PATCH
        r_patch = await client.patch(
            f"/api/v1/workspaces/{ws_id}",
            headers=lead_a_hdrs,
            json={"visibility_mode": "CONFIDENTIAL_RESTRICTED", "lifecycle_phase": "RUN"},
        )
        assert r_patch.status_code == 200, r_patch.text
        assert r_patch.json()["visibility_mode"] == "CONFIDENTIAL_RESTRICTED"
        assert r_patch.json()["lifecycle_phase"] == "RUN"

        # Direct SQL SELECT verification on workspaces, memberships & audit_ledger
        async with engine.connect() as conn:  # type: ignore[attr-defined]
            ws_row = (
                await conn.execute(
                    sa.text(
                        "SELECT visibility_mode, settings_jsonb "
                        "FROM workspaces WHERE id = CAST(:id AS uuid)"
                    ),
                    {"id": ws_id},
                )
            ).first()
            assert ws_row is not None
            assert ws_row[0] == "CONFIDENTIAL_RESTRICTED"
            assert ws_row[1]["lifecycle_phase"] == "RUN"
            mem_cnt = int(
                (
                    await conn.execute(
                        sa.text(
                            "SELECT COUNT(*) FROM workspace_memberships "
                            "WHERE workspace_id = CAST(:wid AS uuid) "
                            "AND user_id = CAST(:uid AS uuid)"
                        ),
                        {"wid": ws_id, "uid": lead_a_id},
                    )
                ).scalar()
                or 0
            )
            assert mem_cnt == 1
            audit_cnt = int(
                (
                    await conn.execute(
                        sa.text(
                            "SELECT COUNT(*) FROM audit_ledger "
                            "WHERE workspace_id = CAST(:wid AS uuid) "
                            "AND event_type = 'WORKSPACE_UPDATED'"
                        ),
                        {"wid": ws_id},
                    )
                ).scalar()
                or 0
            )
            assert audit_cnt >= 1

        # Same-team Dev A & cross-team Lead B are isolated from patched CONFIDENTIAL_RESTRICTED
        for bad_hdrs in (dev_a_hdrs, lead_b_hdrs):
            assert (
                await client.get(f"/api/v1/workspaces/{ws_id}/datasources", headers=bad_hdrs)
            ).status_code == 403
            assert (
                await client.get(f"/api/v1/workspaces/{ws_id}/five-tabs", headers=bad_hdrs)
            ).status_code == 403

        # Direct CONFIDENTIAL_RESTRICTED creation isolates non-member Admin too
        r_ws_conf = await client.post(
            "/api/v1/workspaces",
            headers=lead_a_hdrs,
            json={
                "name": "Espace Confidentiel Team A",
                "slug": "ws-conf-team-a-292",
                "visibility_mode": "CONFIDENTIAL_RESTRICTED",
                "lifecycle_phase": "BUILD",
                "owner_org_unit_id": team_a_id,
            },
        )
        assert r_ws_conf.status_code == 201, r_ws_conf.text
        ws_conf_id = r_ws_conf.json()["id"]
        for bad_hdrs in (dev_a_hdrs, admin_hdrs):
            assert (
                await client.get(f"/api/v1/workspaces/{ws_conf_id}/datasources", headers=bad_hdrs)
            ).status_code == 403
            assert (
                await client.get(f"/api/v1/workspaces/{ws_conf_id}/five-tabs", headers=bad_hdrs)
            ).status_code == 403

        # Lead A personal workspace cannot change visibility in place
        r_me = await client.get("/api/v1/workspaces", headers=lead_a_hdrs)
        assert r_me.status_code == 200
        priv_ws = next(w for w in r_me.json()["workspaces"] if w["is_personal"])
        r_priv_patch = await client.patch(
            f"/api/v1/workspaces/{priv_ws['id']}",
            headers=lead_a_hdrs,
            json={"visibility_mode": "STANDARD"},
        )
        assert r_priv_patch.status_code == 403
        assert r_priv_patch.json()["error_code"] == "ERR_PRIVATE_WORKSPACE_VISIBILITY_LOCKED"

        # POST /api/v1/workspaces with visibility_mode=PRIVATE_USER persists owner & isolation
        r_ws_priv = await client.post(
            "/api/v1/workspaces",
            headers=lead_a_hdrs,
            json={
                "name": "Espace Privé Créé 29.2",
                "slug": "ws-priv-292",
                "visibility_mode": "PRIVATE_USER",
                "lifecycle_phase": "BUILD",
                "owner_org_unit_id": team_a_id,
            },
        )
        assert r_ws_priv.status_code == 201, r_ws_priv.text
        ws_priv_id = r_ws_priv.json()["id"]
        assert r_ws_priv.json()["visibility_mode"] == "PRIVATE_USER"
        async with engine.connect() as conn:  # type: ignore[attr-defined]
            priv_row = (
                await conn.execute(
                    sa.text(
                        "SELECT visibility_mode, settings_jsonb "
                        "FROM workspaces WHERE id = CAST(:id AS uuid)"
                    ),
                    {"id": ws_priv_id},
                )
            ).first()
            assert priv_row is not None and priv_row[0] == "CONFIDENTIAL_RESTRICTED"
            assert priv_row[1]["ui_visibility_mode"] == "PRIVATE_USER"
            assert priv_row[1]["personal_owner_user_id"] == lead_a_id

        # Non-member Admin is denied on new PRIVATE_USER & CONFIDENTIAL_RESTRICTED routes
        for target_ws_id in (ws_conf_id, ws_priv_id):
            assert (
                await client.get(
                    f"/api/v1/workspaces/{target_ws_id}/dna-mechanisms", headers=admin_hdrs
                )
            ).status_code == 403
            assert (
                await client.get(
                    f"/api/v1/workspaces/{target_ws_id}/codegraph/tools", headers=admin_hdrs
                )
            ).status_code == 403
            assert (
                await client.post(
                    f"/api/v1/workspaces/{target_ws_id}/datasources/reconcile-staleness",
                    headers=admin_hdrs,
                )
            ).status_code == 403
        assert (
            await client.get(
                "/api/v1/control-center/overview",
                params={"scope_type": "WORKSPACE", "scope_id": ws_priv_id},
                headers=admin_hdrs,
            )
        ).status_code == 403

        # P1-A & P2-2: POST /ontology/promotions & Control Center sync PG18 membership + revocation
        r_con = await client.post(
            "/api/v1/ontology-rag/ontology/concepts",
            headers=lead_a_hdrs,
            json={
                "concept_key": "conf-pg18-term-292",
                "canonical_term": "Terme PG18 Confidentiel",
                "level": "3_WORKSPACE",
                "scope_id": ws_conf_id,
                "definition_text": "Terme confidentiel PG18",
            },
        )
        assert r_con.status_code == 200, r_con.text
        assert (
            await client.post(
                "/api/v1/ontology-rag/ontology/promotions",
                headers=dev_a_hdrs,
                json={"concept_key": "conf-pg18-term-292", "target_level": "3_TEAM"},
            )
        ).status_code == 403

        # Grant Dev A membership in PG18 & clear in-memory cache (cold worker simulation)
        async with engine.begin() as conn:  # type: ignore[attr-defined]
            await conn.execute(
                sa.text(
                    "INSERT INTO workspace_memberships "
                    "(id, workspace_id, user_id, role, access_mode) "
                    "VALUES (:id, CAST(:wid AS uuid), CAST(:uid AS uuid), "
                    "'CONTRIBUTOR', 'CONTRIBUTOR_ACTION_REQUIRED')"
                ),
                {"id": new_uuid7_str(), "wid": ws_conf_id, "uid": dev_a_id},
            )
        app.state.auth_service.evaluator.replace_memberships(())  # type: ignore[attr-defined]
        assert (
            await client.post(
                "/api/v1/ontology-rag/ontology/promotions",
                headers=dev_a_hdrs,
                json={"concept_key": "conf-pg18-term-292", "target_level": "3_TEAM"},
            )
        ).status_code == 200
        assert (
            await client.get(
                "/api/v1/control-center/overview",
                params={"scope_type": "WORKSPACE", "scope_id": ws_conf_id},
                headers=dev_a_hdrs,
            )
        ).status_code == 200

        # Revoke Dev A membership in PG18 -> immediate 403 despite warm evaluator
        async with engine.begin() as conn:  # type: ignore[attr-defined]
            await conn.execute(
                sa.text(
                    "DELETE FROM workspace_memberships "
                    "WHERE workspace_id = CAST(:wid AS uuid) "
                    "AND user_id = CAST(:uid AS uuid)"
                ),
                {"wid": ws_conf_id, "uid": dev_a_id},
            )
        assert (
            await client.post(
                "/api/v1/ontology-rag/ontology/promotions",
                headers=dev_a_hdrs,
                json={"concept_key": "conf-pg18-term-292", "target_level": "3_TEAM"},
            )
        ).status_code == 403
        assert (
            await client.get(
                "/api/v1/control-center/overview",
                params={"scope_type": "WORKSPACE", "scope_id": ws_conf_id},
                headers=dev_a_hdrs,
            )
        ).status_code == 403
