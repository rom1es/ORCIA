"""Unit tests for the read-only PostgreSQL E2E query helper (`infra/scripts/e2e/query_db.py`)."""

from __future__ import annotations

import asyncio
import importlib.util
import json
import sys
from contextlib import asynccontextmanager
from datetime import UTC, date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any
from uuid import UUID

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
E2E_SCRIPTS_DIR = REPO_ROOT / "infra" / "scripts" / "e2e"
QUERY_DB_PATH = E2E_SCRIPTS_DIR / "query_db.py"


def _pg_url(host: str, port: int, db: str) -> str:
    return f"postgresql+asyncpg://orcia:{'pw'}@{host}:{port}/{db}"


E2E_PG_URL = _pg_url("127.0.0.1", 49321, "orcia_e2e")


def _load_query_db() -> Any:
    if str(E2E_SCRIPTS_DIR) not in sys.path:
        sys.path.insert(0, str(E2E_SCRIPTS_DIR))
    spec = importlib.util.spec_from_file_location("e2e_query_db", QUERY_DB_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


@pytest.mark.parametrize(
    ("raw_sql", "expected_fragment"),
    [
        ("SELECT id, email FROM users WHERE email = :email", "SELECT id, email FROM users"),
        ("  select count(*) as count from org_units;  ", "select count(*) as count from org_units"),
        ("WITH recent AS (SELECT id FROM users) SELECT * FROM recent", "WITH recent AS"),
        ("-- header\n/* outer /* inner */ */\nSELECT 1 AS ok", "SELECT 1 AS ok"),
        (
            "SELECT 'DELETE FROM users' AS lit, E'UPDATE \\'x\\'' AS esc, $q$DROP TABLE y$q$ AS dq",
            "SELECT 'DELETE FROM users'",
        ),
        ('SELECT "UPDATE" FROM "DELETE" WHERE id = :id', 'SELECT "UPDATE" FROM "DELETE"'),
    ],
)
def test_validate_readonly_sql_accepts_safe_select_and_cte_queries(
    raw_sql: str, expected_fragment: str
) -> None:
    cleaned = _load_query_db().validate_readonly_sql(raw_sql)
    assert expected_fragment in cleaned
    assert not cleaned.endswith(";")


_FORBIDDEN = (
    "INSERT",
    "UPDATE",
    "DELETE",
    "DROP",
    "ALTER",
    "TRUNCATE",
    "CREATE",
    "GRANT",
    "REVOKE",
    "COPY",
    "VACUUM",
    "CALL",
    "DO",
    "LOCK",
)


@pytest.mark.parametrize("forbidden_keyword", _FORBIDDEN)
def test_validate_readonly_sql_rejects_mutating_and_admin_keywords(forbidden_keyword: str) -> None:
    mod = _load_query_db()
    with pytest.raises(ValueError):
        mod.validate_readonly_sql(f"{forbidden_keyword} TABLE users")
    with pytest.raises(ValueError):
        mod.validate_readonly_sql(f"WITH x AS ({forbidden_keyword} FROM users) SELECT * FROM x")


_BAD_SQL = (
    "",
    "   \n\t  ",
    "-- comment only",
    "/* only block comment */",
    "SELECT 1; SELECT 2",
    "SELECT 1; DROP TABLE users;",
    "SELECT 1;;",
    "EXPLAIN ANALYZE SELECT 1",
    "SHOW server_version",
    "SELECT 'unterminated",
    "/* unclosed comment",
    "SELECT $tag$unclosed",
)


@pytest.mark.parametrize("bad_sql", _BAD_SQL)
def test_validate_readonly_sql_rejects_empty_multi_statement_and_malformed_sql(
    bad_sql: str,
) -> None:
    with pytest.raises(ValueError):
        _load_query_db().validate_readonly_sql(bad_sql)


@pytest.mark.parametrize(
    "unsafe_url",
    [
        _pg_url("127.0.0.1", 5432, "orcia_e2e"),
        _pg_url("127.0.0.1", 5433, "orcia_e2e"),
        _pg_url("127.0.0.1", 5433, "orcia"),
        _pg_url("127.0.0.1", 49321, "orcia"),
        _pg_url("db.prod.internal", 49321, "orcia_e2e"),
        "",
    ],
)
def test_readonly_execution_and_cli_reject_non_isolated_database_urls(
    unsafe_url: str, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    mod = _load_query_db()
    assert not mod.is_isolated_e2e_database_url(unsafe_url)
    with pytest.raises(ValueError, match="orcia_e2e"):
        asyncio.run(mod.execute_readonly_query(unsafe_url, "SELECT 1"))

    state_file = tmp_path / "e2e-state.json"
    state_file.write_text(json.dumps({"database_url": unsafe_url}), encoding="utf-8")
    assert mod.main(["--sql", "SELECT 1", "--state-file", str(state_file)]) == 2
    assert "REFUS" in capsys.readouterr().err


def test_json_default_serializes_uuid_datetime_and_decimal() -> None:
    mod = _load_query_db()
    payload = {
        "id": UUID("0195f000-0000-7000-8000-000000000301"),
        "created_at": datetime(2026, 11, 18, 8, 30, 0, tzinfo=UTC),
        "day": date(2026, 11, 18),
        "budget": Decimal("250.125000"),
    }
    serialized = json.loads(json.dumps(payload, default=mod._json_default))
    assert serialized == {
        "id": "0195f000-0000-7000-8000-000000000301",
        "created_at": "2026-11-18T08:30:00+00:00",
        "day": "2026-11-18",
        "budget": "250.125000",
    }


def test_execute_readonly_query_sets_transaction_read_only_and_disposes_engine(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mod = _load_query_db()
    recorded: list[tuple[str, dict[str, Any] | None]] = []
    state = {"disposed": False}

    class _ReadonlyQuerySpyConn:
        @asynccontextmanager
        async def begin(self) -> Any:
            yield self

        async def execute(self, clause: Any, params: dict[str, Any] | None = None) -> Any:
            recorded.append((str(clause), params))
            row = {"id": UUID("0195f000-0000-7000-8000-000000000301"), "slug": "bu-e2e"}
            return type(
                "R", (), {"mappings": lambda _s: type("M", (), {"all": lambda _m: [row]})()}
            )()

    class _ReadonlyQuerySpyHandle:
        @asynccontextmanager
        async def connect(self) -> Any:
            yield _ReadonlyQuerySpyConn()

        async def dispose(self) -> None:
            state["disposed"] = True

    monkeypatch.setattr(mod, "create_async_engine", lambda url, **kwargs: _ReadonlyQuerySpyHandle())
    rows = asyncio.run(
        mod.execute_readonly_query(
            E2E_PG_URL,
            "SELECT id, slug FROM org_units WHERE slug = :slug;",
            {"slug": "bu-e2e"},
        )
    )
    assert rows[0]["slug"] == "bu-e2e"
    assert recorded[0][0] == "SET TRANSACTION READ ONLY"
    assert recorded[1] == ("SELECT id, slug FROM org_units WHERE slug = :slug", {"slug": "bu-e2e"})
    assert state["disposed"] is True


def test_cli_outputs_serialized_rows_and_handles_invalid_params(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    mod = _load_query_db()
    state_file = tmp_path / "e2e-state.json"
    state_file.write_text(json.dumps({"database_url": E2E_PG_URL}), encoding="utf-8")

    async def _fake_exec(url: str, sql: str, params: dict[str, Any]) -> list[dict[str, Any]]:
        return [{"id": UUID("0195f000-0000-7000-8000-000000000301"), "amount": Decimal("42.50")}]

    monkeypatch.setattr(mod, "execute_readonly_query", _fake_exec)
    exit_ok = mod.main(
        ["--sql", "SELECT id, amount FROM finops_scope_budgets", "--state-file", str(state_file)]
    )
    assert exit_ok == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["row_count"] == 1
    assert payload["rows"][0]["amount"] == "42.50"
    assert mod.main(["--sql", "SELECT 1", "--params", "[]", "--state-file", str(state_file)]) == 2
