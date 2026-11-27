"""Story 26.10 — Epic 26 Closure Structural AST, Guard, Legacy & 0-Uncalled-Route Audits."""

from __future__ import annotations

import ast
import inspect
import re
from pathlib import Path
from typing import Any

from fastapi.routing import APIRoute
from tests.unit._epic_26_closure_ast_helpers import (
    collect_epic_26_harness_files,
    find_mutable_module_container_violations,
    find_sync_blocking_io_violations,
)
from tests.unit.fakes.test_app_helpers import get_repo_source_index

from orcia_api.main import create_app
from orcia_api.routers.auth import resolve_request_user

REPO_ROOT = Path(__file__).resolve().parents[2]
API_SRC_DIR = REPO_ROOT / "apps" / "api" / "src"
API_ROUTERS_DIR = API_SRC_DIR / "orcia_api" / "routers"
CORE_SRC_DIR = REPO_ROOT / "packages" / "orcia-core" / "src"

_LEGACY_ROUTE_FRAGMENTS = (
    "/three-speed/",
    "/assistant/chat",
    "/citations/verify-turn",
    "/artifacts/action",
    "/workflows/save-and-launch",
    "/assistant/threads/{thread_id}/turns",
)
_EXPECTED_ASSISTANT_CLIENT_CALLS: dict[tuple[str, str], str] = {
    ("POST", "/api/v1/assistant/turns"): "streamAssistantTurnSse",
    ("GET", "/api/v1/assistant/turns/{turn_id}/stream"): "streamAssistantTurnByIdSse",
    ("GET", "/api/v1/assistant/turns/active"): "listActiveAssistantTurns",
    ("POST", "/api/v1/assistant/turns/{turn_id}/stop"): "stopAssistantTurn",
    ("POST", "/api/v1/assistant/turns/{turn_id}/synthesize-now"): "synthesizeAssistantTurnNow",
    ("POST", "/api/v1/assistant/turns/{turn_id}/approve"): "approveAssistantTurnProposal",
    ("POST", "/api/v1/assistant/turns/{turn_id}/feedback"): "recordAssistantTurnFeedback",
    ("GET", "/api/v1/assistant/workspaces/{workspace_id}/overview"): "listAssistantFolders",
    ("POST", "/api/v1/assistant/folders"): "createAssistantFolder",
    ("POST", "/api/v1/assistant/folders/{folder_id}/share"): "configureAssistantFolderSharing",
    ("POST", "/api/v1/assistant/folders/{folder_id}/launch-process"): "launchProcessFromFolder",
    ("POST", "/api/v1/assistant/threads"): "createAssistantThread",
    ("GET", "/api/v1/assistant/threads/{thread_id}/messages"): "listAssistantThreadMessages",
    ("GET", "/api/v1/assistant/governance"): "getAssistantGovernance",
    ("PUT", "/api/v1/assistant/governance/mode-a/user"): "updateAssistantUserPreferences",
    ("PUT", "/api/v1/assistant/governance/mode-a/workspace"): "updateAssistantWorkspaceSettings",
}


def _collect_dependant_callables(dependant: Any) -> set[Any]:
    out = set()
    if getattr(dependant, "call", None):
        out.add(dependant.call)
    for sub in getattr(dependant, "dependencies", []):
        out.update(_collect_dependant_callables(sub))
    return out


def _collect_assistant_routes() -> list[tuple[str, APIRoute]]:
    app = create_app()
    found: list[tuple[str, APIRoute]] = []

    def _walk(item: Any, prefix: str = "") -> None:
        for r in getattr(item, "routes", []):
            if isinstance(r, APIRoute):
                full = prefix + r.path
                if full.startswith("/api/v1/assistant"):
                    found.append((full, r))
            elif hasattr(r, "original_router"):
                sub_prefix = (
                    getattr(r.include_context, "prefix", "")
                    if hasattr(r, "include_context")
                    else ""
                )
                _walk(r.original_router, prefix + sub_prefix)
            elif hasattr(r, "routes"):
                _walk(r, prefix)

    _walk(app)
    return found


def test_zero_module_level_mutable_harness_state_in_api_routers() -> None:
    """Ensure `apps/api/src/orcia_api/routers/` holds 0 module-level mutable containers/locks."""
    violations = find_mutable_module_container_violations(API_ROUTERS_DIR)
    assert violations == [], "Mutable harness globals found:\n" + "\n".join(violations)


def test_every_assistant_route_has_auth_scope_and_observer_guards() -> None:
    """Every `/api/v1/assistant/*` route MUST enforce user auth + workspace/turn guard."""
    routes = _collect_assistant_routes()
    assert len(routes) == len(_EXPECTED_ASSISTANT_CLIENT_CALLS)
    violations: list[str] = []
    for full_path, route in routes:
        deps = _collect_dependant_callables(route.dependant)
        if resolve_request_user not in deps:
            violations.append(f"{full_path} missing resolve_request_user")
        src = inspect.getsource(route.endpoint)
        has_guard = (
            "enforce_assistant_workspace_guard" in src or "require_owned_assistant_turn" in src
        )
        if not has_guard:
            violations.append(f"{full_path} missing workspace/turn guard call")
        methods = {m.upper() for m in (route.methods or set())}
        if methods & {"POST", "PUT", "PATCH", "DELETE"} and "require_write=True" not in src:
            violations.append(f"{methods} {full_path} missing `require_write=True`")
    assert violations == [], "Unguarded assistant routes:\n" + "\n".join(violations)


def test_zero_testclient_or_blocking_sync_io_in_src_and_assistant_core() -> None:
    """Forbid `testclient`/`pytest in sys.modules` & sync I/O in `apps/api` + `orcia_core`."""
    idx = get_repo_source_index(REPO_ROOT)
    test_branch_violations: list[str] = []
    for path in idx.files_under_many(("apps/api/src", "packages/orcia-core/src"), suffix=".py"):
        src = idx.read_text(path)
        if "testclient" in src.lower() or "ORCIA_FORCE_LIVE_LLM" in src:
            test_branch_violations.append(str(path.relative_to(idx.repo_root)))
        if re.search(r"['\"]pytest['\"]\s+in\s+sys\.modules", src):
            test_branch_violations.append(str(path.relative_to(idx.repo_root)))
    assert test_branch_violations == [], f"Test branches in src/: {test_branch_violations}"

    sync_violations = find_sync_blocking_io_violations(API_SRC_DIR, CORE_SRC_DIR)
    assert sync_violations == [], "Blocking sync I/O violations:\n" + "\n".join(sync_violations)


def test_zero_legacy_routes_zero_require_rag_and_zero_story26_overrides() -> None:
    """Confirm 0 legacy routes, 0 `require_rag_available`, and 0 `dependency_overrides`."""
    idx = get_repo_source_index(REPO_ROOT)
    schema = create_app().openapi()
    paths = set(schema.get("paths", {}).keys())
    for legacy in _LEGACY_ROUTE_FRAGMENTS:
        assert not any(legacy in p for p in paths), f"Legacy route still in OpenAPI: {legacy}"

    for router_file in idx.files_under("apps/api/src/orcia_api/routers", suffix=".py"):
        if router_file.name != "ontology_and_rag.py":
            txt = idx.read_text(router_file)
            assert "require_rag_available" not in txt, (
                f"{router_file.name} references require_rag_available"
            )

    story_26_tests = sorted(
        p for p in idx.files_under("tests", suffix=".py") if p.name.startswith("test_story_26_")
    )
    assert any(p.parent.name == "api" for p in story_26_tests)
    story_3_3 = (
        REPO_ROOT / "tests" / "unit" / "test_story_3_3_assistant_agent_5_nodes_and_context_ports.py"
    )
    for test_path in [*story_26_tests, story_3_3]:
        txt = idx.read_text(test_path)
        if test_path.name != Path(__file__).name:
            assert "require_rag_available" not in txt, (
                f"{test_path} references require_rag_available"
            )
        tree = idx.parse_ast(test_path)
        for node in ast.walk(tree):
            if isinstance(node, ast.Subscript) and isinstance(node.value, ast.Attribute):
                assert node.value.attr != "dependency_overrides", (
                    f"{test_path.name}:{node.lineno} mutates dependency_overrides"
                )
            elif (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Attribute)
                and isinstance(node.func.value, ast.Attribute)
                and node.func.value.attr == "dependency_overrides"
            ):
                raise AssertionError(f"{test_path.name}:{node.lineno} mutates dependency_overrides")
            elif isinstance(node, ast.Assign):
                for tgt in node.targets:
                    if isinstance(tgt, ast.Attribute) and tgt.attr == "dependency_overrides":
                        raise AssertionError(
                            f"{test_path.name}:{node.lineno} assigns dependency_overrides"
                        )


def test_zero_uncalled_assistant_routes_and_mcp_ask_exposure() -> None:
    """Every `/api/v1/assistant/*` route is typed in `@orcia/api-client` & called in `apps/web`."""
    schema_paths = create_app().openapi().get("paths", {})
    assistant_ops = {
        (m.upper(), p)
        for p, methods in schema_paths.items()
        if p.startswith("/api/v1/assistant")
        for m in methods
        if m.lower() in {"get", "post", "put", "patch", "delete"}
    }
    assert assistant_ops == set(_EXPECTED_ASSISTANT_CLIENT_CALLS.keys())

    gen_schema = (
        REPO_ROOT / "packages" / "api-client" / "src" / "generated" / "schema.ts"
    ).read_text(encoding="utf-8")
    domains_src = "\n".join(
        p.read_text(encoding="utf-8")
        for p in sorted((REPO_ROOT / "packages" / "api-client" / "src" / "domains").rglob("*.ts"))
    )
    web_src = "\n".join(
        p.read_text(encoding="utf-8")
        for p in sorted((REPO_ROOT / "apps" / "web" / "src").rglob("*.ts*"))
        if "__tests__" not in p.parts
    )
    for (_method, path), client_fn in _EXPECTED_ASSISTANT_CLIENT_CALLS.items():
        assert f'"{path}"' in gen_schema, f"{path} missing in generated schema.ts"
        assert client_fn in domains_src, f"{client_fn} missing in @orcia/api-client domains"
        assert client_fn in web_src, f"{client_fn} for {path} has 0 callers in apps/web/src"

    assert '"/api/v1/mcp/spaces/{workspace_slug}/invoke"' in gen_schema
    mcp_bridge = (API_ROUTERS_DIR / "_mcp_assistant_ask_bridge.py").read_text(encoding="utf-8")
    assert "invoke_mcp_assistant_ask_async" in mcp_bridge


def test_epic_26_harness_files_under_300_lines_and_single_prompt_builder() -> None:
    """Confirm all Epic 26 harness modules <= 300 L and single canonical prompt builder."""
    harness_files = collect_epic_26_harness_files(REPO_ROOT)
    assert len(harness_files) >= 50
    oversized = [
        f"{p.relative_to(REPO_ROOT)} ({len(p.read_text(encoding='utf-8').splitlines())} L)"
        for p in harness_files
        if len(p.read_text(encoding="utf-8").splitlines()) > 300
    ]
    assert oversized == [], f"Epic 26 harness files > 300 L: {oversized}"

    idx = get_repo_source_index(REPO_ROOT)
    layer1_holders: list[str] = []
    raw_marker_holders: list[str] = []
    prompt_builders: list[str] = []
    for path in idx.files_under_many(
        ("apps/api/src", "packages/orcia-core/src/orcia_core"), suffix=".py"
    ):
        txt = idx.read_text(path)
        rel = str(path.relative_to(idx.repo_root))
        if "[CONSTITUTIONAL_IMMUTABLE_LAYER_1]" in txt:
            raw_marker_holders.append(rel)
        if "Core operating principles:" in txt:
            layer1_holders.append(rel)
        if "class AssistantPromptBuilder" in txt:
            prompt_builders.append(rel)

    assert raw_marker_holders == []
    assert layer1_holders == [
        "packages/orcia-core/src/orcia_core/orchestration/assistant_prompt_locales.py"
    ]
    assert prompt_builders == [
        "packages/orcia-core/src/orcia_core/orchestration/assistant_prompt_builder.py"
    ]
    facade = (API_ROUTERS_DIR / "assistant_llm_prompts.py").read_text(encoding="utf-8")
    assert "_PROMPT_BUILDER = AssistantPromptBuilder()" in facade
