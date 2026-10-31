"""Epic 9 Portal Router: Two-Speed Federated Search (`GET /api/v1/search`),
User Preferences / Personal MCP Tokens & Hybrid Contextual Help (`AD-8`, `AD-14`, `AD-19`).
"""

from __future__ import annotations

from dataclasses import asdict
from typing import Literal

from fastapi import APIRouter, Query, Request

from orcia_api.dependencies import (
    get_contextual_help_service,
    get_two_speed_search_service,
    get_user_preferences_and_mcp_token_service,
)
from orcia_api.routers.auth import PROBLEM_RESPONSES, resolve_request_user
from orcia_api.schemas.auth_and_org import (
    McpPersonalTokenCreateRequest,
    McpPersonalTokenIssuedResponse,
    McpPersonalTokenListResponse,
    McpPersonalTokenMetadataItem,
    UserPreferencesResponse,
    UserPreferencesUpdateRequest,
)
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
from orcia_core.permissions.user_preferences_and_mcp_tokens import ScopedMcpPersonalTokenRecord

router = APIRouter(prefix="/api/v1", tags=["portal-and-help"])


def _trace(request: Request) -> str:
    return str(getattr(request.state, "trace_id", None) or get_current_trace_id())


def _serialize_mcp_token_record(rec: ScopedMcpPersonalTokenRecord) -> McpPersonalTokenMetadataItem:
    return McpPersonalTokenMetadataItem(
        token_id=rec.token_id,
        user_id=rec.user_id,
        label=rec.label,
        token_prefix=rec.token_prefix,
        token_sha256=rec.token_sha256,
        expires_in_days=rec.expires_in_days,
        rpm_limit=rec.rpm_limit,
        allowed_workspace_slugs=list(rec.allowed_workspace_slugs),
        exposed_capabilities=list(rec.exposed_capabilities),
        target_kind=rec.target_kind,
        target_slug=rec.target_slug,
        mcp_endpoint_uri=rec.mcp_endpoint_uri,
        ide_json_snippet=rec.ide_json_snippet,
        revoked=rec.revoked,
    )


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
    q: str = Query(default="", max_length=256),
    scope: Literal["SCREEN", "WORKSPACE", "ALL_WORKSPACES"] = Query(default="WORKSPACE"),
    workspace_id: str = Query(default="ws-claims-alpha", min_length=1, max_length=128),
    screen_route: str = Query(default="/cockpit", min_length=1, max_length=128),
    include_speed2: bool = Query(default=True),
    force_semantic: bool = Query(default=False),
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> TwoSpeedSearchResponse:
    user = resolve_request_user(request, persona_key=persona_key)
    svc = get_two_speed_search_service(request)
    report = svc.execute_search(
        query=q,
        scope=scope,
        active_workspace_id=workspace_id,
        active_screen_route=screen_route,
        user_role=user.platform_role,
        include_speed2=include_speed2,
        force_semantic=force_semantic,
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
    "/users/me/preferences",
    response_model=UserPreferencesResponse,
    summary="Get current user's display & workspace preferences (`Story 9.4`)",
    responses=PROBLEM_RESPONSES,
)
async def get_my_preferences(
    request: Request,
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> UserPreferencesResponse:
    user = resolve_request_user(request, persona_key=persona_key)
    svc = get_user_preferences_and_mcp_token_service(request)
    prefs = svc.get_preferences(user.id)
    return UserPreferencesResponse(**asdict(prefs), trace_id=_trace(request))


@router.patch(
    "/users/me/preferences",
    response_model=UserPreferencesResponse,
    summary="Synchronize user preferences (`0 ms` Anti-FOUC background sync, `Story 9.4`)",
    responses=PROBLEM_RESPONSES,
)
async def patch_my_preferences(
    request: Request,
    body: UserPreferencesUpdateRequest,
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> UserPreferencesResponse:
    user = resolve_request_user(request, persona_key=persona_key)
    svc = get_user_preferences_and_mcp_token_service(request)
    prefs = svc.update_preferences(
        user_id=user.id,
        theme=body.theme,
        locale=body.locale,
        default_hat=body.default_hat,
        auto_open_contextual_help=body.auto_open_contextual_help,
        notifications_enabled=body.notifications_enabled,
    )
    return UserPreferencesResponse(**asdict(prefs), trace_id=_trace(request))


@router.get(
    "/users/me/mcp-tokens",
    response_model=McpPersonalTokenListResponse,
    summary="List personal IDE/MCP tokens (`pat_mcp_*` SHA-256 metadata, `Story 9.4`)",
    responses=PROBLEM_RESPONSES,
)
async def list_my_mcp_tokens(
    request: Request,
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> McpPersonalTokenListResponse:
    user = resolve_request_user(request, persona_key=persona_key)
    svc = get_user_preferences_and_mcp_token_service(request)
    records = svc.list_user_mcp_tokens(user.id)
    return McpPersonalTokenListResponse(
        tokens=[_serialize_mcp_token_record(r) for r in records],
        trace_id=_trace(request),
    )


@router.post(
    "/users/me/mcp-tokens",
    response_model=McpPersonalTokenIssuedResponse,
    summary="Issue a scoped personal IDE/MCP token (`pat_mcp_*` hashed SHA-256, `Story 9.4`)",
    responses=PROBLEM_RESPONSES,
)
async def create_my_mcp_token(
    request: Request,
    body: McpPersonalTokenCreateRequest,
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> McpPersonalTokenIssuedResponse:
    user = resolve_request_user(request, persona_key=persona_key)
    svc = get_user_preferences_and_mcp_token_service(request)
    issued = svc.issue_mcp_token(
        user_id=user.id,
        label=body.label,
        expires_in_days=body.expires_in_days,
        rpm_limit=body.rpm_limit,
        allowed_workspace_slugs=tuple(body.allowed_workspace_slugs),
        exposed_capabilities=tuple(body.exposed_capabilities),
        target_kind=body.target_kind,
        target_slug=body.target_slug,
    )
    return McpPersonalTokenIssuedResponse(
        plaintext_token=issued.plaintext_token,
        record=_serialize_mcp_token_record(issued.record),
        trace_id=_trace(request),
    )


@router.delete(
    "/users/me/mcp-tokens/{token_id}",
    response_model=McpPersonalTokenMetadataItem,
    summary="Revoke a personal IDE/MCP token in `< 10 ms` Redis (`Story 9.4`)",
    responses=PROBLEM_RESPONSES,
)
async def revoke_my_mcp_token(
    request: Request,
    token_id: str,
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> McpPersonalTokenMetadataItem:
    user = resolve_request_user(request, persona_key=persona_key)
    svc = get_user_preferences_and_mcp_token_service(request)
    revoked = svc.revoke_mcp_token(user_id=user.id, token_id=token_id)
    return _serialize_mcp_token_record(revoked)


@router.get(
    "/help/resolve",
    response_model=ContextualHelpResolveResponse,
    summary="Resolve Contextual Help (`< 10 ms` Redis + 4-layer merge, `Story 9.5`)",
    responses=PROBLEM_RESPONSES,
)
async def resolve_contextual_help(
    request: Request,
    route: str = Query(default="/mes-espaces/$id/sources", min_length=1, max_length=256),
    pack: str = Query(default="orcia-pack-sdlc", min_length=1, max_length=128),
    lang: Literal["fr", "en"] = Query(default="fr"),
) -> ContextualHelpResolveResponse:
    svc = get_contextual_help_service(request)
    res = svc.resolve_for_route(route=route, pack=pack, lang=lang)
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
    updated = svc.publish_hot_version(
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
    restored = svc.rollback_to_previous_version(body.resource_id)
    return _serialize_help_article(restored)
