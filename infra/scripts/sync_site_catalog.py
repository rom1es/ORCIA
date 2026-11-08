#!/usr/bin/env python3
"""ORCIA Living Product & Architecture Showcase Site Synchronizer (`pnpm site:sync`).

Introspects the ORCIA repository deterministically:
1. `docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24/ARCHITECTURE-SPINE.md`
2. `apps/web/src/routes/*.tsx` & `apps/web/src/router.tsx`
3. `packages/ui/src/index.ts`
4. `packages/orcia-pack-*/pyproject.toml`
5. `infra/migrations/versions/*.py`
6. `docs/implementation-artifacts/tech-lead-reports/README.md`

Generates:
- `apps/web/src/generated/orciaSiteManifest.ts` (zero raw hex color literals to obey Invariant 2)
- `docs/site-catalog/index.html` (versioned self-contained HTML5/CSS/JS showcase site)
- `dist/orcia-site/index.html` (dist copy of the self-contained HTML5/CSS/JS showcase site)

Supports `--check` to verify in CI that committed artifacts are 100% in sync with the repository.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
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

MANIFEST_TS_OUT = REPO_ROOT / "apps" / "web" / "src" / "generated" / "orciaSiteManifest.ts"
DOCS_HTML_OUT = REPO_ROOT / "docs" / "site-catalog" / "index.html"
DIST_HTML_OUT = REPO_ROOT / "dist" / "orcia-site" / "index.html"

HEX_COLOR_RE = re.compile(r"#[0-9a-fA-F]{3,8}\b")


def sanitize_no_hex_for_ts(text: str) -> str:
    """Strip any raw hex color literal (#6D28D9 -> Violet signature, #D97706 -> Ambre, etc.)
    so generated .ts files strictly pass @orcia/ui Invariant 2.
    """

    def _replace(match: re.Match[str]) -> str:
        token = match.group(0).upper()
        mapping = {
            "#6D28D9": "Violet signature",
            "#D97706": "Ambre arbitrage",
            "#059669": "Émeraude",
            "#2563EB": "Cobalt",
            "#DC2626": "Pourpre alerte",
            "#0F172A": "Ardoise",
            "#F8FAFC": "Clair",
        }
        return mapping.get(token, f"teinte-{token[1:]}")

    return HEX_COLOR_RE.sub(_replace, text)


def clean_markdown_inline(text: str) -> str:
    """Clean markdown formatting links/backticks for clean display."""
    cleaned = re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)
    cleaned = cleaned.replace("$\\rightarrow$", "→").replace("$\\leftrightarrow$", "↔")
    cleaned = cleaned.replace("$\\ge$", "≥").replace("$\\le$", "≤")
    cleaned = cleaned.replace("**", "").replace("`", "")
    return sanitize_no_hex_for_ts(cleaned.strip())


def parse_architecture_spine(
    spine_path: Path,
) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    content = spine_path.read_text(encoding="utf-8")
    decisions: list[dict[str, str]] = []
    for match in re.finditer(
        r"^###\s+(AD-\d+)\s+—\s+([^\n]+?)(?:\s*\[ADOPTED\])?\s*$",
        content,
        flags=re.MULTILINE,
    ):
        decisions.append(
            {
                "code": match.group(1).strip(),
                "title": clean_markdown_inline(match.group(2)),
            }
        )

    stack_items: list[dict[str, str]] = []
    stack_section_match = re.search(r"^##\s+Stack\s*$([\s\S]+)", content, flags=re.MULTILINE)
    if stack_section_match:
        stack_block = stack_section_match.group(1)
        for line in stack_block.splitlines():
            line_str = line.strip()
            if not line_str.startswith("|"):
                if stack_items and line_str.startswith("#"):
                    break
                continue
            cells = [c.strip() for c in line_str.strip("|").split("|")]
            if len(cells) >= 2:
                name_raw, version_raw = cells[0], cells[1]
                if name_raw in ("Name", "---") or set(name_raw) <= {"-", ":"}:
                    continue
                stack_items.append(
                    {
                        "name": clean_markdown_inline(name_raw),
                        "version": clean_markdown_inline(version_raw),
                    }
                )
    return decisions, stack_items


def parse_active_routes(routes_dir: Path, router_file: Path) -> list[str]:
    routes: set[str] = set()
    for route_file in sorted(routes_dir.glob("*.tsx")):
        if route_file.name in ("__root.tsx", "searchSchema.ts"):
            continue
        text = route_file.read_text(encoding="utf-8")
        for m in re.finditer(r'path:\s*"([^"]+)"', text):
            routes.add(m.group(1))
    if router_file.exists():
        router_text = router_file.read_text(encoding="utf-8")
        for m in re.finditer(r'path:\s*"([^"]+)"', router_text):
            routes.add(m.group(1))
    return sorted(routes)


def parse_ui_primitives(ui_index_file: Path) -> list[str]:
    text = ui_index_file.read_text(encoding="utf-8")
    primitives: list[str] = []
    for block_match in re.finditer(r'export\s*\{([^}]+)\}\s*from\s*"([^"]+)"', text):
        exports_raw = block_match.group(1)
        for token in exports_raw.split(","):
            tok = token.strip()
            if not tok or tok.startswith("type "):
                continue
            tok_name = tok.split(" as ")[0].strip()
            if (
                tok_name
                and tok_name[0].isupper()
                and not tok_name.startswith("DEFAULT_")
                and tok_name not in primitives
            ):
                primitives.append(tok_name)
    return sorted(primitives)


def parse_business_packs(packages_dir: Path) -> list[dict[str, str]]:
    packs: list[dict[str, str]] = []
    for pack_toml in sorted(packages_dir.glob("orcia-pack-*/pyproject.toml")):
        text = pack_toml.read_text(encoding="utf-8")
        name_match = re.search(r'^name\s*=\s*"([^"]+)"', text, flags=re.MULTILINE)
        version_match = re.search(r'^version\s*=\s*"([^"]+)"', text, flags=re.MULTILINE)
        desc_match = re.search(r'^description\s*=\s*"([^"]+)"', text, flags=re.MULTILINE)
        packs.append(
            {
                "key": name_match.group(1) if name_match else pack_toml.parent.name,
                "version": version_match.group(1) if version_match else "0.1.0",
                "description": sanitize_no_hex_for_ts(
                    desc_match.group(1) if desc_match else "Pack Métier ORCIA"
                ),
            }
        )
    return packs


def parse_migrations(migrations_dir: Path) -> list[str]:
    files: list[str] = []
    for f in sorted(migrations_dir.glob("*.py")):
        if f.name.startswith("__"):
            continue
        files.append(f.stem)
    return files


def parse_tech_lead_reports(readme_path: Path) -> list[dict[str, str]]:
    content = readme_path.read_text(encoding="utf-8")
    reports: list[dict[str, str]] = []
    for line in content.splitlines():
        s = line.strip()
        if not s.startswith("| **202"):
            continue
        cells = [c.strip() for c in s.strip("|").split("|")]
        if len(cells) < 5:
            continue
        date_str = clean_markdown_inline(cells[0])
        story_str = clean_markdown_inline(cells[1])
        file_cell = cells[2]
        file_match = re.search(r"\[`?([^`\]]+)`?\]", file_cell)
        file_name = file_match.group(1) if file_match else clean_markdown_inline(file_cell)
        domain_str = clean_markdown_inline(cells[3])
        summary_str = clean_markdown_inline(cells[4])
        reports.append(
            {
                "date": date_str,
                "phaseOrStory": story_str,
                "reportFile": sanitize_no_hex_for_ts(file_name),
                "domain": domain_str,
                "summary": summary_str,
            }
        )
    return reports


def build_manifest_data() -> dict[str, Any]:
    decisions, stack_items = parse_architecture_spine(SPINE_PATH)
    routes = parse_active_routes(ROUTES_DIR, ROUTER_FILE)
    primitives = parse_ui_primitives(UI_INDEX_FILE)
    packs = parse_business_packs(PACKAGES_DIR)
    migrations = parse_migrations(MIGRATIONS_DIR)
    reports = parse_tech_lead_reports(REPORTS_README)

    latest_date = reports[-1]["date"] if reports else "2026-11-05"

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
    json_payload = json.dumps(manifest, ensure_ascii=False, indent=2)
    json_payload = sanitize_no_hex_for_ts(json_payload)
    return (
        "/**\n"
        " * AUTO-GENERATED BY `infra/scripts/sync_site_catalog.py` (`pnpm site:sync`).\n"
        " * DO NOT EDIT MANUALLY — run `pnpm site:sync` to refresh from the repository.\n"
        " */\n\n"
        'import type { OrciaShowcaseManifestData } from "@orcia/ui";\n\n'
        f"export const ORCIA_SITE_MANIFEST: OrciaShowcaseManifestData = {json_payload};\n"
    )


def _format_report_card_html(r: dict[str, str]) -> str:
    search_val = html.escape(
        f"{r['date']} {r['phaseOrStory']} {r['domain']} {r['summary']}".lower()
    )
    date_esc = html.escape(r["date"])
    story_esc = html.escape(r["phaseOrStory"])
    file_esc = html.escape(r["reportFile"])
    domain_esc = html.escape(r["domain"])
    summary_esc = html.escape(r["summary"])
    return (
        f'<article class="report-card" data-search="{search_val}">'
        '<div class="report-meta">'
        f'<span class="badge badge-cobalt">{date_esc}</span>'
        f'<span class="badge badge-emerald">{story_esc}</span>'
        f'<code class="mono-code">{file_esc}</code>'
        "</div>"
        f"<h4>{domain_esc}</h4>"
        f"<p>{summary_esc}</p>"
        "</article>"
    )


def render_standalone_html(manifest: dict[str, Any]) -> str:
    stats = manifest["stats"]
    reports = manifest["techLeadReports"]
    stack_items = manifest["stackComponents"]
    decisions = manifest["architectureDecisions"]
    packs = manifest["installedPacks"]

    reports_rows_html = "\n".join(_format_report_card_html(r) for r in reports)
    stack_rows_html = "\n".join(
        f"<tr><td><strong>{html.escape(item['name'])}</strong></td>"
        f'<td><code class="mono-code">{html.escape(item["version"])}</code></td></tr>'
        for item in stack_items
    )
    decisions_html = "\n".join(
        f'<div class="ad-pill"><span class="badge badge-cobalt">{html.escape(ad["code"])}</span>'
        f"<span>{html.escape(ad['title'])}</span></div>"
        for ad in decisions
    )
    packs_html = "\n".join(
        f'<div class="pack-item"><span class="badge badge-emerald">'
        f"{html.escape(p['key'])}@{html.escape(p['version'])}</span>"
        f"<span>{html.escape(p['description'])}</span></div>"
        for p in packs
    )

    lines = [
        "<!DOCTYPE html>",
        '<html lang="fr">',
        "<head>",
        '  <meta charset="UTF-8" />',
        '  <meta name="viewport" content="width=device-width, initial-scale=1.0" />',
        "  <title>ORCIA — Site de Présentation &amp; Documentation Vivante</title>",
        "  <style>",
        "    :root {",
        "      --color-surface-bg: #EAF2FB;",
        "      --color-surface-card: #FFFFFF;",
        "      --color-surface-elevated: #F8FAFC;",
        "      --color-foreground: #0F172A;",
        "      --color-muted-foreground: #475569;",
        "      --color-border: #E2E8F0;",
        "      --color-primary-cobalt: #2563EB;",
        "      --color-primary-foreground: #FFFFFF;",
        "      --color-action-primary-subtle: #EFF6FF;",
        "      --color-human-led-violet: #6D28D9;",
        "      --color-human-led-bg: #F5F3FF;",
        "      --color-arbitration-amber: #D97706;",
        "      --color-arbitration-bg: #FFFBEB;",
        "      --color-gate-emerald: #059669;",
        "      --color-gate-emerald-bg: #ECFDF5;",
        "      --color-stale-crimson: #DC2626;",
        "      --color-stale-bg: #FEF2F2;",
        '      --font-sans: "Inter", "Geist Sans", system-ui, sans-serif;',
        '      --font-mono: "JetBrains Mono", "Geist Mono", monospace;',
        "      --radius-sm: 6px; --radius-md: 10px; --radius-lg: 14px;",
        "      --shadow-card: 0 4px 16px rgba(15, 23, 42, 0.05);",
        "    }",
        '    [data-theme="dark"] {',
        "      --color-surface-bg: #0B0F17; --color-surface-card: #111827;",
        "      --color-surface-elevated: #1E293B; --color-foreground: #F8FAFC;",
        "      --color-muted-foreground: #94A3B8; --color-border: #1E293B;",
        "      --color-primary-cobalt: #6366F1; --color-action-primary-subtle: #1E293B;",
        "      --color-human-led-bg: #2E1065; --color-arbitration-bg: #451A03;",
        "      --color-gate-emerald-bg: #064E3B;",
        "    }",
        "    * { box-sizing: border-box; }",
        "    body {",
        "      margin: 0; font-family: var(--font-sans);",
        "      background-color: var(--color-surface-bg);",
        "      color: var(--color-foreground); line-height: 1.6; font-size: 14px;",
        "    }",
        "    .container { max-width: 1280px; margin: 0 auto; padding: 24px; }",
        "    .hero {",
        "      background-color: var(--color-surface-card);",
        "      border: 1px solid var(--color-border); border-radius: var(--radius-lg);",
        "      padding: 24px; box-shadow: var(--shadow-card); margin-bottom: 20px;",
        "      display: flex; justify-content: space-between;",
        "      align-items: flex-start; gap: 16px; flex-wrap: wrap;",
        "    }",
        "    .hero h1 { margin: 0 0 8px 0; font-size: 24px; }",
        "    .hero p { margin: 0; color: var(--color-muted-foreground); max-width: 820px; }",
        "    .tabs { display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 20px; }",
        "    .tab-btn {",
        "      padding: 10px 16px; border-radius: var(--radius-sm);",
        "      border: 1px solid #93C5FD;",
        "      background-color: #DBEAFE;",
        "      color: #1E3A8A; font-weight: 600; cursor: pointer;",
        "    }",
        '    .tab-btn[aria-selected="true"], .tab-btn:focus-visible {',
        "      background-color: var(--color-primary-cobalt);",
        "      border-color: var(--color-primary-cobalt);",
        "      color: var(--color-primary-foreground);",
        "    }",
        "    .pillar-panel { display: none; }",
        "    .pillar-panel.active { display: block; }",
        "    .bento-grid {",
        "      display: grid;",
        "      grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));",
        "      gap: 18px; margin-bottom: 20px;",
        "    }",
        "    .card {",
        "      background-color: var(--color-surface-card);",
        "      border: 1px solid var(--color-border); border-radius: var(--radius-lg);",
        "      padding: 20px; box-shadow: var(--shadow-card); margin-bottom: 18px;",
        "    }",
        "    .card h2 { margin-top: 0; font-size: 18px; }",
        "    .card h3 { margin-top: 0; font-size: 15.5px; }",
        "    .card-violet {",
        "      border-left: 4px solid var(--color-human-led-violet);",
        "      background-color: var(--color-human-led-bg);",
        "    }",
        "    .card-emerald {",
        "      border-left: 4px solid var(--color-gate-emerald);",
        "      background-color: var(--color-gate-emerald-bg);",
        "    }",
        "    .card-amber {",
        "      border-left: 4px solid var(--color-arbitration-amber);",
        "      background-color: var(--color-arbitration-bg);",
        "    }",
        "    .badge {",
        "      display: inline-block; padding: 3px 9px;",
        "      border-radius: 9999px; font-size: 11.5px; font-weight: 600;",
        "    }",
        "    .badge-cobalt {",
        "      background-color: var(--color-action-primary-subtle);",
        "      color: var(--color-primary-cobalt);",
        "    }",
        "    .badge-violet {",
        "      background-color: var(--color-human-led-bg);",
        "      color: var(--color-human-led-violet);",
        "      border: 1px solid var(--color-human-led-violet);",
        "    }",
        "    .badge-emerald {",
        "      background-color: var(--color-gate-emerald-bg);",
        "      color: var(--color-gate-emerald);",
        "    }",
        "    .badge-amber {",
        "      background-color: var(--color-arbitration-bg);",
        "      color: var(--color-arbitration-amber);",
        "    }",
        "    .mono-code {",
        "      font-family: var(--font-mono); font-size: 12px;",
        "      background-color: var(--color-surface-elevated);",
        "      padding: 2px 6px; border-radius: 4px;",
        "      border: 1px solid var(--color-border);",
        "    }",
        "    .stats-row {",
        "      display: grid;",
        "      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));",
        "      gap: 12px; margin-bottom: 20px;",
        "    }",
        "    .stat-box {",
        "      background-color: var(--color-surface-card);",
        "      border: 1px solid var(--color-border); border-radius: var(--radius-md);",
        "      padding: 14px; text-align: center;",
        "    }",
        "    .stat-box strong {",
        "      display: block; font-size: 22px; color: var(--color-primary-cobalt);",
        "    }",
        "    table { width: 100%; border-collapse: collapse; font-size: 13px; }",
        "    th, td {",
        "      text-align: left; padding: 8px 10px;",
        "      border-bottom: 1px solid var(--color-border);",
        "    }",
        "    .report-card {",
        "      border: 1px solid var(--color-border); border-radius: var(--radius-md);",
        "      padding: 14px; margin-bottom: 12px;",
        "      background-color: var(--color-surface-elevated);",
        "    }",
        "    .report-card h4 { margin: 8px 0 4px 0; font-size: 14px; }",
        "    .report-card p {",
        "      margin: 0; font-size: 13px; color: var(--color-muted-foreground);",
        "    }",
        "    .report-meta { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }",
        "    .ad-pill, .pack-item {",
        "      padding: 8px 12px; border: 1px solid var(--color-border);",
        "      border-radius: var(--radius-sm); margin-bottom: 8px;",
        "      display: flex; gap: 10px; align-items: center; flex-wrap: wrap;",
        "      background-color: var(--color-surface-elevated);",
        "    }",
        "    .search-input {",
        "      width: 100%; padding: 9px 12px; border-radius: var(--radius-sm);",
        "      border: 1px solid var(--color-border);",
        "      background-color: var(--color-surface-card);",
        "      color: var(--color-foreground); margin-bottom: 14px;",
        "    }",
        "  </style>",
        "</head>",
        "<body>",
        '  <div class="container">',
        '    <header class="hero">',
        "      <div>",
        '        <span class="badge badge-cobalt">ORCIA · Synchronisé ('
        + html.escape(manifest["lastSyncedDate"])
        + ")</span>",
        "        <h1>ORCIA — Processus, Contexte et Agents sous Conduite Humaine</h1>",
        "        <p>",
        "          Explorez la plateforme selon 3 espaces strictement séparés",
        "          (aucun mélange entre la vision métier, le guide des écrans et",
        "          l'architecture d'ingénierie), complétés par l'historique vivant.",
        "        </p>",
        "      </div>",
        "      <div>",
        '        <button type="button" class="tab-btn" onclick="toggleTheme()">',
        "          🌗 Thème Clair / Sombre",
        "        </button>",
        "      </div>",
        "    </header>",
        '    <nav class="tabs" role="tablist">',
        '      <button type="button" class="tab-btn" role="tab" aria-selected="true"',
        "        onclick=\"switchTab('pillar-macro', this)\">",
        "        1. Vision &amp; Pilotage Humain (Macro)",
        "      </button>",
        '      <button type="button" class="tab-btn" role="tab" aria-selected="false"',
        "        onclick=\"switchTab('pillar-features', this)\">",
        "        2. Fonctionnalités &amp; Écrans (Guide Fonctionnel)",
        "      </button>",
        '      <button type="button" class="tab-btn" role="tab" aria-selected="false"',
        "        onclick=\"switchTab('pillar-architecture', this)\">",
        "        3. Architecture &amp; Choix Techniques (Sous le Capot)",
        "      </button>",
        '      <button type="button" class="tab-btn" role="tab" aria-selected="false"',
        "        onclick=\"switchTab('pillar-changelog', this)\">",
        f"        4. 🔄 Historique des Évolutions ({stats['techLeadReportsCount']})",
        "      </button>",
        "    </nav>",
        '    <section id="pillar-macro" class="pillar-panel active"',
        '      data-testid="showcase-pillar-macro">',
        '      <div class="card">',
        '        <span class="badge badge-cobalt">1.1 · Pourquoi ORCIA ?</span>',
        "        <h2>Orchestrer Processus, Contexte documentaire et Agents spécialisés</h2>",
        "        <p>",
        "          ORCIA réunit dans un environnement unique les processus métiers",
        "          structurés, le contexte documentaire vérifié de l'organisation et des",
        "          agents spécialisés sous conduite humaine.",
        "        </p>",
        "      </div>",
        '      <div class="card card-violet">',
        '        <span class="badge badge-violet">',
        "          1.2 · Principe Fondateur « Human-Led » (L'Humain aux Commandes)",
        "        </span>",
        "        <h2>Quatre garanties concrètes qui placent l'auteur humain au centre</h2>",
        '        <div class="bento-grid">',
        "          <div>",
        "            <h3>✍️ Ancrages de Rédaction Humaine obligatoires (Violet)</h3>",
        "            <p>",
        "              L'intention initiale, les objectifs et les hypothèses structurantes",
        "              appartiennent exclusivement à l'auteur humain.",
        "            </p>",
        "          </div>",
        "          <div>",
        "            <h3>🛑 Zéro validation machinale (« Anti-Validation Fantôme »)</h3>",
        "            <p>",
        "              Synthèse de décision en 4 blocs, approbation section par section",
        "              (Approuver / Co-éditer / Contester) et temps minimal de lecture active.",
        "            </p>",
        "          </div>",
        "          <div>",
        "            <h3>⚖️ Arbitrage humain systématique en cas de dilemme</h3>",
        "            <p>",
        "              L'IA n'invente jamais un compromis flou : le processus se met en",
        "              pause et présente les options à l'humain.",
        "            </p>",
        "          </div>",
        "          <div>",
        "            <h3>🛡️ Aucune modification sauvage des outils de l'entreprise</h3>",
        "            <p>",
        "              Actions préparées en attente d'accord humain avant toute écriture",
        "              externe et réconciliation respectueuse des modifications humaines.",
        "            </p>",
        "          </div>",
        "        </div>",
        "      </div>",
        '      <div class="card card-emerald">',
        '        <span class="badge badge-emerald">',
        "          1.3 · Double Barrière Anti-Hallucination (Déterministe + Probabiliste)",
        "        </span>",
        "        <h2>Stopper l'effet boule de neige dès la première étape</h2>",
        '        <div class="bento-grid">',
        "          <div>",
        "            <h3>1. Barrière n°1 — Les Contrôles Déterministes (100 %, coût nul)</h3>",
        "            <p>",
        "              Vérification exacte de la structure du livrable, des sections",
        "              obligatoires, des règles métiers du glossaire et des citations",
        "              (<code>[S1]</code>, <code>[G1]</code>, <code>[O1]</code>).",
        "            </p>",
        "          </div>",
        "          <div>",
        "            <h3>2. Barrière n°2 — Les Contrôles Probabilistes Croisés</h3>",
        "            <p>",
        "              Interdiction pour un modèle IA d'être juge et partie (famille",
        "              différente obligatoire), analyse sous 5 angles et purge des brouillons.",
        "            </p>",
        "          </div>",
        "          <div>",
        "            <h3>3. Barrière n°3 — La Remise en Cause Amont</h3>",
        "            <p>",
        "              Simulation d'impact sur les étapes suivantes et recalcul ciblé à",
        "              partir de l'étape corrigée sans recommencer tout le processus.",
        "            </p>",
        "          </div>",
        "        </div>",
        "      </div>",
        '      <div class="card">',
        '        <span class="badge badge-cobalt">',
        "          1.4 · Gouvernance par l'Organisation Réelle &amp; Packs Métiers",
        "        </span>",
        "        <h2>Plateforme entière ➔ Directions (BU) ➔ Espaces &amp; Packs Métiers</h2>",
        "        <p>",
        "          Chaque périmètre hérite des règles communes et active en 1 clic les",
        "          Packs Métiers adaptés à son domaine.",
        "        </p>",
        "      </div>",
        "    </section>",
        '    <section id="pillar-features" class="pillar-panel"',
        '      data-testid="showcase-pillar-features">',
        '      <div class="card">',
        '        <span class="badge badge-violet">',
        "          Volet A · Les 6 Dispositifs Concrets du Pilotage Humain",
        "        </span>",
        "        <h2>Dispositifs interactifs de pilotage humain et de fiabilité</h2>",
        '        <div class="bento-grid">',
        '          <div class="card"><h3>1. Carte d\'Ancrage Humain (Violet)</h3></div>',
        '          <div class="card"><h3>2. Carte d\'Arbitrage en 1 Clic</h3></div>',
        '          <div class="card"><h3>3. Grille 4 Blocs &amp; Validation par Section</h3></div>',
        (
            '          <div class="card"><h3>4. Simulateur d\'Impact Amont'
            " &amp; Retour Ciblé</h3></div>"
        ),
        (
            '          <div class="card"><h3>5. Citations ([S1], [G1], [O1])'
            " &amp; Glossaire</h3></div>"
        ),
        '          <div class="card"><h3>6. Prise en Charge Exclusive &amp; Observation</h3></div>',
        "        </div>",
        "      </div>",
        '      <div class="card">',
        '        <span class="badge badge-cobalt">',
        "          Volet B · Les 9 Écrans du Menu d'ORCIA expliqués un par un",
        "        </span>",
        "        <h2>Repères visuels et rôle de chaque écran</h2>",
        '        <div class="bento-grid">',
        '          <div class="card"><h3>1. ◈ Cockpit (<code>/cockpit</code>)</h3></div>',
        '          <div class="card"><h3>2. 💬 Mon Assistant (<code>/assistant</code>)</h3></div>',
        '          <div class="card"><h3>3. ☍ Mes Processus (<code>/processes</code>)</h3></div>',
        '          <div class="card"><h3>4. 🤖 Mes Agents (<code>/agents</code>)</h3></div>',
        '          <div class="card"><h3>5. 📦 Mes Espaces (<code>/spaces</code>)</h3></div>',
        '          <div class="card"><h3>6. 📊 Suivi des Coûts (<code>/finops</code>)</h3></div>',
        (
            '          <div class="card"><h3>7. 📜 Journal d\'Activité'
            " (<code>/activity</code>)</h3></div>"
        ),
        '          <div class="card"><h3>8. ⚙ Configuration (<code>/settings</code>)</h3></div>',
        (
            '          <div class="card"><h3>9. ❓ Aide (<code>/help</code>)'
            " &amp; <code>⌘K</code></h3></div>"
        ),
        "        </div>",
        "      </div>",
        "    </section>",
        '    <section id="pillar-architecture" class="pillar-panel"',
        '      data-testid="showcase-pillar-architecture">',
        '      <div class="card">',
        '        <span class="badge badge-cobalt">',
        "          3.1 · Monolithe Modulaire Hybride (TypeScript / Python 3.12+)",
        "        </span>",
        "        <h2>Isolation Hexagonale &amp; Contrats lint-imports</h2>",
        "        <p>",
        "          Stack : <code>pnpm 10.6</code>, <code>Turborepo 2.4</code>,",
        "          <code>uv 0.13.5</code>, <code>FastAPI</code>, <code>SQLAlchemy 2.1</code>,",
        "          <code>DBOS Transact 2.14</code>, <code>Dramatiq 2.1</code>,",
        "          <code>PostgreSQL 18</code>, <code>pgvector 0.8.7</code>,",
        "          <code>SeaweedFS 4.17</code>.",
        "        </p>",
        "      </div>",
        '      <div class="card card-violet">',
        '        <span class="badge badge-violet">',
        "          3.2 · Implémentation Technique des Garanties Human-Led",
        "        </span>",
        "        <p>",
        "          Signatures <code>SHA-256</code> dans <code>human_anchor_signatures</code>",
        "          (<code>ERR_HUMAN_ANCHOR_REQUIRED</code>),",
        "          <code>AdaptiveHumanGateService</code>, table <code>chunk_approvals</code>,",
        "          verrous Redis 7.4 <code>SET lock:step:&lt;id&gt; NX EX 900</code>",
        "          (<code>ResourceLeaseService</code>), <code>ExternalEditRebaser</code>",
        "          (<code>HUMAN_AMENDED_EXTERNAL</code>).",
        "        </p>",
        "      </div>",
        '      <div class="card card-emerald">',
        '        <span class="badge badge-emerald">',
        "          3.3 · Mécanismes Déterministes &amp; Sandboxes Paliers 1a, 1b et 2",
        "        </span>",
        "        <p>",
        "          <code>WorkflowYamlValidator</code>, <code>RunLockService</code>,",
        "          Sandbox Palier 1a <code>Wasmtime</code>",
        "          (<code>SubprocessTier1SandboxAdapter</code>),",
        "          Compilateur <code>Text-to-Starlark</code> &amp;",
        "          <code>StarlarkMechanismSandbox</code> O(n) anti-ReDoS, Sandbox Palier 2",
        "          <code>BimodalSandboxAdapter</code>, et",
        "          <code>AssistantCitationAndV5GuardService</code>.",
        "        </p>",
        "      </div>",
        '      <div class="card card-amber">',
        '        <span class="badge badge-amber">',
        "          3.4 · Mécanismes Probabilistes Gouvernés &amp; 3.5 · Sécurité",
        "        </span>",
        "        <p>",
        "          <code>AgenticGateService</code>, <code>CognitiveRouterService</code>,",
        "          <code>PostgreSQL 18</code> + <code>pgvector</code>",
        "          <code>halfvec(1024)</code> + <code>ts_rank_cd</code> fusionnés par",
        "          <code>RRF (k=60)</code>, <code>DBOS Transact</code>,",
        "          <code>blackboard_snapshots</code>,",
        "          <code>UpstreamChallengeAndReplayService</code>,",
        "          <code>OIDC PKCE</code> + <code>Argon2id</code>,",
        "          <code>EnvelopeVaultSecretProvider</code>, <code>PiiReversibleScrubber</code>.",
        "        </p>",
        "      </div>",
        "    </section>",
        '    <section id="pillar-changelog" class="pillar-panel"',
        '      data-testid="showcase-pillar-changelog">',
        '      <div class="stats-row">',
        '        <div class="stat-box">'
        f"<strong>{stats['activeRoutesCount']}</strong><span>Routes Web</span></div>",
        '        <div class="stat-box">'
        f"<strong>{stats['uiPrimitivesCount']}</strong><span>Primitives UI</span></div>",
        '        <div class="stat-box">'
        f"<strong>{stats['installedPacksCount']}</strong><span>Packs Métiers</span></div>",
        '        <div class="stat-box">'
        f"<strong>{stats['alembicMigrationsCount']}</strong><span>Migrations</span></div>",
        '        <div class="stat-box">'
        f"<strong>{stats['architectureDecisionsCount']}</strong><span>Décisions AD</span></div>",
        '        <div class="stat-box">'
        f"<strong>{stats['techLeadReportsCount']}</strong><span>Rapports</span></div>",
        "      </div>",
        '      <div class="bento-grid">',
        '        <div class="card">',
        "          <h3>Packs Métiers Installés</h3>",
        f"          {packs_html}",
        "          <h3>Décisions d'Architecture</h3>",
        f"          {decisions_html}",
        "        </div>",
        '        <div class="card">',
        "          <h3>Versions Verrouillées de la Stack</h3>",
        "          <table>",
        "            <thead><tr><th>Composant</th><th>Version</th></tr></thead>",
        f"            <tbody>{stack_rows_html}</tbody>",
        "          </table>",
        "        </div>",
        "      </div>",
        '      <div class="card">',
        f"        <h2>Chronologie des Rapports Tech Lead ({stats['techLeadReportsCount']})</h2>",
        '        <input type="text" class="search-input"',
        '          placeholder="Filtrer par mot-clé, story, date ou domaine..."',
        '          oninput="filterReports(this.value)" />',
        f'        <div id="reports-list">{reports_rows_html}</div>',
        "      </div>",
        "    </section>",
        "  </div>",
        "  <script>",
        "    function switchTab(targetId, btnEl) {",
        "      document.querySelectorAll('.pillar-panel').forEach(function(panel) {",
        "        panel.classList.remove('active');",
        "      });",
        "      document.querySelectorAll('.tab-btn[role=\"tab\"]').forEach(function(btn) {",
        "        btn.setAttribute('aria-selected', 'false');",
        "      });",
        "      var target = document.getElementById(targetId);",
        "      if (target) target.classList.add('active');",
        "      if (btnEl) btnEl.setAttribute('aria-selected', 'true');",
        "    }",
        "    function toggleTheme() {",
        "      var root = document.documentElement;",
        "      if (root.getAttribute('data-theme') === 'dark') {",
        "        root.removeAttribute('data-theme');",
        "      } else {",
        "        root.setAttribute('data-theme', 'dark');",
        "      }",
        "    }",
        "    function filterReports(query) {",
        "      var q = (query || '').toLowerCase().trim();",
        "      document.querySelectorAll('#reports-list .report-card').forEach(function(card) {",
        "        var haystack = card.getAttribute('data-search') || '';",
        "        card.style.display = (!q || haystack.indexOf(q) !== -1) ? 'block' : 'none';",
        "      });",
        "    }",
        "  </script>",
        "</body>",
        "</html>",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Synchronize ORCIA showcase manifest and standalone HTML site."
    )
    parser.add_argument(
        "--check",
        action="store_true",
        help="Verify that committed manifest and static HTML are up-to-date.",
    )
    args = parser.parse_args(argv)

    manifest = build_manifest_data()
    expected_ts = render_typescript_manifest(manifest)
    expected_html = render_standalone_html(manifest)

    if args.check:
        errors: list[str] = []
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from capabilities_registry import run_registry_check

        errors.extend(f"[capabilities.yaml] {e}" for e in run_registry_check())
        from capabilities_registry import capability_test_stats, load_registry

        stats = capability_test_stats(load_registry())
        print(
            f"[capabilities] {stats['with_tests']}/{stats['live']} capacités live référencent "
            f"au moins un test ({len(stats['without_tests'])} sans test)."
        )
        if not MANIFEST_TS_OUT.exists():
            errors.append(f"Missing generated manifest: {MANIFEST_TS_OUT}")
        elif MANIFEST_TS_OUT.read_text(encoding="utf-8") != expected_ts:
            errors.append(
                f"Out-of-sync TypeScript manifest: {MANIFEST_TS_OUT} (run `pnpm site:sync`)"
            )

        if not DOCS_HTML_OUT.exists():
            errors.append(f"Missing static HTML catalog: {DOCS_HTML_OUT}")
        elif DOCS_HTML_OUT.read_text(encoding="utf-8") != expected_html:
            errors.append(
                f"Out-of-sync static HTML catalog: {DOCS_HTML_OUT} (run `pnpm site:sync`)"
            )

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

    MANIFEST_TS_OUT.parent.mkdir(parents=True, exist_ok=True)
    MANIFEST_TS_OUT.write_text(expected_ts, encoding="utf-8")

    DOCS_HTML_OUT.parent.mkdir(parents=True, exist_ok=True)
    DOCS_HTML_OUT.write_text(expected_html, encoding="utf-8")

    DIST_HTML_OUT.parent.mkdir(parents=True, exist_ok=True)
    DIST_HTML_OUT.write_text(expected_html, encoding="utf-8")

    print(
        f"[site:sync OK] Generated:\n"
        f"  - {MANIFEST_TS_OUT.relative_to(REPO_ROOT)}\n"
        f"  - {DOCS_HTML_OUT.relative_to(REPO_ROOT)}\n"
        f"  - {DIST_HTML_OUT.relative_to(REPO_ROOT)}\n"
        f"  Stats: {manifest['stats']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
