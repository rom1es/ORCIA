# Story 2.1 — Modélisation Relationnelle-Graphe de l'Ontologie à 4 Niveaux & Triple Exécution Active

- **Date** : 2026-10-25
- **Story / Clé Sprint** : `2-1-modélisation-relationnelle-graphe-de-l-ontologie-à-4-niveaux` (`Epic 2`)
- **Auteur / Contexte** : Implémentation de l'ontologie relationnelle-graphe à 4 niveaux (`1_ENTERPRISE`, `2_DOMAIN`, `3_TEAM` le long de l'arbre `Équipe Parente -> Sous-Équipe`, `3_WORKSPACE`, `4_RUN_EPHEMERAL`), de la résolution récursive CTE (`< 15 ms`), de la protection des axiomes `immutable: true` (`HTTP 422 ERR_ONTOLOGY_CONFLICT`) et de la triple exécution active (`FR-8`, `AD-7`, `NFR-PERF-3`, `UX-DR12`).
- **Commits associés** : `Epic 2`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- Les équipes métier, architecture et engineering utilisent des vocabulaires différents pour désigner les mêmes actifs critiques, ce qui provoque des ambiguïtés dans les livrables du Blackboard et les requêtes RAG.
- Il faut modéliser une ontologie hiérarchique à 4 niveaux (`1_ENTERPRISE -> 2_DOMAIN -> 3_TEAM [Parent -> Sous-Équipe] -> 3_WORKSPACE -> 4_RUN_EPHEMERAL`) résolue en moins de `15 ms` et active sur 3 plans : validation de schéma/cardinalité du Blackboard, traduction par Profil Humain (`6` profils) et expansion sémantique des requêtes RAG.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_query`, `gitnexus_context`, `gitnexus_impact`)** :
  - Exécution de `gitnexus_impact` sur `OrciaErrorCode` (`packages/orcia-core/src/orcia_core/domain/exceptions.py`), `create_app` (`apps/api/src/orcia_api/main.py`) et `createOrciaApiClient` (`packages/api-client/src/index.ts`).
- **Exploration & Chiffres Clés (Base de Données / Conteneurs / Benchmark)** :
  - Temps de résolution mesuré pour `OntologyHierarchyResolver.resolve_effective_ontology` : `< 0.5 ms` en mémoire et `< 5 ms` via CTE récursive PostgreSQL 18 (`NFR-PERF-3 < 15 ms`).
- **Opportunités de Factorisation & Résorption de Dette Technique Naissante** :
  - Découpage strict du domaine `packages/orcia-core/src/orcia_core/ontology/` en 3 modules dédiés (`models.py` 161 lignes, `resolver.py` 314 lignes, `impact_and_promotion.py` 304 lignes), tous sous le seuil de `350 lignes`.
  - État par défaut 100 % vide (`build_empty_ontology_service()`), jeu de données déterministe isolé dans `build_seeded_ontology_service()` pour les tests automatisés.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/...`, si applicable)
- `infra/migrations/versions/0006_story_2_1_ontology_4_levels.py` :
  - Création des tables `ontology_concepts`, `ontology_relations` et `ontology_axioms` avec clés primaires `UUIDv7` et index `idx_ontology_concepts_level_scope_term`, `idx_ontology_relations_source_target` et `idx_ontology_axioms_concept_level`.
  - Réversibilité complète vérifiée (`upgrade()` et `downgrade()`).

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers (`packages/orcia-core/`, `apps/worker/`, `infra/sandbox/`)
- `packages/orcia-core/src/orcia_core/ontology/resolver.py` :
  - `build_ontology_resolution_cte_sql()`, `OntologyHierarchyResolver` (fusion des 4 niveaux avec héritage `Sous-Équipe -> Équipe Parente`, rejet `OntologyConflictError` sur axiome `immutable: true`, validation Blackboard et expansion RAG) et `ProfileSemanticTranslator`.

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- `apps/api/src/orcia_api/routers/ontology_and_rag.py` :
  - Endpoints `GET /api/v1/ontology-rag/state`, `POST /api/v1/ontology-rag/ontology/resolve` et `POST /api/v1/ontology-rag/ontology/concepts` (retourne `HTTP 422 ERR_ONTOLOGY_CONFLICT` avec `trace_id` en cas de violation d'un axiome `immutable: true`).
- `packages/api-client/` :
  - Régénération `0-diff` via `.venv/bin/python scripts/export_openapi.py`.

### 2.4 Interface Utilisateur & Expérience (`apps/web/`)
- Composant `@orcia/ui` `OntologyAndKbExplorerPanel` (`packages/ui/src/shell/OntologyAndKbExplorerPanel.tsx`) affichant les colonnes `1_ENTERPRISE` à `4_RUN_EPHEMERAL`, le sélecteur de traduction par Profil Humain et l'état vide par défaut (`ontology-kb-empty-state`).

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature (Création / Modification / Refactoring) | Description synthétique |
| :--- | :--- | :--- |
| `infra/migrations/versions/0006_story_2_1_ontology_4_levels.py` | Création | Tables `ontology_concepts`, `ontology_relations`, `ontology_axioms` |
| `packages/orcia-core/src/orcia_core/ontology/models.py` | Création | Entités immuables de l'ontologie à 4 niveaux |
| `packages/orcia-core/src/orcia_core/ontology/resolver.py` | Création | Résolveur CTE, `ProfileSemanticTranslator` et triple exécution active |
| `tests/unit/test_ontology_and_what_if.py` | Création | Tests unitaires, propriétés `hypothesis` et contrat FastAPI 422 |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Couverture de tests** : `97.40 %` sur `packages/orcia-core` ($\ge 90\%$ requis).
- **Performances mesurées** : Résolution hiérarchique 4 niveaux `< 1 ms` (`< 15 ms` requis).
- **Qualité statique & Architecture** :
  - `ruff check` & `ruff format --check` : `0 warning`
  - `mypy --strict` & `pnpm typecheck` : `0 error`
  - `lint_spine.py` : `ok: true, 0 findings`
  - `gitnexus_detect_changes()` : Périmètre vérifié et conforme.

### 3.3 Validation & Procédure de Test (5 Couches `AD-17`)
- **Couche 1 — Tests Unitaires & Propriétés (`pytest` + `hypothesis`, `Vitest`)** : `test_ontology_and_what_if.py` + `i18n-and-shell.test.tsx`.
- **Couche 2 — Tests d'Intégration (`testcontainers-python` : PostgreSQL 18 + `pgvector`, Redis 7.4, MinIO)** : `test_real_containers.py` (migrations `0006..0009` + script `05_backfill_ontology_and_rag_graph.py`).
- **Couche 3 — Tests de Contrat API (`openapi-typescript` 0-diff + `Schemathesis`)** : `test_openapi_contract.py` + `scripts/export_openapi.py`.
- **Couche 4 — Tests d'Orchestration IA (`DeterministicCassetteLLM`)** : Validation déterministe sans appel LLM externe (`0 $`).
- **Couche 5 — Tests E2E & Accessibilité (`@playwright/test` Desktop `1440x900` & Mobile `390x844`)** : `apps/web/e2e/shell.spec.ts`.
