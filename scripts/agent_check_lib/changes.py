"""Git change detection and deterministic file snapshotting."""

from __future__ import annotations

import hashlib
import subprocess
from pathlib import Path


def _run_git(repo_root: Path, args: list[str]) -> str:
    proc = subprocess.run(
        ["git", *args],
        cwd=repo_root,
        capture_output=True,
        text=True,
        check=False,
    )
    return proc.stdout if proc.returncode == 0 else ""


def detect_changed_files(repo_root: Path) -> list[str]:
    """Return sorted repo-relative paths of modified/staged/untracked non-ignored files."""
    seen: set[str] = set()

    has_head = (
        subprocess.run(
            ["git", "rev-parse", "--verify", "HEAD"],
            cwd=repo_root,
            capture_output=True,
            check=False,
        ).returncode
        == 0
    )

    if has_head:
        diff_head = _run_git(repo_root, ["diff", "--name-only", "HEAD"])
        for line in diff_head.splitlines():
            cleaned = line.strip()
            if cleaned:
                seen.add(cleaned)
    else:
        cached = _run_git(repo_root, ["diff", "--cached", "--name-only"])
        unstaged = _run_git(repo_root, ["diff", "--name-only"])
        for line in (cached + "\n" + unstaged).splitlines():
            cleaned = line.strip()
            if cleaned:
                seen.add(cleaned)

    untracked = _run_git(repo_root, ["ls-files", "--others", "--exclude-standard"])
    for line in untracked.splitlines():
        cleaned = line.strip()
        if cleaned and not cleaned.startswith(".agent_check/"):
            seen.add(cleaned)

    return sorted(seen)


def normalize_file_args(repo_root: Path, raw_files: list[str] | None) -> list[str]:
    """Normalize CLI `--files` arguments into sorted repo-relative paths."""
    if not raw_files:
        return detect_changed_files(repo_root)
    normalized: set[str] = set()
    root_resolved = repo_root.resolve()
    for item in raw_files:
        for part in item.split(","):
            trimmed = part.strip()
            if not trimmed:
                continue
            candidate = Path(trimmed)
            if candidate.is_absolute():
                try:
                    rel = candidate.resolve().relative_to(root_resolved).as_posix()
                except ValueError:
                    rel = trimmed
            else:
                rel = trimmed.lstrip("./")
            normalized.add(rel)
    return sorted(normalized)


def hash_file_bytes(path: Path) -> str:
    """Return SHA-256 hex digest of a file, or `'DELETED'` if absent."""
    if not path.is_file():
        return "DELETED"
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        while chunk := handle.read(65536):
            hasher.update(chunk)
    return hasher.hexdigest()


def snapshot_dirty_hashes(repo_root: Path) -> tuple[str, dict[str, str], dict[str, str]]:
    """Capture `(head_sha, non_docs_hashes, docs_hashes)` for bounce evaluation."""
    head_sha = _run_git(repo_root, ["rev-parse", "HEAD"]).strip() or "NO_HEAD"
    changed = detect_changed_files(repo_root)
    non_docs: dict[str, str] = {}
    docs: dict[str, str] = {}
    for rel in changed:
        digest = hash_file_bytes(repo_root / rel)
        if rel.startswith("docs/"):
            docs[rel] = digest
        else:
            non_docs[rel] = digest
    return head_sha, non_docs, docs
