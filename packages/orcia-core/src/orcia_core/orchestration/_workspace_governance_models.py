"""Domain models for Story 11.1 Workspace Governance, DNA Waivers & External Rebaser."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Literal
from uuid import UUID

WorkspaceSubTab = Literal[
    "OVERVIEW",
    "DOCUMENTS_SOURCES",
    "DELIVERABLES_ARTIFACTS",
    "GLOSSARY_RULES",
    "MEMBERS_TEAM",
]
SourceAuthorityRole = Literal["REFERENCE", "ACTIVE"]
SourceAccessMode = Literal["READ_ONLY", "READ_WRITE_TARGET"]
NormOntologyLevel = Literal["1_ENTERPRISE", "2_DOMAIN", "3_TEAM", "3_WORKSPACE"]
SovereigntyTier = Literal["CLOUD_PUBLIC", "EU_SOVEREIGN", "ON_PREM_AIRGAPPED"]
WaiverStatus = Literal["ACTIVE", "INVALIDATED_SHA_DRIFT", "EXPIRED", "REVOKED"]

SOVEREIGNTY_RANK: dict[SovereigntyTier, int] = {
    "CLOUD_PUBLIC": 1,
    "EU_SOVEREIGN": 2,
    "ON_PREM_AIRGAPPED": 3,
}


@dataclass(frozen=True, slots=True)
class DnaChainNode:
    """Node in the causal DNA chain (`DIRECTIVE ➔ NORME ➔ MÉCANISME`)."""

    node_key: str
    stereotype: Literal["DIRECTIVE", "NORM", "MECHANISM"]
    level: NormOntologyLevel
    inviolable: bool = False


@dataclass(frozen=True, slots=True)
class ExceptionWaiverRecord:
    """Persisted `workspace_exception_waivers` record (`Verrou V1`, `AD-11` + `AD-7`)."""

    waiver_id: UUID
    workspace_id: UUID
    source_uri: str
    source_sha256: str
    conflict_rule_id: str
    norm_level: NormOntologyLevel
    dna_chain: tuple[DnaChainNode, ...]
    approved_by_user_id: UUID
    approved_by_role: str
    reason: str
    status: WaiverStatus
    expires_at: datetime
    created_at: datetime


@dataclass(frozen=True, slots=True)
class WorkspaceSourceSummary:
    """Qualified workspace source displayed in Tab 2 (`Documents & Sources`)."""

    source_id: UUID
    uri: str
    title: str
    authority_role: SourceAuthorityRole
    access_mode: SourceAccessMode
    freshness_status: Literal["FRESH", "STALE_WARNING", "WAIVED"]


@dataclass(frozen=True, slots=True)
class WorkspaceFiveTabsState:
    """Consolidated state for the 5 sub-tabs of `Mes Espaces` (`Story 11.1`)."""

    workspace_id: UUID
    workspace_slug: str
    tabs: tuple[WorkspaceSubTab, ...]
    default_artifact_destination_uri: str
    local_root_realpath: str | None
    sources: tuple[WorkspaceSourceSummary, ...]
    active_waivers: tuple[ExceptionWaiverRecord, ...]
    pending_glossary_candidates_count: int


@dataclass(frozen=True, slots=True)
class ResolvedArtifactDestination:
    """Result of the 4-level artifact destination cascade (`Story 11.1`)."""

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


@dataclass(frozen=True, slots=True)
class RebasedSectionChunk:
    """Section chunk evaluated by `ExternalEditRebaser` (`Verrou V2`)."""

    chunk_key: str
    section_title: str
    content_markdown: str
    status: Literal["APPROVED", "HUMAN_AMENDED_EXTERNAL"]
    locked_against_agent_overwrite: bool


@dataclass(frozen=True, slots=True)
class ExternalRebaseResult:
    """Outcome of `ExternalEditRebaser` when an external edit (`@v(N+1)`) is detected."""

    artifact_uri: str
    previous_version: int
    imported_version: int
    previous_sha256: str
    external_sha256: str
    divergence_detected: bool
    chunks: tuple[RebasedSectionChunk, ...]
    step_memlog_annotations: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class PilotWorkflowRunResult:
    """Execution result of `orcia://pack-sdlc/workflows/ticket-to-tech-spec`."""

    workflow_uri: str
    ticket_key: str
    executed_steps: tuple[str, ...]
    generator_model_family: str
    judge_model_family: str
    judge_sovereignty_tier: SovereigntyTier
    requires_human_anchor_card: bool
    destination: ResolvedArtifactDestination
    staged_transitions: tuple[str, ...]
