# 2026-11-23 — AI Model Edit API Key Exposure, Localized Preset Display Names & FR/EN Assistant Locale Alignment

- **Date** : 2026-11-23
- **Story / Clé Sprint** : `2026-11-23-ai-model-edit-api-key-and-fr-en-locale` (`Cross-Cutting UX & Locale Adjustment`)
- **Capacité(s)** : `CAP-052`, `CAP-053`, `CAP-074`, `CAP-076`, `CAP-190` — classification : `ux`
- **Auteur / Contexte** : Expose the optional API key input (`data-testid="ai-model-api-key-input"`) in `AiModelConfigModal` edit mode (`mode === "edit"` when `authMode === "api_key"`), localize provider preset display-name suffixes using `tierLabels` instead of raw tier keys, split oversized frontend i18n/form modules to stay strictly `<= 300` lines, and align backend French/English locale resolution and Assistant internal prompts (`resolve_request_locale`, `PROMPT_LOCALES["fr"].language_rule`, `_assistant_turn_producer_tool_loop.py`, `_assistant_turn_producer.py`).
- **Commits associés** : `pending`

---

## 1. Analyse du Besoin — Needs Analysis & Tech Lead Impact Study (Pre-Implementation)

### 1.1 Context & Problem Statement
- **Issue 1 — Missing API key input in AI Model edit mode (`AiModelFormFields.tsx`)**: Currently `data-testid="ai-model-api-key-input"` is rendered only when `mode === "create" && authMode === "api_key"`. Administrators editing an existing AI model mapping cannot update or switch to an API key directly inside the Edit modal, and `useAiModelConfigModalState.ts` omits `secret_input` from `AiModelPatchRequest` in `mode === "edit"`. Additionally, clicking a provider preset in `create` mode sets `displayName` using the raw internal key (`${preset.label} (${selectedTier})`) instead of the localized `tierLabels` badge.
- **Issue 2 — `Accept-Language` resolution bug (`_assistant_prompt_sanitization.py`)**: `resolve_request_locale` checks `",en" in raw` before inspecting the primary preferred language tag. A standard French browser header such as `Accept-Language: fr-FR,fr;q=0.9,en-US;q=0.8` resolves incorrectly to `"en"`.
- **Issue 3 — French Assistant language rule & internal tool-loop strings**: `PROMPT_LOCALES["fr"].language_rule` is currently written in English without defaulting to French for replies and generated artifacts when the UI locale is `"fr"`, and internal tool-loop synthesis/zero-token messages in `_assistant_turn_producer_tool_loop.py` and `_assistant_turn_producer.py` are hardcoded in English regardless of `locale`.
- **Architecture Constraints (`ARCHITECTURE-SPINE.md`)**:
  - Maintain strict `<= 300` line ceiling on every created or modified file (`AiModelFormFields.tsx` at `378` L split with `AiModelAuthAndEndpointFields.tsx`; `ai_models_hub_labels.ts` at `369` L split with `ai_models_hub_labels_en.ts`).
  - Zero raw user-facing UI strings hardcoded inside JSX; all labels/placeholders come from typed `apps/web/src/i18n/locales/` dictionaries.
  - Keep `AD-19` modular monolith boundaries (`lint-imports`) and `0-diff` OpenAPI contracts (`AiModelPatchRequest.secret_input` already exists in the backend schema and generated TypeScript SDK).

### 1.2 Exploration, GitNexus Impact, Refactoring & Technical Debt
- **Caller & Impact Analysis (`grep` + `gitnexus_impact`)**:
  - `AiModelFormFields`: single caller in `AiModelConfigModal.tsx`, with `378` lines prior to refactoring.
  - `useAiModelConfigModalState`: single hook consumer in `AiModelConfigModal.tsx`, `273` lines.
  - `ai_models_hub_labels.ts`: imported by 8 frontend modules and 6 test suites, `369` lines prior to splitting out `AI_MODELS_HUB_EN` into `ai_models_hub_labels_en.ts`.
  - `resolve_request_locale`: called by 6 API router modules (`_assistant_llm_stream_bridge.py`, `_mcp_assistant_ask_bridge.py`, `assistant_llm_bridge.py`, `assistant_llm_prompts.py`, `assistant_turns.py`, `assistant_workspace_governance.py`).
  - `PROMPT_LOCALES["fr"]`: consumed via `get_prompt_locale_bundle(locale)` in `assistant_prompt_builder.py` and `assistant_prompt_preview.py`.
- **Refactoring & File Size Control**:
  - Split `AiModelFormFields.tsx` (`378` L) into `AiModelFormFields.tsx` (`<= 230` L) and `AiModelAuthAndEndpointFields.tsx` (`<= 170` L).
  - Split `ai_models_hub_labels.ts` (`369` L) by moving `AI_MODELS_HUB_EN` to `ai_models_hub_labels_en.ts` and re-exporting it from `ai_models_hub_labels.ts` (matching `assistant_labels.ts` + `assistant_labels_en.ts`).

---

## 2. Plan d'Implémentation — Implementation Plan

### 2.1 Database Schema & Alembic Migrations (`infra/migrations/versions/...`)
- No Alembic migration required: `AiModelPatchRequest.secret_input` (`SecretInputPayload`) is already wired end-to-end in `apps/api/src/orcia_api/schemas/ai_models_hub.py`, `apps/api/src/orcia_api/routers/ai_models_hub.py`, and `packages/api-client/src/generated/ai_models_hub.ts`.

### 2.2 Hexagonal Core, Orchestration & Workers (`packages/orcia-core/`)
- `packages/orcia-core/src/orcia_core/orchestration/assistant_prompt_locales.py` (`<= 240` L): update `PROMPT_LOCALES["fr"].language_rule` to instruct the model in French to reply and author generated files/artifacts in French by default when the UI locale is `"fr"` (unless the user explicitly writes in or requests another language).

### 2.3 Backend API, Security & Contracts (`apps/api/`, `packages/api-client/`)
- `apps/api/src/orcia_api/routers/_assistant_prompt_sanitization.py` (`<= 200` L): fix `resolve_request_locale(request, explicit_locale)` to parse the primary preferred language tag (`raw.split(",")[0].split(";")[0].strip()`) before matching `"en"` or `"es"`, defaulting to `"fr"`.
- `apps/api/src/orcia_api/routers/_assistant_turn_locale_messages.py` (New, `<= 60` L), `_assistant_turn_producer_tool_loop.py` (`<= 298` L) & `_assistant_turn_producer.py` (`<= 299` L): localize internal forced-synthesis prompts (`synthesize-now` and budget reached), reflexive step summary, and zero-token diagnostic error message based on `locale` (`"fr"` vs `"en"`).

### 2.4 User Interface & Experience (`apps/web/`)
- `apps/web/src/i18n/locales/ai_models_hub_labels.ts` (`<= 270` L) & `apps/web/src/i18n/locales/ai_models_hub_labels_en.ts` (`<= 160` L): add `secretApiKeyCreatePlaceholder` and `secretApiKeyEditPlaceholder` in French and English and re-export `AI_MODELS_HUB_EN` cleanly.
- `apps/web/src/features/admin/ai-models/AiModelAuthAndEndpointFields.tsx` (New, `<= 170` L): extract model/endpoint/authentication fields and render `data-testid="ai-model-api-key-input"` for `(mode === "create" || mode === "edit") && authMode === "api_key"` with localized label and create/edit placeholders.
- `apps/web/src/features/admin/ai-models/AiModelFormFields.tsx` (`<= 230` L): delegate bottom fields to `AiModelAuthAndEndpointFields` and resolve localized preset display names using `tierLabels` (`simpleBadge`, `mediumBadge`, `complexBadge`, `autoBadge`).
- `apps/web/src/features/admin/ai-models/useAiModelConfigModalState.ts` (`<= 285` L): reset `setRawApiKey("")` in `edit` / `rotate-key` initialization and pass `secret_input: authMode === "api_key" && rawApiKey.trim() ? { action: "set", plaintext_value: rawApiKey.trim() } : undefined` in `AiModelPatchRequest`.

### 2.5 Test Pyramid Impact (`AD-17` — Layers 1 to 5 + Security)
- **Layer 1a (Python Unit `tests/unit/`)**: add `tests/unit/test_assistant_locale_and_tool_loop_i18n.py` (`<= 160` L) testing `resolve_request_locale`, `PROMPT_LOCALES["fr"].language_rule`, and FR/EN localized prompts/messages in `_assistant_turn_producer_tool_loop.py` and `_assistant_turn_producer.py`.
- **Layer 1b (Frontend Vitest `apps/web/src/__tests__/`)**: add `apps/web/src/__tests__/ai-model-edit-modal-api-key.test.tsx` (`<= 180` L) testing `AiModelFormFields` (`create` & `edit` API key input + FR/EN placeholders, localized preset `displayName`) and `useAiModelConfigModalState` (`secret_input` included when provided, omitted when blank).
- **Layers 2–5**: deferred to the independent Testing Sub-Agent after Coding completes.

---

## 3. Bilan des Modifications — Summary of Changes & Results

### 3.1 Modified & Created Files
| File | Action | Lines (`wc -l`) | Summary |
| :--- | :--- | :---: | :--- |
| `packages/orcia-core/src/orcia_core/orchestration/assistant_prompt_locales.py` | Modified | 227 | Aligned `PROMPT_LOCALES["fr"]` and `PROMPT_LOCALES["en"]` `language_rule` strings for default FR/EN output & artifact authoring while preserving explicit user-language overrides. |
| `apps/api/src/orcia_api/routers/_assistant_prompt_sanitization.py` | Modified | 185 | Fixed `resolve_request_locale` to evaluate the primary preferred language tag (`raw.split(",")[0].split(";")[0].strip()`) before matching `en`/`es`, defaulting to `fr`. |
| `apps/api/src/orcia_api/routers/_assistant_turn_locale_messages.py` | Created | 55 | Extracted localized `fr`/`en` internal synthesis prompts, reflexive step summaries, and zero-token diagnostic messages to keep producer modules `<= 300` lines. |
| `apps/api/src/orcia_api/routers/_assistant_turn_producer_tool_loop.py` | Modified | 291 | Routed `synthesize-now`, tool-budget reached prompts, and reflexive step summaries through `_assistant_turn_locale_messages.py`. |
| `apps/api/src/orcia_api/routers/_assistant_turn_producer.py` | Modified | 299 | Routed zero-token stream diagnostic error detail through `format_zero_tokens_error_detail(..., locale)`. |
| `apps/web/src/features/admin/ai-models/AiModelAuthAndEndpointFields.tsx` | Created | 180 | Extracted model/endpoint/authentication fields and exposed `data-testid="ai-model-api-key-input"` in both `create` and `edit` modes when `authMode === "api_key"` with localized placeholders. |
| `apps/web/src/features/admin/ai-models/AiModelFormFields.tsx` | Modified | 281 | Delegated bottom fields to `AiModelAuthAndEndpointFields` and localized provider preset `displayName` suffixes via `tierLabels` (`simpleBadge`/`mediumBadge`/`complexBadge`/`autoBadge`). |
| `apps/web/src/features/admin/ai-models/useAiModelConfigModalState.ts` | Modified | 278 | Reset `rawApiKey` on `edit`/`rotate-key` initialization and included `secret_input` in `AiModelPatchRequest` when a non-empty API key is entered in `edit` mode. |
| `apps/web/src/i18n/locales/ai_models_hub_labels.ts` | Modified | 251 | Added `secretApiKeyCreatePlaceholder` and `secretApiKeyEditPlaceholder` in French (`AI_MODELS_HUB_FR`) and re-exported `AI_MODELS_HUB_EN`. |
| `apps/web/src/i18n/locales/ai_models_hub_labels_en.ts` | Created | 127 | Split out `AI_MODELS_HUB_EN` dictionary (`<= 300` lines) with English `secretApiKeyCreatePlaceholder` and `secretApiKeyEditPlaceholder`. |
| `tests/unit/test_assistant_locale_and_tool_loop_i18n.py` | Created | 188 | Unit tests covering `resolve_request_locale` (`Accept-Language` priority), `PROMPT_LOCALES["fr"]`/`["en"]`, and FR/EN tool-loop & zero-token localized messages. |
| `tests/unit/test_epic_10_story_10_2_three_speed_router.py` | Modified | 191 | Aligned router tests and split tier-routing assertions into a dedicated module `<= 300` lines. |
| `tests/unit/test_epic_10_story_10_2_three_speed_tier_routing.py` | Created | 249 | Dedicated tier-routing unit tests split from `test_epic_10_story_10_2_three_speed_router.py`. |
| `apps/web/src/__tests__/ai-model-edit-modal-api-key.test.tsx` | Created | 170 | Vitest tests verifying `AiModelFormFields` (`create`/`edit` API key field, FR/EN placeholders, localized preset `displayName`) and `useAiModelConfigModalState` (`secret_input` patch behavior). |

### 3.2 Quantitative Metrics, Coverage & Static Quality
- **Targeted Branch Coverage (`coverage run --branch`, `73 passed` across `test_assistant_*.py`, `test_epic_10_*.py`, `test_story_26_2_*.py`, `test_story_26_3_*.py`, `test_story_26_6b_*.py`, `test_story_26_7_*.py`, `test_story_26_8_*.py`)**: **`98%`** total (`142` stmts, `3` miss, `18` branches, `1` partial):
  - `apps/api/src/orcia_api/routers/_assistant_prompt_sanitization.py`: **`94%`**
  - `apps/api/src/orcia_api/routers/_assistant_turn_locale_messages.py`: **`100%`**
  - `apps/api/src/orcia_api/routers/_assistant_turn_producer.py`: **`100%`**
  - `apps/api/src/orcia_api/routers/_assistant_turn_producer_tool_loop.py`: **`94%`**
  - `packages/orcia-core/src/orcia_core/orchestration/assistant_prompt_locales.py`: **`100%`**
- **File Size Discipline**: All `14` modified/created source and test files are strictly `<= 299` lines (`2,972` lines total).
- **Static & Architecture Gates**:
  - `.venv/bin/ruff check .` & `.venv/bin/ruff format --check .`: `0` issues (`1566` files formatted).
  - `.venv/bin/mypy --strict packages/orcia-core packages/orcia-connectors apps/api apps/worker`: `0` issues across `723` source files.
  - `.venv/bin/lint-imports`: `5` contracts kept, `0` broken (`766` files, `5617` dependencies).
  - `lint_spine.py`: `ok: true`, `0` findings.
  - `scripts/export_openapi.py --check`: `0-diff` (`exit 0`).
  - `detect-secrets-hook --baseline .secrets.baseline`: `exit 0`.
  - `gitnexus_detect_changes` (`repo: "/home/romain/Documents/Projects/ORCIA"`, `scope: "all"`): `changed_count: 14`, `affected_count: 3`, `changed_files: 18`, `risk_level: "medium"` (`run_streaming_tool_loop` flows & AI-model modal symbols).

### 3.3 AD-17 Test Pyramid & Vertical Wiring Verification
- **Layer 1a — Python Unit Tests**: Full `pytest tests/unit --no-cov -q --tb=short` passed (`exit 0`, `[100%]`), including `test_assistant_locale_and_tool_loop_i18n.py`, `test_epic_10_story_10_2_three_speed_router.py`, `test_epic_10_story_10_2_three_speed_tier_routing.py`, and `test_site_catalog_sync.py`.
- **Layer 1b — TypeScript Monorepo (`pnpm turbo run lint typecheck test`)**: `9/9` tasks succeeded (`@orcia/api-client` `3` test files / `20` tests, `@orcia/ui` `35` test files, `@orcia/web` `70` test files / `270` tests, `exit 0`).
- **Layer 2 — PG18 + Redis Integration (`testcontainers`, `--no-cov`)**: `6/6` passed across two isolated batches:
  - Batch 1 (`test_story_17_5_ai_models_hub_postgres18.py`, `test_story_19_3_ai_models_connection_test_postgres18.py`, `test_story_25_5_assistant_chat_only_and_rag_guard_postgres18.py`): `5 passed in 51.23s` (`exit 0`).
  - Batch 2 (`test_story_26_10_multi_worker_sse_stop_recovery_postgres18.py`): `1 passed in 34.39s` (`exit 0`).
- **Layer 3 & 4 & Security (`pytest tests/security tests/evals tests/contract --no-cov -q`)**: `180 passed` (`exit 0`).
- **Layer 5 — Playwright Desktop E2E (`env -u ORCIA_E2E_SEED_FIXTURES`, `--project=desktop-cockpit`)**: `7 passed (1.7m)` across `apps/web/e2e/16-ai-models-reindex-connectors-and-broker.spec.ts` and `apps/web/e2e/02-assistant-streaming-and-folders.spec.ts` (`exit 0`).
