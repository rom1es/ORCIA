"""HTTP/OpenAPI 3.1 transport schemas for Epic 11 Story 11.1 (`Mes Espaces`, Waivers, Rebaser)."""

from __future__ import annotations

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class DnaChainNodeSchema(BaseModel):
    """Transport schema for a causal DNA chain node (`DIRECTIVE ➔ NORME ➔ MÉCANISME`)."""

    model_config = ConfigDict(extra="forbid")

    node_key: str = Field(..., min_length=1, max_length=128)
    stereotype: Literal["DIRECTIVE", "NORM", "MECHANISM"]
    level: Literal["1_ENTERPRISE", "2_DOMAIN", "3_TEAM", "3_WORKSPACE"]
    inviolable: bool = False


class WorkspaceSourceSummarySchema(BaseModel):
    """Transport schema for a qualified workspace source in Tab 2 (`Documents & Sources`)."""

    model_config = ConfigDict(extra="forbid")

    source_id: UUID
    uri: str = Field(..., min_length=1, max_length=512)
    title: str = Field(..., min_length=1, max_length=255)
    authority_role: Literal["REFERENCE", "ACTIVE"]
    access_mode: Literal["READ_ONLY", "READ_WRITE_TARGET"]
    freshness_status: Literal["FRESH", "STALE_WARNING", "WAIVED"] = "FRESH"


class ConfigureWorkspaceTabsRequest(BaseModel):
    """Request to configure a workspace's 5 sub-tabs, sources, and default destination."""

    model_config = ConfigDict(extra="forbid")

    workspace_slug: str = Field(..., min_length=1, max_length=128)
    default_artifact_destination_uri: str = Field(..., min_length=1, max_length=512)
    local_root_realpath: str | None = None
    sources: list[WorkspaceSourceSummarySchema] = Field(default_factory=list)
    pending_glossary_candidates_count: int = Field(default=0, ge=0, le=100)


class ExceptionWaiverResponse(BaseModel):
    """Response representing a persisted `workspace_exception_waivers` record (`Verrou V1`)."""

    model_config = ConfigDict(extra="forbid")

    waiver_id: UUID
    workspace_id: UUID
    source_uri: str
    source_sha256: str
    conflict_rule_id: str
    norm_level: Literal["1_ENTERPRISE", "2_DOMAIN", "3_TEAM", "3_WORKSPACE"]
    dna_chain: list[DnaChainNodeSchema]
    approved_by_user_id: UUID
    approved_by_role: str
    reason: str
    status: Literal["ACTIVE", "INVALIDATED_SHA_DRIFT", "EXPIRED", "REVOKED"]
    expires_at: datetime
    created_at: datetime


class WorkspaceFiveTabsStateResponse(BaseModel):
    """Response for the 5 sub-tabs of `Mes Espaces` (`Story 11.1`)."""

    model_config = ConfigDict(extra="forbid")

    workspace_id: UUID
    workspace_slug: str
    tabs: list[
        Literal[
            "OVERVIEW",
            "DOCUMENTS_SOURCES",
            "DELIVERABLES_ARTIFACTS",
            "GLOSSARY_RULES",
            "MEMBERS_TEAM",
        ]
    ]
    default_artifact_destination_uri: str
    local_root_realpath: str | None
    sources: list[WorkspaceSourceSummarySchema]
    active_waivers: list[ExceptionWaiverResponse]
    pending_glossary_candidates_count: int


class RegisterExceptionWaiverRequest(BaseModel):
    """Request to register an exception waiver governed by the causal DNA chain (`Verrou V1`)."""

    model_config = ConfigDict(extra="forbid")

    source_uri: str = Field(..., min_length=1, max_length=512)
    source_sha256: str = Field(..., min_length=8, max_length=64)
    conflict_rule_id: str = Field(..., min_length=1, max_length=128)
    norm_level: Literal["1_ENTERPRISE", "2_DOMAIN", "3_TEAM", "3_WORKSPACE"] = "3_WORKSPACE"
    dna_chain: list[DnaChainNodeSchema] = Field(default_factory=list)
    reason: str = Field(..., min_length=3, max_length=1000)
    ttl_days: int = Field(default=30, ge=1, le=365)


class ResolveArtifactDestinationRequest(BaseModel):
    """Request to resolve the 4-level artifact destination cascade (`Story 11.1`)."""

    model_config = ConfigDict(extra="forbid")

    workspace_slug: str = Field(..., min_length=1, max_length=128)
    artifact_type: str = Field(..., min_length=1, max_length=64)
    artifact_slug: str = Field(..., min_length=1, max_length=128)
    version: int = Field(default=1, ge=1)
    content_markdown: str = Field(default="")
    run_override_uri: str | None = None
    workflow_step_target_uri: str | None = None
    workspace_default_uri: str | None = None
    local_root_realpath: str | None = None


class ResolvedArtifactDestinationResponse(BaseModel):
    """Response for the 4-level artifact destination cascade."""

    model_config = ConfigDict(extra="forbid")

    selected_level: Literal[
        "1_RUN_OVERRIDE",
        "2_WORKFLOW_STEP_TARGET",
        "3_WORKSPACE_DEFAULT",
        "4_ORCIA_VAULT_FALLBACK",
    ]
    resolved_uri: str
    cas_storage_path: str
    canonical_alias_uri: str
    staged_for_gate_publication: bool


class RebaseExternalArtifactEditsRequest(BaseModel):
    """Request to run `ExternalEditRebaser` on an externally edited artifact (`Verrou V2`)."""

    model_config = ConfigDict(extra="forbid")

    artifact_uri: str = Field(..., min_length=1, max_length=512)
    current_version: int = Field(default=1, ge=1)
    orcia_markdown: str
    external_markdown: str
    step_memlog_entries: list[str] = Field(default_factory=list)


class RebasedSectionChunkSchema(BaseModel):
    """Section chunk evaluated by `ExternalEditRebaser`."""

    model_config = ConfigDict(extra="forbid")

    chunk_key: str
    section_title: str
    content_markdown: str
    status: Literal["APPROVED", "HUMAN_AMENDED_EXTERNAL"]
    locked_against_agent_overwrite: bool


class ExternalRebaseResponse(BaseModel):
    """Response from `ExternalEditRebaser` (`Verrou V2`)."""

    model_config = ConfigDict(extra="forbid")

    artifact_uri: str
    previous_version: int
    imported_version: int
    previous_sha256: str
    external_sha256: str
    divergence_detected: bool
    chunks: list[RebasedSectionChunkSchema]
    step_memlog_annotations: list[str]


class RunPilotTicketToTechSpecRequest(BaseModel):
    """Request to execute `orcia://pack-sdlc/workflows/ticket-to-tech-spec` (`Verrou V3`)."""

    model_config = ConfigDict(extra="forbid")

    workspace_slug: str = Field(..., min_length=1, max_length=128)
    ticket_key: str = Field(..., min_length=2, max_length=64)
    ticket_summary: str = Field(..., min_length=3, max_length=2000)
    workspace_sovereignty_tier: Literal["CLOUD_PUBLIC", "EU_SOVEREIGN", "ON_PREM_AIRGAPPED"] = (
        "EU_SOVEREIGN"
    )
    generator_model_family: str = Field(default="claude-4.6")
    judge_model_family: str = Field(default="mistral-large-3")
    judge_sovereignty_tier: Literal["CLOUD_PUBLIC", "EU_SOVEREIGN", "ON_PREM_AIRGAPPED"] = (
        "EU_SOVEREIGN"
    )
    run_override_uri: str | None = None


class PilotWorkflowRunResponse(BaseModel):
    """Response for the 3-step pilot workflow `ticket-to-tech-spec`."""

    model_config = ConfigDict(extra="forbid")

    workflow_uri: str
    ticket_key: str
    executed_steps: list[str]
    generator_model_family: str
    judge_model_family: str
    judge_sovereignty_tier: Literal["CLOUD_PUBLIC", "EU_SOVEREIGN", "ON_PREM_AIRGAPPED"]
    requires_human_anchor_card: bool
    destination: ResolvedArtifactDestinationResponse
    staged_transitions: list[str]
