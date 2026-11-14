"""PostgreSQL 18 persistence facade for Workspace Datasources (`Story 18.1`).

Re-exports query and mutation functions with clean modularity.
"""

from __future__ import annotations

from orcia_core.bootstrap._internal.sql_workspace_datasources_mutations import (
    create_workspace_datasource_on_postgres18,
    delete_workspace_datasource_on_postgres18,
    trigger_workspace_datasource_sync_on_postgres18,
    update_workspace_datasource_on_postgres18,
)
from orcia_core.bootstrap._internal.sql_workspace_datasources_queries import (
    ensure_workspace_datasources_schema,
    get_workspace_datasource_from_postgres18,
    list_workspace_datasources_from_postgres18,
    resolve_workspace_context,
)

# Backward-compatibility alias
_resolve_workspace_context = resolve_workspace_context

__all__ = [
    "_resolve_workspace_context",
    "create_workspace_datasource_on_postgres18",
    "delete_workspace_datasource_on_postgres18",
    "ensure_workspace_datasources_schema",
    "get_workspace_datasource_from_postgres18",
    "list_workspace_datasources_from_postgres18",
    "resolve_workspace_context",
    "trigger_workspace_datasource_sync_on_postgres18",
    "update_workspace_datasource_on_postgres18",
]
