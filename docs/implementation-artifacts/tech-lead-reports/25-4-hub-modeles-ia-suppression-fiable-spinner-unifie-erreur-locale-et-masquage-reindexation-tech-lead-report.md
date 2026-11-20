# Story 25.4 — Hub Modèles IA : Suppression PG18 Fiable sans Fallback RAM, `<OrciaSpinner />` Unifié, Erreur Locale & Masquage Réindexation

- **Date** : 2026-11-20
- **Story / Clé Sprint** : `25-4-hub-modeles-ia-suppression-fiable-spinner-unifie-erreur-locale-et-masquage-reindexation` (`Epic 25`)
- **Capacité(s)** : `CAP-053`, `CAP-100`, `CAP-190` — classification : `feature` + `hygiène` (`UX/API/SQL`)
- **Auteur / Contexte** : Correction de 4 défauts critiques sur `Administration › Modèles IA` (`/settings/ai-models`) et l'UI de chargement transverse : (1) suppression du fallback RAM `settingsAiModelsFallback.ts` et du faux positif SQL `ILIKE` bloquant la suppression du dernier modèle en PG18 (`AD-21` §5), avec propagation immédiate vers l'accostage/menu shell ; (2) unification des spinners sur `<OrciaSpinner />` dans `@orcia/ui` ; (3) localisation par modèle + timeout client `16 s` des erreurs de test de connexion sous chaque carte ; (4) masquage du panneau `"Semantic Reindexing & Vector Corpus"` lorsqu'il existe `0` document/chunk indexé en PG18 (`AD-24`).
- **Commits associés** : *(en cours d'implémentation)*

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Bug 3 (Suppression impossible & résurrection après `F5`)** :
  - Côté backend, `evaluate_ai_model_delete_impact_pg18` (`packages/orcia-core/src/orcia_core/orchestration/_internal/sql_ai_model_mutations.py`) exécute `SELECT id FROM workflow_definitions_v2 WHERE status IN ('published', 'active') AND CAST(spec_jsonb AS TEXT) ILIKE '%{inference_tier}%'`, générant des faux positifs sur des définitions statiques contenant des mots courants (`auto`, `simple`, `medium`, `complex`) et levant `409 LastTierModelInUseError` même sans aucun run actif épinglant le modèle.
  - Côté frontend, `useAiModelsSectionController.ts` recourt à `buildFallbackMappingsFromProps(llmTiers)` (`settingsAiModelsFallback.ts`) dès que `serverMappings` est vide, et appelle `upsertLlmTier(...)` lors de la création, ce qui réinjecte les modèles depuis le snapshot `platform_setup_state` / RAM après suppression et ne rafraîchit pas `accostageCounts` (`hasModels`) dans `platformSetupStore.tsx`. De plus, `AiModelDeleteDialog.tsx` ignore le retour `{ ok: false, errorMessage }` sans afficher le motif d'échec dans `[role="alert"]` et comporte des libellés français codés en dur.
- **Spinner unifié (`<OrciaSpinner />`) & bouton `Tester`** :
  - `ShellAuthFallbackView.tsx` utilise un spinner CSS ad-hoc (`animate-spin rounded-full border-2 border-current border-t-transparent`) et `AiModelsMasterTable.tsx` affiche un texte statique avec points de suspension (`"Testing..."` / `"Test en cours..."`) pendant le test de connexion.
- **Erreur / Timeout de `Tester` non localisé** :
  - `useAiModelsSectionController.ts` stocke l'erreur de test dans `operationError` (bandeau global en haut de page) sans `AbortSignal.timeout` client en filet de sécurité du timeout serveur `15 s`.
- **Bug 2 (Panneau réindexation visible avec `0` document indexé)** :
  - `RagReindexStatusResponse` ne retourne pas le décompte réel PG18 (`kb_chunks`, `kb_documents`) et `AiModelReindexPanel.tsx` reste affiché (`Ready (0%)`) dès l'ouverture ou après ajout/changement d'un modèle d'embedding même avec `0` document indexé.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus & Recherche de Références (`repo: /home/romain/Documents/Projects/ORCIA`)** :
  - `evaluate_ai_model_delete_impact_pg18` / `delete_or_drain_ai_model_mapping_pg18` : appelés uniquement par `apps/api/src/orcia_api/routers/_ai_models_test_and_reindex_routes.py` et réexportés par `sql_ai_model_mappings.py` (+ tests `test_story_17_5_*`).
  - `AiModelsMasterTable` : monté par `apps/web/src/routes/SettingsAiModelsSection.tsx` (et tests `story-17-5`, `story-19-5`, `story-24-6`).
  - `AiModelReindexPanel` : monté par `SettingsAiModelsSection.tsx`.
  - `buildFallbackMappingsFromProps` : importé uniquement par `apps/web/src/routes/useAiModelsSectionController.ts`.
  - Spinners ad-hoc détectés dans `packages/ui/src/` et `apps/web/src/` : `apps/web/src/components/ShellAuthFallbackView.tsx:32` (`animate-spin ... border-t-transparent`), ainsi que l'indicateur de chargement texte de `packages/ui/src/primitives/OrciaModelCombobox.tsx:215`.
- **Vérification schéma PG18 (`workflow_runs` & `kb_documents`/`kb_chunks`)** :
  - Contrainte `ck_workflow_runs_status` (`20261117_0704_story_7_4_post_hoc_audit_and_kill_switch.py`) : statuts actifs/en pause = `INITIALIZED`, `RUNNING`, `WAITING_FOR_HUMAN_ARBITRATION`, `WAITING_FOR_HUMAN_GATE`, `PAUSED_CIRCUIT_BREAKER`, `PAUSED_BUDGET_EXCEEDED`, `PAUSED_MAX_RETRIES`, `PAUSED_AUTONOMOUS_ESCALATION` (plus statuts étendus éventuels `WAITING_FOR_HUMAN_ANCHOR`, `WAITING_FOR_PERMISSION`, `PAUSED`).
  - `kb_chunks` filtre `chunk_role != 'AST_SYMBOL'` et `kb_documents` filtre `indexing_regime != 'CODE_AST_GRAPH'`.
- **Opportunités de Factorisation & Contrôle de Volumétrie (`> 300–400` lignes)** :
  - `packages/orcia-core/src/orcia_core/orchestration/_internal/sql_ai_model_mutations.py` (`416` L) $\rightarrow$ extraction de `_sql_ai_model_delete_guards.py` (`< 160` L) pour ramener `sql_ai_model_mutations.py` sous `< 280` L.
  - `apps/web/src/features/admin/ai-models/AiModelsMasterTable.tsx` (`411` L) $\rightarrow$ extraction de `AiModelMappingRowCard.tsx` (`< 200` L) pour ramener `AiModelsMasterTable.tsx` sous `< 260` L.
  - Création d'une primitive unique `<OrciaSpinner />` dans `packages/ui/src/primitives/OrciaSpinner.tsx` (`< 70` L) réutilisée partout.
  - Extraction de `buildAccostageCountsFromStatus` dans `platformSetupHydration.ts` pour éviter la duplication entre hydratation initiale et `refreshAccostage()`.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic
- Aucune migration Alembic requise : les tables `workspace_llm_tier_mappings`, `workflow_runs`, `inference_attempts`, `kb_documents`, `kb_chunks` et `rag_reindexing_jobs` disposent déjà de toutes les colonnes et contraintes nécessaires.

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers (`packages/orcia-core/`)
- `packages/orcia-core/src/orcia_core/orchestration/_internal/_sql_ai_model_delete_guards.py` (création) & `sql_ai_model_mutations.py` (`< 280` L) :
  - Extraction de `evaluate_ai_model_delete_impact_pg18` et `delete_or_drain_ai_model_mapping_pg18` (réexportés depuis `sql_ai_model_mutations.py` et `sql_ai_model_mappings.py`).
  - Suppression complète du faux positif `CAST(spec_jsonb AS TEXT) ILIKE` sur `workflow_definitions_v2`.
  - Vérification stricte sur les runs actifs/en pause de `workflow_runs` joints à `inference_attempts` (`model_name` ou `requested_tier`/`resolved_tier` lorsque `is_last_active_for_tier`). Journalisation structurée `get_logger(...)` sur exception SQL éventuelle (zéro `except Exception` muet).
- `packages/orcia-core/src/orcia_core/rag/_internal/sql_reindex_jobs.py` & `packages/orcia-core/src/orcia_core/rag/reindex.py` :
  - Ajout de `count_indexed_corpus_pg18(conn)` comptant les chunks non-AST (`kb_chunks`) et documents non-AST (`kb_documents`) en PG18.

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- `apps/api/src/orcia_api/schemas/ai_models_hub.py` :
  - Ajout de `indexed_chunks_count: int = 0` et `indexed_documents_count: int = 0` à `RagReindexStatusResponse`.
- `apps/api/src/orcia_api/routers/_ai_models_reindex_helpers.py` :
  - Peuplement systématique de `indexed_chunks_count` et `indexed_documents_count` depuis `count_indexed_corpus_pg18` dans `fetch_reindex_status_response`.
- `packages/api-client/` :
  - Régénération OpenAPI `0-diff` via `.venv/bin/python scripts/export_openapi.py`.
  - Support optionnel `signal?: AbortSignal` dans `createRequestJson` (`helpers.ts`) et `testAiModelMapping(mappingId, { signal })` (`domains/aiModelsHub.ts`).

### 2.4 Interface Utilisateur & Expérience (`packages/ui/`, `apps/web/`)
- `packages/ui/src/primitives/OrciaSpinner.tsx` (`< 70` L) & `packages/ui/src/index.ts` :
  - Primitive SVG circulaire animée (`animate-spin`), tailles `xs | sm | md | lg`, `currentColor` strict, `data-testid="orcia-spinner"`.
  - Remplacement des spinners/indicateurs ad-hoc dans `ShellAuthFallbackView.tsx` et `OrciaModelCombobox.tsx`.
- Suppression de `apps/web/src/routes/settingsAiModelsFallback.ts` et suppression de `buildFallbackMappingsFromProps` / `llmTiers` / `upsertLlmTier` dans `SettingsAiModelsSection.tsx` et `useAiModelsSectionController.ts`.
- Ajout de `refreshAccostage()` dans `platformSetupStore.tsx` / `platformSetupContextTypes.ts` (réinitialisant `llmTiers` si `models_count === 0` en PG18) et appel `await refreshAccostage()` après suppression, création, modification ou bascule actif/inactif dans `useAiModelsSectionController.ts`.
- `AiModelDeleteDialog.tsx` : gestion des retours `{ ok: false, errorMessage }` et exceptions sans fermer la modale avec bandeau `[role="alert"]`, et internationalisation complète via `ai_models_hub_labels.ts` (`Fournisseur` / `Provider`, `Modèle` / `Model`, `Palier` / `Tier`, chargement avec `<OrciaSpinner />`).
- Découpage de `AiModelsMasterTable.tsx` (`< 260` L) + `AiModelMappingRowCard.tsx` (`< 200` L) :
  - Bouton `Tester` affichant `<OrciaSpinner size="sm" />` + libellé sans `...` pendant `isTesting`.
  - Erreurs/timeouts (`AbortSignal.timeout(16_000)` dans `aiModelsApiBridge.ts`) stockés par ID dans `testErrorsByModelId` et affichés localement sous la carte du modèle (`<div role="alert" data-testid={`ai-model-test-error-${mapping.id}`}>`).
- `AiModelReindexPanel.tsx` :
  - Retourne `null` lorsque `indexed_chunks_count === 0 && total_chunks === 0` et aucun job actif (`PENDING`/`IN_PROGRESS`) ou en échec (`FAILED`) n'existe (y compris après ajout/changement d'un modèle d'embedding sur corpus vide).
  - Lorsque `>= 1` document/chunk existe à l'état `IDLE`, affiche le décompte réel d'extraits indexés (jamais `"Ready (0%)"`) et désactive `Relaunch reindexing` si aucun modèle `embedding` actif n'est configuré.

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17` — Géré par QA indépendant)
- **Couche 1a (`tests/unit/`)** : `test_story_17_5_ai_models_hub_secrets_and_lifecycle.py`, `test_story_19_7_rag_reindexing_and_blocking.py`, nouveaux cas sur `_sql_ai_model_delete_guards.py` et `count_indexed_corpus_pg18`.
- **Couche 1b (`apps/web/src/__tests__/`, `packages/ui/src/__tests__/`)** : `story-17-5-*`, `story-19-3-*`, `story-19-5-*`, `story-19-7-*`, `gemini-settings-and-assistant.test.tsx`, `zero-dead-buttons-and-silent-catches-audit.test.tsx`, tests `<OrciaSpinner />`.
- **Couche 2 (`tests/integration/api/`)** : `test_story_17_5_ai_models_hub_postgres18.py`, `test_story_19_7_reindexing_and_blocking_postgres18.py` (suppression du dernier modèle avec `workflow_definitions_v2` publiées sans run actif vs blocage 409 avec run actif + comptage `kb_chunks`/`kb_documents`).
- **Couche 3 (Contrats & Static Gates)** : `export_openapi.py --check` (`0-diff`), `ruff`, `mypy --strict`, `lint-imports`, `pnpm turbo run lint typecheck`.
- **Couche 5 (E2E Playwright)** : `apps/web/e2e/16-ai-models-reindex-connectors-and-broker.spec.ts`.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature | Description synthétique |
| :--- | :--- | :--- |
| `packages/orcia-core/src/orcia_core/orchestration/_internal/_sql_ai_model_delete_guards.py` | Création (`165` L) | Extraction des gardes de suppression PG18 (`evaluate_ai_model_delete_impact_pg18`, `delete_or_drain_ai_model_mapping_pg18`), suppression du faux positif `ILIKE` sur `workflow_definitions_v2`, blocage `409` strict sur `workflow_runs` actifs/en pause joints à `inference_attempts` et journalisation structurée `get_logger`. |
| `packages/orcia-core/src/orcia_core/orchestration/_internal/sql_ai_model_mutations.py` | Modification (`275` L) | Réexport des gardes de suppression et incrémentation automatique de `fallback_order` pour tous les usages (`chat` & `embedding`) afin d'autoriser plusieurs modèles sur un même palier sans erreur `500`. |
| `packages/orcia-core/src/orcia_core/rag/_internal/sql_reindex_jobs.py` / `sql_reindex.py` / `reindex.py` | Modification | Ajout de `count_indexed_corpus_pg18(conn)` comptant les chunks (`chunk_role != 'AST_SYMBOL'`) et documents (`indexing_regime != 'CODE_AST_GRAPH'`) en PG18. |
| `apps/api/src/orcia_api/schemas/ai_models_hub.py` & `routers/_ai_models_reindex_helpers.py` | Modification | Exposition de `indexed_chunks_count` et `indexed_documents_count` dans `RagReindexStatusResponse` (`GET /api/v1/settings/ai-models/reindex-status`). |
| `packages/api-client/openapi.json` & `src/{generated/schema.ts,helpers.ts,domains/aiModelsHub.ts}` | Modification | Régénération OpenAPI `0-diff`, support `signal?: AbortSignal` dans `createRequestJson` et `testAiModelMapping`. |
| `packages/ui/src/components/icons/OrciaSpinnerSvg.tsx` & `packages/ui/src/primitives/OrciaSpinner.tsx` & `packages/ui/src/index.ts` | Création / Modification | Primitive unifiée `<OrciaSpinner size="xs|sm|md|lg" />` (`data-testid="orcia-spinner"`, `currentColor`) respectant l'Audit Gate 1 (`0` SVG orphelin hors `components/icons/`). |
| `packages/ui/src/primitives/{OrciaModelCombobox,PlatformAuthSettingsCard,RemoteServiceTestBenchAndMcpExposureView}.tsx` & `components/SourceLineInspectorDrawer.tsx` | Modification | Remplacement de `100 %` des indicateurs CSS ad-hoc / `⏳` / sabliers de chargement par `<OrciaSpinner />` (`0` `animate-spin` hors `OrciaSpinner.tsx`). |
| `apps/web/src/routes/settingsAiModelsFallback.ts` | Suppression | Élimination définitive du fallback RAM (`buildFallbackMappingsFromProps`) dans le Hub Modèles IA. |
| `apps/web/src/components/{ShellAuthFallbackView,platformSetupContextTypes,platformSetupHydration,platformSetupStore}.tsx` & `routes/{settings,SettingsAiModelsSection,useAiModelsSectionController}.ts` | Modification | Ajout de `refreshAccostage()` réinitialisant `hasModels` / `llmTiers` si `models_count === 0`, suppression des props mortes `llmTiers`/`upsertLlmTier`, timeout client `16 s` et stockage par modèle `testErrorsByModelId`. |
| `apps/web/src/features/admin/ai-models/{AiModelMappingRowCard.tsx,AiModelsMasterTable.tsx,AiModelDeleteDialog.tsx,AiModelConfigModal.tsx,AiModelReindexPanel.tsx,aiModelsApiBridge.ts}` & `auth/SettingsAuthenticationSection.tsx` & `i18n/locales/ai_models_hub_labels.ts` | Création / Modification | Découpage `AiModelMappingRowCard.tsx` (`184` L), `<OrciaSpinner />` sans `...` sur `Tester`, erreurs/timeout `16 s` localisées (`ai-model-test-error-${id}`), alerte `[role="alert"]` (`ai-model-delete-error`) + i18n complète dans `AiModelDeleteDialog`, masquage strict de `AiModelReindexPanel` à `0` document/chunk (`null`, zéro `"Ready (0%)"`). |
| `tests/unit/test_story_25_4_ai_model_delete_and_reindex_empty.py`, `tests/integration/api/test_story_17_5_ai_models_hub_postgres18.py`, `tests/unit/test_e2e_sql_coverage_audit.py` | Création / Modification | Couverture unitaire & PG18 réelle (`create_app()` sans override) des gardes de suppression, `fallback_order`, `count_indexed_corpus_pg18` et statut réindexation vide `0/0`. |
| `apps/web/src/__tests__/story-25-4-spinner-localized-timeout-and-delete.test.tsx`, `setup/{aiModelsAndToolsMockHandlers,authAndBootstrapMockHandlers,mockBackendState}.ts`, `story-17-5-*`, `story-19-3-*`, `gemini-settings-and-assistant.test.tsx`, `i18n-and-shell.test.tsx` | Création / Modification | Validation `<RouterProvider>` réel (`OrciaSpinner` sans `...`, erreur localisée/timeout `16 s`, suppression + survie `F5` sans résurrection, modale delete i18n EN + `[role="alert"]`, masquage `AiModelReindexPanel`). |
| `apps/web/e2e/16-ai-models-reindex-connectors-and-broker.spec.ts` | Modification | Vérification navigateur réel PG18 : masquage `ai-model-reindex-panel` à `0` doc, `<OrciaSpinner />` sur `Tester`, erreur HTTP `500` localisée sous le modèle testé, suppression de tous les modèles (`COUNT(*) == 0` en PG18) et survie à `page.reload()` + `reloadColdFromPg`. |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Couverture ciblée Python Story 25.4 (`pytest --cov`)** : **`98.06 %`** (`46 passed`, seuil `--cov-fail-under=90` atteint) :
  - `_sql_ai_model_delete_guards.py` : `100 %` (`50/50` stmts, `14/14` branches)
  - `sql_ai_model_mutations.py` : `97 %` (`62/62` stmts, `8/10` branches)
  - `sql_reindex.py` : `100 %` (`5/5` stmts)
  - `sql_reindex_jobs.py` : `96 %` (`56/58` stmts, `11/12` branches)
  - `reindex.py` : `100 %` (`39/39` stmts, `8/8` branches)
- **Qualité statique & Architecture** :
  - `ruff check .` & `ruff format --check .` : `0` erreur (`1 337` fichiers formatés).
  - `mypy --strict packages/orcia-core packages/orcia-connectors apps/api apps/worker` : `0` erreur (`579` fichiers source).
  - `lint-imports` : `5 contracts kept, 0 broken` (`622` fichiers, `4 497` dépendances).
  - `scripts/export_openapi.py --check` : `0-diff`.
  - `lint_spine.py` : `ok: true, 0 findings`.
  - `gitnexus_detect_changes({ repo: "/home/romain/Documents/Projects/ORCIA", scope: "all" })` : `changed_count: 7`, `changed_files: 43`, `affected_count: 1483`, `risk_level: "critical"` (périmètre attendu `PlatformSetupContextValue`, `useAiModelsSectionController`, `AiModelsMasterTableProps`, `AiModelDeleteDialogProps`, `ai_models_hub_labels`).
  - Audit `grep -rn "animate-spin" packages/ui/src apps/web/src` (hors tests) : `1` seule occurrence dans `packages/ui/src/primitives/OrciaSpinner.tsx`.

### 3.3 Validation sur la Pyramide des Tests (`AD-17` — 5 Couches + Sécurité)
- **Couche 1a (Python Unitaires, Sécurité & Evals)** : `tests/unit tests/security tests/evals` vert (`1 051 passed`), incluant `test_story_25_4_ai_model_delete_and_reindex_empty.py` (`7/7`).
- **Couche 1b (`pnpm turbo run lint typecheck test`)** : **`9/9` tâches réussies** — `@orcia/ui` (`34` fichiers, `136/136` tests), `@orcia/api-client` (`3` fichiers, `13/13` tests), `@orcia/web` (`65` fichiers, `254/254` tests dont `3/3` sur `story-25-4-spinner-localized-timeout-and-delete.test.tsx` sous `<RouterProvider>` réel).
- **Couche 2 (Intégration Verticale `HTTP ➔ PostgreSQL 18` `testcontainers`)** : `test_story_17_5_ai_models_hub_postgres18.py` (`2/2`, dont `test_ai_models_hub_delete_without_false_positive_and_empty_reindex_status_pg18` sur `create_app()` réel sans override) et `test_story_19_7_reindexing_and_blocking_postgres18.py` (`6/6`) verts.
- **Couche 3 (Contrats & Synchronisation Vitrine)** : `export_openapi.py --check` (`0-diff`), `sync_site_catalog.py --check` & `check_implementation_docs.py` (`0` erreur).
- **Couche 5 (E2E Playwright `--project=desktop-cockpit`, `ORCIA_E2E_CAMPAIGN_DIR=/tmp/orcia-e2e-story-25-4`)** : **`10 passed (2.4m)`** sur `16-ai-models-reindex-connectors-and-broker.spec.ts` (`4/4`), `01-day0-boot-and-f5-persistence.spec.ts` (`2/2`) et `shell.spec.ts` (`4/4`).
