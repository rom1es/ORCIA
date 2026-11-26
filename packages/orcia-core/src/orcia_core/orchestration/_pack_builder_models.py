"""Dataclasses, error classes & PG18 persistence helper for `orcia-pack-builder` (`Story 11.4`)."""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, field
from typing import Any, Literal
from uuid import UUID

import sqlalchemy as sa
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from uuid_utils import uuid7

from orcia_core.orchestration._studio_and_packs_locales import PACK_BUILDER_AGENTS_META
from orcia_kernel.errors import OrciaDomainError

PackCertificationTier = Literal["TIER_1B_STARLARK", "TIER_2_CONTAINER"]
PromotableAssetKind = Literal["AGENT", "WORKFLOW", "NORM", "STARLARK_MECHANISM"]

_PACK_SLUG_RE = re.compile(r"^[a-z][a-z0-9-]{1,40}$")
_FORBIDDEN_CORE_SLUGS = frozenset({"kernel", "core", "api", "worker"})
_SCRUB_PATTERNS: tuple[tuple[re.Pattern[str], str], ...] = (
    (re.compile(r"local://[^\s\"']+"), "pack://artifacts/default"),
    (re.compile(r"(?:secret|vault|kms)://[^\s\"']+"), "secret://pack-placeholder"),
    (re.compile(r"\bpat_mcp_[A-Za-z0-9_-]+"), "[REDACTED_MCP_PAT]"),
    (re.compile(r"\bsk-[A-Za-z0-9_-]{12,}"), "[REDACTED_API_KEY]"),
    (
        re.compile(r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b", re.I),
        "{{WORKSPACE_SCOPED_UUID}}",
    ),
)


class PackBuilderValidationError(OrciaDomainError):
    """Raised when `pack.yaml`, `pack_slug`, or tool certification fails (`HTTP 422`)."""

    error_code = "ERR_PACK_BUILDER_VALIDATION_FAILED"
    http_status, type_slug = 422, "pack-builder-validation-failed"

    def __init__(
        self,
        detail: str | None = None,
        *,
        error_code: str = "ERR_PACK_BUILDER_VALIDATION_FAILED",
        detail_code: str | None = None,
        detail_params: dict[str, object] | None = None,
    ) -> None:
        self.error_code = error_code
        super().__init__(
            detail_override=detail,
            detail_code=detail_code or (error_code if detail is None else None),
            detail_params=detail_params,
        )


@dataclass(frozen=True, slots=True)
class PackBuilderAgentSpec:
    """Specialized agent embedded in `packages/orcia-pack-builder`."""

    slug: str
    handle: str
    role_fr: str
    role_en: str


@dataclass(frozen=True, slots=True)
class DnaChainPackSeedSpec:
    """Causal DNA chain (`DIRECTIVE -> NORM -> MECHANISM`) declared in a Business Pack."""

    directive_code: str
    directive_title: str
    norm_code: str
    norm_title: str
    mechanism_code: str
    rule_id: str
    starlark_source: str
    passing_test_payload: dict[str, Any] = field(default_factory=dict)
    failing_test_payload: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True, slots=True)
class CreatedBusinessPackResult:
    """Result of Process 1 (`create-business-pack`)."""

    pack_id: str
    pack_slug: str
    version: str
    title: str
    human_anchor_intent: str
    target_directory: str
    generated_files: dict[str, str]
    manifest_validation_elapsed_ms: float
    starlark_rules_certified_count: int
    max_starlark_elapsed_ms: float
    kernel_or_core_touched: bool


@dataclass(frozen=True, slots=True)
class WhatIfWorkspaceImpactItem:
    """Per-workspace impact entry produced by Process 2 (`evolve-business-pack`)."""

    workspace_key: str
    impacted_workflows: tuple[str, ...]
    breaking_norms: tuple[str, ...]
    active_runs_count: int
    run_locks_untouched: bool


@dataclass(frozen=True, slots=True)
class PackEvolutionWhatIfReport:
    """Result of Process 2 (`evolve-business-pack` *What-If* simulation)."""

    pack_slug: str
    previous_version: str
    target_version: str
    impacted_workspaces_count: int
    impacted_workflows_count: int
    breaking_changes_detected: bool
    active_run_locks_preserved: bool
    untouched_run_lock_ids: tuple[str, ...]
    workspace_impacts: tuple[WhatIfWorkspaceImpactItem, ...]


@dataclass(frozen=True, slots=True)
class PackToolCertificationReport:
    """Result of Process 3 (`certify-pack-tool`)."""

    tool_slug: str
    sandbox_tier: PackCertificationTier
    certified: bool
    elapsed_ms: float
    passing_vector_ok: bool
    failing_vector_rejected_ok: bool
    network_isolated: bool
    certificate_sha256: str
    diagnostics: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class WorkspaceToPackPromotionResult:
    """Result of Process 4 (`export-from-workspace-to-pack`)."""

    source_workspace_key: str
    target_pack_slug: str
    target_pack_version: str
    asset_kind: PromotableAssetKind
    asset_slug: str
    promoted_uri: str
    scrubbed_references_count: int
    sanitized_payload: dict[str, Any]


PACK_BUILDER_AGENTS: tuple[PackBuilderAgentSpec, ...] = tuple(
    PackBuilderAgentSpec(slug=m.slug, handle=m.handle_fr, role_fr=m.role_fr, role_en=m.role_en)
    for m in PACK_BUILDER_AGENTS_META
)


async def persist_pack_and_audit_pg(
    session_factory: async_sessionmaker[AsyncSession],
    pack: CreatedBusinessPackResult,
    *,
    actor_id: str,
) -> None:
    """Persist generated Business Pack catalog item and Outbox audit event in PG18."""
    manifest_bytes = pack.generated_files[f"{pack.target_directory}/pack.yaml"].encode("utf-8")
    content_hash = hashlib.sha256(manifest_bytes).hexdigest()
    metadata_json = json.dumps(
        {
            "pack_slug": pack.pack_slug,
            "title": pack.title,
            "human_anchor_intent": pack.human_anchor_intent,
            "target_directory": pack.target_directory,
            "starlark_rules_certified_count": pack.starlark_rules_certified_count,
        }
    )
    audit_payload = json.dumps(
        {
            "actor_id": actor_id,
            "pack_id": pack.pack_id,
            "version": pack.version,
            "starlark_rules_certified_count": pack.starlark_rules_certified_count,
            "kernel_or_core_touched": pack.kernel_or_core_touched,
        }
    )
    root_org_id = UUID("0192c4e0-0000-7000-8000-000000000001")

    async with session_factory() as session, session.begin():
        await session.execute(
            sa.text(
                """
                INSERT INTO org_units (id, slug, name, unit_type, parent_id)
                VALUES (:id, 'orcia-root-org', 'ORCIA Root Org', 'ENTERPRISE', NULL)
                ON CONFLICT (id) DO NOTHING
                """
            ),
            {"id": root_org_id},
        )
        await session.execute(
            sa.text(
                """
                INSERT INTO catalog_items (
                    id, resource_id, uri, title, description,
                    resource_type, source_format, version, sha256, cas_key,
                    visibility_scope, owner_org_unit_id, owner_workspace_id,
                    item_type, metadata_jsonb
                ) VALUES (
                    :id, :resource_id, :uri, :title, :description,
                    'template', 'BMAD_PACK', :version, :sha256, :cas_key,
                    'PUBLISHED_ORG', :owner_org_unit_id, NULL,
                    'BUSINESS_PACK', CAST(:metadata_jsonb AS jsonb)
                )
                ON CONFLICT (resource_id) WHERE pack_bundle_id IS NULL DO UPDATE
                SET version = EXCLUDED.version,
                    sha256 = EXCLUDED.sha256,
                    cas_key = EXCLUDED.cas_key,
                    metadata_jsonb = EXCLUDED.metadata_jsonb
                """
            ),
            {
                "id": UUID(str(uuid7())),
                "resource_id": f"pack-{pack.pack_slug}",
                "uri": pack.pack_id,
                "title": pack.title,
                "description": pack.human_anchor_intent,
                "version": pack.version,
                "sha256": content_hash,
                "cas_key": f"cas/{content_hash}",
                "owner_org_unit_id": root_org_id,
                "metadata_jsonb": metadata_json,
            },
        )
        await session.execute(
            sa.text(
                """
                INSERT INTO domain_events_outbox (
                    event_id, event_type, aggregate_type, aggregate_id,
                    run_id, workspace_id, payload_jsonb, trace_id, status
                ) VALUES (
                    :event_id, 'ArtifactProduced', 'BusinessPack', :aggregate_id,
                    NULL, NULL, CAST(:payload AS jsonb), 'trace-pack-builder-11-4', 'PENDING'
                )
                """
            ),
            {
                "event_id": UUID(str(uuid7())),
                "aggregate_id": pack.pack_id,
                "payload": audit_payload,
            },
        )


__all__ = [
    "CreatedBusinessPackResult",
    "DnaChainPackSeedSpec",
    "PACK_BUILDER_AGENTS",
    "PackBuilderAgentSpec",
    "PackBuilderValidationError",
    "PackCertificationTier",
    "PackEvolutionWhatIfReport",
    "PackToolCertificationReport",
    "PromotableAssetKind",
    "WhatIfWorkspaceImpactItem",
    "WorkspaceToPackPromotionResult",
    "_FORBIDDEN_CORE_SLUGS",
    "_PACK_SLUG_RE",
    "_SCRUB_PATTERNS",
    "persist_pack_and_audit_pg",
]
