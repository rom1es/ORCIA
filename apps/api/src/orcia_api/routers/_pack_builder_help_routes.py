"""Help article validation and attachment endpoints for `pack_builder` (`Story 11.5`)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, status

from orcia_api.dependencies import get_help_generation_and_attachment_service
from orcia_api.schemas.pack_builder import (
    GenerateAndAttachHelpRequest,
    GenerateAndAttachHelpResponse,
    ValidateHelpArticleRequest,
    ValidateHelpArticleResponse,
)
from orcia_core.orchestration.help_generator_and_validator import (
    HelpGenerationAndHotAttachmentService,
)

help_router = APIRouter()


@help_router.post(
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


@help_router.post(
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
