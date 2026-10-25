"""Centralized environment & `.env` configuration loader for ORCIA (`packages/orcia-core`).

Ensures all components (`apps/api`, `apps/worker`, `infra/migrations`,
`infra/scripts/maintenance/*`, `scripts/*`, and `packages/orcia-core`) resolve their host, port,
path, and credential settings from the root `.env` file while preserving explicit process
environment overrides (`override=False`).
"""

from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv

REPO_ROOT: Path = Path(__file__).resolve().parents[4]
DEFAULT_ENV_FILE: Path = REPO_ROOT / ".env"

_ENV_LOADED = False


def load_orcia_env(*, env_file: Path | None = None, override: bool = False) -> Path:
    """Load the root `.env` file into `os.environ` without clobbering explicit env vars."""
    global _ENV_LOADED
    target = env_file or Path(os.environ.get("ORCIA_ENV_FILE", str(DEFAULT_ENV_FILE)))
    if target.is_file():
        load_dotenv(dotenv_path=target, override=override)
    _ENV_LOADED = True
    return target


def get_env(key: str, default: str = "") -> str:
    """Return environment variable value after ensuring `.env` has been loaded."""
    if not _ENV_LOADED:
        load_orcia_env()
    return os.environ.get(key, default)


def get_env_int(key: str, default: int) -> int:
    """Return integer environment variable value after ensuring `.env` has been loaded."""
    raw = get_env(key, str(default)).strip()
    try:
        return int(raw)
    except ValueError:
        return default


def resolve_database_url() -> str:
    """Resolve the async SQLAlchemy PostgreSQL URL from `.env` or `POSTGRES_*` components."""
    explicit = get_env("DATABASE_URL").strip()
    if explicit:
        return explicit
    user = get_env("POSTGRES_USER", "orcia")
    password = quote_plus(get_env("POSTGRES_PASSWORD", "orcia_dev_secret"))
    host = get_env("POSTGRES_HOST", "127.0.0.1")
    port = get_env_int("POSTGRES_PORT", 5433)
    db = get_env("POSTGRES_DB", "orcia")
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"


def resolve_redis_url() -> str:
    """Resolve the Redis broker URL from `.env` or `REDIS_*` components."""
    explicit = get_env("REDIS_URL").strip()
    if explicit:
        return explicit
    host = get_env("REDIS_HOST", "127.0.0.1")
    port = get_env_int("REDIS_PORT", 6380)
    db = get_env_int("REDIS_DB", 0)
    return f"redis://{host}:{port}/{db}"


def resolve_api_host_and_port() -> tuple[str, int]:
    """Resolve the FastAPI bind host and port from `.env`."""
    host = get_env("ORCIA_API_HOST", "127.0.0.1")
    port = get_env_int("ORCIA_API_PORT", 8000)
    return host, port


def resolve_web_host_and_port() -> tuple[str, int]:
    """Resolve the Next.js Web UI bind host and port from `.env`."""
    host = get_env("ORCIA_WEB_HOST", "127.0.0.1")
    port = get_env_int("ORCIA_WEB_PORT", 3100)
    return host, port
