"""FastAPI router for Story 11.4 (`packages/orcia-pack-builder` Processes 1 to 4)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, status

from orcia_api.dependencies_epic11 import get_pack_builder_system_service
from orcia_api.schemas.epic11_pack_builder import (
    CertifyPackToolRequest,
    CertifyPackToolResponse,
    CreateBusinessPackRequest,
    CreateBusinessPackResponse,
    EvolveBusinessPackWhatIfRequest,
    EvolveBusinessPackWhatIfResponse,
    ExportFromWorkspaceToPackRequest,
    ExportFromWorkspaceToPackResponse,
    WhatIfWorkspaceImpactItemResponse,
)
from orcia_core.orchestration.pack_builder_processes import (
    DnaChainPackSeedSpec,
    PackBuilderSystemService,
)
from orcia_pack_builder import get_pack_builder_manifest

router = APIRouter(tags=["epic11-pack-builder"])


@router.get(
    "/api/v1/pack-builder/manifest",
    status_code=status.HTTP_200_OK,
)
async def get_system_pack_builder_manifest_endpoint() -> dict[str, Any]:
    """Return the system `orcia-pack-builder` manifest (4 agents + 5 governed processes)."""
    return get_pack_builder_manifest()


@router.post(
    "/api/v1/pack-builder/processes/create-pack",
    response_model=CreateBusinessPackResponse,
    status_code=status.HTTP_201_CREATED,
)
async def create_business_pack_endpoint(
    payload: CreateBusinessPackRequest,
    svc: Annotated[PackBuilderSystemService, Depends(get_pack_builder_system_service)],
) -> CreateBusinessPackResponse:
    """Execute Process 1 (`create-business-pack`)."""
    seeds = [
        DnaChainPackSeedSpec(
            directive_code=s.directive_code,
            directive_title=s.directive_title,
            norm_code=s.norm_code,
            norm_title=s.norm_title,
            mechanism_code=s.mechanism_code,
            rule_id=s.rule_id,
            starlark_source=s.starlark_source,
            passing_test_payload=s.passing_test_payload,
            failing_test_payload=s.failing_test_payload,
        )
        for s in payload.dna_seeds
    ]
    res = await svc.create_business_pack(
        pack_slug=payload.pack_slug,
        title=payload.title,
        version=payload.version,
        domain_name=payload.domain_name,
        human_anchor_intent=payload.human_anchor_intent,
        dna_seeds=seeds,
        human_profiles=payload.human_profiles,
        agents=payload.agents,
        workflows=payload.workflows,
        actor_role=payload.actor_role,
        actor_id=payload.actor_id,
    )
    return CreateBusinessPackResponse(
        pack_id=res.pack_id,
        pack_slug=res.pack_slug,
        version=res.version,
        title=res.title,
        human_anchor_intent=res.human_anchor_intent,
        target_directory=res.target_directory,
        generated_file_paths=sorted(res.generated_files.keys()),
        manifest_validation_elapsed_ms=res.manifest_validation_elapsed_ms,
        starlark_rules_certified_count=res.starlark_rules_certified_count,
        max_starlark_elapsed_ms=res.max_starlark_elapsed_ms,
        kernel_or_core_touched=res.kernel_or_core_touched,
    )


@router.post(
    "/api/v1/pack-builder/processes/evolve-what-if",
    response_model=EvolveBusinessPackWhatIfResponse,
    status_code=status.HTTP_200_OK,
)
async def evolve_business_pack_what_if_endpoint(
    payload: EvolveBusinessPackWhatIfRequest,
    svc: Annotated[PackBuilderSystemService, Depends(get_pack_builder_system_service)],
) -> EvolveBusinessPackWhatIfResponse:
    """Execute Process 2 (`evolve-business-pack` *What-If* simulation)."""
    report = await svc.evolve_business_pack_what_if(
        pack_slug=payload.pack_slug,
        previous_version=payload.previous_version,
        target_version=payload.target_version,
        modified_norms=payload.modified_norms,
        modified_workflows=payload.modified_workflows,
        subscribed_workspaces=payload.subscribed_workspaces,
        active_run_lock_ids=payload.active_run_lock_ids,
        actor_role=payload.actor_role,
    )
    return EvolveBusinessPackWhatIfResponse(
        pack_slug=report.pack_slug,
        previous_version=report.previous_version,
        target_version=report.target_version,
        impacted_workspaces_count=report.impacted_workspaces_count,
        impacted_workflows_count=report.impacted_workflows_count,
        breaking_changes_detected=report.breaking_changes_detected,
        active_run_locks_preserved=report.active_run_locks_preserved,
        untouched_run_lock_ids=list(report.untouched_run_lock_ids),
        workspace_impacts=[
            WhatIfWorkspaceImpactItemResponse(
                workspace_key=w.workspace_key,
                impacted_workflows=list(w.impacted_workflows),
                breaking_norms=list(w.breaking_norms),
                active_runs_count=w.active_runs_count,
                run_locks_untouched=w.run_locks_untouched,
            )
            for w in report.workspace_impacts
        ],
    )


@router.post(
    "/api/v1/pack-builder/processes/certify-tool",
    response_model=CertifyPackToolResponse,
    status_code=status.HTTP_200_OK,
)
async def certify_pack_tool_endpoint(
    payload: CertifyPackToolRequest,
    svc: Annotated[PackBuilderSystemService, Depends(get_pack_builder_system_service)],
) -> CertifyPackToolResponse:
    """Execute Process 3 (`certify-pack-tool` in Tier 1b Starlark or Tier 2 Container)."""
    cert = await svc.certify_pack_tool(
        tool_slug=payload.tool_slug,
        sandbox_tier=payload.sandbox_tier,
        starlark_source=payload.starlark_source,
        rule_id=payload.rule_id,
        passing_test_payload=payload.passing_test_payload,
        failing_test_payload=payload.failing_test_payload,
        container_image_digest=payload.container_image_digest,
        container_command=payload.container_command,
        actor_role=payload.actor_role,
    )
    return CertifyPackToolResponse(
        tool_slug=cert.tool_slug,
        sandbox_tier=cert.sandbox_tier,
        certified=cert.certified,
        elapsed_ms=cert.elapsed_ms,
        passing_vector_ok=cert.passing_vector_ok,
        failing_vector_rejected_ok=cert.failing_vector_rejected_ok,
        network_isolated=cert.network_isolated,
        certificate_sha256=cert.certificate_sha256,
        diagnostics=list(cert.diagnostics),
    )


@router.post(
    "/api/v1/pack-builder/processes/export-from-workspace",
    response_model=ExportFromWorkspaceToPackResponse,
    status_code=status.HTTP_200_OK,
)
async def export_from_workspace_to_pack_endpoint(
    payload: ExportFromWorkspaceToPackRequest,
    svc: Annotated[PackBuilderSystemService, Depends(get_pack_builder_system_service)],
) -> ExportFromWorkspaceToPackResponse:
    """Execute Process 4 (`export-from-workspace-to-pack`)."""
    res = await svc.export_from_workspace_to_pack(
        source_workspace_key=payload.source_workspace_key,
        target_pack_slug=payload.target_pack_slug,
        target_pack_version=payload.target_pack_version,
        asset_kind=payload.asset_kind,
        asset_slug=payload.asset_slug,
        raw_asset_payload=payload.raw_asset_payload,
        actor_role=payload.actor_role,
    )
    return ExportFromWorkspaceToPackResponse(
        source_workspace_key=res.source_workspace_key,
        target_pack_slug=res.target_pack_slug,
        target_pack_version=res.target_pack_version,
        asset_kind=res.asset_kind,
        asset_slug=res.asset_slug,
        promoted_uri=res.promoted_uri,
        scrubbed_references_count=res.scrubbed_references_count,
        sanitized_payload=res.sanitized_payload,
    )
