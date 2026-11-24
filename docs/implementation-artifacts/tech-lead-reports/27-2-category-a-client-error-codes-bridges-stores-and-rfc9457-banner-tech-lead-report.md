# Story 27.2 — Category A Remediation: Migrate Client API Bridges, SSE Stores, Controllers & `formatRfc9457ErrorToBanner` to `ClientErrorCode`

- **Date**: 2026-11-23
- **Story / Sprint Key**: `27.2` (`Epic 27` — Lot 1: Category A Client Errors)
- **Capability(ies)**: `CAP-001`..`CAP-260` (cross-cutting client error localization; primary hygiene/NFR/UX enforcement) — classification: `hygiene` (see `AGENTS.md` §5)
- **Author / Context**: Coding Sub-Agent (`Amelia`) implementing Story 27.2 under `ACTION_ITEM-I18N.1`, Bilingual Application Policy (`fr` / `en`), and UX Rule 3.1 (zero internal plumbing jargon in user-facing UI text).
- **Associated Commits**: `54ca196` (`feat(story-27.2): migrate Category A client errors across 26 files to ClientErrorCode and lock Gate 3 to zero`) on branch `feat/epic-27-bilingual-i18n-and-deterministic-locale-guards`

---

## 1. Needs Analysis & Tech Lead Impact Study (Pre-Implementation)

### 1.1 Context & Problem Statement
- **Problem**: Although Story 27.1 established the shared `ClientErrorCode` foundation (`apps/web/src/lib/clientErrorCodes.ts`, `apps/web/src/i18n/locales/client_errors_labels.ts`) and automated Gate 1/2/3 audits, `177` Gate 3 client error violations across `23` files (plus additional Category A inventory hits across `packages/api-client`, `authSessionStore.ts`, `platformSetupHydration.ts`, `platformSetupStore.tsx`, `useSidebarAccountSettings.ts`, and `useAssistantStreamingTurn.ts`) still emit hardcoded French or English error strings or inline `locale === "fr" ? ... : ...` / `isFr ? ... : ...` ternaries.
- **Expected vs Current**:
  - Currently, `formatRfc9457ErrorToBanner.ts` embeds a 150-line inline `RFC9457_ACTIONABLE_CATALOG`, HTTP status fallback switch with `locale === "fr"` ternaries, French-only token sanitization replacements (`"lecture seule"`, etc.), and `" (Ressource : ...)"` formatting; bridges (`aiModelsApiBridge.ts`, `iamApiBridge.ts`, `orgUnitsApiBridge.ts`, `activityApiBridge.ts`) and controllers (`useEnterpriseConnectorsController.ts`, `useCockpitGovernanceController.ts`, `useFinopsDashboardController.ts`, `useInteractiveProcessRunController.ts`, `useStudioWorkflowController.ts`, `usePacksRegistryHealthchecks.ts`, `usePermissionBrokerTickets.ts`, `useAiModelsSectionController.ts`, `useSidebarAccountSettings.ts`, `wizards.tsx`, `WorkspaceSourcesRagTab.tsx`, `ShellFederatedSearchModal.tsx`, `ProcessStudioAndPackAuthoringSection.tsx`, `assistantBackgroundStreamStore.ts`, `useAssistantStreamingTurn.ts`, `authSessionStore.ts`, `platformSetup*`) hardcode client error prose or locale ternaries; `packages/api-client` throws English prose errors; and `packages/ui/src/primitives/UserPasswordChangeCard.tsx` carries `DEFAULT_FR_PASSWORD_LABELS` / `DEFAULT_EN_PASSWORD_LABELS` fallbacks.
  - Expected behavior: Every client timeout, network failure, SSE disconnect, validation error, and RFC 9457 status fallback resolves cleanly through `ClientErrorCode` / typed `apps/web/src/i18n/locales/*.ts` dictionaries in both `fr` and `en`, `packages/api-client` emits structured `ERR_CLIENT_*` codes via `OrciaClientError` (without depending on `apps/web`), `UserPasswordChangeCard` consumes required typed `labels` props (without fallback French/English strings), and Gate 3 (`clientErrorBaseline`) locks permanently to **`0`**.
- **Constraints from `ARCHITECTURE-SPINE.md` & `AGENTS.md`**:
  - Zero circular dependencies across workspace packages (`packages/api-client` and `packages/ui` must remain completely independent of `apps/web`).
  - Zero UX Rule 3.1 jargon (`RFC 9457`, `READ_ONLY_OBSERVER`, `human_authored_required`, etc.) in `frDictionary` / `enDictionary` leaf values (`i18n-dictionary-parity-and-jargon-audit.test.ts`).
  - Every modified/created file must stay `<= 300` lines (`wc -l`) with English-only comments/docstrings.

### 1.2 Exploration, GitNexus Impact Analysis, Refactoring & Technical Debt
- **GitNexus Impact Analysis (`gitnexus_query`, `gitnexus_context`, `gitnexus_impact` scoped to `/home/romain/Documents/Projects/ORCIA`)**:
  - `gitnexus_impact({target: "formatRfc9457ErrorToBanner", direction: "upstream", repo: "/home/romain/Documents/Projects/ORCIA"})` returned `risk: UNKNOWN` (TypeScript index behind by 2 commits / symbol unresolved in graph).
  - `gitnexus_impact({target: "resolveClientErrorMessage", direction: "upstream", repo: "/home/romain/Documents/Projects/ORCIA"})` returned `risk: UNKNOWN`.
  - Per GitNexus governance (`UNKNOWN` treated as unresolved, confirmed via repo-wide grep on `apps/` and `packages/`), direct callers verified:
    - `formatRfc9457ErrorToBanner`: called across 16+ files (`platformSetupGovernanceActions.ts`, `usePlatformSetupHydrationEffect.ts`, `assistantTurnControlsHelper.ts`, `inboxTurnSyncHelpers.ts`, `useServerAssistantFolders.ts`, `useFinopsDashboardController.ts`, `WorkspaceSourceAttachModal.tsx`, `WorkspaceDnaAndWaiversSection.tsx`, `WorkspaceStudioSummaryCard.tsx`, `WorkspaceSourcesRagTab.tsx`, `features/workspaces/index.tsx`, `ValueStreamMapView.tsx`, `useStudioWorkflowController.ts`, `useWorkflowTriggers.ts`, `ProcessesHubPage.tsx`, `SettingsPacksSection.tsx`, and Vitest spec `ux-polish-rfc9457-alerts-euro-and-jargon-purge.test.tsx`). Preserving its exported signature `(error, locale = "fr", resourceLabel?) => FormattedRfc9457Banner` guarantees drop-in compatibility.
    - `resolveClientErrorMessage`: called by `client-error-code-resolution.test.ts` and `client-error-code-contract-audit.test.ts`. Preserving its signature while adding `resolveClientErrorForLocale(code, locale, params)` and `ClientCodedError` keeps all existing contracts intact.
    - `UserPasswordChangeCard`: used in `packages/ui/src/primitives/UserSettingsProfileAndPassthroughTabs.tsx` (which receives `passwordSecurity` from `UserSettingsModalDialog.tsx` -> `apps/web` `dictionary.userAccountAndSettings.passwordSecurity`) and tested in `packages/ui/src/__tests__/temporary-password-modal.test.tsx`.
- **Exploration & Key Metrics**:
  - Line-count audit of all 30 Category A / Gate 3 files identified 7 files currently above 300 lines requiring modular splitting when edited:
    1. `apps/web/src/lib/formatRfc9457ErrorToBanner.ts` (`360` lines)
    2. `packages/api-client/src/helpers.ts` (`301` lines)
    3. `apps/web/src/features/admin/organization/orgUnitsApiBridge.ts` (`318` lines)
    4. `apps/web/src/features/processes/execution/useInteractiveProcessRunController.ts` (`349` lines)
    5. `apps/web/src/features/workspaces/WorkspaceSourcesRagTab.tsx` (`346` lines)
    6. `apps/web/src/routes/wizards.tsx` (`331` lines)
    7. `apps/web/src/stores/authSessionStore.ts` (`349` lines)
  - Existing Vitest contract assertions checked:
    - `story-25-4-spinner-localized-timeout-and-delete.test.tsx` asserts `localErr.textContent` contains `"16 s"` and `ERR_MODEL_CONNECTION_TIMEOUT` handling.
    - `ux-polish-rfc9457-alerts-euro-and-jargon-purge.test.tsx` asserts exact FR/EN banner titles for `ERR_OBSERVER_MODE_READ_ONLY`, `ERR_RESOURCE_NOT_FOUND`, `ERR_ONTOLOGY_CONFLICT`, `ERR_VALIDATION_FAILED`, and HTTP `503`.
    - `assistant-workspace.test.tsx` asserts adaptive step label `"Spécification et cas limites"`.
- **Refactoring Opportunities & Emerging Technical Debt Mitigation**:
  - Extract RFC 9457 actionable catalog, HTTP status fallbacks, resource suffix, and jargon sanitization replacements into modular `apps/web/src/i18n/locales/rfc9457_banner_labels_{fr,en}.ts` + `rfc9457_banner_labels.ts` wired into `TranslationDictionary`.
  - Extract shared client error resolution helpers (`resolveClientErrorForLocale`, `extractClientOrProblemBanner`) so bridges and controllers stop duplicating `err instanceof OrciaProblemError ? ... : locale === "fr" ? ... : ...` blocks.
  - Extract shared modular helpers from the 7 oversized files (`> 300` lines) so every touched/created file stays `<= 300` lines.

---

## 2. Implementation Plan

### 2.1 Data Schema & Alembic Migrations
- Not applicable (no database schema or Alembic migration changes).

### 2.2 Hexagonal Core, Orchestration & Workers
- Not applicable (Python domain/worker layers are out of scope for Story 27.2; verified via English-only diff audit).

### 2.3 Backend API, Security & Contracts (`packages/api-client/`)
- `packages/api-client/src/sseAndQueryHelpers.ts`:
  - Introduce `OrciaClientError` (`code: string`, `params?: { seconds?: number; detail?: string }`) and export it via `packages/api-client/src/helpers.ts` and `packages/api-client/src/index.ts`.
  - Replace hardcoded `"HTTP Error"` / `"Unexpected non-JSON error response"` in `parseProblemError` with structured non-user-facing error codes (`"ERR_CLIENT_HTTP_FALLBACK"` / `"ERR_CLIENT_INVALID_PAYLOAD"`).
- `packages/api-client/src/helpers.ts` (trimmed `<= 300` lines):
  - Replace `throw new Error(\`SSE stream error: empty response body...\`)` with `throw new OrciaClientError("ERR_CLIENT_SSE_EMPTY_BODY", { detail: params.path })`.
- `packages/api-client/src/domains/workflowsV2.ts`:
  - Replace `throw new Error("Binary download helper not configured on workflowsV2 client.")` with `throw new OrciaClientError("ERR_CLIENT_NOT_CONFIGURED", { detail: "workflowsV2.requestBinary" })`.

### 2.4 User Interface & Experience (`apps/web/`, `packages/ui/`)
- **`packages/ui`**:
  - `packages/ui/src/primitives/UserPasswordChangeCard.tsx`: Remove `DEFAULT_FR_PASSWORD_LABELS`, `DEFAULT_EN_PASSWORD_LABELS`, and `locale === "en"` fallback; require `labels: UserPasswordSecurityLabels` via props.
  - `packages/ui/src/primitives/UserAccountDropdownTypes.ts` & `packages/ui/src/primitives/UserSettingsProfileAndPassthroughTabs.tsx`: Require `passwordSecurity: UserPasswordSecurityLabels`.
  - `packages/ui/src/__tests__/userSettingsLabelsFixture.ts` & `packages/ui/src/__tests__/temporary-password-modal.test.tsx`: Supply `passwordSecurity` in test fixtures.
- **`apps/web` Shared Error Infrastructure & Dictionaries**:
  - Expand `apps/web/src/lib/clientErrorCodes.ts` with Category A `ClientErrorCode` variants (`ERR_CLIENT_SSE_EMPTY_BODY`, `ERR_CLIENT_HTTP_FALLBACK`, `ERR_CLIENT_NOT_CONFIGURED`, `ERR_CLIENT_AUTH_HYDRATION_TIMEOUT`, `ERR_CLIENT_SESSION_EXPIRED`, `ERR_CLIENT_AI_*`, `ERR_CLIENT_IAM_NETWORK`, `ERR_CLIENT_ORG_UNITS_NETWORK`, `ERR_CLIENT_AUDIT_NETWORK`, `ERR_CLIENT_CONNECTOR_*`, `ERR_CLIENT_FEDERATED_SEARCH`, `ERR_CLIENT_PLATFORM_HYDRATION`, `ERR_CLIENT_CONTEXT_MISSING`, `ERR_CLIENT_PERMISSION_*`, `ERR_CLIENT_PACKS_*`, `ERR_CLIENT_PROCESS_*`, `ERR_CLIENT_HELP_ARTICLE_ATTACHED_LOCAL`, `ERR_CLIENT_WIZARD_*`, `ERR_CLIENT_WORKSPACE_SOURCE_ACTION`) and add `ClientCodedError`.
  - Update `apps/web/src/i18n/locales/client_errors_labels.ts` (split FR/EN into `client_errors_labels_{fr,en}.ts` if approaching 300 lines) with bilingual, jargon-free `fr` / `en` messages (preserving `"16 s"` in FR timeout message for `story-25-4` compatibility).
  - Create modular `apps/web/src/i18n/locales/rfc9457_banner_labels_{fr,en}.ts` + `rfc9457_banner_labels.ts` and `apps/web/src/i18n/locales/category_a_controller_labels_{fr,en}.ts` + `category_a_controller_labels.ts` (wired into `TranslationDictionary`, `fr.ts`, `en.ts`) for non-error controller/stream labels previously co-located with Category A files (e.g., `assistantBackgroundStreamStore.ts` adaptive thinking steps, `useStudioWorkflowController.ts`, `usePacksRegistryHealthchecks.ts`, `useEnterpriseConnectorsController.ts`, `wizards.tsx`, `WorkspaceSourcesRagTab.tsx`, `useInteractiveProcessRunController.ts`, `ProcessStudioAndPackAuthoringSection.tsx`).
  - Refactor `apps/web/src/lib/formatRfc9457ErrorToBanner.ts` (`<= 200` lines) to resolve RFC 9457 catalog entries, HTTP status fallbacks, `OrciaClientError`, `ClientCodedError`, and sanitization replacements strictly from locale dictionary maps (`{ fr, en }[locale]`) with zero inline prose or `locale === "fr"` ternaries.
- **Category A Bridges, Stores & Controllers (all `<= 300` lines)**:
  - Migrate all remaining 23 Gate 3 files and Category A inventory files (`ShellFederatedSearchModal.tsx`, `platformSetupWorkspaces.ts`, `platformSetupStore.tsx`, `platformSetupHydration.ts`, `useSidebarAccountSettings.ts`, `aiModelsApiBridge.ts`, `useEnterpriseConnectorsController.ts`, `iamApiBridge.ts`, `orgUnitsApiBridge.ts` + split helper, `useCockpitGovernanceController.ts`, `useFinopsDashboardController.ts`, `assistantBackgroundStreamStore.ts`, `useAssistantStreamingTurn.ts`, `useInboxPanelController.ts`, `usePermissionBrokerTickets.ts`, `ProcessStudioAndPackAuthoringSection.tsx`, `useInteractiveProcessRunController.ts` + split helper, `useStudioWorkflowController.ts`, `usePacksRegistryHealthchecks.ts`, `WorkspaceSourcesRagTab.tsx` + split helper, `activityApiBridge.ts`, `settingsAiModelsPresets.ts`, `useAiModelsSectionController.ts`, `wizards.tsx` + split helper, `authSessionStore.ts` + split helper).
  - Lock `clientErrorBaseline` in `apps/web/src/__tests__/i18n-hardcoded-locale-baseline.json` to `{}` (`totalClientErrorViolations: 0`) and decrement Gate 1 (`astFiles`) counts strictly on every touched file.

### 2.5 Test Pyramid Impact Analysis (`AD-17` — Layers 1 to 5 + Security, Mandatory)
- **Layer 1a & 1b (Unit & Component)**:
  - Extend `apps/web/src/__tests__/client-error-code-resolution.test.ts` (keeping `<= 300` lines) to cover `formatRfc9457ErrorToBanner` in `fr` and `en` across `OrciaClientError`, `ClientCodedError`, HTTP fallbacks, `ERR_CLIENT_*` codes inside `ProblemDetails`, and token sanitization parity.
  - Run Gate 1 (`i18n-hardcoded-locale-ast-audit.test.ts`), Gate 2 (`i18n-dictionary-parity-and-jargon-audit.test.ts`), Gate 3 (`client-error-code-contract-audit.test.ts`), `ux-polish-rfc9457-alerts-euro-and-jargon-purge.test.tsx`, `story-25-4-spinner-localized-timeout-and-delete.test.tsx`, `packages/api-client`, and `packages/ui` (`temporary-password-modal.test.tsx`) plus `tsc --noEmit` across `@orcia/api-client`, `@orcia/ui`, and `@orcia/web`.
- **Layer 2, Layer 3, Layer 4, Security, Layer 5**:
  - Verified by the Testing Sub-Agent after Coding completes (no backend/schema changes in Story 27.2; `test_i18n_backend_catalog_and_english_dev_audit.py --no-cov` validates English-only comments/docstrings on modified lines).

---

## 3. Summary of Changes & Results (Post-Implementation)

### 3.1 Created & Modified Files (`56` `.ts`/`.tsx` files + baseline/tracking docs)
| File | Action | Lines (`wc -l`) | Concise Summary |
| :--- | :--- | :--- | :--- |
| `packages/api-client/src/sseAndQueryHelpers.ts` | Modified | `141` L | Added `OrciaClientError` (`code`, `params`) and replaced raw HTTP/payload error strings in `parseProblemError` with `ERR_CLIENT_HTTP_FALLBACK` / `ERR_CLIENT_INVALID_PAYLOAD`. |
| `packages/api-client/src/helpers.ts` | Modified | `300` L | Replaced raw SSE empty-body error prose with `OrciaClientError("ERR_CLIENT_SSE_EMPTY_BODY")` and re-exported `OrciaClientError`. |
| `packages/api-client/src/domains/workflowsV2.ts` | Modified | `139` L | Replaced hardcoded binary-download configuration error with `OrciaClientError("ERR_CLIENT_NOT_CONFIGURED")`. |
| `packages/api-client/src/index.ts` | Modified | `219` L | Exported `OrciaClientError` and `OrciaClientErrorParams` from `@orcia/api-client`. |
| `packages/ui/src/primitives/UserPasswordChangeCard.tsx` | Modified | `230` L | Removed `DEFAULT_FR_PASSWORD_LABELS` / `DEFAULT_EN_PASSWORD_LABELS` and `locale === "en"` fallbacks; now requires typed `labels` props. |
| `packages/ui/src/primitives/UserAccountDropdownTypes.ts` | Modified | `195` L | Made `passwordSecurity: UserPasswordSecurityLabels` required on `UserSettingsModalProps`. |
| `packages/ui/src/__tests__/userSettingsLabelsFixture.ts` | Modified | `119` L | Added `passwordSecurity` fixture labels for `@orcia/ui` tests. |
| `packages/ui/src/__tests__/temporary-password-modal.test.tsx` | Modified | `142` L | Passed required `labels` prop to `UserPasswordChangeCard`. |
| `apps/web/src/lib/clientErrorCodes.ts` | Modified | `164` L | Expanded `CLIENT_ERROR_CODES` (`43` Category A codes), added `ClientCodedError` and `resolveClientErrorForLocale`, and preserved `resolveClientErrorMessage`. |
| `apps/web/src/i18n/locales/client_errors_labels.ts` | Refactored | `10` L | Split FR/EN client error catalogs into symmetric sub-modules. |
| `apps/web/src/i18n/locales/client_errors_labels_fr.ts` | Created | `86` L | French Category A client error dictionary (`ERR_CLIENT_*`, UX Rule 3.1 zero-jargon, `16 s` timeout parity). |
| `apps/web/src/i18n/locales/client_errors_labels_en.ts` | Created | `86` L | English Category A client error dictionary (`ERR_CLIENT_*`, 1:1 key & `{param}` parity). |
| `apps/web/src/i18n/locales/rfc9457_banner_labels.ts` | Created | `38` L | Typed `Rfc9457BannerLabels` interface and FR/EN export barrel. |
| `apps/web/src/i18n/locales/rfc9457_banner_labels_fr.ts` | Created | `135` L | French RFC 9457 actionable catalog, HTTP status fallbacks, resource suffix, and jargon sanitization replacements. |
| `apps/web/src/i18n/locales/rfc9457_banner_labels_en.ts` | Created | `127` L | English RFC 9457 actionable catalog, HTTP status fallbacks, resource suffix, and sanitization replacements. |
| `apps/web/src/i18n/locales/category_a_controller_labels.ts` | Created | `95` L | Typed `CategoryAControllerLabels` interface for localized controller/store feedback. |
| `apps/web/src/i18n/locales/category_a_controller_labels_fr.ts` | Created | `169` L | French controller/store/stream feedback labels (`packsRegistry`, `wizards`, `connectors`, `processes`, `workspaceSources`, `assistantStream`). |
| `apps/web/src/i18n/locales/category_a_controller_labels_en.ts` | Created | `168` L | English controller/store/stream feedback labels (`1:1` parity with French). |
| `apps/web/src/i18n/locales/fr.ts` | Modified | `51` L | Wired `rfc9457Banner` and `categoryAControllers` into `frDictionary`. |
| `apps/web/src/i18n/locales/en.ts` | Modified | `51` L | Wired `rfc9457Banner` and `categoryAControllers` into `enDictionary`. |
| `apps/web/src/i18n/types.ts` | Modified | `100` L | Added `rfc9457Banner` and `categoryAControllers` to `TranslationDictionary`. |
| `apps/web/src/i18n/index.tsx` | Modified | `69` L | Exposed `getDictionaryForLocale` helper for non-React stores/bridges. |
| `apps/web/src/lib/formatRfc9457ErrorToBanner.ts` | Refactored | `282` L | Migrated RFC 9457 banner formatting, HTTP status fallbacks, `OrciaClientError`, `ClientCodedError`, `formatLocalizedProblemWithCode`, and `extractLocalizedApiError` to typed FR/EN dictionary maps with zero inline ternaries. |
| `apps/web/src/stores/authSessionHydration.ts` | Created | `87` L | Extracted auth session hydration & timeout/expired code resolution from `authSessionStore.ts`. |
| `apps/web/src/stores/authSessionStore.ts` | Refactored | `293` L | Split under `300` L and replaced inline auth session error strings with `ClientErrorCode`. |
| `apps/web/src/components/platformSetupHydration.ts` | Modified | `253` L | Migrated platform setup hydration error paths to `ClientErrorCode`. |
| `apps/web/src/components/platformSetupStore.tsx` | Modified | `289` L | Migrated platform setup store error handling to `extractLocalizedApiError` / `ClientErrorCode`. |
| `apps/web/src/components/platformSetupWorkspaces.ts` | Modified | `258` L | Migrated workspace bootstrap action errors to localized `ClientErrorCode` resolution. |
| `apps/web/src/components/ShellFederatedSearchModal.tsx` | Modified | `211` L | Replaced hardcoded search error fallback with `ClientErrorCode` (`ERR_CLIENT_FEDERATED_SEARCH`). |
| `apps/web/src/components/useSidebarAccountSettings.ts` | Modified | `297` L | Replaced account settings error strings and passed `passwordSecurity` labels. |
| `apps/web/src/features/admin/ai-models/aiModelsApiBridge.ts` | Modified | `136` L | Migrated AI model bridge errors to `ClientErrorCode`. |
| `apps/web/src/features/admin/connectors/useEnterpriseConnectorsController.ts` | Modified | `108` L | Migrated enterprise connector errors/messages to `ClientErrorCode` and `categoryAControllers`. |
| `apps/web/src/features/admin/iam/iamApiBridge.ts` | Modified | `268` L | Migrated IAM API bridge errors to `ClientErrorCode`. |
| `apps/web/src/features/admin/organization/orgUnitsApiMappers.ts` | Created | `64` L | Split organization unit DTO mappers from `orgUnitsApiBridge.ts`. |
| `apps/web/src/features/admin/organization/orgUnitsApiBridge.ts` | Refactored | `256` L | Split under `300` L and migrated org-unit bridge errors to `ClientErrorCode`. |
| `apps/web/src/features/bootstrap/WizardsStepForm.tsx` | Modified | `250` L | Wired localized `categoryAControllers` labels into wizard step form. |
| `apps/web/src/features/cockpit/useCockpitGovernanceController.ts` | Modified | `164` L | Migrated cockpit governance error handling to `ClientErrorCode`. |
| `apps/web/src/features/finops/useFinopsDashboardController.ts` | Modified | `299` L | Migrated FinOps dashboard error handling to `ClientErrorCode` / `formatRfc9457ErrorToBanner`. |
| `apps/web/src/features/inbox/assistantBackgroundStreamStore.ts` | Modified | `274` L | Migrated background stream errors and adaptive thinking step labels to `ClientErrorCode` / `categoryAControllers`. |
| `apps/web/src/features/inbox/useInboxPanelController.ts` | Modified | `286` L | Migrated inbox panel error paths to `ClientErrorCode`. |
| `apps/web/src/features/inbox/usePermissionBrokerTickets.ts` | Modified | `129` L | Migrated permission broker error strings to `ClientErrorCode`. |
| `apps/web/src/features/processes/ProcessStudioAndPackAuthoringSection.tsx` | Modified | `229` L | Migrated authoring errors/feedback to `ClientErrorCode` and `categoryAControllers`. |
| `apps/web/src/features/processes/execution/interactiveRunGoalPayload.ts` | Created | `21` L | Extracted run goal payload builder from `useInteractiveProcessRunController.ts`. |
| `apps/web/src/features/processes/execution/useInteractiveProcessRunController.ts` | Refactored | `291` L | Split under `300` L and migrated process run errors/status labels to `ClientErrorCode` / `categoryAControllers`. |
| `apps/web/src/features/processes/studio/useStudioWorkflowController.ts` | Modified | `285` L | Migrated workflow studio errors/messages to `ClientErrorCode` / `categoryAControllers`. |
| `apps/web/src/features/settings/packs/usePacksRegistryHealthchecks.ts` | Modified | `176` L | Migrated packs registry errors to `formatLocalizedProblemWithCode` / `ClientErrorCode` and health banners to `categoryAControllers.packsRegistry`. |
| `apps/web/src/features/workspaces/sources/WorkspaceSourcesColdStartBanner.tsx` | Created | `44` L | Extracted cold-start warning banner component from `WorkspaceSourcesRagTab.tsx`. |
| `apps/web/src/features/workspaces/sources/WorkspaceSourcesRenewReferentForm.tsx` | Created | `82` L | Extracted referent renewal form from `WorkspaceSourcesRagTab.tsx`. |
| `apps/web/src/features/workspaces/WorkspaceSourcesRagTab.tsx` | Refactored | `292` L | Split under `300` L and migrated workspace source error handling to `ClientErrorCode` / `categoryAControllers`. |
| `apps/web/src/routes/activityApiBridge.ts` | Modified | `161` L | Migrated activity API bridge errors to `ClientErrorCode`. |
| `apps/web/src/routes/profile.tsx` | Modified | `131` L | Passed `passwordSecurity` dictionary labels to profile password card. |
| `apps/web/src/routes/settingsAiModelsPresets.ts` | Modified | `235` L | Migrated AI model preset error/status helpers to `ClientErrorCode`. |
| `apps/web/src/routes/useAiModelsSectionController.ts` | Modified | `291` L | Migrated AI models section controller errors to `ClientErrorCode`. |
| `apps/web/src/routes/useWizardsRouteController.ts` | Created | `238` L | Extracted wizard route state/actions and `formatLocalizedProblemWithCode` error handling from `wizards.tsx`. |
| `apps/web/src/routes/wizards.tsx` | Refactored | `128` L | Split under `300` L and consumed `useWizardsRouteController` + `categoryAControllers.wizards`. |
| `apps/web/src/__tests__/client-error-code-resolution.test.ts` | Modified | `180` L | Extended unit coverage (`9` tests) for `formatRfc9457ErrorToBanner`, `OrciaClientError`, `ClientCodedError`, HTTP fallbacks, and sanitization parity (`fr`/`en`). |
| `apps/web/src/__tests__/i18n-hardcoded-locale-baseline.json` | Modified | `160` L | Locked Gate 3 `clientErrorBaseline` to `{}` (`totalClientErrorViolations: 0`) and decremented Gate 1 `totalAstViolations` (`1,253 -> 1,129`). |

### 3.2 Quantitative Metrics, Baseline Counts & Static Quality (Independent Testing Sub-Agent)
- **Line-Count Guard (`wc -l <= 300`)**: `56/56` modified/created `.ts`/`.tsx` files (`0` `.py` files modified) are `<= 300` lines (max `300` L in `packages/api-client/src/helpers.ts`, `299` L in `useFinopsDashboardController.ts`).
- **Deterministic Ratchet Baselines**:
  - **Gate 1 (`i18n-hardcoded-locale-ast-audit.test.ts`, `3` tests)**: Reduced `totalAstViolations` from **`1,253` $\rightarrow$ `1,129`** (`-124` violations across `astFiles`).
  - **Gate 2 (`i18n-dictionary-parity-and-jargon-audit.test.ts`, `2` tests)**: **`0` violations** across `frDictionary` and `enDictionary` (recursive key parity, `{param}` placeholder parity, non-empty leaves, UX Rule 3.1 zero-jargon).
  - **Gate 3 (`client-error-code-contract-audit.test.ts`, `4` tests)**: **`0` violations** (`totalClientErrorViolations: 0`, `clientErrorBaseline: {}` across `apps/web/src` and `packages/api-client/src`).
  - **Gate 4 (`tests/unit/test_i18n_backend_catalog_and_english_dev_audit.py`, `3 passed` in `13.91s`)**: **PASS** (backend `ERROR_CATALOG` parity, prompt neutrality, and English-only diff comments/docstrings verified).
- **Workspace Lint, Typecheck & Test Results (`pnpm turbo run lint typecheck test`)**: **`9/9` tasks passed** (`447` JS/TS tests across `112` test files):
  - `@orcia/api-client`: `lint`, `typecheck`, `test` PASS — `3 passed (3)` test files, **`20 passed (20)`** tests.
  - `@orcia/ui`: `lint`, `typecheck`, `test` PASS — `35 passed (35)` test files, **`139 passed (139)`** tests.
  - `@orcia/web`: `lint`, `typecheck`, `test` PASS — `74 passed (74)` test files, **`288 passed (288)`** tests (including Gate 1 `3`, Gate 2 `2`, Gate 3 `4`, `client-error-code-resolution.test.ts` `9`, and `ux-polish-rfc9457-alerts-euro-and-jargon-purge.test.tsx` `5`).
- **Documentation & Showcase Governance Gates**:
  - `.venv/bin/python scripts/check_implementation_docs.py`: verified clean.
  - `pnpm site:sync && pnpm site:check` & `.venv/bin/pytest tests/unit/test_site_catalog_sync.py --no-cov -q`: verified clean.

### 3.3 AD-17 Test Pyramid & Vertical Wiring Verification
- **Layer 1a — Python Governance Audit (`tests/unit/`)**: `test_i18n_backend_catalog_and_english_dev_audit.py` (`3 passed`) confirms `0` non-English comment/docstring regressions vs `main` and preserves Gate 4 baseline integrity.
- **Layer 1b — Frontend TS, Design System & AST Audits (`Vitest`)**: `447` tests passed across `@orcia/api-client` (`20`), `@orcia/ui` (`139`), and `@orcia/web` (`288`), validating `OrciaClientError` propagation, required `UserPasswordChangeCard` typed props, `formatRfc9457ErrorToBanner` FR/EN parity, Gate 1 (`1,129`), Gate 2 (`0`), and Gate 3 (`0`).
- **Layer 2 (`tests/integration/`), Layer 3 (`OpenAPI`), Layer 4 (`tests/evals/`), Security (`tests/security/`) & Layer 5 (`Playwright`)**: No database schema, Python domain/router, or OpenAPI schema changes in Story 27.2; existing UI error banners (`[role="alert"]` and code-bearing messages on packs/wizards) verified under real `<RouterProvider>` in `@orcia/web` Vitest suites.
