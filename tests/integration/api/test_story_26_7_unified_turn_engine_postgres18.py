"""Story 26.7 — Real PG18 + Redis Vertical Integration Tests (`create_app()`, 0 overrides)."""

from __future__ import annotations

import json
import time
import uuid
from typing import Any

import pytest
import sqlalchemy as sa
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine
from tests.integration.api._pg18_story_26_5_helpers import (
    pg_and_redis_urls,
    real_lifespan_client_factory,
    seed_pg18_ontology_rag_and_blackboard,
)

from orcia_api.main import create_app

__all__ = ["pg_and_redis_urls", "real_lifespan_client_factory"]


def _parse_sse(raw_text: str) -> list[dict[str, Any]]:
    events: list[dict[str, Any]] = []
    for block in raw_text.strip().split("\n\n"):
        if not block.strip():
            continue
        eid, ename, edata = "", "", {}
        for line in block.splitlines():
            if line.startswith("id: "):
                eid = line[4:].strip()
            elif line.startswith("event: "):
                ename = line[7:].strip()
            elif line.startswith("data: "):
                edata = json.loads(line[6:])
        if ename:
            events.append({"id": eid, "event": ename, "data": edata})
    return events


@pytest.mark.asyncio
async def test_story_26_7_unified_turn_engine_citations_profile_and_mcp_postgres18(
    pg_and_redis_urls: tuple[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify Speed 1/2/3 convergence, `ASSISTANT` profile, `CitationGuard` & MCP ask."""
    pg_url, redis_url = pg_and_redis_urls
    monkeypatch.setenv("DATABASE_URL", pg_url)
    monkeypatch.setenv("REDIS_URL", redis_url)
    monkeypatch.setenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", "0")
    monkeypatch.setenv("ORCIA_FORCE_REAL_RUNTIME", "1")
    monkeypatch.setenv("ORCIA_ENABLE_PG_SESSION_MAKER", "1")
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
    monkeypatch.setenv("ORCIA_ENV", "local")
    monkeypatch.setenv("ORCIA_JWT_SIGNING_SECRET", "orcia-story-26-7-jwt-secret-0001")
    monkeypatch.setenv("ORCIA_PASSTHROUGH_MASTER_KEY", "orcia-story-26-7-vault-key-0001")

    engine = create_async_engine(pg_url)
    app = create_app()
    try:
        async with (
            app.router.lifespan_context(app),
            AsyncClient(transport=ASGITransport(app=app), base_url="http://test-26-7") as client,
        ):
            boot = await client.post(
                "/api/v1/bootstrap/welcome-setup/first-admin",
                json={
                    "email": "admin267@orcia.io",
                    "display_name": "Admin 26.7",
                    "password": "Admin267!StrongPassword",  # pragma: allowlist secret
                    "orcia_env": "local",
                },
            )
            assert boot.status_code == 200, boot.text
            admin_id = boot.json()["user_id"]
            hdrs = {"Authorization": f"Bearer {boot.json()['access_token']}"}

            bu = await client.post(
                "/api/v1/org-units",
                headers=hdrs,
                json={"name": "BU 26.7", "slug": "bu-267", "kind": "BU"},
            )
            assert bu.status_code == 200, bu.text
            ws_id = (
                await client.post(
                    "/api/v1/workspaces",
                    headers=hdrs,
                    json={
                        "name": "WS 26.7",
                        "slug": "ws-267",
                        "owner_org_unit_id": bu.json()["id"],
                        "visibility_mode": "STANDARD",
                    },
                )
            ).json()["id"]

            r_model = await client.post(
                "/api/v1/settings/ai-models/mappings",
                headers=hdrs,
                json={
                    "scope_level": "GLOBAL",
                    "display_name": "Chat 26.7",
                    "inference_tier": "medium",
                    "effort": "balanced",
                    "provider_slug": "openai",
                    "model_family": "OpenAI",
                    "model_name": "gpt-4o-mini",
                    "endpoint_uri": "https://api.openai.com/v1",
                    "auth_mode": "none_local",
                    "protocol_mode": "openai_compatible",
                    "usage": "chat",
                },
            )
            assert r_model.status_code in (200, 201), r_model.text

            ws_b_id = (
                await client.post(
                    "/api/v1/workspaces",
                    headers=hdrs,
                    json={
                        "name": "WS B 26.7",
                        "slug": "ws-b-267",
                        "owner_org_unit_id": bu.json()["id"],
                        "visibility_mode": "STANDARD",
                    },
                )
            ).json()["id"]
            await seed_pg18_ontology_rag_and_blackboard(
                engine, ws_a=ws_id, ws_b=ws_b_id, admin_user_id=admin_id
            )
            thread_id = (
                await client.post(
                    "/api/v1/assistant/threads",
                    headers=hdrs,
                    json={"workspace_id": ws_id, "title": "Thread 26.7"},
                )
            ).json()["thread_id"]

            # 1. Speed 1 turn -> TTFT < 1.2s + citation_map before turn_completed + PG18 persistence
            t0 = time.perf_counter()
            r1 = await client.post(
                "/api/v1/assistant/turns",
                headers=hdrs,
                json={
                    "workspace_id": ws_id,
                    "thread_id": thread_id,
                    "user_prompt": "What is the Payment Ledger settlement rule?",
                    "requested_speed": "SPEED_1_FAST",
                    "locale": "en",
                },
            )
            assert r1.status_code == 202, r1.text
            t1_id = r1.json()["turn_id"]
            s1 = await client.get(f"/api/v1/assistant/turns/{t1_id}/stream", headers=hdrs)
            ttft_ms = round((time.perf_counter() - t0) * 1000.0, 2)
            assert s1.status_code == 200
            assert ttft_ms < 1200.0
            ev1 = _parse_sse(s1.text)
            n1 = [e["event"] for e in ev1]
            assert "citation_map" in n1 and "turn_completed" in n1
            assert n1.index("citation_map") < n1.index("turn_completed")
            comp1 = next(e["data"] for e in ev1 if e["event"] == "turn_completed")
            assert comp1["low_evidence"] is False
            assert comp1["supports_tools"] is True

            # 2. Linked Speed 2 turn (parent_turn_id) -> creates ASSISTANT reflexive session in PG18
            r2 = await client.post(
                "/api/v1/assistant/turns",
                headers=hdrs,
                json={
                    "workspace_id": ws_id,
                    "thread_id": thread_id,
                    "parent_turn_id": t1_id,
                    "user_prompt": "Deepen settlement audit @architect",
                    "requested_speed": "SPEED_2_AGENT_TOOLS",
                    "locale": "en",
                },
            )
            assert r2.status_code == 202, r2.text
            t2_id = r2.json()["turn_id"]
            assert r2.json()["parent_turn_id"] == t1_id
            r_synth = await client.post(
                f"/api/v1/assistant/turns/{t2_id}/synthesize-now", headers=hdrs
            )
            assert r_synth.status_code == 202
            s2 = await client.get(f"/api/v1/assistant/turns/{t2_id}/stream", headers=hdrs)
            assert s2.status_code == 200
            assert "event: turn_completed" in s2.text

            # 3. Lock V5 approve validation on PG18 audit_ledger
            r_app_bad = await client.post(
                f"/api/v1/assistant/turns/{t2_id}/approve",
                headers=hdrs,
                json={"workspace_id": ws_id, "proposal_id": "prop-pg-1", "approved": True},
            )
            assert r_app_bad.status_code == 422
            r_app_ok = await client.post(
                f"/api/v1/assistant/turns/{t2_id}/approve",
                headers=hdrs,
                json={
                    "workspace_id": ws_id,
                    "proposal_id": "prop-pg-1",
                    "approved": True,
                    "human_anchor_markdown": "Validated PG18 decision anchor >= 10 chars.",
                },
            )
            assert r_app_ok.status_code == 200

            # 4. MCP assistant.ask read-only Speed 1 under PG18 PAT + Quota + Scope + 7 locks
            mcp_svc = app.state.remote_test_bench_and_mcp_service
            raw_pat = f"pat_mcp_{uuid.uuid4().hex}"
            await mcp_svc._exposure.register_pat_mcp_token_async(
                raw_pat_token=raw_pat, allowed_workspace_slugs={ws_id}
            )
            r_mcp = await client.post(
                f"/api/v1/mcp/spaces/{ws_id}/invoke",
                headers=hdrs,
                json={
                    "raw_pat_token": raw_pat,
                    "agent_slug": "assistant",
                    "tool_name": "assistant.ask",
                    "caller_verbs": ["execute", "read"],
                    "passthrough_identity": "admin267@orcia.io",
                    "prompt_text": "What is the Payment Ledger settlement rule?",
                },
            )
            assert r_mcp.status_code == 200, r_mcp.text
            mcp_body = r_mcp.json()
            assert mcp_body["tool_name"] == "assistant.ask"
            assert mcp_body["system_prompt_exposed"] is None
            assert mcp_body["secret_refs_exposed"] == []
            assert mcp_body["staged_actions"] == []

            # 5. Deleted legacy routes return 404/405
            for legacy in (
                "/api/v1/assistant/three-speed/turn",
                "/api/v1/assistant/chat",
                "/api/v1/assistant/citations/verify-turn",
                "/api/v1/assistant/artifacts/action",
            ):
                assert (
                    await client.post(legacy, headers=hdrs, json={"workspace_id": ws_id})
                ).status_code in (404, 405)

        # Verify SQL ground truth directly on PostgreSQL 18
        async with engine.connect() as conn:
            prof_row = (
                await conn.execute(
                    sa.text(
                        "SELECT execution_profile, status FROM reflexive_execution_sessions "
                        "WHERE execution_id = :eid"
                    ),
                    {"eid": t2_id},
                )
            ).fetchone()
            assert prof_row is not None
            assert prof_row[0] == "ASSISTANT"
            assert prof_row[1] == "COMPLETED"

            msgs = (
                await conn.execute(
                    sa.text(
                        "SELECT turn_id, parent_turn_id, role FROM assistant_thread_messages "
                        "WHERE thread_id = :tid ORDER BY created_at ASC"
                    ),
                    {"tid": thread_id},
                )
            ).fetchall()
            assert len(msgs) >= 4
            assert any(str(m[0]) == t2_id and str(m[1]) == t1_id for m in msgs)

        # P1 #3 + #5: Re-measure warm SQL prompt-assembly latency (single Mode-A) & Redis lock 409
        app_w = create_app()
        async with (
            app_w.router.lifespan_context(app_w),
            AsyncClient(
                transport=ASGITransport(app=app_w), base_url="http://test-26-7-w"
            ) as client_w,
        ):
            r_login_w = await client_w.post(
                "/api/v1/auth/login/local",
                json={
                    "email": "admin267@orcia.io",
                    "password": "Admin267!StrongPassword",  # pragma: allowlist secret
                },
            )
            hdrs_w = {"Authorization": f"Bearer {r_login_w.json()['access_token']}"}
            warm_latencies: list[float] = []
            # 1 warmup turn on fresh `app_w` pool, then 5 warm measurements
            for idx in range(6):
                rw = await client_w.post(
                    "/api/v1/assistant/turns",
                    headers=hdrs_w,
                    json={
                        "workspace_id": ws_id,
                        "thread_id": thread_id,
                        "user_prompt": f"Warm R6 check {idx}: settlement rule?",
                        "requested_speed": "SPEED_1_FAST",
                        "locale": "en",
                    },
                )
                assert rw.status_code == 202, rw.text
                tw_id = rw.json()["turn_id"]
                sw = await client_w.get(f"/api/v1/assistant/turns/{tw_id}/stream", headers=hdrs_w)
                assert sw.status_code == 200
                turn_rec = await app_w.state.assistant_turn_registry.get_turn_by_id(tw_id)
                assert turn_rec is not None
                if idx > 0:
                    warm_latencies.append(float(turn_rec.prompt_assembly_latency_ms))

            sorted_lat = sorted(warm_latencies)
            p50_ms = sorted_lat[len(sorted_lat) // 2]
            p95_ms = sorted_lat[-1]
            assert p95_ms <= 100.0, f"R6 warm prompt assembly exceeded 100ms: {sorted_lat}"
            print(
                f"[R6_PG18_WARM_ASSEMBLY] p50_ms={p50_ms:.2f} p95_ms={p95_ms:.2f} "
                f"samples={sorted_lat}"
            )

            # Peer RedisThreadTurnLock conflict -> 409 ERR_THREAD_TURN_LOCK_HELD
            import redis.asyncio as aioredis

            rc = aioredis.from_url(redis_url)
            try:
                await rc.set(f"lock:thread:{thread_id}", "peer-user-id:tok-1", nx=True, ex=60)
                conf = await client_w.post(
                    "/api/v1/assistant/turns",
                    headers=hdrs_w,
                    json={
                        "workspace_id": ws_id,
                        "thread_id": thread_id,
                        "user_prompt": "Blocked while locked",
                    },
                )
                assert conf.status_code == 409
                assert conf.json()["error_code"] == "ERR_THREAD_TURN_LOCK_HELD"
                await rc.delete(f"lock:thread:{thread_id}")
            finally:
                await rc.aclose()
    finally:
        await engine.dispose()


def test_story_26_7_alembic_upgrade_downgrade_postgres18(
    pg_and_redis_urls: tuple[str, str],
) -> None:
    """Verify `20261122_267` Alembic `downgrade` -> `20261122_266a` -> `upgrade head` on PG18."""
    import os
    import subprocess
    import sys
    from pathlib import Path

    pg_url, _ = pg_and_redis_urls
    repo_root = Path(__file__).resolve().parents[3]
    alembic_bin = str(Path(sys.executable).with_name("alembic"))
    env = {
        "PATH": os.environ.get("PATH", "/usr/bin:/bin"),
        "PYTHONPATH": os.environ.get("PYTHONPATH", ""),
        "DATABASE_URL": pg_url,
        "ORCIA_ENV_FILE": str(repo_root / ".orcia-run" / "does-not-exist.env"),
    }
    down = subprocess.run(
        [alembic_bin, "-c", "infra/migrations/alembic.ini", "downgrade", "20261122_266a"],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
    )
    assert down.returncode == 0, f"{down.stdout}\n{down.stderr}"
    up = subprocess.run(
        [alembic_bin, "-c", "infra/migrations/alembic.ini", "upgrade", "head"],
        cwd=repo_root,
        env=env,
        capture_output=True,
        text=True,
    )
    assert up.returncode == 0, f"{up.stdout}\n{up.stderr}"
