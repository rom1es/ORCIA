"""AST and route audit helpers for Story 26.10 Epic 26 closure checks."""

from __future__ import annotations

import ast
from pathlib import Path

FORBIDDEN_STATE_PREFIXES = (
    "_TURN_",
    "_THREAD_",
    "_DRAFT_",
    "_GOVERNANCE_",
    "_DEFAULT_",
    "ACTIVE_WORKSPACE_TURNS",
    "PROMPT_TELEMETRY_LOG",
    "_phantom_audit_log",
    "_saved_drafts",
    "_folder_meta",
)

MUTABLE_CALL_NAMES = frozenset(
    {"dict", "list", "set", "defaultdict", "OrderedDict", "deque", "Lock", "RLock", "Semaphore"}
)

LEGACY_SYNC_IO_CORE_ALLOWLIST = frozenset(
    {
        "bootstrap/_internal/litellm_adapter.py",
        "bootstrap/rag_seeds.py",
        "catalog/_internal/seaweedfs_adapter.py",
        "gates/agentic.py",
        "gates/deterministic.py",
        "gates/sandbox.py",
        "gates/tier2_sandbox.py",
        "orchestration/agents_and_skills_manager.py",
        "orchestration/assistant_agent.py",
        "orchestration/assistant_agent_synthesis.py",
        "orchestration/step_executors.py",
        "rag/context_adapters.py",
        "rag/hybrid_rag_service.py",
    }
)


def _is_openapi_responses_dict(name: str, val: ast.expr | None) -> bool:
    if not isinstance(val, ast.Dict):
        return False
    if not (name.endswith("_RESPONSES") or name == "PROBLEM_RESPONSES"):
        return False
    return all(
        key is None
        or (
            isinstance(key, ast.Constant) and isinstance(key.value, int) and 100 <= key.value <= 599
        )
        for key in val.keys
    )


def _call_leaf_name(func: ast.expr) -> str | None:
    if isinstance(func, ast.Name):
        return func.id
    if isinstance(func, ast.Attribute):
        return func.attr
    return None


def find_mutable_module_container_violations(routers_dir: Path) -> list[str]:
    """Reject any module-level mutable container or lock in `routers/` (no upper-case exemption)."""
    violations: list[str] = []
    for path in sorted(routers_dir.rglob("*.py")):
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in tree.body:
            targets: list[str] = []
            val: ast.expr | None = None
            if isinstance(node, ast.Assign):
                targets = [t.id for t in node.targets if isinstance(t, ast.Name)]
                val = node.value
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                targets = [node.target.id]
                val = node.value
            for name in targets:
                if name == "__all__":
                    continue
                if any(name.startswith(p) for p in FORBIDDEN_STATE_PREFIXES):
                    violations.append(f"{path.name}:{node.lineno} forbidden global `{name}`")
                elif isinstance(val, ast.List | ast.Set):
                    violations.append(
                        f"{path.name}:{node.lineno} mutable module container `{name}`"
                    )
                elif isinstance(val, ast.Dict) and not _is_openapi_responses_dict(name, val):
                    violations.append(f"{path.name}:{node.lineno} mutable module dict `{name}`")
                elif isinstance(val, ast.Call):
                    callee = _call_leaf_name(val.func)
                    if callee in MUTABLE_CALL_NAMES:
                        violations.append(
                            f"{path.name}:{node.lineno} mutable call `{callee}()` for `{name}`"
                        )
    return violations


def _scan_blocking_sync_ast(path: Path, rel: str) -> list[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=rel)
    hits: list[str] = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                if alias.name == "requests" or alias.name == "urllib.request":
                    hits.append(f"{rel}:{node.lineno} imports `{alias.name}`")
        elif isinstance(node, ast.ImportFrom) and node.module in {"requests", "urllib.request"}:
            hits.append(f"{rel}:{node.lineno} imports from `{node.module}`")
        elif isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
            pair = f"{node.value.id}.{node.attr}"
            if pair in {"httpx.Client", "asyncio.run", "requests.get", "requests.post"}:
                hits.append(f"{rel}:{node.lineno} uses `{pair}`")
        elif isinstance(node, ast.Name) and node.id == "ThreadPoolExecutor":
            hits.append(f"{rel}:{node.lineno} references `ThreadPoolExecutor`")
    return hits


def find_sync_blocking_io_violations(api_src_dir: Path, core_src_dir: Path) -> list[str]:
    """Audit all `apps/api/src/` and `packages/orcia-core/src/orcia_core/` against sync I/O."""
    violations: list[str] = []
    core_pkg = core_src_dir / "orcia_core"
    for rel_legacy in sorted(LEGACY_SYNC_IO_CORE_ALLOWLIST):
        assert (core_pkg / rel_legacy).exists(), f"Stale sync allowlist entry: {rel_legacy}"

    for path in sorted(api_src_dir.rglob("*.py")):
        violations.extend(_scan_blocking_sync_ast(path, str(path.relative_to(api_src_dir.parent))))

    for path in sorted(core_pkg.rglob("*.py")):
        rel_pkg = str(path.relative_to(core_pkg))
        if rel_pkg in LEGACY_SYNC_IO_CORE_ALLOWLIST:
            continue
        violations.extend(_scan_blocking_sync_ast(path, f"orcia_core/{rel_pkg}"))
    return violations


def collect_epic_26_harness_files(repo_root: Path) -> list[Path]:
    """Return every Epic 26 harness file across `apps/api` and `packages/orcia-core`."""
    api_pkg = repo_root / "apps" / "api" / "src" / "orcia_api"
    core_pkg = repo_root / "packages" / "orcia-core" / "src" / "orcia_core"
    paths = [
        *sorted((api_pkg / "routers").glob("*assistant*.py")),
        *sorted((api_pkg / "dependencies").glob("*assistant*.py")),
        *sorted((api_pkg / "schemas").glob("assistant*.py")),
        *sorted((core_pkg / "orchestration").glob("assistant_*.py")),
        *sorted((core_pkg / "orchestration").glob("_assistant_*.py")),
        *sorted((core_pkg / "orchestration").glob("llm_*.py")),
        *sorted((core_pkg / "orchestration").glob("redis_*.py")),
        core_pkg / "orchestration" / "ssrf_guard.py",
        *sorted((core_pkg / "orchestration").glob("ai_models_*.py")),
        *sorted((core_pkg / "agents").glob("*assistant*.py")),
        core_pkg / "agents" / "governed_tool_router.py",
    ]
    return sorted({p for p in paths if p.exists()})
