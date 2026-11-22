# Story 26.6a — `LlmStreamingPort` Native Tool Calls on 2 Dialects (OpenAI-Compatible & Anthropic), `supports_tools` Flag & Loop Budgets

- **Date**: 2026-11-22
- **Story / Sprint Key**: `26-6a-llm-streaming-port-tool-calls-and-loop-budgets` (`Epic 26` — Lot 5.1)
- **Capabilities**: `CAP-074`, `CAP-076`, `CAP-190` — classification: `feature` (`AD-24` Rule 8, `AD-25` Rule 6)
- **Author / Context**: Dedicated Coding Sub-Agent — Implement native streamed and non-streamed `tool_calls` parsing/formatting strictly across 2 dialects (`openai_compatible` and `anthropic`), persist 0-token discovered `supports_tools` with `PLATFORM_ADMIN` override in PostgreSQL 18, enforce `HTTP 422 ERR_MODEL_TOOLS_UNSUPPORTED` on Speed 2/3 when `supports_tools=false`, preserve all 3 text streaming adapters (`CAP-076`) and `AD-24.6` chat-only usability, and add deterministic multi-step loop budgets (`assistant_loop_budgets.py`) with extended `DeterministicCassetteLLM` cassettes.
- **Associated Commits**: *(pending coordinator atomic commit after Testing Sub-Agent verification)*

---

## 1. Need Analysis & Tech Lead Impact Study (Analyse du Besoin)

### 1.1 Context & Problem Statement
- **Current Gaps (`H-03`, `H-04`, `H-27`, `D5 + R7`)**:
  1. `LlmStreamingPort` (`packages/orcia-core/src/orcia_core/ports/llm_streaming_port.py`) currently emits `LlmStreamDelta` with only `thinking_delta`, `token_delta`, `turn_completed`, and `stream_error`. Streamed `delta.tool_calls` (OpenAI-compatible) and `tool_use` / `input_json_delta` (Anthropic) are silently dropped during SSE streaming, and there are no typed `ContentDelta | ReasoningDelta | ToolCallDelta | Usage | Finish` stream events.
  2. `BaseHttpxLlmAdapter.complete_chat()` (`llm_streaming_base_httpx.py:L108-113`) drops `tools` (and `tool_choice`) on the OpenAI HTTP 404 legacy fallback (`/api/chat` or fallback endpoint), breaking tool-calling requests whenever fallback triggers.
  3. Tool-result re-injection (`role: "tool"` with `tool_call_id` for OpenAI-compatible; `role: "user"` with `tool_result` content blocks for Anthropic) is missing from `llm_provider_parsing.py` / `llm_gemini_dialect.py`, and `assistant_llm_bridge.py` falls back to a synthetic `role: "user"` prompt instead of native dialect tool-result turns.
  4. `workspace_llm_tier_mappings` in PostgreSQL 18 lacks `supports_tools` and `supports_tools_override` columns. Consequently, AI Hub 0-token discovery (`ai_models_discovery_dialects.py`) and connection testing (`ai_models_connection.py`) do not persist tool-calling capability, `PLATFORM_ADMIN` cannot manually override it, `gemini_native` and non-`/v1` native Ollama endpoints are not flagged `supports_tools=false` (`ACTION_ITEM-26.4`), and Speed 2/3 requests against `supports_tools=false` models are not rejected pre-stream with `HTTP 422 ERR_MODEL_TOOLS_UNSUPPORTED` (`D5`).
  5. There is no bounded multi-step tool-loop budget controller in `orcia_core/orchestration/` enforcing `max_iterations`, cumulative `max_total_tokens`, and `max_wall_clock_seconds` with clean forced synthesis or `TurnBudgetExceededError` (`ERR_ASSISTANT_TURN_BUDGET_EXCEEDED`).
- **Spine Constraints (`AD-19`, `AD-24`, `AD-25`)**:
  - `orcia_core/ports/llm_streaming_port.py` must remain pure Python with zero framework/SDK imports (`lint-imports` 5/5).
  - All 3 text/reasoning streaming adapters (`openai_compatible`, `anthropic`, `gemini_native` `CAP-076`) and strict `thinking`/`content` separation must remain intact.
  - SSRF DNS pinning (`prepare_pinned_http_request`) and `AD-24.6` (`Story 25.5`: `"Mon Assistant"` unlocked with 1 active `chat` model and `0` `embedding` models) must remain preserved.
  - Every touched or created non-generated source file must stay `<= 300` lines.

### 1.2 Exploration, GitNexus Impact Analysis, Refactoring & Technical Debt
- **GitNexus Impact Analysis (`repo: /home/romain/Documents/Projects/ORCIA`)**:
  - `gitnexus_query` & `gitnexus_impact` on `LlmStreamingPort`, `complete_chat`, and `stream_chat_sse` identified `HttpxMultiProviderLlmStreamingAdapter.complete_chat` (`impactedCount: 145`, `risk: HIGH`) and `LlmStreamingPort` protocol implementers across `packages/orcia-core/src/orcia_core/orchestration/llm_streaming_*`, `packages/orcia-core/src/orcia_core/testing/cassette_llm.py`, `apps/api/src/orcia_api/routers/_assistant_turn_producer.py`, `apps/api/src/orcia_api/routers/assistant_llm_bridge.py`, and existing unit test fakes (`_SpyLlmPort`, `_EmptyPort`, `_SlowStreamingPort`, `_ExplodingPort`).
  - Maintaining backward compatibility on `LlmStreamingPort` (`complete_chat` and `stream_chat_sse`) while adding typed stream events (`ContentDelta | ReasoningDelta | ToolCallDelta | Usage | Finish` and `stream_chat_events`) ensures zero breakage in `test_story_26_2_*` and `test_story_26_3_*`.
- **Database & Schema Findings**:
  - The authoritative AI Models Hub table in PG18 is `workspace_llm_tier_mappings` (created in `0022`, extended in `20261114_1705`, `20261115_2105`, and `20261122_264a`). Single Alembic head is `20261122_265`.
  - `_first_boot_reset_guards.py` already truncates/cleans `workspace_llm_tier_mappings` safely without requiring table list changes.
  - `sql_ai_model_queries.py` uses explicit column selection (`COLUMNS_SELECT`) mapped by positional tuple indices (`row[0..31]`); adding `supports_tools` and `supports_tools_override` at positions `32` and `33` is clean and deterministic.
- **Refactoring & Line-Budget Control (`<= 300` L)**:
  - `ai_models_governance.py` is currently `392` lines (`> 300` L). Before modifying it, delete/impact helpers will be extracted into `_ai_models_delete_helpers.py` so both files remain `<= 260` lines.
  - `llm_streaming_base_httpx.py` (`294` L) will delegate dialect-specific tool-call accumulation, stream chunk extraction, and message formatting to a dedicated `llm_tool_dialects.py` (`<= 280` L) so `llm_streaming_base_httpx.py` stays `<= 270` lines.
  - `ai_models_discovery_dialects.py` (`291` L) will reuse shared capability inference helpers in `ai_models_capabilities.py` (`<= 120` L) so all discovery files stay `<= 295` lines.
  - `ai_models_hub.py` (`296` L), `_assistant_turn_producer.py` (`296` L), and `assistant_workspace.py` (`295` L) will stay strictly `<= 300` lines by delegating validation/mapping helpers to `_ai_models_helpers.py`, `assistant_llm_resolver.py`, and `_assistant_turn_producer_helpers.py`.
  - `cassette_llm.py` (`207` L) will offload tool-calling cassette fixtures to `packages/orcia-core/src/orcia_core/testing/_cassette_tool_cassettes.py` (`<= 200` L).

---

## 2. Implementation Plan (Plan d'Implémentation)

### 2.1 Data Schema & Alembic Migrations (`infra/migrations/versions/`)
- **`infra/migrations/versions/20261122_266a_story_26_6a_llm_supports_tools.py`**:
  - `revision = "20261122_266a"`, `down_revision = "20261122_265"`.
  - Pure raw SQL (`op.execute(sa.text(...))`), zero ORM imports:
    - `upgrade()`: `ALTER TABLE workspace_llm_tier_mappings ADD COLUMN IF NOT EXISTS supports_tools BOOLEAN NOT NULL DEFAULT FALSE, ADD COLUMN IF NOT EXISTS supports_tools_override BOOLEAN NULL;`
    - `downgrade()`: `ALTER TABLE workspace_llm_tier_mappings DROP COLUMN IF EXISTS supports_tools_override, DROP COLUMN IF EXISTS supports_tools;`
  - Effective capability rule: `COALESCE(supports_tools_override, supports_tools)`.

### 2.2 Hexagonal Core, Streaming Port, Tool Dialects & Loop Budgets (`packages/orcia-core/`)
- **`packages/orcia-core/src/orcia_core/ports/llm_streaming_port.py`**:
  - Add `supports_tools: bool = False` to `LlmEndpointConfig`, `tool_choice: str | dict[str, Any] | None = None` to `LlmStreamRequest`, and `finish_reason: str = "stop"` to `LlmChatTurnOutcome`.
  - Define typed stream events `ContentDelta`, `ReasoningDelta`, `ToolCallDelta`, `Usage`, `Finish` (`LlmTypedStreamEvent` union) alongside backward-compatible `LlmStreamDelta` (extended with `tool_call_index`, `tool_call_id`, `tool_name`, `arguments_delta`, `tool_calls`, `finish_reason`).
- **`packages/orcia-core/src/orcia_core/orchestration/llm_tool_dialects.py`** (new, `<= 280` L):
  - Native tool-call parsing & re-injection strictly for **2 dialects**:
    1. `openai_compatible`: parse streamed `delta.tool_calls` (`index`, `id`, `function.name`, `function.arguments` fragments) and non-streamed `message.tool_calls`; reassemble arguments deterministically by `(id, index)` and parse JSON safely; stop on `finish_reason="tool_calls"`; format `role: "tool"` (`tool_call_id`, `name`) and assistant `tool_calls`.
    2. `anthropic_messages`: parse streamed `content_block_start` (`tool_use`), `content_block_delta` (`input_json_delta`), `content_block_stop`, `message_delta` (`stop_reason="tool_use"`), and non-streamed `tool_use` blocks; format `role: "user"` `tool_result` blocks (`tool_use_id`, coalescing consecutive tool results) and assistant `tool_use` content blocks.
- **`llm_streaming_base_httpx.py` / `llm_streaming_httpx.py` / `llm_provider_parsing.py`**:
  - Strip `tools` and `tool_choice` whenever `not ep.supports_tools` (`D5`).
  - Preserve `tools` and `tool_choice` on OpenAI 404 fallback (`H-04`).
  - Implement `stream_chat_events()` emitting `ContentDelta | ReasoningDelta | ToolCallDelta | Usage | Finish` while preserving `stream_chat_sse()` and all 3 text/reasoning streaming adapters (`openai_compatible`, `anthropic`, `gemini_native` `CAP-076`).
- **AI Hub `supports_tools` Discovery, Persistence & Errors**:
  - `ai_models_capabilities.py` (new): deterministic `infer_default_supports_tools(...)` defaulting `gemini_native` and non-`/v1` native Ollama to `False` (`ACTION_ITEM-26.4`), and OpenAI-compatible (`/v1`) / Anthropic chat models to `True` (respecting explicit provider metadata).
  - `ai_models_records.py`, `sql_ai_model_queries.py`, `sql_ai_model_mutations.py`, `ai_models_governance.py` (+ `_ai_models_delete_helpers.py`), `llm_endpoint_resolver.py`: persist `supports_tools` and `supports_tools_override`, resolve effective `supports_tools`.
  - `ai_models_errors.py`: add `ModelToolsUnsupportedError` (`HTTP 422 ERR_MODEL_TOOLS_UNSUPPORTED`, localized `fr`/`en`).
- **Loop Budgets & Extended Cassettes**:
  - `packages/orcia-core/src/orcia_core/orchestration/assistant_loop_budgets.py` (new): `AssistantLoopBudgetPolicy`, `AssistantLoopBudgetController`, and `run_bounded_tool_loop` enforcing `max_iterations`, `max_total_tokens`, and `max_wall_clock_seconds` with forced no-tools synthesis or `TurnBudgetExceededError` (`ERR_ASSISTANT_TURN_BUDGET_EXCEEDED` in `assistant_turn_errors.py`).
  - `packages/orcia-core/src/orcia_core/testing/cassette_llm.py` + `_cassette_tool_cassettes.py`: streamed & non-streamed tool-calling cassettes for both OpenAI-compatible and Anthropic dialects.

### 2.3 Backend API, RFC 9457 Errors & OpenAPI SDK (`apps/api/`, `packages/api-client/`)
- **`apps/api/src/orcia_api/schemas/ai_models_hub.py`**: expose `supports_tools: bool` and `supports_tools_override: bool | None` on `AiModelMappingItemResponse`, `AiModelCreateRequest`, `AiModelPatchRequest`, `AiModelTestResponse`, and `DiscoveredModelItem`.
- **`apps/api/src/orcia_api/routers/ai_models_hub.py` & `_ai_models_helpers.py`**: propagate `supports_tools` and `supports_tools_override` on create/patch/test/discovery.
- **`apps/api/src/orcia_api/routers/assistant_llm_resolver.py`, `_assistant_turns_v2_routes.py`, `assistant_workspace.py`, `_assistant_turn_producer_helpers.py`**:
  - Reject Speed 2/3 pre-stream with `HTTP 422 ERR_MODEL_TOOLS_UNSUPPORTED` (RFC 9457 with `trace_id`) when resolved endpoint has `supports_tools=false`.
  - Map `OrciaDomainError` subclasses (including `TurnBudgetExceededError`) cleanly in `handle_turn_failure` to terminal `stream_error` with RFC 9457 payload and `error_code`.
- **`apps/api/src/orcia_api/errors/registry.py`**: register `ModelToolsUnsupportedError` and `TurnBudgetExceededError`.
- **`packages/api-client/`**: regenerate TypeScript OpenAPI 3.1 SDK (`scripts/export_openapi.py` + `pnpm --filter @orcia/api-client generate`) and verify `0-diff` gate.

### 2.4 SPA Interface (`apps/web/`)
- No new SPA view edits required in Story 26.6a (UI "Deepen" & Speed 2/3 gating land in Story 26.7); regenerated `@orcia/api-client` exposes `supports_tools` cleanly for `apps/web` TypeScript typechecking (`pnpm turbo run typecheck`).

### 2.5 Test Pyramid Impact Analysis (`AD-17`)
- **Layer 1a (Python Unit `tests/unit/`)**: `tests/unit/test_story_26_6a_tool_dialects_and_budgets.py` covering OpenAI-compatible & Anthropic streamed/non-streamed tool calls, 404 fallback `tools` preservation, Gemini/non-`/v1` Ollama `supports_tools=false`, `HTTP 422 ERR_MODEL_TOOLS_UNSUPPORTED`, loop budgets (`iterations`, `tokens`, `wall_clock`, forced synthesis, `TurnBudgetExceededError`), `DeterministicCassetteLlmStreamingAdapter` cassettes, `<= 300` L file caps, and `>= 90%` branch coverage.
- **Layer 2 (Vertical Integration `HTTP -> PG18` `tests/integration/`)**: `tests/integration/api/test_story_26_6a_supports_tools_postgres18.py` verifying Alembic `20261122_266a` (`upgrade -> downgrade -> upgrade`), `create_app()` PG18 persistence of `supports_tools` & `supports_tools_override`, `422 ERR_MODEL_TOOLS_UNSUPPORTED` on Speed 2/3, and `SELECT` verification in PG18.
- **Layer 3 (Contracts `0-diff` & `lint-imports`)**: `export_openapi.py --check`, `lint-imports` (`5/5`), `ruff`, `mypy --strict`.

---

## 3. Summary of Modifications & Results (Bilan des Modifications)

### 3.1 Delivered Files & Line-Count Compliance (`<= 300` Lines)
All modified and newly created non-generated backend/infrastructure source files stay strictly at or below `300` lines:

| Layer / Area | Created or Modified Files | Max Lines | Highlights |
| :--- | :--- | :--- | :--- |
| **Alembic Migration** | `infra/migrations/versions/20261122_266a_story_26_6a_llm_supports_tools.py` | `46` | Pure raw SQL (`up`: `supports_tools` `BOOLEAN NOT NULL DEFAULT FALSE`, `supports_tools_override` `BOOLEAN NULL`; `down`: reversible column drops), single linear head `20261122_266a (head)`. |
| **Ports & Kernel Boundary** | `packages/orcia-core/src/orcia_core/ports/{__init__.py,llm_streaming_port.py}` | `288` | Added `supports_tools`, `tool_choice`, `finish_reason`, and typed stream events (`ContentDelta \| ReasoningDelta \| ToolCallDelta \| Usage \| Finish`) alongside backward-compatible `LlmStreamDelta`. |
| **Tool Dialects & Streaming Adapters** | `llm_tool_dialects.py`, `llm_streaming_base_httpx.py`, `_llm_streaming_http_helpers.py`, `llm_provider_parsing.py`, `llm_gemini_dialect.py`, `llm_streaming_httpx.py`, `llm_streaming_sse_utils.py` | `290` | Native streamed/non-streamed `tool_calls` parsing & re-injection strictly on `openai_compatible` and `anthropic_messages`, HTTP 404 fallback `tools` preservation (`H-04`), stripping `tools` when `supports_tools=false`, and preservation of all 3 text/reasoning streaming adapters (`CAP-076`). |
| **AI Hub `supports_tools` & Concurrency** | `ai_models_capabilities.py`, `ai_models_discovery_dialects.py`, `_ai_models_discovery_common.py`, `ai_models_connection.py`, `ai_models_connection_helpers.py`, `ai_models_records.py`, `ai_models_governance.py`, `_ai_models_governance_helpers.py`, `_ai_models_delete_helpers.py`, `sql_ai_model_queries.py`, `sql_ai_model_mutations.py`, `_sql_ai_model_helpers.py`, `llm_endpoint_resolver.py`, `ai_models_errors.py`, `sql_permission_broker.py`, `_sql_permission_broker_queries.py` | `299` | 0-token `supports_tools` capability inference (`gemini_native` & non-`/v1` Ollama default `False`), PG18 persistence & `PLATFORM_ADMIN` override (`COALESCE`), `HTTP 422 ERR_MODEL_TOOLS_UNSUPPORTED`, `ai_models_governance.py` split (`<= 299` L), and `ON CONFLICT DO NOTHING` + per-loop `asyncio.Lock` eliminating concurrent `permission_broker_policies_pkey` races. |
| **Loop Budgets & Cassettes** | `assistant_loop_budgets.py`, `assistant_turn_errors.py`, `testing/cassette_llm.py`, `testing/_cassette_tool_cassettes.py` | `287` | Deterministic multi-step tool loop budget controller (`max_iterations`, `max_total_tokens`, `max_wall_clock_seconds`, forced no-tools synthesis, `TurnBudgetExceededError`) and OpenAI/Anthropic tool cassettes (`0 $`). |
| **FastAPI, Errors & OpenAPI SDK** | `schemas/ai_models_hub.py`, `errors/registry.py`, `dependencies/_rag_availability_guards.py`, `routers/{ai_models_hub.py,_ai_models_helpers.py,_ai_models_test_and_reindex_routes.py,assistant_llm_bridge.py,assistant_llm_resolver.py,_assistant_llm_stream_bridge.py,_assistant_turn_producer.py,_assistant_turn_producer_helpers.py,_assistant_turns_v2_routes.py,assistant_workspace.py}`, `packages/api-client/{openapi.json,src/generated/schema.ts}` | `300` | Pre-stream `422 ERR_MODEL_TOOLS_UNSUPPORTED` on Speed 2/3, RFC 9457 domain error mapping, `supports_tools` / `supports_tools_override` Hub endpoints, and `0-diff` OpenAPI 3.1 SDK regeneration. |
| **Automated Tests** | `tests/unit/test_story_26_6a_{tool_dialects_and_budgets,edge_cases_and_cassettes,queries_and_broker_concurrency}.py`, `tests/integration/api/test_story_26_6a_supports_tools_postgres18.py`, `tests/unit/test_epic_10_story_10_2_three_speed_router.py` | — | Dedicated unit, concurrency, edge-case, and `create_app()` PG18 integration coverage. |

### 3.2 Metrics & Branch Coverage (`>= 90%`)
- **28-Module Story `26.6a` Branch Coverage**: **`94%`** (`1913` statements, `76` missed, `584` branches, `57` partial branches; `.venv/bin/coverage report --fail-under=90` **PASSED**).
- Key module coverage highlights: `ai_models_errors.py` (`100%`), `assistant_turn_errors.py` (`100%`), `_sql_ai_model_helpers.py` (`100%`), `_ai_models_delete_helpers.py` (`100%`), `cassette_llm.py` (`100%`), `sql_ai_model_queries.py` (`99%`), `assistant_loop_budgets.py` (`99%`), `ai_models_connection_helpers.py` (`99%`), `llm_gemini_dialect.py` (`98%`), `llm_endpoint_resolver.py` (`98%`), `llm_provider_parsing.py` (`97%`), `llm_streaming_port.py` (`96%`), `llm_tool_dialects.py` (`93%`).

### 3.3 Five-Layer Test Pyramid (`AD-17`) & Verification Gates
All checks were independently executed post-final-edit by the Final Verification Testing Sub-Agent with zero source modifications:

| Verification Gate | Command / Scope | Result |
| :--- | :--- | :--- |
| **Static, Typing, Boundaries & Secrets** | `ruff check .`, `ruff format --check .`, `mypy --strict packages/orcia-core apps/api apps/worker`, `lint-imports`, `lint_spine.py`, `scripts/export_openapi.py --check`, `detect-secrets-hook` | **PASSED** (`0` ruff issues across `1502` formatted files; `0` mypy errors across `652` files; `5/5` `lint-imports` contracts kept across `736` files; `0` spine findings; `0-diff` OpenAPI; `0` secret findings). |
| **Alembic Schema Head** | `.venv/bin/alembic -c infra/migrations/alembic.ini heads` | **PASSED** (`20261122_266a (head)` single linear head). |
| **Layer 1 & Security/Eval/Contract Suites** | `tests/unit` (`1024` collected; `test_story_7_0c` run standalone `--no-cov` due to OTel provider shutdown isolation from `7_0b`; 6 testcontainer unit specs run `--no-cov`), `tests/evals` (`23`), `tests/security` (`125`), `tests/contract` (`2`) | **PASSED** (`1174` tests across Python suites, `0` failures). |
| **Layer 2 PG18 + Redis Integration (`--no-cov`)** | `test_story_26_6a_supports_tools_postgres18.py`, `test_story_17_5_ai_models_hub_postgres18.py`, `test_story_26_5_*.py`, `test_story_26_4a_*.py`, `test_story_26_4b_*.py`, `test_story_26_3_*.py`, `test_story_26_1_*.py`, `test_story_25_5_*.py` | **PASSED** (`6 + 8 = 14` integration tests on ephemeral PG18 + Redis `testcontainers`, `0` failures). |
| **TypeScript / SPA Suites** | `pnpm turbo run lint typecheck test` | **PASSED** (`9/9` tasks across `@orcia/api-client`, `@orcia/ui`, `@orcia/web`). |
| **Layer 5 Playwright Desktop E2E** | `playwright test --project=desktop-cockpit` (`00`, `02`, `12-finops`, `12-epic16`, `16`, `21`, `ORCIA_E2E_SEED_FIXTURES` unset) | **PASSED** (`15 passed, 1 skipped, 0 failed`; `git diff docs/implementation-artifacts/e2e-campaign-epic-*` empty). |
| **Docs & Site Sync** | `pnpm site:sync && pnpm site:check`, `.venv/bin/python scripts/check_implementation_docs.py`, `npx gitnexus analyze --index-only .` | **PASSED**. |
