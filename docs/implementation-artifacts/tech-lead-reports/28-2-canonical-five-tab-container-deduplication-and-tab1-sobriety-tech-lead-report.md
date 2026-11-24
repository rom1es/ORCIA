# Story 28.2 — Canonical 5-Tab Workspace Container, De-Duplication of 3-Tab vs 5-Tab Panels & Direction C `total == 0` Sobriety on Tab 1

- **Date**: 2026-11-24
- **Story / Sprint Key**: `28-2-canonical-five-tab-container-deduplication-and-tab1-sobriety` (`Epic 28` — Lot 1: Container & Tab 1 Consolidation)
- **Capability(ies)**: `CAP-061`, `CAP-080` — classification: `ux`
- **Author / Context**: Unified `/workspaces` ("Mes Espaces") 5-tab workspace container (`WX-01`, `WX-05`), consolidating the competing 3-tab (`WorkspaceDetailTabsPanel`) and 5-tab (`WorkspaceFiveTabsAndExternalRebaseView`) panels into a single canonical `[role="tablist"]` while enforcing Direction C `total == 0` sobriety (`DESIGN.md` §Brand & Style #3 & §Do's and Don'ts `L198`) on Tab 1 (`Accostage & Vue d'ensemble`).
- **Associated Commits**: Pending closure

---

## 1. Needs Analysis & Tech Lead Impact Study (Pre-Implementation)

### 1.1 Context & Problem Statement
- **Current behavior**:
  1. `WorkspacesFeaturePanel` (`apps/web/src/features/workspaces/index.tsx`) mounts `<WorkspaceStudioCardsAndDetailView />` followed by `<WorkspaceDnaAndWaiversSection />`.
  2. `WorkspaceStudioCardsAndDetailView` (`142` lines) mounts `WorkspaceDetailTabsPanel` (`211` lines), which renders a **3-tab** bar (`workspace-detail-tab-sources`, `workspace-detail-tab-glossary`, `workspace-detail-tab-members`) hosting `WorkspaceSourcesRagTab`, `WorkspaceGlossaryAndOntologyTab`, and the workspace members & instructions textarea (`workspace-detail-members-content`, `workspace-instructions-textarea`, `workspace-instructions-saved-badge`).
  3. Immediately below it, `WorkspaceDnaAndWaiversSection` (`147` lines) mounts `WorkspaceFiveTabsAndExternalRebaseView` (`290` lines), which renders a **competing 5-tab** bar (`workspace-tab-OVERVIEW`, `workspace-tab-DOCUMENTS_SOURCES`, `workspace-tab-DELIVERABLES_ARTIFACTS`, `workspace-tab-GLOSSARY_RULES`, `workspace-tab-MEMBERS_TEAM`).
  4. On Tab 1 (`OVERVIEW`), `WorkspaceFiveTabsAndExternalRebaseView` unconditionally renders a 4-card KPI counter grid (`0 / 0 / 0`) even when the workspace has `sources.length === 0 && pendingGlossaryCandidatesCount === 0 && activeWaivers.length === 0`, violating Direction C `total == 0` sobriety (`WX-05`).
- **Expected behavior**:
  - `/workspaces` renders **strictly one** workspace `[role="tablist"]` (`workspace-five-tabs-view`) with the 5 canonical tabs (`OVERVIEW`, `DOCUMENTS_SOURCES`, `DELIVERABLES_ARTIFACTS`, `GLOSSARY_RULES`, `MEMBERS_TEAM`), completely removing `WorkspaceDetailTabsPanel` (`workspace-detail-tabs-panel` and `workspace-detail-tab-*`).
  - `WorkspaceFiveTabsAndExternalRebaseView` exposes optional ReactNode slots (`sourcesTabSlot?`, `glossaryTabSlot?`, `membersTabSlot?`) so:
    - Tab 2 (`DOCUMENTS_SOURCES`) mounts `WorkspaceSourcesRagTab` inside `workspace-sources-panel` (falling back to `SourcesTabListPanel` when `sourcesTabSlot` is omitted so `@orcia/ui` unit tests stay intact).
    - Tab 4 (`GLOSSARY_RULES`) mounts `WorkspaceGlossaryAndOntologyTab` inside `workspace-glossary-rules-panel` (preserving existing fallback content when `glossaryTabSlot` is omitted).
    - Tab 5 (`MEMBERS_TEAM`) mounts the workspace members & instructions panel (`workspace-detail-members-content`, `workspace-instructions-textarea`, `workspace-instructions-saved-badge`) alongside the team member access summary inside `workspace-members-panel` (preserving existing fallback content when `membersTabSlot` is omitted).
  - Route `initialTab` maps `"sources"` / `"SOURCES"` (e.g., `/workspaces/$wsId/sources`) to `"DOCUMENTS_SOURCES"`, `"glossary"` to `"GLOSSARY_RULES"`, `"members"` to `"MEMBERS_TEAM"`, `"deliverables"` to `"DELIVERABLES_ARTIFACTS"`, and otherwise defaults to `"OVERVIEW"`.
  - On Tab 1 (`OVERVIEW`), when `sources.length === 0 && pendingGlossaryCandidatesCount === 0 && activeWaivers.length === 0`, the `0 / 0 / 0` KPI counter grid is hidden and replaced by a single-sentence pedagogical empty-state hint passed via `WorkspaceFiveTabsLabels.overviewEmptyStateHint` (`fr`/`en`). When `>= 1` source, candidate, or waiver exists, the KPI grid renders normally.
  - `DnaStarlarkCompilerAndGlossaryLifecycleView` remains in `WorkspaceDnaAndWaiversSection` for Story 28.2 (relocation inside Tab 4 is scoped to Story 28.4).
- **Architectural constraints**:
  - All modified and newly created `.ts`/`.tsx` files must remain `<= 300` lines (`wc -l`).
  - 100% bilingual `fr`/`en` via typed dictionaries (`apps/web/src/i18n/locales/`); zero hardcoded user-facing strings or inline `locale === "fr"` ternaries in `@orcia/ui` or `apps/web`.
  - `e2e-testids-sync-audit.test.ts` and `zero-dead-buttons-and-silent-catches-audit.test.tsx` must pass with `0` regressions.

### 1.2 Exploration, GitNexus Impact Analysis, Refactoring & Technical Debt
- **GitNexus Impact Analysis (`gitnexus_query`, `gitnexus_context`, `gitnexus_impact`)**:
  - Queried repository `ORCIA` (`/home/romain/Documents/Projects/ORCIA`) using `gitnexus_query({search_query: "WorkspaceDetailTabsPanel WorkspaceFiveTabsAndExternalRebaseView WorkspacesFeaturePanel"})`, `gitnexus_context({name: "WorkspaceDetailTabsPanel"})`, and `gitnexus_impact({target: "WorkspaceFiveTabsAndExternalRebaseView", direction: "upstream"})`.
  - Because the current GitNexus graph index does not retain individual React TSX function symbol nodes (`Symbol not found`), complete upstream caller and selector verification was performed across `apps/web/` and `packages/ui/`:
    - `WorkspaceDetailTabsPanel`: imported exclusively by `apps/web/src/features/workspaces/WorkspaceStudioCardsAndDetailView.tsx:L17` (`0` other imports); safe to delete after migrating its members/instructions card and tab routing into `WorkspaceDnaAndWaiversSection` + `WorkspaceFiveTabsAndExternalRebaseView`.
    - `workspace-detail-tab-{sources,glossary,members}`: referenced only in `apps/web/e2e/support/workspaceAndCatalogHelpers.ts:L100` (`openWorkspaceGlossaryTab`) and `apps/web/src/__tests__/i18n-and-shell.test.tsx:L2162, L2206, L2234`.
    - `WorkspaceFiveTabsAndExternalRebaseView`: exported from `packages/ui/src/index.ts`, rendered by `apps/web/src/features/workspaces/WorkspaceDnaAndWaiversSection.tsx`, and tested by `packages/ui/src/__tests__/story-24-2-five-tabs-and-triggers-modal.test.tsx` and `packages/ui/src/__tests__/workspace-governance-and-packs.test.tsx`.
    - `WorkspaceStudioCardsAndDetailView`: imported by `apps/web/src/features/workspaces/index.tsx` and `apps/web/src/__tests__/story-24-6-packs-counters-microcopy-and-finops.test.tsx`. Preserving its prop contract ensures zero breakage in Story 24.6 tests.
- **Refactoring Opportunities & Emerging Technical Debt Mitigation**:
  - `packages/ui/src/primitives/WorkspaceFiveTabsPanels.tsx` (`298` lines) and `WorkspaceFiveTabsAndExternalRebaseView.tsx` (`290` lines) are near the `300`-line limit. Extract `OverviewTabPanel` and `GlossaryRulesTabPanel` into `packages/ui/src/primitives/WorkspaceFiveTabsOverviewAndGlossaryPanels.tsx` (`<= 140` lines) so all three files remain comfortably `<= 270` lines.
  - Extract the workspace instructions/members card from deleted `WorkspaceDetailTabsPanel.tsx` into `apps/web/src/features/workspaces/WorkspaceMembersInstructionsCard.tsx` (`<= 90` lines) so `WorkspaceDnaAndWaiversSection.tsx` stays `<= 220` lines.
  - Delete dead `apps/web/src/features/workspaces/WorkspaceDetailTabsPanel.tsx` (`211` lines eliminated).

---

## 2. Implementation Plan

### 2.1 Data Schema & Alembic Migrations (`infra/migrations/versions/...`)
- None required (frontend container deduplication and Tab 1 sobriety only).

### 2.2 Hexagonal Core, Orchestration & Workers (`packages/orcia-core/`, `apps/worker/`, `infra/sandbox/`)
- None required.

### 2.3 Backend API, Security & Contracts (`apps/api/`, `packages/api-client/`)
- None required.

### 2.4 User Interface & Experience (`apps/web/`, `packages/ui/`)
1. **i18n Dictionaries (`apps/web/src/i18n/locales/governance_and_packs_labels*.ts` & `feature_workspaces_labels*.ts`)**:
   - Add symmetric `overviewEmptyStateHint` (FR & EN, zero UX Rule 3.1 jargon) to `WorkspaceFiveTabsLabels` (`packages/ui/src/primitives/WorkspaceFiveTabsAndExternalRebaseView.tsx`) and populate it in `governance_and_packs_labels_fr.ts` and `governance_and_packs_labels_en.ts`.
   - Keep `featureWorkspaces.detailTabs` keys intact for `WorkspaceMembersInstructionsCard` (and reuse `featureWorkspaces` cleanly in both FR & EN).
2. **`@orcia/ui` 5-Tab Primitives (`packages/ui/src/primitives/`)**:
   - Create `WorkspaceFiveTabsOverviewAndGlossaryPanels.tsx` (`OverviewTabPanel` with `total == 0` sobriety gate hiding `workspace-overview-kpi-grid` when `sources.length === 0 && pendingGlossaryCandidatesCount === 0 && activeWaivers.length === 0` and displaying `workspace-overview-empty-hint` instead; `GlossaryRulesTabPanel` supporting optional `glossaryTabSlot`).
   - Update `WorkspaceFiveTabsPanels.tsx` (`MembersTeamTabPanel` accepts optional `membersTabSlot?: React.ReactNode` rendered inside `workspace-members-panel` below the team access summary cards).
   - Update `WorkspaceFiveTabsAndExternalRebaseView.tsx` to accept `sourcesTabSlot?: React.ReactNode`, `glossaryTabSlot?: React.ReactNode`, `membersTabSlot?: React.ReactNode`, mounting `sourcesTabSlot` inside `workspace-sources-panel` (falling back to `SourcesTabListPanel` + `WaiversAndRebasePanel` when omitted), `glossaryTabSlot` inside `GlossaryRulesTabPanel`, and `membersTabSlot` inside `MembersTeamTabPanel`.
3. **`apps/web/src/features/workspaces/`**:
   - Delete `WorkspaceDetailTabsPanel.tsx`.
   - Update `WorkspaceStudioCardsAndDetailView.tsx` to render only `WorkspaceCompactHeader` and `workspaces-cards-empty-state` (when `!activeWorkspace`), removing `WorkspaceDetailTabsPanel`.
   - Create `WorkspaceMembersInstructionsCard.tsx` preserving `workspace-detail-members-content`, `workspace-instructions-textarea`, and `workspace-instructions-saved-badge`.
   - Update `WorkspaceDnaAndWaiversSection.tsx` and `index.tsx` to pass `initialTab`, `orgUnits`, `openHelpSection`, `onRegisterDatasource`, `onPromoteOntologyConcept`, map `initialTab` (`"sources"`/`"SOURCES"` -> `"DOCUMENTS_SOURCES"`, `"glossary"` -> `"GLOSSARY_RULES"`, `"members"` -> `"MEMBERS_TEAM"`, `"deliverables"` -> `"DELIVERABLES_ARTIFACTS"`, else `"OVERVIEW"`), sync on `initialTab` changes, and inject `sourcesTabSlot`, `glossaryTabSlot`, and `membersTabSlot` into `WorkspaceFiveTabsAndExternalRebaseView`.

### 2.5 Test Pyramid Impact Analysis (`AD-17`)
- **Layer 1b (`@orcia/ui` & `@orcia/web` Vitest)**:
  - Update `packages/ui/src/__tests__/story-24-2-five-tabs-and-triggers-modal.test.tsx` to verify both `total == 0` (KPI grid hidden, `workspace-overview-empty-hint` visible) and `total >= 1` (`workspace-overview-kpi-grid` visible).
  - Update `apps/web/src/__tests__/i18n-and-shell.test.tsx` (`L2144-2247`) to click `workspace-tab-DOCUMENTS_SOURCES`, `workspace-tab-GLOSSARY_RULES`, and `workspace-tab-MEMBERS_TEAM` instead of `workspace-detail-tab-*`.
  - Create `apps/web/src/__tests__/story-28-2-canonical-five-tabs-and-tab1-sobriety.test.tsx` verifying: (1) strictly 1 workspace `[role="tablist"]` with all 5 canonical tabs and 0 `workspace-detail-tabs-panel` / `workspace-detail-tab-*` in the DOM, (2) `initialTab="sources"` (`/workspaces/$wsId/sources`) opens `DOCUMENTS_SOURCES` directly (`workspace-sources-master-table-root` visible), (3) Tab 1 hides `0 / 0 / 0` KPI counter cards when `total == 0` and shows them when `total >= 1`, and (4) bilingual `fr` & `en` rendering.
  - Run `e2e-testids-sync-audit.test.ts`, `i18n-hardcoded-locale-ast-audit.test.ts`, `i18n-dictionary-parity-and-jargon-audit.test.ts`, `zero-dead-buttons-and-silent-catches-audit.test.tsx`, `story-28-1-*`, `story-18-1-*`, `story-22-2-*`, `story-24-2-*`.
- **Layer 5 (Playwright E2E — updated in lockstep for Testing Sub-Agent)**:
  - Update `apps/web/e2e/support/workspaceAndCatalogHelpers.ts` (`openWorkspaceGlossaryTab` clicking `workspace-tab-GLOSSARY_RULES` instead of `workspace-detail-tab-glossary`).

---

## 3. Summary of Changes & Results (Post-Implementation)

### 3.1 Created, Modified & Deleted Files
| File | Action (Created / Modified / Deleted) | Line Count | Concise Summary |
| :--- | :--- | :---: | :--- |
| `apps/web/src/features/workspaces/WorkspaceDetailTabsPanel.tsx` | Deleted | — | Removed the competing legacy 3-tab panel (`workspace-detail-tabs-panel` / `workspace-detail-tab-*`). |
| `packages/ui/src/primitives/WorkspaceFiveTabsOverviewAndGlossaryPanels.tsx` | Created | `131` | Extracted `OverviewTabPanel` (with `total == 0` sobriety gate hiding `workspace-overview-kpi-grid` and rendering `workspace-overview-empty-hint`) and `GlossaryRulesTabPanel` (supporting optional `glossaryTabSlot`). |
| `packages/ui/src/primitives/WorkspaceFiveTabsAndExternalRebaseView.tsx` | Modified | `276` | Added optional `sourcesTabSlot`, `glossaryTabSlot`, and `membersTabSlot` plus `WorkspaceFiveTabsLabels.overviewEmptyStateHint`; wired Tab 2 (`DOCUMENTS_SOURCES`), Tab 4 (`GLOSSARY_RULES`), and Tab 5 (`MEMBERS_TEAM`). |
| `packages/ui/src/primitives/WorkspaceFiveTabsPanels.tsx` | Modified | `297` | Delegated `OverviewTabPanel` and `GlossaryRulesTabPanel` to `WorkspaceFiveTabsOverviewAndGlossaryPanels.tsx` and added optional `membersTabSlot` inside `MembersTeamTabPanel`. |
| `apps/web/src/features/workspaces/WorkspaceMembersInstructionsCard.tsx` | Created | `85` | Extracted the workspace members & persistent instructions card (`workspace-detail-members-content`, `workspace-instructions-textarea`, `workspace-instructions-saved-badge`) from the deleted 3-tab panel. |
| `apps/web/src/features/workspaces/WorkspaceStudioCardsAndDetailView.tsx` | Modified | `119` | Removed `WorkspaceDetailTabsPanel` mounting; kept only `WorkspaceCompactHeader` and `workspaces-cards-empty-state` (`!activeWorkspace`). |
| `apps/web/src/features/workspaces/WorkspaceDnaAndWaiversSection.tsx` | Modified | `232` | Mapped route `initialTab` (`sources`, `glossary`, `members`, `deliverables`, `overview`) to canonical 5-tab keys and injected `sourcesTabSlot` (`WorkspaceSourcesRagTab`), `glossaryTabSlot` (`WorkspaceGlossaryAndOntologyTab`), and `membersTabSlot` (`WorkspaceMembersInstructionsCard`). |
| `apps/web/src/features/workspaces/index.tsx` | Modified | `217` | Propagated `initialTab`, `orgUnits`, `openHelpSection`, `onRegisterDatasource`, and `onPromoteOntologyConcept` to `WorkspaceDnaAndWaiversSection`. |
| `apps/web/src/i18n/locales/governance_and_packs_labels_fr.ts` | Modified | `182` | Added French `overviewEmptyStateHint` (zero jargon) for Tab 1 `total == 0` empty state. |
| `apps/web/src/i18n/locales/governance_and_packs_labels_en.ts` | Modified | `179` | Added English `overviewEmptyStateHint` (zero jargon) for Tab 1 `total == 0` empty state. |
| `apps/web/e2e/support/workspaceAndCatalogHelpers.ts` | Modified | `163` | Updated `openWorkspaceGlossaryTab` E2E helper to click canonical `workspace-tab-GLOSSARY_RULES`. |
| `apps/web/src/__tests__/story-28-2-canonical-five-tabs-and-tab1-sobriety.test.tsx` | Created | `173` | Added Story 28.2 Vitest suite (`2` tests) verifying strictly 1 `[role="tablist"]` with 5 canonical tabs (`0` `workspace-detail-tab-*`), `initialTab="sources"` direct opening, Tab 1 `total == 0` vs `total >= 1` KPI visibility, and FR/EN rendering. |
| `packages/ui/src/__tests__/story-24-2-five-tabs-and-triggers-modal.test.tsx` | Modified | `217` | Updated Story 24.2 5-tab `@orcia/ui` unit tests (`3` tests) to assert both `total == 0` (`workspace-overview-empty-hint`) and `total >= 1` (`workspace-overview-kpi-grid`). |
| `apps/web/src/__tests__/i18n-and-shell.test.tsx` | Modified | `2307` | Updated legacy shell/workspaces tab assertions (`26` tests) to click canonical `workspace-tab-DOCUMENTS_SOURCES`, `workspace-tab-GLOSSARY_RULES`, and `workspace-tab-MEMBERS_TEAM` (pre-existing legacy test file). |
| `docs/implementation-artifacts/sprint-status.yaml` | Modified | — | Marked `28-2-canonical-five-tab-container-deduplication-and-tab1-sobriety: done`. |

### 3.2 Quantitative Metrics, Coverage & Static Quality
- **Line-count discipline**: Every modified or created production `.ts`/`.tsx` file (`10/10`, max `297` lines), `workspaceAndCatalogHelpers.ts` (`163` lines), and the new/modified Story `28.2` & `24.2` test files (`173` and `217` lines) are `<= 300` lines.
- **JS/TS Monorepo Verification (`timeout -k 10s 300s pnpm turbo run lint typecheck test`)**:
  - **`9/9` Turbo tasks passed** (`@orcia/api-client`, `@orcia/ui`, `@orcia/web` — `lint`, `typecheck`, `test` in `59.01s`).
  - **`@orcia/api-client`**: `3` test files / `20` tests passed.
  - **`@orcia/ui`**: `35` test files / `140` tests passed.
  - **`@orcia/web`**: `77` test files / `294` tests passed (total **`115` files / `454` JS/TS tests passed**).
- **Architecture & Documentation Gates**:
  - `lint_spine.py --workspace docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24`: `ok: true`, `total_findings: 0`.
  - `scripts/check_implementation_docs.py`: passed (`0` errors).
  - `pnpm site:sync && pnpm site:check`: passed (`0` errors).

### 3.3 AD-17 Test Pyramid & Vertical Wiring Verification
- **Layer 1b — Frontend TS (`Vitest` without `isJsdom` short-circuits)**:
  - `story-28-2-canonical-five-tabs-and-tab1-sobriety.test.tsx`: **`2` tests passed** (`1547ms`) — verifies single `[role="tablist"]` (`5` canonical tabs, `0` legacy 3-tab selectors), `initialTab="sources"` opening Tab 2 (`workspace-sources-master-table-root`), Tab 1 `total == 0` KPI suppression (`workspace-overview-empty-hint`) vs `total >= 1` (`workspace-overview-kpi-grid`), and FR/EN rendering.
  - `story-24-2-five-tabs-and-triggers-modal.test.tsx` (`@orcia/ui`): **`3` tests passed** (`658ms`) — verifies Tab 1 `total == 0` sobriety and `total >= 1` KPI display alongside 5-tab navigation.
  - `i18n-and-shell.test.tsx`: **`26` tests passed** (`24328ms`) — full shell, workspaces studio, RAG sources, glossary promotion, and members/instructions verification under canonical 5 tabs.
  - `zero-dead-buttons-and-silent-catches-audit.test.tsx`: **`4` tests passed** (`7174ms`) — zero unwired buttons or silent `.catch()` handlers.
  - `e2e-testids-sync-audit.test.ts`: **`1` test passed** (`2097ms`) — 100% E2E `data-testid` synchronization preserved.
  - `i18n-hardcoded-locale-ast-audit.test.ts` (Gate 1): **`3` tests passed** (`4200ms`) — zero hardcoded locale conditionals or raw JSX strings.
  - `i18n-dictionary-parity-and-jargon-audit.test.ts` (Gate 2): **`2` tests passed** (`158ms`) — full FR/EN parity and zero internal jargon.
  - `client-error-code-contract-audit.test.ts` (Gate 3) & `client-error-code-resolution.test.ts`: **`4` + `9` tests passed**.
- **Layers 1a / 2 / 3 / 4 / Security**: Not impacted (pure frontend/UI container deduplication and Tab 1 sobriety story; zero Python, SQL, or OpenAPI schema changes).
- **Layer 5 — Playwright E2E**: Deferred to Epic 28 final lock (`Story 28.4`); `e2e-testids-sync-audit.test.ts` verified all existing E2E selectors (including updated `openWorkspaceGlossaryTab`) resolve cleanly against UI sources.
