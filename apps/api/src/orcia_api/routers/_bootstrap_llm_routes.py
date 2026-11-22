"""Progressive Day-0 LLM Registration & Connection Test Routes (`Story 9.2`, `Story 26.1`)."""

from __future__ import annotations

from typing import Literal

from fastapi import APIRouter, Request

from orcia_api.dependencies import get_accostage_service
from orcia_api.dependencies._core_providers import (
    get_configured_db_engine,
    should_auto_init_infra,
)
from orcia_api.dependencies._llm_streaming_providers import get_or_create_async_http_client
from orcia_api.routers._auth_policy_runtime import resolve_auth_policy_runtime
from orcia_api.routers.auth import PROBLEM_RESPONSES
from orcia_api.schemas import bootstrap as bs
from orcia_core import bootstrap as bm
from orcia_core.bootstrap.errors import OrciaDomainError
from orcia_core.bootstrap.setup_snapshot_cache import invalidate_platform_setup_snapshot_async
from orcia_core.kernel.errors import TransientInfraError
from orcia_core.observability.logging import (
    get_current_trace_id,
    get_logger,
    scrub_sensitive_text,
)
from orcia_core.orchestration import LlmProtocolMode, test_ai_model_endpoint_connection
from orcia_core.permissions.ssrf_guard import validate_safe_llm_endpoint_url
from orcia_kernel.ids import new_uuid7_str

logger = get_logger("orcia.api.bootstrap")
llm_router = APIRouter()


def trace_id_for_bootstrap(request: Request) -> str:
    """Resolve active trace_id for bootstrap responses."""
    return str(getattr(request.state, "trace_id", None) or get_current_trace_id())


def raise_if_non_test_pg_error(exc: Exception, *, path: str) -> None:
    """Propagate PostgreSQL infra errors when auto-infra initialization is enabled."""
    if should_auto_init_infra("DATABASE_URL"):
        raise TransientInfraError(
            detail_override="PostgreSQL 18 unavailable during platform bootstrap.",
            instance=path,
        ) from exc


def serialize_accostage_status(
    rep: bm.AccostageStatusReport,
    trace_id: str,
    *,
    boot_epoch: str | None = None,
    counts: bm.AccostagePg18Counts | None = None,
) -> bs.AccostageStatusResponse:
    """Serialize `AccostageStatusReport` into OpenAPI response DTO."""
    admin_created = counts.admin_created if counts is not None else rep.first_admin_initialized
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
        platform_admin_display_name=rep.platform_admin_display_name,
        visible_milestones=[
            bs.AccostageMilestoneItem(
                index=m.index,
                key=m.key,
                title_fr=m.title_fr,
                title_en=m.title_en,
                target_route=m.target_route,
                completed=m.completed,
                is_accessible=m.is_accessible,
            )
            for m in rep.visible_milestones
        ],
        admin_created=admin_created,
        users_count=(
            counts.users_count if counts is not None else (1 if rep.first_admin_initialized else 0)
        ),
        org_units_count=counts.org_units_count if counts is not None else 0,
        workspaces_count=counts.workspaces_count if counts is not None else 0,
        models_count=counts.models_count if counts is not None else len(rep.distinct_families),
        sources_count=counts.sources_count if counts is not None else 0,
        workflows_count=counts.workflows_count if counts is not None else 0,
        boot_epoch=boot_epoch,
        trace_id=trace_id,
    )


@llm_router.post(
    "/welcome-setup/progressive-llm",
    response_model=bs.AccostageStatusResponse,
    summary="Register progressive LLM endpoint (1 family -> Quick Trial; >= 2 -> AD-10 Gates)",
    responses=PROBLEM_RESPONSES,
)
async def register_welcome_setup_progressive_llm(
    payload: bs.ProgressiveLlmEndpointRequest,
    request: Request,
) -> bs.AccostageStatusResponse:
    validate_safe_llm_endpoint_url(payload.endpoint_uri, instance=str(request.url.path))
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
            raise_if_non_test_pg_error(exc, path=str(request.url.path))
    await invalidate_platform_setup_snapshot_async(
        request.app.state, redis_client=getattr(request.app.state, "redis_client", None)
    )
    from orcia_api.routers.bootstrap_accostage import _resolve_optional_caller_role

    policy_state, _, _ = await resolve_auth_policy_runtime(request)
    user_role, is_observer = _resolve_optional_caller_role(request)
    scoped_rep = (
        svc.get_accostage_status(user_role=user_role, read_only_observer=is_observer)
        if user_role is not None or is_observer
        else rep
    )
    return serialize_accostage_status(
        scoped_rep,
        trace_id_for_bootstrap(request),
        boot_epoch=policy_state.boot_epoch,
    )


@llm_router.post(
    "/welcome-setup/llm-test",
    response_model=bs.LlmConnectionTestResponse,
    summary="Test LLM endpoint connectivity, URL format, and authentication configuration",
    responses=PROBLEM_RESPONSES,
)
async def test_welcome_setup_llm_connection(
    payload: bs.LlmConnectionTestRequest,
    request: Request,
) -> bs.LlmConnectionTestResponse:
    trace_id = trace_id_for_bootstrap(request)
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

    u_lower, p_lower = uri.lower(), provider.lower()
    if "anthropic" in p_lower or u_lower.endswith("/messages"):
        protocol_mode: LlmProtocolMode = "anthropic_messages"
    elif (
        "google" in p_lower or "gemini" in p_lower or "generativelanguage.googleapis.com" in u_lower
    ):
        protocol_mode = "openai_compatible" if "/openai" in u_lower else "gemini_native"
    else:
        protocol_mode = "openai_compatible"

    http_client = get_or_create_async_http_client(request)

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
        return _resp(True, "CONNECTED", res.latency_ms, res.message_fr, res.message_en)
    except OrciaDomainError as exc:
        lat = getattr(exc, "latency_ms", 0) or 0
        st: Literal["CONNECTED", "INVALID_PARAMETERS", "AUTH_REQUIRED"] = (
            "AUTH_REQUIRED"
            if getattr(exc, "http_status", 400) in (401, 403)
            else "INVALID_PARAMETERS"
        )
        err_msg = scrub_sensitive_text(str(exc.detail_override or exc))
        return _resp(
            False,
            st,
            lat,
            f"❌ Échec du test de connexion : {err_msg}",
            f"❌ Connection test failed: {err_msg}",
        )
