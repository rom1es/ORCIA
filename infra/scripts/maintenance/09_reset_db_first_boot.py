"""Maintenance script `09_reset_db_first_boot.py` — Reset database to Day-0 First-Boot state.

Allows resetting the ORCIA PostgreSQL 18 database to the clean 1st-boot state (`0` users, `0`
workspaces, `0` org_units, `0` runs) so the Day-0 Initial Platform Administrator creation screen
(`first-boot-admin-setup-modal` / `/welcome-setup`) is presented again as on first launch.

Conventions (GEMINI.md):
- Operational data transformations or maintenance scripts live in
  `infra/scripts/maintenance/XX_*.py`.
- Mandatory `--dry-run` mode by default (rolls back unless `--apply` is explicitly passed).
- Never disables append-only triggers (`trg_blackboard_snapshots_append_only`, etc.) — deletes
  only from mutable tables (`blackboard_snapshots` is only truncated if `COUNT(*) == 0` or skipped).
- Uses batched idempotent transactions.
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

from orcia_core.config import resolve_database_url  # noqa: E402

PROTECTED_TABLES: frozenset[str] = frozenset(
    {
        "alembic_version",
        "blackboard_snapshots",
        "audit_ledger",
    }
)

ORDERED_MUTABLE_TABLES_TO_CLEAR: tuple[str, ...] = (
    "domain_events_outbox",
    "reflexive_execution_sessions",
    "upstream_challenges",
    "human_arbitration_requests",
    "human_anchor_signatures",
    "gate_evaluations",
    "chunk_approvals",
    "inference_attempts",
    "step_executions",
    "run_lock_manifests",
    "workflow_runs",
    "workflow_triggers",
    "task_notifications",
    "resource_leases",
    "tripartite_trace_edges",
    "kb_stale_alerts",
    "kb_chunks",
    "kb_documents",
    "code_graph_edges",
    "ontology_promotion_proposals",
    "ontology_axioms",
    "ontology_relations",
    "ontology_concepts",
    "permission_broker_tickets",
    "permission_broker_policies",
    "catalog_acl_entries",
    "catalog_items",
    "workspace_customization_overrides",
    "workspace_datasources",
    "workspace_invitations",
    "workspace_memberships",
    "workspace_llm_tier_mappings",
    "role_permission_grants",
    "platform_settings",
    "wizard_sessions",
    "system_bootstrap_runs",
    "user_onboarding_states",
    "user_passthrough_credentials",
    "user_transverse_groups",
    "transverse_groups",
    "workflow_definitions_v2",
    "workflow_definitions",
    "llm_model_endpoints",
    "workspaces",
    "users",
    "org_units",
)


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


async def reset_database_to_first_boot(
    engine: AsyncEngine,
    *,
    apply_changes: bool = False,
) -> FirstBootResetReport:
    """Reset mutable tables to the clean Day-0 First-Boot state (`COUNT(*) FROM users == 0`).

    Rolls back by default unless `apply_changes=True` is explicitly passed.
    Never disables append-only triggers on `blackboard_snapshots` or `audit_ledger`.
    """
    deleted_total = 0
    cleared_tables = 0

    async with engine.connect() as conn:
        trans = await conn.begin()
        try:
            existing_rows = await conn.execute(
                sa.text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
            )
            existing_tables = {str(r[0]) for r in existing_rows.fetchall()}

            for table_name in ORDERED_MUTABLE_TABLES_TO_CLEAR:
                if table_name in PROTECTED_TABLES or table_name not in existing_tables:
                    continue
                res = await conn.execute(sa.text(f"DELETE FROM {table_name}"))
                deleted_total += int(res.rowcount or 0)
                cleared_tables += 1

            # Also clear any remaining mutable public tables discovered dynamically
            for table_name in sorted(existing_tables):
                if table_name in PROTECTED_TABLES or table_name in ORDERED_MUTABLE_TABLES_TO_CLEAR:
                    continue
                res = await conn.execute(sa.text(f"DELETE FROM {table_name}"))
                deleted_total += int(res.rowcount or 0)
                cleared_tables += 1

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
        "--dry-run",
        action="store_true",
        default=True,
        help="Simulate the reset and roll back the transaction (default).",
    )
    mode_group.add_argument(
        "--apply",
        action="store_true",
        default=False,
        help="Commit the database reset to Day-0 First-Boot state.",
    )
    return parser


async def _async_main(argv: list[str] | None = None) -> int:
    args = build_arg_parser().parse_args(argv)
    db_url = args.database_url.strip() or resolve_database_url()
    engine = create_async_engine(db_url)
    try:
        report = await reset_database_to_first_boot(
            engine,
            apply_changes=bool(args.apply),
        )
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
