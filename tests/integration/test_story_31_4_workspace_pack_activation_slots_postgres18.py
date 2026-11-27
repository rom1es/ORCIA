"""Layer 2 PG18 integration test for Story 31.4 (`create_app()`, `--no-cov`, `<= 300 L`)."""

from __future__ import annotations

import pytest
import sqlalchemy as sa
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine
from tests.integration._shared_topology_fixture import SharedIntegrationTopology
from tests.integration._story_31_4_pack_fixture import (
    REPO_ROOT,
    build_slot_pack_zip,
    seed_story_31_4_topology,
)
from uuid_utils import uuid7


@pytest.mark.asyncio
async def test_story_31_4_activation_slots_422_guard_and_run_lock_pg18(
    isolated_worker_pg18_env: SharedIntegrationTopology, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify workspace pack activation, slot bindings, 422 guard, reorder, run lock & 409."""
    pg18_url = isolated_worker_pg18_env.async_database_url
    monkeypatch.setenv("ORCIA_ENV_FILE", str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"))

    org_id, ws_a, ws_b, admin_id = str(uuid7()), str(uuid7()), str(uuid7()), str(uuid7())
    ds_a_id, ds_b_id, ec_id = str(uuid7()), str(uuid7()), str(uuid7())
    eng = create_async_engine(pg18_url)
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

    from orcia_api.main import create_app

    app = create_app()
    assert app.dependency_overrides == {}
    try:
        async with (
            app.router.lifespan_context(app),
            AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
        ):
            token_pair = app.state.auth_service.jwt_manager.issue_token_pair(
                user_id=admin_id,
                email="admin314@orcia.test",
                role="PLATFORM_ADMIN",
                org_unit_id=org_id,
                archetype="ARCHITECT",
                auth_mode="LOCAL",
            )
            client.headers["Authorization"] = f"Bearer {token_pair.access_token}"
            zip_alpha = build_slot_pack_zip(
                slug="alpha-pack",
                version="1.0.0",
                scope_id=ws_a,
                slots=[
                    {"slot_key": "code-repo", "scheme": "git", "required": True},
                    {"slot_key": "opt-kb", "scheme": "db", "required": False},
                ],
                with_workflow=True,
            )
            zip_beta = build_slot_pack_zip(
                slug="beta-pack",
                version="1.0.0",
                scope_id=ws_a,
                slots=[{"slot_key": "ec-bridge", "scheme": "git", "required": True}],
            )
            zip_other = build_slot_pack_zip(
                slug="other-pack",
                version="1.0.0",
                scope_id=ws_b,
                slots=[],
            )
            imp_a = await client.post(
                "/api/v1/packs/import",
                files={"file": ("alpha.zip", zip_alpha, "application/zip")},
                data={"scope_type": "WORKSPACE", "scope_id": ws_a},
            )
            assert imp_a.status_code == 200, imp_a.text
            alpha_bundle_id = imp_a.json()["bundle_id"]
            assert (
                await client.post(
                    "/api/v1/packs/import",
                    files={"file": ("beta.zip", zip_beta, "application/zip")},
                    data={"scope_type": "WORKSPACE", "scope_id": ws_a},
                )
            ).status_code == 200
            assert (
                await client.post(
                    "/api/v1/packs/import",
                    files={"file": ("other.zip", zip_other, "application/zip")},
                    data={"scope_type": "WORKSPACE", "scope_id": ws_b},
                )
            ).status_code == 200

            assert (
                await client.post(f"/api/v1/workspaces/{ws_a}/packs/other-pack/activate")
            ).status_code == 403
            obs = await client.post(
                f"/api/v1/workspaces/{ws_a}/packs/alpha-pack/activate",
                headers={"x-orcia-access-mode": "READ_ONLY_OBSERVER"},
            )
            assert obs.status_code == 403
            assert obs.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"

            act_fail = await client.post(f"/api/v1/workspaces/{ws_a}/packs/alpha-pack/activate")
            assert act_fail.status_code == 422
            assert act_fail.json()["error_code"] == "ERR_PACK_SLOT_UNBOUND"
            assert "code-repo" in act_fail.json()["detail"]

            bad_bind = await client.put(
                f"/api/v1/workspaces/{ws_a}/packs/alpha-pack/slots",
                json={
                    "bindings": [
                        {
                            "slot_key": "code-repo",
                            "target_kind": "WORKSPACE_DATASOURCE",
                            "target_id": ds_b_id,
                        }
                    ]
                },
            )
            assert bad_bind.status_code == 422

            bad_scheme = await client.put(
                f"/api/v1/workspaces/{ws_a}/packs/alpha-pack/slots",
                json={
                    "bindings": [
                        {
                            "slot_key": "opt-kb",
                            "target_kind": "WORKSPACE_DATASOURCE",
                            "target_id": ds_a_id,
                        }
                    ]
                },
            )
            assert bad_scheme.status_code == 422

            from orcia_core.packs._internal._sql_workspace_pack_mutations import (
                activate_workspace_pack_sql,
            )
            from orcia_core.packs.errors import PackActivationInvalidError

            with pytest.raises(PackActivationInvalidError):
                await activate_workspace_pack_sql(
                    eng,
                    workspace_id=ws_a,
                    pack_slug="alpha-pack",
                    priority_order=0,
                    actor_id=admin_id,
                )

            good_bind = await client.put(
                f"/api/v1/workspaces/{ws_a}/packs/alpha-pack/slots",
                json={
                    "bindings": [
                        {
                            "slot_key": "code-repo",
                            "target_kind": "WORKSPACE_DATASOURCE",
                            "target_id": ds_a_id,
                        }
                    ]
                },
            )
            assert good_bind.status_code == 200, good_bind.text
            assert (
                await client.put(
                    f"/api/v1/workspaces/{ws_a}/packs/beta-pack/slots",
                    json={
                        "bindings": [
                            {
                                "slot_key": "ec-bridge",
                                "target_kind": "ENTERPRISE_CONNECTOR",
                                "target_id": ec_id,
                            }
                        ]
                    },
                )
            ).status_code == 200

            assert (
                await client.post(f"/api/v1/workspaces/{ws_a}/packs/alpha-pack/activate")
            ).json()["priority_order"] == 1
            assert (
                await client.post(f"/api/v1/workspaces/{ws_a}/packs/beta-pack/activate")
            ).json()["priority_order"] == 2

            reord = await client.put(
                f"/api/v1/workspaces/{ws_a}/packs/reorder",
                json={"ordered_pack_slugs": ["beta-pack", "alpha-pack"]},
            )
            assert reord.status_code == 200, reord.text
            assert [p["pack_slug"] for p in reord.json()["packs"]] == ["beta-pack", "alpha-pack"]

            views = await client.get(f"/api/v1/workspaces/{ws_a}/packs")
            assert views.status_code == 200
            assert any(p["slug"] == "alpha-pack" and p["is_active"] for p in views.json()["packs"])

            start_run = await client.post(
                "/api/v1/workflows/v2/wf-alpha-pack/runs",
                json={"workspace_id": ws_a, "inputs": {"objective": "Deliver feature"}},
            )
            assert start_run.status_code == 200, start_run.text
            run_id = start_run.json()["run"]["run_id"]
            assert start_run.json()["run"]["status"] == "WAITING_SUBSTEP_HITL"

            lock_resp = await client.get(f"/api/v1/runs/{run_id}/lock")
            assert lock_resp.status_code == 200, lock_resp.text
            lock_json = lock_resp.json()
            assert [p["pack_slug"] for p in lock_json["pinned_packs"]] == [
                "beta-pack",
                "alpha-pack",
            ]
            slot_map = {s["slot_key"]: s for s in lock_json["resolved_pack_slots"]}
            assert slot_map["code-repo"]["status"] == "bound"
            assert slot_map["code-repo"]["target_id"] == ds_a_id
            assert slot_map["opt-kb"]["status"] == "optional_unbound"
            assert slot_map["opt-kb"]["target_id"] is None

            deact = await client.delete(f"/api/v1/workspaces/{ws_a}/packs/alpha-pack/deactivate")
            assert deact.status_code == 200
            lock_after = await client.get(f"/api/v1/runs/{run_id}/lock")
            assert lock_after.json()["manifest_sha256"] == lock_json["manifest_sha256"]

            del_pinned = await client.delete(f"/api/v1/packs/{alpha_bundle_id}")
            assert del_pinned.status_code == 409
            assert del_pinned.json()["error_code"] == "ERR_RESOURCE_PINNED_BY_ACTIVE_RUNS"

            fin1 = await client.post(
                f"/api/v1/runs/{run_id}/hitl-signal",
                json={"action": "APPROVE", "actor_id": admin_id},
            )
            assert fin1.status_code == 200
            assert fin1.json()["run"]["status"] == "WAITING_FINAL_ANCHOR"
            fin2 = await client.post(
                f"/api/v1/runs/{run_id}/hitl-signal",
                json={"action": "APPROVE", "actor_id": admin_id},
            )
            assert fin2.status_code == 200
            assert fin2.json()["run"]["status"] == "COMPLETED_APPROVED"
            assert (await client.delete(f"/api/v1/packs/{alpha_bundle_id}")).status_code == 200

            assert (
                await client.post(
                    "/api/v1/packs/import",
                    files={"file": ("alpha.zip", zip_alpha, "application/zip")},
                    data={"scope_type": "WORKSPACE", "scope_id": ws_a},
                )
            ).status_code == 200
            bind_body = {
                "bindings": [
                    {
                        "slot_key": "code-repo",
                        "target_kind": "WORKSPACE_DATASOURCE",
                        "target_id": ds_a_id,
                    }
                ]
            }
            r_bind = await client.put(
                f"/api/v1/workspaces/{ws_a}/packs/alpha-pack/slots", json=bind_body
            )
            assert r_bind.status_code == 200
            r_act = await client.post(f"/api/v1/workspaces/{ws_a}/packs/alpha-pack/activate")
            assert r_act.status_code == 200
            r_del = await client.delete(f"/api/v1/workspaces/{ws_a}/datasources/{ds_a_id}")
            assert r_del.status_code == 200
            blocked_run = await client.post(
                "/api/v1/workflows/v2/wf-alpha-pack/runs",
                json={"workspace_id": ws_a, "inputs": {"objective": "Should fail closed"}},
            )
            assert blocked_run.status_code == 422
            assert blocked_run.json()["error_code"] == "ERR_PACK_SLOT_UNBOUND"
            assert "code-repo" in blocked_run.json()["detail"]

        async with eng.connect() as conn:
            audit_q = "SELECT COUNT(*) FROM audit_ledger WHERE event_type = 'PACK_SLOTS_BOUND'"
            audit_cnt = (await conn.execute(sa.text(audit_q))).scalar_one()
            assert int(audit_cnt) >= 3
            xor_q = (
                "SELECT is_active, priority_order FROM workspace_pack_activations "
                "WHERE workspace_id = CAST(:ws AS uuid) AND pack_slug = 'alpha-pack'"
            )
            xor_row = (await conn.execute(sa.text(xor_q), {"ws": ws_a})).first()
            assert xor_row is not None and bool(xor_row[0]) is True
    finally:
        await eng.dispose()
