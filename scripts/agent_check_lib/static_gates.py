"""Stage 1 static gate builders (Python, TypeScript, architecture spine, secrets)."""

from __future__ import annotations

import json
import shutil
from pathlib import Path

from scripts.agent_check_lib.changes import hash_file_bytes
from scripts.agent_check_lib.env import ToolchainEnv
from scripts.agent_check_lib.runner_exec import CommandResult, run_cmd

TS_PACKAGE_FILTERS: tuple[tuple[str, str], ...] = (
    ("packages/api-client", "@orcia/api-client"),
    ("packages/ui", "@orcia/ui"),
    ("apps/web", "@orcia/web"),
)

SPINE_SCRIPT_REL = ".agent/skills/bmad-architecture/scripts/lint_spine.py"
SPINE_WORKSPACE_REL = "docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24"


def resolve_mypy_targets(repo_root: Path, touched_files: list[str]) -> list[str]:
    """Map touched Python files to mypy `--strict` targets."""
    if "pyproject.toml" in touched_files:
        return [
            p
            for p in (
                "packages/orcia-kernel",
                "packages/orcia-core",
                "packages/orcia-connectors",
                "apps/api",
                "apps/worker",
            )
            if (repo_root / p).is_dir()
        ]
    targets: set[str] = set()
    pkg_roots = (
        "packages/orcia-kernel",
        "packages/orcia-core",
        "packages/orcia-connectors",
        "apps/api",
        "apps/worker",
    )
    for rel in touched_files:
        if not rel.endswith(".py") or not (repo_root / rel).is_file():
            continue
        matched = next((pkg for pkg in pkg_roots if rel.startswith(f"{pkg}/")), None)
        if matched:
            targets.add(matched)
        elif rel.startswith("scripts/"):
            targets.add(rel)
    return sorted(targets)


def resolve_ts_packages(repo_root: Path, touched_files: list[str], *, force_all: bool) -> list[str]:
    """Return workspace package names requiring TS `lint` + `typecheck`."""
    available = [
        (prefix, pkg_name)
        for prefix, pkg_name in TS_PACKAGE_FILTERS
        if (repo_root / prefix / "package.json").is_file()
    ]
    if not available:
        return []
    if force_all or any(
        f in ("package.json", "pnpm-lock.yaml", "turbo.json") for f in touched_files
    ):
        return [pkg_name for _, pkg_name in available]

    selected: list[str] = []
    for prefix, pkg_name in available:
        if any(
            f.startswith(f"{prefix}/")
            and f.endswith((".ts", ".tsx", ".js", ".mjs", ".json", ".css"))
            for f in touched_files
        ):
            selected.append(pkg_name)
    return selected


def build_static_gates(
    env_info: ToolchainEnv,
    *,
    touched_files: list[str],
    no_skip: bool,
) -> tuple[list[tuple[str, list[str]]], list[str]]:
    """Build Stage 1 check-only gates and optional warning messages."""
    root = env_info.repo_root
    warnings: list[str] = []
    gates: list[tuple[str, list[str]]] = [
        ("ruff-check", [str(env_info.ruff_bin), "check", "."]),
        ("ruff-format", [str(env_info.ruff_bin), "format", "--check", "."]),
    ]

    mypy_targets = resolve_mypy_targets(root, touched_files)
    if mypy_targets:
        gates.append(("mypy", [str(env_info.mypy_bin), "--strict", *mypy_targets]))

    gates.append(("lint-imports", [str(env_info.lint_imports_bin)]))

    if (root / "scripts" / "export_openapi.py").is_file():
        gates.append(
            ("openapi-check", [str(env_info.python_bin), "scripts/export_openapi.py", "--check"])
        )

    if (root / "scripts" / "generate_vitest_openapi_mocks.py").is_file():
        gates.append(
            (
                "vitest-openapi-mocks",
                [str(env_info.python_bin), "scripts/generate_vitest_openapi_mocks.py", "--check"],
            )
        )

    if (root / "scripts" / "check_agent_rules.py").is_file():
        gates.append(("rules-lint", [str(env_info.python_bin), "scripts/check_agent_rules.py"]))

    if (root / "scripts" / "generate_test_fixture_index.py").is_file():
        gates.append(
            (
                "fixture-index",
                [str(env_info.python_bin), "scripts/generate_test_fixture_index.py", "--check"],
            )
        )

    if (root / "scripts" / "lint_tests.py").is_file():
        gates.append(("lint-tests", [str(env_info.python_bin), "scripts/lint_tests.py"]))

    for pkg_name in resolve_ts_packages(root, touched_files, force_all=no_skip):
        gates.append((f"ts-lint:{pkg_name}", [env_info.pnpm_bin, "--filter", pkg_name, "lint"]))
        gates.append(
            (f"ts-typecheck:{pkg_name}", [env_info.pnpm_bin, "--filter", pkg_name, "typecheck"])
        )

    spine_script = root / SPINE_SCRIPT_REL
    spine_ws = root / SPINE_WORKSPACE_REL
    if spine_script.is_file() and spine_ws.is_dir():
        gates.append(
            (
                "lint-spine",
                [str(env_info.python_bin), SPINE_SCRIPT_REL, "--workspace", SPINE_WORKSPACE_REL],
            )
        )

    existing_touched = [f for f in touched_files if (root / f).is_file()]
    if existing_touched:
        baseline = root / ".secrets.baseline"
        hook_bin = env_info.venv_dir / "bin" / "detect-secrets-hook"
        if not baseline.is_file():
            warnings.append("WARN [static]: .secrets.baseline absent; skipping detect-secrets-hook")
        elif hook_bin.exists() or shutil.which("detect-secrets-hook"):
            cmd_bin = str(hook_bin) if hook_bin.exists() else "detect-secrets-hook"
            gates.append(
                (
                    "detect-secrets",
                    [cmd_bin, "--baseline", ".secrets.baseline", *existing_touched],
                )
            )

    return gates, warnings


def autofix_touched_python(
    env_info: ToolchainEnv, touched_py: list[str], sub_env: dict[str, str]
) -> list[str]:
    """Run `ruff format` and `ruff check --fix` on touched Python files without unsafe fixes."""
    if not touched_py:
        return []
    root = env_info.repo_root
    before = {rel: hash_file_bytes(root / rel) for rel in touched_py}
    run_cmd([str(env_info.ruff_bin), "format", *touched_py], root, sub_env)
    run_cmd([str(env_info.ruff_bin), "check", "--fix", *touched_py], root, sub_env)
    return [rel for rel in touched_py if hash_file_bytes(root / rel) != before[rel]]


def validate_gate_result(gate_name: str, res: CommandResult) -> CommandResult:
    """Validate structured JSON output for gates whose CLI contract always exits 0."""
    if gate_name != "lint-spine" or res.returncode != 0:
        return res
    try:
        payload = json.loads(res.stdout)
    except json.JSONDecodeError as exc:
        err = res.stderr or f"lint-spine produced invalid JSON output: {exc}"
        return CommandResult(returncode=1, stdout=res.stdout, stderr=err)
    if not isinstance(payload, dict):
        return CommandResult(
            returncode=1,
            stdout=res.stdout,
            stderr=res.stderr or "lint-spine JSON must be an object",
        )
    ok = payload.get("ok") is True
    findings_cnt = int(payload.get("total_findings", 0) or 0)
    if not ok or findings_cnt > 0:
        err = res.stderr or f"lint-spine failed: ok={payload.get('ok')}, findings={findings_cnt}"
        return CommandResult(returncode=1, stdout=res.stdout, stderr=err)
    return res


def run_single_cmd(cmd: list[str], cwd: Path, env: dict[str, str]) -> CommandResult:
    """Thin delegate for Stage 1 execution (easily mockable in tests)."""
    return run_cmd(cmd, cwd, env)
