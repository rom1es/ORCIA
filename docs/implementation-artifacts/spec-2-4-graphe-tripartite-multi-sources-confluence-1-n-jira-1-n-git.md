---
title: 'Story 2.4: Graphe Tripartite Multi-Sources (Confluence 1..N <-> Jira 1..N <-> Git 1..N) & Alertes [STALE_WARNING] (data-freshness)'
type: 'feature'
created: '2026-10-25'
status: 'done'
route: 'dispatch'
baseline_commit: 'd0230a1e8f92e15a7822e4f0e12d4a50b18c0e11' # pragma: allowlist secret
review_loop_iteration: 1
context:
  - '{project-root}/AGENTS.md'
  - '{project-root}/docs/implementation-artifacts/epic-2-context.md'
---

<frozen-after-approval reason="human-owned intent — do not modify unless human renegotiates">

## Intent

**Problem:** Dans un projet *Brownfield*, une spécification Confluence peut diverger du code Git suite à une évolution livrée via un ticket Jira ultérieur à l'état `Done` sans que la page Confluence n'ait été mise à jour. Sans graphe tripartite reliant `Confluence <-> Jira <-> Git`, un agent d'audit qualifierait à tort l'écart comme un bug du code au lieu d'une documentation obsolète (`[DOC_OBSOLETE_SUSPECTED]`).

**Approach:** Créer la révision Alembic `0009_story_2_4_tripartite_graph_and_stale_alerts.py` (`tripartite_trace_edges`, `kb_stale_alerts`), implémenter dans `packages/orcia-core/rag/tripartite_and_freshness.py` l'extracteur regex de clés Jira (`extract_jira_issue_keys`), le graphe tripartite à 6 types de relations (`DOCUMENTS`, `SPECIFIES`, `FIXES`, `BLOCKS`, `IMPLEMENTS_ISSUE`, `AFFECTS_CONCEPT`), la brique `data-freshness` (`evaluate_data_freshness` émettant `[STALE_WARNING]`) et l'audit croisé `audit_doc_vs_code_divergence` (`[DOC_OBSOLETE_SUSPECTED]` vs `[BUG_CODE_SUSPECTED]` vs `[ALIGNED]`), livrer le script de maintenance `05_backfill_ontology_and_rag_graph.py` (`--dry-run` / `--apply`), et exposer le graphe tripartite et les alertes de fraîcheur dans `OntologyAndKbExplorerPanel` (`@orcia/ui`).

## Boundaries & Constraints

**Always:**
- Émettre les 6 types de relations tripartites (`DOCUMENTS`, `SPECIFIES`, `FIXES`, `BLOCKS`, `IMPLEMENTS_ISSUE`, `AFFECTS_CONCEPT`) et lever `ResourceNotFoundError` si `mark_document_stale` est appelé sur un `doc_key` inconnu.
- Tester `05_backfill_ontology_and_rag_graph.py` en mode `--dry-run` (0 ligne persistée) et `--apply` sur PostgreSQL 18 (`testcontainers`).

**Never:**
- Ne jamais qualifier comme `[BUG_CODE_SUSPECTED]` une divergence Doc vs Code justifiée par un ticket Jira ultérieur à l'état `Done` lié au commit Git (`[DOC_OBSOLETE_SUSPECTED]`).

</frozen-after-approval>

## Code Map

- `infra/migrations/versions/0009_story_2_4_tripartite_graph_and_stale_alerts.py` — Tables `tripartite_trace_edges` et `kb_stale_alerts`.
- `packages/orcia-core/src/orcia_core/rag/tripartite_and_freshness.py` — `TripartiteGraphAndFreshnessService` et `extract_jira_issue_keys`.
- `infra/scripts/maintenance/05_backfill_ontology_and_rag_graph.py` — Backfill idempotent `--dry-run` / `--apply` pour l'Epic 2.
- `packages/ui/src/shell/OntologyAndKbExplorerPanel.tsx` — Sections `tripartite-graph-section` et `stale-alerts-section` avec action de rejeu `stale-alert-replay-btn-*`.
- `tests/unit/test_hybrid_rag_and_tripartite.py` & `tests/integration/test_real_containers.py` — Tests unitaires, FastAPI et PostgreSQL 18.
