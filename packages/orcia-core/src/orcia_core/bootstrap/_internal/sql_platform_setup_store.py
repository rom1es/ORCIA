"""PostgreSQL 18 Persistence Adapter for Platform Setup State (`Epics 8..12` Vertical Wiring).

Atomically persists and reloads the full platform setup state (`orgUnits`, `rbacGrants`,
`llmTiers`, `workspaces`, `datasources`, `packs`, `workflows`, `runs`, `catalogItems`,
`ontologyConcepts`, `auditEvents`) inside `platform_settings` while synchronizing relational
tables (`org_units`, `workspaces`, `llm_model_endpoints`) on PostgreSQL 18.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Any
from uuid import UUID, uuid5

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncConnection, AsyncEngine

from orcia_core.bootstrap._internal.sql_first_user_guard import (
    get_first_platform_admin_from_postgres18,
)
from orcia_core.bootstrap.models import LlmModelEndpoint
from orcia_kernel.ids import new_uuid7_str

GLOBAL_SETUP_SCOPE_ID = UUID("0192c4e0-0000-7000-8000-000000000000")
ROOT_ORG_UNIT_ID = UUID("0192c4e0-0000-7000-8000-000000000001")
PLATFORM_SETUP_SETTING_KEY = "platform_setup_state_v1"
_NAMESPACE_ORCIA_SETUP = UUID("0192c4e0-0000-7000-8000-000000000099")
_SLUG_CLEAN_RE = re.compile(r"[^a-z0-9-]+")


def _deterministic_uuid(seed: str) -> UUID:
    try:
        return UUID(seed)
    except (ValueError, TypeError):
        return uuid5(_NAMESPACE_ORCIA_SETUP, seed)


def _normalize_slug(raw: str, fallback: str) -> str:
    cleaned = _SLUG_CLEAN_RE.sub("-", raw.strip().lower()).strip("-")
    return (cleaned or fallback)[:120]


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


async def _ensure_root_org_unit(conn: AsyncConnection) -> UUID:
    row = (
        await conn.execute(
            sa.text(
                """
                INSERT INTO org_units (id, slug, name, unit_type, parent_id)
                VALUES (:id, 'orcia-root', 'ORCIA Root Organization', 'ENTERPRISE', NULL)
                ON CONFLICT (slug) DO UPDATE SET name = EXCLUDED.name
                RETURNING id
                """
            ),
            {"id": ROOT_ORG_UNIT_ID},
        )
    ).first()
    if row is not None and row[0] is not None:
        return UUID(str(row[0]))
    return ROOT_ORG_UNIT_ID


async def _sync_relational_tables_on_postgres18(
    conn: AsyncConnection,
    snapshot: PlatformSetupSnapshotRecord,
) -> None:
    root_org_id = await _ensure_root_org_unit(conn)

    # 1. Synchronize org_units (BU / TEAM)
    for idx, org in enumerate(snapshot.org_units):
        org_key = str(org.get("id") or f"org-{idx + 1}")
        org_uuid = _deterministic_uuid(f"org:{org_key}")
        name = str(org.get("name") or org_key).strip() or org_key
        slug = _normalize_slug(str(org.get("slug") or name), f"org-{idx + 1}")
        level = str(org.get("level") or "BU").upper()
        unit_type = "TEAM" if level == "TEAM" else "BU"
        await conn.execute(
            sa.text(
                """
                INSERT INTO org_units (id, slug, name, unit_type, parent_id)
                VALUES (:id, :slug, :name, :unit_type, :parent_id)
                ON CONFLICT (slug) DO UPDATE
                SET name = EXCLUDED.name,
                    unit_type = EXCLUDED.unit_type
                """
            ),
            {
                "id": org_uuid,
                "slug": slug,
                "name": name[:255],
                "unit_type": unit_type,
                "parent_id": root_org_id,
            },
        )

    # 2. Synchronize workspaces
    for idx, ws in enumerate(snapshot.workspaces):
        ws_key = str(ws.get("workspaceId") or ws.get("id") or f"ws-{idx + 1}")
        ws_uuid = _deterministic_uuid(f"ws:{ws_key}")
        name = str(ws.get("name") or ws_key).strip() or ws_key
        raw_slug = str(ws.get("slug") or name)
        slug = _normalize_slug(raw_slug, f"ws-{idx + 1}")
        vis_raw = str(ws.get("visibilityMode") or "STANDARD").upper()
        visibility_mode = (
            "CONFIDENTIAL_RESTRICTED" if vis_raw == "CONFIDENTIAL_RESTRICTED" else "STANDARD"
        )
        phase = str(ws.get("lifecyclePhase") or "BUILD").upper()
        settings_json = json.dumps({"lifecycle_phase": phase, "ui_workspace_id": ws_key})
        await conn.execute(
            sa.text(
                """
                INSERT INTO workspaces (
                    id, slug, name, owner_org_unit_id, visibility_mode, settings_jsonb
                )
                VALUES (
                    :id, :slug, :name, :owner_org_unit_id, :visibility_mode,
                    CAST(:settings_jsonb AS jsonb)
                )
                ON CONFLICT (slug) DO UPDATE
                SET name = EXCLUDED.name,
                    visibility_mode = EXCLUDED.visibility_mode,
                    settings_jsonb = EXCLUDED.settings_jsonb
                """
            ),
            {
                "id": ws_uuid,
                "slug": slug,
                "name": name[:255],
                "owner_org_unit_id": root_org_id,
                "visibility_mode": visibility_mode,
                "settings_jsonb": settings_json,
            },
        )

    # 3. Synchronize llm_model_endpoints from llm_tiers
    for idx, tier_item in enumerate(snapshot.llm_tiers):
        tier_name = str(tier_item.get("tier") or f"tier-{idx + 1}").strip().lower()
        primary_model = str(tier_item.get("primaryModel") or "model-primary").strip()
        model_family = str(tier_item.get("modelFamily") or "family-a").strip()
        endpoint_key = _normalize_slug(f"tier-{tier_name}-{primary_model}", f"tier-{idx + 1}")
        ep_uuid = _deterministic_uuid(f"llm-ep:{endpoint_key}")
        provider_slug = primary_model.split("/", 1)[0] if "/" in primary_model else "openai-compat"
        await conn.execute(
            sa.text(
                """
                INSERT INTO llm_model_endpoints (
                    id, endpoint_key, provider_slug, model_family, model_name,
                    endpoint_uri, connectivity_verified, is_active
                )
                VALUES (
                    :id, :endpoint_key, :provider_slug, :model_family, :model_name,
                    :endpoint_uri, TRUE, TRUE
                )
                ON CONFLICT (endpoint_key) DO UPDATE
                SET model_family = EXCLUDED.model_family,
                    model_name = EXCLUDED.model_name,
                    is_active = TRUE
                """
            ),
            {
                "id": ep_uuid,
                "endpoint_key": endpoint_key[:128],
                "provider_slug": provider_slug[:64] or "local",
                "model_family": model_family[:64] or "family-a",
                "model_name": primary_model[:128] or "default-model",
                "endpoint_uri": f"https://llm.orcia.local/{endpoint_key}",
            },
        )


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
        await _sync_relational_tables_on_postgres18(conn, snapshot)

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

        # Fallback reconciliation from llm_model_endpoints if llm_tiers in JSONB is empty
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

        workspaces = list(raw_value.get("workspaces") or [])
        if not workspaces:
            ws_rows = (
                await conn.execute(
                    sa.text(
                        """
                        SELECT id, slug, name, visibility_mode, settings_jsonb, finops_cost_usd
                        FROM workspaces
                        ORDER BY created_at ASC
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
                workspaces.append(
                    {
                        "workspaceId": str(st_dict.get("ui_workspace_id") or ws_row[0]),
                        "name": str(ws_row[2]),
                        "slug": str(ws_row[1]),
                        "visibilityMode": str(ws_row[3]),
                        "lifecyclePhase": str(st_dict.get("lifecycle_phase") or "BUILD"),
                        "suggestedWorkflows": [],
                        "accessMode": "CONTRIBUTOR_ACTION_REQUIRED",
                        "finopsCostUsd": float(ws_row[5] or 0.0),
                    }
                )

    return PlatformSetupSnapshotRecord(
        first_admin_initialized=admin_rec is not None,
        first_admin_email=admin_rec.email if admin_rec is not None else None,
        first_admin_display_name=admin_rec.display_name if admin_rec is not None else None,
        org_units=list(raw_value.get("org_units") or []),
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
    ep_uuid = _deterministic_uuid(f"llm-ep:{endpoint.endpoint_key}")
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
