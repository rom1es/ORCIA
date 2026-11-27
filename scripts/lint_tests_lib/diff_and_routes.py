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
    """Return unified-0 git diff (HEAD + staged + untracked new tests) for test directories."""
    chunks: list[str] = []
    for cmd in (
        ["git", "diff", "--unified=0", "HEAD", "--", "tests", "apps/web", "packages"],
        ["git", "diff", "--cached", "--unified=0", "--", "tests", "apps/web", "packages"],
    ):
        proc = subprocess.run(cmd, cwd=repo_root, capture_output=True, text=True, check=False)
        if proc.returncode == 0 and proc.stdout:
            chunks.append(proc.stdout)
    untracked = subprocess.run(
        [
            "git",
            "ls-files",
            "--others",
            "--exclude-standard",
            "--",
            "tests",
            "apps/web",
            "packages",
        ],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    if untracked.returncode == 0 and untracked.stdout:
        for rel in untracked.stdout.splitlines():
            rel = rel.strip()
            if not rel or not _is_test_rel_path(rel):
                continue
            target = repo_root / rel
            if not target.is_file():
                continue
            added_lines = [
                f"+{ln}"
                for ln in target.read_text(encoding="utf-8", errors="replace").splitlines()
                if ASSERT_LINE_RE.match(ln)
            ]
            if added_lines:
                chunks.append(
                    "\n".join(
                        [
                            f"diff --git a/{rel} b/{rel}",
                            "new file mode 100644",
                            *added_lines,
                        ]
                    )
                )
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
    deleted_files: set[str] = set()
    new_file_added_by_dir: dict[str, int] = {}
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
        if line.startswith("deleted file mode "):
            if current_file is not None and _is_test_rel_path(current_file):
                deleted_files.add(current_file)
            continue
        if current_file is None or not _is_test_rel_path(current_file):
            continue
        if is_new_file:
            if (
                line.startswith("+")
                and not line.startswith("+++")
                and ASSERT_LINE_RE.match(line[1:])
            ):
                dir_key = str(Path(current_file).parent)
                new_file_added_by_dir[dir_key] = new_file_added_by_dir.get(dir_key, 0) + 1
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
    remaining_new_by_dir = dict(new_file_added_by_dir)
    for rel, removed_cnt in sorted(removed_by_file.items()):
        if rel in redundancy_audit_allowlist:
            continue
        if rel in deleted_files:
            dir_key = str(Path(rel).parent)
            avail = remaining_new_by_dir.get(dir_key, 0)
            if avail >= removed_cnt:
                remaining_new_by_dir[dir_key] = avail - removed_cnt
                continue
        added_cnt = added_by_file.get(rel, 0)
        if removed_cnt > added_cnt:
            violations.append(
                f"{rel}: removed {removed_cnt} assertion(s) vs {added_cnt} added "
                "(requires redundancy-audit allowlist entry)"
            )
    return violations


def _extract_depends_targets(node: ast.AST, aliases: dict[str, set[str]]) -> set[str]:
    """Collect callable names referenced inside `Depends(...)` or `Annotated[..., Depends(...)]`."""
    found: set[str] = set()
    for sub in ast.walk(node):
        if (
            isinstance(sub, ast.Call)
            and isinstance(sub.func, ast.Name)
            and sub.func.id == "Depends"
            and sub.args
        ):
            arg0 = sub.args[0]
            if isinstance(arg0, ast.Name):
                found.add(arg0.id)
            elif isinstance(arg0, ast.Attribute):
                found.add(arg0.attr)
        elif isinstance(sub, ast.Name) and sub.id in aliases:
            found.update(aliases[sub.id])
    return found


def _resolve_import_module_rel(cur_rel: str, node: ast.ImportFrom, repo_root: Path) -> str | None:
    """Resolve `orcia_api.*` or relative `ImportFrom` target to repo-relative `.py` path."""
    mod = node.module or ""
    if node.level > 0:
        cur_parts = Path(cur_rel).parts[: -node.level]
        base = Path(*cur_parts)
        rel_parts = mod.split(".") if mod else []
        cand_dir = base.joinpath(*rel_parts) if rel_parts else base
        for cand in (cand_dir.with_suffix(".py"), cand_dir / "__init__.py"):
            if (repo_root / cand).is_file():
                return cand.as_posix()
        return None
    if mod.startswith("orcia_api."):
        cand_dir = Path("apps/api/src").joinpath(*mod.split("."))
        for cand in (cand_dir.with_suffix(".py"), cand_dir / "__init__.py"):
            if (repo_root / cand).is_file():
                return cand.as_posix()
    return None


def _collect_router_and_guard_helpers(
    api_orcia_dir: Path,
    repo_root: Path,
) -> tuple[
    dict[str, dict[str, tuple[str, ast.AST]]],
    dict[str, tuple[str, ast.AST]],
    dict[str, dict[str, tuple[str, str]]],
    dict[str, set[str]],
]:
    """Collect module-scoped ASTs, shared deps, module import maps, and `Depends` aliases."""
    module_helpers: dict[str, dict[str, tuple[str, ast.AST]]] = {}
    shared_helpers: dict[str, tuple[str, ast.AST]] = {}
    module_imports: dict[str, dict[str, tuple[str, str]]] = {}
    dep_aliases: dict[str, set[str]] = {}
    scan_dirs = [api_orcia_dir / "routers", api_orcia_dir / "dependencies"]
    for scan_dir in scan_dirs:
        if not scan_dir.is_dir():
            continue
        is_deps = scan_dir.name == "dependencies"
        for p in sorted(scan_dir.rglob("*.py")):
            src = p.read_text(encoding="utf-8", errors="replace")
            try:
                tree = ast.parse(src)
            except SyntaxError:
                continue
            rel = p.relative_to(repo_root).as_posix()
            mod_map = module_helpers.setdefault(rel, {})
            imp_map = module_imports.setdefault(rel, {})
            for node in tree.body:
                if isinstance(node, ast.ImportFrom):
                    target_rel = _resolve_import_module_rel(rel, node, repo_root)
                    if target_rel:
                        for alias in node.names:
                            local_name = alias.asname or alias.name
                            imp_map[local_name] = (target_rel, alias.name)
                elif isinstance(node, ast.Assign) and len(node.targets) == 1:
                    tgt = node.targets[0]
                    if isinstance(tgt, ast.Name):
                        deps = _extract_depends_targets(node.value, {})
                        if deps:
                            dep_aliases.setdefault(tgt.id, set()).update(deps)
                elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    if (
                        is_deps
                        and node.name.startswith("get_")
                        and not node.name.endswith("_guard")
                    ):
                        continue
                    seg = ast.get_source_segment(src, node) or ""
                    if seg:
                        mod_map[node.name] = (seg, node)
                        if is_deps:
                            shared_helpers[node.name] = (seg, node)
    return module_helpers, shared_helpers, module_imports, dep_aliases


def _expand_route_and_helper_source(
    module_rel: str,
    route_node: ast.FunctionDef | ast.AsyncFunctionDef,
    fn_src: str,
    module_helpers: dict[str, dict[str, tuple[str, ast.AST]]],
    shared_helpers: dict[str, tuple[str, ast.AST]],
    module_imports: dict[str, dict[str, tuple[str, str]]],
    dep_aliases: dict[str, set[str]],
    *,
    max_hops: int = 3,
) -> str:
    """Return route source combined with up to `max_hops` of module/imported/dependency helpers."""
    chunks = [fn_src]
    visited: set[tuple[str, str]] = set()
    frontier: list[tuple[str, ast.AST]] = [(module_rel, route_node)]
    for _ in range(max_hops):
        next_frontier: list[tuple[str, ast.AST]] = []
        for cur_mod, cur_ast in frontier:
            names = _extract_depends_targets(cur_ast, dep_aliases)
            for sub in ast.walk(cur_ast):
                if isinstance(sub, ast.Call):
                    if isinstance(sub.func, ast.Name):
                        names.add(sub.func.id)
                    elif isinstance(sub.func, ast.Attribute):
                        names.add(sub.func.attr)
            local_map = module_helpers.get(cur_mod, {})
            imp_map = module_imports.get(cur_mod, {})
            for name in sorted(names):
                if name in local_map:
                    key = (cur_mod, name)
                    if key not in visited:
                        visited.add(key)
                        seg, helper_ast = local_map[name]
                        chunks.append(seg)
                        next_frontier.append((cur_mod, helper_ast))
                elif name in imp_map:
                    tgt_mod, orig_name = imp_map[name]
                    tgt_entry = module_helpers.get(tgt_mod, {}).get(orig_name)
                    if tgt_entry is not None:
                        key = (tgt_mod, orig_name)
                        if key not in visited:
                            visited.add(key)
                            chunks.append(tgt_entry[0])
                            next_frontier.append((tgt_mod, tgt_entry[1]))
                    elif orig_name in shared_helpers:
                        key = ("dependencies", orig_name)
                        if key not in visited:
                            visited.add(key)
                            seg, helper_ast = shared_helpers[orig_name]
                            chunks.append(seg)
                            next_frontier.append(("dependencies", helper_ast))
                elif name in shared_helpers:
                    key = ("dependencies", name)
                    if key not in visited:
                        visited.add(key)
                        seg, helper_ast = shared_helpers[name]
                        chunks.append(seg)
                        next_frontier.append(("dependencies", helper_ast))
        if not next_frontier:
            break
        frontier = next_frontier
    return "\n".join(chunks)


def find_unguarded_workspace_or_run_routes(repo_root: Path) -> list[str]:
    """Return sorted `<rel_path>:<func_name>` for routes lacking a workspace/run guard."""
    api_orcia_dir = repo_root / "apps" / "api" / "src" / "orcia_api"
    routers_dir = api_orcia_dir / "routers"
    if not routers_dir.is_dir():
        return []
    module_helpers, shared_helpers, module_imports, dep_aliases = _collect_router_and_guard_helpers(
        api_orcia_dir, repo_root
    )
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
            combined = _expand_route_and_helper_source(
                rel, node, fn_src, module_helpers, shared_helpers, module_imports, dep_aliases
            )
            if not any(tok in combined for tok in ROUTE_GUARD_TOKENS):
                unguarded.append(f"{rel}:{node.name}")
    return sorted(set(unguarded))


def check_unguarded_routes(repo_root: Path, allowlist: set[str]) -> list[str]:
    """Fail on any unguarded `workspace_id`/`run_id` FastAPI route beyond `allowlist`."""
    current = find_unguarded_workspace_or_run_routes(repo_root)
    return [entry for entry in current if entry not in allowlist]
