"""Story 11.1: Workspace 5 Sub-Tabs, 4-Level Artifact Cascade, DNA Waivers & External Rebaser."""

from __future__ import annotations

import hashlib
import os
import re
from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from typing import Literal
from uuid import UUID

from uuid_utils.compat import uuid7

from orcia_core.orchestration.errors import (
    EnterpriseDirectiveWaiverForbiddenError,
    OrthogonalJudgeSovereigntyViolationError,
    PathTraversalDeniedError,
)
from orcia_core.permissions.errors import ObserverModeReadOnlyError

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

_SOVEREIGNTY_RANK: dict[SovereigntyTier, int] = {
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
    status: Literal["ACTIVE", "INVALIDATED_SHA_DRIFT", "EXPIRED", "REVOKED"]
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


@dataclass
class WorkspaceGovernanceAndArtifactRoutingService:
    """Domain service for Story 11.1 (5 Sub-Tabs, Cascade, DNA Waivers, External Rebaser)."""

    _waivers: dict[UUID, ExceptionWaiverRecord] = field(default_factory=dict)
    _workspace_defaults: dict[UUID, tuple[str, str, str | None]] = field(default_factory=dict)
    _workspace_sources: dict[UUID, list[WorkspaceSourceSummary]] = field(default_factory=dict)

    def configure_workspace_tabs(
        self,
        *,
        workspace_id: UUID,
        workspace_slug: str,
        actor_role: str,
        default_artifact_destination_uri: str,
        local_root_realpath: str | None = None,
        sources: list[WorkspaceSourceSummary] | None = None,
        pending_glossary_candidates_count: int = 0,
    ) -> WorkspaceFiveTabsState:
        """Configure workspace sources, default destination, and return the 5 sub-tabs state."""
        if actor_role == "READ_ONLY_OBSERVER":
            raise ObserverModeReadOnlyError(
                detail_override="READ_ONLY_OBSERVER cannot mutate workspace configuration."
            )
        self._workspace_defaults[workspace_id] = (
            workspace_slug,
            default_artifact_destination_uri,
            local_root_realpath,
        )
        if sources is not None:
            self._workspace_sources[workspace_id] = list(sources)
        return self.get_workspace_five_tabs_state(
            workspace_id=workspace_id,
            workspace_slug=workspace_slug,
            pending_glossary_candidates_count=pending_glossary_candidates_count,
        )

    def get_workspace_five_tabs_state(
        self,
        *,
        workspace_id: UUID,
        workspace_slug: str = "default-ws",
        pending_glossary_candidates_count: int = 0,
    ) -> WorkspaceFiveTabsState:
        """Return the 5 sub-tabs state for `Mes Espaces`."""
        slug, default_dest, local_root = self._workspace_defaults.get(
            workspace_id,
            (
                workspace_slug,
                f"orcia://workspaces/{workspace_slug}/artifacts",
                None,
            ),
        )
        active_waivers = tuple(
            w
            for w in self._waivers.values()
            if w.workspace_id == workspace_id and w.status == "ACTIVE"
        )
        return WorkspaceFiveTabsState(
            workspace_id=workspace_id,
            workspace_slug=slug,
            tabs=(
                "OVERVIEW",
                "DOCUMENTS_SOURCES",
                "DELIVERABLES_ARTIFACTS",
                "GLOSSARY_RULES",
                "MEMBERS_TEAM",
            ),
            default_artifact_destination_uri=default_dest,
            local_root_realpath=local_root,
            sources=tuple(self._workspace_sources.get(workspace_id, [])),
            active_waivers=active_waivers,
            pending_glossary_candidates_count=min(pending_glossary_candidates_count, 15),
        )

    def register_exception_waiver(
        self,
        *,
        workspace_id: UUID,
        source_uri: str,
        source_sha256: str,
        conflict_rule_id: str,
        norm_level: NormOntologyLevel,
        dna_chain: list[DnaChainNode],
        approved_by_user_id: UUID,
        approved_by_role: str,
        reason: str,
        ttl_days: int = 30,
    ) -> ExceptionWaiverRecord:
        """Register an exception waiver governed by the causal DNA chain (`Verrou V1`)."""
        if approved_by_role == "READ_ONLY_OBSERVER":
            raise ObserverModeReadOnlyError(
                detail_override="READ_ONLY_OBSERVER cannot register exception waivers."
            )
        has_inviolable_enterprise_directive = norm_level == "1_ENTERPRISE" or any(
            node.level == "1_ENTERPRISE" and node.inviolable for node in dna_chain
        )
        if has_inviolable_enterprise_directive and approved_by_role not in {
            "PLATFORM_ADMIN",
            "SECOPS",
        }:
            raise EnterpriseDirectiveWaiverForbiddenError(
                detail_override=(
                    f"Rule '{conflict_rule_id}' operationalizes an inviolable 1_ENTERPRISE "
                    f"directive; role '{approved_by_role}' cannot waive it locally."
                )
            )

        now = datetime.now(UTC)
        waiver = ExceptionWaiverRecord(
            waiver_id=uuid7(),
            workspace_id=workspace_id,
            source_uri=source_uri,
            source_sha256=source_sha256,
            conflict_rule_id=conflict_rule_id,
            norm_level=norm_level,
            dna_chain=tuple(dna_chain),
            approved_by_user_id=approved_by_user_id,
            approved_by_role=approved_by_role,
            reason=reason.strip(),
            status="ACTIVE",
            expires_at=now + timedelta(days=max(1, ttl_days)),
            created_at=now,
        )
        self._waivers[waiver.waiver_id] = waiver
        return waiver

    def evaluate_conflict_waiver(
        self,
        *,
        workspace_id: UUID,
        source_uri: str,
        current_source_sha256: str,
        conflict_rule_id: str,
    ) -> bool:
        """Check whether an active waiver suppresses a conflict; invalidate on SHA-256 drift."""
        now = datetime.now(UTC)
        waived = False
        for waiver_id, waiver in list(self._waivers.items()):
            if (
                waiver.workspace_id != workspace_id
                or waiver.source_uri != source_uri
                or waiver.conflict_rule_id != conflict_rule_id
                or waiver.status != "ACTIVE"
            ):
                continue
            if waiver.expires_at <= now:
                self._waivers[waiver_id] = replace(waiver, status="EXPIRED")
                continue
            if waiver.source_sha256 != current_source_sha256:
                self._waivers[waiver_id] = replace(waiver, status="INVALIDATED_SHA_DRIFT")
                continue
            waived = True
        return waived

    def resolve_artifact_destination(
        self,
        *,
        workspace_id: UUID,
        workspace_slug: str,
        artifact_type: str,
        artifact_slug: str,
        version: int,
        content_bytes: bytes,
        run_override_uri: str | None = None,
        workflow_step_target_uri: str | None = None,
        workspace_default_uri: str | None = None,
        local_root_realpath: str | None = None,
    ) -> ResolvedArtifactDestination:
        """Resolve the 4-level artifact destination cascade with `local://` path confinement."""
        sha256_hex = hashlib.sha256(content_bytes).hexdigest()
        cas_storage_path = f"cas/{sha256_hex}"
        canonical_alias = (
            f"orcia://workspaces/{workspace_slug}/artifacts/"
            f"{artifact_type}/{artifact_slug}@v{version}"
        )

        if run_override_uri:
            selected_level: Literal[
                "1_RUN_OVERRIDE",
                "2_WORKFLOW_STEP_TARGET",
                "3_WORKSPACE_DEFAULT",
                "4_ORCIA_VAULT_FALLBACK",
            ] = "1_RUN_OVERRIDE"
            raw_uri = run_override_uri
        elif workflow_step_target_uri:
            selected_level = "2_WORKFLOW_STEP_TARGET"
            raw_uri = workflow_step_target_uri
        elif workspace_default_uri or workspace_id in self._workspace_defaults:
            selected_level = "3_WORKSPACE_DEFAULT"
            raw_uri = workspace_default_uri or self._workspace_defaults[workspace_id][1]
        else:
            selected_level = "4_ORCIA_VAULT_FALLBACK"
            raw_uri = canonical_alias

        if raw_uri.startswith("local://"):
            effective_root = (
                local_root_realpath
                or (self._workspace_defaults.get(workspace_id, ("", "", None))[2])
            )
            self._enforce_local_realpath_confinement(
                local_uri=raw_uri,
                allowed_root=effective_root or "/tmp/orcia-workspaces",
            )

        staged = "://" in raw_uri and not raw_uri.startswith("orcia://")
        return ResolvedArtifactDestination(
            selected_level=selected_level,
            resolved_uri=raw_uri,
            cas_storage_path=cas_storage_path,
            canonical_alias_uri=canonical_alias,
            staged_for_gate_publication=staged,
        )

    def _enforce_local_realpath_confinement(
        self,
        *,
        local_uri: str,
        allowed_root: str,
    ) -> str:
        rel_part = local_uri.removeprefix("local://").lstrip("/")
        root_real = os.path.realpath(allowed_root)
        candidate_real = os.path.realpath(os.path.join(root_real, rel_part))
        if candidate_real != root_real and not candidate_real.startswith(root_real + os.sep):
            raise PathTraversalDeniedError(
                detail_override=(f"Destination '{local_uri}' escapes workspace root '{root_real}'.")
            )
        return candidate_real

    def rebase_external_artifact_edits(
        self,
        *,
        artifact_uri: str,
        current_version: int,
        orcia_markdown: str,
        external_markdown: str,
        step_memlog_entries: list[str],
    ) -> ExternalRebaseResult:
        """Detect external `SHA-256` divergence and lock human-amended sections (`Verrou V2`)."""
        prev_sha = hashlib.sha256(orcia_markdown.encode("utf-8")).hexdigest()
        ext_sha = hashlib.sha256(external_markdown.encode("utf-8")).hexdigest()
        orcia_sections = self._split_markdown_sections(orcia_markdown)
        ext_sections = self._split_markdown_sections(external_markdown)

        if prev_sha == ext_sha:
            chunks = tuple(
                RebasedSectionChunk(
                    chunk_key=key,
                    section_title=title,
                    content_markdown=body,
                    status="APPROVED",
                    locked_against_agent_overwrite=False,
                )
                for key, (title, body) in orcia_sections.items()
            )
            return ExternalRebaseResult(
                artifact_uri=artifact_uri,
                previous_version=current_version,
                imported_version=current_version,
                previous_sha256=prev_sha,
                external_sha256=ext_sha,
                divergence_detected=False,
                chunks=chunks,
                step_memlog_annotations=tuple(step_memlog_entries),
            )

        rebased_chunks: list[RebasedSectionChunk] = []
        amended_titles: list[str] = []
        for key, (ext_title, ext_body) in ext_sections.items():
            orig = orcia_sections.get(key)
            if orig is None or orig[1].strip() != ext_body.strip():
                rebased_chunks.append(
                    RebasedSectionChunk(
                        chunk_key=key,
                        section_title=ext_title,
                        content_markdown=ext_body,
                        status="HUMAN_AMENDED_EXTERNAL",
                        locked_against_agent_overwrite=True,
                    )
                )
                amended_titles.append(ext_title)
            else:
                rebased_chunks.append(
                    RebasedSectionChunk(
                        chunk_key=key,
                        section_title=ext_title,
                        content_markdown=ext_body,
                        status="APPROVED",
                        locked_against_agent_overwrite=False,
                    )
                )

        annotated_memlog = list(step_memlog_entries)
        for idx, entry in enumerate(annotated_memlog):
            if any(title.lower() in entry.lower() for title in amended_titles):
                annotated_memlog[idx] = f"[SUPERSEDED_BY_HUMAN_COMMIT] {entry}"
        if amended_titles and not any(
            "[SUPERSEDED_BY_HUMAN_COMMIT]" in e for e in annotated_memlog
        ):
            annotated_memlog.append(
                f"[SUPERSEDED_BY_HUMAN_COMMIT] External commit amended sections: "
                f"{', '.join(amended_titles)}"
            )

        return ExternalRebaseResult(
            artifact_uri=artifact_uri,
            previous_version=current_version,
            imported_version=current_version + 1,
            previous_sha256=prev_sha,
            external_sha256=ext_sha,
            divergence_detected=True,
            chunks=tuple(rebased_chunks),
            step_memlog_annotations=tuple(annotated_memlog),
        )

    def run_pilot_ticket_to_tech_spec_workflow(
        self,
        *,
        workspace_id: UUID,
        workspace_slug: str,
        ticket_key: str,
        ticket_summary: str,
        workspace_sovereignty_tier: SovereigntyTier,
        generator_model_family: str,
        judge_model_family: str,
        judge_sovereignty_tier: SovereigntyTier,
        run_override_uri: str | None = None,
    ) -> PilotWorkflowRunResult:
        """Execute pilot workflow `ticket-to-tech-spec` (`Verrou V3`)."""
        judge_rank = _SOVEREIGNTY_RANK[judge_sovereignty_tier]
        ws_rank = _SOVEREIGNTY_RANK[workspace_sovereignty_tier]
        if judge_rank < ws_rank:
            raise OrthogonalJudgeSovereigntyViolationError(
                detail_override=(
                    f"Judge tier '{judge_sovereignty_tier}' is less sovereign than workspace tier "
                    f"'{workspace_sovereignty_tier}'."
                )
            )
        requires_human_anchor = generator_model_family.strip().lower() == (
            judge_model_family.strip().lower()
        )
        spec_markdown = (
            f"# Spécification Technique — {ticket_key}\n\n"
            f"## 1. Contexte & Périmètre\n{ticket_summary}\n\n"
            "## 2. Contrats d'Interface & Impacts\nValidation via Gate adaptative.\n"
        )
        destination = self.resolve_artifact_destination(
            workspace_id=workspace_id,
            workspace_slug=workspace_slug,
            artifact_type="tech-spec",
            artifact_slug=ticket_key.lower(),
            version=1,
            content_bytes=spec_markdown.encode("utf-8"),
            run_override_uri=run_override_uri,
        )
        return PilotWorkflowRunResult(
            workflow_uri="orcia://pack-sdlc/workflows/ticket-to-tech-spec",
            ticket_key=ticket_key,
            executed_steps=(
                "1_extract_ticket_and_repo_context",
                "2_draft_tech_spec_and_impact_tree",
                "3_adaptive_human_gate_and_staged_publish",
            ),
            generator_model_family=generator_model_family,
            judge_model_family=judge_model_family,
            judge_sovereignty_tier=judge_sovereignty_tier,
            requires_human_anchor_card=requires_human_anchor,
            destination=destination,
            staged_transitions=(
                f"STAGE_PUBLISH:{destination.resolved_uri}",
                f"STAGE_TICKET_COMMENT:{ticket_key}",
            ),
        )

    @staticmethod
    def _split_markdown_sections(markdown_text: str) -> dict[str, tuple[str, str]]:
        sections: dict[str, tuple[str, str]] = {}
        current_title = "Introduction"
        current_lines: list[str] = []
        for line in markdown_text.splitlines():
            if line.startswith("## ") or line.startswith("# "):
                if current_lines:
                    slug = re.sub(r"[^a-z0-9]+", "-", current_title.lower()).strip("-") or "sec"
                    sections[slug] = (current_title, "\n".join(current_lines).strip())
                current_title = line.lstrip("#").strip()
                current_lines = [line]
            else:
                current_lines.append(line)
        if current_lines:
            slug = re.sub(r"[^a-z0-9]+", "-", current_title.lower()).strip("-") or "sec"
            sections[slug] = (current_title, "\n".join(current_lines).strip())
        return sections
