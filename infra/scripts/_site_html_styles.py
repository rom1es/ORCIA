"""Static CSS and client JS fragments for standalone ORCIA showcase HTML."""

from __future__ import annotations

STANDALONE_STYLE_BLOCK = """  <style>
    :root {
      --color-surface-bg: #EAF2FB;
      --color-surface-card: #FFFFFF;
      --color-surface-elevated: #F8FAFC;
      --color-foreground: #0F172A;
      --color-muted-foreground: #475569;
      --color-border: #E2E8F0;
      --color-primary-cobalt: #2563EB;
      --color-primary-foreground: #FFFFFF;
      --color-action-primary-subtle: #EFF6FF;
      --color-human-led-violet: #6D28D9;
      --color-human-led-bg: #F5F3FF;
      --color-arbitration-amber: #D97706;
      --color-arbitration-bg: #FFFBEB;
      --color-gate-emerald: #059669;
      --color-gate-emerald-bg: #ECFDF5;
      --color-stale-crimson: #DC2626;
      --color-stale-bg: #FEF2F2;
      --font-sans: "Inter", "Geist Sans", system-ui, sans-serif;
      --font-mono: "JetBrains Mono", "Geist Mono", monospace;
      --radius-sm: 6px; --radius-md: 10px; --radius-lg: 14px;
      --shadow-card: 0 4px 16px rgba(15, 23, 42, 0.05);
    }
    [data-theme="dark"] {
      --color-surface-bg: #0B0F17; --color-surface-card: #111827;
      --color-surface-elevated: #1E293B; --color-foreground: #F8FAFC;
      --color-muted-foreground: #94A3B8; --color-border: #1E293B;
      --color-primary-cobalt: #6366F1; --color-action-primary-subtle: #1E293B;
      --color-human-led-bg: #2E1065; --color-arbitration-bg: #451A03;
      --color-gate-emerald-bg: #064E3B;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0; font-family: var(--font-sans);
      background-color: var(--color-surface-bg);
      color: var(--color-foreground); line-height: 1.6; font-size: 14px;
    }
    .container { max-width: 1280px; margin: 0 auto; padding: 24px; }
    .hero {
      background-color: var(--color-surface-card);
      border: 1px solid var(--color-border); border-radius: var(--radius-lg);
      padding: 24px; box-shadow: var(--shadow-card); margin-bottom: 20px;
      display: flex; justify-content: space-between;
      align-items: flex-start; gap: 16px; flex-wrap: wrap;
    }
    .hero h1 { margin: 0 0 8px 0; font-size: 24px; }
    .hero p { margin: 0; color: var(--color-muted-foreground); max-width: 820px; }
    .tabs { display: flex; flex-wrap: wrap; gap: 10px; margin-bottom: 20px; }
    .tab-btn {
      padding: 10px 16px; border-radius: var(--radius-sm);
      border: 1px solid #93C5FD; background-color: #DBEAFE;
      color: #1E3A8A; font-weight: 600; cursor: pointer;
    }
    .tab-btn[aria-selected="true"], .tab-btn:focus-visible {
      background-color: var(--color-primary-cobalt);
      border-color: var(--color-primary-cobalt);
      color: var(--color-primary-foreground);
    }
    .pillar-panel { display: none; }
    .pillar-panel.active { display: block; }
    .bento-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(360px, 1fr));
      gap: 18px; margin-bottom: 20px;
    }
    .card {
      background-color: var(--color-surface-card);
      border: 1px solid var(--color-border); border-radius: var(--radius-lg);
      padding: 20px; box-shadow: var(--shadow-card); margin-bottom: 18px;
    }
    .card h2 { margin-top: 0; font-size: 18px; }
    .card h3 { margin-top: 0; font-size: 15.5px; }
    .card-violet {
      border-left: 4px solid var(--color-human-led-violet);
      background-color: var(--color-human-led-bg);
    }
    .card-emerald {
      border-left: 4px solid var(--color-gate-emerald);
      background-color: var(--color-gate-emerald-bg);
    }
    .card-amber {
      border-left: 4px solid var(--color-arbitration-amber);
      background-color: var(--color-arbitration-bg);
    }
    .badge {
      display: inline-block; padding: 3px 9px;
      border-radius: 9999px; font-size: 11.5px; font-weight: 600;
    }
    .badge-cobalt {
      background-color: var(--color-action-primary-subtle);
      color: var(--color-primary-cobalt);
    }
    .badge-violet {
      background-color: var(--color-human-led-bg);
      color: var(--color-human-led-violet);
      border: 1px solid var(--color-human-led-violet);
    }
    .badge-emerald {
      background-color: var(--color-gate-emerald-bg);
      color: var(--color-gate-emerald);
    }
    .badge-amber {
      background-color: var(--color-arbitration-bg);
      color: var(--color-arbitration-amber);
    }
    .mono-code {
      font-family: var(--font-mono); font-size: 12px;
      background-color: var(--color-surface-elevated);
      padding: 2px 6px; border-radius: 4px; border: 1px solid var(--color-border);
    }
    .stats-row {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
      gap: 12px; margin-bottom: 20px;
    }
    .stat-box {
      background-color: var(--color-surface-card);
      border: 1px solid var(--color-border); border-radius: var(--radius-md);
      padding: 14px; text-align: center;
    }
    .stat-box strong {
      display: block; font-size: 22px; color: var(--color-primary-cobalt);
    }
    table { width: 100%; border-collapse: collapse; font-size: 13px; }
    th, td {
      text-align: left; padding: 8px 10px; border-bottom: 1px solid var(--color-border);
    }
    .report-card {
      border: 1px solid var(--color-border); border-radius: var(--radius-md);
      padding: 14px; margin-bottom: 12px; background-color: var(--color-surface-elevated);
    }
    .report-card h4 { margin: 8px 0 4px 0; font-size: 14px; }
    .report-card p { margin: 0; font-size: 13px; color: var(--color-muted-foreground); }
    .report-meta { display: flex; gap: 8px; align-items: center; flex-wrap: wrap; }
    .ad-pill, .pack-item {
      padding: 8px 12px; border: 1px solid var(--color-border);
      border-radius: var(--radius-sm); margin-bottom: 8px;
      display: flex; gap: 10px; align-items: center; flex-wrap: wrap;
      background-color: var(--color-surface-elevated);
    }
    .search-input {
      width: 100%; padding: 9px 12px; border-radius: var(--radius-sm);
      border: 1px solid var(--color-border); background-color: var(--color-surface-card);
      color: var(--color-foreground); margin-bottom: 14px;
    }
  </style>"""

STANDALONE_SCRIPT_BLOCK = """  <script>
    function switchTab(targetId, btnEl) {
      document.querySelectorAll('.pillar-panel').forEach(function(p) {
        p.classList.remove('active');
      });
      document.querySelectorAll('.tab-btn[role="tab"]').forEach(function(b) {
        b.setAttribute('aria-selected', 'false');
      });
      var target = document.getElementById(targetId);
      if (target) target.classList.add('active');
      if (btnEl) btnEl.setAttribute('aria-selected', 'true');
    }
    function toggleTheme() {
      var root = document.documentElement;
      if (root.getAttribute('data-theme') === 'dark') { root.removeAttribute('data-theme'); }
      else { root.setAttribute('data-theme', 'dark'); }
    }
    function filterReports(query) {
      var q = (query || '').toLowerCase().trim();
      document.querySelectorAll('#reports-list .report-card').forEach(function(card) {
        var haystack = card.getAttribute('data-search') || '';
        card.style.display = (!q || haystack.indexOf(q) !== -1) ? 'block' : 'none';
      });
    }
  </script>"""
