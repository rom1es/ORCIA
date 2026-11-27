"""Git diff removed-assertion check and FastAPI route guard AST audit."""

from __future__ import annotations

import ast
import re
import subprocess
from pathlib import Path

ASSERT_LINE_RE = re.compile(r"^\s*(?:assert\b|expect\s*\()")
TEST_FILE_PATTERNS = ("tests/", "/__tests__/", "/e2e/")

ROUTE_GUARD_TOKENS: tuple[str, ...] = (
    "ScopeAccessGuard",
    "RunAccessGuard",
    "resolve_workspace_access",
    "enforce_workspace",
    "require_workspace",
    "validate_workspace",
    "resolve_finops_read_scope",
    "_enforce_",
    "access_mode",
    "evaluator",
    "require_scope",
    "check_scope",
    "has_permission",
    "authorize",
    "permission",
    "assert_workspace",
    "verify_workspace",
    "assert_run",
    "check_run",
    "enforce_run",
    "require_run",
)


def _is_test_rel_path(rel_path: str) -> bool:
    if rel_path.endswith(".py") and rel_path.startswith("tests/"):
        return Path(rel_path).name.startswith("test_")
    return bool(
        rel_path.endswith((".ts", ".tsx"))
        and ("/__tests__/" in rel_path or rel_path.startswith("apps/web/e2e/"))
    )


def collect_git_test_diff(repo_root: Path) -> str:
    """Return unified-0 git diff (HEAD + staged) for test directories."""
    chunks: list[str] = []
    for cmd in (
        ["git", "diff", "--unified=0", "HEAD", "--", "tests", "apps/web", "packages"],
        ["git", "diff", "--cached", "--unified=0", "--", "tests", "apps/web", "packages"],
    ):
        proc = subprocess.run(cmd, cwd=repo_root, capture_output=True, text=True, check=False)
        if proc.returncode == 0 and proc.stdout:
            chunks.append(proc.stdout)
    return "\n".join(chunks)


def check_removed_assertions(
    diff_text: str,
    *,
    redundancy_audit_allowlist: set[str],
) -> list[str]:
    """Detect net assertion removals in modified pre-existing test files unless allowlisted."""
    if not diff_text.strip():
        return []
    current_file: str | None = None
    removed_by_file: dict[str, int] = {}
    added_by_file: dict[str, int] = {}
    is_new_file = False

    for line in diff_text.splitlines():
        if line.startswith("diff --git "):
            parts = line.split()
            b_part = parts[-1] if parts else ""
            current_file = b_part[2:] if b_part.startswith("b/") else b_part
            is_new_file = False
            continue
        if line.startswith("new file mode "):
            is_new_file = True
            continue
        if current_file is None or is_new_file or not _is_test_rel_path(current_file):
            continue
        if line.startswith("---") or line.startswith("+++") or line.startswith("@@"):
            continue
        if line.startswith("-"):
            body = line[1:]
            if ASSERT_LINE_RE.match(body):
                removed_by_file[current_file] = removed_by_file.get(current_file, 0) + 1
        elif line.startswith("+"):
            body = line[1:]
            if ASSERT_LINE_RE.match(body):
                added_by_file[current_file] = added_by_file.get(current_file, 0) + 1

    violations: list[str] = []
    for rel, removed_cnt in sorted(removed_by_file.items()):
        if rel in redundancy_audit_allowlist:
            continue
        added_cnt = added_by_file.get(rel, 0)
        if removed_cnt > added_cnt:
            violations.append(
                f"{rel}: removed {removed_cnt} assertion(s) vs {added_cnt} added "
                "(requires redundancy-audit allowlist entry)"
            )
    return violations


def _collect_router_helpers(routers_dir: Path) -> dict[str, str]:
    helpers: dict[str, str] = {}
    for p in sorted(routers_dir.rglob("*.py")):
        src = p.read_text(encoding="utf-8", errors="replace")
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        for node in tree.body:
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                seg = ast.get_source_segment(src, node) or ""
                if seg:
                    helpers[node.name] = seg
    return helpers


def find_unguarded_workspace_or_run_routes(repo_root: Path) -> list[str]:
    """Return sorted `<rel_path>:<func_name>` for routes lacking a workspace/run guard."""
    routers_dir = repo_root / "apps" / "api" / "src" / "orcia_api" / "routers"
    if not routers_dir.is_dir():
        return []
    helpers = _collect_router_helpers(routers_dir)
    unguarded: list[str] = []
    for p in sorted(routers_dir.rglob("*.py")):
        src = p.read_text(encoding="utf-8", errors="replace")
        try:
            tree = ast.parse(src)
        except SyntaxError:
            continue
        rel = p.relative_to(repo_root).as_posix()
        for node in tree.body:
            if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                continue
            is_route = any(
                isinstance(d, ast.Call)
                and isinstance(d.func, ast.Attribute)
                and isinstance(d.func.value, ast.Name)
                and "router" in d.func.value.id
                and d.func.attr in ("get", "post", "put", "patch", "delete")
                for d in node.decorator_list
            )
            if not is_route:
                continue
            fn_src = ast.get_source_segment(src, node) or ""
            if "workspace_id" not in fn_src and "run_id" not in fn_src:
                continue
            combined = fn_src
            for call in ast.walk(node):
                if isinstance(call, ast.Call) and isinstance(call.func, ast.Name):
                    combined += "\n" + helpers.get(call.func.id, "")
            if not any(tok in combined for tok in ROUTE_GUARD_TOKENS):
                unguarded.append(f"{rel}:{node.name}")
    return sorted(set(unguarded))


def check_unguarded_routes(repo_root: Path, allowlist: set[str]) -> list[str]:
    """Fail on any unguarded `workspace_id`/`run_id` FastAPI route beyond `allowlist`."""
    current = find_unguarded_workspace_or_run_routes(repo_root)
    return [entry for entry in current if entry not in allowlist]
