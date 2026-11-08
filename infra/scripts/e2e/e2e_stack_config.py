"""Logique pure de la pile E2E isolée (TEST-01) : environnement, garde-fou, état.

Garde-fou central : `09_reset_db_first_boot.py --apply` vide la base résolue par l'environnement.
Aucun reset ni démarrage d'API E2E ne doit donc jamais cibler la base de développement.
"""

from __future__ import annotations

import json
import os
import re
from collections.abc import Mapping
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

REPO_ROOT = Path(__file__).resolve().parents[3]
STATE_FILE = REPO_ROOT / ".orcia-run" / "e2e-stack-state.json"
E2E_DB_NAME = "orcia_e2e"
DEV_POSTGRES_PORTS = frozenset({5432, 5433})
LOCAL_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})
NO_ENV_FILE = REPO_ROOT / ".orcia-run" / "does-not-exist.env"

# Secrets fixes de test (jamais utilisés hors pile éphémère) — non faibles au sens de `config.py`.
E2E_JWT_SECRET = "orcia-e2e-jwt-signing-secret-ephemeral-0001"  # pragma: allowlist secret
E2E_VAULT_KEY = "orcia-e2e-aes256gcm-master-key-ephemeral-0001"  # pragma: allowlist secret
WEAK_E2E_SECRETS = frozenset({"", "change-me", "change-me-jwt-signing-secret"})


def is_isolated_e2e_database_url(url: str) -> bool:
    """Vrai uniquement pour une base locale nommée `orcia_e2e` hors ports de développement."""
    if not url:
        return False
    parsed = urlparse(re.sub(r"^postgresql\+\w+://", "postgresql://", url))
    db_name = parsed.path.lstrip("/").split("?")[0]
    return (
        db_name == E2E_DB_NAME
        and parsed.hostname in LOCAL_HOSTS
        and parsed.port is not None
        and parsed.port not in DEV_POSTGRES_PORTS
    )


def build_api_env(
    *,
    base_env: Mapping[str, str],
    database_url: str,
    redis_url: str,
    api_port: int,
) -> dict[str, str]:
    """Environnement du processus FastAPI E2E : jamais le `.env` de dev, cassette LLM forcée."""
    if not is_isolated_e2e_database_url(database_url):
        raise ValueError("Base de données non isolée : refus de démarrer la pile E2E.")
    env = dict(base_env)
    env.update(
        {
            "DATABASE_URL": database_url,
            "REDIS_URL": redis_url,
            "ORCIA_ENV_FILE": str(NO_ENV_FILE),
            "ORCIA_USE_CASSETTE_LLM": "true",
            "ORCIA_API_HOST": "127.0.0.1",
            "ORCIA_API_PORT": str(api_port),
            "ORCIA_JWT_SIGNING_SECRET": E2E_JWT_SECRET,
            "ORCIA_PASSTHROUGH_MASTER_KEY": E2E_VAULT_KEY,
            "ORCIA_WORKER_STUB_BROKER": "1",
        }
    )
    return env


def write_state(path: Path, *, database_url: str, redis_url: str, api_port: int) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"database_url": database_url, "redis_url": redis_url, "api_port": api_port}
    path.write_text(json.dumps(payload), encoding="utf-8")


def read_state(path: Path = STATE_FILE) -> dict[str, Any]:
    if not path.is_file():
        raise FileNotFoundError(
            f"État de la pile E2E absent ({path}) : lancer e2e_stack.py d'abord."
        )
    state: dict[str, Any] = json.loads(path.read_text(encoding="utf-8"))
    return state


def process_env() -> Mapping[str, str]:
    return os.environ
