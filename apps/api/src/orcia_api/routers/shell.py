"""Direction C Shell navigation router (`/api/v1/navigation/shell`)."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request

from orcia_api.routers.auth import get_auth_service, resolve_request_user
from orcia_core.domain.exceptions import ObserverModeReadOnlyError, ResourceNotFoundError
from orcia_core.observability.logging import get_current_trace_id
from orcia_core.schemas.problem_details import ProblemDetails
from orcia_core.schemas.shell import (
    HumanProfileBadge,
    ShellNavigationResponse,
    build_default_shell_navigation,
)

router = APIRouter(prefix="/api/v1/navigation", tags=["navigation"])


@router.get(
    "/shell",
    response_model=ShellNavigationResponse,
    summary="Get Direction C 7-module Global Sidebar & Hierarchical Scope Switcher tree",
    responses={
        401: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
        403: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
        404: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
        422: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
    },
)
async def get_shell_navigation(
    request: Request,
    scope_id: str | None = Query(
        default=None,
        min_length=1,
        max_length=128,
        description="Optional active scope identifier to select in the 4-level scope tree.",
    ),
    require_contributor: bool = Query(
        default=False,
        description="When true, verifies the selected scope is not READ_ONLY_OBSERVER.",
    ),
    persona_key: str | None = Query(
        default=None,
        min_length=1,
        max_length=64,
        description="Optional persona key (`karim`, `claire`, `marc`, `nadia`, `partenaire`).",
    ),
    require_module: str | None = Query(
        default=None,
        min_length=1,
        max_length=32,
        description="Optional module key to enforce server-side RBAC module access (`HTTP 403`).",
    ),
) -> ShellNavigationResponse:
    """Return the 7-module Direction C navigation shell and 4-level scope switcher state."""
    trace_id: str = getattr(request.state, "trace_id", None) or get_current_trace_id()
    svc = get_auth_service(request)
    has_identity_context = bool(persona_key or request.headers.get("Authorization"))

    enabled_modules: dict[str, bool] | None = None
    custom_profile: HumanProfileBadge | None = None
    if has_identity_context:
        user = resolve_request_user(request, persona_key=persona_key)
        enabled_modules = svc.evaluator.evaluate_module_permissions(user)
        if require_module is not None:
            svc.evaluator.enforce_module_access(
                user, require_module, instance=str(request.url.path)
            )
        org_node = next(
            (u for u in svc.evaluator.org_units if u.id == user.primary_org_unit_id),
            None,
        )
        custom_profile = HumanProfileBadge(
            archetype_key=user.human_profile_archetype,
            display_name=user.display_name,
            access_mode=(
                "READ_ONLY_OBSERVER"
                if user.platform_role in ("OBSERVER", "BU_DIRECTOR")
                else "CONTRIBUTOR_ACTION_REQUIRED"
            ),
            role=user.platform_role,
            org_unit_id=user.primary_org_unit_id,
            org_unit_name=org_node.name if org_node else "",
        )
    elif require_module is not None:
        user = resolve_request_user(request, persona_key="marc")
        svc.evaluator.enforce_module_access(user, require_module, instance=str(request.url.path))

    default_nav = build_default_shell_navigation(
        trace_id=trace_id,
        enabled_modules=enabled_modules,
        human_profile=custom_profile,
    )

    if scope_id is None:
        selected_scope = next(s for s in default_nav.scopes if s.id == default_nav.active_scope_id)
    else:
        matched = [s for s in default_nav.scopes if s.id == scope_id]
        if not matched:
            raise ResourceNotFoundError(instance=str(request.url.path))
        selected_scope = matched[0]

    if require_contributor and (
        selected_scope.access_mode == "READ_ONLY_OBSERVER"
        or default_nav.human_profile.access_mode == "READ_ONLY_OBSERVER"
    ):
        raise ObserverModeReadOnlyError(instance=str(request.url.path))

    return ShellNavigationResponse(
        active_scope_id=selected_scope.id,
        scopes=default_nav.scopes,
        modules=default_nav.modules,
        human_profile=default_nav.human_profile,
        trace_id=trace_id,
    )
