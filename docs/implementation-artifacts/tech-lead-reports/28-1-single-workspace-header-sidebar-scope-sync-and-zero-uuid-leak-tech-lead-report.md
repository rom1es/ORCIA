# Story 28.1 — Single Compact Workspace Header, Global Sidebar Scope Synchronization, Zero Raw UUID Leak & Workspace Switcher/Creation Flow

- **Date**: 2026-11-24
- **Story / Sprint Key**: `28-1-single-workspace-header-sidebar-scope-sync-and-zero-uuid-leak` (`Epic 28` — Lot 1: Header & Scope Unification)
- **Capability(ies)**: `CAP-067`, `CAP-080` — classification: `ux`
- **Author / Context**: Unified `/workspaces` ("Mes Espaces") header and scope synchronization (`WX-02`, `WX-06`), addressing `DESIGN.md` §Brand & Style #1 & #3 (`1` sober header + canonical Sidebar selector), `EXPERIENCE.md` §1.2 #1 (zero internal plumbing/UUIDs), and `EXPERIENCE.md` §2.1 #1 / §2.2.
- **Associated Commits**: Pending closure

---

## 1. Needs Analysis & Tech Lead Impact Study (Pre-Implementation)

### 1.1 Context & Problem Statement
- **Current behavior**: Navigating to `/workspaces` (or `/spaces`) renders multiple vertically stacked headers and workspace selection surfaces:
  1. `ModuleWorkspaceView.tsx` renders an outer `.orcia-bento-card` header (`headerSubtitle`, `module-uri-badge-admin`, `headerDescription`) for `currentModule === "admin"`.
  2. `WorkspacesFeaturePanel` (`apps/web/src/features/workspaces/index.tsx`) renders a secondary `<nav>` bar with `wsPanelCopy.headerTitle` and `spaces-open-glossary-link`.
  3. `WorkspaceStudioCardsAndDetailView.tsx` renders `workspaces-header-and-filters-bar` (filter pills + search input + `toggle-create-workspace-form-btn`) followed by a full-width `workspaces-summary-cards-grid` (`WorkspaceStudioSummaryCard` with `"Travailler dans cet Espace"` competing with the Sidebar selector).
  4. `WorkspaceFiveTabsAndExternalRebaseView.tsx` renders yet another `<header>` showing raw `workspaceSlug` (`personal-<uuidv7>`) and raw `defaultArtifactDestinationUri` (`orcia://workspaces/personal-<uuidv7>/artifacts`) above the 5-tab bar.
  5. `WorkspaceStudioCardsAndDetailView.tsx` manages local `selectedWsId` state independently of `ShellNavigationContext`, so switching workspaces inside `/workspaces` does not update the Sidebar `sidebar-workspace-selector` (`activeScopeId` / `ORCIA_ACTIVE_SCOPE_STORAGE_KEY`) or `WorkspaceDnaAndWaiversSection`.
- **Expected behavior**:
  - `/workspaces` displays **one single compact workspace header** (`workspaces-compact-header`) showing the active workspace's human-readable name, lifecycle phase badge, visibility badge (`Personnel` / `Équipe` / `Confidentiel` in FR; `Personal` / `Team` / `Confidential` in EN), a compact workspace switcher synchronized **bidirectionally** with the global Sidebar `activeWorkspaceId`, `+ Nouvel espace` (`toggle-create-workspace-form-btn`), `📖 Glossaire métier →` (`spaces-open-glossary-link`), and compact phase/visibility/team-share governance controls.
  - Zero raw `personal-<uuid>` slugs or raw `UUIDv7` strings leak into any visible UI text across `/workspaces` (`WorkspaceFiveTabsAndExternalRebaseView.tsx`, `WorkspaceFiveTabsPanels.tsx`, `WorkspaceDnaAndWaiversSection.tsx`, `WorkspaceStudioSummaryCard.tsx`, `WorkspaceStudioCardsAndDetailView.tsx`, `WorkspacesFeaturePanel`).
  - `WorkspaceDetailTabsPanel` (removed in Story 28.2) and `DnaStarlarkCompilerAndGlossaryLifecycleView` (encapsulated in Tab 4 in Story 28.4) remain intact in this story so Stories 28.2–28.4 stay isolated.
- **Architectural constraints**:
  - Every modified/created `.ts`/`.tsx` file must stay `<= 300` lines (`WorkspaceFiveTabsAndExternalRebaseView.tsx` is currently `323` lines and must be trimmed/split to `<= 300`).
  - 100% bilingual `fr`/`en` via typed `apps/web/src/i18n/locales/` dictionaries (Gate 1, Gate 2, Gate 3 at `0` violations).
  - Preserve `e2e-testids-sync-audit.test.ts` and `zero-dead-buttons-and-silent-catches-audit.test.tsx`.

### 1.2 Exploration, GitNexus Impact Analysis, Refactoring & Technical Debt
- **GitNexus Impact Analysis (`gitnexus_query`, `gitnexus_context`, `gitnexus_impact`)**:
  - Queried `/home/romain/Documents/Projects/ORCIA` via `gitnexus_query`, `gitnexus_context({name: "WorkspacesFeaturePanel"})`, and `gitnexus_impact({target: "ModuleWorkspaceView", direction: "upstream"})` / `WorkspaceFiveTabsAndExternalRebaseView`. Because the TypeScript symbol nodes for those React components were not resolved in the current graph index (`Symbol not found`), exhaustive upstream caller verification was completed via repository-wide `grep` across `apps/web/src/`, `apps/web/e2e/`, and `packages/ui/src/`:
    - `ModuleWorkspaceView` (`moduleKey="admin"`): called from `apps/web/src/routes/workspaces.tsx` and `/spaces`, `/workspaces/$wsId`, `/workspaces/$wsId/sources` in `apps/web/src/router.tsx`. `module-uri-badge-admin` has `0` test assertions (`story-23-5-sobriety-and-citations-wiring.test.tsx` checks `inbox` and `ontology` only).
    - `WorkspacesFeaturePanel`: called exclusively by `ModuleWorkspaceView`.
    - `WorkspaceFiveTabsAndExternalRebaseView`: exported from `packages/ui/src/index.ts`, called by `WorkspaceDnaAndWaiversSection.tsx` and unit-tested in `packages/ui/src/__tests__/story-24-2-five-tabs-and-triggers-modal.test.tsx` and `workspace-governance-and-packs.test.tsx`.
    - `ShellNavigationContext`: provided by `apps/web/src/components/ShellContainer.tsx` and consumed via `useShellNavigation()`. Adding an optional `setActiveScopeId?: (scopeId: string) => void` is backwards-compatible with all consumers and standalone test harnesses.
- **Refactoring Opportunities & Emerging Technical Debt Mitigation**:
  - Extract `apps/web/src/features/workspaces/workspaceDisplayHelpers.ts` (`<= 90` lines) to centralize `isTechnicalWorkspaceSlug`, `formatWorkspaceDisplaySlug`, `formatWorkspaceCreatedBannerId`, and localized phase/visibility label formatting without duplicating `personal-<uuid>` detection.
  - Extract `apps/web/src/features/workspaces/WorkspaceCompactHeader.tsx` (`<= 190` lines) so `WorkspaceStudioCardsAndDetailView.tsx` drops from `246` lines to `~95` lines (`<= 300` L limit).
  - Trim `packages/ui/src/primitives/WorkspaceFiveTabsAndExternalRebaseView.tsx` from `323` lines to `<= 285` lines by removing the redundant secondary `<header>` block and delegating slug sanitization cleanly.
  - `WorkspaceStudioSummaryCard.tsx` remains exported for Story 24.6 microcopy unit coverage and is kept free of raw UUID leaks (scheduled for final removal check in Story 28.2 once superseded).

---

## 2. Implementation Plan

### 2.1 Data Schema & Alembic Migrations (`infra/migrations/versions/...`)
- None required (`WX-02` and `WX-06` are frontend unification & scope-synchronization changes over existing PostgreSQL 18 tables).

### 2.2 Hexagonal Core, Orchestration & Workers (`packages/orcia-core/`, `apps/worker/`, `infra/sandbox/`)
- None required.

### 2.3 Backend API, Security & Contracts (`apps/api/`, `packages/api-client/`)
- None required; all workspace CRUD, phase, and visibility mutations continue through existing typed `@orcia/api-client` endpoints.

### 2.4 User Interface & Experience (`apps/web/`, `packages/ui/`)
1. **`apps/web/src/components/shellNavigationContext.ts` & `ShellContainer.tsx`**:
   - Expose optional `setActiveScopeId` on `ShellNavigationContextValue` and wire `state.setActiveScopeId` from `ShellContainer` so `/workspaces` switches update both React state, `ORCIA_ACTIVE_SCOPE_STORAGE_KEY` (`localStorage`), Sidebar `sidebar-workspace-selector`, and `TopHeaderBar` breadcrumbs.
2. **`apps/web/src/components/ModuleWorkspaceView.tsx`**:
   - Suppress the outer `.orcia-bento-card` module banner when `currentModule === "admin"`, keeping `data-testid="module-view-admin"` on the outer container.
3. **`apps/web/src/i18n/locales/feature_workspaces_labels*.ts`**:
   - Add symmetric FR/EN keys (`compactHeader` / `summaryCard` short visibility badges `Personnel` / `Équipe` / `Confidentiel` vs `Personal` / `Team` / `Confidential`, switcher `aria-label`, group labels, and Day-0 empty header title/hint).
4. **`apps/web/src/features/workspaces/workspaceDisplayHelpers.ts` & `WorkspaceCompactHeader.tsx`**:
   - Render one compact workspace header (`workspaces-compact-header`) displaying active workspace title (`workspaces-active-title`), billing team name, lifecycle phase badge (`workspace-phase-badge-<id>`), short visibility badge (`workspace-visibility-badge-<id>`), autosaved badge (`workspace-autosaved-badge-<id>`), compact switcher (`workspaces-active-switcher-select`), `+ Nouvel espace` (`toggle-create-workspace-form-btn`), `📖 Glossaire métier →` (`spaces-open-glossary-link`), and inline phase/visibility/team-share controls.
   - Sanitize `personal-<uuid>` and raw `UUIDv7` strings into clean human-readable kebab-case slugs derived from `workspace.name` wherever a slug or `orcia://workspaces/.../deliverables` URI is formatted.
5. **`apps/web/src/features/workspaces/index.tsx` & `WorkspaceStudioCardsAndDetailView.tsx`**:
   - Remove the standalone `<nav>` bar in `index.tsx`, remove `workspaces-header-and-filters-bar` and `workspaces-summary-cards-grid`, keep `workspaces-cards-empty-state` when `workspaces.length === 0`, synchronize active workspace selection bidirectionally with `activeScopeId` / `setActiveScopeId`, and pass the active workspace to both `WorkspaceDetailTabsPanel` (preserved until Story 28.2) and `WorkspaceDnaAndWaiversSection`.
6. **`apps/web/src/features/workspaces/WorkspaceDnaAndWaiversSection.tsx`, `packages/ui/src/primitives/WorkspaceFiveTabsAndExternalRebaseView.tsx`, & `WorkspaceFiveTabsPanels.tsx`**:
   - Remove the redundant `<header>` in `WorkspaceFiveTabsAndExternalRebaseView.tsx` (lines 272–286), replace `orcia://workspaces/personal-<uuid>/artifacts` with sanitized `orcia://workspaces/<human-slug>/deliverables`, and sanitize any fallback slug display in `@orcia/ui` panels so zero `personal-<uuid>` strings can appear even in direct primitive renders.

### 2.5 Test Pyramid Impact Analysis (`AD-17`)
- **Layer 1b (Vitest `@orcia/web` & `@orcia/ui`)**:
  - Create `apps/web/src/__tests__/story-28-1-single-workspace-header-and-zero-uuid.test.tsx` verifying: (1) single compact header on `/workspaces` synced bidirectionally with the global Sidebar selector and surviving `F5` remount, (2) zero `personal-<uuid>` or raw UUID strings in rendered text, and (3) bilingual `fr` & `en` rendering.
  - Update lockstep assertions in `apps/web/src/__tests__/story-22-1-workspace-uuid-and-identity.test.tsx`, `story-22-2-portals-tailwind-and-routes.test.tsx`, `story-24-6-packs-counters-microcopy-and-finops.test.tsx`, `story-25-2-shell-9-items-org-admin-and-unified-scope.test.tsx`, and `i18n-and-shell.test.tsx`.
  - Run `e2e-testids-sync-audit.test.ts`, `i18n-hardcoded-locale-ast-audit.test.ts`, `i18n-dictionary-parity-and-jargon-audit.test.ts`, and `packages/ui` five-tabs tests (`story-24-2`, `workspace-governance-and-packs`).
- **Layer 5 (Playwright E2E)**:
  - Executed by Testing Sub-Agent (`07-spaces-org-and-workspace-persistence.spec.ts`, `17-workspace-sources-codegraph-dna-and-ontology.spec.ts`).

---

## 3. Summary of Changes & Results (Post-Implementation)

### 3.1 Created & Modified Files
| File | Action (Created / Modified / Refactored) | Line Count | Concise Summary |
| :--- | :--- | :---: | :--- |
| `apps/web/src/components/shellNavigationContext.ts` | Modified | `29` | Added optional `setActiveScopeId?: (scopeId: string) => void` on `ShellNavigationContextValue`. |
| `apps/web/src/components/ShellContainer.tsx` | Modified | `286` | Wired `state.setActiveScopeId` into `ShellNavigationContext` for bidirectional Sidebar/Topbar/Workspace scope sync. |
| `apps/web/src/components/ModuleWorkspaceView.tsx` | Modified | `107` | Suppressed the outer `.orcia-bento-card` module banner when `currentModule === "admin"` while preserving `module-view-admin`. |
| `apps/web/src/features/workspaces/workspaceDisplayHelpers.ts` | Created | `102` | Centralized `isTechnicalWorkspaceSlug`, `formatWorkspaceDisplaySlug`, `formatWorkspaceCreatedBannerId`, and localized phase/visibility label resolution (`zero personal-<uuid>` leak). |
| `apps/web/src/features/workspaces/WorkspaceCompactHeader.tsx` | Created | `292` | Implemented the single compact `/workspaces` header (`workspaces-compact-header`) with switcher (`workspaces-active-switcher-select`), `+ Nouvel espace`, glossary link, phase/visibility badges, and governance controls. |
| `apps/web/src/features/workspaces/index.tsx` | Modified | `212` | Removed redundant secondary `<nav>` header and wired compact header + active scope sync. |
| `apps/web/src/features/workspaces/WorkspaceStudioCardsAndDetailView.tsx` | Refactored | `142` | Removed `workspaces-header-and-filters-bar` and `workspaces-summary-cards-grid`, delegated header to `WorkspaceCompactHeader`, and synced active workspace with `activeScopeId` / `setActiveScopeId`. |
| `apps/web/src/features/workspaces/WorkspaceDnaAndWaiversSection.tsx` | Modified | `147` | Replaced raw `personal-<uuid>` artifact destination URI with sanitized `orcia://workspaces/<human-slug>/deliverables` and normalized active workspace title/slug props. |
| `apps/web/src/i18n/locales/feature_workspaces_labels.ts` | Modified | `132` | Added typed `compactHeader` & short visibility badge keys to the workspaces i18n interface. |
| `apps/web/src/i18n/locales/feature_workspaces_labels_fr.ts` | Modified | `139` | Added French (`fr`) translations for compact header, switcher labels, Day-0 empty state, and short visibility badges (`Personnel`, `Équipe`, `Confidentiel`). |
| `apps/web/src/i18n/locales/feature_workspaces_labels_en.ts` | Modified | `139` | Added English (`en`) translations for compact header, switcher labels, Day-0 empty state, and short visibility badges (`Personal`, `Team`, `Confidential`). |
| `packages/ui/src/primitives/WorkspaceFiveTabsAndExternalRebaseView.tsx` | Refactored | `290` | Removed the redundant secondary `<header>` block above the 5-tab bar and sanitized fallback slug display (`<= 300` lines). |
| `packages/ui/src/primitives/WorkspaceFiveTabsPanels.tsx` | Modified | `298` | Sanitized any raw `personal-<uuid>` / technical slug display inside `@orcia/ui` panels (`<= 300` lines). |
| `apps/web/src/__tests__/story-28-1-single-workspace-header-and-zero-uuid.test.tsx` | Created | `254` | Added Story 28.1 Vitest suite (`2` tests) covering single compact header, bidirectional Sidebar scope sync + `F5` remount survival, zero UUID leaks, and FR/EN bilingual labels. |
| `apps/web/src/__tests__/i18n-and-shell.test.tsx` | Modified | `2299` | Updated existing shell/workspaces test assertions to match the unified compact header and scope sync (pre-existing legacy test file). |
| `apps/web/src/__tests__/story-22-1-workspace-uuid-and-identity.test.tsx` | Modified | `195` | Updated Story 22.1 workspace identity assertions for sanitized slugs and compact header. |
| `apps/web/src/__tests__/story-22-2-portals-tailwind-and-routes.test.tsx` | Modified | `341` | Updated Story 22.2 route assertions to align with single header layout (pre-existing legacy test file). |
| `apps/web/src/__tests__/story-24-6-packs-counters-microcopy-and-finops.test.tsx` | Modified | `332` | Updated Story 24.6 microcopy assertions for unified workspaces header (pre-existing legacy test file). |
| `apps/web/src/__tests__/story-25-2-shell-9-items-org-admin-and-unified-scope.test.tsx` | Modified | `390` | Updated Story 25.2 unified scope assertions for bidirectional `/workspaces` $\leftrightarrow$ Sidebar sync (pre-existing legacy test file). |
| `docs/implementation-artifacts/sprint-status.yaml` | Modified | — | Marked `28-1-single-workspace-header-sidebar-scope-sync-and-zero-uuid-leak: done`. |

### 3.2 Quantitative Metrics, Coverage & Static Quality
- **Line-count discipline**: Every modified or created production `.ts`/`.tsx` file (`13/13`, max `298` lines) and the new Story 28.1 test file (`254` lines) are `<= 300` lines.
- **JS/TS Monorepo Verification (`timeout -k 10s 300s pnpm turbo run lint typecheck test`)**:
  - **`9/9` Turbo tasks passed** (`@orcia/api-client`, `@orcia/ui`, `@orcia/web` — `lint`, `typecheck`, `test` in `1m4.17s`).
  - **`@orcia/api-client`**: `3` test files / `20` tests passed.
  - **`@orcia/ui`**: `35` test files / `139` tests passed.
  - **`@orcia/web`**: `76` test files / `292` tests passed (total **`114` files / `451` JS/TS tests passed**).
- **Architecture & Documentation Gates**:
  - `lint_spine.py --workspace docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24`: `ok: true`, `total_findings: 0`.
  - `scripts/check_implementation_docs.py`: passed (`0` errors).
  - `pnpm site:sync && pnpm site:check`: passed (`0` errors).

### 3.3 AD-17 Test Pyramid & Vertical Wiring Verification
- **Layer 1b — Frontend TS (`Vitest` without `isJsdom` short-circuits)**:
  - `story-28-1-single-workspace-header-and-zero-uuid.test.tsx`: **`2` tests passed** (`2193ms`) — verifies single compact header (`workspaces-compact-header`), bidirectional Sidebar selector sync, `F5` remount persistence, zero `personal-<uuid>` / raw UUID leaks, and FR/EN bilingual rendering.
  - `zero-dead-buttons-and-silent-catches-audit.test.tsx`: **`4` tests passed** (`7406ms`) — zero unwired buttons or silent `.catch()` handlers.
  - `e2e-testids-sync-audit.test.ts`: **`1` test passed** (`2041ms`) — 100% E2E `data-testid` synchronization preserved.
  - `i18n-hardcoded-locale-ast-audit.test.ts` (Gate 1): **`3` tests passed** (`2495ms`) — zero hardcoded locale conditionals or raw JSX strings.
  - `i18n-dictionary-parity-and-jargon-audit.test.ts` (Gate 2): **`2` tests passed** (`183ms`) — full FR/EN parity and zero internal jargon.
  - `client-error-code-contract-audit.test.ts` (Gate 3) & `client-error-code-resolution.test.ts`: **`4` + `9` tests passed**.
- **Layers 1a / 2 / 3 / 4 / Security**: Not impacted (pure frontend/UI unification story; zero Python, SQL, or OpenAPI schema changes).
- **Layer 5 — Playwright E2E**: Deferred to Epic 28 final lock (`Story 28.4`); `e2e-testids-sync-audit.test.ts` verified all existing E2E selectors resolve cleanly against UI sources.
