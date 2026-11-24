# Story 28.3 — Scoped PG18 Consolidation of Tab 2 (`Documents & Sources`), Tab 3 (`Livrables & Artefacts`) & Tab 5 (`Membres & Paramètres de l'espace`)

- **Date**: 2026-11-24
- **Story / Sprint Key**: `28-3-scoped-pg18-sources-deliverables-and-members-tabs-consolidation` (`Epic 28` — Lot 2: Functional Tabs Consolidation)
- **Capability(ies)**: `CAP-067`, `CAP-080`, `CAP-180` — classification: `feature`
- **Author / Context**: Consolidate `/workspaces` ("Mes Espaces") Tabs 2, 3, and 5 onto scoped PostgreSQL 18 truth (`WX-01`, `WX-04`, `WX-05`): eliminate the unscoped `PlatformSetupContext.datasources` duplicate in `WorkspaceDnaAndWaiversSection` in favor of `client.listWorkspaceDatasources(targetWorkspace.workspaceId)`, hide category filter pills on Tab 2 when `datasources.length === 0 && activeNatureFilter === "ALL"` (`DESIGN.md:L198`), consolidate Tab 3 deliverables & `ExternalEditRebaser` (`Lock V2`) with sanitized URIs, and consolidate Tab 5 members, PG18-persisted workspace instructions (`getAssistantGovernance` / `updateAssistantWorkspaceSettings`), and workspace settings controls (`lifecyclePhase` / `visibilityMode` / team sharing).
- **Associated Commits**: Pending closure

---

## 1. Needs Analysis & Tech Lead Impact Study (Pre-Implementation)

### 1.1 Context & Problem Statement
- **Current behavior**:
  1. **Unscoped Datasources (`WX-04`)**: `WorkspacesFeaturePanel` (`apps/web/src/features/workspaces/index.tsx:L166`) passes `PlatformSetupContext.datasources` (global/unscoped) into `WorkspaceDnaAndWaiversSection.tsx`, which forwards it to `WorkspaceFiveTabsAndExternalRebaseView` (driving Tab 1 `sourcesCount`, Tab 2 badge, `defaultArtifactDestinationUri`, and waiver availability) and as `fallbackDatasources` to `WorkspaceSourcesRagTab.tsx`. Meanwhile, `WorkspaceSourcesRagTab.tsx:L87` fetches `client.listWorkspaceDatasources(wsId)` internally without notifying `WorkspaceDnaAndWaiversSection` when sources are loaded, attached, edited, synced, or deleted — nor clearing stale state immediately on workspace switch.
  2. **Tab 2 Empty Filter Pill Clutter (`WX-05`)**: `WorkspaceSourcesMasterTable.tsx:L106-129` unconditionally renders all 5 category filter pills (`sources-filter-pill-all`, `sources-filter-pill-document_kb`, `sources-filter-pill-work_tracker`, `sources-filter-pill-source_code`, `sources-filter-pill-relational_schema`) even when `datasources.length === 0 && activeNatureFilter === "ALL"`, cluttering an empty workspace above `workspace-sources-empty-state`.
  3. **Tab 3 Deliverables & Rebase Consolidation (`WX-01`)**: `DeliverablesTabPanel` (`packages/ui/src/primitives/WorkspaceFiveTabsPanels.tsx:L201-246`) sanitizes `defaultArtifactDestinationUri` with hardcoded `"ws"` instead of `safeSlug`, displays `supersededMemlogNotice` even when `rebasedChunks.length === 0`, and lacks a scoped deliverables catalog list (`orcia://` CAS `@vN` / scoped runs) cleanly separated from header chrome.
  4. **Tab 5 Ephemeral RAM Instructions & Split Controls (`WX-01`, `WX-04`)**: `WorkspaceMembersInstructionsCard.tsx:L23-24` stores workspace instructions in an ephemeral `useState<Record<string, string>>({})` that disappears on `F5` reload instead of hydrating from and persisting to PostgreSQL 18 via `client.getAssistantGovernance(wsId)` / `client.updateAssistantWorkspaceSettings(...)`. Additionally, Tab 5 lacks a consolidated view of owner team members/access roles and workspace lifecycle/visibility/sharing controls synced to PG18.
- **Expected behavior**:
  - `useWorkspaceDnaAndWaivers.ts` fetches `client.listWorkspaceDatasources(targetWorkspace.workspaceId)` directly and exposes `scopedDatasources` + `reloadScopedDatasources` / `handleSourcesChanged` so Tab 1, Tab 2, Tab 3, and waivers share a single scoped PG18 source of truth.
  - `WorkspaceSourcesMasterTable.tsx` hides the 5 `sources-filter-pill-*` buttons when `datasources.length === 0 && natureFilter === "ALL"` while keeping `open-attach-source-modal-btn`, `workspace-sources-reconcile-btn`, and `workspace-sources-empty-state` (with pedagogical 1-sentence guidance) accessible, and renders all 5 filter pills whenever `datasources.length >= 1` or `natureFilter !== "ALL"`.
  - Tab 3 (`workspace-deliverables-panel`) renders the sanitized default destination (`safeSlug`, zero `personal-<uuid>`), scoped deliverables catalog when present, `ExternalEditRebaser` (`rebased-chunk-*`, `human-amended-badge-*` Lock V2) when `rebasedChunks.length > 0`, and a concise pedagogical empty state (`workspace-deliverables-empty-state`) when empty — without repeating header chrome.
  - Tab 5 (`workspace-members-panel`) renders team members & effective access summary, PG18-persisted workspace instructions (`getAssistantGovernance` + `updateAssistantWorkspaceSettings` with `[role="alert"]` error handling and `workspace-instructions-saved-badge` confirmed on server success), and workspace settings controls (lifecycle phase, visibility, team sharing) synced to PG18 while preserving all `WorkspaceCompactHeader` controls and `data-testid`s.
  - `DnaStarlarkCompilerAndGlossaryLifecycleView` stays outside Tab 4 for Story 28.3 (its encapsulation inside Tab 4 is strictly scoped to Story 28.4).
- **Architectural constraints**:
  - Every modified or created `.ts`/`.tsx` file MUST stay **`<= 300` lines** (`wc -l`).
  - 100% bilingual `fr`/`en` via `apps/web/src/i18n/locales/*.ts` (symmetric keys, zero inline `locale === "fr"` ternaries, zero hardcoded UI strings in `@orcia/ui`, zero UX Rule 3.1 jargon).
  - `e2e-testids-sync-audit.test.ts` and `zero-dead-buttons-and-silent-catches-audit.test.tsx` MUST pass with `0` regressions.

### 1.2 Exploration, GitNexus Impact Analysis, Refactoring & Technical Debt
- **GitNexus Impact Analysis (`gitnexus_query`, `gitnexus_context`, `gitnexus_impact`, repo `/home/romain/.gemini/antigravity/worktrees/ORCIA/analyze_ui_screenshot`)**:
  - `useWorkspaceDnaAndWaivers`: 1 direct caller (`WorkspaceDnaAndWaiversSection.tsx`); `context()` confirms clean isolation.
  - `WorkspaceSourcesMasterTable`: upstream impact `LOW` (`impactedCount: 3`: `WorkspaceSourcesRagTab` d=1 → `WorkspaceDnaAndWaiversSection` d=2 → `WorkspacesFeaturePanel` d=3).
  - `WorkspaceFiveTabsAndExternalRebaseView`: upstream impact `LOW` (`impactedCount: 3`: `WorkspaceDnaAndWaiversSection` d=1 → `WorkspacesFeaturePanel` d=2 → `ModuleWorkspaceView` d=3), plus direct Vitest specs in `packages/ui/src/__tests__/`.
  - `WorkspaceMembersInstructionsCard`: upstream impact `LOW` (`impactedCount: 3`: `WorkspaceDnaAndWaiversSection` d=1 → `WorkspacesFeaturePanel` d=2 → `ModuleWorkspaceView` d=3).
- **Refactoring Opportunities & Emerging Technical Debt Mitigation**:
  - `packages/ui/src/primitives/WorkspaceFiveTabsPanels.tsx` is currently `297` lines. Extract `DeliverablesTabPanel` and `MembersTeamTabPanel` into `packages/ui/src/primitives/WorkspaceFiveTabsDeliverablesAndMembersPanels.tsx` (`<= 175` lines) so both files remain well below `250` lines.
  - Extract Tab 5 team members & workspace settings controls into `apps/web/src/features/workspaces/WorkspaceMembersAndSettingsTab.tsx` (`<= 175` lines) composing `WorkspaceMembersInstructionsCard.tsx` (`<= 165` lines) so `WorkspaceDnaAndWaiversSection.tsx` and `WorkspaceMembersInstructionsCard.tsx` stay well below `300` lines.
  - `WorkspaceSourcesRagTab.tsx` is `292` lines — keep changes surgical (`<= 298` lines).

---

## 2. Implementation Plan

### 2.1 Data Schema & Alembic Migrations (`infra/migrations/versions/...`)
- None required (backend PG18 endpoints `listWorkspaceDatasources`, `getAssistantGovernance`, `updateAssistantWorkspaceSettings`, `listWorkspaceExceptionWaivers`, `listDnaMechanisms`, and `savePlatformSetupState` already exist).

### 2.2 Hexagonal Core, Orchestration & Workers (`packages/orcia-core/`, `apps/worker/`, `infra/sandbox/`)
- None required.

### 2.3 Backend API, Security & Contracts (`apps/api/`, `packages/api-client/`)
- None required (reuses existing typed `@orcia/api-client` methods).

### 2.4 User Interface & Experience (`apps/web/`, `packages/ui/`)
1. **i18n Dictionaries (`apps/web/src/i18n/locales/feature_workspaces_labels*.ts` & `governance_and_packs_labels_*.ts`)**:
   - Add symmetric FR/EN keys (zero UX Rule 3.1 jargon):
     - `featureWorkspaces.sources.emptyWorkspaceMessage`: 1-sentence pedagogical empty guidance when `0` sources are attached.
     - `featureWorkspaces.detailTabs`: `saveInstructionsBtn`, `instructionsTooShortHint`, `instructionsErrorContext`, `membersRosterTitle`, `membersLeadsLabel`, `membersListLabel`, `membersEmptyHint`, `workspaceSettingsTitle`, `workspaceSettingsPhaseLabel`, `workspaceSettingsVisibilityLabel`.
     - `workspaceFiveTabs`: `deliverablesCatalogTitle`, `deliverableVersionPrefix` (used cleanly via typed labels in `@orcia/ui`).
2. **`@orcia/ui` 5-Tab Primitives (`packages/ui/src/primitives/` & `packages/ui/src/index.ts`)**:
   - Create `WorkspaceFiveTabsDeliverablesAndMembersPanels.tsx` hosting `DeliverablesTabPanel` (sanitized destination URI using `safeSlug`, deliverables catalog list `workspace-deliverables-list`, conditional `ExternalEditRebaser` Lock V2 section when `rebasedChunks.length > 0`, concise `workspace-deliverables-empty-state` when `0` deliverables & chunks) and `MembersTeamTabPanel`.
   - Update `WorkspaceFiveTabsPanels.tsx` to re-export `DeliverablesTabPanel` and `MembersTeamTabPanel` if needed and stay `<= 220` lines.
   - Update `WorkspaceFiveTabsAndExternalRebaseView.tsx` & `packages/ui/src/index.ts` to export `WorkspaceDeliverableItem` and accept optional `deliverables?: readonly WorkspaceDeliverableItem[]` + `deliverablesTabSlot?: React.ReactNode`.
3. **Scoped Sources & Tab 2 Sobriety (`apps/web/src/features/workspaces/`)**:
   - Update `useWorkspaceDnaAndWaivers.ts` to fetch `client.listWorkspaceDatasources(targetWsId)`, clear on workspace change, and expose `scopedDatasources`, `reloadScopedDatasources`, and `setScopedDatasources`.
   - Update `WorkspaceSourcesRagTab.tsx` to reset stale state on `wsId` change and call `onSourcesChanged?.(dsRes.items)` whenever scoped datasources load or mutate.
   - Update `sources/WorkspaceSourcesMasterTable.tsx` to hide the 5 `sources-filter-pill-*` buttons when `datasources.length === 0 && natureFilter === "ALL"`, show `sourcesCopy.emptyWorkspaceMessage` in `workspace-sources-empty-state` at `0` sources (`emptyFilterMessage` when filtered out), and keep `+ Rattacher une source` + `Vérifier fraîcheur` accessible.
   - Update `WorkspaceDnaAndWaiversSection.tsx` & `index.tsx` to pass `runs`, `onUpdateWorkspacePhase`, and `onUpdateWorkspaceVisibility`, derive scoped `deliverables` from `runs` matching `targetWorkspace.workspaceId`, and eliminate the unscoped `datasources` list completely.
4. **Tab 5 Members, PG18 Instructions & Settings (`WorkspaceMembersInstructionsCard.tsx` & `WorkspaceMembersAndSettingsTab.tsx`)**:
   - Update `WorkspaceMembersInstructionsCard.tsx` to hydrate `workspace_instructions` and `canEditWorkspaceLayer` from `client.getAssistantGovernance(activeWorkspace.workspaceId)` and persist via `client.updateAssistantWorkspaceSettings(...)` (preserving existing workspace governance fields), supporting both debounced auto-save (`>= 3` chars) and explicit Save CTA (`workspace-instructions-save-btn`), showing `workspace-instructions-saved-badge` only after persistence succeeds and surfacing `>= 400` errors via `onFeedback` / `[role="alert"]`.
   - Create `WorkspaceMembersAndSettingsTab.tsx` displaying team leads/members from `orgUnits` (`ownerOrgUnitId`), workspace settings selects/share action (`workspace-settings-phase-select-*`, `workspace-settings-visibility-select-*`, `workspace-settings-share-btn-*`), and `<WorkspaceMembersInstructionsCard />`, without duplicating `WorkspaceCompactHeader` testids.

### 2.5 Test Pyramid Impact Analysis (`AD-17`)
- **Layer 1b (`@orcia/ui` & `@orcia/web` Vitest)**:
  - Update `apps/web/src/__tests__/setup/assistantGovernanceMockHandlers.ts` to key `workspaceSettings` per `workspace_id` with default fallback so multi-workspace & F5 remount tests verify true workspace-scoped PG18 persistence.
  - Update `apps/web/src/__tests__/story-28-2-canonical-five-tabs-and-tab1-sobriety.test.tsx` (`withActivity: true`) to seed `seedVitestConnectorsInitialData` so `listWorkspaceDatasources(WS_ID)` returns the seeded scoped source cleanly.
  - Verify `apps/web/src/__tests__/i18n-and-shell.test.tsx` (`L2147-2220`) asserts `0`-source filter pill hiding, `>= 1`-source filter pill visibility, and awaited PG18 persistence of `workspace-instructions-saved-badge`.
  - Verify `apps/web/src/__tests__/story-18-1-workspace-sources-route-modal-and-f5.test.tsx` and `packages/ui/src/__tests__/story-24-2-five-tabs-and-triggers-modal.test.tsx`.
  - Create `apps/web/src/__tests__/story-28-3-scoped-sources-deliverables-and-members-tabs.test.tsx` covering: (1) scoped `listWorkspaceDatasources` isolation across two workspaces, (2) Tab 2 filter pill hiding at `0` sources vs visibility at `>= 1` source, (3) Tab 3 deliverables catalog (`orcia://` `@vN`) + Lock V2 `rebased-chunk-*` + sanitized URI (zero `personal-<uuid>`) + empty state, (4) Tab 5 PG18 persisted instructions, team members, lifecycle/visibility/share settings with `F5` remount survival and `[role="alert"]` error handling, and (5) bilingual `fr` & `en` rendering.
  - Run typechecks (`@orcia/ui`, `@orcia/web`) and i18n/audit gates (`e2e-testids-sync-audit`, `i18n-hardcoded-locale-ast-audit`, `i18n-dictionary-parity-and-jargon-audit`, `zero-dead-buttons-and-silent-catches-audit`).
- **Layer 5 (Playwright E2E — deferred to Story 28.4 E2E lock)**:
  - `17-workspace-sources-codegraph-dna-and-ontology.spec.ts` and `07-spaces-org-and-workspace-persistence.spec.ts` selectors preserved (`e2e-testids-sync-audit` 0 missing).

---

## 3. Summary of Changes & Results (Post-Implementation)

### 3.1 Created & Modified Files

| File | Action | Line Count (`wc -l`) | Concise Summary |
| :--- | :--- | :--- | :--- |
| `packages/ui/src/primitives/WorkspaceFiveTabsDeliverablesAndMembersPanels.tsx` | Created | `187` | Extracted `DeliverablesTabPanel` (sanitized URI via `safeSlug`, deliverables catalog `workspace-deliverables-list`, conditional Lock V2 `ExternalEditRebaser`, empty state `workspace-deliverables-empty-state`) and `MembersTeamTabPanel`. |
| `packages/ui/src/primitives/WorkspaceFiveTabsPanels.tsx` | Modified / Split | `194` | Split deliverables/members panels out into `WorkspaceFiveTabsDeliverablesAndMembersPanels.tsx` and re-exported them (`297` $\rightarrow$ `194` L). |
| `packages/ui/src/primitives/WorkspaceFiveTabsAndExternalRebaseView.tsx` | Modified | `294` | Exported `WorkspaceDeliverableItem` and added `deliverables` + `deliverablesTabSlot` props and `deliverablesCatalogTitle`/`deliverableVersionPrefix` labels. |
| `packages/ui/src/index.ts` | Modified | `781` (barrel) | Exported `WorkspaceDeliverableItem` and updated 5-tab barrel exports. |
| `apps/web/src/features/workspaces/useWorkspaceDnaAndWaivers.ts` | Modified | `198` | Added scoped `client.listWorkspaceDatasources(targetWsId)` fetching, workspace-switch state reset, and `scopedDatasources` / `reloadScopedDatasources` / `setScopedDatasources`. |
| `apps/web/src/features/workspaces/WorkspaceDnaAndWaiversSection.tsx` | Modified | `273` | Eliminated unscoped `datasources` prop; wired `scopedDatasources`, derived scoped `deliverables` from `runs`, and passed `WorkspaceMembersAndSettingsTab` into `membersTabSlot`. |
| `apps/web/src/features/workspaces/index.tsx` | Modified | `219` | Passed `runs`, `onUpdateWorkspacePhase`, and `onUpdateWorkspaceVisibility` to `WorkspaceDnaAndWaiversSection` and removed unscoped `datasources` prop. |
| `apps/web/src/features/workspaces/WorkspaceSourcesRagTab.tsx` | Modified | `295` | Reset stale state on workspace change and notified `onSourcesChanged` on PG18 load/mutation. |
| `apps/web/src/features/workspaces/sources/WorkspaceSourcesMasterTable.tsx` | Modified | `223` | Hid the 5 `sources-filter-pill-*` buttons when `datasources.length === 0 && natureFilter === "ALL"` while preserving attach/reconcile CTAs and showing pedagogical `emptyWorkspaceMessage`. |
| `apps/web/src/features/workspaces/sources/WorkspaceSourcesFallbackHelper.ts` | Modified | `60` | Updated fallback helper alignment for scoped workspace datasource resolution. |
| `apps/web/src/features/workspaces/WorkspaceMembersInstructionsCard.tsx` | Modified | `230` | Replaced ephemeral `useState` map with PG18 hydration (`getAssistantGovernance`) and persistence (`updateAssistantWorkspaceSettings`), explicit save CTA, saved badge on success, and `[role="alert"]` errors. |
| `apps/web/src/features/workspaces/WorkspaceMembersAndSettingsTab.tsx` | Created | `233` | Consolidated Tab 5 team roster (`orgUnits`), lifecycle phase / visibility / team sharing controls synced to PG18, and `<WorkspaceMembersInstructionsCard />`. |
| `apps/web/src/i18n/locales/feature_workspaces_labels.ts` | Modified | `144` | Added typed symmetric i18n keys for Tab 2 empty guidance and Tab 5 members, instructions, and workspace settings. |
| `apps/web/src/i18n/locales/feature_workspaces_labels_fr.ts` | Modified | `153` | Added French labels for Tab 2 empty guidance and Tab 5 consolidation. |
| `apps/web/src/i18n/locales/feature_workspaces_labels_en.ts` | Modified | `153` | Added English labels for Tab 2 empty guidance and Tab 5 consolidation. |
| `apps/web/src/i18n/locales/governance_and_packs_labels_fr.ts` | Modified | `183` | Added French `deliverablesCatalogTitle` and `deliverableVersionPrefix` labels. |
| `apps/web/src/i18n/locales/governance_and_packs_labels_en.ts` | Modified | `180` | Added English `deliverablesCatalogTitle` and `deliverableVersionPrefix` labels. |
| `apps/web/src/__tests__/setup/assistantGovernanceMockHandlers.ts` | Modified | `182` | Keyed `workspaceSettings` per `workspace_id` with default fallback for multi-workspace & `F5` remount verification. |
| `apps/web/src/__tests__/setup/mockBackendState.ts` | Modified | `363` | Updated mock backend state for scoped workspace governance/datasources persistence. |
| `apps/web/src/__tests__/story-28-2-canonical-five-tabs-and-tab1-sobriety.test.tsx` | Modified | `195` | Seeded `seedVitestConnectorsInitialData` in `withActivity: true` scenario for scoped `listWorkspaceDatasources`. |
| `apps/web/src/__tests__/i18n-and-shell.test.tsx` | Modified | `2313` | Updated assertions for `0`-source pill hiding, `>= 1`-source pill visibility, and awaited PG18 persistence of `workspace-instructions-saved-badge`. |
| `apps/web/src/__tests__/story-28-3-scoped-sources-deliverables-and-members-tabs.test.tsx` | Created | `281` | Added Story 28.3 Vitest suite covering multi-workspace scoped datasources isolation, Tab 2 filter pill sobriety, Tab 3 deliverables + Lock V2 + sanitized URI, Tab 5 PG18 instructions/members/settings + `F5` survival + error alert, and FR/EN bilingual rendering. |
| `packages/ui/src/__tests__/story-24-2-five-tabs-and-triggers-modal.test.tsx` | Modified | `260` | Updated 5-tab primitive spec props (`deliverablesCatalogTitle`, `deliverableVersionPrefix`). |

### 3.2 Quantitative Metrics, Coverage & Static Quality
- **Production file-size compliance (`wc -l <= 300`)**: `16/16` Story 28.3 non-barrel production `.ts`/`.tsx` files are `<= 295` lines (max `295` L in `WorkspaceSourcesRagTab.tsx`, `294` L in `WorkspaceFiveTabsAndExternalRebaseView.tsx`).
- **JS/TS Monorepo Verification (`pnpm turbo run lint typecheck test`)**: **`9/9` tasks successful** (`0` lint/typecheck errors):
  - `@orcia/api-client`: `lint` + `typecheck` + `test` (`3` test files, `20` tests passed — cached)
  - `@orcia/ui`: `lint` + `typecheck` + `test` (**`35` test files, `141` tests passed**, incl. `story-24-2-five-tabs-and-triggers-modal.test.tsx`)
  - `@orcia/web`: `lint` + `typecheck` + `test` (**`78` test files, `296` tests passed**, incl. `story-28-3-scoped-sources-deliverables-and-members-tabs.test.tsx` `2/2`, `story-28-2` passed, `i18n-and-shell.test.tsx` `26/26`, `i18n-hardcoded-locale-ast-audit.test.ts` `3/3`, `i18n-dictionary-parity-and-jargon-audit.test.ts` `2/2`, `zero-dead-buttons-and-silent-catches-audit.test.tsx` `4/4`, `e2e-testids-sync-audit.test.ts` `1/1`)
- **Architecture & Governance Gates**:
  - `lint_spine.py`: `ok: true`, `total_findings: 0`
  - `check_implementation_docs.py` & `pnpm site:sync && pnpm site:check`: Verified post-report update (`0` errors)
  - `gitnexus_detect_changes()` (`scope: "all"` on worktree): `changed_count: 51`, `changed_files: 21`, `affected_count: 0`, `risk_level: "low"`

### 3.3 AD-17 Test Pyramid & Vertical Wiring Verification
- **Layer 1b — Frontend TS (`Vitest` under real `RouterProvider`, zero `isJsdom` bypass)**: Verified scoped `listWorkspaceDatasources` isolation across workspaces, Tab 2 filter pill hiding at `0` sources vs visibility at `>= 1` source, Tab 3 sanitized URIs + deliverables catalog + Lock V2 `rebased-chunk-*`, Tab 5 PG18 persisted instructions/members/settings with `F5` remount survival and `[role="alert"]` error handling, and full FR/EN parity across `457` total JS/TS tests (`20 + 141 + 296`).
- **Layer 3 — Contract & Selector Audits**: `e2e-testids-sync-audit.test.ts` (`1/1`), `zero-dead-buttons-and-silent-catches-audit.test.tsx` (`4/4`), `i18n-hardcoded-locale-ast-audit.test.ts` (`3/3`), `i18n-dictionary-parity-and-jargon-audit.test.ts` (`2/2`), and `lint_spine.py` (`0` findings) all passed.
- **Layers 1a, 2, 4, Security**: Not impacted (zero Python/backend/Alembic modifications in Story 28.3; all mutations reuse existing PG18 endpoints).
- **Layer 5 — Playwright E2E**: Deferred to Story `28.4` (`28-4-tab4-glossary-dna-starlark-encapsulation-and-e2e-lock`); selector compatibility verified via `e2e-testids-sync-audit.test.ts` (`1/1` passed).
