"""Day-0 Accostage (1/6) & First Admin Sub-Router (`Story 9.2`, `Story 26.1`)."""

from __future__ import annotations

from fastapi import APIRouter, Request, Response

from orcia_api.dependencies import get_accostage_service, get_auth_service
from orcia_api.dependencies._core_providers import get_configured_db_engine
from orcia_api.routers._auth_pg_helpers import set_auth_refresh_cookie
from orcia_api.routers._auth_policy_runtime import resolve_auth_policy_runtime
from orcia_api.routers._bootstrap_llm_routes import (
    llm_router,
    raise_if_non_test_pg_error,
    serialize_accostage_status,
    trace_id_for_bootstrap,
)
from orcia_api.routers._bootstrap_setup_state import setup_state_router
from orcia_api.routers.auth import PROBLEM_RESPONSES, resolve_request_user
from orcia_api.schemas import bootstrap as bs
from orcia_core import bootstrap as bm
from orcia_core.bootstrap.errors import OrciaDomainError
from orcia_core.observability.logging import get_logger
from orcia_core.orchestration import build_default_orchestration_setup_service
from orcia_core.permissions import UserIdentity

logger = get_logger("orcia.api.bootstrap")


def _resolve_optional_caller_role(request: Request) -> tuple[str | None, bool]:
    """Return `(platform_role, read_only_observer)` when caller supplies auth or local persona."""
    auth_svc = get_auth_service(request)
    raw_persona = (
        request.query_params.get("persona_key") if hasattr(request, "query_params") else None
    )
    has_persona = (
        getattr(auth_svc, "allow_persona_impersonation", False) is True
        and isinstance(raw_persona, str)
        and bool(raw_persona.strip())
    )
    has_auth = bool(
        request.headers.get("Authorization")
        or getattr(request.state, "resolved_bearer_user", None) is not None
        or has_persona
    )
    if not has_auth:
        return None, False
    try:
        user = (
            resolve_request_user(request, persona_key=raw_persona)
            if has_persona
            else resolve_request_user(request)
        )
    except Exception as exc:
        logger.warning("bootstrap_optional_caller_role_fallback", error_type=type(exc).__name__)
        return None, False
    role_set = {str(r).strip().upper() for r in user.roles}
    role_set.add(str(user.platform_role).strip().upper())
    is_observer = "READ_ONLY_OBSERVER" in role_set or "OBSERVER" in role_set
    return str(user.platform_role), is_observer


_serialize_accostage_status = serialize_accostage_status
resolve_optional_caller_role = _resolve_optional_caller_role
router = APIRouter()
router.include_router(llm_router)
router.include_router(setup_state_router)


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
        raise_if_non_test_pg_error(exc, path=str(request.url.path))


async def _load_pg18_accostage_counts(request: Request) -> bm.AccostagePg18Counts | None:
    engine = get_configured_db_engine(request)
    if engine is None:
        return None
    try:
        return await bm.get_accostage_pg18_counts(engine)
    except Exception as exc:
        logger.warning("bootstrap_accostage_pg_counts_skipped", error_type=type(exc).__name__)
        raise_if_non_test_pg_error(exc, path=str(request.url.path))
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
    user_role, is_observer = resolve_optional_caller_role(request)
    return serialize_accostage_status(
        svc.get_accostage_status(user_role=user_role, read_only_observer=is_observer),
        trace_id_for_bootstrap(request),
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
            raise_if_non_test_pg_error(exc, path=str(request.url.path))
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
        trace_id=trace_id_for_bootstrap(request),
    )
