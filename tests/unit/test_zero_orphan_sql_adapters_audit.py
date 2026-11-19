"""AST audit ensuring zero orphan SQL adapter modules in `packages/orcia-core`.

Traverses the static import graph starting from `apps/api/src/` and `apps/worker/src/`
(including transitive imports across `orcia_core`, `orcia_kernel`, and `orcia_connectors`)
and verifies that 100 % of `packages/orcia-core/src/orcia_core/**/_internal/*sql*.py`
SQL adapter modules have at least one active runtime caller outside `tests/`.
"""

from __future__ import annotations

import ast
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
ORCIA_CORE_PKG_DIR = REPO_ROOT / "packages" / "orcia-core" / "src" / "orcia_core"

RUNTIME_ENTRY_ROOTS: tuple[Path, ...] = (
    REPO_ROOT / "apps" / "api" / "src",
    REPO_ROOT / "apps" / "worker" / "src",
)

WORKSPACE_SRC_ROOTS: tuple[Path, ...] = (
    REPO_ROOT / "packages" / "orcia-core" / "src",
    REPO_ROOT / "packages" / "orcia-kernel" / "src",
    REPO_ROOT / "packages" / "orcia-connectors" / "src",
    REPO_ROOT / "apps" / "api" / "src",
    REPO_ROOT / "apps" / "worker" / "src",
)


def _build_module_index() -> tuple[dict[str, Path], dict[Path, str]]:
    mod_to_file: dict[str, Path] = {}
    file_to_mod: dict[Path, str] = {}
    for root in WORKSPACE_SRC_ROOTS:
        if not root.exists():
            continue
        for py_file in sorted(root.rglob("*.py")):
            rel = py_file.relative_to(root)
            parts = list(rel.parts)
            if parts[-1] == "__init__.py":
                mod_name = ".".join(parts[:-1])
            else:
                parts[-1] = parts[-1][:-3]
                mod_name = ".".join(parts)
            if mod_name:
                mod_to_file[mod_name] = py_file
                file_to_mod[py_file] = mod_name
    return mod_to_file, file_to_mod


def _extract_imported_modules(
    py_file: Path,
    current_mod: str,
    mod_to_file: dict[str, Path],
) -> list[str]:
    tree = ast.parse(py_file.read_text(encoding="utf-8"), filename=str(py_file))
    targets: set[str] = set()
    is_pkg = py_file.name == "__init__.py"
    pkg_parts = current_mod.split(".") if is_pkg else current_mod.split(".")[:-1]

    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                targets.add(alias.name)
        elif isinstance(node, ast.ImportFrom):
            base = node.module or ""
            if node.level > 0:
                up = pkg_parts[: len(pkg_parts) - (node.level - 1)]
                base = ".".join([*up, base]) if base else ".".join(up)
            if base:
                targets.add(base)
                for alias in node.names:
                    candidate = f"{base}.{alias.name}"
                    if candidate in mod_to_file:
                        targets.add(candidate)

    return sorted(t for t in targets if t in mod_to_file)


def _collect_reachable_runtime_modules(
    mod_to_file: dict[str, Path],
    file_to_mod: dict[Path, str],
) -> set[str]:
    queue: list[str] = []
    visited: set[str] = set()

    for root in RUNTIME_ENTRY_ROOTS:
        if not root.exists():
            continue
        for py_file in sorted(root.rglob("*.py")):
            mod = file_to_mod[py_file]
            if mod not in visited:
                visited.add(mod)
                queue.append(mod)

    while queue:
        current = queue.pop(0)
        for dep in _extract_imported_modules(mod_to_file[current], current, mod_to_file):
            if dep not in visited:
                visited.add(dep)
                queue.append(dep)

    return visited


def test_every_core_internal_sql_adapter_is_wired_to_api_or_worker_runtime() -> None:
    """Verify 100 % of `orcia_core/**/_internal/{sql_,_sql_}*.py` adapters have runtime callers."""
    mod_to_file, file_to_mod = _build_module_index()
    reachable = _collect_reachable_runtime_modules(mod_to_file, file_to_mod)

    sql_adapter_files = sorted(
        path
        for path in ORCIA_CORE_PKG_DIR.rglob("_internal/*.py")
        if path.name.startswith(("sql_", "_sql_"))
    )
    assert len(sql_adapter_files) >= 50

    orphans = [
        f"{file_to_mod[path]} ({path.relative_to(REPO_ROOT)})"
        for path in sql_adapter_files
        if file_to_mod[path] not in reachable
    ]
    assert orphans == [], (
        "Orphan SQL adapter module(s) found in `packages/orcia-core` without active caller "
        "in `apps/api/src/` or `apps/worker/src/`:\n" + "\n".join(orphans)
    )
