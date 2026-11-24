"""Pure `SurgicalObservation` builders for `SurgicalContextExplorer` (`Story 16.1`)."""

from __future__ import annotations

import hashlib

import orcia_connectors._error_catalog  # noqa: F401
from orcia_connectors._connectors_locales import get_surgical_copy
from orcia_connectors._surgical_parsers import (
    extract_display_filename,
    extract_outline_nodes,
    resolve_file_badge_code,
)
from orcia_core.kernel.enums import DEFAULT_LOCALE, SupportedLocale
from orcia_core.kernel.errors import ResourceNotFoundError
from orcia_core.ports.surgical_explorer_port import (
    MAX_SURGICAL_LINES,
    SurgicalLineEntry,
    SurgicalObservation,
    SurgicalPrimitiveName,
    SurgicalSnippetMatch,
)

DEFAULT_READ_SOURCE_HINT = get_surgical_copy(DEFAULT_LOCALE).default_read_source_hint


def build_redacted_observation(
    kind: SurgicalPrimitiveName,
    uri: str,
    hint: str | None,
    *,
    locale: SupportedLocale = DEFAULT_LOCALE,
) -> SurgicalObservation:
    """Build a zero-raw-content masked observation when `READ_SOURCE` is missing."""
    copy = get_surgical_copy(locale)
    filename = extract_display_filename(uri)
    badge = resolve_file_badge_code(uri)
    return SurgicalObservation(
        kind=kind,
        resource_uri=uri,
        display_filename=filename,
        file_badge_code=badge,
        formatted_badge=f"Protected {badge} {filename}",
        exists=True,
        total_lines=0,
        lines=[],
        outline=[],
        snippets=[],
        summary=copy.redacted_summary,
        sha256=None,
        redacted=True,
        redacted_reason="READ_SOURCE_REQUIRED",
        permission_request_hint=hint or copy.default_read_source_hint,
    )


def build_check_state_observation(
    cleaned_uri: str,
    *,
    exists: bool,
    text: str,
    locale: SupportedLocale = DEFAULT_LOCALE,
) -> SurgicalObservation:
    """Build `check_resource_state` metadata observation without leaking file lines."""
    copy = get_surgical_copy(locale)
    filename = extract_display_filename(cleaned_uri)
    badge = resolve_file_badge_code(cleaned_uri)
    if not exists:
        return SurgicalObservation(
            kind=SurgicalPrimitiveName.CHECK_RESOURCE_STATE,
            resource_uri=cleaned_uri,
            display_filename=filename,
            file_badge_code=badge,
            formatted_badge=f"Checked {badge} {filename} (absent)",
            exists=False,
            total_lines=0,
            check_label=copy.check_missing_label.format(filename=filename),
            summary=copy.check_missing_summary.format(filename=filename),
            sha256=None,
        )
    total_lines = len(text.splitlines())
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    return SurgicalObservation(
        kind=SurgicalPrimitiveName.CHECK_RESOURCE_STATE,
        resource_uri=cleaned_uri,
        display_filename=filename,
        file_badge_code=badge,
        formatted_badge=f"Checked {badge} {filename} ({total_lines} lines)",
        exists=True,
        total_lines=total_lines,
        check_label=copy.check_ok_label.format(filename=filename, total_lines=total_lines),
        summary=copy.check_ok_summary.format(filename=filename, total_lines=total_lines),
        sha256=digest,
    )


def build_outline_observation(
    cleaned_uri: str,
    *,
    exists: bool,
    text: str,
    locale: SupportedLocale = DEFAULT_LOCALE,
) -> SurgicalObservation:
    """Build `outline_resource_structure` observation with structural line-anchored nodes."""
    if not exists:
        raise ResourceNotFoundError(
            detail_code="ERR_SURGICAL_RESOURCE_NOT_FOUND",
            detail_params={"uri": cleaned_uri},
        )
    copy = get_surgical_copy(locale)
    filename = extract_display_filename(cleaned_uri)
    badge = resolve_file_badge_code(cleaned_uri)
    total_lines = len(text.splitlines())
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()
    nodes = extract_outline_nodes(text, cleaned_uri)
    return SurgicalObservation(
        kind=SurgicalPrimitiveName.OUTLINE_RESOURCE_STRUCTURE,
        resource_uri=cleaned_uri,
        display_filename=filename,
        file_badge_code=badge,
        formatted_badge=f"Outlined {badge} {filename} ({len(nodes)} entries)",
        exists=True,
        total_lines=total_lines,
        outline=nodes,
        summary=copy.outline_summary.format(
            filename=filename, node_count=len(nodes), total_lines=total_lines
        ),
        sha256=digest,
    )


def build_inspect_lines_observation(
    cleaned_uri: str,
    *,
    exists: bool,
    text: str,
    start_line: int,
    end_line: int,
    locale: SupportedLocale = DEFAULT_LOCALE,
) -> SurgicalObservation:
    """Build `inspect_resource_lines` observation capped at `MAX_SURGICAL_LINES` (`250`)."""
    if not exists:
        raise ResourceNotFoundError(
            detail_code="ERR_SURGICAL_RESOURCE_NOT_FOUND",
            detail_params={"uri": cleaned_uri},
        )
    copy = get_surgical_copy(locale)
    filename = extract_display_filename(cleaned_uri)
    badge = resolve_file_badge_code(cleaned_uri)
    all_lines = text.splitlines()
    total_lines = len(all_lines)
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()

    if total_lines == 0 or start_line > total_lines:
        eff_start = min(start_line, max(1, total_lines))
        return SurgicalObservation(
            kind=SurgicalPrimitiveName.INSPECT_RESOURCE_LINES,
            resource_uri=cleaned_uri,
            display_filename=filename,
            file_badge_code=badge,
            formatted_badge=f"Analyzed {badge} {filename} #L{eff_start}-{eff_start}",
            exists=True,
            start_line=eff_start,
            end_line=eff_start,
            total_lines=total_lines,
            lines=[],
            summary=copy.inspect_empty_summary.format(filename=filename, total_lines=total_lines),
            sha256=digest,
        )

    capped_end = min(end_line, start_line + MAX_SURGICAL_LINES - 1, total_lines)
    sliced = [
        SurgicalLineEntry(line_number=idx, content=all_lines[idx - 1])
        for idx in range(start_line, capped_end + 1)
    ]
    return SurgicalObservation(
        kind=SurgicalPrimitiveName.INSPECT_RESOURCE_LINES,
        resource_uri=cleaned_uri,
        display_filename=filename,
        file_badge_code=badge,
        formatted_badge=f"Analyzed {badge} {filename} #L{start_line}-{capped_end}",
        exists=True,
        start_line=start_line,
        end_line=capped_end,
        total_lines=total_lines,
        lines=sliced,
        summary=copy.inspect_lines_summary.format(
            count=len(sliced),
            filename=filename,
            start_line=start_line,
            end_line=capped_end,
        ),
        sha256=digest,
    )


def match_file_snippets(
    *,
    rel_uri: str,
    file_name: str,
    file_lines: list[str],
    needle: str,
    remaining: int,
) -> list[SurgicalSnippetMatch]:
    """Return up to `remaining` 3-line contextual matches within `file_lines`."""
    total = len(file_lines)
    badge = resolve_file_badge_code(file_name)
    found: list[SurgicalSnippetMatch] = []
    for idx, line_text in enumerate(file_lines, start=1):
        if needle in line_text.lower():
            s_start = max(1, idx - 1)
            s_end = min(total, idx + 1)
            excerpt = "\n".join(f"{ln}: {file_lines[ln - 1]}" for ln in range(s_start, s_end + 1))
            found.append(
                SurgicalSnippetMatch(
                    resource_uri=rel_uri,
                    display_filename=file_name,
                    file_badge_code=badge,
                    start_line=s_start,
                    end_line=s_end,
                    line_anchor=f"#L{s_start}-{s_end}",
                    excerpt=excerpt,
                )
            )
            if len(found) >= remaining:
                break
    return found
