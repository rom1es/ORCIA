"""Layer 2 integration test verifying shared PG18/Redis/S3 topology & typed seeds."""

from __future__ import annotations

import pytest
import sqlalchemy as sa
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine
from tests.integration._shared_topology_fixture import (
    SharedIntegrationTopology,
    activate_pack_with_slots,
    seed_org_workspace_admin,
)

from orcia_api.main import create_app

pytestmark = pytest.mark.story("32.3")


@pytest.mark.asyncio
async def test_shared_topology_template_clone_typed_seeds_and_create_app(
    isolated_worker_pg18_env: SharedIntegrationTopology,
) -> None:
    """Verify xdist-isolated PG18 template clone, typed seeds, and real `create_app()`."""
    topo = isolated_worker_pg18_env
    seeded = await seed_org_workspace_admin(
        topo.async_database_url,
        org_slug="ent-shared-32-3",
        workspace_slug="ws-shared-32-3",
        admin_email="shared323@orcia.test",
    )
    activated = await activate_pack_with_slots(
        topo.async_database_url,
        workspace_id=seeded.workspace_id,
        pack_slug="shared-pack-32-3",
        slot_keys=("git_repo",),
    )
    assert len(activated.slot_binding_ids) == 1

    eng = create_async_engine(topo.async_database_url)
    try:
        async with eng.connect() as conn:
            ws_count = await conn.execute(
                sa.text("SELECT COUNT(*) FROM workspaces WHERE id = CAST(:ws AS uuid)"),
                {"ws": seeded.workspace_id},
            )
            assert int(ws_count.scalar_one()) == 1
            act_count = await conn.execute(
                sa.text(
                    "SELECT COUNT(*) FROM workspace_pack_activations WHERE id = CAST(:id AS uuid)"
                ),
                {"id": activated.activation_id},
            )
            assert int(act_count.scalar_one()) == 1
    finally:
        await eng.dispose()

    app = create_app()
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://testserver") as client,
    ):
        resp = await client.get("/api/v1/health")
        assert resp.status_code == 200
