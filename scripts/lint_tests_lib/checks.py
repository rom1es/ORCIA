"""AST/file checks for fake SQL engines, `test_story_*` ratchet, and proportionality."""

from __future__ import annotations

import ast
from pathlib import Path

FAKE_SQL_CLASS_NAMES: frozenset[str] = frozenset(
    {"FakeSqlEngine", "_FakeEngine", "FakeSqlResult", "_FakeSqlResult"}
)
SQL_DISPATCH_VERBS: tuple[str, ...] = ("SELECT ", "INSERT ", "UPDATE ", "DELETE ", "FROM ")
SQL_METHODS: frozenset[str] = frozenset(
    {
        "execute",
        "scalars",
        "scalar",
        "scalar_one",
        "scalar_one_or_none",
        "mappings",
        "fetchall",
        "fetchone",
        "begin",
        "connect",
        "commit",
        "rollback",
    }
)


def _has_fake_sql_engine_ast(source: str) -> bool:
    """Return True if Python source defines or imports a fake SQL engine or SQL dispatcher."""
    try:
        tree = ast.parse(source)
    except SyntaxError:
        return False
    for node in ast.walk(tree):
        if isinstance(node, ast.ClassDef):
            if node.name in FAKE_SQL_CLASS_NAMES:
                return True
            name_low = node.name.lower()
            if "fake" in name_low:
                if any(
                    k in name_low
                    for k in (
                        "engine",
                        "session",
                        "sqlresult",
                        "sql_result",
                        "sqlconn",
                        "mappingsresult",
                    )
                ):
                    return True
                if "sql" in name_low:
                    method_names = {
                        item.name
                        for item in node.body
                        if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                    }
                    if method_names & SQL_METHODS:
                        return True
        elif isinstance(node, ast.ImportFrom):
            if node.module and "_fake_sql_engine" in node.module:
                return True
            if any(alias.name in FAKE_SQL_CLASS_NAMES for alias in node.names):
                return True
        elif isinstance(node, ast.AsyncFunctionDef) and node.name == "execute":
            seg = ast.get_source_segment(source, node) or ""
            upper_seg = seg.upper()
            if sum(1 for v in SQL_DISPATCH_VERBS if v in upper_seg) >= 2:
                return True
    return False


def find_fake_sql_engine_files(repo_root: Path) -> list[str]:
    """Return sorted `tests/unit/` relative paths containing fake SQL engines."""
    unit_dir = repo_root / "tests" / "unit"
    if not unit_dir.is_dir():
        return []
    found: list[str] = []
    for path in sorted(unit_dir.rglob("*.py")):
        if "__pycache__" in path.parts:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        if _has_fake_sql_engine_ast(text):
            found.append(path.relative_to(repo_root).as_posix())
    return found


def check_fake_sql_engines(repo_root: Path, allowlist: set[str]) -> list[str]:
    """Fail on any `tests/unit/` file with fake SQL engines beyond `allowlist`."""
    current = find_fake_sql_engine_files(repo_root)
    return [rel for rel in current if rel not in allowlist]


def find_story_test_files(repo_root: Path) -> list[str]:
    """Return sorted `tests/**/test_story_*.py` relative paths."""
    tests_dir = repo_root / "tests"
    if not tests_dir.is_dir():
        return []
    return sorted(
        p.relative_to(repo_root).as_posix()
        for p in tests_dir.rglob("test_story_*.py")
        if "__pycache__" not in p.parts
    )


def check_legacy_story_test_files(repo_root: Path, allowlist: set[str]) -> list[str]:
    """Fail on any `test_story_*.py` file beyond `allowlist`."""
    current = find_story_test_files(repo_root)
    return [rel for rel in current if rel not in allowlist]


def _count_lines_in_roots(repo_root: Path, rel_dirs: tuple[str, ...], exts: tuple[str, ...]) -> int:
    total = 0
    for rel_dir in rel_dirs:
        base = repo_root / rel_dir
        if not base.is_dir():
            continue
        for p in base.rglob("*"):
            if not p.is_file() or p.suffix not in exts:
                continue
            if any(
                part in {"node_modules", "__pycache__", ".venv", "generated"} for part in p.parts
            ):
                continue
            try:
                total += len(p.read_text(encoding="utf-8", errors="replace").splitlines())
            except OSError:
                continue
    return total


def compute_proportionality_report(repo_root: Path) -> tuple[int, int, float]:
    """Return `(test_loc, prod_loc, ratio)` as a non-blocking test-to-code metric."""
    prod_loc = _count_lines_in_roots(
        repo_root,
        (
            "packages/orcia-core/src",
            "packages/orcia-connectors/src",
            "apps/api/src",
            "apps/worker/src",
        ),
        (".py",),
    ) + _count_lines_in_roots(repo_root, ("packages/ui/src", "apps/web/src"), (".ts", ".tsx"))
    # Subtract Vitest __tests__ from prod_loc if counted under apps/web/src or packages/ui/src
    ts_test_loc = _count_lines_in_roots(
        repo_root,
        (
            "packages/ui/src/__tests__",
            "packages/api-client/src/__tests__",
            "apps/web/src/__tests__",
            "apps/web/e2e",
        ),
        (".ts", ".tsx"),
    )
    py_test_loc = _count_lines_in_roots(repo_root, ("tests",), (".py",))
    test_loc = py_test_loc + ts_test_loc
    effective_prod = max(1, prod_loc - ts_test_loc)
    return test_loc, effective_prod, round(test_loc / effective_prod, 2)
