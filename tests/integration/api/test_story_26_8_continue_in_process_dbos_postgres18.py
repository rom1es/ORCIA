"""Story 26.8 — Real Composition Root (`create_app()`, `0` overrides) PG18 + DBOS Tests."""

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

__all__ = ["pg18_db_url"]


@pytest.mark.asyncio
async def test_pg18_dbos_continue_in_process_folder_launch_and_cold_restart_resume(
    pg18_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify DBOS + PG18 end-to-end launch, `WAITING_FOR_HUMAN_ANCHOR`, 422 gate & cold resume."""
    configure_pg18_test_env(monkeypatch, pg18_db_url)
    engine = create_async_engine(pg18_db_url)
    try:
        run_turn_id = ""
        run_folder_id = ""
        ws_id = ""

        app1 = create_app()
        async with (
            app1.router.lifespan_context(app1),
            AsyncClient(transport=ASGITransport(app=app1), base_url="http://app1") as c1,
        ):
            hdrs, ws_id = await bootstrap_admin_and_workspace(
                c1, email="story268@orcia.io", slug_suffix="story-26-8"
            )

            # 1. Deleted legacy endpoint must return 404/405
            legacy = await c1.post(
                "/api/v1/assistant/workflows/save-and-launch",
                headers=hdrs,
                json={"workspace_id": ws_id, "manifest_yaml": "uri: orcia://workflows/legacy\n"},
            )
            assert legacy.status_code in (404, 405)

            # 2. Observer header guard returns 403 ERR_OBSERVER_MODE_READ_ONLY
            obs_hdrs = {**hdrs, "X-Orcia-Access-Mode": "READ_ONLY_OBSERVER"}

            # 3. Create assistant turn -> approve with CONTINUE_IN_PROCESS
            t_resp = await c1.post(
                "/api/v1/assistant/turns",
                headers=hdrs,
                json={"workspace_id": ws_id, "user_prompt": "Draft governed delivery workflow."},
            )
            assert t_resp.status_code == 202, t_resp.text
            turn_id = t_resp.json()["turn_id"]

            obs_app = await c1.post(
                f"/api/v1/assistant/turns/{turn_id}/approve",
                headers=obs_hdrs,
                json={
                    "workspace_id": ws_id,
                    "proposal_id": "prop-obs-pg",
                    "approved": True,
                    "human_anchor_markdown": "Blocked observer continuation attempt.",
                    "continue_in_process": True,
                },
            )
            assert obs_app.status_code == 403
            assert obs_app.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"

            app_resp = await c1.post(
                f"/api/v1/assistant/turns/{turn_id}/approve",
                headers=hdrs,
                json={
                    "workspace_id": ws_id,
                    "proposal_id": "prop-pg-268",
                    "approved": True,
                    "human_anchor_markdown": "Human signoff for process continuation.",
                    "continue_in_process": True,
                },
            )
            assert app_resp.status_code == 200, app_resp.text
            app_body = app_resp.json()
            run_turn_id = app_body["run_id"]
            assert run_turn_id
            assert app_body["dbos_workflow_id"] == f"assistant-process:{run_turn_id}"
            assert app_body["waiting_step_keys"] == ["frame-architecture-intent"]

            # 4. Create thematic folder -> launch durable process via DBOS + PG18
            f_resp = await c1.post(
                "/api/v1/assistant/folders",
                headers=hdrs,
                json={
                    "workspace_id": ws_id,
                    "title": "Story 26.8 Spec Folder",
                    "pinned_notes_markdown": "Enforce mandatory human anchors.",
                },
            )
            assert f_resp.status_code == 200, f_resp.text
            folder_id = f_resp.json()["folder_id"]

            fl_resp = await c1.post(
                f"/api/v1/assistant/folders/{folder_id}/launch-process",
                headers=hdrs,
                json={
                    "workspace_id": ws_id,
                    "target_workflow_uri": "orcia://pack-sdlc/workflows/ticket-to-tech-spec",
                },
            )
            assert fl_resp.status_code == 200, fl_resp.text
            fl_body = fl_resp.json()
            run_folder_id = fl_body["run_id"]
            assert run_folder_id
            assert fl_body["dbos_workflow_id"] == f"assistant-process:{run_folder_id}"
            assert fl_body["waiting_step_keys"] == ["frame-spec-human-anchor"]

        # Verify PG18 rows persisted after app1 shuts down
        async with engine.connect() as conn:
            run_row = (
                await conn.execute(
                    sa.text(
                        "SELECT status, trigger_idempotency_key "
                        "FROM workflow_runs WHERE id = CAST(:rid AS uuid)"
                    ),
                    {"rid": run_folder_id},
                )
            ).fetchone()
            assert run_row is not None
            assert run_row[0] == "WAITING_FOR_HUMAN_ARBITRATION"
            assert str(run_row[1]).startswith("assistant-process:folder:")

            step_rows = (
                await conn.execute(
                    sa.text(
                        "SELECT step_key, status FROM step_executions "
                        "WHERE run_id = CAST(:rid AS uuid) ORDER BY step_index ASC"
                    ),
                    {"rid": run_folder_id},
                )
            ).fetchall()
            assert [(r[0], r[1]) for r in step_rows] == [
                ("frame-spec-human-anchor", "WAITING_FOR_HUMAN_ANCHOR"),
                ("synthesize-spec-artifact", "PENDING"),
                ("post-spec-verification", "PENDING"),
            ]

            snap_count_before = (
                await conn.execute(
                    sa.text(
                        "SELECT COUNT(*) FROM blackboard_snapshots "
                        "WHERE run_id = CAST(:rid AS uuid)"
                    ),
                    {"rid": run_folder_id},
                )
            ).scalar_one()
            assert snap_count_before == 0

            outbox_types = (
                (
                    await conn.execute(
                        sa.text(
                            "SELECT event_type FROM domain_events_outbox "
                            "WHERE run_id = CAST(:rid AS uuid)"
                        ),
                        {"rid": run_folder_id},
                    )
                )
                .scalars()
                .all()
            )
            assert "HumanArbitrationRequested" in outbox_types

        # 5. Cold restart (`app2`): unsigned step fails 422, then human signature resumes DBOS
        app2 = create_app()
        async with (
            app2.router.lifespan_context(app2),
            AsyncClient(transport=ASGITransport(app=app2), base_url="http://app2") as c2,
        ):
            login = await c2.post(
                "/api/v1/auth/login/local",
                json={
                    "email": "story268@orcia.io",
                    "password": "Admin264b!StrongPassword",  # pragma: allowlist secret
                },
            )
            assert login.status_code == 200, login.text
            hdrs2 = {"Authorization": f"Bearer {login.json()['access_token']}"}

            unsigned = await c2.post(
                "/api/v1/orchestration/runs/steps/execute",
                headers=hdrs2,
                json={
                    "run_id": run_folder_id,
                    "step_key": "frame-spec-human-anchor",
                    "commit_immediately": True,
                },
            )
            assert unsigned.status_code == 422, unsigned.text
            assert unsigned.json()["error_code"] == "ERR_HUMAN_ANCHOR_REQUIRED"

            signed = await c2.post(
                "/api/v1/orchestration/runs/anchors/sign",
                headers=hdrs2,
                json={
                    "run_id": run_folder_id,
                    "step_key": "frame-spec-human-anchor",
                    "section_key": "primary-anchor",
                    "content_text": (
                        "Human anchor signed after cold restart to resume durable DBOS run."
                    ),
                    "signature_text": "Admin Story 26.8",
                    "author_type": "HUMAN",
                },
            )
            assert signed.status_code == 200, signed.text

        # Verify downstream completion & append-only snapshots + outbox in PG18
        async with engine.connect() as conn:
            final_status = (
                await conn.execute(
                    sa.text("SELECT status FROM workflow_runs WHERE id = CAST(:rid AS uuid)"),
                    {"rid": run_folder_id},
                )
            ).scalar_one()
            assert final_status == "COMPLETED"

            final_steps = (
                await conn.execute(
                    sa.text(
                        "SELECT step_key, status FROM step_executions "
                        "WHERE run_id = CAST(:rid AS uuid) ORDER BY step_index ASC"
                    ),
                    {"rid": run_folder_id},
                )
            ).fetchall()
            assert [(r[0], r[1]) for r in final_steps] == [
                ("frame-spec-human-anchor", "COMMITTED"),
                ("synthesize-spec-artifact", "COMMITTED"),
                ("post-spec-verification", "COMMITTED"),
            ]

            snap_count_after = (
                await conn.execute(
                    sa.text(
                        "SELECT COUNT(*) FROM blackboard_snapshots "
                        "WHERE run_id = CAST(:rid AS uuid)"
                    ),
                    {"rid": run_folder_id},
                )
            ).scalar_one()
            assert snap_count_after == 3

            all_outbox = (
                (
                    await conn.execute(
                        sa.text(
                            "SELECT event_type FROM domain_events_outbox "
                            "WHERE run_id = CAST(:rid AS uuid)"
                        ),
                        {"rid": run_folder_id},
                    )
                )
                .scalars()
                .all()
            )
            assert "StepCompleted" in all_outbox
            assert "ArtifactProduced" in all_outbox
            assert "RunTerminated" in all_outbox

            turn_run_status = (
                await conn.execute(
                    sa.text("SELECT status FROM workflow_runs WHERE id = CAST(:rid AS uuid)"),
                    {"rid": run_turn_id},
                )
            ).scalar_one()
            assert turn_run_status == "WAITING_FOR_HUMAN_ARBITRATION"
    finally:
        await engine.dispose()
