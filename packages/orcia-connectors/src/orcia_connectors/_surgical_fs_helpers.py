"""Filesystem confinement & searchable file discovery helpers for `surgical.py`."""

from __future__ import annotations

from pathlib import Path

from orcia_core.kernel.errors import ValidationDomainError

SEARCHABLE_SUFFIXES: frozenset[str] = frozenset(
    {".md", ".mdx", ".yaml", ".yml", ".json", ".py", ".ts", ".tsx", ".sql", ".txt", ".star"}
)


def detect_default_repo_root(anchor: Path) -> Path:
    """Locate repository root containing `packs/` and `docs/` directories."""
    curr = anchor.resolve()
    for parent in curr.parents:
        if (parent / "packs").is_dir() and (parent / "docs").is_dir():
            return parent
    return Path.cwd()


def allowed_root_paths(repo_root: Path, allowed_subdirs: tuple[str, ...]) -> tuple[Path, ...]:
    """Return resolved root directories allowed for surgical exploration."""
    return tuple((repo_root / sub).resolve() for sub in allowed_subdirs)


def is_within_allowed_roots(
    candidate: Path, repo_root: Path, allowed_subdirs: tuple[str, ...]
) -> bool:
    """Return True if `candidate` resolves inside one of the authorized root folders."""
    resolved = candidate.resolve()
    return any(
        resolved == root or resolved.is_relative_to(root)
        for root in allowed_root_paths(repo_root, allowed_subdirs)
    )


def resolve_pack_uri_content(repo_root: Path, rest: str) -> tuple[bool, str]:
    """Resolve `pack://` virtual URI safely within `repo_root/packs`."""
    rel_tail = rest.strip("/")
    base_packs = (repo_root / "packs").resolve()
    candidates = [
        (base_packs / rel_tail).resolve(),
        (base_packs / f"{rel_tail}.md").resolve(),
        (base_packs / f"{rel_tail}.yaml").resolve(),
    ]
    for cand in candidates:
        if not cand.is_relative_to(base_packs):
            raise ValidationDomainError(detail_code="ERR_SURGICAL_PACK_URI_OUT_OF_BOUNDS")
        if cand.is_file():
            return True, cand.read_text(encoding="utf-8", errors="replace")
    return False, ""


def collect_searchable_files(
    repo_root: Path, allowed_subdirs: tuple[str, ...], cleaned_scope: str
) -> list[Path]:
    """Return sorted searchable files within `cleaned_scope` or all authorized roots."""
    if cleaned_scope:
        target = (repo_root / cleaned_scope).resolve()
        if not is_within_allowed_roots(target, repo_root, allowed_subdirs):
            raise ValidationDomainError(
                detail_code="ERR_SURGICAL_SEARCH_SCOPE_DENIED",
                detail_params={"scope": cleaned_scope},
            )
        if target.is_file():
            return [target]
        if target.is_dir():
            return sorted(
                p
                for p in target.rglob("*")
                if p.is_file() and p.suffix.lower() in SEARCHABLE_SUFFIXES
            )
        return []

    collected: list[Path] = []
    for root in allowed_root_paths(repo_root, allowed_subdirs):
        if root.is_dir():
            collected.extend(
                sorted(
                    p
                    for p in root.rglob("*")
                    if p.is_file() and p.suffix.lower() in SEARCHABLE_SUFFIXES
                )
            )
    return collected
