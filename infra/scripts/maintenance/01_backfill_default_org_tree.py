"""Maintenance script `01_backfill_default_org_tree.py` for Story 1.2.

Conventions (AGENTS.md):
- Operational data transformations or backfills outside schema migrations live in
  `infra/scripts/maintenance/XX_*.py`.
- Mandatory `--dry-run` mode (default rollback unless `--apply` is explicitly passed).
- Uses batched idempotent transactions (`INSERT ... ON CONFLICT DO UPDATE`).
"""

from __future__ import annotations

import argparse
import asyncio
import os
from dataclasses import dataclass

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from orcia_core.bootstrap.seeder import (
    DEFAULT_ORG_UNIT_SEEDS,
    DEFAULT_WORKSPACE_DATASOURCE_SEEDS,
    DEFAULT_WORKSPACE_SEEDS,
    ORG_UNITS_UPSERT_SPEC,
    WORKSPACE_DATASOURCES_UPSERT_SPEC,
    WORKSPACES_UPSERT_SPEC,
    build_postgres_upsert_sql,
)


@dataclass(frozen=True, slots=True)
class OrgTreeBackfillReport:
    """Summary of the reference organizational tree and multi-source workspaces backfill."""

    org_units_count: int
    workspaces_count: int
    datasources_count: int
    dry_run: bool
    committed: bool


async def backfill_default_org_tree(
    engine: AsyncEngine,
    *,
    apply_changes: bool = False,
    batch_size: int = 100,
) -> OrgTreeBackfillReport:
    """Populate or update the reference `org_units`, `workspaces`, and `workspace_datasources`.

    Rolls back by default unless `apply_changes=True` is explicitly provided.
    """
    if batch_size <= 0:
        raise ValueError("batch_size must be strictly positive")

    org_sql = sa.text(build_postgres_upsert_sql(ORG_UNITS_UPSERT_SPEC))
    ws_sql = sa.text(build_postgres_upsert_sql(WORKSPACES_UPSERT_SPEC))
    ds_sql = sa.text(build_postgres_upsert_sql(WORKSPACE_DATASOURCES_UPSERT_SPEC))

    async with engine.connect() as conn:
        trans = await conn.begin()
        try:
            for idx in range(0, len(DEFAULT_ORG_UNIT_SEEDS), batch_size):
                batch = DEFAULT_ORG_UNIT_SEEDS[idx : idx + batch_size]
                for item in batch:
                    await conn.execute(
                        org_sql,
                        {
                            "id": item.id,
                            "slug": item.slug,
                            "name": item.name,
                            "unit_type": item.unit_type,
                            "parent_id": item.parent_id,
                        },
                    )

            for idx in range(0, len(DEFAULT_WORKSPACE_SEEDS), batch_size):
                ws_batch = DEFAULT_WORKSPACE_SEEDS[idx : idx + batch_size]
                for ws in ws_batch:
                    await conn.execute(
                        ws_sql,
                        {
                            "id": ws.id,
                            "slug": ws.slug,
                            "name": ws.name,
                            "owner_org_unit_id": ws.owner_org_unit_id,
                            "visibility_mode": ws.visibility_mode,
                            "finops_cost_usd": ws.finops_cost_usd,
                        },
                    )

            for idx in range(0, len(DEFAULT_WORKSPACE_DATASOURCE_SEEDS), batch_size):
                ds_batch = DEFAULT_WORKSPACE_DATASOURCE_SEEDS[idx : idx + batch_size]
                for ds in ds_batch:
                    await conn.execute(
                        ds_sql,
                        {
                            "id": ds.id,
                            "workspace_id": ds.workspace_id,
                            "alias": ds.alias,
                            "scheme": ds.scheme,
                            "uri": ds.uri,
                            "role": ds.role,
                            "execution_identity": ds.execution_identity,
                            "freshness_ttl_days": ds.freshness_ttl_days,
                        },
                    )

            org_count_res = await conn.execute(sa.text("SELECT COUNT(*) FROM org_units"))
            ws_count_res = await conn.execute(sa.text("SELECT COUNT(*) FROM workspaces"))
            ds_count_res = await conn.execute(sa.text("SELECT COUNT(*) FROM workspace_datasources"))
            org_count = int(org_count_res.scalar() or 0)
            ws_count = int(ws_count_res.scalar() or 0)
            ds_count = int(ds_count_res.scalar() or 0)

            if apply_changes:
                await trans.commit()
                committed = True
            else:
                await trans.rollback()
                committed = False

            return OrgTreeBackfillReport(
                org_units_count=org_count,
                workspaces_count=ws_count,
                datasources_count=ds_count,
                dry_run=not apply_changes,
                committed=committed,
            )
        except Exception:
            await trans.rollback()
            raise


def build_arg_parser() -> argparse.ArgumentParser:
    """Build CLI argument parser with mandatory dry-run default."""
    parser = argparse.ArgumentParser(
        description="Backfill reference ORCIA org_units and workspaces (dry-run default)."
    )
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Execute upserts and roll back transaction (default).",
    )
    mode_group.add_argument(
        "--apply",
        action="store_true",
        default=False,
        help="Commit transaction after upserts.",
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
        report = await backfill_default_org_tree(
            engine,
            apply_changes=bool(args.apply),
            batch_size=int(args.batch_size),
        )
    finally:
        await engine.dispose()

    if report.org_units_count < len(DEFAULT_ORG_UNIT_SEEDS):
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    return asyncio.run(_async_main(argv))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
