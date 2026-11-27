"""Layer 2 PG18 + SeaweedFS S3 integration test for Story 31.5 (`create_app()`, `<= 280 L`)."""

from __future__ import annotations

import hashlib
import io
import zipfile

import pytest
import sqlalchemy as sa
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine
from tests.integration._shared_topology_fixture import SharedIntegrationTopology
from tests.integration._story_31_4_pack_fixture import seed_story_31_4_topology
from tests.integration._story_31_5_fixture import REPO_ROOT, seed_story_31_5_entities
from uuid_utils import uuid7


@pytest.mark.asyncio
async def test_story_31_5_composer_anti_hostage_closure_scrub_export_and_roundtrip(
    isolated_worker_pg18_env: SharedIntegrationTopology, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify full Story 31.5 vertical path HTTP -> PG18 + SeaweedFS CAS -> fresh WS re-import."""
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

    from orcia_api.main import create_app

    app = create_app()
    assert app.dependency_overrides == {}
    try:
        async with (
            app.router.lifespan_context(app),
            AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
        ):
            tok = app.state.auth_service.jwt_manager.issue_token_pair(
                user_id=admin_id,
                email="admin314@orcia.test",
                role="PLATFORM_ADMIN",
                org_unit_id=org_id,
                archetype="ARCHITECT",
                auth_mode="LOCAL",
            )
            client.headers["Authorization"] = f"Bearer {tok.access_token}"

            obs = await client.post(
                "/api/v1/packs/composer",
                headers={"x-orcia-access-mode": "READ_ONLY_OBSERVER"},
                json={
                    "slug": "obs-draft",
                    "name": "Obs",
                    "scope_type": "WORKSPACE",
                    "scope_id": ws_a,
                },
            )
            assert obs.status_code == 403
            assert obs.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"

            cr = await client.post(
                "/api/v1/packs/composer",
                json={
                    "slug": "biz-custom-315",
                    "name": "Business Custom 315",
                    "version": "1.0.0",
                    "description": "Custom composed pack",
                    "author": "admin314@orcia.test",
                    "scope_type": "WORKSPACE",
                    "scope_id": ws_a,
                },
            )
            assert cr.status_code == 201, cr.text
            draft_id = cr.json()["bundle_id"]
            assert cr.json()["bundle_kind"] == "CUSTOM"
            assert cr.json()["status"] == "DRAFT"

            assert (
                await client.patch(
                    f"/api/v1/packs/composer/{draft_id}",
                    json={"name": "Business Custom 315 Updated"},
                )
            ).status_code == 200

            # 1. Partial selection -> closure gate fails closed with 422 ERR_PACK_CLOSURE_INCOMPLETE
            put_partial = await client.put(
                f"/api/v1/packs/composer/{draft_id}/members",
                json={
                    "members": [
                        {"entity_type": "WORKFLOW_V2", "entity_id": eids["wf_id"]},
                    ]
                },
            )
            assert put_partial.status_code == 200
            exp_fail = await client.post(f"/api/v1/packs/composer/{draft_id}/export")
            assert exp_fail.status_code == 422
            assert exp_fail.json()["error_code"] == "ERR_PACK_CLOSURE_INCOMPLETE"
            assert exp_fail.json()["missing_dependencies"]

            # 2. Populate all 8 typed FK columns & verify via direct PG18 SQL SELECT
            member_pairs = (
                ("AGENT", "agent_id"),
                ("SKILL", "skill_id"),
                ("WORKFLOW_V2", "wf_id"),
                ("VSM_V2", "vsm_id"),
                ("ONTOLOGY_CONCEPT", "c1_key"),
                ("ONTOLOGY_CONCEPT", "c2_key"),
                ("ONTOLOGY_RELATION", "rel_key"),
                ("ONTOLOGY_AXIOM", "ax_key"),
                ("DNA_MECHANISM", "dna_slug"),
                ("POLICY", "pol_key"),
            )
            all_members = [{"entity_type": t, "entity_id": eids[k]} for t, k in member_pairs]
            assert (
                await client.put(
                    f"/api/v1/packs/composer/{draft_id}/members",
                    json={"members": all_members},
                )
            ).status_code == 200

            async with eng.connect() as conn:
                fk_counts = (
                    (
                        await conn.execute(
                            sa.text(
                                "SELECT COUNT(catalog_item_id) AS cat, "
                                "COUNT(workflow_v2_id) AS wf, COUNT(vsm_v2_id) AS vsm, "
                                "COUNT(ontology_concept_id) AS con, "
                                "COUNT(ontology_relation_id) AS rel, "
                                "COUNT(ontology_axiom_id) AS ax, "
                                "COUNT(dna_mechanism_id) AS dna, COUNT(policy_id) AS pol "
                                "FROM pack_draft_memberships "
                                "WHERE draft_bundle_id = CAST(:b AS uuid)"
                            ),
                            {"b": draft_id},
                        )
                    )
                    .mappings()
                    .one()
                )
                assert dict(fk_counts) == {
                    "cat": 2,
                    "wf": 1,
                    "vsm": 1,
                    "con": 2,
                    "rel": 1,
                    "ax": 1,
                    "dna": 1,
                    "pol": 1,
                }

            # 3. Anti-hostage delete guard: 409 default, list_referencing_pack_drafts_conn & cb
            from orcia_core.storage.pack_draft_guard import (
                guard_or_unlink_pack_drafts_conn,
                list_referencing_pack_drafts_conn,
            )

            del_blocked = await client.delete(
                f"/api/v1/agents-and-skills/agents/{eids['agent_id']}"
            )
            assert del_blocked.status_code == 409
            assert del_blocked.json()["error_code"] == "ERR_ENTITY_REFERENCED_BY_PACK_DRAFT"
            assert del_blocked.json()["draft_packs"][0]["pack_slug"] == "biz-custom-315"

            async with eng.begin() as conn:
                res_id = await conn.execute(
                    sa.text("SELECT id::text FROM catalog_items WHERE resource_id = :r"),
                    {"r": eids["agent_id"]},
                )
                agent_uuid = str(res_id.scalar_one())
                refs = await list_referencing_pack_drafts_conn(
                    conn, fk_column="catalog_item_id", target_uuid=agent_uuid
                )
                assert [r["pack_slug"] for r in refs] == ["biz-custom-315"]
                cb_seen: list[str] = []
                unlinked_cb = await guard_or_unlink_pack_drafts_conn(
                    conn,
                    fk_column="catalog_item_id",
                    target_uuid=agent_uuid,
                    entity_type="AGENT",
                    entity_label=eids["agent_id"],
                    unlink_from_draft_packs=True,
                    authorize_draft_cb=lambda bid, _st, _sid: cb_seen.append(bid),
                    scope_path=f"WORKSPACE:{ws_a}",
                )
                assert len(unlinked_cb) == 1 and cb_seen == [draft_id]
                await conn.rollback()

            # Re-test auto_include_dependencies=true on workflow -> agent -> skill
            cr2 = await client.post(
                "/api/v1/packs/composer",
                json={
                    "slug": "auto-inc-315",
                    "name": "Auto",
                    "scope_type": "WORKSPACE",
                    "scope_id": ws_a,
                },
            )
            draft2_id = cr2.json()["bundle_id"]
            await client.put(
                f"/api/v1/packs/composer/{draft2_id}/members",
                json={"members": [{"entity_type": "WORKFLOW_V2", "entity_id": eids["wf_id"]}]},
            )
            exp_auto = await client.post(
                f"/api/v1/packs/composer/{draft2_id}/export?auto_include_dependencies=true"
            )
            assert exp_auto.status_code == 200
            assert int(exp_auto.headers["x-orcia-included-dependencies-count"]) >= 2

            # Deterministic repeat export check
            exp_auto_2 = await client.post(f"/api/v1/packs/composer/{draft2_id}/export")
            assert exp_auto_2.status_code == 200
            assert exp_auto.content == exp_auto_2.content
            assert (
                hashlib.sha256(exp_auto.content).hexdigest()
                == exp_auto.headers["x-orcia-archive-sha256"]
            )
            with zipfile.ZipFile(io.BytesIO(exp_auto.content), "r") as zf:
                names = set(zf.namelist())
                assert "auto-inc-315/apm.yml" in names
                assert "auto-inc-315/apm.lock.yaml" in names
                apm_text = zf.read("auto-inc-315/apm.yml").decode("utf-8")
                assert ws_a not in apm_text
                assert ds_a_id not in apm_text
                assert "repo_a" in apm_text

            # 4. Fresh workspace (ws_b) round-trip import -> slot bind -> activate
            imp = await client.post(
                "/api/v1/packs/import",
                files={"file": ("auto-inc-315.zip", exp_auto.content, "application/zip")},
                data={"scope_type": "WORKSPACE", "scope_id": ws_b},
            )
            assert imp.status_code == 200, imp.text
            assert imp.json()["slug"] == "auto-inc-315"
            slot_res = await client.put(
                f"/api/v1/workspaces/{ws_b}/packs/auto-inc-315/slots",
                json={
                    "bindings": [
                        {
                            "slot_key": "repo_a",
                            "target_kind": "WORKSPACE_DATASOURCE",
                            "target_id": ds_b_id,
                        }
                    ]
                },
            )
            assert slot_res.status_code == 200
            act = await client.post(f"/api/v1/workspaces/{ws_b}/packs/auto-inc-315/activate")
            assert act.status_code == 200, act.text
            assert act.json()["is_active"] is True

            # 5. Leak scanner 422 ERR_PACK_PII_OR_INFRA_LEAK on residual secret in authored text
            leak_sql = (
                "UPDATE catalog_items SET metadata_jsonb = jsonb_set(metadata_jsonb, "
                "'{instructions}', to_jsonb('Leak sk-1234567890abcdef1234567890'::text)) "
                "WHERE resource_id = :aid"
            )
            async with eng.begin() as conn:
                await conn.execute(sa.text(leak_sql), {"aid": eids["agent_id"]})
            leak_resp = await client.post(f"/api/v1/packs/composer/{draft_id}/export")
            assert leak_resp.status_code == 422
            assert leak_resp.json()["error_code"] == "ERR_PACK_PII_OR_INFRA_LEAK"

            # 6. Anti-hostage atomic unlink + audit_ledger + delete on agent
            unlink_url = (
                f"/api/v1/agents-and-skills/agents/{eids['agent_id']}?unlink_from_draft_packs=true"
            )
            del_ok = await client.delete(unlink_url)
            assert del_ok.status_code == 200, del_ok.text
            assert len(del_ok.json()["unlinked_draft_packs"]) >= 1
            audit_sql = (
                "SELECT COUNT(*) FROM audit_ledger "
                "WHERE event_type = 'PACK_DRAFT_MEMBER_UNLINKED_ON_ENTITY_DELETE'"
            )
            async with eng.connect() as conn:
                audit_cnt = (await conn.execute(sa.text(audit_sql))).scalar_one()
                assert int(audit_cnt) >= 1

            # 7. Delete draft bundle cleanly (ON DELETE CASCADE)
            del_draft = await client.delete(f"/api/v1/packs/composer/{draft2_id}")
            assert del_draft.status_code == 200
            assert del_draft.json()["deleted"] is True
    finally:
        await eng.dispose()
