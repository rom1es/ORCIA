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
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

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

from orcia_core.packs import seed_system_packs_on_engine  # noqa: E402

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


async def _verify_post_reset_invariants(
    engine: AsyncEngine,
    all_public: list[str],
    dbos_to_truncate: list[str],
) -> None:
    """Verify triggers `'O'`, `pg_constraint`, `dbos.* == 0`, and Day-0 seeds after reset."""
    async with engine.connect() as conn:
        # 1. Verify append-only triggers on audit_ledger / blackboard_snapshots stay enabled ('O')
        append_only = [t for t in ("audit_ledger", "blackboard_snapshots") if t in all_public]
        if append_only:
            trig_rows = (
                await conn.execute(
                    sa.text(
                        """
                        SELECT c.relname, t.tgname, t.tgenabled::text
                        FROM pg_trigger t
                        JOIN pg_class c ON c.oid = t.tgrelid
                        JOIN pg_namespace n ON n.oid = c.relnamespace
                        WHERE n.nspname = 'public' AND NOT t.tgisinternal
                          AND c.relname = ANY(:tables)
                        """
                    ),
                    {"tables": append_only},
                )
            ).fetchall()
            if not trig_rows or any(str(r[2]) != "O" for r in trig_rows):
                raise RuntimeError(f"Triggers append-only invalides après reset : {trig_rows!r}")

            # 2. Inspect ON DELETE RESTRICT constraints via pg_constraint (append-only & seeds)
            restrict_rows = (
                await conn.execute(
                    sa.text(
                        """
                        SELECT conname
                        FROM pg_constraint
                        WHERE contype = 'f' AND confdeltype = 'r'
                          AND connamespace = 'public'::regnamespace
                        """
                    )
                )
            ).fetchall()
            restrict_names = {str(r[0]) for r in restrict_rows}
            expected_restrict = (
                {"blackboard_snapshots_step_execution_id_fkey"}
                if "blackboard_snapshots" in all_public
                else set()
            )
            if not restrict_names or not expected_restrict.issubset(restrict_names):
                raise RuntimeError(
                    "Contraintes ON DELETE RESTRICT attendues manquantes dans pg_constraint : "
                    f"attendu={sorted(expected_restrict)}, trouve={sorted(restrict_names)}"
                )

        # 3. Verify runtime dbos.* tables are empty
        for dbos_tbl in dbos_to_truncate:
            dbos_q = _quote_table("dbos", dbos_tbl)
            cnt = int((await conn.execute(sa.text(f"SELECT COUNT(*) FROM {dbos_q}"))).scalar() or 0)
            if cnt != 0:
                raise RuntimeError(f"Table runtime dbos.{dbos_tbl} non vide après reset ({cnt}).")

        # 4. Verify Day-0 seeds: connector_schemes >= 7 & declarative_pack_bundles >= 1.
        # Note: `catalog_items` (`HELP_ARTICLE`) porte une FK `ON DELETE RESTRICT` vers `org_units`
        # vide au Jour 0 ; il s'amorce paresseusement dès qu'une organisation existe.
        if "connector_schemes" in all_public:
            schemes_q = await conn.execute(sa.text("SELECT COUNT(*) FROM connector_schemes"))
            schemes_cnt = int(schemes_q.scalar() or 0)
            if schemes_cnt < 7:
                raise RuntimeError(f"Seed connector_schemes incomplet ({schemes_cnt} < 7).")
        if "declarative_pack_bundles" in all_public:
            packs_q = await conn.execute(sa.text("SELECT COUNT(*) FROM declarative_pack_bundles"))
            packs_cnt = int(packs_q.scalar() or 0)
            if packs_cnt < 1:
                raise RuntimeError(f"Seed declarative_pack_bundles absent ({packs_cnt} < 1).")


async def _reset_postgres_e2e(database_url: str) -> tuple[list[str], list[str], int]:
    seed_reset_fn = _load_seed_reset_fn()
    engine = create_async_engine(_normalize_async_pg_url(database_url), pool_pre_ping=False)
    try:
        all_public: list[str] = []
        public_to_truncate: list[str] = []
        dbos_to_truncate: list[str] = []
        users_count = 0
        async with engine.begin() as conn:
            schema_rows = await conn.execute(
                sa.text(
                    "SELECT table_schema, table_name FROM information_schema.tables "
                    "WHERE table_type = 'BASE TABLE' AND table_schema IN ('public', 'dbos') "
                    "ORDER BY table_schema ASC, table_name ASC"
                )
            )
            discovered = [(str(r[0]), str(r[1])) for r in schema_rows.fetchall()]
            all_public = [t for s, t in discovered if s == "public"]
            public_to_truncate = [t for t in all_public if t not in PUBLIC_EXCLUDED_TABLES]
            dbos_to_truncate = [
                t for s, t in discovered if s == "dbos" and t not in DBOS_EXCLUDED_TABLES
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
            await seed_system_packs_on_engine(engine)

        await _verify_post_reset_invariants(engine, all_public, dbos_to_truncate)
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
        if int(client.dbsize()) != 0:
            raise RuntimeError("Redis DBSIZE != 0 après FLUSHDB.")
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
    resolved_state: Mapping[str, Any] = (
        state if state is not None else (read_state() if database_url is None else {})
    )

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
