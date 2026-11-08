# 2026-11-08 — Intégration de Google Gemini (`Gemini Argon` / `gemini-argon`) dans la Configuration IA et Mon Assistant (Modes B Natif & A Compatible OpenAI)

> **Convention de nommage du fichier (Obligatoire — créé AVANT toute modification de code)** :
> - `docs/implementation-artifacts/tech-lead-reports/2026-11-08-integration-gemini-argon-configuration-et-assistant-tech-lead-report.md`

- **Date** : 2026-11-08
- **Story / Clé Sprint** : `2026-11-08-integration-gemini-argon-configuration-et-assistant` (`Ajustement Transverse` — `Epics 6, 8 & 9`)
- **Auteur / Contexte** : Intégration de bout en bout du modèle de raisonnement Google Gemini (`Gemini Argon` / `gemini-argon`) dans l'écran `⚙️ Configuration > Modèles IA` et dans `💬 Mon Assistant` (`/api/v1/assistant/three-speed/turn` & `/stream`), avec support double protocole : **Mode B (Recommandé — API Native Google Gemini `:generateContent` / `:streamGenerateContent?alt=sse`, en-tête `x-goog-api-key` et `thinkingConfig: {"includeThoughts": True}`)** et **Mode A (Pont Compatible OpenAI `/v1beta/openai/chat/completions` avec `Authorization: Bearer`)**, découpage modulaire sous 380 lignes, et séparation stricte du flux de réflexion (`part.thought == True` $\rightarrow$ `thinking_delta`) et du flux de réponse (`part.text` $\rightarrow$ `token_delta`).
- **Commits associés** : `47facaf` (`feat/gemini-argon-provider-config-and-assistant-integration`)

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Constat côté Frontend (`⚙️ Configuration > Modèles IA` & `💬 Mon Assistant`)** :
  1. Le fichier [`apps/web/src/routes/SettingsAiModelsSection.tsx`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/routes/SettingsAiModelsSection.tsx) atteint **660 lignes**, dépassant la limite stricte des `300–400 lignes` fixée par `GEMINI.md`.
  2. Le préréglage `"google"` dans `SettingsAiModelsSection.tsx` ne proposait que `gemini-2.5-pro` avec `https://generativelanguage.googleapis.com/v1beta/openai`, sans puce de sélection rapide pour **`gemini-argon`** (`data-testid="ai-model-quick-chip-gemini-argon"`) ni sélecteur de protocole permettant de choisir entre **Mode B (API Native Google Gemini `https://generativelanguage.googleapis.com/v1beta`)** et **Mode A (Pont Compatible OpenAI `https://generativelanguage.googleapis.com/v1beta/openai`)**.
  3. Dans `💬 Mon Assistant` ([`apps/web/src/features/inbox/savedConversationsStore.ts`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/features/inbox/savedConversationsStore.ts)), lorsque plusieurs modèles différents sont configurés sur les paliers (ex. `gemma4:12b` sur `medium` et `gemini-argon` sur `complex`), le titre ou sous-titre des options du sélecteur `assistant-model-and-effort-picker-trigger` doit afficher explicitement le nom du modèle configuré afin de ne jamais masquer un modèle distinct comme `gemini-argon`.
- **Constat côté Backend (`apps/api/src/orcia_api/routers/`)** :
  1. **Anomalie Mode A (`/v1beta/openai`)** : `normalize_chat_completions_url("https://generativelanguage.googleapis.com/v1beta/openai", "google")` ajoutait `/v1/chat/completions` à la fin car l'URL ne se terminait pas par `/v1`, produisant une URL invalide `.../v1beta/openai/v1/chat/completions` au lieu de `https://generativelanguage.googleapis.com/v1beta/openai/chat/completions`.
  2. **Absence du Mode B (API Native Google Gemini `/v1beta`)** : `assistant_llm_providers.py` (déjà à **389 lignes**) ne gérait pas le protocole natif Google Gemini (`/v1beta/models/{model}:generateContent` et `:streamGenerateContent?alt=sse`), l'en-tête `x-goog-api-key`, la structure de requête `systemInstruction` + `contents` + `generationConfig.thinkingConfig = {"includeThoughts": True}`, ni l'extraction des blocs `parts[]` distinguant `{"thought": True, "text": "..."}` (canal de réflexion `thinking_delta`) et `{"text": "..."}` (canal de réponse `token_delta`).
  3. **Test de connexion (`POST /api/v1/bootstrap/welcome-setup/llm-test`)** : `bootstrap_accostage.py` (385 lignes) ne fournissait pas de diagnostic détaillé distinguant le Mode B (API Native Google Gemini) et le Mode A (Compatible OpenAI) ni d'appel/validation spécifique sur `generativelanguage.googleapis.com`.

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_impact`)** :
  - `SettingsAiModelsSection` (`apps/web/src/routes/SettingsAiModelsSection.tsx`) : `impactedCount = 5`, `risk = LOW`, appelé directement par `SettingsHubView` (`apps/web/src/routes/settings.tsx`).
  - `test_welcome_setup_llm_connection` (`apps/api/src/orcia_api/routers/bootstrap_accostage.py`) : route HTTP `POST /api/v1/bootstrap/welcome-setup/llm-test`, consommée par `createOrciaApiClient.testLlmEndpointConnection` dans `SettingsAiModelsSection.tsx`.
  - `assistant_llm_providers.py` & `assistant_llm_bridge.py` : consommés par `assistant_three_speed.py` (`/api/v1/assistant/three-speed/turn` et `/api/v1/assistant/three-speed/stream`).
- **Opportunités de Factorisation & Contrôle de Volumétrie (`< 380–390 lignes`)** :
  1. **Découpage Frontend** :
     - Créer [`apps/web/src/routes/settingsAiModelsPresets.ts`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/routes/settingsAiModelsPresets.ts) (`< 250` lignes) contenant `AI_PROVIDER_PRESETS` (avec `recommendedModels` par fournisseur et `gemini-argon` par défaut sur Google Gemini), les constantes des modes Google Gemini (`native` `/v1beta` vs `openai` `/v1beta/openai`), et le helper `runLlmConnectionTestEvaluation`.
     - Réduire [`apps/web/src/routes/SettingsAiModelsSection.tsx`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/routes/SettingsAiModelsSection.tsx) de `660` lignes à **`< 360` lignes**.
  2. **Découpage Backend** :
     - Créer [`apps/api/src/orcia_api/routers/assistant_llm_gemini_adapter.py`](file:///home/romain/Documents/Projects/ORCIA/apps/api/src/orcia_api/routers/assistant_llm_gemini_adapter.py) (`< 240` lignes) regroupant tous les adaptateurs Google Gemini Mode B & Mode A (`is_google_gemini_native_provider`, `build_gemini_native_url`, `build_gemini_native_headers`, `build_gemini_native_request_body`, `parse_gemini_native_response`, `extract_gemini_stream_chunk_deltas`, et `evaluate_welcome_llm_connection_test`).
     - Maintenir [`apps/api/src/orcia_api/routers/assistant_llm_providers.py`](file:///home/romain/Documents/Projects/ORCIA/apps/api/src/orcia_api/routers/assistant_llm_providers.py) sous **`380` lignes** et [`apps/api/src/orcia_api/routers/bootstrap_accostage.py`](file:///home/romain/Documents/Projects/ORCIA/apps/api/src/orcia_api/routers/bootstrap_accostage.py) sous **`380` lignes**.

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/...`, si applicable)
- Aucune migration Alembic requise : les paliers LLM (`llm_tiers`) sont stockés en JSONB dans le snapshot de configuration de la plateforme (`platform_setup_state`) et dans la table `llm_model_endpoints` existante.

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers (`packages/orcia-core/`, `apps/worker/`)
- Aucun changement dans `packages/orcia-kernel` ni `packages/orcia-core` : l'isolation hexagonale (`AD-19`) est intégralement préservée (5 contrats `lint-imports` intacts).

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- **Création de [`apps/api/src/orcia_api/routers/assistant_llm_gemini_adapter.py`](file:///home/romain/Documents/Projects/ORCIA/apps/api/src/orcia_api/routers/assistant_llm_gemini_adapter.py)** :
  - `is_google_gemini_native_provider(endpoint_uri: str, provider: str = "") -> bool` : détecte si le fournisseur ou l'URL cible Google Gemini en mode natif (ni `/openai` ni `/chat/completions`).
  - `build_gemini_native_url(endpoint_uri: str, model_name: str, *, stream: bool) -> str` : construit `{base}/models/{model_id}:generateContent` (`stream=False`) ou `{base}/models/{model_id}:streamGenerateContent?alt=sse` (`stream=True`), en nettoyant le préfixe `models/` éventuel et en ajoutant `/v1beta` si seul le domaine `https://generativelanguage.googleapis.com` est fourni.
  - `build_gemini_native_headers(api_key: str | None) -> dict[str, str]` : positionne `Content-Type: application/json` et `x-goog-api-key: <api_key>` sans exposer la clé dans l'URL.
  - `build_gemini_native_request_body(messages, *, include_thoughts=True, tools=None)` : convertit les messages `system` en `systemInstruction.parts`, les tours `user`/`assistant` en `contents` (`role: "user" | "model"`), active `generationConfig.thinkingConfig = {"includeThoughts": True}`, et convertit les déclarations d'outils OpenAI en `tools: [{"functionDeclarations": [...]}]`.
  - `parse_gemini_native_response(data)` : extrait séparément les parts avec `part.get("thought") is True` vers `thinking_text`, les parts textuelles standard vers `clean_content`, et les `functionCall` vers `tool_calls`.
  - `extract_gemini_stream_chunk_deltas(chunk)` : sur chaque événement SSE `:streamGenerateContent?alt=sse`, route `part.thought == True` vers `reasoning_delta` (`thinking_delta`) et `part.text` vers `content_delta` (`token_delta`).
  - `evaluate_welcome_llm_connection_test(...)` : valide les paramètres et diagnostique clairement le Mode B (`API Native Google Gemini`) ou le Mode A (`Compatible OpenAI`) pour `gemini-argon` et les autres fournisseurs tout en préservant 100 % de la compatibilité hors-ligne des tests existants.
- **Mise à jour de [`apps/api/src/orcia_api/routers/assistant_llm_providers.py`](file:///home/romain/Documents/Projects/ORCIA/apps/api/src/orcia_api/routers/assistant_llm_providers.py)** :
  - Correction de `normalize_chat_completions_url` pour que toute URL se terminant par `/v1beta/openai` ou `/openai` devienne `{base}/chat/completions` (sans `/v1` supplémentaire).
  - Intégration de `is_google_gemini_native_provider` et des helpers `assistant_llm_gemini_adapter` dans `normalize_chat_completions_url`, `build_provider_headers`, `build_provider_request_body`, `_parse_non_stream_json`, `_extract_stream_chunk_deltas`, `invoke_provider_chat_async`, et `stream_provider_chat_sse_async`.
- **Mise à jour de [`apps/api/src/orcia_api/routers/bootstrap_accostage.py`](file:///home/romain/Documents/Projects/ORCIA/apps/api/src/orcia_api/routers/bootstrap_accostage.py)** :
  - Délégation de la logique de test de connexion LLM à `evaluate_welcome_llm_connection_test` pour enrichir le support Gemini Argon tout en abaissant la taille du fichier sous 350 lignes.

### 2.4 Interface Utilisateur & Expérience (`apps/web/`)
- **Création de [`apps/web/src/routes/settingsAiModelsPresets.ts`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/routes/settingsAiModelsPresets.ts)** et **Refonte de [`apps/web/src/routes/SettingsAiModelsSection.tsx`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/routes/SettingsAiModelsSection.tsx)** :
  - Le préréglage `"google"` (*Google Gemini*) pré-remplit **`gemini-argon`** (`samplePrimaryModel: "gemini-argon"`, `sampleSecondaryModel: "gemini-2.5-flash"`) et l'URL Mode B recommandée **`https://generativelanguage.googleapis.com/v1beta`**.
  - Ajout des puces de sélection rapide de modèles (`data-testid="ai-model-quick-chip-${model}"`, dont `data-testid="ai-model-quick-chip-gemini-argon"`, `data-testid="ai-model-quick-chip-gemini-2.5-pro"`, `data-testid="ai-model-quick-chip-gemini-2.5-flash"`) pour tous les fournisseurs.
  - Ajout du sélecteur de mode de protocole Google Gemini (`data-testid="google-gemini-protocol-mode-selector"`) lorsque le fournisseur actif est Google Gemini :
    - Bouton **Mode B (Recommandé) — API Native Google Gemini (`/v1beta`)** (`data-testid="google-gemini-mode-native-btn"`),
    - Bouton **Mode A — Pont Compatible OpenAI (`/v1beta/openai`)** (`data-testid="google-gemini-mode-openai-btn"`).
- **Mise à jour de [`apps/web/src/features/inbox/savedConversationsStore.ts`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/features/inbox/savedConversationsStore.ts)** :
  - Dans `buildAssistantModelOptions`, enrichissement du sous-titre avec le nom du modèle configuré (`configuredModelName`) lorsque plusieurs modèles distincts sont configurés (ex. `gemma4:12b` sur `medium` et `gemini-argon` sur `complex`), garantissant une visibilité immédiate de `gemini-argon` dans le sélecteur de `💬 Mon Assistant`.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Tableau Synthétique des Fichiers Développés & Modifiés

| Fichier | Action | Lignes | Rôle & Responsabilité |
| :--- | :--- | :---: | :--- |
| [`apps/api/src/orcia_api/routers/assistant_llm_gemini_adapter.py`](file:///home/romain/Documents/Projects/ORCIA/apps/api/src/orcia_api/routers/assistant_llm_gemini_adapter.py) | **Créé** | `238` | Adaptateur Google Gemini (`gemini-argon`) Mode B (API Native `:generateContent` / `:streamGenerateContent?alt=sse`, `x-goog-api-key`, `systemInstruction`, `thinkingConfig: {"includeThoughts": True}`, séparation `part.thought == True` $\rightarrow$ `thinking_delta` vs `part.text` $\rightarrow$ `token_delta`) et diagnostic `evaluate_welcome_llm_connection_test`. |
| [`apps/api/src/orcia_api/routers/assistant_llm_providers.py`](file:///home/romain/Documents/Projects/ORCIA/apps/api/src/orcia_api/routers/assistant_llm_providers.py) | **Modifié** | `379` | Normalisation de `/v1beta/openai` et `/openai` vers `{base}/chat/completions` (Mode A sans `/v1` dupliqué) et branchement complet du Mode B natif Google Gemini dans les appels synchrones/asynchrones et le streaming SSE. |
| [`apps/api/src/orcia_api/routers/bootstrap_accostage.py`](file:///home/romain/Documents/Projects/ORCIA/apps/api/src/orcia_api/routers/bootstrap_accostage.py) | **Modifié** | `321` | Délégation du test de connexion `POST /api/v1/bootstrap/welcome-setup/llm-test` à `evaluate_welcome_llm_connection_test` (Mode B vs Mode A Google Gemini `gemini-argon`) et réduction de la taille sous 350 lignes. |
| [`apps/web/src/routes/settingsAiModelsPresets.ts`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/routes/settingsAiModelsPresets.ts) | **Créé** | `258` | Préréglages des 7 fournisseurs IA (`AI_PROVIDER_PRESETS`), défaut Google Gemini sur **`gemini-argon`** (`samplePrimaryModel: "gemini-argon"`, `sampleSecondaryModel: "gemini-2.5-flash"`, Mode B `https://generativelanguage.googleapis.com/v1beta`), liste de modèles recommandés (`recommendedModels`) et helpers de validation/test de connexion. |
| [`apps/web/src/routes/SettingsAiModelsSection.tsx`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/routes/SettingsAiModelsSection.tsx) | **Modifié** | `348` | Découpage modulaire (`660` $\rightarrow$ `348` lignes), puces de sélection rapide de modèles (`data-testid="ai-model-quick-chip-${model}"` dont `ai-model-quick-chip-gemini-argon`), et sélecteur de protocole Google Gemini (`data-testid="google-gemini-protocol-mode-selector"`, boutons `google-gemini-mode-native-btn` et `google-gemini-mode-openai-btn`). |
| [`apps/web/src/features/inbox/savedConversationsStore.ts`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/features/inbox/savedConversationsStore.ts) | **Modifié** | `360` | Affichage explicite du modèle configuré dans le titre et le sous-titre des options du sélecteur `buildAssistantModelOptions` lorsque plusieurs modèles différents sont configurés (ex. `gemma4:12b` sur `medium` et `gemini-argon` sur `complex`). |
| [`tests/unit/test_gemini_argon_provider_adapter.py`](file:///home/romain/Documents/Projects/ORCIA/tests/unit/test_gemini_argon_provider_adapter.py) | **Créé** | `339` | Suite de 9 tests unitaires et d'intégration couvrant le Mode A (`/v1beta/openai/chat/completions`), le Mode B (`:generateContent` & `:streamGenerateContent?alt=sse`, `x-goog-api-key`, `thinkingConfig`, séparation `thinking_delta` / `token_delta`), `invoke_configured_llm_for_assistant_turn_async`, `stream_configured_llm_for_assistant_turn_sse` et `POST /api/v1/bootstrap/welcome-setup/llm-test`. |
| [`apps/web/src/__tests__/gemini-argon-settings-and-assistant.test.tsx`](file:///home/romain/Documents/Projects/ORCIA/apps/web/src/__tests__/gemini-argon-settings-and-assistant.test.tsx) | **Créé** | `116` | Suite Vitest vérifiant la sélection du préréglage Google Gemini (`gemini-argon`), la bascule Mode B (`/v1beta`) $\leftrightarrow$ Mode A (`/v1beta/openai`), les puces rapides (`ai-model-quick-chip-gemini-argon`), le test de connexion, l'enregistrement d'un palier et l'affichage de `gemini-argon` à côté de `gemma4:12b` dans `buildAssistantModelOptions`. |

### 3.2 Résultats Chiffrés, Métriques & Couverture de Tests
- **Contrôle de volumétrie (`< 380–390 lignes`)** :
  - `assistant_llm_gemini_adapter.py` : **238 lignes** (`< 250`)
  - `assistant_llm_providers.py` : **379 lignes** (`< 380`)
  - `bootstrap_accostage.py` : **321 lignes** (`< 390`)
  - `settingsAiModelsPresets.ts` : **258 lignes** (`< 380`)
  - `SettingsAiModelsSection.tsx` : **348 lignes** (`< 380`, réduit depuis `660` lignes)
  - `savedConversationsStore.ts` : **360 lignes** (`< 380`)
- **Qualité & Typage Python (`.venv/bin/`)** :
  - `ruff check .` : `All checks passed!` (`0` erreur, règle `TID251` respectée)
  - `ruff format --check .` : `556 files already formatted`
  - `mypy --strict packages/orcia-kernel packages/orcia-core apps/api apps/worker` : `Success: no issues found in 218 source files`
  - `lint-imports` : `Contracts: 5 kept, 0 broken.`
- **Qualité, Typage & Tests Frontend (`pnpm turbo run lint typecheck test`)** :
  - `9 successful, 9 total` (`@orcia/ui`, `@orcia/api-client`, `@orcia/web`)
  - `@orcia/web:test` : **5 fichiers de tests passés (`40/40` tests Vitest passés)**, incluant `gemini-argon-settings-and-assistant.test.tsx`, `i18n-and-shell.test.tsx` (`26/26`), `zero-dead-buttons-and-silent-catches-audit.test.tsx` et `design-system-look-and-feel-isolation.test.tsx`.

### 3.3 Validation des 5 Couches de Tests (`AD-17`) & des 4 Invariants Anti-Régression
1. **Règle 1 (`TID251` — Zéro Client HTTP/DB Synchrone)** : Tous les appels vers Google Gemini (`Mode B` et `Mode A`) passent exclusivement par `httpx.AsyncClient` (`request.app.state.http_client`).
2. **Règle 2 (Vrai Streaming SSE & Préservation du Markdown)** : `stream_provider_chat_sse_async` consomme `resp.aiter_lines()` sur `:streamGenerateContent?alt=sse` et émet les fragments en temps réel sans découpage artificiel `.split(" ")`.
3. **Règle 3 (Séparation Stricte du Canal de Réflexion `thinking` vs `content`)** : Les blocs `parts[]` de Gemini Argon portant `"thought": True` sont routés exclusivement vers `thinking_delta` (`AssistantThinkingSubWindow`), tandis que les blocs `"text"` standard alimentent `token_delta` (`clean_content`), sans jamais injecter la chaîne de pensée brute dans la réponse finale.
4. **Règle 4 (Garde-Fou SSRF & Journalisation Structurée)** : `is_safe_llm_endpoint_url` valide systématiquement l'URL avant tout appel réseau et chaque erreur est journalisée via `structlog` (`logger.warning`).
