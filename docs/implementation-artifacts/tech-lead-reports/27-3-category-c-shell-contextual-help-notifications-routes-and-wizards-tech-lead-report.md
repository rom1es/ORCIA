# Story 27.3 — Category C Remediation (Part 1): `apps/web` Shell, Contextual Help, Notifications, Routes & Bootstrap Wizards

- **Date**: 2026-11-23
- **Story / Sprint Key**: `27.3` (`Epic 27` — Lot 2 Part 1: Category C Core Web)
- **Capability(ies)**: `CAP-004`, `CAP-058`, `CAP-060`, `CAP-065`, `CAP-066`, `CAP-068`, `CAP-100` — classification: `hygiene` (see `AGENTS.md` §5)
- **Author / Context**: Coding Sub-Agent (`Amelia`) implementing Story 27.3 under `ACTION_ITEM-I18N.1`, Bilingual Application Policy (`fr` / `en`), and UX Rule 3.1 (zero internal plumbing jargon in user-facing UI copy).
- **Associated Commits**: Pending commit on branch `feat/epic-27-bilingual-i18n-and-deterministic-locale-guards`.

---

## 1. Needs Analysis & Tech Lead Impact Study (Pre-Implementation)

### 1.1 Context & Problem Statement
- **Problem**: While Story 27.1 installed Gates 1–4 (`i18n-hardcoded-locale-ast-audit.test.ts`, `i18n-dictionary-parity-and-jargon-audit.test.ts`, `client-error-code-contract-audit.test.ts`, and `test_i18n_backend_catalog_and_english_dev_audit.py`) and Story 27.2 locked Gate 3 (`clientErrorBaseline`) to `0`, `186` Gate 1 AST violations across `33` files remain inside the Story 27.3 scopes (`apps/web/src/components/`, `apps/web/src/routes/`, `apps/web/src/features/bootstrap/`, `apps/web/src/lib/formatters.ts`, and `apps/web/src/stores/settingsRbacResolver.ts`), alongside non-AST hardcoded French strings and `"fr"` locale literals in `platformSetupGovernanceActions.ts`, `useOrgUnitsBlockActions.ts`, `useSecopsGrantsHandlers.ts`, `settingsPacksPresets.ts`, `WizardsStepForm.tsx`, and `_contextualHelpSections*.ts`.
- **Expected vs Current**:
  - Currently, contextual help sections (`_contextualHelpSections.ts` + `_contextualHelpSectionsEn.ts` + `contextualHelpCatalog.ts`), shell notifications (`shellNotificationBuilder.ts`), breadcrumbs (`shellBreadcrumbBuilders.ts`, `shellBreadcrumbAndScope.ts`), scope options (`shellScopeOptions.ts`, `shellUnifiedScope.ts`), shell modals/views (`CreateProcessFormDialog.tsx`, `FirstBootAdminSetupModal.tsx`, `LoginScreenView.tsx`, `ModuleWorkspaceView.tsx`, `OrciaRootErrorBoundary.tsx`, `ShellAuthFallbackView.tsx`, `ShellContainer.tsx`, `SimplifiedProcessBuilderSection.tsx`, `TemporaryPasswordWarningBanner.tsx`, `platformSetupAccostage.ts`, `shellZone4HelpWiring.tsx`, `useSidebarAccountSettings.ts`), route views/formatters (`SettingsAiModelsQuickForm.tsx`, `SettingsAiModelsSection.tsx`, `SettingsIamOrganizationSection.tsx`, `SettingsOrganizationUnitRow.tsx`, `SettingsOrganizationUnitsBlock.tsx`, `SettingsPacksSection.tsx`, `settingsPacksPresets.ts`, `activity.tsx`, `activityFormatters.ts`, `organization.tsx`, `settings.tsx`, `useOrgUnitsBlockActions.ts`, `useSecopsGrantsHandlers.ts`), bootstrap wizards (`WizardsStepForm.tsx`), and shared helpers (`formatters.ts`, `settingsRbacResolver.ts`) branch inline on `isFr` / `locale === "fr"` / `locale === "en"` or embed raw French/English JSX text.
  - Expected behavior: 100% of user-facing strings, notifications, contextual help sections/fallbacks, activity event labels, wizard steps, and route/shell labels resolve from typed modular `fr`/`en` sub-dictionaries under `apps/web/src/i18n/locales/` (`<= 300` lines each), with **0** Gate 1 AST violations across `apps/web/src/components/`, `apps/web/src/routes/`, `apps/web/src/features/bootstrap/`, `apps/web/src/lib/`, and `apps/web/src/stores/`, **0** Gate 2 parity/jargon violations, and every touched file strictly `<= 300` lines.
- **Constraints from `ARCHITECTURE-SPINE.md` & `AGENTS.md`**:
  - Preserve all `data-testid` attributes (`e2e-testids-sync-audit.test.ts`) and interactive callbacks (`zero-dead-buttons-and-silent-catches-audit.test.tsx`).
  - Keep `_contextualHelpSections.ts` and `_contextualHelpSectionsEn.ts` compatible with existing test/audit contracts (`anti-jargon-and-secrets-ui-audit.test.ts`, `direction-c-shell-mobile-companion-and-dynamic-help.test.tsx`, `story-23-3-zone4-route-fidelity-and-no-unauth-resolve.test.tsx`) while moving all narrative/copy to `apps/web/src/i18n/locales/`.
  - Keep every modified or created file `<= 300` lines (`wc -l`) with English-only comments/docstrings and zero UX Rule 3.1 internal plumbing jargon (`DBOS`, `PG18`, `Outbox`, `Passthrough`, `RFC 9457`, etc.) in dictionary leaf values.

### 1.2 Exploration, GitNexus Impact Analysis, Refactoring & Technical Debt
- **GitNexus Impact Analysis (`gitnexus_query`, `gitnexus_context`, `gitnexus_impact` scoped to `/home/romain/Documents/Projects/ORCIA`)**:
  - `gitnexus_impact` on `getContextualHelpSectionsForRoute` (`apps/web/src/components/_contextualHelpSections.ts`), `buildShellNotificationItems` (`apps/web/src/components/shellNotificationBuilder.ts`), and `buildActivityScopeOptions` (`apps/web/src/routes/activityFormatters.ts`) returned `risk: UNKNOWN` (TypeScript index behind by 3 commits / function symbols unresolved). `gitnexus_cypher` confirmed `SECTIONS_BY_ROUTE_FR/EN`, `CONFIGURATION_SECTIONS_FR/EN`, `WORKFLOW_SECTIONS_FR/EN`, `EVENT_TYPE_FR/EN_LABELS`, `ScopeSourceOrgUnit`, and `ScopeSourceWorkspace` definitions in the graph.
  - Repo-wide grep verification of direct upstream callers:
    - `getContextualHelpSectionsForRoute`: called by `apps/web/src/components/contextualHelpCatalog.ts` and `apps/web/src/components/ShellContextualHelpColumn.tsx` (plus `story-23-3` / `direction-c` / `anti-jargon` tests). Keeping the exported function signatures while sourcing content from `DICTIONARIES[locale].contextualHelp` preserves all callers cleanly.
    - `buildShellNotificationItems`: called by `apps/web/src/components/shellBreadcrumbAndScope.ts` and re-exported by `apps/web/src/components/shellScopeOptions.ts`.
    - `EVENT_TYPE_FR_LABELS` / `EVENT_TYPE_EN_LABELS` / `formatActivityTimestamp` / `buildActivityScopeOptions`: called by `apps/web/src/routes/activity.tsx`.
- **Exploration & Key Metrics**:
  - Exact Gate 1 AST baseline audit across the 5 Story 27.3 scopes: **`186` violations across `33` files**:
    - `apps/web/src/components/` (`20` files, `125` violations): `CreateProcessFormDialog.tsx` (`23`), `CreateProcessFormDialogHelpers.ts` (`3`), `FirstBootAdminSetupModal.tsx` (`3`), `LoginScreenView.tsx` (`1`), `ModuleWorkspaceView.tsx` (`3`), `OrciaRootErrorBoundary.tsx` (`2`), `ShellAuthFallbackView.tsx` (`2`), `ShellContainer.tsx` (`1`), `SimplifiedProcessBuilderSection.tsx` (`11`), `TemporaryPasswordWarningBanner.tsx` (`2`), `_contextualHelpSections.ts` (`1`), `contextualHelpCatalog.ts` (`7`), `platformSetupAccostage.ts` (`6`), `shellBreadcrumbAndScope.ts` (`1`), `shellBreadcrumbBuilders.ts` (`10`), `shellNotificationBuilder.ts` (`37`), `shellScopeOptions.ts` (`3`), `shellUnifiedScope.ts` (`1`), `shellZone4HelpWiring.tsx` (`4`), `useSidebarAccountSettings.ts` (`4`).
    - `apps/web/src/routes/` (`10` files, `49` violations): `SettingsAiModelsQuickForm.tsx` (`16`), `SettingsAiModelsSection.tsx` (`1`), `SettingsIamOrganizationSection.tsx` (`1`), `SettingsOrganizationUnitRow.tsx` (`1`), `SettingsOrganizationUnitsBlock.tsx` (`2`), `SettingsPacksSection.tsx` (`18`), `activity.tsx` (`5`), `activityFormatters.ts` (`1`), `organization.tsx` (`1`), `settings.tsx` (`3`).
    - `apps/web/src/features/bootstrap/` (`1` file, `9` violations): `WizardsStepForm.tsx` (`9`).
    - `apps/web/src/lib/` (`1` file, `2` violations): `formatters.ts` (`2`).
    - `apps/web/src/stores/` (`1` file, `1` violation): `settingsRbacResolver.ts` (`1`).
  - Line-count audit identified `8` oversized files (`> 300` lines) in target scopes requiring modular splits upon modification:
    1. `apps/web/src/components/platformSetupGovernanceActions.ts` (`502` L)
    2. `apps/web/src/routes/SettingsAiModelsQuickForm.tsx` (`354` L)
    3. `apps/web/src/components/CreateProcessFormDialog.tsx` (`348` L)
    4. `apps/web/src/routes/SettingsPacksSection.tsx` (`344` L)
    5. `apps/web/src/routes/SettingsIamOrganizationSection.tsx` (`339` L)
    6. `apps/web/src/routes/useOrgUnitsBlockActions.ts` (`328` L)
    7. `apps/web/src/components/LoginScreenView.tsx` (`311` L)
    8. `apps/web/src/components/platformSetupStorageHelpers.ts` (`303` L, if modified)
- **Refactoring Opportunities & Emerging Technical Debt Mitigation**:
  - Extract modular typed sub-dictionaries (`<= 300` L each) under `apps/web/src/i18n/locales/` for contextual help (`contextual_help_labels*.ts`), shell chrome & notifications (`shell_chrome_labels*.ts`, `shell_notifications_labels*.ts`), and routes & wizards (`routes_and_wizards_labels*.ts`, `activity_event_labels*.ts`).
  - Replace repeated `locale === "fr"` / `isFr ? ... : ...` checks in pure helpers (`formatters.ts`, `settingsRbacResolver.ts`, `useSidebarAccountSettings.ts`, `shellBreadcrumbAndScope.ts`, `shellZone4HelpWiring.tsx`, `platformSetupGovernanceActions.ts`) with table-driven `Record<SupportedWebLocale, ...>` lookups and `DICTIONARIES[locale]`.
  - Split oversized UI components and action builders into focused modules `<= 300` lines (`SettingsAiModelsQuickFormFields.tsx`, `CreateProcessFormFields.tsx`, `SettingsPacksCatalogCard.tsx`, `platformSetupOrgActions.ts` / `platformSetupAiAndAuditActions.ts`, etc.).

---

## 2. Implementation Plan

### 2.1 Data Schema & Alembic Migrations
- Not applicable (no database schema or Alembic migration changes).

### 2.2 Hexagonal Core, Orchestration & Workers
- Not applicable (Python domain/worker layers are out of scope for Story 27.3).

### 2.3 Backend API, Security & Contracts
- Not applicable (no FastAPI or OpenAPI contract changes; backend `Accept-Language` error catalog remediation is scoped to Story 27.7).

### 2.4 User Interface & Experience (`apps/web/src/i18n/`, `components/`, `routes/`, `features/bootstrap/`, `lib/`, `stores/`)
- **Modular Typed Sub-Dictionaries (`apps/web/src/i18n/locales/`, `types.ts`, `fr.ts`, `en.ts`)**:
  - `contextual_help_sections_{fr,en}.ts` & `contextual_help_catalog_{fr,en}.ts` + `contextual_help_labels.ts` (`<= 300` L each): unify `_contextualHelpSections.ts`, `_contextualHelpSectionsEn.ts`, and `contextualHelpCatalog.ts` narratives, settings help, and default step-by-step items into `TranslationDictionary["contextualHelp"]`.
  - `shell_notifications_labels{,_fr,_en}.ts` & `shell_chrome_labels{,_fr,_en}.ts` (`<= 300` L each): hold all strings for `shellNotificationBuilder.ts`, `shellBreadcrumbBuilders.ts`, `shellScopeOptions.ts`, `shellUnifiedScope.ts`, `platformSetupAccostage.ts`, `CreateProcessFormDialog*.ts*`, `FirstBootAdminSetupModal.tsx`, `LoginScreenView.tsx`, `ModuleWorkspaceView.tsx`, `OrciaRootErrorBoundary.tsx`, `ShellAuthFallbackView.tsx`, `SimplifiedProcessBuilderSection.tsx`, `TemporaryPasswordWarningBanner.tsx`, `platformSetupGovernanceActions.ts`, and `platformSetupAuditHelpers.ts`.
  - `routes_and_wizards_labels{,_fr,_en}.ts` & `activity_event_labels{,_fr,_en}.ts` (`<= 300` L each): hold all strings for `activityFormatters.ts` (`eventTypeLabels` + scope builder labels), `activity.tsx`, `settings.tsx`, `SettingsAiModelsQuickForm.tsx`, `SettingsPacksSection.tsx`, `settingsPacksPresets.ts`, `SettingsOrganizationUnitsBlock.tsx`, `SettingsOrganizationUnitRow.tsx`, `SettingsIamOrganizationSection.tsx`, `useOrgUnitsBlockActions.ts`, `useSecopsGrantsHandlers.ts`, and `WizardsStepForm.tsx`.
- **Component, Route, Wizard, Helper & Store Remediation**:
  - Refactor all `33` Gate 1 files across `components/`, `routes/`, `features/bootstrap/`, `lib/`, and `stores/` plus non-AST hardcoded French modules (`platformSetupGovernanceActions.ts`, `platformSetupAuditHelpers.ts`, `useOrgUnitsBlockActions.ts`, `useSecopsGrantsHandlers.ts`, `settingsPacksPresets.ts`, `_contextualHelpSectionsEn.ts`) to consume `useI18n()` / `DICTIONARIES[locale]` / `Record<SupportedWebLocale, ...>` with zero inline `isFr` / `locale === "fr"` conditionals or hardcoded JSX text.
  - Keep `_contextualHelpSections.ts` and `_contextualHelpSectionsEn.ts` as thin dictionary-backed wrappers (`0` hardcoded prose, `0` AST violations) so existing static and integration tests remain satisfied.
  - Split all `> 300` line touched files cleanly so every modified and created file is `<= 300` lines.
- **Gate 1 Baseline Ratchet (`apps/web/src/__tests__/i18n-hardcoded-locale-baseline.json`)**:
  - Remove all `33` files under `apps/web/src/components/`, `apps/web/src/routes/`, `apps/web/src/features/bootstrap/`, `apps/web/src/lib/`, and `apps/web/src/stores/` (`186` violations removed, `totalAstViolations` reduced from `1129` to `943`).

### 2.5 Test Pyramid Impact Analysis (`AD-17` — Layers 1 to 5 + Security)
- **Layer 1a & 1b (Unit / Component Audit Tests)**:
  - `apps/web/src/__tests__/i18n-hardcoded-locale-ast-audit.test.ts` (Gate 1 strict ratchet verification: `0` violations in target scopes).
  - `apps/web/src/__tests__/i18n-dictionary-parity-and-jargon-audit.test.ts` (Gate 2: 100% `fr`/`en` key & placeholder parity + `0` UX Rule 3.1 jargon).
  - `apps/web/src/__tests__/client-error-code-contract-audit.test.ts` (Gate 3 remains `0`).
  - `apps/web/src/__tests__/i18n-and-shell.test.tsx`, `e2e-testids-sync-audit.test.ts`, `zero-dead-buttons-and-silent-catches-audit.test.tsx`, `anti-jargon-and-secrets-ui-audit.test.ts`, `direction-c-shell-mobile-companion-and-dynamic-help.test.tsx`, `story-23-3-*`, `story-24-5-*`, `story-25-2-*`, `declarative-packs-and-durable-wizards-f5.test.tsx`.
  - `.venv/bin/pytest tests/unit/test_i18n_backend_catalog_and_english_dev_audit.py --no-cov -q` (Gate 4 + English-only comments/docstrings).
- **Layers 2–5**: Deferred to Testing Sub-Agent full verification (`pnpm turbo run lint typecheck test`, Playwright Desktop E2E, `pnpm site:sync && pnpm site:check`) after Coding Sub-Agent completes local `< 60s` sanity checks.

---

## 3. Summary of Changes & Results (Post-Implementation)

### 3.1 Created & Modified Files (`66` `.ts`/`.tsx` files: `45` modified, `21` created + `1` `.json` baseline)
| File | Action | Lines (`wc -l`) | Concise Summary |
| :--- | :--- | :--- | :--- |
| `apps/web/src/i18n/locales/contextual_help_labels.ts` | Created | `27` L | Typed `ContextualHelpLabels` interface and FR/EN dictionary barrel. |
| `apps/web/src/i18n/locales/contextual_help_catalog_fr.ts` | Created | `99` L | French contextual help route fallbacks, settings descriptions, and default step-by-step items. |
| `apps/web/src/i18n/locales/contextual_help_catalog_en.ts` | Created | `99` L | English contextual help route fallbacks, settings descriptions, and default step-by-step items (`1:1` parity). |
| `apps/web/src/i18n/locales/contextual_help_sections_fr.ts` | Created | `245` L | French contextual help sections per route (`SECTIONS_BY_ROUTE`, configuration, workflow). |
| `apps/web/src/i18n/locales/contextual_help_sections_en.ts` | Created | `245` L | English contextual help sections per route (`1:1` parity). |
| `apps/web/src/i18n/locales/shell_chrome_labels.ts` | Created | `91` L | Typed `ShellChromeLabels` interface for shell chrome, modals, breadcrumbs, and accostage. |
| `apps/web/src/i18n/locales/shell_chrome_labels_fr.ts` | Created | `97` L | French shell chrome, auth fallback, error boundary, login, and process dialog labels. |
| `apps/web/src/i18n/locales/shell_chrome_labels_en.ts` | Created | `95` L | English shell chrome labels (`1:1` parity). |
| `apps/web/src/i18n/locales/shell_notifications_labels.ts` | Created | `87` L | Typed `ShellNotificationsLabels` interface for notifications, scope options, and account labels. |
| `apps/web/src/i18n/locales/shell_notifications_labels_fr.ts` | Created | `95` L | French notification builder, scope switcher, and platform audit labels. |
| `apps/web/src/i18n/locales/shell_notifications_labels_en.ts` | Created | `95` L | English notification builder, scope switcher, and platform audit labels (`1:1` parity). |
| `apps/web/src/i18n/locales/routes_and_wizards_labels.ts` | Created | `70` L | Typed `RoutesAndWizardsLabels` interface for `/settings`, `/activity`, `/organization`, and `/wizards`. |
| `apps/web/src/i18n/locales/routes_and_wizards_labels_fr.ts` | Created | `127` L | French route, AI model form, pack catalog, org-unit, activity event, and wizard labels. |
| `apps/web/src/i18n/locales/routes_and_wizards_labels_en.ts` | Created | `127` L | English route, AI model form, pack catalog, org-unit, activity event, and wizard labels (`1:1` parity). |
| `apps/web/src/i18n/locales/fr.ts` | Modified | `63` L | Wired `contextualHelp`, `shellChrome`, `shellNotifications`, and `routesAndWizards` into `frDictionary`. |
| `apps/web/src/i18n/locales/en.ts` | Modified | `63` L | Wired `contextualHelp`, `shellChrome`, `shellNotifications`, and `routesAndWizards` into `enDictionary`. |
| `apps/web/src/i18n/locales/shell_scope_labels.ts` | Modified | `81` L | Extended `ShellScopeLabels` with localized RBAC/scope labels. |
| `apps/web/src/i18n/types.ts` | Modified | `112` L | Extended `TranslationDictionary` with `contextualHelp`, `shellChrome`, `shellNotifications`, and `routesAndWizards`. |
| `apps/web/src/i18n/index.tsx` | Modified | `100` L | Exposed localized dictionary accessors for shell/help/route modules. |
| `apps/web/src/components/_contextualHelpSections.ts` | Modified | `52` L | Replaced hardcoded FR/EN prose with `DICTIONARIES[locale].contextualHelp` lookups while preserving exports. |
| `apps/web/src/components/_contextualHelpSectionsEn.ts` | Modified | `4` L | Reduced to thin re-export of `DICTIONARIES.en.contextualHelp` sections. |
| `apps/web/src/components/contextualHelpCatalog.ts` | Modified | `75` L | Migrated help fallbacks, settings items, and step-by-step sections to `DICTIONARIES[locale].contextualHelp`. |
| `apps/web/src/components/CreateProcessFormFields.tsx` | Created | `220` L | Split form fields out of `CreateProcessFormDialog.tsx` (`<= 300` L) with `useI18n()`. |
| `apps/web/src/components/CreateProcessFormDialog.tsx` | Modified | `137` L | Split under `300` L and migrated dialog copy to `shellChrome`. |
| `apps/web/src/components/CreateProcessFormDialogHelpers.ts` | Modified | `70` L | Replaced inline `isFr` strings with `DICTIONARIES[locale].shellChrome`. |
| `apps/web/src/components/FirstBootAdminSetupModal.tsx` | Modified | `277` L | Migrated Day-0 admin setup modal copy to `shellChrome`. |
| `apps/web/src/components/LoginScreenView.tsx` | Modified | `291` L | Split/refactored under `300` L and migrated login view strings to `shellChrome`. |
| `apps/web/src/components/ModuleWorkspaceView.tsx` | Modified | `106` L | Migrated module workspace labels to `shellChrome`. |
| `apps/web/src/components/OrciaRootErrorBoundary.tsx` | Modified | `73` L | Migrated root error boundary UI strings to `shellChrome`. |
| `apps/web/src/components/ShellAuthFallbackView.tsx` | Modified | `94` L | Migrated auth fallback screen labels to `shellChrome`. |
| `apps/web/src/components/ShellContainer.tsx` | Modified | `285` L | Migrated remaining shell container strings to `shellChrome` / `shellNotifications`. |
| `apps/web/src/components/SimplifiedProcessBuilderSection.tsx` | Modified | `158` L | Migrated simplified process builder strings to `shellChrome`. |
| `apps/web/src/components/TemporaryPasswordWarningBanner.tsx` | Modified | `33` L | Migrated temporary password banner copy to `shellChrome`. |
| `apps/web/src/components/platformSetupAccostage.ts` | Modified | `230` L | Migrated Day-0 accostage step labels to `DICTIONARIES[locale].shellChrome`. |
| `apps/web/src/components/platformSetupAuditHelpers.ts` | Modified | `85` L | Migrated audit helper descriptions to `DICTIONARIES[locale].shellNotifications`. |
| `apps/web/src/components/platformSetupCatalogAndRunActions.ts` | Created | `202` L | Split catalog and run actions out of `platformSetupGovernanceActions.ts` (`<= 300` L). |
| `apps/web/src/components/platformSetupOrgAndRbacActions.ts` | Created | `238` L | Split org and RBAC actions out of `platformSetupGovernanceActions.ts` (`<= 300` L). |
| `apps/web/src/components/platformSetupGovernanceActions.ts` | Modified | `241` L | Split under `300` L and migrated governance action labels to dictionaries. |
| `apps/web/src/components/platformSetupStore.tsx` | Modified | `292` L | Wired dictionary-backed setup store helpers under `300` L. |
| `apps/web/src/components/shellBreadcrumbAndScope.ts` | Modified | `216` L | Migrated breadcrumb and scope orchestration strings to `shellChrome` / `shellNotifications`. |
| `apps/web/src/components/shellBreadcrumbBuilders.ts` | Modified | `183` L | Migrated breadcrumb builders to `DICTIONARIES[locale].shellChrome`. |
| `apps/web/src/components/shellNotificationBuilder.ts` | Modified | `210` L | Migrated all notification copy and templates (`37` AST hits) to `DICTIONARIES[locale].shellNotifications`. |
| `apps/web/src/components/shellScopeOptions.ts` | Modified | `235` L | Migrated scope selector option labels to `DICTIONARIES[locale].shellNotifications`. |
| `apps/web/src/components/shellUnifiedScope.ts` | Modified | `121` L | Migrated unified scope label resolution to `DICTIONARIES[locale].shellNotifications`. |
| `apps/web/src/components/shellZone4HelpWiring.tsx` | Modified | `103` L | Migrated Zone 4 help wiring copy to `contextualHelp` / `shellChrome`. |
| `apps/web/src/components/sidebarAccountMappers.ts` | Modified | `115` L | Migrated sidebar account mapping labels to `DICTIONARIES[locale].shellNotifications`. |
| `apps/web/src/components/useSidebarAccountSettings.ts` | Modified | `298` L | Migrated sidebar account settings hook strings to `shellNotifications` (`<= 300` L). |
| `apps/web/src/features/bootstrap/WizardsStepForm.tsx` | Modified | `186` L | Migrated bootstrap wizard step form strings (`9` AST hits) to `routesAndWizards`. |
| `apps/web/src/lib/formatters.ts` | Modified | `70` L | Replaced inline `locale === "fr"` conditionals with `Record<SupportedWebLocale, ...>` lookups. |
| `apps/web/src/stores/settingsRbacResolver.ts` | Modified | `174` L | Replaced inline locale branching with `DICTIONARIES[locale].shellScope`. |
| `apps/web/src/routes/SettingsAiModelsQuickFormFields.tsx` | Created | `184` L | Split quick form fields out of `SettingsAiModelsQuickForm.tsx` (`<= 300` L). |
| `apps/web/src/routes/SettingsAiModelsQuickForm.tsx` | Modified | `238` L | Split under `300` L and migrated AI model quick form copy (`16` AST hits) to `routesAndWizards`. |
| `apps/web/src/routes/SettingsAiModelsSection.tsx` | Modified | `157` L | Migrated AI models route section labels to `routesAndWizards`. |
| `apps/web/src/routes/useIamOrganizationAccountHandlers.ts` | Created | `146` L | Split IAM account handlers out of `SettingsIamOrganizationSection.tsx` (`<= 300` L). |
| `apps/web/src/routes/SettingsIamOrganizationSection.tsx` | Modified | `238` L | Split under `300` L and migrated IAM organization labels to `routesAndWizards`. |
| `apps/web/src/routes/SettingsOrganizationUnitRow.tsx` | Modified | `288` L | Migrated org-unit row labels to `routesAndWizards`. |
| `apps/web/src/routes/SettingsOrganizationUnitsBlock.tsx` | Modified | `220` L | Migrated org-unit block labels to `routesAndWizards`. |
| `apps/web/src/routes/SettingsPacksCatalogCard.tsx` | Created | `179` L | Split pack catalog card out of `SettingsPacksSection.tsx` (`<= 300` L). |
| `apps/web/src/routes/SettingsPacksSection.tsx` | Modified | `182` L | Split under `300` L and migrated packs section copy (`18` AST hits) to `routesAndWizards`. |
| `apps/web/src/routes/activity.tsx` | Modified | `183` L | Migrated `/activity` route copy (`5` AST hits) to `routesAndWizards`. |
| `apps/web/src/routes/activityFormatters.ts` | Modified | `134` L | Replaced hardcoded `EVENT_TYPE_FR/EN_LABELS` and scope text with `DICTIONARIES[locale].routesAndWizards`. |
| `apps/web/src/routes/organization.tsx` | Modified | `80` L | Migrated `/organization` route copy to `routesAndWizards`. |
| `apps/web/src/routes/settings.tsx` | Modified | `275` L | Migrated `/settings` route copy (`3` AST hits) to `routesAndWizards`. |
| `apps/web/src/routes/orgUnitsAuditHelpers.ts` | Created | `75` L | Split org-unit audit helpers out of `useOrgUnitsBlockActions.ts` (`<= 300` L). |
| `apps/web/src/routes/useOrgUnitsBlockActions.ts` | Modified | `285` L | Split under `300` L and migrated org-unit action messages to `routesAndWizards`. |
| `apps/web/src/routes/useSecopsGrantsHandlers.ts` | Modified | `96` L | Migrated SecOps grant handler strings to `routesAndWizards`. |
| `apps/web/src/__tests__/i18n-hardcoded-locale-baseline.json` | Modified | `127` L | Removed all `33` files (`186` violations) across the 5 Story 27.3 scopes (`totalAstViolations: 1129 -> 943`, `totalClientErrorViolations: 0`). |

### 3.2 Quantitative Metrics, Baseline Counts & Static Quality (Independent Testing Sub-Agent)
- **Line-Count Guard (`wc -l <= 300`)**: `66/66` modified and created `.ts`/`.tsx` files (`45` modified, `21` created; `0` `.py` files modified) are `<= 300` lines (max `298` L in `apps/web/src/components/useSidebarAccountSettings.ts`, `292` L in `platformSetupStore.tsx`, `291` L in `LoginScreenView.tsx`).
- **Deterministic Ratchet Baselines**:
  - **Gate 1 (`i18n-hardcoded-locale-ast-audit.test.ts`, `3` tests)**: Reduced `totalAstViolations` from **`1,129` -> `943`** (`-186` AST violations across `33` files), with **`0` entries** remaining in `astFiles` or `clientErrorBaseline` under `apps/web/src/components/`, `apps/web/src/routes/`, `apps/web/src/features/bootstrap/`, `apps/web/src/lib/`, and `apps/web/src/stores/`.
  - **Gate 2 (`i18n-dictionary-parity-and-jargon-audit.test.ts`, `2` tests)**: **`0` violations** across `frDictionary` and `enDictionary` (recursive key parity, `{param}` placeholder parity, non-empty leaves, UX Rule 3.1 zero-jargon).
  - **Gate 3 (`client-error-code-contract-audit.test.ts`, `4` tests)**: **`0` violations** (`totalClientErrorViolations: 0`, `clientErrorBaseline: {}`).
  - **Gate 4 (`tests/unit/test_i18n_backend_catalog_and_english_dev_audit.py --no-cov -q`, `3 passed`)**: **PASS** (`ERROR_CATALOG` parity, prompt neutrality, and English-only diff comments/docstrings verified).
- **Workspace Lint, Typecheck & Test Results (`pnpm turbo run lint typecheck test`)**: **`9/9` tasks passed** (`447` JS/TS tests across `112` test files):
  - `@orcia/api-client`: `lint`, `typecheck`, `test` PASS — `3 passed (3)` test files, **`20 passed (20)`** tests.
  - `@orcia/ui`: `lint`, `typecheck`, `test` PASS — `35 passed (35)` test files, **`139 passed (139)`** tests.
  - `@orcia/web`: `lint`, `typecheck`, `test` PASS — `74 passed (74)` test files, **`288 passed (288)`** tests (including Gate 1 `3`, Gate 2 `2`, Gate 3 `4`, `i18n-and-shell.test.tsx` `26`, `anti-jargon-and-secrets-ui-audit.test.ts`, `e2e-testids-sync-audit.test.ts`, and `zero-dead-buttons-and-silent-catches-audit.test.tsx`).
- **Documentation & Showcase Governance Gates**:
  - `.venv/bin/python scripts/check_implementation_docs.py`: verified clean.
  - `pnpm site:sync && pnpm site:check` & `.venv/bin/pytest tests/unit/test_site_catalog_sync.py --no-cov -q`: verified clean.

### 3.3 AD-17 Test Pyramid & Vertical Wiring Verification
- **Layer 1a — Python Governance Audit (`tests/unit/`)**: `test_i18n_backend_catalog_and_english_dev_audit.py` (`3 passed`) confirms `0` non-English comment/docstring regressions and preserves Gate 4 integrity.
- **Layer 1b — Frontend TS, Design System & AST Audits (`Vitest`)**: `447` tests passed across `@orcia/api-client` (`20`), `@orcia/ui` (`139`), and `@orcia/web` (`288`), validating Gate 1 (`943`, `0` in Story 27.3 scopes), Gate 2 (`0`), Gate 3 (`0`), Zone 4 contextual help route fidelity, `data-testid` E2E synchronization, and zero dead buttons.
- **Layer 2 (`tests/integration/`), Layer 3 (`OpenAPI`), Layer 4 (`tests/evals/`), Security (`tests/security/`) & Layer 5 (`Playwright`)**: No database schema, Python domain/router, or OpenAPI schema changes in Story 27.3.
