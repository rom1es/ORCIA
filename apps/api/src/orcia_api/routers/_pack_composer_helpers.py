"""Scope guards, serializers & export helpers for Pack Composer (`Story 31.5`, `<= 220 L`)."""

from __future__ import annotations

import re

from fastapi import Request, Response

from orcia_api.dependencies import get_auth_service
from orcia_api.routers._finops_auth_guards import enforce_observer_headers_guard
from orcia_api.routers._finops_scope_guards import (
    sync_evaluator_topology_from_pg,
    user_governs_org_unit,
)
from orcia_api.routers._workspace_packs_guards import enforce_workspace_packs_access, trace_id_for
from orcia_api.routers.auth import resolve_request_user
from orcia_api.schemas._pack_composer import (
    ClosureMissingDependencyResponse,
    PackClosureReportResponse,
    PackComposerQuickActionSchema,
    PackComposerSlotSchema,
    PackDraftDetailResponse,
    PackDraftMemberResponse,
    ProseLintWarningResponse,
)
from orcia_core.packs import (
    PackClosureReport,
    PackComposerService,
    PackDraftDetail,
    PackScopeEscalationForbiddenError,
)
from orcia_core.permissions.errors import ObserverModeReadOnlyError, ScopeAccessDeniedError
from orcia_core.permissions.models import UserIdentity


async def compute_caller_composer_scopes(
    request: Request,
    *,
    persona_key: str | None = None,
) -> tuple[UserIdentity, bool, frozenset[str], frozenset[str]]:
    """Compute caller identity, admin flag, authorized workspaces & authorized org units."""
    user = resolve_request_user(request, persona_key=persona_key)
    auth_svc = get_auth_service(request)
    await sync_evaluator_topology_from_pg(request, auth_svc)
    is_admin = user.platform_role == "PLATFORM_ADMIN" or "PLATFORM_ADMIN" in user.roles
    allowed_ws: set[str] = set()
    for acc in auth_svc.evaluator.resolve_accessible_workspaces(user):
        ws = acc.workspace
        if ws.ui_visibility_mode == "PRIVATE_USER" and (
            ws.personal_owner_user_id is None or str(ws.personal_owner_user_id) != str(user.id)
        ):
            continue
        allowed_ws.add(ws.id)
    allowed_orgs: set[str] = {
        *(str(x) for x in (user.primary_org_unit_id, *user.transverse_groups) if x)
    }
    for ou in auth_svc.evaluator.org_units:
        if user.id in ou.lead_user_ids or ou.lead_user_id == user.id:
            allowed_orgs.add(ou.id)
            allowed_orgs.update(auth_svc.evaluator.get_descendant_org_unit_ids(ou.id))
    return user, is_admin, frozenset(allowed_ws), frozenset(allowed_orgs)


async def enforce_composer_scope_access(
    request: Request,
    *,
    scope_type: str,
    scope_id: str,
    require_write: bool,
    persona_key: str | None = None,
) -> tuple[UserIdentity, str]:
    """Enforce `ScopeAccessGuard` and `READ_ONLY_OBSERVER` checks on composer scopes."""
    path = str(request.url.path)
    st = scope_type.strip().upper()
    if st == "WORKSPACE":
        return await enforce_workspace_packs_access(
            request, scope_id, require_write=require_write, persona_key=persona_key
        )
    user = resolve_request_user(request, persona_key=persona_key)
    if require_write:
        enforce_observer_headers_guard(request, user)
        if (
            user.platform_role in ("OBSERVER", "READ_ONLY_OBSERVER", "BU_DIRECTOR")
            or "OBSERVER" in user.roles
            or "READ_ONLY_OBSERVER" in user.roles
        ):
            raise ObserverModeReadOnlyError(instance=path)
    if st == "GLOBAL":
        if require_write:
            raise PackScopeEscalationForbiddenError(
                detail_override="Composer mutations cannot target GLOBAL packs.",
                instance=path,
            )
        return user, scope_id
    auth_svc = get_auth_service(request)
    await sync_evaluator_topology_from_pg(request, auth_svc)
    is_admin = user.platform_role == "PLATFORM_ADMIN" or "PLATFORM_ADMIN" in user.roles
    if not is_admin:
        if require_write:
            if not user_governs_org_unit(auth_svc, user, scope_id):
                raise ScopeAccessDeniedError(instance=path)
        else:
            _, _, allowed_ws, allowed_orgs = await compute_caller_composer_scopes(
                request, persona_key=persona_key
            )
            desc = {scope_id, *auth_svc.evaluator.get_descendant_org_unit_ids(scope_id)}
            has_ws_under = any(
                (ws := auth_svc.evaluator.get_workspace(ws_id)) is not None
                and ws.owner_org_unit_id in desc
                for ws_id in allowed_ws
            )
            if scope_id not in allowed_orgs and not has_ws_under:
                raise ScopeAccessDeniedError(instance=path)
    return user, scope_id


def serialize_closure_report(report: PackClosureReport | None) -> PackClosureReportResponse | None:
    """Serialize domain `PackClosureReport` into OpenAPI response schema."""
    if report is None:
        return None
    return PackClosureReportResponse(
        complete=report.complete,
        missing_dependencies=[
            ClosureMissingDependencyResponse(**m.model_dump()) for m in report.missing_dependencies
        ],
        non_active_dependencies=[
            ClosureMissingDependencyResponse(**m.model_dump())
            for m in report.non_active_dependencies
        ],
        prose_lint_warnings=[
            ProseLintWarningResponse(**w.model_dump()) for w in report.prose_lint_warnings
        ],
        auto_included_count=report.auto_included_count,
    )


def serialize_draft_detail(detail: PackDraftDetail, *, trace_id: str) -> PackDraftDetailResponse:
    """Serialize domain `PackDraftDetail` into OpenAPI response schema."""
    return PackDraftDetailResponse(
        bundle_id=detail.bundle_id,
        pack_id=detail.pack_id,
        slug=detail.slug,
        name=detail.name,
        version=detail.version,
        description=detail.description,
        author=detail.author,
        maintainers=list(detail.maintainers),
        license=detail.license,
        bundle_kind=detail.bundle_kind,
        scope_type=detail.scope_type,
        scope_id=detail.scope_id,
        status=detail.status,
        source_origin=detail.source_origin,
        archive_sha256=detail.archive_sha256,
        cas_object_key=detail.cas_object_key,
        declared_slots=[
            PackComposerSlotSchema(**s.model_dump(mode="json")) for s in detail.declared_slots
        ],
        quick_actions=[
            PackComposerQuickActionSchema(**q.model_dump(mode="json")) for q in detail.quick_actions
        ],
        members=[PackDraftMemberResponse(**m.model_dump(mode="json")) for m in detail.members],
        closure=serialize_closure_report(detail.closure),
        created_by_user_id=detail.created_by_user_id,
        published_at_iso=detail.published_at_iso,
        updated_at_iso=detail.updated_at_iso,
        trace_id=trace_id,
    )


async def execute_export_pack_zip_handler(
    bundle_id: str,
    *,
    request: Request,
    svc: PackComposerService,
    auto_include_dependencies: bool = False,
    persona_key: str | None = None,
) -> Response:
    """Guard, run closure + O(1) scrub/scan, and return deterministic `.zip` archive."""
    detail = await svc.get_draft(bundle_id, include_closure=False, instance=str(request.url.path))
    mutates_draft = bool(
        auto_include_dependencies and detail.bundle_kind == "CUSTOM" and detail.status == "DRAFT"
    )
    await enforce_composer_scope_access(
        request,
        scope_type=detail.scope_type,
        scope_id=detail.scope_id,
        require_write=mutates_draft,
        persona_key=persona_key,
    )
    res = await svc.export_bundle(
        detail.bundle_id,
        auto_include_dependencies=auto_include_dependencies,
        instance=str(request.url.path),
    )
    safe_slug = re.sub(r"[^A-Za-z0-9_.-]+", "-", res.slug).strip("-") or "pack"
    safe_ver = re.sub(r"[^A-Za-z0-9_.-]+", "-", res.version).strip("-") or "1.0.0"
    filename = f"{safe_slug}-{safe_ver}.zip"
    return Response(
        content=res.zip_bytes,
        media_type="application/zip",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"',
            "X-Orcia-Archive-Sha256": res.archive_sha256,
            "X-Orcia-Lockfile-Bundle-Sha256": res.lockfile_bundle_sha256,
            "X-Orcia-Included-Dependencies-Count": str(res.included_dependencies_count),
            "X-Orcia-Prose-Lint-Warnings-Count": str(len(res.prose_lint_warnings)),
            "X-Trace-Id": trace_id_for(request),
        },
    )


__all__ = [
    "compute_caller_composer_scopes",
    "enforce_composer_scope_access",
    "execute_export_pack_zip_handler",
    "serialize_closure_report",
    "serialize_draft_detail",
]
