"""Story 11.4 — System Pack `orcia-pack-builder` Processes 1 to 4 (`AD-7`, `AD-9`, `AD-20`).

Provides `PackBuilderSystemService` orchestrating the 4 specialized Pack Builder agents
across Processes 1 to 4 (`create-business-pack`, `evolve-business-pack`,
`certify-pack-tool`, and `export-from-workspace-to-pack`).
"""

from __future__ import annotations

import time
from pathlib import Path
from typing import Any

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from orcia_core.gates._internal.starlark_sandbox import StarlarkMechanismSandbox
from orcia_core.orchestration._pack_builder_helpers import (
    build_pack_generated_files,
    certify_pack_tool_impl,
    export_from_workspace_to_pack_impl,
)
from orcia_core.orchestration._pack_builder_models import (
    _FORBIDDEN_CORE_SLUGS,
    _PACK_SLUG_RE,
    PACK_BUILDER_AGENTS,
    CreatedBusinessPackResult,
    DnaChainPackSeedSpec,
    PackBuilderAgentSpec,
    PackBuilderValidationError,
    PackCertificationTier,
    PackEvolutionWhatIfReport,
    PackToolCertificationReport,
    PromotableAssetKind,
    WhatIfWorkspaceImpactItem,
    WorkspaceToPackPromotionResult,
    persist_pack_and_audit_pg,
)
from orcia_core.orchestration.errors import (
    HumanAnchorRequiredError,
    ObserverModeReadOnlyError,
)


class PackBuilderSystemService:
    """Domain service implementing Processes 1 to 4 of `packages/orcia-pack-builder`."""

    def __init__(
        self,
        *,
        session_factory: async_sessionmaker[AsyncSession] | None = None,
        starlark_sandbox: StarlarkMechanismSandbox | None = None,
    ) -> None:
        self._session_factory = session_factory
        self._sandbox = starlark_sandbox or StarlarkMechanismSandbox()
        self._created_packs: dict[str, CreatedBusinessPackResult] = {}
        self._what_if_reports: list[PackEvolutionWhatIfReport] = []
        self._certifications: dict[str, PackToolCertificationReport] = {}
        self._promotions: list[WorkspaceToPackPromotionResult] = []

    def list_pack_builder_agents(self) -> tuple[PackBuilderAgentSpec, ...]:
        """Return the 4 specialized agents of `orcia-pack-builder`."""
        return PACK_BUILDER_AGENTS

    def list_created_packs(self) -> tuple[CreatedBusinessPackResult, ...]:
        """Return all custom Business Packs created via Process 1 (`create-business-pack`)."""
        return tuple(self._created_packs.values())

    async def create_business_pack(
        self,
        *,
        pack_slug: str,
        title: str,
        version: str,
        domain_name: str,
        human_anchor_intent: str,
        dna_seeds: list[DnaChainPackSeedSpec],
        human_profiles: list[str],
        agents: list[str],
        workflows: list[str],
        actor_role: str = "ARCHITECT",
        actor_id: str = "architect-user",
        output_root_dir: Path | None = None,
    ) -> CreatedBusinessPackResult:
        """Process 1 (`create-business-pack`): Violet Anchor + DNA chain + Tier 1a/1b."""
        if actor_role.upper() == "READ_ONLY_OBSERVER":
            raise ObserverModeReadOnlyError(detail_override="create_business_pack")

        cleaned_anchor = human_anchor_intent.strip()
        if len(cleaned_anchor) < 30:
            raise HumanAnchorRequiredError(
                detail_override="pack_builder.create_business_pack.human_anchor_intent"
            )

        slug = pack_slug.strip().lower()
        if not _PACK_SLUG_RE.match(slug) or slug in _FORBIDDEN_CORE_SLUGS:
            raise PackBuilderValidationError(
                error_code="ERR_PACK_SLUG_RESERVED_OR_INVALID",
                detail_code="ERR_PACK_SLUG_RESERVED_OR_INVALID",
                detail_params={"pack_slug": pack_slug},
            )

        t0 = time.perf_counter()
        if not dna_seeds:
            raise PackBuilderValidationError(
                error_code="ERR_PACK_DNA_CHAIN_EMPTY",
                detail_code="ERR_PACK_DNA_CHAIN_EMPTY",
            )

        max_starlark_ms = 0.0
        rules_files: dict[str, str] = {}
        for seed in dna_seeds:
            cert = await self.certify_pack_tool(
                tool_slug=seed.mechanism_code.lower(),
                sandbox_tier="TIER_1B_STARLARK",
                starlark_source=seed.starlark_source,
                rule_id=seed.rule_id,
                passing_test_payload=seed.passing_test_payload,
                failing_test_payload=seed.failing_test_payload,
                actor_role=actor_role,
            )
            if not cert.certified:
                raise PackBuilderValidationError(
                    error_code="ERR_STARLARK_RULE_CERTIFICATION_FAILED",
                    detail_code="ERR_STARLARK_RULE_CERTIFICATION_FAILED",
                    detail_params={
                        "mechanism_code": seed.mechanism_code,
                        "rule_id": seed.rule_id,
                    },
                )
            max_starlark_ms = max(max_starlark_ms, cert.elapsed_ms)
            rules_files[f"rules/{seed.mechanism_code.lower()}.star"] = seed.starlark_source

        pack_id, target_dir, generated_files, kernel_or_core_touched = build_pack_generated_files(
            slug=slug,
            title=title,
            version=version,
            domain_name=domain_name,
            human_profiles=human_profiles,
            agents=agents,
            workflows=workflows,
            rules_files=rules_files,
            output_root_dir=output_root_dir,
        )

        manifest_elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 3)
        result = CreatedBusinessPackResult(
            pack_id=pack_id,
            pack_slug=slug,
            version=version,
            title=title,
            human_anchor_intent=cleaned_anchor,
            target_directory=target_dir,
            generated_files=generated_files,
            manifest_validation_elapsed_ms=manifest_elapsed_ms,
            starlark_rules_certified_count=len(dna_seeds),
            max_starlark_elapsed_ms=max_starlark_ms,
            kernel_or_core_touched=kernel_or_core_touched,
        )
        self._created_packs[slug] = result
        await self._persist_pack_and_audit(result, actor_id=actor_id)
        return result

    async def evolve_business_pack_what_if(
        self,
        *,
        pack_slug: str,
        previous_version: str,
        target_version: str,
        modified_norms: list[str],
        modified_workflows: list[str],
        subscribed_workspaces: list[dict[str, Any]],
        active_run_lock_ids: list[str],
        actor_role: str = "ARCHITECT",
    ) -> PackEvolutionWhatIfReport:
        """Process 2 (`evolve-business-pack`): *What-If* preserving active `run-lock.json`."""
        if actor_role.upper() == "READ_ONLY_OBSERVER":
            raise ObserverModeReadOnlyError(detail_override="evolve_business_pack_what_if")

        workspace_impacts: list[WhatIfWorkspaceImpactItem] = []
        total_workflows = 0
        for ws in subscribed_workspaces:
            ws_key = (
                str(ws.get("workspace_key", "")).strip()
                or str(ws.get("workspace_id", "")).strip()
                or "workspace"
            )
            ws_workflows = tuple(
                wf
                for wf in ws.get("workflows", [])
                if wf in modified_workflows or not modified_workflows
            )
            total_workflows += len(ws_workflows)
            workspace_impacts.append(
                WhatIfWorkspaceImpactItem(
                    workspace_key=ws_key,
                    impacted_workflows=ws_workflows,
                    breaking_norms=tuple(modified_norms),
                    active_runs_count=int(ws.get("active_runs_count", 0)),
                    run_locks_untouched=True,
                )
            )

        report = PackEvolutionWhatIfReport(
            pack_slug=pack_slug,
            previous_version=previous_version,
            target_version=target_version,
            impacted_workspaces_count=len(workspace_impacts),
            impacted_workflows_count=total_workflows,
            breaking_changes_detected=len(modified_norms) > 0,
            active_run_locks_preserved=True,
            untouched_run_lock_ids=tuple(active_run_lock_ids),
            workspace_impacts=tuple(workspace_impacts),
        )
        self._what_if_reports.append(report)
        return report

    async def certify_pack_tool(
        self,
        *,
        tool_slug: str,
        sandbox_tier: PackCertificationTier,
        starlark_source: str = "",
        rule_id: str = "NORM-PACK-001",
        passing_test_payload: dict[str, Any] | None = None,
        failing_test_payload: dict[str, Any] | None = None,
        container_image_digest: str = "",
        container_command: list[str] | None = None,
        actor_role: str = "ARCHITECT",
    ) -> PackToolCertificationReport:
        """Process 3 (`certify-pack-tool`): Tier 1b Starlark (`< 2 ms`) or Tier 2 (`< 60 s`)."""
        if actor_role.upper() == "READ_ONLY_OBSERVER":
            raise ObserverModeReadOnlyError(detail_override="certify_pack_tool")

        report = certify_pack_tool_impl(
            self._sandbox,
            tool_slug=tool_slug,
            sandbox_tier=sandbox_tier,
            starlark_source=starlark_source,
            rule_id=rule_id,
            passing_test_payload=passing_test_payload,
            failing_test_payload=failing_test_payload,
            container_image_digest=container_image_digest,
            container_command=container_command,
        )
        self._certifications[tool_slug] = report
        return report

    async def export_from_workspace_to_pack(
        self,
        *,
        source_workspace_key: str,
        target_pack_slug: str,
        target_pack_version: str,
        asset_kind: PromotableAssetKind,
        asset_slug: str,
        raw_asset_payload: dict[str, Any],
        actor_role: str = "ARCHITECT",
    ) -> WorkspaceToPackPromotionResult:
        """Process 4 (`export-from-workspace-to-pack`): scrub workspace specifics & secrets."""
        if actor_role.upper() == "READ_ONLY_OBSERVER":
            raise ObserverModeReadOnlyError(detail_override="export_from_workspace_to_pack")

        result = export_from_workspace_to_pack_impl(
            source_workspace_key=source_workspace_key,
            target_pack_slug=target_pack_slug,
            target_pack_version=target_pack_version,
            asset_kind=asset_kind,
            asset_slug=asset_slug,
            raw_asset_payload=raw_asset_payload,
        )
        self._promotions.append(result)
        return result

    async def _persist_pack_and_audit(
        self, pack: CreatedBusinessPackResult, *, actor_id: str
    ) -> None:
        if self._session_factory is None:
            return
        await persist_pack_and_audit_pg(self._session_factory, pack, actor_id=actor_id)


__all__ = [
    "CreatedBusinessPackResult",
    "DnaChainPackSeedSpec",
    "PACK_BUILDER_AGENTS",
    "PackBuilderAgentSpec",
    "PackBuilderSystemService",
    "PackBuilderValidationError",
    "PackCertificationTier",
    "PackEvolutionWhatIfReport",
    "PackToolCertificationReport",
    "PromotableAssetKind",
    "WhatIfWorkspaceImpactItem",
    "WorkspaceToPackPromotionResult",
]
