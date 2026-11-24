# Story 27.6 — Category C Remediation (Part 4): `@orcia/ui` Design System Components & Primitives via Typed Label Props (`packages/ui` Gate 1 Baseline = 0)

- **Date**: 2026-11-24
- **Story / Sprint Key**: `27.6` (`Epic 27` — Lot 3 Part 2: Category C `@orcia/ui` Design System Components & Primitives)
- **Capability(ies)**: `CAP-060`, `CAP-090`, `CAP-091`, `CAP-100`, `CAP-200`, `CAP-260` — classification: `hygiene` (see `AGENTS.md` §5)
- **Author / Context**: Coding Sub-Agent (`Amelia`) implementing Story 27.6 under `ACTION_ITEM-I18N.1`, Bilingual Application Policy (`fr` / `en`), strict `@orcia/ui` package isolation, and UX Rule 3.1 (zero internal plumbing jargon in user-facing UI copy).
- **Associated Commits**: `c182531` (`feat(story-27.6): inject typed i18n label props into @orcia/ui primitives and lock packages/ui Gate 1 baseline to zero`) on branch `feat/epic-27-bilingual-i18n-and-deterministic-locale-guards` (with post-review Architect remediation applied in Story `27.8` closure)

---

## 1. Needs Analysis & Tech Lead Impact Study (Pre-Implementation)

### 1.1 Context & Problem Statement
- **Problem**: Following Story 27.5 (`apps/web/src/` Gate 1 baseline reduced to `0` files), **`421` Gate 1 AST violations across `55` files** remain in `packages/ui/src/`:
  - `packages/ui/src/primitives/OrciaProductShowcaseSiteView.tsx` (`139` AST hits, `1,682` lines)
  - `packages/ui/src/components/` (`14` files, `122` AST hits: Agent & Skill Studio components, `FormattedMarkdownContent.tsx`, `RgaaModalGuardLabels.ts`, `WorkspaceAssistantPinnedCard.tsx`, plus non-AST French maps/helpers in `AgentGovernanceTypesAndDefaults.ts`)
  - `packages/ui/src/primitives/` (`36` files, `149` AST hits: Assistant primitives, `TemporaryPasswordInvitationModal.tsx`, `TopHeaderSearchCommand.tsx`, `WorkspaceControlCenter.tsx`, `ContextualHelp*`, `BiModeLoginView.tsx`, `UserProfileOverviewPage.tsx`, `UserRoleDisplayLabels.ts`, `UserSettings*`, `CockpitDecisionsCard.tsx`, `CollapsibleAppRail.tsx`, `DnaStarlarkCompilerAndGlossaryLifecycleView.tsx`, `FourZoneTopHeaderSection.tsx`, `HelpArticleGeneratorAndValidatorView.tsx`, `OrciaModelCombobox.tsx`, `PackBuilderProcessesStudioView.tsx`, `ProductLifecycleCard.tsx`, `TopHeaderBar.tsx`, `finops/FinopsRemoteMcpServicesTab.tsx`, plus non-AST French fallbacks in `RemoteServiceTestBenchAndMcpExposureView.tsx`)
  - `packages/ui/src/shell/` (`4` files, `11` AST hits: `AppShellTopbar.tsx`, `OntologyAndKbExplorerPanel.tsx`, `OntologyTripartiteAndStaleSection.tsx`, `WorkflowStudioSection.tsx`, `WorkspaceTopologyPanel.tsx`)
- **Expected vs Current**:
  - Currently, these `@orcia/ui` components and primitives hardcode French JSX strings, `title`/`aria-label`/`placeholder` attributes, `DEFAULT_*` French label constants, or `locale === "fr"` / `isFr` / `isEn` ternaries directly inside `packages/ui/src/`.
  - Expected behavior: 100% of user-facing strings, placeholders, aria-labels, titles, empty states, and showcase copy in `packages/ui/src/` come from typed label props passed by `apps/web` from modular `apps/web/src/i18n/locales/` dictionaries (`fr` and `en`) — or typed fixture labels in `packages/ui/src/__tests__/`, with zero hardcoded FR/EN strings or `locale` ternaries inside `packages/ui/src/`.
- **Constraints from `ARCHITECTURE-SPINE.md` & `AGENTS.md`**:
  - `packages/ui` must never import `apps/web`, `@tanstack/react-router`, `next/*`, or `@orcia/api-client`, and must never introduce raw hex colors outside `packages/ui/src/styles/tokens.css`.
  - Every created or modified file must remain `<= 300` lines (`wc -l`) with English-only comments/docstrings.
  - Preserve all `data-testid` attributes (`e2e-testids-sync-audit.test.ts`), interactive callbacks (`zero-dead-buttons-and-silent-catches-audit.test.tsx`), and strict separation of `/showcase` pillars (`orcia-showcase-site.test.tsx`).
  - Keep `frDictionary` and `enDictionary` 100% compliant with Gate 2 (`i18n-dictionary-parity-and-jargon-audit.test.ts` — key/placeholder parity + zero UX Rule 3.1 jargon), while placing Showcase Space 3 (Under-the-Hood Architecture) in dedicated bilingual `apps/web/src/routes/showcaseArchitectureCatalog.ts` so technical terms required by `orcia-showcase-site.test.tsx` do not pollute `apps/web/src/i18n/locales/`.

### 1.2 Exploration, GitNexus Impact Analysis, Refactoring & Technical Debt
- **GitNexus Impact Analysis (`gitnexus_query`, `gitnexus_context`, `gitnexus_impact` scoped to `/home/romain/Documents/Projects/ORCIA`)**:
  - GitNexus index is 6 commits behind `HEAD`; symbol lookups for `OrciaProductShowcaseSiteView`, `RemoteServiceTestBenchAndMcpExposureView`, and `AgentGovernanceTypesAndDefaults` returned `not found` / `UNKNOWN`, so all upstream callers were exhaustively mapped via repo-wide `grep` across `packages/ui/src/`, `apps/web/src/`, `apps/web/e2e/`, and `tests/`.
  - Verified callers:
    - `OrciaProductShowcaseSiteView` $\rightarrow$ mounted solely by `apps/web/src/routes/showcase.tsx` (tested in `orcia-showcase-site.test.tsx`, `direction-c-shell-mobile-companion-and-dynamic-help.test.tsx`, `story-24-5-accostage-routes-navigation-and-day0.test.tsx`, `e2e/21-*`).
    - `RemoteServiceTestBenchAndMcpExposureView` $\rightarrow$ mounted by `apps/web/src/features/catalog/index.tsx` and tested in `packages/ui/src/__tests__/story-24-3-remote-test-bench-and-mcp-exposure.test.tsx` and `apps/web/src/__tests__/i18n-and-shell.test.tsx`.
    - `AgentGovernanceTypesAndDefaults` (`AGENT_STUDIO_BLOCKS`, `computeAgentReadinessChecklist`, label maps) $\rightarrow$ consumed by `AgentAndSkillCreateForms.tsx`, `AgentDetailAndSandboxModal.tsx`, `AgentSixBlocksFormSections.tsx`, `AgentSixBlocksKnowledgeToolsGuardrailsSections.tsx`, `AgentStudioCardItem.tsx`, `AgentTestBenchSection.tsx`, `packages/ui/src/index.ts`, and `apps/web/src/features/catalog/`.
    - `TemporaryPasswordInvitationModal` $\rightarrow$ consumed by `OrgUnitInlineCreateMemberModal.tsx`, `SettingsIamOrganizationSection.tsx`, `SettingsOrganizationUnitsBlock.tsx`, and `packages/ui/src/__tests__/temporary-password-modal.test.tsx`.
    - `iconRegistry.ts` reviewed: `OrciaIconName` keys and `ORCIA_ICONS` glyphs are internal icon identifiers/glyphs (zero rendered French UI text; `description` is non-rendered developer metadata).
- **Exploration & Key Metrics**:
  - Gate 1 baseline before Story 27.6: `55` files in `packages/ui/src/` totaling `421` AST violations (`0` in `apps/web/src/`).
  - Oversized `> 300` L files in `packages/ui/src/` requiring modular splits during remediation:
    1. `OrciaProductShowcaseSiteView.tsx` (`1,682` L)
    2. `ChunkValidationCard.tsx` (`485` L)
    3. `WorkspaceControlCenter.tsx` (`481` L)
    4. `AgentSixBlocksFormSections.tsx` (`442` L)
    5. `OrciaModelCombobox.tsx` (`429` L)
    6. `AssistantGovernanceModeATabs.tsx` (`357` L)
    7. `AppShellTopbar.tsx` (`349` L)
    8. `AgentStudioCardItem.tsx` (`342` L)
    9. `AgentSixBlocksKnowledgeToolsGuardrailsSections.tsx` (`340` L)
    10. `TopHeaderSearchCommand.tsx` (`338` L)
    11. `OntologyAndKbExplorerPanel.tsx` (`323` L)
    12. `BiModeLoginView.tsx` (`317` L)
    13. `FourZoneTopHeaderSection.tsx` (`317` L)
    14. `AssistantPromptPlusAndAutocomplete.tsx` (`312` L)
- **Refactoring Opportunities & Emerging Technical Debt Mitigation**:
  - Split `OrciaProductShowcaseSiteView.tsx` into `OrciaShowcaseTypes.ts`, `OrciaShowcaseMacroTab.tsx`, `OrciaShowcaseFeaturesTab.tsx`, `OrciaShowcaseArchitectureTab.tsx`, `OrciaShowcaseChangelogTab.tsx`, and a slim `OrciaProductShowcaseSiteView.tsx` orchestrator (`<= 250` L each).
  - Extract typed label interfaces for Agent/Skill Studio (`AgentAndSkillStudioLabels`), Assistant Primitives (`AssistantGovernanceModeATabsLabels`, `AssistantPromptPlusLabels`, `AssistantResponseFooterLabels`, `AssistantFoldersLabels`, etc.), Temporary Password Modal, Top Header / Search Command, Control Center, Contextual Help, and Shell Panels, injecting all FR/EN strings from modular `apps/web/src/i18n/locales/` dictionaries (`<= 300` L each).
  - Remove the `OrciaProductShowcaseSiteView.tsx` exemption in `apps/web/src/__tests__/anti-jargon-and-secrets-ui-audit.test.ts` once Showcase copy is decoupled into `apps/web`.

---

## 2. Implementation Plan

### 2.1 Data Schema & Alembic Migrations
- Not applicable (no database schema or Alembic migration changes).

### 2.2 Hexagonal Core, Orchestration & Workers
- Not applicable (Python domain/worker layers are out of scope for Story 27.6).

### 2.3 Backend API, Security & Contracts
- Not applicable (no FastAPI or OpenAPI contract changes).

### 2.4 User Interface & Experience (`packages/ui/src/`, `apps/web/src/`)
- **Typed Label Props & Modular Splits in `packages/ui/src/` (all touched files `<= 300` L, zero hardcoded FR/EN strings or `locale` ternaries)**:
  - **Showcase**: Split `OrciaProductShowcaseSiteView.tsx` into `OrciaShowcaseTypes.ts` + 4 pillar tab views + orchestrator, taking typed `labels: OrciaShowcaseLabels` (hero, tabs, macro, features + 9 screens, architecture, changelog).
  - **Agent & Skill Studio (`components/`)**: Refactor `AgentGovernanceTypesAndDefaults.ts` (parameterize `computeAgentReadinessChecklist(draft, labels)` and remove French `*_LABELS_FR` / `AGENT_STUDIO_BLOCKS` hardcoded prose or expose typed label contracts), split `AgentSixBlocksFormSections.tsx`, `AgentSixBlocksKnowledgeToolsGuardrailsSections.tsx`, and `AgentStudioCardItem.tsx`, and migrate `AgentAndSkillCreateForms.tsx`, `AgentDetailAndSandboxModal.tsx`, `AgentIdentityAndSkillsFields.tsx`, `AgentTestBenchSection.tsx`, `AgentsAndSkillsHeaderAndToolbar.tsx`, `SkillCreateFormDrawer.tsx`, `SkillDetailAndSandboxModal.tsx`, `SkillStudioCardItem.tsx`, `WorkspaceAssistantPinnedCard.tsx`, `FormattedMarkdownContent.tsx`, and `RgaaModalGuardLabels.ts` (remove `locale === "en"` conditional).
  - **Assistant Primitives (`primitives/`)**: Migrate `AssistantActiveStreamContent.tsx`, `AssistantAutocompleteDropdown.tsx`, `AssistantCitationPillsAndArtifactCard.tsx`, `AssistantFoldersAndCollaborativeThreadView.tsx`, `AssistantGovernanceModalAndStudio.tsx`, `AssistantGovernanceModeATabs.tsx` (split `<= 300` L), `AssistantGovernanceStudioModeB.tsx`, `AssistantModelAndEffortPopover.tsx`, `AssistantPromptPlusAndAutocomplete.tsx` (split `<= 300` L), `AssistantResponseFooterActionsAndCitations.tsx`, `AssistantSpeedSelectorHelpers.tsx`, `AssistantStickyFooterBadges.tsx`, and `AssistantStickyPromptFooter.tsx` to typed label props.
  - **Auth, Users, Help, Shell & Operations (`primitives/` & `shell/`)**: Migrate `RemoteServiceTestBenchAndMcpExposureView.tsx` (remove `DEFAULT_STEP_LABELS` / `DEFAULT_STATUS_LABELS` / inline fallbacks), `TemporaryPasswordInvitationModal.tsx`, `BiModeLoginView.tsx` (split `<= 300` L), `UserProfileOverviewPage.tsx`, `UserRoleDisplayLabels.ts` (remove `locale === "en"` conditional), `UserSettingsMcpTokensTab.tsx`, `UserSettingsProfileAndPassthroughTabs.tsx`, `OrciaModelCombobox.tsx` (split `<= 300` L), `ContextualHelpColumnView.tsx`, `ContextualHelpSectionsAndFooter.tsx`, `ContextualHelpSharedBlocks.tsx`, `TopHeaderBar.tsx`, `TopHeaderSearchCommand.tsx` (split `<= 300` L), `FourZoneTopHeaderSection.tsx` (split `<= 300` L), `CollapsibleAppRail.tsx`, `WorkspaceControlCenter.tsx` (split `<= 300` L), `CockpitDecisionsCard.tsx`, `ChunkValidationCard.tsx` (split `<= 300` L), `ProductLifecycleCard.tsx`, `DnaStarlarkCompilerAndGlossaryLifecycleView.tsx`, `HelpArticleGeneratorAndValidatorView.tsx`, `PackBuilderProcessesStudioView.tsx`, `finops/FinopsRemoteMcpServicesTab.tsx`, `shell/AppShellTopbar.tsx` (split `<= 300` L), `shell/OntologyAndKbExplorerPanel.tsx` (split `<= 300` L), `shell/OntologyTripartiteAndStaleSection.tsx`, `shell/WorkflowStudioSection.tsx`, and `shell/WorkspaceTopologyPanel.tsx`.
- **Modular FR/EN Dictionaries & Consumer Wiring (`apps/web/src/`)**:
  - Add modular `<= 300` L dictionary files under `apps/web/src/i18n/locales/` wired into `TranslationDictionary`, `fr.ts`, and `en.ts`, plus `apps/web/src/routes/showcaseArchitectureCatalog.ts` for Space 3 technical showcase data.
  - Update all `apps/web` consumers (`routes/showcase.tsx`, `features/catalog/`, `features/inbox/`, `features/admin/`, `features/spaces/`, `features/processes/`, `features/cockpit/`, `components/Shell*`, etc.) to pass typed `dictionary.*` labels down to `@orcia/ui`.
  - Update `packages/ui/src/__tests__/` to pass typed label fixtures (keeping every test file `<= 300` L).
- **Gate 1 Baseline Lock (`apps/web/src/__tests__/i18n-hardcoded-locale-baseline.json`)**:
  - Clear `astFiles` to `{}` and lock `totalAstViolations: 0` (alongside `totalClientErrorViolations: 0`).

### 2.5 Test Pyramid Impact Analysis (`AD-17` — Layers 1 to 5 + Security, Mandatory)
- **Layer 1a & 1b (Unit / Component Audit Tests)**:
  - `apps/web/src/__tests__/i18n-hardcoded-locale-ast-audit.test.ts` (Gate 1: `0` violations across `apps/web/src/` and `packages/ui/src/`).
  - `apps/web/src/__tests__/i18n-dictionary-parity-and-jargon-audit.test.ts` (Gate 2: `0` key/placeholder/UX Rule 3.1 jargon violations).
  - `apps/web/src/__tests__/client-error-code-contract-audit.test.ts` (Gate 3: `0` violations), `anti-jargon-and-secrets-ui-audit.test.ts`, `e2e-testids-sync-audit.test.ts`, `zero-dead-buttons-and-silent-catches-audit.test.tsx`, `orcia-showcase-site.test.tsx`, `i18n-and-shell.test.tsx`, plus impacted `packages/ui/src/__tests__/*.test.tsx`.
  - `.venv/bin/pytest tests/unit/test_i18n_backend_catalog_and_english_dev_audit.py --no-cov -q` (Gate 4 + English-only comments/docstrings).
- **Layer 2–5**: Deferred to Testing Sub-Agent for full `AD-17` suite verification (`pnpm turbo run lint typecheck test`, `pnpm site:sync && pnpm site:check`, Playwright Desktop E2E).

---

## 3. Summary of Changes & Results (Post-Implementation)

### 3.1 Inventory of Created & Modified Files (`167` code/test/config files: `121` modified, `46` created; `166` `.ts`/`.tsx` files + `1` `.json` baseline)
- **`apps/web/src/` (`50` files: `31` modified, `19` created)**:
  - **Modular Typed FR/EN Sub-Dictionaries (`apps/web/src/i18n/`)** (`33` files: `15` modified, `18` created): `types.ts`, `fr.ts`, `en.ts`, `ai_models_hub_labels{_en,}.ts`, `assistant_labels{_fr,_en,}.ts`, `assistant_stream_labels_{fr,en}.ts`, `agents_and_skills_studio_labels_{fr,en}.ts`, `core_domain_labels_{fr,en}.ts`, `feature_inbox_assistant_labels{_fr,_en,}.ts`, `finops_remote_labels.ts`, `gates_and_inbox_labels.ts`, `governance_and_packs_labels{_fr,_en,}.ts`, `inbox_and_cockpit_labels{_fr,_en,}.ts`, `profile_overview_labels.ts`, `role_display_labels.ts`, `shell_and_search_labels{_fr,_en,}.ts`, `showcase_labels{_fr,_en,}.ts`, `showcase_changelog_labels.ts`, `user_account_settings_labels_{fr,en}.ts`.
  - **Routes, Features, Stores & Tests (`17` files: `16` modified, `1` created)**: `routes/showcaseArchitectureCatalog.ts` (Space 3 technical showcase catalog), `routes/showcase.tsx`, `routes/SettingsIamOrganizationSection.tsx`, `routes/SettingsOrganizationUnitsBlock.tsx`, `features/admin/ai-models/AiModelAuthAndEndpointFields.tsx`, `features/admin/organization/OrgUnitInlineCreateMemberModal.tsx`, `features/inbox/{InboxAuxiliaryPanels,SavedConversationsAndThreadView,assistantAutocompleteHelpers,useInboxPanelController}`, `stores/settingsRbacResolver.ts`, `__tests__/anti-jargon-and-secrets-ui-audit.test.ts`, `__tests__/i18n-and-shell.test.tsx`, and `__tests__/i18n-hardcoded-locale-baseline.json`.
- **`packages/ui/src/` (`117` files: `90` modified, `27` created)**:
  - **Barrel & Components (`24` files: `18` modified, `6` created)**: `index.ts`, `AgentGovernanceReadiness.ts`, `AgentsAndSkillsSkillsPanel.tsx`, `AgentSixBlocksBlockB.tsx`, `AgentSixBlocksBlockC.tsx`, `AgentSixBlocksGuardrailsSection.tsx`, `AgentStudioCardBadgesAndPassport.tsx`, plus typed label prop refactors across `AgentAndSkillCreateForms.tsx`, `AgentDetailAndSandboxModal.tsx`, `AgentGovernanceTypesAndDefaults.ts`, `AgentIdentityAndSkillsFields.tsx`, `AgentSixBlocksFormSections.tsx`, `AgentSixBlocksKnowledgeToolsGuardrailsSections.tsx`, `AgentStudioCardItem.tsx`, `AgentTestBenchSection.tsx`, `AgentsAndSkillsHeaderAndToolbar.tsx`, `AgentsAndSkillsManagerView.tsx`, `AgentsAndSkillsTypes.ts`, `FormattedMarkdownContent.tsx`, `RgaaModalGuardLabels.ts`, `SkillCreateFormDrawer.tsx`, `SkillDetailAndSandboxModal.tsx`, `SkillStudioCardItem.tsx`, and `WorkspaceAssistantPinnedCard.tsx`.
  - **Primitives (`63` files: `47` modified, `16` created)**: Split `OrciaProductShowcaseSiteView.tsx` into `OrciaShowcaseTypes.ts`, `OrciaShowcaseMacroTab.tsx`, `OrciaShowcaseFeaturesTab.tsx`, `OrciaShowcaseArchitectureTab.tsx`, `OrciaShowcaseChangelogTab.tsx`, and `OrciaProductShowcaseSiteView.tsx`; extracted `AssistantAttachedFilesInlineBar.tsx`, `AssistantFolderNotesDrawer.tsx`, `AssistantPromptTelemetrySection.tsx`, `BiModeLoginLocalForm.tsx`, `ChunkValidationGuardModal.tsx`, `ChunkValidationItemsList.tsx`, `FourZoneTopHeaderSelectors.tsx`, `OrciaModelComboboxDropdown.tsx`, `OrciaModelComboboxTypes.ts`, `TopHeaderSearchFooterBanner.tsx`, and `WorkspaceControlCenterTabs.tsx`; migrated all remaining Category C Assistant, Auth, User Settings, Help, FinOps, Cockpit, and Control Center primitives to typed label props.
  - **Shell (`9` files: `6` modified, `3` created)**: Extracted `AppShellTopbarProfileMenu.tsx`, `ontologyAndOnboardingTypes.ts`, and `OntologyConceptCard.tsx`; migrated `AppShellTopbar.tsx`, `OntologyAndKbExplorerPanel.tsx`, `OntologyTripartiteAndStaleSection.tsx`, `WorkflowStudioSection.tsx`, `WorkspaceTopologyPanel.tsx`, and `types.ts`.
  - **Design System Tests & Label Fixtures (`21` files: `19` modified, `2` created)**: Added `agentsAndSkillsLabelsFixture.ts` and `assistantLabelsFixture.ts`; updated `userSettingsLabelsFixture.ts` and `18` component/primitive Vitest suites.

### 3.2 Quantitative Metrics, Baseline Counts & Static Quality (Independent Testing Sub-Agent)
- **Line-Count Guard (`wc -l`)**:
  - **Non-barrel production source files (`apps/web/src/`, `packages/ui/src/`)**: **`0`** files `> 300` lines (max = **`299`** L in `packages/ui/src/primitives/AssistantSpeedSelectorAndStreamView.tsx`).
  - **Barrel file**: `packages/ui/src/index.ts` = `785` L.
  - **Modified test files**: `11` pre-existing test suites `> 300` L (max = `2,304` L in `apps/web/src/__tests__/i18n-and-shell.test.tsx`).
- **Deterministic Ratchet Baselines (Gates 1–4)**:
  - **Gate 1 (`i18n-hardcoded-locale-ast-audit.test.ts`, `3` tests)**: Reduced `totalAstViolations` from **`421` -> `0`** across `apps/web/src/` and `packages/ui/src/`. *Post-review Architect remediation addendum (`2026-11-24`)*: closed Gate 1 blind spots (parameter default user-facing strings, `??`/`||` fallback literals, `switch` fallback prose, and module-level `DEFAULT_*` / `*_LABELS_FR/EN` constants) and removed all remaining FR/EN default label constants and fallbacks across all 16 `@orcia/ui` primitives/components (moving RGAA modal default labels into `apps/web/src/i18n/locales/rgaa_modal_labels.ts`, splitting `UpstreamChallengeRewindModal.tsx`, `CommandPaletteModal.tsx`, `FourZoneDirectionCShell.tsx`, `RadixDesignSystemPrimitives.tsx`, `OrciaKnownUserCombobox.tsx`, and restoring exact `CatalogExplorerPanel` testids) while keeping `packages/ui/src/` free of hardcoded FR/EN defaults (`totalAstViolations: 0`).
  - **Gate 2 (`i18n-dictionary-parity-and-jargon-audit.test.ts`, `2` tests)**: **`0` violations** across `frDictionary` and `enDictionary` (recursive key parity, `{param}` placeholder parity, non-empty leaves, UX Rule 3.1 zero-jargon).
  - **Gate 3 (`client-error-code-contract-audit.test.ts`, `4` tests)**: **`0` violations** (`totalClientErrorViolations: 0`, `clientErrorBaseline: {}`).
  - **Gate 4 (`tests/unit/test_i18n_backend_catalog_and_english_dev_audit.py --no-cov`, `3 passed`)**: **PASS** (`3 passed in 10.51s` — `ERROR_CATALOG` parity, prompt neutrality, and English-only diff comments/docstrings verified).
- **Workspace Lint, Typecheck & Test Results (`pnpm turbo run lint typecheck test`)**: **`9/9` tasks passed** (`57.598s`; **`449`** JS/TS tests across `113` test files):
  - `@orcia/api-client`: `lint`, `typecheck`, `test` PASS — `3 passed (3)` test files, **`20 passed (20)`** tests.
  - `@orcia/ui`: `lint`, `typecheck`, `test` PASS — `35 passed (35)` test files, **`139 passed (139)`** tests.
  - `@orcia/web`: `lint`, `typecheck`, `test` PASS — `75 passed (75)` test files, **`290 passed (290)`** tests (including Gate 1 `3`, Gate 2 `2`, Gate 3 `4`, `design-system-look-and-feel-isolation.test.tsx`, `i18n-and-shell.test.tsx`, `orcia-showcase-site.test.tsx`, `anti-jargon-and-secrets-ui-audit.test.ts`, `e2e-testids-sync-audit.test.ts`, and `zero-dead-buttons-and-silent-catches-audit.test.tsx`).
- **Secret Scan (`detect-secrets-hook`)**: `.venv/bin/detect-secrets-hook --baseline .secrets.baseline` across all `170` modified/untracked files since `HEAD` exited `0` with `0` findings.
- **Documentation & Showcase Governance Gates**:
  - `.venv/bin/python scripts/check_implementation_docs.py`: verified clean.
  - `pnpm site:sync && pnpm site:check` & `.venv/bin/pytest tests/unit/test_site_catalog_sync.py --no-cov -q`: verified clean.

### 3.3 AD-17 Test Pyramid & Vertical Wiring Verification
- **Layer 1a — Python Governance Audit (`tests/unit/`)**: `test_i18n_backend_catalog_and_english_dev_audit.py` (`3 passed`) confirms `0` non-English comment/docstring regressions and preserves Gate 4 integrity.
- **Layer 1b — Frontend TS, Design System & AST Audits (`Vitest`)**: `449` tests passed across `@orcia/api-client` (`20`), `@orcia/ui` (`139`), and `@orcia/web` (`290`), validating Gate 1 (`421 -> 0` across `apps/web/src/` and `packages/ui/src/`), Gate 2 (`0`), Gate 3 (`0`), strict `@orcia/ui` isolation (`design-system-look-and-feel-isolation.test.tsx`), `data-testid` synchronization, anti-jargon/secrets UI audits, and zero dead buttons.
- **Layer 2 (`tests/integration/`), Layer 3 (`OpenAPI`), Layer 4 (`tests/evals/`), Security (`tests/security/`) & Layer 5 (`Playwright`)**: No database schema, Python domain/router, or OpenAPI schema changes in Story 27.6 (bilingual Playwright E2E verification is scheduled in Story `27.8`).
