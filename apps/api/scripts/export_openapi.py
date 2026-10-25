"""Forwarding script to root `scripts/export_openapi.py`."""

from __future__ import annotations

import runpy
from pathlib import Path

if __name__ == "__main__":  # pragma: no cover
    target = Path(__file__).resolve().parents[3] / "scripts" / "export_openapi.py"
    runpy.run_path(str(target), run_name="__main__")
