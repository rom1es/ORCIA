"""ORCIA FastAPI Application (`apps/api`)."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from orcia_api.main import (
        app as app,
    )
    from orcia_api.main import (
        create_app as create_app,
    )


def __getattr__(name: str) -> Any:
    if name in ("app", "create_app"):
        import orcia_api.main as main_mod

        value = getattr(main_mod, name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["app", "create_app"]
