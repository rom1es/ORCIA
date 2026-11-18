"""Story 11.1: Workspace 5 Sub-Tabs, 4-Level Artifact Cascade, DNA Waivers & External Rebaser."""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from datetime import UTC, datetime, timedelta
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from uuid_utils.compat import uuid7

from orcia_core.orchestration._internal.sql_workspace_waivers import (
    list_workspace_waivers_sql,
    update_workspace_waiver_status_sql,
    upsert_workspace_waiver_sql,
)
from orcia_core.orchestration._workspace_governance_models import (
    DnaChainNode,
    ExceptionWaiverRecord,
    ExternalRebaseResult,
    NormOntologyLevel,
    PilotWorkflowRunResult,
    RebasedSectionChunk,
    ResolvedArtifactDestination,
    SourceAccessMode,
    SourceAuthorityRole,
    SovereigntyTier,
    WorkspaceFiveTabsState,
    WorkspaceSourceSummary,
    WorkspaceSubTab,
)
from orcia_core.orchestration._workspace_rebase_helpers import (
    build_pilot_ticket_to_tech_spec_result,
    compute_external_rebase_result,
    resolve_artifact_destination_cascade,
)
from orcia_core.orchestration.errors import EnterpriseDirectiveWaiverForbiddenError
from orcia_core.permissions.errors import ObserverModeReadOnlyError


@dataclass
class WorkspaceGovernanceAndArtifactRoutingService:
    """Domain service for Story 11.1 (5 Sub-Tabs, Cascade, DNA Waivers, External Rebaser)."""

    session_factory: async_sessionmaker[AsyncSession] | None = None
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
        waivers_override: tuple[ExceptionWaiverRecord, ...] | None = None,
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
        active_waivers = (
            waivers_override
            if waivers_override is not None
            else tuple(
                w
                for w in self._waivers.values()
                if w.workspace_id == workspace_id and w.status == "ACTIVE"
            )
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

    async def get_workspace_five_tabs_state_async(
        self,
        *,
        workspace_id: UUID,
        workspace_slug: str = "default-ws",
        pending_glossary_candidates_count: int = 0,
    ) -> WorkspaceFiveTabsState:
        """Return the 5 sub-tabs state hydrated with PG18 `workspace_exception_waivers`."""
        waivers = await self.list_exception_waivers_async(
            workspace_id=workspace_id,
            active_only=True,
        )
        return self.get_workspace_five_tabs_state(
            workspace_id=workspace_id,
            workspace_slug=workspace_slug,
            pending_glossary_candidates_count=pending_glossary_candidates_count,
            waivers_override=tuple(waivers),
        )

    async def list_exception_waivers_async(
        self,
        *,
        workspace_id: UUID,
        active_only: bool = False,
    ) -> list[ExceptionWaiverRecord]:
        """List exception waivers from PostgreSQL 18 (or memory fallback in unit tests)."""
        if self.session_factory is not None:
            rows = await list_workspace_waivers_sql(
                self.session_factory,
                workspace_id=workspace_id,
                active_only=active_only,
            )
            for item in rows:
                self._waivers[item.waiver_id] = item
            return rows
        return [
            w
            for w in self._waivers.values()
            if w.workspace_id == workspace_id and (not active_only or w.status == "ACTIVE")
        ]

    def _build_validated_waiver(
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
        return ExceptionWaiverRecord(
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
        waiver = self._build_validated_waiver(
            workspace_id=workspace_id,
            source_uri=source_uri,
            source_sha256=source_sha256,
            conflict_rule_id=conflict_rule_id,
            norm_level=norm_level,
            dna_chain=dna_chain,
            approved_by_user_id=approved_by_user_id,
            approved_by_role=approved_by_role,
            reason=reason,
            ttl_days=ttl_days,
        )
        self._waivers[waiver.waiver_id] = waiver
        return waiver

    async def register_exception_waiver_async(
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
        approved_by_email: str | None = None,
    ) -> ExceptionWaiverRecord:
        """Validate and persist an exception waiver to PostgreSQL 18 (`Verrou V1`)."""
        waiver = self._build_validated_waiver(
            workspace_id=workspace_id,
            source_uri=source_uri,
            source_sha256=source_sha256,
            conflict_rule_id=conflict_rule_id,
            norm_level=norm_level,
            dna_chain=dna_chain,
            approved_by_user_id=approved_by_user_id,
            approved_by_role=approved_by_role,
            reason=reason,
            ttl_days=ttl_days,
        )
        if self.session_factory is not None:
            waiver = await upsert_workspace_waiver_sql(
                self.session_factory,
                waiver,
                approved_by_email=approved_by_email,
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

    async def evaluate_conflict_waiver_async(
        self,
        *,
        workspace_id: UUID,
        source_uri: str,
        current_source_sha256: str,
        conflict_rule_id: str,
    ) -> bool:
        """Evaluate conflict waivers against PG18 and persist status invalidations."""
        waivers = await self.list_exception_waivers_async(
            workspace_id=workspace_id,
            active_only=True,
        )
        now = datetime.now(UTC)
        waived = False
        for waiver in waivers:
            if (
                waiver.source_uri != source_uri
                or waiver.conflict_rule_id != conflict_rule_id
                or waiver.status != "ACTIVE"
            ):
                continue
            if waiver.expires_at <= now:
                self._waivers[waiver.waiver_id] = replace(waiver, status="EXPIRED")
                if self.session_factory is not None:
                    await update_workspace_waiver_status_sql(
                        self.session_factory, waiver_id=waiver.waiver_id, status="EXPIRED"
                    )
                continue
            if waiver.source_sha256 != current_source_sha256:
                self._waivers[waiver.waiver_id] = replace(waiver, status="INVALIDATED_SHA_DRIFT")
                if self.session_factory is not None:
                    await update_workspace_waiver_status_sql(
                        self.session_factory,
                        waiver_id=waiver.waiver_id,
                        status="INVALIDATED_SHA_DRIFT",
                    )
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
        return resolve_artifact_destination_cascade(
            workspace_slug=workspace_slug,
            artifact_type=artifact_type,
            artifact_slug=artifact_slug,
            version=version,
            content_bytes=content_bytes,
            default_entry=self._workspace_defaults.get(workspace_id),
            run_override_uri=run_override_uri,
            workflow_step_target_uri=workflow_step_target_uri,
            workspace_default_uri=workspace_default_uri,
            local_root_realpath=local_root_realpath,
        )

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
        return compute_external_rebase_result(
            artifact_uri=artifact_uri,
            current_version=current_version,
            orcia_markdown=orcia_markdown,
            external_markdown=external_markdown,
            step_memlog_entries=step_memlog_entries,
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
        return build_pilot_ticket_to_tech_spec_result(
            workspace_id=workspace_id,
            workspace_slug=workspace_slug,
            ticket_key=ticket_key,
            ticket_summary=ticket_summary,
            workspace_sovereignty_tier=workspace_sovereignty_tier,
            generator_model_family=generator_model_family,
            judge_model_family=judge_model_family,
            judge_sovereignty_tier=judge_sovereignty_tier,
            run_override_uri=run_override_uri,
            resolve_destination_fn=lambda content_bytes: self.resolve_artifact_destination(
                workspace_id=workspace_id,
                workspace_slug=workspace_slug,
                artifact_type="tech-spec",
                artifact_slug=ticket_key.lower(),
                version=1,
                content_bytes=content_bytes,
                run_override_uri=run_override_uri,
            ),
        )


__all__ = [
    "DnaChainNode",
    "ExceptionWaiverRecord",
    "ExternalRebaseResult",
    "NormOntologyLevel",
    "PilotWorkflowRunResult",
    "RebasedSectionChunk",
    "ResolvedArtifactDestination",
    "SourceAccessMode",
    "SourceAuthorityRole",
    "SovereigntyTier",
    "WorkspaceFiveTabsState",
    "WorkspaceGovernanceAndArtifactRoutingService",
    "WorkspaceSourceSummary",
    "WorkspaceSubTab",
]
