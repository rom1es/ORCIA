"""Unit tests for `infra/scripts/sync_site_catalog.py` (`pnpm site:sync` / `pnpm site:check`).

Verifies:
1. `sync_site_catalog.py --check` returns 0 (manifest and static HTML are in sync).
2. Generated `orciaSiteManifest.ts` contains zero raw hex color literals (`#[0-9a-fA-F]{3,8}`).
3. Standalone HTML `docs/site-catalog/index.html` is self-contained and enforces strict
   editorial separation between Space 1, Space 2, and Space 3.
"""

from __future__ import annotations

import importlib.util
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SYNC_SCRIPT_PATH = REPO_ROOT / "infra" / "scripts" / "sync_site_catalog.py"
MANIFEST_TS_PATH = REPO_ROOT / "apps" / "web" / "src" / "generated" / "orciaSiteManifest.ts"
DOCS_HTML_PATH = REPO_ROOT / "docs" / "site-catalog" / "index.html"


def _load_sync_module():
    spec = importlib.util.spec_from_file_location("sync_site_catalog", SYNC_SCRIPT_PATH)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_sync_site_catalog_check_is_up_to_date() -> None:
    module = _load_sync_module()
    exit_code = module.main(["--check"])
    assert exit_code == 0

    manifest = module.build_manifest_data()
    assert manifest["stats"]["activeRoutesCount"] >= 20
    assert manifest["stats"]["uiPrimitivesCount"] >= 65
    assert manifest["stats"]["installedPacksCount"] >= 2
    assert manifest["stats"]["alembicMigrationsCount"] >= 27
    assert manifest["stats"]["architectureDecisionsCount"] >= 21
    assert manifest["stats"]["techLeadReportsCount"] >= 71
    assert "/showcase" in manifest["activeRoutes"]
    assert "OrciaProductShowcaseSiteView" in manifest["uiPrimitives"]


def test_generated_manifest_has_zero_raw_hex_colors() -> None:
    content = MANIFEST_TS_PATH.read_text(encoding="utf-8")
    hex_matches = re.findall(r"#[0-9a-fA-F]{3,8}\b", content)
    assert hex_matches == [], f"Found forbidden hex colors in orciaSiteManifest.ts: {hex_matches}"


def test_standalone_html_editorial_separation_between_pillars() -> None:
    html_text = DOCS_HTML_PATH.read_text(encoding="utf-8")

    macro_match = re.search(r'<section id="pillar-macro"[\s\S]*?</section>', html_text)
    features_match = re.search(r'<section id="pillar-features"[\s\S]*?</section>', html_text)
    arch_match = re.search(r'<section id="pillar-architecture"[\s\S]*?</section>', html_text)
    changelog_match = re.search(r'<section id="pillar-changelog"[\s\S]*?</section>', html_text)

    assert macro_match is not None
    assert features_match is not None
    assert arch_match is not None
    assert changelog_match is not None

    macro_section = macro_match.group(0)
    features_section = features_match.group(0)
    arch_section = arch_match.group(0)

    forbidden_impl_terms = [
        "PostgreSQL",
        "FastAPI",
        "DBOS",
        "SQLAlchemy",
        "pgvector",
        "halfvec",
        "Starlark",
        "Wasmtime",
        "Argon2id",
        "Dramatiq",
        "SeaweedFS",
    ]
    for term in forbidden_impl_terms:
        assert term not in macro_section, f"{term} leaked into standalone Macro pillar"
        assert term not in features_section, f"{term} leaked into standalone Features pillar"
        assert term in arch_section, f"{term} missing from standalone Architecture pillar"
