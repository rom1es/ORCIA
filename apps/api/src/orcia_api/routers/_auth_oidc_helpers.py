"""OIDC Authorization Code flow helpers (`GET /oidc/authorize` & `POST /oidc/callback`)."""

from __future__ import annotations

import base64
import json
import secrets
import time
from urllib.parse import urlencode

from fastapi import Request, Response
from sqlalchemy.ext.asyncio import AsyncEngine

from orcia_api.routers._auth_policy_runtime import discover_oidc_endpoints
from orcia_api.routers._auth_token_issuer import (
    issue_completed_auth_response,
    user_identity_from_candidate,
)
from orcia_api.schemas.auth_and_org import AuthTokenResponse
from orcia_api.schemas.auth_policy import OidcAuthorizeUrlResponse, OidcCallbackExchangeRequest
from orcia_core.bootstrap import (
    load_auth_candidate_by_oidc_from_postgres18,
    load_decrypted_oidc_client_secret,
)
from orcia_core.observability.logging import get_logger
from orcia_core.permissions import (
    AuthAndOrganizationService,
    PlatformAuthPolicyState,
)
from orcia_core.permissions.errors import (
    InvalidCredentialsError,
    SsoAuthDisabledByPolicyError,
    SsoConfigurationIncompleteError,
    ValidationDomainError,
)

logger = get_logger("orcia.api.auth.oidc")
OIDC_STATE_COOKIE_NAME = "orcia_oidc_state"
OIDC_STATE_TTL_SECONDS = 600


def _issue_signed_oidc_state(svc: AuthAndOrganizationService) -> str:
    nonce = secrets.token_urlsafe(16)
    exp = int(time.time()) + OIDC_STATE_TTL_SECONDS
    ct_b64, nonce_b64 = svc.vault_cipher.encrypt(
        "oidc-state",
        f"{nonce}|{exp}",
        connector_scheme="https",
        target_host="oidc-state",
    )
    return f"{ct_b64}.{nonce_b64}"


def _verify_and_consume_oidc_state(svc: AuthAndOrganizationService, state: str) -> bool:
    parts = state.strip().split(".", 1)
    if len(parts) != 2:
        return False
    try:
        plain = svc.vault_cipher.decrypt(
            "oidc-state",
            parts[0],
            parts[1],
            connector_scheme="https",
            target_host="oidc-state",
        )
        nonce, exp_str = plain.split("|", 1)
        exp = int(exp_str)
    except Exception as exc:
        logger.warning("oidc_state_decrypt_failed", error_type=type(exc).__name__)
        return False
    if exp < int(time.time()):
        return False
    revoke_key = f"oidc-state:{nonce}"
    if svc.revocation_store.is_revoked(revoke_key):
        return False
    svc.revocation_store.revoke_jti(revoke_key, ttl_seconds=OIDC_STATE_TTL_SECONDS)
    return True


def _decode_jwt_claims_unverified(id_token: str) -> dict[str, object]:
    segments = id_token.split(".")
    if len(segments) != 3:
        return {}
    padded = segments[1] + "=" * ((4 - len(segments[1]) % 4) % 4)
    try:
        raw = base64.urlsafe_b64decode(padded.encode("ascii"))
        parsed = json.loads(raw.decode("utf-8"))
        return parsed if isinstance(parsed, dict) else {}
    except Exception as exc:
        logger.warning("oidc_id_token_decode_failed", error_type=type(exc).__name__)
        return {}


async def execute_oidc_authorize(
    *,
    request: Request,
    response: Response,
    svc: AuthAndOrganizationService,
    policy: PlatformAuthPolicyState,
    trace_id: str,
) -> OidcAuthorizeUrlResponse:
    """Build SSRF-validated OIDC Authorization Code redirect URL & single-use state."""
    if policy.auth_mode != "SSO":
        raise SsoAuthDisabledByPolicyError(instance=str(request.url.path))
    if not policy.oidc_issuer_url or not policy.oidc_client_id or not policy.oidc_redirect_uri:
        raise SsoConfigurationIncompleteError(instance=str(request.url.path))

    doc, _ = await discover_oidc_endpoints(request, issuer_url=policy.oidc_issuer_url)
    auth_endpoint = str(doc["authorization_endpoint"])
    state = _issue_signed_oidc_state(svc)
    query = urlencode(
        {
            "response_type": "code",
            "client_id": policy.oidc_client_id,
            "redirect_uri": policy.oidc_redirect_uri,
            "scope": policy.oidc_scopes or "openid profile email",
            "state": state,
        }
    )
    sep = "&" if "?" in auth_endpoint else "?"
    response.set_cookie(
        key=OIDC_STATE_COOKIE_NAME,
        value=state,
        max_age=OIDC_STATE_TTL_SECONDS,
        path="/api/v1/auth",
        httponly=True,
        samesite="lax",
    )
    return OidcAuthorizeUrlResponse(
        authorize_url=f"{auth_endpoint}{sep}{query}",
        state=state,
        trace_id=trace_id,
    )


async def execute_oidc_callback(
    *,
    engine: AsyncEngine | None,
    request: Request,
    response: Response,
    svc: AuthAndOrganizationService,
    payload: OidcCallbackExchangeRequest,
    trace_id: str,
) -> AuthTokenResponse:
    """Exchange OIDC authorization code, bind to PostgreSQL user, and mint ORCIA session JWT."""
    if engine is None:
        raise SsoConfigurationIncompleteError(instance=str(request.url.path))
    policy, client_secret = await load_decrypted_oidc_client_secret(engine, cipher=svc.vault_cipher)
    if policy.auth_mode != "SSO":
        raise SsoAuthDisabledByPolicyError(instance=str(request.url.path))
    if not policy.oidc_issuer_url or not policy.oidc_client_id or not policy.oidc_redirect_uri:
        raise SsoConfigurationIncompleteError(instance=str(request.url.path))

    cookie_state = request.cookies.get(OIDC_STATE_COOKIE_NAME)
    if cookie_state and cookie_state != payload.state:
        raise InvalidCredentialsError(instance=str(request.url.path))
    if not _verify_and_consume_oidc_state(svc, payload.state):
        raise InvalidCredentialsError(instance=str(request.url.path))
    response.delete_cookie(key=OIDC_STATE_COOKIE_NAME, path="/api/v1/auth")

    doc, _ = await discover_oidc_endpoints(request, issuer_url=policy.oidc_issuer_url)
    token_endpoint = str(doc["token_endpoint"])
    token_form: dict[str, str] = {
        "grant_type": "authorization_code",
        "code": payload.code,
        "redirect_uri": payload.redirect_uri or policy.oidc_redirect_uri,
        "client_id": policy.oidc_client_id,
    }
    if client_secret:
        token_form["client_secret"] = client_secret

    try:
        token_resp = await request.app.state.http_client.post(
            token_endpoint, data=token_form, timeout=10.0
        )
    except Exception as exc:
        logger.warning("oidc_token_exchange_failed", error_type=type(exc).__name__)
        raise ValidationDomainError(
            detail_override="OIDC token endpoint request failed.",
            instance=str(request.url.path),
        ) from exc
    if token_resp.status_code != 200:
        raise InvalidCredentialsError(instance=str(request.url.path))

    token_json = token_resp.json()
    sub = ""
    email: str | None = None
    userinfo_ep = str(doc.get("userinfo_endpoint") or "").strip() or None
    access_tok = str(token_json.get("access_token") or "").strip()
    if userinfo_ep and access_tok:
        try:
            ui_resp = await request.app.state.http_client.get(
                userinfo_ep,
                headers={"Authorization": f"Bearer {access_tok}"},
                timeout=5.0,
            )
            if ui_resp.status_code == 200:
                ui_data = ui_resp.json()
                sub = str(ui_data.get("sub") or "").strip()
                email = str(ui_data.get("email") or "").strip() or None
        except Exception as exc:
            logger.warning("oidc_userinfo_fetch_failed", error_type=type(exc).__name__)
    if not sub and token_json.get("id_token"):
        claims = _decode_jwt_claims_unverified(str(token_json["id_token"]))
        sub = str(claims.get("sub") or "").strip()
        email = email or (str(claims.get("email") or "").strip() or None)

    if not sub:
        raise InvalidCredentialsError(instance=str(request.url.path))

    async with engine.begin() as conn:
        candidate = await load_auth_candidate_by_oidc_from_postgres18(
            conn, oidc_subject=sub, email=email
        )
    if candidate is None or not candidate.is_active or candidate.iam_status == "DISABLED":
        raise InvalidCredentialsError(instance=str(request.url.path))

    user = user_identity_from_candidate(candidate, auth_mode="OIDC")
    return issue_completed_auth_response(
        response=response,
        request=request,
        svc=svc,
        user=user,
        trace_id=trace_id,
        auth_mode="OIDC",
    )
