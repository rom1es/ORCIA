"""Remise à zéro Jour 0 de la pile E2E isolée (`orcia_e2e` + Redis 7.4 + caches RAM API).

Exécute :
1. Garde bloquant `is_isolated_e2e_database_url(...)` (`orcia_e2e` local hors 5432/5433).
2. `TRUNCATE TABLE ... RESTART IDENTITY CASCADE` atomique sur `public` (hors
   `alembic_version`, `connector_schemes`) et `dbos` (hors tables de migrations DBOS),
   sans jamais désactiver les triggers append-only (`BEFORE UPDATE OR DELETE`).
3. Réinitialisation `platform_auth_settings` + seed socle `connector_schemes` (`0` user).
4. `FLUSHDB` Redis 7.4 si `redis_url` est fourni.
5. `POST /api/v1/_e2e/evict-memory-caches` si `api_port` est fourni et joignable.
"""

from __future__ import annotations

import asyncio
import importlib.util
import re
import sys
from collections.abc import Awaitable, Callable, Mapping
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, cast

import httpx
import redis
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine

sys.path.insert(0, str(Path(__file__).resolve().parent))

from e2e_stack_config import (  # noqa: E402
    REPO_ROOT,
    is_isolated_e2e_database_url,
    read_state,
)

for _rel_pkg in ("packages/orcia-kernel/src", "packages/orcia-core/src"):
    _pkg_path = str(REPO_ROOT / _rel_pkg)
    if _pkg_path not in sys.path:
        sys.path.insert(0, _pkg_path)

from orcia_core.bootstrap import upsert_declarative_pack_bundles_sql  # noqa: E402
from orcia_core.packs.loader import (  # noqa: E402
    DeclarativePackLoader,
    resolve_default_packs_root,
)

RESET_SCRIPT = REPO_ROOT / "infra" / "scripts" / "maintenance" / "09_reset_db_first_boot.py"

PUBLIC_EXCLUDED_TABLES: frozenset[str] = frozenset({"alembic_version", "connector_schemes"})
DBOS_EXCLUDED_TABLES: frozenset[str] = frozenset(
    {"dbos_migrations", "dbos_datasource_migrations", "alembic_version"}
)
_SAFE_IDENT_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")


def _normalize_async_pg_url(database_url: str) -> str:
    return re.sub(
        r"^postgresql(?:\+(?:psycopg2|psycopg))?://", "postgresql+asyncpg://", database_url
    )


def _quote_table(schema: str, table: str) -> str:
    if not _SAFE_IDENT_RE.match(schema) or not _SAFE_IDENT_RE.match(table):
        raise ValueError(f"Identifiant SQL invalide : {schema!r}.{table!r}")
    return f'"{schema}"."{table}"'


def _load_seed_reset_fn() -> Callable[..., Awaitable[None]]:
    spec = importlib.util.spec_from_file_location("orcia_reset_db_first_boot", RESET_SCRIPT)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Impossible de charger {RESET_SCRIPT}")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    fn = getattr(module, "reset_platform_auth_settings_and_system_seed", None)
    if fn is None:
        raise RuntimeError("Fonction `reset_platform_auth_settings_and_system_seed` introuvable.")
    return cast(Callable[..., Awaitable[None]], fn)


async def _reset_postgres_e2e(database_url: str) -> tuple[list[str], list[str], int]:
    seed_reset_fn = _load_seed_reset_fn()
    engine = create_async_engine(_normalize_async_pg_url(database_url), pool_pre_ping=False)
    try:
        all_public: list[str] = []
        public_to_truncate: list[str] = []
        dbos_to_truncate: list[str] = []
        users_count = 0
        async with engine.begin() as conn:
            public_rows = await conn.execute(
                sa.text(
                    "SELECT tablename FROM pg_tables "
                    "WHERE schemaname = 'public' ORDER BY tablename ASC"
                )
            )
            all_public = [str(r[0]) for r in public_rows.fetchall()]
            public_to_truncate = [t for t in all_public if t not in PUBLIC_EXCLUDED_TABLES]

            dbos_rows = await conn.execute(
                sa.text(
                    "SELECT tablename FROM pg_tables "
                    "WHERE schemaname = 'dbos' ORDER BY tablename ASC"
                )
            )
            dbos_to_truncate = [
                str(r[0]) for r in dbos_rows.fetchall() if str(r[0]) not in DBOS_EXCLUDED_TABLES
            ]

            qualified = [_quote_table("public", t) for t in public_to_truncate] + [
                _quote_table("dbos", t) for t in dbos_to_truncate
            ]
            if qualified:
                await conn.execute(
                    sa.text(f"TRUNCATE TABLE {', '.join(qualified)} RESTART IDENTITY CASCADE")
                )

            await seed_reset_fn(conn, existing_tables=set(all_public))

            if "users" in all_public:
                users_count = int(
                    (await conn.execute(sa.text("SELECT COUNT(*) FROM users"))).scalar() or 0
                )

        if "declarative_pack_bundles" in all_public:
            pack_bundles = DeclarativePackLoader(resolve_default_packs_root()).load_all_packs()
            await upsert_declarative_pack_bundles_sql(engine, pack_bundles)

        return public_to_truncate, dbos_to_truncate, users_count
    finally:
        await engine.dispose()


def _run_async(
    coro: Awaitable[tuple[list[str], list[str], int]],
) -> tuple[list[str], list[str], int]:
    async def _runner() -> tuple[list[str], list[str], int]:
        return await coro

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(_runner())
    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(asyncio.run, _runner()).result()


def _flush_redis(redis_url: str) -> None:
    client = redis.Redis.from_url(redis_url)
    try:
        client.flushdb()
    finally:
        client.close()


def _evict_api_memory_caches(api_port: int) -> bool:
    url = f"http://127.0.0.1:{api_port}/api/v1/_e2e/evict-memory-caches"
    try:
        resp = httpx.post(url, timeout=5.0)
    except httpx.ConnectError:
        return False
    if resp.status_code >= 400:
        raise RuntimeError(
            f"Échec éviction caches mémoire API ({url}) : HTTP {resp.status_code} {resp.text}"
        )
    return True


def reset_day0_environment(
    state: Mapping[str, Any] | None = None,
    *,
    database_url: str | None = None,
    redis_url: str | None = None,
    api_port: int | None = None,
) -> dict[str, Any]:
    """Réinitialise la base `orcia_e2e`, Redis 7.4 et les caches mémoire de l'API E2E."""
    resolved_state: Mapping[str, Any]
    if state is not None:
        resolved_state = state
    elif database_url is None:
        resolved_state = read_state()
    else:
        resolved_state = {}

    db_url = str(
        database_url if database_url is not None else resolved_state.get("database_url", "")
    ).strip()
    if not is_isolated_e2e_database_url(db_url):
        raise RuntimeError(
            "REFUS : base non isolée (`orcia_e2e` sur hôte local hors ports 5432/5433 requis)."
        )

    raw_redis = redis_url if redis_url is not None else resolved_state.get("redis_url", "")
    resolved_redis = str(raw_redis).strip() if raw_redis is not None else ""

    raw_port = api_port if api_port is not None else resolved_state.get("api_port")
    resolved_port = int(raw_port) if raw_port is not None and str(raw_port).strip() else None

    public_tables, dbos_tables, users_count = _run_async(_reset_postgres_e2e(db_url))

    redis_flushed = False
    if resolved_redis:
        _flush_redis(resolved_redis)
        redis_flushed = True

    api_caches_evicted = False
    if resolved_port is not None:
        api_caches_evicted = _evict_api_memory_caches(resolved_port)

    return {
        "truncated_public_tables": public_tables,
        "truncated_dbos_tables": dbos_tables,
        "redis_flushed": redis_flushed,
        "api_caches_evicted": api_caches_evicted,
        "remaining_users_count": users_count,
    }


def main() -> int:
    """Point d'entrée CLI invoqué par Playwright (`apps/web/e2e/support/day0.ts`)."""
    try:
        summary = reset_day0_environment()
    except (FileNotFoundError, RuntimeError, ValueError) as exc:
        print(f"[e2e-reset] {exc}", file=sys.stderr)
        return 2
    if int(summary.get("remaining_users_count", 0)) != 0:
        print("[e2e-reset] ERREUR : des utilisateurs subsistent après reset.", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
