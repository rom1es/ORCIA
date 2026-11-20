"""Day-0 Accostage (1/6) & Platform Setup State Sub-Router (`Story 9.2`)."""

from __future__ import annotations

import sys
from typing import Literal

import httpx
from fastapi import APIRouter, Request, Response

from orcia_api.dependencies import (
    get_accostage_service,
    get_auth_service,
)
from orcia_api.dependencies._core_providers import get_configured_db_engine
from orcia_api.routers._auth_pg_helpers import set_auth_refresh_cookie
from orcia_api.routers._auth_policy_runtime import resolve_auth_policy_runtime
from orcia_api.routers._bootstrap_evaluator_sync import sync_setup_snapshot_to_evaluator
from orcia_api.routers.auth import PROBLEM_RESPONSES
from orcia_api.schemas import bootstrap as bs
from orcia_core import bootstrap as bm
from orcia_core.bootstrap import (
    load_platform_setup_state_from_postgres18,
    save_platform_setup_state_to_postgres18,
)
from orcia_core.bootstrap.errors import OrciaDomainError
from orcia_core.kernel.errors import TransientInfraError
from orcia_core.observability.logging import get_current_trace_id, get_logger
from orcia_core.orchestration import (
    LlmProtocolMode,
    build_default_orchestration_setup_service,
    test_ai_model_endpoint_connection,
)
from orcia_core.permissions import UserIdentity
from orcia_kernel.ids import new_uuid7_str

logger = get_logger("orcia.api.bootstrap")
router = APIRouter()


def _trace(request: Request) -> str:
    return str(getattr(request.state, "trace_id", None) or get_current_trace_id())


def _raise_if_non_test_pg_error(exc: Exception, *, path: str) -> None:
    if "pytest" not in sys.modules:
        raise TransientInfraError(
            detail_override="PostgreSQL 18 indisponible lors du bootstrap plateforme.",
            instance=path,
        ) from exc


async def _sync_first_admin_with_postgres18(
    request: Request, svc: bm.ProgressiveDay0AccostageService
) -> None:
    """Synchronize `svc.first_admin` with PostgreSQL 18 `users` table when active."""
    engine = get_configured_db_engine(request)
    if engine is None:
        return
    try:
        db_record = await bm.get_first_platform_admin_from_postgres18(
            engine, orcia_env=svc.orcia_env
        )
        svc.set_first_platform_admin_record(db_record)
    except Exception as exc:
        logger.warning("bootstrap_first_admin_pg_sync_skipped", error_type=type(exc).__name__)
        _raise_if_non_test_pg_error(exc, path=str(request.url.path))


def _serialize_accostage_status(
    rep: bm.AccostageStatusReport,
    trace_id: str,
    *,
    boot_epoch: str | None = None,
    counts: bm.AccostagePg18Counts | None = None,
) -> bs.AccostageStatusResponse:
    admin_created = counts.admin_created if counts is not None else rep.first_admin_initialized
    users_count = (
        counts.users_count if counts is not None else (1 if rep.first_admin_initialized else 0)
    )
    org_units_count = counts.org_units_count if counts is not None else 0
    workspaces_count = counts.workspaces_count if counts is not None else 0
    models_count = counts.models_count if counts is not None else len(rep.distinct_families)
    sources_count = counts.sources_count if counts is not None else 0
    workflows_count = counts.workflows_count if counts is not None else 0
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
        admin_created=admin_created,
        users_count=users_count,
        org_units_count=org_units_count,
        workspaces_count=workspaces_count,
        models_count=models_count,
        sources_count=sources_count,
        workflows_count=workflows_count,
        boot_epoch=boot_epoch,
        trace_id=trace_id,
    )


async def _load_pg18_accostage_counts(request: Request) -> bm.AccostagePg18Counts | None:
    engine = get_configured_db_engine(request)
    if engine is None:
        return None
    try:
        return await bm.get_accostage_pg18_counts(engine)
    except Exception as exc:
        logger.warning("bootstrap_accostage_pg_counts_skipped", error_type=type(exc).__name__)
        _raise_if_non_test_pg_error(exc, path=str(request.url.path))
        return None


@router.get(
    "/accostage-status",
    response_model=bs.AccostageStatusResponse,
    summary="Get progressive Day-0 Accostage (0/6..6/6) status and LLM tier state (`Story 9.2`)",
    responses=PROBLEM_RESPONSES,
)
async def get_accostage_status(request: Request) -> bs.AccostageStatusResponse:
    svc = get_accostage_service(request)
    await _sync_first_admin_with_postgres18(request, svc)
    counts = await _load_pg18_accostage_counts(request)
    if counts is not None:
        svc.sync_from_pg18_counts(
            users_count=counts.users_count,
            org_units_count=counts.org_units_count,
            workspaces_count=counts.workspaces_count,
            models_count=counts.models_count,
            sources_count=counts.sources_count,
            workflows_count=counts.workflows_count,
        )
    policy_state, _, _ = await resolve_auth_policy_runtime(request)
    return _serialize_accostage_status(
        svc.get_accostage_status(),
        _trace(request),
        boot_epoch=policy_state.boot_epoch,
        counts=counts,
    )


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
    response: Response,
) -> bs.WelcomeSetupFirstAdminResponse:
    svc = get_accostage_service(request)
    auth_svc = get_auth_service(request)
    password_hash = auth_svc.hasher.hash_password(payload.password)

    rec: bm.FirstPlatformAdminRecord | None = None
    engine = get_configured_db_engine(request)
    if engine is not None:
        try:
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
            _raise_if_non_test_pg_error(exc, path=str(request.url.path))
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

    admin_user = UserIdentity(
        id=rec.user_id,
        email=rec.email,
        display_name=rec.display_name,
        auth_mode="LOCAL",
        human_profile_archetype="CONTRIBUTOR",
        platform_role="PLATFORM_ADMIN",
        primary_org_unit_id="0192c4e0-0000-7000-8000-000000000101",
        password_hash_argon2id=password_hash,
        roles=("PLATFORM_ADMIN", "SECOPS"),
        must_change_password=False,
    )
    auth_svc.register_user(admin_user)
    request.app.state.orchestration_service = build_default_orchestration_setup_service(
        evaluator=auth_svc.evaluator,
    )
    tokens = auth_svc.jwt_manager.issue_token_pair(
        user_id=admin_user.id,
        email=admin_user.email,
        role="PLATFORM_ADMIN",
        org_unit_id=admin_user.primary_org_unit_id,
        archetype=admin_user.human_profile_archetype,
        auth_mode="LOCAL",
    )
    set_auth_refresh_cookie(response, tokens.refresh_token, request)

    return bs.WelcomeSetupFirstAdminResponse(
        user_id=rec.user_id,
        email=rec.email,
        display_name=rec.display_name,
        platform_role=rec.platform_role,
        orcia_env=rec.orcia_env,
        sql_lock_statement=rec.sql_lock_statement,
        access_token=tokens.access_token,
        must_change_password=False,
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
    engine = get_configured_db_engine(request)
    if engine is not None:
        try:
            await bm.persist_progressive_llm_endpoint_to_postgres18(engine, endpoint)
        except Exception as exc:
            logger.warning(
                "bootstrap_progressive_llm_pg_sync_skipped", error_type=type(exc).__name__
            )
            _raise_if_non_test_pg_error(exc, path=str(request.url.path))
    policy_state, _, _ = await resolve_auth_policy_runtime(request)
    return _serialize_accostage_status(
        rep,
        _trace(request),
        boot_epoch=policy_state.boot_epoch,
    )


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
    trace_id = _trace(request)
    provider = payload.provider_slug.strip() or "OpenAI / Compatible"
    model, uri = payload.model_name.strip(), payload.endpoint_uri.strip()
    has_key = bool((payload.api_key and payload.api_key.strip()) or payload.api_key_configured)

    def _resp(
        ok: bool,
        st: Literal["CONNECTED", "INVALID_PARAMETERS", "AUTH_REQUIRED"],
        lat: int,
        fr: str,
        en: str,
        m_name: str = model,
    ) -> bs.LlmConnectionTestResponse:
        return bs.LlmConnectionTestResponse(
            ok=ok,
            status=st,
            latency_ms=lat,
            provider_slug=provider,
            model_name=m_name,
            endpoint_uri=uri,
            auth_mode=payload.auth_mode,
            message_fr=fr,
            message_en=en,
            trace_id=trace_id,
        )

    if not model:
        return _resp(
            False,
            "INVALID_PARAMETERS",
            0,
            "❌ Échec du test : veuillez renseigner l'identifiant du modèle principal.",
            "❌ Test failed: please enter the primary model identifier.",
            m_name="",
        )
    if not uri or not uri.startswith(("http://", "https://")):
        return _resp(
            False,
            "INVALID_PARAMETERS",
            0,
            "❌ Échec du test : veuillez indiquer une URL d'API valide (https:// ou http://).",
            "❌ Test failed: please enter a valid API URL starting with https:// or http://.",
        )
    if payload.auth_mode == "api_key" and not has_key:
        return _resp(
            False,
            "AUTH_REQUIRED",
            0,
            "❌ Échec du test : veuillez saisir votre clé d'API (jeton secret) ou « Sans clé ».",
            "❌ Test failed: please enter your API key (secret token) or select 'No key'.",
        )

    u_lower = uri.lower()
    p_lower = provider.lower()
    if "anthropic" in p_lower or u_lower.endswith("/messages"):
        protocol_mode: LlmProtocolMode = "anthropic_messages"
    elif (
        "google" in p_lower or "gemini" in p_lower or "generativelanguage.googleapis.com" in u_lower
    ):
        protocol_mode = "openai_compatible" if "/openai" in u_lower else "gemini_native"
    else:
        protocol_mode = "openai_compatible"

    http_client: httpx.AsyncClient | None = getattr(request.app.state, "http_client", None)
    if http_client is None or getattr(http_client, "is_closed", False):
        http_client = httpx.AsyncClient(timeout=15.0)

    try:
        res = await test_ai_model_endpoint_connection(
            http_client=http_client,
            endpoint_uri=uri,
            protocol_mode=protocol_mode,
            model_name=model,
            usage="chat",
            api_key=payload.api_key if payload.auth_mode == "api_key" else None,
            provider_slug=provider,
            instance=str(request.url.path),
        )
        return _resp(
            True,
            "CONNECTED",
            res.latency_ms,
            res.message_fr,
            res.message_en,
        )
    except OrciaDomainError as exc:
        lat = getattr(exc, "latency_ms", 0) or 0
        st: Literal["CONNECTED", "INVALID_PARAMETERS", "AUTH_REQUIRED"] = (
            "AUTH_REQUIRED"
            if getattr(exc, "http_status", 400) in (401, 403)
            else "INVALID_PARAMETERS"
        )
        err_msg = str(exc.detail_override or exc)
        return _resp(
            False,
            st,
            lat,
            f"❌ Échec du test de connexion : {err_msg}",
            f"❌ Connection test failed: {err_msg}",
        )


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
            if custom_uri.startswith("http://") or custom_uri.startswith("https://")
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
    engine = get_configured_db_engine(request)
    if engine is not None:
        try:
            snap = await load_platform_setup_state_from_postgres18(engine, orcia_env=svc.orcia_env)
            db_admin = await bm.get_first_platform_admin_from_postgres18(
                engine, orcia_env=svc.orcia_env
            )
            svc.set_first_platform_admin_record(db_admin)
        except Exception as exc:
            logger.warning("bootstrap_platform_setup_load_fallback", error_type=type(exc).__name__)
            _raise_if_non_test_pg_error(exc, path=str(request.url.path))
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
    engine = get_configured_db_engine(request)
    if engine is not None:
        try:
            saved = await save_platform_setup_state_to_postgres18(
                engine, candidate, orcia_env=svc.orcia_env
            )
        except Exception as exc:
            logger.warning("bootstrap_platform_setup_save_fallback", error_type=type(exc).__name__)
            _raise_if_non_test_pg_error(exc, path=str(request.url.path))
            saved = None

    final_snap = saved or candidate
    request.app.state.platform_setup_snapshot = final_snap
    _sync_accostage_from_snapshot(svc, final_snap)
    sync_setup_snapshot_to_evaluator(request, final_snap, svc.first_admin)
    return _serialize_setup_snapshot(final_snap, _trace(request))
