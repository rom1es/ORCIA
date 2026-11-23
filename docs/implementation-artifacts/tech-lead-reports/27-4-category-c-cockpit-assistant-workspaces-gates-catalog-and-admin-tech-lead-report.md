# Story 27.4 — Category C Remediation (Part 2): `apps/web` Cockpit, Inbox/Assistant, Workspaces, Gates, Catalog, Admin, Settings & Shared Features

- **Date**: 2026-11-23
- **Story / Sprint Key**: `27.4` (`Epic 27` — Lot 2 Part 2: Category C Core Web Features)
- **Capability(ies)**: `CAP-001`..`CAP-091`, `CAP-180`, `CAP-190`, `CAP-200`..`CAP-260` — classification: `hygiene` (see `AGENTS.md` §5)
- **Author / Context**: Coding Sub-Agent (`Amelia`) implementing Story 27.4 under `ACTION_ITEM-I18N.1`, Bilingual Application Policy (`fr` / `en`), and UX Rule 3.1 (zero internal plumbing jargon in user-facing UI copy).
- **Associated Commits**: Pending commit on branch `feat/epic-27-bilingual-i18n-and-deterministic-locale-guards`.

---

## 1. Needs Analysis & Tech Lead Impact Study (Pre-Implementation)

### 1.1 Context & Problem Statement
- **Problem**: Following Story 27.1 (Gates 1–4 foundation), Story 27.2 (Gate 3 `clientErrorBaseline = 0`), and Story 27.3 (`apps/web` shell, contextual help, notifications, routes, and wizards at `0` Gate 1 violations; `totalAstViolations = 943`), **`316` Gate 1 AST violations across `45` files** remain inside the 8 core business feature directories of `apps/web/src/features/`: `cockpit`, `inbox`, `workspaces`, `gates`, `catalog`, `admin`, `settings`, and `shared` (all feature domains except `features/processes/`, which belongs to Story 27.5). Additionally, several sibling controllers and helper files in those 8 directories pass or branch on `isFr` / `locale === "fr"` outside JSX attributes/text.
- **Expected vs Current**:
  - Currently, components, hooks, and helpers across `cockpit`, `inbox`, `workspaces`, `gates`, `catalog`, `admin`, `settings`, and `shared` contain inline `isFr ? ... : ...` / `locale === "fr"` expressions and hardcoded French/English JSX text, labels, placeholders, aria-labels, and tooltips.
  - Expected behavior: 100% of user-facing strings, dynamic labels, formatters, badges, modals, and empty states across those 8 feature directories resolve from typed modular `fr`/`en` dictionaries under `apps/web/src/i18n/locales/` (`<= 300` lines each), with **0** Gate 1 AST violations across `apps/web/src/features/{cockpit,inbox,workspaces,gates,catalog,admin,settings,shared}/`, **0** Gate 2 parity/jargon violations, and every modified or created file strictly `<= 300` lines.
- **Constraints from `ARCHITECTURE-SPINE.md` & `AGENTS.md`**:
  - Preserve all `data-testid` attributes (`e2e-testids-sync-audit.test.ts`), interactive callbacks (`zero-dead-buttons-and-silent-catches-audit.test.tsx`), and strict feature domain isolation (`check-feature-boundaries.mjs`).
  - Keep every modified or created file `<= 300` lines (`wc -l`) with English-only comments/docstrings and zero UX Rule 3.1 internal plumbing jargon (`DBOS`, `PG18`, `Outbox`, `Passthrough`, `RFC 9457`, `What-If`, `Tie-Break`, `Rebase`, etc.) in dictionary leaf values.
  - Add `// pragma: allowlist secret` on any label key/value mentioning `"password"`, `"secret"`, `"token"`, or `"key"` if flagged by `detect-secrets`.

### 1.2 Exploration, GitNexus Impact Analysis, Refactoring & Technical Debt
- **GitNexus Impact Analysis (`gitnexus_query`, `gitnexus_context`, `gitnexus_impact` scoped to `/home/romain/Documents/Projects/ORCIA`)**:
  - `gitnexus_query` (`cockpit inbox workspaces gates catalog admin i18n feature helpers`) confirmed the `check-feature-boundaries.mjs` domain isolation structure across `FEATURE_DOMAINS` (`cockpit`, `inbox`, `workspaces`, `gates`, `catalog`, `admin`, `settings`, `shared`).
  - `gitnexus_impact` / `gitnexus_context` on `useGatesAdaptiveHumanReview`, `useServerAssistantGovernance`, `useCatalogRemoteTestBench`, `buildCockpitGovernanceProps`, `formatStepStatusLabel`, `buildIndentedOrgTree`, `WorkspaceDnaAndWaiversSection`, and `buildNonEmptyDeleteSummary` reported `risk: UNKNOWN` (GitNexus index is 4 commits behind `HEAD` and TS function-level references in `apps/web` are not emitted in the pre-Epic-27 index).
  - Repo-wide `grep` verification of direct upstream callers confirmed safe refactoring surfaces:
    - `formatStepStatusLabel` / `formatStepKeyLabel` (`cockpitGovernanceHelpers.ts`) $\rightarrow$ called by `CockpitRunsSection.tsx` and `CockpitHumanLedGovernanceSection.tsx`.
    - `useGatesAdaptiveHumanReview` $\rightarrow$ called by `GatesAdaptiveHumanReviewSection.tsx` and `GatesAdaptiveReviewHeaderCard.tsx`.
    - `useServerAssistantGovernance` $\rightarrow$ called by `useInboxPanelController.ts`.
    - `useCatalogRemoteTestBench` $\rightarrow$ called by `apps/web/src/features/catalog/index.tsx`.
    - `buildIndentedOrgTree` / `buildNonEmptyDeleteSummary` (`orgTreeHelpers.ts`) $\rightarrow$ called by `SettingsOrganizationUnitsBlock.tsx` and `ConfirmDeleteOrgUnitModal.tsx`.
- **Exploration & Key Metrics**:
  - Exact Gate 1 AST baseline audit across the 8 Story 27.4 feature scopes: **`316` violations across `45` files**:
    - `apps/web/src/features/admin/` (`6` files, `36` hits): `AiModelMappingRowCard.tsx` (`1`), `AiModelReindexPanel.tsx` (`2`), `EnterpriseConnectorsSettingsSection.tsx` (`23`), `index.tsx` (`5`), `OrgUnitInlineCreateMemberModal.tsx` (`1`), `orgTreeHelpers.ts` (`4`).
    - `apps/web/src/features/catalog/` (`2` files, `15` hits): `index.tsx` (`3`), `useCatalogRemoteTestBench.ts` (`12`).
    - `apps/web/src/features/cockpit/` (`5` files, `25` hits): `CockpitRunsSection.tsx` (`6`), `CockpitUpstreamChallengePanel.tsx` (`5`), `PlatformOnboardingChecklistCard.tsx` (`5`), `cockpitGovernanceHelpers.ts` (`8`), `index.tsx` (`1`).
    - `apps/web/src/features/gates/` (`7` files, `60` hits): `GatesAdaptiveHumanReviewSection.tsx` (`3`), `GatesAdaptiveReviewHeaderCard.tsx` (`8`), `GatesChallengeModalSection.tsx` (`7`), `OrciaDocumentationProcessCard.tsx` (`19`), `index.tsx` (`5`), `orciaDocProcessTemplates.ts` (`6`), `useGatesAdaptiveHumanReview.ts` (`12`).
    - `apps/web/src/features/inbox/` (`12` files, `56` hits): `AssistantTopToolbar.tsx` (`3`), `InboxAuxiliaryPanels.tsx` (`4`), `InboxNotificationsCenterView.tsx` (`14`), `SavedConversationsAndThreadView.tsx` (`4`), `assistantAutocompleteHelpers.ts` (`7`), `assistantStreamingRunner.ts` (`2`), `assistantTurnControlsHelper.ts` (`6`), `assistantTurnPayloadHelper.ts` (`5`), `inboxCitationHelpers.ts` (`3`), `index.tsx` (`2`), `useServerAssistantGovernance.ts` (`3`), `useServerAssistantThreads.ts` (`1`).
    - `apps/web/src/features/settings/` (`3` files, `15` hits): `PackCardItem.tsx` (`4`), `PacksRegistryPage.tsx` (`8`), `packDisplayFormatters.ts` (`3`).
    - `apps/web/src/features/shared/` (`1` file, `1` hit): `useSourceLineInspector.ts` (`1`).
    - `apps/web/src/features/workspaces/` (`9` files, `108` hits): `CreateWorkspaceCard.tsx` (`18`), `WorkspaceDetailTabsPanel.tsx` (`11`), `WorkspaceDnaAndWaiversSection.tsx` (`19`), `WorkspaceGlossaryAndOntologyTab.tsx` (`1`), `WorkspaceStudioCardsAndDetailView.tsx` (`9`), `WorkspaceStudioSummaryCard.tsx` (`29`), `index.tsx` (`14`), `sources/WorkspaceSourceAttachSyncFields.tsx` (`2`), `sources/WorkspaceSourcesMasterTable.tsx` (`3`).
  - Line-count audit identified `4` oversized files (`> 300` lines) plus `5` near-limit files (`276–298` lines) requiring modular splits upon modification:
    1. `apps/web/src/features/cockpit/index.tsx` (`364` L)
    2. `apps/web/src/features/workspaces/WorkspaceGlossaryAndOntologyTab.tsx` (`340` L)
    3. `apps/web/src/features/workspaces/WorkspaceDnaAndWaiversSection.tsx` (`331` L)
    4. `apps/web/src/features/workspaces/sources/WorkspaceSourcesMasterTable.tsx` (`316` L)
    5. Near-limit files (`276–298` L): `EnterpriseConnectorsSettingsSection.tsx` (`298` L), `OrciaDocumentationProcessCard.tsx` (`295` L), `inbox/index.tsx` (`293` L), `CreateWorkspaceCard.tsx` (`288` L), `assistantTurnPayloadHelper.ts` (`276` L).
- **Refactoring Opportunities & Emerging Technical Debt Mitigation**:
  - Extract modular typed sub-dictionaries (`<= 300` L each) under `apps/web/src/i18n/locales/` organized cleanly by feature cluster (`feature_cockpit_gates_labels*`, `feature_inbox_assistant_labels*`, `feature_workspaces_labels*`, `feature_admin_catalog_settings_labels*`).
  - Reuse `formatI18nTemplate`, `resolveLocaleForFlag`, and `resolveDictionaryForFlag` (`apps/web/src/i18n/index.tsx`) and eliminate duplicate `isFr ? ... : ...` ternaries in `useCockpitGovernanceController`, `useInboxPanelController`, `assistantTurnSseProcessor`, `WorkspaceSourcesRagTab`, and `ConfirmDeleteOrgUnitModal`.
  - Split all `> 300` L (and any near-limit) files into focused sub-components/helpers (`<= 300` L each) without breaking any feature boundary or barrel export.

---

## 2. Implementation Plan

### 2.1 Data Schema & Alembic Migrations
- Not applicable (no database schema or Alembic migration changes).

### 2.2 Hexagonal Core, Orchestration & Workers
- Not applicable (Python domain/worker layers are out of scope for Story 27.4).

### 2.3 Backend API, Security & Contracts
- Not applicable (no FastAPI or OpenAPI contract changes; backend `Accept-Language` error catalog remediation is scoped to Story 27.7).

### 2.4 User Interface & Experience (`apps/web/src/i18n/`, `apps/web/src/features/`)
- **Modular Typed Sub-Dictionaries (`apps/web/src/i18n/locales/`, `types.ts`, `fr.ts`, `en.ts`)**:
  - `feature_cockpit_gates_labels{,_fr,_en}.ts` (`<= 300` L each): typed labels for `cockpit/*` and `gates/*` (including `orciaDocProcessTemplates` step/template copy, governance helpers, onboarding checklist, and adaptive human review).
  - `feature_inbox_assistant_labels{,_fr,_en}.ts` (`<= 300` L each): typed labels for `inbox/*` (notifications center, assistant toolbar, autocomplete items/speeds, streaming runner/payload helpers, citation helpers, saved conversations, and governance).
  - `feature_workspaces_labels{,_fr,_en}.ts` (`<= 300` L each): typed labels for `workspaces/*` and `shared/*` (`CreateWorkspaceCard`, studio cards/summary, detail tabs, DNA/waivers, glossary/ontology tab, sources table/attach fields, and `useSourceLineInspector`).
  - `feature_admin_catalog_settings_labels{,_fr,_en}.ts` (`<= 300` L each): typed labels for `admin/*`, `catalog/*`, and `settings/*` (`EnterpriseConnectorsSettingsSection`, `ai-models/*`, `organization/*`, `iam/*`, `catalog/index.tsx`, `useCatalogRemoteTestBench.ts`, and `settings/packs/*`).
- **Component, Hook & Helper Remediation + Modular Splits (`<= 300` L)**:
  - Migrate all `45` Gate 1 files and sibling `isFr`/`locale` helpers across the 8 feature directories to `useI18n()` / `DICTIONARIES[resolveLocaleForFlag(isFr, locale)]` / `formatI18nTemplate`.
  - Split `cockpit/index.tsx` (`364` L), `WorkspaceGlossaryAndOntologyTab.tsx` (`340` L), `WorkspaceDnaAndWaiversSection.tsx` (`331` L), `WorkspaceSourcesMasterTable.tsx` (`316` L), and any near-300-line file that grows during i18n extraction into focused `<= 300` L modules.
  - Ensure all UX Rule 3.1 forbidden terms (`What-If`, `Tie-Break`, `Rebase`, `PG18`, `DBOS`, `Outbox`, `Passthrough`, `RFC 9457`, etc.) are absent from `fr` and `en` dictionary leaf values.
- **Gate 1 Baseline Ratchet (`apps/web/src/__tests__/i18n-hardcoded-locale-baseline.json`)**:
  - Remove all `45` entries under `apps/web/src/features/{cockpit,inbox,workspaces,gates,catalog,admin,settings,shared}/` (`316` violations removed, reducing `totalAstViolations` from `943` to `627`).

### 2.5 Test Pyramid Impact Analysis (`AD-17` — Layers 1 to 5 + Security)
- **Layer 1a & 1b (Unit / Component Audit Tests)**:
  - `apps/web/src/__tests__/i18n-hardcoded-locale-ast-audit.test.ts` (Gate 1 strict ratchet verification: `0` violations across the 8 Story 27.4 feature directories).
  - `apps/web/src/__tests__/i18n-dictionary-parity-and-jargon-audit.test.ts` (Gate 2: 100% `fr`/`en` key & `{param}` placeholder parity + `0` UX Rule 3.1 jargon).
  - `apps/web/src/__tests__/client-error-code-contract-audit.test.ts` (Gate 3 remains `0`).
  - `apps/web/src/__tests__/anti-jargon-and-secrets-ui-audit.test.ts`, `e2e-testids-sync-audit.test.ts`, `zero-dead-buttons-and-silent-catches-audit.test.tsx`, plus targeted feature specs (`story-26-9-*`, `story-25-3-*`, `story-25-4-*`, `story-24-2-*`, etc.).
  - `.venv/bin/pytest tests/unit/test_i18n_backend_catalog_and_english_dev_audit.py --no-cov -q` (Gate 4 + English-only comments/docstrings).
- **Layers 2–5**: Deferred to Testing Sub-Agent full verification (`pnpm turbo run lint typecheck test`, Playwright Desktop E2E, `pnpm site:sync && pnpm site:check`, Report §3, `sprint-status.yaml`, and GitNexus refresh) after Coding Sub-Agent completes local `< 60 s` sanity checks.

---

## 3. Summary of Changes & Results (Post-Implementation)

### 3.1 Created & Modified Files (`72` `.ts`/`.tsx` files: `55` modified, `17` created + `1` `.json` baseline)
| File | Action | Lines (`wc -l`) | Concise Summary |
| :--- | :--- | :--- | :--- |
| `apps/web/src/features/cockpit/cockpitWorkflowPreview.ts` | Created | `24` L | Split workflow preview helpers out of `cockpit/index.tsx` (`<= 300` L). |
| `apps/web/src/features/cockpit/useCockpitGovernancePoll.ts` | Created | `124` L | Split governance polling hook out of `cockpit/index.tsx` (`<= 300` L). |
| `apps/web/src/features/workspaces/WorkspaceGlossaryCascadeGrid.tsx` | Created | `175` L | Split glossary cascade grid out of `WorkspaceGlossaryAndOntologyTab.tsx` (`<= 300` L). |
| `apps/web/src/features/workspaces/sources/WorkspaceSourcesMasterRow.tsx` | Created | `198` L | Split table row component out of `WorkspaceSourcesMasterTable.tsx` (`<= 300` L). |
| `apps/web/src/features/workspaces/useWorkspaceDnaAndWaivers.ts` | Created | `187` L | Split DNA & waivers controller hook out of `WorkspaceDnaAndWaiversSection.tsx` (`<= 300` L). |
| `apps/web/src/i18n/locales/feature_admin_catalog_settings_labels.ts` | Created | `89` L | Typed `FeatureAdminCatalogSettingsLabels` interface for admin, catalog, and settings features. |
| `apps/web/src/i18n/locales/feature_admin_catalog_settings_labels_fr.ts` | Created | `162` L | French admin, AI models, connectors, org tree, catalog, and packs labels. |
| `apps/web/src/i18n/locales/feature_admin_catalog_settings_labels_en.ts` | Created | `162` L | English admin, AI models, connectors, org tree, catalog, and packs labels (`1:1` parity). |
| `apps/web/src/i18n/locales/feature_cockpit_gates_labels.ts` | Created | `120` L | Typed `FeatureCockpitGatesLabels` interface for cockpit and gates features. |
| `apps/web/src/i18n/locales/feature_cockpit_gates_labels_fr.ts` | Created | `224` L | French cockpit, onboarding checklist, governance, gates, and process template labels. |
| `apps/web/src/i18n/locales/feature_cockpit_gates_labels_en.ts` | Created | `224` L | English cockpit, onboarding checklist, governance, gates, and process template labels (`1:1` parity). |
| `apps/web/src/i18n/locales/feature_inbox_assistant_labels.ts` | Created | `82` L | Typed `FeatureInboxAssistantLabels` interface for inbox and assistant features. |
| `apps/web/src/i18n/locales/feature_inbox_assistant_labels_fr.ts` | Created | `86` L | French inbox notifications, assistant toolbar, autocomplete, citations, and thread labels. |
| `apps/web/src/i18n/locales/feature_inbox_assistant_labels_en.ts` | Created | `85` L | English inbox notifications, assistant toolbar, autocomplete, citations, and thread labels (`1:1` parity). |
| `apps/web/src/i18n/locales/feature_workspaces_labels.ts` | Created | `125` L | Typed `FeatureWorkspacesLabels` interface for workspaces and shared source line inspector. |
| `apps/web/src/i18n/locales/feature_workspaces_labels_fr.ts` | Created | `132` L | French workspace creation, studio cards, DNA/waivers, glossary, sources, and line inspector labels. |
| `apps/web/src/i18n/locales/feature_workspaces_labels_en.ts` | Created | `132` L | English workspace creation, studio cards, DNA/waivers, glossary, sources, and line inspector labels (`1:1` parity). |
| `apps/web/src/i18n/types.ts` | Modified | `121` L | Extended `TranslationDictionary` with the four Story 27.4 feature label sections. |
| `apps/web/src/i18n/index.tsx` | Modified | `111` L | Exposed localized dictionary resolution for Story 27.4 feature modules. |
| `apps/web/src/i18n/locales/fr.ts` | Modified | `71` L | Wired all four Story 27.4 French sub-dictionaries into `frDictionary`. |
| `apps/web/src/i18n/locales/en.ts` | Modified | `71` L | Wired all four Story 27.4 English sub-dictionaries into `enDictionary`. |
| `apps/web/src/features/admin/ai-models/AiModelConfigModal.tsx` | Modified | `183` L | Migrated AI model configuration modal copy to `featureAdminCatalogSettings`. |
| `apps/web/src/features/admin/ai-models/AiModelMappingRowCard.tsx` | Modified | `184` L | Migrated AI model mapping row labels to `featureAdminCatalogSettings`. |
| `apps/web/src/features/admin/ai-models/AiModelReindexPanel.tsx` | Modified | `197` L | Migrated AI model reindex panel copy to `featureAdminCatalogSettings`. |
| `apps/web/src/features/admin/ai-models/AiModelsMasterTable.tsx` | Modified | `216` L | Migrated AI models master table labels to `featureAdminCatalogSettings`. |
| `apps/web/src/features/admin/connectors/EnterpriseConnectorsSettingsSection.tsx` | Modified | `283` L | Migrated enterprise connectors settings (`23` AST hits) to `featureAdminCatalogSettings` (`<= 300` L). |
| `apps/web/src/features/admin/index.tsx` | Modified | `78` L | Migrated admin feature root copy (`5` AST hits) to `featureAdminCatalogSettings`. |
| `apps/web/src/features/admin/organization/OrgUnitInlineCreateMemberModal.tsx` | Modified | `167` L | Migrated org-unit inline member modal copy to `featureAdminCatalogSettings`. |
| `apps/web/src/features/admin/organization/orgTreeHelpers.ts` | Modified | `215` L | Migrated org-tree and delete summary helpers (`4` AST hits) to `DICTIONARIES[locale]`. |
| `apps/web/src/features/catalog/index.tsx` | Modified | `246` L | Migrated catalog feature copy (`3` AST hits) to `featureAdminCatalogSettings`. |
| `apps/web/src/features/catalog/useCatalogRemoteTestBench.ts` | Modified | `211` L | Migrated remote test-bench hook strings (`12` AST hits) to `featureAdminCatalogSettings`. |
| `apps/web/src/features/cockpit/CockpitRunsSection.tsx` | Modified | `233` L | Migrated cockpit runs section (`6` AST hits) to `featureCockpitGates`. |
| `apps/web/src/features/cockpit/CockpitUpstreamChallengePanel.tsx` | Modified | `190` L | Migrated upstream challenge panel (`5` AST hits) to `featureCockpitGates`. |
| `apps/web/src/features/cockpit/PlatformOnboardingChecklistCard.tsx` | Modified | `157` L | Migrated onboarding checklist card (`5` AST hits) to `featureCockpitGates`. |
| `apps/web/src/features/cockpit/cockpitGovernanceHelpers.ts` | Modified | `233` L | Migrated governance helpers (`8` AST hits) to `DICTIONARIES[locale].featureCockpitGates`. |
| `apps/web/src/features/cockpit/index.tsx` | Modified | `252` L | Split from `364` L to `252` L and migrated cockpit view to `featureCockpitGates`. |
| `apps/web/src/features/gates/GatesAdaptiveHumanReviewSection.tsx` | Modified | `121` L | Migrated adaptive human review section (`3` AST hits) to `featureCockpitGates`. |
| `apps/web/src/features/gates/GatesAdaptiveReviewHeaderCard.tsx` | Modified | `89` L | Migrated adaptive review header card (`8` AST hits) to `featureCockpitGates`. |
| `apps/web/src/features/gates/GatesChallengeModalSection.tsx` | Modified | `115` L | Migrated gate challenge modal (`7` AST hits) to `featureCockpitGates`. |
| `apps/web/src/features/gates/OrciaDocumentationProcessCard.tsx` | Modified | `230` L | Migrated documentation process card (`19` AST hits) to `featureCockpitGates`. |
| `apps/web/src/features/gates/index.tsx` | Modified | `102` L | Migrated gates root view (`5` AST hits) to `featureCockpitGates`. |
| `apps/web/src/features/gates/orciaDocProcessTemplates.ts` | Modified | `31` L | Migrated process template labels (`6` AST hits) to `DICTIONARIES[locale].featureCockpitGates`. |
| `apps/web/src/features/gates/useGatesAdaptiveHumanReview.ts` | Modified | `210` L | Migrated adaptive review hook messages (`12` AST hits) to `featureCockpitGates`. |
| `apps/web/src/features/inbox/AssistantTopToolbar.tsx` | Modified | `84` L | Migrated assistant top toolbar (`3` AST hits) to `featureInboxAssistant`. |
| `apps/web/src/features/inbox/InboxAuxiliaryPanels.tsx` | Modified | `188` L | Migrated inbox auxiliary panels (`4` AST hits) to `featureInboxAssistant`. |
| `apps/web/src/features/inbox/InboxNotificationsCenterView.tsx` | Modified | `244` L | Migrated notifications center (`14` AST hits) to `featureInboxAssistant`. |
| `apps/web/src/features/inbox/SavedConversationsAndThreadView.tsx` | Modified | `230` L | Migrated saved conversations thread view (`4` AST hits) to `featureInboxAssistant`. |
| `apps/web/src/features/inbox/assistantAutocompleteHelpers.ts` | Modified | `214` L | Migrated autocomplete helpers (`7` AST hits) to `DICTIONARIES[locale].featureInboxAssistant`. |
| `apps/web/src/features/inbox/assistantStreamingRunner.ts` | Modified | `158` L | Migrated streaming runner strings (`2` AST hits) to `DICTIONARIES[locale].featureInboxAssistant`. |
| `apps/web/src/features/inbox/assistantTurnControlsHelper.ts` | Modified | `131` L | Migrated turn controls helper (`6` AST hits) to `DICTIONARIES[locale].featureInboxAssistant`. |
| `apps/web/src/features/inbox/assistantTurnPayloadHelper.ts` | Modified | `278` L | Migrated turn payload helper (`5` AST hits) to `DICTIONARIES[locale].featureInboxAssistant` (`<= 300` L). |
| `apps/web/src/features/inbox/assistantTurnSseProcessor.ts` | Modified | `207` L | Removed inline locale branching in SSE turn processing. |
| `apps/web/src/features/inbox/inboxCitationHelpers.ts` | Modified | `214` L | Migrated citation helpers (`3` AST hits) to `DICTIONARIES[locale].featureInboxAssistant`. |
| `apps/web/src/features/inbox/inboxTurnSyncHelpers.ts` | Modified | `108` L | Migrated turn sync helpers to `DICTIONARIES[locale].featureInboxAssistant`. |
| `apps/web/src/features/inbox/index.tsx` | Modified | `295` L | Migrated inbox feature root (`2` AST hits) to `featureInboxAssistant` (`<= 300` L). |
| `apps/web/src/features/inbox/savedConversationsStore.ts` | Modified | `205` L | Removed inline locale defaults in saved conversations store. |
| `apps/web/src/features/inbox/useInboxPanelController.ts` | Modified | `286` L | Migrated inbox panel controller strings to `featureInboxAssistant` (`<= 300` L). |
| `apps/web/src/features/inbox/useServerAssistantGovernance.ts` | Modified | `142` L | Migrated server assistant governance hook (`3` AST hits) to `featureInboxAssistant`. |
| `apps/web/src/features/inbox/useServerAssistantThreads.ts` | Modified | `217` L | Migrated server assistant threads hook (`1` AST hit) to `featureInboxAssistant`. |
| `apps/web/src/features/settings/packs/PackCardItem.tsx` | Modified | `201` L | Migrated pack card item (`4` AST hits) to `featureAdminCatalogSettings`. |
| `apps/web/src/features/settings/packs/PacksRegistryPage.tsx` | Modified | `155` L | Migrated packs registry page (`8` AST hits) to `featureAdminCatalogSettings`. |
| `apps/web/src/features/settings/packs/packDisplayFormatters.ts` | Modified | `79` L | Migrated pack display formatters (`3` AST hits) to `DICTIONARIES[locale]`. |
| `apps/web/src/features/shared/useSourceLineInspector.ts` | Modified | `203` L | Migrated shared source line inspector (`1` AST hit) to `featureWorkspaces`. |
| `apps/web/src/features/workspaces/CreateWorkspaceCard.tsx` | Modified | `248` L | Migrated workspace creation card (`18` AST hits) to `featureWorkspaces`. |
| `apps/web/src/features/workspaces/WorkspaceDetailTabsPanel.tsx` | Modified | `211` L | Migrated workspace detail tabs panel (`11` AST hits) to `featureWorkspaces`. |
| `apps/web/src/features/workspaces/WorkspaceDnaAndWaiversSection.tsx` | Modified | `164` L | Split from `331` L to `164` L and migrated DNA & waivers (`19` AST hits) to `featureWorkspaces`. |
| `apps/web/src/features/workspaces/WorkspaceGlossaryAndOntologyTab.tsx` | Modified | `296` L | Split from `340` L to `296` L and migrated glossary tab (`1` AST hit) to `featureWorkspaces`. |
| `apps/web/src/features/workspaces/WorkspaceStudioCardsAndDetailView.tsx` | Modified | `246` L | Migrated studio cards & detail view (`9` AST hits) to `featureWorkspaces`. |
| `apps/web/src/features/workspaces/WorkspaceStudioSummaryCard.tsx` | Modified | `272` L | Migrated studio summary card (`29` AST hits) to `featureWorkspaces`. |
| `apps/web/src/features/workspaces/index.tsx` | Modified | `228` L | Migrated workspaces feature root (`14` AST hits) to `featureWorkspaces`. |
| `apps/web/src/features/workspaces/sources/WorkspaceSourceAttachSyncFields.tsx` | Modified | `131` L | Migrated source attach sync fields (`2` AST hits) to `featureWorkspaces`. |
| `apps/web/src/features/workspaces/sources/WorkspaceSourcesMasterTable.tsx` | Modified | `210` L | Split from `316` L to `210` L and migrated sources master table (`3` AST hits) to `featureWorkspaces`. |
| `apps/web/src/__tests__/i18n-hardcoded-locale-baseline.json` | Modified | `82` L | Removed all `45` entries (`312` AST hits) under the 8 Story 27.4 feature directories (`totalAstViolations: 943 -> 631`, `totalClientErrorViolations: 0`). |

### 3.2 Quantitative Metrics, Baseline Counts & Static Quality (Independent Testing Sub-Agent)
- **Line-Count Guard (`wc -l <= 300`)**: `72/72` modified and created `.ts`/`.tsx` files (`55` modified, `17` created; `0` `.py` files modified) are `<= 300` lines (max `296` L in `WorkspaceGlossaryAndOntologyTab.tsx`, `295` L in `inbox/index.tsx`, `286` L in `useInboxPanelController.ts`, `283` L in `EnterpriseConnectorsSettingsSection.tsx`).
- **Deterministic Ratchet Baselines**:
  - **Gate 1 (`i18n-hardcoded-locale-ast-audit.test.ts`, `3` tests)**: Reduced `totalAstViolations` from **`943` -> `631`** (`-312` AST violations across `45` files; `74` files remaining in `astFiles` outside Story 27.4 scopes), with **`0` entries** remaining under `apps/web/src/features/{cockpit,inbox,workspaces,gates,catalog,admin,settings,shared}/`.
  - **Gate 2 (`i18n-dictionary-parity-and-jargon-audit.test.ts`, `2` tests)**: **`0` violations** across `frDictionary` and `enDictionary` (recursive key parity, `{param}` placeholder parity, non-empty leaves, UX Rule 3.1 zero-jargon).
  - **Gate 3 (`client-error-code-contract-audit.test.ts`, `4` tests)**: **`0` violations** (`totalClientErrorViolations: 0`, `clientErrorBaseline: {}`).
  - **Gate 4 (`tests/unit/test_i18n_backend_catalog_and_english_dev_audit.py --no-cov -q`, `3 passed`)**: **PASS** (`ERROR_CATALOG` parity, prompt neutrality, and English-only diff comments/docstrings verified).
- **Workspace Lint, Typecheck & Test Results (`pnpm turbo run lint typecheck test`)**: **`9/9` tasks passed** (`447` JS/TS tests across `112` test files):
  - `@orcia/api-client`: `lint`, `typecheck`, `test` PASS — `3 passed (3)` test files, **`20 passed (20)`** tests.
  - `@orcia/ui`: `lint`, `typecheck`, `test` PASS — `35 passed (35)` test files, **`139 passed (139)`** tests.
  - `@orcia/web`: `lint`, `typecheck`, `test` PASS — `74 passed (74)` test files, **`288 passed (288)`** tests (including Gate 1 `3`, Gate 2 `2`, Gate 3 `4`, `i18n-and-shell.test.tsx` `26`, `anti-jargon-and-secrets-ui-audit.test.ts` `4`, `e2e-testids-sync-audit.test.ts` `1`, and `zero-dead-buttons-and-silent-catches-audit.test.tsx` `4`).
- **Secret Scan (`detect-secrets-hook`)**: `.venv/bin/detect-secrets-hook --baseline .secrets.baseline` across all modified/untracked files exited `0` with `0` findings.
- **Documentation & Showcase Governance Gates**:
  - `.venv/bin/python scripts/check_implementation_docs.py`: verified clean.
  - `pnpm site:sync && pnpm site:check` & `.venv/bin/pytest tests/unit/test_site_catalog_sync.py --no-cov -q`: verified clean.

### 3.3 AD-17 Test Pyramid & Vertical Wiring Verification
- **Layer 1a — Python Governance Audit (`tests/unit/`)**: `test_i18n_backend_catalog_and_english_dev_audit.py` (`3 passed`) confirms `0` non-English comment/docstring regressions and preserves Gate 4 integrity.
- **Layer 1b — Frontend TS, Design System & AST Audits (`Vitest`)**: `447` tests passed across `@orcia/api-client` (`20`), `@orcia/ui` (`139`), and `@orcia/web` (`288`), validating Gate 1 (`631`, `0` across all 8 Story 27.4 feature scopes), Gate 2 (`0`), Gate 3 (`0`), `data-testid` E2E synchronization, anti-jargon/secrets UI audits, and zero dead buttons.
- **Layer 2 (`tests/integration/`), Layer 3 (`OpenAPI`), Layer 4 (`tests/evals/`), Security (`tests/security/`) & Layer 5 (`Playwright`)**: No database schema, Python domain/router, or OpenAPI schema changes in Story 27.4.
