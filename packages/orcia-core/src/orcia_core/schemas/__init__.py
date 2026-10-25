"""Pydantic v2 contracts (single source of truth for OpenAPI 3.1 schema generation, AD-1)."""

from orcia_core.schemas.problem_details import ProblemDetails
from orcia_core.schemas.shell import (
    AccessMode,
    HealthResponse,
    HumanProfileBadge,
    ModuleKey,
    ScopeLevel,
    ScopeNode,
    ShellModuleItem,
    ShellNavigationResponse,
)

__all__ = [
    "AccessMode",
    "HealthResponse",
    "HumanProfileBadge",
    "ModuleKey",
    "ProblemDetails",
    "ScopeLevel",
    "ScopeNode",
    "ShellModuleItem",
    "ShellNavigationResponse",
]
