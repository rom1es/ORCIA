"""Snapshot Record & Progressive LLM Persistence Helpers for PG18 Setup Store."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_core.bootstrap._internal.setup_snapshot_sanitizer import (
    strip_snapshot_credentials,
)
from orcia_core.bootstrap._internal.sql_platform_setup_relational_sync import (
    deterministic_setup_uuid,
)
from orcia_core.bootstrap.models import LlmModelEndpoint

GLOBAL_SETUP_SCOPE_ID = UUID("0192c4e0-0000-7000-8000-000000000000")
PLATFORM_SETUP_SETTING_KEY = "platform_setup_state_v1"


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
            "llm_tiers": strip_snapshot_credentials(list(self.llm_tiers)),
            "workspaces": list(self.workspaces),
            "datasources": strip_snapshot_credentials(list(self.datasources)),
            "packs": list(self.packs),
            "workflows": list(self.workflows),
            "runs": list(self.runs),
            "catalog_items": list(self.catalog_items),
            "ontology_concepts": list(self.ontology_concepts),
            "audit_events": list(self.audit_events),
        }


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
