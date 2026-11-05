"""Maintenance script `04_backfill_system_bootstrap.py` for Story 1.5.

Conventions (AGENTS.md):
- Operational data transformations or backfills outside schema migrations live in
  `infra/scripts/maintenance/XX_*.py`.
- Mandatory `--dry-run` mode (default rollback unless `--apply` is explicitly passed).
- Uses batched idempotent transactions (`INSERT ... ON CONFLICT DO UPDATE`).
"""

from __future__ import annotations

import argparse
import asyncio
import sys
from dataclasses import dataclass
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

_CORE_SRC = str(Path(__file__).resolve().parents[3] / "packages" / "orcia-core" / "src")
if _CORE_SRC not in sys.path:
    sys.path.insert(0, _CORE_SRC)

from orcia_core.bootstrap.seeder import (  # noqa: E402
    DEFAULT_LLM_MODEL_ENDPOINT_SEEDS,
    DEFAULT_SYSTEM_BOOTSTRAP_WORKFLOW_SEEDS,
    LLM_MODEL_ENDPOINTS_UPSERT_SPEC,
    WORKFLOW_DEFINITIONS_UPSERT_SPEC,
    build_postgres_upsert_sql,
)


@dataclass(frozen=True, slots=True)
class SystemBootstrapBackfillReport:
    """Summary of the reference System Bootstrap workflows & LLM endpoints backfill."""

    llm_endpoints_count: int
    bootstrap_workflows_count: int
    bootstrap_runs_count: int
    onboarding_states_count: int
    dry_run: bool
    committed: bool


async def backfill_system_bootstrap(
    engine: AsyncEngine,
    *,
    apply_changes: bool = False,
    batch_size: int = 100,
) -> SystemBootstrapBackfillReport:
    """Populate or update `llm_model_endpoints` and `workflow_definitions` (`orcia://system/bootstrap/*`).

    Never inserts fictional users, fictional org units, fictional workspaces, or fictional runs.
    Rolls back by default unless `apply_changes=True` is explicitly provided.
    """
    if batch_size <= 0:
        raise ValueError("batch_size must be strictly positive")

    llm_sql = sa.text(build_postgres_upsert_sql(LLM_MODEL_ENDPOINTS_UPSERT_SPEC))
    wf_sql = sa.text(build_postgres_upsert_sql(WORKFLOW_DEFINITIONS_UPSERT_SPEC))

    async with engine.connect() as conn:
        trans = await conn.begin()
        try:
            for idx in range(0, len(DEFAULT_LLM_MODEL_ENDPOINT_SEEDS), batch_size):
                for ep in DEFAULT_LLM_MODEL_ENDPOINT_SEEDS[idx : idx + batch_size]:
                    await conn.execute(
                        llm_sql,
                        {
                            "id": ep.id,
                            "endpoint_key": ep.endpoint_key,
                            "provider_slug": ep.provider_slug,
                            "model_family": ep.model_family,
                            "model_name": ep.model_name,
                            "endpoint_uri": ep.endpoint_uri,
                            "connectivity_verified": ep.connectivity_verified,
                            "is_active": ep.is_active,
                        },
                    )

            for idx in range(0, len(DEFAULT_SYSTEM_BOOTSTRAP_WORKFLOW_SEEDS), batch_size):
                for wf in DEFAULT_SYSTEM_BOOTSTRAP_WORKFLOW_SEEDS[idx : idx + batch_size]:
                    await conn.execute(
                        wf_sql,
                        {
                            "id": wf.id,
                            "workspace_id": None,
                            "uri": wf.uri,
                            "version": "v1.0.0",
                            "source_format": "ORCIA",
                            "steps_schema_jsonb": wf.steps_schema_json,
                            "adaptive_gate_policy": "STRICT",
                            "sha256": wf.sha256,
                        },
                    )

            llm_res = await conn.execute(sa.text("SELECT COUNT(*) FROM llm_model_endpoints"))
            wf_res = await conn.execute(
                sa.text(
                    "SELECT COUNT(*) FROM workflow_definitions "
                    "WHERE uri LIKE 'orcia://system/bootstrap/%'"
                )
            )
            run_res = await conn.execute(sa.text("SELECT COUNT(*) FROM system_bootstrap_runs"))
            onb_res = await conn.execute(sa.text("SELECT COUNT(*) FROM user_onboarding_states"))
            llm_count = int(llm_res.scalar() or 0)
            wf_count = int(wf_res.scalar() or 0)
            runs_count = int(run_res.scalar() or 0)
            onb_count = int(onb_res.scalar() or 0)

            if apply_changes:
                await trans.commit()
                committed = True
            else:
                await trans.rollback()
                committed = False

            return SystemBootstrapBackfillReport(
                llm_endpoints_count=llm_count,
                bootstrap_workflows_count=wf_count,
                bootstrap_runs_count=runs_count,
                onboarding_states_count=onb_count,
                dry_run=not apply_changes,
                committed=committed,
            )
        except Exception:
            await trans.rollback()
            raise


def build_arg_parser() -> argparse.ArgumentParser:
    """Build CLI argument parser with mandatory dry-run default."""
    parser = argparse.ArgumentParser(
        description="Backfill reference ORCIA Day-0 System Bootstrap workflows and LLM families."
    )
    mode_group = parser.add_mutually_exclusive_group()
    mode_group.add_argument(
        "--dry-run", action="store_true", default=True, help="Roll back transaction (default)."
    )
    mode_group.add_argument(
        "--apply", action="store_true", default=False, help="Commit transaction after upserts."
    )
    parser.add_argument("--batch-size", type=int, default=100, help="Batch size (default: 100).")
    return parser


async def _async_main(argv: list[str] | None = None) -> int:
    from orcia_core.config import resolve_database_url

    args = build_arg_parser().parse_args(argv)
    db_url = resolve_database_url()
    engine = create_async_engine(db_url)
    try:
        report = await backfill_system_bootstrap(
            engine, apply_changes=bool(args.apply), batch_size=int(args.batch_size)
        )
    finally:
        await engine.dispose()
    return 0 if report.bootstrap_workflows_count >= 6 and report.llm_endpoints_count >= 2 else 1


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    return asyncio.run(_async_main(argv))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
