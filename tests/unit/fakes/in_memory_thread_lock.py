"""In-memory fake for `ThreadTurnLockPort` for unit tests (`tests/unit/fakes/`)."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass

from orcia_core.orchestration.errors import ThreadTurnLockHeldError


@dataclass
class _FakeThreadLockEntry:
    holder_user_id: str
    token: str
    expires_at_monotonic: float


class InMemoryThreadTurnLock:
    """Deterministic unit-test fake implementing `ThreadTurnLockPort` (`AD-19`)."""

    def __init__(self) -> None:
        self._locks: dict[str, _FakeThreadLockEntry] = {}

    @staticmethod
    def build_key(thread_id: str) -> str:
        return f"lock:thread:{thread_id}"

    def acquire_sync(
        self, *, thread_id: str, user_id: str, ttl_seconds: int = 60
    ) -> tuple[str, str]:
        now = time.monotonic()
        key = self.build_key(thread_id)
        existing = self._locks.get(thread_id)
        if (
            existing is not None
            and existing.expires_at_monotonic > now
            and existing.holder_user_id != user_id
        ):
            raise ThreadTurnLockHeldError(
                detail_override=(
                    f"Active Redis turn lock on {key} (held by '{existing.holder_user_id}')."
                )
            )
        token = uuid.uuid4().hex
        self._locks[thread_id] = _FakeThreadLockEntry(
            holder_user_id=user_id,
            token=token,
            expires_at_monotonic=now + float(ttl_seconds),
        )
        return key, token

    def release_sync(self, *, thread_id: str, user_id: str, token: str | None = None) -> bool:
        existing = self._locks.get(thread_id)
        if existing is None or existing.holder_user_id != user_id:
            return False
        if token is not None and existing.token != token:
            return False
        del self._locks[thread_id]
        return True

    async def acquire_async(
        self, *, thread_id: str, user_id: str, ttl_seconds: int = 60
    ) -> tuple[str, str]:
        return self.acquire_sync(thread_id=thread_id, user_id=user_id, ttl_seconds=ttl_seconds)

    async def release_async(
        self, *, thread_id: str, user_id: str, token: str | None = None
    ) -> bool:
        return self.release_sync(thread_id=thread_id, user_id=user_id, token=token)


__all__ = ["InMemoryThreadTurnLock"]
