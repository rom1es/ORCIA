# Story 25.5 — Découplage `Mon Assistant` sans Modèle d'Embedding, Blocage Ciblé des Sources RAG (`POST /datasources` + UI) & Clôture Epic 25

- **Date** : 2026-11-20
- **Story / Clé Sprint** : `25-5-decouplage-assistant-sans-modele-semantique-blocage-sources-rag-et-cloture-epic-25` (`Epic 25`)
- **Capacité(s)** : `CAP-011`, `CAP-022`, `CAP-074`, `CAP-075`, `CAP-076`, `CAP-180`, `CAP-190` — classification : `feature`
- **Auteur / Contexte** : Implémentation de la `Story 25.5` (clôture de l'`Epic 25`) conformément à l'amendement Epic 25 de **`AD-24`** (`ARCHITECTURE-SPINE.md`, 20/11/2026) et aux exigences `AD-8`, `AD-15`, `AD-16`, `AD-17`, `AD-19`, `FR-1`, `FR-14`, `FR-23`, `FR-33`, `FR-34`.
- **Commits associés** : *(en cours d'implémentation — sans commit)*

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Comportement actuel** :
  - Suite à l'Epic 19 (`AD-24`), la dépendance FastAPI `require_rag_available` est injectée sur les routes de `Mon Assistant` (`/api/v1/assistant/chat`, `/api/v1/assistant/chat/stream`, `/api/v1/assistant/three-speed/turn`, `/api/v1/assistant/three-speed/stream`, `/api/v1/assistant/threads/{thread_id}/turns`) et sur `GET /api/v1/search`. En l'absence de modèle d'embedding GLOBAL actif (ou pendant une réindexation sémantique), `Mon Assistant` est matériellement bloqué en backend (`HTTP 422 ERR_NO_ACTIVE_EMBEDDING_MODEL` / `HTTP 503 ERR_RAG_REINDEX_IN_PROGRESS`) et côté UI (`assistantInputBlocked = true`, champ de saisie et bouton d'envoi désactivés).
  - Parallèlement, l'ajout d'une source documentaire nécessitant un RAG vectoriel via `POST /api/v1/workspaces/{workspace_id}/datasources` (`create_workspace_datasource_on_postgres18`) n'est pas encore bloqué dès la création : l'insertion SQL réussit et l'erreur `422 ERR_NO_ACTIVE_EMBEDDING_MODEL` n'apparaît que plus tard lors du `/sync` ; côté UI (`WorkspaceSourceAttachModal`), les natures documentaires RAG restent sélectionnables sans avertissement ni redirection vers `/settings/ai-models`.
  - Enfin, le bridge `/api/v1/assistant/three-speed/turn` et `/stream` ne filtre pas `usage = 'chat'` dans `resolve_decrypted_ai_model_for_tier_pg18`, et en runtime réel sans modèle `chat` actif configuré il bascule silencieusement sur la synthèse déterministe de repli au lieu de retourner une erreur RFC 9457 explicite (`422 ERR_TIER_MODEL_NOT_CONFIGURED`).
- **Comportement attendu (`AD-24` amendé Epic 25)** :
  1. **`Mon Assistant` immédiatement utilisable dès qu'un modèle `chat` actif est configuré** : `Mon Assistant` ne requiert plus de modèle d'embedding ni de pause pendant une réindexation. Lorsque `embedding_port is None`, `AssistantAgentService` / `AssistantHarness` et le bridge LLM exécutent normalement les couches Identité, Rôle/Casquette, Glossaire/Ontologie SQL, Historique et le streaming SSE réel sur le modèle `chat` actif avec `rag_chunks = []` / citations documentaires vides (`0` erreur `422 ERR_NO_ACTIVE_EMBEDDING_MODEL` ni `503`). Côté UI, un indicateur sobre **non-bloquant** (`data-testid="assistant-rag-inactive-notice"`) informe l'utilisateur que le dialogue direct et le glossaire sont actifs mais que la recherche documentaire nécessite un modèle sémantique (lien vers `/settings/ai-models`). Si **`0` modèle `chat`** est actif, la saisie est bloquée côté UI et l'API retourne `HTTP 422 ERR_TIER_MODEL_NOT_CONFIGURED` en runtime réel.
  2. **Recherche fédérée (`GET /api/v1/search`)** : Speed-1 lexical PG18 reste actif à `0` modèle d'embedding ; Speed-2 vectoriel est sauté proprement si `embedding_port is None`.
  3. **`require_rag_available` strictement réservé aux routes RAG vectorielles pures** : `/api/v1/ontology-rag/rag/search` et `/api/v1/ontology-rag/rag/index-db-ddl`.
  4. **Blocage ciblé des sources RAG dès `POST /datasources` & UI** : lorsque `source_nature != 'SOURCE_CODE'` et qu'aucun modèle `embedding` GLOBAL actif n'existe en base (`workspace_llm_tier_mappings`), `create_workspace_datasource_on_postgres18` rejette la création **avant tout `INSERT`** avec `NoActiveEmbeddingModelError` (`HTTP 422 ERR_NO_ACTIVE_EMBEDDING_MODEL`), tout en préservant la création et la synchro des sources `SOURCE_CODE` (GitNexus AST sans embedding). Côté UI (`WorkspaceSourceAttachModal` + `WorkspaceSourcesRagTab`), les natures documentaires RAG sont désactivées avec un encart explicite (`data-testid="datasource-rag-embedding-required-notice"`) et lien vers `/settings/ai-models`, `SOURCE_CODE` reste sélectionnable et créable, et toute erreur `422` RFC 9457 retournée par l'API est affichée dans `[role="alert"]`.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`npx gitnexus analyze` + `gitnexus_query` + audit AST/grep exhaustif sur `ORCIA`)** :
  - Index GitNexus rafraîchi à `42 763` nœuds / `261 005` arêtes / `1 478` flux.
  - **`require_rag_available` (`apps/api/src/orcia_api/dependencies/portal_and_assistant.py`)** : `8` points d'injection FastAPI identifiés :
    - `2` routes RAG pures à **conserver** : `ontology_and_rag.py` (`search_hybrid_rag`, `index_db_ddl_schema`).
    - `5` routes Assistant à **basculer vers `get_optional_embedding_port`** : `assistant.py` (`assistant_chat_turn`, `assistant_chat_stream`), `assistant_workspace.py` (`execute_three_speed_turn_endpoint`, `stream_three_speed_turn_endpoint`), `assistant_workspace_folders.py` (`send_collaborative_thread_turn_endpoint`).
    - `1` route recherche fédérée à **basculer vers `get_optional_embedding_port`** : `portal_and_help.py` (`execute_two_speed_federated_search`).
  - **`get_embedding_port` (`apps/api/src/orcia_api/dependencies/portal_and_assistant.py`)** : utilisé par `require_rag_available`, `dependencies/__init__.py` et `dependencies/_core_providers.py` (inspection `dependency_overrides`).
  - **`create_workspace_datasource_on_postgres18` (`packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_workspace_datasources_mutations.py`)** : appelé par `apps/api/src/orcia_api/routers/workspace_datasources.py:180` (`POST /api/v1/workspaces/{workspace_id}/datasources`), réexporté par `sql_workspace_datasources.py` et `orcia_core.bootstrap`.
  - **`useActiveEmbeddingModelStatus` (`apps/web/src/features/inbox/useActiveEmbeddingModelStatus.ts`)** : consommé par `useInboxPanelController.ts`, et réutilisable pour `WorkspaceSourcesRagTab.tsx` (factorisation DRY).
- **Volumétrie constatée & Découpage préventif (`< 300–350` L)** :
  - `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_workspace_datasources_mutations.py` (`430` L) $\rightarrow$ découpage en `sql_workspace_datasources_mutations.py` (`< 280` L) + `_sql_workspace_datasources_sync.py` (`< 220` L) réexportés par `sql_workspace_datasources.py`.
  - `apps/api/src/orcia_api/dependencies/portal_and_assistant.py` (`315` L) $\rightarrow$ extraction de `_rag_availability_guards.py` (`< 180` L) afin de maintenir `portal_and_assistant.py` (`< 210` L) et garder une séparation nette avec `get_optional_embedding_port`.
  - `apps/api/src/orcia_api/routers/workspace_datasources.py` (`343` L) $\rightarrow$ allègement `< 340` L.
  - `apps/web/src/features/inbox/index.tsx` (`369` L) $\rightarrow$ découpage par extraction d'un sous-composant `InboxActiveTraceAndTurns.tsx` (ou `InboxAssistantHeaderAndPanels.tsx`, `< 150` L) pour ramener `inbox/index.tsx` sous `< 270` L.
- **Opportunités de factorisation (`DRY`)** :
  - Extraction d'un garde SQL partagé `assert_active_global_embedding_model_for_rag_source` utilisé par `create_workspace_datasource_on_postgres18`, `update_workspace_datasource_on_postgres18` (si passage vers une nature RAG) et `trigger_workspace_datasource_sync_on_postgres18` (avec statut `AWAITING_EMBEDDING_MODEL` uniquement sur sync d'une source déjà existante).
  - Réutilisation du hook `useActiveEmbeddingModelStatus` (enrichi avec `hasActiveChatModel`) entre `Mon Assistant` (`useInboxPanelController.ts`) et `Mes Espaces › Sources` (`WorkspaceSourcesRagTab.tsx`).
  - Centralisation 100 % des nouveaux libellés UI et messages d'erreur dans les dictionnaires `i18n` (`assistant_labels.ts`, `epic18_sources_labels.ts`) et `formatRfc9457ErrorToBanner.ts` (zéro ternaire `isFr ? ... : ...` codé en dur dans les composants).

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic
- Aucune nouvelle migration Alembic requise : les colonnes `workspace_llm_tier_mappings.usage` (`20261115_2105`), `workspace_datasources.source_nature` (`20261114_1801`), `kb_chunks.embedding_model_id` (`20261115_2206`) et `rag_reindexing_jobs` (`20261115_2307`) existent déjà en base PostgreSQL 18.

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers (`packages/orcia-core/`)
- `packages/orcia-core/src/orcia_core/orchestration/assistant_agent.py` :
  - Ajouter le paramètre optionnel `embedding_available: bool | None = None` sur `run_conversation_turn` et `stream_conversation_turn_sse`.
  - Au nœud `3_PARALLEL_FAN_OUT`, lorsque `embedding_available is False` (ou si `self._vector_store.hybrid_search` lève `NoActiveEmbeddingModelError` / `RagReindexInProgressError`), ignorer proprement l'appel `pgvector` / `VectorStorePort` et retourner `vector_hits = ()`, exclure la source `"kb"` de `fetch_context_slices` si `embedding_available is False` afin d'éviter toute citation documentaire RAG lorsque la recherche vectorielle est inactive.
- `packages/orcia-core/src/orcia_core/orchestration/_internal/sql_ai_model_queries.py` :
  - Filtrer strictement `AND usage = 'chat'` dans `resolve_decrypted_ai_model_for_tier_pg18` et privilégier le palier exact avant repli sur tout autre modèle `chat` actif GLOBAL (`ORDER BY CASE WHEN inference_tier = :tier THEN 0 ELSE 1 END, fallback_order ASC, created_at ASC LIMIT 1`), garantissant qu'un modèle `embedding` seul n'est jamais utilisé pour le chat et qu'un unique modèle `chat` actif sur n'importe quel palier déverrouille `Mon Assistant`.
- `packages/orcia-core/src/orcia_core/rag/errors.py` & `packages/orcia-core/src/orcia_core/rag/reindex.py` :
  - Mettre à jour les messages `ERR_RAG_REINDEX_IN_PROGRESS` pour indiquer que la recherche documentaire et l'ingestion RAG sont temporairement indisponibles (sans mentionner à tort que Mon Assistant est bloqué).
- `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_workspace_datasources_mutations.py` & `_sql_workspace_datasources_sync.py` & `sql_workspace_datasources.py` :
  - Scinder le fichier de `430` L en `sql_workspace_datasources_mutations.py` (`< 280` L) et `_sql_workspace_datasources_sync.py` (`< 220` L).
  - Dans `create_workspace_datasource_on_postgres18`, dès que `resolved_nature != 'SOURCE_CODE'`, vérifier l'existence d'un modèle `embedding` actif GLOBAL dans `workspace_llm_tier_mappings` (`SELECT id FROM workspace_llm_tier_mappings WHERE usage = 'embedding' AND is_active = TRUE AND scope_level = 'GLOBAL' LIMIT 1`, précédé de `to_regclass('workspace_llm_tier_mappings')`) ; en cas d'absence, lever immédiatement `NoActiveEmbeddingModelError` avant tout `INSERT`.

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- `apps/api/src/orcia_api/dependencies/_rag_availability_guards.py`, `portal_and_assistant.py` & `__init__.py` :
  - Extraire `get_embedding_port`, `get_optional_embedding_port` (retourne `EmbeddingPort | None` en interceptant `NoActiveEmbeddingModelError` et `RagReindexInProgressError`, et respecte `dependency_overrides[get_embedding_port]`) et `require_rag_available` dans `_rag_availability_guards.py` et les réexporter depuis `portal_and_assistant.py` et `orcia_api.dependencies`.
- `apps/api/src/orcia_api/routers/assistant.py`, `assistant_workspace.py`, `assistant_workspace_folders.py`, `portal_and_help.py` :
  - Remplacer `Depends(require_rag_available)` par `Depends(get_optional_embedding_port)` sur les 5 routes Assistant et `GET /api/v1/search`.
  - Dans `portal_and_help.py` (`GET /api/v1/search`), conserver Speed-1 lexical actif quand `_embedding_port is None` et passer `include_speed2=include_speed2 and (_embedding_port is not None)` pour sauter Speed-2 vectoriel.
  - Dans `assistant_workspace.py` (`/three-speed/turn` et `/three-speed/stream`), lorsque l'exécution est en mode live hors cassette (`can_call_live and not use_cassette`), lever `TierModelNotConfiguredError` (`HTTP 422 ERR_TIER_MODEL_NOT_CONFIGURED`) si aucun modèle `chat` actif n'est résolu.
  - Dans `assistant_llm_resolver.py`, exclure tout élément `usage == "embedding"` de `extract_tier_endpoint_from_dict` et résoudre également via `ai_models_hub_service` si `db_engine is None`.
- `apps/api/src/orcia_api/routers/ontology_and_rag.py` :
  - Conserver strictement `Depends(require_rag_available)` sur `/rag/search` et `/rag/index-db-ddl`.
- `apps/api/src/orcia_api/routers/workspace_datasources.py` :
  - Rester `< 340` L et s'appuyer sur `create_workspace_datasource_on_postgres18` pour renvoyer `HTTP 422 ERR_NO_ACTIVE_EMBEDDING_MODEL` en RFC 9457 avant toute insertion d'une source non `SOURCE_CODE` sans modèle `embedding`.

### 2.4 Interface Utilisateur & Expérience (`apps/web/`)
- `apps/web/src/features/inbox/useActiveEmbeddingModelStatus.ts` :
  - Interroger `listAiModelMappings({ is_active: true })` pour exposer `{ hasActiveEmbeddingModel, hasActiveChatModel, isLoaded }` (avec compatibilité des tests existants).
- `apps/web/src/features/inbox/useInboxPanelController.ts`, `InboxDisabledBanner.tsx`, `AssistantNoEmbeddingBanner.tsx`, `AssistantReindexingBanner.tsx`, `index.tsx` + `InboxActiveTraceAndTurns.tsx` :
  - Définir `assistantInputBlocked = !hasActiveChatModel` (ne jamais bloquer faute de modèle `embedding` ou pendant une réindexation dès qu'un modèle `chat` actif existe).
  - Si `!hasActiveChatModel` : afficher la bannière bloquante `role="alert"` (`data-testid="assistant-no-chat-model-banner"`) avec lien `/settings/ai-models`.
  - Si `hasActiveChatModel` et (`!hasActiveEmbeddingModel` ou réindexation en cours / échouée) : afficher un encart informatif sobre **non-bloquant** (`role="status"`, `data-testid="assistant-rag-inactive-notice"`) via les dictionnaires `i18n` FR/EN (zéro ternaire en dur) avec lien vers `/settings/ai-models`.
  - Découper `apps/web/src/features/inbox/index.tsx` (`369` L $\rightarrow$ `< 270` L) via l'extraction de `InboxActiveTraceAndTurns.tsx`.
- `apps/web/src/features/workspaces/WorkspaceSourcesRagTab.tsx` & `sources/WorkspaceSourceAttachModal.tsx` :
  - Consommer `useActiveEmbeddingModelStatus()` dans `WorkspaceSourcesRagTab` et transmettre `hasActiveEmbeddingModel` et `onNavigateToAiModels={() => navigateToRoute("/settings/ai-models")}` à `WorkspaceSourceAttachModal`.
  - Dans `WorkspaceSourceAttachModal`, si `!hasActiveEmbeddingModel`, désactiver les natures RAG (`DOCUMENT_KB`, `WORK_TRACKER`, `RELATIONAL_SCHEMA`), présélectionner `SOURCE_CODE` en création, afficher l'encart explicite `data-testid="datasource-rag-embedding-required-notice"` avec lien vers `/settings/ai-models`, et afficher toute erreur `422` RFC 9457 dans `[role="alert"]` sans fermer silencieusement la modale.
  - Dans `WorkspaceSourcesRagTab`, utiliser `formatRfc9457ErrorToBanner` et afficher les erreurs API (`422`, etc.) dans un bandeau `[role="alert"]`.
- `apps/web/src/i18n/locales/assistant_labels.ts`, `epic18_sources_labels.ts`, `apps/web/src/lib/formatRfc9457ErrorToBanner.ts` :
  - Ajouter les entrées localisées FR/EN pour `assistantNoChatModel`, `assistantRagNotice`, `assistantReindexing`, `epic18Sources.modal.ragEmbeddingRequired*`, et `ERR_TIER_MODEL_NOT_CONFIGURED` / `ERR_NO_ACTIVE_EMBEDDING_MODEL`.

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17` — À traiter par le sous-agent QA indépendant)
- **Couche 1a (Unitaires Python `tests/unit/`)** :
  - `tests/unit/test_assistant_and_rag_routes_require_rag_guard_audit.py` : mettre à jour la liste des routes exigeant `require_rag_available` (`/rag/search`, `/rag/index-db-ddl`) vs `get_optional_embedding_port` (5 routes Assistant + `/search`).
  - `tests/unit/test_story_19_6_rag_blocking_and_embedding_model.py` & `tests/unit/test_story_19_7_rag_reindexing_and_blocking.py` : vérifier que `Mon Assistant` et `GET /search` (Speed-1) restent actifs à `0` embedding et pendant réindexation, tandis que `POST /datasources` (non `SOURCE_CODE`) et `/rag/search` / `/rag/index-db-ddl` retournent `422` / `503`.
  - Nouveau test unitaire `Story 25.5` (assistant `0` embedding + `1` chat, `0` chat -> `422`, `POST /datasources` RAG bloqué vs `SOURCE_CODE` autorisé).
- **Couche 1b (Unitaires / Composants TS `Vitest`)** :
  - `apps/web/src/__tests__/story-19-6-assistant-no-embedding-blocking-and-f5.test.tsx` & `story-19-7-reindexing-banner-hub-and-f5.test.tsx` : adapter les assertions au nouveau découplage (`1` chat + `0` embedding $\rightarrow$ saisie active + `assistant-rag-inactive-notice` ; `0` chat $\rightarrow$ saisie bloquée), et tester `WorkspaceSourcesRagTab` / `WorkspaceSourceAttachModal`.
- **Couche 2 (Intégration Verticale `HTTP FastAPI ➔ PostgreSQL 18`)** :
  - `tests/integration/api/test_story_19_6_alembic_and_rag_blocking_postgres18.py`, `test_story_19_7_reindexing_and_blocking_postgres18.py`, `test_story_18_1_workspace_sources_postgres18.py`, `test_story_17_4_connectors_passthrough_and_rag_referent_postgres18.py`, `test_story_22_1_workspaces_permissions_pg18.py`, `test_story_24_2_triggers_dna_waivers_postgres18.py` : vérifier les cas PG18 sans modèle d'embedding (`POST /datasources` RAG rejeté `422` avant `INSERT` vs `SOURCE_CODE` persisté en PG18).
- **Couche 3 (Contrats OpenAPI 3.1, `lint-imports`)** : `scripts/export_openapi.py --check`, `lint-imports`.
- **Couche 5 (Playwright E2E)** : `apps/web/e2e/02-assistant-streaming-and-folders.spec.ts`, `16-ai-models-reindex-connectors-and-broker.spec.ts`, `17-workspace-sources-codegraph-dna-and-ontology.spec.ts`.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature (Création / Modification / Refactoring) | Description synthétique |
| :--- | :--- | :--- |
| `apps/api/src/orcia_api/dependencies/_rag_availability_guards.py` | Création (Refactoring) | Extraction des gardes RAG (`get_embedding_port`, `get_optional_embedding_port`, `require_rag_available`) ; découplage Assistant (`AD-24` amendé Epic 25). |
| `apps/api/src/orcia_api/dependencies/portal_and_assistant.py` | Modification | Ré-exportation de `get_optional_embedding_port` et `require_rag_available`. |
| `apps/api/src/orcia_api/routers/assistant.py`, `assistant_workspace.py`, `portal_and_help.py` | Modification | Injection `get_optional_embedding_port` sur les 5 routes Assistant et `GET /api/v1/search` (Speed-1 lexical déverrouillé sans embedding). |
| `apps/api/src/orcia_api/routers/assistant_llm_resolver.py` | Modification | Filtrage `usage="chat"` strict lors de la résolution du modèle de dialogue. |
| `apps/api/src/orcia_api/routers/workspace_datasources.py` | Modification | Blocage `422 ERR_NO_ACTIVE_EMBEDDING_MODEL` pour toute nature `!= SOURCE_CODE` sans modèle `embedding` GLOBAL actif. |
| `packages/orcia-core/src/orcia_core/orchestration/assistant_agent.py` | Modification | Exclusion du RAG documentaire lorsque `embedding_available=False` (`rag_active=False`, citations vides, réponse chat normale). |
| `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_workspace_datasources_mutations.py` & `_sql_workspace_datasources_sync.py` | Refactoring / Modification | Découpage `< 300` L et garde SQL `assert_active_global_embedding_model_for_rag_source` avant `INSERT`/`UPDATE` hors `SOURCE_CODE`. |
| `apps/web/src/features/shared/useActiveEmbeddingModelStatus.ts` | Création (Factorisation DRY) | Hook partagé exposant `hasActiveEmbeddingModel` et `hasActiveChatModel` depuis `/api/v1/settings/ai-models/mappings?is_active=true`. |
| `apps/web/src/features/inbox/index.tsx`, `InboxActiveTraceAndTurns.tsx`, `useInboxPanelController.ts`, `InboxDisabledBanner.tsx`, `AssistantNoEmbeddingBanner.tsx` | Refactoring / Modification | Découpage `inbox/index.tsx` (`261` L), `assistantInputBlocked = !hasActiveChatModel`, notice non-bloquant `assistant-rag-inactive-notice` et bannière bloquante `assistant-no-chat-model-banner`. |
| `apps/web/src/features/workspaces/WorkspaceSourcesRagTab.tsx`, `sources/WorkspaceSourceAttachModal.tsx`, `index.tsx`, `WorkspaceStudioCardsAndDetailView.tsx` | Modification | Blocage UX des natures RAG sans modèle `embedding`, présélection `SOURCE_CODE`, alerte RFC 9457 `[role="alert"]`, et respect explicite de `initialWorkspaceId` sur `/workspaces/$wsId/sources`. |
| `apps/web/src/components/useShellContainerState.ts`, `ShellContainer.tsx` | Correctif QA | Garde `!isAuthHydrating && !isInitialLoading` empêchant le basculement prématuré de `activeScopeId` avant hydratation complète des rôles RBAC. |
| `apps/web/src/i18n/locales/assistant_labels.ts`, `epic18_sources_labels.ts`, `lib/formatRfc9457ErrorToBanner.ts` | Modification | Dictionnaires `i18n` FR/EN et libellés RFC 9457 (`ERR_TIER_MODEL_NOT_CONFIGURED`, `ERR_NO_ACTIVE_EMBEDDING_MODEL`). |
| `tests/unit/test_story_25_5_assistant_without_embedding_and_datasource_guard.py`, `test_assistant_and_rag_routes_require_rag_guard_audit.py`, `test_story_25_4_ai_model_delete_and_reindex_empty.py`, `test_epic_9_story_9_2_accostage_and_first_user.py`, `test_story_19_2_*`, `test_story_19_5_*`, `test_story_19_6_*`, `test_story_19_7_*`, `test_epic_25_guards_and_helpers_coverage.py`, `test_zero_fictional_data_and_mocks_in_prod.py`, `tests/security/test_story_25_4_ai_models_rbac_isolation.py`, `test_story_25_1_personal_workspace_isolation.py` | Création / Modification | Audits AST/FastAPI `AD-24`, preuve `42P01` vs `RuntimeError`, RBAC `PLATFORM_ADMIN` AI Models (`403` `CONTRIBUTOR` même avec `?actor_role=PLATFORM_ADMIN`), isolation `PRIVATE_USER` même entre `PLATFORM_ADMIN`, couverture `>= 90%`, et isolation herméneutique Redis/PG. |
| `tests/integration/api/test_story_25_5_assistant_chat_only_and_rag_guard_postgres18.py`, `test_story_17_5_*`, `test_story_19_3_*`, `test_story_19_5_*`, `test_story_19_6_*`, `test_story_19_7_*`, `test_story_25_1_*`, `test_story_17_4_*` | Création / Modification | Intégration verticale `create_app()` réel sur PostgreSQL 18 + Redis 7.4 `testcontainers` : `409 ERR_RESOURCE_PINNED_BY_ACTIVE_RUNS` sur `workflow_runs × inference_attempts`, `PATCH /datasources` `SOURCE_CODE -> DOCUMENT_KB` (`422 ERR_NO_ACTIVE_EMBEDDING_MODEL`), `SELECT` vérifiés. |
| `apps/web/src/__tests__/story-25-5-assistant-unlocked-and-rag-source-blocked.test.tsx`, `story-25-4-spinner-localized-timeout-and-delete.test.tsx`, `story-19-6-*`, `story-19-7-*`, `story-23-2-*`, `vitestConnectorsMockHandlers.ts`, `setup/transportAndOpenApiValidator.ts` | Création / Modification | Tests composants sous `<RouterProvider>` réel : rejet réel `DOMException("The operation timed out.", "TimeoutError")`, filtre `scope_level === "GLOBAL" && !draining` dans `useActiveEmbeddingModelStatus`, et contrat `POST /datasources` `422`. |
| `apps/web/e2e/02-assistant-streaming-and-folders.spec.ts`, `10-command-palette-search.spec.ts`, `16-ai-models-reindex-connectors-and-broker.spec.ts`, `17-workspace-sources-codegraph-dna-and-ontology.spec.ts`, `21-*`, `support/embeddingModel.ts` | Modification | Campagne E2E Playwright Epic 25 après `pnpm db:reset`. |

### 3.2 Résultats Chiffrés, Métriques & Qualité (Post-Revue `VALIDATE`)
- **Couverture Python ciblée sur les 9 modules modifiés** (`coverage.py` avec `--fail-under=90`) : **96 %** global (`_rag_availability_guards.py` : **94 %**, `_ai_models_helpers.py` : **99 %**, `_finops_auth_guards.py` : **96 %**, `_finops_scope_guards.py` : **97 %**, `_sql_workspace_datasources_sync.py` : **99 %**, `sql_workspace_datasources_mutations.py` : **97 %**, `_sql_ai_model_delete_guards.py` : **98 %**, `sql_ai_model_mutations.py` : **97 %**, `assistant_agent.py` : **93 %**).
- **Suite Python complète (`unit` + `security` + `evals`)** : **`1066 passed`**, `0 failed`.
- **Intégration PG18 `testcontainers` (Post-Revue Epic 25)** : **`14 passed`**, `0 failed` (`test_story_17_5_*`, `19_3_*`, `19_5_*`, `19_6_*`, `19_7_*`, `25_1_*`, `25_5_*`).
- **Turbo / Frontend TypeScript** : **`9/9` tâches réussies** (`@orcia/api-client` : **`20/20`**, `@orcia/ui` : **`136/136`**, `@orcia/web` : **`66/66` fichiers de test, `260/260` tests Vitest passés**).
- **Qualité statique & Architecture** :
  - `.venv/bin/ruff check .` & `.venv/bin/ruff format --check .` : **0 erreur** (`1343` fichiers formatés)
  - `.venv/bin/mypy --strict` : **0 erreur** (`581` fichiers source)
  - `.venv/bin/lint-imports` : **`5 contracts kept, 0 broken`**
  - `scripts/export_openapi.py --check` : **`0-diff`**
  - `lint_spine.py` : **`ok: true, total_findings: 0`**

### 3.3 Validation & Procédure de Test sur Toute la Pyramide (`AD-17` + 5 Garde-Fous de Câblage Vertical)
- **Couche 1a & 1b (Unitaires Python & Vitest)** : Audits AST vérifiant `require_rag_available` strict sur `/ontology-rag/rag/search` et `/rag/index-db-ddl` vs `get_optional_embedding_port` sur les 5 routes Assistant et `/search`, filtrage `usage="chat"`, rejet `422 ERR_NO_ACTIVE_EMBEDDING_MODEL` avant `INSERT`/`UPDATE` pour les sources RAG vs autorisation `SOURCE_CODE`, tolérance stricte `42P01` (`UndefinedTableError`) vs propagation `RuntimeError`, test réel `DOMException(..., "TimeoutError")`, filtre `GLOBAL && !draining` et validation complète sous `<RouterProvider>` réel.
- **Couche 2 (Intégration Verticale PG18 `create_app()` réel)** : `14 passed` sur conteneurs `pgvector:pg18` + `redis:7.4.2-alpine` confirmant `200` sur Assistant chat-only et Speed-1 `/search`, `422` + `SELECT COUNT(*) == 0` sur `DOCUMENT_KB`, rejet `PATCH /datasources` `SOURCE_CODE -> DOCUMENT_KB` (`422`), `201` + ligne persistée sur `SOURCE_CODE`, et `409 ERR_RESOURCE_PINNED_BY_ACTIVE_RUNS` sur `workflow_runs × inference_attempts` réel.
- **Couche 3 (Contrats & Frontend)** : OpenAPI 3.1 `0-diff`, `5/5` contrats `lint-imports`, `9/9` `pnpm turbo run lint typecheck test`.
- **Couche 4 & Sécurité** : Inclus dans les `1066 passed` (`DeterministicCassetteLLM` à `0 $`, SSRF, `403 ERR_OBSERVER_MODE_READ_ONLY`, RBAC `PLATFORM_ADMIN` AI Models rejetant `CONTRIBUTOR` en `403` même avec `?actor_role=PLATFORM_ADMIN`, isolation `PRIVATE_USER` sur `/datasources` et `/finops/dashboard` même entre `PLATFORM_ADMIN`).
- **Couche 5 (Playwright `--project=desktop-cockpit` après `pnpm db:reset` vers `/tmp/orcia-e2e-post-review`)** : **`14 passed, 1 skipped (mobile-only), 0 failed (4.0m)`** sur les 6 specs critiques post-revue (`shell`, `01`, `02`, `15`, `16`, `17`) avec vérifications directes PostgreSQL 18 et survie au rechargement `F5`.
