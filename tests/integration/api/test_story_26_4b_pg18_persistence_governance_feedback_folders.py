"""Story 26.4b — Layer 2 Real PG18 Vertical Integration Tests (`create_app()`, 0 overrides)."""

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
async def test_vertical_pg18_persistence_across_cold_restart_real_create_app(
    pg18_db_url: str,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify Mode A, feedback, folders meta, and phantom audit survive fresh create_app()."""
    configure_pg18_test_env(monkeypatch, pg18_db_url)
    engine = create_async_engine(pg18_db_url)
    try:
        app1 = create_app()
        assert app1.dependency_overrides == {}
        async with (
            app1.router.lifespan_context(app1),
            AsyncClient(transport=ASGITransport(app=app1), base_url="http://app1") as c1,
        ):
            hdrs, ws_id = await bootstrap_admin_and_workspace(
                c1, email="admin264b@orcia.io", slug_suffix="26-4b"
            )

            assert (
                await c1.put(
                    "/api/v1/assistant/governance/mode-a/user",
                    headers=hdrs,
                    json={
                        "workspace_id": ws_id,
                        "response_tone": "SYNTHETIC",
                        "favorite_format": "BULLETS_SUMMARY",
                        "default_hat": "SECOPS",
                        "personal_instructions": "Persist USER layer in PG18.",
                    },
                )
            ).status_code == 200
            assert (
                await c1.put(
                    "/api/v1/assistant/governance/mode-a/workspace",
                    headers=hdrs,
                    json={
                        "workspace_id": ws_id,
                        "workspace_instructions": "Persist WORKSPACE layer in PG18.",
                        "default_checked_sources": ["orcia://sources/main"],
                        "recommended_agents": ["@security-reviewer"],
                        "arbitration_policy": "AUTO_RESOLVE_WITH_TRACE",
                        "mcp_expose_assistant": False,
                    },
                )
            ).status_code == 200

            r_mb = await c1.post(
                "/api/v1/assistant/governance/mode-b/save",
                headers=hdrs,
                json={
                    "scope_level": "WORKSPACE",
                    "scope_id": ws_id,
                    "ai_pre_prompt": "x",
                    "nodes": [],
                },
            )
            assert r_mb.status_code in (404, 405)

            turn_v2_id = new_uuid7_str()
            assert (
                await c1.post(
                    f"/api/v1/assistant/turns/{turn_v2_id}/feedback",
                    headers=hdrs,
                    json={
                        "workspace_id": ws_id,
                        "rating": "down",
                        "reason_code": "MISSING_SOURCE",
                        "comment": "Initial feedback",
                    },
                )
            ).status_code == 200
            assert (
                await c1.post(
                    f"/api/v1/assistant/turns/{turn_v2_id}/feedback",
                    headers=hdrs,
                    json={
                        "workspace_id": ws_id,
                        "rating": "up",
                        "reason_code": "VERIFIED",
                        "comment": "Updated feedback",
                    },
                )
            ).status_code == 200

            turn_legacy_id = new_uuid7_str()
            assert (
                await c1.post(
                    "/api/v1/assistant/three-speed/feedback",
                    headers=hdrs,
                    json={
                        "workspace_id": ws_id,
                        "turn_id": turn_legacy_id,
                        "user_feedback": "LIKE",
                    },
                )
            ).status_code in (404, 405)

            r_fld = await c1.post(
                "/api/v1/assistant/folders",
                headers=hdrs,
                json={
                    "workspace_id": ws_id,
                    "title": "Folder 26.4b Meta",
                    "pinned_notes_markdown": "Keep PCI scope intact.",
                    "working_attachments_uris": ["orcia://drafts/spec@draft"],
                    "evidence_tags": ["S1", "G2"],
                },
            )
            assert r_fld.status_code == 200, r_fld.text
            folder_id = r_fld.json()["folder_id"]

            assert (
                await c1.post(
                    "/api/v1/assistant/folders",
                    headers=hdrs,
                    json={
                        "folder_id": folder_id,
                        "workspace_id": ws_id,
                        "title": "Folder 26.4b Meta Updated",
                        "pinned_notes_markdown": "Keep PCI scope intact v2.",
                        "working_attachments_uris": ["orcia://drafts/spec@draft", "orcia://kb/adr"],
                        "evidence_tags": ["S1", "G2", "O1"],
                    },
                )
            ).status_code == 200
            assert (
                await c1.post(
                    f"/api/v1/assistant/folders/{folder_id}/share",
                    headers=hdrs,
                    json={"workspace_id": ws_id, "visibility_mode": "WORKSPACE_OPEN", "shares": []},
                )
            ).status_code == 200

            gov_svc = app1.state.assistant_governance_service
            await gov_svc.freeze_mcp_at_upper_layer_async(
                workspace_id=ws_id, frozen=True, origin="TEAM"
            )
            r_funnel = await c1.put(
                "/api/v1/assistant/governance/mode-a/workspace",
                headers=hdrs,
                json={
                    "workspace_id": ws_id,
                    "workspace_instructions": "Blocked MCP reopen",
                    "default_checked_sources": [],
                    "recommended_agents": [],
                    "arbitration_policy": "PAUSE_AND_ESCALATE",
                    "mcp_expose_assistant": True,
                },
            )
            assert r_funnel.status_code == 403
            assert r_funnel.json()["error_code"] == "ERR_FUNNEL_RULE_VIOLATION"
            await gov_svc.freeze_mcp_at_upper_layer_async(
                workspace_id=ws_id, frozen=False, origin="TEAM"
            )
            layers = await gov_svc.assemble_five_layers_preview_async(
                workspace_id=ws_id, user_id="admin"
            )
            assert len(layers) == 5

            assert (
                await c1.post(
                    "/api/v1/assistant/citations/verify-turn",
                    headers=hdrs,
                    json={"workspace_id": ws_id, "response_text": "Claim [S99] unverified."},
                )
            ).status_code in (404, 405)
            from orcia_core.audit_finops._internal.sql_audit_ledger import SqlAuditLedgerService
            from orcia_core.orchestration.assistant_citations_and_v5_guard import (
                AssistantCitationAndV5GuardService,
            )

            cit_guard = AssistantCitationAndV5GuardService(
                audit_ledger_sink=SqlAuditLedgerService(engine=engine)
            )
            await cit_guard.verify_and_sanitize_citations_async(
                response_text="Claim [S99] unverified.",
                evidence_table=cit_guard.build_evidence_table(sources=()),
                workspace_id=ws_id,
                user_id="admin264b@orcia.io",
                turn_id=turn_v2_id,
            )
            assert (
                await c1.post(
                    "/api/v1/assistant/artifacts/action",
                    headers=hdrs,
                    json={
                        "workspace_id": ws_id,
                        "action_type": "SAVE_DRAFT",
                        "artifact_title": "Removed in 26.7",
                        "artifact_content": "Draft content",
                    },
                )
            ).status_code in (404, 405)

        app2 = create_app()
        async with (
            app2.router.lifespan_context(app2),
            AsyncClient(transport=ASGITransport(app=app2), base_url="http://app2") as c2,
        ):
            login = await c2.post(
                "/api/v1/auth/login/local",
                json={
                    "email": "admin264b@orcia.io",
                    "password": "Admin264b!StrongPassword",  # pragma: allowlist secret
                },
            )
            hdrs2 = {"Authorization": f"Bearer {login.json()['access_token']}"}
            gov2 = (
                await c2.get(
                    "/api/v1/assistant/governance", headers=hdrs2, params={"workspace_id": ws_id}
                )
            ).json()
            assert "studio_graph" not in gov2
            assert (
                gov2["user_preferences"]["personal_instructions"] == "Persist USER layer in PG18."
            )
            assert (
                gov2["workspace_settings"]["workspace_instructions"]
                == "Persist WORKSPACE layer in PG18."
            )
            assert gov2["workspace_settings"]["mcp_expose_assistant"] is False

            ov2 = (
                await c2.get(f"/api/v1/assistant/workspaces/{ws_id}/overview", headers=hdrs2)
            ).json()
            matched = [f for f in ov2["folders"] if f["folder_id"] == folder_id]
            assert len(matched) == 1
            assert matched[0]["working_attachments_uris"] == [
                "orcia://drafts/spec@draft",
                "orcia://kb/adr",
            ]
            assert matched[0]["evidence_tags"] == ["S1", "G2", "O1"]

        async with engine.connect() as conn:
            ov_count = (
                await conn.execute(
                    sa.text(
                        "SELECT COUNT(*) FROM workspace_customization_overrides "
                        "WHERE workspace_id = CAST(:ws AS uuid)"
                    ),
                    {"ws": ws_id},
                )
            ).scalar_one()
            assert ov_count >= 2
            fb_rows = (
                (
                    await conn.execute(
                        sa.text(
                            "SELECT turn_id::text, rating, comment "
                            "FROM assistant_turn_feedback "
                            "WHERE workspace_id = CAST(:ws AS uuid)"
                        ),
                        {"ws": ws_id},
                    )
                )
                .mappings()
                .all()
            )
            by_turn = {str(r["turn_id"]): r for r in fb_rows}
            assert len(by_turn) == 1 and by_turn[turn_v2_id]["rating"] == "up"
            ledger_count = (
                await conn.execute(
                    sa.text(
                        "SELECT COUNT(*) FROM audit_ledger "
                        "WHERE workspace_id = CAST(:ws AS uuid) "
                        "AND event_type = 'ASSISTANT_PHANTOM_CITATION_PURGED'"
                    ),
                    {"ws": ws_id},
                )
            ).scalar_one()
            assert ledger_count >= 1
    finally:
        await engine.dispose()
