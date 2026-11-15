"""Maintenance script `10_reset_auth_mode_local.py` — Break-Glass Auth Mode Recovery.

Resets `platform_auth_settings` singleton `GLOBAL` back to exclusive `LOCAL` authentication with
`two_factor_mode = 'NONE'` so an administrator can regain access if misconfigured SSO blocks login.

Defaults to `--dry-run`; pass `--apply` to commit.
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

_CORE_SRC = str(Path(__file__).resolve().parents[3] / "packages" / "orcia-core" / "src")
_KERNEL_SRC = str(Path(__file__).resolve().parents[3] / "packages" / "orcia-kernel" / "src")
for _src_path in (_KERNEL_SRC, _CORE_SRC):
    if _src_path not in sys.path:
        sys.path.insert(0, _src_path)

from orcia_core.bootstrap import ensure_platform_auth_policy_schema  # noqa: E402
from orcia_core.config import resolve_database_url  # noqa: E402
from orcia_kernel.ids import new_uuid7_str  # noqa: E402


@dataclass(frozen=True, slots=True)
class AuthModeResetReport:
    """Outcome summary of break-glass local auth reset."""

    previous_auth_mode: str
    previous_two_factor_mode: str
    auth_mode: str
    two_factor_mode: str
    dry_run: bool
    committed: bool


async def reset_auth_mode_to_local(
    engine: AsyncEngine,
    *,
    apply_changes: bool = False,
) -> AuthModeResetReport:
    """Reset `platform_auth_settings` (`GLOBAL`) back to `LOCAL` + `NONE`."""
    async with engine.connect() as conn:
        trans = await conn.begin()
        try:
            await ensure_platform_auth_policy_schema(conn)
            cur = (
                await conn.execute(
                    sa.text(
                        "SELECT auth_mode, two_factor_mode FROM platform_auth_settings "
                        "WHERE singleton_key = 'GLOBAL';"
                    )
                )
            ).fetchone()
            prev_auth = str(cur[0]) if cur else "UNKNOWN"
            prev_2fa = str(cur[1]) if cur else "UNKNOWN"

            await conn.execute(
                sa.text(
                    """
                    UPDATE platform_auth_settings
                    SET auth_mode = 'LOCAL',
                        two_factor_mode = 'NONE',
                        updated_by = 'cli:10_reset_auth_mode_local',
                        updated_at = NOW()
                    WHERE singleton_key = 'GLOBAL';
                    """
                )
            )
            await conn.execute(
                sa.text(
                    "UPDATE platform_auth_settings SET boot_epoch = COALESCE(boot_epoch, :ep);"
                ),
                {"ep": UUID(new_uuid7_str())},
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

    return AuthModeResetReport(
        previous_auth_mode=prev_auth,
        previous_two_factor_mode=prev_2fa,
        auth_mode="LOCAL",
        two_factor_mode="NONE",
        dry_run=not apply_changes,
        committed=committed,
    )


def build_arg_parser() -> argparse.ArgumentParser:
    """Build CLI parser with mandatory `--dry-run` default."""
    parser = argparse.ArgumentParser(
        description="Break-glass reset of ORCIA platform auth mode back to LOCAL + NONE."
    )
    parser.add_argument("--database-url", default="", help="Optional async SQLAlchemy DB URL.")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--dry-run", action="store_true", default=True, help="Default dry-run mode.")
    mode.add_argument("--apply", action="store_true", default=False, help="Commit LOCAL reset.")
    return parser


async def _async_main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    db_url = args.database_url.strip() or resolve_database_url()
    engine = create_async_engine(db_url)
    try:
        report = await reset_auth_mode_to_local(engine, apply_changes=bool(args.apply))
        mode_str = "APPLY (COMMITTED)" if report.committed else "DRY-RUN (ROLLED BACK)"
        print(
            f"[10_reset_auth_mode_local] {mode_str} — "
            f"{report.previous_auth_mode}/{report.previous_two_factor_mode} "
            f"-> {report.auth_mode}/{report.two_factor_mode}"
        )
        return 0
    finally:
        await engine.dispose()


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    return asyncio.run(_async_main(argv))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
