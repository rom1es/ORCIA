"""Maintenance script `03_backfill_permission_broker.py` for Story 1.4.

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
    DEFAULT_PERMISSION_BROKER_POLICY_SEEDS,
    DEFAULT_PERMISSION_BROKER_TICKET_SEEDS,
    DEFAULT_WORKSPACE_SEEDS,
    ORG_UNITS_UPSERT_SPEC,
    PERMISSION_BROKER_POLICIES_UPSERT_SPEC,
    PERMISSION_BROKER_TICKETS_UPSERT_SPEC,
    WORKSPACES_UPSERT_SPEC,
    build_postgres_upsert_sql,
)


@dataclass(frozen=True, slots=True)
class PermissionBrokerBackfillReport:
    """Summary of the reference Permission Broker KB policies and tickets backfill."""

    policies_count: int
    tickets_count: int
    dry_run: bool
    committed: bool


_REFERENCE_USERS: tuple[dict[str, str], ...] = (
    {
        "id": "0192c4e0-0000-7000-8000-000000000601",
        "email": "karim.admin@orcia.io",
        "display_name": "Karim (Ingénieur Plateforme)",
        "auth_mode": "HYBRID",
        "oidc_subject": "oidc|karim-admin",
        "human_profile_archetype": "SECOPS",
        "platform_role": "PLATFORM_ADMIN",
        "primary_org_unit_id": "0192c4e0-0000-7000-8000-000000000101",
    },
    {
        "id": "0192c4e0-0000-7000-8000-000000000603",
        "email": "marc.lead@orcia.io",
        "display_name": "Marc (Chef d'Équipe / Tech Lead)",
        "auth_mode": "HYBRID",
        "oidc_subject": "oidc|marc-lead",
        "human_profile_archetype": "TECH_LEAD",
        "platform_role": "TEAM_LEAD",
        "primary_org_unit_id": "0192c4e0-0000-7000-8000-000000000104",
    },
    {
        "id": "0192c4e0-0000-7000-8000-000000000604",
        "email": "nadia.dev@orcia.io",
        "display_name": "Nadia (Développeuse Senior)",
        "auth_mode": "LOCAL",
        "oidc_subject": "local|nadia-dev",
        "human_profile_archetype": "DEVELOPER",
        "platform_role": "CONTRIBUTOR",
        "primary_org_unit_id": "0192c4e0-0000-7000-8000-000000000104",
    },
)


async def backfill_permission_broker(
    engine: AsyncEngine,
    *,
    apply_changes: bool = False,
    batch_size: int = 100,
) -> PermissionBrokerBackfillReport:
    """Populate or update `permission_broker_policies` and `permission_broker_tickets`.

    Rolls back by default unless `apply_changes=True` is explicitly provided.
    """
    if batch_size <= 0:
        raise ValueError("batch_size must be strictly positive")

    org_sql = sa.text(build_postgres_upsert_sql(ORG_UNITS_UPSERT_SPEC))
    ws_sql = sa.text(build_postgres_upsert_sql(WORKSPACES_UPSERT_SPEC))
    user_sql = sa.text(
        "INSERT INTO users (id, email, display_name, auth_mode, oidc_subject, "
        "human_profile_archetype, platform_role, primary_org_unit_id) "
        "VALUES (:id, :email, :display_name, :auth_mode, :oidc_subject, "
        ":human_profile_archetype, :platform_role, :primary_org_unit_id) "
        "ON CONFLICT (email) DO UPDATE SET "
        "display_name = EXCLUDED.display_name, "
        "platform_role = EXCLUDED.platform_role, "
        "primary_org_unit_id = EXCLUDED.primary_org_unit_id;"
    )
    pol_sql = sa.text(build_postgres_upsert_sql(PERMISSION_BROKER_POLICIES_UPSERT_SPEC))
    tkt_sql = sa.text(build_postgres_upsert_sql(PERMISSION_BROKER_TICKETS_UPSERT_SPEC))

    async with engine.connect() as conn:
        trans = await conn.begin()
        try:
            for org in DEFAULT_ORG_UNIT_SEEDS:
                await conn.execute(
                    org_sql,
                    {
                        "id": org.id,
                        "slug": org.slug,
                        "name": org.name,
                        "unit_type": org.unit_type,
                        "parent_id": org.parent_id,
                    },
                )
            for usr in _REFERENCE_USERS:
                await conn.execute(user_sql, usr)
            for ws in DEFAULT_WORKSPACE_SEEDS:
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

            for idx in range(0, len(DEFAULT_PERMISSION_BROKER_POLICY_SEEDS), batch_size):
                for pol in DEFAULT_PERMISSION_BROKER_POLICY_SEEDS[idx : idx + batch_size]:
                    await conn.execute(
                        pol_sql,
                        {
                            "id": pol.id,
                            "policy_key": pol.policy_key,
                            "uri_pattern": pol.uri_pattern,
                            "connector_scheme": pol.connector_scheme,
                            "required_role": pol.required_role,
                            "approver_team": pol.approver_team,
                            "request_url_template": pol.request_url_template,
                            "sla_hours": pol.sla_hours,
                            "procedure_markdown": pol.procedure_markdown,
                            "service_principal_allowed": pol.service_principal_allowed,
                            "approved_by_admin_id": pol.approved_by_admin_id,
                            "human_anchor_author_id": pol.human_anchor_author_id,
                            "human_anchor_signature": pol.human_anchor_signature,
                            "freshness_ttl_days": pol.freshness_ttl_days,
                        },
                    )

            for idx in range(0, len(DEFAULT_PERMISSION_BROKER_TICKET_SEEDS), batch_size):
                for tkt in DEFAULT_PERMISSION_BROKER_TICKET_SEEDS[idx : idx + batch_size]:
                    await conn.execute(
                        tkt_sql,
                        {
                            "id": tkt.id,
                            "ticket_key": tkt.ticket_key,
                            "workspace_id": tkt.workspace_id,
                            "requester_user_id": tkt.requester_user_id,
                            "policy_id": tkt.policy_id,
                            "step_key": tkt.step_key,
                            "step_number": tkt.step_number,
                            "step_state": tkt.step_state,
                            "status": tkt.status,
                            "target_uri": tkt.target_uri,
                            "connector_scheme": tkt.connector_scheme,
                            "execution_identity": tkt.execution_identity,
                            "upstream_http_status": tkt.upstream_http_status,
                            "required_role": tkt.required_role,
                            "approver_team": tkt.approver_team,
                            "sla_hours": tkt.sla_hours,
                            "jira_request_url": tkt.jira_request_url,
                            "permission_broker_hint": tkt.permission_broker_hint,
                            "procedure_markdown": tkt.procedure_markdown,
                        },
                    )

            pol_res = await conn.execute(sa.text("SELECT COUNT(*) FROM permission_broker_policies"))
            tkt_res = await conn.execute(sa.text("SELECT COUNT(*) FROM permission_broker_tickets"))
            policies_count = int(pol_res.scalar() or 0)
            tickets_count = int(tkt_res.scalar() or 0)

            if apply_changes:
                await trans.commit()
                committed = True
            else:
                await trans.rollback()
                committed = False

            return PermissionBrokerBackfillReport(
                policies_count=policies_count,
                tickets_count=tickets_count,
                dry_run=not apply_changes,
                committed=committed,
            )
        except Exception:
            await trans.rollback()
            raise


def build_arg_parser() -> argparse.ArgumentParser:
    """Build CLI argument parser with mandatory dry-run default."""
    parser = argparse.ArgumentParser(
        description="Backfill reference ORCIA Permission Broker KB policies and tickets."
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
        report = await backfill_permission_broker(
            engine,
            apply_changes=bool(args.apply),
            batch_size=int(args.batch_size),
        )
    finally:
        await engine.dispose()

    if report.policies_count < len(DEFAULT_PERMISSION_BROKER_POLICY_SEEDS):
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    return asyncio.run(_async_main(argv))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
