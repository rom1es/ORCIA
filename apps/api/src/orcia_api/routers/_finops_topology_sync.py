"""PG18 topology synchronization re-export for FinOps routers (`_finops_scope_guards`)."""

from __future__ import annotations

from orcia_api.dependencies._topology_sync import (
    sync_evaluator_topology_from_pg as sync_evaluator_topology_from_pg,
)

__all__ = ["sync_evaluator_topology_from_pg"]
