# Story 29.4 — Canonical `<OrciaPageHeader />`, `<OrciaTabStrip />`, `<OrciaDataCard />`, Strict Cobalt Visual Grammar & Disabled Secondary Button Tokens

- **Date**: 2026-11-25
- **Story / Sprint Key**: `29-4-canonical-page-header-tab-strip-data-card-and-visual-grammar-tokens` (`Epic 29` / Lot 2)
- **Capability(ies)**: `CAP-060`, `CAP-100` (`docs/product/capabilities.yaml`) — classification: `ux`
- **Author / Context**: Resolves findings `UH-06` (`P1`) and `UH-07` (`P1`) from `docs/planning-artifacts/sprint-change-proposal-2026-11-24-epic-29-ui-headers-scope-and-screen-consistency.md`. Establishes the canonical Direction C page framing primitives (`<OrciaPageHeader />`, `<OrciaTabStrip />`, `<OrciaDataCard />`) in `@orcia/ui`, introduces strict three-tier Cobalt visual grammar separation across primary CTAs, page tabs, and filter/scope pills, fixes disabled secondary/ghost button feedback (`opacity: 0.48; cursor: not-allowed; pointer-events: none;`), migrates `ModuleWorkspaceView` onto `<OrciaPageHeader />` (`<h1>` at `var(--font-size-h2)`), and documents the unified header & visual grammar rules in `DESIGN.md`.
- **Associated Commits**: `pending (working tree)`

---

## 1. Needs Analysis & Tech Lead Impact Study (Pre-Implementation)

### 1.1 Context & Problem Statement
1. **`UH-06` — Missing Canonical Page Framing Primitives (`<OrciaPageHeader />`, `<OrciaTabStrip />`, `<OrciaDataCard />`)**:
   - **Current behavior**: `packages/ui/src/index.ts` exports no `<OrciaPageHeader />`, `<OrciaTabStrip />`, or `<OrciaDataCard />`. `apps/web/src/components/ModuleWorkspaceView.tsx:L55-L88` bypasses header rendering for five main routes (`cockpit`, `catalog`, `finops`, `inbox`, `admin`) and renders an ad-hoc `<div className="orcia-bento-card">` with `<strong style={{ fontSize: "16px" }}>` instead of a semantic `<h1>` heading for `ontology`, `gates`, and `bootstrap`. As a result, audited screens (`Mon Assistant`, `Mes Processus`, `Mes Agents`, `Mes Espaces`, `Mon Organisation`, `FinOps`, `Aide`) exhibit seven incompatible header layouts.
   - **Expected behavior**: `@orcia/ui` exports three composable, pure-UI primitives:
     - `<OrciaPageHeader />`: Two-tier `.orcia-bento-card` anatomy — Tier 1 with monochrome `<OrciaIcon />`, semantic `<h1>` (`var(--font-size-h2)`), optional context badge, 1-line subtitle, and right-aligned Secondary + at-most-one Primary Cobalt CTA; optional Tier 2 with `<OrciaTabStrip />` + Scope Bar; plus an optional aligned `alertSlot` rendered strictly beneath the header card.
     - `<OrciaTabStrip />`: Accessible horizontal `role="tablist"` strip (`underline` or `segmented` variant) with keyboard navigation (`ArrowLeft`/`ArrowRight`/`Home`/`End`), optional monochrome icons, badge counts, disabled/tooltip support, and optional trailing action slot.
     - `<OrciaDataCard />`: Canonical white surface card (`var(--orcia-surface-card)`, `var(--orcia-border-subtle)`) with optional header bar (monochrome `<OrciaIcon />`, `<h2>` title, subtitle, `metaBadge`, right `actions`), body slot, and optional footer.
   - `ModuleWorkspaceView.tsx` adopts `<OrciaPageHeader />` (with semantic `<h1>` and `ORCIA_MODULE_ICON_NAMES[currentModule]`) for module routes not yet migrated by Stories 29.5–29.6, while preserving existing route exclusions and `module-uri-badge-*` test IDs.
2. **`UH-07` — Overloaded Primary Cobalt `#2563EB` Visual Grammar & Indistinct Disabled Secondary/Ghost Buttons**:
   - **Current behavior**: `packages/ui/src/styles/tokens-components.css` styles `.orcia-ds-btn-primary:disabled` (`opacity: 0.48`) and `.orcia-ds-btn-danger:disabled` (`opacity: 0.5`), while `.orcia-ds-btn-secondary` and `.orcia-ds-btn-ghost` fall back to `.orcia-ds-btn:disabled` (`opacity: 0.72` without `pointer-events: none`), making disabled secondary/ghost actions appear clickable. Furthermore, tabs and filters share solid Cobalt `#2563EB` fill styling with primary CTAs.
   - **Expected behavior**:
     - `.orcia-ds-btn-secondary:disabled` and `.orcia-ds-btn-ghost:disabled` apply `opacity: 0.48; cursor: not-allowed; pointer-events: none;`, matching `.orcia-ds-btn-primary:disabled` (`0.48`) and `.orcia-ds-btn-danger:disabled` (`0.50`), with clean `:hover:not(:disabled)` affordance.
     - `<OrciaTabStrip />` (`.orcia-ds-tab-strip`, `.orcia-ds-tab-strip-item`) uses underline or neutral segmented active grammar visually distinct from solid `#2563EB` primary buttons (`.orcia-ds-btn-primary`) and neutral filter/scope pills, while preserving legacy `--color-tab-*` and `[role="tab"]` rules for backward compatibility until Stories 29.5–29.6 migrate all screens.

### 1.2 Exploration, GitNexus Impact Analysis, Refactoring & Technical Debt
- **GitNexus Impact Analysis (`repo: "ORCIA"`, workspace inspection)**:
  - Inspected `packages/ui/src/index.ts` (781 lines), `packages/ui/src/styles/tokens-palette.css` (164 lines), `packages/ui/src/styles/tokens-components.css` (276 lines), `packages/ui/src/styles/tokens-dark.css` (59 lines), `packages/ui/src/styles/tokens-shell.css` (279 lines), `packages/ui/src/primitives/DesignSystemControls.tsx` (281 lines), `packages/ui/src/components/icons/iconRegistry.ts` (`ORCIA_MODULE_ICON_NAMES`), and `apps/web/src/components/ModuleWorkspaceView.tsx` (107 lines).
  - Upstream callers of `ModuleWorkspaceView`: `apps/web/src/router.tsx` and route modules (`bootstrap.tsx`, `catalog.tsx`, `cockpit.tsx`, `finops.tsx`, `gates.tsx`, `inbox.tsx`, `index.tsx`, `ontology.tsx`, `workspaces.tsx`), plus Vitest specs `story-23-5-sobriety-and-citations-wiring.test.tsx` (`module-uri-badge-ontology`, `module-view-inbox`), `i18n-and-shell.test.tsx`, `story-28-1-single-workspace-header-and-zero-uuid-leak.test.tsx`, and `workspaces-single-tabs-anti-stacking-audit.test.tsx`.
  - Upstream CSS/token invariant checks: `apps/web/src/__tests__/design-system-look-and-feel-isolation.test.tsx` explicitly asserts `--color-tab-active-bg: var(--color-primary-cobalt);`, `--color-tab-inactive-bg: #DBEAFE;`, `--color-tab-inactive-fg: #1E3A8A;`, `[role="tab"][aria-selected="true"]`, and `[role="tab"]:focus-visible` in `packages/ui/src/styles/`, plus zero raw hex colors outside `packages/ui/src/styles/`.
  - **Blast radius / Risk**: Low. Adding new primitives, semantic tokens, and `.orcia-ds-page-header` / `.orcia-ds-tab-strip` / `.orcia-ds-data-card` classes is strictly additive; preserving `--color-tab-*` and existing `ModuleWorkspaceView` exclusion conditions prevents regressions prior to Stories 29.5–29.6.
- **Exploration & Key Metrics**:
  - Verified `packages/ui/src/__tests__/ui-isolation.test.ts` and `apps/web/src/__tests__/i18n-hardcoded-locale-ast-audit.test.ts` (Gate 1 zero-baseline): `@orcia/ui` primitives must have zero forbidden framework/API imports, zero raw hex colors in `.ts/.tsx`, zero hardcoded user-facing JSX strings/fallbacks/defaults, and zero `--color-human-led-violet` references outside `HumanLedAnchorCard.tsx`.
- **Refactoring Opportunities & File Line-Count Control (`<= 300` lines)**:
  - Place each new primitive in its own cohesive module (`OrciaPageHeader.tsx`, `OrciaTabStrip.tsx`, `OrciaDataCard.tsx`) under `packages/ui/src/primitives/`, each strictly `<= 200` lines.
  - Reuse `OrciaIcon` + `ORCIA_MODULE_ICON_NAMES` from `packages/ui/src/components/icons` and `StatusBadge` inside `ModuleWorkspaceView.tsx` rather than duplicating SVG or badge styling.
  - Keep every CSS stylesheet modular and strictly `<= 300` lines: place `.orcia-ds-btn-secondary:disabled` and `.orcia-ds-btn-ghost:disabled` in `tokens-components.css` (~289 lines), semantic tokens in `tokens-palette.css` (~185 lines), and canonical `.orcia-ds-page-header` / `.orcia-ds-tab-strip` / `.orcia-ds-data-card` rules in a dedicated `packages/ui/src/styles/tokens-headers.css` imported from `tokens.css` (~195 lines).

---

## 2. Implementation Plan

### 2.1 Data Schema & Alembic Migrations
- None required. Story 29.4 is strictly a Design System (`@orcia/ui`), CSS token, `ModuleWorkspaceView`, and `DESIGN.md` deliverable.

### 2.2 Hexagonal Core, Orchestration & Workers (`packages/orcia-core/`, `apps/worker/`)
- None required.

### 2.3 Backend API, Security & Contracts (`apps/api/`, `packages/api-client/`)
- None required.

### 2.4 User Interface & Experience (`packages/ui/`, `apps/web/`, `DESIGN.md`)
- **`packages/ui/src/styles/tokens-palette.css`**:
  - Add `--orcia-surface-card` alias (`var(--color-surface-card)`) and semantic `<OrciaTabStrip />` / `<OrciaPageHeader />` tokens (`--color-tab-strip-border`, `--color-tab-strip-fg`, `--color-tab-strip-hover-fg`, `--color-tab-strip-hover-bg`, `--color-tab-strip-active-fg`, `--color-tab-strip-active-indicator`, `--color-tab-strip-segmented-bg`, `--color-tab-strip-segmented-active-bg`, `--color-tab-strip-badge-bg`, `--color-tab-strip-badge-fg`, `--color-tab-strip-badge-active-bg`, `--color-tab-strip-badge-active-fg`) using existing theme-aware CSS variables (compatible with both light mode and `[data-theme="dark"]`, zero raw hex outside `styles/`).
- **`packages/ui/src/styles/tokens-components.css` & `packages/ui/src/styles/tokens-headers.css` (imported via `tokens.css`)**:
  - Update `.orcia-ds-btn-secondary:disabled` and `.orcia-ds-btn-ghost:disabled` in `tokens-components.css` to `opacity: 0.48; cursor: not-allowed; pointer-events: none;` (plus subtle hover states for `:hover:not(:disabled)`).
  - Define `.orcia-ds-page-header` (two-tier `.orcia-bento-card` anatomy, Tier 1 identity + `<h1>` at `var(--font-size-h2)` + right actions, Tier 2 tabs + scope bar, aligned `.orcia-ds-page-header-alert-slot`), `.orcia-ds-tab-strip` (`underline` and `segmented` variants overriding `[role="tab"]` Cobalt fill cleanly), and `.orcia-ds-data-card` in `tokens-headers.css` (imported in `tokens.css`) so every CSS file stays `<= 300` lines and `readAllTokensCss()` captures every class and variable cleanly.
- **`packages/ui/src/primitives/OrciaPageHeader.tsx` (`<= 300` lines)**:
  - Pure typed component rendering `<header data-testid={testId} className="orcia-bento-card orcia-ds-page-header ...">` with Tier 1 (optional monochrome `<OrciaIcon />`, `<h1>` title, optional `contextBadge`, optional 1-line `subtitle`, right-aligned `secondaryActions` / `actions` / `primaryAction`), optional Tier 2 (`tabs` + `scopeBar`), and optional aligned `alertSlot` strictly beneath the `<header>` card.
- **`packages/ui/src/primitives/OrciaTabStrip.tsx` (`<= 300` lines)**:
  - Pure typed `role="tablist"` horizontal strip supporting `underline` (default) and `segmented` variants, `activeTabId`, `onSelectTab`, `ariaLabel` (required caller prop, zero hardcoded fallback), `count` badges, optional `icon`, `disabled` + `disabledReason` / `tooltip`, `ArrowLeft`/`ArrowRight`/`Home`/`End` keyboard navigation skipping disabled tabs, and optional `trailingSlot`.
- **`packages/ui/src/primitives/OrciaDataCard.tsx` (`<= 300` lines)**:
  - Pure typed white surface card (`orcia-bento-card orcia-ds-data-card`) with optional header bar (`icon`, `title` in `<h2>`, `subtitle`, `metaBadge`, `actions`), body content (`children`), and optional `footer`.
- **`packages/ui/src/index.ts`**:
  - Export `OrciaPageHeader`, `OrciaTabStrip`, `OrciaDataCard` and their exported TypeScript prop/item types.
- **`apps/web/src/components/ModuleWorkspaceView.tsx` (`<= 300` lines)**:
  - Replace the `<div className="orcia-bento-card">` + `<strong style={{ fontSize: "16px" }}>` block with `<OrciaPageHeader />` using `icon={ORCIA_MODULE_ICON_NAMES[currentModule]}`, `title={headerSubtitle}` (semantic `<h1>`), `subtitle={headerDescription}`, and `contextBadge={<StatusBadge testId={`module-uri-badge-${currentModule}`} label={pageCopy.uriBadgeExample} tone="cobalt" />}` while preserving existing screen exclusions (`cockpit`, `catalog`, `finops`, `inbox`, `admin`).
- **`docs/planning-artifacts/ux-designs/ux-ORCIA-2026-10-24/DESIGN.md`**:
  - Document `<OrciaPageHeader />`, `<OrciaTabStrip />`, `<OrciaDataCard />`, the three-tier Cobalt visual grammar rules (single Primary CTA vs underline/segmented Tabs vs neutral Filters/Scope Pills), and disabled secondary/ghost button contrast rules in English.

### 2.5 Test Pyramid Impact Analysis (`AD-17` — Layers 1 to 5 + Security, Mandatory)
- **Layer 1a (`tests/unit/`)**: Existing `tests/unit/test_i18n_backend_catalog_and_english_dev_audit.py` verifies zero French regressions in code/docs.
- **Layer 1b (`packages/ui/src/__tests__/` & `apps/web/src/__tests__/`)**:
  - `packages/ui/src/__tests__/orcia-page-header-tab-strip-card.test.tsx`: Isolated unit tests for `<OrciaPageHeader />`, `<OrciaTabStrip />` (`aria-selected`, keyboard navigation, disabled tab skipping, count badges, `underline` & `segmented` classes, `trailingSlot`), `<OrciaDataCard />`, `alertSlot` placement beneath `<header>`, and `data-testid` propagation.
  - `apps/web/src/__tests__/story-29-4-canonical-header-and-visual-grammar.test.tsx`: Governance & integration test verifying `@orcia/ui` exports, CSS rules (`.orcia-ds-btn-secondary:disabled`, `.orcia-ds-btn-ghost:disabled`, `.orcia-ds-page-header`, `.orcia-ds-tab-strip`, `.orcia-ds-data-card`), `ModuleWorkspaceView` semantic `<h1>` rendering via `<OrciaPageHeader />`, zero forbidden imports in `packages/ui`, and zero raw hex outside `tokens*.css`.
  - Re-run existing `i18n-dictionary-parity-and-jargon-audit.test.ts`, `i18n-hardcoded-locale-ast-audit.test.ts`, `design-system-look-and-feel-isolation.test.tsx`, and `story-23-5-sobriety-and-citations-wiring.test.tsx`.
- **Layer 2 (`tests/integration/api/`)**: Not impacted (pure UI/CSS story).
- **Layer 3 (`OpenAPI 3.1`, `lint-imports`)**: Not impacted (no API or Python domain changes).
- **Layer 4 & Security**: Delegated to Testing Sub-Agent for full `AD-17` closure checks.
- **Layer 5 (Playwright E2E)**: Delegated to Testing Sub-Agent (`env -u ORCIA_E2E_SEED_FIXTURES`).

---

## 3. Summary of Changes & Results (Post-Implementation)

### 3.1 Created & Modified Files (`wc -l`)
| File | Action | Line Count (`wc -l`) | Concise Summary |
| :--- | :--- | :--- | :--- |
| `packages/ui/src/primitives/OrciaPageHeader.tsx` | Created | `124` | Pure Direction C canonical two-tier page header (`<header class="orcia-bento-card orcia-ds-page-header">`), monochrome `<OrciaIcon />`, semantic `<h1>` (`var(--font-size-h2)`), optional `contextBadge`, `secondaryActions` / `primaryAction`, Tier-2 `tabs` & `scopeBar`, and aligned `alertSlot` beneath the header card. |
| `packages/ui/src/primitives/OrciaTabStrip.tsx` | Created | `144` | Accessible horizontal `role="tablist"` strip (`underline` and `segmented` variants), monochrome icon & count badge support, disabled tab skipping, `ArrowLeft`/`ArrowRight`/`Home`/`End` keyboard navigation, and optional `trailingSlot`. |
| `packages/ui/src/primitives/OrciaDataCard.tsx` | Created | `84` | Pure Direction C surface card (`orcia-bento-card orcia-ds-data-card`) with optional header (`<OrciaIcon />`, `<h2>`, `subtitle`, `metaBadge`, `actions`), body slot, and optional `footer`. |
| `packages/ui/src/styles/tokens-headers.css` | Created | `300` | Canonical CSS rules for `.orcia-ds-page-header*`, `.orcia-ds-tab-strip*` (`underline` + `segmented`, clean override over legacy `[role="tab"]` fill), and `.orcia-ds-data-card*` across light and dark themes. |
| `packages/ui/src/styles/tokens-palette.css` | Modified | `187` | Added `--orcia-surface-card` alias and `--color-tab-strip-*` semantic tokens for three-tier Cobalt visual grammar separation. |
| `packages/ui/src/styles/tokens-components.css` | Modified | `293` | Enforced `.orcia-ds-btn-secondary:disabled` and `.orcia-ds-btn-ghost:disabled` (`opacity: 0.48; cursor: not-allowed; pointer-events: none;`) plus `:hover:not(:disabled)` affordances. |
| `packages/ui/src/styles/tokens.css` | Modified | `12` | Imported `./tokens-headers.css` in the Direction C token stylesheet barrel. |
| `packages/ui/src/index.ts` | Modified | `795` (barrel) | Exported `OrciaPageHeader`, `OrciaTabStrip`, `OrciaDataCard` and their public TypeScript prop/item types. |
| `apps/web/src/components/ModuleWorkspaceView.tsx` | Modified | `97` | Migrated unmigrated module headers onto `<OrciaPageHeader />` (`<h1>` + `ORCIA_MODULE_ICON_NAMES[currentModule]` + `StatusBadge`), preserving existing screen exclusions (`cockpit`, `catalog`, `finops`, `inbox`, `admin`). |
| `docs/planning-artifacts/ux-designs/ux-ORCIA-2026-10-24/DESIGN.md` | Modified | `224` | Documented `<OrciaPageHeader />`, `<OrciaTabStrip />`, `<OrciaDataCard />`, three-tier Cobalt visual grammar rules, and disabled secondary/ghost button tokens in English. |
| `packages/ui/src/__tests__/orcia-page-header-tab-strip-card.test.tsx` | Created | `184` | Isolated `@orcia/ui` unit tests (`3` tests) covering `<OrciaPageHeader />`, `<OrciaTabStrip />` (`underline`, `segmented`, keyboard nav, disabled skip, `trailingSlot`), and `<OrciaDataCard />`. |
| `apps/web/src/__tests__/story-29-4-canonical-header-and-visual-grammar.test.tsx` | Created | `108` | Governance & integration Vitest suite (`4` tests) verifying `@orcia/ui` exports, CSS disabled/header/tab/card rules, `ModuleWorkspaceView` semantic `<h1>`, `@orcia/ui` import purity, and zero raw hex outside `tokens*.css`. |

All non-barrel production and test files are `<= 300` lines (`84`–`300` lines; `packages/ui/src/index.ts` is the existing package barrel at `795` lines).

### 3.2 Quantitative Metrics, Test Results & Static Quality
- **Frontend Unit & Component Suites (`Vitest`)**:
  - `@orcia/ui` (`pnpm --filter @orcia/ui run test`): **`37` test files passed (`37`), `147` tests passed (`147`)**, including `orcia-page-header-tab-strip-card.test.tsx` (`3/3` passed).
  - `@orcia/web` (`pnpm --filter @orcia/web exec vitest run --maxWorkers=4`): **`86` test files passed (`86`), `318` tests passed (`318`)**, including `story-29-4-canonical-header-and-visual-grammar.test.tsx` (`4/4` passed), `i18n-dictionary-parity-and-jargon-audit.test.ts`, `i18n-hardcoded-locale-ast-audit.test.ts`, and `design-system-look-and-feel-isolation.test.tsx`.
  - Monorepo Turbo (`pnpm turbo run lint typecheck test --concurrency=1`): **`9/9` tasks successful** (`@orcia/api-client`: `3` files / `20` tests passed; `@orcia/ui`: `37` files / `147` tests passed; `@orcia/web`: `86` files / `318` tests passed — **`485` JS/TS tests passed**, `0` errors).
- **Static Quality, Architecture & Python Sanity**:
  - `tests/unit/test_i18n_backend_catalog_and_english_dev_audit.py`: **`3` passed** (`0` non-English regressions).
  - `.venv/bin/ruff check . && .venv/bin/ruff format --check .`: **`0` warnings / `1743` files formatted**.
  - `.venv/bin/mypy --strict packages/orcia-core packages/orcia-connectors apps/api apps/worker`: **`0` issues in `856` source files**.
  - `.venv/bin/lint-imports`: **`5` contracts kept, `0` broken** (`899` files, `6,486` dependencies).
  - `lint_spine.py`: **`ok: true`, `0` findings**.
  - `scripts/export_openapi.py --check`: **`0-diff`** (`exit 0`).
  - `tests/security tests/contract tests/evals`: **`181` passed** (`exit 0`).
- **GitNexus Index & Impact Summary (`repo: "ORCIA"`)**:
  - `npx gitnexus analyze --index-only .`: indexed **`46,312` nodes, `99,001` edges, `775` clusters, `1,531` flows** (`changed=12, added=5, deleted=0`).
  - `gitnexus_detect_changes(repo="ORCIA", scope="all")`: **`changed_files: 6, changed_count: 0, affected_count: 0, risk_level: "low"`**.

### 3.3 AD-17 Test Pyramid & Vertical Wiring Verification
- **Layer 1a & 1b (`pytest` + `Vitest`)**: Verified `3/3` English-dev/i18n backend audit tests, `37/37` `@orcia/ui` test files (`147` tests), and `86/86` `@orcia/web` test files (`318` tests) with zero raw hex outside `packages/ui/src/styles/tokens*.css`, zero forbidden `@orcia/ui` imports, and zero hardcoded JSX labels.
- **Layer 2 (`HTTP ➔ PostgreSQL 18`)**: Not directly impacted by Story `29.4` (pure Design System / `ModuleWorkspaceView` / CSS deliverable); real PG18 + Redis stack verified via Layer 5 Playwright E2E without fixture seeding.
- **Layer 3 (`OpenAPI 3.1`, `lint-imports`, `lint_spine.py`)**: Verified `0-diff` OpenAPI schema, `5/5` `AD-19`/`AD-20` import contracts, and `0` architecture spine findings.
- **Layer 4 & Security (`tests/security`, `tests/contract`, `tests/evals`)**: Verified **`181 passed`** with zero UI isolation or contract regressions.
- **Layer 5 (Playwright Desktop E2E, `env -u ORCIA_E2E_SEED_FIXTURES`)**: Executed `--project=desktop-cockpit e2e/11-screens-smoke-without-server-errors.spec.ts` (`apps/web/e2e/14-*` corresponds to `14-auth-2fa-account-and-profile.spec.ts`, not a visual hierarchy spec) on ephemeral PostgreSQL 18 + Redis 7.4: **`2 passed (41.1s)`**, zero server/console errors, temporary artifacts cleaned, and zero leftover worktree Vite/API processes. Updated `CAP-060` and `CAP-100` in `docs/product/capabilities.yaml`.
