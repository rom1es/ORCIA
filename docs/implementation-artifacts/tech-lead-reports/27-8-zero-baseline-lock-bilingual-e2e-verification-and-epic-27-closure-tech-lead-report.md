# Story 27.8 — Zero-Baseline Deterministic Lock, Bilingual (`fr` & `en`) Playwright E2E Verification, Showcase Sync & Epic 27 Closure

- **Date**: 2026-11-24
- **Story / Sprint Key**: `27-8-zero-baseline-lock-bilingual-e2e-verification-and-epic-27-closure` (`Epic 27` / Lot 5)
- **Capability(ies)**: `CAP-001`, `CAP-100` (cross-cutting zero-baseline CI lock and bilingual `fr`/`en` E2E verification across `CAP-001`..`CAP-260` — classification: `feature`)
- **Author / Context**: `Amelia` (`bmad-dev-worker` Coding Sub-Agent) — Implements Epic 27 Decisions `D2`, `D3`, and `D4` (Lot 5): permanently locks all four deterministic i18n CI gates to `0` allowed baseline exceptions, delivers live dual-server bilingual (`fr` & `en`) Playwright E2E verification without `ORCIA_E2E_SEED_FIXTURES`, closes the original `2026-11-20` audit report Section 3, and prepares full `AD-17` & `bmad-architect-worker` closure for `Epic 27` (`ACTION_ITEM-I18N.1`).
- **Associated Commits**: `6ce78a9` (`feat(story-27.8): lock i18n CI gates to zero baseline, add bilingual FR/EN E2E suite, and close Epic 27`) on branch `feat/epic-27-bilingual-i18n-and-deterministic-locale-guards` (Architect Closure Remediation applied in working tree)

---

## 1. Needs Analysis & Tech Lead Impact Study (Pre-Implementation)

### 1.1 Context & Problem Statement
- **Problem**: Following Stories `27.1`–`27.7`, both frontend (`apps/web/src/__tests__/i18n-hardcoded-locale-baseline.json`) and backend (`tests/unit/i18n_backend_audit_baseline.json`) ratchet baselines have reached `0` violations across all metrics (`astFiles: {}`, `totalAstViolations: 0`, `totalClientErrorViolations: 0`, `clientErrorBaseline: {}`, `missingErrorCatalogCodes: []`, `totalPromptDirectiveViolations: 0`, `totalNonCatalogFrenchLiterals: 0`, `nonCatalogFrenchFiles: {}`). However, the four CI gate test suites currently check regressions against the baseline map without explicitly asserting that the baseline itself remains permanently locked at `0` (empty maps and zero totals). Furthermore, Epic 27 requires end-to-end runtime proof against the live dual-server stack (`env -u ORCIA_E2E_SEED_FIXTURES`) that ORCIA operates seamlessly in both French (`fr`) and English (`en`), including UI locale toggling persisted in PostgreSQL 18 across cold `F5` reload (`reloadColdFromPg`), client error banners (`ERR_CLIENT_*`), and backend **RFC 9457** `application/problem+json` error localization via `Accept-Language: fr` vs `Accept-Language: en`.
- **Expected vs Current Behavior**:
  - Current: Gate 1, Gate 3, and Gate 4 still allow non-zero baseline entries if someone manually edits the JSON baseline files upward or re-adds entries, and no dedicated functional Playwright E2E spec exercises the full `fr` ↔ `en` switch + cold PG18 persistence + client error banner + bilingual RFC 9457 API envelope flow.
  - Expected: All four deterministic CI gates fail closed on **both** any non-zero baseline configuration and any live violation (`> 0`); `apps/web/e2e/23-bilingual-fr-en-i18n-and-rfc9457.spec.ts` verifies the full bilingual `fr` & `en` end-to-end journey on the Day-0 stack; the original `2026-11-20` audit report records Epic 27 closure in Section 3; and `capabilities.yaml` registers the new E2E spec cleanly.
- **Constraints (`ARCHITECTURE-SPINE.md` / `GEMINI.md`)**:
  - Keep every created or modified source/test file `<= 300` lines (`wc -l`).
  - Maintain `100%` `data-testid` synchronization between `apps/web/e2e/` and `apps/web/src` / `packages/ui/src` (`e2e-testids-sync-audit.test.ts`).
  - Keep all comments, docstrings, and documentation strictly in **English** while keeping the web application and RFC 9457 API surfaces 100% bilingual `fr`/`en`.
  - Never set `ORCIA_E2E_SEED_FIXTURES`; boot cleanly from Day-0 reset (`resetDay0()`) and use `@orcia/api-client` typed request helpers (`typedApiRequest.ts`).

### 1.2 Exploration, GitNexus Impact Analysis, Refactoring & Technical Debt
- **GitNexus Impact Analysis (`repo: "/home/romain/Documents/Projects/ORCIA"`)**:
  - `gitnexus_query("i18n hardcoded locale baseline audit and client error codes")`: confirmed gate boundaries in `tests/unit/test_i18n_backend_catalog_and_english_dev_audit.py`, `apps/web/src/lib/clientErrorCodes.ts`, `apps/web/src/lib/formatRfc9457ErrorToBanner.ts`, and `packages/orcia-core/src/orcia_core/kernel/errors.py`.
  - `gitnexus_context("resolveClientErrorMessage")`: `epistemic: exact`, callers `formatRfc9457ErrorToBanner` and `resolveLocalizedClientError` in `apps/web/src/lib/formatRfc9457ErrorToBanner.ts`, propagating localized `ClientErrorCode` strings (such as `ERR_CLIENT_FEDERATED_SEARCH` rendered in `cmdk-speed2-error-banner`).
  - `gitnexus_impact("resolve_locale", direction: "upstream")`: confirmed via text search across `apps/api/src/orcia_api/middleware/trace_and_error.py`, `apps/api/src/orcia_api/routers/`, and `packages/orcia-core/src/orcia_core/kernel/_error_catalog.py`; `trace_and_error.py` resolves `Accept-Language` dynamically per request into RFC 9457 `application/problem+json` responses while preserving invariant `error_code` and `trace_id`.
- **Exploration & Key Metrics**:
  - `apps/web/src/__tests__/i18n-hardcoded-locale-baseline.json`: already `totalAstViolations: 0`, `astFiles: {}`, `totalClientErrorViolations: 0`, `clientErrorBaseline: {}`.
  - `tests/unit/i18n_backend_audit_baseline.json`: already `missingErrorCatalogCodes: []`, `totalPromptDirectiveViolations: 0`, `promptDirectiveFiles: {}`, `totalNonCatalogFrenchLiterals: 0`, `nonCatalogFrenchFiles: {}`.
  - `apps/web/src/components/useSidebarAccountSettings.ts` + `packages/ui/src/primitives/UserSettingsGeneralTab.tsx`: toggling `settings-locale-en` / `settings-locale-fr` calls `PUT /api/v1/users/me/preferences` (persisted in PG18 `user_preferences`) and immediately updates `I18nProvider` (`onLocaleChange`), rehydrating automatically on cold `F5` reload (`reloadColdFromPg`).
  - `apps/web/src/components/ShellFederatedSearchModal.tsx` (`cmdk-speed2-error-banner`): triggers `resolveLocalizedClientError("ERR_CLIENT_FEDERATED_SEARCH", locale, { detail })` cleanly when `GET /api/v1/search*` fails at the network layer.
  - Backend RFC 9457 endpoints (`GET /api/v1/sources/inspect-lines?uri=../pyproject.toml&start_line=1&end_line=10` returning `422 ERR_VALIDATION_FAILED`, and `PATCH /api/v1/org-units/01930000-0000-7000-8000-000000000999` returning `404 ERR_ORG_UNIT_NOT_FOUND` with `ERR_ORG_UNIT_NOT_FOUND_DETAIL`) localize `title` and `detail` cleanly via `Accept-Language: fr` vs `Accept-Language: en`.
- **Refactoring Opportunities & Emerging Technical Debt Mitigation**:
  - Extract reusable E2E bilingual verification helpers into `apps/web/e2e/helpers/bilingualI18nHelpers.ts` (`<= 300` lines) so `apps/web/e2e/23-bilingual-fr-en-i18n-and-rfc9457.spec.ts` stays concise (`<= 300` lines) and readable.
  - Lock Gate 1–4 assertions cleanly without adding extra complexity or duplicating AST helper logic.

---

## 2. Implementation Plan

### 2.1 Data Schema & Alembic Migrations
- None. No database table or Alembic revision changes are required.

### 2.2 Hexagonal Core, Orchestration & Workers (`packages/orcia-core/`)
- No production code modifications needed; `Story 27.7` completed backend RFC 9457 catalogs, prompt locale bundles, and seed localization with Gate 4 baseline at `0`.

### 2.3 Backend API, Security & Contracts (`apps/api/`, `packages/api-client/`)
- No API schema or endpoint changes required; existing `GET /api/v1/users/me/preferences`, `PUT /api/v1/users/me/preferences`, `GET /api/v1/sources/inspect-lines`, and `PATCH /api/v1/org-units/{id}` endpoints remain `0-diff` OpenAPI 3.1 compliant.

### 2.4 User Interface, Governance & Documentation (`apps/web/`, `docs/`)
- **Permanent Zero-Baseline Lock on Deterministic Gates 1–4**:
  - `apps/web/src/__tests__/i18n-hardcoded-locale-ast-audit.test.ts`: assert `BASELINE.totalAstViolations === 0` and `Object.keys(BASELINE.astFiles).length === 0`, and reject **any** file with `violations.length > 0` without honoring baseline exemptions.
  - `apps/web/src/__tests__/i18n-dictionary-parity-and-jargon-audit.test.ts`: confirm strict `fr` ↔ `en` parity, placeholder parity, non-empty values, and zero UX Rule 3.1 jargon (plus keep `<= 300` lines and English-only comments).
  - `apps/web/src/__tests__/client-error-code-contract-audit.test.ts`: assert `BASELINE.totalClientErrorViolations === 0` and `Object.keys(BASELINE.clientErrorBaseline).length === 0`, and reject **any** file with `violations.length > 0` without honoring baseline exemptions.
  - `tests/unit/test_i18n_backend_catalog_and_english_dev_audit.py`: assert `missingErrorCatalogCodes == []`, `totalPromptDirectiveViolations == 0`, `promptDirectiveFiles == {}`, `totalNonCatalogFrenchLiterals == 0`, and `nonCatalogFrenchFiles == {}`, and fail closed on any missing catalog code, prompt directive violation, or non-catalog French literal (`> 0`).
- **Bilingual (`fr` & `en`) Playwright E2E Spec (`<= 300` lines)**:
  - `apps/web/e2e/helpers/bilingualI18nHelpers.ts` (`<= 300` L): shared E2E helpers for verifying `fr`/`en` cockpit shell navigation, contextual help panel labels, `UserSettingsGeneralTab` locale switch (`settings-locale-en` / `settings-locale-fr`), `⌘K` client error banner localization, and RFC 9457 `Accept-Language: fr` vs `en` HTTP envelope assertions.
  - `apps/web/e2e/23-bilingual-fr-en-i18n-and-rfc9457.spec.ts` (`<= 300` L, tagged `/** @uj UJ-13, UJ-16 | @cap CAP-001, CAP-100 */`): exercises Day-0 French rendering, live `fr` → `en` → `fr` switching with cold `F5` (`reloadColdFromPg`) PG18 persistence, localized `fr`/`en` client error banners (`ERR_CLIENT_FEDERATED_SEARCH` and `/login` RFC 9457 banner), and live backend RFC 9457 `application/problem+json` localization (`Accept-Language: fr` vs `Accept-Language: en`).
- **Traceability & Audit Closure**:
  - Register `apps/web/e2e/23-bilingual-fr-en-i18n-and-rfc9457.spec.ts` under `CAP-100` (and `CAP-001`) in `docs/product/capabilities.yaml`.
  - Update Section 3 of `docs/implementation-artifacts/tech-lead-reports/2026-11-20-audit-i18n-chaines-codees-en-dur-tech-lead-report.md` in English summarizing full Epic 27 (`Stories 27.1`–`27.8`) remediation closure (`A: 71 -> 0`, `B: 577 -> 0`, `C: 2,816 -> 0`, `D: 193 -> 0`, `E` governed via English-only dev policy, Gates 1–4 permanently locked at `0`).

### 2.5 Test Pyramid Impact Analysis (`AD-17` — Layers 1 to 5 + Security, Mandatory)
- **Layer 1a (`tests/unit/`)**: `test_i18n_backend_catalog_and_english_dev_audit.py`, `test_capabilities_registry.py`, `test_uj_e2e_coverage_gate.py`, plus full `tests/unit` & `>= 90%` branch coverage run by Testing Verifier.
- **Layer 1b (`Vitest`)**: `i18n-hardcoded-locale-ast-audit.test.ts`, `i18n-dictionary-parity-and-jargon-audit.test.ts`, `client-error-code-contract-audit.test.ts`, `e2e-testids-sync-audit.test.ts`, `zero-dead-buttons-and-silent-catches-audit.test.tsx`, plus full `pnpm turbo run lint typecheck test` run by Testing Verifier.
- **Layer 2 / Layer 3 / Layer 4 / Security**: Full `tests/security`, `tests/evals`, `tests/contract`, impacted PG18+Redis integration suites, `ruff`, `mypy --strict`, `lint-imports`, `lint_spine.py`, `export_openapi.py --check`, `detect-secrets-hook` run by Testing Verifier.
- **Layer 5 (Dual-Server Playwright E2E `env -u ORCIA_E2E_SEED_FIXTURES`)**: `apps/web/e2e/23-bilingual-fr-en-i18n-and-rfc9457.spec.ts` and impacted specs executed by Testing Verifier.

---

## 3. Summary of Changes & Results (Post-Implementation)

> **Verified by Independent Testing Sub-Agent (`bmad-dev-worker`)** — All 5 `AD-17` testing layers, permanent zero-baseline Locks across Gates 1–4 (`apps/web/src`, `packages/ui/src`, `packages/orcia-core/src`, `packages/orcia-connectors/src`, `apps/api/src`, `apps/worker/src`), bilingual FR/EN Playwright Desktop E2E verification (`env -u ORCIA_E2E_SEED_FIXTURES`), `docs/product/capabilities.yaml`, and Showcase sync passed with zero regressions.

### 3.1 Summary of Modified & Created Files

| Artifact / File | Role / Scope | Lines |
| :--- | :--- | :---: |
| `apps/web/src/__tests__/i18n-hardcoded-locale-ast-audit.test.ts` | Gate 1: permanent `totalAstViolations === 0` & `astFiles: {}` lock (fail-closed) | 81 |
| `apps/web/src/__tests__/i18n-dictionary-parity-and-jargon-audit.test.ts` | Gate 2: recursive FR/EN key & placeholder parity + UX Rule 3.1 zero-jargon check | 130 |
| `apps/web/src/__tests__/client-error-code-contract-audit.test.ts` | Gate 3: permanent `totalClientErrorViolations === 0` & `clientErrorBaseline: {}` lock | 80 |
| `tests/unit/test_i18n_backend_catalog_and_english_dev_audit.py` | Gate 4: permanent `0` backend French literals / prompt directives across `orcia-core`, `orcia-connectors`, `orcia-api`, `orcia-worker` + English-only dev diff audit | 288 |
| `packages/orcia-connectors/src/orcia_connectors/_error_catalog.py` & `apps/api/src/orcia_api/errors/registry.py` | 14 bilingual FR/EN `ERR_SURGICAL_*` catalog entries + API error registry wiring | 158 / 176 |
| `packages/orcia-connectors/src/orcia_connectors/*` (`_connectors_locales.py`, `_pack_builder_locales.py`, `_sdlc_template_locales.py`, `_surgical_parsers.py`, split modules) | Localized connector messages/errors & `<= 299` L modular splits | `<= 299` |
| `tests/unit/connectors/test_story_27_8_connectors_i18n.py` | Unit tests for `orcia-connectors` bilingual catalogs & locale helpers | 158 |
| `tests/unit/test_e2e_sql_coverage_audit.py` | Registered `23-bilingual-fr-en-i18n-and-rfc9457.spec.ts` (`len(specs) == 26`, `total_blocks == 59`) | 294 |
| `apps/web/e2e/23-bilingual-fr-en-i18n-and-rfc9457.spec.ts` | Dual-server bilingual FR/EN E2E spec (`@uj UJ-13, UJ-16 \| @cap CAP-001, CAP-100`) with direct PG18 `users` & `user_preferences` assertions | 130 |
| `apps/web/e2e/helpers/bilingualI18nHelpers.ts` | Shared E2E helpers (shell/help/models locale checks, `PATCH /users/me/preferences` + cold F5 reload, `⌘K` client error banner, RFC 9457 `Accept-Language` probes) | 277 |
| `docs/product/capabilities.yaml` | Registered `apps/web/e2e/23-bilingual-fr-en-i18n-and-rfc9457.spec.ts` under `CAP-001` & `CAP-100` | — |
| `docs/implementation-artifacts/tech-lead-reports/2026-11-20-audit-i18n-chaines-codees-en-dur-tech-lead-report.md` | Completed Section 3 closing Epic 27 (`Stories 27.1`–`27.8`) remediation | — |
| `docs/implementation-artifacts/sprint-status.yaml` & `tech-lead-reports/README.md` | Closed `27-8-...: done`, `epic-27: done`, `ACTION_ITEM-I18N.1: done` | — |

### 3.2 Quantitative Metrics & Branch Coverage

- **Line-count compliance (`wc -l <= 300`)**: `100%` of hand-written Story `27.8` Python & TypeScript source/test files are `<= 299` lines (`max: 299` L in `surgical.py`).
- **Scoped Branch Coverage (`coverage run --branch`, `--fail-under=90`)**: **`96%`** across Epic 27 error/locale/registry modules (`194 Stmts, 4 Miss, 26 Branch, 2 BrPart` across `93` targeted unit tests in `test_i18n_backend_catalog_and_english_dev_audit.py`, `tests/unit/connectors/`, `test_story_3_2e_sdlc_pack_and_connectors.py`, `test_story_27_7_*`, `test_capabilities_registry.py`, `test_uj_e2e_coverage_gate.py`, `test_site_catalog_sync.py`, `test_e2e_sql_coverage_audit.py`; `.coverage*` cleaned).
- **Zero-Baseline Gates**:
  - Gate 1 (`apps/web/src/__tests__/i18n-hardcoded-locale-baseline.json`): `totalAstViolations: 0`, `astFiles: {}`.
  - Gate 2 (`i18n-dictionary-parity-and-jargon-audit.test.ts`): `0` parity/placeholder/jargon violations.
  - Gate 3 (`i18n-hardcoded-locale-baseline.json`): `totalClientErrorViolations: 0`, `clientErrorBaseline: {}`.
  - Gate 4 (`tests/unit/i18n_backend_audit_baseline.json`): `missingErrorCatalogCodes: []`, `totalPromptDirectiveViolations: 0`, `promptDirectiveFiles: {}`, `totalNonCatalogFrenchLiterals: 0`, `nonCatalogFrenchFiles: {}` (enforced across `orcia-core`, `orcia-connectors`, `orcia-api`, `orcia-worker`).

### 3.3 AD-17 Verification Matrix (5 Layers + Security & Architectural Gates)

| Gate / Layer | Command & Scope | Result |
| :--- | :--- | :--- |
| **Static & Type Safety** | `.venv/bin/ruff check .`, `.venv/bin/ruff format --check .` (`1,705` files), `.venv/bin/mypy --strict` (`845` files) | **PASS** (`0` issues) |
| **Boundaries & Spine** | `.venv/bin/lint-imports` (`888` files, `6,371` deps), `lint_spine.py`, `export_openapi.py --check`, `detect-secrets-hook` | **PASS** (`5/5` contracts kept, `0` spine findings, `0-diff` OpenAPI, `0` secrets) |
| **Layer 1a (`tests/unit`)** | `.venv/bin/pytest tests/unit --no-cov -q` | **PASS** (`1,091 passed`) |
| **Layer 1b (`pnpm turbo`)** | `pnpm turbo run lint typecheck test` (`@orcia/api-client`, `@orcia/ui`, `@orcia/web`) | **PASS** (`9/9` tasks; `20 + 139 + 290 = 449` Vitest tests) |
| **Layer 2 (PG18 + Redis)** | `test_composition_root_zero_ram_silo_postgres18.py`, `test_contextual_help_and_accostage_postgres18.py`, `api/test_story_17_5_ai_models_hub_postgres18.py`, `api/test_story_25_5_assistant_chat_only_and_rag_guard_postgres18.py` (`--no-cov`) | **PASS** (`6 passed`, real `create_app()` + `testcontainers`) |
| **Layer 3/4 & Security** | `.venv/bin/pytest tests/security tests/evals tests/contract --no-cov -q` | **PASS** (`180 passed`) |
| **Layer 5 (Playwright E2E)** | `env -u ORCIA_E2E_SEED_FIXTURES ORCIA_E2E_CAMPAIGN_DIR=/tmp/orcia-e2e-27-8 pnpm --filter @orcia/web exec playwright test --project=desktop-cockpit` (`23-bilingual-fr-en-i18n-and-rfc9457.spec.ts`, `00-stack-smoke.spec.ts`, `01-day0-boot-and-f5-persistence.spec.ts`) | **PASS** (`8 passed (1.3m)`, `0` skipped, `0` failed; `e2e-campaign-epic-22/` untouched) |
| **Docs & Showcase Sync** | `scripts/check_implementation_docs.py` & `pnpm site:sync && pnpm site:check` | **PASS** (`0` findings) |

### 3.4 GitNexus Impact Verification (`gitnexus_detect_changes`)
- `npx gitnexus analyze --index-only .`: `45,227 nodes | 77,810 edges | 752 clusters | 1,540 flows`.
- `gitnexus_detect_changes({repo: "/home/romain/Documents/Projects/ORCIA", scope: "all"})`: `changed_count: 33`, `affected_count: 0`, `changed_files: 29`, `risk_level: "low"`.

### 3.5 Architect Closure Remediation (`2026-11-24`)
Following the `bmad-architect-worker` closure review (`VALIDATE: CHANGES REQUIRED`), all 5 blocking findings and 4 hardening/hygiene items were remediated:
1. **`packages/ui/src/` Zero Hardcoded FR/EN Defaults**: Removed `DEFAULT_RGAA_MODAL_LABELS_FR/EN`, `resolveRgaaModalGuardLabels`, `DEFAULT_DISABLED_REASON`, `DEFAULT_ACTIVITY_LOG_PROVENANCE_LABELS_FR`, and all parameter/nullish/switch FR/EN defaults across all `@orcia/ui` primitives/components (moving RGAA modal labels to `apps/web/src/i18n/locales/rgaa_modal_labels.ts`, updating every caller in `apps/web/src/` and `packages/ui/src/__tests__/`, splitting `UpstreamChallengeRewindModal.tsx`, `CommandPaletteModal.tsx`, `FourZoneDirectionCShell.tsx`, `RadixDesignSystemPrimitives.tsx`, `OrciaKnownUserCombobox.tsx`, `ActivityLogExplorerView.tsx`, `WorkflowTriggersModal.tsx`, and `CatalogExplorerPanel.tsx` `<= 300` lines, and preserving original `CatalogExplorerPanel` testids).
2. **Untranslated French in `enDictionary` Fixed & Dictionary Split**: Translated `EPIC18_SOURCES_LABELS_EN.codegraph.leadRequiredTooltip` and `switchNotice` into natural English, split `epic18_sources_labels.ts` into `epic18_sources_labels.ts` + `_fr.ts` + `_en.ts` (`<= 300` L each), cleaned French entries from `SHELL_NOTIFICATIONS_LABELS_EN.redundantAllSpacesLabels`, and extracted `useManagedAgentsAndSkills.ts` / `IamAccountModal.tsx` / `CreateOrgUnitModal.tsx` (`<= 300` L each) with typed bilingual keys in `feature_admin_catalog_settings_labels*.ts`.
3. **Gate 1 & Gate 2 Hardening (`D3`)**: Extended Gate 1 (`_i18nAuditRules.ts`, `_i18nAuditHelpers.ts`, `i18n-hardcoded-locale-ast-audit.test.ts`) to flag `PARAM_DEFAULT`, `FALLBACK_LITERAL` (`??`/`||`), `SWITCH_FALLBACK`, and `UI_DEFAULT_CONST` across `apps/web/src/` and `packages/ui/src/`, and extended Gate 2 (`i18n-dictionary-parity-and-jargon-audit.test.ts`) with deterministic FR-in-EN detection across `enDictionary` and `SHOWCASE_ARCHITECTURE_LABELS_BY_LOCALE` — both gates pass with `0` violations.
4. **Backend `orcia-connectors` & Gate 4 Fail-Closed Hardening**: Updated `packages/orcia-connectors/src/orcia_connectors/surgical.py` and `_connectors_locales.py` (`search_formatted_badge`) to resolve `locale` dynamically via `resolve_locale(locale)` with bilingual FR/EN tests in `test_story_27_8_connectors_i18n.py`, and made `base_ref is None` fail closed (`assert base_ref is not None`) in `tests/unit/test_i18n_backend_catalog_and_english_dev_audit.py`.
5. **Hygiene & Governance**: Verified all created/modified non-barrel/non-generated production files vs `main` are `<= 300` lines (`wc -l`), translated `docs/implementation-artifacts/tech-lead-reports/README.md` (`L1-35`) into English, backfilled real branch commit hashes across `27-1`..`27-8` reports, updated `27-6` §3, and updated `verified_at: "2026-11-24"` on `CAP-001` and `CAP-100` in `docs/product/capabilities.yaml`.
6. **Post-Remediation Independent Testing Verification (`2026-11-24`)**:
   - **Line counts**: `687` created/modified production files vs `main` + untracked checked — `0` exceeding `300` lines; Story `27.8` / remediation test files all `<= 289` lines (`_i18nAuditRules.ts`: `121`, `_i18nAuditHelpers.ts`: `214`, `i18n-hardcoded-locale-ast-audit.test.ts`: `93`, `i18n-dictionary-parity-and-jargon-audit.test.ts`: `129`, `test_i18n_backend_catalog_and_english_dev_audit.py`: `289`, `test_story_27_8_connectors_i18n.py`: `175`, `23-bilingual-fr-en-i18n-and-rfc9457.spec.ts`: `130`, `bilingualI18nHelpers.ts`: `276`).
   - **Static & Boundaries**: `ruff check .` (`0` issues), `ruff format --check .` (`1,705` files), `mypy --strict` (`845` source files, `0` issues), `lint-imports` (`888` files, `6,371` deps, `5/5` contracts kept), `lint_spine.py` (`0` findings), `export_openapi.py --check` (`0-diff`), `detect-secrets-hook` (`0` findings).
   - **Python Suites & Scoped Branch Coverage**: `tests/unit --no-cov` (`1,091 passed`), `tests/security tests/evals tests/contract --no-cov` (`180 passed`), `coverage run --branch` over `tests/unit/connectors/` + `test_i18n_backend_catalog_and_english_dev_audit.py` on `_connectors_locales.py`, `_error_catalog.py`, `_surgical_fs_helpers.py`, and `_surgical_observations.py` (`90%` total: `119 Stmts, 7 Miss, 24 Branch, 3 BrPart`; `.coverage*` cleaned).
   - **Impacted PG18 + Redis Integration (`--no-cov`)**: `6 passed` (`test_composition_root_zero_ram_silo_postgres18.py`, `test_contextual_help_and_accostage_postgres18.py`, `api/test_story_17_5_ai_models_hub_postgres18.py`, `api/test_story_25_5_assistant_chat_only_and_rag_guard_postgres18.py`).
   - **TypeScript Monorepo (`pnpm turbo run lint typecheck test`)**: `9/9` tasks passed (`@orcia/api-client`: `3` files / `20` tests; `@orcia/ui`: `35` files / `139` tests; `@orcia/web`: `75` files / `290` tests).
   - **Playwright Desktop E2E (`env -u ORCIA_E2E_SEED_FIXTURES`, `ORCIA_E2E_CAMPAIGN_DIR=/tmp/orcia-e2e-27-8`)**: `8 passed (1.3m)` across `23-bilingual-fr-en-i18n-and-rfc9457.spec.ts`, `00-stack-smoke.spec.ts`, and `01-day0-boot-and-f5-persistence.spec.ts`; `docs/implementation-artifacts/e2e-campaign-epic-22/` untouched.
   - **Docs & Showcase**: `scripts/check_implementation_docs.py` (`230` reports compliant) and `pnpm site:sync && pnpm site:check` (`230` reports, `28` routes, `131` UI primitives, `66/66` live capabilities, `63/63` E2E covered, `20/20` UJs).
