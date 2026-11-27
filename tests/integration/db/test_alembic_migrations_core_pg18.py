"""Layer 2 Alembic `0013`–`0016` core schema migrations against real PostgreSQL 18."""

from __future__ import annotations

from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from tests.integration._tc_socket_helpers import open_pg18_alembic_container

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_alembic_0013_0014_connector_schemes_expand_contract_with_rows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify `0013` (Expand) and `0014` (Contract) upgrade & downgrade on PostgreSQL 18."""
    with open_pg18_alembic_container("tc_0013", monkeypatch, REPO_ROOT) as (engine, alembic_cfg):
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

        command.upgrade(alembic_cfg, "0014_story_3_2e")
        with engine.begin() as conn:
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
            conn.execute(sa.text("DELETE FROM workspace_datasources WHERE scheme = 'sap';"))

        command.downgrade(alembic_cfg, "0012_story_3_2c")
        command.upgrade(alembic_cfg, "head")


def test_alembic_0015_human_anchors_and_arbitration_tables(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify migration 0015 creates `human_anchor_signatures` and `human_arbitration_requests`."""
    with open_pg18_alembic_container("tc_0015", monkeypatch, REPO_ROOT) as (engine, alembic_cfg):
        command.upgrade(alembic_cfg, "0015_story_3_4")
        with engine.begin() as conn:
            tables = set(
                conn.execute(
                    sa.text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
                ).scalars()
            )
            assert "human_anchor_signatures" in tables
            assert "human_arbitration_requests" in tables

        command.downgrade(alembic_cfg, "0014_story_3_2e")
        command.upgrade(alembic_cfg, "0015_story_3_4")


def test_alembic_0016_upstream_challenges_table(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify migration 0016 creates `upstream_challenges` on PostgreSQL 18."""
    with open_pg18_alembic_container("tc_0016", monkeypatch, REPO_ROOT) as (engine, alembic_cfg):
        command.upgrade(alembic_cfg, "0016_story_3_5")
        with engine.begin() as conn:
            tables = set(
                conn.execute(
                    sa.text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
                ).scalars()
            )
            assert "upstream_challenges" in tables

        command.downgrade(alembic_cfg, "0015_story_3_4")
        command.upgrade(alembic_cfg, "0016_story_3_5")
