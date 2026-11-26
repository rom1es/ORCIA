"""Pack Composer CRUD & Typed Membership Router (`Story 31.5`, `<= 250 L`)."""

from __future__ import annotations

from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Path, Query, Request, status

from orcia_api.dependencies import get_pack_composer_service
from orcia_api.routers._pack_composer_helpers import (
    compute_caller_composer_scopes,
    enforce_composer_scope_access,
    serialize_draft_detail,
)
from orcia_api.routers._pack_composer_publish_routes import publish_router
from orcia_api.routers._workspace_packs_guards import trace_id_for
from orcia_api.routers.auth import PROBLEM_RESPONSES
from orcia_api.schemas._pack_composer import (
    CreatePackDraftRequest,
    PackDraftDeleteResponse,
    PackDraftDetailResponse,
    PackDraftListResponse,
    SetPackDraftMembersRequest,
    UpdatePackDraftRequest,
)
from orcia_core.packs import (
    PackComposerService,
    PackDraftEntityType,
    PackDraftMemberInput,
    PackQuickActionSpec,
    PackScopeType,
    PackSlotSpec,
)

router = APIRouter(
    prefix="/api/v1/packs/composer",
    tags=["Pack Composer & Export (Story 31.5)"],
    responses=PROBLEM_RESPONSES,
)
router.include_router(publish_router)

ComposerSvcDep = Annotated[PackComposerService, Depends(get_pack_composer_service)]
DraftIdPath = Annotated[str, Path(min_length=1, max_length=128)]
PersonaQuery = Annotated[str | None, Query(min_length=1, max_length=64)]


@router.post("", response_model=PackDraftDetailResponse, status_code=status.HTTP_201_CREATED)
async def create_pack_draft(
    payload: CreatePackDraftRequest,
    request: Request,
    svc: ComposerSvcDep,
    persona_key: PersonaQuery = None,
) -> PackDraftDetailResponse:
    """Create a `CUSTOM` `DRAFT` pack bundle scoped to a workspace/team/BU."""
    user, resolved_scope_id = await enforce_composer_scope_access(
        request,
        scope_type=payload.scope_type,
        scope_id=payload.scope_id,
        require_write=True,
        persona_key=persona_key,
    )
    trace_id = trace_id_for(request)
    detail = await svc.create_draft(
        slug=payload.slug,
        name=payload.name,
        version=payload.version,
        description=payload.description,
        author=payload.author,
        maintainers=payload.maintainers,
        license_name=payload.license,
        scope_type=PackScopeType(payload.scope_type),
        scope_id=resolved_scope_id,
        declared_slots=[PackSlotSpec(**s.model_dump()) for s in payload.declared_slots],
        quick_actions=[PackQuickActionSpec(**q.model_dump()) for q in payload.quick_actions],
        actor_id=user.id,
        actor_email=user.email,
        trace_id=trace_id,
        instance=str(request.url.path),
    )
    return serialize_draft_detail(detail, trace_id=trace_id)


@router.get("", response_model=PackDraftListResponse)
async def list_pack_drafts(
    request: Request,
    svc: ComposerSvcDep,
    scope_type: Literal["BU", "TEAM", "WORKSPACE"] | None = None,
    scope_id: str | None = Query(default=None, max_length=128),
    status_filter: Annotated[
        Literal["DRAFT", "PUBLISHED", "DEPRECATED", "ALL"], Query(alias="status")
    ] = "DRAFT",
    persona_key: PersonaQuery = None,
) -> PackDraftListResponse:
    """List `CUSTOM` composer pack bundles visible to the caller."""
    resolved_scope_id = scope_id
    unrestricted = False
    allowed_ws: frozenset[str] = frozenset()
    allowed_orgs: frozenset[str] = frozenset()
    allow_global = False
    if scope_type is not None and scope_id:
        _, resolved_scope_id = await enforce_composer_scope_access(
            request,
            scope_type=scope_type,
            scope_id=scope_id,
            require_write=False,
            persona_key=persona_key,
        )
        unrestricted = True
    else:
        _, unrestricted, allowed_ws, allowed_orgs = await compute_caller_composer_scopes(
            request, persona_key=persona_key
        )
        allow_global = unrestricted
    items = await svc.list_drafts(
        scope_type=PackScopeType(scope_type) if scope_type else None,
        scope_id=resolved_scope_id,
        status_filter=status_filter,
        unrestricted=unrestricted,
        allowed_workspace_ids=allowed_ws,
        allowed_org_ids=allowed_orgs,
        allow_global=allow_global,
    )
    trace_id = trace_id_for(request)
    return PackDraftListResponse(
        drafts=[serialize_draft_detail(item, trace_id=trace_id) for item in items],
        trace_id=trace_id,
    )


@router.get("/{draft_id}", response_model=PackDraftDetailResponse)
async def get_pack_draft(
    draft_id: DraftIdPath,
    request: Request,
    svc: ComposerSvcDep,
    persona_key: PersonaQuery = None,
) -> PackDraftDetailResponse:
    """Fetch a composer pack draft with hydrated members & live closure preview."""
    detail = await svc.get_draft(draft_id, include_closure=True, instance=str(request.url.path))
    await enforce_composer_scope_access(
        request,
        scope_type=detail.scope_type,
        scope_id=detail.scope_id,
        require_write=False,
        persona_key=persona_key,
    )
    return serialize_draft_detail(detail, trace_id=trace_id_for(request))


@router.patch("/{draft_id}", response_model=PackDraftDetailResponse)
async def update_pack_draft(
    draft_id: DraftIdPath,
    payload: UpdatePackDraftRequest,
    request: Request,
    svc: ComposerSvcDep,
    persona_key: PersonaQuery = None,
) -> PackDraftDetailResponse:
    """Update metadata & declared slots on a mutable `CUSTOM` `DRAFT` pack."""
    existing = await svc.get_draft(draft_id, include_closure=False, instance=str(request.url.path))
    await enforce_composer_scope_access(
        request,
        scope_type=existing.scope_type,
        scope_id=existing.scope_id,
        require_write=True,
        persona_key=persona_key,
    )
    updated = await svc.update_draft(
        existing.bundle_id,
        name=payload.name,
        version=payload.version,
        description=payload.description,
        author=payload.author,
        maintainers=payload.maintainers,
        license_name=payload.license,
        declared_slots=(
            [PackSlotSpec(**s.model_dump()) for s in payload.declared_slots]
            if payload.declared_slots is not None
            else None
        ),
        quick_actions=(
            [PackQuickActionSpec(**q.model_dump()) for q in payload.quick_actions]
            if payload.quick_actions is not None
            else None
        ),
        instance=str(request.url.path),
    )
    return serialize_draft_detail(updated, trace_id=trace_id_for(request))


@router.put("/{draft_id}/members", response_model=PackDraftDetailResponse)
async def set_pack_draft_members(
    draft_id: DraftIdPath,
    payload: SetPackDraftMembersRequest,
    request: Request,
    svc: ComposerSvcDep,
    persona_key: PersonaQuery = None,
) -> PackDraftDetailResponse:
    """Atomically set `pack_draft_memberships` resolving all 8 typed surrogate UUID FKs."""
    existing = await svc.get_draft(draft_id, include_closure=False, instance=str(request.url.path))
    user, _ = await enforce_composer_scope_access(
        request,
        scope_type=existing.scope_type,
        scope_id=existing.scope_id,
        require_write=True,
        persona_key=persona_key,
    )
    trace_id = trace_id_for(request)
    updated = await svc.set_members(
        existing.bundle_id,
        [
            PackDraftMemberInput(
                entity_type=PackDraftEntityType(m.entity_type),
                entity_id=m.entity_id,
                entity_slug=m.entity_slug,
            )
            for m in payload.members
        ],
        actor_id=user.id,
        actor_email=user.email,
        trace_id=trace_id,
        instance=str(request.url.path),
    )
    hydrated = await svc.get_draft(
        updated.bundle_id, include_closure=True, instance=str(request.url.path)
    )
    return serialize_draft_detail(hydrated, trace_id=trace_id)


@router.delete("/{draft_id}", response_model=PackDraftDeleteResponse)
async def delete_pack_draft(
    draft_id: DraftIdPath,
    request: Request,
    svc: ComposerSvcDep,
    persona_key: PersonaQuery = None,
) -> PackDraftDeleteResponse:
    """Delete a `CUSTOM` `DRAFT` bundle (`ON DELETE CASCADE` on `pack_draft_memberships`)."""
    existing = await svc.get_draft(draft_id, include_closure=False, instance=str(request.url.path))
    user, _ = await enforce_composer_scope_access(
        request,
        scope_type=existing.scope_type,
        scope_id=existing.scope_id,
        require_write=True,
        persona_key=persona_key,
    )
    trace_id = trace_id_for(request)
    deleted = await svc.delete_draft(
        existing.bundle_id,
        actor_id=user.id,
        actor_email=user.email,
        trace_id=trace_id,
        instance=str(request.url.path),
    )
    return PackDraftDeleteResponse(
        bundle_id=deleted["bundle_id"],
        slug=deleted["slug"],
        version=deleted["version"],
        deleted=True,
        trace_id=trace_id,
    )
