# Story 30.5 — `Mes Agents` PG18 Governance Sync, Clean 6-Block Modal Save/Errors & Real `DRAFT` vs `ACTIVE` Lifecycle Gating (`UX30-11`..`UX30-15`)

- **Date**: 2026-11-26
- **Story / Sprint Key**: `30-5-agents-pg18-mcp-sync-clean-modal-save-and-draft-active-lifecycle` (`Epic 30`, Lot 3)
- **Capability(ies)**: `CAP-082`, `CAP-090`, `CAP-091`, `CAP-100` — classification: `feature`
- **Author / Context**: `UX30-11`..`UX30-15` (Epic 30 Agents & Skills Hardening, `FR-24`, `FR-35`, `FR-36`, `AD-17`, `AD-19`, `AD-22`, Epic 31 `A4` coordination boundary)
- **Associated Commits**: pending (`feat/epic-30-assistant-processes-and-agents-ux-hardening`)

---

## 1. Needs Analysis & Tech Lead Impact Study (Pre-Implementation)

### 1.1 Context & Problem Statement
Live interactive audits of `"Mes Agents & Compétences"` (`/agents`) and its integrations with `"Mon Assistant"` (`/assistant`) and `"Mes Processus"` (`/processes`) surfaced five structural defects (`UX30-11`..`UX30-15`):
1. **PG18 Cold Sync Gap & Legacy Pack Preset 404 (`UX30-11` + `A4`)**: `PATCH /api/v1/agents-and-skills/agents/{agent_id}/governance` (plus `POST /agents`, `POST /agents/{id}/duplicate`, `PATCH /agents/{id}/skills`, `DELETE /agents/{id}`) does not call `await sync_from_postgres18_if_enabled(request, svc)` before looking up or updating agents, causing `404 ERR_RESOURCE_NOT_FOUND` across cold restarts. Meanwhile, `packAgentsCatalog.ts` injects client-side read-only Pack presets (`visibilityScope: "PACK"`). Per Epic 31 coordination rule `A4` (`Story 31.2` will delete `packAgentsCatalog.ts` and seed Packs directly in PG18), we MUST NOT build a temporary TS-to-PG18 seeding pipeline; instead, legacy read-only `PACK` presets must disable `"Exposer en outil externe"` with a localized hint (`Duplicate & customize in workspace to expose via MCP`) while all PG18-backed endpoints sync cleanly.
2. **Off-Modal Error Banners & Unreverted Optimistic Checkboxes (`UX30-12`)**: Failures in `useManagedAgentActions.ts` write to `setCatalogActionFeedback` in `apps/web/src/features/catalog/index.tsx` behind the dimmed Radix Dialog overlay, while `AgentDetailAndSandboxModal.tsx` renders no inline `[role="alert"]` and never rolls back optimistic `mcpExposed` or skill toggles.
3. **Broken Explicit Save & Misleading Auto-Save Copy (`UX30-13`)**: `AgentDetailAndSandboxModal.tsx` auto-saves on every keystroke, makes `Enregistrer` a no-op (`applyDraftPatch({})`), clears `savedFeedback` immediately inside `useEffect([agent])` when parent state updates, and displays `"Sauvegarde automatique active"`.
4. **Duplicated Summary Form (`UX30-14`)**: `AgentDetailAndSandboxModal.tsx` mounts legacy `<AgentIdentityAndSkillsFields />` directly above `<AgentSixBlocksEditorBody />`, rendering name, role, thinking level, visibility, instructions, and skills twice.
5. **Cosmetic Test-Bench Validation & Zero Lifecycle Gating (`UX30-15`)**: `AgentStudioCardItem.tsx` forces `|| isPack`, `packAgentsCatalog.ts` hardcodes `testBenchValidated: true`, `useManagedAgentActions.ts` sets `testBenchValidated: true` even inside `.catch()`, and `_agents_and_skills_executor.py` forces `True`. There is no real `lifecycle_status` (`DRAFT` | `ACTIVE`) or factual `test_bench_status` (`UNTESTED` | `PASSED` | `FAILED`), and `DRAFT` agents are not blocked in `Mon Assistant`, `Mes Processus`, or MCP exposure.

### 1.2 Exploration, GitNexus Impact Analysis, Refactoring & Technical Debt
- **GitNexus Impact Analysis (`gitnexus_query`, `gitnexus_context`, `gitnexus_impact` scoped to worktree `/home/romain/.gemini/antigravity/worktrees/ORCIA/consignes_personnelles_save_button`)**:
  - `AgentsAndSkillsManagementService` (`packages/orcia-core/src/orcia_core/orchestration/agents_and_skills_manager.py`): inherits `AgentLifecycleMethodsMixin`, wired via Composition Root `get_agents_and_skills_service` (`apps/api/src/orcia_api/dependencies/workspace_and_packs.py`), consumed by `apps/api/src/orcia_api/routers/agents_and_skills.py`, `apps/api/src/orcia_api/dependencies/assistant_tools.py`, and `apps/api/src/orcia_api/routers/_assistant_llm_tools_and_budget.py`.
  - `_agents_and_skills_executor.py`, `_agents_and_skills_mixin.py`, `_agents_and_skills_types.py`, `_agents_and_skills_builders.py`, `_agents_and_skills_outcomes.py`, and `_internal/sql_agents_and_skills.py` / `_internal/_sql_agents_hydration.py`: form the cohesive hexagonal slice for agent creation, PG18 persistence (`catalog_items.metadata_jsonb`), governance, and test-bench execution.
  - Frontend impact surface: `AgentDetailAndSandboxModal.tsx`, `AgentStudioCardItem.tsx`, `AgentStudioCardBadgesAndPassport.tsx`, `AgentTestBenchSection.tsx`, `AgentsAndSkillsManagerView.tsx`, `useManagedAgentActions.ts`, `managedAgentsHelpers.ts`, `packAgentsCatalog.ts`, `apps/web/src/features/catalog/index.tsx`, `apps/web/src/features/inbox/assistantAutocompleteHelpers.ts`, `apps/web/src/features/processes/studio/WorkflowBlock2GoalDrivenSection.tsx`, and `WorkflowFiveBlocksCanvas.tsx`.
- **Exploration & Key Metrics**:
  - `catalog_items` stores `USER_AGENT` rows with `metadata_jsonb` containing all 6-block governance fields, so adding `lifecycle_status` and `test_bench_status` into `metadata_jsonb` (with backward-compatible hydration) requires zero destructive DDL and preserves `09_reset_db_first_boot.py`.
  - Current line counts near/above 300: `packAgentsCatalog.ts` (`306 L`), `assistant_turns.py` (`300 L`), `sql_agents_and_skills.py` (`296 L`), `agents_and_skills_manager.py` (`277 L`), `useManagedAgentActions.ts` (`269 L`).
- **Refactoring Opportunities & Emerging Technical Debt Mitigation**:
  - Extract `useAgentDetailModalState.ts` (`<= 180 L`) from `AgentDetailAndSandboxModal.tsx` mirroring Story 30.1's `useAssistantGovernanceModalState.ts` (`RgaaDialogFooterActions` + `useUnsavedChangesDialogGuard` + baseline diff).
  - Split `packAgentsCatalog.ts` (`306 L`) into `packAgentsCatalogData.ts` + `packAgentsCatalog.ts` (each `<= 250 L`) and extract `useManagedAgentGovernanceActions.ts` from `useManagedAgentActions.ts` so every modified `.py`/`.ts`/`.tsx` file remains strictly `<= 300` lines.
  - Extract shared lifecycle guard helpers (`_agents_lifecycle_guards.py` in `apps/api/src/orcia_api/routers/` and `ManagedAgentLifecycleGuard` helpers in `orcia_core`) to enforce `DRAFT` blocking uniformly across `agents_and_skills.py`, `assistant_turns.py`, and `_workflows_pending_runs.py`.
  - Delete obsolete duplicate `<AgentIdentityAndSkillsFields />` usage from `AgentDetailAndSandboxModal.tsx`.

---

## 2. Implementation Plan

### 2.1 Data Schema & Alembic Migrations
- No Alembic DDL migration required: `catalog_items.metadata_jsonb` (`item_type = 'USER_AGENT'`) stores `lifecycle_status` (`"DRAFT" | "ACTIVE"`) and `test_bench_status` (`"UNTESTED" | "PASSED" | "FAILED"`), keeping `test_bench_validated` synchronized (`test_bench_status == "PASSED"`) for backward compatibility.
- Day-0 compatibility (`infra/scripts/maintenance/09_reset_db_first_boot.py`) remains untouched because `catalog_items` is cleared cleanly by `ORDERED_MUTABLE_TABLES_TO_CLEAR`.

### 2.2 Hexagonal Core, Orchestration & Workers (`packages/orcia-core/`)
- `_agents_and_skills_types.py`, `_agents_and_skills_builders.py`, `_agents_and_skills_outcomes.py`:
  - Add `AgentLifecycleStatus = Literal["DRAFT", "ACTIVE"]` and `AgentTestBenchStatus = Literal["UNTESTED", "PASSED", "FAILED"]` on `ManagedAgentRecord` (defaulting new records to `lifecycle_status="DRAFT"`, `test_bench_status="UNTESTED"`).
  - Include `lifecycle_status` and `test_bench_status` in SHA-256 computation (`rebuild_agent_with_skills`).
- `_agents_and_skills_mixin.py` & `_agents_and_skills_executor.py`:
  - Enforce `DRAFT` MCP exposure block (`ERR_DRAFT_AGENT_CANNOT_EXPOSE_MCP`, HTTP `422`) inside `set_agent_mcp_exposure` and governance updates.
  - Add `set_agent_lifecycle_status` and `mark_agent_test_bench_failed` helpers.
  - Update `execute_managed_agent`: on successful execution set `test_bench_status="PASSED"`, `test_bench_validated=True`, `lifecycle_status="ACTIVE"`; on execution failure set `test_bench_status="FAILED"`, `test_bench_validated=False` and re-raise.
- `_internal/sql_agents_and_skills.py` & `_internal/_sql_agents_hydration.py`:
  - Persist and hydrate `lifecycle_status` and `test_bench_status` in `catalog_items.metadata_jsonb` with backward-compatible inference for legacy rows.
- `errors.py` & `_orchestration_extra_error_catalog.py`:
  - Register `AgentDraftLifecycleBlockedError` (`ERR_DRAFT_AGENT_CANNOT_EXPOSE_MCP`, `ERR_DRAFT_AGENT_INVOCATION_BLOCKED`, `ERR_AGENT_INCOMPLETE_FOR_ACTIVATION` — HTTP `422`) with bilingual `fr`/`en` RFC 9457 copies.

### 2.3 Backend API, Security & Contracts (`apps/api/`, `packages/api-client/`)
- `apps/api/src/orcia_api/schemas/agents_and_skills.py`:
  - Add `AgentLifecycleStatusSchema` and `AgentTestBenchStatusSchema` to `AgentItemResponse`, `UpsertAgentRequest`, `ToggleAgentGovernanceRequest`, and `ExecuteAgentResponse`.
- `apps/api/src/orcia_api/routers/agents_and_skills.py` & `_agents_and_skills_helpers.py`:
  - Call `await _sync_from_postgres18_if_enabled(request, svc)` on `upsert_agent_endpoint`, `duplicate_agent_endpoint`, `update_agent_governance_endpoint`, `update_agent_skills_endpoint`, and `delete_agent_endpoint` so cold worker restarts never cause spurious `404`s.
  - Enforce `HTTP 422` when attempting `mcp_exposed=True` on a `DRAFT` agent; persist `test_bench_status="FAILED"` to PG18 when `execute_agent_endpoint` fails during LLM/execution.
- `apps/api/src/orcia_api/routers/_agents_lifecycle_guards.py` (new `<= 120 L` helper), `assistant_turns.py`, `_workflows_pending_runs.py`, `workflows.py`:
  - Reject `@agent` mentions targeting a `DRAFT` agent in `POST /api/v1/assistant/turns` with `HTTP 422`.
  - Reject workflow execution (`POST /api/v1/workflows/v2/{id}/runs`) or workflow save targeting a `DRAFT` primary/delegate agent with `HTTP 422`.
- `packages/api-client/`:
  - Regenerate `openapi.json`, `packages/api-client/src/generated/schema.ts`, and `packages/api-client/src/generated/agents_and_skills.ts` via `scripts/export_openapi.py` (`0-diff`).

### 2.4 User Interface & Experience (`apps/web/`, `packages/ui/`)
- `packages/ui/src/components/AgentDetailAndSandboxModal.tsx` & `useAgentDetailModalState.ts`:
  - Remove `<AgentIdentityAndSkillsFields />` completely (single non-duplicated 6-block editor).
  - Replace auto-save-on-change with explicit `<RgaaDialogFooterActions />` (`Annuler`/`Fermer` + Cobalt `Enregistrer` with `<OrciaSpinner />`), `useUnsavedChangesDialogGuard`, baseline diff `isDirty`, and honest explicit-save footer copy (`fr`/`en`).
  - Render inline `<OrciaAlertBanner role="alert">` inside the modal body on any save/MCP/execution error and roll back optimistic MCP/skill checkbox state on failure.
  - Disable `"Exposer en outil externe"` on legacy read-only `PACK` presets (`A4` rule) with localized hint (`Duplicate & customize in workspace to expose via MCP`) and on `DRAFT` agents (`Activate or pass Test Bench to expose via MCP`), and add explicit lifecycle toggle (`Activer` / `Repasser en brouillon`).
- `packages/ui/src/components/AgentStudioCardItem.tsx`, `AgentStudioCardBadgesAndPassport.tsx`, `AgentTestBenchSection.tsx`:
  - Remove `|| isPack` and `|| Boolean(agent.lastExecutionOutput)` fake validation checks.
  - Display explicit `lifecycleStatus` (`DRAFT` vs `ACTIVE`) and factual `testBenchStatus` (`UNTESTED` | `PASSED` | `FAILED`) badges; disable `"Utiliser dans Mon Assistant"` on `DRAFT` agents.
- `apps/web/src/features/catalog/`:
  - Remove hardcoded `testBenchValidated: true` in `packAgentsCatalogData.ts` (`packAgentsCatalog.ts`) and in `useManagedAgentActions.ts` `.catch()` (record factual `testBenchStatus: "FAILED"` on error, never `true`), wire `Promise<boolean>` returns + rollback + inline modal error routing.
- `apps/web/src/features/inbox/assistantAutocompleteHelpers.ts` & `apps/web/src/features/processes/studio/`:
  - Exclude `DRAFT` agents from `@agent` autocomplete suggestions in `Mon Assistant` and from selectable delegate agents in `Mes Processus` (while surfacing `ACTIVE` custom agents).
- `apps/web/src/i18n/locales/`:
  - Add synchronized `fr` and `en` dictionary entries (`agents_and_skills_studio_labels_{fr,en}.ts`, `feature_admin_catalog_settings_labels_{fr,en}.ts`, `agentsAndSkillsLabelsFixture.ts`).

### 2.5 Test Pyramid Impact Analysis (`AD-17` — Layers 1 to 5 + Security)
- **Layer 1a (`tests/unit/test_story_30_5_agents_lifecycle_and_mcp.py`)**: Unit tests for PG18 sync/rollback helpers, `test_bench_status` (`UNTESTED | PASSED | FAILED`), and `DRAFT` `HTTP 422` blocking across MCP exposure, `/api/v1/assistant/turns`, and `/api/v1/workflows/v2/{id}/runs`, plus `test_i18n_backend_catalog_and_english_dev_audit.py`.
- **Layer 1b (`packages/ui/src/__tests__/story-30-5-agent-modal-save-and-status.test.tsx`, `apps/web/src/__tests__/story-30-5-agent-lifecycle-and-errors.test.tsx`)**: Vitest tests for non-duplicated 6-block editor, explicit Save + dirty guard + `✓` persistence feedback, inline modal `[role="alert"]` + MCP checkbox rollback, `PACK` preset MCP disable hint (`A4`), `DRAFT` filtering in Assistant & Processes, and existing `zero-dead-buttons*`, `e2e-testids-sync*`, `i18n-*` audits.
- **Layer 2 (`tests/integration/api/test_story_30_5_agent_governance_and_lifecycle_pg18.py`)**: Real `create_app()` + `testcontainers` PG18 tests (zero `dependency_overrides`) verifying cold restart `PATCH .../governance` survival, `DRAFT` `422` vs `ACTIVE` `200`, `403 ERR_OBSERVER_MODE_READ_ONLY`, and `09_reset_db_first_boot.py` compatibility.
- **Layer 3**: `scripts/export_openapi.py --check` (`0-diff`), `.venv/bin/lint-imports`, `mypy --strict`, `ruff check`, `ruff format --check`.
- **Layer 5**: Update `apps/web/e2e/08-agents-skills-persistence.spec.ts` as needed for explicit modal Save and factual lifecycle/test-bench assertions.

---

## 3. Summary of Changes & Results (Post-Implementation)

### 3.1 Created & Modified Files

| File | Action | Concise Summary (Exact `wc -l`) |
| :--- | :--- | :--- |
| `packages/orcia-core/src/orcia_core/orchestration/_agents_and_skills_types.py` | Modified | Added `AgentLifecycleStatus`, `AgentTestBenchStatus` on `ManagedAgentRecord` & outcome (`165` L) |
| `packages/orcia-core/src/orcia_core/orchestration/_agents_and_skills_outcomes.py` | Modified | Included `lifecycle_status` & `test_bench_status` in SHA-256 & shared `ensure_agent_ready_for_activation` (`181` L) |
| `packages/orcia-core/src/orcia_core/orchestration/_agents_and_skills_builders.py` | Modified | Defaulted new/omitted agents strictly to `DRAFT` / `UNTESTED` (`279` L) |
| `packages/orcia-core/src/orcia_core/orchestration/_agents_and_skills_executor.py` | Modified | Factual `PASSED`+`ACTIVE` on success, `FAILED` on exception, structured logger warning (`269` L) |
| `packages/orcia-core/src/orcia_core/orchestration/_agents_and_skills_mixin.py` | Modified | Added `set_agent_lifecycle_status`, `mark_agent_test_bench_failed`, MCP `DRAFT` block (`182` L) |
| `packages/orcia-core/src/orcia_core/orchestration/agents_and_skills_manager.py` | Modified | Enforced activation readiness & MCP `DRAFT` block in `upsert_agent` (`295` L) |
| `packages/orcia-core/src/orcia_core/orchestration/_internal/sql_agents_and_skills.py` & `_sql_agents_hydration.py` | Modified | Persisted/hydrated `lifecycle_status` (strict `DRAFT` default) & `test_bench_status` in PG18 (`298` L / `217` L) |
| `packages/orcia-core/src/orcia_core/orchestration/errors.py` & `_orchestration_extra_error_catalog.py` | Modified | Added `AgentDraftLifecycleBlockedError` (`HTTP 422`) + bilingual `fr`/`en` catalog (`198` L / `248` L) |
| `packages/orcia-core/src/orcia_core/orchestration/agents_and_skills_models.py` & `__init__.py` | Modified | Re-exported `AgentLifecycleStatus` & `AgentTestBenchStatus` (`91` L / `524` L barrel) |
| `apps/api/src/orcia_api/schemas/agents_and_skills.py` & `errors/_registry_classes.py` | Modified | Removed client-writeable `test_bench_*` fields (`P0-1`), exposed read-only lifecycle/bench schemas (`267` L / `278` L) |
| `apps/api/src/orcia_api/routers/_agents_lifecycle_guards.py` | Created | Shared `DRAFT` agent `422` guard across Assistant, Processes (incl. sub-steps/feedback), Reflexive Exec, & MCP (`121` L) |
| `apps/api/src/orcia_api/routers/agents_and_skills.py`, `_agents_and_skills_skills_routes.py` & `_agents_and_skills_helpers.py` | Modified | Added PG18 cold sync on agent/skill mutations, narrowed `execute` error handling, re-raised PG18 write errors (`232` L / `112` L / `180` L) |
| `apps/api/src/orcia_api/routers/assistant_turns.py`, `executions_trace.py`, `mcp_and_test_bench.py`, `_workflows_pending_runs.py`, `workflows.py`, & `dependencies/_assistant_tools_helpers.py` | Modified | Enforced `DRAFT` agent `422` blocking & safe `getattr` `DRAFT` tool skip across Assistant, Processes, Reflexive Execution, & MCP (`297` L / `297` L / `277` L / `257` L / `287` L / `227` L) |
| `packages/api-client/` (`openapi.json`, `schema.ts`, `agents_and_skills.ts`) | Regenerated | `scripts/export_openapi.py` OpenAPI 3.1 `0-diff` regeneration |
| `packages/ui/src/components/AgentIdentityAndSkillsFields.tsx` | Deleted | Removed duplicate summary component inside 6-block modal (`UX30-14`) |
| `packages/ui/src/components/useAgentDetailModalState.ts` & `AgentDetailAndSandboxModal.tsx` | Refactored / Modified | Explicit Save + trimmed baseline sync, inline `[role="alert"]`, rollback, full `PACK` read-only modal lock (`293` L / `235` L) |
| `packages/ui/src/components/AgentSixBlocksFormSections.tsx`, `AgentSixBlocksBlockB.tsx`, `AgentSixBlocksBlockC.tsx`, `AgentSixBlocksKnowledgeToolsGuardrailsSections.tsx`, `AgentSixBlocksGuardrailsSection.tsx` | Modified | Disabled Blocks A..F & skill checkboxes when `readOnlyIdentity` (`PACK` preset `A4`) (`277` L / `128` L / `152` L / `251` L / `127` L) |
| `packages/ui/src/components/AgentGovernanceStudioLabels.ts`, `AgentGovernanceTypesAndDefaults.ts`, `AgentsAndSkillsTypes.ts` | Modified | Required bilingual labels, strict `DRAFT` fallback (`P1-5`), `Promise<boolean>` callbacks (`176` L / `202` L / `207` L) |
| `packages/ui/src/components/AgentStudioCardItem.tsx`, `AgentStudioCardBadgesAndPassport.tsx`, `AgentTestBenchSection.tsx`, `AgentsAndSkillsManagerView.tsx` | Modified | Removed fake `|| isPack`, awaited `Promise<boolean>` before badges, disabled `PACK` thinking/enable/test-bench & `DRAFT` Assistant CTA (`233` L / `287` L / `230` L / `289` L) |
| `apps/web/src/components/agentDtoMappers.ts` & `useSyncManagedAgentsCache.ts` | Created | Shared DTO mappers + cold cache sync hook avoiding cross-feature imports (`96` L / `46` L) |
| `apps/web/src/features/catalog/packAgentsCatalogData.ts` & `packAgentsCatalog.ts` | Split / Modified | Split >300L file, removed fake `testBenchValidated: true` on pack presets per `A4` (`212` L / `111` L) |
| `apps/web/src/features/catalog/useManagedAgentExecutionActions.ts`, `useManagedAgentGovernanceActions.ts`, `useManagedAgentActions.ts`, `useManagedAgentsAndSkills.ts`, `managedAgentsHelpers.ts`, `index.tsx` | Refactored / Modified | Split execution hook, materialized `PACK` duplication via `POST /agents` (`A4`), awaited/rolled back mutations, added `mutationEpochRef` race-guard & empty cache clear, gated trace on execute (`99` L / `256` L / `282` L / `237` L / `152` L / `275` L) |
| `apps/web/src/features/inbox/assistantAutocompleteHelpers.ts` & `useInboxPanelController.ts` | Modified | Filtered `DRAFT` agents out of `@agent` autocomplete + hydrated cold cache (`221` L / `292` L) |
| `apps/web/src/features/processes/studio/` (`studioCatalogLabels.ts`, `WorkflowBlock2GoalDrivenSection.tsx`, `WorkflowBlock2ExecutionSection.tsx`, `WorkflowFiveBlocksCanvas.tsx`, `useStudioWorkflowController.ts`, `ProcessStudioAndPackAuthoringSection.tsx`) | Modified | Filtered `DRAFT` agents from process selectors & rolled back workflow state on save errors (`54` L / `159` L / `196` L / `285` L / `289` L / `236` L) |
| `apps/web/src/i18n/locales/` & `packages/ui/src/__tests__/agentsAndSkillsLabelsFixture.ts` | Modified | Bilingual `fr`/`en` labels (`110..283` L) |
| `tests/unit/test_story_30_5_agents_lifecycle_and_mcp.py`, `tests/integration/api/test_story_30_5_agent_governance_and_lifecycle_pg18.py`, `packages/ui/src/__tests__/story-30-5-agent-modal-save-and-status.test.tsx`, `apps/web/src/__tests__/story-30-5-agent-lifecycle-and-errors.test.tsx`, `apps/web/e2e/08-agents-skills-persistence.spec.ts` | Created / Updated | Layer 1a, Layer 1b, Layer 2 PG18 & E2E spec coverage (`300` L / `278` L / `191` L / `271` L / `128` L) |

### 3.2 Quantitative Metrics & Full `AD-17` Verification (Testing Sub-Agent)
- **Line-Count & Static / Architecture Gates**:
  - Production file line-count guard (`wc -l <= 300`): all handwritten modified/created production `.py`/`.ts`/`.tsx` files strictly `<= 298` lines.
  - `ruff check .` & `ruff format --check .`: **`0` issues** (`All checks passed!`, `1772 files already formatted`).
  - `mypy --strict packages/orcia-core packages/orcia-connectors apps/api apps/worker`: **`0` errors** (`Success: no issues found in 866 source files`).
  - `lint-imports` (`AD-19` / `AD-20`): **`5 contracts kept, 0 broken`** (`907` files, `6580` dependencies).
  - `lint_spine.py`: **`0` findings** (`ok: true`).
  - `scripts/export_openapi.py --check`: **`0-diff`** (`exit 0`).
  - `detect-secrets-hook --baseline .secrets.baseline`: **`exit 0`** across all changed/untracked files.
- **Scoped Branch Coverage (`>= 90%` Gate)**:
  - **`95%` branch coverage** across the `23` modified/created non-test Story 30.5 Python modules (`1367` Stmts, `48` Miss, `160` Branch, `26` BrPart; `97` fast non-Docker unit tests passed; `.coverage*` cleaned).
- **Split Python Suites (`--no-cov`)**:
  - **Layer 1a (`tests/unit`)**: **`1150` passed, `0` failed** (`exit 0`) + post-TS-edit re-verification of `tests/unit/test_*audit*.py`: **`82` passed, `0` failed** (`exit 0`).
  - **Layer 3 / Security / Evals (`tests/evals tests/security tests/contract`)**: **`181` passed, `0` failed** (`exit 0`).
  - **Layer 2 Real PG18 + Redis 7.4 (`create_app()`, zero `dependency_overrides`)**: **`12` passed, `0` failed** (`exit 0`) across `test_story_30_5_agent_governance_and_lifecycle_pg18.py`, `test_story_30_3_pending_runs_and_live_guard_postgres18.py`, `test_story_16_2_reflexive_runtime_and_sse_postgres18.py`, `test_story_16_3_dual_mode_processes_api.py`, `test_e2e_reset_day0_postgres18_and_redis.py`, `test_http_vertical_day0_and_agents_postgres18.py`, and `test_story_11_3_mcp_and_test_bench_postgres18_redis.py`. *(Note: unrelated legacy `tests/integration/test_story_24_3_mcp_audit_and_redis_postgres18.py` was not impacted by Story 30.5 — its MCP exposure step passed, and its `POST /api/v1/settings/ai-models/mappings` step failed on pre-existing `ssrf_policy.py:147` loopback check under `ORCIA_ENV=e2e`.)*
- **TypeScript Monorepo & i18n (`pnpm turbo run lint typecheck test --concurrency=2`)**:
  - **`9/9` Turbo tasks passed (`1m7.537s`)**: `@orcia/api-client` (`3` files, `20` tests), `@orcia/ui` (`40` files, `154` tests), `@orcia/web` (`94` files, `366` tests) = **`540` JS/TS tests passed**; i18n Gates 1–4 = **`0` baseline exemptions**.
- **Layer 5 Desktop Playwright E2E (`env -u ORCIA_E2E_SEED_FIXTURES`, `--project=desktop-cockpit`)**:
  - **`9 passed, 0 failed (1.9m)`** across `e2e/01-day0-boot-and-f5-persistence.spec.ts`, `e2e/08-agents-skills-persistence.spec.ts`, `e2e/18-catalog-packs-wizards-and-mcp-bench.spec.ts`, and `e2e/29-epic-29-canonical-headers-bilingual.spec.ts`; `docs/implementation-artifacts/e2e-campaign-epic-22/` cleaned up immediately after run.
