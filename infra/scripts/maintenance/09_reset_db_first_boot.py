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
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine, create_async_engine

_CORE_SRC = str(Path(__file__).resolve().parents[3] / "packages" / "orcia-core" / "src")
_KERNEL_SRC = str(Path(__file__).resolve().parents[3] / "packages" / "orcia-kernel" / "src")
for _src_path in (_KERNEL_SRC, _CORE_SRC):
    if _src_path not in sys.path:
        sys.path.insert(0, _src_path)

from orcia_core.config import resolve_database_url  # noqa: E402
from orcia_kernel.ids import new_uuid7_str  # noqa: E402

PROTECTED_TABLES: frozenset[str] = frozenset(
    {
        "alembic_version",
        "blackboard_snapshots",
        "audit_ledger",
        "connector_schemes",
    }
)

BASE_CONNECTOR_SCHEMES: tuple[tuple[str, str, str, str], ...] = (
    ("0192c4e0-0000-7000-8000-00000000c001", "orcia", "ORCIA Native URI", "orcia-core"),
    ("0192c4e0-0000-7000-8000-00000000c002", "db", "Relational Database Connector", "orcia-core"),
    ("0192c4e0-0000-7000-8000-00000000c003", "mcp",
     "Model Context Protocol Connector", "orcia-core"),
    ("0192c4e0-0000-7000-8000-00000000c004", "git", "Git Repository Connector", "orcia-pack-sdlc"),
    ("0192c4e0-0000-7000-8000-00000000c005", "jira",
     "Jira Issue Tracker Connector", "orcia-pack-sdlc"),
    ("0192c4e0-0000-7000-8000-00000000c006", "confluence",
     "Confluence Wiki Connector", "orcia-pack-sdlc"),
    ("0192c4e0-0000-7000-8000-00000000c007", "nexus",
     "Nexus Artifact Repository Connector", "orcia-pack-sdlc"),
)  # fmt: skip

ORDERED_MUTABLE_TABLES_TO_CLEAR: tuple[str, ...] = (
    "finops_connector_quotas", "finops_budget_overrides", "finops_workflow_baselines",
    "finops_scope_budgets", "domain_events_outbox", "reflexive_execution_sessions",
    "upstream_challenges", "human_arbitration_requests", "human_anchor_signatures",
    "gate_evaluations", "chunk_approvals", "inference_attempts", "step_executions",
    "run_lock_manifests", "autonomous_post_hoc_audits", "workflow_runs",
    "trigger_webhook_deliveries", "workflow_triggers", "task_notifications",
    "resource_leases", "tripartite_trace_edges", "kb_stale_alerts", "kb_chunks",
    "kb_documents", "code_graph_edges", "ontology_rejected_candidates",
    "ontology_promotion_proposals", "ontology_axioms", "ontology_relations",
    "ontology_concepts", "permission_broker_tickets", "permission_broker_policies",
    "catalog_acl_entries", "catalog_items", "workspace_customization_overrides",
    "workspace_datasources", "workspace_invitations", "workspace_memberships",
    "workspace_llm_tier_mappings", "role_permission_grants", "auth_login_challenges",
    "autonomy_contracts", "iam_accounts", "platform_auth_settings", "platform_settings",
    "user_connector_passthrough_tokens", "enterprise_connectors", "wizard_sessions",
    "system_bootstrap_runs", "user_onboarding_states", "user_mcp_tokens",
    "user_preferences", "user_passthrough_credentials", "user_transverse_groups",
    "transverse_groups", "workflow_definitions_v2", "workflow_definitions",
    "llm_model_endpoints", "workspaces", "users", "org_units",
)  # fmt: skip


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


_APPEND_ONLY_GUARDED_TABLES: frozenset[str] = frozenset({"step_executions", "workflow_runs"})


async def _assert_no_append_only_restrict_refs(
    conn: AsyncConnection,
    table_name: str,
    existing_tables: set[str],
) -> None:
    """Fail explicitly if append-only tables hold ON DELETE RESTRICT refs to `table_name`."""
    if table_name not in _APPEND_ONLY_GUARDED_TABLES:
        return
    has_target_rows = bool(
        (await conn.execute(sa.text(f"SELECT EXISTS (SELECT 1 FROM {table_name})"))).scalar()
    )
    if not has_target_rows:
        return

    fk_rows = await conn.execute(
        sa.text(
            """
            SELECT conrelid::regclass::text AS ref_table
            FROM pg_constraint
            WHERE contype = 'f'
              AND confdeltype = 'r'
              AND confrelid = to_regclass(:target_table)
            """
        ),
        {"target_table": f"public.{table_name}"},
    )
    restrict_refs = {str(r[0]).split(".")[-1].strip('"') for r in fk_rows.fetchall()}
    if "blackboard_snapshots" in existing_tables:
        restrict_refs.add("blackboard_snapshots")

    append_only_protected = PROTECTED_TABLES - {"alembic_version", "connector_schemes"}
    for ref_table in sorted(restrict_refs & append_only_protected):
        if ref_table not in existing_tables:
            continue
        has_ref_rows = bool(
            (await conn.execute(sa.text(f"SELECT EXISTS (SELECT 1 FROM {ref_table})"))).scalar()
        )
        if has_ref_rows:
            raise RuntimeError(
                f"Impossible de supprimer '{table_name}' : des lignes append-only dans "
                f"'{ref_table}' référencent cette table via ON DELETE RESTRICT. "
                "`09_reset_db_first_boot.py` préserve strictement les tables append-only "
                "sans `DISABLE TRIGGER` ni `TRUNCATE`. Pour réinitialiser une base E2E "
                "isolée `orcia_e2e`, utilisez `infra/scripts/e2e/reset_day0.py`."
            )


async def reset_platform_auth_settings_and_system_seed(
    conn: AsyncConnection,
    *,
    existing_tables: set[str] | None = None,
) -> None:
    """Reset `platform_auth_settings` to Day-0 LOCAL defaults and ensure base connector schemes."""
    if existing_tables is None:
        existing_rows = await conn.execute(
            sa.text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
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
                await _assert_no_append_only_restrict_refs(conn, table_name, existing_tables)
                res = await conn.execute(sa.text(f"DELETE FROM {table_name}"))
                deleted_total += int(res.rowcount or 0)
                cleared_tables += 1

            # Also clear any remaining mutable public tables discovered dynamically
            for table_name in sorted(existing_tables):
                if table_name in PROTECTED_TABLES or table_name in ORDERED_MUTABLE_TABLES_TO_CLEAR:
                    continue
                await _assert_no_append_only_restrict_refs(conn, table_name, existing_tables)
                res = await conn.execute(sa.text(f"DELETE FROM {table_name}"))
                deleted_total += int(res.rowcount or 0)
                cleared_tables += 1

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
