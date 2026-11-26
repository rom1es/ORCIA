"""Publish, Export & DNA Mechanism Delete sub-routes for Pack Composer (`Story 31.5`)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Body, Depends, Path, Query, Request, Response

from orcia_api.dependencies import get_pack_composer_service
from orcia_api.dependencies._core_providers import get_configured_db_engine
from orcia_api.routers._entity_delete_rbac import (
    build_dna_target_authorizer,
    prepare_entity_delete_guards,
)
from orcia_api.routers._pack_composer_helpers import (
    enforce_composer_scope_access,
    execute_export_pack_zip_handler,
    serialize_draft_detail,
)
from orcia_api.routers._workspace_packs_guards import trace_id_for
from orcia_api.routers.auth import PROBLEM_RESPONSES
from orcia_api.schemas._pack_composer import (
    GuardedEntityDeleteResponse,
    PackDraftDetailResponse,
    PackExportRequest,
    PackPublishRequest,
)
from orcia_core.packs import PackComposerService
from orcia_core.permissions.errors import ScopeAccessDeniedError
from orcia_core.storage.entity_delete_tx import delete_entity_guarded_tx

publish_router = APIRouter(responses=PROBLEM_RESPONSES)
ComposerSvcDep = Annotated[PackComposerService, Depends(get_pack_composer_service)]
DraftIdPath = Annotated[str, Path(min_length=1, max_length=128)]
PersonaQuery = Annotated[str | None, Query(min_length=1, max_length=64)]


@publish_router.post("/{draft_id}/publish", response_model=PackDraftDetailResponse)
async def publish_pack_draft(
    draft_id: DraftIdPath,
    request: Request,
    svc: ComposerSvcDep,
    payload: Annotated[PackPublishRequest | None, Body()] = None,
    auto_include_dependencies: bool = Query(default=False),
    persona_key: PersonaQuery = None,
) -> PackDraftDetailResponse:
    """Validate closure & ACTIVE readiness, scrub/scan, snapshot CAS & publish `CUSTOM` pack."""
    existing = await svc.get_draft(draft_id, include_closure=False, instance=str(request.url.path))
    user, _ = await enforce_composer_scope_access(
        request,
        scope_type=existing.scope_type,
        scope_id=existing.scope_id,
        require_write=True,
        persona_key=persona_key,
    )
    trace_id = trace_id_for(request)
    auto_inc = auto_include_dependencies or (
        payload.auto_include_dependencies if payload is not None else False
    )
    published = await svc.publish_draft(
        existing.bundle_id,
        auto_include_dependencies=auto_inc,
        actor_id=user.id,
        actor_email=user.email,
        trace_id=trace_id,
        instance=str(request.url.path),
    )
    return serialize_draft_detail(published, trace_id=trace_id)


@publish_router.post(
    "/{draft_id}/export",
    responses={
        **PROBLEM_RESPONSES,
        200: {"content": {"application/zip": {"schema": {"type": "string", "format": "binary"}}}},
    },
)
async def export_pack_draft_zip(
    draft_id: DraftIdPath,
    request: Request,
    svc: ComposerSvcDep,
    payload: Annotated[PackExportRequest | None, Body()] = None,
    auto_include_dependencies: bool = Query(default=False),
    persona_key: PersonaQuery = None,
) -> Response:
    """Export a composed `CUSTOM` pack draft/bundle as a scrubbed APM `.zip` + `apm.lock.yaml`."""
    auto_inc = auto_include_dependencies or (
        payload.auto_include_dependencies if payload is not None else False
    )
    return await execute_export_pack_zip_handler(
        draft_id,
        request=request,
        svc=svc,
        auto_include_dependencies=auto_inc,
        persona_key=persona_key,
    )


@publish_router.delete("/dna-mechanisms/{mechanism_id}", response_model=GuardedEntityDeleteResponse)
async def delete_pack_dna_mechanism_endpoint(
    mechanism_id: DraftIdPath,
    request: Request,
    unlink_from_draft_packs: bool = Query(default=False),
    persona_key: PersonaQuery = None,
) -> GuardedEntityDeleteResponse:
    """Delete a `pack_dna_mechanisms` row with RBAC, immutability & `409` guard."""
    inst = str(request.url.path)
    user, auth_svc, trace_id, authorize_draft = await prepare_entity_delete_guards(
        request, persona_key=persona_key
    )
    engine = get_configured_db_engine(request)
    if engine is None:
        raise ScopeAccessDeniedError(
            detail_override="PostgreSQL 18 engine is required for DNA mechanism deletion.",
            instance=inst,
        )
    outcome = await delete_entity_guarded_tx(
        engine,
        entity_type="DNA_MECHANISM",
        entity_id_or_key=mechanism_id,
        unlink_from_draft_packs=unlink_from_draft_packs,
        authorize_target_cb=build_dna_target_authorizer(auth_svc, user, instance=inst),
        authorize_draft_cb=authorize_draft,
        actor_id=user.id,
        actor_email=user.email,
        trace_id=trace_id,
        instance=inst,
    )
    return GuardedEntityDeleteResponse(
        entity_type=outcome.entity_type,
        deleted_id=outcome.deleted_id,
        deleted_uuid=outcome.deleted_uuid,
        unlinked_draft_packs=list(outcome.unlinked_draft_packs),
        trace_id=trace_id,
    )


__all__ = ["publish_router"]
