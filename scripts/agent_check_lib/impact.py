"""Static impact selection: AST import graph, FastAPI router prefixes, audits, Vitest."""

from __future__ import annotations

import ast
import re
from collections import defaultdict, deque
from dataclasses import dataclass
from pathlib import Path

from scripts.agent_check_lib.env import load_pyproject_pythonpath

DEFAULT_ALWAYS_RUN_AUDITS: tuple[str, ...] = (
    "tests/unit/test_integration_no_manual_app_state_audit.py",
    "tests/unit/test_capabilities_registry.py",
    "tests/unit/test_e2e_stack_config.py",
    "tests/unit/test_e2e_sql_coverage_audit.py",
    "tests/unit/test_assistant_and_rag_routes_require_rag_guard_audit.py",
)

ROUTER_PREFIX_RE = re.compile(r'APIRouter\([^)]*prefix\s*=\s*["\']([^"\']+)["\']')
ROUTE_DECORATOR_RE = re.compile(
    r'@router\.(?:get|post|put|patch|delete|options|head)\(\s*["\']([^"\']+)["\']'
)


@dataclass(frozen=True, slots=True)
class ImpactPlan:
    """Selected Python tests, Vitest workspace inputs, and `--explain` reasons."""

    python_tests: list[str]
    vitest_files_by_pkg: dict[str, list[str]]
    reasons: dict[str, list[str]]


def _module_name_for_path(path: Path, roots: list[Path]) -> str | None:
    resolved = path.resolve()
    for root in roots:
        try:
            rel = resolved.relative_to(root.resolve())
        except ValueError:
            continue
        parts = list(rel.parts)
        if not parts:
            continue
        if parts[-1] == "__init__.py":
            parts = parts[:-1]
        elif parts[-1].endswith(".py"):
            parts[-1] = parts[-1][:-3]
        else:
            continue
        if parts:
            return ".".join(parts)
    return None


def _extract_imported_modules(py_file: Path) -> set[str]:
    try:
        tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
    except (OSError, SyntaxError, UnicodeDecodeError):
        return set()
    imported: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                imported.add(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.add(node.module)
            for alias in node.names:
                if alias.name != "*":
                    imported.add(f"{node.module}.{alias.name}")
    return imported


def _build_reverse_import_graph(
    repo_root: Path, roots: list[Path]
) -> tuple[dict[str, set[str]], dict[str, str]]:
    """Build `(reverse_graph: module -> importing_modules, module_to_rel_path)`."""
    reverse_graph: dict[str, set[str]] = defaultdict(set)
    module_to_rel: dict[str, str] = {}
    scan_dirs = [p for p in [*roots, repo_root / "tests"] if p.is_dir()]
    seen_files: set[Path] = set()

    for scan_dir in scan_dirs:
        for py_file in scan_dir.rglob("*.py"):
            resolved = py_file.resolve()
            if resolved in seen_files:
                continue
            if any(
                part in {".venv", "__pycache__", "node_modules", ".git"} for part in resolved.parts
            ):
                continue
            seen_files.add(resolved)
            mod_name = _module_name_for_path(resolved, [*roots, repo_root])
            if not mod_name:
                continue
            try:
                rel = resolved.relative_to(repo_root.resolve()).as_posix()
            except ValueError:
                continue
            module_to_rel[mod_name] = rel
            for imp in _extract_imported_modules(resolved):
                reverse_graph[imp].add(mod_name)
                # Also index parent package imports (`from pkg.mod import fn` -> `pkg.mod`)
                if "." in imp:
                    reverse_graph[imp.rsplit(".", 1)[0]].add(mod_name)
    return reverse_graph, module_to_rel


def _collect_router_paths(router_file: Path) -> set[str]:
    try:
        text = router_file.read_text(encoding="utf-8")
    except OSError:
        return set()
    literals: set[str] = set()
    for match in ROUTER_PREFIX_RE.finditer(text):
        val = match.group(1).strip()
        if val and val != "/":
            literals.add(val)
    for match in ROUTE_DECORATOR_RE.finditer(text):
        val = match.group(1).strip()
        if len(val) > 3:
            literals.add(val)
    return literals


def _is_unit_or_fast_test_rel(rel: str) -> bool:
    return (
        rel.startswith(("tests/unit/", "tests/contract/", "tests/evals/", "tests/security/"))
        and Path(rel).name.startswith("test_")
        and rel.endswith(".py")
    )


def select_impacted_targets(
    repo_root: Path,
    *,
    touched_files: list[str],
    always_run_audits: tuple[str, ...] = DEFAULT_ALWAYS_RUN_AUDITS,
) -> ImpactPlan:
    """Select Python tests and Vitest inputs deterministically with `--explain` reasons."""
    reasons: dict[str, list[str]] = defaultdict(list)
    roots = load_pyproject_pythonpath(repo_root)
    reverse_graph, module_to_rel = _build_reverse_import_graph(repo_root, roots)

    # 1. Always-run fast audits
    for audit_rel in always_run_audits:
        if (repo_root / audit_rel).is_file():
            reasons[audit_rel].append("always_run_audit")

    # 2. Direct touched test files + seed modules for BFS + router path literals
    seed_modules: list[str] = []
    router_literals: dict[str, set[str]] = {}
    vitest_by_pkg: dict[str, list[str]] = defaultdict(list)

    for rel in touched_files:
        abs_path = repo_root / rel
        if _is_unit_or_fast_test_rel(rel) and abs_path.is_file():
            reasons[rel].append(f"touched_test:{rel}")
        if rel.endswith(".py") and abs_path.is_file():
            mod = _module_name_for_path(abs_path, [*roots, repo_root])
            if mod:
                seed_modules.append(mod)
            if "/routers/" in rel or rel.endswith("_router.py"):
                lits = _collect_router_paths(abs_path)
                if lits:
                    router_literals[rel] = lits

        for pkg_prefix in ("apps/web", "packages/ui", "packages/api-client"):
            if rel.startswith(f"{pkg_prefix}/") and rel.endswith((".ts", ".tsx", ".css", ".json")):
                pkg_rel = rel[len(pkg_prefix) + 1 :]
                vitest_by_pkg[pkg_prefix].append(pkg_rel)
                reasons[f"vitest:{pkg_prefix}"].append(f"vitest_related:{rel}")

    # 3. Reverse import graph BFS
    visited: set[str] = set(seed_modules)
    queue: deque[str] = deque(seed_modules)
    while queue:
        current = queue.popleft()
        for importer in sorted(reverse_graph.get(current, ())):
            rel = module_to_rel.get(importer, "")
            if rel and _is_unit_or_fast_test_rel(rel):
                reasons[rel].append(f"reverse_import:{current}")
            if importer not in visited:
                visited.add(importer)
                queue.append(importer)

    # 4. FastAPI router prefix / path literal matching against HTTP tests
    if router_literals:
        for rel in sorted(module_to_rel.values()):
            if not _is_unit_or_fast_test_rel(rel):
                continue
            try:
                content = (repo_root / rel).read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            for router_rel, lits in router_literals.items():
                if any(lit in content for lit in lits):
                    reasons[rel].append(f"router_prefix:{router_rel}")

    python_tests = sorted(k for k in reasons if k.endswith(".py"))
    return ImpactPlan(
        python_tests=python_tests,
        vitest_files_by_pkg={k: sorted(set(v)) for k, v in sorted(vitest_by_pkg.items())},
        reasons={k: sorted(set(v)) for k, v in sorted(reasons.items())},
    )
