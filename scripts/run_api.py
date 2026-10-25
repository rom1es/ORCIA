#!/usr/bin/env python3
"""Start the ORCIA FastAPI development server using host/port settings from root `.env`."""

from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
for rel_src in ("packages/orcia-core/src", "apps/api/src", "apps/worker/src"):
    candidate = str(REPO_ROOT / rel_src)
    if candidate not in sys.path:
        sys.path.insert(0, candidate)

import uvicorn  # noqa: E402

from orcia_core.config import load_orcia_env, resolve_api_host_and_port  # noqa: E402


def main() -> None:
    """Launch uvicorn with `ORCIA_API_HOST` and `ORCIA_API_PORT` from `.env`."""
    load_orcia_env()
    host, port = resolve_api_host_and_port()
    uvicorn.run("orcia_api.main:app", host=host, port=port, reload=True)


if __name__ == "__main__":  # pragma: no cover
    main()
