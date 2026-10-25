#!/usr/bin/env python3
"""
scripts/generate_db_docs.py
===========================
Generates Markdown schema documentation and Mermaid ER diagrams
for ORCIA using tbls (adapted from StoreMirror). Reads active database
credentials from environment / .env (defaults to local ORCIA docker-compose PostgreSQL 18).
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from urllib.parse import quote_plus

BASE_DIR = Path(__file__).resolve().parent.parent


def find_tbls_binary() -> str:
    """Locate tbls binary in .venv or system PATH."""
    candidates = [
        str(BASE_DIR / ".venv" / "bin" / "tbls"),
        os.path.expanduser("~/.local/bin/tbls"),
        "/usr/local/bin/tbls",
        "/home/romain/Documents/Projects/SCRAPING/StoreMirror/venv/bin/tbls",
        "tbls",
    ]
    for candidate in candidates:
        if os.path.isfile(candidate) and os.access(candidate, os.X_OK):
            return candidate
    return "tbls"


def get_db_settings() -> dict[str, str]:
    """Read local .env database settings by default to keep Git documentation stable."""
    from dotenv import dotenv_values

    env_path = BASE_DIR / ".env"
    cfg = dotenv_values(env_path) if env_path.exists() else {}
    return {
        "user": str(
            cfg.get("ORCIA_DB_USER")
            or cfg.get("POSTGRES_USER")
            or os.environ.get("ORCIA_DB_USER")
            or os.environ.get("POSTGRES_USER", "orcia")
        ),
        "password": str(
            cfg.get("ORCIA_DB_PASSWORD")
            or cfg.get("POSTGRES_PASSWORD")
            or os.environ.get("ORCIA_DB_PASSWORD")
            or os.environ.get("POSTGRES_PASSWORD", "orcia_dev_secret")
        ),
        "host": str(
            cfg.get("ORCIA_DB_HOST")
            or cfg.get("POSTGRES_HOST")
            or os.environ.get("ORCIA_DB_HOST")
            or os.environ.get("POSTGRES_HOST", "127.0.0.1")
        ),
        "port": str(
            cfg.get("ORCIA_DB_PORT")
            or cfg.get("POSTGRES_PORT")
            or os.environ.get("ORCIA_DB_PORT")
            or os.environ.get("POSTGRES_PORT", "5433")
        ),
        "database": str(
            cfg.get("ORCIA_DB_NAME")
            or cfg.get("POSTGRES_DB")
            or os.environ.get("ORCIA_DB_NAME")
            or os.environ.get("POSTGRES_DB", "orcia")
        ),
    }


def generate_docs() -> int:
    tbls_bin = find_tbls_binary()
    db_cfg = get_db_settings()
    user = db_cfg["user"]
    password = quote_plus(db_cfg["password"])
    host = db_cfg["host"]
    port = db_cfg["port"]
    dbname = db_cfg["database"]

    dsn = f"pg://{user}:{password}@{host}:{port}/{dbname}?search_path=public&sslmode=disable"
    output_dir = BASE_DIR / "docs" / "schema"
    output_dir.mkdir(parents=True, exist_ok=True)

    cmd = [
        tbls_bin,
        "doc",
        dsn,
        str(output_dir),
        "-t",
        "mermaid",
        "-f",
        "--sort",
    ]

    print(
        f"Generating schema documentation for '{dbname}.public' on {host}:{port} "
        "(deterministic sort)..."
    )
    result = subprocess.run(cmd, capture_output=True, text=True, check=False)

    if result.returncode == 0:
        print(f"✅ Schema documentation successfully generated in {output_dir}")
        return 0

    err_msg = (result.stderr or result.stdout or "").strip()
    print(f"⚠️ tbls: could not update schema docs ({err_msg})")
    return result.returncode


if __name__ == "__main__":
    sys.exit(generate_docs())
