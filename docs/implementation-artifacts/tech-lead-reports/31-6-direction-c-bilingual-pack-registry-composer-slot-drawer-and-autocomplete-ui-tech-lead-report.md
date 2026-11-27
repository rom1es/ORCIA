# Story 31.6 — Direction C Bilingual Pack Registry, Composer, Slot Drawer & Qualified Autocomplete UI

- **Date**: 2026-11-26
- **Story / Sprint Key**: `31-6-direction-c-bilingual-pack-registry-composer-slot-drawer-and-autocomplete-ui` (`Epic 31` — Lot 5)
- **Capability(ies)**: `CAP-055`, `CAP-056`, `CAP-070`, `CAP-082`, `CAP-090`, `CAP-100`, `CAP-140`, `CAP-200` — classification: `feature`
- **Author / Context**: Vertical Frontend + `@orcia/api-client` + `@orcia/ui` implementation for Story 31.6 covering Direction C bilingual (`fr`/`en`) Pack Registry (`/settings/packs` & `/settings?tab=packs`), Workspace Pack Activation & Priority Reordering (`/spaces` / workspace tab), interactive Connector Slot Binding Drawer (`422 ERR_PACK_SLOT_UNBOUND`), `CUSTOM` Pack Composer Modal (`422 ERR_PACK_CLOSURE_INCOMPLETE`, `422 ERR_PACK_PII_OR_INFRA_LEAK`), Anti-Hostage Unlink Confirmation Dialog (`409 ERR_ENTITY_REFERENCED_BY_PACK_DRAFT` with `?unlink_from_draft_packs=true`), and qualified `@pack/agent` / `/pack/skill` autocomplete badges.

---

## 1. Needs Analysis & Tech Lead Impact Study (Pre-Implementation)

### 1.1 Context & Problem Statement
- Stories 31.1–31.5 delivered the full PostgreSQL 18 + SeaweedFS CAS backend for declarative APM packs:
  - Transactional import (`POST /api/v1/packs/import` multipart `.zip` or JSON base64), bundle delete (`DELETE /api/v1/packs/{bundle_id}`), and bundle scrubbed export (`POST /api/v1/packs/{bundle_id}/export`).
  - Workspace-scoped pack listing, activation, deactivation, atomic `DEFERRABLE` priority reordering, connector slot binding (`/api/v1/workspaces/{workspace_id}/packs*`), and immutable `run_lock_manifests` inspection (`GET /api/v1/runs/{run_id}/lock`).
  - Pack Composer CRUD (`POST/GET/PATCH/DELETE /api/v1/packs/composer*`), membership management (`PUT /api/v1/packs/composer/{draft_id}/members`), publish (`POST .../publish`), scrubbed export (`POST .../export`), and anti-hostage delete guards (`?unlink_from_draft_packs=true` on agents, skills, instructions, workflows v2, VSM v2, ontology, DNA mechanisms, policies, help articles).
- However, the frontend currently lacks:
  1. Typed domain client wrappers in `packages/api-client/src/domains/` for Workspace Packs, Slot Bindings, Run Lock Manifests, Pack Composer CRUD/publish/export, multipart `.zip` import, and `unlinkFromDraftPacks` delete parameters.
  2. A unified Direction C `"Mes Packs"` experience across `/settings/packs` and `/settings?tab=packs`, including `.zip` import modal, bundle delete/export, and workspace-scoped activation/priority/slot status badges.
  3. An interactive Slot Binding Drawer (`@orcia/ui` + `apps/web`) displaying required vs optional slots, workspace datasource/connector selectors, and inline `[role="alert"]` highlighting on `422 ERR_PACK_SLOT_UNBOUND`.
  4. A Pack Composer Modal (`@orcia/ui` + `apps/web`) for creating/editing `CUSTOM` drafts, toggling workspace member entities, previewing closure gaps (`422 ERR_PACK_CLOSURE_INCOMPLETE` + `auto_include_dependencies`), publishing, and exporting scrubbed `.zip` (`422 ERR_PACK_PII_OR_INFRA_LEAK`).
  5. Anti-hostage `409 ERR_ENTITY_REFERENCED_BY_PACK_DRAFT` confirmation dialog across Agent, Skill, Workflow v2, and VSM v2 deletions.
  6. Origin pack attribution badges inside `@`/`/` autocomplete options (`AssistantPromptPlusAndAutocomplete` + `AssistantStickyFooterBadges`) and `Mes Agents` cards matching the exact Story 31.3 backend qualified format (`@<pack>/<slug>` and `/<pack>/<slug>`).

### 1.2 Exploration, GitNexus Impact Analysis, Refactoring & Technical Debt
- **GitNexus & Codebase Impact Analysis (scoped to `ORCIA`)**:
  - `gitnexus_query({query: "packs", repo: "/home/romain/.gemini/antigravity/worktrees/ORCIA/consignes_personnelles_save_button"})` and targeted `git grep` confirmed:
    - Story 31.3 backend (`packages/orcia-core/src/orcia_core/packs/_internal/_sql_pack_entity_materializer.py` and `namespacing.py`) formats qualified handles strictly as `@<pack_slug>/<slug>` and `/<pack_slug>/<slug>` (and `@workspace/<slug>` / `/workspace/<slug>`).
    - `apps/web/src/features/inbox/assistantAutocompleteHelpers.ts` already produces `@<pack>/<slug>` / `/<pack>/<slug>` on collision, while `AssistantStickyFooterBadges.tsx` (`mergeAssistantAutocompleteOptions`) currently drops `badge` before passing options to `AssistantPromptPlusAndAutocomplete.tsx`, and `useSyncManagedAgentsCache.ts` omits `workspaceId` when calling `listAgentsAndSkills()`.
    - Existing tests assert specific testids on `/settings?tab=packs` (`settings-packs-section`, `installed-pack-card-*`, `pack-scope-input`, `activate-pack-btn-*`, `deactivate-pack-btn-*`, `packs-empty-state`) and `/settings/packs` (`packs-registry-v2-page`, `packs-registry-page-header`, `declarative-pack-card-*`).
    - OpenAPI schemas (`packages/api-client/src/generated/packs.ts`, `schema.ts`) already contain all Story 31.2–31.5 endpoints and schemas.
- **Refactoring Opportunities & File Line-Count Control (`<= 300` lines)**:
  - Extract a shared `packs.ts` domain client in `packages/api-client/src/domains/packs.ts` + multipart helper in `packages/api-client/src/helpers.ts` (or dedicated helper file to keep `helpers.ts <= 300` lines).
  - Extract focused `@orcia/ui` primitives (`PackSlotBindingDrawer.tsx`, `PackComposerModal.tsx`, `PackImportModal.tsx`, `EntityUnlinkConfirmDialog.tsx`, `WorkspacePacksSectionView.tsx`) under `packages/ui/src/primitives/`, each strictly `<= 300` lines, portaled via `OrciaDialog` (zero raw hex colors, zero `display: "none"`, zero hardcoded strings).
  - Share a single `DeclarativePacksRegistrySection` across `/settings/packs` (`PacksRegistryPage`) and `/settings?tab=packs` (`SettingsPacksSection`) without duplicating `<OrciaPageHeader />`.
  - Keep every created/modified `.ts` and `.tsx` file (production and test) `<= 300` lines.

---

## 2. Implementation Plan

### 2.1 Data Schema & Alembic Migrations
- None required in Story 31.6 (all DDL and triggers were delivered in Stories 31.1–31.5).

### 2.2 Hexagonal Core, Orchestration & Workers
- None required in Story 31.6 (backend contracts and services are locked by Stories 31.2–31.5).

### 2.3 Backend API, Security & Contracts (`packages/api-client/`)
- `packages/api-client/src/multipartHelper.ts` (new, `<= 100 L`): `createRequestMultipart` supporting `FormData` `.zip`/YAML uploads with bearer auth, single-flight refresh, and RFC 9457 `OrciaProblemError` parsing.
- `packages/api-client/src/domains/packs.ts` (new, `<= 250 L`): typed wrappers for:
  - Pack Registry: `listDeclarativePacks`, `getPacksHealth`, `importPackArchive` (JSON base64), `importPackArchiveFile` (`multipart/form-data`), `deletePackBundle`, `exportPackBundleZip`, `exportWorkspacePackZip`.
  - Workspace Packs & Slots: `listWorkspacePacks`, `activateWorkspacePack`, `deactivateWorkspacePack`, `reorderWorkspacePacks`, `bindWorkspacePackSlots`, `getWorkflowV2RunLock`.
  - Pack Composer: `listPackDrafts`, `createPackDraft`, `getPackDraft`, `updatePackDraft`, `setPackDraftMembers`, `deletePackDraft`, `publishPackDraft`, `exportPackDraftZip`.
  - Error extractors: typed helpers parsing `ProblemDetails` extras (`missing_slots`, `draft_packs`, `missing_dependencies`, `leak_findings`).
- `packages/api-client/src/domains/workflowsV2.ts` & `agentsAndSkills.ts`: add `deleteWorkflowV2(workflowId, { unlinkFromDraftPacks?, personaKey? })`, `deleteVsmV2(vsmId, { unlinkFromDraftPacks?, personaKey? })`, and `unlinkFromDraftPacks?: boolean` on `deleteAgent` / `deleteSkill`.
- `packages/api-client/src/index.ts`: export `createPacksDomainClient` and all new Story 31.6 types cleanly.

### 2.4 User Interface & Experience (`packages/ui/`, `apps/web/`)
- **Design System Primitives (`packages/ui/src/primitives/`)**:
  - `PackImportModal.tsx`: `OrciaDialog` modal for `.zip` / YAML upload (`<input type="file" className="sr-only">` + scope selector + `replace_draft` checkbox) with inline `[role="alert"]` error display.
  - `PackSlotBindingDrawer.tsx`: `OrciaDialog`-backed drawer listing required and optional slots, datasource/connector target pickers, `ready` / `optional_unbound` / `unbound` badges, `422 ERR_PACK_SLOT_UNBOUND` missing slot highlighting + inline `[role="alert"]`, and read-only observer disabling.
  - `PackComposerModal.tsx` + `PackComposerMembersStep.tsx`: step-by-step `OrciaDialog` modal for creating/editing `CUSTOM` draft packs, selecting workspace agents/skills/workflows/VSM/concepts, viewing live closure gaps & prose lint warnings, toggling `auto_include_dependencies`, publishing, and exporting scrubbed `.zip` with inline `[role="alert"]` errors (`422 ERR_PACK_CLOSURE_INCOMPLETE`, `422 ERR_PACK_PII_OR_INFRA_LEAK`).
  - `EntityUnlinkConfirmDialog.tsx`: `OrciaDialog` confirmation modal listing referencing draft pack names/slugs from `409 ERR_ENTITY_REFERENCED_BY_PACK_DRAFT` and invoking confirmed unlink deletion (`unlink_from_draft_packs=true`).
  - `WorkspacePacksPanel.tsx`: Direction C workspace pack activation, priority reorder controls (up/down swap -> `PUT /reorder`), slot status badges, and "Configure slots" trigger opening `PackSlotBindingDrawer`.
  - Update `AssistantStickyFooterBadges.tsx` & `AssistantPromptPlusAndAutocomplete.tsx` to preserve and render origin pack attribution `badge` (`sdlc`, `legal-audit`, `workspace`) in `@` / `/` dropdown options.
  - Update `AgentStudioCardBadgesAndPassport.tsx` & `SkillStudioCardItem.tsx` to show origin pack attribution (`packSlug`) and qualified handle on collision (`qualifiedRef` when `isColliding`).
- **SPA Integration (`apps/web/src/`)**:
  - `apps/web/src/i18n/locales/`: bilingual `fr`/`en` dictionaries (`packs_ui_labels.ts`, `packs_ui_labels_fr.ts`, `packs_ui_labels_en.ts`, plus `rfc9457_banner_labels_{fr,en}.ts` entries for Epic 31 error codes), keeping 100% key parity and zero jargon.
  - `apps/web/src/features/settings/packs/`: unify `/settings/packs` (`PacksRegistryPage.tsx`) and `/settings?tab=packs` (`SettingsPacksSection.tsx`) around shared `DeclarativePacksRegistrySection.tsx`, adding `.zip` import, bundle uninstall, scrubbed `.zip` export, Pack Composer modal trigger, and workspace pack activation/slot drawer integration while preserving existing card testids.
  - `apps/web/src/features/workspaces/`: add workspace pack activation & slot binding panel in Workspace Members/Settings & Overview (`WorkspacePacksContainer.tsx` inside `WorkspaceMembersAndSettingsTab.tsx` / `WorkspaceFiveTabsAndExternalRebaseView.tsx`), surviving `F5` cold reload from PG18.
  - `apps/web/src/features/catalog/` & `apps/web/src/features/processes/`: wire `409 ERR_ENTITY_REFERENCED_BY_PACK_DRAFT` interception + `EntityUnlinkConfirmDialog` into `useManagedAgentActions.ts`, `useManagedAgentsAndSkills.ts`, `CatalogFeaturePanel`, and `ProcessCatalogCardGrid` / `useProcessesHubData` (plus guarded workflow/VSM delete).
  - `apps/web/src/components/useSyncManagedAgentsCache.ts` & `apps/web/src/features/inbox/useInboxPanelController.ts`: pass `activeWorkspaceId` so workspace-scoped pack collisions and qualified `@pack/agent` / `/pack/skill` suggestions hydrate accurately.

### 2.5 Test Pyramid Impact Analysis (`AD-17`)
- **Layer 1b (Vitest Unit & Component Tests, `<= 300 L` each)**:
  - `packages/api-client/src/__tests__/packsDomainClient.test.ts`: typed pack registry, multipart upload, workspace packs, slot bindings, composer CRUD/publish/export, and `unlink_from_draft_packs` delete query params.
  - `packages/ui/src/__tests__/story-31-6-pack-ui-primitives.test.tsx`: Slot Binding Drawer (`ERR_PACK_SLOT_UNBOUND` highlight, `optional_unbound`, observer disabled), Pack Composer Modal (`ERR_PACK_CLOSURE_INCOMPLETE`, `auto_include_dependencies`, `ERR_PACK_PII_OR_INFRA_LEAK`), Unlink Confirmation Dialog, and qualified autocomplete origin badges.
  - `apps/web/src/__tests__/story-31-6-pack-registry-and-slots.test.tsx`: `/settings/packs`, `/settings?tab=packs`, `/spaces` workspace pack activation/priority/slot binding + `F5` cold reload + `READ_ONLY_OBSERVER` disabling + `[role="alert"]` errors.
  - `apps/web/src/__tests__/story-31-6-composer-unlink-and-autocomplete.test.tsx`: Pack Composer modal flow, `409 ERR_ENTITY_REFERENCED_BY_PACK_DRAFT` unlink dialog on Agent/Skill/Workflow delete, and `@pack/agent` / `/pack/skill` autocomplete badges & insertion.
  - Extend `apps/web/src/__tests__/vitestPacksAndWizardsMockHandlers.ts` (or modular helper `vitestEpic31PackHandlers.ts`) to support all Story 31.2–31.5 endpoints under `openApiRequestValidator`.
- **Mandatory Existing Audits**:
  - `zero-dead-buttons-and-silent-catches-audit.test.tsx`, `e2e-testids-sync-audit.test.ts`, `i18n-hardcoded-locale-ast-audit.test.ts`, `i18n-dictionary-parity-and-jargon-audit.test.ts`, `client-error-code-contract-audit.test.ts`, `page-header-structure-and-visual-grammar-audit.test.tsx`, `no-hidden-legacy-panels-audit.test.ts`.

---

## 3. Summary of Changes & Results (Post-Verification)

### 3.1 Delivered Files & Line-Count Discipline (`<= 300` L)
All new and modified production `.ts` / `.tsx` files comply with the `<= 300`-line limit (only pre-existing barrel `packages/ui/src/index.ts` at `799` L and test handler `apps/web/src/__tests__/vitestPacksAndWizardsMockHandlers.ts` at `429` L predate/test-support Story 31.6):

| Package | File | Lines | Role |
|---|---|---|---|
| `@orcia/api-client` | `packages/api-client/src/packTypes.ts` | 16 | Story 31.6 pack & composer client types |
| `@orcia/api-client` | `packages/api-client/src/multipartHelper.ts` | 131 | `createRequestMultipart` (`FormData`, bearer auth, RFC 9457 errors) |
| `@orcia/api-client` | `packages/api-client/src/domains/packs.ts` | 286 | Registry, workspace packs, slot bindings, composer & zip export/import client |
| `@orcia/api-client` | `packages/api-client/src/domains/agentsAndSkills.ts`, `workflowsV2.ts`, `helpers.ts`, `index.ts` | 168 / 222 / 300 / 243 | `unlinkFromDraftPacks` delete query params & exports |
| `@orcia/ui` | `packages/ui/src/primitives/PackUiTypes.ts`, `packsExports.ts` | 212 / 47 | Typed UI models & barrel exports |
| `@orcia/ui` | `packages/ui/src/primitives/WorkspacePacksPanel.tsx` | 193 | Workspace pack activation, priority swap & slot status UI |
| `@orcia/ui` | `packages/ui/src/primitives/PackImportModal.tsx` | 209 | `.zip`/YAML import dialog (`OrciaDialog`, `sr-only` file input, `[role="alert"]`) |
| `@orcia/ui` | `packages/ui/src/primitives/PackSlotBindingDrawer.tsx` | 279 | Connector slot binding drawer & `422 ERR_PACK_SLOT_UNBOUND` highlight |
| `@orcia/ui` | `packages/ui/src/primitives/PackComposerMetadataStep.tsx`, `PackComposerMembersStep.tsx`, `PackComposerModal.tsx` | 175 / 182 / 273 | `CUSTOM` pack composer wizard (`auto_include_dependencies`, publish, export) |
| `@orcia/ui` | `packages/ui/src/primitives/EntityUnlinkConfirmDialog.tsx` | 90 | Anti-hostage `409 ERR_ENTITY_REFERENCED_BY_PACK_DRAFT` unlink dialog |
| `@orcia/ui` | `packages/ui/src/primitives/AssistantPromptPlusAndAutocomplete.tsx`, `AssistantStickyFooterBadges.tsx`, `AgentStudioCardBadgesAndPassport.tsx`, `AgentStudioCardItem.tsx`, `SkillStudioCardItem.tsx` | 278 / 197 / 290 / 236 / 205 | Origin pack attribution badges & `@pack/agent` / `/pack/skill` collision handles |
| `@orcia/web` | `apps/web/src/features/settings/packs/DeclarativePacksRegistrySection.tsx`, `packMappers.ts`, `PackCardItem.tsx`, `PacksRegistryPage.tsx`, `usePacksRegistryHealthchecks.ts`, `usePackComposerAndImportController.ts`, `usePackImportAndUninstallController.ts`, `useWorkspacePacksController.ts` | 286 / 161 / 234 / 122 / 181 / 248 / 83 / 212 | Unified Direction C registry, export/import/uninstall, composer & workspace pack controllers |
| `@orcia/web` | `apps/web/src/features/workspaces/WorkspacePacksTabSection.tsx`, `WorkspaceMembersAndSettingsTab.tsx`, `routes/SettingsPacksSection.tsx` | 70 / 207 / 197 | Workspace pack activation/slots tab & `/settings?tab=packs` unification |
| `@orcia/web` | `apps/web/src/features/shared/useGuardedEntityDelete.ts`, `catalog/managedAgentDeleteHelper.ts`, `catalog/useManagedAgentActions.ts`, `catalog/useManagedAgentsAndSkills.ts`, `catalog/index.tsx`, `processes/ProcessCatalogCardGrid.tsx`, `processes/ProcessesHubPage.tsx`, `processes/useProcessesHubData.ts`, `components/useSyncManagedAgentsCache.ts`, `inbox/useInboxPanelController.ts` | 90 / 72 / 279 / 265 / 291 / 252 / 237 / 216 / 47 / 293 | `409` unlink guard wiring & workspace-scoped `@`/`/` autocomplete hydration |
| `@orcia/web` | `apps/web/src/i18n/locales/{packs_ui_labels,packs_ui_labels_fr,packs_ui_labels_en,fr,en,rfc9457_banner_labels_fr,rfc9457_banner_labels_en}.ts`, `i18n/types.ts` | 46..186 | 100% bilingual FR/EN keys & Epic 31 RFC 9457 error banners |
| Tests | `packsDomainClient.test.ts`, `story-31-6-pack-ui-primitives.test.tsx`, `story-31-6-pack-registry-and-slots.test.tsx`, `story-31-6-composer-unlink-and-autocomplete.test.tsx` + `vitestEpic31*Mock.ts` | 166..243 | Layer 1b typed API client, `@orcia/ui`, and `@orcia/web` verification |

### 3.2 Static, Security & GitNexus Verification Gates
- `detect-secrets-hook --baseline .secrets.baseline`: **PASS** (`exit 0`, zero leaks).
- `ruff check .` & `ruff format --check .`: **PASS** (`1,916` files already formatted, `0` warnings).
- `scripts/export_openapi.py --check`: **PASS** (`0-diff` against committed OpenAPI schema).
- `lint_spine.py`: **PASS** (`ok: true`, `total_findings: 0`).
- `gitnexus analyze --index-only .`: **PASS** (`51,479` nodes, `235,430` edges, `881` clusters, `1,524` flows).
- `gitnexus_detect_changes({scope: "all"})`: `changed_count: 24`, `changed_files: 34`, `affected_count: 1,520`, `risk_level: critical` (expected for shared `@orcia/api-client`, `@orcia/ui` primitives, and `i18n` dictionary exports).

### 3.3 AD-17 Test Pyramid & Vertical Wiring Verification
- **Layer 1b — Full JS/TS Turbo Matrix (`pnpm turbo run lint typecheck test --concurrency=2`)**: **PASS** (`9/9` tasks, `0` failures in `53.65s`):
  - `@orcia/api-client`: `lint` + `typecheck` + `test` (**`4` files / `23` tests** passed).
  - `@orcia/ui`: `lint` + `typecheck` + `test` (**`41` files / `157` tests** passed).
  - `@orcia/web`: `lint` + `typecheck` + `test` (**`98` files / `375` tests** passed, including all `i18n`, `zero-dead-buttons`, `e2e-testids-sync`, `client-error-code`, `page-header`, and `no-hidden-legacy-panels` audits).
  - Total JS/TS: **`143` files / `555` tests** passed.
- **Layer 5 — Dual-Server Playwright Desktop E2E (`env -u ORCIA_E2E_SEED_FIXTURES`, real FastAPI Composition Root + PG18 + Redis + Vite SPA)**: **PASS** (**`11 passed, 0 failed`** in `2.1m` across `02-assistant-streaming-and-folders.spec.ts`, `07-spaces-org-and-workspace-persistence.spec.ts`, `08-agents-skills-persistence.spec.ts`, `09-pack-builder-and-contextual-help.spec.ts`, `18-catalog-packs-wizards-and-mcp-bench.spec.ts`).
- **Closeout & Registry Sync**:
  - Updated `docs/product/capabilities.yaml` (`CAP-055`, `CAP-056`, `CAP-070`, `CAP-082`, `CAP-090`, `CAP-100`, `CAP-140`, `CAP-200`), `docs/implementation-artifacts/sprint-status.yaml` (`31-6: done`), and `docs/implementation-artifacts/tech-lead-reports/README.md`.
  - Executed `pnpm site:sync && pnpm site:check`, `scripts/check_implementation_docs.py`, and post-sync `pytest --no-cov -q tests/unit` (zero leftover `.coverage*`).
