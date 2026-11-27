"""Layer 2 PG18 + SeaweedFS S3 RBAC, Publish Cleanup & Rich Round-Trip (`Story 31.5`)."""

from __future__ import annotations

import io
import zipfile
from uuid import UUID

import pytest
import sqlalchemy as sa
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine
from tests.integration._shared_topology_fixture import SharedIntegrationTopology
from tests.integration._story_31_4_pack_fixture import seed_story_31_4_topology
from tests.integration._story_31_5_fixture import (
    REPO_ROOT,
    seed_story_31_5_entities,
)
from tests.integration._story_31_5_fixture_extra import issue_tok_hdr, seed_extra_315_fixtures
from uuid_utils import uuid7


@pytest.mark.asyncio
async def test_story_31_5_rbac_publish_cleanup_and_rich_roundtrip(
    isolated_worker_pg18_env: SharedIntegrationTopology,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify publish cleanup, cross-tenant RBAC, observer export & VSM/HELP/MCP round-trip."""
    pg_url = isolated_worker_pg18_env.async_database_url
    monkeypatch.setenv("S3_ENDPOINT_URL", isolated_worker_pg18_env.s3_endpoint_url)
    monkeypatch.setenv("ORCIA_ENV_FILE", str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"))

    org_id, ws_a, ws_b, admin_id = str(uuid7()), str(uuid7()), str(uuid7()), str(uuid7())
    ds_a_id, ds_b_id, ec_id = str(uuid7()), str(uuid7()), str(uuid7())
    eng = create_async_engine(pg_url)
    await seed_story_31_4_topology(
        eng,
        org_id=org_id,
        ws_a=ws_a,
        ws_b=ws_b,
        admin_id=admin_id,
        ds_a_id=ds_a_id,
        ds_b_id=ds_b_id,
        ec_id=ec_id,
    )
    eids = await seed_story_31_5_entities(eng, org_id=org_id, ws_a=ws_a, ds_a_id=ds_a_id)
    ex = await seed_extra_315_fixtures(
        eng, org_id=org_id, ws_a=ws_a, ws_b=ws_b, ds_a_id=ds_a_id, eids=eids
    )

    from orcia_api.main import create_app

    app = create_app()
    assert app.dependency_overrides == {}
    try:
        async with (
            app.router.lifespan_context(app),
            AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
        ):
            adm_h = issue_tok_hdr(
                app, uid=admin_id, email="admin314@orcia.test", role="PLATFORM_ADMIN", org_id=org_id
            )
            wsb_h = issue_tok_hdr(
                app, uid=ex["wsb_uid"], email="wsb315@orcia.test", role="CONTRIBUTOR", org_id=ws_b
            )
            obs_h = issue_tok_hdr(
                app, uid=ex["obs_uid"], email="obs315@orcia.test", role="OBSERVER", org_id=org_id
            )

            # 1. Publish clears pack_draft_memberships -> entity no longer held hostage
            d1 = (
                await client.post(
                    "/api/v1/packs/composer",
                    headers=adm_h,
                    json={
                        "slug": "pub-clean-315",
                        "name": "Pub Clean",
                        "scope_type": "WORKSPACE",
                        "scope_id": ws_a,
                    },
                )
            ).json()["bundle_id"]
            r_m1 = await client.put(
                f"/api/v1/packs/composer/{d1}/members",
                headers=adm_h,
                json={"members": [{"entity_type": "AGENT", "entity_id": "ag-free-315"}]},
            )
            assert r_m1.status_code == 200
            pub = await client.post(f"/api/v1/packs/composer/{d1}/publish", headers=adm_h)
            assert pub.status_code == 200, pub.text
            assert pub.json()["status"] == "PUBLISHED"
            async with eng.connect() as conn:
                cnt = (
                    await conn.execute(
                        sa.text(
                            "SELECT COUNT(*) FROM pack_draft_memberships "
                            "WHERE draft_bundle_id = CAST(:bid AS uuid)"
                        ),
                        {"bid": d1},
                    )
                ).scalar_one()
                assert int(cnt) == 0
            r_free = await client.delete(
                "/api/v1/agents-and-skills/agents/ag-free-315", headers=adm_h
            )
            assert r_free.status_code == 200

            # 2. Rich export (WORKFLOW_V2 + VSM_V2 + HELP_ARTICLE + INSTRUCTION) -> import ws_b
            d2 = (
                await client.post(
                    "/api/v1/packs/composer",
                    headers=adm_h,
                    json={
                        "slug": "rich-315",
                        "name": "Rich 315",
                        "scope_type": "WORKSPACE",
                        "scope_id": ws_a,
                    },
                )
            ).json()["bundle_id"]
            r_m2 = await client.put(
                f"/api/v1/packs/composer/{d2}/members",
                headers=adm_h,
                json={
                    "members": [
                        {"entity_type": "VSM_V2", "entity_id": eids["vsm_id"]},
                        {"entity_type": "WORKFLOW_V2", "entity_id": eids["wf_id"]},
                        {"entity_type": "AGENT", "entity_id": eids["agent_id"]},
                        {"entity_type": "SKILL", "entity_id": eids["skill_id"]},
                        {"entity_type": "INSTRUCTION", "entity_id": "instr-315"},
                        {"entity_type": "HELP_ARTICLE", "entity_id": "help-315"},
                    ]
                },
            )
            assert r_m2.status_code == 200, r_m2.text
            exp = await client.post(f"/api/v1/packs/composer/{d2}/export", headers=adm_h)
            assert exp.status_code == 200, exp.text
            with zipfile.ZipFile(io.BytesIO(exp.content), "r") as zf:
                names = set(zf.namelist())
                assert "rich-315/help/fr/help-315.md" in names
                assert "rich-315/instructions/instr-315.instructions.md" in names
                assert f"rich-315/workflows/vsm-{eids['vsm_id']}.yaml" in names

            imp = await client.post(
                "/api/v1/packs/import",
                headers=adm_h,
                files={"file": ("rich-315.zip", exp.content, "application/zip")},
                data={"scope_type": "WORKSPACE", "scope_id": ws_b},
            )
            assert imp.status_code == 200, imp.text
            async with eng.connect() as conn:
                wf_row = (
                    await conn.execute(
                        sa.text(
                            "SELECT spec_jsonb FROM workflow_definitions_v2 "
                            "WHERE pack_id = 'orcia-pack-rich-315' LIMIT 1"
                        )
                    )
                ).scalar_one()
                assert isinstance(wf_row["sub_steps"][0]["toolbox_mcp_permissions"], list)
                vsm_row = (
                    await conn.execute(
                        sa.text(
                            "SELECT spec_jsonb FROM vsm_definitions_v2 "
                            "WHERE pack_id = 'orcia-pack-rich-315' LIMIT 1"
                        )
                    )
                ).scalar_one()
                assert len(vsm_row["nodes"]) == 1
                help_meta = (
                    await conn.execute(
                        sa.text(
                            "SELECT metadata_jsonb FROM catalog_items WHERE owner_workspace_id = "
                            "CAST(:ws AS uuid) AND item_type = 'HELP_ARTICLE' LIMIT 1"
                        ),
                        {"ws": ws_b},
                    )
                ).scalar_one()
                assert "Help Body 315" in str(help_meta.get("markdown_body", ""))

            # 3. Observer exports GLOBAL SYSTEM bundle (200) & legacy export (200) vs ws_b (403)
            r_obs_sys = await client.post(f"/api/v1/packs/{ex['sys_bid']}/export", headers=obs_h)
            assert r_obs_sys.status_code == 200, r_obs_sys.text
            r_leg = await client.post(
                f"/api/v1/packs/export/{ws_a}?pack_id=orcia-pack-rich-315", headers=adm_h
            )
            assert r_leg.status_code == 200, r_leg.text
            assert (await client.get("/api/v1/packs/composer", headers=wsb_h)).json()[
                "drafts"
            ] == []
            assert (
                await client.get(f"/api/v1/packs/composer/{d2}", headers=wsb_h)
            ).status_code == 403
            assert (
                await client.post(f"/api/v1/packs/composer/{d2}/export", headers=wsb_h)
            ).status_code == 403
            assert (
                await client.post(f"/api/v1/packs/export/{ws_a}", headers=wsb_h)
            ).status_code == 403
            assert (
                await client.delete(
                    f"/api/v1/agents-and-skills/agents/{eids['agent_id']}", headers=wsb_h
                )
            ).status_code == 403
            assert (
                await client.delete(
                    f"/api/v1/packs/composer/dna-mechanisms/{eids['dna_slug']}", headers=adm_h
                )
            ).status_code == 403

            # 4. INSTRUCTION & HELP_ARTICLE 409 anti-hostage + atomic unlink + UUID deleted_uuid
            assert (
                await client.delete("/api/v1/catalog/instructions/instr-315", headers=adm_h)
            ).status_code == 409
            assert (await client.delete("/api/v1/help/help-315", headers=adm_h)).status_code == 409
            del_i = await client.delete(
                "/api/v1/catalog/instructions/instr-315?unlink_from_draft_packs=true",
                headers=adm_h,
            )
            assert del_i.status_code == 200
            assert (
                UUID(del_i.json()["deleted_uuid"]) and del_i.json()["deleted_uuid"] != "instr-315"
            )
            del_h = await client.delete(
                "/api/v1/help/help-315?unlink_from_draft_packs=true", headers=adm_h
            )
            assert del_h.status_code == 200
            assert UUID(del_h.json()["deleted_uuid"]) and del_h.json()["deleted_uuid"] != "help-315"

            # 5. P1-1 + P1-2: TEAM draft attaches ancestor BU pack ontology (`level='2_DOMAIN'`)
            r_td = await client.post(
                "/api/v1/packs/composer",
                headers=adm_h,
                json={
                    "slug": "team-anc-315",
                    "name": "Team Ancestor 315",
                    "scope_type": "TEAM",
                    "scope_id": ex["team_id"],
                },
            )
            assert r_td.status_code == 201, r_td.text
            td_id = r_td.json()["bundle_id"]
            r_tm = await client.put(
                f"/api/v1/packs/composer/{td_id}/members",
                headers=adm_h,
                json={
                    "members": [
                        {"entity_type": "ONTOLOGY_CONCEPT", "entity_id": "pack:bupack315:kpi"}
                    ]
                },
            )
            assert r_tm.status_code == 200, r_tm.text
            assert r_tm.json()["closure"]["complete"] is True
            async with eng.connect() as conn:
                acnt = (
                    await conn.execute(
                        sa.text(
                            "SELECT COUNT(*) FROM audit_ledger "
                            "WHERE event_type = 'PACK_DRAFT_MEMBER_UNLINKED_ON_ENTITY_DELETE'"
                        )
                    )
                ).scalar_one()
                assert int(acnt) >= 2
    finally:
        await eng.dispose()
