"""Platform Authentication Policy & OIDC Discovery Router (`/api/v1/settings/authentication`)."""

from __future__ import annotations

from fastapi import APIRouter, Query, Request

from orcia_api.dependencies import get_auth_service, get_or_create_shared_db_engine
from orcia_api.routers._auth_policy_runtime import (
    discover_oidc_endpoints,
    enforce_platform_admin_only,
    get_in_memory_auth_policy_store,
    pg_auth_enabled,
    resolve_auth_policy_runtime,
    serialize_admin_auth_settings,
    trace_id_for,
)
from orcia_api.routers.enterprise_connectors import ENTERPRISE_CONNECTORS_PROBLEM_RESPONSES
from orcia_api.schemas.auth_policy import (
    OidcDiscoveryTestRequest,
    OidcDiscoveryTestResponse,
    PlatformAuthSettingsResponse,
    UpdatePlatformAuthSettingsRequest,
)
from orcia_core.bootstrap import update_platform_auth_policy_on_postgres18
from orcia_core.observability.logging import get_logger
from orcia_core.permissions import PlatformAuthPolicyState

logger = get_logger("orcia.api.auth_settings")

router = APIRouter(
    prefix="/api/v1/settings/authentication",
    tags=["auth-settings"],
    responses=ENTERPRISE_CONNECTORS_PROBLEM_RESPONSES,
)


@router.get(
    "",
    response_model=PlatformAuthSettingsResponse,
    summary="Read platform authentication policy (PLATFORM_ADMIN only)",
)
async def get_platform_authentication_settings(
    request: Request,
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> PlatformAuthSettingsResponse:
    """Return exclusive authentication mode, 2FA mode, and Write-Only OIDC settings."""
    enforce_platform_admin_only(request, persona_key=persona_key)
    state, _, _ = await resolve_auth_policy_runtime(request)
    return serialize_admin_auth_settings(state, trace_id=trace_id_for(request))


@router.put(
    "",
    response_model=PlatformAuthSettingsResponse,
    summary="Configure exclusive LOCAL vs SSO authentication mode and 2FA (PLATFORM_ADMIN only)",
)
async def update_platform_authentication_settings(
    payload: UpdatePlatformAuthSettingsRequest,
    request: Request,
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> PlatformAuthSettingsResponse:
    """Persist singleton authentication mode and two-factor policy in PostgreSQL 18."""
    user = enforce_platform_admin_only(request, persona_key=persona_key)
    auth_svc = get_auth_service(request)
    trace_id = trace_id_for(request)
    instance = str(request.url.path)

    updated_state: PlatformAuthPolicyState
    if pg_auth_enabled():
        try:
            engine = get_or_create_shared_db_engine(request)
            updated_state = await update_platform_auth_policy_on_postgres18(
                engine,
                cipher=auth_svc.vault_cipher,
                auth_mode=payload.auth_mode,
                two_factor_mode=payload.two_factor_mode,
                oidc_issuer_url=payload.oidc_issuer_url,
                oidc_client_id=payload.oidc_client_id,
                oidc_client_secret=payload.oidc_client_secret,
                clear_oidc_client_secret=payload.clear_oidc_client_secret,
                oidc_scopes=payload.oidc_scopes,
                oidc_redirect_uri=payload.oidc_redirect_uri,
                sso_button_label=payload.sso_button_label,
                updated_by=user.email,
                instance=instance,
            )
            return serialize_admin_auth_settings(updated_state, trace_id=trace_id)
        except Exception as exc:
            # Domain errors (e.g. incomplete SSO / missing SMTP) must propagate cleanly as RFC 9457
            from orcia_kernel.errors import OrciaDomainError

            if isinstance(exc, OrciaDomainError):
                raise
            logger.warning("auth_settings_pg_update_fallback", error_type=type(exc).__name__)

    connectors_svc = getattr(request.app.state, "enterprise_connectors_service", None)
    active_smtp_name: str | None = None
    if connectors_svc is not None:
        for conn in connectors_svc.list_connectors():
            if conn.connector_kind == "SMTP_MAIL" and conn.enabled:
                active_smtp_name = conn.name
                break

    store = get_in_memory_auth_policy_store(request)
    updated_state = store.update_policy(
        auth_mode=payload.auth_mode,
        two_factor_mode=payload.two_factor_mode,
        oidc_issuer_url=payload.oidc_issuer_url,
        oidc_client_id=payload.oidc_client_id,
        oidc_client_secret=payload.oidc_client_secret,
        clear_oidc_client_secret=payload.clear_oidc_client_secret,
        oidc_scopes=payload.oidc_scopes,
        oidc_redirect_uri=payload.oidc_redirect_uri,
        sso_button_label=payload.sso_button_label,
        has_active_smtp_connector=active_smtp_name is not None,
        smtp_connector_name=active_smtp_name,
        updated_by=user.email,
        instance=instance,
    )
    request.app.state.auth_policy_explicitly_set = True
    return serialize_admin_auth_settings(updated_state, trace_id=trace_id)


@router.post(
    "/test-oidc",
    response_model=OidcDiscoveryTestResponse,
    summary="Verify OIDC `.well-known/openid-configuration` discovery safely (PLATFORM_ADMIN only)",
)
async def test_oidc_discovery_endpoint(
    payload: OidcDiscoveryTestRequest,
    request: Request,
    persona_key: str | None = Query(default=None, min_length=1, max_length=64),
) -> OidcDiscoveryTestResponse:
    """Perform SSRF-validated async OIDC discovery and return discovered endpoints."""
    enforce_platform_admin_only(request, persona_key=persona_key)
    doc, latency_ms = await discover_oidc_endpoints(request, issuer_url=payload.issuer_url)
    return OidcDiscoveryTestResponse(
        ok=True,
        issuer=str(doc.get("issuer") or payload.issuer_url.strip().rstrip("/")),
        authorization_endpoint=str(doc["authorization_endpoint"]),
        token_endpoint=str(doc["token_endpoint"]),
        userinfo_endpoint=str(doc.get("userinfo_endpoint") or "") or None,
        latency_ms=latency_ms,
        trace_id=trace_id_for(request),
    )
