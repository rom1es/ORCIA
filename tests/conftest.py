"""Global pytest configuration defaulting `ORCIA_ENV` to `"test"` when unset."""

from __future__ import annotations

import os

os.environ.setdefault("ORCIA_ENV", "test")
