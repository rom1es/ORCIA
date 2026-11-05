"""FastAPI router for Story 11.4 & Story 11.5 (`packages/orcia-pack-builder` Processes 1 to 5)."""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Depends, status

from orcia_api.dependencies import (
    get_help_generation_and_attachment_service,
    get_pack_builder_system_service,
)
from orcia_api.schemas.pack_builder import (
    CertifyPackToolRequest,
    CertifyPackToolResponse,
    CreateBusinessPackRequest,
    CreateBusinessPackResponse,
    EvolveBusinessPackWhatIfRequest,
    EvolveBusinessPackWhatIfResponse,
    ExportFromWorkspaceToPackRequest,
    ExportFromWorkspaceToPackResponse,
    GenerateAndAttachHelpRequest,
    GenerateAndAttachHelpResponse,
    InstalledBusinessPackItemResponse,
    InstalledBusinessPackListResponse,
    ValidateHelpArticleRequest,
    ValidateHelpArticleResponse,
    WhatIfWorkspaceImpactItemResponse,
)
from orcia_core.orchestration.help_generator_and_validator import (
    HelpGenerationAndHotAttachmentService,
)
from orcia_core.orchestration.pack_builder_processes import (
    DnaChainPackSeedSpec,
    PackBuilderSystemService,
)
from orcia_pack_builder import (
    PACK_BUILDER_AGENTS,
    PACK_BUILDER_PROCESSES,
    get_pack_builder_manifest,
)
from orcia_pack_builder import (
    __version__ as pack_builder_version,
)
from orcia_pack_sdlc import __version__ as pack_sdlc_version

router = APIRouter(tags=["pack-builder"])


@router.get(
    "/api/v1/pack-builder/installed-packs",
    response_model=InstalledBusinessPackListResponse,
    status_code=status.HTTP_200_OK,
)
async def list_installed_business_packs_endpoint(
    svc: Annotated[PackBuilderSystemService, Depends(get_pack_builder_system_service)],
) -> InstalledBusinessPackListResponse:
    """Return the catalog of Business Packs installed and known in the ORCIA backend."""
    installed: list[InstalledBusinessPackItemResponse] = [
        InstalledBusinessPackItemResponse(
            pack_key="orcia-pack-sdlc",
            pack_slug="sdlc",
            title="Ingénierie Logicielle & Cycle de Vie Produit",
            title_en="Software Engineering & Product Lifecycle",
            version=pack_sdlc_version or "1.0.0",
            domain_name="INGÉNIERIE LOGICIELLE & PRODUIT",
            description=(
                "Connecteurs Git, Jira, Confluence et Nexus, processus guidés de spécification "
                "et réalisation, revues croisées et suivi de cohérence documentaire."
            ),
            description_en=(
                "Git, Jira, Confluence, and Nexus connectors, guided specification and delivery "
                "processes, cross-checked reviews, and documentation consistency tracking."
            ),
            workflows_count=4,
            agents_count=6,
            is_system_pack=True,
        ),
        InstalledBusinessPackItemResponse(
            pack_key="orcia-pack-builder",
            pack_slug="pack-builder",
            title="Atelier de Création & Gouvernance de Packs Métiers",
            title_en="Business Pack Authoring & Governance Studio",
            version=pack_builder_version or "1.0.0",
            domain_name="GOUVERNANCE & MÉTHODOLOGIE",
            description=(
                "Conception guidée de nouveaux Packs métiers, simulation d'impact avant "
                "évolution, certification des règles métiers et génération de fiches d'aide."
            ),
            description_en=(
                "Guided creation of new Business Packs, impact simulation before evolution, "
                "business rule certification, and help article generation."
            ),
            workflows_count=len(PACK_BUILDER_PROCESSES),
            agents_count=len(PACK_BUILDER_AGENTS),
            is_system_pack=True,
        ),
    ]
    seen_keys = {item.pack_key for item in installed}
    for custom in svc.list_created_packs():
        custom_key = f"orcia-pack-{custom.pack_slug}"
        if custom_key in seen_keys:
            continue
        seen_keys.add(custom_key)
        installed.append(
            InstalledBusinessPackItemResponse(
                pack_key=custom_key,
                pack_slug=custom.pack_slug,
                title=custom.title,
                title_en=custom.title,
                version=custom.version,
                domain_name="PACK MÉTIER PERSONNALISÉ",
                description=custom.human_anchor_intent,
                description_en=custom.human_anchor_intent,
                workflows_count=max(1, custom.starlark_rules_certified_count),
                agents_count=1,
                is_system_pack=False,
            )
        )
    return InstalledBusinessPackListResponse(packs=installed)


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


@router.post(
    "/api/v1/pack-builder/processes/validate-help-article",
    response_model=ValidateHelpArticleResponse,
    status_code=status.HTTP_200_OK,
)
async def validate_help_article_endpoint(
    payload: ValidateHelpArticleRequest,
    svc: Annotated[
        HelpGenerationAndHotAttachmentService,
        Depends(get_help_generation_and_attachment_service),
    ],
) -> ValidateHelpArticleResponse:
    """Execute deterministic Gate `validate_help_article` (`< 5 s`)."""
    rep = svc.validator.validate_help_article(
        markdown_text=payload.markdown_text,
        lang=payload.lang,
        extra_allowed_routes=payload.extra_allowed_routes or None,
        known_glossary_terms=payload.known_glossary_terms or None,
    )
    return ValidateHelpArticleResponse(
        article_id=rep.article_id,
        lang=rep.lang,
        passed=rep.passed,
        bound_routes_valid=rep.bound_routes_valid,
        ui_components_and_sections_valid=rep.ui_components_and_sections_valid,
        glossary_and_zero_secret_valid=rep.glossary_and_zero_secret_valid,
        elapsed_ms=rep.elapsed_ms,
        violations=list(rep.violations),
    )


@router.post(
    "/api/v1/pack-builder/processes/generate-and-attach-help",
    response_model=GenerateAndAttachHelpResponse,
    status_code=status.HTTP_201_CREATED,
)
async def generate_and_attach_help_endpoint(
    payload: GenerateAndAttachHelpRequest,
    svc: Annotated[
        HelpGenerationAndHotAttachmentService,
        Depends(get_help_generation_and_attachment_service),
    ],
) -> GenerateAndAttachHelpResponse:
    """Execute Process 5 (`generate-and-attach-help`)."""
    res = await svc.generate_and_attach_help(
        article_id=payload.article_id,
        article_slug=payload.article_slug,
        version=payload.version,
        pack_slug=payload.pack_slug,
        title_fr=payload.title_fr,
        title_en=payload.title_en,
        bound_routes=payload.bound_routes,
        roles_allowed=payload.roles_allowed,
        glossary_terms=payload.glossary_terms,
        related_workflows=payload.related_workflows,
        purpose_fr=payload.purpose_fr,
        purpose_en=payload.purpose_en,
        steps_fr=payload.steps_fr,
        steps_en=payload.steps_en,
        faq_fr=payload.faq_fr,
        faq_en=payload.faq_en,
        ui_component_name=payload.ui_component_name,
        trigger_regime=payload.trigger_regime,
        known_glossary_terms=payload.known_glossary_terms or None,
        actor_role=payload.actor_role,
    )
    return GenerateAndAttachHelpResponse(
        article_id=res.article_id,
        version=res.version,
        pack_id=res.pack_id,
        trigger_regime=res.trigger_regime,
        bound_routes=list(res.bound_routes),
        fr_cas_key=res.fr_cas_key,
        en_cas_key=res.en_cas_key,
        fr_sha256=res.fr_sha256,
        en_sha256=res.en_sha256,
        validation_fr=ValidateHelpArticleResponse(
            article_id=res.validation_fr.article_id,
            lang=res.validation_fr.lang,
            passed=res.validation_fr.passed,
            bound_routes_valid=res.validation_fr.bound_routes_valid,
            ui_components_and_sections_valid=res.validation_fr.ui_components_and_sections_valid,
            glossary_and_zero_secret_valid=res.validation_fr.glossary_and_zero_secret_valid,
            elapsed_ms=res.validation_fr.elapsed_ms,
            violations=list(res.validation_fr.violations),
        ),
        validation_en=ValidateHelpArticleResponse(
            article_id=res.validation_en.article_id,
            lang=res.validation_en.lang,
            passed=res.validation_en.passed,
            bound_routes_valid=res.validation_en.bound_routes_valid,
            ui_components_and_sections_valid=res.validation_en.ui_components_and_sections_valid,
            glossary_and_zero_secret_valid=res.validation_en.glossary_and_zero_secret_valid,
            elapsed_ms=res.validation_en.elapsed_ms,
            violations=list(res.validation_en.violations),
        ),
        invalidated_redis_keys=list(res.invalidated_redis_keys),
        exported_git_paths=list(res.exported_git_paths),
        hot_attach_elapsed_ms=res.hot_attach_elapsed_ms,
        authority_role=res.authority_role,
    )
