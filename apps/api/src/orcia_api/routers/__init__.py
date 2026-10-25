"""Routers for ORCIA API v1."""

from orcia_api.routers.health import router as health_router
from orcia_api.routers.shell import router as shell_router

__all__ = ["health_router", "shell_router"]
