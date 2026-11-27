"""Layer 2 Alembic `0017`–`0021` governance & runtime migrations against PostgreSQL 18."""

from __future__ import annotations

from pathlib import Path

import pytest
import sqlalchemy as sa
from alembic import command
from tests.integration._tc_socket_helpers import open_pg18_alembic_container

REPO_ROOT = Path(__file__).resolve().parents[3]


def test_alembic_0017_gate_evaluations_columns(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify migration `0017_story_4_1` (`gate_evaluations`) on real PostgreSQL 18 container."""
    with open_pg18_alembic_container("tc_0017", monkeypatch, REPO_ROOT) as (engine, alembic_cfg):
        command.upgrade(alembic_cfg, "0017_story_4_1")
        with engine.begin() as conn:
            cols = list(
                conn.execute(
                    sa.text(
                        "SELECT column_name FROM information_schema.columns "
                        "WHERE table_name = 'gate_evaluations' ORDER BY ordinal_position"
                    )
                ).scalars()
            )
            assert "gate_type" in cols
            assert "sandbox_tier" in cols
            assert "pattern_drift_passed" in cols
            assert "pattern_drift_findings_jsonb" in cols
            assert "briefing_4blocks_jsonb" in cols

        command.downgrade(alembic_cfg, "0016_story_3_5")
        command.upgrade(alembic_cfg, "0017_story_4_1")


def test_alembic_0019_expand_backfill_and_0020_contract_request_url(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify `0019` (Expand + Backfill `request_url`) and `0020` (Contract `jira_request_url`)."""
    with open_pg18_alembic_container("tc_0019", monkeypatch, REPO_ROOT) as (engine, alembic_cfg):
        command.upgrade(alembic_cfg, "0018_story_4_3")
        with engine.begin() as conn:
            conn.execute(
                sa.text(
                    """
                    INSERT INTO org_units (id, slug, name, unit_type)
                    VALUES (
                        '0192c4e0-0000-7000-8000-000000000101',
                        'org-1', 'Org 1', 'ENTERPRISE'
                    );
                    INSERT INTO users (
                        id, email, display_name, auth_mode,
                        human_profile_archetype, platform_role, primary_org_unit_id
                    ) VALUES (
                        '0192c4e0-0000-7000-8000-000000000601',
                        'lead@orcia.io', 'Lead', 'LOCAL',
                        'TECH_LEAD', 'TEAM_LEAD', '0192c4e0-0000-7000-8000-000000000101'
                    );
                    INSERT INTO permission_broker_policies (
                        id, policy_key, uri_pattern, connector_scheme,
                        required_role, approver_team, request_url_template, sla_hours
                    ) VALUES (
                        '0192c4e0-0000-7000-8000-000000000501',
                        'pol-jira', 'jira://*', 'jira',
                        'DEV', 'SECOPS', 'https://jira.internal/req', 24
                    );
                    INSERT INTO permission_broker_tickets (
                        id, ticket_key, requester_user_id, policy_id,
                        step_key, target_uri, connector_scheme, required_role,
                        approver_team, sla_hours, jira_request_url, permission_broker_hint
                    ) VALUES (
                        '0192c4e0-0000-7000-8000-000000000502',
                        'tkt-legacy-jira', '0192c4e0-0000-7000-8000-000000000601',
                        '0192c4e0-0000-7000-8000-000000000501',
                        'step-1', 'jira://PAYSEC/PAYSEC-204', 'jira', 'DEV',
                        'SECOPS', 24, 'https://jira.internal/req?legacy=1', 'jira://IAM/DEV'
                    );
                    """
                )
            )

        command.upgrade(alembic_cfg, "0019_story_4_4_expand")
        with engine.connect() as conn:
            row = conn.execute(
                sa.text(
                    "SELECT request_url, jira_request_url FROM permission_broker_tickets "
                    "WHERE ticket_key = 'tkt-legacy-jira'"
                )
            ).one()
            assert row[0] == "https://jira.internal/req?legacy=1"
            assert row[1] == "https://jira.internal/req?legacy=1"

        command.upgrade(alembic_cfg, "0020_story_4_4_contract")
        with engine.connect() as conn:
            cols = {
                r[0]
                for r in conn.execute(
                    sa.text(
                        "SELECT column_name FROM information_schema.columns "
                        "WHERE table_name = 'permission_broker_tickets'"
                    )
                )
            }
            assert "request_url" in cols
            assert "jira_request_url" not in cols

        command.downgrade(alembic_cfg, "0018_story_4_3")
        command.upgrade(alembic_cfg, "head")


def test_alembic_0021_notifications_and_resource_leases_tables(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify Alembic 0021_story_5_1 upgrade/downgrade/upgrade on real PostgreSQL 18."""
    with open_pg18_alembic_container("tc_0021", monkeypatch, REPO_ROOT) as (engine, alembic_cfg):
        command.upgrade(alembic_cfg, "0021_story_5_1")
        with engine.connect() as conn:
            tables = {
                r[0]
                for r in conn.execute(
                    sa.text(
                        "SELECT table_name FROM information_schema.tables "
                        "WHERE table_schema = 'public'"
                    )
                )
            }
            assert "task_notifications" in tables
            assert "resource_leases" in tables
            step_cols = {
                r[0]
                for r in conn.execute(
                    sa.text(
                        "SELECT column_name FROM information_schema.columns "
                        "WHERE table_name = 'step_executions'"
                    )
                )
            }
            assert "claimed_by_user_id" in step_cols
            assert "claimed_at" in step_cols

        command.downgrade(alembic_cfg, "0020_story_4_4_contract")
        command.upgrade(alembic_cfg, "head")
