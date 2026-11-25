# Story 29.7 — Monochrome Icon Purge, Copy/Jargon Hygiene, Zone 4 Contextual Help Alignment, Automated Header CI Guard & Epic 29 Closure (`UH-14`, `UH-15`)

- **Date**: 2026-11-25
- **Story / Sprint Key**: `29-7-icon-purge-copy-hygiene-contextual-help-ci-guard-and-epic-29-closure` (`Epic 29` / Lot 4)
- **Capability(ies)**: `CAP-060`, `CAP-064`, `CAP-090`, `CAP-100`, `CAP-203` — classification: `ux` / `hygiene`
- **Author / Context**: Tech Lead / Senior Dev implementation for `Story 29.7` (`UH-14`, `UH-15` and full Epic 29 exit lock). Covers `DESIGN.md` §Brand & Style #3–#4, §UI Rules #1/#3/#5, §Microcopy, `EXPERIENCE.md` §1.2 #1–#3, and `AD-17` Layers 1 & 5.
- **Associated Commits**: Pending final verification & closure gate

---

## 1. Needs Analysis & Tech Lead Impact Study (Pre-Implementation)

### 1.1 Context & Problem Statement
- **Mixed icon systems, technical jargon & FR pluralization defects (`UH-14`)**:
  - Even after Stories `29.4`–`29.6` converged screens onto `<OrciaPageHeader />`, `<OrciaTabStrip />`, and `<OrciaDataCard />`, raw Unicode emojis (`🤖`, `🛠️`, `🔌`, `🔒`, `📁`, `📦`, `🧠`, `📚`, `📄`, `🛡️`, `🌐`, `⚠️`, `✅`, `✕`) remain embedded in `apps/web/src/i18n/locales/*.ts` (headers, tab labels, card titles, badges, scope options, and action labels), `apps/web/src/components/shellScopeOptions.ts`, `apps/web/src/components/shellUnifiedScope.ts`, and `packages/ui/src/components/icons/iconRegistry.ts` (consumed via `getOrciaIconGlyph(...)` in several `@orcia/ui` and `apps/web` views).
  - Agent cards in `packages/ui/src/components/AgentStudioCardBadgesAndPassport.tsx` still expose raw technical settings (`Temp 0.2 · 4096 tok` and raw tier keys like `team_default`) and English `"SKILLS (/SKILLS)"` / `"(Skills)"` noise inside the French interface (`agents_and_skills_studio_labels_fr.ts`, `governance_and_packs_labels_fr.ts`).
  - `AgentsAndSkillsHeaderAndToolbar.tsx` appends fixed plural suffixes (`1 actifs`, `1 réutilisables`) regardless of singular count `1`.
  - Residual test fixture references (`Story 26.1 Regression Agent`, `Verify agent execution`) exist in `tests/security/test_story_26_1_assistant_security_hardening.py` and must remain strictly isolated to that test's ephemeral `TestClient` without ever leaking into seeded/dev bootstrap or E2E workspace states.
- **Zone 4 Contextual Help structural & content drift (`UH-15`)**:
  - `packages/ui/src/primitives/ContextualHelpColumnView.tsx` renders `<HelpTargetedSectionsList />` **above** `<HelpCoreNarrativeBlocks />`, pushing `À quoi sert cet écran ?` and `EN N GESTES` below the fold on `Mon Assistant`, `Mes Espaces`, `FinOps`, and `Mes Processus`.
  - `apps/web/src/components/_contextualHelpSections.ts:L33-L40` (`normalizeCanonicalHelpRoute`) routes `/organization` into `/settings`, causing `Mon Organisation` to display Administration help instead of its dedicated `/organization` guide (`docs/help/{fr,en}/organization.md`).
  - `docs/help/{fr,en}/spaces.md` and `apps/web/src/i18n/locales/contextual_help_catalog_{fr,en}.ts` still describe removed list filters (`« Tous »`, `« Espaces d'Équipe »`, `« Mes Espaces Privés »`), the removed `Phase` lifecycle selector, `Configuration ›`, and duplicate `Glossaire métier` header button.
  - `docs/help/{fr,en}/help.md` still instructs users to click removed `ⓘ` icons instead of the TopBar `Aide` / `Help` button.
  - `docs/planning-artifacts/ux-designs/ux-ORCIA-2026-10-24/DESIGN.md` still places `👤 Mon Profil` / `UserAccountDropdown` in `TopHeaderBar` instead of reflecting the live Bottom-Left Sidebar `Mon Compte` (`SidebarAccountPopover` + 5-tab `UserSettingsModalDialog`) and Story 29.4–29.7 visual rules.
- **Anti-drift lock**: No runtime & static audit test currently asserts across all 12 primary and secondary routes (in both `fr` and `en`) that every screen mounts `<OrciaPageHeader />` with a single semantic `<h1>`, at most one solid Cobalt header CTA, zero raw Unicode emojis in header/tab/action/scope text, and Zone 4 4-block ordering.

### 1.2 Exploration, GitNexus Impact Analysis, Refactoring & Technical Debt
- **GitNexus Impact Analysis (`repo: "ORCIA"`)**:
  - `gitnexus_query` & `gitnexus_cypher` on `ORCIA_ICONS`, `OrciaIcon`, `OrciaPageHeader`, `ContextualHelpColumnView`, `shellZone4HelpWiring`:
    - `ORCIA_ICONS` (`packages/ui/src/components/icons/iconRegistry.ts`) is consumed by `OrciaIcon.tsx`, `FourZoneShellTypes.ts`, `ScopeSwitcher.tsx`, `shellScopeOptions.ts`, `WorkspaceGlossaryAndOntologyTab.tsx`, and 4 Agent/Skill UI components (`AgentIdentityAndSkillsFields.tsx`, `AgentSixBlocksFormSections.tsx`, `SkillCreateFormDrawer.tsx`, `SkillDetailAndSandboxModal.tsx`). `icon-registry-centralization.test.tsx` (`Audit Gate 4`) relies on `ORCIA_ICONS[name].glyph` reactivity, so `<OrciaIcon />` SVG rendering must be preserved alongside `hasCustomGlyphOverride` while migrating UI call sites from `getOrciaIconGlyph(...)` to `<OrciaIcon />` and replacing raw Unicode emojis in `ORCIA_ICONS` fallback glyphs with clean monochrome symbols.
    - `OrciaPageHeader` (`packages/ui/src/primitives/OrciaPageHeader.tsx`) is mounted across all 8+ primary and secondary views (`ModuleWorkspaceView.tsx`, `CockpitFeaturePanel`, `AssistantTopToolbar`, `ProcessesHubPage`, `AgentsAndSkillsHeaderAndToolbar`, `WorkspaceCompactHeader`, `SettingsOrganizationUnitsBlock`, `FinopsGovernanceDashboardView`, `HelpCenterRouteView`, `SettingsHubView`, `PacksRegistryPage`, `UserProfileOverviewPage`, `ActivityLogExplorerView`).
    - `ContextualHelpColumnView` (`packages/ui/src/primitives/ContextualHelpColumnView.tsx`) is rendered exclusively by `ContextualHelpColumnAndCenter` (`ShellContextualHelpColumn.tsx` in Zone 4), so reordering `<HelpCoreNarrativeBlocks />` before `<HelpTargetedSectionsList />` immediately restores above-the-fold 4-block structure across every route while preserving `activeSectionId` highlighting and scroll-into-view.
- **Exploration & Key Findings**:
  - Grep across `apps/web/src/i18n/locales/*`, `packages/ui/src/`, `docs/help/{fr,en}/*.md` pinpointed all remaining emojis, `Temp {temperature} · {maxTokens} tok` occurrences, `COMPÉTENCES (/SKILLS)` / `(Skills)` copy, singular/plural KPI suffix mismatches, and `normalizeCanonicalHelpRoute("/organization") -> "/settings"`.
  - Verified `tests/security/test_story_26_1_assistant_security_hardening.py` is the sole file containing `Story 26.1 Regression Agent` / `Verify agent execution` (ephemeral in-memory `TestClient`, zero seed/bootstrap pollution).
- **Refactoring Opportunities & Emerging Technical Debt Mitigation**:
  - Extract a pure `formatAgentSettingsSummary(...)` helper in `packages/ui/src/components/AgentGovernanceTypesAndDefaults.ts` so both `AgentStudioCardBadgesAndPassport.tsx` and readiness checklist formatting share clean bilingual settings labels without `Temp ... · ... tok`.
  - Keep all modified and newly created files strictly `<= 300` lines. No new `Story N.Ma` debt ticket is required; all Epic 29 findings (`UH-01`..`UH-15`) close cleanly under `29.7`.

---

## 2. Implementation Plan

### 2.1 Data Schema & Alembic Migrations
- None (`0` schema or Alembic changes required for Story `29.7`).

### 2.2 Hexagonal Core, Orchestration & Workers (`packages/orcia-core/`, `apps/worker/`)
- Verify `packages/orcia-core/src/orcia_core/catalog/contextual_help_resolver.py` resolves `/organization` cleanly to `help-base-organization-{lang}`.
- Confirm zero seeded/bootstrap leaks of `Story 26.1 Regression Agent` or `Verify agent execution` in `packages/orcia-core/` or `infra/scripts/`.

### 2.3 Backend API, Security & Contracts (`apps/api/`, `packages/api-client/`)
- No HTTP schema changes (`export_openapi.py --check` stays `0-diff`).
- Keep `tests/security/test_story_26_1_assistant_security_hardening.py` scoped cleanly to its ephemeral `TestClient`.

### 2.4 User Interface & Experience (`apps/web/`, `packages/ui/`, `docs/help/`, `DESIGN.md`)
1. **Monochrome Icon Purge (`UH-14`)**:
   - Replace raw Unicode emojis with `<OrciaIcon />` SVGs in `AssistantTopToolbar.tsx`, `AiModelMappingRowCard.tsx`, `SettingsAiModelsSection.tsx`, `AgentAndSkillCreateForms.tsx`, `AgentSixBlocksFormSections.tsx`, `AgentIdentityAndSkillsFields.tsx`, `SkillCreateFormDrawer.tsx`, `SkillDetailAndSandboxModal.tsx`, `AgentStudioCardBadgesAndPassport.tsx`, and `WorkspaceGlossaryAndOntologyTab.tsx`.
   - Purge raw Unicode emojis from headers, tabs, card titles, primary CTAs, scope options, and badge labels across `apps/web/src/i18n/locales/*.ts`, `shellScopeOptions.ts`, `shellUnifiedScope.ts`, and `packages/ui/src/components/icons/iconRegistry.ts` (preserving `ORCIA_ICONS` API and `Audit Gate 4` reactivity).
2. **Copy / Jargon Hygiene & Bilingual Pluralization (`UH-14`)**:
   - Replace `Temp 0.2 · 4096 tok` and raw `team_default` in `AgentStudioCardBadgesAndPassport.tsx` & `AgentGovernanceTypesAndDefaults.ts` with human-readable bilingual settings (`Par défaut · Précis · Contexte 4k` / `Team default · Precise · 4k context`).
   - Remove English `"(/SKILLS)"` / `"(Skills)"` / `"(Skill)"` noise in `agents_and_skills_studio_labels_fr.ts` and `governance_and_packs_labels_fr.ts` (`COMPÉTENCES` in FR, `SKILLS` in EN).
   - Fix singular/plural KPI counts in `AgentsAndSkillsHeaderAndToolbar.tsx` (`1 actif` vs `N actifs`, `1 réutilisable` vs `N réutilisables`, `1 Pack/Équipe` vs `N Packs/Équipes`).
3. **Zone 4 Contextual Help Alignment (`UH-15`)**:
   - Reorder `ContextualHelpColumnView.tsx` so `<HelpCoreNarrativeBlocks />` renders immediately below `<HelpArticleHeaderBlock />` (keeping `À quoi sert cet écran ?` and `EN N GESTES` cleanly above the fold), followed by `<HelpTargetedSectionsList />`.
   - Fix `normalizeCanonicalHelpRoute` in `_contextualHelpSections.ts` so `/organization` maps to `/organization` (not `/settings`), and add dedicated `/organization` fallback & sections in `contextual_help_catalog_{fr,en}.ts` and `contextual_help_sections_{fr,en}.ts`.
   - Update `docs/help/{fr,en}/spaces.md`, `help.md`, `agents.md`, `assistant.md`, `gates.md`, `settings.md`, `workspaces.md` and `contextual_help_catalog_{fr,en}.ts` to remove stale `« Tous »`/`« Espaces d'Équipe »`/`Phase`/`ⓘ`/`Configuration ›` references.
4. **`DESIGN.md` Alignment**:
   - Update `docs/planning-artifacts/ux-designs/ux-ORCIA-2026-10-24/DESIGN.md` in English to document TopHeaderBar (`⌘K`, `Aide`/`Help`, `Notifications`), Bottom-Left Sidebar `Mon Compte` (`SidebarAccountPopover` + 5-tab `UserSettingsModalDialog`), monochrome `<OrciaIcon />` policy, and Zone 4 above-the-fold 4-block structure.

### 2.5 Test Pyramid Impact Analysis (`AD-17` — Layers 1 to 5 + Security)
- **Layer 1b (`Vitest` without `isJsdom`)**:
  - New CI guard `apps/web/src/__tests__/page-header-structure-and-visual-grammar-audit.test.tsx` (`<= 300` L) mounting all 12 primary & secondary routes (`/cockpit`, `/assistant`, `/processes`, `/agents`, `/spaces`, `/organization`, `/finops`, `/help`, `/settings`, `/settings/packs`, `/profile`, `/activity`) in both `"fr"` and `"en"`, verifying `<OrciaPageHeader />`, single `<h1>`, `<= 1` `.orcia-ds-btn-primary` in `<header>`, zero raw Unicode emojis in headers/tabs/actions/scope options, zero duplicate alert banners, and Zone 4 4-block priority order.
  - Update impacted UI/web tests (`agentsAndSkillsLabelsFixture.ts`, `agents-and-skills.test.tsx`, `scope-switcher-and-org-sync.test.tsx`, `i18n-and-shell.test.tsx`, `story-24-3-remote-test-bench-and-mcp-exposure.test.tsx`, `story-29-5-core-screens-header-convergence.test.tsx`, etc.) to match purified monochrome icons, pluralization, and clean copy.
- **Layer 1a & Security (`pytest`)**:
  - Verify `tests/unit/test_i18n_backend_catalog_and_english_dev_audit.py` passes (`100%` English comments/docstrings) and `tests/security/test_story_26_1_assistant_security_hardening.py` remains isolated and green.
- **Layer 5 (Dual-Server Playwright E2E `apps/web/e2e/`)**:
  - New `apps/web/e2e/29-epic29-canonical-headers-bilingual.spec.ts` (`<= 250` L) exercising all 8 primary screens (`/cockpit`, `/assistant`, `/processes`, `/agents`, `/spaces`, `/organization`, `/finops`, `/help`) in both French (`fr`) and English (`en`) under `env -u ORCIA_E2E_SEED_FIXTURES` after `resetDay0()`.

---

## 3. Summary of Changes & Results (Post-Implementation)

### 3.1 Created & Modified Files

Total diff scope: **111 files** (`104` modified, `7` created). Every production file and every new Story 29.7 test file satisfies `<= 300` lines (`apps/web/src/__tests__/i18n-and-shell.test.tsx` is a pre-existing legacy suite at `2,303` lines).

| Area / File | Action | Lines (`wc -l`) | Summary |
| :--- | :--- | :---: | :--- |
| **Created Story 29.7 Artifacts** | | | |
| `apps/web/e2e/29-epic-29-canonical-headers-bilingual.spec.ts` | Created | `194` | Bilingual (`fr`/`en`) Playwright audit across all 8 primary routes verifying `<OrciaPageHeader />`, single `<h1>`, `<= 1` Cobalt header CTA, zero raw Unicode emojis, Zone 4 ordering, PG18 persistence, and clean console/HTTP. |
| `apps/web/src/__tests__/page-header-structure-and-visual-grammar-audit.test.tsx` | Created | `274` | CI guard mounting all 12 primary & secondary routes in `fr` and `en` (`25` tests) asserting canonical header structure, `<= 1` Cobalt CTA, zero emojis, and Zone 4 4-block priority ordering. |
| `apps/web/src/features/shared/alertFeedback.ts` | Created | `28` | Shared typed alert banner feedback helper across workspace & feature surfaces. |
| `apps/web/src/features/workspaces/sources/WorkspaceSourceAttachBaseFields.tsx` | Created | `137` | Modular split keeping `WorkspaceSourceAttachModal.tsx` (`284` L) `<= 300` lines. |
| `packages/ui/src/__tests__/agents-and-skills-studio-and-governance.test.tsx` | Created | `282` | Split Studio & Governance UI test suite (`<= 300` L) covering purified monochrome icons and bilingual labels. |
| `packages/ui/src/__tests__/story233HelpFixture.ts` | Created | `58` | Extracted fixture keeping `story-23-3-contextual-help-design-blocks.test.tsx` (`289` L) `<= 300` lines. |
| `docs/implementation-artifacts/tech-lead-reports/29-7-...-tech-lead-report.md` | Created | — | This permanent Tech Lead report (`Sections 1–3`). |
| **Design System & `@orcia/ui` Components (`14` modified)** | | | |
| `packages/ui/src/components/icons/iconRegistry.ts` | Modified | `291` | Replaced raw Unicode emoji fallback glyphs in `ORCIA_ICONS` with monochrome symbols while preserving `Audit Gate 4` reactivity. |
| `packages/ui/src/primitives/ContextualHelpColumnView.tsx` | Modified | `153` | Reordered `<HelpCoreNarrativeBlocks />` before `<HelpTargetedSectionsList />` so Zone 4 narrative & key steps stay above the fold. |
| `packages/ui/src/shell/ScopeSwitcher.tsx` | Modified | `188` | Migrated scope selector icons to monochrome `<OrciaIcon />`. |
| `packages/ui/src/components/AgentAndSkillCreateForms.tsx` | Modified | `192` | Replaced raw emojis with monochrome `<OrciaIcon />`. |
| `packages/ui/src/components/AgentGovernanceReadiness.ts` | Modified | `106` | Cleaned agent governance readiness labels. |
| `packages/ui/src/components/AgentGovernanceTypesAndDefaults.ts` | Modified | `297` | Added pure `formatAgentSettingsSummary(...)` helper removing `Temp ... · ... tok` technical jargon. |
| `packages/ui/src/components/AgentIdentityAndSkillsFields.tsx` | Modified | `168` | Replaced raw emojis with `<OrciaIcon />` & purified FR/EN copy. |
| `packages/ui/src/components/AgentSixBlocksFormSections.tsx` | Modified | `273` | Replaced raw emojis with `<OrciaIcon />` across 6-block editor. |
| `packages/ui/src/components/AgentStudioCardBadgesAndPassport.tsx` | Modified | `249` | Applied human-readable bilingual settings summary & monochrome icons. |
| `packages/ui/src/components/AgentsAndSkillsHeaderAndToolbar.tsx` | Modified | `263` | Fixed singular vs. plural KPI counts (`1 actif` vs `N actifs`, `1 réutilisable` vs `N réutilisables`). |
| `packages/ui/src/components/SkillCreateFormDrawer.tsx` | Modified | `250` | Replaced raw emojis with `<OrciaIcon />`. |
| `packages/ui/src/components/SkillDetailAndSandboxModal.tsx` | Modified | `192` | Replaced raw emojis with `<OrciaIcon />`. |
| `packages/ui/src/__tests__/agents-and-skills.test.tsx`, `agentsAndSkillsLabelsFixture.ts`, `story-23-3-contextual-help-design-blocks.test.tsx` | Modified | `237` / `264` / `289` | Updated UI test expectations & fixtures for monochrome icons, pluralization, and Zone 4 block ordering. |
| **`apps/web` Components, Features, Routes, i18n & Tests (`72` modified)** | | | |
| `apps/web/src/components/_contextualHelpSections.ts`, `shellScopeOptions.ts`, `shellUnifiedScope.ts` | Modified | `52` / `231` / `121` | Fixed `normalizeCanonicalHelpRoute("/organization") -> "/organization"` and purged scope emojis. |
| `apps/web/src/features/**` (`21` files across `admin`, `catalog`, `gates`, `inbox`, `processes`, `workspaces`) | Modified | `21`–`297` | Replaced emojis with `<OrciaIcon />`, unified alert feedback, and kept all modules `<= 297` lines. |
| `apps/web/src/routes/SettingsAiModelsSection.tsx`, `settingsAiModelsPresets.ts` | Modified | `158` / `232` | Purged raw emojis from AI model configuration views & presets. |
| `apps/web/src/i18n/locales/*.ts` (`43` files) | Modified | `81`–`291` | Purged all raw emojis, removed English `(/SKILLS)`/`(Skills)` from FR labels, added `/organization` Zone 4 fallback & sections, fixed singular/plural copy, and removed stale help references. |
| `apps/web/src/__tests__/i18n-and-shell.test.tsx`, `scope-switcher-and-org-sync.test.tsx` | Modified | `2303` / `124` | Updated test assertions for purified icons, scope options, and bilingual copy. |
| **Help Docs, UX Spec & Python Audits (`17` modified)** | | | |
| `docs/help/{fr,en}/{agents,assistant,gates,help,settings,spaces,workspaces}.md` (`14` files) | Modified | `31`–`36` | Removed stale `« Tous »`, `« Espaces d'Équipe »`, `Phase`, `ⓘ`, and `Configuration ›` instructions. |
| `docs/planning-artifacts/ux-designs/ux-ORCIA-2026-10-24/DESIGN.md` | Modified | `212` | Aligned UX spec in English with TopHeaderBar, Bottom-Left Sidebar `Mon Compte`, monochrome `<OrciaIcon />`, and Zone 4 4-block structure. |
| `tests/unit/test_e2e_sql_coverage_audit.py`, `tests/unit/test_story_19_7_rag_reindexing_and_blocking.py` | Modified | `297` / `293` | Registered `29-epic-29-canonical-headers-bilingual.spec.ts` in the E2E SQL audit (`27` specs) and kept unit tests `<= 300` lines. |

### 3.2 Quantitative Metrics, Coverage & Static Quality
- **Python Coverage (`AD-17` Layer 1a)**:
  - Scoped Epic 29 Python branch coverage: **`98%`** (`70 passed` in `57.19s`, `615 stmts`, `7 miss`, `222 branch`, `9 brpart`) across all 8 Epic 29 modified Python modules.
  - Full `tests/unit`: **`175/175` files, `1,066` tests passed** (`orcia-core` domain branch coverage `--omit="*/_internal/*"`: **`90%`** across `22,539` stmts / `4,916` branches; raw with unexecuted `_internal` PG18 adapters: `84%`).
  - Post-E2E-edit audit gate: `test_e2e_sql_coverage_audit.py` + `test_i18n_backend_catalog_and_english_dev_audit.py` (`5 passed` in `16.30s`).
- **Frontend Coverage (`AD-17` Layer 1b)**:
  - Full `pnpm turbo run lint typecheck test --concurrency=1`: **`9/9` tasks green** (`@orcia/api-client`: `20`, `@orcia/ui`: `148`, `@orcia/web`: `354` = **`522` JS/TS tests**, `90/90` `@orcia/web` files).
  - Post-E2E-edit Vitest CI guard run: `e2e-testids-sync-audit.test.ts` (`1/1`) + `page-header-structure-and-visual-grammar-audit.test.tsx` (`25/25`) = **`26 passed` in `15.44s`**.
- **Static Quality & Architecture**:
  - `ruff check .`: `0` issues
  - `ruff format --check .`: `1746` files formatted (`0` diffs)
  - `mypy --strict`: `0` issues across `856` files
  - `lint-imports`: `5/5` contracts kept, `0` broken
  - `lint_spine.py`: `ok: true, 0 findings`
  - `export_openapi.py --check`: `0-diff`
  - `sync_site_catalog.py` + `--check` + `check_implementation_docs.py`: `0` errors
- **GitNexus Index & Impact (`npx gitnexus analyze --index-only .` & `gitnexus_detect_changes`)**:
  - Index refreshed: **`46,753` nodes | `127,433` edges | `786` clusters | `1,532` flows** (`67.3s`).
  - `gitnexus_detect_changes(repo="/home/romain/.gemini/antigravity/worktrees/ORCIA/audit_ui_headers", scope="all")`: `changed_count: 59`, `changed_files: 104`, `affected_count: 1,532`, `risk_level: critical` (expected blast radius from shared frontend FR/EN locale dictionaries in `apps/web/src/i18n/locales/*.ts`, `ORCIA_ICONS` in `packages/ui/src/components/icons/iconRegistry.ts`, and `ScopeSwitcher.tsx`, with zero production Python runtime edits).

### 3.3 AD-17 Test Pyramid & Vertical Wiring Verification
- **Layer 1a & 1b (Unit & Static Audits)**: `1,066` Python unit tests (`90%` `orcia-core` domain branch coverage; `98%` scoped Epic 29 branch coverage) and `522` JS/TS tests across `9/9` Turbo tasks (`@orcia/api-client` `20`, `@orcia/ui` `148`, `@orcia/web` `354`), including i18n Gates 1–4, `zero-dead-buttons-and-silent-catches-audit`, `e2e-testids-sync-audit`, and `page-header-structure-and-visual-grammar-audit` (`25/25`).
- **Layer 2 (`HTTP ➔ PostgreSQL 18` via `testcontainers-python`)**: **`3 passed`** (`test_story_29_1_*`, `test_story_29_2_*`, `test_story_7_4_*` on real `create_app()` Composition Root without overrides).
- **Layer 3 (API Contract & Architecture)**: `export_openapi.py --check` (`0-diff`), `lint-imports` (`5/5`), `lint_spine.py` (`0` findings), and `tests/contract` green.
- **Layer 4 (`$0` Evals) & Security (`tests/evals`, `tests/security`)**: **`181 passed` in `88.32s`** (`tests/security` + `tests/contract` + `tests/evals`), confirming zero leak of `Story 26.1 Regression Agent` and full `CONFIDENTIAL_RESTRICTED` / RBAC / SSRF enforcement.
- **Layer 5 (Dual-Server Playwright Desktop E2E, `env -u ORCIA_E2E_SEED_FIXTURES`, `--project=desktop-cockpit`)**: **`23 passed, 0 failed`** across 3 sequential batches (`12` spec files on real ephemeral PostgreSQL 18 + Redis 7.4):
  - **Batch 1 (`8 passed` in `2.1m`)**: `29-epic-29-canonical-headers-bilingual.spec.ts` (`1/1`, `22.7s`), `07-spaces-org-and-workspace-persistence.spec.ts` (`1/1`, `17.7s`), `11-screens-smoke-without-server-errors.spec.ts` (`2/2`, `13.4s` + `7.6s`), `shell.spec.ts` (`4/4`, `7.1s` + `5.9s` + `6.7s` + `7.6s`). *(Note: an initial Batch 1 run was interrupted externally by `SIGTERM` on the API/worker processes; isolated spec 29 passed `1/1` in `1.0m` and the full Batch 1 re-run passed `8/8` in `2.1m`.)*
  - **Batch 2 (`4 passed` in `1.2m`)**: `09-pack-builder-and-contextual-help.spec.ts` (`11.1s`), `12-processes-multi-workspace-and-global-scope.spec.ts` (`10.0s`), `13-finops-rbac-scope-and-error-guard.spec.ts` (`9.5s`), `14-auth-2fa-account-and-profile.spec.ts` (`10.3s`).
  - **Batch 3 (`11 passed` in `3.0m`)**: `15-organization-iam-secops-inbox-and-observer.spec.ts` (`3/3`, `16.1s` + `8.3s` + `8.1s`), `17-workspace-sources-codegraph-dna-and-ontology.spec.ts` (`4/4`, `7.1s` + `13.3s` + `14.6s` + `17.7s`), `20-process-studio-v2-finops-and-log-sink.spec.ts` (`2/2`, `16.7s` + `19.1s`), `21-assistant-citations-v5-audit-help-showcase.spec.ts` (`2/2`, `15.3s` + `8.2s`).
- **Epic 29 Closure**: All 7 stories (`29.1`–`29.7`) are `done`, `epic-29` is `done`, and `CAP-060`, `CAP-064`, `CAP-090`, `CAP-100`, `CAP-203` are verified `runtime` in `docs/product/capabilities.yaml`.
