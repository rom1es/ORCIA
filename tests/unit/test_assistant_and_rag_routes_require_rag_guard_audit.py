"""Audit test for Assistant and RAG routes FastAPI dependencies (`Story 19.7`, `AD-24.7`).

Verifies that ALL endpoints executing an Assistant conversational turn or RAG search/indexing
enforce the unified `require_rag_available` (or `get_embedding_port`) dependency.
"""

from __future__ import annotations

from typing import Any

from fastapi.routing import APIRoute

from orcia_api.dependencies import get_embedding_port, require_rag_available
from orcia_api.main import create_app

# Set of protected routes that MUST have RAG availability guard
MANDATORY_PROTECTED_ROUTES: frozenset[tuple[str, str]] = frozenset(
    {
        ("GET", "/api/v1/search"),
        ("POST", "/api/v1/assistant/chat"),
        ("POST", "/api/v1/assistant/chat/stream"),
        ("POST", "/api/v1/assistant/three-speed/turn"),
        ("POST", "/api/v1/assistant/three-speed/stream"),
        ("POST", "/api/v1/assistant/threads/{thread_id}/turns"),
        ("POST", "/api/v1/ontology-rag/rag/search"),
        ("POST", "/api/v1/ontology-rag/rag/index-db-ddl"),
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
    """Audit all registered FastAPI routes to assert require_rag_available is present."""
    app = create_app()

    all_routes = _collect_all_routes_recursive(app)
    found_protected_routes: set[tuple[str, str]] = set()

    for full_path, route in all_routes:
        endpoint_callables = _collect_callables_from_dependant(route.dependant)
        has_guard = (require_rag_available in endpoint_callables) or (
            get_embedding_port in endpoint_callables
        )

        for method in route.methods:
            route_key = (method.upper(), full_path)
            if route_key in MANDATORY_PROTECTED_ROUTES:
                assert has_guard, (
                    f"Route {route_key} is missing mandatory RAG availability guard "
                    f"('require_rag_available' or 'get_embedding_port')."
                )
                found_protected_routes.add(route_key)

    missing = MANDATORY_PROTECTED_ROUTES - found_protected_routes
    assert not missing, f"Mandatory protected routes not registered in FastAPI app: {missing}"
