"""Unit tests for Story 16.1 — `SurgicalExplorerPort` & `SurgicalContextExplorer`.

Covers:
- Protocol conformance (`isinstance(explorer, SurgicalExplorerPort)`) & strict Pydantic models
- 4 surgical primitives (`check_resource_state`, `outline_resource_structure`,
  `search_workspace_snippets`, `inspect_resource_lines`)
- Strict `MAX_SURGICAL_LINES = 250` cap and normalized badges (`M↓`, `Y`, `TS`, `PY`, `JSON`,
  `SQL`, `DOC`) + `formatted_badge`
- `READ_SOURCE` governance (`redacted=True`, `redacted_reason="READ_SOURCE_REQUIRED"`, `0` leaks)
- Path Traversal & SSRF rejections (`ValidationDomainError` / `PolicyDeniedError`)
"""

from __future__ import annotations

import hashlib
from pathlib import Path

import pytest
from pydantic import ValidationError

from orcia_connectors.surgical import SurgicalContextExplorer
from orcia_core.kernel.errors import PolicyDeniedError, ResourceNotFoundError, ValidationDomainError
from orcia_core.ports import (
    MAX_SURGICAL_LINES,
    SurgicalExplorerPort,
    SurgicalLineEntry,
    SurgicalObservation,
    SurgicalOutlineNode,
    SurgicalPrimitiveName,
    SurgicalSnippetMatch,
)


def _seed_sample_workspace(root: Path) -> Path:
    packs_dir = root / "packs" / "demo"
    docs_dir = root / "docs"
    packs_dir.mkdir(parents=True)
    docs_dir.mkdir(parents=True)

    md_text = "\n".join(
        [
            "# Architecture Overview",
            "Intro paragraph with keyword needle_alpha.",
            "```python",
            "# comment inside code block must not be an outline heading",
            "```",
            "## Domain Layer",
            "### Bounded Contexts",
            "#### Invariants",
        ]
    )
    (docs_dir / "guide.md").write_text(md_text + "\n", encoding="utf-8")

    yaml_text = "\n".join(
        [
            "id: demo-pack",
            "name: Demo Pack",
            "metadata:",
            "  owner: platform-team",
            "  needle_key: needle_alpha",
        ]
    )
    (packs_dir / "pack.yaml").write_text(yaml_text + "\n", encoding="utf-8")

    json_text = '{\n  "version": "1.0.0",\n  "limits": {\n    "max_lines": 250\n  }\n}\n'
    (docs_dir / "config.json").write_text(json_text, encoding="utf-8")

    py_text = "\n".join(
        [
            "class SampleExplorer:",
            "    async def run_check(self) -> bool:",
            "        return True",
            "",
            "def helper_fn(x: int) -> int:",
            "    return x + 1",
        ]
    )
    (docs_dir / "sample.py").write_text(py_text + "\n", encoding="utf-8")

    ts_text = "\n".join(
        [
            "export interface TraceProps {",
            "  id: string;",
            "}",
            "export function renderTrace(props: TraceProps): string {",
            "  return props.id;",
            "}",
        ]
    )
    (docs_dir / "trace.tsx").write_text(ts_text + "\n", encoding="utf-8")
    (docs_dir / "schema.sql").write_text("SELECT 1;\n", encoding="utf-8")
    (docs_dir / "notes.txt").write_text("Plain document note.\n", encoding="utf-8")

    long_lines = [f"Line {idx:03d}: content payload" for idx in range(1, 361)]
    (docs_dir / "long_spec.md").write_text("\n".join(long_lines) + "\n", encoding="utf-8")
    return root


def test_surgical_port_protocol_and_extra_forbid_models(tmp_path: Path) -> None:
    explorer = SurgicalContextExplorer(repo_root=tmp_path)
    assert isinstance(explorer, SurgicalExplorerPort)
    assert MAX_SURGICAL_LINES == 250

    with pytest.raises(ValidationError):
        SurgicalLineEntry.model_validate({"line_number": 1, "content": "ok", "unexpected": 1})
    with pytest.raises(ValidationError):
        SurgicalOutlineNode.model_validate(
            {"kind": "heading", "title": "T", "line_number": 1, "extra_field": True}
        )
    with pytest.raises(ValidationError):
        SurgicalSnippetMatch.model_validate(
            {
                "resource_uri": "docs/a.md",
                "display_filename": "a.md",
                "start_line": 1,
                "end_line": 2,
                "excerpt": "hi",
                "rogue": "x",
            }
        )
    obs = SurgicalObservation(
        kind=SurgicalPrimitiveName.CHECK_RESOURCE_STATE,
        resource_uri="docs/a.md",
        display_filename="a.md",
    )
    assert obs.redacted is False


@pytest.mark.asyncio
async def test_check_resource_state_existing_and_missing(tmp_path: Path) -> None:
    root = _seed_sample_workspace(tmp_path)
    explorer = SurgicalContextExplorer(repo_root=root)

    existing = await explorer.execute_primitive(
        SurgicalPrimitiveName.CHECK_RESOURCE_STATE,
        resource_uri="packs/demo/pack.yaml",
    )
    expected_sha = hashlib.sha256((root / "packs" / "demo" / "pack.yaml").read_bytes()).hexdigest()
    assert existing.exists is True
    assert existing.sha256 == expected_sha
    assert existing.total_lines == 5
    assert existing.file_badge_code == "Y"
    assert existing.check_label is not None
    assert "pack.yaml" in existing.summary

    missing = await explorer.execute_primitive(
        SurgicalPrimitiveName.CHECK_RESOURCE_STATE,
        resource_uri="docs/missing-file.md",
    )
    assert missing.exists is False
    assert missing.total_lines == 0
    assert missing.sha256 is None


@pytest.mark.asyncio
async def test_outline_resource_structure_md_yaml_json_py_ts(tmp_path: Path) -> None:
    root = _seed_sample_workspace(tmp_path)
    explorer = SurgicalContextExplorer(repo_root=root)

    md_obs = await explorer.execute_primitive(
        SurgicalPrimitiveName.OUTLINE_RESOURCE_STRUCTURE,
        resource_uri="docs/guide.md",
    )
    titles = [(n.level, n.title, n.line_number) for n in md_obs.outline]
    assert titles == [
        (1, "Architecture Overview", 1),
        (2, "Domain Layer", 6),
        (3, "Bounded Contexts", 7),
        (4, "Invariants", 8),
    ]

    yaml_obs = await explorer.execute_primitive(
        SurgicalPrimitiveName.OUTLINE_RESOURCE_STRUCTURE,
        resource_uri="packs/demo/pack.yaml",
    )
    yaml_keys = [(n.level, n.title, n.line_number) for n in yaml_obs.outline]
    assert (1, "id", 1) in yaml_keys
    assert (1, "metadata", 3) in yaml_keys
    assert (2, "owner", 4) in yaml_keys

    json_obs = await explorer.execute_primitive(
        SurgicalPrimitiveName.OUTLINE_RESOURCE_STRUCTURE,
        resource_uri="docs/config.json",
    )
    json_keys = [(n.level, n.title) for n in json_obs.outline]
    assert (1, "version") in json_keys
    assert (2, "max_lines") in json_keys

    py_obs = await explorer.execute_primitive(
        SurgicalPrimitiveName.OUTLINE_RESOURCE_STRUCTURE,
        resource_uri="docs/sample.py",
    )
    py_symbols = [(n.kind, n.title, n.line_number) for n in py_obs.outline]
    assert ("class", "SampleExplorer", 1) in py_symbols
    assert ("function", "run_check", 2) in py_symbols
    assert ("function", "helper_fn", 5) in py_symbols

    ts_obs = await explorer.execute_primitive(
        SurgicalPrimitiveName.OUTLINE_RESOURCE_STRUCTURE,
        resource_uri="docs/trace.tsx",
    )
    ts_titles = [n.title for n in ts_obs.outline]
    assert "TraceProps" in ts_titles
    assert "renderTrace" in ts_titles


@pytest.mark.asyncio
async def test_search_workspace_snippets_and_inspect_lines_250_cap_and_badges(
    tmp_path: Path,
) -> None:
    root = _seed_sample_workspace(tmp_path)
    explorer = SurgicalContextExplorer(repo_root=root)

    search_obs = await explorer.execute_primitive(
        SurgicalPrimitiveName.SEARCH_WORKSPACE_SNIPPETS,
        query="needle_alpha",
        max_results=5,
    )
    assert len(search_obs.snippets) == 2
    matched_files = {s.display_filename for s in search_obs.snippets}
    assert matched_files == {"guide.md", "pack.yaml"}
    assert all(s.line_anchor.startswith("#L") for s in search_obs.snippets)

    capped_obs = await explorer.inspect_lines(
        "docs/long_spec.md",
        start_line=10,
        end_line=350,
    )
    assert len(capped_obs.lines) == MAX_SURGICAL_LINES
    assert capped_obs.start_line == 10
    assert capped_obs.end_line == 259
    assert capped_obs.total_lines == 360
    assert capped_obs.file_badge_code == "M↓"
    assert capped_obs.formatted_badge == "Analyzed M↓ long_spec.md #L10-259"
    assert capped_obs.lines[0].line_number == 10
    assert capped_obs.lines[-1].line_number == 259

    virtual_pack = await explorer.inspect_lines("pack://demo/pack.yaml", start_line=1, end_line=3)
    assert virtual_pack.file_badge_code == "Y"
    assert len(virtual_pack.lines) == 3

    for uri, expected_badge in (
        ("docs/sample.py", "PY"),
        ("docs/trace.tsx", "TS"),
        ("docs/config.json", "JSON"),
        ("docs/schema.sql", "SQL"),
        ("docs/notes.txt", "DOC"),
    ):
        obs = await explorer.inspect_lines(uri, start_line=1, end_line=5)
        assert obs.file_badge_code == expected_badge

    with pytest.raises(ValidationDomainError):
        await explorer.inspect_lines("docs/guide.md", start_line=0, end_line=10)
    with pytest.raises(ValidationDomainError):
        await explorer.inspect_lines("docs/guide.md", start_line=10, end_line=5)
    with pytest.raises(ResourceNotFoundError):
        await explorer.inspect_lines("docs/nonexistent.md", start_line=1, end_line=10)


@pytest.mark.asyncio
async def test_read_source_redaction_and_traversal_ssrf_guards(tmp_path: Path) -> None:
    root = _seed_sample_workspace(tmp_path)
    explorer = SurgicalContextExplorer(
        repo_root=root,
        read_source_authorizer=lambda uri, _ws, _actor: (
            (False, "orcia://permissions/request/demo-secret")
            if "pack.yaml" in uri
            else (True, None)
        ),
    )

    redacted_flag = await explorer.inspect_lines(
        "docs/guide.md",
        start_line=1,
        end_line=5,
        has_read_source=False,
    )
    assert redacted_flag.redacted is True
    assert redacted_flag.redacted_reason == "READ_SOURCE_REQUIRED"
    assert redacted_flag.lines == []
    assert redacted_flag.sha256 is None
    assert redacted_flag.permission_request_hint is not None

    redacted_policy = await explorer.inspect_lines("packs/demo/pack.yaml", start_line=1, end_line=5)
    assert redacted_policy.redacted is True
    assert redacted_policy.redacted_reason == "READ_SOURCE_REQUIRED"
    assert redacted_policy.lines == []
    assert redacted_policy.permission_request_hint == "orcia://permissions/request/demo-secret"

    malicious_uris = (
        "../pyproject.toml",
        "docs/../../etc/passwd",
        "docs/%2e%2e/secrets.env",
        "docs/guide.md\x00.txt",
        "/etc/passwd",
        "file:///etc/passwd",
        "http://169.254.169.254/latest/meta-data/",
        "http://169.254.12.34/metadata",
        "https://[fe80::1]/secret",
        "http://metadata.google.internal/computeMetadata/v1/",
        "http://100.100.100.200/latest/meta-data/",
    )
    for bad_uri in malicious_uris:
        with pytest.raises((ValidationDomainError, PolicyDeniedError)):
            await explorer.inspect_lines(bad_uri, start_line=1, end_line=10)


@pytest.mark.asyncio
async def test_edge_cases_virtual_resolver_scoped_search_and_out_of_range(tmp_path: Path) -> None:
    root = _seed_sample_workspace(tmp_path)
    (root / "docs" / "broken.py").write_text("class Broken(\ndef recover_fn():\n", encoding="utf-8")
    explorer = SurgicalContextExplorer(
        repo_root=root,
        virtual_resource_resolver=lambda uri, _ws: (
            "alpha\nbeta\n" if uri.startswith("catalog://mem") else None
        ),
    )
    virt = await explorer.inspect_lines("catalog://mem/doc.md@abc#L1-2", start_line=1, end_line=2)
    assert len(virt.lines) == 2
    assert virt.display_filename == "doc.md"

    past_eof = await explorer.inspect_lines("docs/notes.txt", start_line=50, end_line=60)
    assert past_eof.lines == []

    py_fallback = await explorer.execute_primitive(
        SurgicalPrimitiveName.OUTLINE_RESOURCE_STRUCTURE, resource_uri="docs/broken.py"
    )
    assert any(n.title == "recover_fn" for n in py_fallback.outline)

    scoped_file = await explorer.execute_primitive(
        SurgicalPrimitiveName.SEARCH_WORKSPACE_SNIPPETS,
        resource_uri="docs/guide.md",
        query="needle_alpha",
        max_results=1,
    )
    assert len(scoped_file.snippets) == 1

    redacted_search = await explorer.execute_primitive(
        SurgicalPrimitiveName.SEARCH_WORKSPACE_SNIPPETS,
        query="needle_alpha",
        has_read_source=False,
    )
    assert redacted_search.redacted is True
    assert redacted_search.snippets == []

    redacted_state = await explorer.execute_primitive(
        SurgicalPrimitiveName.CHECK_RESOURCE_STATE,
        resource_uri="docs/guide.md",
        has_read_source=False,
    )
    assert redacted_state.redacted is True

    with pytest.raises(ResourceNotFoundError):
        await explorer.execute_primitive(
            SurgicalPrimitiveName.OUTLINE_RESOURCE_STRUCTURE, resource_uri="docs/absent.md"
        )
    with pytest.raises(ValidationDomainError):
        await explorer.execute_primitive(
            SurgicalPrimitiveName.SEARCH_WORKSPACE_SNIPPETS, query="   "
        )
    with pytest.raises(ValidationDomainError):
        await explorer.inspect_lines("   ", start_line=1, end_line=5)
    with pytest.raises(ValidationDomainError):
        await explorer.inspect_lines("unknown://item", start_line=1, end_line=5)
    with pytest.raises(PolicyDeniedError):
        await explorer.inspect_lines("https://example.org/doc.md", start_line=1, end_line=5)
