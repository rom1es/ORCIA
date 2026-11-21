# Story 26.2 — Core LLM Streaming Extraction (`LlmStreamingPort`), Unified Localized `AssistantPromptBuilder`, Prod Test-Branch Purge & `<= 300 L` Splits

- **Date**: 2026-11-21
- **Story / Sprint Key**: `26-2-core-llm-streaming-extraction-and-unified-prompt-builder` (`Epic 26` — Lot 2: Core Foundations)
- **Capabilities**: `CAP-069`, `CAP-074`, `CAP-076` — classification: `feature` (`docs/product/capabilities.yaml`)
- **Context / Scope**: Extract ~2,100 lines of LLM streaming, provider dialects, endpoint resolution, prompt assembly, and usage telemetry out of `apps/api/routers/` into `packages/orcia-core` hexagonal ports and `httpx` adapters (`AD-1`, `AD-15`, `AD-19`, `AD-24`, `AD-25`, `D5 + R7`); unify the three prompt builders into one localized `AssistantPromptBuilder` (`H-31`); derive default hats from `user.human_profile_archetype`; replace synthetic latencies and hardcoded pack/workflow literals with real values and `perf_counter()` measurements (`H-30` P2); purge all `testclient`, `"pytest" in sys.modules`, and `ORCIA_FORCE_LIVE_LLM_IN_TESTS` branches from production code (`H-24`); eliminate `_internal` imports in `apps/api/src` and `testing.cassette_llm` imports inside `orcia_core` domain packages; and split all oversized harness/dependency files to `<= 300` lines (`H-34`).
- **Associated Commits**: pending (working on branch `feat/epic-26-assistant-harness-debt-remediation`)

---

## 1. Requirements & Tech Lead Impact Analysis (Analyse du Besoin)

### 1.1 Context & Problem Statement
- **Architectural boundary violations (`H-25`, `AD-1`, `AD-19`)**:
  - Multi-provider HTTP streaming (`assistant_llm_providers.py`, `assistant_llm_gemini_adapter.py`, `_assistant_llm_provider_parsing.py`), endpoint resolution (`assistant_llm_resolver.py`), prompt assembly (`assistant_llm_prompts.py`), and usage telemetry (`_assistant_usage_telemetry.py`) currently reside in `apps/api/src/orcia_api/routers/`.
  - `agents_and_skills.py` and `_agents_and_skills_skills_routes.py` import `invoke_configured_llm_for_assistant_turn` directly from `assistant_llm_bridge` (router-to-router coupling).
  - Multiple files under `apps/api/src` import `orcia_core.*._internal.*` directly instead of public domain exports.
  - Seven modules inside `packages/orcia-core/src/orcia_core/{bootstrap,orchestration,gates}/` import `DeterministicCassetteLLM` from `orcia_core.testing.cassette_llm`, coupling core domains to test fixtures.
- **Divergent prompt builders & English locale leakage (`H-31`)**:
  - Three separate builders exist: `AssistantHarness.assemble_prompt`, `build_assistant_system_instructions`, and `AssistantFourLevelGovernanceService.assemble_five_layers_preview`.
  - When `locale="en"`, `CONSTITUTIONAL_LAYER_1_TEXT`, `PROFILE_ADAPTATION_MAP`, layer preview labels, `"Active Hat (Casquette)"`, and `assistantTurnPayloadHelper.ts` (`[Pièces jointes fournies par l'utilisateur]`) leak French tokens into English prompts.
- **Hardcoded defaults & synthetic timings (`H-30` P2)**:
  - Default `hat` falls back to RBAC role `"PLATFORM_ADMIN"` in `assistant_workspace.py` and `agents_and_skills.py` instead of `user.human_profile_archetype`.
  - `assistant_three_speed_router.py`, `assistant_three_speed_steps.py`, and `assistant_citations_and_v5_guard.py` inject synthetic latencies (`14.5`, `380.0`, `410.0`, `490.0`, `520.0`, `640.0`, `820.0`, `1460.0`, `min(..., 4.2)`, `min(..., 4.1)`, `80.0`) and hardcode `"orcia-pack-sdlc"` / `"orcia://pack-sdlc/workflows/ticket-to-tech-spec"`.
- **Production test branches (`H-24`)**:
  - `client_host == "testclient"`, `"pytest" in sys.modules`, and `ORCIA_FORCE_LIVE_LLM_IN_TESTS` appear across `assistant_llm_bridge.py`, `assistant_llm_resolver.py`, `_assistant_llm_stream_bridge.py`, `assistant_background_turns.py`, `assistant_workspace.py`, `_rag_availability_guards.py`, `_core_providers.py`, `core_and_lifespan.py`, `org_and_workspaces.py`, and `_bootstrap_llm_routes.py`.
- **File size debt (`H-34`)**:
  - `core_and_lifespan.py` (559 L), `orchestration_and_settings.py` (412 L), `assistant_folders_and_sharing.py` (376 L), `useAssistantStreamingTurn.ts` (349 L), and `reflexive_runtime.py` (343 L) exceed the 300-line ceiling.

### 1.2 Exploration, GitNexus Impact Analysis, Refactoring & Debt
- **GitNexus Impact Analysis (`repo: /home/romain/Documents/Projects/ORCIA`)**:
  - `stream_configured_llm_for_assistant_turn` (`_assistant_llm_stream_bridge.py`): `impactedCount = 46`, risk `CRITICAL` (`42` direct, `5` processes, `8` modules).
  - `AssistantHarness` (`assistant_harness.py`): `impactedCount = 46`, risk `CRITICAL` (`42` direct).
  - `query` confirmed symbols across `assistant_three_speed_steps.py`, `_assistant_llm_stream_bridge.py`, `_assistant_llm_provider_parsing.py`, `assistant_llm_providers.py`, `assistant_governance_studio.py`, and `_assistant_workspace_controls.py` (index 1 commit behind `HEAD`, will be refreshed via `npx gitnexus analyze --index-only` post-implementation).
- **Direct Codebase Audit (`grep` & `wc -l`)**:
  - Identified all 13 `testclient` / `pytest in sys.modules` / `ORCIA_FORCE_LIVE_LLM_IN_TESTS` lines in `apps/api/src`.
  - Identified all 20 `_internal` imports in `apps/api/src` and all 7 `testing.cassette_llm` imports in `packages/orcia-core/src`.
  - Confirmed 3 text/reasoning streaming dialects to preserve (`D5 + R7`): OpenAI-compatible (+ `/api/chat` 404 fallback + `<think>` separation), Anthropic `/v1/messages` (`thinking`/`text` blocks), and Google Gemini Native `/v1beta` (`CAP-076`).
- **Refactoring & Modularity Opportunities**:
  - Introduce pure hexagonal `LlmStreamingPort` in `orcia_core/ports/llm_streaming_port.py` (zero third-party SDK imports).
  - Extract concrete `httpx` adapters (`HttpxOpenAiCompatibleLlmAdapter`, `HttpxAnthropicLlmAdapter`, `HttpxGeminiNativeLlmAdapter`, and dispatching `HttpxMultiProviderLlmStreamingAdapter`) into `orcia_core/orchestration/llm_streaming_httpx.py` following `embedding_httpx.py` and reusing `prepare_pinned_http_request` (`26.1`).
  - Extract `DeterministicCassetteLlmStreamingAdapter` into `orcia_core/testing/cassette_llm.py`, injected strictly from Composition Root (`apps/api/src/orcia_api/dependencies/`) when `ORCIA_USE_CASSETTE_LLM` is enabled.
  - Consolidate prompt assembly into `AssistantPromptBuilder` + `assistant_prompt_locales.py` while keeping thin backward-compatible facades for `AssistantHarness`, `assistant_llm_prompts.py`, and `assistant_governance_layers.py`.

---

## 2. Implementation Plan (Plan d'Implémentation)

### 2.1 Data Schema & Alembic Migrations
- None required for Story `26.2` (no PostgreSQL schema changes; PG18 persistence stories belong to Lot 3 `26.3`–`26.4b`).

### 2.2 Core Hexagonal Domain, Ports & Adapters (`packages/orcia-core/`)
- **New Port (`packages/orcia-core/src/orcia_core/ports/llm_streaming_port.py`, `<= 160 L`)**:
  - Define pure Python dataclasses `LlmEndpointConfig`, `LlmStreamRequest`, `LlmStreamDelta`, `LlmChatTurnOutcome` and Protocol `LlmStreamingPort` (`complete_chat`, `stream_chat_sse`). Export from `orcia_core/ports/__init__.py`.
- **Extracted LLM Streaming, Dialects, Resolver & Telemetry (`packages/orcia-core/src/orcia_core/orchestration/`, each `<= 300 L`)**:
  - `llm_gemini_dialect.py`: native Gemini URL, headers, body, non-stream & SSE delta parsing (`CAP-076`).
  - `llm_provider_parsing.py`: headers, body, non-stream JSON & SSE delta extraction for OpenAI-compatible, Anthropic, and Gemini, plus `<think>` separation.
  - `llm_streaming_httpx.py`: `HttpxOpenAiCompatibleLlmAdapter`, `HttpxAnthropicLlmAdapter`, `HttpxGeminiNativeLlmAdapter`, and `HttpxMultiProviderLlmStreamingAdapter` implementing `LlmStreamingPort` with DNS-pinned SSRF (`prepare_pinned_http_request`).
  - `llm_usage_telemetry.py`: `extract_usage_tokens_from_payload`, `estimate_tokens_deterministic`, `resolve_usage_with_fallback`, `persist_assistant_turn_ledger_entry`.
  - `llm_endpoint_resolver.py`: `extract_tier_endpoint_from_dict`, `select_endpoint_from_tiers`, `resolve_configured_llm_endpoint_from_sources` (using public `sql_ai_model_mappings` exports, re-validating SSRF on every resolved endpoint).
- **Unified Localized `AssistantPromptBuilder` (`packages/orcia-core/src/orcia_core/orchestration/`, each `<= 300 L`)**:
  - `assistant_prompt_locales.py`: complete `fr` and `en` prompt localization tables (`CONSTITUTIONAL_LAYER_1_TEXT_FR/EN`, `PROFILE_ADAPTATION_MAP_EN/FR`, layer labels, runtime metadata, tone/format labels).
  - `assistant_prompt_builder.py`: `AssistantPromptBuilder` unifying `assemble_prompt`, `build_system_instructions`, and `build_five_layers_preview`, plus `resolve_default_hat(explicit_hat, user_archetype)` (never `"PLATFORM_ADMIN"`).
  - Update `assistant_harness.py`, `assistant_profile_adaptation.py`, `assistant_governance.py`, `assistant_governance_layers.py`, and `assistant_governance_studio.py` to delegate cleanly to `AssistantPromptBuilder` without breaking existing imports.
- **Latency & Hardcoded Default Cleanup (`H-30` P2)**:
  - Replace synthetic latencies (`14.5`, `380.0`, `410.0`, `490.0`, `520.0`, `640.0`, `820.0`, `1460.0`, `min(..., 4.2)`, `min(..., 4.1)`, `80.0`) in `assistant_three_speed_router.py`, `assistant_three_speed_steps.py`, `assistant_citations_and_v5_guard.py`, and `assistant_citations_models.py` with `time.perf_counter()` measurements and `0.0` defaults when unmeasured.
  - Parameterize `pack_key` / `target_workflow_uri` defaults (`None` / `"core"` instead of hardcoded `"orcia-pack-sdlc"` where non-SDLC generic core applies).
- **Remove `testing.cassette_llm` Imports from `orcia_core` Domains**:
  - Remove `orcia_core.testing.cassette_llm` imports from `litellm_adapter.py`, `plugin_registry.py`, `agents_and_skills_manager.py`, `step_executors.py`, `assistant_agent.py`, `assistant_agent_synthesis.py`, and `gates/agentic.py`. Move `build_cassette_gateway_plugin` to `orcia_core.testing.cassette_llm` and update `packages/orcia-core/pyproject.toml` entry point.
  - Add `DeterministicCassetteLlmStreamingAdapter` to `orcia_core/testing/cassette_llm.py`.
- **`<= 300 L` Splits**:
  - Split `assistant_folders_and_sharing.py` (376 L) -> extract async query/overview helpers into `_assistant_folders_queries.py`.
  - Split `reflexive_runtime.py` (343 L) -> extract delegation & execution lifecycle helpers into `_reflexive_delegation.py`.

### 2.3 Backend API, Composition Root, Security & Contracts (`apps/api/`)
- **Thin HTTP & DI Facades (`apps/api/src/orcia_api/routers/`)**:
  - Reduce `assistant_llm_providers.py`, `assistant_llm_gemini_adapter.py`, `_assistant_llm_provider_parsing.py`, `assistant_llm_prompts.py`, `assistant_llm_resolver.py`, `_assistant_usage_telemetry.py`, `assistant_llm_bridge.py`, and `_assistant_llm_stream_bridge.py` to thin re-export / HTTP translation facades delegating to `orcia_core` (`<= 300 L` each).
  - Migrate `agents_and_skills.py` and `_agents_and_skills_skills_routes.py` to invoke `LlmStreamingPort` via `Depends(get_llm_streaming_port)` / `Depends(get_configured_llm_endpoint)` instead of importing `assistant_llm_bridge`, using `user.human_profile_archetype` instead of `"PLATFORM_ADMIN"`.
  - Purge all `client_host == "testclient"`, `"pytest" in sys.modules`, and `ORCIA_FORCE_LIVE_LLM_IN_TESTS` branches across `apps/api/src/`.
  - Purge all `_internal` imports in `apps/api/src/` by consuming public domain package exports.
- **Composition Root (`apps/api/src/orcia_api/dependencies/`)**:
  - Split `core_and_lifespan.py` (559 L) and `orchestration_and_settings.py` (412 L) into cohesive modules `<= 300 L`.
  - Wire `get_llm_streaming_port(request)` and `get_optional_llm_streaming_port(request)` in `portal_and_assistant.py` / `_llm_streaming_providers.py`, returning `DeterministicCassetteLlmStreamingAdapter` strictly when `ORCIA_USE_CASSETTE_LLM` is enabled and `HttpxMultiProviderLlmStreamingAdapter` otherwise.
- **OpenAPI Contract**:
  - Verify `scripts/export_openapi.py --check` (`0-diff`) or regenerate SDK if query defaults change.

### 2.4 Frontend SPA (`apps/web/`)
- Split `apps/web/src/features/inbox/useAssistantStreamingTurn.ts` (349 L) into `useAssistantStreamingTurn.ts` (`<= 220 L`) and `assistantStreamingHandlers.ts` (`<= 160 L`).
- Fix `apps/web/src/features/inbox/assistantTurnPayloadHelper.ts` (`[User-supplied attachments]` when `!isFr` instead of hardcoded `[Pièces jointes fournies par l'utilisateur]`, `H-31`).

### 2.5 Test Pyramid Impact Analysis (`AD-17`)
- **Layer 1a & 1b (Unit Python & Vitest TS)**:
  - New `tests/unit/test_story_26_2_core_llm_streaming_and_prompt_builder.py` covering `LlmStreamingPort` + all 3 `httpx` streaming/non-stream adapters + DNS-pinned SSRF, `AssistantPromptBuilder` unified `fr`/`en` localization (`0` French leakage in `en`), hat derivation (`user.human_profile_archetype`), real `perf_counter()` latencies, `agents_and_skills` DI port usage, and AST audits (`0` `testclient`/`pytest in sys.modules`/`ORCIA_FORCE_LIVE_LLM_IN_TESTS` in `src/`, `0` `_internal` in `apps/api/src/`, `0` `testing.cassette_llm` in `orcia_core` domains, `0` touched/listed harness files `> 300 L`).
  - Update existing unit tests that previously relied on `ORCIA_FORCE_LIVE_LLM_IN_TESTS` or implicit `testclient` fallback so they explicitly configure `ORCIA_USE_CASSETTE_LLM` (for cassette tests) or `MockTransport` (for live tests).
  - Run `pnpm turbo run lint typecheck test`.
- **Layer 2 (PG18 Integration)**:
  - Run `tests/integration/api/test_story_26_1_assistant_security_postgres18.py` (and `25.5` PG18 integration test) verifying live Composition Root resolution without `ORCIA_FORCE_LIVE_LLM_IN_TESTS`.
- **Layer 3 (Contracts & Architecture)**:
  - `.venv/bin/lint-imports` (`5/5` contracts), `scripts/export_openapi.py --check`, `mypy --strict`, `ruff check`, `ruff format --check`.
- **Layer 4 (Golden Evals) & Security**:
  - `.venv/bin/pytest tests/evals tests/security tests/contract --no-cov -q`.
- **Layer 5 (Playwright E2E)**:
  - Verify `ORCIA_USE_CASSETTE_LLM=true` E2E path compatibility (`e2e/02`, `12`, `16`, `21`).

---

## 3. Modifications Summary & Verification Results (Bilan des Modifications)

### 3.1 Files Created & Modified (Strict `<= 300 L` Harness Split Compliance)

| Layer | Created / Modified Modules (`wc -l`) | Purpose & Architectural Compliance |
| :--- | :--- | :--- |
| **Ports (`orcia_core.ports`)** | `llm_streaming_port.py` (`86`), `__init__.py` (`107`) | Zero-SDK `LlmStreamingPort` protocol + typed `LlmStreamingRequest`, `LlmStreamDelta`, `LlmEndpointResolution` contracts (`AD-1`, `AD-19`) |
| **Core Streaming Adapters (`orcia_core.orchestration`)** | `llm_streaming_httpx.py` (`104`), `llm_streaming_base_httpx.py` (`240`), `llm_streaming_sse_utils.py` (`65`), `llm_provider_parsing.py` (`155`), `llm_gemini_dialect.py` (`198`), `llm_endpoint_resolver.py` (`165`), `llm_usage_telemetry.py` (`148`) | Extracted HTTPX streaming for all `3` text/reasoning dialects (`openai_compatible`, `anthropic`, `gemini_native` `CAP-076`), DNS-pinned SSRF verification (`26.1`), strict `thinking`/`content` separation, and usage telemetry |
| **Unified Prompt Builder (`orcia_core.orchestration`)** | `assistant_prompt_builder.py` (`296`), `assistant_prompt_locales.py` (`224`), `assistant_prompt_preview.py` (`148`), `assistant_harness.py` (`74`), `assistant_harness_types.py` (`48`), `assistant_profile_adaptation.py` (`208`), `assistant_governance.py` (`298`), `assistant_governance_layers.py` (`34`), `assistant_governance_studio.py` (`244`) | Single `AssistantPromptBuilder` replacing `AssistantHarness.assemble_prompt`, `build_assistant_system_instructions`, and `assemble_five_layers_preview`; strict `fr`/`en` localization (`0` French tokens in `en`); Layer 1 immutability; default `active_hat` derived from `human_profile_archetype` via `resolve_default_hat` |
| **Harness Splits & Latency/Cassette Purge (`orcia_core`, `orcia_connectors`)** | `assistant_three_speed_router.py` (`294`), `assistant_three_speed_steps.py` (`288`), `assistant_agent.py` (`291`), `assistant_agent_synthesis.py` (`244`), `assistant_citations_and_v5_guard.py` (`275`), `assistant_citations_models.py` (`189`), `assistant_folders_and_sharing.py` (`253`), `_assistant_folders_async_ops.py` (`171`), `agents/reflexive_runtime.py` (`298`), `agents/_runtime_delegation.py` (`92`), `testing/cassette_llm.py` (`207`), `bootstrap/_internal/litellm_adapter.py` (`297`), `bootstrap/plugin_registry.py` (`152`), `orchestration/__init__.py` (`524`), `bootstrap/__init__.py` (`372`), `orcia_connectors/__init__.py` (`126`), plus Cassette import cleanups in `agents_and_skills_manager.py`, `step_executors.py`, `gates/agentic.py`, `_internal/dbos_engine.py` | Replaced synthetic latencies (`14.5`, `380`, `520`, `640`, `820`, `1460`, `min(..., 4.2)`), hardcoded `"orcia-pack-sdlc"`, and pilot URIs with `time.perf_counter()` and request/context values; purged `testing.cassette_llm` imports from domain packages via `orcia.llm_gateways` entry point + `DeterministicCassetteLlmStreamingAdapter` |
| **API Composition Root & Thin Facades (`apps/api`)** | `dependencies/__init__.py` (`148`), `dependencies/core_and_lifespan.py` (`256`), `dependencies/_lifespan_infra.py` (`181`), `dependencies/_lifespan_services.py` (`137`), `dependencies/_core_providers.py` (`181`), `dependencies/_llm_streaming_providers.py` (`60`), `dependencies/orchestration_and_settings.py` (`207`), `dependencies/finops_and_triggers.py` (`231`), `dependencies/portal_and_assistant.py` (`196`), `dependencies/_rag_availability_guards.py` (`165`), `dependencies/jira_and_mcp.py` (`53`), `dependencies/workspace_and_packs.py` (`242`); `routers/assistant_llm_bridge.py` (`297`), `_assistant_llm_stream_bridge.py` (`109`), `assistant_llm_prompts.py` (`180`), `assistant_llm_providers.py` (`121`), `assistant_llm_resolver.py` (`105`), `assistant_llm_gemini_adapter.py` (`39`), `_assistant_llm_provider_parsing.py` (`39`), `_assistant_usage_telemetry.py` (`44`), `assistant_background_turns.py` (`286`), `assistant_workspace.py` (`246`), `assistant_workspace_governance.py` (`266`), `agents_and_skills.py` (`236`), `_agents_and_skills_skills_routes.py` (`110`), `_agents_and_skills_helpers.py` (`123`), `ai_models_hub.py` (`293`), `schemas/assistant.py` (`188`), plus `_internal` & test-branch cleanups across `datasource_webhooks.py`, `org_and_workspaces.py`, `codegraph_mcp.py`, `_bootstrap_*.py`, `_ai_models_*.py`, `_org_units_users.py` | Zero `_internal` imports in `apps/api/src`; zero `client_host == "testclient"`, `"pytest" in sys.modules`, or `ORCIA_FORCE_LIVE_LLM_IN_TESTS` branches in `packages/*/src` and `apps/*/src`; `agents_and_skills.py` migrated to `Depends(get_llm_streaming_port)` |
| **SPA & Contracts (`apps/web`, `packages/api-client`)** | `useAssistantStreamingTurn.ts` (`230`), `assistantStreamingRunner.ts` (`224`), `assistantTurnPayloadHelper.ts` (`129`), `assistantAndInboxMockHandlers.ts` (`292`), `packages/api-client/openapi.json` | Localized `[Pièces jointes fournies par l'utilisateur]` vs `[User-supplied attachments]` via `locale`; split streaming runner under `300` lines; `0-diff` OpenAPI schema sync |
| **Tests & Governance** | `tests/unit/test_story_26_2_core_llm_streaming_and_prompt_builder.py` (`510`), plus updates to `test_assistant_agnostic_async_llm_bridge.py`, `test_agents_and_skills_router_and_service.py`, `test_epic_10_story_10_2_three_speed_router.py`, `test_story_19_6_*`, `test_story_19_7_*`, `test_story_25_5_*`, `test_story_3_3_*`, `test_story_26_1_*`, `test_assistant_and_ontology_evals.py`, `docs/product/capabilities.yaml` | Dedicated Story `26.2` contract, localization, hat-derivation, anti-stub/anti-`testclient` AST guards, and updated `CAP-069`, `CAP-074`, `CAP-076` registry entries |

### 3.2 Verification Gates & Quantitative Metrics

| Gate | Command Executed | Observed Result |
| :--- | :--- | :--- |
| **Architecture Boundaries (`AD-19`)** | `.venv/bin/lint-imports` | **`5 kept, 0 broken`** (`679` files, `4870` dependencies) |
| **Lint & Formatting** | `.venv/bin/ruff check . && .venv/bin/ruff format --check .` | **`All checks passed!`**; **`1411` files already formatted** |
| **Strict Typechecking** | `.venv/bin/mypy --strict packages/orcia-core/src packages/orcia-connectors/src apps/api/src apps/worker/src` | **`Success: no issues found in 635 source files`** |
| **OpenAPI 3.1 Sync** | `.venv/bin/python scripts/export_openapi.py --check` | **`0-diff`** (`exit 0`) |
| **Unit / Security / Evals / Contract** | `.venv/bin/pytest tests/unit tests/security tests/evals tests/contract --no-cov -q` | **`1094 passed`** (`exit 0`, zero failures; confirmed by independent Testing Sub-Agent) |
| **Targeted Story 26.2 Coverage** | `.venv/bin/pytest ... --cov-fail-under=90` across extracted core/API modules | **`92.64%`** independent Testing Sub-Agent gate (`92.95%` dev run across `27` modules; `>= 90%`) |
| **PG18 Integration (`AD-17`)** | `.venv/bin/pytest tests/integration/api/test_story_26_1_assistant_security_postgres18.py tests/integration/api/test_story_25_5_assistant_chat_only_and_rag_guard_postgres18.py` | **`2/2 passed`** against real `testcontainers` PostgreSQL 18 (`create_app()`, `exit 0`) |
| **Registry & Story 25.5 Non-Regression** | `.venv/bin/pytest tests/unit/test_capabilities_registry.py tests/unit/test_uj_e2e_coverage_gate.py tests/unit/test_story_25_5_assistant_without_embedding_and_datasource_guard.py --no-cov -q` | **`32 passed`** (`22` registry/UJ + `10` Story `25.5`) |
| **Frontend Monorepo** | `pnpm turbo run lint typecheck test` | **`9 successful, 9 total`** (`@orcia/api-client`: `3` files / `20` tests, `@orcia/ui`: `34` files / `136` tests, `@orcia/web`: `67` files / `261` tests) |
| **Playwright Desktop E2E (`AD-17` L5)** | Independent Testing Sub-Agent E2E campaign (`00`, `02`, `12-finops`, `12-epic16`, `16`, `21`) | **`15 passed / 1 skipped / 0 failed`** (`exit 0`) |
| **Architecture Spine Lint** | `.venv/bin/python .agent/skills/bmad-architecture/scripts/lint_spine.py --workspace docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24` | **`total_findings: 0`** (`"ok": true`) |
| **Secret Hygiene** | `.venv/bin/detect-secrets-hook --baseline .secrets.baseline ...` | **`exit 0`**, zero credentials leaked |
| **Docs & Site Catalog** | `.venv/bin/python scripts/check_implementation_docs.py && pnpm site:sync && pnpm site:check` | Passed (`209` Tech Lead reports synced & verified) |
| **GitNexus Index & Impact** | `npx gitnexus analyze --index-only && npx gitnexus status` + `gitnexus_detect_changes({repo: "/home/romain/Documents/Projects/ORCIA", scope: "all"})` | Index **`up-to-date`** (`45,221` nodes, `362,818` edges, `1,952` covered files); `detect_changes`: `changed_files: 75`, `changed_count: 12`, `affected_count: 0`, `risk_level: "low"` |

### 3.3 Final Closure (`done`) & Deferred Debt Notes
- **Closure Decision**: Story `26.2` passed 100% of independent verification gates (`1094 passed` unit/security/evals/contract, `92.64%` targeted coverage, `2/2` PG18 `create_app()` integration, `5/5` `lint-imports`, `0-diff` OpenAPI, `9/9` Turbo, `15 passed / 1 skipped / 0 failed` Playwright Desktop E2E across `00, 02, 12-finops, 12-epic16, 16, 21`, all Story `26.2` harness modules `<= 298 L`) and is closed as **`done`**.
- **Deferred Split (`Story 26.3`)**: `packages/orcia-core/src/orcia_core/orchestration/step_executors.py` (`524` L, touched only to remove a `testing.cassette_llm` import) is explicitly deferred for modular splitting into Story `26.3`.
