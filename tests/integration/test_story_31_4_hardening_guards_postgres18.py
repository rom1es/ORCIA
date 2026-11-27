"""Layer 2 PG18 hardening tests for Story 31.4 P0/P1/P2 findings (`create_app()`, `--no-cov`)."""

from __future__ import annotations

import pytest
import sqlalchemy as sa
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine
from tests.integration._shared_topology_fixture import SharedIntegrationTopology
from tests.integration._story_31_4_pack_fixture import (
    REPO_ROOT,
    build_dummy_lock_for_p01_test,
    build_slot_pack_zip,
    seed_story_31_4_hardening_extras,
    seed_story_31_4_topology,
)
from uuid_utils import uuid7


@pytest.mark.asyncio
async def test_story_31_4_p0_p1_p2_hardening_guards_pg18(
    isolated_worker_pg18_env: SharedIntegrationTopology, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Verify P0-1..5, P1-2/3/6 & P2-1/3 on real PG18 + `create_app()`."""
    pg18_url = isolated_worker_pg18_env.async_database_url
    monkeypatch.setenv("ORCIA_ENV_FILE", str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"))

    org_id, ws_a, ws_b, admin_id = str(uuid7()), str(uuid7()), str(uuid7()), str(uuid7())
    obs_id, ds_a_id, ds_b_id, ec_id = str(uuid7()), str(uuid7()), str(uuid7()), str(uuid7())
    ds_db_id = str(uuid7())
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
    await seed_story_31_4_hardening_extras(
        eng, org_id=org_id, ws_a=ws_a, obs_id=obs_id, ds_db_id=ds_db_id
    )

    from orcia_api.main import create_app
    from orcia_core.bootstrap._internal.sql_enterprise_connectors import (
        delete_enterprise_connector_on_postgres18,
    )
    from orcia_core.kernel.errors import ResourceNotFoundError, ResourcePinnedByActiveRunsError
    from orcia_core.orchestration._internal._sql_orchestration_parents import (
        upsert_run_lock_manifest_sql,
    )

    app = create_app()
    assert app.dependency_overrides == {}
    try:
        async with (
            app.router.lifespan_context(app),
            AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
        ):
            jwt_mgr = app.state.auth_service.jwt_manager
            admin_tok = jwt_mgr.issue_token_pair(
                user_id=admin_id,
                email="admin314@orcia.test",
                role="PLATFORM_ADMIN",
                org_unit_id=org_id,
                archetype="ARCHITECT",
                auth_mode="LOCAL",
            ).access_token
            obs_tok = jwt_mgr.issue_token_pair(
                user_id=obs_id,
                email="obs314@orcia.test",
                role="CONTRIBUTOR",
                org_unit_id=org_id,
                archetype="ARCHITECT",
                auth_mode="LOCAL",
            ).access_token
            adm_h = {"Authorization": f"Bearer {admin_tok}"}
            obs_h = {"Authorization": f"Bearer {obs_tok}"}

            zip_a1 = build_slot_pack_zip(
                slug="alpha-pack",
                version="1.0.0",
                scope_id=ws_a,
                slots=[
                    {"slot_key": "code-repo", "scheme": "git", "required": True},
                    {"slot_key": "ec-bridge", "scheme": "git", "required": True},
                    {"slot_key": "opt-kb", "scheme": "db", "required": False},
                    {"slot_key": "int-bus", "scheme": "internal", "required": False},
                ],
                with_workflow=True,
            )
            zip_a2 = build_slot_pack_zip(
                slug="alpha-pack",
                version="2.0.0",
                scope_id=ws_a,
                slots=[
                    {"slot_key": "code-repo", "scheme": "git", "required": True},
                    {"slot_key": "ec-bridge", "scheme": "git", "required": True},
                    {"slot_key": "opt-kb", "scheme": "db", "required": False},
                ],
                with_workflow=True,
            )
            zip_gamma = build_slot_pack_zip(
                slug="gamma-pack",
                version="1.0.0",
                scope_id=ws_a,
                slots=[{"slot_key": "code-repo", "scheme": "git", "required": True}],
                with_workflow=True,
            )
            imp1 = await client.post(
                "/api/v1/packs/import",
                headers=adm_h,
                files={"file": ("a1.zip", zip_a1, "application/zip")},
                data={"scope_type": "WORKSPACE", "scope_id": ws_a},
            )
            v1_id = imp1.json()["bundle_id"]
            assert (
                await client.post(
                    "/api/v1/packs/import",
                    headers=adm_h,
                    files={"file": ("gamma.zip", zip_gamma, "application/zip")},
                    data={"scope_type": "WORKSPACE", "scope_id": ws_a},
                )
            ).status_code == 200

            # P0-4: invalid INTERNAL, scheme mismatch, unknown scheme, EC kind mismatch
            bad_cases: tuple[tuple[str, str, str | None, str | None], ...] = (
                ("code-repo", "INTERNAL", None, None),
                ("code-repo", "WORKSPACE_DATASOURCE", ds_db_id, None),
                ("code-repo", "WORKSPACE_DATASOURCE", ds_a_id, "db"),
                ("opt-kb", "ENTERPRISE_CONNECTOR", ec_id, None),
                ("ec-bridge", "ENTERPRISE_CONNECTOR", ec_id, "nonexistent"),
            )
            for skey, tkind, tid, sch in bad_cases:
                b_item = {"slot_key": skey, "target_kind": tkind, "target_id": tid}
                if sch is not None:
                    b_item["connector_scheme"] = sch
                bad = await client.put(
                    f"/api/v1/workspaces/{ws_a}/packs/alpha-pack/slots",
                    headers=adm_h,
                    json={"bindings": [b_item]},
                )
                assert bad.status_code == 422, f"{b_item} -> {bad.text}"

            # Valid bind incl. INTERNAL on internal slot
            assert (
                await client.put(
                    f"/api/v1/workspaces/{ws_a}/packs/alpha-pack/slots",
                    headers=adm_h,
                    json={
                        "bindings": [
                            {
                                "slot_key": "code-repo",
                                "target_kind": "WORKSPACE_DATASOURCE",
                                "target_id": ds_a_id,
                            },
                            {
                                "slot_key": "ec-bridge",
                                "target_kind": "ENTERPRISE_CONNECTOR",
                                "target_id": ec_id,
                            },
                            {"slot_key": "int-bus", "target_kind": "INTERNAL"},
                        ]
                    },
                )
            ).status_code == 200
            assert (
                await client.post(
                    f"/api/v1/workspaces/{ws_a}/packs/alpha-pack/activate", headers=adm_h
                )
            ).status_code == 200

            # P0-5 / P1-6: invalid priority & bad UUID delete never 500
            assert (
                await client.post(
                    f"/api/v1/workspaces/{ws_a}/packs/alpha-pack/activate",
                    headers=adm_h,
                    json={"priority_order": 0},
                )
            ).status_code == 422
            with pytest.raises(ResourceNotFoundError):
                await delete_enterprise_connector_on_postgres18(eng, "not-a-uuid")

            # P0-3: unactivated pack workflow fails closed with workspace & without workspace
            assert (
                await client.post(
                    "/api/v1/workflows/v2/wf-gamma-pack/runs",
                    headers=adm_h,
                    json={"workspace_id": ws_a, "inputs": {"x": "1"}},
                )
            ).status_code == 422
            assert (
                await client.post(
                    "/api/v1/workflows/v2/wf-gamma-pack/runs",
                    headers=adm_h,
                    json={"inputs": {"x": "1"}},
                )
            ).status_code == 422

            # P0-2: cold PG18 READ_ONLY_OBSERVER membership rejected on workflow v2 run start
            app.state.auth_service.evaluator._memberships = ()
            obs_run = await client.post(
                "/api/v1/workflows/v2/wf-alpha-pack/runs",
                headers=obs_h,
                json={"workspace_id": ws_a, "inputs": {"x": "1"}},
            )
            assert obs_run.status_code == 403
            assert obs_run.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"

            # P2-1 & P2-3: start via workspace slug + strip unbound slot://opt-kb
            started = await client.post(
                "/api/v1/workflows/v2/wf-alpha-pack/runs",
                headers=adm_h,
                json={
                    "workspace_id": "ws-31-4-a",
                    "inputs": {"kb": "slot://opt-kb", "resources": ["slot://opt-kb", "orcia://ok"]},
                },
            )
            assert started.status_code == 200, started.text
            run_id = started.json()["run"]["run_id"]
            assert started.json()["run"]["inputs"] == {"resources": ["orcia://ok"]}
            before_lock = (await client.get(f"/api/v1/runs/{run_id}/lock", headers=adm_h)).json()

            # P0-1: subsequent upsert_run_lock_manifest_sql NEVER overwrites pinned_packs
            dummy_lock = build_dummy_lock_for_p01_test(run_id, ws_a, org_id)
            await upsert_run_lock_manifest_sql(app.state.dbos_uow, dummy_lock)
            after_lock = (await client.get(f"/api/v1/runs/{run_id}/lock", headers=adm_h)).json()
            assert after_lock["manifest_sha256"] == before_lock["manifest_sha256"]
            assert len(after_lock["pinned_packs"]) == 1

            # P1-2: deleting pinned datasource or connector fails 409 while run is active
            assert (
                await client.delete(
                    f"/api/v1/workspaces/{ws_a}/datasources/{ds_a_id}", headers=adm_h
                )
            ).status_code == 409
            with pytest.raises(ResourcePinnedByActiveRunsError):
                await delete_enterprise_connector_on_postgres18(eng, ec_id)

            # Complete run -> deletion allowed & v2 upgrade preserves slot bindings (P1-3)
            for _ in range(2):
                await client.post(
                    f"/api/v1/runs/{run_id}/hitl-signal",
                    headers=adm_h,
                    json={"action": "APPROVE", "actor_id": admin_id},
                )
            async with eng.begin() as conn:
                await conn.execute(
                    sa.text(
                        "UPDATE workflow_runs SET status = 'COMMITTED_AUTONOMOUS' "
                        "WHERE id = CAST(:rid AS uuid)"
                    ),
                    {"rid": run_id.removeprefix("run-")},
                )
            assert (
                await client.post(
                    "/api/v1/packs/import",
                    headers=adm_h,
                    files={"file": ("a2.zip", zip_a2, "application/zip")},
                    data={"scope_type": "WORKSPACE", "scope_id": ws_a},
                )
            ).status_code == 200
            up = await client.post(
                f"/api/v1/workspaces/{ws_a}/packs/alpha-pack/activate",
                headers=adm_h,
                json={"version": "2.0.0"},
            )
            assert up.status_code == 200
            v2_id = up.json()["pack_bundle_id"]
            assert (await client.delete(f"/api/v1/packs/{v1_id}", headers=adm_h)).status_code == 200

        async with eng.connect() as conn:
            sb_cnt = (
                await conn.execute(
                    sa.text(
                        "SELECT COUNT(*) FROM workspace_pack_slot_bindings WHERE "
                        "workspace_id = CAST(:ws AS uuid) AND pack_bundle_id = CAST(:b AS uuid)"
                    ),
                    {"ws": ws_a, "b": v2_id},
                )
            ).scalar_one()
            assert int(sb_cnt) == 2
            ws_v2_run = (
                await conn.execute(
                    sa.text("SELECT workspace_id::text FROM workflow_v2_runs WHERE run_id = :r"),
                    {"r": run_id},
                )
            ).scalar_one()
            assert ws_v2_run == ws_a
    finally:
        await eng.dispose()
