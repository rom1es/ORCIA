"""Reference maintenance script verifying ORCIA database invariants.

Conventions (AGENTS.md):
- Operational data transformations or verification scripts live in
  `infra/scripts/maintenance/XX_*.py`.
- Mandatory `--dry-run` mode (default rollback unless `--apply` is explicitly passed).
- Uses batched idempotent transactions.
"""

from __future__ import annotations

import argparse
import asyncio
import os
from dataclasses import dataclass

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine


@dataclass(frozen=True, slots=True)
class DbInvariantReport:
    """Summary of foundation database invariants checked by maintenance script."""

    has_vector_extension: bool
    has_append_only_trigger_fn: bool
    dry_run: bool
    committed: bool


async def verify_database_invariants(
    engine: AsyncEngine,
    *,
    apply_changes: bool = False,
    batch_size: int = 100,
) -> DbInvariantReport:
    """Verify pgvector and append-only trigger function inside a controlled transaction.

    Rolls back by default unless `apply_changes=True` is explicitly provided.
    """
    if batch_size <= 0:
        raise ValueError("batch_size must be strictly positive")

    async with engine.connect() as conn:
        trans = await conn.begin()
        try:
            vec_res = await conn.execute(
                sa.text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname = 'vector')")
            )
            has_vector = bool(vec_res.scalar())

            fn_res = await conn.execute(
                sa.text(
                    "SELECT EXISTS (SELECT 1 FROM pg_proc WHERE proname = "
                    "'orcia_prevent_append_only_mutation')"
                )
            )
            has_fn = bool(fn_res.scalar())

            if apply_changes:
                await trans.commit()
                committed = True
            else:
                await trans.rollback()
                committed = False

            return DbInvariantReport(
                has_vector_extension=has_vector,
                has_append_only_trigger_fn=has_fn,
                dry_run=not apply_changes,
                committed=committed,
            )
        except Exception:
            await trans.rollback()
            raise


def build_arg_parser() -> argparse.ArgumentParser:
    """Build CLI argument parser with mandatory dry-run default."""
    parser = argparse.ArgumentParser(
        description="Verify ORCIA PostgreSQL foundation invariants (dry-run by default)."
    )
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Execute checks and roll back transaction (default).",
    )
    mode_group.add_argument(
        "--apply",
        action="store_true",
        default=False,
        help="Commit transaction after verification.",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=100,
        help="Batch size for idempotent processing (default: 100).",
    )
    return parser


async def _async_main(argv: list[str] | None = None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)
    db_url = os.getenv(
        "DATABASE_URL",
        "postgresql+asyncpg://orcia:orcia_dev_secret@localhost:5433/orcia",
    )
    engine = create_async_engine(db_url)
    try:
        report = await verify_database_invariants(
            engine,
            apply_changes=bool(args.apply),
            batch_size=int(args.batch_size),
        )
    finally:
        await engine.dispose()

    if not (report.has_vector_extension and report.has_append_only_trigger_fn):
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    return asyncio.run(_async_main(argv))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
