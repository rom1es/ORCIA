"""OpenAPI 3.1 / Pydantic v2 transport schemas for Platform Authentication Policy & 2FA."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

from orcia_api.schemas.auth_and_org import AuthTokenResponse

PlatformAuthModeLiteral = Literal["LOCAL", "SSO"]
PlatformTwoFactorModeLiteral = Literal["NONE", "EMAIL_OTP", "TOTP"]
LoginChallengeKindLiteral = Literal["EMAIL_OTP", "TOTP", "TOTP_ENROLL"]


class PublicAuthConfigResponse(BaseModel):
    """Anonymous login page bootstrap configuration (never exposes secrets)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    auth_mode: PlatformAuthModeLiteral
    two_factor_mode: PlatformTwoFactorModeLiteral
    oidc_enabled: bool
    sso_button_label: str | None = Field(default=None, max_length=160)
    boot_epoch: str = Field(..., max_length=64)
    trace_id: str = Field(..., min_length=32, max_length=32)


class PlatformAuthSettingsResponse(BaseModel):
    """Administrator view of exclusive authentication mode, 2FA, and OIDC configuration."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    auth_mode: PlatformAuthModeLiteral
    two_factor_mode: PlatformTwoFactorModeLiteral
    oidc_issuer_url: str | None = Field(default=None, max_length=512)
    oidc_client_id: str | None = Field(default=None, max_length=255)
    oidc_client_secret_configured: bool = False
    oidc_client_secret_fingerprint: str | None = Field(default=None, max_length=64)
    oidc_scopes: str = Field(default="openid profile email", max_length=255)
    oidc_redirect_uri: str | None = Field(default=None, max_length=512)
    sso_button_label: str | None = Field(default=None, max_length=160)
    smtp_connector_configured: bool = False
    smtp_connector_name: str | None = Field(default=None, max_length=160)
    boot_epoch: str = Field(..., max_length=64)
    updated_by: str | None = Field(default=None, max_length=255)
    updated_at_iso: str = ""
    trace_id: str = Field(..., min_length=32, max_length=32)


class UpdatePlatformAuthSettingsRequest(BaseModel):
    """Payload for `PUT /api/v1/settings/authentication` (`PLATFORM_ADMIN` only)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    auth_mode: PlatformAuthModeLiteral
    two_factor_mode: PlatformTwoFactorModeLiteral = "NONE"
    oidc_issuer_url: str | None = Field(default=None, max_length=512)
    oidc_client_id: str | None = Field(default=None, max_length=255)
    oidc_client_secret: str | None = Field(default=None, max_length=1024)
    clear_oidc_client_secret: bool = False
    oidc_scopes: str = Field(default="openid profile email", max_length=255)
    oidc_redirect_uri: str | None = Field(default=None, max_length=512)
    sso_button_label: str | None = Field(default=None, max_length=160)


class OidcDiscoveryTestRequest(BaseModel):
    """Payload for `POST /api/v1/settings/authentication/test-oidc`."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    issuer_url: str = Field(..., min_length=4, max_length=512)


class OidcDiscoveryTestResponse(BaseModel):
    """Result of OIDC `.well-known/openid-configuration` discovery test."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    ok: bool = True
    issuer: str = Field(..., max_length=512)
    authorization_endpoint: str = Field(..., max_length=512)
    token_endpoint: str = Field(..., max_length=512)
    userinfo_endpoint: str | None = Field(default=None, max_length=512)
    latency_ms: float = Field(..., ge=0.0)
    trace_id: str = Field(..., min_length=32, max_length=32)


class VerifyLoginTwoFactorRequest(BaseModel):
    """Step-2 verification request for `EMAIL_OTP`, `TOTP`, or `TOTP_ENROLL`."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    challenge_token: str = Field(..., min_length=16, max_length=255)
    code: str = Field(..., min_length=6, max_length=6)


class ResendLoginTwoFactorRequest(BaseModel):
    """Request to resend a fresh 6-digit `EMAIL_OTP` code for an active challenge."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    challenge_token: str = Field(..., min_length=16, max_length=255)


class ResendLoginTwoFactorResponse(BaseModel):
    """Confirmation of 6-digit `EMAIL_OTP` regeneration and SMTP dispatch."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    sent: bool = True
    masked_destination: str | None = Field(default=None, max_length=255)
    expires_in_seconds: int = Field(..., ge=60)
    trace_id: str = Field(..., min_length=32, max_length=32)


class OidcAuthorizeUrlResponse(BaseModel):
    """OIDC Authorization Code flow redirect URL & CSRF state."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    authorize_url: str = Field(..., max_length=2048)
    state: str = Field(..., min_length=16, max_length=255)
    trace_id: str = Field(..., min_length=32, max_length=32)


class OidcCallbackExchangeRequest(BaseModel):
    """OIDC authorization code + CSRF state exchange payload."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    code: str = Field(..., min_length=1, max_length=2048)
    state: str = Field(..., min_length=16, max_length=255)
    redirect_uri: str | None = Field(default=None, max_length=512)


class AuthSessionBootstrapResponse(BaseModel):
    """Silent anonymous/authenticated browser session bootstrap payload (`GET /auth/session`)."""

    model_config = ConfigDict(extra="forbid", frozen=True)

    authenticated: bool
    session: AuthTokenResponse | None = None
    trace_id: str = Field(..., min_length=32, max_length=32)
