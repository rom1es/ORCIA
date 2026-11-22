"""Audit test for Assistant, Search, RAG & Datasource guards (`Story 19.7`, `Story 25.5`, `AD-24`).

Verifies the Epic 25 amendment to AD-24:
- Pure vector RAG routes (`/api/v1/ontology-rag/rag/search` and
  `/api/v1/ontology-rag/rag/index-db-ddl`) MUST enforce `require_rag_available`
  (or `get_embedding_port`).
- Assistant routes (`/api/v1/assistant/chat`, `/chat/stream`, `/three-speed/turn`,
  `/three-speed/stream`, `/threads/{thread_id}/turns`) and federated search (`GET /api/v1/search`)
  MUST inject `get_optional_embedding_port` and MUST NOT inject `require_rag_available`.
- AST audit verifies `workspace_datasources.py` delegates datasource mutations to
  `sql_workspace_datasources_mutations.py`, which enforces
  `assert_active_global_embedding_model_for_rag_source` for `source_nature != 'SOURCE_CODE'`.
"""

from __future__ import annotations

import ast
from pathlib import Path
from typing import Any

from fastapi.routing import APIRoute

from orcia_api.dependencies import (
    get_embedding_port,
    get_optional_embedding_port,
    require_rag_available,
)
from orcia_api.main import create_app

REPO_ROOT = Path(__file__).resolve().parents[2]

STRICT_RAG_PROTECTED_ROUTES: frozenset[tuple[str, str]] = frozenset(
    {
        ("POST", "/api/v1/ontology-rag/rag/search"),
        ("POST", "/api/v1/ontology-rag/rag/index-db-ddl"),
    }
)

OPTIONAL_EMBEDDING_ROUTES: frozenset[tuple[str, str]] = frozenset(
    {
        ("GET", "/api/v1/search"),
        ("POST", "/api/v1/assistant/turns"),
        ("POST", "/api/v1/assistant/threads/{thread_id}/turns"),
        ("POST", "/api/v1/mcp/spaces/{workspace_slug}/invoke"),
    }
)


def _collect_callables_from_dependant(dependant: Any) -> set[Any]:
    callables = set()
    if getattr(dependant, "call", None):
        callables.add(dependant.call)
    for sub in getattr(dependant, "dependencies", []):
        callables.update(_collect_callables_from_dependant(sub))
    return callables


def _collect_all_routes_recursive(item: Any, prefix: str = "") -> list[tuple[str, APIRoute]]:
    collected: list[tuple[str, APIRoute]] = []
    routes = getattr(item, "routes", [])
    for r in routes:
        if isinstance(r, APIRoute):
            collected.append((prefix + r.path, r))
        elif hasattr(r, "original_router"):
            sub_prefix = (
                getattr(r.include_context, "prefix", "") if hasattr(r, "include_context") else ""
            )
            collected.extend(_collect_all_routes_recursive(r.original_router, prefix + sub_prefix))
        elif hasattr(r, "routes"):
            collected.extend(_collect_all_routes_recursive(r, prefix))
    return collected


def test_assistant_and_rag_routes_require_rag_guard_audit() -> None:
    """Audit registered FastAPI routes for AD-24 Epic 25 strict vs optional embedding guards."""
    app = create_app()
    all_routes = _collect_all_routes_recursive(app)
    found_strict: set[tuple[str, str]] = set()
    found_optional: set[tuple[str, str]] = set()

    for full_path, route in all_routes:
        endpoint_callables = _collect_callables_from_dependant(route.dependant)
        has_strict_guard = (require_rag_available in endpoint_callables) or (
            get_embedding_port in endpoint_callables
        )
        has_optional_guard = get_optional_embedding_port in endpoint_callables

        for method in route.methods:
            route_key = (method.upper(), full_path)
            if route_key in STRICT_RAG_PROTECTED_ROUTES:
                assert has_strict_guard, (
                    f"Pure RAG route {route_key} missing 'require_rag_available' guard."
                )
                found_strict.add(route_key)
            elif route_key in OPTIONAL_EMBEDDING_ROUTES:
                assert not has_strict_guard, (
                    f"Route {route_key} MUST NOT use 'require_rag_available' or "
                    "'get_embedding_port' (AD-24 Epic 25 decoupling)."
                )
                assert has_optional_guard, (
                    f"Route {route_key} MUST inject 'get_optional_embedding_port'."
                )
                found_optional.add(route_key)

    missing_strict = STRICT_RAG_PROTECTED_ROUTES - found_strict
    missing_optional = OPTIONAL_EMBEDDING_ROUTES - found_optional
    assert not missing_strict, f"Strict RAG routes missing in FastAPI app: {missing_strict}"
    assert not missing_optional, (
        f"Optional embedding routes missing in FastAPI app: {missing_optional}"
    )


def _extract_called_names(node: ast.AST) -> set[str]:
    names: set[str] = set()
    for child in ast.walk(node):
        if isinstance(child, ast.Call):
            if isinstance(child.func, ast.Name):
                names.add(child.func.id)
            elif isinstance(child.func, ast.Attribute):
                names.add(child.func.attr)
    return names


def test_ast_audit_no_require_rag_available_on_assistant_or_search_and_datasource_guard() -> None:
    """AST audit on routers and SQL datasource mutations (`AD-24` Epic 25)."""
    decoupled_router_files = (
        REPO_ROOT / "apps/api/src/orcia_api/routers/assistant_turns.py",
        REPO_ROOT / "apps/api/src/orcia_api/routers/assistant_workspace_folders.py",
        REPO_ROOT / "apps/api/src/orcia_api/routers/mcp_and_test_bench.py",
        REPO_ROOT / "apps/api/src/orcia_api/routers/portal_and_help.py",
    )
    for path in decoupled_router_files:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        referenced_names = {node.id for node in ast.walk(tree) if isinstance(node, ast.Name)} | {
            node.attr for node in ast.walk(tree) if isinstance(node, ast.Attribute)
        }
        assert "require_rag_available" not in referenced_names, (
            f"{path} must not reference require_rag_available"
        )
        assert "get_optional_embedding_port" in referenced_names, (
            f"{path} must reference get_optional_embedding_port"
        )

    ws_router_tree = ast.parse(
        (REPO_ROOT / "apps/api/src/orcia_api/routers/workspace_datasources.py").read_text(
            encoding="utf-8"
        )
    )
    ws_router_calls = _extract_called_names(ws_router_tree)
    assert "create_workspace_datasource_on_postgres18" in ws_router_calls
    assert "update_workspace_datasource_on_postgres18" in ws_router_calls

    mutations_path = (
        REPO_ROOT
        / "packages/orcia-core/src/orcia_core/bootstrap/_internal"
        / "sql_workspace_datasources_mutations.py"
    )
    mutations_tree = ast.parse(mutations_path.read_text(encoding="utf-8"))
    fns = {
        node.name: node
        for node in mutations_tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    assert "assert_active_global_embedding_model_for_rag_source" in _extract_called_names(
        fns["create_workspace_datasource_on_postgres18"]
    )
    assert "assert_active_global_embedding_model_for_rag_source" in _extract_called_names(
        fns["update_workspace_datasource_on_postgres18"]
    )

    sync_path = (
        REPO_ROOT
        / "packages/orcia-core/src/orcia_core/bootstrap/_internal"
        / "_sql_workspace_datasources_sync.py"
    )
    sync_src = sync_path.read_text(encoding="utf-8")
    sync_tree = ast.parse(sync_src)
    sync_fns = {
        node.name: node
        for node in sync_tree.body
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef))
    }
    guard_fn = sync_fns["assert_active_global_embedding_model_for_rag_source"]
    assert "source_nature == 'SOURCE_CODE'" in ast.unparse(guard_fn)
    assert "NoActiveEmbeddingModelError" in _extract_called_names(guard_fn)
