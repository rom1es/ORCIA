# Story 2.3 — Indexation Différenciée Incrémentale Multi-Sources & RAG Hybride (`halfvec(1024)` + BM25)

- **Date** : 2026-10-25
- **Story / Clé Sprint** : `2-3-indexation-différenciée-incrémentale-multi-sources-n-conflue` (`Epic 2`)
- **Auteur / Contexte** : Implémentation des 3 régimes d'indexation différenciés (`DOC_PARENT_CHILD` pour `1..N confluence://` CQL et `1..N jira://` JQL de référence avec en-tête contextuel `[Alias Source : Espace/Projet > Parent > Titre | Concepts Ontologie]`, `CODE_AST_GRAPH` pour `1..N git://` par symbole AST + graphe `CodeGraphEdge`, et `DB_DDL_ONLY` pour `db://` rejetant les données transactionnelles avec `HTTP 422 ERR_DDL_ONLY_TRANSACTIONAL_DATA_FORBIDDEN`), du moteur `HybridRagService` (`halfvec(1024)` + BM25 via *Reciprocal Rank Fusion* `< 50 ms`) et du worker idempotent Dramatiq `docling_indexer_actor` (`FR-10`, `AD-8`, `NFR-PERF-4`).
- **Commits associés** : `Epic 2`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- Un découpage générique à taille fixe dégrade la pertinence sur les pages Confluence hiérarchiques, casse la syntaxe des fonctions/classes Git et risque d'indexer des lignes transactionnelles métier sensibles issues des bases `db://`.
- Il faut combiner recherche vectorielle `pgvector halfvec(1024)` (HNSW) et recherche lexicale exacte `BM25` (`tsvector` GIN) via *Reciprocal Rank Fusion* (`RRF`) en moins de `50 ms`, tout en appliquant le filtrage d'habilitation *Passthrough* par source.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_query`, `gitnexus_context`, `gitnexus_impact`)** :
  - Exécution de `gitnexus_impact` sur `apps/worker/src/orcia_worker/__init__.py`, `packages/orcia-core/src/orcia_core/domain/exceptions.py` et `apps/api/src/orcia_api/main.py`.
- **Exploration & Chiffres Clés (Base de Données / Conteneurs / Benchmark)** :
  - Validation sur conteneur réel `pgvector/pgvector:pg18` : support natif de `halfvec(1024)` avec index `USING hnsw (embedding halfvec_cosine_ops)` et colonne générée `search_tsv TSVECTOR` avec index `USING gin (search_tsv)`.
  - Temps d'exécution mesuré de `search_hybrid_rrf` : `< 2 ms` (`NFR-PERF-4 < 50 ms`).
- **Opportunités de Factorisation & Résorption de Dette Technique Naissante** :
  - Découpage du module `packages/orcia-core/src/orcia_core/rag/` en 5 fichiers modulaires (< 350 lignes) : `models.py` (`158 lignes`), `vector_and_ast.py` (`144 lignes`), `indexer_and_rrf.py` (`345 lignes`), `hybrid_rag_service.py` (`191 lignes`) et `tripartite_and_freshness.py` (`299 lignes`).
  - Découpage du routeur FastAPI en `apps/api/src/orcia_api/routers/ontology_and_rag.py` (`244 lignes`) et `ontology_rag_helpers.py` (`174 lignes`).

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/...`, si applicable)
- `infra/migrations/versions/0008_story_2_3_hybrid_rag_halfvec_bm25_and_code_graph.py` :
  - Création des tables `kb_documents`, `kb_chunks` (avec `embedding halfvec(1024)` indexé en HNSW et `search_tsv TSVECTOR` indexé en GIN) et `code_graph_edges`.

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers (`packages/orcia-core/`, `apps/worker/`, `infra/sandbox/`)
- `packages/orcia-core/src/orcia_core/rag/indexer_and_rrf.py` & `vector_and_ast.py` :
  - `DifferentiatedIncrementalIndexer` : Régime 1a (`index_confluence_parent_child` CQL `orcia-kb`), Régime 1b (`index_jira_reference_issue` JQL types de référence), Régime 2 (`index_git_ast_and_code_graph` AST fonctions/classes/méthodes + repli `SyntaxError` + `CodeGraphEdgeEntity`), Régime 3 (`index_db_ddl_schema_only` nettoyant les commentaires SQL et levant `DdlOnlyTransactionalDataError` sur `INSERT/UPDATE/DELETE/COPY/SELECT`).
- `apps/worker/src/orcia_worker/docling_indexer.py` :
  - Acteur Dramatiq idempotent `docling_indexer_actor` supportant les 3 régimes (`DOC_PARENT_CHILD`, `CODE_AST_GRAPH`, `DB_DDL_ONLY`) et ignorant toute ré-indexation lorsque l'empreinte `content_sha256` est inchangée (`already_indexed=True`).

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- `apps/api/src/orcia_api/routers/ontology_and_rag.py` :
  - Endpoints `POST /api/v1/ontology-rag/rag/search` (avec expansion ontologique et filtrage *Passthrough* `allowed_datasource_aliases`) et `POST /api/v1/ontology-rag/rag/index-db-ddl` (garde `ObserverModeReadOnlyError` `HTTP 403` + `HTTP 422 ERR_DDL_ONLY_TRANSACTIONAL_DATA_FORBIDDEN`).

### 2.4 Interface Utilisateur & Expérience (`apps/web/`)
- Champ de recherche RAG Hybride (`data-testid="hybrid-rag-search-input"`) intégré dans `OntologyAndKbExplorerPanel` (`@orcia/ui`) filtrant dynamiquement les relations et concepts affichés.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature (Création / Modification / Refactoring) | Description synthétique |
| :--- | :--- | :--- |
| `infra/migrations/versions/0008_story_2_3_hybrid_rag_halfvec_bm25_and_code_graph.py` | Création | Tables `kb_documents`, `kb_chunks` (`halfvec(1024)` HNSW + GIN `tsvector`), `code_graph_edges` |
| `packages/orcia-core/src/orcia_core/rag/vector_and_ast.py` | Création | Vecteurs `halfvec(1024)` déterministes, en-tête contextuel `AD-8` et découpeur AST |
| `packages/orcia-core/src/orcia_core/rag/indexer_and_rrf.py` | Création | Indexeur différencié 3 régimes (`DOC_PARENT_CHILD`, `CODE_AST_GRAPH`, `DB_DDL_ONLY`) |
| `packages/orcia-core/src/orcia_core/rag/hybrid_rag_service.py` | Création | `HybridRagService` (`search_hybrid_rrf`, purge des arêtes AST obsolètes) |
| `apps/worker/src/orcia_worker/docling_indexer.py` | Création | Acteur Dramatiq idempotent `docling_indexer_actor` |
| `tests/unit/test_hybrid_rag_and_tripartite.py` | Création | Tests des 3 régimes, RRF `< 50 ms`, filtrage Passthrough et idempotence |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Couverture de tests** : `97.40 %` sur `packages/orcia-core` ($\ge 90\%$ requis).
- **Performances mesurées** : Recherche RRF (`halfvec(1024)` + BM25) `< 2 ms` (`< 50 ms` requis).
- **Qualité statique & Architecture** :
  - `ruff check` & `ruff format --check` : `0 warning`
  - `mypy --strict` & `pnpm typecheck` : `0 error`
  - `lint_spine.py` : `ok: true, 0 findings`
  - `gitnexus_detect_changes()` : Périmètre vérifié et conforme.

### 3.3 Validation & Procédure de Test (5 Couches `AD-17`)
- **Couche 1 — Tests Unitaires & Propriétés (`pytest` + `hypothesis`, `Vitest`)** : `test_3_regime_differentiated_indexing_and_ddl_transactional_guard`, `test_hybrid_rrf_search_parent_injection_passthrough_and_latency`, `test_idempotent_docling_indexer_actor_skips_unchanged_sha256`.
- **Couche 2 — Tests d'Intégration (`testcontainers-python` : PostgreSQL 18 + `pgvector`, Redis 7.4, MinIO)** : `test_real_containers.py` (insertion `CAST(:embedding AS halfvec(1024))` et index HNSW/GIN réels).
- **Couche 3 — Tests de Contrat API (`openapi-typescript` 0-diff + `Schemathesis`)** : `test_openapi_contract.py`.
- **Couche 4 — Tests d'Orchestration IA (`DeterministicCassetteLLM`)** : Validation déterministe sans appel externe.
- **Couche 5 — Tests E2E & Accessibilité (`@playwright/test` Desktop `1440x900` & Mobile `390x844`)** : `apps/web/e2e/shell.spec.ts`.
