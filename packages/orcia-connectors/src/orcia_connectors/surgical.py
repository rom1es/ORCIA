"""Concrete `SurgicalContextExplorer` adapter (`Story 16.1`, `CA-16.1.1`, `CA-16.1.2`).

Implements `SurgicalExplorerPort` over authorized workspace/pack/documentation roots
with strict `MAX_SURGICAL_LINES = 250` slicing, `READ_SOURCE` governance, and
Path Traversal + SSRF protection.
"""

from __future__ import annotations

import asyncio
from collections.abc import Callable
from pathlib import Path

import orcia_connectors._error_catalog  # noqa: F401
from orcia_connectors._connectors_locales import get_surgical_copy
from orcia_connectors._surgical_fs_helpers import (
    collect_searchable_files,
    detect_default_repo_root,
    is_within_allowed_roots,
    resolve_pack_uri_content,
)
from orcia_connectors._surgical_observations import (
    DEFAULT_READ_SOURCE_HINT,
    build_check_state_observation,
    build_inspect_lines_observation,
    build_outline_observation,
    build_redacted_observation,
    match_file_snippets,
)
from orcia_connectors._surgical_parsers import (
    extract_display_filename,
    extract_outline_nodes,
    resolve_file_badge_code,
    validate_surgical_uri_security,
)
from orcia_core.kernel.enums import DEFAULT_LOCALE
from orcia_core.kernel.errors import ValidationDomainError
from orcia_core.ports.surgical_explorer_port import (
    SurgicalExplorerPort,
    SurgicalObservation,
    SurgicalPrimitiveName,
    SurgicalSnippetMatch,
)

ReadSourceAuthorizer = Callable[[str, str | None, str | None], tuple[bool, str | None]]
VirtualResourceResolver = Callable[[str, str | None], str | None]

_DEFAULT_ALLOWED_SUBDIRS: tuple[str, ...] = ("packs", "docs", "specs")


class SurgicalContextExplorer(SurgicalExplorerPort):
    """Governed read-only adapter executing the 4 surgical exploration primitives."""

    def __init__(
        self,
        *,
        repo_root: Path | None = None,
        allowed_subdirs: tuple[str, ...] = _DEFAULT_ALLOWED_SUBDIRS,
        read_source_authorizer: ReadSourceAuthorizer | None = None,
        virtual_resource_resolver: VirtualResourceResolver | None = None,
    ) -> None:
        self._repo_root = (repo_root or detect_default_repo_root(Path(__file__))).resolve()
        self._allowed_subdirs = allowed_subdirs
        self._read_source_authorizer = read_source_authorizer
        self._virtual_resource_resolver = virtual_resource_resolver

    def _is_within_allowed_roots(self, candidate: Path) -> bool:
        return is_within_allowed_roots(candidate, self._repo_root, self._allowed_subdirs)

    def _evaluate_read_source(
        self,
        uri: str,
        *,
        workspace_id: str | None,
        actor_id: str | None,
        has_read_source: bool,
    ) -> tuple[bool, str | None]:
        if not has_read_source:
            return False, DEFAULT_READ_SOURCE_HINT
        if self._read_source_authorizer is not None:
            allowed, hint = self._read_source_authorizer(uri, workspace_id, actor_id)
            if not allowed:
                return False, hint or DEFAULT_READ_SOURCE_HINT
        return True, None

    def _resolve_target_content(
        self, cleaned_uri: str, *, workspace_id: str | None
    ) -> tuple[bool, str]:
        """Return `(exists, utf8_text)` for an authorized relative or virtual URI."""
        if self._virtual_resource_resolver is not None:
            virtual_text = self._virtual_resource_resolver(cleaned_uri, workspace_id)
            if virtual_text is not None:
                return True, virtual_text

        if "://" in cleaned_uri:
            scheme, rest = cleaned_uri.split("://", 1)
            if scheme.lower() == "pack":
                return resolve_pack_uri_content(self._repo_root, rest)
            return False, ""

        raw_path = Path(cleaned_uri)
        candidate = (
            raw_path.resolve() if raw_path.is_absolute() else (self._repo_root / raw_path).resolve()
        )
        if not self._is_within_allowed_roots(candidate):
            raise ValidationDomainError(
                detail_code="ERR_SURGICAL_PATH_OUT_OF_BOUNDS",
                detail_params={"uri": cleaned_uri, "roots": ", ".join(self._allowed_subdirs)},
            )
        if not candidate.exists() or not candidate.is_file():
            return False, ""
        return True, candidate.read_text(encoding="utf-8", errors="replace")

    async def execute_primitive(
        self,
        primitive: SurgicalPrimitiveName,
        *,
        resource_uri: str = "",
        query: str = "",
        start_line: int = 1,
        end_line: int = 200,
        max_results: int = 20,
        workspace_id: str | None = None,
        actor_id: str | None = None,
        has_read_source: bool = True,
    ) -> SurgicalObservation:
        """Execute one of the 4 read-only surgical exploration primitives."""
        if primitive == SurgicalPrimitiveName.INSPECT_RESOURCE_LINES:
            return await self.inspect_lines(
                resource_uri,
                start_line=start_line,
                end_line=end_line,
                workspace_id=workspace_id,
                actor_id=actor_id,
                has_read_source=has_read_source,
            )
        if primitive == SurgicalPrimitiveName.SEARCH_WORKSPACE_SNIPPETS:
            return await asyncio.to_thread(
                self._search_snippets_sync,
                resource_uri=resource_uri,
                query=query,
                max_results=max_results,
                workspace_id=workspace_id,
                actor_id=actor_id,
                has_read_source=has_read_source,
            )
        cleaned_uri = validate_surgical_uri_security(resource_uri)
        allowed, hint = self._evaluate_read_source(
            cleaned_uri,
            workspace_id=workspace_id,
            actor_id=actor_id,
            has_read_source=has_read_source,
        )
        if not allowed:
            return build_redacted_observation(primitive, cleaned_uri, hint)

        if primitive == SurgicalPrimitiveName.CHECK_RESOURCE_STATE:
            return await asyncio.to_thread(
                self._check_state_sync, cleaned_uri, workspace_id=workspace_id
            )
        if primitive == SurgicalPrimitiveName.OUTLINE_RESOURCE_STRUCTURE:
            return await asyncio.to_thread(
                self._outline_sync, cleaned_uri, workspace_id=workspace_id
            )
        raise ValidationDomainError(
            detail_code="ERR_SURGICAL_UNKNOWN_PRIMITIVE",
            detail_params={"primitive": str(primitive)},
        )

    async def inspect_lines(
        self,
        resource_uri: str,
        *,
        start_line: int = 1,
        end_line: int = 200,
        workspace_id: str | None = None,
        actor_id: str | None = None,
        has_read_source: bool = True,
    ) -> SurgicalObservation:
        """Read a 1-indexed inclusive slice strictly capped at `MAX_SURGICAL_LINES` (`250`)."""
        cleaned_uri = validate_surgical_uri_security(resource_uri)
        if start_line < 1 or end_line < start_line:
            raise ValidationDomainError(
                detail_code="ERR_SURGICAL_INVALID_LINE_RANGE",
                detail_params={"start_line": start_line, "end_line": end_line},
            )
        allowed, hint = self._evaluate_read_source(
            cleaned_uri,
            workspace_id=workspace_id,
            actor_id=actor_id,
            has_read_source=has_read_source,
        )
        if not allowed:
            return build_redacted_observation(
                SurgicalPrimitiveName.INSPECT_RESOURCE_LINES, cleaned_uri, hint
            )
        return await asyncio.to_thread(
            self._inspect_lines_sync,
            cleaned_uri,
            start_line=start_line,
            end_line=end_line,
            workspace_id=workspace_id,
        )

    def _check_state_sync(
        self, cleaned_uri: str, *, workspace_id: str | None
    ) -> SurgicalObservation:
        exists, text = self._resolve_target_content(cleaned_uri, workspace_id=workspace_id)
        return build_check_state_observation(cleaned_uri, exists=exists, text=text)

    def _outline_sync(self, cleaned_uri: str, *, workspace_id: str | None) -> SurgicalObservation:
        exists, text = self._resolve_target_content(cleaned_uri, workspace_id=workspace_id)
        return build_outline_observation(cleaned_uri, exists=exists, text=text)

    def _inspect_lines_sync(
        self,
        cleaned_uri: str,
        *,
        start_line: int,
        end_line: int,
        workspace_id: str | None,
    ) -> SurgicalObservation:
        exists, text = self._resolve_target_content(cleaned_uri, workspace_id=workspace_id)
        return build_inspect_lines_observation(
            cleaned_uri,
            exists=exists,
            text=text,
            start_line=start_line,
            end_line=end_line,
        )

    def _search_snippets_sync(
        self,
        *,
        resource_uri: str,
        query: str,
        max_results: int,
        workspace_id: str | None,
        actor_id: str | None,
        has_read_source: bool,
    ) -> SurgicalObservation:
        cleaned_scope = validate_surgical_uri_security(resource_uri, allow_empty=True)
        needle = query.strip().lower()
        if not needle or len(needle) > 256:
            raise ValidationDomainError(detail_code="ERR_SURGICAL_INVALID_QUERY")
        scope_label = cleaned_scope or "workspace"
        if not has_read_source:
            return build_redacted_observation(
                SurgicalPrimitiveName.SEARCH_WORKSPACE_SNIPPETS, scope_label, None
            )

        bounded_max = max(1, min(max_results, 50))
        files_to_scan = collect_searchable_files(
            self._repo_root, self._allowed_subdirs, cleaned_scope
        )
        matches: list[SurgicalSnippetMatch] = []

        for file_path in files_to_scan:
            rel_uri = file_path.relative_to(self._repo_root).as_posix()
            allowed, _ = self._evaluate_read_source(
                rel_uri,
                workspace_id=workspace_id,
                actor_id=actor_id,
                has_read_source=has_read_source,
            )
            if not allowed:
                continue
            file_lines = file_path.read_text(encoding="utf-8", errors="replace").splitlines()
            matches.extend(
                match_file_snippets(
                    rel_uri=rel_uri,
                    file_name=file_path.name,
                    file_lines=file_lines,
                    needle=needle,
                    remaining=bounded_max - len(matches),
                )
            )
            if len(matches) >= bounded_max:
                break

        copy = get_surgical_copy(DEFAULT_LOCALE)
        return SurgicalObservation(
            kind=SurgicalPrimitiveName.SEARCH_WORKSPACE_SNIPPETS,
            resource_uri=scope_label,
            display_filename=extract_display_filename(scope_label),
            file_badge_code=resolve_file_badge_code(scope_label),
            formatted_badge=f"Searched '{query.strip()}' ({len(matches)} matches)",
            exists=True,
            snippets=matches,
            summary=copy.search_matches_summary.format(count=len(matches), query=query.strip()),
        )


__all__ = [
    "SurgicalContextExplorer",
    "extract_outline_nodes",
    "resolve_file_badge_code",
    "validate_surgical_uri_security",
]
