# 2026-11-23 — Support Google Gemini Interactions API, Modèle de Secours Runtime & Résolution Protocole Frontend

- **Date** : 2026-11-23
- **Story / Clé Sprint** : `2026-11-23-gemini-interactions-api-et-fallback-secours` (`Ajustement Transverse`)
- **Capacité(s)** : `CAP-052`, `CAP-053`, `CAP-074`, `CAP-076`, `CAP-190` — classification : `feature`
- **Auteur / Contexte** : Prise en charge de l'API Google Gemini Interactions (`/v1beta/interactions`) pour les modèles spécialisés (`antigravity-*`, `deep-research-*`, ou réponse HTTP 400 imposant Interactions API), bascule runtime automatique sur `fallback_model_name` (modèle de secours) avant émission du premier octet SSE ou en complétion synchrone, tri prioritaire de la découverte Gemini (`gemini-*` en tête + support `createInteraction`), et résolution cohérente du `protocol_mode` côté frontend (`apps/web`). Exigences couvertes : `AD-15`, `AD-17`, `AD-19`, `AD-21`, `AD-24`, `CAP-076`.
- **Commits associés** : `pending`

---

## 1. Analyse du Besoin & Étude d'Impact Tech Lead (Pré-Implémentation)

### 1.1 Contexte & Problématique
- **Problème 1 — Modèles Google Gemini restreints à l'API Interactions (`/v1beta/interactions`)** : Certains modèles émergents ou agents Google Gemini (ex. `antigravity-preview-05-2026`, `deep-research-*`) rejettent les requêtes sur `:generateContent` / `:streamGenerateContent` avec `HTTP 400` (`"This model only supports Interactions API."`), et peuvent attendre le champ `"model"` ou `"agent"` selon l'agent/modèle ciblé.
- **Problème 2 — Modèle de secours (`fallback_model_name`) non exploité au runtime ni au test de connexion** : Bien que `fallback_model_name` soit persisté en base PG18 (`ai_model_mappings`) et éditable dans l'UI, `LlmEndpointConfig`, `BaseHttpxLlmAdapter`, `llm_endpoint_resolver.py` et `test_ai_model_endpoint_connection` ne propagent ni n'exécutent la bascule automatique vers ce modèle secondaire lorsque le modèle principal échoue avant le premier octet (hors `401/403`).
- **Problème 3 — Tri découverte Gemini & `protocol_mode` frontend** : `discover_gemini_native` trie par ordre alphabétique strict (plaçant `antigravity-*` ou `aqa` avant `gemini-*`) et ignore `createInteraction` dans `supportedGenerationMethods`. Côté frontend, `handleQuickSubmit` et certains chemins de création/édition forcent `"openai_compatible"` au lieu de déduire `gemini_native` ou `anthropic_messages` depuis la famille/URL.
- **Contraintes d'architecture (`ARCHITECTURE-SPINE.md`)** :
  - Respect strict `AD-19` (`lint-imports`) : zéro import SDK externe (`httpx`, `fastapi`, `sqlalchemy`) dans `orcia_core/ports` (`llm_streaming_port.py`) ni dans le dialecte pur `llm_gemini_interactions.py`.
  - Respect du plafond de taille `<= 300` lignes par fichier modifié/créé (dont réduction de `useAiModelConfigModalState.ts` de 321 L à `<= 295` L).
  - Journalisation structurée obligatoire sur toute bascule/erreur (`logger.warning`, zéro `except Exception:` silencieux).

### 1.2 Exploration, Analyse d'Impact GitNexus, Factorisation & Dette Technique
- **Analyse d'Impact GitNexus (`gitnexus_query`, `gitnexus_context`, `gitnexus_impact`)** :
  - `is_google_gemini_native_provider` : **131** symboles/processus impactés en amont (`upstream`) — comportement conservé à l'identique pour Mode A/B.
  - `build_gemini_native_request_body` : **176** symboles/processus impactés en amont — inchangé ; les payloads Interactions API sont isolés dans un module dédié `llm_gemini_interactions.py` et activés uniquement sur URL `/interactions` ou auto-switch 400.
  - `BaseHttpxLlmAdapter.complete_chat` : **181** symboles/processus impactés en amont.
  - `BaseHttpxLlmAdapter.stream_chat_events` : **130** symboles/processus impactés en amont.
- **Opportunités de Factorisation & Contrôle de Volumétrie** :
  - Extraction des constructions de requêtes Interactions API et de secours dans `_llm_streaming_http_helpers.py` (`<= 220` L) afin de maintenir `llm_streaming_base_httpx.py` sous `270` L.
  - Isolation complète du dialecte Google Interactions API dans `packages/orcia-core/src/orcia_core/orchestration/llm_gemini_interactions.py` (`<= 220` L) avec réutilisation de `separate_think_tags` depuis `llm_gemini_dialect.py`.
  - Factorisation frontend de la détection de protocole dans `resolveEffectiveLlmProtocolMode` (`settingsAiModelsPresets.ts`), partagée entre `useAiModelsSectionController.ts` et `useAiModelConfigModalState.ts` (réduit ce dernier de `321` L à `<= 295` L).

---

## 2. Plan d'Implémentation

### 2.1 Schéma de Données & Migrations Alembic (`infra/migrations/versions/...`)
- Aucune migration Alembic requise : la colonne `fallback_model_name` existe déjà dans la table `ai_model_mappings` et dans `AiModelMappingRecord` (`sql_ai_model_queries.py`).

### 2.2 Noyau Métier Hexagonal, Orchestration & Workers (`packages/orcia-core/`)
- `packages/orcia-core/src/orcia_core/ports/llm_streaming_port.py` (`<= 295` L) : ajout de `fallback_model_name: str | None = None` sur `LlmEndpointConfig` (zéro import SDK externe).
- `packages/orcia-core/src/orcia_core/orchestration/ai_models_urls.py` (`<= 160` L) : ajout de `is_gemini_interactions_only_model`, `is_gemini_interactions_url`, `build_gemini_interactions_url`, et routage dans `build_gemini_native_chat_url`.
- `packages/orcia-core/src/orcia_core/orchestration/llm_gemini_interactions.py` (Nouveau, `<= 220` L) : module pur (zéro SDK externe) exposant `is_gemini_interactions_api_required_error`, `is_gemini_interactions_agent_field_required_error`, `build_gemini_interactions_probe_body`, `build_gemini_interactions_request_body`, `parse_gemini_interactions_response`, `extract_gemini_interactions_stream_deltas`.
- `packages/orcia-core/src/orcia_core/orchestration/llm_provider_parsing.py` (`<= 230` L) & `llm_usage_telemetry.py` (`<= 160` L) : prise en charge des URLs `/interactions`, du parsing `outputs`/`steps`/`interaction`/`output_text`, des deltas `delta`/`content.*`/`step.*`/`interaction.*` et de `usage.total_input_tokens` / `total_output_tokens` + `interaction.usage`.
- `packages/orcia-core/src/orcia_core/orchestration/llm_endpoint_resolver.py` (`<= 215` L) : propagation de `fallback_model_name` depuis le snapshot JSON (`secondaryModel` / `fallback_model_name`), le chemin PG18 (`rec.fallback_model_name`) et `hub_svc`.
- `packages/orcia-core/src/orcia_core/orchestration/_llm_streaming_http_helpers.py` (`<= 220` L) & `llm_streaming_base_httpx.py` (`<= 270` L) : auto-switch HTTP 400 Interactions API (`model` puis `agent` sur 400/404) et bascule vers `fallback_model_name` avant émission du premier octet (hors `401`/`403`) avec log structuré `logger.warning`.
- `packages/orcia-core/src/orcia_core/orchestration/ai_models_connection_helpers.py` (`<= 230` L) & `ai_models_connection.py` (`<= 290` L) : support du probe Interactions API, retry auto-switch + `agent`, et bascule de test de connexion sur `fallback_model_name` avec messages localisés FR/EN.
- `packages/orcia-core/src/orcia_core/orchestration/ai_models_discovery_dialects.py` (`<= 298` L) : intégration de `createInteraction` et tri prioritaire `gemini-*` (chat) devant les autres modèles chat/embedding et inconnus.

### 2.3 Couche Backend API, Sécurité & Contrats (`apps/api/`, `packages/api-client/`)
- `apps/api/src/orcia_api/routers/_ai_models_helpers.py` (`<= 265` L) : transmission de `fallback_model_name=rec.fallback_model_name` à `test_ai_model_endpoint_connection` dans `execute_model_connection_test`.
- Aucune modification de schéma OpenAPI / routeur HTTP requise.

### 2.4 Interface Utilisateur & Expérience (`apps/web/`)
- `apps/web/src/routes/settingsAiModelsPresets.ts` (`<= 235` L) : export de `resolveEffectiveLlmProtocolMode(modelFamily, endpointUrl, fallbackMode)`.
- `apps/web/src/routes/useAiModelsSectionController.ts` (`<= 290` L) : utilisation de `resolveEffectiveLlmProtocolMode` dans `handleQuickSubmit`.
- `apps/web/src/features/admin/ai-models/useAiModelConfigModalState.ts` (`<= 295` L) : utilisation de `resolveEffectiveLlmProtocolMode` dans `triggerDiscovery` et `handleFormSubmit` (`create` et `edit`), tout en réduisant le fichier à `<= 295` lignes.

### 2.5 Analyse d'Impact sur la Pyramide des Tests (`AD-17` — Couches 1 à 5 + Sécurité, Obligatoire)
- **Couche 1a (Unitaires Python `tests/unit/`) & Couche 1b (Unitaires/Composants TS `Vitest`)** :
  - Création de `tests/unit/test_gemini_interactions_and_fallback_model.py` (`<= 280` L) couvrant auto-switch Interactions API (`model` & `agent`), parsing/streaming Interactions API, fallback modèle secondaire (runtime + test de connexion + exclusion `401/403`), et tri `discover_gemini_native`.
  - Création d'un test Vitest dans `apps/web/src/__tests__/` pour `resolveEffectiveLlmProtocolMode` (Gemini Mode A/B + Anthropic + OpenAI fallback).
- **Couche 2 / 3 / 4 / Sécurité / 5** : vérifications complètes exécutées par le Testing Sub-Agent en fin d'implémentation.

---

## 3. Bilan des Modifications & Résultats (Post-Implémentation)

### 3.1 Fichiers Développés & Modifiés
| Fichier | Nature (Création / Modification / Refactoring) | Volumétrie | Description synthétique |
| :--- | :--- | :--- | :--- |
| `packages/orcia-core/src/orcia_core/ports/llm_streaming_port.py` | Modification | `289` L | Ajout de `fallback_model_name: str \| None = None` sur `LlmEndpointConfig` (zéro dépendance SDK externe `AD-19`). |
| `packages/orcia-core/src/orcia_core/orchestration/ai_models_urls.py` | Modification | `154` L | Routage Gemini Interactions API (`is_gemini_interactions_only_model`, `is_gemini_interactions_url`, `build_gemini_interactions_url`, `build_gemini_native_chat_url`). |
| `packages/orcia-core/src/orcia_core/orchestration/llm_gemini_interactions.py` | Création | `196` L | Dialecte pur Google Gemini Interactions (`/v1beta/interactions`) : payload `model`/`agent`, `system_instruction`, `tools`, parsing `outputs`/`steps` et deltas SSE. |
| `packages/orcia-core/src/orcia_core/orchestration/llm_provider_parsing.py` | Modification | `208` L | Support `/interactions` dans le parsing de réponses et deltas SSE streaming. |
| `packages/orcia-core/src/orcia_core/orchestration/llm_usage_telemetry.py` | Modification | `158` L | Extraction des compteurs tokens `usage.total_input_tokens` / `total_output_tokens` et `interaction.usage`. |
| `packages/orcia-core/src/orcia_core/orchestration/llm_endpoint_resolver.py` | Modification | `194` L | Propagation de `fallback_model_name` depuis snapshot JSON, PG18 (`rec.fallback_model_name`) et `hub_svc`. |
| `packages/orcia-core/src/orcia_core/orchestration/_llm_streaming_http_helpers.py` | Modification | `210` L | Helpers de requêtes Interactions API et `build_secondary_model_fallback_request` (anti-boucle). |
| `packages/orcia-core/src/orcia_core/orchestration/_llm_streaming_fallbacks.py` | Création | `132` L | Encapsulation des tentatives HTTP de repli Interactions API (`model` $\rightarrow$ `agent`) et bascule modèle secondaire. |
| `packages/orcia-core/src/orcia_core/orchestration/llm_streaming_base_httpx.py` | Modification | `262` L | Auto-switch HTTP 400 Interactions API (`model` puis `agent`) et fallback `fallback_model_name` avant premier octet (hors `401`/`403`) avec `logger.warning`. |
| `packages/orcia-core/src/orcia_core/orchestration/ai_models_connection_helpers.py` | Modification | `248` L | Probe Interactions API, retry auto-switch + `agent`, et helpers de test de connexion. |
| `packages/orcia-core/src/orcia_core/orchestration/ai_models_connection.py` | Modification | `281` L | Bascule du test de connexion vers `fallback_model_name` (hors `401`/`403`) avec diagnostics localisés FR/EN. |
| `packages/orcia-core/src/orcia_core/orchestration/ai_models_discovery_dialects.py` | Modification | `300` L | Support `createInteraction` dans `discover_gemini_native` et tri prioritaire des modèles `generateContent` devant les autres modèles chat/embedding et inconnus. |
| `apps/api/src/orcia_api/routers/_ai_models_helpers.py` | Modification | `255` L | Transmission de `fallback_model_name=rec.fallback_model_name` dans `execute_model_connection_test`. |
| `apps/web/src/routes/settingsAiModelsPresets.ts` | Modification | `233` L | Export de `resolveEffectiveLlmProtocolMode(modelFamily, endpointUrl, fallbackMode)`. |
| `apps/web/src/routes/useAiModelsSectionController.ts` | Modification | `286` L | Détection cohérente du `protocol_mode` dans `handleQuickSubmit` via `resolveEffectiveLlmProtocolMode`. |
| `apps/web/src/features/admin/ai-models/useAiModelConfigModalState.ts` | Modification / Refactoring | `273` L | Partage de `resolveEffectiveLlmProtocolMode` dans `triggerDiscovery`/`handleFormSubmit` et réduction sous `300` lignes. |
| `tests/unit/test_gemini_interactions_and_fallback_model.py` | Création | `272` L | Tests unitaires Interactions API, fallback modèle secondaire, et tri découverte Gemini. |
| `tests/unit/test_gemini_interactions_coverage_edges.py` | Création | `244` L | Cas limites dialecte Interactions API, URLs, parsing et télémétrie tokens. |
| `tests/unit/test_gemini_adapters_coverage_edges.py` | Création | `181` L | Cas limites adaptateurs streaming httpx, fallbacks et test de connexion. |
| `tests/unit/test_gemini_endpoint_resolver_coverage.py` | Création | `287` L | Résolution PG18/snapshot/hub de `fallback_model_name` et transmission API `_ai_models_helpers`. |
| `apps/web/src/__tests__/gemini-protocol-mode-resolution.test.ts` | Création | `40` L | Tests Vitest de `resolveEffectiveLlmProtocolMode` (Gemini Mode A/B, Anthropic, OpenAI fallback). |

### 3.2 Résultats Chiffrés, Métriques & Qualité
- **Volumétrie des fichiers** : l'ensemble des 21 fichiers créés/modifiés respecte le seuil `<= 300` lignes (`132` à `300` L).
- **Couverture de branches (`coverage run --branch`)** : **`97 %`** combiné sur les 13 modules backend créés/modifiés (`1047 Stmts, 14 Miss, 374 Branch, 30 BrPart`, `119` tests unitaires ciblés passés, chaque module entre `91 %` et `99 %` : `_ai_models_helpers.py` `98%`, `_llm_streaming_fallbacks.py` `99%`, `_llm_streaming_http_helpers.py` `99%`, `ai_models_connection.py` `94%`, `ai_models_connection_helpers.py` `99%`, `ai_models_discovery_dialects.py` `95%`, `ai_models_urls.py` `99%`, `llm_endpoint_resolver.py` `95%`, `llm_gemini_interactions.py` `96%`, `llm_provider_parsing.py` `97%`, `llm_streaming_base_httpx.py` `99%`, `llm_usage_telemetry.py` `91%`, `llm_streaming_port.py` `96%`).
- **Qualité statique & Architecture** :
  - `ruff check .` & `ruff format --check .` : `All checks passed!`, `1562 files already formatted` (`0` erreur)
  - `mypy --strict packages/orcia-core packages/orcia-connectors apps/api apps/worker` : `Success: no issues found in 722 source files`
  - `lint-imports` : `Analyzed 765 files, 5614 dependencies. Contracts: 5 kept, 0 broken.`
  - `lint_spine.py` : `{"ok": true, "total_findings": 0}`
  - `scripts/export_openapi.py --check` : `0-diff` (exit `0`)
  - `detect-secrets-hook --baseline .secrets.baseline` : exit `0`
  - `gitnexus_detect_changes(repo="/home/romain/Documents/Projects/ORCIA", scope="all")` (après réindexation `42,294 nodes | 84,687 edges | 726 clusters | 1550 flows`) : `changed_count: 21`, `changed_files: 20`, `affected_count: 1550`, `risk_level: "critical"` (surface cœur d'orchestration LLM & configuration modèles).

### 3.3 Validation & Procédure de Test sur Toute la Pyramide (`AD-17` + 5 Garde-Fous de Câblage Vertical)
- **Couche 1a — Tests Unitaires Python (`pytest --no-cov`)** : suite complète `tests/unit` exécutée sans `--ignore` (`1049 passed`, exit `0`).
- **Couche 1b — Frontend TS (`pnpm turbo run lint typecheck test`)** : **`9/9` tâches vertes** en `38.524s` — `@orcia/api-client` (`3` fichiers, `20 passed`), `@orcia/ui` (`35` fichiers, `139 passed`), `@orcia/web` (`69` fichiers, `268 passed`, total **`427 passed`** JS/TS dont `gemini-protocol-mode-resolution.test.ts`).
- **Couche 2 — Intégration Verticale PG18 + Redis (`testcontainers`, `--no-cov`)** : **`15 passed` in `134.79s`** sur les 8 suites impactées (`test_story_17_5_ai_models_hub_postgres18.py`, `test_story_19_3_ai_models_connection_test_postgres18.py`, `test_story_19_5_ai_models_usage_postgres18.py`, `test_story_19_6_alembic_and_rag_blocking_postgres18.py`, `test_story_19_7_reindexing_and_blocking_postgres18.py`, `test_story_25_5_assistant_chat_only_and_rag_guard_postgres18.py`, `test_story_26_6a_supports_tools_postgres18.py`, `test_story_26_10_multi_worker_sse_stop_recovery_postgres18.py`).
- **Couche 3, 4 & Sécurité (`tests/security tests/evals tests/contract --no-cov`)** : **`180 passed`** (exit `0`), couvrant les audits AST d'isolation domaine/anti-patterns, garde SSRF, évaluations déterministes `0 $` et contrats OpenAPI/RFC 9457.
- **Couche 5 — E2E Navigateur Playwright Bi-Serveur (`desktop-cockpit`, `env -u ORCIA_E2E_SEED_FIXTURES`)** : **`7 passed (1.6m)`** sur `e2e/16-ai-models-reindex-connectors-and-broker.spec.ts` et `e2e/02-assistant-streaming-and-folders.spec.ts` (Jour 0 sans fixtures cachées, création/test/suppression modèles IA, garde SSRF, streaming cassette LLM et survie au `F5`).
