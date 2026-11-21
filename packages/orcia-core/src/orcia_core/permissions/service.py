"""AuthAndOrganizationService: Bi-Mode Authentication (OIDC + Local Argon2id/TOTP) & Session Store.

Zero framework imports (`fastapi`, `sqlalchemy`, `dramatiq`, `redis`, `litellm`).
"""

from __future__ import annotations

from typing import Literal

from orcia_core.config import get_env
from orcia_core.permissions._passthrough_helpers import (
    decrypt_passthrough_record,
    encrypt_passthrough_record,
)
from orcia_core.permissions.crypto import (
    Argon2idPasswordHasher,
    JwtSessionManager,
    PassthroughVaultCipher,
    SessionTokenPair,
    TokenClaims,
    TotpManager,
)
from orcia_core.permissions.errors import (
    AuthenticationRequiredError,
    InvalidCredentialsError,
    InvalidMfaCodeError,
    ResourceNotFoundError,
    RevokedTokenError,
)
from orcia_core.permissions.evaluator import MatrixPermissionEvaluator
from orcia_core.permissions.models import (
    DatasourceScheme,
    PassthroughCredentialRecord,
    UserIdentity,
)
from orcia_core.permissions.revocation import (
    PERSONA_IMPERSONATION_ENVIRONMENTS as PERSONA_IMPERSONATION_ENVIRONMENTS,
)
from orcia_core.permissions.revocation import (
    InMemoryRevocationStore as InMemoryRevocationStore,
)
from orcia_core.permissions.revocation import (
    KeyValueRevocationStore as KeyValueRevocationStore,
)
from orcia_core.permissions.revocation import (
    RedisSyncClientProtocol as RedisSyncClientProtocol,
)
from orcia_core.permissions.revocation import (
    RevocationStoreProtocol as RevocationStoreProtocol,
)
from orcia_core.permissions.revocation import (
    persona_impersonation_allowed as persona_impersonation_allowed,
)

DEFAULT_TOTP_SECRET_KARIM: str = "JBSWY3DPEHPK3PXP"


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
        allow_persona_impersonation: bool = False,
    ) -> None:
        self.evaluator = evaluator
        self.allow_persona_impersonation = allow_persona_impersonation
        self.hasher = hasher or Argon2idPasswordHasher()
        self.jwt_manager = jwt_manager or JwtSessionManager(
            signing_secret=get_env(
                "ORCIA_JWT_SIGNING_SECRET", "orcia-story-1-2-jwt-signing-secret-key-2026"
            )
        )
        self.vault_cipher = vault_cipher or PassthroughVaultCipher(
            master_key=get_env(
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

    def list_personas(self) -> tuple[str, ...]:
        """Return configured development persona keys (empty when isolated)."""
        return tuple(sorted(self._persona_map.keys()))

    def get_user_by_id(self, user_id: str) -> UserIdentity:
        """Retrieve user by ID or raise `ResourceNotFoundError`."""
        user = self._users_by_id.get(user_id)
        if user is None or not user.is_active:
            raise ResourceNotFoundError()
        return user

    def has_user_in_memory(self, user_id: str) -> bool:
        """Return True if user is present in memory and currently active."""
        user = self._users_by_id.get(user_id)
        return user is not None and user.is_active

    def register_user(self, user: UserIdentity) -> None:
        """Register or update an in-memory user identity."""
        self._users_by_id[user.id] = user
        self._users_by_email[user.email.lower()] = user
        if user.oidc_subject:
            self._users_by_oidc[user.oidc_subject] = user

    def unregister_user(self, user_id_or_email: str) -> None:
        """Unregister user from in-memory index."""
        target = self._users_by_id.pop(user_id_or_email, None)
        if target is None:
            target = self._users_by_email.pop(user_id_or_email.lower(), None)
        if target is not None:
            self._users_by_id.pop(target.id, None)
            self._users_by_email.pop(target.email.lower(), None)
            if target.oidc_subject:
                self._users_by_oidc.pop(target.oidc_subject, None)

    def resolve_user(
        self,
        *,
        persona_key: str | None = None,
        bearer_token: str | None = None,
        now_ts: int | None = None,
    ) -> UserIdentity:
        """Resolve caller identity from Bearer JWT, else (local / test only) a reference persona.

        Without `allow_persona_impersonation`, a missing Bearer raises `AuthenticationRequiredError`
        and any `persona_key` is ignored, so no caller can impersonate another user.
        """
        if bearer_token:
            raw = bearer_token.removeprefix("Bearer ").removeprefix("bearer ").strip()
            return self.authenticate_access_token(raw, now_ts=now_ts)
        if not self.allow_persona_impersonation:
            raise AuthenticationRequiredError()
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

    def verify_access_token_claims(
        self, bearer_or_raw_token: str, *, now_ts: int | None = None
    ) -> TokenClaims:
        """Verify signature, expiry and revocation of access JWT without requiring cached user."""
        raw = bearer_or_raw_token.removeprefix("Bearer ").removeprefix("bearer ").strip()
        claims = self.jwt_manager.verify_token(raw, expected_type="access", now_ts=now_ts)
        if self.revocation_store.is_revoked(claims.jti):
            raise RevokedTokenError()
        return claims

    def verify_refresh_token_claims(
        self, refresh_token: str, *, now_ts: int | None = None
    ) -> TokenClaims:
        """Verify signature, expiry and revocation of a refresh JWT without rotating it."""
        raw = refresh_token.removeprefix("Bearer ").removeprefix("bearer ").strip()
        claims = self.jwt_manager.verify_token(raw, expected_type="refresh", now_ts=now_ts)
        if self.revocation_store.is_revoked(claims.jti):
            raise RevokedTokenError()
        return claims

    def authenticate_access_token(
        self, access_token: str, *, now_ts: int | None = None
    ) -> UserIdentity:
        """Verify access JWT and ensure its `jti` is not revoked."""
        claims = self.verify_access_token_claims(access_token, now_ts=now_ts)
        return self.get_user_by_id(claims.sub)

    def bootstrap_access_from_refresh(
        self, refresh_token: str, *, now_ts: int | None = None
    ) -> tuple[UserIdentity, SessionTokenPair]:
        """Verify refresh JWT without rotating/revoking it and issue a fresh 15-min access JWT."""
        claims = self.verify_refresh_token_claims(refresh_token, now_ts=now_ts)
        user = self.get_user_by_id(claims.sub)
        issued = self._issue_for_user(user, claims.auth_mode, now_ts)
        return user, SessionTokenPair(
            access_token=issued.access_token,
            refresh_token=refresh_token,
            refresh_jti=claims.jti,
            access_jti=issued.access_jti,
            expires_in_seconds=issued.expires_in_seconds,
        )

    def refresh_session(
        self, refresh_token: str, *, now_ts: int | None = None
    ) -> tuple[UserIdentity, SessionTokenPair]:
        """Rotate refresh token (revoking prior `jti`) and issue a new 15-min JWT pair."""
        claims = self.verify_refresh_token_claims(refresh_token, now_ts=now_ts)
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
        record = encrypt_passthrough_record(
            self.vault_cipher,
            user,
            connector_scheme=connector_scheme,
            target_host=target_host,
            plaintext_secret=plaintext_secret,
            instance=instance,
        )
        self._passthrough_records[record.id] = record
        return record

    def decrypt_passthrough_credential(self, user: UserIdentity, record_id: str) -> str:
        """Decrypt a stored Passthrough credential exclusively for its owning `user`."""
        return decrypt_passthrough_record(
            self.vault_cipher, user, self._passthrough_records.get(record_id)
        )
