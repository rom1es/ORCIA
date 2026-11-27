"""Canonical shared unit-test app, lifespan, and cached repo AST/file index helpers."""

from __future__ import annotations

import ast
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI

from orcia_api.main import create_app
from orcia_core.packs import ApmPackCodec
from orcia_core.packs.models import LoadedPackBundleV2
from orcia_core.workflows import SqlVsmDefinitionsV2Store, SqlWorkflowDefinitionsV2Store

_REPO_ROOT = Path(__file__).resolve().parents[3]
_IGNORED_PARTS: frozenset[str] = frozenset({".venv", "__pycache__", "node_modules", ".git"})


@lru_cache(maxsize=1)
def _cached_sdlc_bundle() -> LoadedPackBundleV2:
    return ApmPackCodec().decode_directory(_REPO_ROOT / "packs" / "sdlc")


def create_seeded_test_app() -> FastAPI:
    """Return a real `create_app()` instance with SDLC workflows & VSMs pre-seeded in RAM stores."""
    app = create_app()
    bundle = _cached_sdlc_bundle()
    wf_store = SqlWorkflowDefinitionsV2Store(strict_sql=False)
    for wf in bundle.workflows:
        wf_store._memory_fallback[f"{wf.id}:{wf.version}"] = wf.model_dump(mode="json")
    vsm_store = SqlVsmDefinitionsV2Store(strict_sql=False)
    for vsm in bundle.vsm_specs:
        vsm_store._memory_fallback[vsm.id] = vsm.model_dump(mode="json")
    app.state.workflows_v2_sql_store = wf_store
    app.state.vsm_v2_sql_store = vsm_store
    return app


@asynccontextmanager
async def run_with_lifespan(app: FastAPI) -> AsyncIterator[FastAPI]:
    """Run FastAPI's real `lifespan_context` around `app` and yield it cleanly."""
    async with app.router.lifespan_context(app):
        yield app


class RepoSourceIndex:
    """Cached per-process repository `.py` file walker, source reader, and AST parser."""

    def __init__(self, repo_root: Path) -> None:
        self.repo_root = repo_root.resolve()
        self._text_cache: dict[Path, str] = {}
        self._ast_cache: dict[Path, ast.Module] = {}
        self._dir_files_cache: dict[tuple[str, str], tuple[Path, ...]] = {}

    def files_under(self, rel_dir: str, *, suffix: str = ".py") -> tuple[Path, ...]:
        """Return cached sorted file paths under `rel_dir` matching `suffix`."""
        key = (rel_dir.strip("/"), suffix)
        cached = self._dir_files_cache.get(key)
        if cached is not None:
            return cached
        target = (self.repo_root / key[0]).resolve()
        if not target.is_dir():
            self._dir_files_cache[key] = ()
            return ()
        items = tuple(
            p
            for p in sorted(target.rglob(f"*{suffix}"))
            if p.is_file() and not any(part in _IGNORED_PARTS for part in p.parts)
        )
        self._dir_files_cache[key] = items
        return items

    def files_under_many(
        self, rel_dirs: tuple[str, ...], *, suffix: str = ".py"
    ) -> tuple[Path, ...]:
        """Return deduplicated sorted files across multiple repository-relative directories."""
        seen: dict[Path, None] = {}
        for rel_dir in rel_dirs:
            for path in self.files_under(rel_dir, suffix=suffix):
                seen[path] = None
        return tuple(sorted(seen))

    def read_text(self, path: Path) -> str:
        """Read and cache UTF-8 file text."""
        resolved = path.resolve()
        cached = self._text_cache.get(resolved)
        if cached is not None:
            return cached
        text = resolved.read_text(encoding="utf-8")
        self._text_cache[resolved] = text
        return text

    def parse_ast(self, path: Path) -> ast.Module:
        """Parse and cache AST module for `path`."""
        resolved = path.resolve()
        cached = self._ast_cache.get(resolved)
        if cached is not None:
            return cached
        rel = resolved.relative_to(self.repo_root)
        tree = ast.parse(self.read_text(resolved), filename=str(rel))
        self._ast_cache[resolved] = tree
        return tree


@lru_cache(maxsize=4)
def get_repo_source_index(repo_root: Path | None = None) -> RepoSourceIndex:
    """Return a cached `RepoSourceIndex` singleton for `repo_root`."""
    return RepoSourceIndex(repo_root or _REPO_ROOT)
