## Epic 28: Unified "Mes Espaces" (`/workspaces`) 5-Tab Screen, Component De-Duplication & Direction C Sobriety (`Stories 28.1`..`28.4`)

Eliminate the 6-block vertical stacking, duplicate 3-tab vs 5-tab systems, redundant headers, raw `personal-<uuid>` slug leaks, permanent bottom-of-page DNA Starlark/glossary panels, and empty-state `0 / 0 / 0` counter/filter clutter on `/workspaces` (`WX-01`..`WX-06`, audited in `docs/planning-artifacts/sprint-change-proposal-2026-11-23-epic-28-workspaces-unification.md`), converging the screen onto a single compact workspace header synchronized with the global Sidebar Active Workspace Selector and a single canonical 5-tab container (`Accostage & Vue d'ensemble` | `Documents & Sources` | `Livrables & Artefacts` | `Glossaire & Règles Métiers` | `Membres & Paramètres de l'espace`) wired 100% to scoped PostgreSQL 18 truth.

> **Coordination Gate:** Do not start Story `28.1` until Epic 27 (`Stories 27.4` & `27.6` touching `apps/web/src/features/workspaces/` and `packages/ui/src/primitives/`) merges; rebase `feat/epic-28-workspaces-screen-unification` onto `main` first so all touched files inherit the bilingual `fr`/`en` dictionary architecture (`0` Gate 1/2/3 baseline).

### Story 28.1: Single Compact Workspace Header, Global Sidebar Scope Synchronization, Zero Raw UUID Leak & Workspace Switcher/Creation Flow (`WX-02`, `WX-06`)

As an ORCIA Workspace Contributor or Lead (`Hélène UJ-1`, `Karim UJ-9`, `Marc UJ-5`),
I want `/workspaces` ("Mes Espaces") to display a single compact workspace header synchronized directly with the global Sidebar Active Workspace Selector — without stacked redundant headers, duplicate workspace summary cards, or raw `personal-<uuid>` slugs — while preserving `+ Nouvel espace` modal creation and workspace switching,
So that I always know which workspace I am managing and never face competing workspace headers or technical UUID leaks.

**Lot:** 1 — Header & Scope Unification. **Dependencies:** `Epic 27 (27.4, 27.6)`. **Agent:** `bmad-dev-worker` (`flash`).
**Findings covered:** `WX-02`, `WX-06`.
**CAPs covered:** `CAP-067`, `CAP-080`.
**Impacted files:** `apps/web/src/routes/workspaces.tsx`, `apps/web/src/components/ModuleWorkspaceView.tsx`, `apps/web/src/features/workspaces/index.tsx`, `apps/web/src/features/workspaces/WorkspaceStudioCardsAndDetailView.tsx`, `apps/web/src/features/workspaces/WorkspaceStudioSummaryCard.tsx`, `apps/web/src/i18n/locales/{fr,en}.ts`, `apps/web/src/__tests__/`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/28-1-single-workspace-header-sidebar-scope-sync-and-zero-uuid-leak-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** an authenticated user navigating to `/workspaces` (or `/spaces`)
**When** the page renders
**Then** `WorkspacesFeaturePanel` renders **at most one compact page header** synchronized with the global Sidebar `activeWorkspaceId` (removing the duplicate secondary `<nav>`, stacked summary card headers, and generic redundant banner chrome), displays the workspace human-readable name, lifecycle phase badge, and visibility badge (`Personnel` / `Équipe`), exposes a clean compact workspace switcher (plus `+ Nouvel espace` modal trigger and team-sharing CTA when permitted), and hides **all** raw `personal-<uuid>` technical slugs or raw `orcia://workspaces/personal-<uuid>` strings from primary UI text (`EXPERIENCE.md` §1.2 #1).

**Given** a user switching workspaces via either the global Left Sidebar Active Workspace Selector or the compact `/workspaces` switcher
**When** changing from the personal workspace to a team workspace and reloading (`F5`)
**Then** both the Sidebar selector, `TopHeaderBar` breadcrumb, and `/workspaces` active header/tabs stay synchronized with persisted state, all touched files remain `<= 300` lines, and `fr`/`en` i18n Gates 1–3 stay at `0`.

---

### Story 28.2: Canonical 5-Tab Workspace Container, De-Duplication of 3-Tab vs 5-Tab Panels & Direction C `total == 0` Sobriety on Tab 1 (`Accostage & Vue d'ensemble`) (`WX-01`, `WX-05`)

As an ORCIA User (`Hélène UJ-1`, `Marc UJ-5`),
I want `/workspaces` to expose a **single canonical 5-tab bar** (`1. Accostage & Vue d'ensemble` | `2. Documents & Sources` | `3. Livrables & Artefacts` | `4. Glossaire & Règles Métiers` | `5. Membres & Paramètres de l'espace`) — deleting the duplicate 3-tab `WorkspaceDetailTabsPanel` — and to obey Direction C `total == 0` sobriety on Tab 1 without displaying `0 / 0 / 0` KPI cards on an empty workspace,
So that every workspace capability lives in one obvious place with zero visual noise at Day-0.

**Lot:** 1 — Container & Tab 1 Consolidation. **Dependencies:** `28.1`. **Agent:** `bmad-dev-worker` (`flash`).
**Findings covered:** `WX-01`, `WX-05`.
**CAPs covered:** `CAP-061`, `CAP-080`.
**Impacted files:** `apps/web/src/features/workspaces/index.tsx`, `apps/web/src/features/workspaces/WorkspaceStudioCardsAndDetailView.tsx`, `apps/web/src/features/workspaces/WorkspaceDetailTabsPanel.tsx` (removed/merged), `apps/web/src/features/workspaces/WorkspaceDnaAndWaiversSection.tsx`, `packages/ui/src/primitives/WorkspaceFiveTabsAndExternalRebaseView.tsx`, `apps/web/src/i18n/locales/{fr,en}.ts`, `apps/web/src/__tests__/`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/28-2-canonical-five-tab-container-deduplication-and-tab1-sobriety-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** the `/workspaces` page
**When** rendered for any active workspace
**Then** the DOM contains **strictly one** workspace `[role="tablist"]` with the **5 canonical Direction C tabs** (`Accostage & Vue d'ensemble`, `Documents & Sources`, `Livrables & Artefacts`, `Glossaire & Règles Métiers`, `Membres & Paramètres de l'espace`), eliminating the competing 3-tab `WorkspaceDetailTabsPanel` (`SOURCES`, `GLOSSARY`, `MEMBERS`) completely.

**Given** Tab 1 (`Accostage & Vue d'ensemble`) on a workspace with `total == 0` (zero attached sources, zero pending glossary candidates, and zero active waivers)
**When** rendered
**Then** KPI summary cards with `0` counters are hidden (`DESIGN.md:L198`) and external-rebase clutter is hidden when `rebasedChunks.length === 0`, replaced by a single clear pedagogical empty-state sentence alongside local adaptations / exception waivers (`workspace_exception_waivers` Lock V1) and sanitized deliverable destination info (editable destination `PUT` tracked in `ACTION_ITEM-28.1`), cleanly presented with `<= 300` lines per modified file and zero dead buttons.

---

### Story 28.3: Scoped PG18 Consolidation of Tab 2 (`Documents & Sources`), Tab 3 (`Livrables & Artefacts`) & Tab 5 (`Membres & Paramètres de l'espace`) (`WX-01`, `WX-04`, `WX-05`)

As an ORCIA Workspace Member or Lead (`Yanis UJ-3`, `Marc UJ-5`, `Lucas UJ-7`),
I want Tab 2 (`Documents & Sources`), Tab 3 (`Livrables & Artefacts`), and Tab 5 (`Membres & Paramètres de l'espace`) to host the real, single-source-of-truth PG18 views scoped to the active workspace ID — hiding empty-state filter pills when `0` sources exist —
So that there is only one place to attach/probe sources, manage deliverables, and configure workspace members and parameters.

**Lot:** 2 — Functional Tabs Consolidation. **Dependencies:** `28.2`. **Agent:** `bmad-dev-worker` (`flash`).
**Findings covered:** `WX-01`, `WX-04`, `WX-05`.
**CAPs covered:** `CAP-067`, `CAP-080`, `CAP-180`.
**Impacted files:** `apps/web/src/features/workspaces/WorkspaceSourcesRagTab.tsx`, `apps/web/src/features/workspaces/WorkspaceDnaAndWaiversSection.tsx`, `apps/web/src/features/workspaces/WorkspaceMembersAndSettingsTab.tsx` (extracted `<= 300` L), `packages/ui/src/primitives/WorkspaceFiveTabsAndExternalRebaseView.tsx`, `apps/web/src/i18n/locales/{fr,en}.ts`, `apps/web/src/__tests__/`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/28-3-scoped-pg18-sources-deliverables-and-members-tabs-consolidation-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** Tab 2 (`Documents & Sources`) active for `activeWorkspaceId`
**When** the workspace has `0` attached sources
**Then** category filter pills (`Toutes`, `Connaissances`, `Modèles & Trames`, `Code & Contrats`, `Schémas SQL`) are hidden (`total == 0`) while `+ Rattacher une source` and pedagogical 1-sentence empty-state guidance remain accessible; when `>= 1` source exists, `WorkspaceSourcesRagTab` loads exclusively from `listWorkspaceDatasources(activeWorkspaceId)` (eliminating the unscoped `datasources` duplicate list from `WorkspaceDnaAndWaiversSection`) with freshness probe and `[STALE_WARNING]` waiver support intact.

**Given** Tab 3 (`Livrables & Artefacts`) and Tab 5 (`Membres & Paramètres de l'espace`)
**When** selected and modified by an authorized user
**Then** Tab 3 renders the workspace deliverables summary (`orcia://` sanitized CAS URI, `ExternalEditRebaser` Lock V2 `rebasedChunks` list when present, and clean empty state when `0` exist — full PG18 artifact store, diff preview, download CTA & `POST /artifacts/external-rebase` deferred cleanly under `ACTION_ITEM-28.1`) without repeating header chrome, and Tab 5 displays the consolidated organization team roster, read-only workspace governance summary badges (without duplicating interactive controls from the compact header), and PG18-persisted workspace instructions (`@orcia/api-client`, `F5` cold survival verified; per-workspace member add/remove, role/tool toggles & non-admin workspace `PATCH` persistence tracked under `ACTION_ITEM-28.1`).

---

### Story 28.4: Encapsulation of DNA Starlark Compiler & PG18 Glossary Candidate Queue Inside Tab 4 (`Glossaire & Règles Métiers`), Anti-Stacking Guard & Playwright E2E Verification (`WX-03`, `WX-04`)

As a Business Lead or Ontology Referent (`Nadia UJ-4`, `ONTOLOGY_LEAD`),
I want the DNA Starlark Rule Compiler (`🛡️ Directive ➔ 📏 Norme ➔ ⚙️ Mécanisme`), `Top-3` in-flow promotions (`Lock V4`), and the `✨ À valider` glossary candidate queue to live strictly inside Tab 4 (`Glossaire & Règles Métiers`) backed by PostgreSQL 18 — never permanently pinned at the bottom of the page or backed by `useState([])` — and locked by automated anti-stacking and Playwright E2E tests,
So that `/workspaces` remains clean, consistent, and regression-proof across both French and English sessions.

**Lot:** 2 — Glossary/DNA Tab & Verification Closure. **Dependencies:** `28.3`. **Agent:** `bmad-dev-worker` (`flash`) + mandatory `bmad-architect-worker` (`pro`) closure gate.
**Findings covered:** `WX-03`, `WX-04`, full `WX-01`..`WX-06` verification.
**CAPs covered:** `CAP-010`, `CAP-080`, `CAP-081`, `CAP-084`, `CAP-180`.
**Impacted files:** `apps/web/src/features/workspaces/WorkspaceGlossaryAndOntologyTab.tsx`, `apps/web/src/features/workspaces/WorkspaceDnaAndWaiversSection.tsx`, `packages/ui/src/primitives/DnaStarlarkCompilerAndGlossaryLifecycleView.tsx`, `apps/web/src/__tests__/workspaces-single-tabs-anti-stacking-audit.test.tsx` (new), `apps/web/e2e/07-spaces-org-and-workspace-persistence.spec.ts`, `apps/web/e2e/17-workspace-sources-codegraph-dna-and-ontology.spec.ts`, `docs/product/capabilities.yaml`, `docs/implementation-artifacts/sprint-status.yaml`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/28-4-tab4-glossary-dna-starlark-encapsulation-and-e2e-lock-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** Tab 1, Tab 2, Tab 3, or Tab 5 is active on `/workspaces`
**When** rendered
**Then** `DnaStarlarkCompilerAndGlossaryLifecycleView` is **not mounted** anywhere outside Tab 4 (`Glossaire & Règles Métiers`).

**Given** Tab 4 (`Glossaire & Règles Métiers`) is active
**When** the user compiles a DNA Starlark gate rule, inspects `Top-3` in-flow proposals, or accepts/adjusts/discards a candidate in `✨ À valider`
**Then** all candidate state hydrates from and persists to PostgreSQL 18 via `@orcia/api-client` (zero ephemeral `useState([])` business store) and survives `F5` cold reload (`reloadColdFromPg`).

**Given** full `AD-17` verification and `bmad-architect-worker` (`pro`) closure review
**When** closing Epic 28
**Then** `workspaces-single-tabs-anti-stacking-audit.test.tsx`, `zero-dead-buttons-and-silent-catches-audit.test.tsx`, `e2e-testids-sync-audit.test.ts`, i18n Gates 1–4 (`0` baseline), `pnpm turbo run lint typecheck test`, `apps/web/e2e/07-spaces-org-and-workspace-persistence.spec.ts` & `17-workspace-sources-codegraph-dna-and-ontology.spec.ts` (`env -u ORCIA_E2E_SEED_FIXTURES`, `fr` & `en`), `scripts/check_implementation_docs.py`, and `pnpm site:sync && pnpm site:check` all pass, `CAP-080` / `CAP-081` / `CAP-084` remain `runtime`, and `epic-28` becomes `done`.

---
