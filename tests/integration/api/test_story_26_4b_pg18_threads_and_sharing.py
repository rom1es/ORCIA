"""Story 26.4b — PG18 Vertical Tests for Threads, Layer 5 Launch & Folder Sharing."""

from __future__ import annotations

import pytest
import sqlalchemy as sa
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine
from tests.integration.api._pg18_story_26_4b_helpers import (
    bootstrap_admin_and_workspace,
    configure_pg18_test_env,
    pg18_db_url,
)

from orcia_api.main import create_app
from orcia_kernel.ids import new_uuid7_str

__all__ = ["pg18_db_url"]


@pytest.mark.asyncio
async def test_pg18_threads_turns_sharing_and_launch_process_cold_restart(
    pg18_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify folder threads, turns, sharing grants, and Layer 5 survive PG18 restart."""
    configure_pg18_test_env(monkeypatch, pg18_db_url)
    engine = create_async_engine(pg18_db_url)
    try:
        app1 = create_app()
        async with (
            app1.router.lifespan_context(app1),
            AsyncClient(transport=ASGITransport(app=app1), base_url="http://app1") as c1,
        ):
            hdrs, ws_id = await bootstrap_admin_and_workspace(
                c1, email="threads264b@orcia.io", slug_suffix="threads-26-4b"
            )
            peer_id = new_uuid7_str()
            async with engine.begin() as conn:
                await conn.execute(
                    sa.text(
                        "INSERT INTO users (id, email, display_name, auth_mode, "
                        "human_profile_archetype, platform_role, primary_org_unit_id) "
                        "SELECT CAST(:uid AS uuid), 'peer264b@orcia.io', 'Peer 26.4b', "
                        "'LOCAL', 'ENGINEERING', 'CONTRIBUTOR', primary_org_unit_id "
                        "FROM users LIMIT 1 ON CONFLICT (email) DO NOTHING"
                    ),
                    {"uid": peer_id},
                )
            r_fld = await c1.post(
                "/api/v1/assistant/folders",
                headers=hdrs,
                json={
                    "workspace_id": ws_id,
                    "title": "Architecture Folder",
                    "pinned_notes_markdown": "Pin: zero orphan SQL adapters.",
                    "working_attachments_uris": ["orcia://specs/arch@v1"],
                    "evidence_tags": ["G1"],
                    "has_restricted_sources": True,
                },
            )
            assert r_fld.status_code == 200, r_fld.text
            folder_id = r_fld.json()["folder_id"]
            app1.state.assistant_folders_and_sharing_service.register_workspace_members(
                ws_id, [peer_id]
            )

            r_share = await c1.post(
                f"/api/v1/assistant/folders/{folder_id}/share",
                headers=hdrs,
                json={
                    "workspace_id": ws_id,
                    "visibility_mode": "SHARED_SELECTED",
                    "shares": [{"grantee_user_id": peer_id, "access_role": "CO_CONTRIBUTOR"}],
                    "outside_workspace_user_ids": [],
                },
            )
            assert r_share.status_code == 200, r_share.text
            assert r_share.json()["restricted_sources_warning"]

            r_thr = await c1.post(
                "/api/v1/assistant/threads",
                headers=hdrs,
                json={
                    "workspace_id": ws_id,
                    "folder_id": folder_id,
                    "title": "Design Review Thread",
                    "initial_summary": "Initial context summary.",
                },
            )
            assert r_thr.status_code == 200, r_thr.text
            thread_id = r_thr.json()["thread_id"]
            assert r_thr.json()["turn_count"] == 1

            r_turn1 = await c1.post(
                "/api/v1/assistant/turns",
                headers=hdrs,
                json={
                    "workspace_id": ws_id,
                    "thread_id": thread_id,
                    "folder_id": folder_id,
                    "user_prompt": "Validate PG18 persistence invariant.",
                },
            )
            assert r_turn1.status_code == 202, r_turn1.text
            r_stream1 = await c1.get(r_turn1.json()["stream_url"], headers=hdrs)
            assert r_stream1.status_code == 200

            r_turn2 = await c1.post(
                "/api/v1/assistant/turns",
                headers=hdrs,
                json={
                    "workspace_id": ws_id,
                    "thread_id": thread_id,
                    "folder_id": folder_id,
                    "user_prompt": "Confirm release on exit.",
                },
            )
            assert r_turn2.status_code == 202, r_turn2.text
            r_stream2 = await c1.get(r_turn2.json()["stream_url"], headers=hdrs)
            assert r_stream2.status_code == 200

            r_msgs = await c1.get(
                f"/api/v1/assistant/threads/{thread_id}/messages",
                headers=hdrs,
                params={"workspace_id": ws_id},
            )
            assert r_msgs.status_code == 200, r_msgs.text
            assert any(
                "Validate PG18 persistence invariant." in m["content"]
                for m in r_msgs.json()["messages"]
            )

            r_launch = await c1.post(
                f"/api/v1/assistant/folders/{folder_id}/launch-process",
                headers=hdrs,
                json={
                    "workspace_id": ws_id,
                    "target_workflow_uri": "orcia://workflows/ticket-to-tech-spec",
                },
            )
            assert r_launch.status_code == 200, r_launch.text
            assert "Initial context summary." in str(r_launch.json()["prefilled_contract_inputs"])

        app2 = create_app()
        async with (
            app2.router.lifespan_context(app2),
            AsyncClient(transport=ASGITransport(app=app2), base_url="http://app2") as c2,
        ):
            login = await c2.post(
                "/api/v1/auth/login/local",
                json={
                    "email": "threads264b@orcia.io",
                    "password": "Admin264b!StrongPassword",  # pragma: allowlist secret
                },
            )
            hdrs2 = {"Authorization": f"Bearer {login.json()['access_token']}"}
            ov2 = (
                await c2.get(
                    f"/api/v1/assistant/workspaces/{ws_id}/overview",
                    headers=hdrs2,
                    params={"active_folder_id": folder_id, "search_query": "Design Review"},
                )
            ).json()
            assert ov2["folders_count"] == 1
            assert any(t["thread_id"] == thread_id and t["turn_count"] == 3 for t in ov2["threads"])

        async with engine.connect() as conn:
            turn_count_db = (
                await conn.execute(
                    sa.text(
                        "SELECT turn_count FROM assistant_threads "
                        "WHERE thread_id = CAST(:tid AS uuid)"
                    ),
                    {"tid": thread_id},
                )
            ).scalar_one()
            assert turn_count_db == 3
            shares_db = (
                await conn.execute(
                    sa.text(
                        "SELECT COUNT(*) FROM assistant_folder_shares "
                        "WHERE folder_id = CAST(:fid AS uuid)"
                    ),
                    {"fid": folder_id},
                )
            ).scalar_one()
            assert shares_db == 1
    finally:
        await engine.dispose()
