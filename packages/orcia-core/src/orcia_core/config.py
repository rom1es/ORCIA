"""Centralized environment & `.env` configuration loader for ORCIA (`packages/orcia-core`).

Ensures all components (`apps/api`, `apps/worker`, `infra/migrations`,
`infra/scripts/maintenance/*`, `scripts/*`, and `packages/orcia-core`) resolve their host, port,
path, and credential settings from the root `.env` file while preserving explicit process
environment overrides (`override=False`) and supporting `<VAR>_FILE` secret files (Docker / K8s
`/run/secrets/*`).
"""

from __future__ import annotations

import os
import re
import secrets
from collections.abc import Callable
from pathlib import Path
from urllib.parse import quote_plus

_dotenv_load: Callable[..., bool] | None
try:
    from dotenv import load_dotenv as _dotenv_load
except ModuleNotFoundError:  # pragma: no cover
    _dotenv_load = None

REPO_ROOT: Path = Path(__file__).resolve().parents[4]
DEFAULT_ENV_FILE: Path = REPO_ROOT / ".env"

WEAK_PLACEHOLDER_SECRETS: frozenset[str] = frozenset(
    {
        "",
        "change-me",
        "change-me-jwt-signing-secret",
        "change-me-aes256gcm-master-key",
        "orcia-story-1-2-jwt-signing-secret-key-2026",
        "orcia-story-1-2-aes256gcm-master-key-2026",
    }
)

ROTATABLE_SECRET_KEYS: tuple[str, ...] = (
    "ORCIA_JWT_SIGNING_SECRET",
    "ORCIA_PASSTHROUGH_MASTER_KEY",
)

_ENV_LOADED = False


def _fallback_load_dotenv(*, dotenv_path: Path, override: bool = False) -> bool:
    """Minimal stdlib `.env` parser fallback when `python-dotenv` is unavailable."""
    for raw_line in dotenv_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        if line.startswith("export "):
            line = line[7:].strip()
        if "=" not in line:
            continue
        key, val = line.split("=", 1)
        key = key.strip()
        val = val.strip()
        if len(val) >= 2 and val[0] == val[-1] and val[0] in ("'", '"'):
            val = val[1:-1]
        if key and (override or key not in os.environ):
            os.environ[key] = val
    return True


def load_orcia_env(*, env_file: Path | None = None, override: bool = False) -> Path:
    """Load the root `.env` file into `os.environ` without clobbering explicit env vars."""
    global _ENV_LOADED
    target = env_file or Path(os.environ.get("ORCIA_ENV_FILE", str(DEFAULT_ENV_FILE)))
    if target.is_file():
        if _dotenv_load is not None:
            _dotenv_load(dotenv_path=target, override=override)
        else:
            _fallback_load_dotenv(dotenv_path=target, override=override)
    _ENV_LOADED = True
    return target


def get_env(key: str, default: str = "") -> str:
    """Return environment variable value, supporting `<KEY>_FILE` secret files first."""
    if not _ENV_LOADED:
        load_orcia_env()
    file_var = os.environ.get(f"{key}_FILE", "").strip()
    if file_var:
        secret_path = Path(file_var)
        if not secret_path.is_file():
            raise ValueError(f"Secret file configured in {key}_FILE does not exist: {file_var}")
        try:
            return secret_path.read_text(encoding="utf-8").strip()
        except OSError as exc:
            msg = f"Secret file configured in {key}_FILE is unreadable: {file_var}"
            raise ValueError(msg) from exc
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


def generate_strong_secret(nbytes: int = 32) -> str:
    """Generate a URL-safe cryptographic secret (`>= 256 bits` by default)."""
    if nbytes < 16:
        raise ValueError("nbytes must be >= 16 (128 bits minimum)")
    return secrets.token_urlsafe(nbytes)


def _write_secure_file(target: Path, text: str) -> None:
    flags = os.O_WRONLY | os.O_CREAT | os.O_TRUNC
    fd = os.open(target, flags, 0o600)
    try:
        os.write(fd, text.encode("utf-8"))
    finally:
        os.close(fd)
    with context_suppress_chmod(target):
        target.chmod(0o600)


def init_or_rotate_env_secrets(
    *,
    env_file: Path | None = None,
    template_file: Path | None = None,
    force_rotate: bool = False,
) -> dict[str, bool]:
    """Ensure `.env` exists and replace weak/placeholder application secrets with 256-bit keys.

    Returns a mapping `{secret_key: was_updated}`.
    """
    target_env = env_file or DEFAULT_ENV_FILE
    source_tpl = template_file or (REPO_ROOT / ".env.example")
    if not target_env.is_file() and source_tpl.is_file():
        _write_secure_file(target_env, source_tpl.read_text(encoding="utf-8"))

    content = target_env.read_text(encoding="utf-8") if target_env.is_file() else ""
    updated: dict[str, bool] = {}

    for key in ROTATABLE_SECRET_KEYS:
        pattern = re.compile(rf"^(?P<prefix>{re.escape(key)}=)(?P<val>.*)$", re.MULTILINE)
        match = pattern.search(content)
        new_secret = generate_strong_secret(32)
        if match is None:
            sep = "" if (not content or content.endswith("\n")) else "\n"
            content = f"{content}{sep}{key}={new_secret}\n"
            updated[key] = True
        else:
            current_val = match.group("val").strip().strip("\"'")
            if force_rotate or current_val in WEAK_PLACEHOLDER_SECRETS:
                content = pattern.sub(rf"\g<prefix>{new_secret}", content, count=1)
                updated[key] = True
            else:
                updated[key] = False

    _write_secure_file(target_env, content)
    load_orcia_env(env_file=target_env, override=True)
    return updated


class context_suppress_chmod:
    """Context manager ignoring OSError when setting file permissions on restricted FS."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def __enter__(self) -> Path:
        return self._path

    def __exit__(self, exc_type: object, exc: object, tb: object) -> bool:
        return isinstance(exc, OSError)
