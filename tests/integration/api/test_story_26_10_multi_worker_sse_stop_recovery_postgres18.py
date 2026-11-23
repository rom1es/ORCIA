"""Story 26.10 — 2-Instance Multi-Worker PG18 + Redis SSE, Stop & Recovery Tests."""

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
from httpx import ASGITransport, AsyncClient
from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import wait_for_logs
from testcontainers.postgres import PostgresContainer

from orcia_api.main import create_app

os.environ["TESTCONTAINERS_RYUK_DISABLED"] = "true"

REPO_ROOT = Path(__file__).resolve().parents[3]
DB_NAME = "orcia_story_26_10"
DB_USER = "orcia"
DB_PASSWORD = "orcia_26_10_pw"  # pragma: allowlist secret


@pytest.fixture(scope="module")
def pg18_and_redis74() -> Iterator[tuple[str, str]]:
    """Spin up real ephemeral PG18 (`pgvector:pg18`) and Redis 7.4 containers."""
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
        env = {"PATH": "/usr/bin:/bin", "DATABASE_URL": pg_url, "ORCIA_ENV_FILE": "/nonexistent"}
        alembic_bin = str(REPO_ROOT / ".venv/bin/alembic")
        subprocess.run(
            [alembic_bin, "-c", "infra/migrations/alembic.ini", "upgrade", "head"],
            cwd=REPO_ROOT,
            env=env,
            check=True,
        )
        yield pg_url, redis_url


def _parse_sse(raw_text: str) -> list[dict[str, Any]]:
    frames: list[dict[str, Any]] = []
    cur: dict[str, Any] = {}
    for line in raw_text.splitlines():
        if not line.strip() and cur:
            frames.append(cur)
            cur = {}
        elif line.startswith("id:"):
            cur["id"] = line[3:].strip()
        elif line.startswith("event:"):
            cur["event"] = line[6:].strip()
        elif line.startswith("data:"):
            cur["data"] = json.loads(line[5:].strip())
    if cur:
        frames.append(cur)
    return frames


@pytest.mark.asyncio
async def test_two_app_instances_cross_worker_stop_cursor_reattach_and_crash_recovery(
    pg18_and_redis74: tuple[str, str],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Prove 2 distinct `create_app()` instances share Redis+PG18 for stop, replay & crash."""
    pg_url, redis_url = pg18_and_redis74
    for k, v in (
        ("DATABASE_URL", pg_url),
        ("REDIS_URL", redis_url),
        ("ORCIA_ENV_FILE", str(REPO_ROOT / ".orcia-run" / "does-not-exist.env")),
        ("ORCIA_ENV", "local"),
        ("ORCIA_USE_CASSETTE_LLM", "false"),
        ("ORCIA_LLM_ALLOWED_PRIVATE_HOSTS", "127.0.0.1"),
        ("ORCIA_JWT_SIGNING_SECRET", "orcia-26-10-jwt-secret-000001"),
        ("ORCIA_PASSTHROUGH_MASTER_KEY", "orcia-26-10-vault-key-000001"),
        ("ORCIA_ENABLE_PG_SESSION_MAKER", "1"),
        ("ORCIA_ASSISTANT_LIVENESS_TTL_S", "2"),
    ):
        monkeypatch.setenv(k, v)

    redis_probe = aioredis.from_url(redis_url, decode_responses=True)
    gate_finish = asyncio.Event()
    crash_hold = asyncio.Event()
    chunk_emitted = asyncio.Event()

    async def _llm_http(reader: asyncio.StreamReader, writer: asyncio.StreamWriter) -> None:
        try:
            hdrs = await reader.readuntil(b"\r\n\r\n")
            clen = next(
                (
                    int(ln.split(":", 1)[1].strip())
                    for ln in hdrs.decode("latin-1").splitlines()
                    if ln.lower().startswith("content-length:")
                ),
                0,
            )
            body = (await reader.readexactly(clen) if clen else b"").decode("utf-8", "replace")
            writer.write(
                b"HTTP/1.1 200 OK\r\nContent-Type: text/event-stream\r\n"
                b"Cache-Control: no-cache\r\nConnection: close\r\n\r\n"
            )
            writer.write(b'data: {"choices":[{"delta":{"content":"Alpha "}}]}\n\n')
            writer.write(b'data: {"choices":[{"delta":{"content":"Beta "}}]}\n\n')
            await writer.drain()
            chunk_emitted.set()
            if "HOLD_STOP" in body:
                await asyncio.wait_for(gate_finish.wait(), timeout=6.0)
            elif "HANG_CRASH" in body:
                await asyncio.wait_for(crash_hold.wait(), timeout=10.0)
            writer.write(
                b'data: {"choices":[{"delta":{"content":"Gamma"}}],'
                b'"usage":{"prompt_tokens":24,"completion_tokens":12}}\n\n'
                b"data: [DONE]\n\n"
            )
            await writer.drain()
        except Exception:
            pass
        finally:
            writer.close()

    server = await asyncio.start_server(_llm_http, "127.0.0.1", 0)
    port = server.sockets[0].getsockname()[1]
    try:
        app1, app2 = create_app(), create_app()
        assert app1.dependency_overrides == {} and app2.dependency_overrides == {}

        async with (
            app1.router.lifespan_context(app1),
            app2.router.lifespan_context(app2),
            AsyncClient(transport=ASGITransport(app=app1), base_url="http://app1") as c1,
            AsyncClient(transport=ASGITransport(app=app2), base_url="http://app2") as c2,
        ):
            boot = await c1.post(
                "/api/v1/bootstrap/welcome-setup/first-admin",
                json={
                    "email": "admin2610@orcia.io",
                    "display_name": "Admin 26.10",
                    "password": "Admin2610!SecurePassword",  # pragma: allowlist secret
                    "orcia_env": "local",
                },
            )
            assert boot.status_code == 200, boot.text
            hdrs = {"Authorization": f"Bearer {boot.json()['access_token']}"}
            bu_res = await c1.post(
                "/api/v1/org-units",
                headers=hdrs,
                json={"name": "BU 26.10", "slug": "bu-26-10", "kind": "BU"},
            )
            ws_res = await c1.post(
                "/api/v1/workspaces",
                headers=hdrs,
                json={
                    "name": "WS 26.10",
                    "slug": "ws-26-10",
                    "owner_org_unit_id": bu_res.json()["id"],
                },
            )
            ws_id = ws_res.json()["id"]
            model_payload = {
                "scope_level": "WORKSPACE",
                "scope_id": ws_id,
                "display_name": "Loopback 26.10",
                "inference_tier": "medium",
                "effort": "balanced",
                "provider_slug": "openai",
                "model_family": "OpenAI",
                "model_name": "loopback-26-10",
                "endpoint_uri": f"http://127.0.0.1:{port}/v1",
                "auth_mode": "none_local",
                "protocol_mode": "openai_compatible",
                "usage": "chat",
            }
            m_res = await c1.post(
                "/api/v1/settings/ai-models/mappings", headers=hdrs, json=model_payload
            )
            assert m_res.status_code in (200, 201), m_res.text
            thread_id = (
                await c1.post(
                    "/api/v1/assistant/threads",
                    headers=hdrs,
                    json={"workspace_id": ws_id, "title": "Multi-Worker Thread"},
                )
            ).json()["thread_id"]

            # 1. Cross-worker SSE re-attach (?after=cursor): monotonic seq & 0 duplicates
            r1 = await c1.post(
                "/api/v1/assistant/turns",
                headers=hdrs,
                json={"workspace_id": ws_id, "thread_id": thread_id, "user_prompt": "Stream A"},
            )
            assert r1.status_code == 202
            t_replay = r1.json()["turn_id"]
            full_frames = _parse_sse(
                (await c2.get(f"/api/v1/assistant/turns/{t_replay}/stream", headers=hdrs)).text
            )
            assert full_frames[-1]["event"] == "turn_completed"
            cursor = full_frames[0]["id"]
            cursor_seq = int(full_frames[0]["data"]["seq"])
            replayed = _parse_sse(
                (
                    await c2.get(
                        f"/api/v1/assistant/turns/{t_replay}/stream",
                        params={"after": cursor},
                        headers=hdrs,
                    )
                ).text
            )
            assert [f["id"] for f in replayed] == [f["id"] for f in full_frames[1:]]
            seqs = [int(f["data"]["seq"]) for f in replayed]
            assert all(s > cursor_seq for s in seqs)
            assert seqs == sorted(set(seqs))

            # 2. Cross-worker STOP on app2 stops turn started on app1 & frees thread lock
            chunk_emitted.clear()
            gate_finish.clear()
            r_hold = await c1.post(
                "/api/v1/assistant/turns",
                headers=hdrs,
                json={"workspace_id": ws_id, "thread_id": thread_id, "user_prompt": "HOLD_STOP"},
            )
            assert r_hold.status_code == 202
            t_stop = r_hold.json()["turn_id"]
            await asyncio.wait_for(chunk_emitted.wait(), timeout=4.0)
            assert (await redis_probe.get(f"lock:thread:{thread_id}")) is not None

            stop_resp = await c2.post(f"/api/v1/assistant/turns/{t_stop}/stop", headers=hdrs)
            assert stop_resp.status_code == 200 and stop_resp.json()["status"] == "STOPPED"
            stop_frames = _parse_sse(
                (await c2.get(f"/api/v1/assistant/turns/{t_stop}/stream", headers=hdrs)).text
            )
            assert stop_frames[-1]["event"] == "turn_stopped"
            assert (await redis_probe.get(f"lock:thread:{thread_id}")) is None

            followup = await c2.post(
                "/api/v1/assistant/turns",
                headers=hdrs,
                json={"workspace_id": ws_id, "thread_id": thread_id, "user_prompt": "Post-stop"},
            )
            assert followup.status_code == 202
            for task in list(app2.state.assistant_turn_tasks):
                await asyncio.gather(task, return_exceptions=True)

            # 3. Crashed-worker liveness recovery -> ERR_ASSISTANT_TURN_INTERRUPTED with seq > 0
            chunk_emitted.clear()
            r_crash = await c1.post(
                "/api/v1/assistant/turns",
                headers=hdrs,
                json={"workspace_id": ws_id, "thread_id": thread_id, "user_prompt": "HANG_CRASH"},
            )
            assert r_crash.status_code == 202
            t_crash = r_crash.json()["turn_id"]
            await asyncio.wait_for(chunk_emitted.wait(), timeout=4.0)

            w1_tasks = list(app1.state.assistant_turn_tasks)
            for task in w1_tasks:
                task.cancel()
            await asyncio.gather(*w1_tasks, return_exceptions=True)
            xrange_rows = await redis_probe.xrange(f"orcia:assistant:turn:stream:{t_crash}") or []
            for eid, fields in xrange_rows:
                if eid is not None and fields is not None:
                    ev = json.loads(fields.get("payload", "{}")).get("event")
                    if ev in ("turn_stopped", "turn_completed", "stream_error"):
                        await redis_probe.xdel(f"orcia:assistant:turn:stream:{t_crash}", eid)
            await redis_probe.delete(f"orcia:assistant:turn:live:{t_crash}")
            raw_meta = await redis_probe.get(f"orcia:assistant:turn:{t_crash}")
            assert raw_meta is not None
            meta = json.loads(raw_meta)
            meta["status"] = "RUNNING"
            await redis_probe.set(f"orcia:assistant:turn:{t_crash}", json.dumps(meta), ex=300)

            crash_frames = _parse_sse(
                (await c2.get(f"/api/v1/assistant/turns/{t_crash}/stream", headers=hdrs)).text
            )
            err_frame = crash_frames[-1]
            assert err_frame["event"] == "stream_error"
            assert err_frame["data"]["error_code"] == "ERR_ASSISTANT_TURN_INTERRUPTED"
            assert int(err_frame["data"]["seq"]) > 0
            assert err_frame["data"]["trace_id"]
    finally:
        gate_finish.set()
        crash_hold.set()
        server.close()
        with contextlib.suppress(TimeoutError):
            await asyncio.wait_for(server.wait_closed(), timeout=2.0)
        await redis_probe.aclose()
