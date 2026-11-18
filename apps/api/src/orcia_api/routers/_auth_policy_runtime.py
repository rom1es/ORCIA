"""Runtime policy resolution & strict `PLATFORM_ADMIN` guard for authentication endpoints."""

from __future__ import annotations

import os
import time
from typing import TYPE_CHECKING, Any

from fastapi import Request

from orcia_api.dependencies import get_auth_service, get_or_create_shared_db_engine
from orcia_api.schemas.auth_policy import (
    PlatformAuthSettingsResponse,
    PublicAuthConfigResponse,
)
from orcia_core.bootstrap import load_platform_auth_policy_from_postgres18
from orcia_core.observability.logging import get_current_trace_id, get_logger
from orcia_core.permissions import (
    InMemoryPlatformAuthPolicyStore,
    PlatformAuthPolicyState,
    UserIdentity,
)
from orcia_core.permissions.enterprise_connectors import validate_safe_connector_base_url
from orcia_core.permissions.errors import (
    ObserverModeReadOnlyError,
    ScopeAccessDeniedError,
    ValidationDomainError,
)

if TYPE_CHECKING:
    from sqlalchemy.ext.asyncio import AsyncEngine

logger = get_logger("orcia.api.auth_policy_runtime")


def pg_auth_enabled() -> bool:
    """Return True when PostgreSQL bootstrap auth is active."""
    from orcia_api.dependencies._core_providers import is_pg_runtime_active

    return is_pg_runtime_active()


def get_in_memory_auth_policy_store(request: Request) -> InMemoryPlatformAuthPolicyStore:
    """Return the app-scoped fallback `InMemoryPlatformAuthPolicyStore`."""
    store: InMemoryPlatformAuthPolicyStore | None = getattr(
        request.app.state, "auth_policy_store", None
    )
    if store is None:
        auth_svc = get_auth_service(request)
        store = InMemoryPlatformAuthPolicyStore(cipher=auth_svc.vault_cipher)
        request.app.state.auth_policy_store = store
    return store


def enforce_platform_admin_only(
    request: Request,
    *,
    persona_key: str | None = None,
) -> UserIdentity:
    """Enforce exclusive `PLATFORM_ADMIN` access and strict `READ_ONLY_OBSERVER` rejection."""
    access_mode_hdr = request.headers.get("x-orcia-access-mode", "").strip().upper()
    observer_hdr = request.headers.get("x-orcia-observer-mode", "").strip().lower()
    active_hat = request.headers.get("x-orcia-active-hat", "").strip().upper()
    if (
        access_mode_hdr == "READ_ONLY_OBSERVER"
        or observer_hdr in ("1", "true", "yes")
        or active_hat == "OBSERVER"
    ):
        raise ObserverModeReadOnlyError(instance=str(request.url.path))

    effective_persona = persona_key or request.headers.get("x-orcia-persona", "").strip() or None
    auth_svc = get_auth_service(request)
    user = auth_svc.resolve_user(
        persona_key=effective_persona,
        bearer_token=request.headers.get("Authorization"),
    )
    if user.platform_role == "OBSERVER":
        raise ObserverModeReadOnlyError(instance=str(request.url.path))

    is_platform_admin = user.platform_role == "PLATFORM_ADMIN" or "PLATFORM_ADMIN" in user.roles
    if not is_platform_admin:
        raise ScopeAccessDeniedError(instance=str(request.url.path))
    if active_hat and active_hat != "PLATFORM_ADMIN":
        raise ScopeAccessDeniedError(instance=str(request.url.path))
    return user


async def resolve_auth_policy_runtime(
    request: Request,
) -> tuple[PlatformAuthPolicyState, bool, AsyncEngine | None]:
    """Return `(policy_state, strict_exclusive_mode, active_pg_engine)` safely."""
    if pg_auth_enabled():
        try:
            engine = get_or_create_shared_db_engine(request)
            state = await load_platform_auth_policy_from_postgres18(engine)
            return state, True, engine
        except Exception as exc:
            logger.warning("auth_policy_pg_load_skipped", error_type=type(exc).__name__)

    store = get_in_memory_auth_policy_store(request)
    is_strict = bool(
        getattr(request.app.state, "auth_policy_explicitly_set", False)
        or os.environ.get("ORCIA_FORCE_REAL_RUNTIME", "").strip() == "1"
    )
    return store.get_state(), is_strict, None


def serialize_public_auth_config(
    state: PlatformAuthPolicyState,
    *,
    trace_id: str,
) -> PublicAuthConfigResponse:
    """Serialize anonymous `/api/v1/auth/public-config` payload without secrets."""
    return PublicAuthConfigResponse(
        auth_mode=state.auth_mode,
        two_factor_mode=state.two_factor_mode,
        oidc_enabled=bool(
            state.auth_mode == "SSO"
            and state.oidc_issuer_url
            and state.oidc_client_id
            and state.oidc_redirect_uri
        ),
        sso_button_label=state.sso_button_label,
        boot_epoch=state.boot_epoch,
        trace_id=trace_id,
    )


def serialize_admin_auth_settings(
    state: PlatformAuthPolicyState,
    *,
    trace_id: str,
) -> PlatformAuthSettingsResponse:
    """Serialize `PLATFORM_ADMIN` `/api/v1/settings/authentication` payload (Write-Only secrets)."""
    return PlatformAuthSettingsResponse(
        auth_mode=state.auth_mode,
        two_factor_mode=state.two_factor_mode,
        oidc_issuer_url=state.oidc_issuer_url,
        oidc_client_id=state.oidc_client_id,
        oidc_client_secret_configured=state.oidc_client_secret_configured,
        oidc_client_secret_fingerprint=state.oidc_client_secret_fingerprint,
        oidc_scopes=state.oidc_scopes,
        oidc_redirect_uri=state.oidc_redirect_uri,
        sso_button_label=state.sso_button_label,
        smtp_connector_configured=state.smtp_connector_configured,
        smtp_connector_name=state.smtp_connector_name,
        boot_epoch=state.boot_epoch,
        updated_by=state.updated_by,
        updated_at_iso=state.updated_at_iso,
        trace_id=trace_id,
    )


async def discover_oidc_endpoints(
    request: Request,
    *,
    issuer_url: str,
) -> tuple[dict[str, Any], float]:
    """Fetch `.well-known/openid-configuration` safely via `request.app.state.http_client`."""
    clean_issuer = validate_safe_connector_base_url(issuer_url, instance=str(request.url.path))
    discovery_url = f"{clean_issuer}/.well-known/openid-configuration"
    http_client = request.app.state.http_client
    start = time.perf_counter()
    try:
        resp = await http_client.get(discovery_url, timeout=5.0)
    except Exception as exc:
        logger.warning(
            "oidc_discovery_request_failed",
            issuer=clean_issuer,
            error_type=type(exc).__name__,
        )
        raise ValidationDomainError(
            detail_override=f"Unable to reach OIDC discovery endpoint ({type(exc).__name__}).",
            instance=str(request.url.path),
        ) from exc
    elapsed_ms = round((time.perf_counter() - start) * 1000.0, 2)
    if resp.status_code != 200:
        raise ValidationDomainError(
            detail_override=f"OIDC discovery returned HTTP {resp.status_code}.",
            instance=str(request.url.path),
        )
    try:
        doc = resp.json()
    except Exception as exc:
        raise ValidationDomainError(
            detail_override="OIDC discovery response is not valid JSON.",
            instance=str(request.url.path),
        ) from exc
    if not isinstance(doc, dict):
        raise ValidationDomainError(
            detail_override="Invalid OIDC discovery JSON object.",
            instance=str(request.url.path),
        )
    auth_ep = str(doc.get("authorization_endpoint") or "").strip()
    token_ep = str(doc.get("token_endpoint") or "").strip()
    if not auth_ep or not token_ep:
        raise ValidationDomainError(
            detail_override="OIDC discovery missing authorization_endpoint or token_endpoint.",
            instance=str(request.url.path),
        )
    validate_safe_connector_base_url(auth_ep, instance=str(request.url.path))
    validate_safe_connector_base_url(token_ep, instance=str(request.url.path))
    userinfo_ep = str(doc.get("userinfo_endpoint") or "").strip() or None
    if userinfo_ep:
        validate_safe_connector_base_url(userinfo_ep, instance=str(request.url.path))
    return doc, elapsed_ms


def trace_id_for(request: Request) -> str:
    """Resolve active trace ID from request state or OTel context."""
    return str(getattr(request.state, "trace_id", None) or get_current_trace_id())
