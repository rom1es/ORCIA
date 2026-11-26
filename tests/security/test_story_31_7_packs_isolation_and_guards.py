"""Story 31.7 Regression Security Tests for P0-1, P1-1 & P1-2 (`<= 280 L`)."""

from __future__ import annotations

import base64
import json
from typing import Any
from unittest.mock import AsyncMock

import pytest
from httpx import ASGITransport, AsyncClient
from tests.security._packs_red_team_fixtures import (
    WS_A,
    WS_B,
    apm_yml,
    setup_packs_red_team_app,
    zip_of,
)
from tests.unit.packs._fake_sql_engine import FakeSqlEngine, FakeSqlResult
from uuid_utils import uuid7

from orcia_api.dependencies import get_remote_test_bench_and_mcp_service
from orcia_api.dependencies.pack_import_deps import get_pack_bundle_v2_repository
from orcia_core.orchestration import load_agents_and_skills_from_postgres18
from orcia_core.packs import PackSlotUnboundError


@pytest.mark.asyncio
async def test_p0_1_packs_catalog_health_visibility_and_global_scope_escalation(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify GET /api/v1/packs & /health filter cross-tenant bundles and reject GLOBAL import."""
    sys_id, wsa_id, wsb_id = str(uuid7()), str(uuid7()), str(uuid7())
    extra_rows = [
        {
            "id": sys_id,
            "pack_id": "orcia-pack-sdlc",
            "slug": "sdlc",
            "name": "SDLC",
            "version": "1.0.0",
            "rbac_namespace": "default",
            "bundle_kind": "SYSTEM",
            "scope_type": "GLOBAL",
            "scope_id": "global",
            "status": "PUBLISHED",
            "source_origin": "LOCAL_SYSTEM",
            "archive_sha256": "b" * 64,
            "cas_object_key": None,
            "manifest": {"description": "System", "counts": {}},
            "declared_slots": [],
        },
        {
            "id": wsa_id,
            "pack_id": "orcia-pack-wsa",
            "slug": "wsa-pack",
            "name": "WS A Pack",
            "version": "1.0.0",
            "rbac_namespace": "default",
            "bundle_kind": "CUSTOM",
            "scope_type": "WORKSPACE",
            "scope_id": WS_A,
            "status": "PUBLISHED",
            "source_origin": "ORCIA_COMPOSER",
            "archive_sha256": "c" * 64,
            "cas_object_key": None,
            "manifest": {"description": "WS A", "counts": {}},
            "declared_slots": [
                {"slot_key": "repo-a", "scheme": "git", "connector_kind": "mcp:git"}
            ],  # noqa: E501
        },
        {
            "id": wsb_id,
            "pack_id": "orcia-pack-wsb",
            "slug": "wsb-pack",
            "name": "WS B Pack",
            "version": "1.0.0",
            "rbac_namespace": "default",
            "bundle_kind": "CUSTOM",
            "scope_type": "WORKSPACE",
            "scope_id": WS_B,
            "status": "PUBLISHED",
            "source_origin": "ORCIA_COMPOSER",
            "archive_sha256": "d" * 64,
            "cas_object_key": None,
            "manifest": {"description": "WS B", "counts": {}},
            "declared_slots": [
                {"slot_key": "secret-b", "scheme": "db", "connector_kind": "mcp:db"}
            ],  # noqa: E501
        },
    ]
    app, tokens = setup_packs_red_team_app(
        monkeypatch,
        draft_id=wsb_id,
        leak_desc="Scoped",
        draft_scope_id=WS_B,
        extra_rows=extra_rows,
    )
    app.dependency_overrides[get_pack_bundle_v2_repository] = lambda: type(
        "_StubRepo",
        (),
        {"_engine": object(), "list_bundles_v2": AsyncMock(return_value=extra_rows)},
    )()
    marc_hdr = {"Authorization": f"Bearer {tokens['marc']}"}
    karim_hdr = {"Authorization": f"Bearer {tokens['karim']}"}
    global_b64 = base64.b64encode(
        zip_of({"apm.yml": apm_yml(scope_type="GLOBAL", scope_id="global")})
    ).decode("ascii")

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r_marc = await client.get("/api/v1/packs", headers=marc_hdr)
        assert r_marc.status_code == 200
        assert {p["slug"] for p in r_marc.json()["packs"]} == {"sdlc", "wsa-pack"}

        r_health = await client.get("/api/v1/packs/health", headers=marc_hdr)
        assert r_health.status_code == 200
        assert {c["connector_type"] for c in r_health.json()["connectors"]} == {"mcp:git"}

        r_admin = await client.get("/api/v1/packs", headers=karim_hdr)
        assert r_admin.status_code == 200
        assert {p["slug"] for p in r_admin.json()["packs"]} == {"sdlc", "wsa-pack", "wsb-pack"}

        r_esc = await client.post(
            "/api/v1/packs/import", headers=marc_hdr, json={"zip_base64": global_b64}
        )
        assert r_esc.status_code == 403
        assert r_esc.json()["error_code"] == "ERR_PACK_SCOPE_ESCALATION_FORBIDDEN"


@pytest.mark.asyncio
async def test_p1_1_agents_skills_block_unactivated_custom_and_foreign_workspace_leak() -> None:
    """Verify unactivated custom packs & foreign workspace rows never leak into WS_A."""
    b_sys, b_unact, b_other = str(uuid7()), str(uuid7()), str(uuid7())
    rows = [
        (
            "sdlc:reviewer",
            "orcia://packs/sdlc/agents/reviewer@1.0.0",
            "SDLC Reviewer",
            "System",
            "agent",
            "1.0.0",
            "a" * 64,
            "USER_AGENT",
            json.dumps({"slug": "reviewer", "lifecycle_status": "ACTIVE"}),
            None,
            "sdlc",
            "SYSTEM",
            b_sys,
            "GLOBAL",
            "global",
        ),
        (
            "unact:reviewer",
            "orcia://packs/unact/agents/reviewer@1.0.0",
            "Unactivated",
            "Should stay hidden",
            "agent",
            "1.0.0",
            "b" * 64,
            "USER_AGENT",
            json.dumps({"slug": "reviewer", "lifecycle_status": "ACTIVE"}),
            None,
            "unact",
            "CUSTOM",
            b_unact,
            "WORKSPACE",
            WS_A,
        ),
        (
            "other-ws:reviewer",
            "orcia://packs/other-ws/agents/reviewer@1.0.0",
            "Foreign Pack",
            "WS_B pack",
            "agent",
            "1.0.0",
            "c" * 64,
            "USER_AGENT",
            json.dumps({"slug": "reviewer", "lifecycle_status": "ACTIVE"}),
            None,
            "other-ws",
            "CUSTOM",
            b_other,
            "WORKSPACE",
            WS_B,
        ),
        (
            "agent-wsb-only",
            "orcia://agents/wsb-only@1.0.0",
            "WS B Agent",
            "Standalone WS_B",
            "agent",
            "1.0.0",
            "d" * 64,
            "USER_AGENT",
            json.dumps({"slug": "wsb-only", "lifecycle_status": "ACTIVE"}),
            WS_B,
            None,
            None,
            None,
            None,
            None,
        ),
    ]

    def _sql(stmt: str, _params: dict[str, Any]) -> FakeSqlResult:
        low = stmt.lower()
        if "to_regclass('public.workspace_pack_activations')" in low:
            return FakeSqlResult(scalar_val="workspace_pack_activations")
        if "from workspace_pack_activations" in low:
            return FakeSqlResult(rows=[])
        if "to_regclass('public.workspaces')" in low:
            return FakeSqlResult(scalar_val="workspaces")
        if "from workspaces" in low:
            return FakeSqlResult(rows=[(WS_A, None)])
        if "from catalog_items" in low:
            return FakeSqlResult(rows=rows)
        return FakeSqlResult(rows=[])

    _, agents = await load_agents_and_skills_from_postgres18(FakeSqlEngine(_sql), workspace_id=WS_A)  # type: ignore[arg-type]
    assert [a.agent_id for a in agents] == ["sdlc:reviewer"]
    assert agents[0].resolution_tier == "SYSTEM_PACK"


@pytest.mark.asyncio
async def test_p1_2_slot_readiness_guard_blocks_assistant_and_mcp_before_llm_spend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify 422 ERR_PACK_SLOT_UNBOUND blocks /assistant/turns and /mcp/spaces/*/invoke."""
    app, tokens = setup_packs_red_team_app(
        monkeypatch, draft_id=str(uuid7()), leak_desc="Clean", draft_scope_id=WS_A
    )
    marc_hdr = {"Authorization": f"Bearer {tokens['marc']}"}
    llm_called = False

    class _StubPacksSvc:
        def has_engine(self) -> bool:
            return True

        async def enforce_run_start_readiness(self, **_kwargs: Any) -> list[Any]:
            raise PackSlotUnboundError(
                pack_slug="sdlc",
                missing_slots=("git-repo",),
                instance="/api/v1/assistant/turns",
            )

    app.state.workspace_packs_service = _StubPacksSvc()

    async def _fail_if_called(*_a: Any, **_kw: Any) -> Any:
        nonlocal llm_called
        llm_called = True
        raise AssertionError("LLM must not be invoked when pack slot is unbound")

    app.state.llm_streaming_port = type("_Llm", (), {"complete_chat": _fail_if_called})()
    app.dependency_overrides[get_remote_test_bench_and_mcp_service] = lambda: type(
        "_StubMcpSvc", (), {"verify_mcp_pat_for_workspace_async": AsyncMock()}
    )()

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        r_turn = await client.post(
            "/api/v1/assistant/turns",
            headers=marc_hdr,
            json={"workspace_id": WS_A, "user_prompt": "Run @sdlc/agent-us check"},
        )
        assert r_turn.status_code == 422, r_turn.text
        assert r_turn.json()["error_code"] == "ERR_PACK_SLOT_UNBOUND"

        r_mcp_ask = await client.post(
            "/api/v1/mcp/spaces/ws-a/invoke",
            headers=marc_hdr,
            json={
                "tool_name": "assistant.ask",
                "agent_slug": "assistant.ask",
                "raw_pat_token": "orcia_mcp_pat_dummy",
                "passthrough_identity": "marc@orcia.test",
                "caller_verbs": ["execute"],
                "prompt_text": "Ask @sdlc/agent-us",
            },
        )
        assert r_mcp_ask.status_code == 422, r_mcp_ask.text
        assert r_mcp_ask.json()["error_code"] == "ERR_PACK_SLOT_UNBOUND"

        r_mcp_agent = await client.post(
            "/api/v1/mcp/spaces/ws-a/invoke",
            headers=marc_hdr,
            json={
                "tool_name": "agent.sdlc_us",
                "agent_slug": "sdlc:agent-us",
                "raw_pat_token": "orcia_mcp_pat_dummy",
                "passthrough_identity": "marc@orcia.test",
                "caller_verbs": ["execute"],
                "prompt_text": "Execute",
            },
        )
        assert r_mcp_agent.status_code == 422, r_mcp_agent.text
        assert r_mcp_agent.json()["error_code"] == "ERR_PACK_SLOT_UNBOUND"
        assert llm_called is False
