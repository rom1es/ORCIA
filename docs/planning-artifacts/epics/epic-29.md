## Epic 29: Canonical Page Headers (`<OrciaPageHeader />`), Multi-Workspace Scope & `CONFIDENTIAL_RESTRICTED` Hardening, Visual Grammar & Cross-Screen Consistency (`Stories 29.1`..`29.7`)

Standardize every primary and secondary ORCIA screen onto a single two-tier `<OrciaPageHeader />` primitive, resolve global `Espace actif` (`"Tous mes espaces"` / `scope-global`) runtime 404/403 bugs, enforce strict explicit-membership isolation for `CONFIDENTIAL_RESTRICTED` (`"Confidentiel isolé"`) workspaces via a real `PATCH /api/v1/workspaces/{id}` endpoint with optimistic rollback and single aligned alert banners, separate Primary Cobalt CTAs from tabs and filters, and align Zone 4 Contextual Help, monochrome `<OrciaIcon />` usage, and bilingual `fr`/`en` copy (`UH-01`..`UH-15`, tracked in `docs/planning-artifacts/sprint-change-proposal-2026-11-24-epic-29-ui-headers-scope-and-screen-consistency.md`).

### Story 29.1: Multi-Workspace Scope Resolution (`Mes Processus` 404 & `FinOps` 403/Scope-Pill Fixes) & Error-vs-Empty Mutual Exclusion (`UH-01`, `UH-02`)

As a Team Lead or Business User (`Claire UJ-8`, `Marc UJ-5`) browsing ORCIA with `"Tous mes espaces"` (`scope-global`) or a BU node selected in the left sidebar,
I want `Mes Processus` (`"Exécutions automatisées sous contrat"`) and `FinOps` to resolve authorized scopes cleanly without triggering false HTTP 404/403 banners, unselected scope pills, or contradictory empty states underneath error alerts,
So that global and delegated views show accurate, RBAC-scoped telemetry on first load.

**Lot:** 1 — P0 Runtime & Scope Fixes. **Dependencies:** `Epic 28`. **Agent:** `bmad-dev-worker` (`flash`).
**Findings covered:** `UH-01`, `UH-02`.
**CAPs covered:** `CAP-140`, `CAP-200`, `CAP-201`.
**Impacted files:** `apps/web/src/features/processes/AutonomousRunsSupervisionPanel.tsx`, `packages/api-client/src/domains/autonomousSupervision.ts`, `apps/api/src/orcia_api/routers/autonomous_supervision.py`, `apps/web/src/features/finops/useFinopsDashboardController.ts`, `packages/ui/src/primitives/finops/FinopsGovernanceDashboardView.tsx`, `apps/api/src/orcia_api/routers/_finops_scope_guards.py`, `apps/web/src/i18n/locales/{fr,en}.ts`, `tests/integration/`, `apps/web/src/__tests__/`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/29-1-multi-workspace-scope-resolution-processes-404-finops-403-and-error-empty-guard-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** an authenticated user opening `Mes Processus` with `"Tous mes espaces"` (`scope-global`) or any non-UUID workspace scope selected
**When** `AutonomousRunsSupervisionPanel` loads autonomous runs
**Then** the frontend never calls `GET /api/v1/workspaces/{non-uuid}/autonomous-runs` (supporting an authorized multi-workspace aggregation query or scoped workspace prompt cleanly), zero HTTP `404 ERR_RESOURCE_NOT_FOUND` banner is rendered, and whenever an API error banner is visible (`error !== null`), the contradictory `"Aucune exécution automatisée..."` empty-state block is suppressed.

**Given** a `TEAM_LEAD` (without global platform audit rights) opening `FinOps` under `"Tous mes espaces"` (`scope-global`) or a `BU` node
**When** `useFinopsDashboardController` initializes scope and renders `FinopsGovernanceDashboardView`
**Then** it defaults automatically to the caller's highest authorized FinOps scope (`TEAM` for `TEAM_LEAD`, `BU` for `BU_DIRECTOR`, `GLOBAL` only for `PLATFORM_ADMIN`/`OBSERVER`), hides or disables unauthorized scope pills (`Plateforme entière`), properly maps `"BU"` scopes so **exactly one** scope pill is selected at all times, suppresses the `"Aucune consommation..."` white card when an error banner is shown, and removes misleading `"demandez l'habilitation dans Mon Organisation"` instructions (`AD-21` / `AD-17` Layer 2 PG18 integration verified).

---

### Story 29.2: Scoped `PATCH /api/v1/workspaces/{id}`, Strict `CONFIDENTIAL_RESTRICTED` Isolation Enforcement, Optimistic Rollback & Single Error Banner (`UH-03`, `UH-04`)

As an ORCIA Team Lead, Workspace Member, or SecOps Reviewer (`Marc UJ-5`, `Sophie UJ-6`),
I want workspace updates to persist through a dedicated `ScopeAccessGuard`-protected `PATCH /api/v1/workspaces/{id}` endpoint with strict `CONFIDENTIAL_RESTRICTED` explicit-membership enforcement across all backend surfaces, zero corrupted `localStorage`/UI state on error, and a single properly aligned alert banner,
So that authorized workspace updates succeed cleanly, failed mutations roll back truthfully, and `"Confidentiel isolé"` truly isolates sensitive workspaces.

**Lot:** 1 — P0 Security & Persistence Integrity. **Dependencies:** `Epic 28` (resolves `ACTION_ITEM-28.1` item 1). **Agent:** `bmad-dev-worker` (`flash`) + `bmad-architect-worker` (`pro`) security check.
**Findings covered:** `UH-03`, `UH-04`.
**CAPs covered:** `CAP-050`, `CAP-067`, `CAP-080`, `CAP-010`, `CAP-062`.
**Impacted files:** `apps/api/src/orcia_api/routers/org_and_workspaces.py`, `apps/api/src/orcia_api/schemas/org_and_workspaces.py`, `packages/orcia-core/src/orcia_core/permissions/evaluator.py`, `packages/orcia-core/src/orcia_core/ontology/permissions.py`, `apps/api/src/orcia_api/routers/ontology_and_rag.py`, `apps/api/src/orcia_api/routers/workspace_governance.py`, `apps/api/src/orcia_api/routers/workspace_datasources.py`, `packages/orcia-core/src/orcia_core/rag/_internal/sql_federated_search.py`, `packages/api-client/src/generated/`, `apps/web/src/components/platformSetupContextTypes.ts`, `apps/web/src/components/usePlatformSetupHydrationEffect.ts`, `apps/web/src/components/ShellAuthFallbackView.tsx`, `apps/web/src/features/workspaces/index.tsx`, `apps/web/src/features/workspaces/WorkspaceCompactHeader.tsx`, `tests/security/`, `tests/integration/`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/29-2-scoped-workspace-patch-confidential-isolation-rollback-and-single-banner-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** an authorized `TEAM_LEAD`, `BU_DIRECTOR`, or `PLATFORM_ADMIN` updating a non-personal workspace via `@orcia/api-client`
**When** `PATCH /api/v1/workspaces/{id}` is invoked (replacing admin-only `PUT /api/v1/bootstrap/platform-setup-state`)
**Then** `ScopeAccessGuard` authorizes mutations on owned team workspaces (rejecting `READ_ONLY_OBSERVER`, cross-team users, and in-place visibility transitions on `PRIVATE_USER` / `personal-*` spaces with RFC 9457 `HTTP 403`), regenerates OpenAPI 3.1 SDK (`0-diff`), persists changes in PG18, and guarantees that if any workspace mutation fails, React state and `localStorage` roll back completely without mutating `Espace personnel` into `Équipe`, while rendering **at most one** `<OrciaAlertBanner />` (eliminating `"Synchronisation plateforme"` duplicate throws, the `"⚠️ "` prefix colliding with `<OrciaIcon name="cross" />`, and the `32px` `px-4` width mismatch).

**Given** a workspace configured as `CONFIDENTIAL_RESTRICTED` (`"Confidentiel isolé"`)
**When** accessed by a same-team member without explicit `workspace_memberships`, a parent `BU_DIRECTOR`, or a non-member `PLATFORM_ADMIN` across `evaluator.py`, `ontology/permissions.py`, `POST /api/v1/ontology-rag/rag/search`, `workspace_governance.py`, `workspace_datasources.py`, and `⌘K` Federated Search (`sql_federated_search.py`)
**Then** all business content (documents, Blackboard, Runs, `3_WORKSPACE` ontology items, datasources, governance, and search results) is strictly denied/filtered (`architecture.md:L692`), reserving visibility strictly to explicit `workspace_memberships` while retaining aggregate FinOps counters (`finops_cost_usd`) for authorized parents/admins (`tests/security/` + real PG18 `testcontainers` verified).

---

### Story 29.3: `Mon Assistant` Prompt & Jargon Sanitization, Speed/Tier Alignment & RBAC-Gated Composer Notices (`UH-05`)

As an ORCIA Team Lead or Business User (`Hélène UJ-1`, `Lucas UJ-7`) conversing with `Mon Assistant`,
I want assistant greetings and system framing to hide raw workspace UUIDs, internal `SPEED_1_FAST` constants, hardcoded `"PM"` fallbacks, and nonexistent `orcia://sources/*` URIs, align displayed model/effort metadata with the active speed mode, and gate admin-only settings links by RBAC,
So that `Mon Assistant` speaks in accurate business language without leaking technical plumbing or broken navigation links.

**Lot:** 1 — P0 Assistant Coherence & RBAC. **Dependencies:** `Epic 26`, `Epic 27`. **Agent:** `bmad-dev-worker` (`flash`).
**Findings covered:** `UH-05`.
**CAPs covered:** `CAP-070`, `CAP-071`, `CAP-075`, `CAP-190`.
**Impacted files:** `packages/orcia-core/src/orcia_core/orchestration/assistant_prompt_preview.py`, `packages/orcia-core/src/orcia_core/orchestration/assistant_governance_models.py`, `packages/orcia-core/src/orcia_core/orchestration/assistant_prompt_locales.py`, `packages/ui/src/primitives/AssistantSpeedSelectorAndStreamView.tsx`, `packages/ui/src/primitives/AssistantStickyPromptFooter.tsx`, `apps/web/src/features/inbox/InboxDisabledBanner.tsx`, `apps/web/src/features/inbox/AssistantNoEmbeddingBanner.tsx`, `apps/web/src/i18n/locales/{fr,en}.ts`, `tests/unit/`, `apps/web/src/__tests__/`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/29-3-assistant-prompt-sanitization-speed-tier-alignment-and-rbac-notices-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** an authenticated user (such as `TEAM_LEAD`) chatting in `Mon Assistant` on a workspace with `0` attached sources and no embedding model configured
**When** a turn executes and the response renders
**Then** the assistant context uses the workspace human-readable name (or active multi-workspace label, never raw UUIDv7), localized human-readable speed labels (never `SPEED_1_FAST`), the user's real active role/hat (never hardcoded `"PM (Product Manager)"`), and **only** genuinely attached sources (omitting unattached `orcia://sources/repo-main` defaults and nonexistent `@spec-architect` / `@security-reviewer` handles), while response footer metadata matches the active speed/tier/effort selection without contradiction.

**Given** the composer notice area above the `Mon Assistant` input when embedding or tools are unavailable
**When** rendered for a non-`PLATFORM_ADMIN` user (`TEAM_LEAD`, `MEMBER`)
**Then** the clickable `Configurer dans Administration › Modèles IA →` action link is hidden or replaced by plain administrator-contact guidance (`AD-21`), and informational notices collapse cleanly into a compact non-stacked status line preserving vertical chat height.

---

### Story 29.4: Canonical `<OrciaPageHeader />`, `<OrciaTabStrip />`, `<OrciaDataCard />`, Strict Cobalt Visual Grammar & Disabled Secondary Button Tokens (`UH-06`, `UH-07`)

As a Frontend Developer or UX Designer implementing ORCIA screens under Direction C,
I want `@orcia/ui` to provide a single canonical `<OrciaPageHeader />` primitive, a dedicated `<OrciaTabStrip />`, an `<OrciaDataCard />` surface wrapper, strict three-tier visual distinction between Primary CTAs, Tabs, and Filters, and proper disabled opacity tokens for `.orcia-ds-btn-secondary`,
So that every screen shares one unmistakable structural grammar and disabled buttons are never visually mistaken for active controls.

**Lot:** 2 — P1 Shared Design System Primitives. **Dependencies:** `Epic 28`. **Agent:** `bmad-dev-worker` (`flash`).
**Findings covered:** `UH-06`, `UH-07`.
**CAPs covered:** `CAP-060`, `CAP-100`.
**Impacted files:** `packages/ui/src/primitives/OrciaPageHeader.tsx` (new), `packages/ui/src/primitives/OrciaTabStrip.tsx` (new), `packages/ui/src/primitives/OrciaDataCard.tsx` (new), `packages/ui/src/index.ts`, `packages/ui/src/styles/tokens-palette.css`, `packages/ui/src/styles/tokens-components.css`, `apps/web/src/components/ModuleWorkspaceView.tsx`, `docs/planning-artifacts/ux-designs/ux-ORCIA-2026-10-24/DESIGN.md`, `packages/ui/src/__tests__/`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/29-4-canonical-page-header-tab-strip-data-card-and-visual-grammar-tokens-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** the `@orcia/ui` component library (`packages/ui/src/index.ts`)
**When** `<OrciaPageHeader />`, `<OrciaTabStrip />`, and `<OrciaDataCard />` are exported and tested in isolation
**Then** `<OrciaPageHeader />` enforces the two-tier `.orcia-bento-card` anatomy (Tier 1: monochrome `<OrciaIcon />`, `<h1>` at `var(--font-size-h2)`, optional context badge, 1-line subtitle, right-aligned Secondary + at-most-one Primary Cobalt CTA; Tier 2 optional: `<OrciaTabStrip />` + Scope Bar; aligned alert slot strictly beneath the header card) while `<OrciaTabStrip />` renders underline/segmented tabs visually distinct from solid Cobalt primary buttons and neutral filter/scope pills.

**Given** disabled secondary/ghost buttons and `ModuleWorkspaceView`
**When** `.orcia-ds-btn-secondary:disabled` and `.orcia-ds-btn-ghost:disabled` are rendered in CSS (`tokens-components.css`) and `ModuleWorkspaceView` wraps module routes
**Then** disabled secondary/ghost buttons apply `opacity: 0.48; cursor: not-allowed; pointer-events: none;` matching primary (`0.48`) and danger (`0.50`) tokens, `ModuleWorkspaceView` uses semantic `<h1>` via `<OrciaPageHeader />` instead of `16px <strong>`, and `packages/ui` preserves zero forbidden imports (`@tanstack/react-router`, `@orcia/api-client`, zero raw hex outside `tokens*.css`).

---

### Story 29.5: Header & Layout Convergence — `Mon Assistant`, `Mes Processus`, `Mes Agents` & `FinOps` (`UH-06`, `UH-09`, `UH-11`, `UH-12`)

As an ORCIA User navigating across `Mon Assistant`, `Mes Processus`, `Mes Agents`, and `FinOps`,
I want all four operational screens to adopt `<OrciaPageHeader />`, `<OrciaTabStrip />`, and `<OrciaDataCard />` cleanly — removing tab-switch header wrapping, misplaced MCP/IDE cards, competing solid-blue CTAs, and bare canvas headers/tables,
So that every screen exhibits predictable hierarchy, zero layout jump across tabs, and clean card framing on `#EAF2FB`.

**Lot:** 3 — P1 Screen Convergence (Batch A). **Dependencies:** `29.1`, `29.3`, `29.4`. **Agent:** `bmad-dev-worker` (`flash`).
**Findings covered:** `UH-06`, `UH-09`, `UH-11`, `UH-12`.
**CAPs covered:** `CAP-071`, `CAP-090`, `CAP-091`, `CAP-140`, `CAP-200`.
**Impacted files:** `apps/web/src/features/inbox/AssistantTopToolbar.tsx`, `apps/web/src/features/inbox/index.tsx`, `apps/web/src/features/processes/ProcessesHubPage.tsx`, `apps/web/src/features/processes/ProcessesActiveDossiersCard.tsx`, `packages/ui/src/components/AgentsAndSkillsHeaderAndToolbar.tsx`, `packages/ui/src/components/AgentsAndSkillsManagerView.tsx`, `packages/ui/src/primitives/finops/FinopsGovernanceDashboardView.tsx`, `apps/web/src/i18n/locales/{fr,en}.ts`, `apps/web/src/__tests__/`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/29-5-header-layout-convergence-assistant-processes-agents-and-finops-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** `Mon Assistant` and `Mes Processus`
**When** rendered
**Then** both mount `<OrciaPageHeader />` with semantic `<h1>`, monochrome icon, 1-line subtitle, and separated Tier-2 navigation/primary CTA (`+ Nouvelle conversation` vs `Conversations` / `Dossiers` on `Mon Assistant`; max 1 solid Cobalt `+ Nouveau processus` header CTA on `Mes Processus` while repeated `Lancer ce processus` card actions use secondary/outline Cobalt styling, and `"Mon Compte"` titles no longer leak under global `"Tous mes espaces"` scope).

**Given** `Mes Agents` (`Mes Agents` | `Compétences` | `Serveurs d'outils & MCP`) and `FinOps`
**When** switching tabs or viewing `FinOps`
**Then** `Mes Agents` unwraps the outer mega-card, moves the 3 tabs into Tier 2 (`<OrciaTabStrip />`) eliminating the Tab-3 header wrap jump (`CLS = 0`), scopes the Agent/Skill KPIs and filter bar strictly to tabs 1–2 (hidden on `Serveurs d'outils & MCP`), and separates outbound MCP Server management from the inbound IDE access card (replacing raw `assistant.ask` / `agent.invoke` / `agent.list_exposed` RPC jargon with human-readable capability labels); `FinOps` wraps its header in `<OrciaPageHeader />` (with non-truncated `Journal d'activité` and distinct scope pills) and wraps its data table inside `<OrciaDataCard />` (`<= 300` lines per modified file).

---

### Story 29.6: Header & Layout Convergence — `Mes Espaces`, `Mon Organisation`, `Aide` & Secondary Routes (`UH-06`, `UH-08`, `UH-10`, `UH-13`)

As an ORCIA User navigating `Mes Espaces`, `Mon Organisation`, `Aide`, and secondary views (`/cockpit`, `/settings`, `/settings/packs`, `/profile`, `/activity`),
I want `Mes Espaces` stripped of its dead `Phase` dropdown, duplicate workspace switcher, and numbered `1.`–`5.` tabs, `Mon Organisation` actions unified in `<OrciaPageHeader />` with accurate sibling badges, and `Aide` expanded cleanly across the full workspace width,
So that workspace configuration, org hierarchy, help resources, and secondary routes match the exact same Direction C layout grammar.

**Lot:** 3 — P1 Screen Convergence (Batch B). **Dependencies:** `29.2`, `29.4`. **Agent:** `bmad-dev-worker` (`flash`).
**Findings covered:** `UH-06`, `UH-08`, `UH-10`, `UH-13`.
**CAPs covered:** `CAP-058`, `CAP-060`, `CAP-064`, `CAP-067`, `CAP-080`, `CAP-203`.
**Impacted files:** `apps/web/src/features/workspaces/WorkspaceCompactHeader.tsx`, `apps/web/src/features/workspaces/WorkspaceMembersAndSettingsTab.tsx`, `apps/web/src/routes/organization.tsx`, `apps/web/src/routes/SettingsOrganizationUnitsBlock.tsx`, `apps/web/src/routes/SettingsOrganizationUnitRow.tsx`, `apps/web/src/routes/help.tsx`, `packages/ui/src/primitives/HelpCenterCatalogView.tsx`, `apps/web/src/components/ShellContainer.tsx`, `apps/web/src/features/cockpit/index.tsx`, `apps/web/src/routes/settings.tsx`, `apps/web/src/features/settings/packs/PacksRegistryPage.tsx`, `packages/ui/src/primitives/UserProfileOverviewPage.tsx`, `packages/ui/src/primitives/ActivityLogExplorerView.tsx`, `apps/web/src/i18n/locales/{fr,en}.ts`, `apps/web/src/__tests__/`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/29-6-header-layout-convergence-workspaces-organization-help-and-secondary-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** `Mes Espaces`
**When** rendered for a personal or team workspace
**Then** the screen uses `<OrciaPageHeader />` + `<OrciaTabStrip />` without the duplicate `workspaces-active-switcher-select`, without the dead `Phase : Construction / Exploitation / Évolution` `<select>` and header badge, without the duplicate `Glossaire métier` header button, and without numeric `1.`–`5.` tab prefixes (`Accostage & Vue d'ensemble` | `Documents & Sources` | `Livrables & Artefacts` | `Glossaire & Règles Métiers` | `Membres & Paramètres de l'espace`), while team-workspace visibility settings (with plain-language mode explanations, powered by `PATCH /api/v1/workspaces/{id}` from `Story 29.2`) live inside Tab 5 (`Membres & Paramètres`) and remain locked on `PRIVATE_USER` spaces.

**Given** `Mon Organisation`, `Aide`, and secondary routes (`/cockpit`, `/settings`, `/settings/packs`, `/profile`, `/activity`)
**When** rendered
**Then** `Mon Organisation` moves `+ Inviter un utilisateur` & `+ Nouvelle unité` into `<OrciaPageHeader />` actions, removes the redundant inline `Repères` box, distinguishes ancestor units (`Contexte parent`) from sibling teams (`Autre équipe — lecture seule`), and hides `Modifier`/`Supprimer` write buttons on read-only rows; `Aide` mounts `<OrciaPageHeader title="Centre d'Aide" />` (putting the Showcase link as a secondary action or card instead of stealing the header slot), removes the `max-w-4xl` half-screen void, and marks/disables the TopBar `Aide` toggle when active on `/help`; and secondary routes standardize onto `<OrciaPageHeader />`.

---

### Story 29.7: Monochrome Icon Purge, Copy/Jargon Hygiene, Zone 4 Contextual Help Alignment, Automated Header CI Guard & Epic 29 Closure (`UH-14`, `UH-15`)

As an ORCIA Product Owner & Maintainer (`Hélène UJ-1`, `Sally`, `Winston`),
I want raw Unicode emojis purged from headers/tabs in favor of `<OrciaIcon />`, remaining FR/EN jargon, pluralization defects, and test fixtures cleaned up, Zone 4 Contextual Help synchronized with `DESIGN.md`, and an automated test gate locking header & visual grammar compliance,
So that all screens remain visually cohesive, bilingual, jargon-free, and immune to header drift regressions.

**Lot:** 4 — P2 Polish, Anti-Drift Lock & Closure. **Dependencies:** `29.5`, `29.6`. **Agent:** `bmad-dev-worker` (`flash`) + mandatory `bmad-architect-worker` (`pro`) closure gate.
**Findings covered:** `UH-14`, `UH-15` (and full `UH-01`..`UH-15` closure verification).
**CAPs covered:** `CAP-060`, `CAP-064`, `CAP-090`, `CAP-100`, `CAP-203`.
**Impacted files:** `apps/web/src/i18n/locales/governance_and_packs_labels_fr.ts`, `apps/web/src/i18n/locales/{fr,en}.ts`, `packages/ui/src/components/iconRegistry.ts`, `docs/help/{fr,en}/*.md`, `docs/planning-artifacts/ux-designs/ux-ORCIA-2026-10-24/DESIGN.md`, `apps/web/src/__tests__/page-header-structure-and-visual-grammar-audit.test.tsx` (new), `apps/web/e2e/`, `docs/product/capabilities.yaml`, `docs/implementation-artifacts/sprint-status.yaml`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/29-7-icon-purge-copy-hygiene-contextual-help-ci-guard-and-epic-29-closure-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** `apps/web` headers, tabs, buttons, and Zone 4 Contextual Help (`docs/help/{fr,en}/*.md`)
**When** inspected in both French (`fr`) and English (`en`) sessions
**Then** zero raw Unicode emojis (`🤖`, `🛠️`, `🔌`, `🔒`, `📁`, `📦`) appear in page headers, tabs, or primary action labels (replaced by `<OrciaIcon />`), zero technical jargon (`Temp 0.2 · 4096 tok`, `Skills`, `(/SKILLS)`), FR pluralization bugs (`1 actifs`, `1 réutilisables`), or seeded E2E fixtures (`Story 26.1 Regression Agent`) appear in UI text, and Zone 4 Contextual Help follows `DESIGN.md`'s 4-block structure accurately (fixing stale `Mes Espaces` filter copy, `Mon Organisation` Admin-help bleed, removed-`ⓘ` instructions in `Aide`, and `DESIGN.md` TopBar vs Bottom-Left `Mon Compte` spec alignment).

**Given** the automated anti-drift guard `page-header-structure-and-visual-grammar-audit.test.tsx` and full `AD-17` closure verification with `bmad-architect-worker` (`pro`)
**When** closing Epic 29
**Then** the CI audit confirms every routed main screen mounts `<OrciaPageHeader />` with a single semantic `<h1>` and at most one primary solid-Cobalt header CTA, `ruff check`, `ruff format --check`, `mypy --strict`, `lint-imports` (`5/5`), `lint_spine.py` (`0 findings`), `export_openapi.py --check` (`0-diff`), full `tests/unit` + `tests/security` + impacted PG18+Redis `testcontainers` suites (`>= 90%` coverage), `pnpm turbo run lint typecheck test`, Desktop Playwright E2E across all 8 audited screens (`env -u ORCIA_E2E_SEED_FIXTURES`, `fr` & `en`), `scripts/check_implementation_docs.py`, and `pnpm site:sync && pnpm site:check` all pass, `CAP-xxx` entries remain `runtime`, GitNexus index refreshes cleanly, and `epic-29` transitions to `done`.

---
