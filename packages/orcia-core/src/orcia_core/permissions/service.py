"""AuthAndOrganizationService: Bi-Mode Authentication (OIDC + Local Argon2id/TOTP) & Session Store.

Zero framework imports (`fastapi`, `sqlalchemy`, `dramatiq`, `redis`, `litellm`).
"""

from __future__ import annotations

import os
import threading
import time
from typing import Literal, Protocol

from orcia_core.domain.exceptions import (
    InvalidCredentialsError,
    InvalidMfaCodeError,
    ObserverModeReadOnlyError,
    ResourceNotFoundError,
    RevokedTokenError,
)
from orcia_core.domain.identifiers import new_uuid7_str
from orcia_core.permissions.crypto import (
    REFRESH_TOKEN_TTL_SECONDS,
    Argon2idPasswordHasher,
    JwtSessionManager,
    PassthroughVaultCipher,
    SessionTokenPair,
    TotpManager,
)
from orcia_core.permissions.evaluator import MatrixPermissionEvaluator
from orcia_core.permissions.models import (
    DatasourceScheme,
    PassthroughCredentialRecord,
    UserIdentity,
)

DEFAULT_TOTP_SECRET_KARIM: str = "JBSWY3DPEHPK3PXP"


class RevocationStoreProtocol(Protocol):
    """Port protocol for JWT/Refresh `jti` revocation (in-memory or Redis 7.4 adapter)."""

    def revoke_jti(self, jti: str, ttl_seconds: int = REFRESH_TOKEN_TTL_SECONDS) -> None:
        """Mark a token `jti` as revoked for `ttl_seconds`."""

    def is_revoked(self, jti: str) -> bool:
        """Return True if `jti` has been revoked."""


class RedisSyncClientProtocol(Protocol):
    """Minimal structural protocol matching `redis.Redis` without importing `redis`."""

    def set(self, name: str, value: str, *, ex: int | None = None) -> object:
        """Set key with expiration."""

    def exists(self, *names: str) -> int:
        """Return count of existing keys."""


class InMemoryRevocationStore:
    """Thread-safe in-memory token revocation store with monotonic TTL expiration."""

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._revoked: dict[str, float] = {}

    def revoke_jti(self, jti: str, ttl_seconds: int = REFRESH_TOKEN_TTL_SECONDS) -> None:
        if ttl_seconds > 0 and jti:
            with self._lock:
                self._revoked[jti] = time.monotonic() + ttl_seconds

    def is_revoked(self, jti: str) -> bool:
        with self._lock:
            expires_at = self._revoked.get(jti)
            if expires_at is None:
                return False
            if time.monotonic() < expires_at:
                return True
            del self._revoked[jti]
            return False


class KeyValueRevocationStore:
    """Adapter backing `RevocationStoreProtocol` with any Redis-compatible key-value client."""

    def __init__(
        self, kv_client: RedisSyncClientProtocol, key_prefix: str = "auth:revoked:"
    ) -> None:
        self._kv = kv_client
        self._prefix = key_prefix

    def revoke_jti(self, jti: str, ttl_seconds: int = REFRESH_TOKEN_TTL_SECONDS) -> None:
        self._kv.set(f"{self._prefix}{jti}", "1", ex=max(1, ttl_seconds))

    def is_revoked(self, jti: str) -> bool:
        return bool(self._kv.exists(f"{self._prefix}{jti}"))


class AuthAndOrganizationService:
    """Application service orchestrating hybrid auth, session revocation, and RBAC evaluation."""

    def __init__(
        self,
        *,
        evaluator: MatrixPermissionEvaluator,
        users: tuple[UserIdentity, ...],
        persona_map: dict[str, str],
        hasher: Argon2idPasswordHasher | None = None,
        jwt_manager: JwtSessionManager | None = None,
        vault_cipher: PassthroughVaultCipher | None = None,
        revocation_store: RevocationStoreProtocol | None = None,
    ) -> None:
        self.evaluator = evaluator
        self.hasher = hasher or Argon2idPasswordHasher()
        self.jwt_manager = jwt_manager or JwtSessionManager(
            signing_secret=os.environ.get(
                "ORCIA_JWT_SIGNING_SECRET", "orcia-story-1-2-jwt-signing-secret-key-2026"
            )
        )
        self.vault_cipher = vault_cipher or PassthroughVaultCipher(
            master_key=os.environ.get(
                "ORCIA_PASSTHROUGH_MASTER_KEY", "orcia-story-1-2-aes256gcm-master-key-2026"
            )
        )
        self.revocation_store: RevocationStoreProtocol = (
            revocation_store or InMemoryRevocationStore()
        )
        self._users_by_id: dict[str, UserIdentity] = {u.id: u for u in users}
        self._users_by_email: dict[str, UserIdentity] = {u.email.lower(): u for u in users}
        self._users_by_oidc: dict[str, UserIdentity] = {
            u.oidc_subject: u for u in users if u.oidc_subject
        }
        self._persona_map = dict(persona_map)
        self._passthrough_records: dict[str, PassthroughCredentialRecord] = {}

    def get_user_by_id(self, user_id: str) -> UserIdentity:
        """Retrieve user by ID or raise `ResourceNotFoundError`."""
        user = self._users_by_id.get(user_id)
        if user is None or not user.is_active:
            raise ResourceNotFoundError()
        return user

    def resolve_user(
        self,
        *,
        persona_key: str | None = None,
        bearer_token: str | None = None,
        now_ts: int | None = None,
    ) -> UserIdentity:
        """Resolve caller identity from Bearer JWT, persona key, or default `marc` (`TEAM_LEAD`)."""
        if bearer_token:
            raw = bearer_token.removeprefix("Bearer ").removeprefix("bearer ").strip()
            return self.authenticate_access_token(raw, now_ts=now_ts)
        key = (persona_key or "marc").strip().lower()
        user_id = self._persona_map.get(key)
        if user_id is None:
            raise ResourceNotFoundError()
        return self.get_user_by_id(user_id)

    def _issue_for_user(
        self, user: UserIdentity, auth_mode: str, now_ts: int | None
    ) -> SessionTokenPair:
        return self.jwt_manager.issue_token_pair(
            user_id=user.id,
            email=user.email,
            role=user.platform_role,
            org_unit_id=user.primary_org_unit_id,
            archetype=user.human_profile_archetype,
            auth_mode=auth_mode,
            now_ts=now_ts,
        )

    def login_local(
        self,
        email: str,
        password: str,
        *,
        totp_code: str | None = None,
        now_ts: int | None = None,
    ) -> tuple[UserIdentity, SessionTokenPair]:
        """Authenticate via local email + Argon2id password + optional TOTP MFA (AD-6)."""
        user = self._users_by_email.get(email.strip().lower())
        if (
            user is None
            or not user.is_active
            or user.auth_mode not in ("LOCAL", "HYBRID")
            or not user.password_hash_argon2id
            or not self.hasher.verify_password(user.password_hash_argon2id, password)
        ):
            raise InvalidCredentialsError()

        if user.totp_enabled:
            if not totp_code or not user.totp_secret:
                raise InvalidMfaCodeError()
            if not TotpManager.verify_code(user.totp_secret, totp_code, timestamp=now_ts):
                raise InvalidMfaCodeError()

        return user, self._issue_for_user(user, "LOCAL", now_ts)

    def login_oidc(
        self, oidc_subject: str, *, email: str | None = None, now_ts: int | None = None
    ) -> tuple[UserIdentity, SessionTokenPair]:
        """Authenticate via Enterprise OIDC / OAuth 2.1 subject claim (AD-6)."""
        user = self._users_by_oidc.get(oidc_subject.strip())
        if (
            user is None
            or not user.is_active
            or user.auth_mode not in ("OIDC", "HYBRID")
            or (email is not None and user.email.lower() != email.strip().lower())
        ):
            raise InvalidCredentialsError()

        return user, self._issue_for_user(user, "OIDC", now_ts)

    def authenticate_access_token(
        self, access_token: str, *, now_ts: int | None = None
    ) -> UserIdentity:
        """Verify access JWT and ensure its `jti` is not revoked."""
        claims = self.jwt_manager.verify_token(access_token, expected_type="access", now_ts=now_ts)
        if self.revocation_store.is_revoked(claims.jti):
            raise RevokedTokenError()
        return self.get_user_by_id(claims.sub)

    def refresh_session(
        self, refresh_token: str, *, now_ts: int | None = None
    ) -> tuple[UserIdentity, SessionTokenPair]:
        """Rotate refresh token (revoking prior `jti`) and issue a new 15-min JWT pair."""
        claims = self.jwt_manager.verify_token(
            refresh_token, expected_type="refresh", now_ts=now_ts
        )
        if self.revocation_store.is_revoked(claims.jti):
            raise RevokedTokenError()
        self.revocation_store.revoke_jti(claims.jti)
        user = self.get_user_by_id(claims.sub)
        return user, self._issue_for_user(user, claims.auth_mode, now_ts)

    def revoke_token(
        self,
        token: str,
        *,
        expected_type: Literal["access", "refresh"] = "refresh",
        now_ts: int | None = None,
    ) -> None:
        """Revoke an access or refresh token's `jti` in the revocation store."""
        claims = self.jwt_manager.verify_token(token, expected_type=expected_type, now_ts=now_ts)
        self.revocation_store.revoke_jti(claims.jti)

    def store_passthrough_credential(
        self,
        user: UserIdentity,
        *,
        connector_scheme: DatasourceScheme,
        target_host: str,
        plaintext_secret: str,
        instance: str | None = None,
    ) -> PassthroughCredentialRecord:
        """Encrypt and store a Passthrough credential in AES-256-GCM (never exposing plaintext)."""
        if user.platform_role in ("OBSERVER", "BU_DIRECTOR"):
            raise ObserverModeReadOnlyError(instance=instance)
        ciphertext_b64, nonce_b64 = self.vault_cipher.encrypt(
            user_id=user.id,
            plaintext_secret=plaintext_secret,
            connector_scheme=connector_scheme,
            target_host=target_host,
        )
        record = PassthroughCredentialRecord(
            id=new_uuid7_str(),
            user_id=user.id,
            connector_scheme=connector_scheme,
            target_host=target_host,
            ciphertext_b64=ciphertext_b64,
            nonce_b64=nonce_b64,
            key_version=1,
        )
        self._passthrough_records[record.id] = record
        return record

    def decrypt_passthrough_credential(self, user: UserIdentity, record_id: str) -> str:
        """Decrypt a stored Passthrough credential exclusively for its owning `user`."""
        record = self._passthrough_records.get(record_id)
        if record is None:
            raise ResourceNotFoundError()
        return self.vault_cipher.decrypt(
            user_id=user.id,
            ciphertext_b64=record.ciphertext_b64,
            nonce_b64=record.nonce_b64,
            connector_scheme=record.connector_scheme,
            target_host=record.target_host,
            key_version=record.key_version,
        )
