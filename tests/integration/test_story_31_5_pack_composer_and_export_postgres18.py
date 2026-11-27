"""Layer 2 PG18 + SeaweedFS S3 integration test for Story 31.5 (`create_app()`, `<= 280 L`)."""

from __future__ import annotations

import hashlib
import io
import os
import zipfile

import pytest
import sqlalchemy as sa
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine
from tests.integration._story_31_4_pack_fixture import seed_story_31_4_topology
from tests.integration._story_31_5_fixture import (
    REPO_ROOT,
    pg18_and_seaweed_urls_315,
    seed_story_31_5_entities,
)
from uuid_utils import uuid7

os.environ["TESTCONTAINERS_RYUK_DISABLED"] = "true"
_PG_S3_FIXTURE = pg18_and_seaweed_urls_315


@pytest.mark.asyncio
async def test_story_31_5_composer_anti_hostage_closure_scrub_export_and_roundtrip(
    pg18_and_seaweed_urls_315: tuple[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify full Story 31.5 vertical path HTTP -> PG18 + SeaweedFS CAS -> fresh WS re-import."""
    pg_url, s3_url = pg18_and_seaweed_urls_315
    monkeypatch.setenv("DATABASE_URL", pg_url)
    monkeypatch.setenv("S3_ENDPOINT_URL", s3_url)
    monkeypatch.setenv("ORCIA_ENABLE_PG_SESSION_MAKER", "1")
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
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
            all_members = [
                {"entity_type": "AGENT", "entity_id": eids["agent_id"]},
                {"entity_type": "SKILL", "entity_id": eids["skill_id"]},
                {"entity_type": "WORKFLOW_V2", "entity_id": eids["wf_id"]},
                {"entity_type": "VSM_V2", "entity_id": eids["vsm_id"]},
                {"entity_type": "ONTOLOGY_CONCEPT", "entity_id": eids["c1_key"]},
                {"entity_type": "ONTOLOGY_CONCEPT", "entity_id": eids["c2_key"]},
                {"entity_type": "ONTOLOGY_RELATION", "entity_id": eids["rel_key"]},
                {"entity_type": "ONTOLOGY_AXIOM", "entity_id": eids["ax_key"]},
                {"entity_type": "DNA_MECHANISM", "entity_id": eids["dna_slug"]},
                {"entity_type": "POLICY", "entity_id": eids["pol_key"]},
            ]
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

            # 3. Anti-hostage delete guard: 409 default, unlink + audit_ledger on query param
            del_blocked = await client.delete(
                f"/api/v1/agents-and-skills/agents/{eids['agent_id']}"
            )
            assert del_blocked.status_code == 409
            assert del_blocked.json()["error_code"] == "ERR_ENTITY_REFERENCED_BY_PACK_DRAFT"
            assert del_blocked.json()["draft_packs"][0]["pack_slug"] == "biz-custom-315"

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
            assert (
                await client.put(
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
            ).status_code == 200
            act = await client.post(f"/api/v1/workspaces/{ws_b}/packs/auto-inc-315/activate")
            assert act.status_code == 200, act.text
            assert act.json()["is_active"] is True

            # 5. Leak scanner 422 ERR_PACK_PII_OR_INFRA_LEAK on residual secret in authored text
            async with eng.begin() as conn:
                await conn.execute(
                    sa.text(
                        "UPDATE catalog_items SET metadata_jsonb = jsonb_set(metadata_jsonb, "
                        "'{instructions}', to_jsonb('Leak sk-1234567890abcdef1234567890'::text)) "
                        "WHERE resource_id = :aid"
                    ),
                    {"aid": eids["agent_id"]},
                )
            leak_resp = await client.post(f"/api/v1/packs/composer/{draft_id}/export")
            assert leak_resp.status_code == 422
            assert leak_resp.json()["error_code"] == "ERR_PACK_PII_OR_INFRA_LEAK"

            # 6. Anti-hostage atomic unlink + audit_ledger + delete on agent
            del_ok = await client.delete(
                f"/api/v1/agents-and-skills/agents/{eids['agent_id']}?unlink_from_draft_packs=true"
            )
            assert del_ok.status_code == 200, del_ok.text
            assert len(del_ok.json()["unlinked_draft_packs"]) >= 1
            async with eng.connect() as conn:
                audit_cnt = (
                    await conn.execute(
                        sa.text(
                            "SELECT COUNT(*) FROM audit_ledger "
                            "WHERE event_type = 'PACK_DRAFT_MEMBER_UNLINKED_ON_ENTITY_DELETE'"
                        )
                    )
                ).scalar_one()
                assert int(audit_cnt) >= 1

            # 7. Delete draft bundle cleanly (ON DELETE CASCADE)
            del_draft = await client.delete(f"/api/v1/packs/composer/{draft2_id}")
            assert del_draft.status_code == 200
            assert del_draft.json()["deleted"] is True
    finally:
        await eng.dispose()
