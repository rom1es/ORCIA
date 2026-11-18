"""Requête SQL lecture seule stricte sur la base E2E isolée `orcia_e2e` (Story 21.4).

Usage : `.venv/bin/python infra/scripts/e2e/query_db.py --sql "SELECT ..." [--params '{"k": "v"}']`
Refuse toute exécution hors base E2E isolée et toute requête non strictement lecture seule.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import re
import sys
from datetime import date, datetime, time
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

from e2e_stack_config import STATE_FILE, is_isolated_e2e_database_url, read_state  # noqa: E402
from sqlalchemy import text  # noqa: E402
from sqlalchemy.ext.asyncio import create_async_engine  # noqa: E402

_DML = {"INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE", "CREATE"}
_DDL_SYS = {"GRANT", "REVOKE", "COPY", "VACUUM", "CALL", "DO", "LOCK"}
FORBIDDEN_SQL_KEYWORDS: frozenset[str] = frozenset(_DML | _DDL_SYS)
_DOLLAR_TAG_RE = re.compile(r"\$([A-Za-z_][A-Za-z0-9_]*)?\$")
_WORD_RE = re.compile(r"[A-Za-z_][A-Za-z0-9_]*")
_LEADING_READONLY_RE = re.compile(r"^(SELECT|WITH)\b", re.IGNORECASE)


def _scan_quoted(sql: str, start: int, quote_char: str, *, allow_backslash: bool) -> int:
    idx, length = start + 1, len(sql)
    while idx < length:
        ch = sql[idx]
        if allow_backslash and ch == "\\":
            idx += 2
            continue
        if ch == quote_char:
            if idx + 1 < length and sql[idx + 1] == quote_char:
                idx += 2
                continue
            return idx + 1
        idx += 1
    raise ValueError("Littéral ou identifiant SQL non fermé.")


def _scan_block_comment(sql: str, start: int) -> int:
    idx, depth, length = start + 2, 1, len(sql)
    while idx < length and depth > 0:
        pair = sql[idx : idx + 2]
        if pair in ("/*", "*/"):
            depth += 1 if pair == "/*" else -1
            idx += 2
        else:
            idx += 1
    if depth != 0:
        raise ValueError("Commentaire SQL /* ... */ non fermé.")
    return idx


def validate_readonly_sql(sql: str) -> str:
    """Valide qu'une requête SQL est strictement lecture seule (SELECT / WITH unique)."""
    if not isinstance(sql, str) or not sql.strip():
        raise ValueError("Requête SQL vide interdite.")

    cleaned_parts, bare_parts = [], []
    started, idx, length = False, 0, len(sql)
    while idx < length:
        ch = sql[idx]
        if ch.isspace():
            if started:
                cleaned_parts.append(ch)
                bare_parts.append(" ")
            idx += 1
        elif sql.startswith(("--", "/*"), idx):
            if sql.startswith("--", idx):
                nl = sql.find("\n", idx + 2)
                idx = length if nl == -1 else nl + 1
            else:
                idx = _scan_block_comment(sql, idx)
            if started:
                cleaned_parts.append(" ")
                bare_parts.append(" ")
        elif ch in ("'", '"'):
            esc = (
                ch == "'"
                and idx > 0
                and sql[idx - 1] in ("E", "e")
                and (idx == 1 or not (sql[idx - 2].isalnum() or sql[idx - 2] == "_"))
            )
            end = _scan_quoted(sql, idx, ch, allow_backslash=esc)
            started = True
            cleaned_parts.append(sql[idx:end])
            bare_parts.append(" _LITERAL_ " if ch == "'" else " _IDENT_ ")
            idx = end
        elif ch == "$" and (tag_m := _DOLLAR_TAG_RE.match(sql, idx)) is not None:
            tag = tag_m.group(0)
            close_pos = sql.find(tag, idx + len(tag))
            if close_pos == -1:
                raise ValueError("Chaîne SQL dollar-quoted non fermée.")
            end = close_pos + len(tag)
            started = True
            cleaned_parts.append(sql[idx:end])
            bare_parts.append(" _LITERAL_ ")
            idx = end
        else:
            started = True
            cleaned_parts.append(ch)
            bare_parts.append(ch)
            idx += 1

    bare = "".join(bare_parts).strip()
    if not bare:
        raise ValueError("Requête SQL vide après suppression des commentaires.")
    if ";" in bare:
        if bare.count(";") > 1 or not bare.endswith(";"):
            raise ValueError("Requêtes SQL multiples interdites (';' hors fin de requête).")
        bare = bare[:-1].rstrip()
    if not _LEADING_READONLY_RE.match(bare):
        raise ValueError("Seules les requêtes commençant par SELECT ou WITH sont autorisées.")
    forbidden = sorted({t.upper() for t in _WORD_RE.findall(bare)} & FORBIDDEN_SQL_KEYWORDS)
    if forbidden:
        raise ValueError(f"Mot-clé SQL interdit en lecture seule : {', '.join(forbidden)}.")

    cleaned = "".join(cleaned_parts).strip()
    return cleaned[:-1].rstrip() if cleaned.endswith(";") else cleaned


def _json_default(value: object) -> object:
    return value.isoformat() if isinstance(value, (datetime, date, time)) else str(value)


async def execute_readonly_query(
    database_url: str, sql: str, params: dict[str, Any] | None = None
) -> list[dict[str, Any]]:
    """Exécute une requête SELECT/WITH validée dans une transaction READ ONLY sur orcia_e2e."""
    if not is_isolated_e2e_database_url(database_url):
        raise ValueError("REFUS : base de données cible non isolée (orcia_e2e requis).")
    cleaned_sql = validate_readonly_sql(sql)
    engine = create_async_engine(database_url, pool_pre_ping=False)
    try:
        async with engine.connect() as conn, conn.begin():
            await conn.execute(text("SET TRANSACTION READ ONLY"))
            result = await conn.execute(text(cleaned_sql), dict(params or {}))
            return [dict(row) for row in result.mappings().all()]
    finally:
        await engine.dispose()


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Exécuteur SQL lecture seule E2E (orcia_e2e).")
    parser.add_argument("--sql", required=True, help="Requête SELECT ou WITH à exécuter.")
    parser.add_argument("--params", default="{}", help="Paramètres nommés au format JSON dict.")
    parser.add_argument("--state-file", type=Path, default=STATE_FILE)
    args = parser.parse_args(argv)
    try:
        raw_params = json.loads(args.params)
        if not isinstance(raw_params, dict):
            raise ValueError("--params doit être un objet JSON.")
        state = read_state(args.state_file)
        rows = asyncio.run(
            execute_readonly_query(str(state.get("database_url", "")), args.sql, raw_params)
        )
    except ValueError as exc:
        print(f"[e2e-query-db] REFUS : {exc}", file=sys.stderr)
        return 2
    except Exception as exc:  # noqa: BLE001 — erreur CLI remontée proprement à Playwright
        print(f"[e2e-query-db] ERREUR : {exc}", file=sys.stderr)
        return 1

    print(json.dumps({"rows": rows, "row_count": len(rows)}, default=_json_default))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
