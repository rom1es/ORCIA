"""Maintenance script `09_reset_db_first_boot.py` — Reset database to Day-0 First-Boot state.

Allows resetting the ORCIA PostgreSQL 18 database to the clean 1st-boot state (`0` users, `0`
workspaces, `0` org_units, `0` runs) so the Day-0 Initial Platform Administrator creation screen
(`first-boot-admin-setup-modal` / `/welcome-setup`) is presented again as on first launch.

Conventions (GEMINI.md):
- Mandatory `--dry-run` mode by default (rolls back unless `--apply` is explicitly passed).
- Never disables append-only triggers (`trg_blackboard_snapshots_append_only`, etc.).
- Uses `information_schema.tables` + `pg_constraint` / `pg_trigger` dynamic introspection.
"""

from __future__ import annotations

import argparse
import asyncio
import os
import sys
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

import redis
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine

_HERE = str(Path(__file__).resolve().parent)
_CORE_SRC = str(Path(__file__).resolve().parents[3] / "packages" / "orcia-core" / "src")
_KERNEL_SRC = str(Path(__file__).resolve().parents[3] / "packages" / "orcia-kernel" / "src")
for _src_path in (_HERE, _KERNEL_SRC, _CORE_SRC):
    if _src_path not in sys.path:
        sys.path.insert(0, _src_path)

from _first_boot_reset_guards import (  # noqa: E402
    BASE_CONNECTOR_SCHEMES,
    DBOS_EXCLUDED_TABLES,
    ORDERED_MUTABLE_TABLES_TO_CLEAR,
    PROTECTED_TABLES,
    assert_no_append_only_restrict_refs,
    inspect_append_only_guards,
    quote_sql_ident,
)

from orcia_core.bootstrap import upsert_declarative_pack_bundles_sql  # noqa: E402
from orcia_core.config import resolve_database_url  # noqa: E402
from orcia_core.packs.loader import (  # noqa: E402
    DeclarativePackLoader,
    resolve_default_packs_root,
)
from orcia_kernel.ids import new_uuid7_str  # noqa: E402

_assert_no_append_only_restrict_refs = assert_no_append_only_restrict_refs


@dataclass(frozen=True, slots=True)
class FirstBootResetReport:
    """Summary of the Day-0 First-Boot database reset execution."""

    cleared_tables_count: int
    deleted_rows_total: int
    remaining_users_count: int
    remaining_org_units_count: int
    remaining_workspaces_count: int
    dry_run: bool
    committed: bool


async def reset_platform_auth_settings_and_system_seed(
    conn: AsyncConnection,
    *,
    existing_tables: set[str] | None = None,
) -> None:
    """Reset `platform_auth_settings` to Day-0 LOCAL defaults and ensure base connector schemes."""
    if existing_tables is None:
        existing_rows = await conn.execute(
            sa.text(
                "SELECT table_name FROM information_schema.tables "
                "WHERE table_schema = 'public' AND table_type = 'BASE TABLE'"
            )
        )
        existing_tables = {str(r[0]) for r in existing_rows.fetchall()}

    if "platform_auth_settings" in existing_tables:
        await conn.execute(
            sa.text(
                """
                INSERT INTO platform_auth_settings (
                    singleton_key, auth_mode, two_factor_mode, oidc_scopes, boot_epoch
                )
                VALUES ('GLOBAL', 'LOCAL', 'NONE', 'openid profile email', :boot_epoch)
                ON CONFLICT (singleton_key) DO UPDATE SET
                    auth_mode = 'LOCAL', two_factor_mode = 'NONE',
                    oidc_issuer_url = NULL, oidc_client_id = NULL,
                    oidc_client_secret_encrypted = NULL, oidc_client_secret_fingerprint = NULL,
                    oidc_scopes = 'openid profile email', oidc_redirect_uri = NULL,
                    sso_button_label = NULL, boot_epoch = EXCLUDED.boot_epoch,
                    updated_by = NULL, updated_at = NOW();
                """
            ),
            {"boot_epoch": UUID(new_uuid7_str())},
        )

    if "connector_schemes" in existing_tables:
        for scheme_id, scheme, display_name, pack_name in BASE_CONNECTOR_SCHEMES:
            await conn.execute(
                sa.text(
                    """
                    INSERT INTO connector_schemes (id, scheme, display_name, pack_name, is_active)
                    VALUES (:id, :scheme, :display_name, :pack_name, TRUE)
                    ON CONFLICT (scheme) DO NOTHING;
                    """
                ),
                {
                    "id": UUID(scheme_id),
                    "scheme": scheme,
                    "display_name": display_name,
                    "pack_name": pack_name,
                },
            )


def _flush_redis_if_configured() -> None:
    redis_url = (os.environ.get("REDIS_URL") or "").strip()
    if not redis_url:
        return
    client = redis.Redis.from_url(redis_url, socket_connect_timeout=1.5)
    try:
        client.flushdb()
    except redis.RedisError as exc:
        print(f"[09_reset_db_first_boot] Redis flush skipped ({exc})", file=sys.stderr)
    finally:
        client.close()


async def reset_database_to_first_boot(
    engine: AsyncEngine,
    *,
    apply_changes: bool = False,
) -> FirstBootResetReport:
    """Reset mutable tables to the clean Day-0 First-Boot state (`COUNT(*) FROM users == 0`)."""
    deleted_total = 0
    cleared_tables = 0
    existing_tables: set[str] = set()

    async with engine.connect() as conn:
        trans = await conn.begin()
        try:
            schema_rows = await conn.execute(
                sa.text(
                    "SELECT table_schema, table_name FROM information_schema.tables "
                    "WHERE table_type = 'BASE TABLE' AND table_schema IN ('public', 'dbos') "
                    "ORDER BY table_schema ASC, table_name ASC"
                )
            )
            all_rows = [(str(r[0]), str(r[1])) for r in schema_rows.fetchall()]
            existing_tables = {t for s, t in all_rows if s == "public"}
            dbos_tables = [t for s, t in all_rows if s == "dbos" and t not in DBOS_EXCLUDED_TABLES]

            unclassified = existing_tables - PROTECTED_TABLES - set(ORDERED_MUTABLE_TABLES_TO_CLEAR)
            if unclassified:
                raise RuntimeError(
                    "Tables Alembic orphelines non classées dans PROTECTED_TABLES ou "
                    f"ORDERED_MUTABLE_TABLES_TO_CLEAR : {sorted(unclassified)}"
                )

            extra_guarded = await inspect_append_only_guards(conn, existing_tables)
            for table_name in ORDERED_MUTABLE_TABLES_TO_CLEAR:
                if table_name in PROTECTED_TABLES or table_name not in existing_tables:
                    continue
                await _assert_no_append_only_restrict_refs(
                    conn, table_name, existing_tables, extra_guarded_tables=extra_guarded
                )
                res = await conn.execute(sa.text(f"DELETE FROM {table_name}"))
                deleted_total += int(res.rowcount or 0)
                cleared_tables += 1

            if dbos_tables:
                qualified_dbos = ", ".join(quote_sql_ident("dbos", t) for t in dbos_tables)
                await conn.execute(
                    sa.text(f"TRUNCATE TABLE {qualified_dbos} RESTART IDENTITY CASCADE")
                )
                cleared_tables += len(dbos_tables)

            await reset_platform_auth_settings_and_system_seed(
                conn, existing_tables=existing_tables
            )
            users_cnt = int(
                (await conn.execute(sa.text("SELECT COUNT(*) FROM users"))).scalar() or 0
            )
            org_cnt = int(
                (await conn.execute(sa.text("SELECT COUNT(*) FROM org_units"))).scalar() or 0
            )
            ws_cnt = int(
                (await conn.execute(sa.text("SELECT COUNT(*) FROM workspaces"))).scalar() or 0
            )

            if apply_changes:
                await trans.commit()
                committed = True
            else:
                await trans.rollback()
                committed = False
        except Exception:
            if trans.is_active:
                await trans.rollback()
            raise

    if committed:
        if "declarative_pack_bundles" in existing_tables:
            pack_bundles = DeclarativePackLoader(resolve_default_packs_root()).load_all_packs()
            await upsert_declarative_pack_bundles_sql(engine, pack_bundles)
        _flush_redis_if_configured()

    return FirstBootResetReport(
        cleared_tables_count=cleared_tables,
        deleted_rows_total=deleted_total,
        remaining_users_count=users_cnt,
        remaining_org_units_count=org_cnt,
        remaining_workspaces_count=ws_cnt,
        dry_run=not apply_changes,
        committed=committed,
    )


def build_arg_parser() -> argparse.ArgumentParser:
    """Build CLI argument parser with mandatory `--dry-run` default."""
    parser = argparse.ArgumentParser(
        description=(
            "Reset the ORCIA PostgreSQL 18 database to Day-0 First-Boot state "
            "(0 users, 0 workspaces, 0 org_units — defaults to --dry-run)."
        )
    )
    parser.add_argument(
        "--database-url",
        default="",
        help="Optional explicit async SQLAlchemy database URL (defaults to .env resolution).",
    )
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--dry-run", action="store_true", default=True, help="Simulate and roll back (default)."
    )
    mode_group.add_argument(
        "--apply", action="store_true", default=False, help="Commit the database reset."
    )
    return parser


async def _async_main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    db_url = args.database_url.strip() or resolve_database_url()
    engine = create_async_engine(db_url)
    try:
        report = await reset_database_to_first_boot(engine, apply_changes=bool(args.apply))
        mode_str = "APPLY (COMMITTED)" if report.committed else "DRY-RUN (ROLLED BACK)"
        print(
            f"[09_reset_db_first_boot] {mode_str} — "
            f"cleared_tables={report.cleared_tables_count}, "
            f"deleted_rows={report.deleted_rows_total}, "
            f"remaining_users={report.remaining_users_count}, "
            f"remaining_org_units={report.remaining_org_units_count}, "
            f"remaining_workspaces={report.remaining_workspaces_count}"
        )
        return 0 if report.remaining_users_count == 0 else 1
    finally:
        await engine.dispose()


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    return asyncio.run(_async_main(argv))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
