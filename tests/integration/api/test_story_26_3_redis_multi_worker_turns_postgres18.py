"""Story 26.3 — Layer 2 Real PostgreSQL 18 + Redis 7.4 Multi-Worker Integration Tests."""

from __future__ import annotations

import asyncio
import contextlib
import json
import os
import subprocess
from collections.abc import Iterator
from pathlib import Path
from typing import Any
from urllib.parse import quote_plus

import pytest
import redis.asyncio as aioredis
import sqlalchemy as sa
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import create_async_engine
from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import wait_for_logs
from testcontainers.postgres import PostgresContainer

from orcia_api.main import create_app

os.environ["TESTCONTAINERS_RYUK_DISABLED"] = "true"

REPO_ROOT = Path(__file__).resolve().parents[3]
DB_NAME = "orcia_story_26_3"
DB_USER = "orcia"
DB_PASSWORD = "orcia_26_3_pw"  # pragma: allowlist secret


@pytest.fixture(scope="module")
def pg18_and_redis74() -> Iterator[tuple[str, str]]:
    """Spin up real ephemeral PostgreSQL 18 (`pgvector:pg18`) and Redis 7.4 containers."""
    pg_container = PostgresContainer(
        "pgvector/pgvector:pg18", username=DB_USER, password=DB_PASSWORD, dbname=DB_NAME
    )
    redis_container = DockerContainer("redis:7.4.2-alpine").with_exposed_ports(6379)

    with pg_container as pg, redis_container as rc:
        wait_for_logs(rc, "Ready to accept connections", timeout=20)
        pg_url = (
            f"postgresql+asyncpg://{DB_USER}:{quote_plus(DB_PASSWORD)}"
            f"@127.0.0.1:{pg.get_exposed_port(5432)}/{DB_NAME}"
        )
        redis_url = f"redis://127.0.0.1:{rc.get_exposed_port(6379)}/0"
        env = {
            "PATH": "/usr/bin:/bin",
            "DATABASE_URL": pg_url,
            "ORCIA_ENV_FILE": str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"),
        }
        subprocess.run(
            [str(REPO_ROOT / ".venv" / "bin" / "alembic"), "-c", "infra/migrations/alembic.ini"]
            + ["upgrade", "head"],
            cwd=REPO_ROOT,
            env=env,
            check=True,
        )
        yield pg_url, redis_url


def _parse_sse_frames(raw_text: str) -> list[dict[str, Any]]:
    frames: list[dict[str, Any]] = []
    cur: dict[str, Any] = {}
    for line in raw_text.splitlines():
        if not line.strip():
            if cur:
                frames.append(cur)
                cur = {}
            continue
        if line.startswith("id:"):
            cur["id"] = line[3:].strip()
        elif line.startswith("event:"):
            cur["event"] = line[6:].strip()
        elif line.startswith("data:"):
            cur["data"] = json.loads(line[5:].strip())
    if cur:
        frames.append(cur)
    return frames


@pytest.mark.asyncio
async def test_two_instances_redis_cursor_replay_cross_worker_stop_and_liveness_pg18(
    pg18_and_redis74: tuple[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify 2 `create_app()` instances sharing real PG18 + Redis 7.4 for cursor, stop & crash."""
    pg_url, redis_url = pg18_and_redis74
    monkeypatch.setenv("DATABASE_URL", pg_url)
    monkeypatch.setenv("REDIS_URL", redis_url)
    monkeypatch.setenv("ORCIA_ENV_FILE", str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"))
    monkeypatch.setenv("ORCIA_ENV", "local")
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "false")
    monkeypatch.setenv("ORCIA_LLM_ALLOWED_PRIVATE_HOSTS", "127.0.0.1")
    monkeypatch.setenv("ORCIA_JWT_SIGNING_SECRET", "orcia-26-3-jwt-secret-00000001")
    monkeypatch.setenv("ORCIA_PASSTHROUGH_MASTER_KEY", "orcia-26-3-vault-key-00000001")
    monkeypatch.setenv("ORCIA_ENABLE_PG_SESSION_MAKER", "1")
    monkeypatch.setenv("ORCIA_ASSISTANT_LIVENESS_TTL_S", "2")

    engine = create_async_engine(pg_url)
    redis_probe = aioredis.from_url(redis_url, decode_responses=True)
    gate_allow_finish = asyncio.Event()
    crash_release = asyncio.Event()
    chunk2_emitted = asyncio.Event()

    async def _handle_llm_http(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            raw_hdrs = await reader.readuntil(b"\r\n\r\n")
            hdr_text = raw_hdrs.decode("latin-1")
            clen = 0
            for line in hdr_text.splitlines():
                if line.lower().startswith("content-length:"):
                    clen = int(line.split(":", 1)[1].strip())
            body_bytes = await reader.readexactly(clen) if clen > 0 else b""
            body_str = body_bytes.decode("utf-8", errors="replace")
            writer.write(
                b"HTTP/1.1 200 OK\r\n"
                b"Content-Type: text/event-stream\r\n"
                b"Cache-Control: no-cache\r\n"
                b"Connection: close\r\n\r\n"
            )
            writer.write(b'data: {"choices":[{"delta":{"content":"Part-A "}}]}\n\n')
            writer.write(b'data: {"choices":[{"delta":{"content":"Part-B "}}]}\n\n')
            await writer.drain()
            chunk2_emitted.set()
            if "HOLD_FOR_STOP" in body_str:
                await asyncio.wait_for(gate_allow_finish.wait(), timeout=5.0)
            elif "HANG_CRASH" in body_str:
                await asyncio.wait_for(crash_release.wait(), timeout=10.0)
            writer.write(
                b'data: {"choices":[{"delta":{"content":"Part-C"}}],'
                b'"usage":{"prompt_tokens":42,"completion_tokens":18}}\n\n'
            )
            writer.write(b"data: [DONE]\n\n")
            await writer.drain()
        except Exception:
            pass
        finally:
            writer.close()

    llm_server = await asyncio.start_server(_handle_llm_http, "127.0.0.1", 0)
    llm_port = llm_server.sockets[0].getsockname()[1]
    try:
        app_w1 = create_app()
        app_w2 = create_app()
        assert app_w1.dependency_overrides == {} and app_w2.dependency_overrides == {}

        async with (
            app_w1.router.lifespan_context(app_w1),
            app_w2.router.lifespan_context(app_w2),
            AsyncClient(transport=ASGITransport(app=app_w1), base_url="http://w1") as c1,
            AsyncClient(transport=ASGITransport(app=app_w2), base_url="http://w2") as c2,
        ):
            # Bootstrap Day-0 admin + org unit + workspace + AI model on Worker 1
            boot = await c1.post(
                "/api/v1/bootstrap/welcome-setup/first-admin",
                json={
                    "email": "admin263@orcia.io",
                    "display_name": "Admin 26.3",
                    "password": "Admin263!SecurePassword",  # pragma: allowlist secret
                    "orcia_env": "local",
                },
            )
            assert boot.status_code == 200, boot.text
            token = boot.json()["access_token"]
            headers = {"Authorization": f"Bearer {token}"}

            bu_res = await c1.post(
                "/api/v1/org-units",
                headers=headers,
                json={"name": "BU 26.3", "slug": "bu-26-3", "kind": "BU"},
            )
            assert bu_res.status_code in (200, 201), bu_res.text
            bu_id = bu_res.json()["id"]

            ws_res = await c1.post(
                "/api/v1/workspaces",
                headers=headers,
                json={
                    "name": "WS Alpha 26.3",
                    "slug": "ws-alpha-263",
                    "owner_org_unit_id": bu_id,
                    "visibility_mode": "STANDARD",
                },
            )
            assert ws_res.status_code in (200, 201), ws_res.text
            ws_id = ws_res.json()["id"]

            model_res = await c1.post(
                "/api/v1/settings/ai-models/mappings",
                headers=headers,
                json={
                    "scope_level": "WORKSPACE",
                    "scope_id": ws_id,
                    "display_name": "Loopback SSE Test Model",
                    "inference_tier": "medium",
                    "effort": "balanced",
                    "provider_slug": "openai",
                    "model_family": "OpenAI",
                    "model_name": "loopback-sse-26-3",
                    "endpoint_uri": f"http://127.0.0.1:{llm_port}/v1",
                    "auth_mode": "none_local",
                    "protocol_mode": "openai_compatible",
                    "usage": "chat",
                },
            )
            assert model_res.status_code in (200, 201), model_res.text

            # 1. Start turn on W1, read partial frames, reattach on W2 via ?after=<cursor>
            chunk2_emitted.clear()
            r_start = await c1.post(
                "/api/v1/assistant/turns",
                headers=headers,
                json={"workspace_id": ws_id, "user_prompt": "Normal turn"},
            )
            assert r_start.status_code == 202, r_start.text
            t_replay = r_start.json()["turn_id"]

            # Read full stream from W2 to capture stream IDs, then replay after cursor[0]
            r_s2_full = await c2.get(
                f"/api/v1/assistant/turns/{t_replay}/stream",
                headers=headers,
            )
            assert r_s2_full.status_code == 200
            full_frames = _parse_sse_frames(r_s2_full.text)
            assert len(full_frames) >= 4
            assert full_frames[-1]["event"] == "turn_completed"
            first_cursor = full_frames[0]["id"]

            # Reattach on Worker 2 strictly after first_cursor -> zero duplicates!
            r_s2_after = await c2.get(
                f"/api/v1/assistant/turns/{t_replay}/stream",
                params={"after": first_cursor},
                headers=headers,
            )
            assert r_s2_after.status_code == 200
            after_frames = _parse_sse_frames(r_s2_after.text)
            assert [f["id"] for f in after_frames] == [f["id"] for f in full_frames[1:]]

            # Verify Redis Stream TTL is set post-completion
            stream_ttl = await redis_probe.ttl(f"orcia:assistant:turn:stream:{t_replay}")
            assert stream_ttl > 0

            # 2. Cross-worker STOP: start on W1, stop on W2 -> turn_stopped + audit_ledger
            chunk2_emitted.clear()
            gate_allow_finish.clear()
            r_stop_start = await c1.post(
                "/api/v1/assistant/turns",
                headers=headers,
                json={"workspace_id": ws_id, "user_prompt": "HOLD_FOR_STOP"},
            )
            assert r_stop_start.status_code == 202
            t_stop = r_stop_start.json()["turn_id"]
            await asyncio.wait_for(chunk2_emitted.wait(), timeout=3.0)

            r_stop_cmd = await c2.post(
                f"/api/v1/assistant/turns/{t_stop}/stop",
                headers=headers,
            )
            assert r_stop_cmd.status_code == 200
            assert r_stop_cmd.json()["status"] == "STOPPED"

            r_stop_stream = await c2.get(
                f"/api/v1/assistant/turns/{t_stop}/stream",
                headers=headers,
            )
            stop_frames = _parse_sse_frames(r_stop_stream.text)
            assert stop_frames[-1]["event"] == "turn_stopped"

            # Verify partial FinOps persisted in PostgreSQL 18 `audit_ledger` (idempotent)
            async with engine.connect() as conn:
                row = (
                    await conn.execute(
                        sa.text(
                            "SELECT event_type, output_tokens FROM audit_ledger "
                            "WHERE metadata_jsonb->>'turn_id' = :tid"
                        ),
                        {"tid": t_stop},
                    )
                ).first()
                assert row is not None, "Expected partial FinOps audit_ledger row after stop"
                assert int(row.output_tokens) >= 1

            # 3. Simulated pod crash: start hanging turn on W1, delete liveness key, reattach on W2
            chunk2_emitted.clear()
            r_crash = await c1.post(
                "/api/v1/assistant/turns",
                headers=headers,
                json={"workspace_id": ws_id, "user_prompt": "HANG_CRASH"},
            )
            assert r_crash.status_code == 202
            t_crash = r_crash.json()["turn_id"]
            await asyncio.wait_for(chunk2_emitted.wait(), timeout=3.0)

            # Simulate brutal pod termination: cancel W1 task, flush any graceful cleanup artifact,
            # expire liveness key, and leave turn RUNNING as if SIGKILL occurred mid-stream
            w1_tasks = list(app_w1.state.assistant_turn_tasks)
            for task in w1_tasks:
                task.cancel()
            await asyncio.gather(*w1_tasks, return_exceptions=True)
            entries = await redis_probe.xrange(f"orcia:assistant:turn:stream:{t_crash}")
            for entry_id, fields in entries:
                payload_obj = json.loads(fields.get("payload", "{}"))
                if payload_obj.get("event") in ("turn_stopped", "turn_completed", "stream_error"):
                    await redis_probe.xdel(f"orcia:assistant:turn:stream:{t_crash}", entry_id)
            await redis_probe.delete(f"orcia:assistant:turn:live:{t_crash}")
            raw_meta = await redis_probe.get(f"orcia:assistant:turn:{t_crash}")
            if raw_meta:
                meta_obj = json.loads(raw_meta)
                meta_obj["status"] = "RUNNING"
                await redis_probe.set(
                    f"orcia:assistant:turn:{t_crash}", json.dumps(meta_obj), ex=300
                )

            r_reattach_crash = await c2.get(
                f"/api/v1/assistant/turns/{t_crash}/stream",
                headers=headers,
            )
            crash_frames = _parse_sse_frames(r_reattach_crash.text)
            assert crash_frames[-1]["event"] == "stream_error"
            assert crash_frames[-1]["data"]["error_code"] == "ERR_ASSISTANT_TURN_INTERRUPTED"
            assert crash_frames[-1]["data"]["trace_id"]

            # 4. Concurrent per-user semaphore / rate limit via Redis -> HTTP 429 RFC 9457
            for rl_key in await redis_probe.keys("orcia:assistant:ratelimit:*"):
                await redis_probe.delete(rl_key)
            monkeypatch.setenv("ORCIA_ASSISTANT_RATE_LIMIT_MAX", "2")
            for idx in range(2):
                ok_rl = await c1.post(
                    "/api/v1/assistant/turns",
                    headers=headers,
                    json={"workspace_id": ws_id, "user_prompt": f"RL {idx}"},
                )
                assert ok_rl.status_code == 202
                for t in list(app_w1.state.assistant_turn_tasks):
                    await asyncio.gather(t, return_exceptions=True)
            blocked_rl = await c2.post(
                "/api/v1/assistant/turns",
                headers=headers,
                json={"workspace_id": ws_id, "user_prompt": "RL blocked across workers"},
            )
            assert blocked_rl.status_code == 429
            assert blocked_rl.json()["error_code"] == "ERR_ASSISTANT_RATE_LIMITED"

            # 5. Per-user Redis concurrency semaphore across workers -> HTTP 429 RFC 9457
            for rl_key in await redis_probe.keys("orcia:assistant:ratelimit:*"):
                await redis_probe.delete(rl_key)
            monkeypatch.setenv("ORCIA_ASSISTANT_RATE_LIMIT_MAX", "20")
            monkeypatch.setenv("ORCIA_ASSISTANT_MAX_CONCURRENT_TURNS_PER_USER", "1")
            chunk2_emitted.clear()
            gate_allow_finish.clear()
            c_hold = await c1.post(
                "/api/v1/assistant/turns",
                headers=headers,
                json={"workspace_id": ws_id, "user_prompt": "HOLD_FOR_STOP concurrency"},
            )
            assert c_hold.status_code == 202
            await asyncio.wait_for(chunk2_emitted.wait(), timeout=3.0)
            c_blocked = await c2.post(
                "/api/v1/assistant/turns",
                headers=headers,
                json={"workspace_id": ws_id, "user_prompt": "Blocked second concurrent turn"},
            )
            assert c_blocked.status_code == 429
            assert c_blocked.json()["error_code"] == "ERR_ASSISTANT_CONCURRENCY_LIMIT"
            gate_allow_finish.set()
            crash_release.set()
            for t in list(app_w1.state.assistant_turn_tasks):
                await asyncio.gather(t, return_exceptions=True)
    finally:
        gate_allow_finish.set()
        crash_release.set()
        llm_server.close()
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(llm_server.wait_closed(), timeout=2.0)
        await redis_probe.aclose()
        await engine.dispose()
