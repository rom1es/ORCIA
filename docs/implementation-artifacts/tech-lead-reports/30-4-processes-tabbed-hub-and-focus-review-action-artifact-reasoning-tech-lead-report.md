# Story 30.4 — `Mes Processus` Tabbed Hub (`<OrciaTabStrip />`), Dedicated Focus Review (`/processes/runs/$runId`) & Single State-Gated Decision Bar (`UX30-09`, `UX30-10`)

- **Date**: 2026-11-26
- **Story / Sprint Key**: `30-4-processes-tabbed-hub-and-focus-review-action-artifact-reasoning` (`Epic 30` — Lot 2)
- **Capability(ies)**: `CAP-020`, `CAP-021`, `CAP-140`, `CAP-160`, `CAP-200` — classification: `feature`
- **Author / Context**: `bmad-dev-worker` / Story 30.4 implementing `UX30-09` and `UX30-10` from `docs/planning-artifacts/sprint-change-proposal-2026-11-25-epic-30-assistant-processes-and-agents-ux-hardening.md`, `docs/planning-artifacts/epics.md`, and `docs/planning-artifacts/ux-designs/ux-ORCIA-2026-10-24/DESIGN.md` (`Direction C`).
- **Associated Commits**: Pending (uncommitted working tree on `feat/epic-30-assistant-processes-and-agents-ux-hardening`)

---

## 1. Needs Analysis & Tech Lead Impact Study (Pre-Implementation)

### 1.1 Context & Problem Statement
- **Problem Statement (`UX30-09`, `UX30-10`)**:
  1. `ProcessesHubPage` (`/processes`) currently stacks pending validations (`ProcessesActiveDossiersCard`), the inline `InteractiveRunDrawer` (including expanded `AgentExecutionTrace` and dual HITL bars), the workflow catalog (`ProcessCatalogCardGrid`), autonomous runs supervision (`AutonomousRunsSupervisionPanel`), and the VSM overview (`ProcessesValueStreamOverviewCard`) vertically on one long page without `<OrciaTabStrip />` separation.
  2. `ProcessesValueStreamOverviewCard`, `process_catalog_vsm_p1_{fr,en}.ts`, and `processStudioV2StructuralVsm.ts` still carry hardcoded `"Mon Compte"` VSM titles/slugs (`"Le workflow agentique de Mon Compte"`, `vsm-mon-compte-idea-to-prod`).
  3. Inside an active run (`InteractiveRunDrawer.tsx` & `InteractiveRunDeliverableAndHitlPanels.tsx`), `defaultCollapsedWhenCompleted={false}` expands the reasoning trace above the deliverable, burying the artifact below the fold, while two competing validation bars stack simultaneously (`WAITING_SUBSTEP_HITL` Bar 1 + unconditional `anchor-card-four-actions-panel` Bar 2) with duplicate Edit buttons, always-visible return-loop step/comment inputs, and unconditional `--color-human-led-bg` styling.
- **Target Behavior**:
  1. Organize `/processes` inside canonical `<OrciaPageHeader />` with Tier-2 `<OrciaTabStrip />` separating 3 tabs:
     - `Validations & Exécutions` (showing `(N)` badge ONLY when pending/active count `N > 0`; integrates `ProcessesActiveDossiersCard` and `AutonomousRunsSupervisionPanel` without unrelated 403/empty clutter);
     - `Processus métiers` (available business processes catalog & launch);
     - `Chaîne de valeur` (`ProcessesValueStreamOverviewCard`).
     Default active tab: `Processus métiers` when `N === 0`, `Validations & Exécutions` when `N > 0` (also supporting optional `?tab=` query param). Remove inline `InteractiveRunDrawer` clutter from `/processes` so launching or opening a dossier navigates to `/processes/runs/$runId`. Purge `"Mon Compte"` VSM titles/slugs from `process_catalog_vsm_p1_{fr,en}.ts` and `processStudioV2StructuralVsm.ts` (with runtime sanitization of legacy pack VSM labels).
  2. Add dedicated Focus Review route `/processes/runs/$runId` structured into 3 Direction C zones:
     - **Zone 1 — Sticky Expected Action Banner** (with back button to `/processes`, semantic Amber styling for pending review/arbitration, `HumanLedAnchorCard` Violet `#6D28D9` strictly ONLY when `human_authored_required === true`, **strictly ONE primary Cobalt CTA** state-gated across `WAITING_SUBSTEP_HITL`, `WAITING_WRITE_PREVIEW`, `WAITING_EXTERNAL_GATE`, and `WAITING_FINAL_ANCHOR`, zero duplicate Edit button, and progressive-disclosure `"Demander une correction"` / `"Request changes"` popover hiding target-step selector and remarks input until clicked).
     - **Zone 2 — Primary Artifact Consultation** (~65% width left pane on Desktop `>= 1280px`): formatted Markdown preview (`FormattedMarkdownContent`), clickable source chips opening `SourceLineInspectorDrawer`, and a clean `Lecture` / `Édition` (`Preview` / `Edit`) mode toggle.
     - **Zone 3 — Secondary Reasoning Rail** (~35% width right pane on Desktop `>= 1280px`; below `1280px`, renders 2 clean sub-tabs switching between Artifact and Agent Reasoning): renders `AgentExecutionTrace` with `defaultCollapsedWhenCompleted={true}` once waiting/completed (`WAITING_*`, `COMPLETED*`, `PAUSED`, `FAILED*`) and live-expanded only while `RUNNING`.
- **Architecture & UX Constraints**:
  - Every created or modified production `.py`/`.ts`/`.tsx` file MUST stay `<= 300` lines.
  - Zero raw hex colors outside `packages/ui/src/styles/tokens*.css`; `--color-human-led-violet` strictly reserved for `HumanLedAnchorCard.tsx`.
  - 100% bilingual `fr`/`en` parity via `apps/web/src/i18n/locales/` (zero hardcoded JSX strings or `locale === "fr"` ternaries).
  - Register `/processes/runs/$runId` in `docs/product/capabilities.yaml` and run `sync_site_catalog.py` so `test_site_catalog_sync.py` stays green.

### 1.2 Exploration, GitNexus Impact Analysis, Refactoring & Technical Debt
- **GitNexus Impact Analysis (`gitnexus_analyze`, `gitnexus_query`, `gitnexus_context`, `gitnexus_impact` scoped to `ORCIA`)**:
  - Direct impacted UI modules: `ProcessesHubPage.tsx`, `ProcessesActiveDossiersCard.tsx`, `ProcessesValueStreamOverviewCard.tsx`, `AutonomousRunsSupervisionPanel.tsx`, `InteractiveRunDrawer.tsx`, `InteractiveRunDeliverableAndHitlPanels.tsx`, `useInteractiveProcessRunController.ts`, `interactiveRunSyncHelpers.ts`, `interactiveRunHitlActions.ts`, `processStudioV2StructuralVsm.ts`, `WorkflowFiveBlocksCanvas.tsx`, `apps/web/src/features/cockpit/index.tsx`, `apps/web/src/router.tsx`, `apps/web/src/components/shellBreadcrumbBuilders.ts`.
  - Impacted unit/Vitest & Playwright specs: `epics-14-15-process-studio-v2-and-declarative-packs.test.tsx`, `story-16-3-dual-mode-processes-studio.test.tsx`, `story-16-4-reflexive-trace-wiring-and-f5.test.tsx`, `story-29-5-core-screens-header-convergence.test.tsx`, `story-30-3-processes-pg18-pending-runs.test.tsx`, `story-7-4-autonomous-supervision-and-f5.test.tsx`, `e2e/12-epic16-reflexive-trace-and-line-inspector.spec.ts`, `e2e/20-process-studio-v2-finops-and-log-sink.spec.ts`, `e2e/support/processAndAssistantHelpers.ts`.
  - Upstream impact risk: Medium — moving run inspection from inline `/processes` drawer to `/processes/runs/$runId` requires updating route-aware tests and E2E helpers while preserving Studio's `Test run` flow and `Story 29.1` standalone `AutonomousRunsSupervisionPanel` assertions.
- **Refactoring Opportunities & File-Size Control (`<= 300` lines)**:
  - Extract Focus Review into cohesive small components under `apps/web/src/features/processes/execution/`:
    - `ProcessRunFocusReviewPage.tsx` (route container + cold PG18 rehydration + 2-column / responsive `< 1280px` layout)
    - `ProcessRunActionBanner.tsx` (Zone 1 sticky expected action banner, single state-gated primary Cobalt CTA, progressive-disclosure correction popover, optional `HumanLedAnchorCard` when `human_authored_required === true`)
    - `ProcessRunArtifactPane.tsx` (Zone 2 primary artifact consultation with source chips + `Lecture` / `Édition` toggle)
    - `ProcessRunReasoningRail.tsx` (Zone 3 `AgentExecutionTrace` with `defaultCollapsedWhenCompleted={true}`)
  - Extract `InteractiveRunDeliverableAndHitlPanels.tsx` to share the single state-gated CTA and progressive-disclosure correction popover so Studio's `InteractiveRunDrawer` also eliminates duplicate Bar 1/Bar 2 and duplicate Edit buttons while staying well below 300 lines.
  - Extract `useProcessesHubController.ts` if needed so `ProcessesHubPage.tsx` remains compact (`<= 220` lines).

---

## 2. Implementation Plan

### 2.1 Data Schema & Alembic Migrations
- None required (`workflow_v2_runs` and `reflexive_execution_sessions` PG18 tables from Stories 16.2 / 30.3 already persist all required run, step, trace, and artifact fields).

### 2.2 Hexagonal Core, Orchestration & Workers (`packages/orcia-core/`, `apps/worker/`)
- Reuse `SqlWorkflowV2RunsStore`, `BoundedWorkflowRunState`, and `apply_hitl_signal_to_run` without core domain modifications.

### 2.3 Backend API, Security & Contracts (`apps/api/`, `packages/api-client/`)
- Reuse Story 30.3 endpoints cleanly via `@orcia/api-client`:
  - `GET /api/v1/workflows/v2/runs` (workspace-scoped via `ScopeAccessGuard`)
  - `GET /api/v1/runs/{run_id}` (PG18 cold rehydration)
  - `POST /api/v1/workflows/v2/{workflow_id}/runs`
  - `POST /api/v1/runs/{run_id}/hitl-signal`
  - `GET /api/v1/executions/{execution_id}` & `/approve-write` & `/reject-write` & `/cancel` & `/synthesize-now`
- Minor safety alias in `apps/api/src/orcia_api/routers/_workflows_helpers.py` (`get_vsm_definition_from_pg18`): resolve `vsm-sdlc-idea-to-prod` / `sdlc-idea-to-prod` to the primary SDLC VSM if not matched by exact ID so legacy pack IDs (`vsm-mon-compte-idea-to-prod`) and clean UI slugs both resolve without 404.

### 2.4 User Interface & Experience (`apps/web/`, `packages/ui/`)
1. **i18n Dictionaries (`apps/web/src/i18n/locales/`)**:
   - Purge `"Mon Compte"` VSM subtitle from `process_catalog_vsm_p1_{fr,en}.ts`.
   - Add typed bilingual `fr`/`en` labels in `process_studio_ui_labels*.ts`, `process_vsm_execution_ui_labels*.ts`, and `shell_notifications_labels*.ts` for:
     - `/processes` 3 tabs (`Validations & Exécutions` / `Reviews & Runs`, `Processus métiers` / `Business Processes`, `Chaîne de valeur` / `Value Stream`) and tab strip aria-label;
     - `/processes/runs/$runId` breadcrumb (`Revue du dossier` / `Run Review`), back CTA, Zone 1 banner guidance, single primary CTA, `"Demander une correction"` / `"Request changes"` progressive-disclosure popover, Zone 2 `Lecture` / `Édition` (`Preview` / `Edit`) toggle + source chips heading, Zone 3 reasoning rail title + `< 1280px` mobile sub-tabs (`Livrable` / `Deliverable` vs `Raisonnement` / `Reasoning`).
2. **`Mes Processus` Tabbed Hub (`UX30-09`)**:
   - Refactor `ProcessesHubPage.tsx` to render `<OrciaPageHeader />` with Tier-2 `<OrciaTabStrip />` (`validations`, `catalog`, `value-stream`).
   - Compute `N` from pending/active runs; omit `count` badge when `N === 0`; default to `catalog` (`Processus métiers`) when `N === 0` and `validations` when `N > 0` (unless `?tab=` or explicit user selection overrides).
   - Remove inline `InteractiveRunDrawer` from `ProcessesHubPage.tsx` and `ProcessesActiveDossiersCard.tsx`; clicking pending runs navigates to `/processes/runs/${run.run_id}`, and clicking launch starts a run via API and navigates to `/processes/runs/${run.run_id}` (displaying inline `[role="alert"]` on `/processes` if launch fails).
   - Suppress unrelated 403/empty card clutter in `AutonomousRunsSupervisionPanel` when mounted inside `ProcessesHubPage` Tab 1 (`hideWhenEmptyOrUnauthorized`), preserving standalone behavior for `Story 29.1`.
   - Replace `vsm-mon-compte-idea-to-prod` / `mon-compte-idea-to-prod` in `processStudioV2StructuralVsm.ts` with `vsm-sdlc-idea-to-prod` / `sdlc-idea-to-prod`, and sanitize legacy `"Mon Compte"` strings from API VSM payloads in `ProcessesValueStreamOverviewCard.tsx` and `mapApiVsmToUiSpec.ts`.
3. **Dedicated 3-Zone Focus Review (`/processes/runs/$runId`) (`UX30-10`)**:
   - Register `/processes/runs/$runId` in `apps/web/src/router.tsx` and `docs/product/capabilities.yaml` (`CAP-140`, `CAP-160`).
   - Wire navigation from `ProcessesActiveDossiersCard`, `ProcessesHubPage` launch, `CockpitFeaturePanel` (`onOpenFocusReview` & active runs list), and `ValueStreamMapView` / Studio if applicable.
   - Implement `ProcessRunFocusReviewPage.tsx` with cold PG18 rehydration (`GET /api/v1/runs/{run_id}` + `listWorkflowsV2` + `listProcessPendingRuns` fallback + `refreshSnapshot` for reflexive traces), 3-zone layout (Desktop `>= 1280px` 65%/35% split, `< 1280px` 2 sub-tabs), semantic Amber banner (Violet `HumanLedAnchorCard` only when `human_authored_required === true`), single state-gated primary Cobalt CTA, hidden progressive-disclosure correction popover, clickable source chips (`SourceLineInspectorDrawer`), `Lecture` / `Édition` toggle, and `AgentExecutionTrace` with `defaultCollapsedWhenCompleted={true}` when not `RUNNING`.

### 2.5 Test Pyramid Impact Analysis (`AD-17` — Layers 1 to 5 + Security, Mandatory)
- **Layer 1b (Vitest)**:
  - Add `apps/web/src/__tests__/story-30-4-processes-tabbed-hub-and-focus-review.test.tsx` verifying: `N === 0` defaults to `Processus métiers` without `(0)` badge vs `N > 0` defaults to `Validations & Exécutions` with `(N)` badge; `"Mon Compte"` absent in VSM; `/processes/runs/$runId` 3-zone desktop vs `< 1280px` 2-tab layout; single primary Cobalt CTA (no duplicate Bar 1/Bar 2 or duplicate Edit button); hidden correction controls until `"Demander une correction"` clicked; `defaultCollapsedWhenCompleted={true}` on waiting/completed vs expanded when `RUNNING`; cold PG18 F5 rehydration; and `fr`/`en` parity.
  - Update impacted Vitest specs (`epics-14-15*`, `story-16-3*`, `story-16-4*`, `story-29-5*`, `story-30-3*`, `story-7-4*`) and verify `zero-dead-buttons-and-silent-catches-audit.test.tsx`, `page-header-structure-and-visual-grammar-audit.test.tsx`, `e2e-testids-sync-audit.test.ts`, and `i18n` audits.
- **Layer 3 & Catalog Sync**:
  - Run `sync_site_catalog.py` and verify `tests/unit/test_site_catalog_sync.py`.
- **Layer 5 (Playwright E2E specs)**:
  - Update `apps/web/e2e/support/processAndAssistantHelpers.ts`, `e2e/12-epic16-reflexive-trace-and-line-inspector.spec.ts`, and `e2e/20-process-studio-v2-finops-and-log-sink.spec.ts` to keep selectors synchronized (`e2e-testids-sync-audit.test.ts`).

---

## 3. Summary of Changes & Results (Independent Testing Sub-Agent Verified — `done`)

### 3.1 Created & Modified Files
| File | Action | Concise Summary |
| :--- | :--- | :--- |
| `apps/api/src/orcia_api/routers/_workflows_helpers.py` | Modified | Added clean `vsm-sdlc-idea-to-prod` / `sdlc-idea-to-prod` fallback alias in `get_vsm_definition_from_pg18` (`140` L) |
| `apps/web/src/router.tsx` | Modified | Added `/processes/runs/$runId` route (`processesRunFocusRoute`) (`207` L) |
| `apps/web/src/components/shellBreadcrumbBuilders.ts` | Modified | Added `/processes/runs` breadcrumb mapping (`189` L) |
| `apps/web/src/features/processes/ProcessesHubPage.tsx` | Modified | Refactored `/processes` into `<OrciaPageHeader />` + Tier-2 `<OrciaTabStrip />` (`Validations & Exécutions` \| `Processus métiers` \| `Chaîne de valeur`), omitted `(0)` badge, defaulted to `Processus métiers` when `N === 0`, removed inline `InteractiveRunDrawer`, navigated on open/launch to `/processes/runs/$runId` (`217` L) |
| `apps/web/src/features/processes/useProcessesHubData.ts` | Created | Extracted `/processes` data hydration, autonomous count lookup, and workflow launch navigation hook (`171` L) |
| `apps/web/src/features/processes/ProcessesActiveDossiersCard.tsx` | Modified | Removed inline drawer mounting; wired dossier open actions to `onOpenPendingRun` (`199` L) |
| `apps/web/src/features/processes/AutonomousRunsSupervisionPanel.tsx` | Modified | Added `hideWhenEmptyOrUnauthorized` to suppress empty/403 clutter inside Tab 1 (`215` L) |
| `apps/web/src/features/processes/autonomousRunsScopeHelper.ts` | Created | Shared scope resolution and RFC 9457 403 detection helper (`48` L) |
| `apps/web/src/features/processes/ProcessesValueStreamOverviewCard.tsx` | Modified | Sanitized legacy `"Mon Compte"` VSM titles/subtitles (`113` L) |
| `apps/web/src/features/processes/ProcessCatalogCardGrid.tsx` | Modified | Added `launchingWorkflowId` in-flight feedback on launch CTAs (`233` L) |
| `apps/web/src/features/processes/processStudioV2StructuralVsm.ts` | Modified | Replaced `vsm-mon-compte-idea-to-prod` / `mon-compte-idea-to-prod` with `vsm-sdlc-idea-to-prod` / `sdlc-idea-to-prod` (`218` L) |
| `apps/web/src/features/processes/processStudioV2Types.ts` | Modified | Added optional `human_authored_required?: boolean` (`102` L) |
| `apps/web/src/features/processes/vsm/mapApiVsmToUiSpec.ts` | Modified | Sanitized legacy `"Mon Compte"` VSM title/subtitle during API mapping (`95` L) |
| `apps/web/src/features/processes/studio/WorkflowFiveBlocksCanvas.tsx` | Modified | Updated parent VSM route target to `/processes/vsm/vsm-sdlc-idea-to-prod` (`279` L) |
| `apps/web/src/features/processes/execution/ProcessRunFocusReviewPage.tsx` | Created | Dedicated 3-zone Focus Review route (`/processes/runs/$runId`) with cold PG18 rehydration and responsive `< 1280px` 2-tab layout (`298` L) |
| `apps/web/src/features/processes/execution/ProcessRunActionBanner.tsx` | Created | Zone 1 sticky expected action banner (Amber pending, Violet `HumanLedAnchorCard` strictly on `human_authored_required === true`, single state-gated Cobalt CTA) (`280` L) |
| `apps/web/src/features/processes/execution/ProcessRunCorrectionPopover.tsx` | Created | Progressive-disclosure correction target-step and remarks popover (`92` L) |
| `apps/web/src/features/processes/execution/ProcessRunArtifactPane.tsx` | Created | Zone 2 primary deliverable consultation with clickable source chips and `Lecture`/`Édition` toggle (`170` L) |
| `apps/web/src/features/processes/execution/ProcessRunReasoningRail.tsx` | Created | Zone 3 secondary reasoning rail (`AgentExecutionTrace` with `defaultCollapsedWhenCompleted={true}`) (`102` L) |
| `apps/web/src/features/processes/execution/InteractiveRunDrawer.tsx` | Modified | Set `defaultCollapsedWhenCompleted={true}` (`280` L) |
| `apps/web/src/features/processes/execution/InteractiveRunDeliverableAndHitlPanels.tsx` | Modified | Reused `ProcessRunActionBanner` & `ProcessRunArtifactPane` cleanly (`98` L) |
| `apps/web/src/features/processes/execution/useInteractiveProcessRunController.ts` | Modified | Added `hydrateOnlyRunId` PG18 rehydration path, backend `APPROVE` persistence for substeps, F5 `WAITING_WRITE_PREVIEW` rehydration synchronization, and live `RUNNING` trace status propagation (`297` L) |
| `apps/web/src/features/shared/useReflexiveExecutionController.ts` | Modified | Fixed cold F5 `WAITING_WRITE_PREVIEW` rehydration race condition (`267` L) |
| `apps/web/src/features/processes/execution/interactiveRunSyncHelpers.ts` | Modified | Added `hydrateExistingRunById` (`GET /api/v1/runs/{run_id}` + `listProcessPendingRuns` fallback) (`240` L) |
| `apps/web/src/features/processes/execution/interactiveRunHitlActions.ts` | Modified | Wired `executeApproveSubStep` to PG18 `sendWorkflowV2HitlSignal` (`238` L) |
| `apps/web/src/features/processes/execution/interactiveRunFormatters.ts` | Modified | Added `buildStatusHumanLabelMap` and `buildFallbackFocusWorkflow` (`174` L) |
| `apps/web/src/features/cockpit/index.tsx` & `CockpitRunsSection.tsx` | Modified | Wired Cockpit focus review & active run navigation to `/processes/runs/$runId` (`257` L / `247` L) |
| `apps/web/src/i18n/locales/process_catalog_vsm_p1_{fr,en}.ts`, `process_studio_ui_labels*.ts`, `process_vsm_execution_ui_labels*.ts`, `shell_notifications_labels*.ts` | Modified | Purged `"Mon Compte"` VSM subtitle; added 100% `fr`/`en` labels for tabbed `/processes` and `/processes/runs/$runId` (all `<= 252` L) |
| `docs/product/capabilities.yaml`, `apps/web/src/generated/orciaSiteManifest.ts`, `docs/site-catalog/index.html`, `docs/implementation-artifacts/sprint-status.yaml`, `docs/implementation-artifacts/tech-lead-reports/README.md` | Modified | Registered `/processes/runs/$runId` & Story 30.4 evidence under `CAP-140`/`CAP-160`, refreshed `CAP-200`, marked Story 30.4 `done`, and synchronized showcase catalog |
| `tests/unit/test_story_30_4_workflows_helpers_coverage.py`, `apps/web/src/__tests__/story-30-4-processes-tabbed-hub-and-focus-review.test.tsx`, `story-30-3*`, `story-29-5*`, `story-16-4*`, `story-27-5*`, `epics-14-15*`, `i18n-and-shell.test.tsx`, `autonomyTriggersAndWorkflowsV2Handlers.ts`, `apps/web/e2e/{12,20}*`, `processAndAssistantHelpers.ts` | Created / Modified | Added Story 30.4 Python unit coverage (`100%` branch on `_workflows_helpers.py`) & Vitest suite and updated impacted Vitest + E2E specs |

### 3.2 Verification Metrics & `AD-17` 5-Layer Validation Results
- **Line-count guard (`wc -l <= 300`)**: All `39/39` modified/created production `.py`/`.ts`/`.tsx` files verified `<= 298` lines (`7,259` total lines; max `298` L in `ProcessRunFocusReviewPage.tsx`, `297` L in `useInteractiveProcessRunController.ts`, `267` L in `useReflexiveExecutionController.ts`).
- **Static, Architecture, OpenAPI & Security Gates**:
  - `.venv/bin/ruff check .`: `0` issues (`All checks passed!`)
  - `.venv/bin/ruff format --check .`: `1,768` files formatted (`0` changes needed)
  - `.venv/bin/mypy --strict packages/orcia-core packages/orcia-connectors apps/api apps/worker`: `865` source files, `0` issues
  - `.venv/bin/lint-imports`: `5` contracts kept, `0` broken (`906` files, `6,559` dependencies)
  - `lint_spine.py`: `0` findings (`ok: true`)
  - `scripts/export_openapi.py --check`: `0-diff`
  - `.venv/bin/detect-secrets-hook --baseline .secrets.baseline`: `0` findings
- **Scoped Branch Coverage (`>= 90%`)**:
  - `apps/api/src/orcia_api/routers/_workflows_helpers.py`: **`100%`** (`78` statements, `0` missed, `30` branches, `0` partial branches) across `15` targeted tests (`test_story_30_4_workflows_helpers_coverage.py`, `test_story_30_3_workflows_and_bridge_coverage.py`, `test_epic_11_story_11_4_pack_builder_processes.py`, `test_story_30_3_processes_live_llm_and_pending_runs.py`).
- **Split Python Suites (`--no-cov`, `AD-17` Layers 1, 2, 3, 4 & Security)**:
  - `tests/evals tests/security tests/contract`: **`181` passed**
  - `tests/unit`: **`1,146` passed** (`266.36s`), plus post-final-TS-edit verification of all `14` `*audit*.py` unit audit files (`82 passed in 42.34s`, including `test_i18n_backend_catalog_and_english_dev_audit.py`, `test_e2e_sql_coverage_audit.py`, `test_zero_orphan_sql_adapters_audit.py`, and `test_codebase_architectural_anti_patterns_audit.py`)
  - Impacted PG18 + Redis `testcontainers` integration (`test_story_30_3_pending_runs_and_live_guard_postgres18.py`, `test_dbos_return_loops_and_claim_check.py`, `test_story_16_3_dual_mode_processes_api.py`): **`6` passed** (`37.95s`)
- **TypeScript Monorepo & i18n Gates (`AD-17` Layer 1b)**:
  - `pnpm turbo run lint typecheck test --concurrency=2`: **`9/9` tasks passed** (`49.38s`):
    - `@orcia/api-client`: `3` test files, `20` tests passed
    - `@orcia/ui`: `39` test files, `151` tests passed
    - `@orcia/web`: `93` test files, `363` tests passed (i18n Gates 1–4 locked at `0` baseline)
- **Desktop Playwright E2E (`AD-17` Layer 5, `env -u ORCIA_E2E_SEED_FIXTURES`)**:
  - `--project=desktop-cockpit` across `01-day0-boot-and-f5-persistence`, `09-pack-builder-and-contextual-help`, `11-screens-smoke-without-server-errors`, `12-epic16-reflexive-trace-and-line-inspector`, `12-finops-and-audit-provenance`, `20-process-studio-v2-finops-and-log-sink`, `29-epic-29-canonical-headers-bilingual`: **`10` passed, `1` mobile-only skipped, `0` failed** (`2.4m`); `docs/implementation-artifacts/e2e-campaign-epic-22/` cleaned immediately.
- **GitNexus Local Index & Documentation Sync**:
  - `npx gitnexus analyze --index-only .`: `47,197` nodes, `112,183` edges, `776` clusters, `1,542` flows (`50.3s`).
  - `sync_site_catalog.py` / `--check`, `check_implementation_docs.py`, and `tests/unit/test_site_catalog_sync.py`: verified clean at closure.
