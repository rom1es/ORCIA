"""Public bootstrap facade for scoped Workspace PATCH persistence (`AD-19`)."""

from __future__ import annotations

from orcia_core.bootstrap._internal.sql_workspace_patch import (
    WorkspacePatchResult,
    patch_workspace_on_postgres18,
)

__all__ = ["WorkspacePatchResult", "patch_workspace_on_postgres18"]
