"""Bounded TTL & Cross-Worker Redis Version Cache for `platform_setup_snapshot` (`H-35`)."""

from __future__ import annotations

import os
import time
from typing import Any

from orcia_core.observability.logging import get_logger
from orcia_kernel.ids import new_uuid7_str

logger = get_logger("orcia.bootstrap.snapshot_cache")

PLATFORM_SETUP_SNAPSHOT_VERSION_KEY = "orcia:platform_setup_snapshot:version"
DEFAULT_PLATFORM_SETUP_SNAPSHOT_TTL_S = 30.0
_VERSION_KEY_TTL_S = 86400


def resolve_platform_setup_snapshot_ttl_seconds() -> float:
    """Resolve bounded TTL (`[0.1, 300.0]` seconds) for `app.state.platform_setup_snapshot`."""
    raw = os.environ.get("ORCIA_PLATFORM_SETUP_SNAPSHOT_TTL_S", "").strip()
    if not raw:
        return DEFAULT_PLATFORM_SETUP_SNAPSHOT_TTL_S
    try:
        val = float(raw)
    except ValueError:
        return DEFAULT_PLATFORM_SETUP_SNAPSHOT_TTL_S
    return min(300.0, max(0.1, val))


def _decode_version(raw: Any) -> str | None:
    if raw is None:
        return None
    val = raw.decode("utf-8") if isinstance(raw, bytes) else str(raw)
    return val.strip() or None


async def get_valid_platform_setup_snapshot_async(
    app_state: Any,
    *,
    redis_client: Any | None = None,
) -> Any | None:
    """Return cached `platform_setup_snapshot` only if within TTL and Redis version matches."""
    if app_state is None:
        return None
    snap = getattr(app_state, "platform_setup_snapshot", None)
    if snap is None:
        return None

    cached_at = getattr(app_state, "platform_setup_snapshot_cached_at", None)
    if cached_at is None:
        return snap

    age_s = time.monotonic() - float(cached_at)
    if age_s > resolve_platform_setup_snapshot_ttl_seconds():
        app_state.platform_setup_snapshot = None
        app_state.platform_setup_snapshot_cached_at = None
        app_state.platform_setup_snapshot_version = None
        return None

    if redis_client is not None:
        try:
            remote_ver = _decode_version(
                await redis_client.get(PLATFORM_SETUP_SNAPSHOT_VERSION_KEY)
            )
            local_ver = getattr(app_state, "platform_setup_snapshot_version", None)
            if remote_ver is not None and local_ver != remote_ver:
                app_state.platform_setup_snapshot = None
                app_state.platform_setup_snapshot_cached_at = None
                app_state.platform_setup_snapshot_version = None
                return None
        except Exception as exc:
            logger.warning(
                "platform_setup_snapshot_redis_check_failed",
                error_type=type(exc).__name__,
            )
    return snap


async def set_cached_platform_setup_snapshot_async(
    app_state: Any,
    snapshot: Any,
    *,
    redis_client: Any | None = None,
    version: str | None = None,
) -> None:
    """Store `platform_setup_snapshot` with bounded monotonic TTL and Redis version alignment."""
    if app_state is None:
        return
    resolved_ver = version
    if resolved_ver is None and redis_client is not None:
        try:
            resolved_ver = _decode_version(
                await redis_client.get(PLATFORM_SETUP_SNAPSHOT_VERSION_KEY)
            )
            if resolved_ver is None:
                resolved_ver = new_uuid7_str()
                await redis_client.set(
                    PLATFORM_SETUP_SNAPSHOT_VERSION_KEY, resolved_ver, ex=_VERSION_KEY_TTL_S
                )
        except Exception as exc:
            logger.warning(
                "platform_setup_snapshot_redis_version_read_failed",
                error_type=type(exc).__name__,
            )
    app_state.platform_setup_snapshot = snapshot
    app_state.platform_setup_snapshot_cached_at = time.monotonic()
    app_state.platform_setup_snapshot_version = resolved_ver


async def invalidate_platform_setup_snapshot_async(
    app_state: Any,
    *,
    redis_client: Any | None = None,
) -> str:
    """Clear local `platform_setup_snapshot` and rotate Redis version marker across workers."""
    next_version = new_uuid7_str()
    if app_state is not None:
        app_state.platform_setup_snapshot = None
        app_state.platform_setup_snapshot_cached_at = None
        app_state.platform_setup_snapshot_version = None
    if redis_client is not None:
        try:
            await redis_client.set(
                PLATFORM_SETUP_SNAPSHOT_VERSION_KEY, next_version, ex=_VERSION_KEY_TTL_S
            )
        except Exception as exc:
            logger.warning(
                "platform_setup_snapshot_redis_invalidate_failed",
                error_type=type(exc).__name__,
            )
    return next_version


__all__ = [
    "DEFAULT_PLATFORM_SETUP_SNAPSHOT_TTL_S",
    "PLATFORM_SETUP_SNAPSHOT_VERSION_KEY",
    "get_valid_platform_setup_snapshot_async",
    "invalidate_platform_setup_snapshot_async",
    "resolve_platform_setup_snapshot_ttl_seconds",
    "set_cached_platform_setup_snapshot_async",
]
