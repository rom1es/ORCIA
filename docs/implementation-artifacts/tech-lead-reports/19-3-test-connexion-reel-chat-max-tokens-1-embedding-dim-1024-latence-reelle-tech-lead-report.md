# Rapport Tech Lead & Implémentation — Story 19.3 : Test de Connexion Réel Chat (`max_tokens=1`) & Embeddings (Validation Dim 1024), Latence Réelle & Erreurs RFC 9457 (D3)

- **Date** : 2026-11-15
- **Story / Clé Sprint** : `19-3-test-connexion-reel-chat-max-tokens-1-embedding-dim-1024-latence-reelle` (`Epic 19` — Décision D3)
- **Capacité(s)** : `CAP-190` (Hub Modèles IA Fiable, Découverte Dynamique 0 Token, Test Réel & Embeddings Sémantiques), impacte `CAP-052` (Fournisseurs LLM Hybrides & Modèles Découplés), `CAP-053` (Routage Cognitif Multi-Modèles à 4 Paliers & Fallback) — classification : `feature`
- **Auteur / Contexte** : Amelia (`bmad-dev-worker`) / Implémentation de la Story 19.3 de l'Epic 19 sur la branche `feat/epic-19-hub-modeles-ia-et-embeddings-semantiques`.
- **Commits associés** : à venir

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique

Dans l'état hérité du Hub des Modèles IA (`/settings/ai-models`) et de l'accostage Jour 0 (`/welcome-setup`), le test de connectivité des modèles reposait sur une simulation hors-ligne :
1. `apps/api/src/orcia_api/routers/_ai_models_helpers.py:L69-104` (`execute_model_connection_test`) déléguait la validation à `evaluate_welcome_llm_connection_test` (`assistant_llm_gemini_adapter.py:L158-238`).
2. Cette fonction simulée n'émettait **aucun appel réseau réel** vers le fournisseur distant, se bornait à un contrôle de syntaxe d'URL et retournait une latence purement factice codée en dur (`18 ms` pour localhost, `42 ms` pour les URLs distantes). Cette pratique violait formellement la Règle 4 de `GEMINI.md` (« Zéro latence factice codée en dur »).
3. Pire encore, côté frontend (`apps/web/src/routes/settingsAiModelsPresets.ts:L185-211`), `runRemoteLlmConnectionTestEvaluation` rattrapait silencieusement tout échec réseau par `catch` et appelait `buildLocalLlmConnectionSuccessFeedback` avec une latence factice de 18/42 ms, masquant complètement les clés invalides ou modèles inexistants.
4. Pour l'usage `embedding` introduit en Story 19.5 (Décision D5), aucun test de dimension vectorielle (dimension fixe 1024 imposée par `AD-8` et `AD-24.5`) n'était opéré lors du test de connexion.

Pour honorer la **Décision D3** de l'Epic 19 :
- **Pré-checks stricts** : Validation du format de l'URL, présence de la clé API (si `auth_mode == "api_key"`), et garde anti-SSRF `is_safe_llm_endpoint_url` (blocage des IPs Cloud metadata `169.254.169.254`, `100.100.100.200`, etc.).
- **Test d'inférence minimal réel pour l'usage `chat`** :
  - Émission d'un appel réseau réel et non-bloquant via `httpx.AsyncClient` partagé (`app.state.http_client`).
  - `openai_compatible` : `POST /v1/chat/completions` (avec fallback `/api/chat` si 404 local Ollama) avec `max_tokens=1`, prompt `"ping"`, messages `[{"role": "user", "content": "ping"}]`.
  - `anthropic_messages` : `POST /v1/messages` avec `max_tokens=1`, messages `[{"role": "user", "content": "ping"}]`.
  - `gemini_native` : `POST :generateContent` avec `generationConfig: {"maxOutputTokens": 1}`, contents `[{"parts": [{"text": "ping"}]}]`.
- **Test d'embedding minimal réel pour l'usage `embedding`** :
  - 1 appel sur une courte chaîne test (`"orcia connection test"`) via le port hexagonal `EmbeddingPort` et ses adaptateurs HTTPX (`HttpxOpenAiCompatibleEmbeddingAdapter` ou `HttpxGeminiNativeEmbeddingAdapter`).
  - Validation stricte de la dimension vectorielle (`len(vector) == 1024`) et de la finitude des flottants (`math.isfinite`).
  - Si la dimension diffère de 1024 (ex. 768 ou 1536), refus avec `HTTP 422 ERR_EMBEDDING_DIMENSION_MISMATCH`.
  - Rejet formel du protocole `anthropic_messages` (`HTTP 422 ERR_EMBEDDING_PROVIDER_UNSUPPORTED`).
- **Mesure de latence réelle & Erreurs RFC 9457 Problem Details** :
  - Latence aller-retour mesurée précisément via `time.perf_counter()` en millisecondes entières (`latency_ms >= 1`), sans aucune valeur codée en dur.
  - Persistance du résultat en base PostgreSQL 18 : `health_status = 'OPERATIONAL'` et `last_latency_ms` sur succès ; `health_status = 'ERROR'` et `last_latency_ms` (si réponse HTTP reçue) sur échec.
  - En cas d'échec du test, l'API ne masque jamais l'erreur dans un faux 200 OK : elle lève une erreur domaine `OrciaDomainError` traduite en enveloppe **RFC 9457 Problem Details** (`error_code`, `status`, `detail`, `trace_id`), avec codes HTTP adéquats (401, 404, 422, 429, 502, 504).
  - Zéro secret (clé API) divulgué dans les réponses d'erreur ou les logs structurés (`register_sensitive_secret_value`).
- **Suppression intégrale de la simulation & garde-fou anti-régression** :
  - Éradication complète de `evaluate_welcome_llm_connection_test` et de la fonction frontend `buildLocalLlmConnectionSuccessFeedback`.
  - Ajout d'une règle dans l'audit permanent anti-patrons (`test_codebase_architectural_anti_patterns_audit.py`) interdisant tout retour de latence codée en dur (18/42 ms).
- **Interface Utilisateur & Zéro Catch Muet** :
  - Le bouton « Enregistrer et tester la connexion » et les boutons de test individuel affichent la latence réelle mesurée ou l'erreur RFC 9457 explicite.
  - Zéro `.catch(() => undefined)` muet.
- **Zéro Dollar en CI (0 $)** :
  - 100 % des tests unitaires et d'intégration utilisent `httpx.MockTransport` simulant chaque protocole et scénario d'erreur sans appel externe payant.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique

- **Analyse d'Impact GitNexus (`direction: "upstream"`, `repo: "ORCIA"`)** :
  - `execute_model_connection_test` (`_ai_models_helpers.py`) : 1 appelant direct (`ai_models_hub.py:test_ai_model_connection`). Devient asynchrone pour consommer `app.state.http_client`.
  - `evaluate_welcome_llm_connection_test` (`assistant_llm_gemini_adapter.py`) : 2 appelants directs (`_ai_models_helpers.py` et `bootstrap_accostage.py:test_welcome_setup_llm_connection`). Est totalement supprimé de `assistant_llm_gemini_adapter.py` ; `bootstrap_accostage.py` bascule sur le testeur réel asynchrone.
  - `workspace_llm_tier_mappings` : persistance du `health_status` (`OPERATIONAL` vs `ERROR`) et `last_latency_ms` via `record_ai_model_test_result_pg18` déjà en place.
- **Opportunités de Factorisation & Contrôle de Volumétrie** :
  - Création du module pur `packages/orcia-core/src/orcia_core/orchestration/ai_models_connection.py` (< 250 lignes) encapsulant la logique d'exécution minimale pour `chat` (`max_tokens=1`) et `embedding` (dimension 1024), les mesures de latence et le mapping d'erreurs domaine.
  - Factorisation des erreurs spécifiques de connexion dans `packages/orcia-core/src/orcia_core/orchestration/ai_models_errors.py` : `ModelConnectionAuthFailedError` (401), `ModelConnectionNotFoundError` (404), `ModelConnectionRateLimitedError` (429), `ModelConnectionTimeoutError` (504), `ModelConnectionNetworkError` (502), `ModelConnectionUpstreamError` (502).
  - Allègement de `apps/api/src/orcia_api/routers/assistant_llm_gemini_adapter.py` par la suppression de 80 lignes mortes de code de simulation factice.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/`)

- Aucun changement de schéma SQL requis : les colonnes `health_status`, `last_latency_ms`, `last_tested_at` et `usage` existent déjà dans `workspace_llm_tier_mappings` (créées en Story 17.5 et Story 19.5).

### 2.2 Noyau Métier Hexagonal & Domaine (`packages/orcia-core/`)

1. **Erreurs Domaine Modèles IA (`packages/orcia-core/src/orcia_core/orchestration/ai_models_errors.py`)** :
   - Déclarer et enregistrer dans `AI_MODELS_ERROR_CATALOG` (FR/EN) :
     - `ModelConnectionAuthFailedError` (`ERR_MODEL_CONNECTION_AUTH_FAILED`, HTTP 401).
     - `ModelConnectionNotFoundError` (`ERR_MODEL_CONNECTION_NOT_FOUND`, HTTP 404).
     - `ModelConnectionRateLimitedError` (`ERR_MODEL_CONNECTION_RATE_LIMITED`, HTTP 429).
     - `ModelConnectionTimeoutError` (`ERR_MODEL_CONNECTION_TIMEOUT`, HTTP 504).
     - `ModelConnectionNetworkError` (`ERR_MODEL_CONNECTION_NETWORK_ERROR`, HTTP 502).
     - `ModelConnectionUpstreamError` (`ERR_MODEL_CONNECTION_UPSTREAM_ERROR`, HTTP 502).
   - Réexporter dans `packages/orcia-core/src/orcia_core/orchestration/__init__.py`.
2. **Client de Test de Connectivité Réelle (`packages/orcia-core/src/orcia_core/orchestration/ai_models_connection.py`)** :
   - `test_ai_model_endpoint_connection(...)` asynchrone :
     - Pré-checks : validation d'URL et garde anti-SSRF `validate_safe_llm_endpoint_url`.
     - Si `usage == "embedding"` :
       - Rejet Anthropic immédiat (`EmbeddingProviderUnsupportedError`).
       - Sélection de l'adaptateur (`HttpxGeminiNativeEmbeddingAdapter` ou `HttpxOpenAiCompatibleEmbeddingAdapter`).
       - Appel `embed(["orcia connection test"])` avec mesure de latence `time.perf_counter()`.
       - Validation stricte de dimension 1024 (`EmbeddingDimensionMismatchError` si != 1024).
     - Si `usage == "chat"` :
       - Construction du payload minimal `max_tokens=1` (ou `maxOutputTokens=1`).
       - Envoi `POST` via `http_client` avec mesure de latence `time.perf_counter()`.
       - Gestion des codes HTTP et conversion en erreurs domaine sans fuite de secrets.
     - Retourne un objet `AiModelConnectionTestSuccess(latency_ms, message_fr, message_en)`.
3. **Suppression du Code Mort & Factice** :
   - Retirer `evaluate_welcome_llm_connection_test` de `apps/api/src/orcia_api/routers/assistant_llm_gemini_adapter.py`.

### 2.3 Couche Backend API, Sécurité & Enregistrement RFC 9457 (`apps/api/`)

1. **Enregistrement des Erreurs RFC 9457 (`apps/api/src/orcia_api/errors/registry.py`)** :
   - Enregistrer les 6 nouvelles erreurs de connexion LLM dans `DOMAIN_ERROR_CLASSES` et `ERROR_CLASS_REGISTRY`.
2. **Mise à Jour de `_ai_models_helpers.py` & `ai_models_hub.py`** :
   - `execute_model_connection_test` devient asynchrone (`async def`) et utilise `request.app.state.http_client`.
   - En cas d'erreur `OrciaDomainError`, persister `health_status = 'ERROR'` en base de données avant de propager l'exception pour que le middleware RFC 9457 produise la réponse `application/problem+json` avec le bon code HTTP.
   - En cas de succès, persister `health_status = 'OPERATIONAL'` et renvoyer `AiModelTestResponse`.
3. **Mise à Jour de `bootstrap_accostage.py`** :
   - Mettre à jour `test_welcome_setup_llm_connection` pour exécuter un vrai appel réseau via `test_ai_model_endpoint_connection`, retournant la latence réelle mesurée.
4. **Audit Permanent Anti-Patrons (`tests/unit/test_codebase_architectural_anti_patterns_audit.py`)** :
   - Ajouter un contrôle statique interdisant les latences factices (18/42 ms) et la simulation de test.

### 2.4 Interface Utilisateur SPA Vite + TanStack Router Direction C (`apps/web/`)

1. **Purge des Catches Muets & Latences Factices (`apps/web/src/routes/settingsAiModelsPresets.ts`)** :
   - Supprimer `buildLocalLlmConnectionSuccessFeedback` (latence 18/42 ms en dur).
   - `runRemoteLlmConnectionTestEvaluation` : en cas d'échec API, retourner le message d'erreur réel extrait de l'enveloppe RFC 9457 (`err.problem.detail`).
2. **Feedback Réel dans `AiModelConfigModal.tsx` & `SettingsAiModelsSection.tsx`** :
   - Le bouton « Enregistrer et tester la connexion » et les boutons de la table maîtresse affichent le statut réel (`OPERATIONAL` avec latence mesurée, ou `ERROR` avec message d'erreur explicite).

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Tableau des Fichiers Modifiés et Créés

| Fichier | Type de Modification | Rôle & Responsabilité |
| :--- | :--- | :--- |
| `packages/orcia-core/src/orcia_core/orchestration/ai_models_errors.py` | Modification | Définition et catalogue bilingue fr/en des 6 erreurs de connectivité IA (`ERR_MODEL_CONNECTION_*`) |
| `packages/orcia-core/src/orcia_core/orchestration/ai_models_connection.py` | Création | Testeur de connectivité pur async (chat `max_tokens=1`, embedding 1024-dim, latence réelle, anti-SSRF) |
| `packages/orcia-core/src/orcia_core/orchestration/__init__.py` | Modification | Réexport propre des erreurs et de `test_ai_model_endpoint_connection` |
| `apps/api/src/orcia_api/errors/registry.py` | Modification | Enregistrement des 6 erreurs dans `DOMAIN_ERROR_CLASSES` et `ERROR_CLASS_REGISTRY` |
| `apps/api/src/orcia_api/routers/assistant_llm_gemini_adapter.py` | Modification | Suppression totale de `evaluate_welcome_llm_connection_test` et des latences factices 18/42 ms |
| `apps/api/src/orcia_api/routers/_ai_models_helpers.py` | Modification | `execute_model_connection_test` rendu asynchrone et câblé sur `test_ai_model_endpoint_connection` |
| `apps/api/src/orcia_api/routers/ai_models_hub.py` | Modification | Route `/mappings/{id}/test` asynchrone avec persistance PG18 `OPERATIONAL`/`ERROR` et RFC 9457 |
| `apps/api/src/orcia_api/routers/bootstrap_accostage.py` | Modification | Route `/bootstrap/welcome-setup/llm-test` câblée sur le test réel non bloquant |
| `apps/web/src/routes/settingsAiModelsPresets.ts` | Modification | Suppression de la simulation locale (18/42 ms) et propagation du message d'erreur RFC 9457 |
| `apps/web/src/routes/SettingsAiModelsSection.tsx` | Modification | Bannière d'alerte explicite en cas d'erreur de test et attente réelle de la connectivité |
| `apps/web/src/__tests__/vitest.setup.ts` | Modification | Mock fetch de test mis à jour sans latence factice |
| `tests/unit/test_story_19_3_ai_model_connection_test.py` | Création | 16 tests unitaires complets sur MockTransport (chat, embedding, erreurs, normalisation) |
| `tests/unit/test_codebase_architectural_anti_patterns_audit.py` | Modification | Règle de garde-fou interdisant toute latence factice codée en dur (18/42 ms) |
| `tests/unit/test_gemini_argon_provider_adapter.py` | Modification | Tests d'accostage Jour 0 mis à jour avec le test HTTPX réel |
| `tests/integration/api/test_story_19_3_ai_models_connection_test_postgres18.py` | Création | Test d'intégration vertical HTTP ➔ PostgreSQL 18 avec SELECT et vérification des statuts |
| `apps/web/src/__tests__/story-19-3-ai-models-real-connection-test-and-no-dead-buttons.test.tsx` | Création | Tests Vitest du bouton de test et de la bannière d'erreur sans catch muet |
| `docs/product/capabilities.yaml` | Modification | Mise à jour de `CAP-190` (`status: in_progress`, surfaces de test) |
| `docs/implementation-artifacts/sprint-status.yaml` | Modification | Passage de `19-3-test-connexion-reel-chat-max-tokens-1-et-embeddings-latence-et-rfc-9457` à `review` |

### 3.2 Métriques Chiffrées & Couverture de Tests

- **Couverture Unit Tests sur `ai_models_connection.py`** : **93.69%** (au-delà du seuil minimal obligatoire de $\ge 90\%$).
- **Nombre de tests unitaires dédiés** : 16 tests unitaires (`test_story_19_3_ai_model_connection_test.py`), 5 tests provider adapter (`test_gemini_argon_provider_adapter.py`), 6 tests anti-patrons (`test_codebase_architectural_anti_patterns_audit.py`).
- **Tests d'intégration PostgreSQL 18 réels** : 1 test vertical complet (`test_story_19_3_ai_models_connection_test_postgres18.py`), exécuté sur conteneur `pgvector/pgvector:pg18` avec requêtes SQL `SELECT` de validation de l'état persisté.
- **Tests Vitest Frontend** : 2 tests unitaires/intégration de composants (`story-19-3-ai-models-real-connection-test-and-no-dead-buttons.test.tsx`) + 7 tests du garde-fou anti-boutons-muets (`zero-dead-buttons-and-silent-catches-audit.test.tsx`).
- **Coût CI** : **0 $** (100% MockTransport et cassettes hermétiques, aucun appel LLM externe payant).

### 3.3 Validation des Cinq Couches de Tests (`AD-17`)

1. **Couche 1 (Unitaires purs)** :
   - `.venv/bin/pytest tests/unit/test_story_19_3_ai_model_connection_test.py --cov=orcia_core.orchestration.ai_models_connection --cov-fail-under=90` : **16 passed in 6.29s (93.69% coverage)**.
   - `.venv/bin/pytest tests/unit/test_codebase_architectural_anti_patterns_audit.py` : **6 passed in 8.97s**.
   - `.venv/bin/pytest tests/unit/test_gemini_argon_provider_adapter.py` : **5 passed in 6.58s**.
2. **Couche 2 (Intégration PostgreSQL 18 réels via Testcontainers)** :
   - `.venv/bin/pytest tests/integration/api/test_story_19_3_ai_models_connection_test_postgres18.py` : **1 passed in 16.36s**.
3. **Couche 3 (Typage & Architecture)** :
   - `.venv/bin/mypy --strict packages/orcia-core/src/orcia_core packages/orcia-connectors/src/orcia_connectors apps/api/src/orcia_api apps/worker/src/orcia_worker` : **Success: no issues found in 328 source files**.
   - `.venv/bin/lint-imports` : **5 kept, 0 broken**.
   - `.venv/bin/ruff check .` : **All checks passed!**
   - `.venv/bin/ruff format --check .` : **815 files already formatted**.
   - `pnpm --filter=@orcia/web typecheck` : **0 errors (tsc --noEmit)**.
   - `pnpm --filter=@orcia/web lint` : **0 errors (boundary check passed)**.
4. **Couche 4 (Tests Vitest UI & Anti-Boutons Muets)** :
   - `pnpm --filter=@orcia/web test src/__tests__/story-19-3-ai-models-real-connection-test-and-no-dead-buttons.test.tsx` : **2 passed in 339ms**.
   - `pnpm --filter=@orcia/web test src/__tests__/zero-dead-buttons-and-silent-catches-audit.test.tsx` : **7 passed in 2.55s**.
5. **Couche 5 (Conformité & Registre des Capacités)** :
   - `docs/product/capabilities.yaml` mis à jour avec `CAP-190` (`status: in_progress`).
   - `docs/implementation-artifacts/sprint-status.yaml` mis à jour avec `story-19-3` à `review`.
