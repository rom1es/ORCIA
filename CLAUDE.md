# Protocole Tech Lead / Dev Senior & Rapport Pérenne d'Implémentation (Obligatoire)

Pour **chaque User Story (`Story N.M`)** ET pour **chaque demande qui nécessite des ajustements, correctifs ou évolutions d'ORCIA**, l'agent DOIT impérativement :

1. **Générer AVANT d'effectuer toute modification un Rapport Tech Lead** dans `docs/implementation-artifacts/tech-lead-reports/` en utilisant le gabarit officiel [`docs/implementation-artifacts/TECH-LEAD-REPORT-TEMPLATE.md`](file:///home/romain/Documents/Projects/ORCIA/docs/implementation-artifacts/TECH-LEAD-REPORT-TEMPLATE.md) :
   - **Nommage du fichier** : préfixer le nom du fichier avec la date du jour au format `YYYY-MM-DD` complété d'un descriptif court des changements en `kebab-case` :
     `docs/implementation-artifacts/tech-lead-reports/{YYYY-MM-DD}-{descriptif-court}-tech-lead-report.md` (ou `{story-key}-tech-lead-report.md` pour une Story du sprint).
   - **Rédaction pré-implémentation obligatoire** : renseigner les **Sections 1 (`Analyse du Besoin & Étude d'Impact Tech Lead`)** et **2 (`Plan d'Implémentation`)** **avant** de modifier le moindre fichier de code, puis compléter la **Section 3 (`Bilan des Modifications & Résultats`)** après passage des portes de vérification.
2. **Respecter les 4 Garde-Fous de Câblage Vertical (Anti-Silos UI / API / SQL)** :
   - **Zéro Adaptateur SQL Orphelin** : toute fonction SQL (`_internal/sql_*.py`, `adapters/postgres_*.py`) doit être effectivement appelée par `apps/api` ou `apps/worker` (vérifié par `gitnexus_impact({direction: "upstream", repo: "ORCIA"})` $\rightarrow$ `impactedCount >= 1` hors `tests/`).
   - **Test d'Intégration Vertical `HTTP ➔ PostgreSQL 18`** : les tests d'intégration `testcontainers` doivent appeler la route FastAPI et vérifier l'écriture réelle en base par `SELECT`.
   - **Zéro Store Métier `useState` Éphémère & Test de « Survie au F5 » (`apps/web`)** : tout état métier modifié dans `apps/web` doit persister via `@orcia/api-client`, s'hydrater au démarrage via `GET`, et être testé avec démontage/remontage complet (`unmount()` puis `render()`).
   - **Réinitialisation Jour 0 (`pnpm db:reset`)** : utiliser `.venv/bin/python infra/scripts/maintenance/09_reset_db_first_boot.py --apply` (`pnpm db:reset`) pour revenir à l'état du 1er démarrage (`0` compte dans `users`).
   - Consulter [`GEMINI.md`](file:///home/romain/Documents/Projects/ORCIA/GEMINI.md) pour l'ensemble des règles d'architecture (`AD-1` à `AD-19`) et des 11 règles fondamentales UX/UI.

---

<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **ORCIA** (541 symbols, 699 relationships, 17 execution flows).

> Index stale? Run `node .gitnexus/run.cjs analyze --index-only` from the project root — it auto-selects an available runner. No `.gitnexus/run.cjs` yet? Bootstrap with `npx`, `bunx`, or `pnpm dlx` — e.g. `bunx gitnexus@latest analyze` (npm 11 npx crash; #1939).

## Always Do

- **MUST run impact before editing.** Use `impact({target: "symbolName", direction: "upstream"})` or `node .gitnexus/run.cjs impact "symbolName" --direction upstream --repo .`; report callers, processes, and risk. Never substitute grep for graph analysis.
- **MUST analyze graph changes before committing.** Use `detect_changes({scope: "all"})` (MCP) or `node .gitnexus/run.cjs detect-changes --scope all --repo .` (CLI fallback). `partial: true` or `truncated: true` is not a clean check — a zero means unseen, not unaffected; re-run it. For regression review: `detect_changes({scope: "compare", base_ref: "main"})` or `node .gitnexus/run.cjs detect-changes --scope compare --base-ref "main" --repo .`.
- MUST warn on HIGH/CRITICAL `risk` pre-edit; never use `riskSharedAxes` to waive a HIGH/CRITICAL `risk` warning. Compare File/symbol: MCP File omits axes; Graph-RAG expands File.
- **MUST treat `risk: UNKNOWN` as unresolved, not as low.** An empty caller set is not evidence the symbol is unused — it can also mean the callers are not resolvable by the index (plain-object property access, dynamic dispatch, cross-language calls). `impact` pairs `UNKNOWN` with a `riskNote` saying so. Confirm with a text search before treating the symbol as safe to change or delete; do not proceed on the strength of a zero.
- **MUST use `query({search_query: "concept"})` for concepts/flows, `context({name: "symbolName"})` for a named symbol, or `impact` for blast radius, on read-only callers, dependencies, imports, or execution flow.** Graph first; text search only for empty/`UNKNOWN`/literals.
- For security review, `explain({target: "fileOrSymbol"})` lists taint findings (source→sink flows; needs `analyze --pdg`).

## Never Do

- NEVER edit a function, class, or method before MCP/CLI impact analysis.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis, and never read `UNKNOWN` as an all-clear — it means the walk could not answer, which is the one verdict that requires confirming by other means.
- NEVER rename symbols with find-and-replace — use `rename` which understands the call graph.
- NEVER commit before MCP/CLI graph change analysis.

## Resources

| Resource | Use for |
| --- | --- |
| `gitnexus://repo/ORCIA/context` | Codebase overview, check index freshness |
| `gitnexus://repo/ORCIA/clusters` | All functional areas |
| `gitnexus://repo/ORCIA/processes` | All execution flows |
| `gitnexus://repo/ORCIA/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
| --- | --- |
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->
