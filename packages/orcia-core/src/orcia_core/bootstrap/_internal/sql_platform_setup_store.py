"""PostgreSQL 18 Persistence Adapter for Platform Setup State (`Epics 8..12` Vertical Wiring).

Atomically persists and reloads the full platform setup state (`orgUnits`, `rbacGrants`,
`llmTiers`, `workspaces`, `datasources`, `packs`, `workflows`, `runs`, `catalogItems`,
`ontologyConcepts`, `auditEvents`) inside `platform_settings` while synchronizing relational
tables (`org_units`, `workspaces`, `llm_model_endpoints`) on PostgreSQL 18.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_core.bootstrap._internal.setup_snapshot_sanitizer import (
    strip_snapshot_credentials,
)
from orcia_core.bootstrap._internal.sql_first_user_guard import (
    get_first_platform_admin_from_postgres18,
)
from orcia_core.bootstrap._internal.sql_platform_setup_models import (
    GLOBAL_SETUP_SCOPE_ID,
    PLATFORM_SETUP_SETTING_KEY,
    PlatformSetupSnapshotRecord,
    persist_progressive_llm_endpoint_to_postgres18,
)
from orcia_core.bootstrap._internal.sql_platform_setup_reconcilers import (
    reconcile_org_units_on_load,
    reconcile_workspaces_on_load,
)
from orcia_core.bootstrap._internal.sql_platform_setup_relational_sync import (
    ROOT_ORG_UNIT_ID,
    deterministic_setup_uuid,
    normalize_setup_slug,
    sync_relational_tables_on_postgres18,
)
from orcia_kernel.ids import new_uuid7_str

# Re-exported aliases for internal compatibility
_deterministic_uuid = deterministic_setup_uuid
_normalize_slug = normalize_setup_slug
_reconcile_org_units_on_load = reconcile_org_units_on_load
_reconcile_workspaces_on_load = reconcile_workspaces_on_load


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
        llm_tiers=strip_snapshot_credentials(list(snapshot.llm_tiers)),
        workspaces=list(snapshot.workspaces),
        datasources=strip_snapshot_credentials(list(snapshot.datasources)),
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
            mapping_rows = (
                await conn.execute(
                    sa.text(
                        """
                        SELECT inference_tier, effort, provider_slug, model_family, model_name,
                               fallback_model_name, endpoint_uri, auth_mode,
                               (
                                   encrypted_api_key IS NOT NULL AND encrypted_api_key <> ''
                               ) AS has_key
                        FROM workspace_llm_tier_mappings
                        WHERE is_active = TRUE
                        ORDER BY created_at ASC
                        """
                    )
                )
            ).fetchall()
            for mp in mapping_rows:
                llm_tiers.append(
                    {
                        "tier": str(mp[0] or "medium"),
                        "defaultEffort": str(mp[1] or "balanced"),
                        "provider": str(mp[2] or mp[3] or ""),
                        "modelFamily": str(mp[3] or mp[2] or ""),
                        "primaryModel": str(mp[4] or ""),
                        "secondaryModel": str(mp[5] or mp[4] or ""),
                        "endpointUrl": str(mp[6] or ""),
                        "authMode": str(mp[7] or "api_key"),
                        "apiKeyConfigured": bool(mp[8]),
                    }
                )
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
        llm_tiers=strip_snapshot_credentials(llm_tiers),
        workspaces=workspaces,
        datasources=strip_snapshot_credentials(list(raw_value.get("datasources") or [])),
        packs=list(raw_value.get("packs") or []),
        workflows=list(raw_value.get("workflows") or []),
        runs=list(raw_value.get("runs") or []),
        catalog_items=list(raw_value.get("catalog_items") or []),
        ontology_concepts=list(raw_value.get("ontology_concepts") or []),
        audit_events=list(raw_value.get("audit_events") or []),
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
