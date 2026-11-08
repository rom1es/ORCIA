"""Tests for `infra/scripts/e2e/e2e_stack_config.py` (TEST-01 — isolated E2E stack)."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import Any

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "infra" / "scripts" / "e2e" / "e2e_stack_config.py"


def _load() -> Any:
    spec = importlib.util.spec_from_file_location("e2e_stack_config", MODULE_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _url(host: str, port: int, db: str) -> str:
    return f"postgresql+asyncpg://orcia:{'pw'}@{host}:{port}/{db}"


PG_URL = _url("127.0.0.1", 49321, "orcia_e2e")


def test_isolated_url_accepts_only_e2e_database_on_non_dev_port() -> None:
    mod = _load()
    assert mod.is_isolated_e2e_database_url(PG_URL)


@pytest.mark.parametrize(
    "url",
    [
        _url("127.0.0.1", 5433, "orcia"),  # base de dev
        _url("127.0.0.1", 5433, "orcia_e2e"),  # port de dev
        _url("127.0.0.1", 49321, "orcia"),  # mauvais nom de base
        _url("db.prod.internal", 49321, "orcia_e2e"),  # hôte distant
        "",
    ],
)
def test_isolated_url_rejects_dev_remote_or_unnamed_databases(url: str) -> None:
    assert not _load().is_isolated_e2e_database_url(url)


def test_build_api_env_isolates_from_dev_dotenv_and_forces_cassette() -> None:
    mod = _load()
    env = mod.build_api_env(
        base_env={
            "PATH": "/usr/bin",
            "DATABASE_URL": "postgresql+asyncpg://dev@127.0.0.1:5433/orcia",
        },
        database_url=PG_URL,
        redis_url="redis://127.0.0.1:49322/0",
        api_port=8100,
    )
    assert env["DATABASE_URL"] == PG_URL
    assert env["REDIS_URL"] == "redis://127.0.0.1:49322/0"
    assert env["ORCIA_USE_CASSETTE_LLM"] == "true"
    assert env["ORCIA_API_PORT"] == "8100"
    assert env["PATH"] == "/usr/bin"
    # `.env` de développement jamais lu : fichier inexistant
    assert not Path(env["ORCIA_ENV_FILE"]).exists()
    # secrets non faibles (sinon le démarrage les remplace / refuse)
    assert env["ORCIA_JWT_SIGNING_SECRET"] not in mod.WEAK_E2E_SECRETS
    assert env["ORCIA_PASSTHROUGH_MASTER_KEY"] not in mod.WEAK_E2E_SECRETS


def test_build_api_env_refuses_non_isolated_database() -> None:
    mod = _load()
    with pytest.raises(ValueError, match="isol"):
        mod.build_api_env(
            base_env={},
            database_url=_url("127.0.0.1", 5433, "orcia"),
            redis_url="redis://127.0.0.1:6380/0",
            api_port=8100,
        )


def test_state_roundtrip(tmp_path: Path) -> None:
    mod = _load()
    state_file = tmp_path / "state.json"
    mod.write_state(
        state_file, database_url=PG_URL, redis_url="redis://127.0.0.1:1/0", api_port=8100
    )
    state = mod.read_state(state_file)
    assert state["database_url"] == PG_URL
    assert state["api_port"] == 8100


def test_read_state_missing_file_is_explicit(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError, match="e2e_stack"):
        _load().read_state(tmp_path / "absent.json")
