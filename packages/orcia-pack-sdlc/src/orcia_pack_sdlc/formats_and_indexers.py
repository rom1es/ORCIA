"""SDLC Catalog Format (`BMAD_PACK`) & Indexer entry_points (`AD-20`, `AC-E1`)."""

from __future__ import annotations

from typing import Any

from orcia_core.catalog.bmad_adapter import BmadSkillPackAdapter
from orcia_core.rag.indexer_and_rrf import DifferentiatedIncrementalIndexer
from orcia_core.rag.tripartite_and_freshness import TripartiteGraphAndFreshnessService


def get_bmad_pack_format_adapter() -> type[BmadSkillPackAdapter]:
    """Return `BMAD_PACK` catalog format adapter registered via `orcia.catalog_formats`."""
    return BmadSkillPackAdapter


def get_git_code_ast_indexer() -> Any:
    """Return `index_git_ast_and_code_graph` registered via `orcia.indexers`."""
    return DifferentiatedIncrementalIndexer.index_git_ast_and_code_graph


def get_jira_hybrid_indexer() -> Any:
    """Return `index_jira_reference_issue` registered via `orcia.indexers`."""
    return DifferentiatedIncrementalIndexer.index_jira_reference_issue


def get_tripartite_graph_indexer() -> type[TripartiteGraphAndFreshnessService]:
    """Return `TripartiteGraphAndFreshnessService` registered via `orcia.indexers`."""
    return TripartiteGraphAndFreshnessService
