"""PostgreSQL 18 Persistence Adapter for Platform Setup State (`Epics 8..12` Vertical Wiring).

Atomically persists and reloads the full platform setup state (`orgUnits`, `rbacGrants`,
`llmTiers`, `workspaces`, `datasources`, `packs`, `workflows`, `runs`, `catalogItems`,
`ontologyConcepts`, `auditEvents`) inside `platform_settings` while synchronizing relational
tables (`org_units`, `workspaces`, `llm_model_endpoints`) on PostgreSQL 18.
"""

from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from orcia_core.bootstrap._internal.sql_first_user_guard import (
    get_first_platform_admin_from_postgres18,
)
from orcia_core.bootstrap._internal.sql_platform_setup_relational_sync import (
    ROOT_ORG_UNIT_ID,
    deterministic_setup_uuid,
    normalize_setup_slug,
    sync_relational_tables_on_postgres18,
)
from orcia_core.bootstrap.models import LlmModelEndpoint
from orcia_kernel.ids import new_uuid7_str

GLOBAL_SETUP_SCOPE_ID = UUID("0192c4e0-0000-7000-8000-000000000000")
PLATFORM_SETUP_SETTING_KEY = "platform_setup_state_v1"

# Re-exported aliases for internal compatibility
_deterministic_uuid = deterministic_setup_uuid
_normalize_slug = normalize_setup_slug


@dataclass(frozen=True, slots=True)
class PlatformSetupSnapshotRecord:
    """Complete platform setup state persisted in PostgreSQL 18."""

    first_admin_initialized: bool = False
    first_admin_email: str | None = None
    first_admin_display_name: str | None = None
    org_units: list[dict[str, Any]] = field(default_factory=list)
    rbac_grants: list[dict[str, Any]] = field(default_factory=list)
    llm_tiers: list[dict[str, Any]] = field(default_factory=list)
    workspaces: list[dict[str, Any]] = field(default_factory=list)
    datasources: list[dict[str, Any]] = field(default_factory=list)
    packs: list[dict[str, Any]] = field(default_factory=list)
    workflows: list[dict[str, Any]] = field(default_factory=list)
    runs: list[dict[str, Any]] = field(default_factory=list)
    catalog_items: list[dict[str, Any]] = field(default_factory=list)
    ontology_concepts: list[dict[str, Any]] = field(default_factory=list)
    audit_events: list[dict[str, Any]] = field(default_factory=list)

    def to_payload_dict(self) -> dict[str, Any]:
        """Serialize the 11 collections into a JSON-compatible dictionary."""
        return {
            "org_units": list(self.org_units),
            "rbac_grants": list(self.rbac_grants),
            "llm_tiers": list(self.llm_tiers),
            "workspaces": list(self.workspaces),
            "datasources": list(self.datasources),
            "packs": list(self.packs),
            "workflows": list(self.workflows),
            "runs": list(self.runs),
            "catalog_items": list(self.catalog_items),
            "ontology_concepts": list(self.ontology_concepts),
            "audit_events": list(self.audit_events),
        }


async def _reconcile_org_units_on_load(
    conn: AsyncConnection,
    raw_org_units: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Reconcile `org_units` from the relational `org_units` table when JSONB list is empty."""
    if raw_org_units:
        return list(raw_org_units)

    org_rows = (
        await conn.execute(
            sa.text(
                """
                SELECT id, slug, name, unit_type, parent_id
                FROM org_units
                WHERE unit_type IN ('BU', 'TEAM')
                ORDER BY CASE WHEN unit_type = 'BU' THEN 0 ELSE 1 END, created_at ASC
                """
            )
        )
    ).fetchall()
    ui_id_by_db_uuid: dict[str, str] = {}
    reconciled: list[dict[str, Any]] = []
    for idx, org_row in enumerate(org_rows):
        db_uuid_str = str(org_row[0])
        ui_id = f"org-{idx + 1}"
        ui_id_by_db_uuid[db_uuid_str] = ui_id
        parent_db_str = str(org_row[4]) if org_row[4] is not None else ""
        parent_ui_id = ui_id_by_db_uuid.get(parent_db_str, "scope-global")
        level = "TEAM" if str(org_row[3]).upper() == "TEAM" else "BU"
        reconciled.append(
            {
                "id": ui_id,
                "name": str(org_row[2]),
                "slug": str(org_row[1]),
                "level": level,
                "parentId": parent_ui_id,
            }
        )
    return reconciled


async def _reconcile_workspaces_on_load(
    conn: AsyncConnection,
    raw_workspaces: list[dict[str, Any]],
    org_units: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Reconcile `workspaces` from relational `workspaces` and enrich `ownerOrgUnitName`."""
    org_by_ref: dict[str, dict[str, Any]] = {}
    for u in org_units:
        uid = str(u.get("id") or "")
        uslug = str(u.get("slug") or "")
        if uid:
            org_by_ref[uid] = u
        if uslug:
            org_by_ref[uslug] = u

    workspaces = [dict(ws) for ws in raw_workspaces]
    if not workspaces:
        ws_rows = (
            await conn.execute(
                sa.text(
                    """
                    SELECT w.id, w.slug, w.name, w.visibility_mode, w.settings_jsonb,
                           w.finops_cost_usd, o.slug, o.name, o.unit_type
                    FROM workspaces w
                    LEFT JOIN org_units o ON o.id = w.owner_org_unit_id
                    ORDER BY w.created_at ASC
                    """
                )
            )
        ).fetchall()
        for ws_row in ws_rows:
            st_raw = ws_row[4]
            st_dict = (
                json.loads(st_raw)
                if isinstance(st_raw, str)
                else (st_raw if isinstance(st_raw, dict) else {})
            )
            owner_slug = str(ws_row[6] or "")
            owner_unit_type = str(ws_row[8] or "").upper()
            matched_org = org_by_ref.get(str(st_dict.get("owner_org_unit_id") or "")) or (
                org_by_ref.get(owner_slug) if owner_unit_type in ("BU", "TEAM") else None
            )
            owner_org_id = (
                str(matched_org["id"])
                if matched_org
                else str(st_dict.get("owner_org_unit_id") or "")
            )
            owner_org_name = (
                str(matched_org["name"])
                if matched_org
                else str(
                    st_dict.get("owner_org_unit_name")
                    or (ws_row[7] if owner_unit_type in ("BU", "TEAM") else "")
                )
            )
            ws_entry: dict[str, Any] = {
                "workspaceId": str(st_dict.get("ui_workspace_id") or ws_row[0]),
                "name": str(ws_row[2]),
                "slug": str(ws_row[1]),
                "visibilityMode": str(st_dict.get("ui_visibility_mode") or ws_row[3]),
                "lifecyclePhase": str(st_dict.get("lifecycle_phase") or "BUILD"),
                "suggestedWorkflows": [],
                "accessMode": "CONTRIBUTOR_ACTION_REQUIRED",
                "finopsCostUsd": float(ws_row[5] or 0.0),
            }
            if owner_org_id:
                ws_entry["ownerOrgUnitId"] = owner_org_id
            if owner_org_name:
                ws_entry["ownerOrgUnitName"] = owner_org_name
            workspaces.append(ws_entry)

    for ws in workspaces:
        if not ws.get("ownerOrgUnitName"):
            owner_ref = str(ws.get("ownerOrgUnitId") or "").strip()
            matched = org_by_ref.get(owner_ref)
            if matched and matched.get("name"):
                ws["ownerOrgUnitName"] = str(matched["name"])
    return workspaces


async def save_platform_setup_state_to_postgres18(
    engine: AsyncEngine,
    snapshot: PlatformSetupSnapshotRecord,
    *,
    orcia_env: str = "local",
) -> PlatformSetupSnapshotRecord:
    """Persist the complete `PlatformSetupSnapshotRecord` into PostgreSQL 18 atomically."""
    payload_dict = snapshot.to_payload_dict()
    payload_json = json.dumps(payload_dict, ensure_ascii=False, sort_keys=True)
    etag = hashlib.sha256(payload_json.encode("utf-8")).hexdigest()[:32]

    async with engine.begin() as conn:
        await conn.execute(
            sa.text(
                """
                INSERT INTO platform_settings (
                    id, scope_level, scope_id, category, key,
                    value_jsonb, version, etag, updated_by
                )
                VALUES (
                    :id, 'GLOBAL', :scope_id, 'iam', :key,
                    CAST(:value_jsonb AS jsonb), 1, :etag, 'platform_admin'
                )
                ON CONFLICT (scope_level, scope_id, category, key) DO UPDATE
                SET value_jsonb = EXCLUDED.value_jsonb,
                    version = platform_settings.version + 1,
                    etag = EXCLUDED.etag,
                    updated_at = NOW()
                """
            ),
            {
                "id": UUID(new_uuid7_str()),
                "scope_id": GLOBAL_SETUP_SCOPE_ID,
                "key": PLATFORM_SETUP_SETTING_KEY,
                "value_jsonb": payload_json,
                "etag": etag,
            },
        )
        await sync_relational_tables_on_postgres18(
            conn,
            org_units=list(snapshot.org_units),
            workspaces=list(snapshot.workspaces),
            llm_tiers=list(snapshot.llm_tiers),
        )

    admin_rec = await get_first_platform_admin_from_postgres18(engine, orcia_env=orcia_env)
    return PlatformSetupSnapshotRecord(
        first_admin_initialized=admin_rec is not None,
        first_admin_email=admin_rec.email if admin_rec is not None else snapshot.first_admin_email,
        first_admin_display_name=(
            admin_rec.display_name if admin_rec is not None else snapshot.first_admin_display_name
        ),
        org_units=list(snapshot.org_units),
        rbac_grants=list(snapshot.rbac_grants),
        llm_tiers=list(snapshot.llm_tiers),
        workspaces=list(snapshot.workspaces),
        datasources=list(snapshot.datasources),
        packs=list(snapshot.packs),
        workflows=list(snapshot.workflows),
        runs=list(snapshot.runs),
        catalog_items=list(snapshot.catalog_items),
        ontology_concepts=list(snapshot.ontology_concepts),
        audit_events=list(snapshot.audit_events),
    )


async def load_platform_setup_state_from_postgres18(
    engine: AsyncEngine,
    *,
    orcia_env: str = "local",
) -> PlatformSetupSnapshotRecord:
    """Load the persisted `PlatformSetupSnapshotRecord` from PostgreSQL 18."""
    admin_rec = await get_first_platform_admin_from_postgres18(engine, orcia_env=orcia_env)
    raw_value: dict[str, Any] = {}

    async with engine.connect() as conn:
        row = (
            await conn.execute(
                sa.text(
                    """
                    SELECT value_jsonb
                    FROM platform_settings
                    WHERE scope_level = 'GLOBAL'
                      AND scope_id = :scope_id
                      AND category = 'iam'
                      AND key = :key
                    LIMIT 1
                    """
                ),
                {
                    "scope_id": GLOBAL_SETUP_SCOPE_ID,
                    "key": PLATFORM_SETUP_SETTING_KEY,
                },
            )
        ).first()
        if row is not None and row[0] is not None:
            loaded = row[0]
            if isinstance(loaded, str):
                raw_value = json.loads(loaded)
            elif isinstance(loaded, dict):
                raw_value = dict(loaded)

        llm_tiers = list(raw_value.get("llm_tiers") or [])
        if not llm_tiers:
            ep_rows = (
                await conn.execute(
                    sa.text(
                        """
                        SELECT endpoint_key, model_name, model_family
                        FROM llm_model_endpoints
                        WHERE is_active = TRUE
                        ORDER BY created_at ASC
                        """
                    )
                )
            ).fetchall()
            tier_names = ("medium", "complex", "simple")
            for idx, ep in enumerate(ep_rows):
                llm_tiers.append(
                    {
                        "tier": tier_names[idx % len(tier_names)],
                        "primaryModel": str(ep[1]),
                        "secondaryModel": str(ep[1]),
                        "modelFamily": str(ep[2]),
                        "defaultEffort": "balanced",
                    }
                )

        org_units = await _reconcile_org_units_on_load(conn, list(raw_value.get("org_units") or []))
        workspaces = await _reconcile_workspaces_on_load(
            conn, list(raw_value.get("workspaces") or []), org_units
        )

    return PlatformSetupSnapshotRecord(
        first_admin_initialized=admin_rec is not None,
        first_admin_email=admin_rec.email if admin_rec is not None else None,
        first_admin_display_name=admin_rec.display_name if admin_rec is not None else None,
        org_units=org_units,
        rbac_grants=list(raw_value.get("rbac_grants") or []),
        llm_tiers=llm_tiers,
        workspaces=workspaces,
        datasources=list(raw_value.get("datasources") or []),
        packs=list(raw_value.get("packs") or []),
        workflows=list(raw_value.get("workflows") or []),
        runs=list(raw_value.get("runs") or []),
        catalog_items=list(raw_value.get("catalog_items") or []),
        ontology_concepts=list(raw_value.get("ontology_concepts") or []),
        audit_events=list(raw_value.get("audit_events") or []),
    )


async def persist_progressive_llm_endpoint_to_postgres18(
    engine: AsyncEngine,
    endpoint: LlmModelEndpoint,
) -> None:
    """Persist a progressive Day-0 LLM endpoint into `llm_model_endpoints` on PostgreSQL 18."""
    ep_uuid = deterministic_setup_uuid(f"llm-ep:{endpoint.endpoint_key}")
    async with engine.begin() as conn:
        await conn.execute(
            sa.text(
                """
                INSERT INTO llm_model_endpoints (
                    id, endpoint_key, provider_slug, model_family, model_name,
                    endpoint_uri, connectivity_verified, is_active
                )
                VALUES (
                    :id, :endpoint_key, :provider_slug, :model_family, :model_name,
                    :endpoint_uri, :connectivity_verified, :is_active
                )
                ON CONFLICT (endpoint_key) DO UPDATE
                SET provider_slug = EXCLUDED.provider_slug,
                    model_family = EXCLUDED.model_family,
                    model_name = EXCLUDED.model_name,
                    endpoint_uri = EXCLUDED.endpoint_uri,
                    connectivity_verified = EXCLUDED.connectivity_verified,
                    is_active = EXCLUDED.is_active
                """
            ),
            {
                "id": ep_uuid,
                "endpoint_key": endpoint.endpoint_key,
                "provider_slug": endpoint.provider_slug,
                "model_family": endpoint.model_family,
                "model_name": endpoint.model_name,
                "endpoint_uri": endpoint.endpoint_uri,
                "connectivity_verified": endpoint.connectivity_verified,
                "is_active": endpoint.is_active,
            },
        )


__all__ = [
    "GLOBAL_SETUP_SCOPE_ID",
    "PLATFORM_SETUP_SETTING_KEY",
    "ROOT_ORG_UNIT_ID",
    "PlatformSetupSnapshotRecord",
    "load_platform_setup_state_from_postgres18",
    "persist_progressive_llm_endpoint_to_postgres18",
    "save_platform_setup_state_to_postgres18",
]
