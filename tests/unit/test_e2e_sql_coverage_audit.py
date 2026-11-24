"""Static AST/SQL audit ensuring 100% of E2E `test(...)` blocks assert domain PG18 tables."""

from __future__ import annotations

import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
E2E_DIR = REPO_ROOT / "apps" / "web" / "e2e"

TEST_BLOCK_START_RE = re.compile(r"(?<!\.)\btest\s*\(")
SQL_CALL_RE = re.compile(
    r"\b(?:expectDbRowExists|expectDbRowCount|queryDbRows)(?:<[^>]+>)?\s*\(\s*([`\"'])(.*?)\1",
    re.DOTALL,
)
FROM_TABLE_RE = re.compile(r"\bFROM\s+(?:public\.)?\"?([a-zA-Z_][a-zA-Z0-9_]*)\"?", re.IGNORECASE)
TRIVIAL_SELECT_RE = re.compile(r"^\s*SELECT\s+1\b(?!.*\bFROM\b)", re.IGNORECASE | re.DOTALL)
TAUTOLOGICAL_COUNT_RE = re.compile(
    r"SELECT\s+COUNT\s*\(.*?\.toBeGreaterThanOrEqual\s*\(\s*0\s*\)",
    re.IGNORECASE | re.DOTALL,
)

SPEC_ALLOWED_DOMAIN_TABLES: dict[str, frozenset[str]] = {
    "00-stack-smoke.spec.ts": frozenset(
        {
            "users",
            "platform_auth_settings",
            "declarative_pack_bundles",
            "reflexive_execution_sessions",
        }
    ),
    "01-day0-boot-and-f5-persistence.spec.ts": frozenset(
        {"users", "platform_auth_settings", "declarative_pack_bundles"}
    ),
    "02-assistant-streaming-and-folders.spec.ts": frozenset(
        {"audit_ledger", "assistant_folders", "assistant_threads", "workspace_llm_tier_mappings"}
    ),
    "03-human-led-anchor-and-arbitration.spec.ts": frozenset(
        {"human_anchor_signatures", "human_arbitration_requests", "workflow_runs"}
    ),
    "04-multi-actor-claim-sse.spec.ts": frozenset({"task_notifications", "resource_leases"}),
    "05-mobile-companion-and-rgaa.spec.ts": frozenset(
        {
            "users",
            "platform_auth_settings",
            "platform_settings",
            "role_permission_grants",
            "declarative_pack_bundles",
        }
    ),
    "06-gates-review-and-anti-rubber-stamping.spec.ts": frozenset(
        {"gate_evaluations", "chunk_approvals"}
    ),
    "07-spaces-org-and-workspace-persistence.spec.ts": frozenset({"org_units", "workspaces"}),
    "08-agents-skills-persistence.spec.ts": frozenset({"catalog_items"}),
    "09-pack-builder-and-contextual-help.spec.ts": frozenset(
        {"workflow_definitions_v2", "catalog_items", "declarative_pack_bundles"}
    ),
    "10-command-palette-search.spec.ts": frozenset(
        {"catalog_items", "workspace_llm_tier_mappings", "kb_chunks"}
    ),
    "11-screens-smoke-without-server-errors.spec.ts": frozenset(
        {"users", "declarative_pack_bundles", "platform_auth_settings"}
    ),
    "12-epic16-reflexive-trace-and-line-inspector.spec.ts": frozenset(
        {"reflexive_execution_sessions"}
    ),
    "12-finops-and-audit-provenance.spec.ts": frozenset(
        {"finops_scope_budgets", "audit_ledger", "finops_workflow_baselines"}
    ),
    "13-epic-7-autonomous-governance-and-supervision.spec.ts": frozenset(
        {
            "autonomy_contracts",
            "workflow_triggers",
            "workflow_runs",
            "autonomous_post_hoc_audits",
            "audit_ledger",
            "workflow_definitions_v2",
            "finops_scope_budgets",
        }
    ),
    "14-auth-2fa-account-and-profile.spec.ts": frozenset(
        {"platform_auth_settings", "users", "user_preferences", "user_mcp_tokens", "audit_ledger"}
    ),
    "15-organization-iam-secops-inbox-and-observer.spec.ts": frozenset(
        {
            "org_units",
            "iam_accounts",
            "audit_ledger",
            "role_permission_grants",
            "task_notifications",
        }
    ),
    "16-ai-models-reindex-connectors-and-broker.spec.ts": frozenset(
        {
            "workspace_llm_tier_mappings",
            "rag_reindexing_jobs",
            "enterprise_connectors",
            "user_connector_passthrough_tokens",
            "permission_broker_tickets",
            "connector_schemes",
        }
    ),
    "17-workspace-sources-codegraph-dna-and-ontology.spec.ts": frozenset(
        {
            "workspace_datasources",
            "datasource_webhook_deliveries",
            "ontology_concepts",
            "ontology_promotion_proposals",
            "audit_ledger",
            "workspace_exception_waivers",
            "kb_documents",
            "tripartite_trace_edges",
        }
    ),
    "18-catalog-packs-wizards-and-mcp-bench.spec.ts": frozenset(
        {
            "catalog_items",
            "catalog_acl_entries",
            "workflow_definitions",
            "platform_settings",
            "declarative_pack_bundles",
            "wizard_sessions",
            "audit_ledger",
        }
    ),
    "19-orchestration-whatif-replay-and-gates.spec.ts": frozenset(
        {
            "workflow_runs",
            "step_executions",
            "blackboard_snapshots",
            "run_lock_manifests",
            "upstream_challenges",
            "human_anchor_signatures",
            "gate_evaluations",
            "chunk_approvals",
        }
    ),
    "20-process-studio-v2-finops-and-log-sink.spec.ts": frozenset(
        {
            "workflow_definitions_v2",
            "vsm_definitions_v2",
            "reflexive_execution_sessions",
            "autonomy_contracts",
            "workflow_triggers",
            "trigger_webhook_deliveries",
            "finops_scope_budgets",
            "finops_connector_quotas",
            "audit_ledger",
        }
    ),
    "21-assistant-citations-v5-audit-help-showcase.spec.ts": frozenset(
        {
            "assistant_folders",
            "assistant_threads",
            "reflexive_execution_sessions",
            "audit_ledger",
            "catalog_items",
        }
    ),
    "22-assistant-tool-loop-approval-and-reattach.spec.ts": frozenset(
        {"assistant_threads", "assistant_thread_messages"}
    ),
    "23-bilingual-fr-en-i18n-and-rfc9457.spec.ts": frozenset({"user_preferences", "users"}),
    "shell.spec.ts": frozenset({"users", "platform_auth_settings"}),
}


def _extract_block_sql_queries(body: str) -> list[str]:
    return [match.group(2) for match in SQL_CALL_RE.finditer(body)]


def _audit_spec_content(
    spec_name: str,
    content: str,
    allowed_tables: frozenset[str],
) -> tuple[int, list[str], list[str], list[str]]:
    total_blocks = 0
    blocks_missing_sql: list[str] = []
    trivial_sql_blocks: list[str] = []
    out_of_domain_blocks: list[str] = []

    starts = [match.start() for match in TEST_BLOCK_START_RE.finditer(content)]
    for idx, start in enumerate(starts):
        total_blocks += 1
        end = starts[idx + 1] if idx + 1 < len(starts) else len(content)
        body = content[start:end]
        line_no = content[:start].count("\n") + 1
        loc = f"{spec_name}:{line_no}"

        sql_queries = _extract_block_sql_queries(body)
        if not sql_queries:
            blocks_missing_sql.append(loc)
            continue

        block_tables: set[str] = set()
        for sql in sql_queries:
            if TRIVIAL_SELECT_RE.match(sql):
                trivial_sql_blocks.append(f"{loc} -> {sql.strip()}")
            for tbl in FROM_TABLE_RE.findall(sql):
                block_tables.add(tbl.lower())
        if TAUTOLOGICAL_COUNT_RE.search(body):
            trivial_sql_blocks.append(f"{loc} -> tautological COUNT(*) toBeGreaterThanOrEqual(0)")

        if not (block_tables & allowed_tables):
            out_of_domain_blocks.append(
                f"{loc} tables={sorted(block_tables)} not in {sorted(allowed_tables)}"
            )

    return total_blocks, blocks_missing_sql, trivial_sql_blocks, out_of_domain_blocks


def test_all_e2e_specs_invoke_domain_postgresql_18_assertions_in_every_test_block() -> None:
    specs = sorted(E2E_DIR.glob("*.spec.ts"))
    assert len(specs) == 26
    assert set(SPEC_ALLOWED_DOMAIN_TABLES.keys()) == {p.name for p in specs}

    total_blocks = 0
    blocks_missing_sql: list[str] = []
    trivial_sql_blocks: list[str] = []
    out_of_domain_blocks: list[str] = []
    cold_reload_consumers = 0

    for spec_path in specs:
        content = spec_path.read_text(encoding="utf-8")
        if "reloadColdFromPg" in content:
            cold_reload_consumers += 1
        allowed_tables = SPEC_ALLOWED_DOMAIN_TABLES[spec_path.name]
        b_cnt, missing, trivial, out_domain = _audit_spec_content(
            spec_path.name, content, allowed_tables
        )
        total_blocks += b_cnt
        blocks_missing_sql.extend(missing)
        trivial_sql_blocks.extend(trivial)
        out_of_domain_blocks.extend(out_domain)

    assert total_blocks == 59
    assert blocks_missing_sql == []
    assert trivial_sql_blocks == []
    assert out_of_domain_blocks == []
    assert cold_reload_consumers >= 1


def test_e2e_sql_audit_rejects_trivial_select_1_out_of_domain_and_missing_sql() -> None:
    finops_allowed = SPEC_ALLOWED_DOMAIN_TABLES["12-finops-and-audit-provenance.spec.ts"]

    trivial_spec = """
    test("alibi trivial sql", async () => {
      await expectDbRowCount("SELECT 1", 1);
    });
    """
    cnt, missing, trivial, out_domain = _audit_spec_content(
        "12-finops-and-audit-provenance.spec.ts", trivial_spec, finops_allowed
    )
    assert cnt == 1
    assert missing == []
    assert len(trivial) == 1
    assert "SELECT 1" in trivial[0]
    assert len(out_domain) == 1

    alibi_spec = """
    test("alibi wrong table on finops spec", async () => {
      await expectDbRowExists("SELECT id FROM users WHERE email = $1", ["a@orcia.ia"]);
    });
    """
    cnt2, missing2, trivial2, out_domain2 = _audit_spec_content(
        "12-finops-and-audit-provenance.spec.ts", alibi_spec, finops_allowed
    )
    assert cnt2 == 1 and missing2 == [] and trivial2 == []
    assert len(out_domain2) == 1 and "users" in out_domain2[0]

    no_sql_spec = """
    test("missing sql altogether", async () => {
      await expect(page.getByTestId("finops")).toBeVisible();
    });
    """
    cnt3, missing3, trivial3, out_domain3 = _audit_spec_content(
        "12-finops-and-audit-provenance.spec.ts", no_sql_spec, finops_allowed
    )
    assert cnt3 == 1 and len(missing3) == 1 and trivial3 == [] and out_domain3 == []

    tautological_count_spec = """
    test("tautological >= 0 on COUNT(*)", async () => {
      const rows = queryDbRows<{ count: number }>(
        "SELECT COUNT(*)::int AS count FROM finops_scope_budgets",
      );
      expect(rows[0]?.count ?? -1).toBeGreaterThanOrEqual(0);
    });
    """
    cnt4, missing4, trivial4, out_domain4 = _audit_spec_content(
        "12-finops-and-audit-provenance.spec.ts", tautological_count_spec, finops_allowed
    )
    assert cnt4 == 1 and missing4 == [] and out_domain4 == []
    assert len(trivial4) == 1 and "toBeGreaterThanOrEqual(0)" in trivial4[0]
