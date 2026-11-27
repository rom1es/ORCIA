"""Deterministic worktree receipts and bounce-rule state management."""

from __future__ import annotations

import hashlib
import json
import os
import platform
import subprocess
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

from scripts.agent_check_lib.changes import (
    detect_changed_files,
    hash_file_bytes,
    snapshot_dirty_hashes,
)
from scripts.agent_check_lib.env import ToolchainEnv

SKIPPABLE_STAGES: frozenset[str] = frozenset({"static", "full-unit", "full-vitest"})


class BounceDecision(StrEnum):
    """Action selected by the bounce rule when a previous failing check exists."""

    NONE = "none"
    ONLY_FAILED_CHECK = "only_failed_check"
    STAGE1_STAGE2_AND_FAILED = "stage1_stage2_and_failed"


@dataclass(frozen=True, slots=True)
class BouncePlan:
    """Planned re-run action based on changes since the last failure."""

    mode: BounceDecision
    failed_check: str | None = None
    failed_tests: tuple[str, ...] = ()
    stage: str | None = None


def _git_tracked_blob_index(repo_root: Path) -> str:
    proc = subprocess.run(
        ["git", "ls-files", "--stage"],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.stdout if proc.returncode == 0 else ""


def _venv_dist_digest(venv_dir: Path) -> str:
    hasher = hashlib.sha256()
    resolved_venv = venv_dir.resolve()
    dist_dirs = sorted(resolved_venv.glob("lib/python*/site-packages/*.dist-info"))
    for dist_dir in dist_dirs:
        hasher.update(dist_dir.name.encode("utf-8"))
        meta = dist_dir / "METADATA"
        if meta.is_file():
            for line in meta.read_text(encoding="utf-8", errors="replace").splitlines()[:20]:
                if line.startswith(("Name:", "Version:")):
                    hasher.update(line.encode("utf-8"))
        hasher.update(b"\n")
    return hasher.hexdigest()


def _runner_source_digest(repo_root: Path) -> str:
    hasher = hashlib.sha256()
    runner_files: list[Path] = []
    scripts_dir = repo_root / "scripts"
    if scripts_dir.is_dir():
        runner_files.extend(sorted(scripts_dir.glob("*.py")))
    lib_dir = scripts_dir / "agent_check_lib"
    if lib_dir.is_dir():
        runner_files.extend(sorted(lib_dir.glob("*.py")))
    for path in runner_files:
        rel = path.relative_to(repo_root).as_posix()
        hasher.update(rel.encode("utf-8"))
        hasher.update(b"\0")
        hasher.update(path.read_bytes())
        hasher.update(b"\0")
    return hasher.hexdigest()


def _resolve_node_version(node_bin: str) -> str:
    proc = subprocess.run([node_bin, "--version"], capture_output=True, text=True, check=False)
    return proc.stdout.strip() if proc.returncode == 0 else "unknown"


def compute_worktree_digest(
    repo_root: Path,
    env_info: ToolchainEnv,
    *,
    node_version: str | None = None,
) -> str:
    """Compute a deterministic SHA-256 digest of code, dirty files, toolchain, and ORCIA_* env."""
    hasher = hashlib.sha256()

    # 1. Tracked git blob index
    hasher.update(b"TRACKED\0")
    hasher.update(_git_tracked_blob_index(repo_root).encode("utf-8"))

    # 2. Modified and untracked non-ignored file contents
    hasher.update(b"\0DIRTY\0")
    for rel in detect_changed_files(repo_root):
        hasher.update(rel.encode("utf-8"))
        hasher.update(b"\0")
        hasher.update(hash_file_bytes(repo_root / rel).encode("utf-8"))
        hasher.update(b"\0")

    # 3. .venv installed distribution digest
    hasher.update(b"VENV\0")
    hasher.update(_venv_dist_digest(env_info.venv_dir).encode("utf-8"))

    # 4. pnpm-lock.yaml hash
    hasher.update(b"\0PNPM\0")
    hasher.update(hash_file_bytes(repo_root / "pnpm-lock.yaml").encode("utf-8"))

    # 5. Python & Node versions
    hasher.update(b"\0VERSIONS\0")
    resolved_node = node_version or _resolve_node_version(env_info.node_bin)
    hasher.update(f"py={platform.python_version()}|node={resolved_node}".encode())

    # 6. Sorted ORCIA_* env vars (hashed, never persisted raw) and PYTHONPATH
    hasher.update(b"\0ENV\0")
    orcia_hash = hashlib.sha256()
    for key in sorted(k for k in os.environ if k.startswith("ORCIA_")):
        orcia_hash.update(f"{key}={os.environ[key]}\n".encode())
    hasher.update(orcia_hash.hexdigest().encode("utf-8"))
    hasher.update(b"\0PYTHONPATH\0")
    hasher.update(env_info.pythonpath.encode("utf-8"))

    # 7. Runner source hash
    hasher.update(b"\0RUNNER\0")
    hasher.update(_runner_source_digest(repo_root).encode("utf-8"))

    return hasher.hexdigest()


def receipt_path_for(repo_root: Path, stage: str, digest: str) -> Path:
    """Return receipt path `.agent_check/receipts/<stage>-<digest>.json`."""
    return repo_root / ".agent_check" / "receipts" / f"{stage}-{digest}.json"


def has_matching_receipt(repo_root: Path, stage: str, digest: str) -> bool:
    """Return True if a deterministic receipt exists for `(stage, digest)`."""
    if stage not in SKIPPABLE_STAGES:
        return False
    return receipt_path_for(repo_root, stage, digest).is_file()


def write_receipt(repo_root: Path, stage: str, digest: str, *, summary: str) -> Path:
    """Persist a deterministic receipt JSON without storing raw env values."""
    target = receipt_path_for(repo_root, stage, digest)
    target.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "stage": stage,
        "digest": digest,
        "summary": summary,
    }
    target.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return target


def _failure_state_path(repo_root: Path) -> Path:
    return repo_root / ".agent_check" / "state" / "last_failure.json"


def record_failure_state(
    repo_root: Path,
    *,
    stage: str,
    failed_check: str,
    failed_tests: list[str],
) -> Path:
    """Persist last failure snapshot for the bounce rule."""
    head_sha, non_docs_hashes, docs_hashes = snapshot_dirty_hashes(repo_root)
    state_path = _failure_state_path(repo_root)
    state_path.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "stage": stage,
        "failed_check": failed_check,
        "failed_tests": failed_tests,
        "head_sha": head_sha,
        "non_docs_hashes": non_docs_hashes,
        "docs_hashes": docs_hashes,
    }
    state_path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    return state_path


def clear_failure_state(repo_root: Path) -> None:
    """Remove recorded failure state once the failing check passes."""
    state_path = _failure_state_path(repo_root)
    if state_path.is_file():
        state_path.unlink()


def evaluate_bounce_rule(repo_root: Path) -> BouncePlan:
    """Decide whether a re-run may run only the failed check or must re-run Stage 1+2+failed."""
    state_path = _failure_state_path(repo_root)
    if not state_path.is_file():
        return BouncePlan(mode=BounceDecision.NONE)
    try:
        data = json.loads(state_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return BouncePlan(mode=BounceDecision.NONE)

    head_sha, non_docs_now, _docs_now = snapshot_dirty_hashes(repo_root)
    non_docs_prev = data.get("non_docs_hashes", {})
    prev_head = data.get("head_sha", "")
    failed_check = str(data.get("failed_check", ""))
    failed_tests = tuple(str(t) for t in data.get("failed_tests", []))
    stage = str(data.get("stage", ""))

    if not failed_check:
        return BouncePlan(mode=BounceDecision.NONE)

    if head_sha == prev_head and non_docs_now == non_docs_prev:
        return BouncePlan(
            mode=BounceDecision.ONLY_FAILED_CHECK,
            failed_check=failed_check,
            failed_tests=failed_tests,
            stage=stage,
        )
    return BouncePlan(
        mode=BounceDecision.STAGE1_STAGE2_AND_FAILED,
        failed_check=failed_check,
        failed_tests=failed_tests,
        stage=stage,
    )
