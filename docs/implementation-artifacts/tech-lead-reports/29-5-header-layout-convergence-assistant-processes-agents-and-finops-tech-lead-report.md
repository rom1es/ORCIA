# Story 29.5 — Header & Layout Convergence: `Mon Assistant`, `Mes Processus`, `Mes Agents` & `FinOps`

- **Date**: 2026-11-25
- **Story / Sprint Key**: `29-5-header-layout-convergence-assistant-processes-agents-and-finops` (`Epic 29` / Lot 3 — Batch A)
- **Capability(ies)**: `CAP-030`, `CAP-040`, `CAP-060`, `CAP-070`, `CAP-071`, `CAP-080`, `CAP-090`, `CAP-091`, `CAP-140`, `CAP-200` (`docs/product/capabilities.yaml`) — classification: `ux`
- **Author / Context**: Resolves findings `UH-06` (`P1`), `UH-09` (`P1`), `UH-11` (`P1`), and `UH-12` (`P1`) from `docs/planning-artifacts/sprint-change-proposal-2026-11-24-epic-29-ui-headers-scope-and-screen-consistency.md`. Converges ORCIA's four primary operational screens (`Mon Assistant` `/assistant`, `Mes Processus` `/processes`, `Mes Agents` `/agents`, and `FinOps` `/finops`) onto the canonical Direction C primitives introduced in Story `29.4` (`<OrciaPageHeader />`, `<OrciaTabStrip />`, `<OrciaDataCard />`, and `.orcia-ds-filter-pill`), enforcing three-tier Cobalt visual grammar separation, zero tab-switch layout wrap (`CLS = 0`), separated outbound MCP vs inbound IDE cards without raw RPC jargon, clean scope-pill differentiation, and `<= 300`-line modular files.
- **Associated Commits**: `pending (working tree)`

---

## 1. Needs Analysis & Tech Lead Impact Study (Pre-Implementation)

### 1.1 Context & Problem Statement
1. **`Mon Assistant` (`/assistant`) — Missing Canonical Page Header & Ad-Hoc Card Bar (`UH-06`)**:
   - **Current behavior**: `ModuleWorkspaceView.tsx` bypasses header rendering for `moduleKey="inbox"`, leaving `InboxFeaturePanel` (`apps/web/src/features/inbox/index.tsx`) to render an ad-hoc rounded pill toolbar (`AssistantTopToolbar.tsx`) above a raw `<div className="orcia-bento-card space-y-3">` stream container and an inline feedback banner above the toolbar.
   - **Expected behavior**: Mount `<OrciaPageHeader />` (`<h1>`, monochrome `"assistant"` `<OrciaIcon />`, 1-line subtitle, right-aligned settings CTA `assistant-open-governance-btn` and single Cobalt primary CTA `assistant-new-conversation-btn`, Tier-2 `<OrciaTabStrip />` for Active Discussion / Saved Conversations / Folders, and `alertSlot` strictly below `<header>`), and wrap stream/saved panels inside `<OrciaDataCard />` while preserving all existing `data-testid` attributes (`assistant-new-conversation-btn`, `assistant-saved-conversations-toggle-btn`, `assistant-folders-toggle-btn`, `assistant-open-governance-btn`).
2. **`Mes Processus` (`/processes`) — Missing Page Header, Competing Solid-Blue CTAs & `"Mon Compte"` Leakage (`UH-06`, `UH-11`)**:
   - **Current behavior**: `ProcessesHubPage.tsx` renders no `<OrciaPageHeader />`, places `processes-hub-error-banner` at the top above cards, embeds `+ Nouveau processus` inside `ProcessCatalogCardGrid.tsx` alongside solid-Cobalt `orcia-ds-tab` filters, applies solid `orcia-ds-btn-primary` styling simultaneously to `resume-featured-dossier-btn` and all `Lancer ce processus` card buttons, and leaks `"Mon Compte"` (`featuredDossierPrefix`) under global `"Tous mes espaces"` scope.
   - **Expected behavior**: Mount `<OrciaPageHeader />` (`<h1>`, `"processes"` `<OrciaIcon />`, 1-line subtitle, single Cobalt primary CTA `open-create-process-modal-btn`, and `alertSlot` below `<header>`), frame content panels in `<OrciaDataCard />`, convert filter controls to `.orcia-ds-filter-pill`, restyle repeated card launch / dossier review buttons as secondary Cobalt-outline (`orcia-ds-btn-cobalt-outline`), and remove `"Mon Compte"` title leakage from `featuredDossierPrefix`.
3. **`Mes Agents` (`/agents`) — Mega-Card Wrapper, Tab-Switch Wrap (`CLS`) & Misplaced MCP/IDE Cards (`UH-06`, `UH-09`, `UH-14`)**:
   - **Current behavior**: `AgentsAndSkillsManagerView.tsx` wraps the entire screen inside a single outer bordered mega-card (`p-4`), `AgentsAndSkillsHeaderAndToolbar.tsx` places `role="tablist"` tabs and dynamic CTAs in one `flex-wrap` header row causing Tab 3 (`Serveurs d'outils & MCP`) to wrap onto Row 2, renders Agent/Skill KPIs and search/filters unconditionally across Tab 3, uses emoji prefixes on header/tab labels, and mixes outbound MCP connection testing with inbound IDE exposure (`assistant.ask`, `agent.invoke`, `agent.list_exposed`) inside one shared card (`RemoteServiceTestBenchAndMcpExposureView.tsx`).
   - **Expected behavior**: Unwrap the outer mega-card, mount `<OrciaPageHeader />` with Tier-2 `<OrciaTabStrip />` (eliminating Tab-3 wrap), guard KPIs and `.orcia-ds-filter-pill` search/filter card to `activeTab !== "CONNECTIONS"`, remove emoji prefixes from headings/tabs, use secondary Cobalt-outline styling on repeated agent card actions, split `RemoteServiceTestBenchAndMcpExposureView.tsx` into two distinct `<OrciaDataCard />` surfaces (outbound MCP server testing vs inbound IDE access), and map raw RPC identifiers (`assistant.ask`, `agent.invoke`, `agent.list_exposed`) to human-readable bilingual capability labels while retaining `exposed-mcp-tool-*` `data-testid` attributes.
4. **`FinOps` (`/finops`) — Bare Canvas Header, Truncated Activity CTA, Indistinct Scope Pills & Unboxed Tables (`UH-06`, `UH-12`)**:
   - **Current behavior**: `FinopsGovernanceDashboardView.tsx` renders an unboxed `<div className="finops-dashboard-header">` directly on `#EAF2FB`, styles scope pills (`finops-scope-*`) identically to tabs (`.orcia-ds-tab`), allows `finops-open-activity-link` to wrap/truncate, places `finops-error-banner` above the header in `FinopsFeaturePanel`, and renders `FinopsProcessAndTiersTab` / `FinopsRemoteMcpServicesTab` tables directly on `#EAF2FB` without white card containers.
   - **Expected behavior**: Mount `<OrciaPageHeader />` (`testId="finops-page"`, preserving `finops-page-title` on `<h1>`, `finops-open-activity-link` non-wrapping in `secondaryActions`, single Cobalt `finops-configure-budget-btn` in `primaryAction`, `<OrciaTabStrip />` in Tier 2 `tabs`, distinct `.orcia-ds-filter-pill` `finops-scope-pills` in Tier 2 `scopeBar`, and `alertSlot` below `<header>`), and wrap FinOps tables and placeholders inside `<OrciaDataCard />`.

### 1.2 Exploration, GitNexus Impact Analysis, Refactoring & Technical Debt
- **GitNexus & Upstream Caller Impact Analysis (`repo: "ORCIA"`)**:
  - `gitnexus_query` (`repo: "ORCIA"`) reported the pre-built index is 5 commits behind HEAD (`AssistantTopToolbar`, `ProcessesHubPage`, `AgentsAndSkillsManagerView`, `FinopsGovernanceDashboardView` symbol lookup returned not found in the stale worktree index). Direct workspace `grep` inspection identified all upstream callers and consumers:
    - `apps/web/src/router.tsx` (`ProcessesHubPage` at `/processes`, `ModuleWorkspaceView` at `/assistant`, `/agents`, `/finops`),
    - `apps/web/src/components/ModuleWorkspaceView.tsx` (`InboxFeaturePanel`, `CatalogFeaturePanel`, `FinopsFeaturePanel`),
    - `apps/web/src/features/inbox/SavedConversationsAndThreadView.tsx` (re-exports `AssistantTopToolbar`),
    - `packages/ui/src/index.ts` (exports `AgentsAndSkillsManagerView`, `RemoteServiceTestBenchAndMcpExposureView`, `FinopsGovernanceDashboardView`),
    - E2E & Vitest suites: `e2e/02`, `e2e/08`, `e2e/09`, `e2e/12`, `e2e/13`, `e2e/18`, `e2e/20`, `e2e/22`, `story-6-2`, `story-6-3`, `story-6-4`, `story-7-4`, `story-16-3`, `story-16-4`, `story-22-2`, `story-22-3`, `story-23-5`, `story-24-3`, `story-29-1`, `agents-and-skills.test.tsx`, `zero-dead-buttons-and-silent-catches-audit.test.tsx`, `e2e-testids-sync-audit.test.ts`, and `i18n-and-shell.test.tsx`.
  - **Risk level**: Medium-Low. Preserving every existing `data-testid`, `role`, `aria-selected`, and callback contract prevents regressions in existing unit and E2E suites while cleanly migrating visual structure.
- **Exploration & Key Metrics**:
  - Verified `packages/ui/src/primitives/OrciaPageHeader.tsx` (124 lines), `OrciaTabStrip.tsx` (144 lines), `OrciaDataCard.tsx` (84 lines), and `packages/ui/src/styles/tokens-headers.css` (300 lines) from Story `29.4`.
  - Identified CSS specificity interaction: `.orcia-ds-tab, [role="tab"]` in `tokens-components.css` targets `[role="tab"]`; therefore `.orcia-ds-filter-pill[role="tab"]` (and `[aria-selected="true"]`) must be explicitly styled in a modular stylesheet (`tokens-actions.css`) imported in `tokens.css` so `finops-scope-pills` retains `[role="tab"]` + `aria-selected` test contracts while rendering visually as neutral filter pills distinct from `<OrciaTabStrip />` and `.orcia-ds-btn-primary`.
- **Refactoring Opportunities & File Line-Count Control (`<= 300` lines)**:
  - Add `packages/ui/src/styles/tokens-actions.css` (`<= 80` lines) for `.orcia-ds-btn-cobalt-outline` and `.orcia-ds-filter-pill[role="tab"]` overrides, keeping `tokens-components.css` (293 lines) and `tokens-headers.css` (300 lines) strictly `<= 300` lines.
  - Ensure all modified `.ts`/`.tsx` files (`AssistantTopToolbar.tsx`, `InboxActiveTraceAndTurns.tsx`, `features/inbox/index.tsx`, `ProcessesHubPage.tsx`, `ProcessesActiveDossiersCard.tsx`, `ProcessCatalogCardGrid.tsx`, `AgentsAndSkillsHeaderAndToolbar.tsx`, `AgentsAndSkillsManagerView.tsx`, `RemoteServiceTestBenchAndMcpExposureView.tsx`, `FinopsGovernanceDashboardView.tsx`, `FinopsProcessAndTiersTab.tsx`, `FinopsRemoteMcpServicesTab.tsx`, `FinopsKpiStrip.tsx`, `features/finops/index.tsx`) remain strictly `<= 300` lines.

---

## 2. Implementation Plan

### 2.1 Data Schema & Alembic Migrations (`infra/migrations/versions/...`)
- None required. Story `29.5` is strictly a frontend UI convergence, `@orcia/ui` component layout, CSS token, and i18n update.

### 2.2 Hexagonal Core, Orchestration & Workers (`packages/orcia-core/`, `apps/worker/`)
- None required.

### 2.3 Backend API, Security & Contracts (`apps/api/`, `packages/api-client/`)
- None required.

### 2.4 User Interface & Experience (`packages/ui/`, `apps/web/`)
1. **Design Tokens (`packages/ui/src/styles/`)**:
   - Create `tokens-actions.css` defining `.orcia-ds-btn-cobalt-outline` (secondary Cobalt outline button for repeated card CTAs using `var(--color-badge-cobalt-border)`, `var(--color-badge-cobalt-fg)`, `var(--color-action-primary-subtle)`) and `.orcia-ds-filter-pill[role="tab"]` / `.orcia-ds-filter-pill:hover` overrides so scope/filter pills never inherit legacy Cobalt tab fill; import `./tokens-actions.css` in `tokens.css`.
2. **`Mon Assistant` (`apps/web/src/features/inbox/`)**:
   - Refactor `AssistantTopToolbar.tsx` to render `<OrciaPageHeader />` (`icon="assistant"`, `<h1>`, 1-line subtitle, `assistant-open-governance-btn` in `secondaryActions`, `assistant-new-conversation-btn` in `primaryAction`, `<OrciaTabStrip />` in Tier 2 `tabs` with `assistant-active-discussion-tab`, `assistant-saved-conversations-toggle-btn`, `assistant-folders-toggle-btn`, and `alertSlot` for `assistant-governance-feedback-banner`).
   - Update `features/inbox/index.tsx` and `SavedConversationsAndThreadView.tsx` to pass `alertSlot` into `InboxTopSection` -> `AssistantTopToolbar`, wrap the stream body in `<OrciaDataCard testId="assistant-stream-card">`, and wrap `SavedConversationsPanel` in `<OrciaDataCard testId="assistant-saved-conversations-panel">`.
   - Add missing toolbar tab labels to `feature_inbox_assistant_labels*.ts` (`tabsAriaLabel`, `activeDiscussionTab`) in both `fr` and `en`.
3. **`Mes Processus` (`apps/web/src/features/processes/`)**:
   - Update `ProcessesHubPage.tsx` to mount `<OrciaPageHeader />` (`testId="processes-page-header"`, `icon="processes"`, `<h1>`, 1-line subtitle, single solid Cobalt `open-create-process-modal-btn` in `primaryAction`, and `processes-hub-error-banner` in `alertSlot`).
   - Update `ProcessCatalogCardGrid.tsx` to wrap in `<OrciaDataCard />`, render filter pills with `.orcia-ds-filter-pill`, and restyle `execute-workflow-btn-*` to `.orcia-ds-btn-cobalt-outline`.
   - Update `ProcessesActiveDossiersCard.tsx`, `ProcessesValueStreamOverviewCard.tsx`, and `AutonomousRunsSupervisionPanel.tsx` to use `<OrciaDataCard />` / `.orcia-ds-btn-cobalt-outline`, and replace `"Mon Compte"` in `process_studio_ui_labels_{fr,en}.ts` `featuredDossierPrefix` with scope-neutral copy (`"Dossier prioritaire"` / `"Priority Dossier"`).
4. **`Mes Agents` (`packages/ui/src/components/` & `apps/web/src/i18n/locales/`)**:
   - Unwrap the outer mega-card in `AgentsAndSkillsManagerView.tsx` (`className="orcia-ds-page"`).
   - Refactor `AgentsAndSkillsHeaderAndToolbar.tsx` to mount `<OrciaPageHeader />` (`icon="agents"`, `<h1>`, 1-line subtitle, secondary Pack import button, single active-tab primary CTA, and Tier-2 `<OrciaTabStrip />`), and guard `<OrciaDataCard testId="agents-kpi-and-filters-card">` (KPI strip + search + `.orcia-ds-filter-pill` filters) strictly to `activeTab !== "CONNECTIONS"`.
   - Update `WorkspaceAssistantPinnedCard.tsx` and `AgentStudioCardItem.tsx` to use `<OrciaDataCard />` / `.orcia-ds-btn-cobalt-outline` instead of competing solid Cobalt CTAs.
   - Refactor `RemoteServiceTestBenchAndMcpExposureView.tsx` into two distinct `<OrciaDataCard />` surfaces (`outbound-mcp-server-card` and `governed-mcp-exposure-panel`) and format exposed capability badges with human-readable i18n labels (`exposedCapabilityLabels`) instead of raw RPC strings while keeping `exposed-mcp-tool-*` `data-testid`s.
   - Remove emoji prefixes from `agentsAndSkillsManager` and `remoteServiceTestBench` headings/tabs in `governance_and_packs_labels_{fr,en}.ts` and add optional bilingual labels on `AgentsAndSkillsManagerLabels` / `RemoteServiceTestBenchLabels`.
5. **`FinOps` (`packages/ui/src/primitives/finops/` & `apps/web/src/features/finops/`)**:
   - Refactor `FinopsGovernanceDashboardView.tsx` to mount `<OrciaPageHeader />` (`testId="finops-page"`, `icon="finops"`, `<h1>` `finops-page-title`, 1-line subtitle, `secondaryActions={headerActions}`, `primaryAction` `finops-configure-budget-btn`, Tier-2 `<OrciaTabStrip />` `finops-tab-strip`, Tier-2 `scopeBar` `finops-scope-pills` with `.orcia-ds-filter-pill`, and `alertSlot`), keeping `FinopsKpiStrip` below `<OrciaPageHeader />` and wrapping tab contents in `<OrciaDataCard />`.
   - Wrap `FinopsProcessAndTiersTab.tsx` tables, `FinopsRemoteMcpServicesTab.tsx` table, `FinopsKpiStrip.tsx` empty state, and `FinopsHumanMasteryWorkflowsTable.tsx` in `<OrciaDataCard />` framing, and pass `finops-error-banner` / `finops-success-banner` via `alertSlot` from `apps/web/src/features/finops/index.tsx` (with `whitespace-nowrap` on `finops-open-activity-link`).

### 2.5 Test Pyramid Impact Analysis (`AD-17` — Layers 1 to 5 + Security, Mandatory)
- **Layer 1a (`tests/unit/`)**: `tests/unit/test_i18n_backend_catalog_and_english_dev_audit.py` ensures zero French regressions in code comments/docstrings.
- **Layer 1b (`packages/ui` & `apps/web` Vitest)**:
  - Add `apps/web/src/__tests__/story-29-5-core-screens-header-convergence.test.tsx` (`<= 300` lines) verifying `<OrciaPageHeader />` (`<h1>`), `<OrciaTabStrip />`, `<OrciaDataCard />`, preserved `data-testid`s, single solid Cobalt primary CTA, Tab-3 KPI/filter hiding on `Mes Agents`, human-readable MCP capability labels, non-leaking `"Mon Compte"` on `Mes Processus`, and bilingual `fr`/`en` rendering across all 4 screens.
  - Run `@orcia/ui` test suite (`agents-and-skills.test.tsx`, `story-24-3-remote-test-bench-and-mcp-exposure.test.tsx`, `story-29-1-finops-pills-and-error-guard.test.tsx`, etc.) and impacted `@orcia/web` tests (`e2e-testids-sync-audit.test.ts`, `zero-dead-buttons-and-silent-catches-audit.test.tsx`, `i18n-dictionary-parity-and-jargon-audit.test.ts`, `i18n-hardcoded-locale-ast-audit.test.ts`, plus assistant/processes/agents/finops specs).
- **Layer 2 (`tests/integration/api/`)**: Not impacted (pure UI/CSS/i18n story).
- **Layer 3 (`OpenAPI 3.1`, `lint-imports`)**: Not impacted.
- **Layer 4 & Security**: Delegated to Testing Sub-Agent.
- **Layer 5 (Playwright E2E)**: Delegated to Testing Sub-Agent (`e2e/02`, `e2e/08`, `e2e/12`, `e2e/13`, `e2e/18`, `e2e/20`, `e2e/22` with `env -u ORCIA_E2E_SEED_FIXTURES`).

---

## 3. Summary of Changes & Results (Post-Implementation)

### 3.1 Created & Modified Files (`wc -l`)
| File | Action | Line Count (`wc -l`) | Concise Summary |
| :--- | :--- | :--- | :--- |
| `packages/ui/src/styles/tokens-actions.css` | Created | `67` | Defined `.orcia-ds-btn-cobalt-outline` secondary Cobalt-outline CTA styling and `.orcia-ds-filter-pill[role="tab"]` specificity overrides to prevent legacy Cobalt tab-fill inheritance. |
| `packages/ui/src/styles/tokens.css` | Modified | `13` | Imported `./tokens-actions.css` in the Direction C token stylesheet barrel. |
| `packages/ui/src/components/AgentsAndSkillsManagerView.tsx` | Modified | `278` | Unwrapped the outer bordered mega-card (`orcia-ds-page`) and delegated header/KPI/filter framing to canonical primitives. |
| `packages/ui/src/components/AgentsAndSkillsHeaderAndToolbar.tsx` | Modified | `240` | Mounted `<OrciaPageHeader />` (`icon="agents"`, `<h1>`, 1-line subtitle, Tier-2 `<OrciaTabStrip />`), and guarded KPIs + `.orcia-ds-filter-pill` search/filter `<OrciaDataCard />` to `activeTab !== "CONNECTIONS"`. |
| `packages/ui/src/components/AgentsAndSkillsTypes.ts` | Modified | `190` | Added optional bilingual label props (`tabsAriaLabel`, `subtitle`, `mcpSectionTitle`, etc.) on `AgentsAndSkillsManagerLabels`. |
| `packages/ui/src/components/AgentsAndSkillsSkillsPanel.tsx` | Modified | `150` | Wrapped skills catalog panel inside `<OrciaDataCard />` and aligned secondary card action button styling. |
| `packages/ui/src/components/AgentStudioCardItem.tsx` | Modified | `214` | Restyled repeated agent card action CTAs to `.orcia-ds-btn-cobalt-outline` to preserve a single solid Cobalt primary CTA. |
| `packages/ui/src/components/SkillStudioCardItem.tsx` | Modified | `202` | Aligned skill card CTA styling to `.orcia-ds-btn-cobalt-outline`. |
| `packages/ui/src/components/WorkspaceAssistantPinnedCard.tsx` | Modified | `81` | Framed pinned Workspace Assistant summary inside `<OrciaDataCard />` with secondary Cobalt-outline styling. |
| `packages/ui/src/primitives/RemoteServiceTestBenchAndMcpExposureView.tsx` | Modified | `244` | Split outbound MCP server testing (`outbound-mcp-server-card`) and inbound IDE access (`governed-mcp-exposure-panel`) into two distinct `<OrciaDataCard />` surfaces with human-readable capability labels (`exposedCapabilityLabels`) preserving `exposed-mcp-tool-*` `data-testid`s. |
| `packages/ui/src/primitives/finops/FinopsGovernanceDashboardView.tsx` | Modified | `280` | Migrated `/finops` onto `<OrciaPageHeader />` (`testId="finops-page"`, `<h1>` `finops-page-title`, `secondaryActions`, single Cobalt `finops-configure-budget-btn`, Tier-2 `<OrciaTabStrip />`, Tier-2 `.orcia-ds-filter-pill` `finops-scope-pills`, and `alertSlot`). |
| `packages/ui/src/primitives/finops/FinopsDashboardTypes.ts` | Modified | `169` | Extended `FinopsDashboardLabels` with bilingual header subtitle and tab strip ARIA label keys. |
| `packages/ui/src/primitives/finops/FinopsKpiStrip.tsx` | Modified | `193` | Framed FinOps KPI empty state inside `<OrciaDataCard />`. |
| `packages/ui/src/primitives/finops/FinopsProcessAndTiersTab.tsx` | Modified | `218` | Wrapped FinOps process breakdown and cognitive tier tables inside `<OrciaDataCard />`. |
| `packages/ui/src/primitives/finops/FinopsRemoteMcpServicesTab.tsx` | Modified | `217` | Wrapped remote MCP service quota/telemetry table and empty state inside `<OrciaDataCard />`. |
| `packages/ui/src/primitives/finops/FinopsHumanMasteryWorkflowsTable.tsx` | Modified | `85` | Wrapped human mastery workflows breakdown table inside `<OrciaDataCard />`. |
| `apps/web/src/features/inbox/AssistantTopToolbar.tsx` | Modified | `132` | Migrated `Mon Assistant` toolbar onto `<OrciaPageHeader />` (`icon="assistant"`, `<h1>`, 1-line subtitle, `assistant-open-governance-btn` in `secondaryActions`, `assistant-new-conversation-btn` in `primaryAction`, Tier-2 `<OrciaTabStrip />`, and `alertSlot`). |
| `apps/web/src/features/inbox/InboxActiveTraceAndTurns.tsx` | Modified | `257` | Threaded `alertSlot` into `InboxTopSection` -> `AssistantTopToolbar`. |
| `apps/web/src/features/inbox/SavedConversationsAndThreadView.tsx` | Modified | `228` | Framed `SavedConversationsPanel` inside `<OrciaDataCard testId="assistant-saved-conversations-panel">` and preserved toolbar re-exports. |
| `apps/web/src/features/inbox/index.tsx` | Modified | `289` | Passed `assistant-governance-feedback-banner` via `alertSlot` below `<OrciaPageHeader />` and wrapped stream body in `<OrciaDataCard testId="assistant-stream-card">`. |
| `apps/web/src/features/inbox/useServerAssistantFolders.ts` | Modified | `240` | Added stale-request sequence guard (`fetchSeqRef`) and `mountedRef` protection on server assistant folder hydration to prevent out-of-order stale response overwrites. |
| `apps/web/src/features/processes/ProcessesHubPage.tsx` | Modified | `214` | Mounted `<OrciaPageHeader />` (`testId="processes-page-header"`, `icon="processes"`, `<h1>`, single Cobalt `open-create-process-modal-btn`, and `processes-hub-error-banner` in `alertSlot`). |
| `apps/web/src/features/processes/ProcessCatalogCardGrid.tsx` | Modified | `226` | Wrapped catalog grid in `<OrciaDataCard />`, converted filter pills to `.orcia-ds-filter-pill`, and restyled repeated `execute-workflow-btn-*` CTAs to `.orcia-ds-btn-cobalt-outline`. |
| `apps/web/src/features/processes/ProcessesActiveDossiersCard.tsx` | Modified | `101` | Framed active dossiers inside `<OrciaDataCard />` with secondary Cobalt-outline CTA styling. |
| `apps/web/src/features/processes/ProcessesValueStreamOverviewCard.tsx` | Modified | `103` | Framed value stream overview panel inside `<OrciaDataCard />`. |
| `apps/web/src/features/processes/AutonomousRunsSupervisionPanel.tsx` | Modified | `215` | Framed autonomous runs supervision panel inside `<OrciaDataCard />`. |
| `apps/web/src/features/catalog/index.tsx` | Modified | `249` | Passed bilingual `exposedCapabilityLabels` and header subtitle/tab props into `AgentsAndSkillsManagerView` and `RemoteServiceTestBenchAndMcpExposureView`. |
| `apps/web/src/features/finops/index.tsx` | Modified | `80` | Passed `finops-error-banner` / `finops-success-banner` via `alertSlot` below `<OrciaPageHeader />` and enforced `whitespace-nowrap` on `finops-open-activity-link`. |
| `apps/web/src/i18n/locales/feature_inbox_assistant_labels.ts` | Modified | `89` | Added `tabsAriaLabel`, `activeDiscussionTab`, and header subtitle keys to `FeatureInboxAssistantDictionary`. |
| `apps/web/src/i18n/locales/feature_inbox_assistant_labels_fr.ts` | Modified | `103` | Added French toolbar tab & header subtitle labels for `Mon Assistant`. |
| `apps/web/src/i18n/locales/feature_inbox_assistant_labels_en.ts` | Modified | `102` | Added English toolbar tab & header subtitle labels for `My Assistant`. |
| `apps/web/src/i18n/locales/finops_labels.ts` | Modified | `103` | Refactored `FinopsDictionarySection` to import split FR/EN modules (`<= 300` L compliance). |
| `apps/web/src/i18n/locales/finops_labels_fr.ts` | Created | `107` | Extracted French FinOps dictionary labels including header subtitle and tab strip ARIA label. |
| `apps/web/src/i18n/locales/finops_labels_en.ts` | Created | `107` | Extracted English FinOps dictionary labels including header subtitle and tab strip ARIA label. |
| `apps/web/src/i18n/locales/governance_and_packs_labels_fr.ts` | Modified | `190` | Removed emoji prefixes on `agentsAndSkillsManager` / `remoteServiceTestBench` headings/tabs and added human-readable French MCP capability labels (`exposedCapabilityLabels`). |
| `apps/web/src/i18n/locales/governance_and_packs_labels_en.ts` | Modified | `187` | Removed emoji prefixes on `agentsAndSkillsManager` / `remoteServiceTestBench` headings/tabs and added human-readable English MCP capability labels (`exposedCapabilityLabels`). |
| `apps/web/src/i18n/locales/process_studio_ui_labels_fr.ts` | Modified | `190` | Replaced `"Mon Compte"` in `featuredDossierPrefix` with scope-neutral `"Dossier prioritaire"` and added `Mes Processus` header subtitle copy. |
| `apps/web/src/i18n/locales/process_studio_ui_labels_en.ts` | Modified | `187` | Replaced `"My Account"` in `featuredDossierPrefix` with scope-neutral `"Priority Dossier"` and added `My Processes` header subtitle copy. |
| `apps/web/src/__tests__/story-29-5-core-screens-header-convergence.test.tsx` | Created | `230` | Unit & integration Vitest suite (`4` tests) verifying `<OrciaPageHeader />` (`<h1>`), `<OrciaTabStrip />`, `<OrciaDataCard />`, preserved `data-testid`s, single solid Cobalt primary CTA, Tab-3 KPI/filter hiding on `Mes Agents`, human-readable MCP capability labels, non-leaking `"Mon Compte"` on `Mes Processus`, and bilingual `fr`/`en` rendering across all 4 screens. |
| `apps/web/src/__tests__/story-29-5-folders-fetch-race-guard.test.tsx` | Created | `240` | Unit Vitest suite (`3` tests) verifying stale-response ordering guard and unmount safety in `useServerAssistantFolders.ts`. |
| `apps/web/src/__tests__/story-22-3-assistant-inbox-and-broker.test.tsx` | Modified | `291` | Updated assertions for `<OrciaPageHeader />` / `<OrciaTabStrip />` markup on `Mon Assistant`. |
| `packages/ui/src/__tests__/story-24-4-css-modals-contrast-and-tabs.test.tsx` | Modified | `326` | Updated tab/pill CSS rule assertions for `.orcia-ds-filter-pill[role="tab"]` specificity (`pre-existing legacy test file > 300 L`). |
| `apps/web/e2e/08-agents-skills-persistence.spec.ts` | Modified | `100` | Updated E2E tab/card assertions for `Mes Agents` (`OrciaTabStrip` & separated MCP/IDE cards). |

All `42` production, i18n, E2E, and new Story `29.5` test files are `<= 291` lines (`13`–`291` lines); only the pre-existing `packages/ui/src/__tests__/story-24-4-css-modals-contrast-and-tabs.test.tsx` test file stands at `326` lines.

### 3.2 Quantitative Metrics, Test Results & Static Quality
- **Frontend Unit & Component Suites (`Vitest`)**:
  - `@orcia/ui` (`pnpm --filter @orcia/ui run test`): **`37` test files passed (`37`), `147` tests passed (`147`)** in `8.79s` (including `story-24-4-css-modals-contrast-and-tabs.test.tsx` `3/3`).
  - `@orcia/web` (`pnpm --filter @orcia/web exec vitest run --maxWorkers=4`): **`88` test files passed (`88`), `325` tests passed (`325`)** in `76.06s` (including `story-29-5-core-screens-header-convergence.test.tsx` `4/4`, `story-29-5-folders-fetch-race-guard.test.tsx` `3/3`, `story-22-3-assistant-inbox-and-broker.test.tsx` `3/3`).
  - Monorepo Turbo (`pnpm turbo run lint typecheck test --concurrency=1`): **`9/9` tasks successful** in `46.749s` (`@orcia/api-client`: `3` files / `20` tests passed; `@orcia/ui`: `37` files / `147` tests passed; `@orcia/web`: `88` files / `325` tests passed — **`492` JS/TS tests passed**, `0` errors).
- **Static Quality, Architecture & Security/Contract/Evals**:
  - `tests/unit/test_i18n_backend_catalog_and_english_dev_audit.py`: **`3` passed** in `8.14s` (`0` non-English regressions).
  - `.venv/bin/ruff check . && .venv/bin/ruff format --check .`: **`0` warnings / `1,744` files formatted**.
  - `.venv/bin/mypy --strict packages/orcia-core packages/orcia-connectors apps/api apps/worker`: **`0` issues in `856` source files**.
  - `.venv/bin/lint-imports`: **`5` contracts kept, `0` broken** (`899` files, `6,486` dependencies).
  - `lint_spine.py`: **`ok: true`, `0` findings**.
  - `scripts/export_openapi.py --check`: **`0-diff`** (`exit 0`).
  - `tests/security tests/contract tests/evals`: **`181` passed** (`1` Starlette deprecation warning) in `58.59s`.
- **Playwright Desktop E2E (`--project=desktop-cockpit`, `env -u ORCIA_E2E_SEED_FIXTURES`, real PG18 + Redis 7.4)**:
  - **Batch 1** (`02-assistant-streaming-and-folders`, `08-agents-skills-persistence`, `11-screens-smoke-without-server-errors`, `12-epic16-reflexive-trace-and-line-inspector`, `12-finops-and-audit-provenance`): **`8 passed, 1 skipped (mobile-companion only in 12-finops), 0 failed` (`1.4m`)**.
  - **Batch 2** (`13-epic-7-autonomous-governance-and-supervision`, `18-catalog-packs-wizard-and-mcp-bench`, `20-process-studio-v2-finops-and-log-sink`, `21-assistant-citations-v5-audit-help-showcase`, `22-assistant-tool-loop-approval-and-reattach`): **`6 passed, 1 skipped (mobile-companion only in 13-epic-7), 0 failed` (`1.4m`)**.
  - Combined E2E total: **`14 passed, 2 intentionally mobile-only skipped, 0 failed`**. Temporary artifacts (`apps/web/test-results`, `/tmp/orcia-e2e-29-5`) cleaned and `0` leftover worktree Vite/API processes confirmed.
- **GitNexus Index & Impact Summary (`repo: "ORCIA"`)**:
  - `npx gitnexus analyze --index-only .`: indexed **`46,388` nodes, `107,681` edges, `786` clusters, `1,531` flows** in `40.3s`.
  - `gitnexus_detect_changes(repo="ORCIA", scope="all", worktree="...")`: **`changed_files: 38, changed_count: 17, affected_count: 0, risk_level: "low"`** (`affected_processes: []`).

### 3.3 AD-17 Test Pyramid & Vertical Wiring Verification
- **Layer 1a & 1b (`pytest` + `Vitest`)**: Verified `3/3` English-dev/i18n backend audit tests, `37/37` `@orcia/ui` test files (`147` tests), and `88/88` `@orcia/web` test files (`325` tests) including i18n parity/AST gates, `zero-dead-buttons-and-silent-catches-audit.test.tsx`, `e2e-testids-sync-audit.test.ts`, and `design-system-look-and-feel-isolation.test.tsx`.
- **Layer 2 (`HTTP ➔ PostgreSQL 18`)**: Exercised end-to-end through the real `create_app()` Composition Root without fixture seeding across both Playwright E2E batches (`14 passed, 0 failed`).
- **Layer 3 (`OpenAPI 3.1`, `lint-imports`, `lint_spine.py`)**: Verified `0-diff` OpenAPI schema, `5/5` `AD-19`/`AD-20` import contracts, and `0` architecture spine findings.
- **Layer 4 & Security (`tests/security`, `tests/contract`, `tests/evals`)**: Verified **`181 passed`** (`exit 0`).
- **Layer 5 (Playwright Desktop E2E, `env -u ORCIA_E2E_SEED_FIXTURES`)**: Verified all `10` impacted specs across Batch 1 and Batch 2 (`14 passed, 2 mobile-only skipped, 0 failed`). Updated `docs/implementation-artifacts/sprint-status.yaml` (`29-5-header-layout-convergence-assistant-processes-agents-and-finops: done`) and `docs/product/capabilities.yaml` (`CAP-070`, `CAP-071`, `CAP-073`, `CAP-082`, `CAP-090`, `CAP-091`, `CAP-140`, `CAP-200`, `CAP-201`).
