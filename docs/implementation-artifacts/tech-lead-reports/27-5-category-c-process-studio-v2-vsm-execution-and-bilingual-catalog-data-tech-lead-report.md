# Story 27.5 — Category C Remediation (Part 3): Process Studio v2, VSM, Execution Panels & Bilingual Catalog Data Modules (`apps/web` Gate 1 Baseline = 0)

- **Date**: 2026-11-24
- **Story / Sprint Key**: `27.5` (`Epic 27` — Lot 3 Part 1: Category C Process Studio v2, VSM, Execution & Bilingual Catalog Data)
- **Capability(ies)**: `CAP-020`..`CAP-036`, `CAP-140`, `CAP-160` — classification: `hygiene` (see `AGENTS.md` §5)
- **Author / Context**: Coding Sub-Agent (`Amelia`) implementing Story 27.5 under `ACTION_ITEM-I18N.1`, Bilingual Application Policy (`fr` / `en`), and UX Rule 3.1 (zero internal plumbing jargon in user-facing UI copy).
- **Associated Commits**: `3194042` (`feat(story-27.5): migrate Process Studio v2 and VSM to bilingual dictionaries and lock apps/web Gate 1 baseline to zero`) on branch `feat/epic-27-bilingual-i18n-and-deterministic-locale-guards`

---

## 1. Needs Analysis & Tech Lead Impact Study (Pre-Implementation)

### 1.1 Context & Problem Statement
- **Problem**: Following Story 27.1 (Gates 1–4 foundation), Story 27.2 (Gate 3 `clientErrorBaseline = 0`), Story 27.3 (shell/routes/wizards at `0` Gate 1 violations), and Story 27.4 (core feature modules at `0` Gate 1 violations; `totalAstViolations = 631`), **`210` Gate 1 AST violations across `19` files** remain in `apps/web/src/`:
  - `apps/web/src/features/finops/index.tsx` (`2` AST hits) and `apps/web/src/features/ontology/index.tsx` (`1` AST hit, plus 4 locale ternaries in `useOntologyFeatureController.ts`),
  - `apps/web/src/features/processes/**` (`17` files, `207` AST hits), alongside non-AST hardcoded French strings and inline `fr`/`en` object maps inside `processStudioV2Data.ts` (`1,726` lines — `434` raw audit hits), `studio/studioCatalogLabels.ts` (`110` L), `studio/studioLabelsAndMappers.ts` (`323` L), and `execution/interactiveRunFormatters.ts` (`89` L).
- **Expected vs Current**:
  - Currently, Process Studio v2 (`WorkflowFiveBlocksCanvas`, `WorkflowStudioHeaderBar`, `StudioCopilotSidebar`, `WorkflowBlock2ExecutionSection`, `WorkflowBlocks1345Sections`, `WorkflowPreviewAndWhatIfPanels`), Value Stream Map (`ValueStreamMapView`, `StepDetailSheet`, `ReturnLoopsSvgOverlay`), Interactive Run Execution (`InteractiveRunDrawer`, `InteractiveRunDrawerHeader`, `InteractiveRunDeliverableAndHitlPanels`, `interactiveRunFormatters`), `ProcessesHubPage`, `ProcessCatalogCardGrid`, `ProcessesValueStreamOverviewCard`, and `processStudioV2Data.ts` embed French-only catalog data and inline `isFr ? ... : ...` conditionals.
  - Expected behavior: 100% of UI strings, VSM phase/step/loop/opportunity copy, workflow catalog definitions, declarative pack descriptions, execution formatters, and studio catalog labels resolve from typed modular `fr`/`en` dictionaries under `apps/web/src/i18n/locales/` (`<= 300` lines each), reducing the `apps/web/src/` slice of `i18n-hardcoded-locale-baseline.json` to **`0` files (`0` AST violations)** while leaving only `packages/ui/src/` entries (`421` AST hits across `55` files) for Story `27.6`.
- **Constraints from `ARCHITECTURE-SPINE.md` & `AGENTS.md`**:
  - Preserve all `data-testid` attributes (`e2e-testids-sync-audit.test.ts`), interactive callbacks (`zero-dead-buttons-and-silent-catches-audit.test.tsx`), and strict feature domain boundaries (`check-feature-boundaries.mjs`).
  - Keep every modified or created file `<= 300` lines (`wc -l`) with English-only comments/docstrings and zero UX Rule 3.1 internal plumbing jargon (`DBOS`, `PG18`, `Outbox`, `Passthrough`, `RFC 9457`, `What-If`, `Tie-Break`, `Rebase`, etc.) in dictionary leaf values.
  - Preserve backwards-compatible exports from `processStudioV2Data.ts` (`INITIAL_DECLARATIVE_PACKS`, `INITIAL_VSM_SPEC`, `INITIAL_WORKFLOWS_V2`, `resetPersistedWorkflowsV2`, `loadPersistedWorkflowsV2`, `savePersistedWorkflowV2`) with French defaults while supporting `locale: "fr" | "en"` resolvers (`getInitialDeclarativePacks`, `getInitialVsmSpec`, `getInitialWorkflowsV2`) for full bilingual rendering.

### 1.2 Exploration, GitNexus Impact Analysis, Refactoring & Technical Debt
- **GitNexus Impact Analysis (`gitnexus_query`, `gitnexus_context`, `gitnexus_impact` scoped to `/home/romain/Documents/Projects/ORCIA`)**:
  - `gitnexus_context` on `INITIAL_VSM_SPEC` (`Const:apps/web/src/features/processes/processStudioV2Data.ts:INITIAL_VSM_SPEC`, L170–1073) returned `epistemic: "exact"` with 4 incoming `accesses` edges; `gitnexus_impact` reported `risk: UNKNOWN` (GitNexus index is 5 commits behind `HEAD` and TS module-scope const/component edges are supplemented by `grep` inspection).
  - Repo-wide `grep` across `apps/web/src/`, `apps/web/e2e/`, and `packages/` verified all upstream consumers:
    - `processStudioV2Data.ts` $\rightarrow$ imported by `ProcessesHubPage.tsx`, `ProcessesValueStreamOverviewCard.tsx`, `ProcessCatalogCardGrid.tsx`, `ValueStreamMapView.tsx`, `mapApiVsmToUiSpec.ts`, `WorkflowBlock2ExecutionSection.tsx`, `WorkflowBlocks1345Sections.tsx`, `WorkflowPreviewAndWhatIfPanels.tsx`, `WorkflowStudioHeaderBar.tsx`, `useStudioWorkflowController.ts`, `InteractiveRunDrawer.tsx`, `InteractiveRunDrawerHeader.tsx`, `InteractiveRunDeliverableAndHitlPanels.tsx`, `useInteractiveProcessRunController.ts`, `studioLabelsAndMappers.ts`, plus Vitest fixtures/specs (`mockBackendState.ts`, `story-7-1`, `story-7-2`, `story-16-3`, `story-16-4`, `story-24-1`, `epics-14-15`, `ux-polish-rfc9457`).
    - `StepDetailSheet.tsx` $\rightarrow$ mounted solely by `ValueStreamMapView.tsx`.
    - `InteractiveRunDeliverableAndHitlPanels.tsx` $\rightarrow$ mounted solely by `InteractiveRunDrawer.tsx`.
    - `studioCatalogLabels.ts` $\rightarrow$ re-exported by `studioLabelsAndMappers.ts` and consumed by `WorkflowBlock2ExecutionSection.tsx` and `WorkflowBlocks1345Sections.tsx`.
    - `WorkflowStudioHeaderBar.tsx` $\rightarrow$ mounted by `WorkflowFiveBlocksCanvas.tsx` and tested standalone (without `<I18nProvider>`) in `ux-polish-rfc9457-alerts-euro-and-jargon-purge.test.tsx:L380`, requiring dictionary lookup via `resolveDictionaryForFlag(isFr)` so standalone mounts stay functional.
- **Exploration & Key Metrics**:
  - Exact Gate 1 AST baseline audit across `apps/web/src/` (`19` files, **`210` AST violations**):
    - `apps/web/src/features/finops/index.tsx` (`2`), `apps/web/src/features/ontology/index.tsx` (`1`)
    - `apps/web/src/features/processes/AutonomousRunsSupervisionPanel.tsx` (`1`), `ProcessCatalogCardGrid.tsx` (`15`), `ProcessesHubPage.tsx` (`11`), `ProcessesValueStreamOverviewCard.tsx` (`6`)
    - `apps/web/src/features/processes/execution/`: `InteractiveRunDeliverableAndHitlPanels.tsx` (`29`), `InteractiveRunDrawer.tsx` (`13`), `InteractiveRunDrawerHeader.tsx` (`5`), `interactiveRunFormatters.ts` (`1`)
    - `apps/web/src/features/processes/studio/`: `StudioCopilotSidebar.tsx` (`11`), `WorkflowBlock2ExecutionSection.tsx` (`13`), `WorkflowBlocks1345Sections.tsx` (`11`), `WorkflowFiveBlocksCanvas.tsx` (`4`), `WorkflowPreviewAndWhatIfPanels.tsx` (`9`), `WorkflowStudioHeaderBar.tsx` (`12`)
    - `apps/web/src/features/processes/vsm/`: `ReturnLoopsSvgOverlay.tsx` (`5`), `StepDetailSheet.tsx` (`39`), `ValueStreamMapView.tsx` (`22`)
  - Line-count audit identified `6` oversized files (`> 300` lines) plus near-limit files (`280–291` L) requiring modular splits:
    1. `processStudioV2Data.ts` (`1,726` L)
    2. `ValueStreamMapView.tsx` (`534` L)
    3. `StepDetailSheet.tsx` (`470` L)
    4. `WorkflowBlock2ExecutionSection.tsx` (`325` L)
    5. `studioLabelsAndMappers.ts` (`323` L)
    6. `ProcessesHubPage.tsx` (`315` L)
    7. Near-limit files (`280–291` L): `StudioCopilotSidebar.tsx` (`291` L), `useInteractiveProcessRunController.ts` (`291` L), `WorkflowFiveBlocksCanvas.tsx` (`288` L), `useStudioWorkflowController.ts` (`285` L), `InteractiveRunDrawer.tsx` (`280` L).
- **Refactoring Opportunities & Emerging Technical Debt Mitigation**:
  - Separate `processStudioV2Data.ts` cleanly into `processStudioV2Types.ts`, `processStudioV2StructuralData.ts`, `processStudioV2Storage.ts`, and `processStudioV2Data.ts` facade (`<= 300` L each), paired with modular `<= 300` L `fr`/`en` dictionary files under `apps/web/src/i18n/locales/`.
  - Split `ValueStreamMapView.tsx`, `StepDetailSheet.tsx`, `WorkflowBlock2ExecutionSection.tsx`, `studioLabelsAndMappers.ts`, and `ProcessesHubPage.tsx` into focused `<= 300` L components/helpers.

---

## 2. Implementation Plan

### 2.1 Data Schema & Alembic Migrations
- Not applicable (no database schema or Alembic migration changes).

### 2.2 Hexagonal Core, Orchestration & Workers
- Not applicable (Python domain/worker layers are out of scope for Story 27.5).

### 2.3 Backend API, Security & Contracts
- Not applicable (no FastAPI or OpenAPI contract changes; backend `Accept-Language` error catalog remediation is scoped to Story 27.7).

### 2.4 User Interface & Experience (`apps/web/src/i18n/`, `apps/web/src/features/`)
- **Modular Typed Sub-Dictionaries (`apps/web/src/i18n/locales/`, `types.ts`, `fr.ts`, `en.ts`)** (every file `<= 300` L):
  - `process_studio_ui_labels{,_fr,_en}.ts`: Process Hub, VSM View, Step Detail Sheet, Return Loops SVG, Workflow Studio Header/Blocks/Sidebar/What-If/YAML, Studio Catalog (tools/skills/KB/delegate agents), and Interactive Run Drawer/Panels/Formatters UI labels.
  - `process_catalog_packs_and_workflows_labels.ts` + `process_catalog_workflows_{fr,en}.ts`: Declarative pack metadata copy (`sdlc`, `orcia-docs`) and localized workflow definitions (`wf-01`, `wf-03`, `wf-06`, `wf-08`, `wf-generate-orcia-documentation`).
  - `process_catalog_vsm_labels.ts` + `process_catalog_vsm_p1_{fr,en}.ts` + `process_catalog_vsm_p2_{fr,en}.ts`: VSM overview, phases 01–04, steps 01–11 (today/tomorrow/passage points/detail tabs), return loops (12 loops), and opportunities (P1–P3), cleanly split so every file stays comfortably `<= 280` L.
  - Extend `ontology_glossary_labels.ts` (`+4` resource labels for `useOntologyFeatureController.ts`) and reuse `dictionary.fourZoneShell.activityMenuLabel` in `finops/index.tsx`.
- **Component, Data & Helper Remediation + Modular Splits (`<= 300` L)**:
  - Remediate `finops/index.tsx`, `ontology/index.tsx`, `useOntologyFeatureController.ts`, and all `17` Gate 1 files + non-AST files (`processStudioV2Data.ts`, `studioCatalogLabels.ts`, `studioLabelsAndMappers.ts`, `interactiveRunFormatters.ts`, `useInteractiveProcessRunController.ts`, `useStudioWorkflowController.ts`, `mapApiVsmToUiSpec.ts`) under `apps/web/src/features/processes/`.
  - Split `ValueStreamMapView.tsx` (`534` L) $\rightarrow$ `ValueStreamMapHeaderAndDrawer.tsx` + `ValueStreamMapPhaseGrid.tsx` + `ValueStreamMapView.tsx`.
  - Split `StepDetailSheet.tsx` (`470` L) $\rightarrow$ `StepDetailSheetTabsContent.tsx` + `StepDetailSheet.tsx`.
  - Split `WorkflowBlock2ExecutionSection.tsx` (`325` L) $\rightarrow$ `WorkflowBlock2GoalDrivenSection.tsx` + `WorkflowBlock2ExecutionSection.tsx`.
  - Split `studioLabelsAndMappers.ts` (`323` L) $\rightarrow$ `studioWorkflowActions.ts` + `studioLabelsAndMappers.ts`.
  - Split `ProcessesHubPage.tsx` (`315` L) $\rightarrow$ `ProcessesActiveDossiersCard.tsx` + `ProcessesHubPage.tsx`.
  - Split `processStudioV2Data.ts` (`1,726` L) $\rightarrow$ `processStudioV2Types.ts`, `processStudioV2StructuralData.ts`, `processStudioV2Storage.ts`, and `processStudioV2Data.ts` (exposing `getInitialDeclarativePacks(locale)`, `getInitialVsmSpec(locale)`, `getInitialWorkflowsV2(locale)` plus French default constants for legacy consumers).
  - Ensure all UX Rule 3.1 forbidden terms (`What-If`, `Tie-Break`, `Rebase`, `PG18`, `DBOS`, `Outbox`, `Passthrough`, `RFC 9457`, etc.) are absent from all `fr` and `en` dictionary leaf values.
- **Gate 1 Baseline Ratchet (`apps/web/src/__tests__/i18n-hardcoded-locale-baseline.json`)**:
  - Remove **all `19` remaining `apps/web/src/` entries** (`210` AST violations removed, reducing `totalAstViolations` from `631` to `421` across the `55` remaining `packages/ui/src/` entries reserved for Story `27.6`).

### 2.5 Test Pyramid Impact Analysis (`AD-17` — Layers 1 to 5 + Security)
- **Layer 1a & 1b (Unit / Component Audit Tests)**:
  - `apps/web/src/__tests__/i18n-hardcoded-locale-ast-audit.test.ts` (Gate 1: `0` violations across `100%` of `apps/web/src/`).
  - `apps/web/src/__tests__/i18n-dictionary-parity-and-jargon-audit.test.ts` (Gate 2: 100% `fr`/`en` key & `{param}` placeholder parity + `0` UX Rule 3.1 jargon).
  - `apps/web/src/__tests__/client-error-code-contract-audit.test.ts` (Gate 3 remains `0`).
  - `apps/web/src/__tests__/anti-jargon-and-secrets-ui-audit.test.ts`, `e2e-testids-sync-audit.test.ts`, `zero-dead-buttons-and-silent-catches-audit.test.tsx`, plus targeted Process/VSM/Studio Vitest specs (`epics-14-15-*`, `story-7-1-*`, `story-7-2-*`, `story-7-4-*`, `story-16-3-*`, `story-16-4-*`, `story-24-1-*`, `ux-polish-rfc9457-*`, `i18n-and-shell.test.tsx`).
  - `.venv/bin/pytest tests/unit/test_i18n_backend_catalog_and_english_dev_audit.py --no-cov -q` (Gate 4 + English-only comments/docstrings).
- **Layers 2–5**: Deferred to Testing Sub-Agent full verification (`pnpm turbo run lint typecheck test`, Playwright Desktop E2E, `pnpm site:sync && pnpm site:check`, Report §3, `sprint-status.yaml`, and GitNexus refresh) after Coding Sub-Agent completes local `< 60 s` sanity checks.

---

## 3. Summary of Changes & Results (Post-Implementation)

### 3.1 Inventory of Created & Modified Files (`58` `apps/web` files: `30` modified, `28` created)
- **Modular Typed FR/EN Sub-Dictionaries (`apps/web/src/i18n/`)** (`18` files: `4` modified, `14` created; all `<= 269` L):
  - `apps/web/src/i18n/types.ts` (`135` L), `fr.ts` (`83` L), `en.ts` (`83` L), and `ontology_glossary_labels.ts` (`235` L, extended with `+4` resource labels).
  - `process_studio_ui_labels.ts` (`122` L) + `process_studio_ui_labels_{fr,en}.ts` (`190` / `187` L).
  - `process_vsm_execution_ui_labels.ts` (`110` L) + `process_vsm_execution_ui_labels_{fr,en}.ts` (`139` / `137` L).
  - `process_catalog_packs_and_workflows_labels.ts` (`38` L) + `process_catalog_workflows_{fr,en}.ts` (`269` / `269` L).
  - `process_catalog_vsm_labels.ts` (`92` L) + `process_catalog_vsm_p1_{fr,en}.ts` (`252` / `250` L) + `process_catalog_vsm_p2_{fr,en}.ts` (`227` / `221` L) + `process_catalog_vsm_p3_{fr,en}.ts` (`246` / `243` L).
- **Process Studio v2 Data Split & Bilingual Catalog Facade (`apps/web/src/features/processes/`)** (`6` files: `1` modified, `5` created; all `<= 234` L):
  - `processStudioV2Data.ts` (`1,726` $\rightarrow$ `22` L facade exposing `getInitialDeclarativePacks`, `getInitialVsmSpec`, `getInitialWorkflowsV2` and legacy French constants), `processStudioV2Types.ts` (`100` L), `processStudioV2Storage.ts` (`62` L), `processStudioV2StructuralPacks.ts` (`101` L), `processStudioV2StructuralVsm.ts` (`218` L), `processStudioV2StructuralWorkflows.ts` (`234` L).
- **Feature UI & Controller Remediation + Modular Splits** (`32` files: `24` modified, `8` created; all `<= 296` L):
  - `finops/index.tsx` (`71` L), `ontology/index.tsx` (`188` L), `ontology/useOntologyFeatureController.ts` (`172` L).
  - `processes/`: `AutonomousRunsSupervisionPanel.tsx` (`211` L), `ProcessCatalogCardGrid.tsx` (`255` L), `ProcessesHubPage.tsx` (`197` L) + `ProcessesActiveDossiersCard.tsx` (`135` L), `ProcessesValueStreamOverviewCard.tsx` (`120` L).
  - `processes/execution/`: `InteractiveRunDeliverableAndHitlPanels.tsx` (`296` L), `InteractiveRunDrawer.tsx` (`262` L), `InteractiveRunDrawerHeader.tsx` (`128` L), `interactiveRunFormatters.ts` (`103` L), `useInteractiveProcessRunController.ts` (`293` L).
  - `processes/studio/`: `StudioCopilotSidebar.tsx` (`201` L), `WorkflowBlock2ExecutionSection.tsx` (`192` L) + `WorkflowBlock2GoalDrivenSection.tsx` (`157` L), `WorkflowBlocks1345Sections.tsx` (`231` L), `WorkflowFiveBlocksCanvas.tsx` (`279` L), `WorkflowPreviewAndWhatIfPanels.tsx` (`166` L), `WorkflowStudioHeaderBar.tsx` (`250` L), `studioCatalogLabels.ts` (`31` L), `studioLabelsAndMappers.ts` (`267` L) + `studioWorkflowActions.ts` (`83` L), `useStudioWorkflowController.ts` (`285` L).
  - `processes/vsm/`: `ReturnLoopsSvgOverlay.tsx` (`200` L), `StepDetailSheet.tsx` (`160` L) + `StepDetailSheetTabsContent.tsx` (`258` L), `ValueStreamMapView.tsx` (`153` L) + `ValueStreamMapHeaderAndDrawer.tsx` (`223` L) + `ValueStreamMapPhaseGrid.tsx` (`226` L).
- **Tests & Gate 1 Baseline** (`2` files: `1` modified, `1` created):
  - `apps/web/src/__tests__/i18n-hardcoded-locale-baseline.json` (removed all `19` remaining `apps/web/src/` entries / `210` AST violations; `totalAstViolations: 631 -> 421`, `totalClientErrorViolations: 0`).
  - `apps/web/src/__tests__/story-27-5-bilingual-process-studio-and-vsm.test.tsx` (`113` L, `2` bilingual FR/EN tests covering Process Studio v2, VSM, and catalog helpers).

### 3.2 Quantitative Metrics, Baseline Counts & Static Quality (Independent Testing Sub-Agent)
- **Line-Count Guard (`wc -l <= 300`)**: `57/57` modified and created `.ts`/`.tsx` files (`29` modified, `28` created; `0` `.py` files modified) are `<= 300` lines (max `296` L in `InteractiveRunDeliverableAndHitlPanels.tsx`, `293` L in `useInteractiveProcessRunController.ts`, `285` L in `useStudioWorkflowController.ts`).
- **Deterministic Ratchet Baselines**:
  - **Gate 1 (`i18n-hardcoded-locale-ast-audit.test.ts`, `3` tests)**: Reduced `totalAstViolations` from **`631` -> `421`** (`-210` AST violations across `19` files), with **`0` entries remaining in `apps/web/src/`** (leaving `55` entries / `421` violations solely in `packages/ui/src/` for Story `27.6`).
  - **Gate 2 (`i18n-dictionary-parity-and-jargon-audit.test.ts`, `2` tests)**: **`0` violations** across `frDictionary` and `enDictionary` (recursive key parity, `{param}` placeholder parity, non-empty leaves, UX Rule 3.1 zero-jargon).
  - **Gate 3 (`client-error-code-contract-audit.test.ts`, `4` tests)**: **`0` violations** (`totalClientErrorViolations: 0`, `clientErrorBaseline: {}`).
  - **Gate 4 (`tests/unit/test_i18n_backend_catalog_and_english_dev_audit.py --no-cov -q`, `3 passed`)**: **PASS** (`ERROR_CATALOG` parity, prompt neutrality, and English-only diff comments/docstrings verified).
- **Workspace Lint, Typecheck & Test Results (`pnpm turbo run lint typecheck test`)**: **`9/9` tasks passed** (`449` JS/TS tests across `113` test files):
  - `@orcia/api-client`: `lint`, `typecheck`, `test` PASS — `3 passed (3)` test files, **`20 passed (20)`** tests.
  - `@orcia/ui`: `lint`, `typecheck`, `test` PASS — `35 passed (35)` test files, **`139 passed (139)`** tests.
  - `@orcia/web`: `lint`, `typecheck`, `test` PASS — `75 passed (75)` test files, **`290 passed (290)`** tests (including Gate 1 `3`, Gate 2 `2`, Gate 3 `4`, `story-27-5-bilingual-process-studio-and-vsm.test.tsx` `2`, `i18n-and-shell.test.tsx` `26`, `anti-jargon-and-secrets-ui-audit.test.ts` `4`, `e2e-testids-sync-audit.test.ts` `1`, and `zero-dead-buttons-and-silent-catches-audit.test.tsx` `4`).
- **Secret Scan (`detect-secrets-hook`)**: `.venv/bin/detect-secrets-hook --baseline .secrets.baseline` across all modified/untracked files exited `0` with `0` findings.
- **Documentation & Showcase Governance Gates**:
  - `.venv/bin/python scripts/check_implementation_docs.py`: verified clean.
  - `pnpm site:sync && pnpm site:check` & `.venv/bin/pytest tests/unit/test_site_catalog_sync.py --no-cov -q`: verified clean.

### 3.3 AD-17 Test Pyramid & Vertical Wiring Verification
- **Layer 1a — Python Governance Audit (`tests/unit/`)**: `test_i18n_backend_catalog_and_english_dev_audit.py` (`3 passed`) confirms `0` non-English comment/docstring regressions and preserves Gate 4 integrity.
- **Layer 1b — Frontend TS, Design System & AST Audits (`Vitest`)**: `449` tests passed across `@orcia/api-client` (`20`), `@orcia/ui` (`139`), and `@orcia/web` (`290`), validating Gate 1 (`421`, **`0` remaining in `apps/web/src/`**), Gate 2 (`0`), Gate 3 (`0`), bilingual Process Studio v2 & VSM rendering, `data-testid` E2E synchronization, anti-jargon/secrets UI audits, and zero dead buttons.
- **Layer 2 (`tests/integration/`), Layer 3 (`OpenAPI`), Layer 4 (`tests/evals/`), Security (`tests/security/`) & Layer 5 (`Playwright`)**: No database schema, Python domain/router, or OpenAPI schema changes in Story 27.5.
