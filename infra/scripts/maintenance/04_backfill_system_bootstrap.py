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
import os
from dataclasses import dataclass

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from orcia_core.bootstrap.seeder import (
    DEFAULT_LLM_MODEL_ENDPOINT_SEEDS,
    DEFAULT_ORG_UNIT_SEEDS,
    DEFAULT_SYSTEM_BOOTSTRAP_RUN_SEEDS,
    DEFAULT_SYSTEM_BOOTSTRAP_WORKFLOW_SEEDS,
    DEFAULT_USER_ONBOARDING_STATE_SEEDS,
    DEFAULT_WORKSPACE_SEEDS,
    LLM_MODEL_ENDPOINTS_UPSERT_SPEC,
    ORG_UNITS_UPSERT_SPEC,
    SYSTEM_BOOTSTRAP_RUNS_UPSERT_SPEC,
    USER_ONBOARDING_STATES_UPSERT_SPEC,
    WORKFLOW_DEFINITIONS_UPSERT_SPEC,
    WORKSPACES_UPSERT_SPEC,
    build_postgres_upsert_sql,
)


@dataclass(frozen=True, slots=True)
class SystemBootstrapBackfillReport:
    """Summary of the reference System Bootstrap workflows, LLM endpoints & onboarding backfill."""

    llm_endpoints_count: int
    bootstrap_workflows_count: int
    bootstrap_runs_count: int
    onboarding_states_count: int
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


async def backfill_system_bootstrap(
    engine: AsyncEngine,
    *,
    apply_changes: bool = False,
    batch_size: int = 100,
) -> SystemBootstrapBackfillReport:
    """Populate or update `llm_model_endpoints`, `workflow_definitions`, `system_bootstrap_runs`,
    and `user_onboarding_states`.

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
    llm_sql = sa.text(build_postgres_upsert_sql(LLM_MODEL_ENDPOINTS_UPSERT_SPEC))
    wf_sql = sa.text(build_postgres_upsert_sql(WORKFLOW_DEFINITIONS_UPSERT_SPEC))
    run_sql = sa.text(build_postgres_upsert_sql(SYSTEM_BOOTSTRAP_RUNS_UPSERT_SPEC))
    onb_sql = sa.text(build_postgres_upsert_sql(USER_ONBOARDING_STATES_UPSERT_SPEC))

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

            for idx in range(0, len(DEFAULT_SYSTEM_BOOTSTRAP_RUN_SEEDS), batch_size):
                for run in DEFAULT_SYSTEM_BOOTSTRAP_RUN_SEEDS[idx : idx + batch_size]:
                    await conn.execute(
                        run_sql,
                        {
                            "id": run.id,
                            "run_key": run.run_key,
                            "workflow_uri": run.workflow_uri,
                            "scope_level": run.scope_level,
                            "target_org_unit_id": run.target_org_unit_id,
                            "target_workspace_id": run.target_workspace_id,
                            "triggered_by_user_id": run.triggered_by_user_id,
                            "status": run.status,
                            "gate_passed": run.gate_passed,
                            "gate_report_jsonb": run.gate_report_json,
                            "execution_payload_jsonb": run.execution_payload_json,
                        },
                    )

            for idx in range(0, len(DEFAULT_USER_ONBOARDING_STATE_SEEDS), batch_size):
                for st in DEFAULT_USER_ONBOARDING_STATE_SEEDS[idx : idx + batch_size]:
                    await conn.execute(
                        onb_sql,
                        {
                            "id": st.id,
                            "user_email": st.user_email,
                            "user_id": st.user_id,
                            "invited_by_user_id": st.invited_by_user_id,
                            "org_unit_id": st.org_unit_id,
                            "human_profile_archetype": st.human_profile_archetype,
                            "assigned_role": st.assigned_role,
                            "workspace_ids_jsonb": st.workspace_ids_json,
                            "init_user_completed": st.init_user_completed,
                            "linked_connectors_jsonb": st.linked_connectors_json,
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
    args = build_arg_parser().parse_args(argv)
    db_url = os.getenv(
        "DATABASE_URL", "postgresql+asyncpg://orcia:orcia_dev_secret@localhost:5432/orcia"
    )
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
