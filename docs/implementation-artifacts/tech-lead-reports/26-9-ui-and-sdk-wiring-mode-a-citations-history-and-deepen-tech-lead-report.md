# Story 26.9 — UI & SDK Wiring: Mode A Governance API, Server `citation_map` Pills, PG18 Thread History, Tool Trace, Approval Cards, "Deepen" Button & F5 Cold Survival

- **Date**: 2026-11-22
- **Story / Sprint Key**: `26-9-ui-and-sdk-wiring-mode-a-citations-history-and-deepen` (`Epic 26` / `Lot 7`)
- **Capabilities**: `CAP-070`, `CAP-071`, `CAP-072`, `CAP-073`, `CAP-260` (classification: `feature`)
- **Author / Context**: Complete UI, SDK (`@orcia/api-client`), Design System (`@orcia/ui` Direction C), and backend route cleanup for `Mon Assistant` (`AD-25`, `D1`–`D9`, `R2`–`R4`, `H-14`, `H-18`, `H-26`), removing duplicate `POST /api/v1/assistant/threads/{thread_id}/turns`, client-side citation heuristics (`filterUsedRagSourcesForTurn`), `localStorage` business persistence of conversation turns & governance preferences, and Mode B Studio UI.

---

## 1. Need Analysis & Tech Lead Impact Study (Analyse du Besoin)

### 1.1 Context & Problem Statement
- **Observed gaps (`H-14` UI, `H-18` UI, `H-26`, `R2`, `R3`, `R4`)**:
  - `apps/api/src/orcia_api/routers/assistant_workspace_folders.py` still exposes duplicate route `POST /api/v1/assistant/threads/{thread_id}/turns` (`SendCollaborativeThreadTurnRequest` / `SendCollaborativeThreadTurnResponse`) alongside canonical `POST /api/v1/assistant/turns`.
  - `apps/web/src/features/inbox/` (`useInboxPanelController.ts`, `savedConversationsStore.ts`, `inboxTurnSyncHelpers.ts`, `assistantTurnPayloadHelper.ts`, `useAssistantStreamingTurn.ts`) still reads/writes conversation turns and Mode A governance preferences in `localStorage`, sends `conversation_history` from `localStorage` on `POST /api/v1/assistant/turns`, omits `thread_id` before turn submission (preventing PG18 `assistant_thread_messages` hydration on cold F5), and never hydrates from `GET /api/v1/assistant/threads/{thread_id}/messages` or `GET /api/v1/assistant/governance`.
  - `apps/web/src/features/inbox/assistantAutocompleteHelpers.ts` and `inboxCitationHelpers.ts` synthesize citations client-side via `filterUsedRagSourcesForTurn` and hardcoded `authorityTier: "REFERENCE"` / `freshness: "FRESH"` / `[Sn]` heuristics instead of rendering exclusively from server `citation_map` / `citation_guard` payloads.
  - `@orcia/ui` lacks dedicated Direction C `AssistantToolCallTrace` and `AssistantApprovalRequiredCard` primitives, a `supports_tools === false` disabled Speed 2/3 state with localized notice, and a **"Deepen"** (`fr`: `"Approfondir"`, `en`: `"Deepen"`) button on Speed 1 turns (`parent_turn_id`, highlighted on `low_evidence`).
  - `AssistantGovernanceModalAndStudio.tsx` still contains Mode B Studio UI (`AssistantGovernanceStudioModeB`, `assistant-open-studio-mode-b-btn`) and `InboxAuxiliaryPanels.tsx` passes stub Studio callbacks and `assembledLayers={[]}`.
- **Expected behavior**:
  - Delete `POST /api/v1/assistant/threads/{thread_id}/turns` and unused schemas, regenerating OpenAPI 3.1 + `@orcia/api-client` (`0-diff`) and adding typed domain methods for `GET /threads/{id}/messages`, `GET /governance`, `PUT /governance/mode-a/user`, and `PUT /governance/mode-a/workspace`.
  - Hydrate threads and conversation turns from PG18 (`GET /overview` + `GET /threads/{id}/messages`), create threads prior to turn dispatch, send zero `localStorage` message-history arrays in `POST /turns`, and reattach active streams via `GET /turns/active` + `GET /turns/{id}/stream?after=<cursor>`.
  - Render citation pills exclusively from server `citation_map` (deleting `filterUsedRagSourcesForTurn` and client `[Sn]`/`REFERENCE`/`FRESH` synthesis), wire Mode A governance + `assembledLayers` to PG18, remove Mode B Studio UI cleanly (`0` dead buttons), and ship Direction C `@orcia/ui` primitives (`AssistantToolCallTrace`, `AssistantApprovalRequiredCard`, `supports_tools=false` disabled Speed 2/3, **"Deepen"** button) with 100% bilingual `i18n` props (`fr`/`en`).

### 1.2 Exploration, GitNexus Impact Analysis, Factorization & Technical Debt
- **GitNexus Impact Analysis (`repo: "/home/romain/Documents/Projects/ORCIA"`)**:
  - `send_collaborative_thread_turn_endpoint` (`assistant_workspace_folders.py`): `0` live UI callers (`impactedCount: 0`); referenced only by `packages/api-client/src/domains/assistantStreaming.ts` and 6 legacy Python tests (`test_epic_10_story_10_4`, `test_assistant_and_rag_routes_require_rag_guard_audit`, `test_story_25_5`, `test_story_26_1`, `test_story_26_4a`, `test_story_26_4b`). All 6 tests migrate cleanly to canonical `POST /api/v1/assistant/turns` + `GET /api/v1/assistant/threads/{thread_id}/messages`.
  - `filterUsedRagSourcesForTurn` (`assistantAutocompleteHelpers.ts`): `impactedCount: 2` (`inboxTurnSyncHelpers.ts` -> `useInboxPanelController.ts`). Safe to delete outright.
  - `useInboxPanelController` (`useInboxPanelController.ts`): `277` L, single caller `AssistantInboxFeatureContent` (`inbox/index.tsx`). New PG18 thread hydration, Mode A governance hydration, and stream reattach helpers will be extracted into focused modular hooks/helpers (`<= 280` L/file) to respect the `300`-line file cap.
- **Factorization & Volumetry Control**:
  - Split new `@orcia/api-client` Mode A governance + thread messages client into `packages/api-client/src/domains/assistantGovernanceAndThreads.ts` (`<= 150` L) so `assistantStreaming.ts` and `index.ts` stay `<= 250` L.
  - Extract PG18 thread/governance hydration & citation mapping in `apps/web/src/features/inbox/` into focused hooks/helpers (`useServerAssistantThreads.ts`, `useServerAssistantGovernance.ts`, `inboxCitationHelpers.ts`), keeping every modified/created file `<= 300` lines (`savedConversationsStore.ts` `309` L -> slimmed `< 200` L; `SavedConversationsAndThreadView.tsx` `325` L -> `< 300` L).
  - Keep `AssistantToolCallTrace.tsx` and `AssistantApprovalRequiredCard.tsx` in `packages/ui/src/primitives/` strictly `<= 250` L each, using only `tokens*.css` CSS variables (zero raw hex codes; `#6D28D9` strictly `HumanLedAnchorCard`-only).

---

## 2. Implementation Plan (Plan d'Implémentation)

### 2.1 Data Schema & Alembic Migrations
- Reuse existing Story `26.4b` / `26.5` / `26.7` PG18 tables (`assistant_threads`, `assistant_thread_messages`, `workspace_customization_overrides`, `user_preferences`, `assistant_turn_feedback`, `reflexive_execution_sessions`). No Alembic migration required.

### 2.2 Hexagonal Core, Orchestration & Workers (`packages/orcia-core/`)
- Preserve existing `AssistantTurnEngine`, `GovernedAssistantToolRouter`, `SqlAssistantThreadMessagesRepository`, `SqlAssistantGovernanceRepository`, and `AssistantCitationAndV5GuardService` contracts without alteration.

### 2.3 Backend API, Security & Contracts (`apps/api/`, `packages/api-client/`)
- Delete `@router.post("/threads/{thread_id}/turns")` from `apps/api/src/orcia_api/routers/assistant_workspace_folders.py` and remove `SendCollaborativeThreadTurnRequest` / `SendCollaborativeThreadTurnResponse` from `apps/api/src/orcia_api/schemas/assistant_citations_and_folders.py`.
- Regenerate `packages/api-client/openapi.json` and `packages/api-client/src/generated/schema.ts` via `scripts/export_openapi.py` (`0-diff`).
- Remove `sendCollaborativeThreadTurn` from `packages/api-client/src/domains/assistantStreaming.ts`, add `packages/api-client/src/domains/assistantGovernanceAndThreads.ts` (`listAssistantThreadMessages`, `getAssistantGovernance`, `updateAssistantUserPreferences`, `updateAssistantWorkspaceSettings`), and wire it in `packages/api-client/src/index.ts`.
- Remove stale `/threads/{thread_id}/turns` references from `docs/product/capabilities.yaml`.

### 2.4 User Interface & Experience (`packages/ui/`, `apps/web/`)
- **Design System (`packages/ui`)**:
  - Add `AssistantToolCallTrace.tsx` (`tool_call` / `tool_result` steps with duration, status, and optional line inspection) and `AssistantApprovalRequiredCard.tsx` (`approval_required` rationale, human anchor input, Approve/Reject actions, Continue-in-process link), using only Direction C semantic CSS vars from `tokens.css` and typed i18n props.
  - Add `supportsTools?: boolean` and localized notice support to `AssistantSpeedSelectorAndStreamView.tsx`, `AssistantSpeedSelectorTypes.ts`, `AssistantStickyPromptFooter.tsx`, and `AssistantModelAndEffortPopover.tsx` so Speed 2/3 controls disable cleanly when `supports_tools === false`.
  - Add localized **"Deepen"** (`fr`: `"Approfondir"`, `en`: `"Deepen"`) button in `AssistantResponseFooterActionsAndCitations.tsx` (visible when `supportsTools !== false`, highlighted on `lowEvidence === true`), emitting `onDeepen`.
  - Remove Mode B Studio UI trigger and studio view (`AssistantGovernanceStudioModeB`) from `AssistantGovernanceModalAndStudio.tsx` (`R2`, `ACTION_ITEM-26.1`), leaving pure Mode A 3-tab governance.
- **i18n (`apps/web/src/i18n/locales/assistant_labels.ts`)**:
  - Add bilingual (`fr` default, `en`) label dictionaries for `AssistantToolCallTrace`, `AssistantApprovalRequiredCard`, `supports_tools=false` notice, and `"Approfondir"` / `"Deepen"` CTA (removing unused Mode B studio strings or marking Mode A cleanly).
- **Inbox Feature (`apps/web/src/features/inbox/`)**:
  - Hydrate threads and turns from PG18 (`GET /overview` + `GET /threads/{id}/messages`) and reattach running turns via `GET /turns/active` + `GET /turns/{id}/stream?after=<cursor>`.
  - Create server thread (`POST /threads`) prior to `POST /turns` when no active thread exists; omit all `localStorage` `conversation_history` payloads (`thread_id` + optional `parent_turn_id` only).
  - Delete `filterUsedRagSourcesForTurn` and rewrite `inboxCitationHelpers.ts` to build citation cards strictly from server-returned `citation_map` / `citation_guard` payloads (wiring restricted-source access requests to `PermissionBroker` / `[role="alert"]`).
  - Hydrate Mode A governance and `assembledLayers` from `GET /api/v1/assistant/governance`, persist changes via `PUT /governance/mode-a/user` and `PUT /governance/mode-a/workspace`, wire `supportsTools` from `listAiModelMappings` + `turn_completed` SSE events, and surface `[role="alert"]` errors on HTTP `>= 400`.

### 2.5 Test Pyramid Impact (`AD-17`)
- **Layer 1a (Python Unit)**: `tests/unit/test_story_26_9_duplicate_thread_turn_removal.py` confirming `POST /threads/{id}/turns` is deleted (`404`/`405`) while `GET /threads/{id}/messages` & `POST /turns` (`parent_turn_id`) work cleanly; migrate the 6 legacy tests off `POST /threads/{id}/turns`.
- **Layer 1b (TS Unit `Vitest`)**: Real `<RouterProvider>` tests (`apps/web/src/__tests__/story-26-9-inbox-server-history-citations-and-deepen.test.tsx` + `@orcia/ui` primitive tests) covering PG18 history hydration, server-only `citation_map` rendering, `AssistantToolCallTrace`, `AssistantApprovalRequiredCard`, `supports_tools=false` disabled Speed 2/3, `"Deepen"` (`parent_turn_id`), plus `zero-dead-buttons-and-silent-catches-audit.test.tsx` and `e2e-testids-sync-audit.test.ts`.
- **Layer 3 (Contracts)**: `scripts/export_openapi.py --check` (`0-diff`), `pnpm --filter @orcia/api-client test`, `pnpm --filter @orcia/ui typecheck`, `pnpm site:sync && pnpm site:check`.
- **Layer 5 (Playwright Desktop E2E)**: `apps/web/e2e/22-assistant-tool-loop-approval-and-reattach.spec.ts` using `reloadColdFromPg` (`env -u ORCIA_E2E_SEED_FIXTURES`) proving Speed 2 tool loop trace, approval card -> approve -> resume/completion, SSE `?after=` cursor re-attach, PG18 thread history survival across `F5`, and Deepen (`parent_turn_id`).

---

## 3. Change Summary & Verification Results (Bilan des Modifications)

### 3.1 Modified & Created Files (`<= 293` L/file across all non-generated, non-barrel production modules)
- **Backend & Persistence (`packages/orcia-core`, `apps/api`, `packages/api-client`)**:
  - `packages/orcia-core/src/orcia_core/orchestration/_internal/sql_assistant_thread_messages.py` (`235` L): added `_SQL_SYNC_THREAD_TURN_COUNT` atomic turn-count synchronization on `assistant_threads` (`turn_count` increment/sync on `append_message`).
  - `apps/api/src/orcia_api/routers/assistant_workspace_folders.py` (`233` L): deleted duplicate `POST /api/v1/assistant/threads/{thread_id}/turns`.
  - `apps/api/src/orcia_api/schemas/assistant_citations_and_folders.py` (`155` L): deleted unused `SendCollaborativeThreadTurnRequest` & `SendCollaborativeThreadTurnResponse`.
  - `packages/api-client/openapi.json` & `packages/api-client/src/generated/schema.ts`: regenerated (`0-diff` on `export_openapi.py --check`).
  - `packages/api-client/src/domains/assistantGovernanceAndThreads.ts` (`67` L, created), `packages/api-client/src/domains/assistantStreaming.ts` (`232` L), `packages/api-client/src/index.ts` (`215` L): added typed `listAssistantThreadMessages`, `getAssistantGovernance`, `updateAssistantUserPreferences`, `updateAssistantWorkspaceSettings`; removed `sendCollaborativeThreadTurn`.
- **Design System (`packages/ui`)**:
  - Created `AssistantToolCallTrace.tsx` (`150` L), `AssistantApprovalRequiredCard.tsx` (`183` L, incl. anti-password-manager attributes on `<textarea>`), `AssistantAutocompleteDropdown.tsx` (`77` L), `AssistantStickyFooterBadges.tsx` (`186` L, zero `display: none`), `AssistantSpeedSelectorHelpers.tsx` (`227` L), `packages/ui/src/__tests__/story-26-9-assistant-ui-primitives.test.tsx` (`216` L).
  - Updated `AssistantResponseFooterActionsAndCitations.tsx` (`271` L), `AssistantGovernanceModalAndStudio.tsx` (`247` L), `AssistantGovernanceTypes.ts` (`125` L), `AssistantModelAndEffortPopover.tsx` (`251` L), `AssistantStickyPromptFooter.tsx` (`278` L), `AssistantActiveStreamContent.tsx` (`185` L), `AssistantSpeedSelectorAndStreamView.tsx` (`286` L), `AssistantSpeedSelectorTypes.ts` (`119` L), `packages/ui/src/index.ts`, `packages/ui/src/__tests__/assistant-workspace.test.tsx`.
- **SPA Feature, i18n & Tests (`apps/web`)**:
  - Created `useServerAssistantThreads.ts` (`211` L), `useServerAssistantGovernance.ts` (`145` L), `assistantTurnSseProcessor.ts` (`205` L), `assistantTurnControlsHelper.ts` (`126` L), `AssistantTopToolbar.tsx` (`89` L), `apps/web/src/i18n/locales/assistant_labels_en.ts` (`134` L), `apps/web/src/__tests__/setup/assistantGovernanceMockHandlers.ts` (`140` L), `apps/web/src/__tests__/story-26-9-inbox-server-history-citations-and-deepen.test.tsx` (`189` L), `apps/web/e2e/22-assistant-tool-loop-approval-and-reattach.spec.ts` (`188` L).
  - Updated `apps/web/src/i18n/locales/assistant_labels.ts` (`183` L), `useActiveEmbeddingModelStatus.ts` (`61` L), `assistantAutocompleteHelpers.ts` (`227` L, deleted `filterUsedRagSourcesForTurn`), `inboxCitationHelpers.ts` (`212` L, strict server `citation_map` parser), `assistantTurnPayloadHelper.ts` (`276` L, omitted `conversation_history`), `assistantBackgroundStreamStore.ts` (`292` L), `assistantStreamingRunner.ts` (`157` L), `useAssistantStreamingTurn.ts` (`289` L), `savedConversationsStore.ts` (`201` L), `inboxTurnSyncHelpers.ts` (`131` L), `useInboxPanelController.ts` (`269` L), `InboxActiveTraceAndTurns.tsx` (`259` L), `InboxAuxiliaryPanels.tsx` (`196` L), `SavedConversationsAndThreadView.tsx` (`239` L), `apps/web/src/features/inbox/index.tsx` (`293` L), `mockBackendState.ts`, `assistantAndInboxMockHandlers.ts` (`268` L), `story-23-5-sobriety-and-citations-wiring.test.tsx`.
- **Migrated & Added Backend Tests (`tests/`)**:
  - Created `tests/unit/test_story_26_9_duplicate_thread_turn_removal.py` (`101` L).
  - Updated `tests/unit/test_e2e_sql_coverage_audit.py` (registered `22-assistant-tool-loop-approval-and-reattach.spec.ts` & PG18 tables `assistant_threads` / `assistant_thread_messages`, counts `25` specs / `57` blocks).
  - Migrated `test_epic_10_story_10_4_folders_and_sharing.py`, `test_assistant_and_rag_routes_require_rag_guard_audit.py`, `test_story_25_5_assistant_without_embedding_and_datasource_guard.py`, `test_story_26_1_assistant_security_hardening.py`, `test_story_26_4a_redis_locks_outbox_ddl_postgres18.py`, `test_story_26_4b_pg18_threads_and_sharing.py`.

### 3.2 Independent Testing Sub-Agent Verification (`AD-17` 5 Layers — 100% GREEN)
- **Static, Contract, Security & Hygiene Gates**:
  - Max touched non-generated, non-barrel production file line count: `293` lines (`apps/web/src/features/inbox/index.tsx`; `sql_assistant_thread_messages.py` `235` L; all `40` production modules `<= 300` L).
  - `.venv/bin/ruff check .`: PASSED (`All checks passed!`).
  - `.venv/bin/ruff format --check .`: PASSED (`1547 files already formatted`).
  - `.venv/bin/mypy --strict packages/orcia-core packages/orcia-connectors apps/api apps/worker`: PASSED (`Success: no issues found in 720 source files`).
  - `.venv/bin/lint-imports`: PASSED (`5 kept, 0 broken`, `762` files / `5593` dependencies).
  - `lint_spine.py`: PASSED (`0` findings).
  - `scripts/export_openapi.py --check`: PASSED (`0-diff`).
  - `detect-secrets-hook --baseline .secrets.baseline`: PASSED (`exit 0`).
  - Hygiene checks: empty `git diff --stat -- docs/implementation-artifacts/e2e-campaign-epic-*`; zero `/threads/{thread_id}/turns` across `apps/`, `packages/`, and `capabilities.yaml`; zero `filterUsedRagSourcesForTurn` in source/tests; `#6D28D9` strictly isolated to `packages/ui/src/styles/tokens-palette.css` and `css-class-integrity-audit.test.ts`.
- **Layer 1 / 3 / 4 / Security Python Suites (`--no-cov`) & `>= 90%` Branch Coverage**:
  - Pure `tests/unit` (3 chunks, `142` files): `361 + 353 + 228 = 942 passed`.
  - Unit subdirectories (`connectors`, `core`, `infra`, `packs`): `55 passed`.
  - Standalone `test_story_7_0c_openshift_scc_kustomize_and_ready.py`: `5 passed`.
  - Standalone `test_epic_11_story_11_2_dna_starlark_and_glossary.py`: `4 passed`.
  - `tests/evals` + `tests/security` + `tests/contract`: `158 passed`.
  - PG18 unit `testcontainers` (`3_2e`, `3_4`, `3_5`, `4_1`, `4_4`, `5_1`, `--no-cov`): `25 passed`.
  - **Total Python Non-Integration Suites**: `1189 passed`.
  - **Story 26.9 Branch Coverage (`.venv/bin/coverage run --branch` + `--no-cov`, `52 passed` across `11` non-container suites, `.coverage*` & `/tmp/.cov_*` cleaned)**:
    - `assistant_workspace_folders.py`: `90%` (`52 Stmts, 3 Miss, 6 Branch, 1 BrPart`, missing `47-49`).
    - `assistant_citations_and_folders.py`: `100%` (`89 Stmts, 0 Miss`).
    - `sql_assistant_thread_messages.py`: `98%` (`70 Stmts, 0 Miss, 14 Branch, 2 BrPart`, partial `88->92, 120->122`).
    - **Combined Total**: `97%` (`211 Stmts, 3 Miss, 20 Branch, 3 BrPart` — `>= 90%` PASSED).
- **Layer 2 PG18 + Redis Integration Suites (`--no-cov`)**:
  - Batch A (`test_story_26_*.py`, `12` files): `15 passed` (`206.79s`).
  - Batch B (`25_5`, `16_2`, `20_4`, `23_5`, `22_1`, `22_3`, `23_2`, `7` files): `9 passed` (`107.24s`).
  - Batch C (`10_1`, `10_2`, `10_3`, `10_4`, `4` files): `4 passed` (`35.18s`).
  - **Total PG18 + Redis Integration**: `28 passed`.
- **Solo TypeScript / Vitest (`pnpm turbo run lint typecheck test --force --concurrency=1`)**:
  - `Tasks: 9 successful, 9 total` (`1m33.338s`):
  - `@orcia/api-client`: `3 test files / 21 passed` + lint + typecheck.
  - `@orcia/ui`: `35 test files / 154 passed` + lint + typecheck.
  - `@orcia/web`: `68 test files / 264 passed` + lint + typecheck (including `story-26-9-inbox-server-history-citations-and-deepen.test.tsx`, `story-23-5-sobriety-and-citations-wiring.test.tsx`, `zero-dead-buttons-and-silent-catches-audit.test.tsx`, `e2e-testids-sync-audit.test.ts`, `i18n-and-shell.test.tsx`, `no-hidden-legacy-panels-audit.test.ts`).
- **Layer 5 Playwright Desktop E2E (`env -u ORCIA_E2E_SEED_FIXTURES`, `--project=desktop-cockpit`)**:
  - Specs `00`, `02`, `12-finops`, `12-epic16`, `16`, `21`, `22`: `16 passed, 1 mobile-only skipped (in 12-finops), 0 failed (2.8m)`.
- **Closure Status**:
  - Story `26-9-ui-and-sdk-wiring-mode-a-citations-history-and-deepen` marked `done` in `docs/implementation-artifacts/sprint-status.yaml`, registered in `docs/implementation-artifacts/tech-lead-reports/README.md`, synchronized with `pnpm site:sync && pnpm site:check`, verified with `scripts/check_implementation_docs.py`, and indexed cleanly via `npx gitnexus analyze --index-only .`.
