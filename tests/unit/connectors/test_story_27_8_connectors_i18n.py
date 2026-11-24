"""Unit tests for Story 27.8 — Bilingual (`fr`/`en`) `orcia_connectors` error catalog & locales."""

from __future__ import annotations

from pathlib import Path

import pytest

import orcia_connectors._error_catalog  # noqa: F401
from orcia_connectors._connectors_locales import (
    AUTONOMOUS_HELP_DEFAULTS,
    BOUNDED_WORKFLOW_LOCALES,
    CONNECTOR_SEED_LOCALES,
    JIRA_ACCESS_REQUEST_LOCALES,
    SDLC_POLICY_AND_MARKER_LOCALES,
    get_codegraph_markdown_copy,
    get_surgical_copy,
)
from orcia_connectors._pack_builder_locales import PACK_BUILDER_PROCESSES
from orcia_connectors._sdlc_template_locales import get_sdlc_doc_vs_code_copy
from orcia_connectors._surgical_observations import (
    build_check_state_observation,
    build_inspect_lines_observation,
    build_outline_observation,
    build_redacted_observation,
)
from orcia_connectors._surgical_parsers import validate_surgical_uri_security
from orcia_connectors.codegraph_tool_runner import format_codegraph_markdown_section
from orcia_connectors.surgical import SurgicalContextExplorer
from orcia_core.kernel.errors import (
    ERROR_CATALOG,
    PolicyDeniedError,
    ResourceNotFoundError,
    ValidationDomainError,
)
from orcia_core.ports.surgical_explorer_port import SurgicalPrimitiveName


def test_connector_error_catalog_entries_localize_fr_and_en() -> None:
    with pytest.raises(ValidationDomainError) as empty_exc:
        validate_surgical_uri_security("   ")
    assert empty_exc.value.localize("fr").detail == "Le paramètre `uri` ne peut pas être vide."
    assert empty_exc.value.localize("en").detail == "The `uri` parameter cannot be empty."

    with pytest.raises(ValidationDomainError) as trav_exc:
        validate_surgical_uri_security("../pyproject.toml")
    assert trav_exc.value.error_code == "ERR_VALIDATION_FAILED"
    assert trav_exc.value.localize("fr").title == "Erreur de validation de la requête"
    assert trav_exc.value.localize("en").title == "Request validation failed"
    assert trav_exc.value.localize("fr").detail == "Traversée de chemin `..` strictement interdite."
    assert trav_exc.value.localize("en").detail == "Path traversal `..` is strictly forbidden."

    with pytest.raises(PolicyDeniedError) as ssrf_exc:
        validate_surgical_uri_security("http://169.254.169.254/latest/meta-data/")
    assert "169.254.169.254" in ssrf_exc.value.localize("fr").detail
    assert "169.254.169.254" in ssrf_exc.value.localize("en").detail
    assert ssrf_exc.value.localize("fr").detail != ssrf_exc.value.localize("en").detail

    with pytest.raises(ValidationDomainError) as file_scheme_exc:
        validate_surgical_uri_security("file:///etc/passwd")
    assert file_scheme_exc.value.localize("fr").detail != (
        file_scheme_exc.value.localize("en").detail
    )

    with pytest.raises(PolicyDeniedError) as scheme_exc:
        validate_surgical_uri_security("ftp://example.org/file")
    assert scheme_exc.value.localize("fr").detail != scheme_exc.value.localize("en").detail

    with pytest.raises(ValidationDomainError) as unknown_scheme_exc:
        validate_surgical_uri_security("custom://resource")
    assert "custom://" in unknown_scheme_exc.value.localize("en").detail

    for code in list(ERROR_CATALOG):
        if code.startswith("ERR_SURGICAL_"):
            assert ERROR_CATALOG[code]["fr"].title.strip()
            assert ERROR_CATALOG[code]["en"].title.strip()
            assert ERROR_CATALOG[code]["fr"].detail != ERROR_CATALOG[code]["en"].detail


@pytest.mark.asyncio
async def test_surgical_explorer_errors_and_observations_localize(tmp_path: Path) -> None:
    (tmp_path / "docs").mkdir(parents=True)
    (tmp_path / "packs").mkdir(parents=True)
    (tmp_path / "docs" / "sample.md").write_text("# Title\nLine 2\n", encoding="utf-8")
    explorer = SurgicalContextExplorer(repo_root=tmp_path)

    with pytest.raises(ValidationDomainError) as bounds_exc:
        await explorer.inspect_lines("docs/sample.md", start_line=10, end_line=2)
    assert "Bornes de lignes invalides" in bounds_exc.value.localize("fr").detail
    assert "Invalid line bounds" in bounds_exc.value.localize("en").detail

    with pytest.raises(ValidationDomainError) as oob_exc:
        await explorer.inspect_lines("/etc/passwd", start_line=1, end_line=2)
    assert "hors des racines autorisées" in oob_exc.value.localize("fr").detail
    assert "outside the authorized roots" in oob_exc.value.localize("en").detail

    with pytest.raises(ResourceNotFoundError) as nf_exc:
        await explorer.inspect_lines("docs/missing.md", start_line=1, end_line=2)
    assert "Ressource introuvable" in nf_exc.value.localize("fr").detail
    assert "Resource not found" in nf_exc.value.localize("en").detail

    red_en = build_redacted_observation(
        SurgicalPrimitiveName.INSPECT_RESOURCE_LINES, "docs/sample.md", None, locale="en"
    )
    assert "READ_SOURCE permission is required" in red_en.summary

    miss_en = build_check_state_observation("docs/missing.md", exists=False, text="", locale="en")
    assert "not found" in (miss_en.check_label or "")
    ok_en = build_check_state_observation("docs/sample.md", exists=True, text="a\nb\n", locale="en")
    assert "available" in ok_en.summary
    out_en = build_outline_observation("docs/sample.md", exists=True, text="# Title\n", locale="en")
    assert "Extracted structure" in out_en.summary
    lines_en = build_inspect_lines_observation(
        "docs/sample.md", exists=True, text="# Title\n", start_line=1, end_line=1, locale="en"
    )
    assert "Read 1 line(s)" in lines_en.summary

    search_fr = await explorer.execute_primitive(
        SurgicalPrimitiveName.SEARCH_WORKSPACE_SNIPPETS,
        resource_uri="docs",
        query="Title",
        locale="fr",
    )
    search_en = await explorer.execute_primitive(
        SurgicalPrimitiveName.SEARCH_WORKSPACE_SNIPPETS,
        resource_uri="docs",
        query="Title",
        locale="en",
    )
    assert "Recherché" in search_fr.formatted_badge
    assert "extrait(s) trouvé(s)" in search_fr.summary
    assert "Searched 'Title'" in search_en.formatted_badge
    assert "snippet(s) matched" in search_en.summary


def test_connector_locale_bundles_and_codegraph_markdown_fr_en_parity() -> None:
    for bundle in (
        AUTONOMOUS_HELP_DEFAULTS,
        JIRA_ACCESS_REQUEST_LOCALES,
        SDLC_POLICY_AND_MARKER_LOCALES,
        BOUNDED_WORKFLOW_LOCALES,
        CONNECTOR_SEED_LOCALES,
    ):
        assert set(bundle["fr"].keys()) == set(bundle["en"].keys())
        for key in bundle["fr"]:
            assert bundle["fr"][key].strip()
            assert bundle["en"][key].strip()

    assert get_surgical_copy("fr").redacted_summary != get_surgical_copy("en").redacted_summary
    assert (
        get_codegraph_markdown_copy("fr")["heading"]
        != (get_codegraph_markdown_copy("en")["heading"])
    )
    assert (
        get_sdlc_doc_vs_code_copy("fr")["wf_title"] != (get_sdlc_doc_vs_code_copy("en")["wf_title"])
    )
    assert len(PACK_BUILDER_PROCESSES) == 6
    for proc in PACK_BUILDER_PROCESSES:
        assert proc.title_fr.strip() and proc.title_en.strip()

    payload = {
        "repo_alias": "orcia",
        "modified_files": ["a.py"],
        "blast_radius_score": 1.5,
        "risk_level": "LOW",
        "drift_warning": "GRAPH_MOVED_SINCE_RUN_LOCK",
        "run_lock_commit_sha": "aaa",
        "indexed_commit_sha": "bbb",
    }
    md_fr = format_codegraph_markdown_section(payload, locale="fr")
    md_en = format_codegraph_markdown_section(payload, locale="en")
    assert "Rayon d'Impact Code Graph" in md_fr
    assert "Code Graph Blast Radius" in md_en
    assert "Dérive détectée" in md_fr
    assert "Drift detected" in md_en
