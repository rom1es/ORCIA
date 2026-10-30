"""Maintenance script `08_seed_uat_dataset.py` — Pre-initialized UAT / Recette database seeder.

Allows initializing a dedicated UAT / test PostgreSQL 18 database with a complete, coherent
dataset across all domains (`org_units`, `workspaces`, `workspace_datasources`,
`role_permission_grants`, `workspace_llm_tier_mappings`, `platform_settings`, `wizard_sessions`),
while keeping the web application 100% empty of sample data by default.

Conventions (GEMINI.md):
- Mandatory `--dry-run` mode by default (rolls back unless `--apply` is explicitly passed).
- Uses batched idempotent SQL upserts (`INSERT ... ON CONFLICT DO UPDATE`).
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
from dataclasses import dataclass
from pathlib import Path

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

_CORE_SRC = str(Path(__file__).resolve().parents[3] / "packages" / "orcia-core" / "src")
if _CORE_SRC not in sys.path:
    sys.path.insert(0, _CORE_SRC)

from orcia_core.bootstrap.seeder import (  # noqa: E402
    DEFAULT_ORG_UNIT_SEEDS,
    DEFAULT_WORKSPACE_DATASOURCE_SEEDS,
    DEFAULT_WORKSPACE_SEEDS,
    ORG_UNITS_UPSERT_SPEC,
    WORKSPACE_DATASOURCES_UPSERT_SPEC,
    WORKSPACES_UPSERT_SPEC,
    build_bootstrap_upsert_specs,
    build_postgres_upsert_sql,
)


@dataclass(frozen=True, slots=True)
class UatDatabaseSeedReport:
    """Summary of the UAT / Recette database seeding execution."""

    org_units_count: int
    workspaces_count: int
    datasources_count: int
    system_specs_count: int
    rbac_grants_count: int
    llm_tiers_count: int
    platform_settings_count: int
    dry_run: bool
    committed: bool


UAT_RBAC_GRANTS: tuple[dict[str, object], ...] = (
    {
        "id": "0195f000-0000-7000-8000-000000008101",
        "subject_type": "ROLE",
        "subject_id": "PLATFORM_ADMIN",
        "scope_path": "GLOBAL",
        "verb": "admin",
        "effect": "ALLOW",
        "conditions_jsonb": "{}",
        "hidden_when_unauthorized": False,
        "granted_by": "0195f000-0000-7000-8000-000000000201",
    },
    {
        "id": "0195f000-0000-7000-8000-000000008102",
        "subject_type": "ROLE",
        "subject_id": "TEAM_LEAD",
        "scope_path": "GLOBAL/BU-DIGITAL/TEAM-CHECKOUT",
        "verb": "execute",
        "effect": "ALLOW",
        "conditions_jsonb": json.dumps(
            {"allowed_environments": ["staging", "uat"], "max_tokens_per_run": 64000}
        ),
        "hidden_when_unauthorized": False,
        "granted_by": "0195f000-0000-7000-8000-000000000201",
    },
)

UAT_LLM_TIERS: tuple[dict[str, object], ...] = (
    {
        "id": "0195f000-0000-7000-8000-000000008201",
        "scope_path": "GLOBAL",
        "tier": "simple",
        "primary_model_id": "claude-haiku-4-5",
        "secondary_model_id": "gemini-2.5-flash",
        "model_family": "anthropic",
        "secondary_model_family": "google",
        "default_effort": "low",
        "local_sovereign_only": False,
    },
    {
        "id": "0195f000-0000-7000-8000-000000008202",
        "scope_path": "GLOBAL",
        "tier": "medium",
        "primary_model_id": "claude-sonnet-4-5",
        "secondary_model_id": "gemini-2.5-pro",
        "model_family": "anthropic",
        "secondary_model_family": "google",
        "default_effort": "medium",
        "local_sovereign_only": False,
    },
    {
        "id": "0195f000-0000-7000-8000-000000008203",
        "scope_path": "GLOBAL",
        "tier": "complex",
        "primary_model_id": "claude-opus-4-5",
        "secondary_model_id": "gemini-2.5-pro",
        "model_family": "anthropic",
        "secondary_model_family": "google",
        "default_effort": "high",
        "local_sovereign_only": False,
    },
)

UAT_PLATFORM_SETTINGS: tuple[dict[str, object], ...] = (
    {
        "id": "0195f000-0000-7000-8000-000000008301",
        "scope_path": "GLOBAL",
        "domain_key": "ai-models",
        "setting_key": "default_routing_policy",
        "value_jsonb": json.dumps({"default_tier": "auto", "default_effort": "balanced"}),
        "is_secret_ref": False,
        "etag_version": 1,
        "updated_by": "0195f000-0000-7000-8000-000000000201",
    },
)


async def seed_uat_database(
    engine: AsyncEngine,
    *,
    apply_changes: bool = False,
) -> UatDatabaseSeedReport:
    """Seed the UAT / Recette database with idempotent transactions.

    Rolls back by default unless `apply_changes=True` is explicitly passed.
    """
    org_sql = sa.text(build_postgres_upsert_sql(ORG_UNITS_UPSERT_SPEC))
    ws_sql = sa.text(build_postgres_upsert_sql(WORKSPACES_UPSERT_SPEC))
    ds_sql = sa.text(build_postgres_upsert_sql(WORKSPACE_DATASOURCES_UPSERT_SPEC))
    system_specs = build_bootstrap_upsert_specs()

    grant_sql = sa.text(
        """
        INSERT INTO role_permission_grants (
            id, subject_type, subject_id, scope_path, verb, effect,
            conditions_jsonb, hidden_when_unauthorized, granted_by
        ) VALUES (
            :id, :subject_type, :subject_id, :scope_path, :verb, :effect,
            CAST(:conditions_jsonb AS jsonb), :hidden_when_unauthorized, :granted_by
        )
        ON CONFLICT (subject_type, subject_id, scope_path, verb) DO UPDATE SET
            effect = EXCLUDED.effect,
            conditions_jsonb = EXCLUDED.conditions_jsonb,
            hidden_when_unauthorized = EXCLUDED.hidden_when_unauthorized
        """
    )

    tier_sql = sa.text(
        """
        INSERT INTO workspace_llm_tier_mappings (
            id, scope_path, tier, primary_model_id, secondary_model_id,
            model_family, secondary_model_family, default_effort, local_sovereign_only
        ) VALUES (
            :id, :scope_path, :tier, :primary_model_id, :secondary_model_id,
            :model_family, :secondary_model_family, :default_effort, :local_sovereign_only
        )
        ON CONFLICT (scope_path, tier) DO UPDATE SET
            primary_model_id = EXCLUDED.primary_model_id,
            secondary_model_id = EXCLUDED.secondary_model_id,
            default_effort = EXCLUDED.default_effort
        """
    )

    setting_sql = sa.text(
        """
        INSERT INTO platform_settings (
            id, scope_path, domain_key, setting_key, value_jsonb,
            is_secret_ref, etag_version, updated_by
        ) VALUES (
            :id, :scope_path, :domain_key, :setting_key, CAST(:value_jsonb AS jsonb),
            :is_secret_ref, :etag_version, :updated_by
        )
        ON CONFLICT (scope_path, domain_key, setting_key) DO UPDATE SET
            value_jsonb = EXCLUDED.value_jsonb,
            etag_version = platform_settings.etag_version + 1
        """
    )

    async with engine.connect() as conn:
        trans = await conn.begin()
        try:
            for item in DEFAULT_ORG_UNIT_SEEDS:
                await conn.execute(
                    org_sql,
                    {
                        "id": item.id,
                        "slug": item.slug,
                        "name": item.name,
                        "unit_type": item.unit_type,
                        "parent_id": item.parent_id,
                    },
                )

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

            for ds in DEFAULT_WORKSPACE_DATASOURCE_SEEDS:
                await conn.execute(
                    ds_sql,
                    {
                        "id": ds.id,
                        "workspace_id": ds.workspace_id,
                        "alias": ds.alias,
                        "scheme": ds.scheme,
                        "uri": ds.uri,
                        "role": ds.role,
                        "execution_identity": ds.execution_identity,
                        "freshness_ttl_days": ds.freshness_ttl_days,
                    },
                )

            for grant in UAT_RBAC_GRANTS:
                await conn.execute(grant_sql, grant)

            for tier in UAT_LLM_TIERS:
                await conn.execute(tier_sql, tier)

            for setting in UAT_PLATFORM_SETTINGS:
                await conn.execute(setting_sql, setting)

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

    return UatDatabaseSeedReport(
        org_units_count=len(DEFAULT_ORG_UNIT_SEEDS),
        workspaces_count=len(DEFAULT_WORKSPACE_SEEDS),
        datasources_count=len(DEFAULT_WORKSPACE_DATASOURCE_SEEDS),
        system_specs_count=len(system_specs),
        rbac_grants_count=len(UAT_RBAC_GRANTS),
        llm_tiers_count=len(UAT_LLM_TIERS),
        platform_settings_count=len(UAT_PLATFORM_SETTINGS),
        dry_run=not apply_changes,
        committed=committed,
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse CLI arguments for `08_seed_uat_dataset.py`."""
    parser = argparse.ArgumentParser(
        description="Seed the pre-initialized UAT / Recette database (defaults to --dry-run)."
    )
    parser.add_argument(
        "--database-url",
        default="postgresql+asyncpg://orcia:orcia@localhost:5432/orcia",  # pragma: allowlist secret
        help="Async SQLAlchemy database URL.",
    )
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument(
        "--dry-run",
        action="store_true",
        default=True,
        help="Run in dry-run mode and roll back transaction (default).",
    )
    mode.add_argument(
        "--apply",
        action="store_true",
        default=False,
        help="Commit the UAT dataset to the database.",
    )
    return parser.parse_args(argv)


async def _async_main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    engine = create_async_engine(args.database_url)
    try:
        report = await seed_uat_database(engine, apply_changes=bool(args.apply))
        mode_str = "APPLY (COMMITTED)" if report.committed else "DRY-RUN (ROLLED BACK)"
        print(
            f"[08_seed_uat_dataset] {mode_str} — "
            f"org_units={report.org_units_count}, workspaces={report.workspaces_count}, "
            f"datasources={report.datasources_count}, rbac_grants={report.rbac_grants_count}, "
            f"llm_tiers={report.llm_tiers_count}, settings={report.platform_settings_count}"
        )
        return 0
    finally:
        await engine.dispose()


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(asyncio.run(_async_main()))
