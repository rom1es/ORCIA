#!/usr/bin/env python3
"""ORCIA Living Product & Architecture Showcase Site Synchronizer (`pnpm site:sync`).

Introspects the ORCIA repository deterministically via `_site_repo_parsers` and
generates:
- `apps/web/src/generated/orciaSiteManifest.ts` (zero raw hex color literals)
- `docs/site-catalog/index.html` (versioned self-contained HTML5/CSS/JS showcase site)
- `dist/orcia-site/index.html` (dist copy of the self-contained HTML5/CSS/JS showcase site)

Supports `--check` to verify in CI that committed artifacts and `capabilities.yaml`
(`CAP ↔ UJ ↔ Spec E2E`) are 100% in sync with the repository.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

_SCRIPTS_DIR = Path(__file__).resolve().parent
if str(_SCRIPTS_DIR) not in sys.path:
    sys.path.insert(0, str(_SCRIPTS_DIR))

from _site_html_renderer import _format_report_card_html, render_standalone_html  # noqa: E402
from _site_repo_parsers import (  # noqa: E402
    HEX_COLOR_RE,
    clean_markdown_inline,
    parse_active_routes,
    parse_architecture_spine,
    parse_business_packs,
    parse_migrations,
    parse_tech_lead_reports,
    parse_ui_primitives,
    sanitize_no_hex_for_ts,
)
from capabilities_registry import (  # noqa: E402
    capability_test_stats,
    load_registry,
    run_registry_check,
)

REPO_ROOT = _SCRIPTS_DIR.parents[1]
SPINE_PATH = (
    REPO_ROOT
    / "docs"
    / "planning-artifacts"
    / "architecture"
    / "architecture-ORCIA-2026-10-24"
    / "ARCHITECTURE-SPINE.md"
)
ROUTES_DIR = REPO_ROOT / "apps" / "web" / "src" / "routes"
ROUTER_FILE = REPO_ROOT / "apps" / "web" / "src" / "router.tsx"
UI_INDEX_FILE = REPO_ROOT / "packages" / "ui" / "src" / "index.ts"
PACKAGES_DIR = REPO_ROOT / "packages"
MIGRATIONS_DIR = REPO_ROOT / "infra" / "migrations" / "versions"
REPORTS_README = REPO_ROOT / "docs" / "implementation-artifacts" / "tech-lead-reports" / "README.md"
CAPABILITIES_INDEX_OUT = REPO_ROOT / "docs" / "product" / "capabilities-index.md"

MANIFEST_TS_OUT = REPO_ROOT / "apps" / "web" / "src" / "generated" / "orciaSiteManifest.ts"
DOCS_HTML_OUT = REPO_ROOT / "docs" / "site-catalog" / "index.html"
DIST_HTML_OUT = REPO_ROOT / "dist" / "orcia-site" / "index.html"

__all__ = [
    "CAPABILITIES_INDEX_OUT",
    "DOCS_HTML_OUT",
    "DIST_HTML_OUT",
    "HEX_COLOR_RE",
    "MANIFEST_TS_OUT",
    "MIGRATIONS_DIR",
    "PACKAGES_DIR",
    "REPO_ROOT",
    "REPORTS_README",
    "ROUTER_FILE",
    "ROUTES_DIR",
    "SPINE_PATH",
    "UI_INDEX_FILE",
    "_format_report_card_html",
    "build_manifest_data",
    "clean_markdown_inline",
    "main",
    "parse_active_routes",
    "parse_architecture_spine",
    "parse_business_packs",
    "parse_migrations",
    "parse_tech_lead_reports",
    "parse_ui_primitives",
    "render_standalone_html",
    "render_typescript_manifest",
    "sanitize_no_hex_for_ts",
]


def build_manifest_data() -> dict[str, Any]:
    """Assemble showcase manifest statistics and repository inventories."""
    decisions, stack_items = parse_architecture_spine(SPINE_PATH)
    routes = parse_active_routes(ROUTES_DIR, ROUTER_FILE)
    primitives = parse_ui_primitives(UI_INDEX_FILE)
    packs = parse_business_packs(PACKAGES_DIR)
    migrations = parse_migrations(MIGRATIONS_DIR)
    reports = parse_tech_lead_reports(REPORTS_README)
    latest_date = reports[-1]["date"] if reports else "2026-11-05"

    cap_data = load_registry()
    caps = cap_data.get("capabilities", [])
    live_caps = [c for c in caps if c.get("status") == "live"]
    verified_caps = [
        c for c in live_caps if c.get("verification") == "runtime" and bool(c.get("tests"))
    ]
    cap_stats = capability_test_stats(cap_data, include_uj_e2e=True)

    return {
        "lastSyncedDate": latest_date,
        "stats": {
            "activeRoutesCount": len(routes),
            "uiPrimitivesCount": len(primitives),
            "installedPacksCount": len(packs),
            "alembicMigrationsCount": len(migrations),
            "architectureDecisionsCount": len(decisions),
            "stackComponentsCount": len(stack_items),
            "techLeadReportsCount": len(reports),
            "capabilitiesCount": len(caps),
            "liveCapabilitiesCount": len(live_caps),
            "verifiedCapabilitiesCount": len(verified_caps),
            "userJourneysCount": cap_stats["userJourneysCount"],
            "coveredUserJourneysCount": cap_stats["coveredUserJourneysCount"],
            "e2eCoveredCapabilitiesCount": cap_stats["e2eCoveredCapabilitiesCount"],
        },
        "activeRoutes": routes,
        "uiPrimitives": primitives,
        "installedPacks": packs,
        "alembicMigrations": migrations,
        "architectureDecisions": decisions,
        "stackComponents": stack_items,
        "techLeadReports": list(reversed(reports)),
    }


def render_typescript_manifest(manifest: dict[str, Any]) -> str:
    """Serialize showcase manifest to TypeScript with zero raw hex literals."""
    json_payload = sanitize_no_hex_for_ts(json.dumps(manifest, ensure_ascii=False, indent=2))
    return (
        "/**\n"
        " * AUTO-GENERATED BY `infra/scripts/sync_site_catalog.py` (`pnpm site:sync`).\n"
        " * DO NOT EDIT MANUALLY — run `pnpm site:sync` to refresh from the repository.\n"
        " */\n\n"
        'import type { OrciaShowcaseManifestData } from "@orcia/ui";\n\n'
        f"export const ORCIA_SITE_MANIFEST: OrciaShowcaseManifestData = {json_payload};\n"
    )


def _run_check(expected_ts: str, expected_html: str, manifest: dict[str, Any]) -> int:
    errors = [f"[capabilities.yaml] {err}" for err in run_registry_check()]
    stats = capability_test_stats(load_registry(), include_uj_e2e=True)
    print(
        f"[capabilities] {stats['with_tests']}/{stats['live']} capacités live référencent "
        f"au moins un test ({len(stats['without_tests'])} sans test) · "
        f"E2E fonctionnels: {stats['e2eCoveredCapabilitiesCount']}/{stats['liveFeaturesCount']} · "
        f"UJ: {stats['coveredUserJourneysCount']}/{stats['userJourneysCount']}."
    )
    if not MANIFEST_TS_OUT.exists():
        errors.append(f"Missing generated manifest: {MANIFEST_TS_OUT}")
    elif MANIFEST_TS_OUT.read_text(encoding="utf-8") != expected_ts:
        errors.append(f"Out-of-sync TypeScript manifest: {MANIFEST_TS_OUT} (run `pnpm site:sync`)")

    root_scripts_dir = REPO_ROOT / "scripts"
    if str(root_scripts_dir) not in sys.path:
        sys.path.insert(0, str(root_scripts_dir))
    import generate_capabilities_index  # type: ignore[import-not-found]
    import generate_tlr_index  # type: ignore[import-not-found]

    if generate_tlr_index.run(REPORTS_README.parent, check=True) != 0:
        errors.append(
            f"Out-of-sync Tech Lead reports index: {REPORTS_README} (run `pnpm site:sync`)"
        )
    if generate_capabilities_index.run(check=True) != 0:
        errors.append(
            f"Out-of-sync capabilities index: {CAPABILITIES_INDEX_OUT} (run `pnpm site:sync`)"
        )

    if not DOCS_HTML_OUT.exists():
        errors.append(f"Missing static HTML catalog: {DOCS_HTML_OUT}")
    elif DOCS_HTML_OUT.read_text(encoding="utf-8") != expected_html:
        errors.append(f"Out-of-sync static HTML catalog: {DOCS_HTML_OUT} (run `pnpm site:sync`)")

    if errors:
        for err in errors:
            print(f"[site:check FAILED] {err}", file=sys.stderr)
        return 1
    print(
        f"[site:check OK] Manifest ({manifest['stats']['techLeadReportsCount']} reports, "
        f"{manifest['stats']['activeRoutesCount']} routes, "
        f"{manifest['stats']['uiPrimitivesCount']} UI primitives) is in sync."
    )
    return 0


def main(argv: list[str] | None = None) -> int:
    """CLI entrypoint for `pnpm site:sync` and `pnpm site:check`."""
    parser = argparse.ArgumentParser(
        description="Synchronize ORCIA showcase manifest and standalone HTML site."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify that committed manifest and static HTML are up-to-date.",
    )
    args = parser.parse_args(argv)

    if not args.check:
        root_scripts_dir = REPO_ROOT / "scripts"
        if str(root_scripts_dir) not in sys.path:
            sys.path.insert(0, str(root_scripts_dir))
        import generate_capabilities_index  # type: ignore[import-not-found]
        import generate_tlr_index  # type: ignore[import-not-found]

        generate_tlr_index.run(REPORTS_README.parent, check=False)
        generate_capabilities_index.run(check=False)

    manifest = build_manifest_data()
    expected_ts = render_typescript_manifest(manifest)
    expected_html = render_standalone_html(manifest)

    if args.check:
        return _run_check(expected_ts, expected_html, manifest)

    for out_path, content in (
        (MANIFEST_TS_OUT, expected_ts),
        (DOCS_HTML_OUT, expected_html),
        (DIST_HTML_OUT, expected_html),
    ):
        out_path.parent.mkdir(parents=True, exist_ok=True)
        out_path.write_text(content, encoding="utf-8")

    print(
        f"[site:sync OK] Generated:\n"
        f"  - {CAPABILITIES_INDEX_OUT.relative_to(REPO_ROOT)}\n"
        f"  - {MANIFEST_TS_OUT.relative_to(REPO_ROOT)}\n"
        f"  - {DOCS_HTML_OUT.relative_to(REPO_ROOT)}\n"
        f"  - {DIST_HTML_OUT.relative_to(REPO_ROOT)}\n"
        f"  Stats: {manifest['stats']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
