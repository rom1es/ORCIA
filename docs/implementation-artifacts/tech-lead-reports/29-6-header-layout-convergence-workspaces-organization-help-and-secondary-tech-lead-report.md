# Story 29.6 — Header & Layout Convergence: Spaces, Organization, Help & Secondary Routes

- **Date**: 2026-11-25
- **Story / Sprint Key**: `29-6-header-layout-convergence-workspaces-organization-help-and-secondary` (`Epic 29` / Lot 3 — Batch B)
- **Capability(ies)**: `CAP-058`, `CAP-060`, `CAP-063`, `CAP-064`, `CAP-065`, `CAP-067`, `CAP-080`, `CAP-100`, `CAP-203` (`docs/product/capabilities.yaml`) — classification: `ux`
- **Author / Context**: Resolves findings `UH-06` (`P1`), `UH-08` (`P1`), `UH-10` (`P1`), and `UH-13` (`P1`) from `docs/planning-artifacts/sprint-change-proposal-2026-11-24-epic-29-ui-headers-scope-and-screen-consistency.md`. Converges `Mes Espaces` (`/spaces` & `/workspaces`), `Mon Organisation` (`/organization`), `Aide` (`/help`), and ORCIA's secondary routes (`/cockpit`, `/settings`, `/settings/packs`, `/profile`, `/activity`) onto the canonical Direction C layout primitives (`<OrciaPageHeader />`, `<OrciaTabStrip />`, and `<OrciaDataCard />`), removes dead `Phase` and duplicate workspace switcher controls, moves workspace visibility governance into Tab 5, clarifies organization ancestor vs. sibling row states, expands `/help` to full canvas width while disabling the active TopBar Help toggle, and enforces `<= 300`-line modular files across both `fr` and `en` locales.
- **Associated Commits**: `pending (working tree)`

---

## 1. Needs Analysis & Tech Lead Impact Study (Pre-Implementation)

### 1.1 Context & Problem Statement
1. **`Mes Espaces` (`/spaces`, `/workspaces`) — Cluttered Header, Dead `Phase` Control, Duplicate Switcher & Numbered Tabs (`UH-06`, `UH-08`)**:
   - **Current behavior**: `WorkspaceCompactHeader.tsx` renders an ad-hoc `<header className="orcia-bento-card">` containing a duplicate workspace selector (`workspaces-active-switcher-select`, contradicting the single Left Rail `sidebar-workspace-selector` rule in `DESIGN.md`), a dead `Phase` dropdown (`workspace-card-phase-select-*`) and header badge (`workspace-phase-badge-*`), and an inline visibility selector (`workspace-card-visibility-select-*`) plus `share-private-workspace-btn-*` on personal spaces. Meanwhile `WorkspacesFeaturePanel` renders `workspaces-action-feedback-banner` above the header instead of inside `alertSlot`, and `WorkspaceFiveTabsAndExternalRebaseView.tsx` uses legacy `.orcia-ds-tabs` with `"1. "`–`"5. "` numeric tab prefixes.
   - **Expected behavior**: Converge `WorkspaceCompactHeader` onto `<OrciaPageHeader />` (`<h1>` `workspaces-active-title`, monochrome `"spaces"` `<OrciaIcon />`, billing team subtitle, concise visibility & autosaved badges, single Cobalt `+ Nouvel espace` / `+ New space` primary CTA, secondary `Glossaire métier` / `Business Glossary` link, and unified `alertSlot` for `workspaces-action-feedback-banner`). Remove the dead `Phase` selector/badge and duplicate workspace switcher completely. Remove numeric `"1. "`–`"5. "` prefixes from tab labels in `fr` and `en` while converging `WorkspaceFiveTabsAndExternalRebaseView` onto `<OrciaTabStrip />` (preserving `<OrciaIcon />` and the source count badge) and `<OrciaDataCard />`. Move the workspace visibility selector (`STANDARD`, `CONFIDENTIAL_RESTRICTED`, `PRIVATE_USER`) cleanly into Tab 5 (`WorkspaceMembersAndSettingsTab.tsx` wrapped in `<OrciaDataCard />`) with plain-language mode explanations, preserving `PATCH /api/v1/workspaces/{id}` persistence, optimistic rollback on HTTP 403, `PRIVATE_USER` lock, and observer read-only protection.
2. **`Mon Organisation` (`/organization`) — Split Header/Actions, Misleading Sibling Badges, Disabled Button Chrome & Inline Callout (`UH-06`, `UH-10`)**:
   - **Current behavior**: `organization.tsx` mounts a bare `<header className="orcia-bento-card">` with an empty right side, while primary/secondary CTAs (`+ Nouvelle unité`, `+ Inviter un utilisateur`) live in Card 2 (`SettingsOrganizationUnitsBlock.tsx`) above a redundant inline `OrgPedagogicalCallout` (`"Repères..."`) that duplicates Zone 4 Contextual Help. `SettingsOrganizationUnitRow.tsx` labels every non-editable row (including sibling teams) with `readOnlyAncestor` and leaves disabled `Edit` / `Delete` buttons mounted.
   - **Expected behavior**: Converge `/organization` onto `<OrciaPageHeader />` (moving `+ Nouvelle unité` as primary Cobalt CTA, `+ Inviter un utilisateur` and `Ouvrir Mes Espaces ->` / `Open My Spaces ->` as secondary actions, and read-only / error notices into `alertSlot`) and `<OrciaDataCard />` for the organization tree card. Remove `OrgPedagogicalCallout` from the page body. Distinguish true ancestor units (`Contexte parent` / `Parent context`) from sibling or out-of-scope units (`Autre équipe — lecture seule` / `Other team — read-only`) and active editable units, and hide write buttons (`Modifier` / `Edit`, `Membres` / `Members`, `Supprimer` / `Delete`) whenever the user lacks the corresponding row capability instead of repeating disabled buttons.
3. **`Aide` (`/help`) — Inverted Hierarchy, Half-Width Void & Silent TopBar Toggle (`UH-06`, `UH-13`)**:
   - **Current behavior**: `apps/web/src/routes/help.tsx` places `help-showcase-site-banner` with a solid primary CTA above `<ContextualHelpColumnAndCenter />`, while `HelpCenterCatalogView.tsx` constrains content with `max-w-4xl`, leaving half the main canvas empty. In `ShellContainer.tsx` and `FourZoneTopHeaderSection.tsx`, `topbar-contextual-help-toggle` stays visually clickable while `onHelpColumnOpenChange` silently no-ops when on `/help`.
   - **Expected behavior**: Mount `<OrciaPageHeader />` (`icon="help"`, `<h1>` Help Center title, 1-line subtitle, and secondary Documentation/Showcase action) at the top of `/help`, remove `max-w-4xl` in `HelpCenterCatalogView.tsx` so `<OrciaDataCard />` spans the full main canvas width, relocate `help-showcase-site-banner` cleanly below the main catalog card as a secondary `<OrciaDataCard />`, and mark/disable `topbar-contextual-help-toggle` (`disabled`, `aria-current="page"`, active highlight) when `/help` is active with Zone 4 suppressed.
4. **Secondary Routes (`/cockpit`, `/settings`, `/settings/packs`, `/profile`, `/activity`) (`UH-06`)**:
   - **Current behavior**: Secondary routes render custom `<header>` or `<div>` wrappers (`<h2>` on `/settings/packs`, bare avatar header on `/profile`, unboxed scope banner above header on `/activity`, raw `.orcia-ds-tabs` on `/settings`, and no `<OrciaPageHeader />` on `/cockpit`).
   - **Expected behavior**: Standardize `/cockpit`, `/settings`, `/settings/packs`, `/profile`, and `/activity` onto `<OrciaPageHeader />`, `<OrciaTabStrip />` (on `/settings`), and `<OrciaDataCard />` with semantic `<h1>`, `<OrciaIcon />`, concise subtitle, aligned header actions, and 100% bilingual `fr`/`en` copy.

### 1.2 Exploration, GitNexus Impact Analysis, Refactoring & Technical Debt
- **GitNexus & Upstream Caller Impact Analysis (`repo: "ORCIA"`)**:
  - `gitnexus_query` (`repo: "ORCIA"`) reported the worktree index is 5 commits behind HEAD (pre-Story `29.4`/`29.5` primitives). Direct repository `grep` and file inspection mapped all upstream callers and test dependencies:
    - `apps/web/src/components/ModuleWorkspaceView.tsx` -> `WorkspacesFeaturePanel`, `CockpitFeaturePanel`
    - `apps/web/src/router.tsx` -> `/spaces`, `/workspaces`, `/cockpit`, `/organization`, `/help`, `/settings`, `/settings/packs`, `/profile`, `/activity`
    - `apps/web/src/components/ShellContainer.tsx` -> `FourZoneDirectionCShell` -> `FourZoneTopHeaderSection`
    - `packages/ui/src/index.ts` -> `OrciaPageHeader`, `OrciaTabStrip`, `OrciaDataCard`, `HelpCenterCatalogView`, `WorkspaceFiveTabsAndExternalRebaseView`, `UserProfileOverviewPage`, `ActivityLogExplorerView`
    - Impacted unit & E2E tests: `e2e/07`, `e2e/09`, `e2e/14`, `e2e/15`, `e2e/17`, `e2e/21`, `e2e/shell.spec.ts`, `story-6-1`, `story-17-1`, `story-17-2`, `story-20-1`, `story-20-2`, `story-20-4`, `story-22-1`, `story-24-2`, `story-24-5`, `story-24-6`, `story-25-2`, `story-25-3`, `story-28-1`, `story-28-2`, `story-28-3`, `story-29-2`, `day0-modal-and-settings-auth-token-wiring.test.tsx`, `i18n-and-shell.test.tsx`, `ux-polish-rfc9457-alerts-euro-and-jargon-purge.test.tsx`, `zero-dead-buttons-and-silent-catches-audit.test.tsx`, and `e2e-testids-sync-audit.test.ts`.
  - **Risk level**: Medium. Removing dead controls (`Phase`, duplicate switcher) and hiding disabled write buttons on read-only org rows requires synchronized updates to legacy unit/E2E assertions while keeping all active `data-testid` contracts and vertical API wiring intact.
- **Refactoring Opportunities & File Line-Count Control (`<= 300` lines)**:
  - Keep `OrciaPageHeader.tsx` (`<= 140` lines) and `OrciaTabStrip.tsx` (`<= 155` lines) strictly modular with optional `titleTestId` and `countTestId` props so legacy `data-testid`s (`workspaces-active-title`, `profile-display-name`, `workspace-tab-badge-*`) are preserved natively without wrapper hacks.
  - Keep every modified `.ts`/`.tsx` file strictly `<= 300` lines (`WorkspaceCompactHeader.tsx`, `WorkspaceMembersAndSettingsTab.tsx`, `SettingsOrganizationUnitsBlock.tsx`, `SettingsOrganizationUnitRow.tsx`, `ShellContainer.tsx`, `FourZoneDirectionCShell.tsx`, `FourZoneTopHeaderSection.tsx`, `UserProfileOverviewPage.tsx`, `ActivityLogExplorerView.tsx`, `settings.tsx`, `cockpit/index.tsx`, `help.tsx`).
  - Extract org ancestor/perimeter classification into a small pure helper in `orgTreeHelpers.ts` (avoiding bloat inside `SettingsOrganizationUnitRow.tsx`).

---

## 2. Implementation Plan

### 2.1 Data Schema & Alembic Migrations (`infra/migrations/versions/...`)
- None required. Story `29.6` is strictly a frontend UI, `@orcia/ui` primitive adoption, i18n, and test synchronization story.

### 2.2 Hexagonal Core, Orchestration & Workers (`packages/orcia-core/`, `apps/worker/`)
- None required.

### 2.3 Backend API, Security & Contracts (`apps/api/`, `packages/api-client/`)
- None required (`PATCH /api/v1/workspaces/{id}` and `GET/POST/PATCH/DELETE /api/v1/org-units` contracts from Stories `20.1` and `29.2` remain unchanged).

### 2.4 User Interface & Experience (`packages/ui/`, `apps/web/`)
1. **Shared Primitives (`packages/ui/src/primitives/`)**:
   - Extend `OrciaPageHeader` with optional `titleTestId?: string` (preserving `workspaces-active-title` and `profile-display-name`) and `OrciaTabStripItem` with optional `countTestId?: string` (preserving `workspace-tab-badge-*`).
   - Extend `FourZoneDirectionCShellProps` & `FourZoneTopHeaderSectionProps` with optional `helpColumnToggleDisabled?: boolean` (and `isHelpCenterActive?: boolean`) so `topbar-contextual-help-toggle` renders active (`aria-current="page"`) and `disabled` on `/help`.
   - Converge `WorkspaceFiveTabsAndExternalRebaseView.tsx` onto `<OrciaDataCard />` and `<OrciaTabStrip variant="underline" />` (with `<OrciaIcon />` icons and source/pending badges).
   - Converge `HelpCenterCatalogView.tsx` onto full-width `<OrciaDataCard />` (removing `max-w-4xl`).
   - Converge `UserProfileOverviewPage.tsx` and `ActivityLogExplorerView.tsx` onto `<OrciaPageHeader />` and `<OrciaDataCard />` (removing `max-w-4xl` constraint on `/profile` or aligning cleanly within `<OrciaPageHeader />` + `<OrciaDataCard />` stack).
2. **`Mes Espaces` (`apps/web/src/features/workspaces/`, `apps/web/src/i18n/locales/`)**:
   - Refactor `WorkspaceCompactHeader.tsx` onto `<OrciaPageHeader />`, removing `workspaces-active-switcher-select`, `workspace-card-phase-select-*`, `workspace-phase-badge-*`, `workspace-card-visibility-select-*`, and `share-private-workspace-btn-*`, while routing `workspaces-action-feedback-banner` through `alertSlot`.
   - Move `workspace-card-visibility-select-*` (with `STANDARD`, `CONFIDENTIAL_RESTRICTED`, `PRIVATE_USER` options and plain-language mode hints, locked for `PRIVATE_USER` and `readOnlyObserver`) into `WorkspaceMembersAndSettingsTab.tsx` wrapped in `<OrciaDataCard />` panels, wiring `updateWorkspaceVisibility` + rollback + `workspaces-action-feedback-banner` via `onFeedback`.
   - Strip `"1. "`–`"5. "` numeric prefixes from `workspaceFiveTabs` labels in `governance_and_packs_labels_{fr,en}.ts`.
3. **`Mon Organisation` (`apps/web/src/routes/organization.tsx`, `SettingsOrganizationUnitsBlock.tsx`, `SettingsOrganizationUnitRow.tsx`)**:
   - Mount `<OrciaPageHeader />` with `open-invite-org-user-modal-btn`, `organization-open-workspaces-btn`, and `open-create-org-unit-modal-btn` in the header action row, and `alertSlot` for `organization-readonly-access-banner`, `org-scoped-view-notice`, and `org-unit-delete-feedback`.
   - Wrap the tree in `<OrciaDataCard testId="settings-organization-section" />`, remove `<OrgPedagogicalCallout />` from the page body, distinguish ancestor vs. sibling read-only units in `orgTreeHelpers.ts` + `SettingsOrganizationUnitRow.tsx`, and hide `Edit` / `Members` / `Delete` buttons when `!rowCanEdit` / `!rowCanManageMembers` / `!rowCanDelete`.
4. **`Aide` (`apps/web/src/routes/help.tsx`, `ShellContainer.tsx`)**:
   - Mount `<OrciaPageHeader />` (`icon="help"`, `<h1>`, subtitle, secondary `open-orcia-showcase-site-btn`), full-width `<ContextualHelpColumnAndCenter />`, and relocate `help-showcase-site-banner` as a secondary `<OrciaDataCard />` below the help catalog.
   - Pass `helpColumnToggleDisabled={isHelpCenterRoute}` from `ShellContainer.tsx` to `FourZoneDirectionCShell`.
5. **Secondary Routes (`cockpit/index.tsx`, `settings.tsx`, `PacksRegistryPage.tsx`)**:
   - Add `<OrciaPageHeader />` and `<OrciaDataCard />` framing to `CockpitFeaturePanel`.
   - Converge `SettingsHubView` (`settings.tsx`) onto `<OrciaPageHeader />` + `<OrciaTabStrip testId="settings-domain-tabs" testIdPrefix="settings-tab" />` + `<OrciaDataCard />`.
   - Converge `PacksRegistryPage.tsx` onto `<OrciaPageHeader />` (semantic `<h1>`, `alertSlot`, single Cobalt primary CTA).

### 2.5 Test Pyramid Impact Analysis (`AD-17` — Layers 1 to 5 + Security, Mandatory)
- **Layer 1a (`tests/unit/`)**: `tests/unit/test_i18n_backend_catalog_and_english_dev_audit.py` verifies English-only comments/docstrings in diffs.
- **Layer 1b (`packages/ui` & `apps/web` Vitest)**:
  - Add `apps/web/src/__tests__/story-29-6-spaces-org-help-and-secondary-convergence.test.tsx` (`<= 300` lines) covering `Mes Espaces` (Tab 5 visibility, no Phase select, no duplicate switcher, unnumbered tabs), `Mon Organisation` (header CTAs, no inline callout, hidden disabled row buttons, ancestor vs. sibling distinction), `Aide` (full width + TopBar active/disabled state), and secondary route `<OrciaPageHeader />` convergence across both `fr` and `en`.
  - Synchronize impacted tests (`story-29-2-*`, `story-28-1-*`, `story-28-2-*`, `story-28-3-*`, `story-24-2-*`, `story-24-6-*`, `story-25-2-*`, `story-20-1-*`, `i18n-and-shell.test.tsx`, `story-22-1-*`) and verify `e2e-testids-sync-audit.test.ts`, `zero-dead-buttons-and-silent-catches-audit.test.tsx`, `i18n-dictionary-parity-and-jargon-audit.test.ts`, and `i18n-hardcoded-locale-ast-audit.test.ts`.
- **Layer 2 (`tests/integration/api/`)**: Not impacted (zero backend/SQL changes).
- **Layer 3 (`OpenAPI 3.1`, `lint-imports`)**: Not impacted.
- **Layer 4 & Security**: Delegated to Testing Sub-Agent.
- **Layer 5 (Playwright E2E)**: Sync `apps/web/e2e/07-spaces-org-and-workspace-persistence.spec.ts` (and verify `14`, `15`, `17`, `21`, `shell.spec.ts` testids); full E2E execution delegated to Testing Sub-Agent (`env -u ORCIA_E2E_SEED_FIXTURES`).

---

## 3. Summary of Changes & Results (Post-Implementation)

### 3.1 Created & Modified Files
| File | Action | Lines (`wc -l`) | Concise Summary |
| :--- | :--- | :--- | :--- |
| `apps/web/src/__tests__/story-29-6-spaces-org-help-and-secondary-convergence.test.tsx` | Created | `297` | Bilingual (`fr`/`en`) unit & component convergence suite covering `Mes Espaces`, `Mon Organisation`, `Aide`, and secondary routes. |
| `packages/ui/src/primitives/OrciaPageHeader.tsx` | Modified | `130` | Added optional `titleTestId` prop to preserve legacy `<h1>` selectors natively. |
| `packages/ui/src/primitives/OrciaTabStrip.tsx` | Modified | `150` | Added optional `countTestId` prop on `OrciaTabStripItem` for source/pending tab count badges. |
| `packages/ui/src/primitives/FourZoneDirectionCShell.tsx` | Modified | `295` | Propagated `helpColumnToggleDisabled` and active `/help` route state to the TopBar toggle. |
| `packages/ui/src/primitives/FourZoneShellTypes.ts` | Modified | `180` | Added optional `helpColumnToggleDisabled` flag to `FourZoneDirectionCShellProps`. |
| `packages/ui/src/primitives/FourZoneTopHeaderSection.tsx` | Modified | `262` | Applied `disabled` and `aria-current="page"` visual state on `topbar-contextual-help-toggle` when `/help` is active. |
| `packages/ui/src/primitives/HelpCenterCatalogView.tsx` | Modified | `114` | Removed `max-w-4xl` constraint so `<OrciaDataCard />` spans full main canvas width. |
| `packages/ui/src/primitives/UserProfileOverviewPage.tsx` | Modified | `221` | Converged `/profile` onto `<OrciaPageHeader />` (`profile-display-name`) and `<OrciaDataCard />`. |
| `packages/ui/src/primitives/ActivityLogExplorerView.tsx` | Modified | `218` | Converged `/activity` onto `<OrciaPageHeader />` (`alertSlot` scope banner) and `<OrciaDataCard />`. |
| `packages/ui/src/primitives/WorkspaceFiveTabsAndExternalRebaseView.tsx` | Modified | `275` | Converged workspace 5-tab container onto `<OrciaTabStrip variant="underline" />` and `<OrciaDataCard />`. |
| `packages/ui/src/styles/tokens-headers.css` | Modified | `300` | Synchronized canonical header/tab-strip disabled and active layout tokens (`<= 300` L). |
| `packages/ui/src/__tests__/orcia-page-header-tab-strip-card.test.tsx` | Modified | `191` | Verified `titleTestId` and `countTestId` props on `<OrciaPageHeader />` and `<OrciaTabStrip />`. |
| `apps/web/src/components/ShellContainer.tsx` | Modified | `287` | Passed `helpColumnToggleDisabled={isHelpCenterRoute}` to `FourZoneDirectionCShell`. |
| `apps/web/src/features/admin/organization/orgTreeHelpers.ts` | Modified | `287` | Added pure ancestor vs. sibling read-only classification helpers for organization rows. |
| `apps/web/src/features/cockpit/index.tsx` | Modified | `255` | Added `<OrciaPageHeader />` and `<OrciaDataCard />` framing to `CockpitFeaturePanel`. |
| `apps/web/src/features/settings/packs/PacksRegistryPage.tsx` | Modified | `127` | Converged `/settings/packs` onto `<OrciaPageHeader />` (semantic `<h1>`, `alertSlot`, Cobalt CTA). |
| `apps/web/src/features/workspaces/WorkspaceCompactHeader.tsx` | Modified | `119` | Converged header onto `<OrciaPageHeader />`; removed dead `Phase`, duplicate switcher, and header visibility dropdown. |
| `apps/web/src/features/workspaces/WorkspaceDnaAndWaiversSection.tsx` | Modified | `243` | Passed visibility mutation callbacks and feedback routing into Tab 5 (`WorkspaceMembersAndSettingsTab`). |
| `apps/web/src/features/workspaces/WorkspaceMembersAndSettingsTab.tsx` | Modified | `204` | Hosted workspace visibility governance (`STANDARD`, `CONFIDENTIAL_RESTRICTED`, `PRIVATE_USER`) inside `<OrciaDataCard />` in Tab 5. |
| `apps/web/src/features/workspaces/WorkspaceStudioCardsAndDetailView.tsx` | Modified | `67` | Simplified studio wrapper around `WorkspaceDnaAndWaiversSection`. |
| `apps/web/src/features/workspaces/index.tsx` | Modified | `221` | Routed `workspaces-action-feedback-banner` through `WorkspaceCompactHeader` `alertSlot`. |
| `apps/web/src/routes/SettingsOrganizationUnitRow.tsx` | Modified | `267` | Distinguished ancestor vs. sibling read-only badges and hid unauthorized row write buttons. |
| `apps/web/src/routes/SettingsOrganizationUnitsBlock.tsx` | Modified | `254` | Wrapped organization tree in `<OrciaDataCard />` and removed redundant inline `OrgPedagogicalCallout`. |
| `apps/web/src/routes/organization.tsx` | Modified | `60` | Mounted `<OrciaPageHeader />` with primary/secondary actions and `alertSlot` banners. |
| `apps/web/src/routes/help.tsx` | Modified | `169` | Mounted `<OrciaPageHeader />`, full-width `<ContextualHelpColumnAndCenter />`, and relocated `help-showcase-site-banner` below catalog. |
| `apps/web/src/routes/settings.tsx` | Modified | `249` | Converged `/settings` onto `<OrciaPageHeader />`, `<OrciaTabStrip />`, and `<OrciaDataCard />`. |
| `apps/web/src/i18n/locales/feature_workspaces_labels.ts` | Modified | `154` | Added typed Tab 5 visibility section labels to `FeatureWorkspacesDictionary`. |
| `apps/web/src/i18n/locales/feature_workspaces_labels_en.ts` | Modified | `169` | Added English Tab 5 visibility labels and plain-language hints. |
| `apps/web/src/i18n/locales/feature_workspaces_labels_fr.ts` | Modified | `169` | Added French Tab 5 visibility labels and plain-language hints. |
| `apps/web/src/i18n/locales/governance_and_packs_labels_en.ts` | Modified | `187` | Stripped numeric `"1. "`–`"5. "` prefixes from `workspaceFiveTabs` English labels. |
| `apps/web/src/i18n/locales/governance_and_packs_labels_fr.ts` | Modified | `190` | Stripped numeric `"1. "`–`"5. "` prefixes from `workspaceFiveTabs` French labels. |
| `apps/web/src/i18n/locales/ontology_glossary_labels.ts` | Modified | `243` | Synchronized FR/EN glossary labels with unnumbered tab navigation. |
| `apps/web/src/i18n/locales/organization_tab_labels.ts` | Modified | `190` | Added FR/EN ancestor vs. sibling read-only labels and updated org header copy. |
| `apps/web/e2e/07-spaces-org-and-workspace-persistence.spec.ts` | Modified | `104` | Synchronized Playwright E2E assertions for Tab 5 visibility selector and header convergence. |
| `apps/web/src/__tests__/i18n-and-shell.test.tsx` | Modified | `2306` | Synchronized legacy shell/i18n assertions (Tab 5 visibility, unnumbered tabs, `/help` toggle). |
| `apps/web/src/__tests__/story-20-1-mon-organisation-and-scoped-activity.test.tsx` | Modified | `300` | Synchronized `/organization` header CTAs and hidden unauthorized row action assertions. |
| `apps/web/src/__tests__/story-22-1-workspace-uuid-and-identity.test.tsx` | Modified | `198` | Synchronized workspace header assertions after duplicate switcher removal. |
| `apps/web/src/__tests__/story-24-5-accostage-routes-navigation-and-day0.test.tsx` | Modified | `294` | Synchronized Day-0 `/organization` and `/spaces` assertions (`<= 300` L). |
| `apps/web/src/__tests__/story-24-6-packs-counters-microcopy-and-finops.test.tsx` | Modified | `259` | Synchronized `/settings/packs` `<OrciaPageHeader />` assertions. |
| `apps/web/src/__tests__/story-25-2-shell-9-items-org-admin-and-unified-scope.test.tsx` | Modified | `391` | Synchronized legacy shell/org assertions with header action placement and row permissions. |
| `apps/web/src/__tests__/story-28-1-single-workspace-header-and-zero-uuid.test.tsx` | Modified | `246` | Synchronized single workspace header assertions without Phase dropdown. |
| `apps/web/src/__tests__/story-28-3-scoped-sources-deliverables-and-members-tabs.test.tsx` | Modified | `280` | Synchronized Tab 5 workspace settings and unnumbered tab assertions. |
| `apps/web/src/__tests__/story-29-2-workspace-patch-rollback-and-banner.test.tsx` | Modified | `296` | Synchronized Tab 5 visibility rollback and `alertSlot` banner assertions. |

### 3.2 Quantitative Metrics, Coverage & Static Quality
- **Line-count compliance**: All `32` modified/created production `.ts`/`.tsx`/`.css` files are `<= 300` lines (max `300` L in `tokens-headers.css`); new test `story-29-6-spaces-org-help-and-secondary-convergence.test.tsx` is `297` L; `story-24-5-accostage-routes-navigation-and-day0.test.tsx` is `294` L; `orcia-page-header-tab-strip-card.test.tsx` is `191` L.
- **Frontend Vitest & Turborepo**:
  - `pnpm --filter @orcia/ui run test`: `37` files / `147` tests passed.
  - `pnpm --filter @orcia/web exec vitest run --maxWorkers=4`: `89` files / `329` tests passed (including `story-29-6`, i18n Gates 1–3, `zero-dead-buttons-and-silent-catches-audit`, and `e2e-testids-sync-audit`).
  - `pnpm turbo run lint typecheck test --concurrency=1`: `9/9` tasks successful (`@orcia/api-client` `3` files / `20` tests, `@orcia/ui` `37` files / `147` tests, `@orcia/web` `89` files / `329` tests; `496` total JS/TS tests).
- **Python Static, English-Diff, Security, Contract & Evals**:
  - `tests/unit/test_i18n_backend_catalog_and_english_dev_audit.py`: `3 passed` (`8.13 s`).
  - `ruff check .` & `ruff format --check .`: `0` warnings (`1745` files formatted).
  - `mypy --strict packages/orcia-core packages/orcia-connectors apps/api apps/worker`: `0` issues (`856` source files).
  - `lint-imports`: `5 contracts kept, 0 broken` (`899` files, `6486` dependencies).
  - `lint_spine.py`: `ok: true, total_findings: 0`.
  - `scripts/export_openapi.py --check`: exit `0` (`0-diff`).
  - `tests/security tests/contract tests/evals`: `181 passed` (`57.32 s`).
- **GitNexus Index & Diff Analysis (`repo: "ORCIA"`)**:
  - `npx gitnexus analyze --index-only .`: `46,472` nodes, `117,154` edges, `776` clusters, `1531` flows.
  - `gitnexus_detect_changes(scope="all", worktree=".../audit_ui_headers")`: `changed_count: 18`, `affected_count: 0`, `changed_files: 42`, `risk_level: "low"`.

### 3.3 AD-17 Test Pyramid & Vertical Wiring Verification
- **Layer 1a & Layer 1b (Unit / Component / AST Audits)**: `3/3` Python i18n/English-diff checks and `496/496` JS/TS Vitest tests passed without `isJsdom` shortcuts or dead buttons.
- **Layer 2 (Vertical Integration `HTTP ➔ PostgreSQL 18`)**: Preserved unchanged (`0` backend/SQL modifications in Story `29.6`); verified end-to-end via real PostgreSQL 18 + Redis 7.4 ephemeral stack in Layer 5.
- **Layer 3 (Contracts & Architecture)**: `export_openapi.py --check` (`0-diff`), `lint-imports` (`5/5` contracts kept), `lint_spine.py` (`0` findings), and `tests/contract` passed.
- **Layer 4 (`$0` Golden Evals) & Security (`tests/evals`, `tests/security`)**: `181/181` passed across `tests/security`, `tests/contract`, and `tests/evals`.
- **Layer 5 (Playwright Desktop E2E, `--project=desktop-cockpit`, `env -u ORCIA_E2E_SEED_FIXTURES`)**:
  - **Batch 1** (`07-spaces-org-and-workspace-persistence`, `11-screens-smoke-without-server-errors`, `14-auth-2fa-account-and-profile`, `15-organization-iam-secops-inbox-and-observer`): `10 passed (1.7 m)`.
  - **Batch 2** (`17-workspace-sources-codegraph-dna-and-ontology`, `21-assistant-citations-v5-audit-help-showcase`, `09-pack-builder-and-contextual-help`, `18-catalog-packs-wizards-and-mcp-bench`, `shell`): `15 passed (2.2 m)`.
  - **Total Desktop E2E**: `25 passed, 0 failed` (`apps/web/test-results` and `/tmp/orcia-e2e-29-6` cleaned, `0` leftover worktree processes).
