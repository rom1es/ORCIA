"""Pile E2E isolée (TEST-01) : PostgreSQL 18 + Redis 7.4 éphémères, migrations, FastAPI.

Lancée par `apps/web/playwright.config.ts` (`webServer`). Reste au premier plan jusqu'à
`SIGTERM`/`SIGINT`, puis arrête l'API et supprime les conteneurs.

Usage : `.venv/bin/python infra/scripts/e2e/e2e_stack.py [--api-port 8100]`
"""

from __future__ import annotations

import argparse
import signal
import subprocess
import sys
import threading
from pathlib import Path
from urllib.parse import quote_plus

sys.path.insert(0, str(Path(__file__).resolve().parent))

from e2e_stack_config import (  # noqa: E402
    E2E_DB_NAME,
    REPO_ROOT,
    STATE_FILE,
    build_api_env,
    process_env,
    write_state,
)
from testcontainers.postgres import PostgresContainer  # noqa: E402
from testcontainers.redis import RedisContainer  # noqa: E402

PG_IMAGE = "pgvector/pgvector:pg18"
REDIS_IMAGE = "redis:7.4-alpine"
E2E_DB_USER = "orcia"
E2E_DB_PASSWORD = "orcia_e2e_pw"  # pragma: allowlist secret


def _log(message: str) -> None:
    print(f"[e2e-stack] {message}", flush=True)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Pile E2E ORCIA isolée.")
    parser.add_argument("--api-port", type=int, default=8100)
    args = parser.parse_args(argv)

    stop = threading.Event()
    for sig in (signal.SIGTERM, signal.SIGINT):
        signal.signal(sig, lambda *_: stop.set())

    pg = PostgresContainer(
        PG_IMAGE, username=E2E_DB_USER, password=E2E_DB_PASSWORD, dbname=E2E_DB_NAME
    )
    redis = RedisContainer(REDIS_IMAGE)
    api_proc: subprocess.Popen[bytes] | None = None
    try:
        _log("démarrage PostgreSQL 18 + Redis 7.4 éphémères…")
        pg.start()
        redis.start()
        database_url = (
            f"postgresql+asyncpg://{E2E_DB_USER}:{quote_plus(E2E_DB_PASSWORD)}"
            f"@127.0.0.1:{pg.get_exposed_port(5432)}/{E2E_DB_NAME}"
        )
        redis_url = f"redis://127.0.0.1:{redis.get_exposed_port(6379)}/0"
        env = build_api_env(
            base_env=process_env(),
            database_url=database_url,
            redis_url=redis_url,
            api_port=args.api_port,
        )

        _log("migrations Alembic (upgrade head)…")
        subprocess.run(
            [
                str(REPO_ROOT / ".venv" / "bin" / "alembic"),
                "-c",
                "infra/migrations/alembic.ini",
                "upgrade",
                "head",
            ],
            cwd=REPO_ROOT,
            env=env,
            check=True,
        )
        write_state(
            STATE_FILE, database_url=database_url, redis_url=redis_url, api_port=args.api_port
        )

        _log(f"démarrage FastAPI sur 127.0.0.1:{args.api_port} (cassette LLM, base {E2E_DB_NAME})")
        api_proc = subprocess.Popen(
            [
                sys.executable,
                "-m",
                "uvicorn",
                "orcia_api.main:create_app",
                "--factory",
                "--host",
                "127.0.0.1",
                "--port",
                str(args.api_port),
                "--log-level",
                "warning",
            ],
            cwd=REPO_ROOT,
            env=env,
        )
        while not stop.is_set():
            if api_proc.poll() is not None:
                _log(f"l'API s'est arrêtée (code {api_proc.returncode})")
                return 1
            stop.wait(0.5)
        return 0
    finally:
        _log("arrêt de la pile E2E…")
        if api_proc is not None and api_proc.poll() is None:
            api_proc.terminate()
            try:
                api_proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                api_proc.kill()
        for container in (redis, pg):
            try:
                container.stop()
            except Exception as exc:  # teardown best-effort : on journalise sans masquer
                _log(f"arrêt conteneur en échec : {exc}")
        STATE_FILE.unlink(missing_ok=True)


if __name__ == "__main__":
    raise SystemExit(main())
