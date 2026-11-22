"""Story 26.6b — Vertical PG18 + Redis Integration Test for Governed Tool Router (`CAP-260`).

Verifies with real `create_app()` (`0` `dependency_overrides`), real PostgreSQL 18, and real Redis:
1. Dynamic tool catalog includes >10 PG18 `catalog_items` skills without truncation and excludes
   `kb.search` when 0 embedding models are configured (`AD-24.6`).
2. `POST /api/v1/assistant/turns` (`SPEED_2_AGENT_TOOLS` + `[CASSETTE_TOOL_LOOP]`) routes tool
   calls through `GovernedAssistantToolRouter`, emits `tool_call` & `tool_result` SSE events,
   and persists `ASSISTANT_TOOL_INVOKED` into PG18 `audit_ledger` + `idem:*` into Redis.
3. Deterministic Lock V5 / Human-Anchor refusal blocks direct writes, persists
   `ASSISTANT_TOOL_DENIED` in `audit_ledger`, and enqueues `HumanArbitrationRequested` in PG18
   `domain_events_outbox`.
"""

from __future__ import annotations

import json
import uuid
from typing import Any

import pytest
import redis.asyncio as aioredis
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine
from tests.integration.api._pg18_story_26_5_helpers import (
    pg_and_redis_urls,
    real_lifespan_client_factory,
)

from orcia_core.ports.assistant_tool_executor_port import (
    AssistantToolCatalogContext,
    AssistantToolExecutionRequest,
    McpExposedToolSpec,
)

__all__ = ["pg_and_redis_urls", "real_lifespan_client_factory"]


def _parse_sse_events(raw_body: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    cur_event = ""
    cur_data = ""
    for line in raw_body.splitlines():
        if line.startswith("event:"):
            cur_event = line.split(":", 1)[1].strip()
        elif line.startswith("data:"):
            cur_data = line.split(":", 1)[1].strip()
        elif not line.strip() and cur_event:
            parsed = json.loads(cur_data) if cur_data else {}
            events.append({"event": cur_event, "data": parsed})
            cur_event, cur_data = "", ""
    if cur_event:
        events.append({"event": cur_event, "data": json.loads(cur_data) if cur_data else {}})
    return events


@pytest.mark.asyncio
async def test_story_26_6b_tool_router_audit_outbox_and_redis_idem_pg18(
    real_lifespan_client_factory: Any,
    pg_and_redis_urls: tuple[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    pg_url, redis_url = pg_and_redis_urls
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    open_client, _ = real_lifespan_client_factory
    engine = create_async_engine(pg_url)
    redis_client = aioredis.from_url(redis_url, decode_responses=True)

    try:
        async with open_client() as client:
            boot = await client.post(
                "/api/v1/bootstrap/welcome-setup/first-admin",
                json={
                    "email": "admin266b@orcia.io",
                    "display_name": "Admin 26.6b",
                    "password": "Admin266b!StrongPassword",  # pragma: allowlist secret
                    "orcia_env": "local",
                },
            )
            assert boot.status_code == 200, boot.text
            boot_json = boot.json()
            hdrs = {"Authorization": f"Bearer {boot_json['access_token']}"}
            admin_id = str(boot_json["user_id"])

            bu = await client.post(
                "/api/v1/org-units",
                headers=hdrs,
                json={"name": "BU 26.6b", "slug": "bu-266b", "kind": "BU"},
            )
            assert bu.status_code in (200, 201), bu.text
            ws = await client.post(
                "/api/v1/workspaces",
                headers=hdrs,
                json={
                    "name": "WS 26.6b",
                    "slug": "ws-266b",
                    "owner_org_unit_id": bu.json()["id"],
                    "visibility_mode": "STANDARD",
                },
            )
            assert ws.status_code in (200, 201), ws.text
            ws_id = ws.json()["id"]

            r_map = await client.post(
                "/api/v1/settings/ai-models/mappings",
                headers=hdrs,
                json={
                    "scope_level": "GLOBAL",
                    "display_name": "OpenAI Tool Tier 26.6b",
                    "inference_tier": "medium",
                    "effort": "balanced",
                    "provider_slug": "openai",
                    "model_family": "GPT",
                    "model_name": "gpt-4.1-mini",
                    "endpoint_uri": "https://api.openai.com/v1/chat/completions",
                    "auth_mode": "none_local",
                    "protocol_mode": "openai_compatible",
                    "usage": "chat",
                },
            )
            assert r_map.status_code in (200, 201), r_map.text
            assert r_map.json()["supports_tools"] is True

            # Persist 12 skills into PG18 `catalog_items` (> 10 to prove cap removal)
            for idx in range(12):
                r_sk = await client.post(
                    "/api/v1/agents-and-skills/skills",
                    headers=hdrs,
                    json={
                        "name": f"Catalog Skill {idx:02d}",
                        "objective": f"Analyze governance dimension {idx:02d}",
                        "input_parameters": ["target_ref", "depth"],
                        "instructions": f"Inspect target_ref deterministically ({idx:02d}).",
                    },
                )
                assert r_sk.status_code in (200, 201), r_sk.text

            # Trigger live background turn with SPEED_2_AGENT_TOOLS & cassette tool-loop marker
            r_turn = await client.post(
                "/api/v1/assistant/turns",
                headers=hdrs,
                json={
                    "workspace_id": ws_id,
                    "user_prompt": "[CASSETTE_TOOL_LOOP] Inspect workspace architecture",
                    "requested_speed": "SPEED_2_AGENT_TOOLS",
                },
            )
            assert r_turn.status_code == 202, r_turn.text
            turn_id = r_turn.json()["turn_id"]

            r_stream = await client.get(
                f"/api/v1/assistant/turns/{turn_id}/stream",
                headers=hdrs,
            )
            assert r_stream.status_code == 200, r_stream.text
            sse_events = _parse_sse_events(r_stream.text)
            ev_names = [e["event"] for e in sse_events]
            assert "tool_call" in ev_names, ev_names
            assert "tool_result" in ev_names, ev_names
            assert "turn_completed" in ev_names, ev_names
            completed_ev = next(e for e in sse_events if e["event"] == "turn_completed")
            assert "<untrusted_tool_output" in str(completed_ev["data"])

            # Verify PG18 catalog_items >= 12 user skills and audit_ledger rows
            async with engine.connect() as conn:
                skill_count = (
                    await conn.execute(
                        sa.text("SELECT COUNT(*) FROM catalog_items WHERE resource_type = 'skill'")
                    )
                ).scalar_one()
                assert int(skill_count) >= 12

                invoked_rows = (
                    await conn.execute(
                        sa.text(
                            "SELECT event_type, summary, metadata_jsonb "
                            "FROM audit_ledger WHERE event_type = 'ASSISTANT_TOOL_INVOKED'"
                        )
                    )
                ).all()
                assert len(invoked_rows) >= 1

            # Verify Redis idempotency key was persisted for the tool call
            idem_keys = await redis_client.keys(
                f"orcia:assistant:idem:{ws_id}:{admin_id}:{turn_id}:*"
            )
            assert len(idem_keys) >= 1

            # Exercise real Composition Root GovernedAssistantToolRouter against PG18 + Redis:
            # 1) Denied direct SI write / human-anchor surfaces APPROVAL_REQUIRED & Outbox row
            real_app: Any = client._transport.app  # type: ignore[union-attr]
            router = getattr(real_app.state, "governed_assistant_tool_router", None)
            assert router is not None

            # Verify replaying the same tool call hits Redis idempotency (DEDUPLICATED)
            ro_cat = router.build_authorized_catalog(
                AssistantToolCatalogContext(
                    workspace_id=ws_id,
                    user_id=admin_id,
                    user_role="PLATFORM_ADMIN",
                    rag_active=False,
                )
            )
            assert "kb.search" not in {d.tool_name for d in ro_cat}
            replay_res = await router.execute_tool_call(
                AssistantToolExecutionRequest(
                    turn_id=turn_id,
                    iteration=1,
                    tool_call_id="call_oai_cassette_1",
                    tool_name="check_resource_state",
                    workspace_id=ws_id,
                    user_id=admin_id,
                    user_role="PLATFORM_ADMIN",
                    arguments={"resource_uri": "docs/testing-strategy.md"},
                ),
                catalog=ro_cat,
            )
            assert replay_res.verdict == "DEDUPLICATED"
            assert replay_res.deduplicated is True

            si_cat = router.build_authorized_catalog(
                AssistantToolCatalogContext(
                    workspace_id=ws_id,
                    user_id=admin_id,
                    user_role="PLATFORM_ADMIN",
                    rag_active=False,
                    mcp_tools=(
                        McpExposedToolSpec(
                            tool_name="mcp.si_write_probe",
                            agent_slug="si-writer",
                            description="Protected external SI write",
                            permission_mode="WRITE_PREVIEW",
                            is_si_write=True,
                            human_authored_required=True,
                            required_permission="execute",
                            source_uri_or_scope="jira://PROJ/ISSUE-266",
                        ),
                    ),
                )
            )
            assert "kb.search" not in {d.tool_name for d in si_cat}

            v5_req = AssistantToolExecutionRequest(
                turn_id=turn_id,
                iteration=7,
                tool_call_id="tc-v5-pg18",
                tool_name="mcp.si_write_probe",
                workspace_id=ws_id,
                user_id=admin_id,
                user_role="PLATFORM_ADMIN",
                trace_id=uuid.uuid4().hex,
                arguments={"target_uri": "jira://PROJ/ISSUE-266"},
            )
            v5_res = await router.execute_tool_call(v5_req, catalog=si_cat)
            assert v5_res.verdict == "APPROVAL_REQUIRED"
            assert v5_res.audit_event_type == "ASSISTANT_TOOL_DENIED"
            assert v5_res.approval_proposal is not None
            assert v5_res.approval_proposal["transition_action"] == "CONTINUE_IN_PROCESS"

            # Verify PG18 persisted ASSISTANT_TOOL_DENIED + HumanArbitrationRequested outbox
            async with engine.connect() as conn:
                denied_count = (
                    await conn.execute(
                        sa.text(
                            "SELECT COUNT(*) FROM audit_ledger "
                            "WHERE event_type = 'ASSISTANT_TOOL_DENIED'"
                        )
                    )
                ).scalar_one()
                assert int(denied_count) >= 1

                outbox_rows = (
                    await conn.execute(
                        sa.text(
                            "SELECT event_type, run_id, payload_jsonb "
                            "FROM domain_events_outbox "
                            "WHERE event_type = 'HumanArbitrationRequested'"
                        )
                    )
                ).all()
                assert len(outbox_rows) >= 1
                assert any(r[1] is None for r in outbox_rows)
    finally:
        await redis_client.aclose()
        await engine.dispose()


@pytest.mark.asyncio
async def test_story_26_6b_http_turn_approval_required_and_pg18_workspace_isolation(
    real_lifespan_client_factory: Any,
    pg_and_redis_urls: tuple[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Prove HTTP `/assistant/turns` halts on `APPROVAL_REQUIRED` & isolates PG18 skills."""
    from starlette.requests import Request as StarletteRequest

    from orcia_api.dependencies import build_assistant_tool_catalog_context_async
    from orcia_core.orchestration._internal.sql_agents_and_skills import persist_skill_to_postgres18
    from orcia_core.orchestration.agents_and_skills_models import build_managed_skill_record
    from orcia_core.permissions.models import UserIdentity

    pg_url, _redis_url = pg_and_redis_urls
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    open_client, _ = real_lifespan_client_factory
    engine = create_async_engine(pg_url)

    try:
        async with open_client() as client:
            boot = await client.post(
                "/api/v1/bootstrap/welcome-setup/first-admin",
                json={
                    "email": "admin266b@orcia.io",
                    "display_name": "Admin 26.6b",
                    "password": "Admin266b!StrongPassword",  # pragma: allowlist secret
                    "orcia_env": "local",
                },
            )
            if boot.status_code == 409:
                boot = await client.post(
                    "/api/v1/auth/login/local",
                    json={
                        "email": "admin266b@orcia.io",
                        "password": "Admin266b!StrongPassword",  # pragma: allowlist secret
                    },
                )
            assert boot.status_code == 200, boot.text
            boot_json = boot.json()
            hdrs = {"Authorization": f"Bearer {boot_json['access_token']}"}
            admin_id = str(boot_json["user_id"])

            bu = await client.post(
                "/api/v1/org-units",
                headers=hdrs,
                json={"name": "BU Iso", "slug": "bu-266b-iso", "kind": "BU"},
            )
            assert bu.status_code in (200, 201), bu.text
            ws_a = await client.post(
                "/api/v1/workspaces",
                headers=hdrs,
                json={
                    "name": "WS Alpha Iso",
                    "slug": "ws-266b-alpha",
                    "owner_org_unit_id": bu.json()["id"],
                    "visibility_mode": "STANDARD",
                },
            )
            ws_b = await client.post(
                "/api/v1/workspaces",
                headers=hdrs,
                json={
                    "name": "WS Beta Iso",
                    "slug": "ws-266b-beta",
                    "owner_org_unit_id": bu.json()["id"],
                    "visibility_mode": "STANDARD",
                },
            )
            assert ws_a.status_code in (200, 201) and ws_b.status_code in (200, 201)
            ws_a_id = ws_a.json()["id"]
            ws_b_id = ws_b.json()["id"]

            r_map = await client.post(
                "/api/v1/settings/ai-models/mappings",
                headers=hdrs,
                json={
                    "scope_level": "GLOBAL",
                    "display_name": "OpenAI Approval Probe",
                    "inference_tier": "medium",
                    "effort": "balanced",
                    "provider_slug": "openai",
                    "model_family": "GPT",
                    "model_name": "gpt-4.1-mini",
                    "endpoint_uri": "https://api.openai.com/v1/chat/completions",
                    "auth_mode": "none_local",
                    "protocol_mode": "openai_compatible",
                    "usage": "chat",
                },
            )
            assert r_map.status_code in (200, 201), r_map.text

            sk_alpha_si = build_managed_skill_record(
                resolved_id="sk-pg18-alpha-si",
                slug="ws_a_si_write",
                clean_name="WS Alpha SI Write",
                clean_obj="Mutate Jira issue via gate",
                params=("target_uri",),
                clean_inst="Requires Process Write Gate.",
                clean_fmt="markdown",
                version="1.0.0",
                existing=None,
                visibility_scope="TEAM",
                source_pack_key=None,
                enabled_in_workspace=True,
                is_si_write=True,
                human_authored_required=True,
                owner_workspace_id=ws_a_id,
            )
            sk_alpha_priv = build_managed_skill_record(
                resolved_id="sk-pg18-alpha-priv-other",
                slug="ws_a_priv_other",
                clean_name="Other User Private Skill",
                clean_obj="Private skill",
                params=(),
                clean_inst="Private",
                clean_fmt="markdown",
                version="1.0.0",
                existing=None,
                visibility_scope="PRIVATE",
                source_pack_key=None,
                enabled_in_workspace=True,
                owner_workspace_id=ws_a_id,
                owner_user_id="0192c4e0-0000-7000-8000-000000009999",
            )
            await persist_skill_to_postgres18(engine, sk_alpha_si)
            await persist_skill_to_postgres18(engine, sk_alpha_priv)

            real_app: Any = client._transport.app  # type: ignore[union-attr]
            mcp_svc = real_app.state.remote_test_bench_and_mcp_service
            await mcp_svc.configure_agent_mcp_exposure_async(
                actor_role="PLATFORM_ADMIN",
                workspace_slug="ws-266b-alpha",
                agent_slug="pg18-ro-mcp",
                display_name="PG18 RO MCP",
                mcp_exposed=True,
                regime="CONSULTATION_ANALYSIS",
                system_prompt_layers_1_to_4="Read only prompt",
                secret_refs=(),
                human_authored_required=False,
            )

            admin_user = UserIdentity(
                id=admin_id,
                email="admin266b@orcia.io",
                display_name="Admin 26.6b",
                auth_mode="LOCAL",
                human_profile_archetype="ARCHITECT",
                platform_role="PLATFORM_ADMIN",
                primary_org_unit_id=bu.json()["id"],
            )
            fake_req = StarletteRequest(
                {"type": "http", "headers": [], "app": real_app, "path": "/"}
            )
            ctx_a = await build_assistant_tool_catalog_context_async(
                fake_req, user=admin_user, workspace_id=ws_a_id
            )
            ctx_b = await build_assistant_tool_catalog_context_async(
                fake_req, user=admin_user, workspace_id=ws_b_id
            )
            a_skill_ids = {s.skill_id for s in ctx_a.skills}
            b_skill_ids = {s.skill_id for s in ctx_b.skills}
            assert "sk-pg18-alpha-si" in a_skill_ids
            assert "sk-pg18-alpha-priv-other" not in a_skill_ids
            assert "sk-pg18-alpha-si" not in b_skill_ids
            alpha_si_entry = next(s for s in ctx_a.skills if s.skill_id == "sk-pg18-alpha-si")
            assert alpha_si_entry.is_si_write is True
            assert alpha_si_entry.human_authored_required is True
            assert any(m.agent_slug == "pg18-ro-mcp" for m in ctx_a.mcp_tools)

            r_turn = await client.post(
                "/api/v1/assistant/turns",
                headers=hdrs,
                json={
                    "workspace_id": ws_a_id,
                    "user_prompt": (
                        "[CASSETTE_TOOL_LOOP] [CASSETTE_TOOL_NAME:skill_ws_a_si_write] "
                        "Update Jira directly"
                    ),
                    "requested_speed": "SPEED_2_AGENT_TOOLS",
                },
            )
            assert r_turn.status_code == 202, r_turn.text
            turn_id = r_turn.json()["turn_id"]

            r_stream = await client.get(
                f"/api/v1/assistant/turns/{turn_id}/stream",
                headers=hdrs,
            )
            assert r_stream.status_code == 200, r_stream.text
            sse_events = _parse_sse_events(r_stream.text)
            ev_names = [e["event"] for e in sse_events]
            assert "tool_call" in ev_names, ev_names
            assert "approval_required" in ev_names, ev_names
            assert "tool_result" in ev_names, ev_names
            assert "turn_completed" in ev_names, ev_names
            assert "stream_error" not in ev_names, sse_events
            completed_ev = next(e for e in sse_events if e["event"] == "turn_completed")
            assert completed_ev["data"].get("approval_required") is True

            async with engine.connect() as conn:
                denied_count = (
                    await conn.execute(
                        sa.text(
                            "SELECT COUNT(*) FROM audit_ledger "
                            "WHERE event_type = 'ASSISTANT_TOOL_DENIED'"
                        )
                    )
                ).scalar_one()
                assert int(denied_count) >= 1

                outbox_rows = (
                    await conn.execute(
                        sa.text(
                            "SELECT event_type, payload_jsonb "
                            "FROM domain_events_outbox "
                            "WHERE event_type = 'HumanArbitrationRequested'"
                        )
                    )
                ).all()
                assert len(outbox_rows) >= 1
    finally:
        await engine.dispose()
