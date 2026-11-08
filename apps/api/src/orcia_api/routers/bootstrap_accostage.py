"""Day-0 Accostage (1/6) & Platform Setup State Sub-Router (`Story 9.2`)."""

from __future__ import annotations

import os

from fastapi import APIRouter, Request

from orcia_api.dependencies import (
    get_accostage_service,
    get_auth_service,
    get_or_create_shared_db_engine,
)
from orcia_api.routers.assistant_llm_gemini_adapter import evaluate_welcome_llm_connection_test
from orcia_api.routers.auth import PROBLEM_RESPONSES
from orcia_api.schemas import bootstrap as bs
from orcia_core import bootstrap as bm
from orcia_core.bootstrap.errors import OrciaDomainError
from orcia_core.observability.logging import get_current_trace_id, get_logger
from orcia_kernel.ids import new_uuid7_str

logger = get_logger("orcia.api.bootstrap")
router = APIRouter()


def _trace(request: Request) -> str:
    return str(getattr(request.state, "trace_id", None) or get_current_trace_id())


async def _sync_first_admin_with_postgres18(
    request: Request, svc: bm.ProgressiveDay0AccostageService
) -> None:
    """Synchronize `svc.first_admin` with PostgreSQL 18 `users` table when reachable."""
    if os.environ.get("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC") == "1":
        return
    try:
        engine = get_or_create_shared_db_engine(request)
        db_record = await bm.get_first_platform_admin_from_postgres18(
            engine, orcia_env=svc.orcia_env
        )
        svc.set_first_platform_admin_record(db_record)
    except Exception as exc:
        logger.warning("bootstrap_first_admin_pg_sync_skipped", error_type=type(exc).__name__)


def _serialize_accostage_status(
    rep: bm.AccostageStatusReport, trace_id: str
) -> bs.AccostageStatusResponse:
    return bs.AccostageStatusResponse(
        completed_count=rep.completed_count,
        total_count=rep.total_count,
        badge_label=rep.badge_label,
        llm_tier_mode=rep.llm_tier_mode,
        distinct_families=list(rep.distinct_families),
        assistant_trial_enabled=rep.assistant_trial_enabled,
        agentic_gates_ad10_enabled=rep.agentic_gates_ad10_enabled,
        amber_warning_badge=rep.amber_warning_badge,
        completed_milestone_keys=list(rep.completed_milestone_keys),
        first_admin_initialized=rep.first_admin_initialized,
        first_admin_email=rep.first_admin_email,
        first_admin_display_name=rep.first_admin_display_name,
        trace_id=trace_id,
    )


@router.get(
    "/accostage-status",
    response_model=bs.AccostageStatusResponse,
    summary="Get progressive Day-0 Accostage (1/6) status and LLM tier unlock state (`Story 9.2`)",
    responses=PROBLEM_RESPONSES,
)
async def get_accostage_status(request: Request) -> bs.AccostageStatusResponse:
    svc = get_accostage_service(request)
    await _sync_first_admin_with_postgres18(request, svc)
    return _serialize_accostage_status(svc.get_accostage_status(), _trace(request))


@router.post(
    "/welcome-setup/first-admin",
    response_model=bs.WelcomeSetupFirstAdminResponse,
    summary="Create first PLATFORM_ADMIN under LOCK TABLE users IN EXCLUSIVE MODE (`Story 9.2`)",
    responses={
        **PROBLEM_RESPONSES,
        409: PROBLEM_RESPONSES[422],
    },
)
async def create_welcome_setup_first_admin(
    payload: bs.WelcomeSetupFirstAdminRequest,
    request: Request,
) -> bs.WelcomeSetupFirstAdminResponse:
    svc = get_accostage_service(request)
    password_hash = get_auth_service(request).hasher.hash_password(payload.password)

    rec: bm.FirstPlatformAdminRecord | None = None
    if os.environ.get("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC") != "1":
        try:
            engine = get_or_create_shared_db_engine(request)
            rec = await bm.create_first_platform_admin_on_postgres18(
                engine,
                email=payload.email,
                display_name=payload.display_name,
                password_hash=password_hash,
                orcia_env=payload.orcia_env,
                expected_bootstrap_token=svc.expected_bootstrap_token,
                provided_bootstrap_token=payload.bootstrap_token,
                instance=str(request.url.path),
            )
            svc.set_first_platform_admin_record(rec)
        except OrciaDomainError:
            raise
        except Exception as exc:
            logger.warning(
                "bootstrap_first_admin_pg_create_fallback", error_type=type(exc).__name__
            )
            rec = None

    if rec is None:
        rec = await svc.create_first_platform_admin_async(
            email=payload.email,
            display_name=payload.display_name,
            password_hash=password_hash,
            bootstrap_token=payload.bootstrap_token,
            orcia_env_override=payload.orcia_env,
            instance=str(request.url.path),
        )
    return bs.WelcomeSetupFirstAdminResponse(
        user_id=rec.user_id,
        email=rec.email,
        display_name=rec.display_name,
        platform_role=rec.platform_role,
        orcia_env=rec.orcia_env,
        sql_lock_statement=rec.sql_lock_statement,
        trace_id=_trace(request),
    )


@router.post(
    "/welcome-setup/progressive-llm",
    response_model=bs.AccostageStatusResponse,
    summary="Register progressive LLM endpoint (1 family -> Quick Trial; >= 2 -> AD-10 Gates)",
    responses=PROBLEM_RESPONSES,
)
async def register_welcome_setup_progressive_llm(
    payload: bs.ProgressiveLlmEndpointRequest,
    request: Request,
) -> bs.AccostageStatusResponse:
    svc = get_accostage_service(request)
    endpoint = bm.LlmModelEndpoint(
        id=new_uuid7_str(),
        endpoint_key=payload.endpoint_key,
        provider_slug=payload.provider_slug,
        model_family=payload.model_family,
        model_name=payload.model_name,
        endpoint_uri=payload.endpoint_uri,
    )
    rep = svc.register_progressive_llm_endpoint(endpoint)
    if os.environ.get("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC") != "1":
        try:
            engine = get_or_create_shared_db_engine(request)
            await bm.persist_progressive_llm_endpoint_to_postgres18(engine, endpoint)
        except Exception as exc:
            logger.warning(
                "bootstrap_progressive_llm_pg_sync_skipped", error_type=type(exc).__name__
            )
    return _serialize_accostage_status(rep, _trace(request))


@router.post(
    "/welcome-setup/llm-test",
    response_model=bs.LlmConnectionTestResponse,
    summary="Test LLM endpoint connectivity, URL format, and authentication configuration",
    responses=PROBLEM_RESPONSES,
)
async def test_welcome_setup_llm_connection(
    payload: bs.LlmConnectionTestRequest,
    request: Request,
) -> bs.LlmConnectionTestResponse:
    return evaluate_welcome_llm_connection_test(payload, _trace(request))


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
        custom_uri = str(t.get("endpointUrl", t.get("endpoint_uri", ""))).strip()
        endpoint_uri = (
            custom_uri
            if custom_uri.startswith("http://") or custom_uri.startswith("https://")
            else f"https://api.{family}.local/v1"
        )
        endpoints.append(
            bm.LlmModelEndpoint(
                id=str(t.get("id", "")).strip() or new_uuid7_str(),
                endpoint_key=str(t.get("tierKey", f"tier-{idx + 1}")).strip() or f"tier-{idx + 1}",
                provider_slug=provider_raw or family,
                model_family=family,
                model_name=str(t.get("model", "claude-3-7-sonnet")).strip() or "claude-3-7-sonnet",
                endpoint_uri=endpoint_uri,
            )
        )
    svc.sync_platform_setup_snapshot(
        llm_endpoints=tuple(endpoints),
        has_workspace=len(snap.workspaces) > 0,
        has_datasource=len(snap.datasources) > 0,
        has_pilot_run=len(snap.runs) > 0,
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
        llm_tiers=list(snap.llm_tiers),
        workspaces=list(snap.workspaces),
        datasources=list(snap.datasources),
        packs=list(snap.packs),
        workflows=list(snap.workflows),
        runs=list(snap.runs),
        catalog_items=list(snap.catalog_items),
        ontology_concepts=list(snap.ontology_concepts),
        audit_events=list(snap.audit_events),
        trace_id=trace_id,
    )


@router.get(
    "/platform-setup-state",
    response_model=bs.PlatformSetupStateResponse,
    summary="Load persisted Day-0 / Epics 8-12 Platform Setup state from PostgreSQL 18",
    responses=PROBLEM_RESPONSES,
)
async def get_platform_setup_state(request: Request) -> bs.PlatformSetupStateResponse:
    svc = get_accostage_service(request)
    snap: bm.PlatformSetupSnapshotRecord | None = None
    if os.environ.get("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC") != "1":
        try:
            engine = get_or_create_shared_db_engine(request)
            snap = await bm.load_platform_setup_state_from_postgres18(
                engine, orcia_env=svc.orcia_env
            )
            db_admin = await bm.get_first_platform_admin_from_postgres18(
                engine, orcia_env=svc.orcia_env
            )
            svc.set_first_platform_admin_record(db_admin)
        except Exception as exc:
            logger.warning("bootstrap_platform_setup_load_fallback", error_type=type(exc).__name__)
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
    return _serialize_setup_snapshot(snap, _trace(request))


@router.put(
    "/platform-setup-state",
    response_model=bs.PlatformSetupStateResponse,
    summary="Persist Day-0 / Epics 8-12 Platform Setup state to PostgreSQL 18",
    responses=PROBLEM_RESPONSES,
)
async def put_platform_setup_state(
    payload: bs.PlatformSetupStatePutRequest,
    request: Request,
) -> bs.PlatformSetupStateResponse:
    svc = get_accostage_service(request)
    admin = svc.first_admin
    candidate = bm.PlatformSetupSnapshotRecord(
        first_admin_initialized=admin is not None,
        first_admin_email=admin.email if admin else None,
        first_admin_display_name=admin.display_name if admin else None,
        org_units=list(payload.org_units),
        rbac_grants=list(payload.rbac_grants),
        llm_tiers=list(payload.llm_tiers),
        workspaces=list(payload.workspaces),
        datasources=list(payload.datasources),
        packs=list(payload.packs),
        workflows=list(payload.workflows),
        runs=list(payload.runs),
        catalog_items=list(payload.catalog_items),
        ontology_concepts=list(payload.ontology_concepts),
        audit_events=list(payload.audit_events),
    )
    saved: bm.PlatformSetupSnapshotRecord | None = None
    if os.environ.get("ORCIA_DISABLE_PG_BOOTSTRAP_SYNC") != "1":
        try:
            engine = get_or_create_shared_db_engine(request)
            saved = await bm.save_platform_setup_state_to_postgres18(
                engine, candidate, orcia_env=svc.orcia_env
            )
        except Exception as exc:
            logger.warning("bootstrap_platform_setup_save_fallback", error_type=type(exc).__name__)
            saved = None

    final_snap = saved or candidate
    request.app.state.platform_setup_snapshot = final_snap
    _sync_accostage_from_snapshot(svc, final_snap)
    return _serialize_setup_snapshot(final_snap, _trace(request))
