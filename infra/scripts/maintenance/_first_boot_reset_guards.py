"""Shared table catalogs and dynamic PostgreSQL introspection guards for Day-0 resets."""

from __future__ import annotations

import re

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection

PROTECTED_TABLES: frozenset[str] = frozenset(
    {
        "alembic_version",
        "blackboard_snapshots",
        "audit_ledger",
        "connector_schemes",
        "declarative_pack_bundles",
    }
)
DBOS_EXCLUDED_TABLES: frozenset[str] = frozenset(
    {"dbos_migrations", "dbos_datasource_migrations", "alembic_version"}
)
APPEND_ONLY_TABLES: frozenset[str] = frozenset({"blackboard_snapshots", "audit_ledger"})
APPEND_ONLY_GUARDED_TABLES: frozenset[str] = frozenset({"step_executions", "workflow_runs"})
_SAFE_IDENT_RE = re.compile(r"^[a-zA-Z_][a-zA-Z0-9_]*$")

BASE_CONNECTOR_SCHEMES: tuple[tuple[str, str, str, str], ...] = (
    ("0192c4e0-0000-7000-8000-00000000c001", "orcia", "ORCIA Native URI", "orcia-core"),
    ("0192c4e0-0000-7000-8000-00000000c002", "db", "Relational Database Connector", "orcia-core"),
    (
        "0192c4e0-0000-7000-8000-00000000c003",
        "mcp",
        "Model Context Protocol Connector",
        "orcia-core",
    ),
    ("0192c4e0-0000-7000-8000-00000000c004", "git", "Git Repository Connector", "orcia-pack-sdlc"),
    (
        "0192c4e0-0000-7000-8000-00000000c005",
        "jira",
        "Jira Issue Tracker Connector",
        "orcia-pack-sdlc",
    ),
    (
        "0192c4e0-0000-7000-8000-00000000c006",
        "confluence",
        "Confluence Wiki Connector",
        "orcia-pack-sdlc",
    ),
    (
        "0192c4e0-0000-7000-8000-00000000c007",
        "nexus",
        "Nexus Artifact Repository Connector",
        "orcia-pack-sdlc",
    ),
)

ORDERED_MUTABLE_TABLES_TO_CLEAR: tuple[str, ...] = (
    "mcp_exposed_agents", "mcp_governed_pat_tokens",
    "jira_staged_actions", "mcp_governed_proposals", "workspace_dna_mechanisms",
    "assistant_turn_feedback", "assistant_folder_shares", "assistant_threads", "assistant_folders",
    "workspace_exception_waivers", "vsm_definitions_v2", "claim_check_artifacts",
    "datasource_webhook_deliveries", "rag_reindexing_pending_ingestions", "rag_reindexing_jobs",
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


def quote_sql_ident(schema: str, table: str) -> str:
    """Safely quote a validated `schema.table` SQL identifier."""
    if not _SAFE_IDENT_RE.match(schema) or not _SAFE_IDENT_RE.match(table):
        raise ValueError(f"Identifiant SQL invalide : {schema!r}.{table!r}")
    return f'"{schema}"."{table}"'


async def assert_no_append_only_restrict_refs(
    conn: AsyncConnection,
    table_name: str,
    existing_tables: set[str],
    *,
    extra_guarded_tables: set[str] | frozenset[str] = frozenset(),
) -> None:
    """Fail explicitly if append-only tables hold ON DELETE RESTRICT refs to `table_name`."""
    if table_name not in APPEND_ONLY_GUARDED_TABLES and table_name not in extra_guarded_tables:
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
            WHERE contype = 'f' AND confdeltype = 'r' AND confrelid = to_regclass(:target_table)
            """
        ),
        {"target_table": f"public.{table_name}"},
    )
    restrict_refs = {str(r[0]).split(".")[-1].strip('"') for r in fk_rows.fetchall()}
    if "blackboard_snapshots" in existing_tables:
        restrict_refs.add("blackboard_snapshots")

    for ref_table in sorted(restrict_refs & APPEND_ONLY_TABLES):
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


async def inspect_append_only_guards(conn: AsyncConnection, existing_tables: set[str]) -> set[str]:
    """Verify append-only triggers stay `'O'` and discover `ON DELETE RESTRICT` targets."""
    targets = sorted(APPEND_ONLY_TABLES & existing_tables)
    if not targets:
        return set()
    trig_rows = await conn.execute(
        sa.text(
            """
            SELECT c.relname, t.tgname, t.tgenabled::text
            FROM pg_trigger t
            JOIN pg_class c ON c.oid = t.tgrelid
            JOIN pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public' AND NOT t.tgisinternal AND c.relname = ANY(:tables)
            """
        ),
        {"tables": targets},
    )
    for relname, tgname, tgenabled in trig_rows.fetchall():
        if str(tgenabled) != "O":
            raise RuntimeError(
                f"Trigger append-only désactivé sur {relname}.{tgname} (tgenabled={tgenabled!r})."
            )
    fk_rows = await conn.execute(
        sa.text(
            """
            SELECT c.confrelid::regclass::text AS parent_table
            FROM pg_constraint c
            JOIN pg_class cl ON cl.oid = c.conrelid
            JOIN pg_namespace n ON n.oid = cl.relnamespace
            WHERE c.contype = 'f' AND c.confdeltype = 'r'
              AND n.nspname = 'public' AND cl.relname = ANY(:tables)
            """
        ),
        {"tables": targets},
    )
    return {str(r[0]).split(".")[-1].strip('"') for r in fk_rows.fetchall() if r[0]}
