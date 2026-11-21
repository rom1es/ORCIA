"""Platform Setup State (`GET`/`PUT /platform-setup-state`) with Admin Gating (`Story 26.1`)."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request
from fastapi.responses import JSONResponse
from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_api.dependencies import get_accostage_service, get_auth_service
from orcia_api.dependencies._core_providers import get_configured_db_engine
from orcia_api.routers._bootstrap_evaluator_sync import sync_setup_snapshot_to_evaluator
from orcia_api.routers._bootstrap_llm_routes import (
    raise_if_non_test_pg_error,
    trace_id_for_bootstrap,
)
from orcia_api.routers.auth import PROBLEM_RESPONSES, resolve_request_user
from orcia_api.schemas import bootstrap as bs
from orcia_core import bootstrap as bm
from orcia_core.bootstrap import (
    load_platform_setup_state_from_postgres18,
    save_platform_setup_state_to_postgres18,
    strip_snapshot_credentials,
)
from orcia_core.kernel.errors import ScopeAccessDeniedError
from orcia_core.observability.logging import get_logger
from orcia_kernel.ids import new_uuid7_str

logger = get_logger("orcia.api.bootstrap")
setup_state_router = APIRouter()


def _sync_accostage_from_snapshot(
    svc: bm.ProgressiveDay0AccostageService, snap: bm.PlatformSetupSnapshotRecord
) -> None:
    endpoints: list[bm.LlmModelEndpoint] = []
    for idx, t in enumerate(snap.llm_tiers):
        provider_raw = str(t.get("provider", t.get("modelFamily", "anthropic"))).strip().lower()
        family = (
            "anthropic"
            if "anthropic" in provider_raw or "claude" in provider_raw
            else "openai"
            if "openai" in provider_raw or "gpt" in provider_raw
            else "google"
            if "google" in provider_raw or "gemini" in provider_raw
            else "mistral"
            if "mistral" in provider_raw
            else provider_raw or "anthropic"
        )
        model_name = str(t.get("primaryModel") or t.get("model") or "").strip()
        if not model_name:
            continue
        custom_uri = str(t.get("endpointUrl", t.get("endpoint_uri", ""))).strip()
        endpoint_uri = (
            custom_uri
            if custom_uri.startswith(("http://", "https://"))
            else f"https://api.{family}.local/v1"
        )
        endpoints.append(
            bm.LlmModelEndpoint(
                id=str(t.get("id", "")).strip() or new_uuid7_str(),
                endpoint_key=str(t.get("tierKey", f"tier-{idx + 1}")).strip() or f"tier-{idx + 1}",
                provider_slug=provider_raw or family,
                model_family=family,
                model_name=model_name,
                endpoint_uri=endpoint_uri,
            )
        )
    svc.sync_platform_setup_snapshot(
        llm_endpoints=tuple(endpoints),
        has_org_unit=len(snap.org_units) > 0,
        has_workspace=len(snap.workspaces) > 0,
        has_datasource=len(snap.datasources) > 0,
        has_pilot_run=len(snap.runs) > 0 or len(snap.workflows) > 0,
    )


def _serialize_setup_snapshot(
    snap: bm.PlatformSetupSnapshotRecord, trace_id: str
) -> bs.PlatformSetupStateResponse:
    return bs.PlatformSetupStateResponse(
        first_admin_initialized=snap.first_admin_initialized,
        first_admin_email=snap.first_admin_email,
        first_admin_display_name=snap.first_admin_display_name,
        org_units=list(snap.org_units),
        rbac_grants=list(snap.rbac_grants),
        llm_tiers=strip_snapshot_credentials(list(snap.llm_tiers)),
        workspaces=list(snap.workspaces),
        datasources=strip_snapshot_credentials(list(snap.datasources)),
        packs=list(snap.packs),
        workflows=list(snap.workflows),
        runs=list(snap.runs),
        catalog_items=list(snap.catalog_items),
        ontology_concepts=list(snap.ontology_concepts),
        audit_events=list(snap.audit_events),
        trace_id=trace_id,
    )


def _has_caller_credentials(request: Request) -> bool:
    auth_svc = get_auth_service(request)
    raw_persona = request.query_params.get("persona_key")
    has_persona = (
        getattr(auth_svc, "allow_persona_impersonation", False) is True
        and isinstance(raw_persona, str)
        and bool(raw_persona.strip())
    )
    return bool(
        request.headers.get("Authorization")
        or getattr(request.state, "resolved_bearer_user", None) is not None
        or has_persona
    )


async def _build_public_setup_state_response(
    request: Request,
    svc: bm.ProgressiveDay0AccostageService,
    engine: AsyncEngine | None,
) -> JSONResponse:
    is_initialized = svc.first_admin is not None
    if engine is not None:
        try:
            db_admin = await bm.get_first_platform_admin_from_postgres18(
                engine, orcia_env=svc.orcia_env
            )
            svc.set_first_platform_admin_record(db_admin)
            is_initialized = db_admin is not None
            db_snap = await load_platform_setup_state_from_postgres18(
                engine, orcia_env=svc.orcia_env
            )
            if db_snap is not None:
                _sync_accostage_from_snapshot(svc, db_snap)
        except Exception as exc:
            logger.warning("bootstrap_public_setup_state_fallback", error_type=type(exc).__name__)
            raise_if_non_test_pg_error(exc, path=str(request.url.path))
    rep = svc.get_accostage_status(user_role="PLATFORM_ADMIN")
    step = (
        "READY"
        if (is_initialized and rep.completed_count >= rep.total_count)
        else (
            next((m.key for m in rep.visible_milestones if not m.completed), "READY")
            if is_initialized
            else "FIRST_ADMIN"
        )
    )
    public_payload = bs.PlatformSetupStatePublicResponse(
        is_initialized=is_initialized,
        step=step,
    )
    return JSONResponse(status_code=200, content=public_payload.model_dump(mode="json"))


@setup_state_router.get(
    "/platform-setup-state",
    response_model=bs.PlatformSetupStateResponse | bs.PlatformSetupStatePublicResponse,
    summary="Load minimal setup state (public/non-admin) or full snapshot (PLATFORM_ADMIN)",
    responses=PROBLEM_RESPONSES,
)
async def get_platform_setup_state(
    request: Request,
    detail: bool = Query(
        default=False,
        description="When true, require PLATFORM_ADMIN role to return full setup snapshot.",
    ),
) -> bs.PlatformSetupStateResponse | JSONResponse:
    svc = get_accostage_service(request)
    engine = get_configured_db_engine(request)

    if not _has_caller_credentials(request):
        if detail:
            raise ScopeAccessDeniedError(
                detail_override="PLATFORM_ADMIN role required to read full platform setup state.",
                instance=str(request.url.path),
            )
        return await _build_public_setup_state_response(request, svc, engine)

    caller = resolve_request_user(request, persona_key=request.query_params.get("persona_key"))
    if caller.platform_role != "PLATFORM_ADMIN":
        if detail:
            raise ScopeAccessDeniedError(
                detail_override="PLATFORM_ADMIN role required to read full platform setup state.",
                instance=str(request.url.path),
            )
        return await _build_public_setup_state_response(request, svc, engine)

    snap: bm.PlatformSetupSnapshotRecord | None = None
    if engine is not None:
        try:
            snap = await load_platform_setup_state_from_postgres18(engine, orcia_env=svc.orcia_env)
            db_admin = await bm.get_first_platform_admin_from_postgres18(
                engine, orcia_env=svc.orcia_env
            )
            svc.set_first_platform_admin_record(db_admin)
        except Exception as exc:
            logger.warning("bootstrap_platform_setup_load_fallback", error_type=type(exc).__name__)
            raise_if_non_test_pg_error(exc, path=str(request.url.path))
            snap = None

    if snap is None:
        cached: bm.PlatformSetupSnapshotRecord | None = getattr(
            request.app.state, "platform_setup_snapshot", None
        )
        admin = svc.first_admin
        snap = cached or bm.PlatformSetupSnapshotRecord(
            first_admin_initialized=admin is not None,
            first_admin_email=admin.email if admin else None,
            first_admin_display_name=admin.display_name if admin else None,
        )
    request.app.state.platform_setup_snapshot = snap
    _sync_accostage_from_snapshot(svc, snap)
    sync_setup_snapshot_to_evaluator(request, snap, svc.first_admin)
    return _serialize_setup_snapshot(snap, trace_id_for_bootstrap(request))


@setup_state_router.put(
    "/platform-setup-state",
    response_model=bs.PlatformSetupStateResponse,
    summary="Persist Day-0 / Epics 8-12 Platform Setup state to PostgreSQL 18 (PLATFORM_ADMIN)",
    responses=PROBLEM_RESPONSES,
)
async def put_platform_setup_state(
    payload: bs.PlatformSetupStatePutRequest,
    request: Request,
) -> bs.PlatformSetupStateResponse:
    caller = resolve_request_user(request, persona_key=request.query_params.get("persona_key"))
    if caller.platform_role != "PLATFORM_ADMIN":
        raise ScopeAccessDeniedError(
            detail_override="PLATFORM_ADMIN role required to modify platform setup state.",
            instance=str(request.url.path),
        )
    svc = get_accostage_service(request)
    admin = svc.first_admin
    candidate = bm.PlatformSetupSnapshotRecord(
        first_admin_initialized=admin is not None,
        first_admin_email=admin.email if admin else None,
        first_admin_display_name=admin.display_name if admin else None,
        org_units=list(payload.org_units),
        rbac_grants=list(payload.rbac_grants),
        llm_tiers=strip_snapshot_credentials(list(payload.llm_tiers)),
        workspaces=list(payload.workspaces),
        datasources=strip_snapshot_credentials(list(payload.datasources)),
        packs=list(payload.packs),
        workflows=list(payload.workflows),
        runs=list(payload.runs),
        catalog_items=list(payload.catalog_items),
        ontology_concepts=list(payload.ontology_concepts),
        audit_events=list(payload.audit_events),
    )
    saved: bm.PlatformSetupSnapshotRecord | None = None
    engine = get_configured_db_engine(request)
    if engine is not None:
        try:
            saved = await save_platform_setup_state_to_postgres18(
                engine, candidate, orcia_env=svc.orcia_env
            )
        except Exception as exc:
            logger.warning("bootstrap_platform_setup_save_fallback", error_type=type(exc).__name__)
            raise_if_non_test_pg_error(exc, path=str(request.url.path))
            saved = None

    final_snap = saved or candidate
    request.app.state.platform_setup_snapshot = final_snap
    _sync_accostage_from_snapshot(svc, final_snap)
    sync_setup_snapshot_to_evaluator(request, final_snap, svc.first_admin)
    return _serialize_setup_snapshot(final_snap, trace_id_for_bootstrap(request))
