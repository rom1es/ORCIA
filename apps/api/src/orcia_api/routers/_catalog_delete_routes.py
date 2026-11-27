"""Guarded DELETE endpoint for standalone Catalog Instructions (`Story 31.5`, `<= 65 L`)."""

from __future__ import annotations

from fastapi import APIRouter, Path, Query, Request

from orcia_api.dependencies._core_providers import get_configured_db_engine
from orcia_api.routers._entity_delete_rbac import (
    build_catalog_target_authorizer,
    prepare_entity_delete_guards,
)
from orcia_api.routers.auth import PROBLEM_RESPONSES
from orcia_api.schemas._pack_composer import GuardedEntityDeleteResponse
from orcia_core.orchestration import delete_catalog_item_guarded
from orcia_core.permissions.errors import ResourceNotFoundError

router = APIRouter(prefix="/api/v1/catalog", tags=["federated-catalog"])


@router.delete(
    "/instructions/{instruction_id}",
    response_model=GuardedEntityDeleteResponse,
    summary="Delete a standalone INSTRUCTION catalog asset with anti-hostage pack-draft guard",
    responses=PROBLEM_RESPONSES,
)
async def delete_catalog_instruction_endpoint(
    request: Request,
    instruction_id: str = Path(..., min_length=1, max_length=128),
    unlink_from_draft_packs: bool = Query(default=False),
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> GuardedEntityDeleteResponse:
    """Delete standalone `INSTRUCTION` row with RBAC, immutability & draft-unlink guard."""
    inst = str(request.url.path)
    user, auth_svc, trace_id, authorize_draft = await prepare_entity_delete_guards(
        request, persona_key=persona_key
    )
    engine = get_configured_db_engine(request)
    if engine is None:
        raise ResourceNotFoundError(
            detail_override=f"INSTRUCTION '{instruction_id}' not found.",
            instance=inst,
        )
    target_uuid, unlinked = await delete_catalog_item_guarded(
        engine,
        instruction_id,
        "INSTRUCTION",
        unlink_from_draft_packs=unlink_from_draft_packs,
        authorize_target_cb=build_catalog_target_authorizer(auth_svc, user, instance=inst),
        authorize_draft_cb=authorize_draft,
        raise_if_missing=True,
        actor_id=user.id,
        actor_email=user.email,
        trace_id=trace_id,
        instance=inst,
    )
    return GuardedEntityDeleteResponse(
        entity_type="INSTRUCTION",
        deleted_id=instruction_id,
        deleted_uuid=target_uuid,
        unlinked_draft_packs=unlinked,
        trace_id=trace_id,
    )


__all__ = ["router"]
