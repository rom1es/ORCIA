"""Dynamic HTML renderer for standalone ORCIA showcase (`docs/site-catalog/index.html`)."""

from __future__ import annotations

import html
from typing import Any

from _site_html_styles import STANDALONE_SCRIPT_BLOCK, STANDALONE_STYLE_BLOCK
from _site_html_template import (
    PILLAR_ARCHITECTURE_HTML,
    PILLAR_FEATURES_HTML,
    PILLAR_MACRO_HTML,
)


def _format_report_card_html(report: dict[str, str]) -> str:
    search_val = html.escape(
        f"{report['date']} {report['phaseOrStory']} {report['domain']} {report['summary']}".lower()
    )
    date_esc = html.escape(report["date"])
    story_esc = html.escape(report["phaseOrStory"])
    file_esc = html.escape(report["reportFile"])
    domain_esc = html.escape(report["domain"])
    summary_esc = html.escape(report["summary"])
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


def _render_hero_and_nav(last_synced_date: str, reports_count: int) -> list[str]:
    return [
        '    <header class="hero">',
        "      <div>",
        f'        <span class="badge badge-cobalt">ORCIA · Synchronisé '
        f"({html.escape(last_synced_date)})</span>",
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
        f"        4. 🔄 Historique des Évolutions ({reports_count})",
        "      </button>",
        "    </nav>",
    ]


def _render_changelog_pillar(manifest: dict[str, Any]) -> list[str]:
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
    return [
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
        *([f"          {packs_html}"] if packs_html.strip() else []),
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
    ]


def render_standalone_html(manifest: dict[str, Any]) -> str:
    """Render the self-contained HTML5 showcase catalog from manifest data."""
    stats = manifest["stats"]
    lines = [
        "<!DOCTYPE html>",
        '<html lang="fr">',
        "<head>",
        '  <meta charset="UTF-8" />',
        '  <meta name="viewport" content="width=device-width, initial-scale=1.0" />',
        "  <title>ORCIA — Site de Présentation &amp; Documentation Vivante</title>",
        STANDALONE_STYLE_BLOCK,
        "</head>",
        "<body>",
        '  <div class="container">',
        *_render_hero_and_nav(manifest["lastSyncedDate"], stats["techLeadReportsCount"]),
        PILLAR_MACRO_HTML,
        PILLAR_FEATURES_HTML,
        PILLAR_ARCHITECTURE_HTML,
        *_render_changelog_pillar(manifest),
        "  </div>",
        STANDALONE_SCRIPT_BLOCK,
        "</body>",
        "</html>",
        "",
    ]
    return "\n".join(line.rstrip() for line in lines)
