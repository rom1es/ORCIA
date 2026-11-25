# Story 30.1 — Mon Assistant Settings Explicit Save, Honest Dirty Guard, Inline Modal Errors & Empty Personal Instructions

- **Date**: 2026-11-25
- **Story / Sprint Key**: `30-1-assistant-settings-explicit-save-dirty-guard-and-empty-instructions` (`Epic 30`, Lot 1)
- **Capability(ies)**: `CAP-070`, `CAP-100` — classification: `feature` + `ux` (updates existing `CAP-070` Mode A governance UX and `CAP-100` RGAA modal & zero-dead-button quality guardrails)
- **Author / Context**: `bmad-dev-worker` / Tech Lead Implementation (`UX30-01`, `UX30-02`, `UX30-03`, `FR-33`, `AD-15`, `AD-17`, `AD-22`, `EXPERIENCE.md` §1.1 #4–#5, `DESIGN.md` §UI Rules #4–#5)
- **Associated Commits**: Pending commit on branch `consignes_personnelles_save_button` (Testing Sub-Agent verified, `status: done`)

---

## 1. Needs Analysis & Tech Lead Impact Study (Pre-Implementation)

### 1.1 Context & Problem Statement
- **Observed defects (`UX30-01`, `UX30-02`, `UX30-03`)**:
  1. **Broken auto-save + hidden Save hybrid (`UX30-01`)**: `AssistantGovernanceModalAndStudio.tsx` calls `setIsDirty(true)` and triggers an un-debounced `triggerAutoSave*` on every keystroke/selection change, while `isDirty` is only cleared by hidden `display: none` Save buttons in `AssistantGovernanceModeATabs.tsx`. Consequently, clicking `"Annuler"` after seeing `"✓ Enregistré"` triggers `"Modifications non enregistrées"`, and `"Quitter sans enregistrer"` only resets local React state without reverting already-committed PostgreSQL 18 `PUT` calls.
  2. **Optimistic feedback lies, mid-typing cursor overwrite & off-modal alerts (`UX30-02`)**: `triggerAutoSave*` synchronously sets `autosavedBadgeVisible(true)` before invoking fire-and-forget `void onSave*` in `InboxAuxiliaryPanels.tsx`. On `PUT` completion, `useServerAssistantGovernance.ts` calls `refreshGovernance()`, updating `initial*` props mid-typing via `useEffect`, overwriting user input. On `4xx`/`5xx`/network failure, errors route to `InboxTopSection` behind the dimmed modal backdrop while `"✓ Enregistré"` still displays.
  3. **Forced `[S1]` boilerplate, `min_length=3` lock, hidden DOM duplicates & select clipping (`UX30-03`)**: `_assistant_locales.py`, `assistant_governance_models.py`, and `assistantFoldersAndPrefsStore.ts` pre-fill `personal_instructions` with a default `[S1]` instruction, and `UpdateUserLayerPreferencesRequest.personal_instructions` enforces `min_length=3`, preventing users from clearing personal instructions. `AssistantGovernanceModeATabs.tsx` also mounts 4 hidden Save buttons and 3 hidden duplicate `<select>` nodes (forcing `.evaluate()` in E2E spec `22-assistant-tool-loop-approval-and-reattach.spec.ts`), and the 3-column select grid clips `"Équilibré & Structuré (Recommandé)"`.
- **Target behavior**:
  - Eliminate all auto-save calls on `onChange*` in `AssistantGovernanceModalAndStudio`; track `isUserDirty` and `isWorkspaceDirty` strictly by comparing Tab 1 and Tab 2 drafts against hydrated baselines; sync drafts from `initial*` props only when `!isDirty && !isSaving`.
  - Render an explicit bottom-right `<RgaaDialogFooterActions />` (`Annuler`/`Fermer` on `assistant-gov-cancel-btn` + primary Cobalt `Enregistrer` on `assistant-save-user-prefs-btn`) with `<OrciaSpinner />` during async save and `<Enter>` submit support via `handleRgaaSubmitKeyDown`.
  - Make `onSaveUserPreferences` and `onSaveWorkspaceSettings` return `Promise<boolean>` end-to-end; show `"✓ Enregistré"` and reset `isDirty = false` only after PG18 `PUT` + `refreshGovernance()` succeed, keep the modal open so Tab 3 refreshes and `Fermer`/`Escape` closes cleanly, and render localized `[role="alert"]` errors inline inside the modal body on failure without clearing `isDirty`.
  - Set default `personal_instructions` to `""` across backend (`_assistant_locales.py`, `assistant_governance_models.py`) and frontend (`DEFAULT_ASSISTANT_GOVERNANCE_PREFS`), relax `UpdateUserLayerPreferencesRequest.personal_instructions` to `Field(default="", min_length=0, max_length=4000)`, regenerate the `0-diff` OpenAPI SDK, remove all 4 hidden Save buttons and 3 hidden `<select>` duplicates, widen the modal/select grid, and replace the `.evaluate()` E2E click workaround with a real button click.

### 1.2 Exploration, GitNexus Impact Analysis, Refactoring & Technical Debt
- **GitNexus Impact Analysis (`repo: "/home/romain/Documents/Projects/ORCIA"`)**:
  - `gitnexus_query({search_query: "AssistantGovernanceModalAndStudio onSaveUserPreferences personal_instructions"})` identified `UserLayerPreferences`, `UpdateUserLayerPreferencesRequest`, `AssistantGovernanceModalAndStudioProps.onSaveUserPreferences`, and `_sql_assistant_governance_queries.py`.
  - `gitnexus_context({name: "UserLayerPreferences"})` confirmed direct usage in `_sql_assistant_governance_queries.py` (`manifest_to_user_prefs` already defaults missing `personal_instructions` to `""`) and `assistant_governance_studio.py` (`build_default_user_preferences`, `build_updated_user_preferences_override`).
  - `gitnexus_impact({target: "UpdateUserLayerPreferencesRequest", direction: "upstream"})` + static worktree `grep` across `packages/`, `apps/`, and `tests/` confirmed upstream callers:
    - Backend: `apps/api/src/orcia_api/routers/assistant_workspace_governance.py` (`update_user_layer_preferences_endpoint`), `packages/api-client/src/domains/assistantGovernanceAndThreads.ts`, `tests/unit/test_epic_10_story_10_1_assistant_governance.py`.
    - Frontend & UI: `apps/web/src/features/inbox/InboxAuxiliaryPanels.tsx`, `apps/web/src/features/inbox/index.tsx`, `apps/web/src/features/inbox/useServerAssistantGovernance.ts`, `packages/ui/src/__tests__/assistant-workspace.test.tsx`, `packages/ui/src/__tests__/rgaa-modals-escape-unsaved-guard.test.tsx`, `apps/web/src/__tests__/story-26-9-inbox-server-history-citations-and-deepen.test.tsx`, and `apps/web/e2e/22-assistant-tool-loop-approval-and-reattach.spec.ts`.
  - `assistant_governance_studio.py:L102` passes `personal_instructions` through `sanitize_layer_marker_tags()`, which preserves `""` cleanly without raising errors; `assistant_prompt_preview.py:L118-L120` omits the personal-instructions line when empty.
- **Refactoring Opportunities & File-Size Control (`<= 300` lines)**:
  - `AssistantGovernanceModalAndStudio.tsx` (`245` L) and `AssistantGovernanceModeATabs.tsx` (`288` L) are near the `300`-line cap; removing the 4 hidden Save buttons and 3 hidden `<select>` nodes reduces `AssistantGovernanceModeATabs.tsx`, while extending `RgaaDialogFooterActions` (`packages/ui/src/components/RgaaModalDialog.tsx`, `278` L) with optional `cancelTestId`, `submitTestId`, and `isSubmitting` avoids duplicating footer markup inside `AssistantGovernanceModalAndStudio.tsx`.
  - If `AssistantGovernanceModalAndStudio.tsx` approaches `300` lines after adding dirty-diff computation, async submit handling, and inline error banner, extract pure baseline-diff / payload helpers to a dedicated `AssistantGovernanceTypes.ts` or helper module.
  - Keep `UpdateWorkspaceLayerSettingsRequest.workspace_instructions` untouched (`min_length=3`) to respect `Story 30.1` scope and preserve existing `assistantGovernanceMockHandlers.ts` validation tests.

---

## 2. Implementation Plan

### 2.1 Data Schema & Alembic Migrations
- None required (`workspace_customization_overrides.override_manifest_jsonb` already stores arbitrary JSONB strings including `""`).

### 2.2 Hexagonal Core, Orchestration & Workers (`packages/orcia-core/`)
- `packages/orcia-core/src/orcia_core/orchestration/_assistant_locales.py`:
  - Change `"user_default_instructions"` in both `"fr"` and `"en"` bundles to `""`.
- `packages/orcia-core/src/orcia_core/orchestration/assistant_governance_models.py`:
  - `UserLayerPreferences.personal_instructions` automatically defaults to `""` via `_FLOC_FR["user_default_instructions"]`.
- `packages/orcia-core/src/orcia_core/orchestration/_internal/sql_assistant_governance.py` & `_sql_assistant_governance_queries.py`:
  - Verify `manifest_to_user_prefs` and `build_default_user_preferences` cleanly persist and rehydrate `""` without falling back to non-empty boilerplate.

### 2.3 Backend API, Security & Contracts (`apps/api/`, `packages/api-client/`)
- `apps/api/src/orcia_api/schemas/assistant_governance_and_three_speed.py`:
  - Update `UpdateUserLayerPreferencesRequest.personal_instructions` to `Field(default="", min_length=0, max_length=4000)`.
- `packages/api-client/`:
  - Run `.venv/bin/python scripts/export_openapi.py` and verify `--check` (`0-diff`).

### 2.4 User Interface & Experience (`apps/web/`, `packages/ui/`)
- `packages/ui/src/components/RgaaModalDialog.tsx`:
  - Extend `RgaaDialogFooterActionsProps` with optional `cancelTestId`, `submitTestId`, and `isSubmitting` (rendering `<OrciaSpinner size="xs" />` alongside `submitLabel` when saving) while keeping all files `<= 300` lines.
- `packages/ui/src/styles/tokens-overlays.css`:
  - Slightly widen `.orcia-ds-dialog-content-wide` (or adjust grid/min-width in `AssistantGovernanceModeATabs.tsx` using responsive columns) so `"Équilibré & Structuré (Recommandé)"` renders without clipping.
- `packages/ui/src/primitives/AssistantGovernanceTypes.ts`, `AssistantGovernanceModeATabs.tsx`, and `AssistantGovernanceModalAndStudio.tsx`:
  - Add typed optional/required i18n labels (`saveChangesCta`, `savingChangesLabel`, `unsavedAssemblyNote`, `saveErrorFallback`) with symmetric FR/EN entries in `apps/web/src/i18n/locales/assistant_stream_labels_{fr,en}.ts` (zero hardcoded UI strings or raw hex colors in `@orcia/ui`).
  - Remove `triggerAutoSaveUserPrefs` / `triggerAutoSaveWorkspace`, all 4 hidden `display: none` Save buttons, and all 3 hidden duplicate `<select>` elements.
  - Compute `isUserDirty` and `isWorkspaceDirty` against hydrated baselines (`isDirty = isUserDirty || isWorkspaceDirty`), sync drafts from `initial*` only when `!isDirty && !isSaving`, and clear `autosavedBadgeVisible` and inline `saveError` on any new edit.
  - Render `<OrciaAlertBanner tone="crimson" testId="assistant-gov-error-banner">` inline inside the modal on failed save, show a non-blocking note in Tab 3 when `isDirty === true`, and render `<RgaaDialogFooterActions />` (`testIdPrefix="assistant-gov"`, `submitTestId="assistant-save-user-prefs-btn"`) at the bottom-right with `"Annuler"`/`"Cancel"` when `isDirty` or `"Fermer"`/`"Close"` when clean, disabled primary Cobalt Save button when `!isDirty || isSaving`, `<OrciaSpinner />` when saving, and `<Enter>` submit support.
- `apps/web/src/features/inbox/assistantFoldersAndPrefsStore.ts`, `useServerAssistantGovernance.ts`, `useInboxPanelController.ts`, `InboxAuxiliaryPanels.tsx`:
  - Default `DEFAULT_ASSISTANT_GOVERNANCE_PREFS.personalInstructions` to `""`.
  - Return `Promise<boolean>` (or `{ ok: boolean; errorMessage?: string }`, bridged cleanly into modal `saveError` + `onSave*(): Promise<boolean>`) from `saveUserPreferences` and `saveWorkspaceSettings` without routing modal save errors exclusively behind the backdrop, and await both in `InboxAuxiliaryPanels.tsx`.

### 2.5 Test Pyramid Impact Analysis (`AD-17`)
- **Layer 1a (Python Unit `tests/unit/`)**: Add `tests/unit/test_story_30_1_assistant_settings_empty_instructions.py` verifying empty default `personal_instructions == ""`, `UpdateUserLayerPreferencesRequest` accepting `""` (`min_length=0`), `max_length=4000`, and `AssistantFourLevelGovernanceService` round-trip with empty instructions.
- **Layer 1b (TS/React Unit/Component `Vitest`)**: Update `packages/ui/src/__tests__/rgaa-modals-escape-unsaved-guard.test.tsx`, `packages/ui/src/__tests__/assistant-workspace.test.tsx`, and `apps/web/src/__tests__/story-26-9-inbox-server-history-citations-and-deepen.test.tsx`; add assertions for zero auto-save on typing, explicit Save awaiting Promise, inline `[role="alert"]` error without `"✓ Enregistré"`, clean `Fermer`/`Escape` after Save vs dirty alert before Save, and empty `personalInstructions` persistence. Verify `e2e-testids-sync-audit.test.ts` and `i18n-dictionary-parity-and-jargon-audit.test.ts`.
- **Layer 3 (OpenAPI 3.1 `0-diff`)**: Verify `scripts/export_openapi.py --check`.
- **Layer 5 (Playwright E2E selector update)**: Update `apps/web/e2e/22-assistant-tool-loop-approval-and-reattach.spec.ts` to click the visible Save button instead of `.evaluate((el) => el.click())`.

---

## 3. Summary of Changes & Results (Post-Implementation)

### 3.1 Created & Modified Files

| Status | File | Lines | Role / Key Change |
| :--- | :--- | :---: | :--- |
| Modified | `packages/orcia-core/src/orcia_core/orchestration/_assistant_locales.py` | 238 | Set default `user_default_instructions` to `""` in both `fr` and `en` bundles (`UX30-03`). |
| Modified | `packages/orcia-core/src/orcia_core/orchestration/_internal/_sql_assistant_governance_queries.py` | 274 | Preserved empty `personal_instructions: ""` during PG18 manifest serialization & rehydration. |
| Modified | `apps/api/src/orcia_api/schemas/assistant_governance_and_three_speed.py` | 256 | Relaxed `UpdateUserLayerPreferencesRequest.personal_instructions` to `Field(default="", min_length=0, max_length=4000)`. |
| Modified | `packages/api-client/openapi.json` & `packages/api-client/src/generated/schema.ts` | 71150 / 7320 | Regenerated OpenAPI 3.1 schema (`0-diff` check passing). |
| Modified | `packages/ui/src/components/RgaaModalDialog.tsx` | 287 | Extended `RgaaDialogFooterActionsProps` with `cancelTestId`, `submitTestId`, `submitDisabled`, and `isSubmitting` (`<OrciaSpinner size="xs" />`). |
| Modified | `packages/ui/src/primitives/AssistantGovernanceTypes.ts` | 152 | Added async `Promise<boolean>` save callbacks, `saveError`, `onClearSaveError`, and bilingual save/error/dirty-note label fields. |
| Created | `packages/ui/src/primitives/useAssistantGovernanceModalState.ts` | 240 | Extracted baseline-diff dirty tracking (`isUserDirty`, `isWorkspaceDirty`), guarded hydration (`!isDirty && !isSaving`), and async save state machine. |
| Modified | `packages/ui/src/primitives/AssistantGovernanceModalAndStudio.tsx` | 195 | Eliminated all auto-save triggers, added inline `<OrciaAlertBanner tone="crimson">` error display, `<RgaaDialogFooterActions />` (`Annuler`/`Fermer` + Cobalt `Enregistrer`), and `<Enter>` submit handler. |
| Modified | `packages/ui/src/primitives/AssistantGovernanceModeATabs.tsx` | 251 | Removed all 4 hidden `display: none` Save buttons & 3 hidden duplicate `<select>` DOM nodes; added non-blocking Tab 3 unsaved note (`UX30-03`). |
| Modified | `packages/ui/src/styles/tokens-overlays.css` | 198 | Widened `.orcia-ds-dialog-content-wide` and governance select layout to eliminate option label clipping. |
| Modified | `apps/web/src/features/inbox/assistantFoldersAndPrefsStore.ts` | 174 | Set `DEFAULT_ASSISTANT_GOVERNANCE_PREFS.personalInstructions` to `""`. |
| Modified | `apps/web/src/features/inbox/useServerAssistantGovernance.ts` | 160 | Made `saveUserPreferences` / `saveWorkspaceSettings` return `Promise<boolean>`, route modal errors to `governanceModalError` (`[role="alert"]`), and await `refreshGovernance()`. |
| Modified | `apps/web/src/features/inbox/InboxAuxiliaryPanels.tsx` & `apps/web/src/features/inbox/index.tsx` | 193 / 291 | Wired `governanceModalError`, `onClearGovernanceModalError`, and awaited `Promise<boolean>` save handlers without silent catch swallowing. |
| Modified | `apps/web/src/i18n/locales/assistant_stream_labels_{fr,en}.ts` | 173 / 172 | Added symmetric FR/EN `saveChangesCta`, `savingChangesLabel`, `unsavedAssemblyNote`, and `saveErrorFallback` keys. |
| Created | `tests/unit/test_story_30_1_assistant_settings_empty_instructions.py` | 113 | Unit tests for empty `personal_instructions` defaults, schema `min_length=0` / `max_length=4000`, and governance round-trip. |
| Created | `apps/web/src/__tests__/story-30-1-assistant-settings-explicit-save.test.tsx` | 139 | Integration tests verifying zero auto-save on typing, explicit `Save` awaiting `PUT`, inline modal errors, honest dirty guard, and empty instructions `F5` persistence. |
| Modified | `packages/ui/src/__tests__/assistant-workspace.test.tsx`, `assistantLabelsFixture.ts`, `rgaa-modals-escape-unsaved-guard.test.tsx` | 1442 / 263 / 601 | Updated `@orcia/ui` modal & RGAA dirty-guard assertions for explicit Save semantics. |
| Modified | `apps/web/src/__tests__/setup/mockBackendState.ts` & `story-26-9-inbox-server-history-citations-and-deepen.test.tsx` | 363 / 192 | Updated default empty `personal_instructions` in mock state and Story 26.9 explicit Save assertions. |
| Modified | `apps/web/e2e/22-assistant-tool-loop-approval-and-reattach.spec.ts` | 206 | Replaced `.evaluate()` click workaround on hidden Save button with real visible click on `assistant-save-user-prefs-btn`. |

All modified/created production source files respect the `<= 300`-line limit (`max = 291` lines in `apps/web/src/features/inbox/index.tsx`).

### 3.2 Quantitative Metrics & Coverage (`>= 90%`)

- **Targeted Python Branch Coverage (Story 30.1 modules)**: **`100%`** (`237` statements, `0` missed, `24` branches, `0` partial branches across `assistant_governance_and_three_speed.py` `100%`, `_assistant_locales.py` `100%`, `_sql_assistant_governance_queries.py` `100%` — `17 passed` in `36.67s`).
- **Full Non-Integration Python Suite**:
  - `tests/unit`: **`1127 passed`** (`336.67s`, `--no-cov`).
  - `tests/evals`, `tests/security`, `tests/contract`: **`181 passed`** (`111.41s`, `--no-cov`).
- **Impacted PG18 + Redis `testcontainers` Integration Tests (`--no-cov`)**:
  - `tests/integration/test_story_10_1_assistant_overrides_postgres18.py` + `tests/integration/api/test_story_26_4b_pg18_persistence_governance_feedback_folders.py`: **`2 passed`** (`35.85s`).
- **TypeScript / React Monorepo (`pnpm turbo run lint typecheck test --concurrency=2`)**: **`9/9` tasks successful** (`1m23.759s`):
  - `@orcia/api-client`: `lint`, `typecheck`, `test` passed.
  - `@orcia/ui`: **`38` test files, `149` tests passed**.
  - `@orcia/web`: **`91` test files, `356` tests passed** (including `story-30-1-assistant-settings-explicit-save.test.tsx`, `i18n-hardcoded-locale-ast-audit.test.ts`, `i18n-dictionary-parity-and-jargon-audit.test.ts`, `client-error-code-contract-audit.test.ts`, `e2e-testids-sync-audit.test.ts`, `zero-dead-buttons-and-silent-catches-audit.test.tsx`).

### 3.3 AD-17 5-Layer & Architecture Gate Verification

| Gate / Layer | Command | Result |
| :--- | :--- | :--- |
| Static Lint (`ruff`) | `.venv/bin/ruff check .` & `.venv/bin/ruff format --check .` | **PASS** (`0` errors, `1749` files formatted) |
| Strict Typing (`mypy`) | `.venv/bin/mypy --strict packages/orcia-core packages/orcia-connectors apps/api apps/worker` | **PASS** (`856` source files, `0` issues) |
| Modular Boundaries (`AD-19`) | `.venv/bin/lint-imports` | **PASS** (`Contracts: 5 kept, 0 broken` across `899` files / `6486` deps) |
| Spine Integrity | `lint_spine.py --workspace docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24` | **PASS** (`total_findings: 0`) |
| Layer 3 OpenAPI 3.1 Contract | `.venv/bin/python scripts/export_openapi.py --check` | **PASS** (`0-diff`) |
| Layer 1a/1b/3/4 Python | `.venv/bin/pytest --no-cov tests/unit tests/evals tests/security tests/contract` | **PASS** (`1127 + 181 = 1308 passed`) |
| Layer 2 PG18 + Redis | `.venv/bin/pytest --no-cov tests/integration/...` | **PASS** (`2 passed`) |
| Layer 1b JS/TS (`Turbo`) | `pnpm turbo run lint typecheck test --concurrency=2` | **PASS** (`9/9` tasks; `@orcia/ui` `149` + `@orcia/web` `356`) |
| Layer 5 Desktop Playwright E2E | `env -u ORCIA_E2E_SEED_FIXTURES pnpm --filter @orcia/web exec playwright test --project=desktop-cockpit e2e/02-assistant-streaming-and-folders.spec.ts e2e/22-assistant-tool-loop-approval-and-reattach.spec.ts` | **PASS** (`4 passed` in `1.4m` on real PG18 + Redis without fixtures) |

### 3.4 GitNexus Impact Verification (`gitnexus_detect_changes`)

- Index refreshed via `npx gitnexus analyze --index-only .` (`46,384 nodes | 79,690 edges | 773 clusters | 1532 flows`).
- `gitnexus_detect_changes({ repo: "/home/romain/.gemini/antigravity/worktrees/ORCIA/consignes_personnelles_save_button", scope: "all", worktree: "/home/romain/.gemini/antigravity/worktrees/ORCIA/consignes_personnelles_save_button" })`:
  - `changed_count`: `54` symbols across `26` changed files (`risk_level: "medium"`).
  - `affected_count`: `1` cross-community execution flow (`proc_69_invoke_mcp_assistant`: `Invoke_mcp_assistant_ask_async -> Manifest_to_user_prefs`, step 5 `manifest_to_user_prefs`).
