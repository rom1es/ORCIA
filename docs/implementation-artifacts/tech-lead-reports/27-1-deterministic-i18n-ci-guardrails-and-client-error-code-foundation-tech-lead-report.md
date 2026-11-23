# Story 27.1 — Deterministic i18n CI Guardrails & Client Error Code Foundation

- **Date**: 2026-11-23
- **Story / Sprint Key**: `27-1-deterministic-i18n-ci-guardrails-and-client-error-code-foundation` (`Epic 27` / Lot 0)
- **Capability(ies)**: `CAP-100` (existing transverse UI/CI quality guardrails — adding deterministic i18n & English-dev CI gates and shared `ClientErrorCode` foundation) — classification: `hygiene`
- **Author / Context**: `bmad-dev-worker` (`Amelia`) — Implements `ACTION_ITEM-I18N.1` Lot 0 and `D1–D4` from `docs/implementation-artifacts/epic-27-decisions-grill-2026-11-23.md`, aligned with the `2026-11-20` audit (`3,809` raw heuristic hits across `461` files: `A=71`, `B=577`, `C=2,816`, `D=193`, `E=152`).
- **Associated Commits**: Pending Testing Sub-Agent verification & commit on `feat/epic-27-bilingual-i18n-and-deterministic-locale-guards`

---

## 1. Needs Analysis & Tech Lead Impact Study (Pre-Implementation)

### 1.1 Context & Problem Statement
- **Problem**: Prior to Epic 27, ORCIA lacked automated deterministic CI guardrails preventing hardcoded French/English UI strings, inline `locale === "fr"` ternaries, missing FR↔EN dictionary keys/placeholders, hardcoded client-side error messages in API bridges/stores, missing `Accept-Language` backend error translations, hardcoded single-language LLM prompt directives, and non-English code comments/docstrings on new changes.
- **Expected Behavior**:
  1. Provide a shared, typed `ClientErrorCode` foundation (`apps/web/src/lib/clientErrorCodes.ts`) and symmetric `fr`/`en` `clientErrors` dictionary entries so client-only failures (timeout, network error, abort, SSE disconnect, invalid payload, unknown error) resolve cleanly in both French and English with `{seconds}` / `{detail}` interpolation and safe unknown-code fallback.
  2. Install 4 deterministic CI gates (Layer 1b TypeScript/Vitest Gates 1–3 and Layer 1a Python/pytest Gate 4) backed by exact measured ratchet baselines (`i18n-hardcoded-locale-baseline.json` and `i18n_backend_audit_baseline.json`) so regressions fail immediately while legacy occurrences are driven down to `0` across Stories `27.2`–`27.8`.
- **Architecture & Governance Constraints (`ARCHITECTURE-SPINE.md`, `AGENTS.md`, `D2–D3`)**:
  - Every created or modified source file MUST remain `<= 300` lines (`wc -l`).
  - Zero raw hex colors, zero UX Rule 3.1 internal plumbing jargon (`DBOS`, `PostgreSQL 18`, `Outbox`, `RFC 9457`, `READ_ONLY_OBSERVER`, etc.) in user-facing dictionaries, and zero changes to `packages/ui` isolation (`@orcia/ui` remains decoupled from `apps/web` stores/routing).
  - English-only code comments, docstrings, and report prose; 100% bilingual `fr`/`en` product copy.

### 1.2 Exploration, GitNexus Impact Analysis, Refactoring & Technical Debt
- **GitNexus Impact Analysis (`repo: "/home/romain/Documents/Projects/ORCIA"`)**:
  - `gitnexus_query("i18n dictionary locale frDictionary enDictionary")` identified `frDictionary` (`apps/web/src/i18n/locales/fr.ts`), `enDictionary` (`apps/web/src/i18n/locales/en.ts`), `_assistant_turn_locale_messages.py`, and `test_assistant_locale_and_tool_loop_i18n.py` (index 1 commit behind HEAD on branch creation; full re-index deferred to Testing Sub-Agent closure gate).
  - `gitnexus_impact({target: "frDictionary", direction: "upstream"})` returned `risk: UNKNOWN` (`impactedCount: 0` because module-scope constants accessed via property reads are not call-graph edges). Per `AGENTS.md` GitNexus protocol, text search confirmed **14** active consumers across `apps/web/src/i18n/index.tsx`, `ShellSidebarAccountControl.tsx`, `ShellUserSettingsModal.tsx`, and 11 test files under `apps/web/src/__tests__/`.
  - `gitnexus_impact({target: "OrciaDomainError", direction: "upstream", summaryOnly: true})` returned `risk: CRITICAL` (`impactedCount: 125` — `110` direct depth-1, `15` depth-2 across `Kernel` and domain error classes). Story `27.1` only **audits** `OrciaDomainError` subclasses and `ERROR_CATALOG` read-only via `apps/api/src/orcia_api/errors/registry.py` without altering `OrciaDomainError` itself.
- **Line-Count & Structural Observations**:
  - `apps/web/src/i18n/locales/fr.ts` and `apps/web/src/i18n/locales/en.ts` are each currently **355 lines** (`> 300` L). Modifying them directly to add `clientErrors` would violate the `<= 300`-line limit.
  - `apps/web/src/i18n/types.ts` (94 lines) defines `TranslationDictionary` and composes sub-dictionary interfaces cleanly.
  - `packages/api-client/src/sseAndQueryHelpers.ts` (124 lines) defines `OrciaProblemError` and `parseProblemError`.
  - Existing audit tests (`anti-jargon-and-secrets-ui-audit.test.ts`, `no-direct-fetch-or-eventsource-audit.test.ts`, `test_codebase_architectural_anti_patterns_audit.py`) establish the TypeScript AST (`typescript.createSourceFile`) and Python AST (`ast.parse`) patterns to mirror.
- **Refactoring Opportunities & Emerging Technical Debt Mitigation**:
  - **Pre-edit Step 0 Refactoring**: Split `fr.ts` and `en.ts` (currently 355 lines each) by extracting their inline `shell`/`humanAnchor`/`arbitrationTieBreak`/`modulePages` and domain sections (`workspaceTopology`/`catalogExplorer`/`permissionBroker`/`bootstrapOnboarding`/`ontologyExplorer`) into dedicated `<= 200`-line sub-dictionaries (`core_shell_labels_{fr,en}.ts` and `core_domain_labels_{fr,en}.ts`), plus `client_errors_labels.ts` (`fr` + `en` symmetric definitions). This drops `fr.ts` and `en.ts` below ~60 lines while preserving 100% export compatibility for `frDictionary` and `enDictionary`.
  - No additional Story `N.Ma` needed; Lot 1 (`27.2`) through Lot 5 (`27.8`) already track the staged remediation down to `0` baseline.

---

## 2. Implementation Plan

### 2.1 Data Schema & Alembic Migrations (`infra/migrations/versions/...`)
- None required: Story `27.1` introduces frontend client error codes, bilingual dictionary entries, and deterministic CI test gates without schema changes.

### 2.2 Hexagonal Core, Orchestration & Workers (`packages/orcia-core/`, `apps/worker/`)
- Read-only inspection in Gate 4 (`tests/unit/test_i18n_backend_catalog_and_english_dev_audit.py` + `tests/unit/i18n_backend_audit_baseline.json`):
  - Import `orcia_api.errors.registry` (`DOMAIN_ERROR_CLASSES`, `ERROR_CATALOG`) and assert every registered `OrciaDomainError` and `ERROR_CATALOG` key defines non-empty `"fr"` and `"en"` `LocalizedErrorCopy` (`title` and `detail`), plus verify `resolve_locale("fr-FR") == "fr"`, `resolve_locale("en-US,fr;q=0.8") == "en"`, and `get_localized_error_text(...)` returns distinct non-empty localized responses.
  - AST/line scan across `packages/orcia-core/src/`, `apps/api/src/`, and `apps/worker/src/` for hardcoded single-language LLM prompt directives outside `assistant_prompt_locales.py` (`PROMPT_LOCALES`), with exact per-file ratchet baseline in `i18n_backend_audit_baseline.json` (and verification of server fallback prose counts tracked for Story `27.7`).
  - `git diff main...HEAD` checker verifying that newly added (`+`) Python/TypeScript comment and docstring lines outside localized resource files (`i18n/locales/`, `_error_catalog*`, `assistant_prompt_locales.py`, `_assistant_turn_locale_messages.py`, `docs/`, `tech-lead-reports/`, historical baselines) are written in English (no French diacritics or French comment/docstring stop-words).

### 2.3 Backend API, Security & Contracts (`apps/api/`, `packages/api-client/`)
- No API routes or Pydantic schemas modified (`0-diff` OpenAPI 3.1 preserved).

### 2.4 User Interface & Experience (`apps/web/`, `packages/ui/`)
- **`apps/web/src/lib/clientErrorCodes.ts`** (`<= 300` L):
  - Define `CLIENT_ERROR_CODES` and `ClientErrorCode` union (`ERR_CLIENT_TIMEOUT`, `ERR_CLIENT_NETWORK`, `ERR_CLIENT_ABORTED`, `ERR_CLIENT_SSE_DISCONNECTED`, `ERR_CLIENT_INVALID_PAYLOAD`, `ERR_CLIENT_UNKNOWN`).
  - Define `ClientErrorParams` (`seconds?: number`, `detail?: string`), `ClientErrorLabels` (`Record<ClientErrorCode, string>`), and `ClientErrorPayload` (`{ readonly code: ClientErrorCode; readonly params?: ClientErrorParams }`).
  - Export `createClientErrorPayload(code, params?)`, `isClientErrorPayload(value)`, `isClientErrorCode(value)`, and `resolveClientErrorMessage(code, labels, params?)` with safe `{seconds}` / `{detail}` placeholder interpolation and fallback to `labels.ERR_CLIENT_UNKNOWN` (or generic non-jargon fallback) when an unknown code is passed at runtime.
- **Bilingual Dictionaries (`apps/web/src/i18n/`)**:
  - Create `apps/web/src/i18n/locales/client_errors_labels.ts` (`CLIENT_ERRORS_FR_LABELS` and `CLIENT_ERRORS_EN_LABELS`, compliant with UX Rule 3.1 zero-jargon).
  - Refactor `apps/web/src/i18n/locales/fr.ts` and `en.ts` into `core_shell_labels_{fr,en}.ts` + `core_domain_labels_{fr,en}.ts` so every dictionary file is `<= 200` lines, and expose `clientErrors: ClientErrorLabels` on `TranslationDictionary` (`apps/web/src/i18n/types.ts`).
- **Modular Deterministic Gate Helpers & Test Suites (`apps/web/src/__tests__/`)**:
  - Keep every test and helper file `<= 300` lines (split AST walking/scanning helpers into `_i18nAuditHelpers.ts` if needed).
  - **Gate 1 (`i18n-hardcoded-locale-ast-audit.test.ts` + `i18n-hardcoded-locale-baseline.json`)**: TypeScript AST (`typescript.createSourceFile`) across `apps/web/src/` and `packages/ui/src/` (excluding `apps/web/src/i18n/locales/`, `generated/`, `__tests__/`, `*.test.*`, `*.spec.*`), detecting inline locale conditionals (`locale === "fr"`, `locale === "en"`, `locale !== "fr"`, `isFr`, `lang === "fr"`) and hardcoded JSX text / JSX attributes (`title`, `placeholder`, `aria-label`, `alt`, `label`, `description`, `emptyMessage`, `helperText`, `submitLabel`, `cancelLabel`, `closeLabel`, `emptyTitle`, `emptyDescription`), excluding explicit `Intl.*` formatting and technical-marker annotations (`// i18n-non-user-facing`). Freeze exact measured per-file counts in `i18n-hardcoded-locale-baseline.json`.
  - **Gate 2 (`i18n-dictionary-parity-and-jargon-audit.test.ts`)**: Recursively verify FR↔EN key-tree parity, `{param}` interpolation placeholder parity, non-empty trimmed values, and zero UX Rule 3.1 forbidden internal jargon tokens across `frDictionary` and `enDictionary`. Fix any existing FR↔EN mismatch immediately so Gate 2 passes with `0` violations.
  - **Gate 3 (`client-error-code-contract-audit.test.ts`)**: Scan `apps/web/src/` (`*ApiBridge.ts`, `*Store.ts*`, `*Controller.ts`, `formatRfc9457ErrorToBanner.ts`, `wizards.tsx`, `WorkspaceSourcesRagTab.tsx`, etc.) and `packages/api-client/src/` (excluding `generated/`, `__tests__/`) for hardcoded user-facing error strings / `locale === "fr"` error ternaries, backed by an exact measured `clientErrorBaseline` section in `i18n-hardcoded-locale-baseline.json`.

### 2.5 Test Pyramid Impact Analysis (`AD-17` — Layers 1 to 5 + Security, Mandatory)
- **Layer 1a (`tests/unit/`)**: `tests/unit/test_i18n_backend_catalog_and_english_dev_audit.py` + `tests/unit/i18n_backend_audit_baseline.json`.
- **Layer 1b (`apps/web/src/__tests__/`)**: `client-error-code-resolution.test.ts`, `i18n-hardcoded-locale-ast-audit.test.ts`, `i18n-dictionary-parity-and-jargon-audit.test.ts`, `client-error-code-contract-audit.test.ts`, plus `i18n-and-shell.test.tsx` and `tsc --noEmit`.
- **Layer 2 (`tests/integration/`)**: No DB/HTTP route changes; full regression delegated to Testing Sub-Agent if required.
- **Layer 3 (`tests/contract/`, `lint-imports`)**: No schema/domain boundary changes; `0-diff` OpenAPI preserved.
- **Layer 4 (`tests/evals/`) & Security (`tests/security/`)**: Unchanged in Lot 0; full execution owned by Testing Sub-Agent.
- **Layer 5 (`apps/web/e2e/`)**: No UI flow/selector mutations in Story `27.1`; bilingual E2E expansion scheduled in Story `27.8`.

---

## 3. Summary of Changes & Results (Post-Implementation)

### 3.1 Created & Modified Files
| File | Action | Lines (`wc -l`) | Concise Summary |
| :--- | :--- | :--- | :--- |
| `apps/web/src/lib/clientErrorCodes.ts` | Created | `111` L | Typed `CLIENT_ERROR_CODES`, `ClientErrorCode`, `ClientErrorPayload`, `createClientErrorPayload`, `isClientErrorCode`, `isClientErrorPayload`, and `resolveClientErrorMessage` with `{seconds}`/`{detail}` interpolation and `ERR_CLIENT_UNKNOWN` fallback. |
| `apps/web/src/i18n/locales/client_errors_labels.ts` | Created | `29` L | Symmetric `CLIENT_ERRORS_FR_LABELS` and `CLIENT_ERRORS_EN_LABELS` compliant with UX Rule 3.1 zero-jargon. |
| `apps/web/src/i18n/locales/core_shell_labels_fr.ts` | Created | `136` L | Step 0 split: extracted `shell`, `humanAnchor`, `arbitrationTieBreak`, and `modulePages` French labels from `fr.ts`. |
| `apps/web/src/i18n/locales/core_shell_labels_en.ts` | Created | `136` L | Step 0 split: extracted `shell`, `humanAnchor`, `arbitrationTieBreak`, and `modulePages` English labels from `en.ts`. |
| `apps/web/src/i18n/locales/core_domain_labels_fr.ts` | Created | `195` L | Step 0 split: extracted domain French sections (`workspaceTopology`, `catalogExplorer`, `permissionBroker`, `bootstrapOnboarding`, `ontologyExplorer`) from `fr.ts`. |
| `apps/web/src/i18n/locales/core_domain_labels_en.ts` | Created | `194` L | Step 0 split: extracted domain English sections from `en.ts`. |
| `apps/web/src/i18n/locales/fr.ts` | Refactored | `47` L | Reduced from `355` L to `47` L; composes extracted sub-dictionaries and `clientErrors`. |
| `apps/web/src/i18n/locales/en.ts` | Refactored | `47` L | Reduced from `355` L to `47` L; composes extracted sub-dictionaries and `clientErrors`. |
| `apps/web/src/i18n/types.ts` | Modified | `96` L | Added `clientErrors: ClientErrorLabels` on `TranslationDictionary`. |
| `apps/web/src/__tests__/_i18nAuditHelpers.ts` | Created | `179` L | Shared TypeScript AST (`typescript.createSourceFile`) helpers for Gate 1 hardcoded locale/JSX scanning. |
| `apps/web/src/__tests__/_clientErrorAuditHelper.ts` | Created | `189` L | Shared AST/source scanner for Gate 3 hardcoded client error strings and locale ternaries across bridges, stores, and controllers. |
| `apps/web/src/__tests__/i18n-hardcoded-locale-baseline.json` | Created | `206` L | Ratchet baseline freezing Gate 1 (`1,253` AST violations) and Gate 3 (`177` client error violations). |
| `apps/web/src/__tests__/i18n-hardcoded-locale-ast-audit.test.ts` | Created | `89` L | Gate 1 deterministic TS/JSX AST audit (`3` tests). |
| `apps/web/src/__tests__/i18n-dictionary-parity-and-jargon-audit.test.ts` | Created | `130` L | Gate 2 FR/EN recursive parity, `{param}` placeholder parity, and UX Rule 3.1 zero-jargon audit (`2` tests, `0` violations). |
| `apps/web/src/__tests__/client-error-code-contract-audit.test.ts` | Created | `88` L | Gate 3 client error contract & ratchet audit (`4` tests). |
| `apps/web/src/__tests__/client-error-code-resolution.test.ts` | Created | `98` L | Unit tests for `ClientErrorCode` FR/EN resolution, interpolation, fallback, and payload validation (`5` tests). |
| `tests/unit/i18n_backend_audit_baseline.json` | Created | `166` L | Gate 4 ratchet baseline (`0` prompt directives, `757` non-catalog French literals, `3` legacy missing `ERROR_CATALOG` codes). |
| `tests/unit/test_i18n_backend_catalog_and_english_dev_audit.py` | Created | `282` L | Gate 4 backend RFC 9457 completeness, prompt neutrality, and English-only diff comment/docstring audit (`3` tests). |

### 3.2 Quantitative Metrics, Baseline Counts & Static Quality
- **Line-Count Guard (`wc -l <= 300`)**: `18/18` code, test, and baseline files are `<= 300` lines (max `282` lines in `test_i18n_backend_catalog_and_english_dev_audit.py`).
- **Deterministic Ratchet Baselines**:
  - **Gate 1 (`i18n-hardcoded-locale-ast-audit.test.ts`)**: `1,253` (`totalAstViolations`) across `astFiles` in `apps/web/src` and `packages/ui/src`.
  - **Gate 2 (`i18n-dictionary-parity-and-jargon-audit.test.ts`)**: `0` violations across `frDictionary` and `enDictionary` (keys, `{param}` placeholders, non-empty leaves, UX Rule 3.1 zero-jargon).
  - **Gate 3 (`client-error-code-contract-audit.test.ts`)**: `177` (`totalClientErrorViolations`) across `clientErrorBaseline` (`apps/web/src` and `packages/api-client/src`).
  - **Gate 4 (`test_i18n_backend_catalog_and_english_dev_audit.py`)**: `0` hardcoded single-language prompt directives (`totalPromptDirectiveViolations: 0`), `757` legacy non-catalog French literals (`totalNonCatalogFrenchLiterals: 757`), `3` legacy missing `ERROR_CATALOG` codes (`missingErrorCatalogCodes`), and `0` non-English comments/docstrings in diff vs `main`.
- **Static Quality & Workspace Gates (Independent Testing Sub-Agent)**:
  - `pnpm turbo run lint typecheck test`: **`9/9` tasks passed** (`443` JS/TS tests across `112` test files):
    - `@orcia/api-client`: `3 passed (3)` files, `20 passed (20)` tests
    - `@orcia/ui`: `35 passed (35)` files, `139 passed (139)` tests
    - `@orcia/web`: `74 passed (74)` files, `284 passed (284)` tests (including `14` new Story `27.1` tests)
  - `.venv/bin/ruff check .` & `.venv/bin/ruff format --check .`: `0` warnings (`All checks passed!`, `1571 files already formatted`).
  - `.venv/bin/mypy --strict packages/orcia-core packages/orcia-connectors apps/api apps/worker`: `0` errors (`Success: no issues found in 723 source files`).
  - `.venv/bin/pytest tests/unit/test_i18n_backend_catalog_and_english_dev_audit.py --no-cov -q`: **`3 passed`**.
  - Governance & Catalog Gates: `scripts/check_implementation_docs.py`, `pnpm site:sync && pnpm site:check`, and `tests/unit/test_site_catalog_sync.py` verified after report/registry closure.

### 3.3 AD-17 Test Pyramid & Vertical Wiring Verification
- **Layer 1a — Python Unit & Governance Audits (`tests/unit/`)**: `test_i18n_backend_catalog_and_english_dev_audit.py` (`3 passed`) enforces RFC 9457 `ERROR_CATALOG` FR/EN completeness, prompt locale neutrality, backend French literal ratchet (`757`), and English-only diff comments/docstrings vs `main`.
- **Layer 1b — Frontend TS & AST Audits (`Vitest`)**: `443` tests across `@orcia/api-client` (`20`), `@orcia/ui` (`139`), and `@orcia/web` (`284`), including `14` new Story `27.1` tests covering `ClientErrorCode` resolution (`5`), Gate 1 (`3`), Gate 2 (`2`), and Gate 3 (`4`).
- **Layer 2 (`tests/integration/`), Layer 3 (`OpenAPI`), Layer 4 (`tests/evals/`), Security (`tests/security/`) & Layer 5 (`Playwright`)**: Unchanged in Lot 0 (`0` DB/API route/UI behavior mutations); no API contracts or OpenAPI schemas modified.
