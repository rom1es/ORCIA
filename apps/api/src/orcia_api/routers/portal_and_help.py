"""Epic 9 Portal Router: Two-Speed Federated Search (`GET /api/v1/search`),
User Preferences / Personal MCP Tokens & Hybrid Contextual Help (`AD-8`, `AD-14`, `AD-19`).
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Path, Query, Request

from orcia_api.dependencies import (
    get_auth_service,
    get_contextual_help_service,
    get_optional_embedding_port,
    get_two_speed_search_service,
)
from orcia_api.dependencies._core_providers import get_configured_db_engine
from orcia_api.routers._entity_delete_rbac import (
    build_catalog_target_authorizer,
    prepare_entity_delete_guards,
)
from orcia_api.routers._finops_scope_guards import sync_evaluator_topology_from_pg
from orcia_api.routers.auth import PROBLEM_RESPONSES, resolve_request_user
from orcia_api.schemas._pack_composer import GuardedEntityDeleteResponse
from orcia_api.schemas.catalog import (
    ContextualHelpPublishRequest,
    ContextualHelpResolveResponse,
    ContextualHelpRollbackRequest,
    HelpArticleSchemaItem,
)
from orcia_api.schemas.ontology_and_rag import (
    TwoSpeedSearchHitSchemaItem,
    TwoSpeedSearchResponse,
)
from orcia_core.catalog.contextual_help import HelpArticleCatalogItem
from orcia_core.observability.logging import get_current_trace_id
from orcia_core.orchestration import delete_catalog_item_guarded
from orcia_core.permissions.errors import ResourceNotFoundError
from orcia_core.ports.embedding import EmbeddingPort
from orcia_core.rag import FederatedSearchCandidate, load_federated_search_candidates_pg18

router = APIRouter(prefix="/api/v1", tags=["portal-and-help"])


def _trace(request: Request) -> str:
    return str(getattr(request.state, "trace_id", None) or get_current_trace_id())


def _serialize_help_article(art: HelpArticleCatalogItem) -> HelpArticleSchemaItem:
    return HelpArticleSchemaItem(
        resource_id=art.resource_id,
        uri=art.uri,
        title=art.title,
        version=art.version,
        lang=art.lang,
        layer=art.layer,
        pack_name=art.pack_name,
        bound_routes=list(art.bound_routes),
        summary_what_for=art.summary_what_for,
        step_by_step_items=list(art.step_by_step_items),
        key_terms_items=list(art.key_terms_items),
        faq_items=list(art.faq_items),
        real_example_text=art.real_example_text,
        common_pitfalls_items=list(art.common_pitfalls_items),
        cas_key=art.cas_key,
        sha256=art.sha256,
        markdown_body=art.markdown_body,
        item_type=art.item_type,
        previous_version=art.previous_version,
        previous_cas_key=art.previous_cas_key,
    )


@router.get(
    "/search",
    response_model=TwoSpeedSearchResponse,
    summary="Execute 2-Speed Federated & Contextual Search (`⌘K`, Zero Layout Shift, `Story 9.3`)",
    responses=PROBLEM_RESPONSES,
)
async def execute_two_speed_federated_search(
    request: Request,
    _embedding_port: Annotated[EmbeddingPort | None, Depends(get_optional_embedding_port)],
    q: str = Query(default="", max_length=256),
    scope: Literal["SCREEN", "WORKSPACE", "ALL_WORKSPACES", "GLOBAL", "CONTEXTUAL"] = Query(
        default="WORKSPACE"
    ),
    workspace_id: str | None = Query(default=None, max_length=128),
    screen_route: str = Query(default="/cockpit", min_length=1, max_length=128),
    include_speed2: bool = Query(default=True),
    force_semantic: bool = Query(default=False),
    locale: str | None = Query(default=None, max_length=16),
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> TwoSpeedSearchResponse:
    user = resolve_request_user(request, persona_key=persona_key)
    svc = get_two_speed_search_service(request)
    normalized_scope: Literal["SCREEN", "WORKSPACE", "ALL_WORKSPACES"]
    if scope == "GLOBAL":
        normalized_scope = "ALL_WORKSPACES"
    elif scope == "CONTEXTUAL":
        normalized_scope = "WORKSPACE"
    else:
        normalized_scope = scope
    effective_ws = (workspace_id or "").strip() or "scope-global"

    raw_locale = (
        ((locale or "").strip() or (request.headers.get("accept-language") or "").strip() or "fr")
        .lower()
        .replace("_", "-")
    )
    req_locale = "en" if raw_locale.split(",", 1)[0].split("-", 1)[0].strip() == "en" else "fr"

    effective_include_speed2 = include_speed2 and (_embedding_port is not None)
    query_embedding: tuple[float, ...] | None = None
    if (
        _embedding_port is not None
        and effective_include_speed2
        and q.strip()
        and (force_semantic or len(q.strip().split()) >= 3)
    ):
        vectors = await _embedding_port.embed([q])
        if vectors:
            query_embedding = tuple(vectors[0])

    extra_candidates: tuple[FederatedSearchCandidate, ...] = ()
    engine = get_configured_db_engine(request)
    if engine is not None:
        async with engine.connect() as conn:
            extra_candidates = await load_federated_search_candidates_pg18(
                conn,
                user_id=user.id,
                user_role=user.platform_role,
                primary_org_unit_id=user.primary_org_unit_id,
                locale=req_locale,
            )

    auth_svc = get_auth_service(request)
    await sync_evaluator_topology_from_pg(request, auth_svc)
    authorized_ws_ids: set[str] = set()
    restricted_ws_ids: set[str] = set()
    for ws in auth_svc.evaluator.workspaces:
        is_restricted = (
            ws.visibility_mode == "CONFIDENTIAL_RESTRICTED"
            or ws.ui_visibility_mode == "PRIVATE_USER"
            or ws.personal_owner_user_id is not None
        )
        if is_restricted:
            restricted_ws_ids.add(ws.id)
            restricted_ws_ids.add(ws.slug)
        if auth_svc.evaluator.resolve_workspace_access(user, ws.id) is not None:
            authorized_ws_ids.add(ws.id)
            authorized_ws_ids.add(ws.slug)

    report = await svc.execute_search_async(
        query=q,
        scope=normalized_scope,
        active_workspace_id=effective_ws,
        active_screen_route=screen_route,
        user_id=user.id,
        user_role=user.platform_role,
        locale=req_locale,
        include_speed2=effective_include_speed2,
        force_semantic=force_semantic,
        query_embedding=query_embedding,
        extra_candidates=extra_candidates,
        authorized_workspace_ids=authorized_ws_ids,
        restricted_workspace_ids=restricted_ws_ids,
    )
    return TwoSpeedSearchResponse(
        query=report.query,
        scope=report.scope,
        hits=[TwoSpeedSearchHitSchemaItem(**asdict(h)) for h in report.hits],
        speed1_llm_cost_usd=report.speed1_llm_cost_usd,
        speed2_executed=report.speed2_executed,
        speed2_cache_hit=report.speed2_cache_hit,
        speed2_redis_key=report.speed2_redis_key,
        speed2_cache_ttl_seconds=report.speed2_cache_ttl_seconds,
        trace_id=_trace(request),
    )


@router.get(
    "/help/resolve",
    response_model=ContextualHelpResolveResponse,
    summary="Resolve Contextual Help (`< 10 ms` Redis + 4-layer merge, `Story 9.5`)",
    responses=PROBLEM_RESPONSES,
)
async def resolve_contextual_help(
    request: Request,
    route: str = Query(default="/mes-espaces/$id/sources", min_length=1, max_length=256),
    pack: str = Query(default="core", min_length=1, max_length=128),
    lang: Literal["fr", "en"] = Query(default="fr"),
) -> ContextualHelpResolveResponse:
    svc = get_contextual_help_service(request)
    res = await svc.resolve_for_route_async(route=route, pack=pack, lang=lang)
    return ContextualHelpResolveResponse(
        route=res.route,
        pack=res.pack,
        lang=res.lang,
        redis_cache_key=res.redis_cache_key,
        cache_hit=res.cache_hit,
        merged_layers=list(res.merged_layers),
        active_article=_serialize_help_article(res.active_article),
        rollback_available=res.rollback_available,
        ask_assistant_prefill=res.ask_assistant_prefill,
        is_autonomous_generated=res.is_autonomous_generated,
        run_id=res.run_id,
        contract_label=res.contract_label,
        trigger_label=res.trigger_label,
        previous_version_available=res.previous_version_available or res.rollback_available,
        trace_id=_trace(request),
    )


@router.post(
    "/help/publish",
    response_model=HelpArticleSchemaItem,
    summary="Publish a hot `@v(N+1)` contextual help article in `cas/<sha256>` (`Story 9.5`)",
    responses=PROBLEM_RESPONSES,
)
async def publish_hot_contextual_help(
    request: Request,
    body: ContextualHelpPublishRequest,
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> HelpArticleSchemaItem:
    resolve_request_user(request, persona_key=persona_key)
    svc = get_contextual_help_service(request)
    updated = await svc.publish_hot_version_async(
        resource_id=body.resource_id,
        new_version=body.new_version,
        new_title=body.new_title,
        new_summary_what_for=body.new_summary_what_for,
        new_markdown_body=body.new_markdown_body,
        layer=body.layer,
    )
    return _serialize_help_article(updated)


@router.post(
    "/help/rollback",
    response_model=HelpArticleSchemaItem,
    summary="Execute 1-click `⏪ Rollback` to `@v(N-1)` for a `HELP_ARTICLE` (`Story 9.5`)",
    responses=PROBLEM_RESPONSES,
)
async def rollback_contextual_help(
    request: Request,
    body: ContextualHelpRollbackRequest,
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> HelpArticleSchemaItem:
    resolve_request_user(request, persona_key=persona_key)
    svc = get_contextual_help_service(request)
    restored = await svc.rollback_to_previous_version_async(body.resource_id)
    return _serialize_help_article(restored)


@router.delete(
    "/help/{article_id}",
    response_model=GuardedEntityDeleteResponse,
    summary="Delete a standalone HELP_ARTICLE catalog item with anti-hostage draft guard",
    responses=PROBLEM_RESPONSES,
)
async def delete_help_article_endpoint(
    request: Request,
    article_id: str = Path(..., min_length=1, max_length=128),
    unlink_from_draft_packs: bool = Query(default=False),
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> GuardedEntityDeleteResponse:
    """Delete standalone `HELP_ARTICLE` row with RBAC, immutability & draft-unlink guard."""
    inst = str(request.url.path)
    user, auth_svc, trace_id, authorize_draft = await prepare_entity_delete_guards(
        request, persona_key=persona_key
    )
    engine = get_configured_db_engine(request)
    if engine is None:
        raise ResourceNotFoundError(
            detail_override=f"HELP_ARTICLE '{article_id}' not found.",
            instance=inst,
        )
    target_uuid, unlinked = await delete_catalog_item_guarded(
        engine,
        article_id,
        "HELP_ARTICLE",
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
        entity_type="HELP_ARTICLE",
        deleted_id=article_id,
        deleted_uuid=target_uuid,
        unlinked_draft_packs=unlinked,
        trace_id=trace_id,
    )
