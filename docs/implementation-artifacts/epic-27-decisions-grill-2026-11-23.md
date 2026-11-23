# Architecture & Governance Decisions — Epic 27 (English-Only Development & Documentation, 100% Bilingual FR/EN Web App & Deterministic i18n Controls)

- **Date**: 2026-11-23
- **Branch**: `feat/epic-27-bilingual-i18n-and-deterministic-locale-guards` (branched from `main` at `a1761e3`)
- **Method**: Interactive `/grill-me` alignment session (`D1–D4`) following the `2026-11-20` hardcoded locale audit
- **Related Artifacts**:
  - Source Audit Report: [`2026-11-20-audit-i18n-chaines-codees-en-dur-tech-lead-report.md`](./tech-lead-reports/2026-11-20-audit-i18n-chaines-codees-en-dur-tech-lead-report.md)
  - Raw Inventory Annex (`3,809` hits / `461` files): [`_i18n-audit-inventory-raw.md`](./tech-lead-reports/_i18n-audit-inventory-raw.md)
  - Backlog: [`epics.md` — Epic 27](../planning-artifacts/epics.md)
  - Sprint Status: [`sprint-status.yaml`](./sprint-status.yaml)

---

## 1. Consolidated Active Decisions (`D1–D4`)

| ID | Topic | Effective Decision | Impacted Stories & Gates |
| :--- | :--- | :--- | :--- |
| **`D1`** | Git Branching Strategy | Commit verified `2026-11-23` changes on `main` (`a1761e3`) first, then create and work on `feat/epic-27-bilingual-i18n-and-deterministic-locale-guards`. | Branch setup (Pre-27.1 Gate) |
| **`D2`** | English-Only Development & Documentation vs 100% Bilingual (`fr`/`en`) Web App | Translate active governance files (`AGENTS.md`, `CLAUDE.md`, `.agents/rules/bmad-model-routing.md`, `_bmad/*` configs, `TECH-LEAD-REPORT-TEMPLATE.md`, and the restored `2026-11-20` audit report) to English immediately. Enforce **English-only** for all chat conversations, planning/architecture docs, Tech Lead reports, commit messages, and code comments/docstrings on all new/modified files, while keeping legacy historical Tech Lead reports immutable. Guarantee **100% bilingual French (`fr`) and English (`en`) compatibility** across `apps/web`, `@orcia/ui`, RFC 9457 error catalogs, and Assistant prompts. | Governance + `27.1`–`27.8` |
| **`D3`** | Four Deterministic CI Controls (Layer 1a & Layer 1b) | Implement 4 automated deterministic gates: **(1)** TS/JSX AST ban on inline locale ternaries and hardcoded user-facing JSX strings with a strictly decreasing ratchet baseline reaching `0`; **(2)** Recursive FR↔EN dictionary key/placeholder parity and UX Rule 3.1 jargon audit; **(3)** `ClientErrorCode` contract audit across API bridges, `packages/api-client`, and `formatRfc9457ErrorToBanner`; **(4)** Python RFC 9457 bilingual (`fr`/`en`) error catalog completeness + LLM prompt locale neutrality + English-only comment/docstring check on touched/new files (`git diff main...HEAD`). | `27.1` (creation), `27.2`–`27.7` (ratchet), `27.8` (zero-baseline lock) |
| **`D4`** | Full Remediation Scope Across 6 Lots (`Stories 27.1`–`27.8`) | Remediate all audited categories (`A=71`, `B=577`, `C=2,816` across `apps/web` and `@orcia/ui`, `D=193`) across 6 structured lots (8 stories: `27.1`..`27.8`), closing with `0` baseline exceptions and bilingual (`fr` & `en`) Playwright E2E proof. | `27.1`–`27.8` |

---

## 2. Detailed Decision Specifications

### `D1` — Git Branching Strategy
- **Context**: `main` held verified `2026-11-23` changes for AI model edit API key input and FR/EN Assistant locale alignment (`a1761e3`).
- **Effective Rule**: Cut `feat/epic-27-bilingual-i18n-and-deterministic-locale-guards` directly from `main` after `a1761e3`, keeping Epic 27 work cleanly isolated and preserving atomic per-story commits.

### `D2` — English-Only Development & Documentation Policy + Bilingual Web App
- **Context**: Previously, project governance defaulted both documentation and development discussions to French while mixing French comments/docstrings into Python and TypeScript modules.
- **Effective Rule**:
  - **Development & Documentation (`100% English`)**: Chat conversations, BMAD configs, governance rules (`AGENTS.md`, `CLAUDE.md`, `.agents/rules/bmad-model-routing.md`), planning docs (`epics.md` Epic 27+, ADRs), Tech Lead reports (`TECH-LEAD-REPORT-TEMPLATE.md`, `scripts/check_implementation_docs.py` supporting both legacy French and new English section headings), commit messages, and code comments/docstrings in Python & TypeScript are strictly **English**. Legacy immutable Tech Lead reports remain untouched.
  - **Product Surface (`100% Bilingual French fr & English en`)**: End users of ORCIA can operate the entire SPA (`apps/web` + `@orcia/ui`) and backend error/Assistant responses seamlessly in either **French (`fr`)** or **English (`en`)** via typed dictionaries (`apps/web/src/i18n/locales/`), typed `@orcia/ui` label props, `ClientErrorCode` resolution, and `Accept-Language` RFC 9457 catalogs.

### `D3` — Four Deterministic CI Controls
1. **Gate 1 — TS/JSX Hardcoded Locale & Raw String AST Audit (`apps/web/src/__tests__/i18n-hardcoded-locale-ast-audit.test.ts`)**:
   - Uses TypeScript's compiler AST (`typescript.createSourceFile`) across `apps/web/src/` and `packages/ui/src/` (excluding `apps/web/src/i18n/locales/`, `generated/`, and `__tests__/`).
   - Flags: (a) inline locale conditional branches (`locale === "fr"`, `locale === "en"`, `isFr ? ... : ...`, `lang === "fr"`), and (b) raw hardcoded user-facing JSX text nodes or UI attributes (`title`, `placeholder`, `aria-label`, `alt`, `label`, `description`, `emptyMessage`, `helperText`, etc.).
   - Enforces a versioned JSON ratchet baseline (`i18n-hardcoded-locale-baseline.json`) that can only **decrease** per story and MUST reach **`0`** by Story `27.8`.
2. **Gate 2 — FR↔EN Dictionary Parity, Placeholders & Zero-Jargon Audit (`apps/web/src/__tests__/i18n-dictionary-parity-and-jargon-audit.test.ts`)**:
   - Traverses every FR/EN dictionary pair under `apps/web/src/i18n/locales/` to assert identical nested key structures, identical `{param}` interpolation placeholders, no untranslated empty values, and zero UX Rule 3.1 forbidden internal jargon tokens.
3. **Gate 3 — Client Error Code Contract Audit (`apps/web/src/__tests__/client-error-code-contract-audit.test.ts`)**:
   - Scans `*ApiBridge.ts`, `packages/api-client/src/`, `formatRfc9457ErrorToBanner.ts`, stores, and controllers for hardcoded client error sentences or `locale === "fr"` error ternaries, requiring `ClientErrorCode` (`ERR_CLIENT_*`) resolved through `resolveClientErrorMessage(code, labels, params)`.
4. **Gate 4 — Backend RFC 9457 Catalog Completeness, Prompt Locale Neutrality & English-Only Dev Audit (`tests/unit/test_i18n_backend_catalog_and_english_dev_audit.py`)**:
   - Verifies every registered `OrciaDomainError` / `error_code` provides complete `fr` and `en` localized copies (`Accept-Language`), bans hardcoded single-language instructions in LLM prompts outside `PROMPT_LOCALES`, and flags non-English/French-accented comments or docstrings on newly added or modified files (`git diff main...HEAD`, with ratchet protection on existing legacy files touched during Epic 27).

### `D4` — 6-Lot / 8-Story Remediation Plan
- **Lot 0 (`27.1`)**: Deterministic CI guardrails (Gates 1–4 + measured baselines) & shared `ClientErrorCode` / `resolveClientErrorMessage` foundation.
- **Lot 1 (`27.2`)**: Category A remediation (`71` hits / `26` files) — `ClientErrorCode` migration across all bridges, SSE stores, controllers, `packages/api-client`, and `formatRfc9457ErrorToBanner.ts` (Gate 3 baseline → `0`).
- **Lot 2 (`27.3`–`27.4`)**: Category C `apps/web` remediation — Shell, Contextual Help, Notifications, Routes, Bootstrap Wizards (`27.3`), and Cockpit, Assistant/Inbox, Workspaces, Gates, Catalog, Admin (`27.4`).
- **Lot 3 (`27.5`–`27.6`)**: Category C Process Studio v2 (`27.5`, bringing `apps/web` Gate 1 baseline → `0`) and `@orcia/ui` design system primitives via typed label props (`27.6`, bringing `packages/ui` Gate 1 baseline → `0`).
- **Lot 4 (`27.7`)**: Categories B & D backend remediation (`577` + `193` hits) — RFC 9457 bilingual error catalogs, `Accept-Language` resolution, LLM prompt bundles, and seed display localization (Gate 4 baseline → `0`).
- **Lot 5 (`27.8`)**: Zero-baseline lock across all 4 gates (`0` exceptions), bilingual (`fr` & `en`) Playwright E2E verification, `pnpm site:sync && pnpm site:check`, and Epic 27 closure.
