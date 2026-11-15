"""Exclusive Platform Authentication Policy (`LOCAL` vs `SSO`) and 2FA Domain Rules."""

from __future__ import annotations

import hashlib
import hmac
import secrets
from dataclasses import dataclass, replace
from datetime import UTC, datetime, timedelta
from typing import Literal
from urllib.parse import quote

from orcia_core.permissions.crypto import PassthroughVaultCipher
from orcia_core.permissions.enterprise_connectors_crypto import (
    compute_secret_fingerprint,
    pack_encrypted_secret,
    unpack_encrypted_secret,
    validate_safe_connector_base_url,
)
from orcia_core.permissions.errors import (
    SmtpConnectorRequiredForEmailOtpError,
    SsoConfigurationIncompleteError,
    ValidationDomainError,
)
from orcia_kernel.ids import new_uuid7_str

PlatformAuthMode = Literal["LOCAL", "SSO"]
PlatformTwoFactorMode = Literal["NONE", "EMAIL_OTP", "TOTP"]
LoginChallengeKind = Literal["EMAIL_OTP", "TOTP", "TOTP_ENROLL"]

VALID_PLATFORM_AUTH_MODES: tuple[PlatformAuthMode, ...] = ("LOCAL", "SSO")
VALID_TWO_FACTOR_MODES: tuple[PlatformTwoFactorMode, ...] = ("NONE", "EMAIL_OTP", "TOTP")
EMAIL_OTP_TTL_SECONDS = 300
TOTP_CHALLENGE_TTL_SECONDS = 300
DEFAULT_LOGIN_CHALLENGE_MAX_ATTEMPTS = 5
DEFAULT_BOOT_EPOCH = "00000000-0000-7000-8000-000000000001"


@dataclass(frozen=True, slots=True)
class PlatformAuthPolicyState:
    """Singleton platform authentication policy snapshot (`platform_auth_settings`)."""

    auth_mode: PlatformAuthMode = "LOCAL"
    two_factor_mode: PlatformTwoFactorMode = "NONE"
    oidc_issuer_url: str | None = None
    oidc_client_id: str | None = None
    oidc_client_secret_configured: bool = False
    oidc_client_secret_fingerprint: str | None = None
    oidc_scopes: str = "openid profile email"
    oidc_redirect_uri: str | None = None
    sso_button_label: str | None = None
    smtp_connector_configured: bool = False
    smtp_connector_name: str | None = None
    boot_epoch: str = DEFAULT_BOOT_EPOCH
    updated_by: str | None = None
    updated_at_iso: str = ""


@dataclass(frozen=True, slots=True)
class LoginSecondFactorChallengeRecord:
    """Single-use step-2 authentication challenge metadata."""

    id: str
    user_id: str
    challenge_kind: LoginChallengeKind
    challenge_token_hash: str
    otp_code_hash: str | None
    pending_totp_secret_encrypted: str | None
    masked_destination: str | None
    attempts_count: int
    max_attempts: int
    expires_at: datetime
    consumed_at: datetime | None = None


def generate_numeric_otp_code(*, digits: int = 6) -> str:
    """Generate a cryptographically random `digits`-digit verification code."""
    return str(secrets.randbelow(10**digits)).zfill(digits)


def generate_opaque_challenge_token() -> str:
    """Generate a high-entropy single-use challenge token (raw value returned once)."""
    return secrets.token_urlsafe(32)


def hash_challenge_token(token: str) -> str:
    """Compute canonical SHA-256 hex digest of an opaque challenge token."""
    return hashlib.sha256(token.strip().encode("utf-8")).hexdigest()


def hash_otp_code(*, challenge_id: str, otp_code: str) -> str:
    """Compute a per-challenge keyed SHA-256 digest of the 6-digit OTP."""
    return hmac.new(
        f"orcia:email-otp:{challenge_id}".encode(),
        otp_code.strip().encode("utf-8"),
        hashlib.sha256,
    ).hexdigest()


def verify_otp_code_hash(*, challenge_id: str, candidate_code: str, expected_hash: str) -> bool:
    """Constant-time verification of a 6-digit email OTP code against its stored digest."""
    normalized = candidate_code.strip()
    if len(normalized) != 6 or not normalized.isdigit():
        return False
    candidate_hash = hash_otp_code(challenge_id=challenge_id, otp_code=normalized)
    return hmac.compare_digest(candidate_hash, expected_hash)


def mask_email_address(email: str) -> str:
    """Mask an email local-part cleanly (e.g. `a***e@company.com`)."""
    cleaned = email.strip()
    if "@" not in cleaned:
        return "***"
    local, domain = cleaned.split("@", 1)
    masked_local = f"{local[:1]}***" if len(local) <= 2 else f"{local[0]}***{local[-1]}"
    return f"{masked_local}@{domain}"


def format_totp_manual_key(secret_b32: str) -> str:
    """Group Base32 secret into 4-char space-separated blocks for manual authenticator entry."""
    cleaned = secret_b32.strip().upper().replace(" ", "")
    return " ".join(cleaned[i : i + 4] for i in range(0, len(cleaned), 4))


def build_totp_provisioning_uri(
    *,
    secret_b32: str,
    account_email: str,
    issuer: str = "ORCIA",
) -> str:
    """Build standard RFC 6238 `otpauth://totp/...` provisioning URI without QR dependencies."""
    cleaned_secret = secret_b32.strip().upper().replace(" ", "")
    label = quote(f"{issuer}:{account_email.strip().lower()}", safe=":@")
    issuer_q = quote(issuer, safe="")
    return (
        f"otpauth://totp/{label}?secret={cleaned_secret}"
        f"&issuer={issuer_q}&algorithm=SHA1&digits=6&period=30"
    )


def pack_totp_secret_for_user(
    cipher: PassthroughVaultCipher,
    *,
    user_id: str,
    secret_b32: str,
) -> str:
    """Encrypt a user's Base32 TOTP secret using AES-256-GCM bound to `user_id`."""
    return pack_encrypted_secret(
        cipher,
        owner_id=f"totp:{user_id.strip()}",
        plaintext=secret_b32.strip().upper().replace(" ", ""),
        scheme="totp",
        host="local",
    )


def unpack_totp_secret_for_user(
    cipher: PassthroughVaultCipher,
    *,
    user_id: str,
    packed: str,
) -> str:
    """Decrypt and authenticate an AES-256-GCM packed user TOTP secret."""
    return unpack_encrypted_secret(
        cipher,
        owner_id=f"totp:{user_id.strip()}",
        packed=packed,
        scheme="totp",
        host="local",
    )


def validate_platform_auth_policy_update(
    *,
    auth_mode: str,
    two_factor_mode: str,
    oidc_issuer_url: str | None,
    oidc_client_id: str | None,
    oidc_scopes: str | None,
    oidc_redirect_uri: str | None,
    sso_button_label: str | None,
    has_active_smtp_connector: bool,
    instance: str | None = None,
) -> tuple[str | None, str | None, str, str | None, str | None]:
    """Validate and normalize platform authentication policy parameters before persistence."""
    if auth_mode not in VALID_PLATFORM_AUTH_MODES:
        raise ValidationDomainError(
            detail_override="auth_mode must be 'LOCAL' or 'SSO'.",
            instance=instance,
        )
    if two_factor_mode not in VALID_TWO_FACTOR_MODES:
        raise ValidationDomainError(
            detail_override="two_factor_mode must be 'NONE', 'EMAIL_OTP', or 'TOTP'.",
            instance=instance,
        )

    clean_issuer = (
        validate_safe_connector_base_url(oidc_issuer_url, instance=instance)
        if oidc_issuer_url and oidc_issuer_url.strip()
        else None
    )
    clean_redirect = (
        validate_safe_connector_base_url(oidc_redirect_uri, instance=instance)
        if oidc_redirect_uri and oidc_redirect_uri.strip()
        else None
    )
    clean_client_id = oidc_client_id.strip() if oidc_client_id and oidc_client_id.strip() else None
    clean_scopes = " ".join((oidc_scopes or "").split()) or "openid profile email"
    clean_label = (
        sso_button_label.strip() if sso_button_label and sso_button_label.strip() else None
    )

    if auth_mode == "SSO":
        if not clean_issuer or not clean_client_id or not clean_redirect:
            raise SsoConfigurationIncompleteError(instance=instance)
    elif two_factor_mode == "EMAIL_OTP" and not has_active_smtp_connector:
        raise SmtpConnectorRequiredForEmailOtpError(instance=instance)

    return clean_issuer, clean_client_id, clean_scopes, clean_redirect, clean_label


class InMemoryPlatformAuthPolicyStore:
    """Thread/async-safe in-memory store mirroring `platform_auth_settings` for unit tests."""

    def __init__(self, *, cipher: PassthroughVaultCipher | None = None) -> None:
        self._cipher = cipher
        self._state = PlatformAuthPolicyState(
            auth_mode="LOCAL",
            two_factor_mode="NONE",
            boot_epoch=new_uuid7_str(),
            updated_at_iso=datetime.now(UTC).isoformat(),
        )
        self._encrypted_oidc_secret: str | None = None
        self._challenges: dict[str, LoginSecondFactorChallengeRecord] = {}

    def get_state(self) -> PlatformAuthPolicyState:
        return self._state

    def update_policy(
        self,
        *,
        auth_mode: PlatformAuthMode,
        two_factor_mode: PlatformTwoFactorMode,
        oidc_issuer_url: str | None = None,
        oidc_client_id: str | None = None,
        oidc_client_secret: str | None = None,
        clear_oidc_client_secret: bool = False,
        oidc_scopes: str = "openid profile email",
        oidc_redirect_uri: str | None = None,
        sso_button_label: str | None = None,
        has_active_smtp_connector: bool = False,
        smtp_connector_name: str | None = None,
        updated_by: str | None = None,
        instance: str | None = None,
    ) -> PlatformAuthPolicyState:
        clean_issuer, clean_cid, clean_scopes, clean_redirect, clean_label = (
            validate_platform_auth_policy_update(
                auth_mode=auth_mode,
                two_factor_mode=two_factor_mode,
                oidc_issuer_url=oidc_issuer_url,
                oidc_client_id=oidc_client_id,
                oidc_scopes=oidc_scopes,
                oidc_redirect_uri=oidc_redirect_uri,
                sso_button_label=sso_button_label,
                has_active_smtp_connector=has_active_smtp_connector,
                instance=instance,
            )
        )
        secret_configured = self._state.oidc_client_secret_configured
        secret_fp = self._state.oidc_client_secret_fingerprint
        if clear_oidc_client_secret:
            self._encrypted_oidc_secret = None
            secret_configured = False
            secret_fp = None
        elif oidc_client_secret and oidc_client_secret.strip():
            plain = oidc_client_secret.strip()
            secret_fp = compute_secret_fingerprint("platform_auth:oidc", plain)
            secret_configured = True
            if self._cipher is not None:
                self._encrypted_oidc_secret = pack_encrypted_secret(
                    self._cipher,
                    owner_id="platform_auth:oidc",
                    plaintext=plain,
                    scheme="https",
                    host="oidc",
                )
        self._state = replace(
            self._state,
            auth_mode=auth_mode,
            two_factor_mode=two_factor_mode,
            oidc_issuer_url=clean_issuer,
            oidc_client_id=clean_cid,
            oidc_client_secret_configured=secret_configured,
            oidc_client_secret_fingerprint=secret_fp,
            oidc_scopes=clean_scopes,
            oidc_redirect_uri=clean_redirect,
            sso_button_label=clean_label,
            smtp_connector_configured=has_active_smtp_connector,
            smtp_connector_name=smtp_connector_name,
            updated_by=updated_by,
            updated_at_iso=datetime.now(UTC).isoformat(),
        )
        return self._state


def challenge_expiry(ttl_seconds: int = EMAIL_OTP_TTL_SECONDS) -> datetime:
    """Return UTC expiration timestamp for a login 2FA challenge."""
    return datetime.now(UTC) + timedelta(seconds=ttl_seconds)


__all__ = [
    "DEFAULT_BOOT_EPOCH",
    "DEFAULT_LOGIN_CHALLENGE_MAX_ATTEMPTS",
    "EMAIL_OTP_TTL_SECONDS",
    "InMemoryPlatformAuthPolicyStore",
    "LoginChallengeKind",
    "LoginSecondFactorChallengeRecord",
    "PlatformAuthMode",
    "PlatformAuthPolicyState",
    "PlatformTwoFactorMode",
    "TOTP_CHALLENGE_TTL_SECONDS",
    "VALID_PLATFORM_AUTH_MODES",
    "VALID_TWO_FACTOR_MODES",
    "build_totp_provisioning_uri",
    "challenge_expiry",
    "format_totp_manual_key",
    "generate_numeric_otp_code",
    "generate_opaque_challenge_token",
    "hash_challenge_token",
    "hash_otp_code",
    "mask_email_address",
    "pack_totp_secret_for_user",
    "unpack_totp_secret_for_user",
    "validate_platform_auth_policy_update",
    "verify_otp_code_hash",
]
