"""Layer 2 Real PostgreSQL 18 + Redis 7.4 Integration Tests for `Story 16.2` (`CAP-160`).

Validates:
- Reversible Alembic migration `20261111_01` (`upgrade head` -> `downgrade 20261108_0910`
  -> `upgrade head`) and Day-0 reset (`09_reset_db_first_boot.py`) on `pgvector/pgvector:pg18`.
- Full vertical `HTTP -> FastAPI -> NonDeterministicReflexiveRuntime -> PostgreSQL 18 + Redis 7.4`:
  - `POST /api/v1/executions/reflexive` (`Approfondi` 25 turns / 48k tokens, surgical exploration,
    stateless `WAITING_WRITE_PREVIEW` pause verified via direct SQL `SELECT`).
  - `F5` reload survival across a brand-new `create_app()` instance (`GET /api/v1/executions/{id}`).
  - `HTTP 403 ERR_POLICY_DENIED` on forged `SignedApprovalToken` (`application/problem+json`).
  - `POST /api/v1/executions/{id}/approve-write` resuming to `COMPLETED` with `ClaimCheckPointer`.
  - Real `AsyncIterator` SSE `GET /api/v1/executions/{id}/trace-stream` preserving `\n` + Redis.
  - `POST .../cancel` (`■ Arrêter`), `POST .../synthesize-now`, human write rejection, and
    `HTTP 403 ERR_OBSERVER_MODE_READ_ONLY` on observer mutations.
"""

from __future__ import annotations

import importlib.util
import json
import os
import shutil
import time
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import httpx
import pytest
import redis as redis_sync
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from sqlalchemy.ext.asyncio import create_async_engine
from testcontainers.core.container import DockerContainer
from testcontainers.core.waiting_utils import wait_for_logs

from orcia_api.main import create_app

os.environ["TESTCONTAINERS_RYUK_DISABLED"] = "true"

REPO_ROOT = Path(__file__).resolve().parents[3]
SOCK_BASE_DIR = REPO_ROOT / ".pytest_cache" / "tc_s16_2"


def _prepare_sock_dir(prefix: str) -> Path:
    unique = f"{prefix}_{os.getpid()}_{int(time.time() * 1000) % 100000}"
    target = SOCK_BASE_DIR / unique
    target.mkdir(parents=True, exist_ok=True)
    target.chmod(0o777)
    return target


def _load_reset_script() -> Any:
    import sys

    script_path = REPO_ROOT / "infra" / "scripts" / "maintenance" / "09_reset_db_first_boot.py"
    spec = importlib.util.spec_from_file_location("reset_db_first_boot_16_2", script_path)
    assert spec is not None and spec.loader is not None
    mod = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = mod
    spec.loader.exec_module(mod)
    return mod


@pytest.fixture(scope="module")
def pg18_and_redis74_urls() -> Iterator[tuple[str, str, Path]]:
    """Spin up real ephemeral PostgreSQL 18 (`pgvector:pg18`) and Redis 7.4 containers."""
    pg_sock_dir = _prepare_sock_dir("pg18")
    rd_sock_dir = _prepare_sock_dir("rd74")
    rd_sock_path = rd_sock_dir / "redis.sock"

    pg_container = (
        DockerContainer("pgvector/pgvector:pg18")
        .with_env("POSTGRES_USER", "orcia")
        .with_env("POSTGRES_PASSWORD", "orcia_dev_secret")
        .with_env("POSTGRES_DB", "orcia")
        .with_volume_mapping(str(pg_sock_dir), "/var/run/postgresql", "rw")
    )
    redis_container = (
        DockerContainer("redis:7.4.2-alpine")
        .with_volume_mapping(str(rd_sock_dir), "/sock", "rw")
        .with_command("redis-server --unixsocket /sock/redis.sock --unixsocketperm 777 --port 6379")
    )

    try:
        with pg_container as pg, redis_container as rc:
            wait_for_logs(pg, "database system is ready to accept connections", timeout=30)
            wait_for_logs(rc, "Ready to accept connections", timeout=20)
            for _ in range(40):
                if (pg_sock_dir / ".s.PGSQL.5432").exists() and rd_sock_path.exists():
                    break
                time.sleep(0.15)

            pg_auth = "orcia:orcia_dev_secret"  # pragma: allowlist secret
            pg_url = f"postgresql+asyncpg://{pg_auth}@/orcia?host={pg_sock_dir}"
            redis_url = f"unix://{rd_sock_path}"
            yield pg_url, redis_url, rd_sock_path
    finally:
        shutil.rmtree(pg_sock_dir, ignore_errors=True)
        shutil.rmtree(rd_sock_dir, ignore_errors=True)


async def test_alembic_20261111_01_upgrade_downgrade_and_vertical_f5_suspend_resume(
    pg18_and_redis74_urls: tuple[str, str, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify Alembic reversibility, PostgreSQL 18 SQL persistence, F5 survival, SSE, & Gate."""
    pg_url, redis_url, rd_sock_path = pg18_and_redis74_urls
    alembic_cfg = Config(str(REPO_ROOT / "infra" / "migrations" / "alembic.ini"))
    alembic_cfg.set_main_option("script_location", str(REPO_ROOT / "infra" / "migrations"))
    alembic_cfg.set_main_option("sqlalchemy.url", pg_url)

    engine = create_async_engine(pg_url)
    try:
        for _ in range(30):
            try:
                async with engine.connect() as probe:
                    await probe.execute(sa.text("SELECT 1"))
                break
            except Exception:
                time.sleep(0.2)

        # 1. Test upgrade head -> downgrade 20261108_0910 -> upgrade head reversibility
        async with engine.begin() as conn:
            await conn.run_sync(
                lambda sc: (
                    alembic_cfg.attributes.__setitem__("connection", sc),
                    command.upgrade(alembic_cfg, "head"),
                    command.downgrade(alembic_cfg, "20261108_0910"),
                    command.upgrade(alembic_cfg, "head"),
                )
            )

        monkeypatch.setenv("DATABASE_URL", pg_url)
        monkeypatch.setenv("ORCIA_ENV_FILE", str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"))
        monkeypatch.setenv("ORCIA_ENABLE_PG_SESSION_MAKER", "1")
        monkeypatch.setenv("REDIS_URL", redis_url)
        monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")
        monkeypatch.delenv("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC", raising=False)

        # 2. Start execution on App #1 -> pauses at WAITING_WRITE_PREVIEW
        app_one = create_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app_one),
            base_url="http://testserver",
        ) as client1:
            start_resp = await client1.post(
                "/api/v1/executions/reflexive",
                params={"persona_key": "marc"},
                json={
                    "actor_slug": "assistant-agent",
                    "objective": "Inspecter capabilities.yaml et préparer la mise à jour gouvernée",
                    "effort_mode": "approfondi",
                    "initial_resources": ["docs/product/capabilities.yaml"],
                    "requested_write_preview": {
                        "connector_type": "mcp:default",
                        "action": "publish_summary",
                        "target_resource_uri": "catalog://docs/architecture-summary",
                        "action_summary": "Publier la synthèse gouvernée",
                        "payload": {"title": "Synthèse ORCIA\nSection 1"},
                    },
                },
            )
            assert start_resp.status_code == 200, start_resp.text
            paused = start_resp.json()
            execution_id = paused["execution_id"]
            assert paused["status"] == "WAITING_WRITE_PREVIEW"
            assert paused["max_turns"] == 25
            assert paused["max_budget_tokens"] == 48_000
            assert paused["pending_write_preview"] is not None
            preview_id = paused["pending_write_preview"]["preview_id"]
            payload_sha = paused["pending_write_preview"]["payload_sha256"]

        # 3. Direct SQL SELECT on PostgreSQL 18 (Garde-Fou #2)
        async with engine.connect() as conn:
            row = (
                await conn.execute(
                    sa.text(
                        """
                        SELECT id::text, status, snapshot_jsonb
                        FROM reflexive_execution_sessions
                        WHERE execution_id = :execution_id
                        """
                    ),
                    {"execution_id": execution_id},
                )
            ).first()
        assert row is not None
        assert len(row[0]) == 36
        assert row[1] == "WAITING_WRITE_PREVIEW"

        # 4. F5 Reload Survival across a BRAND-NEW FastAPI app instance (`0` RAM state)
        app_two = create_app()
        async with httpx.AsyncClient(
            transport=httpx.ASGITransport(app=app_two),
            base_url="http://testserver",
        ) as client2:
            f5_resp = await client2.get(
                f"/api/v1/executions/{execution_id}",
                params={"persona_key": "marc"},
            )
            assert f5_resp.status_code == 200
            f5_data = f5_resp.json()
            assert f5_data["status"] == "WAITING_WRITE_PREVIEW"
            assert f5_data["pending_write_preview"]["preview_id"] == preview_id
            assert len(f5_data["scratchpad"]) >= 1

            # 5. Forged SignedApprovalToken -> 403 ERR_POLICY_DENIED
            forged_resp = await client2.post(
                f"/api/v1/executions/{execution_id}/approve-write",
                params={"persona_key": "marc"},
                json={
                    "approved": True,
                    "preview_id": preview_id,
                    "approval_token": {
                        "preview_id": preview_id,
                        "approver_user_id": "user-marc",
                        "approved_at_utc": "2026-11-11T12:00:00+00:00",
                        "payload_sha256": payload_sha,
                        "broker_signature": "f" * 64,
                    },
                },
            )
            assert forged_resp.status_code == 403
            assert forged_resp.headers["content-type"].startswith("application/problem+json")
            assert forged_resp.json()["error_code"] == "ERR_POLICY_DENIED"
            assert forged_resp.json()["trace_id"]

            # 6. Valid Broker-signed approval -> COMPLETED + ClaimCheckPointer + SQL check
            approve_resp = await client2.post(
                f"/api/v1/executions/{execution_id}/approve-write",
                params={"persona_key": "marc"},
                json={"approved": True, "preview_id": preview_id},
            )
            assert approve_resp.status_code == 200, approve_resp.text
            completed = approve_resp.json()
            assert completed["status"] == "COMPLETED"
            assert completed["artifact_pointer"] is not None
            assert len(completed["artifact_pointer"]["sha256"]) == 64

            # 7. Real SSE stream (`GET .../trace-stream`) preserving `\n` + Redis 7.4 history
            async with client2.stream(
                "GET",
                f"/api/v1/executions/{execution_id}/trace-stream",
                params={"persona_key": "marc"},
            ) as sse_resp:
                assert sse_resp.status_code == 200
                assert sse_resp.headers["content-type"].startswith("text/event-stream")
                raw_sse = (await sse_resp.aread()).decode("utf-8")

            assert "event: write_preview_requested" in raw_sse
            assert "event: answer_token_delta" in raw_sse
            assert "event: loop_completed" in raw_sse
            sse_data_lines = [
                json.loads(line.removeprefix("data: "))
                for line in raw_sse.splitlines()
                if line.startswith("data: ")
            ]
            answer_deltas = [
                ev["delta_text"]
                for ev in sse_data_lines
                if ev["kind"] == "answer_token_delta" and ev.get("delta_text")
            ]
            assert any("\n" in chunk for chunk in answer_deltas)

        # Verify SQL status == COMPLETED and Redis 7.4 history populated
        async with engine.connect() as conn:
            status_db = (
                await conn.execute(
                    sa.text(
                        "SELECT status FROM reflexive_execution_sessions WHERE execution_id = :id"
                    ),
                    {"id": execution_id},
                )
            ).scalar_one()
        assert status_db == "COMPLETED"

        rd_client = redis_sync.Redis(unix_socket_path=str(rd_sock_path), decode_responses=True)
        try:
            rd_events = rd_client.lrange(f"orcia:reflexive:history:{execution_id}", 0, -1)
            assert len(rd_events) >= 2
        finally:
            rd_client.close()

        # 8. Verify Day-0 reset script clears `reflexive_execution_sessions` cleanly
        reset_mod = _load_reset_script()
        dry_rep = await reset_mod.reset_database_to_first_boot(engine, apply_changes=False)
        assert dry_rep.dry_run is True and dry_rep.committed is False
        apply_rep = await reset_mod.reset_database_to_first_boot(engine, apply_changes=True)
        assert apply_rep.committed is True
        async with engine.connect() as conn:
            remaining = (
                await conn.execute(sa.text("SELECT COUNT(*) FROM reflexive_execution_sessions"))
            ).scalar_one()
        assert remaining == 0
    finally:
        await engine.dispose()


async def test_observer_403_rejection_cancel_and_synthesize_now_postgres18(
    pg18_and_redis74_urls: tuple[str, str, Path],
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify `403 ERR_OBSERVER_MODE_READ_ONLY`, write rejection, `cancel`, & `synthesize-now`."""
    pg_url, redis_url, _rd_sock = pg18_and_redis74_urls
    monkeypatch.setenv("DATABASE_URL", pg_url)
    monkeypatch.setenv("ORCIA_ENV_FILE", str(REPO_ROOT / ".orcia-run" / "does-not-exist.env"))
    monkeypatch.setenv("ORCIA_ENABLE_PG_SESSION_MAKER", "1")
    monkeypatch.setenv("REDIS_URL", redis_url)
    monkeypatch.setenv("ORCIA_USE_CASSETTE_LLM", "true")

    app = create_app()
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app),
        base_url="http://testserver",
    ) as client:
        # 1. Observer (`claire` / `READ_ONLY_OBSERVER`) gets 403 on all 4 mutation routes
        obs_start = await client.post(
            "/api/v1/executions/reflexive",
            params={"persona_key": "claire"},
            json={"objective": "Tentative observateur"},
        )
        assert obs_start.status_code == 403
        assert obs_start.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"

        obs_hdr = await client.post(
            "/api/v1/executions/reflexive",
            headers={"X-Orcia-Access-Mode": "READ_ONLY_OBSERVER"},
            params={"persona_key": "marc"},
            json={"objective": "Tentative header observateur"},
        )
        assert obs_hdr.status_code == 403
        assert obs_hdr.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"

        # 2. Human write rejection (`approved=False`) -> recorded in scratchpad & COMPLETED
        paused_resp = await client.post(
            "/api/v1/executions/reflexive",
            params={"persona_key": "marc"},
            json={
                "objective": "Proposer une écriture qui sera refusée",
                "requested_write_preview": {
                    "connector_type": "mcp:default",
                    "action": "update_doc",
                    "target_resource_uri": "catalog://docs/frozen",
                    "action_summary": "Modifier document gelé",
                    "payload": {"body": "Draft"},
                },
            },
        )
        assert paused_resp.status_code == 200
        exec_reject_id = paused_resp.json()["execution_id"]
        preview_reject_id = paused_resp.json()["pending_write_preview"]["preview_id"]

        for route_suffix, body in (
            ("cancel", None),
            ("synthesize-now", None),
            ("approve-write", {"approved": False, "preview_id": preview_reject_id}),
        ):
            obs_mut = await client.post(
                f"/api/v1/executions/{exec_reject_id}/{route_suffix}",
                params={"persona_key": "claire"},
                json=body,
            )
            assert obs_mut.status_code == 403
            assert obs_mut.json()["error_code"] == "ERR_OBSERVER_MODE_READ_ONLY"

        rejected_resp = await client.post(
            f"/api/v1/executions/{exec_reject_id}/approve-write",
            params={"persona_key": "marc"},
            json={
                "approved": False,
                "preview_id": preview_reject_id,
                "rejection_reason": "Périmètre gelé pour audit",
            },
        )
        assert rejected_resp.status_code == 200
        rejected_data = rejected_resp.json()
        assert rejected_data["status"] == "COMPLETED"
        assert any(
            item["action_kind"] == "external_write_rejected" and "Périmètre gelé" in item["summary"]
            for item in rejected_data["scratchpad"]
        )

        # 3. Background start + `cancel` (`■ Arrêter`) -> CANCELLED
        bg_cancel = await client.post(
            "/api/v1/executions/reflexive",
            params={"persona_key": "marc"},
            json={
                "objective": "Exploration longue à interrompre",
                "effort_mode": "approfondi",
                "initial_resources": ["docs/product/capabilities.yaml"],
                "run_in_background": True,
                "step_delay_ms": 200,
            },
        )
        assert bg_cancel.status_code == 200
        cancel_id = bg_cancel.json()["execution_id"]
        cancel_resp = await client.post(
            f"/api/v1/executions/{cancel_id}/cancel",
            params={"persona_key": "marc"},
        )
        assert cancel_resp.status_code == 200
        assert cancel_resp.json()["status"] == "CANCELLED"

        # 4. Background start + `synthesize-now` -> force_final=True
        bg_synth = await client.post(
            "/api/v1/executions/reflexive",
            params={"persona_key": "marc"},
            json={
                "objective": "Exploration avec synthèse anticipée",
                "effort_mode": "approfondi",
                "initial_resources": ["docs/product/capabilities.yaml"],
                "run_in_background": True,
                "step_delay_ms": 120,
            },
        )
        assert bg_synth.status_code == 200
        synth_id = bg_synth.json()["execution_id"]
        synth_resp = await client.post(
            f"/api/v1/executions/{synth_id}/synthesize-now",
            params={"persona_key": "marc"},
        )
        assert synth_resp.status_code == 200
        assert synth_resp.json()["force_final"] is True
