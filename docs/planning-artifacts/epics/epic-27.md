## Epic 27: English-Only Development & Documentation Governance, 100% Bilingual FR/EN Web Application & Deterministic i18n Controls (`AD-17`, `AD-19`, RFC 9457)

Enforce **English** as the mandatory language for all development communications, documentation, Tech Lead reports, commit messages, and code comments/docstrings while preserving and guaranteeing **100% French (`fr`) and English (`en`) bilingual compatibility** across the web application (`apps/web` + `@orcia/ui`) and user-facing backend APIs (`Accept-Language` RFC 9457 error catalogs and Assistant prompt bundles).

This Epic fully executes [`ACTION_ITEM-I18N.1`](../implementation-artifacts/sprint-status.yaml) based on the [`2026-11-20` i18n audit report](../implementation-artifacts/tech-lead-reports/2026-11-20-audit-i18n-chaines-codees-en-dur-tech-lead-report.md) (`3,809` raw heuristic hits across `461` files: `A=71`, `B=577`, `C=2,816`, `D=193`, `E=152`) and the active decisions [`epic-27-decisions-grill-2026-11-23.md`](../implementation-artifacts/epic-27-decisions-grill-2026-11-23.md) (`D1–D4`).

**Execution order across 6 lots (8 stories):**
- **Lot 0 — Deterministic Guardrails & Foundation:** `27.1` (`bmad-dev-worker` `flash`)
- **Lot 1 — Category A Client Errors:** `27.2` (`bmad-dev-worker` `flash`, depends on `27.1`)
- **Lot 2 — Category C `apps/web` Shell, Routes & Features:** `27.3` (`flash`) → `27.4` (`flash`, depends on `27.1`)
- **Lot 3 — Category C Studio/VSM & `@orcia/ui` Design System:** `27.5` (`flash`, depends on `27.3`, `27.4`) → `27.6` (`flash`, depends on `27.5`)
- **Lot 4 — Categories B & D Backend RFC 9457, Prompts & Seeds:** `27.7` (`flash`, depends on `27.1`)
- **Lot 5 — Zero-Baseline Lock & Bilingual E2E Closure:** `27.8` (`flash` + mandatory `bmad-architect-worker` `pro` final gate, depends on `27.2`, `27.5`, `27.6`, `27.7`)

Every modified or created source file must stay `<= 300` lines, preserve `AD-19` modular monolith boundaries (`lint-imports`), keep `0-diff` OpenAPI 3.1 SDK compliance, use English-only code comments/docstrings, and maintain strictly decreasing deterministic ratchet baselines down to **`0`** in Story `27.8`.

---

### Story 27.1: Deterministic i18n CI Guardrails (Gates 1–4) & Shared Client Error Code Resolution Foundation (`ClientErrorCode` + `resolveClientErrorMessage`)

As a Platform Tech Lead and Release Gatekeeper,
I want four deterministic AST/dictionary/contract CI gates installed alongside a shared `ClientErrorCode` + `resolveClientErrorMessage` helper in the frontend,
So that no new hardcoded FR/EN strings, locale ternaries, missing dictionary keys, client error prose, non-localized backend error codes, or non-English code comments can enter the codebase while legacy occurrences ratchet down cleanly to zero.

**Lot:** 0 — Deterministic Guardrails & Foundation. **Dependencies:** None (Epic 27 branch initialized). **Agent:** `bmad-dev-worker` (`flash`).
**Findings covered:** `ACTION_ITEM-I18N.1` (Lot 2 guardrail + Lot 1 shared helper), `D3` (Gates 1–4).
**CAPs covered:** `CAP-100` (`hygiene` — CI guardrails & shared i18n resolution foundation).
**Impacted files:** `apps/web/src/lib/clientErrorCodes.ts` (new), `apps/web/src/i18n/locales/{fr,en}.ts`, `apps/web/src/__tests__/i18n-hardcoded-locale-ast-audit.test.ts` (new), `apps/web/src/__tests__/i18n-hardcoded-locale-baseline.json` (new), `apps/web/src/__tests__/i18n-dictionary-parity-and-jargon-audit.test.ts` (new), `apps/web/src/__tests__/client-error-code-contract-audit.test.ts` (new), `apps/web/src/__tests__/client-error-code-resolution.test.ts` (new), `tests/unit/test_i18n_backend_catalog_and_english_dev_audit.py` (new), `tests/unit/i18n_backend_audit_baseline.json` (new).
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/27-1-deterministic-i18n-ci-guardrails-and-client-error-code-foundation-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** TypeScript/React sources in `apps/web/src/` and `packages/ui/src/` (excluding `apps/web/src/i18n/locales/`, `generated/`, and `__tests__/`)
**When** Gate 1 (`i18n-hardcoded-locale-ast-audit.test.ts`) executes via `pnpm turbo run test`
**Then** the TypeScript Compiler AST visitor detects every inline locale ternary (`locale === "fr" ? ... : ...`, `isFr ? ... : ...`) and raw user-facing JSX text or UI attribute (`title`, `placeholder`, `aria-label`, `alt`, `label`, `description`, `emptyMessage`, `helperText`, etc.), fails immediately on any file exceeding its recorded entry in `i18n-hardcoded-locale-baseline.json` (ratchet), and allows explicit benign technical markers only when annotated as non-user-facing.

**Given** all `fr` and `en` dictionary files under `apps/web/src/i18n/locales/`
**When** Gate 2 (`i18n-dictionary-parity-and-jargon-audit.test.ts`) and Gate 3 (`client-error-code-contract-audit.test.ts`) run
**Then** Gate 2 fails on any missing nested key between FR and EN, any mismatched `{param}` interpolation placeholder, any empty translation value, or any UX Rule 3.1 forbidden internal jargon token; Gate 3 verifies `ClientErrorCode` + `resolveClientErrorMessage(code, labels, params)` resolves `ERR_CLIENT_TIMEOUT`, `ERR_CLIENT_NETWORK`, `ERR_CLIENT_ABORTED`, `ERR_CLIENT_SSE_DISCONNECTED`, `ERR_CLIENT_INVALID_PAYLOAD`, and `ERR_CLIENT_UNKNOWN` cleanly in both `fr` and `en` (falling back safely on unknown codes with parameterized duration/details) and enforces a strictly bounded ratchet baseline across `*ApiBridge.ts`, `packages/api-client/src/`, `formatRfc9457ErrorToBanner.ts`, stores, and controllers.

**Given** Python modules across `packages/orcia-core`, `apps/api`, and `apps/worker`
**When** Gate 4 (`test_i18n_backend_catalog_and_english_dev_audit.py`) executes via `.venv/bin/pytest tests/unit`
**Then** it asserts every `OrciaDomainError` / registered RFC 9457 `error_code` provides non-empty `fr` and `en` localized templates resolved via `Accept-Language`, flags any hardcoded single-language LLM prompt directive outside `PROMPT_LOCALES`, enforces an English-only comment/docstring check on newly added or modified Python/TypeScript lines relative to `main` (while recording legacy ratchet counts in `i18n_backend_audit_baseline.json`), and all unit/Turbo gates pass at `>= 90%` branch coverage on new code.

---

### Story 27.2: Category A Remediation (`71` Hits / `26` Files) — Migrate All Client API Bridges, SSE Stores, Controllers & `formatRfc9457ErrorToBanner` to `ClientErrorCode`

As a French or English ORCIA User,
I want every client-side timeout, network disconnect, stream interruption, and RFC 9457 banner fallback to come from structured `ClientErrorCode` keys resolved in my active language,
So that no hardcoded French/English error string or hardcoded `"16 s"` delay ever leaks into error banners or notifications.

**Lot:** 1 — Category A Client Errors. **Dependencies:** `27.1`. **Agent:** `bmad-dev-worker` (`flash`).
**Findings covered:** `ACTION_ITEM-I18N.1` (Lot 1 — Category A `71` hits / `26` files).
**CAPs covered:** `CAP-001`..`CAP-260` (cross-cutting client error localization).
**Impacted files:** `apps/web/src/lib/formatRfc9457ErrorToBanner.ts`, `packages/api-client/src/helpers.ts`, `packages/api-client/src/sseAndQueryHelpers.ts`, `packages/api-client/src/domains/workflowsV2.ts`, `apps/web/src/features/workspaces/WorkspaceSourcesRagTab.tsx`, `apps/web/src/features/inbox/assistantBackgroundStreamStore.ts`, `apps/web/src/features/inbox/useAssistantStreamingTurn.ts`, `apps/web/src/components/useSidebarAccountSettings.ts`, `apps/web/src/components/platformSetup{Workspaces,Store,Hydration}.ts*`, `apps/web/src/components/ShellFederatedSearchModal.tsx`, `apps/web/src/routes/settingsAiModelsPresets.ts`, `apps/web/src/routes/useAiModelsSectionController.ts`, `apps/web/src/routes/wizards.tsx`, `apps/web/src/routes/activityApiBridge.ts`, `apps/web/src/features/admin/{ai-models/aiModelsApiBridge.ts,connectors/useEnterpriseConnectorsController.ts,iam/iamApiBridge.ts,organization/orgUnitsApiBridge.ts}`, `apps/web/src/features/processes/{ProcessStudioAndPackAuthoringSection.tsx,execution/useInteractiveProcessRunController.ts}`, `apps/web/src/features/settings/packs/usePacksRegistryHealthchecks.ts`, `apps/web/src/features/inbox/usePermissionBrokerTickets.ts`, `apps/web/src/stores/authSessionStore.ts`, `packages/ui/src/primitives/UserPasswordChangeCard.tsx`, `apps/web/src/i18n/locales/{fr,en}.ts`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/27-2-category-a-client-error-codes-bridges-stores-and-rfc9457-banner-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** all `26` files identified in Category A of `_i18n-audit-inventory-raw.md` (including `formatRfc9457ErrorToBanner.ts`, `*ApiBridge.ts`, `packages/api-client`, stores, and controllers)
**When** refactored to emit structured `ClientErrorCode` values (`ERR_CLIENT_*`) with typed parameters (such as timeout duration in seconds)
**Then** zero inline `locale === "fr" ? ... : ...` error ternaries or raw French/English fallback sentences remain in any API bridge, `packages/api-client` helper, SSE runner, store, or `formatRfc9457ErrorToBanner.ts`, all `UserPasswordChangeCard` error fallbacks are passed via typed props from `apps/web` dictionaries, and Gate 3 (`client-error-code-contract-audit.test.ts`) baseline reaches **`0`**.

**Given** an API request timeout, network offline error, SSE disconnect, or unknown HTTP `5xx` error without a localized `problem.detail`
**When** rendered in `fr` and `en` in Vitest under `<RouterProvider>` (`apps/web/src/__tests__/`)
**Then** `[role="alert"]` displays the exact localized copy from `apps/web/src/i18n/locales/{fr,en}.ts` (preserving UX Rule 3.1 zero-jargon and HTTP `>= 400` visibility) and all touched files remain `<= 300` lines with English-only comments/docstrings.

---

### Story 27.3: Category C Remediation (Part 1) — `apps/web` Shell, Contextual Help, Notifications, Routes & Bootstrap Wizards

As a French or English ORCIA User,
I want the shell navigation, breadcrumbs, scope selector, federated search, contextual help panels, notifications, activity formatters, and bootstrap wizards to resolve 100% of their labels from typed `fr`/`en` dictionaries,
So that switching between French and English updates every navigation chrome, help article wrapper, notification, and onboarding step cleanly.

**Lot:** 2 — Category C Core Web (`apps/web`). **Dependencies:** `27.1`. **Agent:** `bmad-dev-worker` (`flash`).
**Findings covered:** `ACTION_ITEM-I18N.1` (Lot 3 — Category C `apps/web` shell, help, routes, wizards).
**CAPs covered:** `CAP-004`, `CAP-058`, `CAP-060`, `CAP-065`, `CAP-066`, `CAP-068`, `CAP-100`.
**Impacted files:** `apps/web/src/components/_contextualHelpSections.ts`, `apps/web/src/components/_contextualHelpSectionsEn.ts`, `apps/web/src/components/contextualHelpCatalog.ts`, `apps/web/src/components/shellNotificationBuilder.ts`, `apps/web/src/components/shellScopeOptions.ts`, `apps/web/src/components/shellBreadcrumbBuilders.ts`, `apps/web/src/components/CreateProcessFormDialog.tsx`, `apps/web/src/components/Shell*.tsx`, `apps/web/src/components/platformSetup*.ts*`, `apps/web/src/routes/activityFormatters.ts`, `apps/web/src/routes/*.tsx`, `apps/web/src/features/bootstrap/WizardsStepForm.tsx`, `apps/web/src/i18n/locales/{fr,en}.ts` (modular sub-dictionaries `<= 300` L), `apps/web/src/__tests__/i18n-hardcoded-locale-baseline.json`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/27-3-category-c-shell-contextual-help-notifications-routes-and-wizards-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** the shell, contextual help (`_contextualHelpSections*.ts`, `contextualHelpCatalog.ts`), notifications (`shellNotificationBuilder.ts`), breadcrumbs, scope selector, route components, `activityFormatters.ts`, and `WizardsStepForm.tsx`
**When** migrated to modular typed sub-dictionaries under `apps/web/src/i18n/locales/`
**Then** zero inline `locale === "fr"` / `isFr ? ... : ...` expressions or raw hardcoded JSX text strings remain in `apps/web/src/components/`, `apps/web/src/routes/`, or `apps/web/src/features/bootstrap/`, `_contextualHelpSections*.ts` are unified into typed `fr`/`en` dictionary modules, all touched files stay `<= 300` lines, and Gate 1 + Gate 2 pass with a strictly reduced baseline.

**Given** shell chrome, notifications, activity feed entries, and wizards rendered in both `fr` and `en`
**When** exercised in Vitest (`i18n-and-shell.test.tsx`, `zero-dead-buttons-and-silent-catches-audit.test.tsx`)
**Then** zero French strings leak in `en` mode, zero English strings leak in `fr` mode, all existing `data-testid` hooks stay intact (`e2e-testids-sync-audit.test.ts` passes), and zero UX Rule 3.1 jargon appears.

---

### Story 27.4: Category C Remediation (Part 2) — `apps/web` Cockpit, Inbox/Assistant, Workspaces, Gates, Catalog & Admin Features

As a French or English ORCIA User,
I want every label, tooltip, badge, modal, and empty state across Cockpit, Mon Assistant, Mes Espaces, Gates, Catalog, Agents, and Administration screens to live in typed `fr`/`en` dictionaries,
So that all primary business workspaces are genuinely bilingual without inline conditionals.

**Lot:** 2 — Category C Core Web (`apps/web`). **Dependencies:** `27.1`. **Agent:** `bmad-dev-worker` (`flash`).
**Findings covered:** `ACTION_ITEM-I18N.1` (Lot 3 — Category C `apps/web` feature modules).
**CAPs covered:** `CAP-001`..`CAP-091`, `CAP-180`, `CAP-190`, `CAP-200`..`CAP-260`.
**Impacted files:** `apps/web/src/features/cockpit/*`, `apps/web/src/features/inbox/*`, `apps/web/src/features/workspaces/*`, `apps/web/src/features/gates/*`, `apps/web/src/features/catalog/*`, `apps/web/src/features/admin/*`, `apps/web/src/features/settings/*`, `apps/web/src/features/shared/*`, `apps/web/src/i18n/locales/*`, `apps/web/src/__tests__/i18n-hardcoded-locale-baseline.json`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/27-4-category-c-cockpit-assistant-workspaces-gates-catalog-and-admin-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** all modules in `apps/web/src/features/{cockpit,inbox,workspaces,gates,catalog,admin,settings,shared}/`
**When** audited by Gate 1 (`i18n-hardcoded-locale-ast-audit.test.ts`) and Gate 2 (`i18n-dictionary-parity-and-jargon-audit.test.ts`)
**Then** zero hardcoded user-facing strings or inline `locale === "fr"` ternaries remain in those feature directories, all new keys are symmetrically populated in `fr` and `en` dictionary files (`<= 300` lines each), no UX Rule 3.1 jargon is introduced, and `i18n-hardcoded-locale-baseline.json` drops strictly for every remediated file.

**Given** Vitest feature suites and `zero-dead-buttons-and-silent-catches-audit.test.tsx`
**When** executed via `pnpm turbo run lint typecheck test`
**Then** all feature views render cleanly in both `fr` and `en`, F5 survival and `data-testid` sync audits pass (`0` regressions), and all touched files comply with the English comment/docstring policy.

---

### Story 27.5: Category C Remediation (Part 3) — Process Studio v2, VSM, Execution Panels & Bilingual Catalog Data Modules (`apps/web` Gate 1 Baseline = 0)

As a French or English Process Designer or Contributor,
I want Process Studio v2, the Value Stream Map, interactive execution/HITL panels, and reference process catalog data (`processStudioV2Data.ts` — 434 raw hits) to resolve all user-facing strings from typed bilingual dictionaries,
So that `apps/web/src/` reaches zero hardcoded locale violations (`baseline = 0`).

**Lot:** 3 — Category C Studio/VSM & `@orcia/ui`. **Dependencies:** `27.3`, `27.4`. **Agent:** `bmad-dev-worker` (`flash`).
**Findings covered:** `ACTION_ITEM-I18N.1` (Lot 3 — `processStudioV2Data.ts`, `StepDetailSheet.tsx`, `studioCatalogLabels.ts`, `InteractiveRunDeliverableAndHitlPanels.tsx`, etc.).
**CAPs covered:** `CAP-020`..`CAP-036`, `CAP-140`, `CAP-160`.
**Impacted files:** `apps/web/src/features/processes/processStudioV2Data.ts` (split into `<= 300` L modules), `apps/web/src/features/processes/vsm/StepDetailSheet.tsx`, `apps/web/src/features/processes/vsm/ValueStreamMapView.tsx`, `apps/web/src/features/processes/studio/*`, `apps/web/src/features/processes/execution/*`, `apps/web/src/features/processes/{ProcessCatalogCardGrid,ProcessesHubPage,ProcessStudioAndPackAuthoringSection}.tsx`, `apps/web/src/i18n/locales/*`, `apps/web/src/__tests__/i18n-hardcoded-locale-baseline.json`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/27-5-category-c-process-studio-v2-vsm-execution-and-bilingual-catalog-data-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** `apps/web/src/features/processes/` (including the `434`-hit `processStudioV2Data.ts` hotspot, `StepDetailSheet.tsx`, `studioCatalogLabels.ts`, `StudioCopilotSidebar.tsx`, and `InteractiveRunDeliverableAndHitlPanels.tsx`)
**When** refactored into localized typed dictionaries and clean `<= 300` line helper/data modules keyed by `fr`/`en`
**Then** Gate 1 (`i18n-hardcoded-locale-ast-audit.test.ts`) reports **`0` violations across the entire `apps/web/src/` workspace** (`apps/web` baseline slice reduced to `0`).

**Given** Process Studio v2, VSM detail sheets, and interactive execution/HITL panels rendered in `fr` and `en`
**When** validated with `pnpm turbo run lint typecheck test`
**Then** Gate 2 (`i18n-dictionary-parity-and-jargon-audit.test.ts`), `e2e-testids-sync-audit.test.ts`, and `zero-dead-buttons-and-silent-catches-audit.test.tsx` pass completely with zero regressions.

---

### Story 27.6: Category C Remediation (Part 4) — `@orcia/ui` Design System Components & Primitives via Typed Label Props (`packages/ui` Gate 1 Baseline = 0)

As a Design System Maintainer (`Sally`),
I want every component and primitive in `packages/ui/src/` to receive 100% of its user-facing labels, placeholders, aria-labels, and showcase copy as typed props (with zero hardcoded French/English defaults or inline `locale` ternaries inside `@orcia/ui`),
So that `@orcia/ui` remains strictly presentation-only, framework-isolated, and 100% bilingual across both `fr` and `en`.

**Lot:** 3 — Category C Studio/VSM & `@orcia/ui`. **Dependencies:** `27.5`. **Agent:** `bmad-dev-worker` (`flash`).
**Findings covered:** `ACTION_ITEM-I18N.1` (Lot 3 — `OrciaProductShowcaseSiteView.tsx` 178 hits, `iconRegistry.ts` 73 hits, `AgentGovernanceTypesAndDefaults.ts`, `AgentSixBlocks*`, `Assistant*`, `TemporaryPasswordInvitationModal.tsx`, `RemoteServiceTestBenchAndMcpExposureView.tsx`, etc.).
**CAPs covered:** `CAP-060`, `CAP-090`, `CAP-091`, `CAP-100`, `CAP-200`, `CAP-260`.
**Impacted files:** `packages/ui/src/primitives/**`, `packages/ui/src/components/**`, `packages/ui/src/shell/**`, `packages/ui/src/__tests__/**`, `apps/web/src/i18n/locales/*`, `apps/web/src/routes/showcase.tsx`, `apps/web/src/__tests__/i18n-hardcoded-locale-baseline.json`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/27-6-category-c-orcia-ui-design-system-primitives-typed-label-props-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** every primitive and component in `packages/ui/src/` (including `OrciaProductShowcaseSiteView.tsx`, `AgentGovernanceTypesAndDefaults.ts`, `AgentSixBlocks*`, `Assistant*`, `RgaaModalGuardLabels.ts`, and `iconRegistry.ts` reviewed for true UI labels vs internal icon IDs)
**When** refactored so all user-visible text is injected via typed label props from `apps/web/src/i18n/locales/{fr,en}.ts` (or typed `labels` props in `packages/ui` tests)
**Then** `packages/ui/src/` contains zero hardcoded user-facing French/English strings or `locale === "fr"` ternaries, `packages/ui` preserves zero imports of `@tanstack/react-router` or `@orcia/api-client`, all modified files stay `<= 300` lines, and Gate 1 (`i18n-hardcoded-locale-ast-audit.test.ts`) baseline drops to **`0` for both `apps/web/src/` and `packages/ui/src/`**.

**Given** `@orcia/ui` component tests and `apps/web` consumer routes (including `/showcase`)
**When** executed via `pnpm turbo run lint typecheck test`
**Then** all `packages/ui` and `apps/web` Vitest suites pass cleanly in both `fr` and `en`, and zero dead buttons or broken `data-testid` attributes are introduced.

---

### Story 27.7: Categories B & D Remediation (`577` + `193` Hits) — Bilingual RFC 9457 Backend Error Catalogs (`Accept-Language`), Prompt Localization & Seed Display Localization (Gate 4 Baseline = 0)

As a Bilingual User and Backend Maintainer,
I want every backend RFC 9457 error envelope (`Category B`), LLM prompt/governance template, and user-facing seed/payload text (`Category D`) to localize cleanly via `Accept-Language` / `locale` while maintaining English-only code comments and docstrings,
So that backend API responses work seamlessly in French and English without leaking hardcoded single-language strings.

**Lot:** 4 — Categories B & D Backend. **Dependencies:** `27.1`. **Agent:** `bmad-dev-worker` (`flash`).
**Findings covered:** `ACTION_ITEM-I18N.1` (Lot 4 — Category B `577` hits & Category D `193` hits).
**CAPs covered:** `CAP-001`..`CAP-260` (cross-cutting backend RFC 9457, prompts, and seed localization).
**Impacted files:** `packages/orcia-core/src/orcia_core/*/errors.py`, `packages/orcia-core/src/orcia_core/permissions/{_error_catalog.py,_auth_error_catalog.py,seeds.py}`, `packages/orcia-core/src/orcia_core/orchestration/{assistant_harness.py,assistant_governance.py,assistant_prompt_locales.py,assistant_three_speed_router.py,ai_models_connection.py,governed_mcp_exposure.py,notifications_and_claims.py,pack_builder_processes.py,remote_test_bench.py,studio_and_packs.py,step_executors.py}`, `packages/orcia-core/src/orcia_core/bootstrap/orchestration_seeds.py`, `packages/orcia-core/src/orcia_core/catalog/{cas_resolver.py,seeds.py}`, `packages/orcia-core/src/orcia_core/agents/llm_adapter.py`, `apps/api/src/orcia_api/routers/*.py`, `apps/api/src/orcia_api/schemas/*.py`, `tests/unit/test_i18n_backend_catalog_and_english_dev_audit.py`, `tests/unit/i18n_backend_audit_baseline.json`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/27-7-categories-b-and-d-bilingual-rfc9457-backend-catalogs-prompts-and-seeds-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** all `OrciaDomainError` subclasses, router error handlers, and `detail_override` paths identified in Category B (`577` raw hits)
**When** audited and migrated to bilingual `fr`/`en` entries in the domain error catalogs resolved via `Accept-Language` (`get_localized_error_text`)
**Then** every `error_code` returns an accurate, jargon-free localized `detail` in both French (`Accept-Language: fr`) and English (`Accept-Language: en`) without hardcoded French-only `detail_override` prose, preserving invariant `error_code` and W3C `trace_id` (`RFC 9457` + `0-diff` OpenAPI).

**Given** backend LLM prompts (`assistant_llm_prompts.py`, `assistant_harness.py`, `assistant_governance.py`, `llm_adapter.py`) and user-facing payload/seed strings (`permissions/seeds.py`, `orchestration_seeds.py`, `catalog/seeds.py`, `rag_seeds.py`) identified in Category D (`193` raw hits)
**When** refactored to resolve display titles/prompts from explicit `fr`/`en` locale bundles or English canonical technical identifiers without breaking deterministic replay/Day-0 reset (`pnpm db:reset`)
**Then** zero hardcoded French-only LLM directives remain outside `PROMPT_LOCALES["fr"]`, seed/default outputs respect the active `locale`, Gate 4 (`test_i18n_backend_catalog_and_english_dev_audit.py`) baseline reaches **`0`**, all touched Python files remain `<= 300` lines with English comments/docstrings, `lint-imports` keeps `5/5` contracts, `export_openapi.py --check` returns `0-diff`, and combined Python unit/PG18 coverage stays `>= 90%`.

---

### Story 27.8: Zero-Baseline Deterministic Lock, Bilingual (`fr` & `en`) Playwright E2E Verification, Showcase Sync & Epic 27 Closure

As a Tech Lead and QA Gatekeeper,
I want all 4 deterministic i18n CI baseline files locked strictly to `0` violations, bilingual (`fr` and `en`) Playwright end-to-end verification passing without `ORCIA_E2E_SEED_FIXTURES`, and all documentation/showcase artifacts synchronized,
So that ORCIA ships permanently bilingual in French and English for end users while enforcing English-only development and documentation governance.

**Lot:** 5 — Zero-Baseline Lock & Bilingual E2E Closure. **Dependencies:** `27.2`, `27.5`, `27.6`, `27.7`. **Agent:** `bmad-dev-worker` (`flash`) + mandatory final `bmad-architect-worker` (`pro`) closure gate.
**Findings covered:** `ACTION_ITEM-I18N.1` (full closure), `D1–D4`.
**CAPs covered:** `CAP-001`..`CAP-260`, `CAP-100`.
**Impacted files:** `apps/web/src/__tests__/i18n-hardcoded-locale-baseline.json`, `apps/web/src/__tests__/i18n-hardcoded-locale-ast-audit.test.ts`, `apps/web/src/__tests__/client-error-code-contract-audit.test.ts`, `tests/unit/i18n_backend_audit_baseline.json`, `apps/web/e2e/23-bilingual-fr-en-i18n-and-rfc9457.spec.ts` (new), `docs/product/capabilities.yaml`, `docs/implementation-artifacts/sprint-status.yaml`, `docs/implementation-artifacts/tech-lead-reports/2026-11-20-audit-i18n-chaines-codees-en-dur-tech-lead-report.md`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/27-8-zero-baseline-lock-bilingual-e2e-verification-and-epic-27-closure-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** Stories `27.1`–`27.7` completed
**When** all 4 deterministic CI gates run
**Then** every baseline ratchet file (`i18n-hardcoded-locale-baseline.json`, `client-error-code-contract-audit`, `i18n_backend_audit_baseline.json`) equals **`0`**, zero inline `locale === "fr"` ternaries or hardcoded UI/error strings remain across `apps/web/src`, `packages/ui/src`, `packages/api-client/src`, `apps/api/src`, and `packages/orcia-core`, and Gates 1–4 fail closed on any non-zero violation.

**Given** a live dual-server Playwright E2E stack booted from Day-0 reset (`env -u ORCIA_E2E_SEED_FIXTURES`)
**When** `23-bilingual-fr-en-i18n-and-rfc9457.spec.ts` and the impacted Playwright Desktop E2E specs execute across both **French (`fr`)** and **English (`en`)** user sessions (including account language switching, `F5` cold PG18 persistence, client timeout/error banners, and RFC 9457 API errors)
**Then** all UI views, modals, contextual help panels, Assistant turns, and error banners render cleanly in both `fr` and `en` with zero language leakage, zero jargon, and zero console/API regressions.

**Given** full `AD-17` verification and `bmad-architect-worker` (`pro`) closure review
**When** closing Epic 27
**Then** `ruff check`, `ruff format --check`, `mypy --strict`, `lint-imports` (`5/5`), `lint_spine.py` (`0 findings`), `export_openapi.py --check` (`0-diff`), `detect-secrets-hook`, full `tests/unit` + `tests/security` + `tests/evals` + `tests/contract` (`>= 90%` branch coverage), impacted PG18+Redis integration suites, `pnpm turbo run lint typecheck test`, `scripts/check_implementation_docs.py`, and `pnpm site:sync && pnpm site:check` all pass, `ACTION_ITEM-I18N.1` and `epic-27` become `done`, and GitNexus index is refreshed cleanly.

---
