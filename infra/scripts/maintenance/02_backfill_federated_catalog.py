"""Maintenance script `02_backfill_federated_catalog.py` for Story 1.3.

Conventions (AGENTS.md):
- Operational data transformations or backfills outside schema migrations live in
  `infra/scripts/maintenance/XX_*.py`.
- Mandatory `--dry-run` mode (default rollback unless `--apply` is explicitly passed).
- Uses batched idempotent transactions (`INSERT ... ON CONFLICT DO UPDATE`).
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
    CATALOG_ITEMS_UPSERT_SPEC,
    CUSTOMIZATION_OVERRIDES_UPSERT_SPEC,
    DEFAULT_CATALOG_ITEM_SEEDS,
    DEFAULT_CUSTOMIZATION_OVERRIDE_SEEDS,
    DEFAULT_ORG_UNIT_SEEDS,
    DEFAULT_WORKFLOW_DEFINITION_SEEDS,
    DEFAULT_WORKSPACE_SEEDS,
    ORG_UNITS_UPSERT_SPEC,
    WORKFLOW_DEFINITIONS_UPSERT_SPEC,
    WORKSPACES_UPSERT_SPEC,
    build_postgres_upsert_sql,
)


@dataclass(frozen=True, slots=True)
class FederatedCatalogBackfillReport:
    """Summary of the reference federated catalog, workflow definitions, and overrides backfill."""

    catalog_items_count: int
    workflow_definitions_count: int
    customization_overrides_count: int
    dry_run: bool
    committed: bool


async def backfill_federated_catalog(
    engine: AsyncEngine,
    *,
    apply_changes: bool = False,
    batch_size: int = 100,
) -> FederatedCatalogBackfillReport:
    """Populate or update `catalog_items`, `workflow_definitions`, and overrides.

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
    item_sql = sa.text(build_postgres_upsert_sql(CATALOG_ITEMS_UPSERT_SPEC))
    wf_sql = sa.text(build_postgres_upsert_sql(WORKFLOW_DEFINITIONS_UPSERT_SPEC))
    ovr_sql = sa.text(build_postgres_upsert_sql(CUSTOMIZATION_OVERRIDES_UPSERT_SPEC))

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
            await conn.execute(
                user_sql,
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

            for idx in range(0, len(DEFAULT_CATALOG_ITEM_SEEDS), batch_size):
                for cat in DEFAULT_CATALOG_ITEM_SEEDS[idx : idx + batch_size]:
                    await conn.execute(
                        item_sql,
                        {
                            "id": cat.id,
                            "resource_id": cat.resource_id,
                            "uri": cat.uri,
                            "title": cat.title,
                            "description": cat.description,
                            "resource_type": cat.resource_type,
                            "source_format": cat.source_format,
                            "version": cat.version,
                            "sha256": cat.sha256,
                            "cas_key": cat.cas_key,
                            "visibility_scope": cat.visibility_scope,
                            "owner_org_unit_id": cat.owner_org_unit_id,
                            "owner_workspace_id": cat.owner_workspace_id,
                        },
                    )

            for idx in range(0, len(DEFAULT_WORKFLOW_DEFINITION_SEEDS), batch_size):
                for wf in DEFAULT_WORKFLOW_DEFINITION_SEEDS[idx : idx + batch_size]:
                    await conn.execute(
                        wf_sql,
                        {
                            "id": wf.id,
                            "workspace_id": wf.workspace_id,
                            "uri": wf.uri,
                            "version": wf.version,
                            "source_format": wf.source_format,
                            "steps_schema_jsonb": json.dumps(json.loads(wf.steps_schema_json)),
                            "adaptive_gate_policy": wf.adaptive_gate_policy,
                            "sha256": wf.sha256,
                        },
                    )

            for idx in range(0, len(DEFAULT_CUSTOMIZATION_OVERRIDE_SEEDS), batch_size):
                for ovr in DEFAULT_CUSTOMIZATION_OVERRIDE_SEEDS[idx : idx + batch_size]:
                    await conn.execute(
                        ovr_sql,
                        {
                            "id": ovr.id,
                            "override_key": ovr.override_key,
                            "org_unit_id": ovr.org_unit_id,
                            "workspace_id": ovr.workspace_id,
                            "user_id": ovr.user_id,
                            "target_uri": ovr.target_uri,
                            "override_layer": ovr.override_layer,
                            "override_manifest_jsonb": json.dumps(
                                json.loads(ovr.override_manifest_json)
                            ),
                            "sha256": ovr.sha256,
                        },
                    )

            items_res = await conn.execute(sa.text("SELECT COUNT(*) FROM catalog_items"))
            wf_res = await conn.execute(sa.text("SELECT COUNT(*) FROM workflow_definitions"))
            ovr_res = await conn.execute(
                sa.text("SELECT COUNT(*) FROM workspace_customization_overrides")
            )
            items_count = int(items_res.scalar() or 0)
            wf_count = int(wf_res.scalar() or 0)
            ovr_count = int(ovr_res.scalar() or 0)

            if apply_changes:
                await trans.commit()
                committed = True
            else:
                await trans.rollback()
                committed = False

            return FederatedCatalogBackfillReport(
                catalog_items_count=items_count,
                workflow_definitions_count=wf_count,
                customization_overrides_count=ovr_count,
                dry_run=not apply_changes,
                committed=committed,
            )
        except Exception:
            await trans.rollback()
            raise


def build_arg_parser() -> argparse.ArgumentParser:
    """Build CLI argument parser with mandatory dry-run default."""
    parser = argparse.ArgumentParser(
        description="Backfill reference ORCIA federated catalog and 4-layer overrides."
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
    from orcia_core.config import resolve_database_url

    parser = build_arg_parser()
    args = parser.parse_args(argv)
    db_url = resolve_database_url()
    engine = create_async_engine(db_url)
    try:
        report = await backfill_federated_catalog(
            engine,
            apply_changes=bool(args.apply),
            batch_size=int(args.batch_size),
        )
    finally:
        await engine.dispose()

    if report.catalog_items_count < len(DEFAULT_CATALOG_ITEM_SEEDS):
        return 1
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entry point."""
    return asyncio.run(_async_main(argv))


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
