"""Guarded DELETE endpoints for Workflow v2 & VSM v2 (`Story 31.5`, `<= 120 L`)."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Query, Request

from orcia_api.dependencies import get_vsm_v2_sql_store, get_workflows_v2_sql_store
from orcia_api.dependencies._core_providers import get_configured_db_engine
from orcia_api.routers._entity_delete_rbac import (
    build_wf_vsm_target_authorizer,
    prepare_entity_delete_guards,
)
from orcia_api.routers.auth import PROBLEM_RESPONSES
from orcia_api.schemas._pack_composer import GuardedEntityDeleteResponse
from orcia_core.permissions.errors import ResourceNotFoundError
from orcia_core.storage.entity_delete_tx import delete_entity_guarded_tx
from orcia_core.workflows import SqlVsmDefinitionsV2Store, SqlWorkflowDefinitionsV2Store

delete_router = APIRouter(responses=PROBLEM_RESPONSES)
PersonaQuery = Annotated[str | None, Query(min_length=1, max_length=64)]


@delete_router.delete(
    "/api/v1/workflows/v2/{workflow_id}", response_model=GuardedEntityDeleteResponse
)
async def delete_workflow_v2_endpoint(
    workflow_id: str,
    request: Request,
    sql_store: Annotated[SqlWorkflowDefinitionsV2Store, Depends(get_workflows_v2_sql_store)],
    unlink_from_draft_packs: bool = Query(default=False),
    persona_key: PersonaQuery = None,
) -> GuardedEntityDeleteResponse:
    """Delete a Workflow v2 with RBAC, immutability & `409` anti-hostage guard."""
    inst = str(request.url.path)
    user, auth_svc, trace_id, authorize_draft = await prepare_entity_delete_guards(
        request, persona_key=persona_key
    )
    engine = get_configured_db_engine(request)
    if engine is None:
        raise ResourceNotFoundError(
            detail_override=f"Workflow '{workflow_id}' not found.",
            instance=inst,
        )
    outcome = await delete_entity_guarded_tx(
        engine,
        entity_type="WORKFLOW_V2",
        entity_id_or_key=workflow_id,
        unlink_from_draft_packs=unlink_from_draft_packs,
        authorize_target_cb=build_wf_vsm_target_authorizer(auth_svc, user, instance=inst),
        authorize_draft_cb=authorize_draft,
        actor_id=user.id,
        actor_email=user.email,
        trace_id=trace_id,
        instance=inst,
    )
    mem = getattr(sql_store, "_memory_fallback", None)
    if isinstance(mem, dict):
        for k in [k for k in list(mem.keys()) if k.startswith(f"{outcome.deleted_id}:")]:
            mem.pop(k, None)
    return GuardedEntityDeleteResponse(
        entity_type=outcome.entity_type,
        deleted_id=outcome.deleted_id,
        deleted_uuid=outcome.deleted_uuid,
        unlinked_draft_packs=list(outcome.unlinked_draft_packs),
        trace_id=trace_id,
    )


@delete_router.delete("/api/v1/vsm/{vsm_id}", response_model=GuardedEntityDeleteResponse)
async def delete_vsm_v2_endpoint(
    vsm_id: str,
    request: Request,
    vsm_store: Annotated[SqlVsmDefinitionsV2Store, Depends(get_vsm_v2_sql_store)],
    unlink_from_draft_packs: bool = Query(default=False),
    persona_key: PersonaQuery = None,
) -> GuardedEntityDeleteResponse:
    """Delete a VSM v2 with RBAC, immutability & `409` anti-hostage guard."""
    inst = str(request.url.path)
    user, auth_svc, trace_id, authorize_draft = await prepare_entity_delete_guards(
        request, persona_key=persona_key
    )
    engine = get_configured_db_engine(request)
    if engine is None:
        raise ResourceNotFoundError(
            detail_override=f"VSM '{vsm_id}' not found.",
            instance=inst,
        )
    outcome = await delete_entity_guarded_tx(
        engine,
        entity_type="VSM_V2",
        entity_id_or_key=vsm_id,
        unlink_from_draft_packs=unlink_from_draft_packs,
        authorize_target_cb=build_wf_vsm_target_authorizer(auth_svc, user, instance=inst),
        authorize_draft_cb=authorize_draft,
        actor_id=user.id,
        actor_email=user.email,
        trace_id=trace_id,
        instance=inst,
    )
    mem = getattr(vsm_store, "_memory_fallback", None)
    if isinstance(mem, dict):
        mem.pop(outcome.deleted_id, None)
    return GuardedEntityDeleteResponse(
        entity_type=outcome.entity_type,
        deleted_id=outcome.deleted_id,
        deleted_uuid=outcome.deleted_uuid,
        unlinked_draft_packs=list(outcome.unlinked_draft_packs),
        trace_id=trace_id,
    )
