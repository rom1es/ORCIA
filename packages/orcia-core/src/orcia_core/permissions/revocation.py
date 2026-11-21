"""Token `jti` revocation stores and environment persona impersonation policy."""

from __future__ import annotations

import threading
import time
from typing import Protocol

from orcia_core.permissions.crypto import REFRESH_TOKEN_TTL_SECONDS

PERSONA_IMPERSONATION_ENVIRONMENTS: frozenset[str] = frozenset({"local", "test"})


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


def persona_impersonation_allowed(orcia_env: str) -> bool:
    """Return `True` only for `ORCIA_ENV` local / test (empty means local) — BUG-E2E-04.

    Outside these environments, identity must come from a verified Bearer JWT: the
    reference personas (`karim`, `claire`, `marc`, `nadia`) can never be selected by a caller.
    """
    return (orcia_env.strip().lower() or "local") in PERSONA_IMPERSONATION_ENVIRONMENTS
