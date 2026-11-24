# Story 28.4 — Encapsulation of DNA Starlark Compiler & PG18 Glossary Candidate Queue Inside Tab 4 (`Glossaire & Règles Métiers`), Anti-Stacking Guard & Playwright E2E Verification (`WX-03`, `WX-04`)

- **Date**: 2026-11-24
- **Story / Sprint Key**: `28-4-tab4-glossary-dna-starlark-encapsulation-and-e2e-lock` (`Epic 28` — Lot 2: Glossary/DNA Tab & Verification Closure)
- **Capability(ies)**: `CAP-010`, `CAP-080`, `CAP-081`, `CAP-084`, `CAP-180` — classification: `feature`
- **Author / Context**: Relocate `DnaStarlarkCompilerAndGlossaryLifecycleView` strictly inside Tab 4 (`GLOSSARY_RULES`) alongside `WorkspaceGlossaryAndOntologyTab` so it never renders at the bottom of `/workspaces` (`WX-03`); hydrate glossary candidate queues and In-Flow promotion/rejection from PostgreSQL 18 via `@orcia/api-client` (`listOntologyPromotions` / `decideOntologyPromotion`) instead of unhydrated local `useState([])` (`WX-03`, `WX-04`); add the automated `WX-01`..`WX-06` anti-stacking & sobriety Vitest audit (`workspaces-single-tabs-anti-stacking-audit.test.tsx`); and update `07-spaces-org-and-workspace-persistence.spec.ts`, `17-workspace-sources-codegraph-dna-and-ontology.spec.ts`, `story-24-2-*`, and `i18n-and-shell.test.tsx` in lockstep.
- **Associated Commits**: Pending closure

---

## 1. Needs Analysis & Tech Lead Impact Study (Pre-Implementation)

### 1.1 Context & Problem Statement
- **Current behavior**:
  1. **Unconditional bottom-of-page mounting (`WX-03`)**: `WorkspaceDnaAndWaiversSection.tsx` (`L228-270`) renders `<DnaStarlarkCompilerAndGlossaryLifecycleView />` unconditionally *below* `<WorkspaceFiveTabsAndExternalRebaseView />`. As a result, the DNA Starlark Rule Compiler (`starlark-compiler-panel` / `dna-starlark-empty-state`), `in-flow-top3-panel`, and `glossary-fifo-queue-panel` remain permanently visible on Tabs 1, 2, 3, and 5 instead of living inside Tab 4 (`GLOSSARY_RULES`).
  2. **Ephemeral `useState([])` glossary candidate queue (`WX-03`, `WX-04`)**: `useWorkspaceDnaAndWaivers.ts` (`L65`) initializes `glossaryCandidates` as an unhydrated `useState<UiGlossaryCandidateItem[]>([])` and never fetches pending proposals from PostgreSQL 18. Furthermore, `onPromoteInFlow` (`WorkspaceDnaAndWaiversSection.tsx:L236-263`) and `onRejectCandidate` (`L264-269`) only mutate local React state and `PlatformSetupContext`, losing any candidate decision upon `F5` cold reload.
  3. **Tab 1 sobriety count leakage**: `WorkspaceDnaAndWaiversSection.tsx:L162` computes `pendingGlossaryCandidatesCount={ontologyConcepts.length + glossaryCandidates.length}` using global `PlatformSetupContext.ontologyConcepts` rather than scoped pending workspace candidates, which risks leaking non-zero KPI counts into Tab 1 (`OverviewTabPanel`) on empty workspaces.
  4. **Stale test assumptions**: `story-24-2-spaces-day0-dna-waivers-and-triggers.test.tsx`, `i18n-and-shell.test.tsx`, and `apps/web/e2e/17-workspace-sources-codegraph-dna-and-ontology.spec.ts` (Test 3) currently interact with `dna-starlark-glossary-view` and `compile-starlark-btn` directly on Tab 1 (`OVERVIEW`) without switching to `workspace-tab-GLOSSARY_RULES`.
- **Expected behavior**:
  - `DnaStarlarkCompilerAndGlossaryLifecycleView` is mounted strictly inside Tab 4 (`glossaryTabSlot` -> `workspace-glossary-rules-panel`) alongside `WorkspaceGlossaryAndOntologyTab`, and is completely unmounted (`null`) whenever Tab 1, Tab 2, Tab 3, or Tab 5 is active.
  - `useWorkspaceDnaAndWaivers.ts` hydrates `glossaryCandidates` scoped to `targetWorkspace.workspaceId` from PostgreSQL 18 via `client.listOntologyPromotions("PENDING_REVIEW", false)` (`p.source_scope_id === targetWsId || p.target_scope_id === targetWsId`), and `onPromoteInFlow` / `onRejectCandidate` persist decisions directly to PG18 via `client.decideOntologyPromotion(candidateId, { decision: "APPROVE" | "REJECT", review_comment }, false)` with `[role="alert"]` error handling (`formatRfc9457ErrorToBanner`), surviving `F5` cold reload (`reloadColdFromPg`) and keeping `WorkspaceGlossaryAndOntologyTab` synchronized.
  - A dedicated Vitest structural audit (`workspaces-single-tabs-anti-stacking-audit.test.tsx`) enforces all six `WX-01`..`WX-06` invariants across French (`fr`) and English (`en`).
  - Playwright E2E `07-spaces-org-and-workspace-persistence.spec.ts` and `17-workspace-sources-codegraph-dna-and-ontology.spec.ts` reflect the unified 5-tab `/workspaces` layout and pass `e2e-testids-sync-audit.test.ts`.
- **Architectural constraints**:
  - Reuse existing PG18 endpoints (`GET/POST /api/v1/ontology-rag/ontology/promotions*`, `GET/POST /api/v1/workspaces/{id}/dna-mechanisms*`) — zero backend schema or API breaking changes.
  - Every modified/created production `.ts`/`.tsx` file MUST stay **`<= 300` lines** (`wc -l`).
  - 100% bilingual `fr`/`en` via `apps/web/src/i18n/locales/*.ts` (zero hardcoded UI strings, zero Gate 1–3 regressions, zero dead buttons).

### 1.2 Exploration, GitNexus Impact Analysis, Refactoring & Technical Debt
- **GitNexus Impact Analysis (`gitnexus_query`, `gitnexus_context`, `gitnexus_impact`, repo `/home/romain/.gemini/antigravity/worktrees/ORCIA/analyze_ui_screenshot`)**:
  - `useWorkspaceDnaAndWaivers`: `context()` shows 1 direct caller (`WorkspaceDnaAndWaiversSection.tsx`) and internal helpers (`reloadWaiversAndMechanisms`, `handleRegisterWaiver`, `handleCompileFromNorm`, `handleSignAndActivate`); upstream `impact()` confirms `WorkspaceDnaAndWaiversSection` as sole `d=1` caller before `WorkspacesFeaturePanel` / `ModuleWorkspaceView` (`d=2`).
  - `WorkspaceDnaAndWaiversSection.tsx`, `WorkspaceGlossaryAndOntologyTab.tsx`, and `DnaStarlarkCompilerAndGlossaryLifecycleView.tsx` were inspected directly with line-range reads and repo-wide `grep` across `apps/web/`, `packages/ui/`, and `packages/api-client/`.
- **Exploration & Key Existing PG18 Surfaces**:
  - `apps/api/src/orcia_api/routers/ontology_promotions.py` & `_ontology_promotions_handlers.py`: `list_ontology_promotions` (`GET /api/v1/ontology-rag/ontology/promotions?status=PENDING_REVIEW&fixture=false`) queries `ontology_promotion_proposals` in PG18, and `decide_ontology_promotion` (`POST .../promotions/{proposal_id}/decide?fixture=false`) updates `ontology_promotion_proposals`, inserts promoted `ontology_concepts`, and writes `ONTOLOGY_PROMOTION_APPROVED`/`REJECTED` into `audit_ledger`.
  - `apps/api/src/orcia_api/routers/dna_and_glossary.py`: `list_dna_starlark_mechanisms` / `compile_dna_starlark_mechanism` / `activate_dna_starlark_mechanism` persist to `workspace_dna_mechanisms` in PG18.
  - `apps/web/src/__tests__/vitestOntologyMockHandlers.ts`: `GET /api/v1/ontology-rag/ontology/promotions` did not filter by the `status` query parameter — will be aligned to match the real FastAPI PG18 endpoint.
- **Refactoring Opportunities & Emerging Technical Debt Mitigation**:
  - `WorkspaceGlossaryAndOntologyTab.tsx` is at `296` lines (`<= 300` ceiling). Keep edits minimal (`<= 299` lines) by passing only `refreshNonce` and `onPromotionsChanged` callbacks.
  - `DnaStarlarkCompilerAndGlossaryLifecycleView.tsx` (`268` lines) uses uncontrolled `defaultChecked` checkboxes on `in-flow-top3-panel` and leaves `promote-in-flow-btn` enabled when 0 candidates exist; add controlled selection state synced to `top3PrecheckedCandidates` and disable `promote-in-flow-btn` when `selectedIds.length === 0 || submitting` while remaining `<= 295` lines.
  - `useWorkspaceDnaAndWaivers.ts` (`198` lines) remains `<= 265` lines after adding PG18 glossary candidate hydration and `handlePromoteInFlow` / `handleRejectCandidate`.

---

## 2. Implementation Plan

### 2.1 Data Schema & Alembic Migrations (`infra/migrations/versions/...`)
- No schema changes required; Story 28.4 reuses the existing PG18 tables `ontology_concepts`, `ontology_promotion_proposals`, `workspace_dna_mechanisms`, `workspace_exception_waivers`, `workspace_datasources`, and `audit_ledger`.

### 2.2 Hexagonal Core, Orchestration & Workers (`packages/orcia-core/`, `apps/worker/`, `infra/sandbox/`)
- No backend domain or worker modifications required.

### 2.3 Backend API, Security & Contracts (`apps/api/`, `packages/api-client/`)
- No backend API route or OpenAPI contract modifications required; `@orcia/api-client` already exposes `listOntologyPromotions`, `decideOntologyPromotion`, `listDnaMechanisms`, `compileDnaStarlark`, `activateDnaMechanism`, `listWorkspaceExceptionWaivers`, `registerWorkspaceExceptionWaiver`, and `listWorkspaceDatasources`.

### 2.4 User Interface & Experience (`apps/web/`, `packages/ui/`)
- **`packages/ui/src/primitives/DnaStarlarkCompilerAndGlossaryLifecycleView.tsx` (`<= 295` lines)**:
  - Add controlled checkbox selection state (`selectedTop3Ids`) initialized/synced from `top3PrecheckedCandidates` (`preCheckedForInFlowPromotion`), toggleable per candidate checkbox, and disable `promote-in-flow-btn` when `submitting || selectedTop3Ids.length === 0`.
- **`apps/web/src/features/workspaces/useWorkspaceDnaAndWaivers.ts` (`<= 270` lines)**:
  - Hydrate `glossaryCandidates` in `reloadWaiversAndMechanisms` via `client.listOntologyPromotions("PENDING_REVIEW", false)` filtered by `p.status === "PENDING_REVIEW"` and `(p.source_scope_id === targetWsId || p.target_scope_id === targetWsId)`.
  - Implement `handlePromoteInFlow(candidateIds)` and `handleRejectCandidate(candidateId)` calling `client.decideOntologyPromotion(...)`, reloading governance state from PG18, invoking `onGlossaryMutated?.()`, and surfacing any HTTP `>= 400` error via `onFeedback` (`⚠️ ...`).
- **`apps/web/src/features/workspaces/WorkspaceGlossaryAndOntologyTab.tsx` (`<= 299` lines)**:
  - Accept optional `refreshNonce?: number` and `onPromotionsChanged?: () => void`; trigger `loadFromServer()` on `refreshNonce` changes and notify `onPromotionsChanged?.()` when a promotion proposal is created.
- **`apps/web/src/features/workspaces/WorkspaceDnaAndWaiversSection.tsx` (`<= 285` lines)**:
  - Remove `<DnaStarlarkCompilerAndGlossaryLifecycleView />` from outside the 5-tab container and place it inside `glossaryTabSlot` below `<WorkspaceGlossaryAndOntologyTab />`.
  - Pass `pendingGlossaryCandidatesCount={glossaryCandidates.length}` so empty workspaces preserve Tab 1 `total == 0` KPI sobriety (`workspace-overview-kpi-grid` hidden).
- **`apps/web/src/i18n/locales/feature_workspaces_labels*.ts`**:
  - Add bilingual `promoteReviewComment` and `rejectReviewComment` strings under `dnaAndWaivers`.

### 2.5 Test Pyramid Impact Analysis (`AD-17` — Layers 1 to 5 + Security, Mandatory)
- **Layer 1a & Layer 1b (Vitest)**:
  - New `apps/web/src/__tests__/workspaces-single-tabs-anti-stacking-audit.test.tsx`: enforces all 6 `WX-01`..`WX-06` invariants (1 `[role="tablist"]`, 1 `workspaces-compact-header`, 0 raw `personal-<uuid>` strings, `total == 0` hides `workspace-overview-kpi-grid` and `sources-filter-pill-*`, `dna-starlark-glossary-view` unmounted on Tabs 1/2/3/5 and mounted strictly in Tab 4, PG18 glossary candidate hydration/promotion/rejection surviving F5 remount, and `fr`/`en` parity).
  - Updated `apps/web/src/__tests__/story-24-2-spaces-day0-dna-waivers-and-triggers.test.tsx` and `apps/web/src/__tests__/i18n-and-shell.test.tsx`: switch to `workspace-tab-GLOSSARY_RULES` before Starlark actions and assert `dna-starlark-glossary-view` is `null` on Tab 1.
  - Updated `apps/web/src/__tests__/vitestOntologyMockHandlers.ts`: filter `GET /ontology/promotions` by `status` query param.
  - Existing guards: `e2e-testids-sync-audit`, `i18n-hardcoded-locale-ast-audit`, `i18n-dictionary-parity-and-jargon-audit`, `zero-dead-buttons-and-silent-catches-audit`, and `story-28-1..3`.
- **Layer 2 / 3 / 4 / Security**: Reuses existing PG18 FastAPI endpoints & contracts (`0` backend/schema edits).
- **Layer 5 (Playwright E2E)**:
  - Updated `apps/web/e2e/17-workspace-sources-codegraph-dna-and-ontology.spec.ts` (Test 3 switches to `workspace-tab-GLOSSARY_RULES` before `dna-starlark-glossary-view` / `compile-starlark-btn` / `starlark-compiler-panel` pre- and post-`reloadColdFromPg`, and asserts `dna-starlark-glossary-view` is hidden on Tab 1).
  - Updated `apps/web/e2e/07-spaces-org-and-workspace-persistence.spec.ts` (adds unified `workspaces-compact-header` + `workspaces-active-switcher-select` + `workspaces-active-title` + single `workspace-five-tabs-view` lock assertions alongside PG18 & sidebar sync verification).

---

## 3. Summary of Changes & Results (Post-Implementation & Architecture Remediation)

### 3.1 Created, Modified & Deleted Files

| File | Action | Line Count (`wc -l`) | Concise Summary |
| :--- | :--- | :---: | :--- |
| `packages/ui/src/primitives/DnaStarlarkCompilerAndGlossaryLifecycleView.tsx` | Modified | `291` | Replaced uncontrolled `defaultChecked` Top-3 checkboxes with controlled `selectedTop3Ids` synced to `top3PrecheckedCandidates` (`toggleTop3Selection`) and disabled `promote-in-flow-btn` when `submitting || selectedTop3Ids.length === 0`. |
| `packages/ui/src/primitives/WorkspaceFiveTabsPanels.tsx` | Modified | `198` | Made Tab 1 `workspace-overview-rebase-section` (`supersededMemlogNotice`) conditional on `rebasedChunks.length > 0` for `total == 0` sobriety. |
| `apps/web/src/features/workspaces/useWorkspaceDnaAndWaivers.ts` | Modified | `289` | Hydrated scoped PG18 `glossaryCandidates` (`listOntologyPromotions("PENDING_REVIEW", false)`), persisted `handlePromoteInFlow`/`handleRejectCandidate` (`decideOntologyPromotion`), localized `compiledVerifiedBadge`/`compiledExplanationTemplate`/`compiledCausalBreadcrumbTemplate` via `dnaCopy`, and stabilized callbacks with refs. |
| `apps/web/src/features/workspaces/WorkspaceGlossaryAndOntologyTab.tsx` | Modified | `284` | Added optional `refreshNonce` and `onPromotionsChanged` props to keep glossary tiers and Tab 4 candidate queue synchronized upon promotion/rejection. |
| `apps/web/src/features/workspaces/WorkspaceDnaAndWaiversSection.tsx` | Modified | `231` | Moved `<DnaStarlarkCompilerAndGlossaryLifecycleView />` strictly inside `glossaryTabSlot` (`workspace-glossary-rules-panel`) so it is unmounted on Tabs 1, 2, 3, and 5; scoped `pendingGlossaryCandidatesCount={glossaryCandidates.length}` and removed duplicate phase/visibility/datasource callbacks. |
| `apps/web/src/features/workspaces/WorkspaceSourcesRagTab.tsx` | Modified | `289` | Removed `"PLATFORM_ADMIN"` fallback escalation (`sessionRoles`/`sessionActiveHat`/`"CONTRIBUTOR"`), removed silent `console.warn` in favor of `showApiError` (`[role="alert"]`), and removed redundant `onRegisterDatasource`. |
| `apps/web/src/features/workspaces/WorkspaceMembersAndSettingsTab.tsx` | Modified | `115` | Converted Tab 5 workspace phase/visibility section to read-only summary badges (`workspace-settings-phase-badge-*`, `workspace-settings-visibility-badge-*`) so interactive controls exist only in `WorkspaceCompactHeader` (`ACTION_ITEM-28.1` tracks future workspace-scoped PATCH). |
| `apps/web/src/features/workspaces/WorkspaceStudioCardsAndDetailView.tsx` | Modified | `98` | Pruned unused `datasources`, `workflows`, `ontologyConcepts`, `orgUnits`, and dead-prop wiring after `WorkspaceStudioSummaryCard` removal. |
| `apps/web/src/features/workspaces/WorkspaceStudioSummaryCard.tsx` | Deleted | — | Removed dead legacy workspace summary card component (`-272` lines). |
| `apps/web/src/features/workspaces/index.tsx` | Modified | `204` | Removed pruned props passed down to `WorkspaceStudioCardsAndDetailView` and `WorkspaceDnaAndWaiversSection`. |
| `apps/web/src/components/platformSetupContextTypes.ts` | Modified | `286` | Added `markMutated()` in `updateWorkspacePhase` and `updateWorkspaceVisibility` so optimistic local state tracks pending persistence cleanly. |
| `apps/web/src/features/ontology/useOntologyFeatureController.ts` | Modified | `180` | Made `handleAuditDocVsCode` workspace resolution deterministic using `activeScopeId`, non-personal workspace preference, and fallback. |
| `apps/web/src/i18n/locales/feature_workspaces_labels.ts` | Modified | `149` | Added `compiledVerifiedBadge`, `compiledExplanationTemplate`, `compiledCausalBreadcrumbTemplate`, `promoteReviewComment`, and `rejectReviewComment` keys under `dnaAndWaivers`. |
| `apps/web/src/i18n/locales/feature_workspaces_labels_fr.ts` | Modified | `159` | Added French translations for compiled Starlark templates/badge and review comments, and aligned Organization nav hints. |
| `apps/web/src/i18n/locales/feature_workspaces_labels_en.ts` | Modified | `159` | Added English translations for compiled Starlark templates/badge and review comments, and aligned Organization nav hints. |
| `apps/web/src/__tests__/workspaces-single-tabs-anti-stacking-audit.test.tsx` | Created | `389` | Added `WX-01`..`WX-06` anti-stacking & sobriety Vitest audit (`3` tests) covering FR/EN parity, PG18 glossary candidate F5 survival, EN Starlark localization, contributor non-escalation on Tab 2, and `[role="alert"]` error handling. |
| `apps/web/src/__tests__/vitestOntologyMockHandlers.ts` | Modified | `466` | Added `status` query parameter filtering on `GET /api/v1/ontology-rag/ontology/promotions` to match the real FastAPI PG18 endpoint. |
| `apps/web/src/__tests__/setup/transportAndOpenApiValidator.ts` | Modified | `182` | Forwarded `parsedUrl` to `handleVitestOntologyRoute` for `status` query filtering. |
| `apps/web/src/__tests__/story-24-2-spaces-day0-dna-waivers-and-triggers.test.tsx` | Modified | `247` | Updated Story 24.2 tests (`3` tests) to assert `dna-starlark-glossary-view` is unmounted on Tab 1 and switch to `workspace-tab-GLOSSARY_RULES` prior to Starlark compilation/activation & F5 check. |
| `packages/ui/src/__tests__/story-24-2-five-tabs-and-triggers-modal.test.tsx` | Modified | `289` | Added assertion verifying `workspace-overview-rebase-section` / `supersededMemlogNotice` renders on Tab 1 only when `rebasedChunks.length > 0`. |
| `apps/web/src/__tests__/story-24-6-packs-counters-microcopy-and-finops.test.tsx` | Modified | `263` | Removed deleted `WorkspaceStudioSummaryCard` assertions and verified `WorkspaceStudioCardsAndDetailView` compact header. |
| `apps/web/src/__tests__/story-28-3-scoped-sources-deliverables-and-members-tabs.test.tsx` | Modified | `294` | Updated Tab 5 governance assertions to target `WorkspaceCompactHeader` controls synced with Tab 5 read-only summary badges across F5. |
| `apps/web/src/__tests__/i18n-and-shell.test.tsx` | Modified | `2315` | Updated workspace tab assertion to switch to `workspace-tab-GLOSSARY_RULES` before asserting `dna-starlark-glossary-view` visibility. |
| `apps/web/e2e/07-spaces-org-and-workspace-persistence.spec.ts` | Modified | `104` | Updated cold-reload assertion (`workspaces-active-switcher-select` + `workspaces-active-title`), added unified compact header + 5-tab + Tab 4 Starlark lock, and added bilingual FR/EN verification. |
| `apps/web/e2e/17-workspace-sources-codegraph-dna-and-ontology.spec.ts` | Modified | `335` | Updated Test 3 to verify `dna-starlark-glossary-view` hidden on Tab 1, switch via `openWorkspaceGlossaryTab` for Starlark compilation/activation pre/post-F5, and select `"Espace ADN Tripartite"` deterministically in `ontology-level-select`. |
| `apps/web/e2e/21-assistant-citations-v5-audit-help-showcase.spec.ts` | Modified | `224` | Added auto-retrying visibility wait on `zone4Help.locator("strong, code").first()` for Zone 4 async `help/resolve` hydration. |
| `apps/web/e2e/support/orgAndWorkspace.ts` | Modified | `57` | Converted JSDoc comments to English per repository language policy. |
| `docs/planning-artifacts/epics.md`, `docs/planning-artifacts/sprint-change-proposal-2026-11-23-epic-28-workspaces-unification.md`, `docs/implementation-artifacts/sprint-status.yaml` | Modified | — | Aligned Story 28.2/28.3 scope wording with `ACTION_ITEM-28.1` (`status: open`, deferred backend workspace-scoped `PATCH` & full Tab 1/3/5 PG18 follow-ups) and marked `28-4` & `epic-28: done`. |
| `docs/product/capabilities.yaml`, `docs/implementation-artifacts/tech-lead-reports/README.md` | Modified | — | Updated `CAP-080`, `CAP-081`, and `CAP-084` (`verified_at: "2026-11-24"`) and registered Story 28.4 Tech Lead report. |

### 3.2 Quantitative Metrics, Coverage & Static Quality
- **Production file-size compliance (`wc -l <= 300`)**: `14/14` Story 28.4 touched production `.ts`/`.tsx` files are `<= 291` lines (`DnaStarlarkCompilerAndGlossaryLifecycleView.tsx`: `291`, `WorkspaceSourcesRagTab.tsx`: `289`, `useWorkspaceDnaAndWaivers.ts`: `289`, `platformSetupContextTypes.ts`: `286`, `WorkspaceGlossaryAndOntologyTab.tsx`: `284`, `WorkspaceDnaAndWaiversSection.tsx`: `231`, `index.tsx`: `204`, `WorkspaceFiveTabsPanels.tsx`: `198`, `useOntologyFeatureController.ts`: `180`, `feature_workspaces_labels_{fr,en}.ts`: `159`, `feature_workspaces_labels.ts`: `149`, `WorkspaceMembersAndSettingsTab.tsx`: `115`, `WorkspaceStudioCardsAndDetailView.tsx`: `98`).
- **JS/TS Monorepo Verification (`timeout -k 10s 300s pnpm turbo run lint typecheck test`)**:
  - **`9/9` tasks successful** (`0` lint/typecheck errors, `44.33s`):
    - `@orcia/api-client`: `lint` + `typecheck` + `test` (`3` test files, `20` tests passed)
    - `@orcia/ui`: `lint` + `typecheck` + `test` (`35` test files, `142` tests passed, incl. `story-24-2-five-tabs-and-triggers-modal.test.tsx` `5/5`)
    - `@orcia/web`: `lint` + `typecheck` + `test` (**`79` test files, `299` tests passed**; total **`117` files / `461` JS/TS tests passed**), including:
      - `workspaces-single-tabs-anti-stacking-audit.test.tsx` (`3/3`)
      - `story-28-1-single-workspace-header-and-zero-uuid.test.tsx` (`2/2`)
      - `story-28-2-canonical-five-tabs-and-tab1-sobriety.test.tsx` (`2/2`)
      - `story-28-3-scoped-sources-deliverables-and-members-tabs.test.tsx` (`2/2`)
      - `story-24-2-spaces-day0-dna-waivers-and-triggers.test.tsx` (`3/3`)
      - `i18n-and-shell.test.tsx` (`26/26`)
      - `zero-dead-buttons-and-silent-catches-audit.test.tsx` (`4/4`)
      - `e2e-testids-sync-audit.test.ts` (`1/1`)
      - `i18n-hardcoded-locale-ast-audit.test.ts` (`3/3`), `i18n-dictionary-parity-and-jargon-audit.test.ts` (`2/2`), `client-error-code-resolution.test.ts` (`9/9`)
- **Python Static, Security & Architecture Gates**:
  - `.venv/bin/ruff check .`: passed (`0` errors)
  - `.venv/bin/ruff format --check .`: passed (`1710 files already formatted`)
  - `.venv/bin/mypy --strict packages/orcia-core apps/api apps/worker`: passed (`795 source files`)
  - `.venv/bin/lint-imports`: passed (`5 kept, 0 broken`, `888` files / `6371` deps)
  - `lint_spine.py`: passed (`ok: true`, `total_findings: 0`)
  - `.venv/bin/detect-secrets-hook`: passed (`0` findings)
  - `gitnexus_detect_changes(scope="all")` on refreshed worktree index (`45,803` nodes / `103,007` edges / `1540` flows): `changed_count: 72`, `affected_count: 0`, `changed_files: 42`, `risk_level: "low"`.
- **Follow-Up Scope (`ACTION_ITEM-28.1: open`)**: Backend workspace-scoped `PATCH /api/v1/workspaces/{id}` for non-admin `TEAM_LEAD` / `personal-*` transitions and full interactive Tab 1/3/5 PG18 endpoints are tracked explicitly under `ACTION_ITEM-28.1` in `docs/implementation-artifacts/sprint-status.yaml`.

### 3.3 AD-17 Test Pyramid & Vertical Wiring Verification
- **Layer 1b — Frontend TS (`Vitest` under real `<RouterProvider>`, zero `isJsdom` bypass)**: Verified all 6 `WX-01`..`WX-06` invariants (`workspaces-single-tabs-anti-stacking-audit.test.tsx` `3/3` in FR & EN), PG18 glossary candidate hydration (`listOntologyPromotions("PENDING_REVIEW", false)`), Top-3 approval and FIFO rejection (`decideOntologyPromotion`) surviving F5 remount, localized Starlark badge/explanation/breadcrumb, contributor non-escalation + `[role="alert"]` on Tab 2, conditional `supersededMemlogNotice` on Tab 1 (`5/5` in `story-24-2-five-tabs`), and `461` total JS/TS tests passing.
- **Layers 1a, 2, 4, Security**: Zero Python/backend/Alembic modifications required (`Story 28.4` reuses existing PG18 `ontology_promotion_proposals` / `ontology_concepts` / `workspace_dna_mechanisms` / `audit_ledger` endpoints); all Python static & `AD-19`/`AD-20` import-linter gates verified clean.
- **Layer 3 — Contract & Selector Audits**: `e2e-testids-sync-audit.test.ts` (`1/1`), `zero-dead-buttons-and-silent-catches-audit.test.tsx` (`4/4`), i18n Gates 1–3 (`3/3`, `2/2`, `9/9`), `lint_spine.py` (`0` findings), `check_implementation_docs.py`, and `pnpm site:sync && pnpm site:check` all passed.
- **Layer 5 — Dual-Server Playwright Desktop E2E (`env -u ORCIA_E2E_SEED_FIXTURES`, real PG18 + Redis 7.4 `testcontainers`)**:
  - Command: `timeout -k 10s 360s env -u ORCIA_E2E_SEED_FIXTURES pnpm --filter @orcia/web exec playwright test --project=desktop-cockpit e2e/07-spaces-org-and-workspace-persistence.spec.ts e2e/17-workspace-sources-codegraph-dna-and-ontology.spec.ts e2e/21-assistant-citations-v5-audit-help-showcase.spec.ts`
  - Result: **`6 passed (1.9m)`** (`0` failed, `0` skipped, `0` retries):
    - `07-spaces-org-and-workspace-persistence.spec.ts`: `1/1` passed (`15.5s`) — org/workspace persistence, cold F5 reload, unified `workspaces-compact-header` & `workspaces-active-title`, single 5-tab container, strict Tab 4 `dna-starlark-glossary-view` gating, and FR/EN bilingual locale switching.
    - `17-workspace-sources-codegraph-dna-and-ontology.spec.ts`: `3/3` passed (`12.0s`, `13.3s`, `16.3s`) — multi-nature sources & CodeGraph + F5, L4→L3 glossary promotion & ontology approval + F5, and Starlark DNA compilation/activation strictly inside Tab 4 + waivers + deterministic tripartite RAG scope + F5.
    - `21-assistant-citations-v5-audit-help-showcase.spec.ts`: `2/2` passed (`13.9s`, plus help/showcase test) — assistant citations, V5 lock, `/spaces` contextual help Zone 4 check (`strong`/`code` formatting), and product showcase.
