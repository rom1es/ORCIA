# Story 30.3 — `Mes Processus` Real PG18 Pending Validations, Live Workspace LLM Execution & Coalesced Reasoning Trace

- **Date**: 2026-11-25
- **Story / Sprint Key**: `30-3-processes-real-pg18-pending-runs-live-llm-and-coalesced-trace` (`Epic 30`, Lot 2)
- **Capability(ies)**: `CAP-020`, `CAP-021`, `CAP-140`, `CAP-160` — classification: `feature` + `ux`
- **Author / Context**: `bmad-dev-worker` (Tech Lead implementation of `UX30-06`, `UX30-07`, `UX30-08` from `sprint-change-proposal-2026-11-25-epic-30-assistant-processes-and-agents-ux-hardening.md`)
- **Associated Commits**: Pending closure commit

---

## 1. Needs Analysis & Tech Lead Impact Study (Pre-Implementation)

### 1.1 Context & Problem Statement
- **UX30-06 (Hardcoded Pending Validation & Sticky Auto-Launch)**: `ProcessesActiveDossiersCard.tsx` unconditionally renders `"1 validation en attente de votre décision"` (`pendingValidationBadge`) without querying PostgreSQL 18 and promotes `workflows[0]` (`wf-generate-orcia-documentation`, sorted first via `packs/orcia-docs`). `ProcessesHubPage.tsx` persists `activeRunWorkflowId` in `localStorage["orcia.processes.active_run_workflow_id.v1"]`, auto-launching a run on mount, while `useInteractiveProcessRunController.ts` locks `status` to `"WAITING_SUBSTEP_HITL"` regardless of the backend `WorkflowV2RunResponse` status, and `workflows.py` stores v2 runs only in RAM (`app.state.workflow_v2_runs_store`).
- **UX30-07 (Production Cassette & `capabilities.yaml` Fallback)**: `apps/api/src/orcia_api/dependencies/core_and_lifespan.py` wires `LiteLLMAdapter(fallback_cassette=DeterministicCassetteLLM())` as the default `app.state.llm_gateway`, causing silent cassette execution even when `ORCIA_USE_CASSETTE_LLM` is unset. `GatewayReflexiveLlmAdapter` (`packages/orcia-core/src/orcia_core/agents/llm_adapter.py`) falls back to `_build_deterministic_cassette_decision` with `_DEFAULT_FALLBACK_RESOURCE = "docs/product/capabilities.yaml"`, and `apps/web/src/features/processes/execution/interactiveRunGoalPayload.ts` / `interactiveRunFormatters.ts` hardcode `docs/product/capabilities.yaml` in `initial_resources`.
- **UX30-08 (Fragmented `THOUGHT_DELTA` Trace Rendering)**: `GatewayReflexiveLlmAdapter.stream_turn_deltas` slices `thought_text` into 64-char chunks and `_runtime_turn_actions.py` emits a separate `THOUGHT_DELTA` event per slice. `AgentExecutionTrace.tsx` and `AgentExecutionTraceItems.tsx` render every `THOUGHT_DELTA` event as its own collapsible `"Réflexion en cours"` header, splitting words and Markdown mid-token.
- **Architectural Constraints**: Enforce `AD-19` (`lint-imports` 5 contracts: `agents` and `workflows` cannot introduce reverse/sibling cycles), `AD-17` Layer 2 real PG18 `create_app()` integration without `dependency_overrides`, bilingual `fr`/`en` RFC 9457 error catalogs, `0-diff` OpenAPI 3.1 SDK regeneration, and `<= 300` lines per modified non-barrel production file.

### 1.2 Exploration, GitNexus Impact Analysis, Refactoring & Technical Debt
- **GitNexus Impact Analysis (`gitnexus_query`, `gitnexus_context`, `gitnexus_impact` scoped to worktree)**:
  - `ProcessExecutionDispatcher` (`packages/orcia-core/src/orcia_core/agents/process_dispatcher.py:47-293`): Direct upstream binding via `apps/api/src/orcia_api/dependencies/reflexive_execution.py` (`get_process_execution_dispatcher`) and `apps/api/src/orcia_api/routers/workflows.py` (`ProcessDispatcherDep`), plus `orcia_connectors.bounded_workflow_models` (`UnifiedProcessRunResult`).
  - `GatewayReflexiveLlmAdapter` (`packages/orcia-core/src/orcia_core/agents/llm_adapter.py:35-217`): Bound via `ReflexiveLlmPort` in `reflexive_execution.py` (`get_reflexive_runtime_service` & `get_assistant_reflexive_runtime_service`) and unit tests in `tests/unit/core/test_reflexive_llm_stream_and_gate_adapters.py`.
  - `ProcessesHubPage` / `ProcessesActiveDossiersCard` / `useInteractiveProcessRunController`: Impact `apps/web/src/features/processes/*`, `apps/web/src/__tests__/story-16-3-*`, `story-16-4-*`, `story-29-5-*`, and Playwright E2E `12-epic16-*`, `20-process-studio-v2-*`.
- **Exploration & Key Metrics**:
  - Audited `infra/migrations/versions/0010_story_3_1_workflow_runs_triggers_and_run_lock.py` (`workflow_runs`), `20261111_01_reflexive_execution_sessions.py` + `20261122_267` (`reflexive_execution_sessions`), and `20261108_0910_declarative_packs_and_workflows_v2.py` (`workflow_definitions_v2`). Found that `workflow_v2_runs` had no PG18 persistence table yet (`workflow_v2_runs_store` was RAM-only).
  - Checked line counts: `process_dispatcher.py` (299L), `AgentExecutionTrace.tsx` (294L), `useInteractiveProcessRunController.ts` (293L), `executions_trace.py` (292L) — all require clean modular extraction so every file stays `<= 300` lines.
- **Refactoring Opportunities & Emerging Technical Debt Mitigation**:
  - Extract a dedicated PG18 store (`SqlWorkflowV2RunsStore` + unified pending-run query) in `packages/orcia-core/src/orcia_core/workflows/_internal/sql_workflow_v2_runs.py` and `apps/api/src/orcia_api/routers/_workflows_pending_runs.py` to keep `workflows.py` and `executions_trace.py` `< 300` lines.
  - Extract `apps/api/src/orcia_api/dependencies/_process_llm_bridge.py` for app-scoped live LLM endpoint & workspace datasource resolution without breaking `AD-19` layer boundaries (`orcia_core.agents` stays independent of `orcia_core.orchestration` and `orcia_core.bootstrap`).
  - Extract `packages/ui/src/components/agentExecutionTraceGrouping.ts` for event grouping + `THOUGHT_DELTA` coalescing so `AgentExecutionTrace.tsx` stays well under `300` lines.
  - Extract `apps/web/src/features/processes/execution/useInteractiveRunHydration.ts` (or helper) if needed to keep `useInteractiveProcessRunController.ts` `<= 300` lines.

---

## 2. Implementation Plan

### 2.1 Data Schema & Alembic Migrations (`infra/migrations/versions/...`)
- `infra/migrations/versions/20261125_303_workflow_v2_runs.py` (revises `20261122_267`):
  - Create `workflow_v2_runs` (`id UUID PRIMARY KEY` UUIDv7, `run_id VARCHAR(128) NOT NULL UNIQUE`, `workspace_id UUID NULL REFERENCES workspaces(id) ON DELETE CASCADE`, `workflow_id VARCHAR(128) NOT NULL`, `workflow_slug VARCHAR(128) NOT NULL`, `workflow_title VARCHAR(255) NOT NULL DEFAULT ''`, `actor_slug VARCHAR(128) NOT NULL DEFAULT ''`, `status VARCHAR(48) NOT NULL`, `reflexive_execution_id VARCHAR(128) NULL`, `state_jsonb JSONB NOT NULL DEFAULT '{}'::jsonb`, `created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`, `updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`).
  - Add B-Tree index `ix_workflow_v2_runs_ws_status_updated ON workflow_v2_runs (workspace_id, status, updated_at DESC)` for fast workspace-scoped pending-validation hydration.
  - Provide reversible `downgrade()` dropping index and table; register `workflow_v2_runs` in `infra/scripts/maintenance/_first_boot_reset_guards.py` (`ORDERED_MUTABLE_TABLES_TO_CLEAR`) so `pnpm db:reset` restores clean `0`-run Day-0 state.

### 2.2 Hexagonal Core, Orchestration & Workers (`packages/orcia-core/`)
- `packages/orcia-core/src/orcia_core/workflows/_internal/sql_workflow_v2_runs.py`:
  - `SqlWorkflowV2RunsStore` persisting `workflow_v2_runs` (`upsert_run`, `get_run`, `list_runs_for_workspaces`) plus unified PG18 reader combining `workflow_v2_runs`, `workflow_runs` (Story 3.x), and unlinked `reflexive_execution_sessions` (`WHERE execution_profile = 'PROCESS'`).
- `packages/orcia-core/src/orcia_core/agents/llm_adapter.py`:
  - Remove `_DEFAULT_FALLBACK_RESOURCE = "docs/product/capabilities.yaml"`.
  - Support live `LlmStreamingPort` + async `endpoint_resolver` (`LlmEndpointConfig`) for real workspace LLM execution; never call `_build_deterministic_cassette_decision` for non-cassette gateways; in explicit test cassette mode (`is_cassette_adapter=True`), use only provided `initial_resources` without hardcoding `capabilities.yaml`.
  - Define localized `ProcessModelNotConfiguredError` / `ProcessDatasourcesRequiredError` in `orcia_core.agents.errors` and symmetric `fr`/`en` entries in `orcia_core.agents._error_catalog`.
- `packages/orcia-core/src/orcia_core/agents/process_dispatcher.py`:
  - Propagate resolved `initial_resources` into `ReflexiveRuntimeConfig` for both Goal-Driven and Milestone-Driven agent sub-steps.

### 2.3 Backend API, Security & Contracts (`apps/api/`, `packages/api-client/`)
- `apps/api/src/orcia_api/dependencies/core_and_lifespan.py`:
  - Wire `LiteLLMAdapter()` (with `fallback_cassette=None`) by default so production never falls back silently to `DeterministicCassetteLLM`.
- `apps/api/src/orcia_api/dependencies/reflexive_execution.py` & `_process_llm_bridge.py`:
  - Wire `GatewayReflexiveLlmAdapter` with app-scoped `endpoint_resolver` + `HttpxMultiProviderLlmStreamingAdapter` when live, plus `SqlWorkflowV2RunsStore` (`get_workflows_v2_runs_sql_store`).
- `apps/api/src/orcia_api/routers/workflows.py` & `_workflows_pending_runs.py` & `executions_trace.py`:
  - Expose `GET /api/v1/workflows/v2/runs` (workspace-scoped / global authorized scope via `ScopeAccessGuard` / `resolve_finops_read_scope`), returning real PG18 active/pending runs (`[]` on clean Day-0).
  - Persist `POST /api/v1/workflows/v2/{workflow_id}/runs` and `POST /api/v1/runs/{run_id}/hitl-signal` in PG18 `workflow_v2_runs` (`GET /api/v1/runs/{run_id}` rehydrates from PG18 on cold boot).
  - Enforce live LLM + attached datasource / explicit step input pre-flight check (returning localized RFC 9457 HTTP `422` when missing in live mode).
- `packages/api-client/`:
  - Regenerate OpenAPI 3.1 (`openapi.json`, `schema.ts`, `process_studio_v2.ts`) via `scripts/export_openapi.py` (`0-diff`) and expose `listProcessPendingRuns(...)` in `workflowsV2.ts`.

### 2.4 User Interface & Experience (`apps/web/`, `packages/ui/`)
- `packages/ui/src/components/agentExecutionTraceGrouping.ts`, `AgentExecutionTrace.tsx`, `AgentExecutionTraceItems.tsx`:
  - Coalesce consecutive `THOUGHT_DELTA` chunks within each phase group (and delegated sub-blocks) into a single continuous thought block, seamlessly merging with `THOUGHT_COMPLETED` without changing `@orcia/ui` isolation boundaries.
- `apps/web/src/features/processes/ProcessesHubPage.tsx` & `ProcessesActiveDossiersCard.tsx`:
  - Hydrate pending validations strictly from `GET /api/v1/workflows/v2/runs` via `@orcia/api-client`, remove `localStorage["orcia.processes.active_run_workflow_id.v1"]` sticky auto-launch, remove the hardcoded `"1 validation en attente de votre décision"` badge and `workflows[0]` promotion, and render truthful backend run statuses (`RUNNING`, `WAITING_SUBSTEP_HITL`, `WAITING_FINAL_ANCHOR`, `WAITING_WRITE_PREVIEW`, `COMPLETED`, `PAUSED`, etc.) using typed `fr`/`en` i18n dictionaries.
- `apps/web/src/features/processes/execution/useInteractiveProcessRunController.ts`, `interactiveRunSyncHelpers.ts`, `interactiveRunHitlActions.ts`, `InteractiveRunDrawer.tsx`, `interactiveRunGoalPayload.ts`, `interactiveRunFormatters.ts`:
  - Support rehydrating an existing PG18 run (`initialPendingRun`), update status truthfully from backend responses, remove hardcoded `docs/product/capabilities.yaml` `initial_resources` payloads, keep every module `<= 300` lines, and display localized RFC 9457 error banners when LLM/datasources are missing.

### 2.5 Test Pyramid Impact Analysis (`AD-17` — Layers 1 to 5 + Security, Mandatory)
- **Layer 1a (`tests/unit/test_story_30_3_processes_live_llm_and_pending_runs.py`) & Layer 1b (`packages/ui/src/__tests__/story-30-3-coalesced-thought-trace.test.tsx`, `apps/web/src/__tests__/story-30-3-processes-pg18-pending-runs.test.tsx`)**: Unit assertions for zero silent cassette/capabilities fallback, localized RFC 9457 errors, coalesced `THOUGHT_DELTA` rendering, empty Day-0 state, absence of sticky `localStorage` auto-launch, and truthful run status mapping. Update impacted existing Vitest specs (`story-29-5`, `story-16-4`).
- **Layer 2 (`tests/integration/api/test_story_30_3_pending_runs_and_live_guard_postgres18.py`)**: Real `testcontainers` PG18 + Redis `create_app()` integration (zero `dependency_overrides`) verifying `0` pending runs on Day-0, workspace isolation + `ScopeAccessGuard`, cold `F5` rehydration of `workflow_v2_runs`, `403 ERR_OBSERVER_MODE_READ_ONLY`, `422` missing LLM/datasource RFC 9457 response, and Alembic `20261125_303` reversibility.
- **Layer 3**: `scripts/export_openapi.py --check` (`0-diff`) & `lint-imports` (`5/5`).
- **Layer 5**: Update impacted Playwright E2E specs (`12-epic16`, `20-process-studio-v2`) to attach real workspace datasources / reopen pending PG18 runs cleanly without sticky `localStorage`.

---

## 3. Summary of Changes & Results (Post-Implementation)

### 3.1 Created & Modified Files

| Status | File | Role & Line Count |
| :--- | :--- | :--- |
| Created | `infra/migrations/versions/20261125_303_workflow_v2_runs.py` | Reversible Alembic migration (`workflow_v2_runs` + B-Tree index `ix_workflow_v2_runs_ws_status_updated`) (`54` L) |
| Created | `packages/orcia-core/src/orcia_core/workflows/_internal/sql_workflow_v2_runs.py` | PG18 `SqlWorkflowV2RunsStore` (`upsert_run`, `get_run`) (`169` L) |
| Created | `packages/orcia-core/src/orcia_core/workflows/_internal/_sql_workflow_v2_pending_query.py` | Unified PG18 pending/active runs query across `workflow_v2_runs`, `workflow_runs`, and `reflexive_execution_sessions` (`231` L) |
| Created | `packages/orcia-core/src/orcia_core/agents/_cassette_reflexive_decisions.py` | Test-cassette-only reflexive turn decision helper without hardcoded `capabilities.yaml` fallback (`151` L) |
| Created | `apps/api/src/orcia_api/dependencies/_process_llm_bridge.py` | App-scoped live LLM endpoint & PG18 `workspace_datasources` preflight bridge (`215` L) |
| Created | `apps/api/src/orcia_api/routers/_workflows_pending_runs.py` | `GET /api/v1/workflows/v2/runs`, PG18 run persistence, cold F5 rehydration, and HITL signal handler (`255` L) |
| Created | `packages/ui/src/components/agentExecutionTraceGrouping.ts` | Phase grouping & `THOUGHT_DELTA` / consecutive `SYNTHESIS_READY` coalescing (`162` L) |
| Created | `apps/web/src/features/processes/execution/interactiveRunHitlActions.ts` | Extracted HITL action handlers (`194` L) |
| Created | `apps/web/src/features/processes/execution/interactiveRunSyncHelpers.ts` | Extracted run sync & rehydration helpers (`132` L) |
| Created | `tests/unit/test_story_30_3_processes_live_llm_and_pending_runs.py` | Unit tests for live LLM guard, zero cassette/capabilities fallback & pending runs (`189` L) |
| Created | `tests/unit/test_story_30_3_workflows_and_bridge_coverage.py` | Unit coverage tests for workflows pending runs & LLM bridge (`307` L) |
| Created | `tests/unit/test_story_30_3_sql_stores_and_llm_coverage.py` | Unit coverage tests for SQL run stores & `GatewayReflexiveLlmAdapter` (`585` L) |
| Created | `tests/integration/api/test_story_30_3_pending_runs_and_live_guard_postgres18.py` | Real PG18 + Redis 7.4 `create_app()` Layer 2 integration test (`321` L) |
| Created | `packages/ui/src/__tests__/story-30-3-coalesced-thought-trace.test.tsx` | Vitest suite for coalesced reasoning & synthesis trace rendering (`197` L) |
| Created | `apps/web/src/__tests__/story-30-3-processes-pg18-pending-runs.test.tsx` | Vitest suite for Day-0 empty pending validations, zero sticky `localStorage`, and F5 rehydration (`205` L) |
| Modified | `packages/orcia-core/src/orcia_core/agents/` (`errors.py`, `_error_catalog.py`, `llm_adapter.py`, `process_dispatcher.py`, `_runtime_helpers.py`, `_runtime_turn_actions.py`, `_internal/dispatcher_helpers.py`), `ports/reflexive_runtime_ports.py`, `workflows/__init__.py` | Localized RFC 9457 live prerequisite errors, live `LlmStreamingPort` bridge, `THOUGHT_COMPLETED` flush before `ANSWER_TOKEN_DELTA`, `initial_resources` propagation (`50`–`296` L, all `<= 300` L) |
| Modified | `apps/api/src/orcia_api/` (`dependencies/__init__.py`, `core_and_lifespan.py`, `reflexive_execution.py`, `routers/workflows.py`, `routers/executions_trace.py`, `schemas/process_studio_v2.py`), `infra/scripts/maintenance/_first_boot_reset_guards.py` | Removed silent `DeterministicCassetteLLM` prod fallback, wired `GET /api/v1/workflows/v2/runs`, PG18 run persistence, and Day-0 reset table guard (`149`–`299` L, all `<= 300` L) |
| Modified | `packages/api-client/` (`openapi.json`, `schema.ts`, `process_studio_v2.ts`, `workflowsV2.ts`, `index.ts`), `packages/ui/src/components/` (`AgentExecutionTrace.tsx`, `AgentExecutionTraceItems.tsx`), `apps/web/src/` (`ProcessesHubPage.tsx`, `ProcessesActiveDossiersCard.tsx`, `execution/*`, `i18n/locales/process_*`) | `0-diff` OpenAPI 3.1 SDK (`listProcessPendingRuns`), coalesced trace UI (`214` L / `258` L), real PG18 pending validations, truthful run statuses, zero hardcoded `capabilities.yaml` (`19`–`278` L, all `<= 300` L) |
| Modified | `tests/unit/` (`test_epic_8_*`, `test_story_4_2_*`), `tests/integration/api/` (`test_dbos_*`, `test_story_16_2_*`, `test_story_16_3_*`), `apps/web/src/__tests__/` (`setup/*`, `vitestReflexiveBackend.ts`, `story-16-4-*`, `story-29-5-*`), `apps/web/e2e/12-epic16-reflexive-trace-and-line-inspector.spec.ts` | Cassette opt-in on legacy unit suites, `tempfile.mkdtemp` AF_UNIX socket fix, updated mock handlers & real workspace+datasource Day-0 setup in E2E spec `12` (`257` L) |

### 3.2 Quantitative Metrics, Test Results & Coverage

- **File-Size Guard (`wc -l <= 300`)**: `100%` pass across all `41` handwritten modified/created production `.py`, `.ts`, and `.tsx` files (`19`–`299` lines; `0` violations).
- **Scoped Branch Coverage (`>= 90%`)**: **`94%`** (`1329` statements, `50` missed, `342` branches, `39` partial) across all `20` Story 30.3 Python modules (`coverage run --branch` over `10` fast unit suites, `45 passed`, `.coverage*` cleaned afterwards).
- **Static & Architecture Gates (`AD-17` / `AD-19`)**:
  - `.venv/bin/ruff check .`: **Passed** (`All checks passed!`)
  - `.venv/bin/ruff format --check .`: **Passed** (`1766 files already formatted`)
  - `.venv/bin/mypy --strict packages/orcia-core packages/orcia-connectors apps/api apps/worker`: **Passed** (`0` issues in `865` source files)
  - `.venv/bin/lint-imports`: **Passed** (`5 kept, 0 broken` across `906` files / `6559` dependencies)
  - `lint_spine.py`: **Passed** (`ok: true`, `0` findings)
  - `scripts/export_openapi.py --check`: **Passed** (`0-diff`)
  - `detect-secrets-hook --baseline .secrets.baseline`: **Passed** (`exit code 0`)
- **Python Test Suites (`--no-cov`)**:
  - `tests/evals tests/security tests/contract`: **`181 passed`** (`77.89s`)
  - `tests/unit`: **`1142 passed`** (`253.12s`)
  - PG18 + Redis 7.4 real `testcontainers` integration (`test_story_30_3_pending_runs_and_live_guard_postgres18.py`, `test_story_16_2_reflexive_runtime_and_sse_postgres18.py`, `test_story_16_3_dual_mode_processes_api.py`, `test_dbos_return_loops_and_claim_check.py`, `test_story_26_8_continue_in_process_dbos_postgres18.py`, `test_story_29_1_autonomous_runs_and_finops_pg18.py`, `test_e2e_reset_day0_postgres18_and_redis.py`): **`11 passed`** (`93.75s`)
- **TypeScript Monorepo & i18n (`pnpm turbo run lint typecheck test --concurrency=2`)**:
  - **`9/9` tasks succeeded** (`1m10.284s`): `@orcia/api-client` (`3` files / `20` tests), `@orcia/ui` (`39` files / `151` tests), `@orcia/web` (`92` files / `359` tests, i18n Gates 1–4 baseline = `0`).
- **Desktop Playwright E2E (`env -u ORCIA_E2E_SEED_FIXTURES`, `--project=desktop-cockpit`)**:
  - Specs `01`, `09`, `11`, `12-epic16`, `12-finops`, `20`, `29`: **`10 passed, 1 skipped (mobile-only), 0 failed`** (`2.2m`), with `docs/implementation-artifacts/e2e-campaign-epic-22/` cleaned immediately afterwards.
- **GitNexus Index**:
  - `npx gitnexus analyze --index-only .` completed cleanly (`46,885` nodes | `97,820` edges | `772` clusters | `1540` flows).
