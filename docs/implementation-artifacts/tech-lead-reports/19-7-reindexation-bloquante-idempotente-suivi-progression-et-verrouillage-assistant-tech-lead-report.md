# Rapport Tech Lead & Implémentation — Story 19.7 : Réindexation Bloquante Idempotente, Suivi de Progression & Verrouillage Assistant/Recherche (D9, D12)

- **Date** : 2026-11-15
- **Story / Clé Sprint** : `19-7-reindexation-bloquante-idempotente-suivi-progression-et-verrouillage-assistant` (`Epic 19` — Décisions D9, D12)
- **Capacité(s)** : `CAP-190` (Hub Modèles IA Fiable, Découverte Dynamique 0 Token, Test Réel & Embeddings Sémantiques), impacte `CAP-070` (Recherche Hybride Documentaire RAG & Fédérée 2 Vitesses), `CAP-071` (Ingestion Documentaire Détaillée Multi-Format), `CAP-060` (Mon Assistant Conversationnel 3 Vitesses), `CAP-181` (Sources d'Espace Multi-Nature & Code Graph GitNexus) — classification : `feature`
- **Auteur / Contexte** : Amelia (`bmad-dev-worker`) / Implémentation de la Story 19.7 clôturant l'Epic 19 sur la branche `feat/epic-19-hub-modeles-ia-et-embeddings-semantiques`.
- **Commits associés** : à venir

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique

La Story 19.7 constitue l'étape finale d'ancrage et de robustesse de l'Epic 19. Après l'introduction du port hexagonal `EmbeddingPort` (Story 19.5) et la purge des anciens pseudo-vecteurs SHA-256 avec mise en place du blocage sans modèle (Story 19.6), le système requiert un mécanisme strict et fiable de réindexation globale bloquante et idempotente lors de l'enregistrement initial ou de tout changement du modèle d'embedding actif.

Les enjeux critiques définis par les décisions `D9`, `D11` et `D12` (`AD-24`, PRD) sont :
1. **Intégrité absolue de l'espace vectoriel (Zéro mélange inter-modèles, D9)** :
   - Deux modèles d'embedding distincts (ex. `text-embedding-3-small` vs `mistral-embed` vs `text-embedding-004`) projettent les concepts sémantiques dans des espaces vectoriels mutuellement incompatibles, même à dimension égale (1024).
   - Tout calcul de similarité cosinus (`<=>`) entre un vecteur de requête généré par le Modèle B et des chunks indexés par le Modèle A produit un classement incohérent.
   - Par conséquent, dès qu'un modèle est activé ou modifié, aucun chunk de l'ancien modèle ne doit coexister avec ceux du nouveau dans une recherche sémantique active.
2. **Réindexation bloquante complète orchestrée par worker (D9)** :
   - La réindexation doit recalculer les vecteurs 1024 de tous les `kb_chunks` documentaires (`chunk_role IN ('PARENT', 'CHILD', 'UNIFIED_JIRA', 'DDL_SCHEMA')`) par lots idempotents (`batch_size = 50`), avec mise à jour continue de la progression (`progress_percentage`, `processed_chunks`, `total_chunks`).
   - Le job doit également rejouer et débloquer les sources documentaires en statut `AWAITING_EMBEDDING_MODEL` (Confluence, Jira, DDL, Markdown, PDF) pour les amener à l'état `SYNCED`.
   - Le graphe de symboles GitNexus / codegraph (`SOURCE_CODE`) est **strictement exclu** de la réindexation et continue d'indexer à $0\ \$$ token avec `embedding = NULL` (`D11`).
3. **Verrouillage total de la recherche RAG et de Mon Assistant pendant le job (D9, D12)** :
   - Pendant toute la durée du job (`reindexing_status == 'IN_PROGRESS'`) :
     - Toute recherche RAG (`POST /api/v1/ontology-rag/rag/search`, Vitesse 2/3, `⌘K`) est immédiatement rejetée avec le statut **`HTTP 503 Service Unavailable`** au format RFC 9457 Problem Details (`ERR_RAG_REINDEX_IN_PROGRESS`) incluant la progression (`progress_percentage`).
     - **Mon Assistant est totalement bloqué** : l'API rejette tout tour conversationnel avec `HTTP 503 ERR_RAG_REINDEX_IN_PROGRESS` ; l'UI affiche une bannière bloquante avec le pourcentage rafraîchi en temps réel, et la zone de saisie ainsi que le bouton d'envoi sont matériellement désactivés (`disabled = true`). Zéro mode dégradé lexical, zéro repli fantaisiste.
4. **Idempotence, résilience aux pannes et concurrence (D9)** :
   - L'état du job est matérialisé dans une table PostgreSQL `rag_reindexing_jobs` (UUIDv7, statut, progression, horodatages, horodatage de démarrage et de fin).
   - Un verrou unique empêche les exécutions concurrentes. Si un changement de modèle intervient pendant un job en cours, l'ancien job est proprement marqué `CANCELLED` et le nouveau job prend le relais.
   - En cas d'interruption / crash du worker, la reprise ne retraite que les chunks non encore vectorisés avec le modèle cible (`embedding_model_id != target_model_id` ou `IS NULL`), sans doublon ni corruption.
   - En cas d'échec irrémédiable du job, le statut bascule à `FAILED` avec message d'erreur clair, le système reste bloqué, et une action admin « Relancer la réindexation » (`POST /api/v1/settings/ai-models/reindex-embeddings`) permet de relancer le calcul.
5. **Mise en file persistante des ingestions concurrentes (D9)** :
   - Toute ingestion documentaire ou webhook arrivant pendant le recalcul est placée dans `rag_reindexing_pending_ingestions` et différée jusqu'à la fin du job, évitant toute écriture sur l'ancien modèle.
6. **Événements Outbox et traçabilité** :
   - Émission des événements `EmbeddingReindexStarted`, `EmbeddingReindexCompleted`, `EmbeddingReindexFailed` dans `domain_events_outbox`.

---

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique

- **Analyse d'Impact GitNexus (`repo: 'ORCIA'`, `upstream`)** :
  - Symboles impactés :
    - `search_hybrid_rag` (`apps/api/src/orcia_api/routers/ontology_and_rag.py`) : ajout du garde-fou réindexation (`assert_rag_operational` / statut job).
    - `get_embedding_port` / dépendances Assistant (`apps/api/src/orcia_api/dependencies/portal_and_assistant.py`) : levée de `RagReindexInProgressError` si réindexation active.
    - `AssistantSpeedSelectorAndStreamView` (`packages/ui/src/primitives/AssistantSpeedSelectorAndStreamView.tsx`) : affichage bannière progression réindexation, désactivation saisie.
    - `AiModelsHubService` / routeurs hub (`apps/api/src/orcia_api/routers/ai_models_hub.py`) : déclenchement automatique de réindexation lors d'un basculement de modèle actif, exposition de `GET /reindex-status` et `POST /reindex-embeddings`.
    - `packages/orcia-core/src/orcia_core/rag/` : création de `packages/orcia-core/src/orcia_core/rag/reindex.py` (orchestrateur de réindexation, gestionnaire d'état, requêtes SQL de batches).
    - `apps/worker/src/orcia_worker/` : création de `rag_reindexer.py` (acteur Dramatiq `rag_reindex_actor`).
- **Opportunités de Factorisation & Contrôle de Volumétrie** :
  - Centralisation des requêtes SQL de réindexation dans `packages/orcia-core/src/orcia_core/rag/_internal/sql_reindex.py` (< 300 lignes).
  - Gestion unifiée du statut de réindexation et du verrou de job pour l'API et le Worker.
  - Définition stricte des erreurs RFC 9457 dans `packages/orcia-core/src/orcia_core/rag/errors.py` (`ERR_RAG_REINDEX_IN_PROGRESS` avec `status = 503`).
  - Ajout de l'extension optionnelle `progress_percentage: int | None` sur `ProblemDetails` (`apps/api/src/orcia_api/schemas/problem_details.py`).
  - Résolution et suppression définitive du `TODO(19-7-reindexation-bloquante-idempotente-suivi-progression-et-verrouillage-assistant)` dans `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_workspace_datasources_mutations.py`.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migration Alembic (`infra/migrations/versions/20261115_2307_story_19_7_rag_reindexing_jobs_and_queue.py`)
- **Table `rag_reindexing_jobs`** :
  - `id` UUID PRIMARY KEY (UUIDv7)
  - `target_model_id` UUID NOT NULL REFERENCES `workspace_llm_tier_mappings(id)` ON DELETE CASCADE
  - `target_model_name` VARCHAR(128) NOT NULL
  - `status` VARCHAR(32) NOT NULL CHECK (`status IN ('PENDING', 'IN_PROGRESS', 'COMPLETED', 'FAILED', 'CANCELLED')`)
  - `total_chunks` INTEGER NOT NULL DEFAULT 0
  - `processed_chunks` INTEGER NOT NULL DEFAULT 0
  - `progress_percentage` INTEGER NOT NULL DEFAULT 0
  - `error_message` TEXT NULL
  - `created_at` TIMESTAMPTZ NOT NULL DEFAULT NOW()
  - `started_at` TIMESTAMPTZ NULL
  - `completed_at` TIMESTAMPTZ NULL
  - `updated_at` TIMESTAMPTZ NOT NULL DEFAULT NOW()
  - `created_by` VARCHAR(128) NOT NULL DEFAULT 'system'
  - `cancelled_by_job_id` UUID NULL
- **Table `rag_reindexing_pending_ingestions`** :
  - `id` UUID PRIMARY KEY (UUIDv7)
  - `workspace_id` UUID NOT NULL REFERENCES `workspaces(id)` ON DELETE CASCADE
  - `datasource_id` UUID NOT NULL REFERENCES `workspace_datasources(id)` ON DELETE CASCADE
  - `job_id` UUID NULL REFERENCES `rag_reindexing_jobs(id)` ON DELETE SET NULL
  - `payload_jsonb` JSONB NOT NULL DEFAULT '{}'::jsonb
  - `status` VARCHAR(32) NOT NULL CHECK (`status IN ('PENDING', 'PROCESSED', 'FAILED')`) DEFAULT 'PENDING'
  - `created_at` TIMESTAMPTZ NOT NULL DEFAULT NOW()
  - `processed_at` TIMESTAMPTZ NULL
- **Index B-Tree et partiel** :
  - Index partiel d'unicité pour garantir un seul job actif à la fois (`PENDING`, `IN_PROGRESS`) : `CREATE UNIQUE INDEX idx_rag_reindex_single_active ON rag_reindexing_jobs ((true)) WHERE status IN ('PENDING', 'IN_PROGRESS');`
  - Index de tri : `CREATE INDEX idx_rag_reindexing_jobs_created_at ON rag_reindexing_jobs (created_at DESC);`
- **Réversibilité (`upgrade` / `downgrade`)** testée.

### 2.2 Noyau Métier Hexagonal & Workers (`packages/orcia-core/`, `apps/worker/`)
- **`packages/orcia-core/src/orcia_core/rag/errors.py`** :
  - Déclaration de `RagReindexInProgressError(OrciaDomainError)` avec `error_code = "ERR_RAG_REINDEX_IN_PROGRESS"`, `http_status = 503`, `type_slug = "rag-reindex-in-progress"`, recevant `progress_percentage: int = 0` et `job_id: str | None = None`.
  - Enregistrement des libellés localisés fr/en dans `RAG_ERROR_CATALOG`.
- **`packages/orcia-core/src/orcia_core/rag/reindex.py` & `_internal/sql_reindex.py`** :
  - Gestionnaire de cycle de vie des jobs : `create_or_replace_reindex_job`, `get_active_reindex_job`, `get_latest_reindex_job`, `record_reindex_batch_progress`, `complete_reindex_job`, `fail_reindex_job`.
  - Itération par lots idempotents de 50 chunks sur `kb_chunks` où `chunk_role != 'AST_SYMBOL'` et `(embedding_model_id != target_model_id OR embedding_model_id IS NULL)`.
  - Calcul des embeddings sémantiques réels via `EmbeddingPort.embed(...)` par lot.
  - Mise à jour atomique en base avec `embedding`, `embedding_model_id = target_model_id`, `embedding_generated_at = NOW()`.
  - Rejeu et déblocage des datasources `AWAITING_EMBEDDING_MODEL` à l'achèvement du job vers `SYNCED`.
  - Dépilement des ingestions en attente (`rag_reindexing_pending_ingestions`).
  - Émission des événements Outbox `EmbeddingReindexStarted`, `EmbeddingReindexCompleted`, `EmbeddingReindexFailed`.
- **`apps/worker/src/orcia_worker/rag_reindexer.py`** :
  - Acteur Dramatiq `@dramatiq.actor(actor_name="rag_reindexer", max_retries=2)` exécutant le job de façon non bloquante.
  - Support de l'exécution synchrone pour les tests (`execute_rag_reindex_job`).

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- **`apps/api/src/orcia_api/schemas/problem_details.py`** :
  - Ajout du champ `progress_percentage: int | None = Field(default=None)` sur `ProblemDetails`.
- **`apps/api/src/orcia_api/schemas/ai_models_hub.py`** :
  - `RagReindexStatusResponse`, `RagReindexTriggerResponse`.
- **`apps/api/src/orcia_api/routers/ai_models_hub.py`** :
  - `GET /api/v1/settings/ai-models/reindex-status` : consultation de l'état du job de réindexation.
  - `POST /api/v1/settings/ai-models/reindex-embeddings` : déclenchement ou relance manuelle par un admin, protégé par vérification RBAC et rejet observer `403`.
  - Déclenchement automatique de réindexation lors de la création ou mise à jour d'un modèle actif d'usage `embedding`.
- **`apps/api/src/orcia_api/routers/ontology_and_rag.py` & `dependencies/portal_and_assistant.py`** :
  - Vérification de l'état de réindexation avant d'exécuter la recherche RAG ou un tour d'Assistant. Si réindexation en cours ou en échec, levée de `RagReindexInProgressError` (`HTTP 503`).
- **`packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_workspace_datasources_mutations.py`** :
  - Suppression et résolution du TODO Story 19.7. Si une réindexation est en cours, inscription dans `rag_reindexing_pending_ingestions`.
- **Régénération SDK TypeScript `@orcia/api-client`** :
  - Mise à jour du SDK et vérification `0-diff`.

### 2.4 Interface Utilisateur SPA Vite + TanStack Router Direction C (`apps/web/`, `packages/ui/`)
- **`apps/web/src/features/inbox/index.tsx` & `AssistantSpeedSelectorAndStreamView.tsx`** :
  - Si une réindexation est en cours : affichage d'une bannière dynamique avec le pourcentage de progression, rafraîchie périodiquement, désactivation matérielle des champs d'envoi.
  - Si la réindexation est en échec : bannière d'alerte avec bouton de redirection vers le Hub / action de relance.
  - Survie au rechargement F5 vérifiée.
- **`apps/web/src/features/admin/ai-models/`** :
  - Panneau ou indicateur d'état de réindexation dans le Hub Modèles IA avec jauge de progression et bouton « Relancer la réindexation » réservé aux administrateurs.
- **Internationalisation (`i18n`)** :
  - Nouvelles clés dans `apps/web/src/i18n/locales/fr.ts` et `en.ts`.

### 2.5 Pyramide des Tests (`AD-17` — Couches 1 à 5)
- **Couche 1a (Unitaires Python)** :
  - Machine d'états du job, transition `PENDING` -> `IN_PROGRESS` -> `COMPLETED` / `FAILED`.
  - Idempotence des lots de 50 chunks, reprise après crash (chunks déjà traités ignorés).
  - Annulation / remplacement par un job plus récent.
  - Blocage RAG et Assistant (503 RFC 9457).
- **Couche 1b (Vitest UI)** :
  - Rendu de la bannière de réindexation avec progression %, désactivation saisie, survie F5, bouton relancer.
- **Couche 2 (Intégration PostgreSQL 18 + Redis `testcontainers`)** :
  - Job réel avec `FakeDeterministicEmbeddingAdapter` : `SELECT` vérifiant `embedding_model_id` du nouveau modèle sur tous les chunks, aucun chunk de l'ancien modèle, codegraph intact.
  - Vérification de la réponse 503 pendant le job.
  - Rejeu d'interruption et reprise sans doublon.
- **Couche 3 (Contrats OpenAPI & Lint)** :
  - Régénération SDK TypeScript `@orcia/api-client`.
  - `lint-imports` et conformité hexagonale `AD-19`.
- **Vérification Jour 0 (`pnpm db:reset`)** :
  - Validation du flux complet : Jour 0 bloqué -> configuration modèle -> réindexation automatique -> Assistant débloqué.

---

## 3. Bilan des Modifications & Résultats

### 3.1 Tableau des Fichiers Modifiés / Créés

| Fichier | Nature | Description |
|---|---|---|
| `infra/migrations/versions/20261115_2307_story_19_7_rag_reindexing_jobs_and_queue.py` | Créé | Migration Alembic SQL brut : tables `rag_reindexing_jobs`, `rag_reindexing_pending_ingestions`, index partiel d'unicité `idx_rag_reindex_single_active`, expansion `domain_events_outbox_event_type_check` |
| `packages/orcia-core/src/orcia_core/kernel/events.py` | Modifié | Nouveaux événements outbox `EmbeddingReindexStarted`, `EmbeddingReindexCompleted`, `EmbeddingReindexFailed` |
| `packages/orcia-core/src/orcia_core/rag/errors.py` | Modifié | `RagReindexInProgressError` (`HTTP 503`, `ERR_RAG_REINDEX_IN_PROGRESS`), catalogue i18n fr/en |
| `packages/orcia-core/src/orcia_core/rag/models.py` | Modifié | `RagReindexJobRecord`, `RagReindexPendingIngestionRecord`, type literal `RagReindexJobStatus` |
| `packages/orcia-core/src/orcia_core/rag/_internal/sql_reindex.py` | Créé | Requêtes SQL Postgres 18 pour création/remplacement de job, batchs idempotents, completion immédiate si corpus vide (0 chunk) |
| `packages/orcia-core/src/orcia_core/rag/reindex.py` | Créé | Orchestrateur `execute_rag_reindex_job`, garde-fou `check_rag_operational_on_conn`, `InMemoryReindexManager` |
| `packages/orcia-core/src/orcia_core/rag/__init__.py` | Modifié | Export des nouveaux modèles et erreurs RAG |
| `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_workspace_datasources_mutations.py` | Modifié | Résolution et suppression définitive du `TODO(19-7-...)`, mise en file d'attente pendant réindexation |
| `apps/worker/src/orcia_worker/rag_reindexer.py` | Créé | Acteur Dramatiq `rag_reindexer` pour l'exécution asynchrone non-bloquante du worker |
| `apps/api/src/orcia_api/schemas/ai_models_hub.py` | Modifié | Schémas `RagReindexStatusResponse`, `RagReindexTriggerResponse`, `RagReindexJobStatusLiteral` |
| `apps/api/src/orcia_api/schemas/problem_details.py` | Modifié | Extension optionnelle `progress_percentage: int \| None` sur `ProblemDetails` |
| `apps/api/src/orcia_api/middleware/trace_and_error.py` | Modifié | Propagation du `progress_percentage` dans les réponses Problem Details |
| `apps/api/src/orcia_api/errors/registry.py` | Modifié | Enregistrement de `RagReindexInProgressError` dans le registre des erreurs domaine |
| `apps/api/src/orcia_api/routers/_ai_models_reindex_helpers.py` | Créé | Helpers déclenchement manuel/automatique et consultation statut avec dispatch Dramatiq découplé |
| `apps/api/src/orcia_api/routers/ai_models_hub.py` | Modifié | Routes `GET /reindex-status` et `POST /reindex-embeddings` + déclenchement auto sur activation embedding |
| `apps/api/src/orcia_api/dependencies/portal_and_assistant.py` | Modifié | Garde-fou `get_embedding_port` levant `RagReindexInProgressError` (HTTP 503) pendant le job |
| `packages/api-client/src/generated/` | Modifié | Régénération SDK TypeScript 0-diff avec `RagReindexStatusResponse` et `RagReindexTriggerResponse` |
| `packages/api-client/src/domains/aiModelsHub.ts` | Modifié | Méthodes client typed `getReindexStatus()` et `reindexEmbeddings()` |
| `apps/web/src/features/inbox/useRagReindexStatus.ts` | Créé | Hook de polling temps réel (2s) de l'état de réindexation |
| `apps/web/src/features/inbox/AssistantReindexingBanner.tsx` | Créé | Bannière dynamique avec jauge %, statut et bouton Relancer en cas d'échec |
| `apps/web/src/features/inbox/index.tsx` | Modifié | Intégration de la bannière et verrouillage matériel des inputs/boutons |
| `apps/web/src/features/admin/ai-models/AiModelReindexPanel.tsx` | Créé | Panneau de suivi et relance admin dans le Hub Modèles IA (100% Tailwind tokens, 0 hex) |
| `apps/web/src/routes/SettingsAiModelsSection.tsx` | Modifié | Montage de `AiModelReindexPanel` dans la section Modèles IA |
| `apps/web/src/__tests__/vitest.setup.ts` | Modifié | Mock handlers `/reindex-status` et `/reindex-embeddings`, helper `setVitestMockReindexStatus` |
| `apps/web/src/__tests__/story-19-7-reindexing-banner-hub-and-f5.test.tsx` | Créé | 4 tests Vitest : bannière %, lock input, F5 reload, échec et relance, Day-0 corpus vide |
| `tests/unit/test_story_19_7_rag_reindexing_and_blocking.py` | Créé | 6 tests unitaires : machine d'états, Outbox, 503 RAG & Assistant, endpoints status/trigger, corpus vide |
| `tests/integration/api/test_story_19_7_reindexing_and_blocking_postgres18.py` | Créé | 3 tests d'intégration PG18 : upgrade/downgrade Alembic, job réel avec mise à jour vectorielle, corpus vide Jour 0 |
| `docs/planning-artifacts/epics.md` | Modifié | Ajout du critère d'acceptation corpus vide / Day-0 reset sur Story 19.7 |
| `docs/implementation-artifacts/sprint-status.yaml` | Modifié | `19-7-reindexation-bloquante-idempotente-suivi-progression-et-verrouillage-assistant: review` |
| `docs/product/capabilities.yaml` | Modifié | `CAP-190` mis à jour vers `complete` avec surfaces de migration et d'API complètes |

### 3.2 Résultats des Vérifications et Portes de Gouvernance

1. **Tests unitaires et intégration Python (`pytest`)** :
   - Commande : `.venv/bin/pytest tests/unit/test_story_19_6_rag_blocking_and_embedding_model.py tests/unit/test_story_19_7_rag_reindexing_and_blocking.py tests/integration/api/test_story_19_6_alembic_and_rag_blocking_postgres18.py tests/integration/api/test_story_19_7_reindexing_and_blocking_postgres18.py`
   - Résultat : **18 passed, 0 failed, 1 warning (33.88s)** sur PostgreSQL 18 testcontainers.
2. **Qualité et typage Python** :
   - `.venv/bin/ruff check .` : **All checks passed!**
   - `.venv/bin/ruff format --check .` : **827 files already formatted.**
   - `.venv/bin/mypy --strict packages/orcia-core apps/api apps/worker` : **Success: no issues found in 320 source files.**
   - `.venv/bin/lint-imports` : **Contracts: 5 kept, 0 broken.**
3. **Tests TypeScript & Web UI (`turborepo`)** :
   - Commande : `pnpm turbo run lint typecheck test`
   - Résultat : **9 successful, 9 total (27.88s)** across `@orcia/api-client`, `@orcia/ui`, `@orcia/web` (114 Vitest tests passing).
4. **Vérification Jour 0 (`pnpm db:reset`)** :
   - `.venv/bin/python infra/scripts/maintenance/09_reset_db_first_boot.py --apply` : **APPLY (COMMITTED) — 60 tables cleared, remaining_users=0, remaining_org_units=0, remaining_workspaces=0.**
5. **Critère d'Acceptation Supplémentaire (Corpus Vide / Jour 0)** :
   - Quand aucun chunk documentaire ni source documentaire n'est présent (total = 0, cas du Jour 0), l'activation d'un modèle d'embedding fait basculer le job directement à `COMPLETED` (100%) sans phase de blocage visible, aucune réponse 503 `ERR_RAG_REINDEX_IN_PROGRESS`, aucune bannière bloquante, et l'Assistant reste immédiatement débloqué. Couvert par test unitaire, test d'intégration PG18 et test Vitest UI.
