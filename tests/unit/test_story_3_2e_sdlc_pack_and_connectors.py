"""Layer 1 Unit & Layer 3 Integration Tests for Story 3.2e (`AD-20`, `DEC-SEED-01`)."""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from alembic.config import Config
from fastapi.testclient import TestClient

from orcia_api.main import create_app
from orcia_core.orchestration.errors import (
    IntentionBeforeCodeRequiredError,
    UnknownWorkflowPolicyError,
)
from orcia_core.orchestration.yaml_validator import WorkflowAsCodeValidator
from orcia_kernel.enums import (
    is_valid_memlog_marker,
    list_registered_memlog_markers,
    normalize_memlog_marker,
    register_memlog_marker,
)
from orcia_kernel.ports import list_registered_connector_schemes
from orcia_pack_sdlc import (
    SDLC_BUG_CODE_MARKER,
    SDLC_DOC_OBSOLETE_MARKER,
    activate_sdlc_pack,
    get_bmad_pack_format_adapter,
    get_git_code_ast_indexer,
    get_jira_hybrid_indexer,
    get_tripartite_graph_indexer,
)

REPO_ROOT = Path(__file__).resolve().parents[2]


def test_ac_e2_zero_sdlc_vocabulary_in_kernel_and_orchestration() -> None:
    """Verify grep for SDLC vocabulary in `orcia_core.kernel` & `orcia-core/orchestration` is 0."""
    proc = subprocess.run(
        [
            "grep",
            "-rnIiE",
            "--exclude-dir=__pycache__",
            "writes_code|BUG_CODE|DOC_OBSOLETE|brownfield|confluence|git://|jira",
            "packages/orcia-core/src/orcia_core/kernel",
            "packages/orcia-core/src/orcia_core/orchestration",
        ],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    assert proc.stdout.strip() == "", f"Unexpected SDLC vocabulary found:\n{proc.stdout}"


def test_ac_e1_and_e2_sdlc_pack_entry_points_and_unknown_workflow_policy_error() -> None:
    """Verify `orcia_pack_sdlc` entry_points, `tags`/`policies` & `ERR_UNKNOWN_WORKFLOW_POLICY`."""
    activate_sdlc_pack()
    assert {"orcia", "db", "mcp", "git", "jira", "confluence", "nexus"}.issubset(
        list_registered_connector_schemes()
    )
    assert get_bmad_pack_format_adapter() is not None
    assert callable(get_git_code_ast_indexer())
    assert callable(get_jira_hybrid_indexer())
    assert get_tripartite_graph_indexer() is not None

    # Namespaced marker registry + legacy aliases
    assert is_valid_memlog_marker(SDLC_BUG_CODE_MARKER) is True
    assert is_valid_memlog_marker(SDLC_DOC_OBSOLETE_MARKER) is True
    assert normalize_memlog_marker("BUG_CODE_SUSPECTED") == SDLC_BUG_CODE_MARKER
    assert normalize_memlog_marker("DOC_OBSOLETE_SUSPECTED") == SDLC_DOC_OBSOLETE_MARKER
    register_memlog_marker("erp.invoice_mismatch_suspected")
    assert "erp.invoice_mismatch_suspected" in list_registered_memlog_markers()

    # Unknown workflow policy raises UnknownWorkflowPolicyError (ERR_UNKNOWN_WORKFLOW_POLICY)
    unknown_policy_yaml = """uri: "orcia://workflows/test-unknown-policy"
title: "Workflow Politique Inconnue"
version: "1.0.0"
criticality: "STANDARD"
execution_regime: "INTERACTIVE_COACHING"
tie_break_policy: "PAUSE_AND_ESCALATE"
mode: "standard"
steps:
  - step_key: "step-1"
    title: "Étape 1"
    step_type: "AGENT"
    instructions: "Test"
    policies:
      - "unregistered.policy_rule"
"""
    with pytest.raises(UnknownWorkflowPolicyError) as pol_exc:
        WorkflowAsCodeValidator.validate_manifest(unknown_policy_yaml, raise_on_error=True)
    assert pol_exc.value.error_code == "ERR_UNKNOWN_WORKFLOW_POLICY"

    # Namespaced tags (`sdlc.writes_code` without `sdlc.declares_intention`) trigger FR-13
    namespaced_fr13_yaml = """uri: "orcia://workflows/test-namespaced-fr13"
title: "Workflow FR-13 Namespaced"
version: "1.0.0"
criticality: "STANDARD"
execution_regime: "INTERACTIVE_COACHING"
tie_break_policy: "PAUSE_AND_ESCALATE"
mode: "standard"
steps:
  - step_key: "code-step"
    title: "Étape Code"
    step_type: "AGENT"
    instructions: "Modifier code"
    tags:
      - "sdlc.writes_code"
    policies:
      - "sdlc.fr13_intention_before_code"
"""
    with pytest.raises(IntentionBeforeCodeRequiredError):
        WorkflowAsCodeValidator.validate_manifest(namespaced_fr13_yaml, raise_on_error=True)

    # API endpoint returns RFC 9457 Problem Details for ERR_UNKNOWN_WORKFLOW_POLICY
    client = TestClient(create_app())
    res = client.post(
        "/api/v1/orchestration/workflows/validate?persona_key=marc",
        json={"raw_manifest": unknown_policy_yaml},
    )
    assert res.status_code == 422
    assert res.json()["error_code"] == "ERR_UNKNOWN_WORKFLOW_POLICY"


def test_ac_e5_alembic_0013_and_0014_expand_contract_with_existing_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify `0013` (Expand) and `0014` (Contract) upgrade & downgrade on PostgreSQL 18."""
    import os
    import shutil
    import time

    from testcontainers.core.container import DockerContainer
    from testcontainers.core.waiting_utils import wait_for_logs

    monkeypatch.setenv("TESTCONTAINERS_RYUK_DISABLED", "true")
    suffix = f"tc_3_2e_{os.getpid()}_{int(time.time() * 1000) % 100000}"
    sock_dir = REPO_ROOT / ".pytest_cache" / suffix
    sock_dir.mkdir(parents=True, exist_ok=True)
    sock_dir.chmod(0o777)

    pg_container = (
        DockerContainer("pgvector/pgvector:pg18")
        .with_env("POSTGRES_USER", "orcia")
        .with_env("POSTGRES_PASSWORD", "orcia_dev_secret")
        .with_env("POSTGRES_DB", "orcia")
        .with_volume_mapping(str(sock_dir), "/var/run/postgresql", "rw")
    )
    try:
        with pg_container as pg:
            wait_for_logs(pg, "database system is ready to accept connections", timeout=30)
            sock_file = sock_dir / ".s.PGSQL.5432"
            for _ in range(40):
                if sock_file.exists():
                    break
                time.sleep(0.2)

            creds = "orcia:orcia_dev_secret"  # pragma: allowlist secret
            sync_url = f"postgresql+psycopg://{creds}@/orcia?host={sock_dir}"
            monkeypatch.setenv("DATABASE_URL", sync_url)
            alembic_cfg = Config(str(REPO_ROOT / "infra" / "migrations" / "alembic.ini"))
            alembic_cfg.set_main_option("script_location", str(REPO_ROOT / "infra" / "migrations"))
            alembic_cfg.set_main_option("sqlalchemy.url", sync_url)

            engine = sa.create_engine(sync_url)
            for _ in range(30):
                try:
                    with engine.connect() as c:
                        c.execute(sa.text("SELECT 1"))
                    break
                except Exception:
                    time.sleep(0.2)

            # 1. Upgrade up to 0012 and insert pre-existing rows in the 4 tables
            command.upgrade(alembic_cfg, "0012_story_3_2c")
            with engine.begin() as conn:
                conn.execute(
                    sa.text(
                        """
                        INSERT INTO org_units (id, slug, name, unit_type)
                        VALUES (
                            '0192c4e0-0000-7000-8000-000000000101',
                            'ent-root', 'Enterprise', 'ENTERPRISE'
                        );
                        INSERT INTO users (
                            id, email, display_name, auth_mode,
                            human_profile_archetype, platform_role, primary_org_unit_id
                        ) VALUES (
                            '0192c4e0-0000-7000-8000-000000000601',
                            'lead@orcia.io', 'Lead', 'LOCAL',
                            'TECH_LEAD', 'TEAM_LEAD', '0192c4e0-0000-7000-8000-000000000101'
                        );
                        INSERT INTO workspaces (id, slug, name, owner_org_unit_id)
                        VALUES (
                            '0192c4e0-0000-7000-8000-000000000201',
                            'ws-alpha', 'WS Alpha', '0192c4e0-0000-7000-8000-000000000101'
                        );
                        INSERT INTO workspace_datasources (
                            id, workspace_id, alias, scheme, uri, role
                        ) VALUES (
                            '0192c4e0-0000-7000-8000-000000000301',
                            '0192c4e0-0000-7000-8000-000000000201',
                            'git_core', 'git', 'git://claims/core@main', 'PRIMARY'
                        );
                        INSERT INTO user_passthrough_credentials (
                            id, user_id, connector_scheme, target_host, ciphertext_b64, nonce_b64
                        ) VALUES (
                            '0192c4e0-0000-7000-8000-000000000401',
                            '0192c4e0-0000-7000-8000-000000000601',
                            'jira', 'jira.internal', 'Y2lwaGVy', 'bm9uY2U='
                        );
                        INSERT INTO permission_broker_policies (
                            id, policy_key, uri_pattern, connector_scheme,
                            required_role, approver_team, request_url_template, sla_hours
                        ) VALUES (
                            '0192c4e0-0000-7000-8000-000000000501',
                            'pol-git', 'git://claims/*', 'git',
                            'DEV', 'SECOPS', 'https://jira/req', 24
                        );
                        INSERT INTO permission_broker_tickets (
                            id, ticket_key, workspace_id, requester_user_id, policy_id,
                            step_key, target_uri, connector_scheme, required_role,
                            approver_team, sla_hours, jira_request_url, permission_broker_hint
                        ) VALUES (
                            '0192c4e0-0000-7000-8000-000000000502',
                            'tkt-001', '0192c4e0-0000-7000-8000-000000000201',
                            '0192c4e0-0000-7000-8000-000000000601',
                            '0192c4e0-0000-7000-8000-000000000501',
                            'step-1', 'git://claims/core', 'git', 'DEV',
                            'SECOPS', 24, 'https://jira/req', 'Hint'
                        );
                        """
                    )
                )

            # 2. Upgrade to 0013 (Expand) and 0014 (Contract)
            command.upgrade(alembic_cfg, "0014_story_3_2e")

            with engine.begin() as conn:
                # Register a custom non-SDLC scheme ('sap') and insert a datasource using it
                conn.execute(
                    sa.text(
                        """
                        INSERT INTO connector_schemes (id, scheme, display_name, pack_name)
                        VALUES (
                            '0192c4e0-0000-7000-8000-00000000c099',
                            'sap', 'SAP S/4HANA', 'orcia-connector-sap-fake'
                        );
                        INSERT INTO workspace_datasources (
                            id, workspace_id, alias, scheme, uri, role
                        ) VALUES (
                            '0192c4e0-0000-7000-8000-000000000399',
                            '0192c4e0-0000-7000-8000-000000000201',
                            'sap_erp', 'sap', 'sap://erp-prod/orders/1@v1', 'ERP'
                        );
                        """
                    )
                )
                count = conn.execute(
                    sa.text("SELECT COUNT(*) FROM workspace_datasources;")
                ).scalar_one()
                assert count == 2
                # Clean up 'sap' row before testing downgrade to 0012
                conn.execute(sa.text("DELETE FROM workspace_datasources WHERE scheme = 'sap';"))

            # 3. Downgrade back to 0012 and re-upgrade to head
            command.downgrade(alembic_cfg, "0012_story_3_2c")
            command.upgrade(alembic_cfg, "head")
            engine.dispose()
    finally:
        shutil.rmtree(sock_dir, ignore_errors=True)
