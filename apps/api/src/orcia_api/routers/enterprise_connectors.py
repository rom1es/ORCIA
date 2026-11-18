"""Story 17.4 — Enterprise Connectors & User Passthrough Tokens.

Exposes:
- `GET    /api/v1/settings/connectors`
- `POST   /api/v1/settings/connectors` (`422 ERR_UNSAFE_CONNECTOR_ENDPOINT_URL`, `403 Observer`)
- `PATCH  /api/v1/settings/connectors/{connector_id}`
- `DELETE /api/v1/settings/connectors/{connector_id}`
- `GET    /api/v1/users/me/account-profile` (identities, roles, FinOps team attachments)
- `GET    /api/v1/users/me/passthrough-tokens`
- `PUT    /api/v1/users/me/passthrough-tokens/{connector_id}` (`403`, Write-Only `AES-256-GCM`)
- `DELETE /api/v1/users/me/passthrough-tokens/{connector_id}` (`403 Observer`)
"""

from __future__ import annotations

from typing import Annotated, Any

from fastapi import APIRouter, Path, Query, Request

from orcia_api.dependencies import (
    get_auth_service,
    get_or_create_shared_db_engine,
)
from orcia_api.routers.auth import resolve_request_user
from orcia_api.schemas.enterprise_connectors import (
    ConnectorSecretStatusResponse,
    EnterpriseConnectorCreateRequest,
    EnterpriseConnectorDeleteResponse,
    EnterpriseConnectorItemResponse,
    EnterpriseConnectorsListResponse,
    EnterpriseConnectorUpdateRequest,
    RevokePassthroughTokenResponse,
    UpsertPassthroughTokenRequest,
    UserAccountOrgUnitItemResponse,
    UserAccountProfileResponse,
    UserPassthroughConnectorItemResponse,
    UserPassthroughTokensListResponse,
)
from orcia_api.schemas.problem_details import ProblemDetails
from orcia_core.bootstrap import (
    create_enterprise_connector_on_postgres18,
    delete_enterprise_connector_on_postgres18,
    get_user_account_profile_from_postgres18,
    list_enterprise_connectors_from_postgres18,
    list_user_passthrough_tokens_from_postgres18,
    revoke_user_passthrough_token_on_postgres18,
    update_enterprise_connector_on_postgres18,
    upsert_user_passthrough_token_on_postgres18,
)
from orcia_core.observability.logging import get_current_trace_id, get_logger
from orcia_core.permissions import ADMIN_MODULE_ALLOWED_ROLES
from orcia_core.permissions.enterprise_connectors import (
    EnterpriseConnectorRecord,
    EnterpriseConnectorsGovernanceService,
    UserPassthroughConnectorView,
    validate_safe_connector_base_url,
)
from orcia_core.permissions.errors import (
    ObserverModeReadOnlyError,
    ScopeAccessDeniedError,
)

logger = get_logger("orcia.api.enterprise_connectors")

ENTERPRISE_CONNECTORS_PROBLEM_RESPONSES: dict[int | str, dict[str, Any]] = {
    400: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
    401: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
    403: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
    404: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
    409: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
    422: {"model": ProblemDetails, "content": {"application/problem+json": {}}},
}

router = APIRouter(
    prefix="/api/v1",
    tags=["enterprise-connectors"],
    responses=ENTERPRISE_CONNECTORS_PROBLEM_RESPONSES,
)


def _trace(request: Request) -> str:
    return str(getattr(request.state, "trace_id", None) or get_current_trace_id())


def _pg_enabled() -> bool:
    from orcia_api.dependencies._core_providers import is_pg_runtime_active

    return is_pg_runtime_active()


def _get_in_memory_service(request: Request) -> EnterpriseConnectorsGovernanceService:
    svc: EnterpriseConnectorsGovernanceService | None = getattr(
        request.app.state, "enterprise_connectors_service", None
    )
    if svc is None:
        auth_svc = get_auth_service(request)
        svc = EnterpriseConnectorsGovernanceService(vault_cipher=auth_svc.vault_cipher)
        request.app.state.enterprise_connectors_service = svc
    return svc


def _enforce_mutation_access(
    request: Request,
    *,
    require_admin: bool,
    persona_key: str | None = None,
) -> Any:
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
    user = resolve_request_user(request, persona_key=effective_persona)
    if user.platform_role == "OBSERVER":
        raise ObserverModeReadOnlyError(instance=str(request.url.path))

    if require_admin:
        if active_hat and active_hat not in (*ADMIN_MODULE_ALLOWED_ROLES, "SECOPS"):
            raise ScopeAccessDeniedError(instance=str(request.url.path))
        if (
            user.platform_role not in ADMIN_MODULE_ALLOWED_ROLES
            and user.human_profile_archetype != "SECOPS"
        ):
            raise ScopeAccessDeniedError(instance=str(request.url.path))
    return user


def _serialize_connector(rec: EnterpriseConnectorRecord) -> EnterpriseConnectorItemResponse:
    return EnterpriseConnectorItemResponse(
        id=rec.id,
        connector_kind=rec.connector_kind,
        name=rec.name,
        base_url=rec.base_url,
        auth_mode=rec.auth_mode,
        enabled=rec.enabled,
        admin_secret_status=ConnectorSecretStatusResponse(
            configured=rec.admin_secret_status.configured,
            fingerprint=rec.admin_secret_status.fingerprint,
            updated_at_iso=rec.admin_secret_status.updated_at_iso,
        ),
        created_at_iso=rec.created_at_iso,
        updated_at_iso=rec.updated_at_iso,
    )


def _serialize_passthrough_view(
    v: UserPassthroughConnectorView,
) -> UserPassthroughConnectorItemResponse:
    return UserPassthroughConnectorItemResponse(
        connector_id=v.connector_id,
        connector_name=v.connector_name,
        connector_kind=v.connector_kind,
        base_url=v.base_url,
        auth_mode=v.auth_mode,
        connected=v.connected,
        external_author_login=v.external_author_login,
        secret_status=ConnectorSecretStatusResponse(
            configured=v.secret_status.configured,
            fingerprint=v.secret_status.fingerprint,
            updated_at_iso=v.secret_status.updated_at_iso,
        ),
    )


# ---------------------------------------------------------------------------
# Platform Connectors (`/api/v1/settings/connectors`)
# ---------------------------------------------------------------------------


@router.get(
    "/settings/connectors",
    response_model=EnterpriseConnectorsListResponse,
    summary="List all platform-level Enterprise Connectors (Socle)",
)
async def list_enterprise_connectors(request: Request) -> EnterpriseConnectorsListResponse:
    if _pg_enabled():
        engine = get_or_create_shared_db_engine(request)
        connectors = await list_enterprise_connectors_from_postgres18(engine)
    else:
        svc = _get_in_memory_service(request)
        connectors = svc.list_connectors()

    return EnterpriseConnectorsListResponse(
        items=[_serialize_connector(c) for c in connectors],
        trace_id=_trace(request),
    )


@router.post(
    "/settings/connectors",
    response_model=EnterpriseConnectorItemResponse,
    status_code=201,
    summary="Register a new platform-level Enterprise Connector",
)
async def create_enterprise_connector(
    request: Request,
    payload: EnterpriseConnectorCreateRequest,
    persona: Annotated[str | None, Query(alias="persona")] = None,
) -> EnterpriseConnectorItemResponse:
    _enforce_mutation_access(request, require_admin=True, persona_key=persona)
    validate_safe_connector_base_url(
        payload.base_url,
        instance=str(request.url.path),
        allow_smtp_schemes=(payload.connector_kind == "SMTP_MAIL"),
    )

    auth_svc = get_auth_service(request)
    if _pg_enabled():
        engine = get_or_create_shared_db_engine(request)
        rec = await create_enterprise_connector_on_postgres18(
            engine,
            cipher=auth_svc.vault_cipher,
            connector_kind=payload.connector_kind,
            name=payload.name,
            base_url=payload.base_url,
            auth_mode=payload.auth_mode,
            admin_secret_value=payload.admin_secret_value,
            enabled=payload.enabled,
            instance=str(request.url.path),
        )
    else:
        svc = _get_in_memory_service(request)
        rec = svc.create_connector(
            connector_kind=payload.connector_kind,
            name=payload.name,
            base_url=payload.base_url,
            auth_mode=payload.auth_mode,
            admin_secret_value=payload.admin_secret_value,
            enabled=payload.enabled,
            instance=str(request.url.path),
        )

    return _serialize_connector(rec)


@router.patch(
    "/settings/connectors/{connector_id}",
    response_model=EnterpriseConnectorItemResponse,
    summary="Update a platform Enterprise Connector and manage its AES-256-GCM secret",
)
async def update_enterprise_connector(
    request: Request,
    connector_id: Annotated[str, Path()],
    payload: EnterpriseConnectorUpdateRequest,
    persona: Annotated[str | None, Query(alias="persona")] = None,
) -> EnterpriseConnectorItemResponse:
    _enforce_mutation_access(request, require_admin=True, persona_key=persona)

    auth_svc = get_auth_service(request)
    if _pg_enabled():
        engine = get_or_create_shared_db_engine(request)
        rec = await update_enterprise_connector_on_postgres18(
            engine,
            connector_id,
            cipher=auth_svc.vault_cipher,
            name=payload.name,
            base_url=payload.base_url,
            auth_mode=payload.auth_mode,
            enabled=payload.enabled,
            admin_secret_value=payload.admin_secret_value,
            clear_admin_secret=payload.clear_admin_secret,
            instance=str(request.url.path),
        )
    else:
        svc = _get_in_memory_service(request)
        rec = svc.update_connector(
            connector_id,
            name=payload.name,
            base_url=payload.base_url,
            auth_mode=payload.auth_mode,
            enabled=payload.enabled,
            admin_secret_value=payload.admin_secret_value,
            clear_admin_secret=payload.clear_admin_secret,
            instance=str(request.url.path),
        )

    return _serialize_connector(rec)


@router.delete(
    "/settings/connectors/{connector_id}",
    response_model=EnterpriseConnectorDeleteResponse,
    summary="Delete a platform Enterprise Connector and cascade tokens",
)
async def delete_enterprise_connector(
    request: Request,
    connector_id: Annotated[str, Path()],
    persona: Annotated[str | None, Query(alias="persona")] = None,
) -> EnterpriseConnectorDeleteResponse:
    _enforce_mutation_access(request, require_admin=True, persona_key=persona)

    if _pg_enabled():
        engine = get_or_create_shared_db_engine(request)
        await delete_enterprise_connector_on_postgres18(
            engine, connector_id, instance=str(request.url.path)
        )
    else:
        svc = _get_in_memory_service(request)
        svc.delete_connector(connector_id, instance=str(request.url.path))

    return EnterpriseConnectorDeleteResponse(
        deleted=True,
        connector_id=connector_id,
        trace_id=_trace(request),
    )


# ---------------------------------------------------------------------------
# Mon Compte & Passthrough (`/api/v1/users/me/*`)
# ---------------------------------------------------------------------------


@router.get(
    "/users/me/account-profile",
    response_model=UserAccountProfileResponse,
    summary="Retrieve current user profile, active roles and FinOps team attachments",
)
async def get_user_account_profile(
    request: Request,
    persona: Annotated[str | None, Query(alias="persona")] = None,
) -> UserAccountProfileResponse:
    effective_persona = persona or request.headers.get("x-orcia-persona", "").strip() or None
    user = resolve_request_user(request, persona_key=effective_persona)

    if _pg_enabled():
        engine = get_or_create_shared_db_engine(request)
        prof = await get_user_account_profile_from_postgres18(
            engine,
            user_id=user.email or user.id,
            default_roles=[user.platform_role],
        )
        teams = [
            UserAccountOrgUnitItemResponse(
                id=t.id,
                slug=t.slug,
                name=t.name,
                unit_type=t.unit_type,
                billing_enabled=t.billing_enabled,
                is_lead=t.is_lead,
            )
            for t in prof.teams
        ]
        billing_units = [
            UserAccountOrgUnitItemResponse(
                id=b.id,
                slug=b.slug,
                name=b.name,
                unit_type=b.unit_type,
                billing_enabled=b.billing_enabled,
                is_lead=b.is_lead,
            )
            for b in prof.billing_org_units
        ]
        return UserAccountProfileResponse(
            principal_id=prof.principal_id,
            display_name=prof.display_name,
            email=prof.email,
            roles=list(prof.roles),
            teams=teams,
            billing_org_units=billing_units,
            trace_id=_trace(request),
        )

    # In-memory fast path
    return UserAccountProfileResponse(
        principal_id=user.email or user.id,
        display_name=user.display_name or user.email or user.id,
        email=user.email or user.id,
        roles=[user.platform_role],
        teams=[],
        billing_org_units=[],
        trace_id=_trace(request),
    )


@router.get(
    "/users/me/passthrough-tokens",
    response_model=UserPassthroughTokensListResponse,
    summary="List per-user passthrough connection status for all enabled tools",
)
async def list_user_passthrough_tokens(
    request: Request,
    persona: Annotated[str | None, Query(alias="persona")] = None,
) -> UserPassthroughTokensListResponse:
    effective_persona = persona or request.headers.get("x-orcia-persona", "").strip() or None
    user = resolve_request_user(request, persona_key=effective_persona)
    uid = user.email or user.id

    if _pg_enabled():
        engine = get_or_create_shared_db_engine(request)
        views = await list_user_passthrough_tokens_from_postgres18(engine, user_id=uid)
    else:
        svc = _get_in_memory_service(request)
        views = svc.list_user_passthrough_tokens(uid)

    return UserPassthroughTokensListResponse(
        items=[_serialize_passthrough_view(v) for v in views],
        trace_id=_trace(request),
    )


@router.put(
    "/users/me/passthrough-tokens/{connector_id}",
    response_model=UserPassthroughConnectorItemResponse,
    summary="Set or update personal passthrough token (AES-256-GCM Write-Only)",
)
async def upsert_user_passthrough_token(
    request: Request,
    connector_id: Annotated[str, Path()],
    payload: UpsertPassthroughTokenRequest,
    persona: Annotated[str | None, Query(alias="persona")] = None,
) -> UserPassthroughConnectorItemResponse:
    user = _enforce_mutation_access(request, require_admin=False, persona_key=persona)
    uid = user.email or user.id

    auth_svc = get_auth_service(request)
    if _pg_enabled():
        engine = get_or_create_shared_db_engine(request)
        view = await upsert_user_passthrough_token_on_postgres18(
            engine,
            cipher=auth_svc.vault_cipher,
            user_id=uid,
            connector_id=connector_id,
            external_author_login=payload.external_author_login,
            secret_value=payload.secret_value,
            instance=str(request.url.path),
        )
    else:
        svc = _get_in_memory_service(request)
        view = svc.upsert_user_passthrough_token(
            user_id=uid,
            connector_id=connector_id,
            external_author_login=payload.external_author_login,
            secret_value=payload.secret_value,
            instance=str(request.url.path),
        )

    return _serialize_passthrough_view(view)


@router.delete(
    "/users/me/passthrough-tokens/{connector_id}",
    response_model=RevokePassthroughTokenResponse,
    summary="Revoke personal passthrough token for a connector",
)
async def revoke_user_passthrough_token(
    request: Request,
    connector_id: Annotated[str, Path()],
    persona: Annotated[str | None, Query(alias="persona")] = None,
) -> RevokePassthroughTokenResponse:
    user = _enforce_mutation_access(request, require_admin=False, persona_key=persona)
    uid = user.email or user.id

    if _pg_enabled():
        engine = get_or_create_shared_db_engine(request)
        await revoke_user_passthrough_token_on_postgres18(
            engine,
            user_id=uid,
            connector_id=connector_id,
            instance=str(request.url.path),
        )
    else:
        svc = _get_in_memory_service(request)
        svc.revoke_user_passthrough_token(
            user_id=uid,
            connector_id=connector_id,
            instance=str(request.url.path),
        )

    return RevokePassthroughTokenResponse(
        revoked=True,
        connector_id=connector_id,
        trace_id=_trace(request),
    )
