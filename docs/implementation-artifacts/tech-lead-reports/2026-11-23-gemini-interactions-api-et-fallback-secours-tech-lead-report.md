# 2026-11-23 — Google Gemini Interactions API Support, Runtime Secondary Fallback Model & Frontend Protocol Resolution

- **Date** : 2026-11-23
- **Story / Clé Sprint** : `2026-11-23-gemini-interactions-api-et-fallback-secours` (`Cross-Cutting Adjustment`)
- **Capacité(s)** : `CAP-052`, `CAP-053`, `CAP-074`, `CAP-076`, `CAP-190` — classification : `feature`
- **Auteur / Contexte** : Support for the Google Gemini Interactions API (`/v1beta/interactions`) for specialized models (`antigravity-*`, `deep-research-*`, or HTTP 400 responses requiring the Interactions API), automatic runtime fallback to `fallback_model_name` before first SSE byte emission or in synchronous completion, priority sorting of Gemini discovery (`gemini-*` chat models first + `createInteraction` support), and consistent `protocol_mode` resolution on the frontend (`apps/web`). Covered requirements: `AD-15`, `AD-17`, `AD-19`, `AD-21`, `AD-24`, `CAP-076`.
- **Commits associés** : `pending`

---

## 1. Analyse du Besoin — Needs Analysis & Tech Lead Impact Study (Pre-Implementation)

### 1.1 Context & Problem Statement
- **Issue 1 — Google Gemini models restricted to the Interactions API (`/v1beta/interactions`)**: Certain emerging models or Google Gemini agents (e.g., `antigravity-preview-05-2026`, `deep-research-*`) reject `:generateContent` / `:streamGenerateContent` requests with `HTTP 400` (`"This model only supports Interactions API."`), and may expect `"model"` or `"agent"` depending on the target endpoint.
- **Issue 2 — Secondary fallback model (`fallback_model_name`) unused at runtime and during connection testing**: Although `fallback_model_name` was already persisted in PG18 (`ai_model_mappings`) and editable in the UI, `LlmEndpointConfig`, `BaseHttpxLlmAdapter`, `llm_endpoint_resolver.py`, and `test_ai_model_endpoint_connection` did not propagate or execute automatic fallback to that secondary model when the primary model fails before the first byte (excluding `401/403`).
- **Issue 3 — Gemini discovery sorting & frontend `protocol_mode`**: `discover_gemini_native` sorted strictly alphabetically (placing `antigravity-*` or `aqa` ahead of `gemini-*`) and ignored `createInteraction` in `supportedGenerationMethods`. On the frontend, `handleQuickSubmit` and certain create/edit paths forced `"openai_compatible"` instead of deriving `gemini_native` or `anthropic_messages` from the family/URL.
- **Architecture Constraints (`ARCHITECTURE-SPINE.md`)**:
  - Strict `AD-19` (`lint-imports`) compliance: zero external SDK imports (`httpx`, `fastapi`, `sqlalchemy`) in `orcia_core/ports` (`llm_streaming_port.py`) or in the pure dialect module `llm_gemini_interactions.py`.
  - Strict `<= 300` line ceiling per modified/created file (including reducing `useAiModelConfigModalState.ts` from `321` L to `<= 295` L).
  - Mandatory structured logging on every fallback/error (`logger.warning`, zero silent `except Exception:`).

### 1.2 Exploration, GitNexus Impact, Refactoring & Technical Debt
- **GitNexus Impact Analysis (`gitnexus_query`, `gitnexus_context`, `gitnexus_impact`)**:
  - `is_google_gemini_native_provider`: **131** upstream symbols/processes impacted — behavior preserved identically for Mode A/B.
  - `build_gemini_native_request_body`: **176** upstream symbols/processes impacted — unchanged; Interactions API payloads are isolated in `llm_gemini_interactions.py` and activated only for `/interactions` URLs or HTTP 400 auto-switch.
  - `BaseHttpxLlmAdapter.complete_chat`: **181** upstream symbols/processes impacted.
  - `BaseHttpxLlmAdapter.stream_chat_events`: **130** upstream symbols/processes impacted.
- **Refactoring & File Size Control**:
  - Extracted Interactions API and secondary fallback request builders into `_llm_streaming_http_helpers.py` (`<= 220` L) to keep `llm_streaming_base_httpx.py` under `270` L.
  - Completely isolated the Google Interactions API dialect in `packages/orcia-core/src/orcia_core/orchestration/llm_gemini_interactions.py` (`<= 220` L), reusing `separate_think_tags` from `llm_gemini_dialect.py`.
  - Consolidated frontend protocol detection into `resolveEffectiveLlmProtocolMode` (`settingsAiModelsPresets.ts`), shared between `useAiModelsSectionController.ts` and `useAiModelConfigModalState.ts` (reducing the latter from `321` L to `<= 295` L).

---

## 2. Plan d'Implémentation — Implementation Plan

### 2.1 Database Schema & Alembic Migrations (`infra/migrations/versions/...`)
- No Alembic migration required: the `fallback_model_name` column already exists in `ai_model_mappings` and `AiModelMappingRecord` (`sql_ai_model_queries.py`).

### 2.2 Hexagonal Core, Orchestration & Workers (`packages/orcia-core/`)
- `packages/orcia-core/src/orcia_core/ports/llm_streaming_port.py` (`<= 295` L): add `fallback_model_name: str | None = None` on `LlmEndpointConfig` (zero external SDK imports).
- `packages/orcia-core/src/orcia_core/orchestration/ai_models_urls.py` (`<= 160` L): add `is_gemini_interactions_only_model`, `is_gemini_interactions_url`, `build_gemini_interactions_url`, and routing inside `build_gemini_native_chat_url`.
- `packages/orcia-core/src/orcia_core/orchestration/llm_gemini_interactions.py` (New, `<= 220` L): pure module (zero external SDK imports) exposing `is_gemini_interactions_api_required_error`, `is_gemini_interactions_agent_field_required_error`, `build_gemini_interactions_probe_body`, `build_gemini_interactions_request_body`, `parse_gemini_interactions_response`, and `extract_gemini_interactions_stream_deltas`.
- `packages/orcia-core/src/orcia_core/orchestration/llm_provider_parsing.py` (`<= 230` L) & `llm_usage_telemetry.py` (`<= 160` L): support `/interactions` URLs, `outputs`/`steps`/`interaction`/`output_text` response parsing, `delta`/`content.*`/`step.*`/`interaction.*` SSE deltas, and `usage.total_input_tokens` / `total_output_tokens` + `interaction.usage`.
- `packages/orcia-core/src/orcia_core/orchestration/llm_endpoint_resolver.py` (`<= 215` L): propagate `fallback_model_name` from JSON snapshot (`secondaryModel` / `fallback_model_name`), PG18 path (`rec.fallback_model_name`), and `hub_svc`.
- `packages/orcia-core/src/orcia_core/orchestration/_llm_streaming_http_helpers.py` (`<= 220` L) & `llm_streaming_base_httpx.py` (`<= 270` L): HTTP 400 Interactions API auto-switch (`model` then `agent` on 400/404) and fallback to `fallback_model_name` before the first byte (excluding `401`/`403`) with structured `logger.warning`.
- `packages/orcia-core/src/orcia_core/orchestration/ai_models_connection_helpers.py` (`<= 230` L) & `ai_models_connection.py` (`<= 290` L): Interactions API probe support, auto-switch + `agent` retry, and connection-test fallback to `fallback_model_name` with localized FR/EN diagnostics.
- `packages/orcia-core/src/orcia_core/orchestration/ai_models_discovery_dialects.py` (`<= 298` L): support `createInteraction` and sort `gemini-*` chat models ahead of other chat/embedding and unknown models.

### 2.3 Backend API, Security & Contracts (`apps/api/`, `packages/api-client/`)
- `apps/api/src/orcia_api/routers/_ai_models_helpers.py` (`<= 265` L): forward `fallback_model_name=rec.fallback_model_name` to `test_ai_model_endpoint_connection` in `execute_model_connection_test`.
- No OpenAPI schema or HTTP router changes required.

### 2.4 User Interface & Experience (`apps/web/`)
- `apps/web/src/routes/settingsAiModelsPresets.ts` (`<= 235` L): export `resolveEffectiveLlmProtocolMode(modelFamily, endpointUrl, fallbackMode)`.
- `apps/web/src/routes/useAiModelsSectionController.ts` (`<= 290` L): use `resolveEffectiveLlmProtocolMode` in `handleQuickSubmit`.
- `apps/web/src/features/admin/ai-models/useAiModelConfigModalState.ts` (`<= 295` L): use `resolveEffectiveLlmProtocolMode` in `triggerDiscovery` and `handleFormSubmit` (`create` and `edit`), while reducing the file to `<= 295` lines.

### 2.5 Test Pyramid Impact (`AD-17` — Layers 1 to 5 + Security)
- **Layer 1a (Python Unit `tests/unit/`) & Layer 1b (Frontend TS `Vitest`)**:
  - Created `tests/unit/test_gemini_interactions_and_fallback_model.py` (`<= 280` L) covering Interactions API auto-switch (`model` & `agent`), Interactions API parsing/streaming, secondary model fallback (runtime + connection test + `401/403` exclusion), and `discover_gemini_native` sorting.
  - Created a Vitest suite in `apps/web/src/__tests__/` for `resolveEffectiveLlmProtocolMode` (Gemini Mode A/B + Anthropic + OpenAI fallback).
- **Layers 2 / 3 / 4 / Security / 5**: full verification executed by the independent Testing Sub-Agent at the end of implementation.

---

## 3. Bilan des Modifications — Summary of Changes & Results (Post-Implementation)

### 3.1 Created & Modified Files
| File | Action | Line Count | Summary |
| :--- | :--- | :--- | :--- |
| `packages/orcia-core/src/orcia_core/ports/llm_streaming_port.py` | Modified | `289` L | Added `fallback_model_name: str \| None = None` to `LlmEndpointConfig` (zero external SDK imports `AD-19`). |
| `packages/orcia-core/src/orcia_core/orchestration/ai_models_urls.py` | Modified | `154` L | Added Gemini Interactions API routing (`is_gemini_interactions_only_model`, `is_gemini_interactions_url`, `build_gemini_interactions_url`, `build_gemini_native_chat_url`). |
| `packages/orcia-core/src/orcia_core/orchestration/llm_gemini_interactions.py` | Created | `196` L | Pure Google Gemini Interactions dialect (`/v1beta/interactions`): `model`/`agent` payload, `system_instruction`, `tools`, `outputs`/`steps` parsing and SSE deltas. |
| `packages/orcia-core/src/orcia_core/orchestration/llm_provider_parsing.py` | Modified | `208` L | Added `/interactions` support to response parsing and streaming SSE deltas. |
| `packages/orcia-core/src/orcia_core/orchestration/llm_usage_telemetry.py` | Modified | `158` L | Extracted `usage.total_input_tokens` / `total_output_tokens` and `interaction.usage` token counts. |
| `packages/orcia-core/src/orcia_core/orchestration/llm_endpoint_resolver.py` | Modified | `194` L | Propagated `fallback_model_name` from JSON snapshot, PG18 (`rec.fallback_model_name`), and `hub_svc`. |
| `packages/orcia-core/src/orcia_core/orchestration/_llm_streaming_http_helpers.py` | Modified | `210` L | Interactions API request helpers and `build_secondary_model_fallback_request` (anti-loop). |
| `packages/orcia-core/src/orcia_core/orchestration/_llm_streaming_fallbacks.py` | Created | `132` L | Encapsulated HTTP fallback attempts for Interactions API (`model` $\rightarrow$ `agent`) and secondary model fallback. |
| `packages/orcia-core/src/orcia_core/orchestration/llm_streaming_base_httpx.py` | Modified | `262` L | HTTP 400 Interactions API auto-switch (`model` then `agent`) and `fallback_model_name` fallback before first byte (excluding `401`/`403`) with `logger.warning`. |
| `packages/orcia-core/src/orcia_core/orchestration/ai_models_connection_helpers.py` | Modified | `248` L | Interactions API probe, auto-switch + `agent` retry, and connection-test helpers. |
| `packages/orcia-core/src/orcia_core/orchestration/ai_models_connection.py` | Modified | `281` L | Connection-test fallback to `fallback_model_name` (excluding `401`/`403`) with localized FR/EN diagnostics. |
| `packages/orcia-core/src/orcia_core/orchestration/ai_models_discovery_dialects.py` | Modified | `300` L | Added `createInteraction` support in `discover_gemini_native` and priority sorting of `generateContent` models ahead of other chat/embedding and unknown models. |
| `apps/api/src/orcia_api/routers/_ai_models_helpers.py` | Modified | `255` L | Forwarded `fallback_model_name=rec.fallback_model_name` in `execute_model_connection_test`. |
| `apps/web/src/routes/settingsAiModelsPresets.ts` | Modified | `233` L | Exported `resolveEffectiveLlmProtocolMode(modelFamily, endpointUrl, fallbackMode)`. |
| `apps/web/src/routes/useAiModelsSectionController.ts` | Modified | `286` L | Consistent `protocol_mode` detection in `handleQuickSubmit` via `resolveEffectiveLlmProtocolMode`. |
| `apps/web/src/features/admin/ai-models/useAiModelConfigModalState.ts` | Modified / Refactored | `273` L | Shared `resolveEffectiveLlmProtocolMode` in `triggerDiscovery`/`handleFormSubmit` and reduced file size below `300` lines. |
| `tests/unit/test_gemini_interactions_and_fallback_model.py` | Created | `272` L | Unit tests for Interactions API, secondary model fallback, and Gemini discovery sorting. |
| `tests/unit/test_gemini_interactions_coverage_edges.py` | Created | `244` L | Edge-case coverage for Interactions API dialect, URLs, parsing, and token telemetry. |
| `tests/unit/test_gemini_adapters_coverage_edges.py` | Created | `181` L | Edge-case coverage for httpx streaming adapters, fallbacks, and connection testing. |
| `tests/unit/test_gemini_endpoint_resolver_coverage.py` | Created | `287` L | Coverage for PG18/snapshot/hub resolution of `fallback_model_name` and `_ai_models_helpers` forwarding. |
| `apps/web/src/__tests__/gemini-protocol-mode-resolution.test.ts` | Created | `40` L | Vitest tests for `resolveEffectiveLlmProtocolMode` (Gemini Mode A/B, Anthropic, OpenAI fallback). |

### 3.2 Metrics, Coverage & Quality Gates
- **File Line Counts**: all 21 created/modified files comply with the `<= 300` line threshold (`132` to `300` L).
- **Branch Coverage (`coverage run --branch`)**: **`97 %`** combined across the 13 created/modified backend modules (`1047 Stmts, 14 Miss, 374 Branch, 30 BrPart`, `119` targeted unit tests passed, every module between `91 %` and `99 %`: `_ai_models_helpers.py` `98%`, `_llm_streaming_fallbacks.py` `99%`, `_llm_streaming_http_helpers.py` `99%`, `ai_models_connection.py` `94%`, `ai_models_connection_helpers.py` `99%`, `ai_models_discovery_dialects.py` `95%`, `ai_models_urls.py` `99%`, `llm_endpoint_resolver.py` `95%`, `llm_gemini_interactions.py` `96%`, `llm_provider_parsing.py` `97%`, `llm_streaming_base_httpx.py` `99%`, `llm_usage_telemetry.py` `91%`, `llm_streaming_port.py` `96%`).
- **Static Quality & Architecture**:
  - `ruff check .` & `ruff format --check .`: `All checks passed!`, `1562 files already formatted` (`0` errors)
  - `mypy --strict packages/orcia-core packages/orcia-connectors apps/api apps/worker`: `Success: no issues found in 722 source files`
  - `lint-imports`: `Analyzed 765 files, 5614 dependencies. Contracts: 5 kept, 0 broken.`
  - `lint_spine.py`: `{"ok": true, "total_findings": 0}`
  - `scripts/export_openapi.py --check`: `0-diff` (exit `0`)
  - `detect-secrets-hook --baseline .secrets.baseline`: exit `0`
  - `gitnexus_detect_changes(repo="/home/romain/Documents/Projects/ORCIA", scope="all")` (after re-indexing `42,294 nodes | 84,687 edges | 726 clusters | 1550 flows`): `changed_count: 21`, `changed_files: 20`, `affected_count: 1550`, `risk_level: "critical"` (core LLM orchestration & model configuration surface).

### 3.3 Full Test Pyramid Validation (`AD-17` + Vertical Wiring Guardrails)
- **Layer 1a — Python Unit Tests (`pytest --no-cov`)**: full `tests/unit` suite passed without `--ignore` (`1049 passed`, exit `0`).
- **Layer 1b — Frontend TS (`pnpm turbo run lint typecheck test`)**: **`9/9` tasks green** in `38.524s` — `@orcia/api-client` (`3` files, `20 passed`), `@orcia/ui` (`35` files, `139 passed`), `@orcia/web` (`69` files, `268 passed`, total **`427 passed`** JS/TS including `gemini-protocol-mode-resolution.test.ts`).
- **Layer 2 — PG18 + Redis Vertical Integration (`testcontainers`, `--no-cov`)**: **`15 passed` in `134.79s`** across the 8 impacted suites (`test_story_17_5_ai_models_hub_postgres18.py`, `test_story_19_3_ai_models_connection_test_postgres18.py`, `test_story_19_5_ai_models_usage_postgres18.py`, `test_story_19_6_alembic_and_rag_blocking_postgres18.py`, `test_story_19_7_reindexing_and_blocking_postgres18.py`, `test_story_25_5_assistant_chat_only_and_rag_guard_postgres18.py`, `test_story_26_6a_supports_tools_postgres18.py`, `test_story_26_10_multi_worker_sse_stop_recovery_postgres18.py`).
- **Layer 3, 4 & Security (`tests/security tests/evals tests/contract --no-cov`)**: **`180 passed`** (exit `0`), covering domain isolation AST audits, anti-pattern audits, SSRF guard, `$0` deterministic evals, and OpenAPI/RFC 9457 contracts.
- **Layer 5 — Bi-Server Playwright Browser E2E (`desktop-cockpit`, `env -u ORCIA_E2E_SEED_FIXTURES`)**: **`7 passed (1.6m)`** on `e2e/16-ai-models-reindex-connectors-and-broker.spec.ts` and `e2e/02-assistant-streaming-and-folders.spec.ts` (Day-0 without hidden fixtures, AI model create/test/delete, SSRF guard, cassette LLM streaming, and `F5` cold reload survival).
