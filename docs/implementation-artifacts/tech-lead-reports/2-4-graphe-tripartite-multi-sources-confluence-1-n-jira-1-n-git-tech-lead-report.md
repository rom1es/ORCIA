# Story 2.4 — Graphe Tripartite Multi-Sources (`Confluence 1..N <-> Jira 1..N <-> Git 1..N`) & Alertes `[STALE_WARNING]` (`data-freshness`)

- **Date** : 2026-10-25
- **Story / Clé Sprint** : `2-4-graphe-tripartite-multi-sources-confluence-1-n-jira-1-n-git` (`Epic 2`)
- **Auteur / Contexte** : Construction du Graphe Tripartite de Traçabilité Multi-Sources (`Confluence 1..N <-> Jira 1..N <-> Git 1..N <-> Ontologie`) par extraction regex des clés Jira (`[A-Z][A-Z0-9]+-[0-9]+`), brique `data-freshness` levant les alertes `[STALE_WARNING]` (`TTL_EXPIRED` ou `NEWER_JIRA_CONTRADICTION`) et qualification `[DOC_OBSOLETE_SUSPECTED]` lors d'un audit croisé Doc vs Code (`FR-11`, `AD-8`, `UX-DR12`, `UJ-10`).
- **Commits associés** : `Epic 2`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- Dans un projet *Brownfield*, une spécification Confluence peut diverger du code Git suite à une évolution livrée via un ticket Jira ultérieur à l'état `Done` sans que la page Confluence n'ait été mise à jour.
- Sans graphe tripartite reliant `Confluence <-> Jira <-> Git`, un agent d'audit qualifierait à tort l'écart comme un bug du code au lieu d'une documentation obsolète (`[DOC_OBSOLETE_SUSPECTED]`).

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_query`, `gitnexus_context`, `gitnexus_impact`)** :
  - Exécution de `gitnexus_impact` sur `packages/ui/src/index.ts`, `apps/web/src/components/ModuleWorkspaceView.tsx` et `apps/web/src/components/workspaceFixtures.ts`.
- **Exploration & Chiffres Clés (Base de Données / Conteneurs / Benchmark)** :
  - Extraction regex `\b([A-Z][A-Z0-9]+-[0-9]+)\b` déterministe préservant l'ordre d'apparition sans doublon.
- **Opportunités de Factorisation & Résorption de Dette Technique Naissante** :
  - Séparation de `HybridRagService` (`hybrid_rag_service.py`, `191 lignes`) et `TripartiteGraphAndFreshnessService` (`tripartite_and_freshness.py`, `299 lignes`) et extraction des fixtures UI dans `apps/web/src/components/ontologyFixtures.ts` (`103 lignes`).

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/...`, si applicable)
- `infra/migrations/versions/0009_story_2_4_tripartite_graph_and_stale_alerts.py` :
  - Création des tables `tripartite_trace_edges` (relations `DOCUMENTS`, `SPECIFIES`, `FIXES`, `BLOCKS`, `IMPLEMENTS_ISSUE`, `AFFECTS_CONCEPT`) et `kb_stale_alerts` (motifs `TTL_EXPIRED`, `NEWER_JIRA_CONTRADICTION`, `CODE_DRIFT_DETECTED` avec `diagnostic_marker = '[STALE_WARNING]'` et `impacted_run_ids_jsonb`).

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers (`packages/orcia-core/`, `apps/worker/`, `infra/sandbox/`)
- `packages/orcia-core/src/orcia_core/rag/tripartite_and_freshness.py` :
  - `extract_jira_issue_keys()`, `TripartiteGraphAndFreshnessService.register_cross_source_traceability()` (émettant les 6 types de relations `DOCUMENTS`, `SPECIFIES`, `FIXES`, `BLOCKS`, `IMPLEMENTS_ISSUE`, `AFFECTS_CONCEPT`), `evaluate_data_freshness()` (marque le document `is_stale=True` et émet `KbStaleAlertEntity` avec les `impacted_run_ids`) et `audit_doc_vs_code_divergence()` (`[DOC_OBSOLETE_SUSPECTED]` vs `[BUG_CODE_SUSPECTED]` vs `[ALIGNED]`).

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- `apps/api/src/orcia_api/routers/ontology_and_rag.py` & `ontology_rag_helpers.py` :
  - Endpoint `POST /api/v1/ontology-rag/tripartite/audit-doc-vs-code` et inclusion des arêtes tripartites et alertes `[STALE_WARNING]` dans `GET /api/v1/ontology-rag/state`.

### 2.4 Interface Utilisateur & Expérience (`apps/web/`)
- Sections `tripartite-graph-section` et `stale-alerts-section` dans `OntologyAndKbExplorerPanel` (`@orcia/ui`) utilisant les jetons sémantiques `var(--color-stale-crimson)` et `var(--color-stale-bg)` et proposant le bouton d'action de rejeu `stale-alert-replay-btn-*`.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature (Création / Modification / Refactoring) | Description synthétique |
| :--- | :--- | :--- |
| `infra/migrations/versions/0009_story_2_4_tripartite_graph_and_stale_alerts.py` | Création | Tables `tripartite_trace_edges` & `kb_stale_alerts` |
| `packages/orcia-core/src/orcia_core/rag/tripartite_and_freshness.py` | Création | `TripartiteGraphAndFreshnessService` (6 types de relations & `data-freshness`) |
| `apps/api/src/orcia_api/routers/ontology_rag_helpers.py` | Création | Convertisseurs de schémas Pydantic v2 pour l'ontologie et le graphe tripartite |
| `apps/web/src/components/ontologyFixtures.ts` | Création | Jeux d'essai d'ontologie et de graphe tripartite isolés pour `?fixture=test` |
| `infra/scripts/maintenance/05_backfill_ontology_and_rag_graph.py` | Création | Script de backfill idempotent `--dry-run` / `--apply` pour Epic 2 |
| `tests/unit/test_hybrid_rag_and_tripartite.py` | Création | Tests du graphe tripartite, `[STALE_WARNING]` et `[DOC_OBSOLETE_SUSPECTED]` |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Couverture de tests** : `97.40 %` sur `packages/orcia-core` ($\ge 90\%$ requis).
- **Performances mesurées** : Qualification tripartite Doc vs Code `< 0.2 ms`.
- **Qualité statique & Architecture** :
  - `ruff check` & `ruff format --check` : `0 warning`
  - `mypy --strict` & `pnpm typecheck` : `0 error`
  - `lint_spine.py` : `ok: true, 0 findings`
  - `gitnexus_detect_changes()` : Périmètre vérifié et conforme.

### 3.3 Validation & Procédure de Test (5 Couches `AD-17`)
- **Couche 1 — Tests Unitaires & Propriétés (`pytest` + `hypothesis`, `Vitest`)** : `test_tripartite_graph_jira_extraction_stale_warning_and_doc_obsolete_audit` + `i18n-and-shell.test.tsx`.
- **Couche 2 — Tests d'Intégration (`testcontainers-python` : PostgreSQL 18 + `pgvector`, Redis 7.4, MinIO)** : `test_real_containers.py` (révision `0009_story_2_4` + `05_backfill_ontology_and_rag_graph.py`).
- **Couche 3 — Tests de Contrat API (`openapi-typescript` 0-diff + `Schemathesis`)** : `test_openapi_contract.py`.
- **Couche 4 — Tests d'Orchestration IA (`DeterministicCassetteLLM`)** : Validation déterministe sans appel externe.
- **Couche 5 — Tests E2E & Accessibilité (`@playwright/test` Desktop `1440x900` & Mobile `390x844`)** : `apps/web/e2e/shell.spec.ts`.
