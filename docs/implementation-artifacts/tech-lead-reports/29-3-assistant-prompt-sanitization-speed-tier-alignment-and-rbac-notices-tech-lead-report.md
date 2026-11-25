# Story 29.3 — `Mon Assistant` Prompt & Jargon Sanitization, Speed/Tier Alignment & RBAC-Gated Composer Notices (`UH-05`)

- **Date**: 2026-11-25
- **Story / Sprint Key**: `29-3-assistant-prompt-sanitization-speed-tier-alignment-and-rbac-notices` (`Epic 29`, Lot 1)
- **Capability(ies)**: `CAP-070`, `CAP-071`, `CAP-075`, `CAP-190` — classification: `feature | ux | security` (existing capabilities updated; no new route/endpoint added)
- **Author / Context**: `UH-05` (`AD-15`, `AD-21`, `EXPERIENCE.md` §1.2 #1) — eliminate raw UUIDv7 / internal enum (`SPEED_1_FAST`) / hardcoded `"PM"` / phantom `orcia://sources/repo-main` & `@spec-architect` prompt leaks, align speed/tier/effort metadata across composer and response footer, and gate admin-only AI model configuration links in composer notices by RBAC while collapsing stacked notices into a compact status bar.
- **Associated Commits**: `pending`

---

## 1. Needs Analysis & Tech Lead Impact Study (Pre-Implementation)

### 1.1 Context & Problem Statement
- **Current defects (`UH-05`)**:
  1. **Prompt & metadata plumbing leaks**:
     - `packages/orcia-core/src/orcia_core/orchestration/assistant_prompt_preview.py` (`build_five_layers_preview_items`, `format_system_instructions_text`) injects raw `[WORKSPACE: {workspace_id}]` and `[USER: {user_id}]` UUIDs, unlocalized `speed_mode` enum strings (`SPEED_1_FAST`), and raw `default_checked_sources` / `recommended_agents` even when empty.
     - `packages/orcia-core/src/orcia_core/orchestration/assistant_governance_models.py` (`UserLayerPreferences`, `WorkspaceLayerSettings`) hardcodes `default_hat = "PM"`, `default_checked_sources = ("orcia://sources/repo-main", ...)`, and `recommended_agents = ("@spec-architect", "@security-reviewer")`.
     - `packages/orcia-core/src/orcia_core/orchestration/assistant_prompt_builder.py` and `_assistant_locales.py` interpolate raw `workspace_id` UUIDs into fanout/scope strings (`empty_fanout_tpl`, `cadrage_summary`, `scope_note`).
     - `apps/web/src/features/inbox/assistantFoldersAndPrefsStore.ts` and `useAssistantStreamingTurn.ts` fall back to `"PM"` instead of the authenticated user's real active role/hat (`authSessionStore.activeHat` / `UserIdentity`).
  2. **Speed / tier / effort metadata contradiction**:
     - `packages/ui/src/primitives/AssistantSpeedSelectorAndStreamView.tsx` and `AssistantSpeedSelectorHelpers.tsx` initialize `speed` to `"SPEED_1_FAST"` while simultaneously initializing `effort` to `"balanced"` (`title: "Standard"` mapped to `SPEED_2_AGENT_TOOLS`) and `tier` to `"medium"` (`Polyvalent` / `Versatile`). When `hideLegacySpeedPills={true}` (`Mon Assistant`), the UI displays `Polyvalent · Standard` while dispatching `requestedSpeed = "SPEED_1_FAST"`.
     - Furthermore, `assistant_stream_labels_{fr,en}.ts` duplicates `"Standard"` as the title for both `effort: "fast"` (`SPEED_1_FAST`) and `effort: "balanced"` (`SPEED_2_AGENT_TOOLS`), and `savedConversationsStore.ts` / `useAssistantStreamingTurn.ts` collapse `"fast"` into `"balanced"` (`Standard`), causing a mismatch when `!supportsTools` forces `SPEED_1_FAST`.
  3. **RBAC-broken & stacked composer notices**:
     - `apps/web/src/features/inbox/InboxDisabledBanner.tsx`, `AssistantNoEmbeddingBanner.tsx`, and `AssistantReindexingBanner.tsx` unconditionally render clickable `<a href="/settings/ai-models">` links (`Configurer dans Administration › Modèles IA →`) even for non-`PLATFORM_ADMIN` users (`TEAM_LEAD`, `CONTRIBUTOR`, `OBSERVER`) who receive HTTP 403 / empty tabs on `/settings/ai-models`.
     - `AssistantStickyPromptFooter.tsx` stacks `disabledReasonBanner` and `<AssistantToolsUnsupportedNotice />` vertically with multi-line blocks, eating vertical chat height.
- **Expected behavior**:
  - Human-readable workspace names (or localized global/active space labels, never raw UUIDv7), localized speed/hat labels (never `SPEED_1_FAST`), real user role/hat (never hardcoded `"PM"`), and strictly genuinely attached sources (omitting unattached defaults) across both `fr` and `en`.
  - Single coherent speed/tier/effort vocabulary across composer selector, dispatched payload, and response footer details popover in `fr` and `en`.
  - Non-`PLATFORM_ADMIN` users see plain administrator-contact guidance without clickable admin links, and informational composer notices collapse into a single compact non-stacked status line.

### 1.2 Exploration, GitNexus Impact Analysis, Refactoring & Technical Debt
- **GitNexus Impact Analysis (`repo: "ORCIA"`)**:
  - `gitnexus_query` traced cross-community flows on `assistant_prompt_builder`, `assistant_governance_and_three_speed`, and `contextual_help_resolver` (index noted 5 commits behind `HEAD`; static grep verified exact upstream callers across `packages/orcia-core`, `apps/api`, `packages/ui`, and `apps/web`).
  - Verified callers of `build_five_layers_preview_items` / `format_system_instructions_text`: `assistant_prompt_builder.py`, `assistant_governance.py`, `_assistant_governance_sync.py`, `assistant_governance_layers.py`, `_assistant_turn_engine_plan.py`, `assistant_llm_prompts.py`.
  - Verified callers of `InboxDisabledBanner`, `AssistantNoEmbeddingBanner`, `AssistantSpeedSelectorAndStreamView`, `AssistantStickyPromptFooter`: `apps/web/src/features/inbox/index.tsx`, `Story 19.6`, `Story 25.5`, `Story 26.9`, `assistant-workspace.test.tsx`, `e2e/02` and `e2e/16`.
- **Refactoring Opportunities & File Line-Count Control (`<= 300` lines)**:
  - `AssistantSpeedSelectorAndStreamView.tsx` is `299` lines and `apps/web/src/features/inbox/index.tsx` is `295` lines; speed/effort alignment logic will live in `AssistantSpeedSelectorHelpers.tsx` (`229` L) and `useInboxPanelController.ts` (`286` L) to keep all touched files `<= 300` lines.
  - Extract pure sanitization helpers (`resolve_human_workspace_label`, `resolve_human_user_label`, `resolve_human_hat_label`, `resolve_human_speed_label`) in `assistant_prompt_preview.py` (`211` L) and reuse across `assistant_prompt_builder.py`, `assistant_governance.py`, and `_assistant_context_assembly.py`.
  - Reuse existing `isPlatformAdministratorSession` in `apps/web/src/stores/settingsRbacResolver.ts` (`AD-21` single RBAC source of truth).

---

## 2. Implementation Plan

### 2.1 Data Schema & Alembic Migrations
- None required. Existing `workspaces.name`, `users.display_name`, `workspace_customization_overrides`, and `workspace_datasources` tables in PostgreSQL 18 already store all needed display names and attachments.

### 2.2 Hexagonal Core, Orchestration & Workers (`packages/orcia-core/`)
- `packages/orcia-core/src/orcia_core/orchestration/assistant_governance_models.py`:
  - Clear hardcoded `default_checked_sources` and `recommended_agents` defaults to `()` (`empty tuple`) so unconfigured workspaces do not claim nonexistent `orcia://sources/repo-main` or `@spec-architect` / `@security-reviewer`.
  - Default `UserLayerPreferences.default_hat` to `""` (empty) so callers resolve the real user role/archetype via `resolve_default_hat(user=user)` rather than falling back to `"PM"`.
- `packages/orcia-core/src/orcia_core/orchestration/assistant_prompt_locales.py`:
  - Add bilingual `fr`/`en` dictionaries on `PromptLocaleBundle` for `speed_mode_labels`, `hat_labels`, `global_scope_label`, `active_workspace_fallback_label`, and `active_user_fallback_label`.
- `packages/orcia-core/src/orcia_core/orchestration/assistant_prompt_preview.py` & `assistant_prompt_builder.py`:
  - Add UUIDv7/UUID detection and human-readable sanitization helpers (`resolve_human_workspace_label`, `resolve_human_user_label`, `resolve_human_speed_label`, `resolve_human_hat_label`).
  - Omit `default_sources_label` and `recommended_agents_label` lines from Layer 4 preview when empty instead of printing blank/fake defaults.
  - Update `resolve_default_hat` to fall back from `explicit_hat` -> `user.human_profile_archetype` -> `user.platform_role` -> `fallback` (`"ARCHITECT"`).
  - Replace raw `{speed_mode}` and `{hat}` interpolation in `format_system_instructions_text` with localized human-readable labels.
  - Support optional `workspace_display_name` and `user_display_name` parameters in `build_five_layers_preview_items`, `build_five_layers_preview`, and `assemble_prompt`.
- `packages/orcia-core/src/orcia_core/orchestration/_internal/_sql_assistant_governance_queries.py`, `sql_assistant_governance.py`, `assistant_governance.py`, `_assistant_governance_sync.py`:
  - Select `workspaces.name` and `users.display_name` in `SQL_SELECT_MODE_A_BUNDLE` (zero extra SQL roundtrips) and pass them to `build_five_layers_preview_items`.
  - Resolve effective `default_hat` from `user` when no `USER` override row specifies a custom hat (`manifest.get("default_hat")` empty).

### 2.3 Backend API, Security & Contracts (`apps/api/`, `packages/api-client/`)
- `apps/api/src/orcia_api/routers/_assistant_context_assembly.py` & `assistant_workspace_governance.py`:
  - Propagate resolved `user_email` / `user_display_name` / `workspace_display_name` from governance/context assembly into 5-layer prompt assembly.
- No HTTP request/response schema breaking changes required; run `scripts/export_openapi.py --check` to verify `0-diff` OpenAPI 3.1 contract.

### 2.4 User Interface & Experience (`apps/web/`, `packages/ui/`)
- **Speed / Tier / Effort Alignment (`packages/ui/src/primitives/`, `apps/web/src/i18n/locales/`, `apps/web/src/features/inbox/`)**:
  - Align `useAssistantSpeedViewState` in `AssistantSpeedSelectorHelpers.tsx` so when `hideLegacySpeedPills` is active (or `effort === "balanced"`), `speed` initializes to `SPEED_2_AGENT_TOOLS` when `supportsTools=true` and `SPEED_1_FAST` when `supportsTools=false`, and reacts cleanly when `supportsTools` changes asynchronously.
  - Distinguish `effort: "fast"` (`title: "Rapide"` / `"Fast"`) from `effort: "balanced"` (`title: "Standard"`) in `assistant_stream_labels_{fr,en}.ts`, `feature_inbox_assistant_labels*.ts`, `savedConversationsStore.ts`, and `useAssistantStreamingTurn.ts`.
  - Replace `"PM"` fallback in `assistantFoldersAndPrefsStore.ts` (`defaultHat: ""`) and `useAssistantStreamingTurn.ts` (`sessionActiveHat` from `useAuthSessionStore`).
- **RBAC-Gated & Compact Composer Notices (`apps/web/src/features/inbox/`, `packages/ui/`)**:
  - Compute `canConfigureAiModels = isPlatformAdministratorSession({ roles, readOnlyObserver })` in `useInboxPanelController.ts` and pass it to `InboxDisabledBanner.tsx`.
  - In `InboxDisabledBanner.tsx`, `AssistantNoEmbeddingBanner.tsx`, and `AssistantReindexingBanner.tsx`, hide `<a href="/settings/ai-models">` for non-`PLATFORM_ADMIN` users and render localized plain administrator-contact guidance (`assistantNoChatModel.contactAdminGuidance`, `assistantRagNotice.contactAdminGuidance`).
  - Collapse `AssistantNoEmbeddingBanner` to a compact single-line status row and render `disabledReasonBanner` + `AssistantToolsUnsupportedNotice` side-by-side inside a non-stacked flex container in `AssistantStickyPromptFooter.tsx` (`AssistantStickyFooterBadges.tsx`).

### 2.5 Test Pyramid Impact Analysis (`AD-17`)
- **Layer 1a (Python Unit `tests/unit/`)**: `tests/unit/test_story_29_3_assistant_prompt_sanitization.py` (new, `<= 300` L) verifying UUID suppression, human workspace/user resolution, localized speed/hat labels (`fr`/`en`), zero phantom `orcia://sources/repo-main` / `@spec-architect` defaults, and real user hat resolution. Run existing assistant governance/prompt tests and `test_i18n_backend_catalog_and_english_dev_audit.py`.
- **Layer 1b (Frontend TS/React Unit `Vitest`)**: `apps/web/src/__tests__/story-29-3-assistant-sanitization-and-rbac-notices.test.tsx` (new, `<= 300` L) verifying aligned speed/tier/effort payload & footer in `fr`/`en`, `PLATFORM_ADMIN` vs `TEAM_LEAD`/`CONTRIBUTOR` RBAC gating on composer notices, and compact non-stacked notice layout. Run i18n parity/AST, `e2e-testids-sync-audit`, and `zero-dead-buttons-and-silent-catches-audit`.
- **Layers 2–5**: Executed by the Testing Sub-Agent.

---

## 3. Summary of Changes & Results (Post-Implementation)

### 3.1 Created & Modified Files

| File(s) | Action | Lines (`wc -l`) | Summary |
|---|---|---|---|
| `packages/orcia-core/src/orcia_core/orchestration/assistant_governance_models.py`, `assistant_prompt_locales.py`, `assistant_prompt_preview.py`, `assistant_prompt_builder.py`, `assistant_three_speed_models.py` | Modified | `151` / `270` / `296` / `275` / `118` | Removed hardcoded `"PM"`, phantom `orcia://sources/repo-main`, and `@spec-architect`/`@security-reviewer` defaults; added UUIDv7/UUID sanitization and localized `fr`/`en` speed, hat, workspace, and user label resolution; omitted empty Layer 4 lines. |
| `packages/orcia-core/src/orcia_core/orchestration/_internal/sql_assistant_governance.py`, `_sql_assistant_governance_queries.py`, `assistant_governance.py`, `assistant_governance_layers.py`, `_assistant_governance_sync.py`, `_assistant_turn_engine_plan.py` | Modified | `284` / `274` / `282` / `38` / `204` / `150` | Selected `workspaces.name` and `users.display_name` in `SQL_SELECT_MODE_A_BUNDLE` and propagated resolved display names and user-profile fallback hats into 5-layer prompt assembly and turn planning. |
| `apps/api/src/orcia_api/routers/_assistant_context_assembly.py` | Modified | `298` | Propagated resolved `workspace_display_name` and `user_display_name` / `user_email` into 5-layer prompt assembly (`<= 300` L). |
| `packages/ui/src/primitives/AssistantSpeedSelectorAndStreamView.tsx`, `AssistantSpeedSelectorHelpers.tsx`, `AssistantStickyFooterBadges.tsx`, `AssistantStickyPromptFooter.tsx` | Modified | `299` / `258` / `195` / `272` | Aligned `useAssistantSpeedViewState` (`hideLegacySpeedPills` / `effort === "balanced"` -> `SPEED_2_AGENT_TOOLS` when `supportsTools=true`, `SPEED_1_FAST` when `false`) and collapsed `disabledReasonBanner` + `AssistantToolsUnsupportedNotice` into a compact non-stacked footer row. |
| `apps/web/src/features/inbox/AssistantNoEmbeddingBanner.tsx`, `AssistantReindexingBanner.tsx`, `InboxDisabledBanner.tsx`, `assistantFoldersAndPrefsStore.ts`, `index.tsx`, `savedConversationsStore.ts`, `useAssistantStreamingTurn.ts`, `useInboxPanelController.ts` | Modified | `57` / `99` / `106` / `175` / `297` / `213` / `292` / `299` | Gated `<a href="/settings/ai-models">` behind `isPlatformAdministratorSession` (`canConfigureAiModels`) with plain administrator-contact guidance for non-admins, collapsed `AssistantNoEmbeddingBanner` to a single status row, separated `fast` vs `balanced` effort states, and replaced `"PM"` fallback with active session hat. |
| `apps/web/src/i18n/locales/assistant_labels*.ts`, `assistant_stream_labels_{en,fr}.ts`, `feature_inbox_assistant_labels*.ts` | Modified | `53`/`123`/`126`, `167`/`168`, `87`/`100`/`101` | Separated `fast` (`Rapide`/`Fast`) from `balanced` (`Standard`) labels and added bilingual FR/EN `contactAdminGuidance` keys. |
| `tests/unit/test_story_29_3_assistant_prompt_sanitization.py`, `test_story_29_3_governance_mappers_cov.py`, `test_story_29_3_governance_service_cov.py`, `test_story_29_3_turn_plan_and_preview_cov.py` | Created | `158` / `267` / `178` / `123` | Added Story 29.3 Python unit tests (`<= 267` L each) covering prompt sanitization, localized labels (`fr`/`en`), zero phantom defaults, governance mappers/service, and turn-plan preview branches. |
| `apps/web/src/__tests__/story-29-3-assistant-sanitization-and-rbac-notices.test.tsx`, `apps/web/src/__tests__/setup/mockBackendState.ts` | Created / Modified | `192` / `363` | Added Story 29.3 Vitest suite (`192` L) covering aligned speed/tier/effort dispatch & footer, `PLATFORM_ADMIN` vs non-admin RBAC notice gating, and compact non-stacked layout; updated shared mock default hat state (`4` lines changed in `mockBackendState.ts`). |
| `apps/web/e2e/02-assistant-streaming-and-folders.spec.ts`, `22-assistant-tool-loop-approval-and-reattach.spec.ts`, `support/workspaceAndCatalogHelpers.ts` | Modified | `130` / `204` / `215` | Aligned assistant streaming/governance E2E assertions and helpers with sanitized prompt layers and effort/speed behavior. |

### 3.2 Quantitative Metrics, Coverage & Static Quality
- **Story 29.3 Combined 10-Module Branch Coverage (Distinct Final Testing Sub-Agent Run via `coverage run --branch` + `--no-cov`)**: **`100%`** (`503` statements, `0` missed, `88` branches, `0` partial across `119 passed` tests in `115.09s`):
  - `_assistant_turn_engine_plan.py`: `100%` (`47` stmts, `10` branches)
  - `_internal/_sql_assistant_governance_queries.py`: `100%` (`65` stmts, `24` branches)
  - `_internal/sql_assistant_governance.py`: `100%` (`68` stmts, `8` branches)
  - `assistant_governance.py`: `100%` (`53` stmts, `14` branches)
  - `assistant_governance_layers.py`: `100%` (`4` stmts, `0` branches)
  - `assistant_governance_models.py`: `100%` (`62` stmts, `0` branches)
  - `assistant_prompt_builder.py`: `100%` (`23` stmts, `4` branches)
  - `assistant_prompt_locales.py`: `100%` (`50` stmts, `0` branches)
  - `assistant_prompt_preview.py`: `100%` (`79` stmts, `28` branches)
  - `assistant_three_speed_models.py`: `100%` (`52` stmts, `0` branches)
- **Static Quality & Contracts**:
  - `.venv/bin/pytest --no-cov tests/unit/test_i18n_backend_catalog_and_english_dev_audit.py`: **`3 passed in 8.13s`**
  - `.venv/bin/ruff check .`: `All checks passed!` (`0` errors)
  - `.venv/bin/ruff format --check .`: `1742 files already formatted`
  - `.venv/bin/mypy --strict packages/orcia-core packages/orcia-connectors apps/api apps/worker`: `Success: no issues found in 856 source files`
  - `.venv/bin/lint-imports`: `Contracts: 5 kept, 0 broken.` (`899` files, `6486` dependencies)
  - `.venv/bin/python .agent/skills/bmad-architecture/scripts/lint_spine.py --workspace docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24`: `ok: true, total_findings: 0`
  - `.venv/bin/python scripts/export_openapi.py --check`: `0-diff` (`exit 0`)
  - Line-count control: All `36` modified/new production `.py`/`.ts`/`.tsx` files (`<= 299` L) and all `5` new test files (`<= 267` L) are strictly `<= 300` lines.

### 3.3 AD-17 Test Pyramid, Guardrails & GitNexus Output
- **Layer 1a (Python Unit, Security, Contract & Evals)**:
  - `tests/security tests/contract tests/evals`: **`181 passed in 59.19s`** (`--no-cov`).
  - Combined branch-coverage unit batch (`test_story_29_3_*.py`, `test_epic_10_story_10_1_assistant_governance.py`, `test_story_26_2_core_llm_streaming_and_prompt_builder.py`, `test_story_26_4b_branches_coverage.py`, `test_story_19_6_*.py`, `test_story_26_*.py`): **`119 passed in 115.09s`**.
- **Layer 1b (Frontend Vitest & Turbo Monorepo)**:
  - `pnpm --filter @orcia/web exec vitest run --maxWorkers=4`: **`Test Files 85 passed (85), Tests 314 passed (314)`** (`74.45s`).
  - `pnpm turbo run lint typecheck test --concurrency=1`: **`9 successful, 9 total`** (`45.784s` across `@orcia/api-client`, `@orcia/ui`, `@orcia/web`).
- **Layer 2 (`HTTP -> PostgreSQL 18` `create_app()` Integration, `--no-cov`)**:
  - `test_story_10_1_assistant_overrides_postgres18.py`, `test_story_25_5_assistant_chat_only_and_rag_guard_postgres18.py`, `test_story_26_1_assistant_security_postgres18.py`, `test_story_26_4b_pg18_migration.py`, `test_story_26_4b_pg18_persistence_governance_feedback_folders.py`, `test_story_26_4b_pg18_threads_and_sharing.py`: **`6 passed in 68.58s`**.
- **Layer 3 (OpenAPI 3.1 & `AD-19` Boundaries)**:
  - `scripts/export_openapi.py --check` (`0-diff`) and `.venv/bin/lint-imports` (`5 kept, 0 broken`).
- **Layer 5 (Playwright Desktop E2E, `env -u ORCIA_E2E_SEED_FIXTURES`)**:
  - `playwright test --project=desktop-cockpit` on `11-screens-smoke-without-server-errors.spec.ts`, `02-assistant-streaming-and-folders.spec.ts`, `15-organization-iam-secops-inbox-and-observer.spec.ts`, `21-assistant-citations-v5-audit-help-showcase.spec.ts`, and `22-assistant-tool-loop-approval-and-reattach.spec.ts`: **`12 passed (1.9m)`** against real ephemeral PostgreSQL 18 + Redis 7.4 (clean shutdown, zero leftover E2E Vite/API processes).
- **GitNexus & Diff Summary**:
  - `npx gitnexus analyze --index-only .`: `46,266 nodes | 87,578 edges | 797 clusters | 1531 flows` (`50.4s`).
  - `git diff --stat` (prior to closure docs): `36 files changed, 568 insertions(+), 136 deletions(-)` plus `5` newly created test files (`<= 267` L each).
