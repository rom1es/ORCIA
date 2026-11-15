# Rapport Tech Lead & Implémentation — Story 19.5 : Usage Embedding dans le Hub des Modèles IA, Port Hexagonal `EmbeddingPort` & Adaptateurs HTTPX (D5, D6)

- **Date** : 2026-11-15
- **Story / Clé Sprint** : `19-5-usage-embedding-hub-port-hexagonal-embedding-port-et-adaptateurs-httpx` (`Epic 19` — Décisions D5, D6)
- **Capacité(s)** : `CAP-190` (Hub Modèles IA Fiable, Découverte Dynamique 0 Token, Test Réel & Embeddings Sémantiques), impacte `CAP-052` (Fournisseurs LLM Hybrides & Modèles Découplés), `CAP-070` (Recherche Hybride Documentaire RAG & Fédérée 2 Vitesses), `CAP-071` (Ingestion Documentaire Détaillée Multi-Format) — classification : `feature`
- **Auteur / Contexte** : Amelia (`bmad-dev-worker`) / Implémentation de la Story 19.5 de l'Epic 19 sur la branche `feat/epic-19-hub-modeles-ia-et-embeddings-semantiques`.
- **Commits associés** : à venir

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique

Dans l'état actuel d'ORCIA, le Hub des Modèles IA (`/settings/ai-models`) est entièrement dédié aux modèles d'inférence de chat / complétion (tiers cognitifs `simple`, `medium`, `complex`, `auto`). Les vecteurs de la base de connaissances documentaire (`kb_chunks.embedding halfvec(1024)`) et les requêtes RAG sont calculés de manière factice via un pseudo-hachage SHA-256 (`compute_deterministic_halfvec_1024` dans `vector_and_ast.py`), sans sémantique vectorielle réelle.

Pour permettre la transition vers de véritables modèles d'embeddings sémantiques (Décisions D5 et D6 de l'Epic 19) sans refondre l'architecture existante :
1. **Attribut `usage: chat | embedding` sur le modèle IA** :
   - Chaque endpoint enregistré dans `workspace_llm_tier_mappings` doit déclarer son usage (`chat` ou `embedding`, défaut `chat` pour l'existant).
   - **Garantie d'unicité stricte** : Il ne doit exister **qu'un seul modèle d'embedding actif** au niveau `scope_level = 'GLOBAL'` pour l'instance ORCIA. Cette contrainte doit être matérialisée au niveau base de données par un index unique partiel (`idx_llm_tier_mappings_single_active_global_embedding`).
   - L'activation d'un nouveau modèle d'embedding global doit automatiquement désactiver le précédent.
   - Le protocole `anthropic_messages` ne proposant aucune API native d'embeddings, il doit être formellement rejeté pour l'usage `embedding`.
2. **Port Hexagonal `EmbeddingPort` (`AD-19`, `AD-24.5`)** :
   - Contrat abstrait pur (`Protocol`) situé dans `packages/orcia-core/src/orcia_core/ports/embedding.py` (zéro import framework, zéro SDK tiers, zéro dépendance vers `fastapi`, `sqlalchemy`, `litellm`, etc.).
   - Signature : `dimension: int` (strictement 1024), `embed(texts: Sequence[str]) -> list[list[float]]`, `embed_texts(texts: Sequence[str]) -> list[list[float]]`, `embed_query(query: str) -> list[float]`.
   - Erreurs domaine explicites : `EmbeddingDimensionMismatchError` (`HTTP 422 ERR_EMBEDDING_DIMENSION_MISMATCH`), `EmbeddingGenerationFailedError` (`HTTP 502 ERR_EMBEDDING_GENERATION_FAILED`), `EmbeddingProviderUnsupportedError` (`HTTP 422 ERR_EMBEDDING_PROVIDER_UNSUPPORTED`).
3. **Adaptateurs HTTPX purs non bloquants** :
   - `openai_compatible` : requêtes `POST /v1/embeddings` avec envoi de `dimensions=1024` (OpenAI `text-embedding-3`, Mistral, vLLM, TEI, Ollama via `/v1/embeddings`). Si endpoint natif Ollama, cibler `/api/embed` (l'ancien `/api/embeddings` déprécié étant banni).
   - `gemini_native` : requêtes `POST :batchEmbedContents` avec `output_dimensionality=1024`.
   - Contrôle strict post-réception : chaque vecteur retourné doit contenir exactement 1024 nombres flottants finis (`math.isfinite`), sous peine de rejet par `ERR_EMBEDDING_DIMENSION_MISMATCH`.
   - Garde anti-SSRF `is_safe_llm_endpoint_url`, déchiffrement AES-256-GCM via `PassthroughVaultCipher`, zéro clé en clair dans les logs structurés (`register_sensitive_secret_value`).
4. **Câblage au Composition Root & Injection (`AD-19`)** :
   - Raccordement via `apps/api/src/orcia_api/dependencies.py` (`get_embedding_port`) et `apps/worker` sans aucun singleton global import-time.
5. **Interface Utilisateur Hub (`apps/web` + `@orcia/ui` + `i18n`)** :
   - Sélecteur d'usage `Chat & Inférence` vs `Embeddings Sémantiques (1024-dim)` dans `AiModelConfigModal.tsx` / `AiModelFormFields.tsx`.
   - Si `Anthropic` est sélectionné, l'option `embedding` est désactivée ou rejetée avec message explicite.
   - Badge « Modèle d'embedding actif (global) » dans la table maîtresse `AiModelsMasterTable.tsx`.
   - Survie au rechargement de page (persistance et GET de réhydratation).

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique

- **Analyse d'Impact GitNexus (`direction: "upstream"`, `repo: "ORCIA"`)** :
  - `workspace_llm_tier_mappings` (table SQL) : consommée par `sql_ai_model_queries.py`, `sql_ai_model_mutations.py`, `ai_models_hub.py`, `cognitive_router.py`. L'ajout de la colonne `usage` et de l'index partiel unique n'altère aucune requête existante (les requêtes existantes ont la valeur par défaut `'chat'`).
  - `AiModelMappingRecord` (`ai_models_records.py`) : entité domaine centrale. L'ajout du champ `usage: Literal["chat", "embedding"] = "chat"` est transparent pour le routeur cognitif de chat qui continue d'opérer sur `inference_tier`.
  - `AiModelCreateRequest`, `AiModelPatchRequest`, `AiModelMappingItemResponse` (`apps/api/src/orcia_api/schemas/ai_models_hub.py`) : transmission du champ `usage` vers le frontend et le SDK `@orcia/api-client`.
  - `AiModelsHubService` (`ai_models_governance.py`) : gestion in-memory du champ `usage` et de la désactivation du précédent modèle d'embedding global lors de l'activation d'un nouveau.
- **Opportunités de Factorisation & Contrôle de Volumétrie** :
  - Création de `packages/orcia-core/src/orcia_core/ports/embedding.py` (< 80 lignes).
  - Création de `packages/orcia-core/src/orcia_core/rag/adapters/embedding_httpx.py` (< 280 lignes) encapsulant les deux protocoles (`openai_compatible` et `gemini_native`) avec validation de dimension commune.
  - Création de `tests/unit/fakes/fake_embedding.py` pour fournir un fake déterministe conforme à `EmbeddingPort` pour les tests CI sans frais LLM (0 $).

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/`)

- Création de la migration `infra/migrations/versions/20261115_2105_story_19_5_ai_models_usage_and_embedding_unique_idx.py` :
  - `upgrade()` :
    - `ALTER TABLE workspace_llm_tier_mappings ADD COLUMN IF NOT EXISTS usage VARCHAR(32) NOT NULL DEFAULT 'chat' CHECK (usage IN ('chat', 'embedding'));`
    - `CREATE UNIQUE INDEX IF NOT EXISTS idx_llm_tier_mappings_single_active_global_embedding ON workspace_llm_tier_mappings (scope_level, usage) WHERE (usage = 'embedding' AND is_active = TRUE AND scope_level = 'GLOBAL');`
  - `downgrade()` :
    - `DROP INDEX IF EXISTS idx_llm_tier_mappings_single_active_global_embedding;`
    - `ALTER TABLE workspace_llm_tier_mappings DROP COLUMN IF EXISTS usage;`
  - Test de réversibilité dans `tests/unit/test_migration_epic_19_usage.py`.

### 2.2 Noyau Métier Hexagonal & Workers (`packages/orcia-core/`, `apps/worker/`)

1. **Port `EmbeddingPort` (`packages/orcia-core/src/orcia_core/ports/embedding.py`)** :
   - Interface `Protocol` pure : `dimension`, `embed()`, `embed_texts()`, `embed_query()`.
   - Réexport dans `packages/orcia-core/src/orcia_core/ports/__init__.py`.
2. **Erreurs Domaine RAG (`packages/orcia-core/src/orcia_core/rag/errors.py`)** :
   - `EmbeddingDimensionMismatchError` (`ERR_EMBEDDING_DIMENSION_MISMATCH`, 422).
   - `EmbeddingGenerationFailedError` (`ERR_EMBEDDING_GENERATION_FAILED`, 502).
   - `EmbeddingProviderUnsupportedError` (`ERR_EMBEDDING_PROVIDER_UNSUPPORTED`, 422).
   - Enregistrement dans `RAG_ERROR_CATALOG` (FR/EN) et dans `apps/api/src/orcia_api/errors/registry.py`.
3. **Adaptateurs HTTPX (`packages/orcia-core/src/orcia_core/rag/adapters/embedding_httpx.py`)** :
   - `HttpxOpenAiCompatibleEmbeddingAdapter` (OpenAI, Mistral, TEI, vLLM, Ollama `/v1/embeddings` ou `/api/embed`).
   - `HttpxGeminiNativeEmbeddingAdapter` (Gemini `:batchEmbedContents`).
   - Validation stricte des 1024 dimensions et des floats finis.
4. **Domaine Hub Modèles IA (`packages/orcia-core/src/orcia_core/orchestration/`)** :
   - Ajout de `usage: Literal["chat", "embedding"]` sur `AiModelMappingRecord`.
   - Mise à jour de `sql_ai_model_queries.py` et `sql_ai_model_mutations.py` pour persister `usage` et désactiver l'ancien modèle d'embedding global si un nouveau est activé.
   - Refus d'Anthropic pour `usage = 'embedding'`.
   - Mise à jour de `AiModelsHubService`.
5. **Fake Déterministe (`tests/unit/fakes/fake_embedding.py`)** :
   - Implémente `EmbeddingPort` pour tests CI (0 $), générant des vecteurs 1024-dim finis déterministes.

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)

1. **DTOs & Schémas Transport (`apps/api/src/orcia_api/schemas/ai_models_hub.py`)** :
   - Ajout du champ `usage: Literal["chat", "embedding"] = "chat"` dans `AiModelCreateRequest`, `AiModelPatchRequest` (optionnel), et `AiModelMappingItemResponse`.
2. **Routeur Hub Modèles IA (`apps/api/src/orcia_api/routers/ai_models_hub.py`)** :
   - Prise en compte de `usage` lors de la création et de la mise à jour des mappings.
   - Filtre optionnel `usage: Literal["chat", "embedding"] | None` sur `GET /mappings`.
   - Enregistrement des erreurs dans `apps/api/src/orcia_api/errors/registry.py`.
3. **Composition Root (`apps/api/src/orcia_api/dependencies/core_and_lifespan.py`)** :
   - Fonction `get_embedding_port(request: Request) -> EmbeddingPort`.
4. **Régénération du SDK OpenAPI `@orcia/api-client`** :
   - Export du schéma OpenAPI 3.1 et régénération typescript (`pnpm --filter @orcia/api-client generate`).

### 2.4 Interface Utilisateur & Expérience (`apps/web/`, `packages/ui/`)

1. **i18n (`apps/web/src/i18n/locales/ai_models_hub_labels.ts`)** :
   - Ajout des libellés d'usage : `usageLabel`, `usageChat`, `usageEmbedding`, `activeEmbeddingBadge`, `anthropicNoEmbeddingWarning`.
2. **Modale de Configuration (`AiModelConfigModal.tsx` & `AiModelFormFields.tsx`)** :
   - Ajout du sélecteur d'usage : Chat & Inférence vs Embedding Sémantique.
   - Si `Anthropic` est sélectionné et qu'on choisit `Embedding`, affichage d'un avertissement ou verrouillage du bouton.
   - Adaptation des libellés de tier (tier masqué ou grisé quand `usage === "embedding"`).
3. **Table Maîtresse des Modèles (`AiModelsMasterTable.tsx`)** :
   - Badge d'usage (`Chat` vs `Embedding 1024-dim`).
   - Badge d'indication sur le modèle actif : `Modèle d'embedding actif (global)`.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Tableau des Fichiers Modifiés / Créés
| Fichier | Nature | Description |
|---|---|---|
| `infra/migrations/versions/20261115_2105_story_19_5_ai_models_usage_and_embedding_unique_idx.py` | Création | Migration Alembic réversible en SQL brut : ajout de la colonne `usage` et index partiel unique pour garantir un seul modèle d'embedding actif au scope GLOBAL. |
| `packages/orcia-core/src/orcia_core/ports/embedding.py` | Création | Port hexagonal pur `EmbeddingPort` (`embed`, `embed_texts`, `embed_query`, `dimension = 1024`, zéro import SDK/framework). |
| `packages/orcia-core/src/orcia_core/ports/__init__.py` | Modification | Export de `EmbeddingPort` et constante `EMBEDDING_FIXED_DIMENSION`. |
| `packages/orcia-core/src/orcia_core/rag/errors.py` | Modification | Erreurs de domaine RFC 9457 : `EmbeddingDimensionMismatchError`, `EmbeddingGenerationFailedError`, `EmbeddingProviderUnsupportedError`, `NoActiveEmbeddingModelError` et catalogue bilingue fr/en. |
| `packages/orcia-core/src/orcia_core/rag/adapters/embedding_httpx.py` | Création | Adaptateurs asynchrones HTTPX `HttpxOpenAiCompatibleEmbeddingAdapter` et `HttpxGeminiNativeEmbeddingAdapter` avec validation stricte de 1024 floats finis et masquage des secrets. |
| `packages/orcia-core/src/orcia_core/orchestration/ai_models_records.py` | Modification | Type `LlmModelUsage` et champ `usage` dans `AiModelMappingRecord`. |
| `packages/orcia-core/src/orcia_core/orchestration/_internal/sql_ai_model_queries.py` | Modification | Prise en charge de la colonne `usage` dans les requêtes de lecture et fonction `get_active_global_embedding_model_pg18`. |
| `packages/orcia-core/src/orcia_core/orchestration/_internal/sql_ai_model_mutations.py` | Modification | Prise en charge de `usage`, auto-désactivation de l'ancien modèle actif d'embedding global et calcul de `fallback_order`. |
| `packages/orcia-core/src/orcia_core/orchestration/ai_models_governance.py` | Modification | Méthode `get_active_embedding_mapping()` et filtrage `usage` dans `AiModelsHubService`. |
| `apps/api/src/orcia_api/schemas/ai_models_hub.py` | Modification | Schémas transport Pydantic v2 avec champ `usage: LlmModelUsage`. |
| `apps/api/src/orcia_api/routers/_ai_models_helpers.py` | Modification | Conversion ORM/record -> schéma transport avec `usage`. |
| `apps/api/src/orcia_api/routers/ai_models_hub.py` | Modification | Paramètre de filtre `usage` et propagation dans les mutations POST/PATCH. |
| `apps/api/src/orcia_api/errors/registry.py` | Modification | Enregistrement des 4 nouvelles exceptions du domaine RAG/embedding dans `DOMAIN_ERROR_CLASSES`. |
| `apps/api/src/orcia_api/dependencies/portal_and_assistant.py` | Modification | Fournisseur `Depends` de composition root `get_embedding_port`. |
| `packages/api-client/openapi.json` | Modification | Schéma OpenAPI 3.1 synchronisé. |
| `packages/api-client/src/generated/schema.ts` | Modification | Types TypeScript synchronisés avec `usage?: "chat" \| "embedding"`. |
| `packages/api-client/src/domains/aiModelsHub.ts` | Modification | Méthode `listAiModelMappings` acceptant le paramètre optionnel `usage`. |
| `apps/web/src/i18n/locales/ai_models_hub_labels.ts` | Modification | Clés de localisation fr/en pour `usageChat`, `usageEmbedding`, `activeEmbeddingBadge`, etc. |
| `apps/web/src/features/admin/ai-models/AiModelFormFields.tsx` | Modification | Sélecteur de boutons d'usage Chat / Embedding avec désactivation pour Anthropic et masquage d'effort. |
| `apps/web/src/features/admin/ai-models/AiModelConfigModal.tsx` | Modification | Gestion de l'état `usage` et validation anti-Anthropic. |
| `apps/web/src/features/admin/ai-models/AiModelsMasterTable.tsx` | Modification | Badge `Embedding (1024-dim)`, badge `★ Modèle d'embedding actif (global)` et isolation de la barre de couverture des tiers cognitifs chat. |
| `tests/unit/fakes/fake_embedding.py` | Création | Adaptateur déterministe en mémoire `FakeDeterministicEmbeddingAdapter` produisant 1024 dimensions. |
| `tests/unit/test_story_19_5_embedding_port_and_adapters.py` | Création | 8 tests unitaires avec `httpx.MockTransport` (0 $). |
| `tests/unit/test_migration_story_19_5_usage.py` | Création | Test de réversibilité upgrade/downgrade de la migration Alembic. |
| `tests/unit/test_story_19_5_ai_models_usage_and_uniqueness.py` | Création | Tests de gouvernance domaine et unicité en mémoire. |
| `tests/integration/api/test_story_19_5_ai_models_usage_postgres18.py` | Création | Test d'intégration vertical sur conteneur réel PostgreSQL 18 via Testcontainers. |
| `apps/web/src/__tests__/story-19-5-ai-models-usage-and-active-embedding.test.tsx` | Création | 3 tests Vitest d'interaction UI, désactivation Anthropic, affichage des badges et rechargement. |

### 3.2 Résultats des Vérifications et Couverture de Tests
- **Linting & Formatage Python** :
  - `.venv/bin/ruff check .` : `All checks passed!`
  - `.venv/bin/ruff format --check .` : `807 files already formatted`
- **Typage Strict Python** :
  - `.venv/bin/mypy --strict packages/orcia-core apps/api apps/worker` : `Success: no issues found in 314 source files`
- **Frontières Architecturales Hexagonales (AD-19)** :
  - `.venv/bin/lint-imports` : `Contracts: 5 kept, 0 broken`
- **Tests & Couverture Python** :
  - `.venv/bin/pytest tests/unit/test_story_19_5* tests/unit/test_migration_story_19_5* tests/integration/api/test_story_19_5* --cov=orcia_core.ports.embedding --cov=orcia_core.rag.adapters.embedding_httpx --cov-fail-under=90` :
    - `11 passed in 30.68s`
    - Couverture sur `ports/embedding.py` : `100%`
    - Couverture sur `rag/adapters/embedding_httpx.py` : `96.21%` (seuil `>= 90%` respecté)
- **TypeScript & Web** :
  - `pnpm turbo run lint typecheck test --filter=@orcia/api-client --filter=@orcia/ui --filter=@orcia/web` :
    - `9 successful, 9 total` (102 tests réussis dans `apps/web`, 23 suites dans `@orcia/ui`, 13 tests dans `@orcia/api-client`)
    - Respect des invariants Direction C (zéro hex color hors `tokens.css`, zéro dead buttons).
