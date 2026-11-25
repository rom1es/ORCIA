# Story 29.2 — Scoped `PATCH /api/v1/workspaces/{id}`, Strict `CONFIDENTIAL_RESTRICTED` Isolation Enforcement, Optimistic Rollback & Single Error Banner

- **Date**: 2026-11-25
- **Story / Sprint Key**: `29-2-scoped-workspace-patch-confidential-isolation-rollback-and-single-banner` (`Epic 29` / Lot 1 — P0 Security & Persistence Integrity; resolves `ACTION_ITEM-28.1` item 1)
- **Capability(ies)**: `CAP-050`, `CAP-067`, `CAP-080`, `CAP-010`, `CAP-062` — classification: `feature` (security hardening, RBAC/ABAC persistence, and UI transactional rollback)
- **Author / Context**: `bmad-dev-worker` (`flash`) following Planning/Security Arbitration — covers `UH-03`, `UH-04`, `ACTION_ITEM-28.1` item 1, `AD-6`, `AD-7`, `AD-8`, `AD-19`, `AD-21`, `architecture.md:L692`, and `EXPERIENCE.md` §1.1 #4.
- **Associated Commits**: Pending Testing & Architect closure

---

## 1. Needs Analysis & Tech Lead Impact Study (Pre-Implementation)

### 1.1 Context & Problem Statement
- **Live `Mes Espaces` persistence & rollback defect (`UH-03`, `ACTION_ITEM-28.1` item 1)**:
  - Currently, changing workspace visibility (e.g., to `"CONFIDENTIAL_RESTRICTED"`) or lifecycle phase in `WorkspaceCompactHeader.tsx` invokes `updateWorkspaceVisibility` / `updateWorkspacePhase` in `apps/web/src/components/platformSetupContextTypes.ts`, which mutates React state and writes to `localStorage` **before** calling admin-only `PUT /api/v1/bootstrap/platform-setup-state`.
  - For a `TEAM_LEAD` (or any non-`PLATFORM_ADMIN`), `PUT /api/v1/bootstrap/platform-setup-state` returns `HTTP 403`. `persistSetupSnapshotStrict` populates global `lastSyncError` (`"Synchronisation plateforme"`, Banner 1 inside `px-4` in `ShellAuthFallbackView.tsx`) AND re-throws; `WorkspaceCompactHeader` catches and sets `actionFeedback` with a `"⚠️ "` prefix (Banner 2 without `px-4` in `features/workspaces/index.tsx`, colliding with `<OrciaIcon name="cross" />` in `OrciaAlertBanner`), leaving two misaligned red banners and corrupted React/`localStorage` state (e.g., `Espace personnel` appearing as `Collectif d'équipe` / `Équipe`).
  - Expected behavior: A dedicated, `ScopeAccessGuard`-protected `PATCH /api/v1/workspaces/{workspace_id}` endpoint backed by PostgreSQL 18 + `audit_ledger` + `MatrixPermissionEvaluator` sync; zero `localStorage` writes before API confirmation; clean React state rollback on error; typed alert state (`{ tone: "crimson" | "emerald"; message: string }`) with zero `"⚠️ "` string hacks; and strictly **at most 1** aligned error banner.
- **`CONFIDENTIAL_RESTRICTED` isolation enforcement gaps (`UH-04`)**:
  - `architecture.md:L692` specifies that `CONFIDENTIAL_RESTRICTED` workspaces strictly confine business content (documents, Blackboard, Runs, ontology, datasources, search) to explicit `workspace_memberships`, while parent `BU_DIRECTOR`/`TEAM_LEAD`/`PLATFORM_ADMIN` retain aggregate FinOps counters (`finops_cost_usd`).
  - Six backend gaps currently bypass this invariant:
    1. `packages/orcia-core/src/orcia_core/permissions/evaluator.py:L177-L187`: grants `DIRECT_TEAM` `CONTRIBUTOR_ACTION_REQUIRED` access to all members/leads of `owner_org_unit_id` even when `visibility_mode == "CONFIDENTIAL_RESTRICTED"`.
    2. `packages/orcia-core/src/orcia_core/ontology/permissions.py`: `can_write_ontology_level` / `can_read_ontology_item` grant blanket `PLATFORM_ADMIN` and org-tree read/write access on `3_WORKSPACE` ontology items without enforcing `CONFIDENTIAL_RESTRICTED` (`workspace_memberships`) or `PRIVATE_USER` (`personal_owner_user_id`) isolation, and `sql_ontology_mappers.py` does not hydrate `personal_owner_user_id` / `ui_visibility_mode`.
    3. `apps/api/src/orcia_api/routers/ontology_and_rag.py`: `POST /api/v1/ontology-rag/rag/search` (`search_hybrid_rag`) does not enforce `resolve_workspace_access` for `body.workspace_id`.
    4. `apps/api/src/orcia_api/routers/workspace_governance.py`: `_validate_workspace_access` skips `resolve_workspace_access` whenever `user.platform_role == "PLATFORM_ADMIN"` (`L82`), and 3 artifact/pilot routes (`resolve_workspace_artifact_destination`, `rebase_external_artifact`, `run_pilot_ticket_to_tech_spec`) do not call `_validate_workspace_access`.
    5. `apps/api/src/orcia_api/routers/workspace_datasources.py`: `_enforce_personal_workspace_isolation` only checks `PRIVATE_USER`, omitting `resolve_workspace_access` for `CONFIDENTIAL_RESTRICTED` and non-member workspaces across `GET`/`POST`/`PATCH`/`DELETE`/`sync`.
    6. `packages/orcia-core/src/orcia_core/rag/_internal/sql_federated_search.py:L260-L285,L322`: includes `:is_admin` bypass (`PLATFORM_ADMIN`) on `CONFIDENTIAL_RESTRICTED` workspaces and `WORKSPACE_OPEN` folders inside `⌘K` Federated Search.

### 1.2 Exploration, GitNexus Impact Analysis, Refactoring & Technical Debt
- **GitNexus Impact Analysis (`repo: "/home/romain/Documents/Projects/ORCIA"`)**:
  - `resolve_workspace_access` (`packages/orcia-core/src/orcia_core/permissions/evaluator.py:L152`): `192` upstream impacted symbols (`183` direct), risk `CRITICAL`.
  - Pre-edit contract check identified two legacy test conflicts that received explicit Planning/Security Arbitration:
    - **Arbitration Decision 1**: Restrict `evaluator.py:L177-L187` (`DIRECT_TEAM` branch) with `workspace.visibility_mode != "CONFIDENTIAL_RESTRICTED"` without altering `compute_finops_rollup_usd`; add an explicit `WorkspaceMembershipEntity` for `marc` (`0192c4e0-0000-7000-8000-000000000603`) on `_WS_CONF` (`0192c4e0-0000-7000-8000-000000000203`) in `_default_service.py` (mirroring the runtime creator/transition explicit-membership guard) so `tests/unit/test_permissions_and_auth.py:178-196` remains intact while adding a dedicated test proving non-member teammates are denied on `_WS_CONF`.
    - **Arbitration Decision 2**: Remove `:is_admin` / `*_ADMIN_ONLY_ROLES` bypass on `CONFIDENTIAL_RESTRICTED` in `sql_federated_search.py` and strengthen `tests/unit/test_story_23_5_search_coverage.py:392` from `("CONTRIBUTOR", "PLATFORM_ADMIN")` to `("CONTRIBUTOR",)`.
- **Refactoring Opportunities & File-Size Control (`<= 300` lines)**:
  - `apps/api/src/orcia_api/routers/org_and_workspaces.py` (`280` lines) and `apps/api/src/orcia_api/schemas/auth_and_org.py` (`278` lines) are near the `300`-line limit. Extract workspace `PATCH` helper logic into `apps/api/src/orcia_api/routers/_workspace_patch_helpers.py` (`<= 200` lines), PG18 SQL update/membership helpers into `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_workspace_patch.py` (`<= 220` lines), and `WorkspacePatchRequest` / `WorkspacePatchResponse` into `apps/api/src/orcia_api/schemas/org_and_workspaces.py` (re-exported in `auth_and_org.py` or imported directly).
  - In `apps/web/src/features/workspaces/`, introduce a clean typed `WorkspaceFeedbackBanner` (`{ tone: "crimson" | "emerald"; message: string }`) helper/type so `"⚠️ "` string prefixes are eliminated from `WorkspaceCompactHeader.tsx`, `features/workspaces/index.tsx`, `useWorkspaceDnaAndWaivers.ts`, `WorkspaceMembersInstructionsCard.tsx`, and `WorkspaceSourcesRagTab.tsx`.
  - Keep every created/modified file strictly `<= 300` lines.

---

## 2. Implementation Plan

### 2.1 Data Schema & Alembic Migrations
- No schema migration required: existing tables `workspaces` (`id`, `slug`, `name`, `owner_org_unit_id`, `visibility_mode`, `finops_cost_usd`, `settings_jsonb`), `workspace_memberships` (`id`, `workspace_id`, `user_id`, `invited_org_unit_id`, `role`, `access_mode`), `platform_settings`, and append-only `audit_ledger` already support all Story 29.2 operations.

### 2.2 Hexagonal Core, Orchestration & Workers (`packages/orcia-core/`)
- `packages/orcia-core/src/orcia_core/permissions/evaluator.py`:
  - Guard the `DIRECT_TEAM` org-unit branch (`L177-L187`) with `if workspace.visibility_mode != "CONFIDENTIAL_RESTRICTED":` so `CONFIDENTIAL_RESTRICTED` requires explicit `WorkspaceMembershipEntity` (`L171-L175`) or `PARTNER_INVITE`.
- `packages/orcia-core/src/orcia_core/permissions/_default_service.py`:
  - Add explicit `WorkspaceMembershipEntity` for `marc` (`0192c4e0-0000-7000-8000-000000000603`) on `_WS_CONF` (`0192c4e0-0000-7000-8000-000000000203`), keeping `DEFAULT_WORKSPACE_SEEDS` / `test_permissions_and_auth.py` coherent with runtime self-lockout guarantees.
- `packages/orcia-core/src/orcia_core/permissions/errors.py` & `_error_catalog.py`:
  - Add `PrivateWorkspaceVisibilityLockedError` (`403 ERR_PRIVATE_WORKSPACE_VISIBILITY_LOCKED`, bilingual FR/EN RFC 9457 copy) for rejecting in-place visibility transitions on `PRIVATE_USER` / `personal-*` workspaces.
- `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_workspace_patch.py` & `_sql_workspaces_sync.py`:
  - Implement `patch_workspace_on_postgres18(...)` with atomic transaction: verify existence (`404`), verify `PRIVATE_USER` / `personal-*` immutability (`403`), update `workspaces` (`name`, `visibility_mode`, `settings_jsonb` `lifecycle_phase` & `ui_visibility_mode`), ensure self-lockout protection by upserting an explicit `WorkspaceMembershipEntity` in `workspace_memberships` for the acting user when transitioning to `CONFIDENTIAL_RESTRICTED`, and sync `platform_settings` snapshot.
  - Ensure `sync_workspace_owner_memberships` in `_sql_workspaces_sync.py` adds the creator (`creator_user_id`) explicitly for all workspaces (while only auto-adding `PLATFORM_ADMIN`s when `visibility_mode != "CONFIDENTIAL_RESTRICTED"` or preserving creator-only self-lockout guard on `CONFIDENTIAL_RESTRICTED`).
- `packages/orcia-core/src/orcia_core/ontology/permissions.py` & `sql_ontology_mappers.py`:
  - Hydrate `personal_owner_user_id` and `ui_visibility_mode` from `workspaces.settings_jsonb` in `load_org_and_workspaces_context`.
  - Enforce `PRIVATE_USER` (`personal_owner_user_id == user.id` only, even for `PLATFORM_ADMIN`) and `CONFIDENTIAL_RESTRICTED` (`WorkspaceMembershipEntity` / `invited_org_unit_id` only, blocking `PLATFORM_ADMIN`, `DIRECT_TEAM`, and `BU` ancestor bypasses) in both `can_write_ontology_level` and `can_read_ontology_item` for `3_WORKSPACE` items.
- `packages/orcia-core/src/orcia_core/rag/_internal/sql_federated_search.py`:
  - Remove `:is_admin` bypass and `*_ADMIN_ONLY_ROLES` expansion on `CONFIDENTIAL_RESTRICTED` workspaces and `WORKSPACE_OPEN` folders inside `CONFIDENTIAL_RESTRICTED` workspaces; require explicit `workspace_memberships` match (`wm.user_id` or `wm.invited_org_unit_id`).

### 2.3 Backend API, Security & Contracts (`apps/api/`, `packages/api-client/`)
- `apps/api/src/orcia_api/schemas/org_and_workspaces.py` (new dedicated schema module) + `apps/api/src/orcia_api/routers/org_and_workspaces.py` + `_workspace_patch_helpers.py`:
  - Add `PATCH /api/v1/workspaces/{workspace_id}` returning `WorkspacePatchResponse` (updating `name`, `visibility_mode`, `lifecycle_phase`).
  - Enforce `ScopeAccessGuard`: reject `READ_ONLY_OBSERVER` (`403 ERR_OBSERVER_MODE_READ_ONLY`), enforce workspace/org-unit governance (`PLATFORM_ADMIN`, subtree `BU_DIRECTOR`/`BU_LEAD`, or owning `TEAM_LEAD` for their team workspaces; reject cross-team callers and non-leads with `403 ERR_SCOPE_ACCESS_DENIED`), reject visibility changes on `PRIVATE_USER` / `personal-*` (`403 ERR_PRIVATE_WORKSPACE_VISIBILITY_LOCKED`), persist in PG18, upsert explicit creator/actor membership on `CONFIDENTIAL_RESTRICTED`, sync `evaluator`, and append an immutable `audit_ledger` entry (`WORKSPACE_UPDATED`).
  - Fix `POST /api/v1/workspaces` in-memory/PG sync so `CONFIDENTIAL_RESTRICTED` creator receives explicit membership without silently granting unrelated admins access when `CONFIDENTIAL_RESTRICTED`.
- `apps/api/src/orcia_api/routers/ontology_and_rag.py`:
  - Enforce `resolve_workspace_access` on `POST /api/v1/ontology-rag/rag/search` (`search_hybrid_rag`) when `body.workspace_id` resolves in topology (denying `CONFIDENTIAL_RESTRICTED` / `PRIVATE_USER` / cross-team access with `403 ERR_SCOPE_ACCESS_DENIED`, while preserving aggregate FinOps endpoints untouched). Also ensure `get_ontology_and_rag_state` enforces `CONFIDENTIAL_RESTRICTED` / `PRIVATE_USER` even for `PLATFORM_ADMIN`.
- `apps/api/src/orcia_api/routers/workspace_governance.py` & `workspace_datasources.py`:
  - Remove `if user.platform_role != "PLATFORM_ADMIN":` bypass in `workspace_governance._validate_workspace_access`, invoke `_validate_workspace_access` on all workspace endpoints (including artifact/pilot endpoints), and enforce `resolve_workspace_access` in `workspace_datasources.py` across `GET`/`POST`/`PATCH`/`DELETE`/`sync`.
- `packages/api-client/`:
  - Regenerate OpenAPI 3.1 schema and domain-sharded TS types (`PYTHONPATH=... .venv/bin/python scripts/export_openapi.py`).
  - Add typed `patchWorkspace(workspaceId, payload, personaKey?)` to `packages/api-client/src/domains/authAndShell.ts`.

### 2.4 User Interface & Experience (`apps/web/`, `packages/ui/`)
- `apps/web/src/components/platformSetupWorkspaces.ts`, `platformSetupContextTypes.ts`, `usePlatformSetupHydrationEffect.ts`, `platformSetupStore.tsx`:
  - Wire `updateWorkspaceVisibility` and `updateWorkspacePhase` to `client.patchWorkspace(workspaceId, ...)` via `@orcia/api-client` (replacing admin-only `PUT /api/v1/bootstrap/platform-setup-state`).
  - **Transactional persistence**: never write to `localStorage` (`writeCachedPlatformSetupState`) or commit workspace mutations without rollback before API confirmation. On error, roll back React state cleanly (`setWorkspaces(prevWorkspaces)`, `setAuditEvents(prevAuditEvents)`), do **not** populate global `lastSyncError` when handled locally by the caller, and rethrow so the caller renders **strictly 1** aligned inline banner.
- `apps/web/src/features/workspaces/index.tsx`, `WorkspaceCompactHeader.tsx`, and sibling workspace feedback emitters:
  - Replace `"⚠️ "` string-prefix detection with typed `WorkspaceAlertFeedback = { readonly tone: "crimson" | "emerald"; readonly message: string } | null` so `OrciaAlertBanner` never renders a double `✕ ⚠️` icon.
- `apps/web/src/components/ShellAuthFallbackView.tsx`:
  - Align `ShellCentralWorkspaceBody` alert banner width (`px-4 pt-3` -> aligned with page content / remove extra `px-4` inset mismatch).
- `apps/web/src/i18n/locales/` (`fr` / `en`):
  - Ensure 100% bilingual FR/EN copy for all error contexts and workspace mutation messages.

### 2.5 Test Pyramid Impact Analysis (`AD-17` — Layers 1 to 5 + Security, Mandatory)
- **Layer 1a (Python Unit `tests/unit/`)**:
  - Update `tests/unit/test_permissions_and_auth.py` (keep `marc` / `claire` assertions intact + add non-member teammate `CONFIDENTIAL_RESTRICTED` denial test).
  - Update `tests/unit/test_story_23_5_search_coverage.py` (`("CONTRIBUTOR",)` + non-member `PLATFORM_ADMIN` exclusion test).
  - Add `tests/unit/test_story_29_2_workspace_patch_and_isolation.py` covering `PATCH` authorization, self-lockout guard, `PRIVATE_USER` lock, ontology `3_WORKSPACE` isolation, and `CONFIDENTIAL_RESTRICTED` router guards.
- **Layer 1b (Frontend TS/React `Vitest`)**:
  - Add `apps/web/src/__tests__/story-29-2-workspace-patch-rollback-and-banner.test.tsx` verifying `PATCH /api/v1/workspaces/{id}` wiring, optimistic rollback on 403 (`localStorage` untouched, `PRIVATE_USER` stays `Personnel`), single aligned alert banner (no `platform-sync-error-banner` + no `⚠️ ` double icon), and both `fr`/`en` locales.
  - Update Vitest mock handlers (`apps/web/src/__tests__/setup/workspacesAndCatalogMockHandlers.ts`) to support `PATCH /api/v1/workspaces/{id}`.
- **Layer 2 (Vertical Integration `HTTP FastAPI ➔ PostgreSQL 18` `tests/integration/api/`)**:
  - Add `tests/integration/api/test_story_29_2_workspace_patch_and_isolation_pg18.py` booting real `create_app()` without `dependency_overrides`, exercising `PATCH /api/v1/workspaces/{id}` as `TEAM_LEAD` / `BU_DIRECTOR` / `PLATFORM_ADMIN` / `OBSERVER` / cross-team, verifying PG18 persistence (`workspaces`, `workspace_memberships`, `audit_ledger`) via direct SQL `SELECT`, and verifying `CONFIDENTIAL_RESTRICTED` isolation across RAG search, datasources, governance, ontology, and federated search while preserving FinOps counters.
- **Layer 3 (OpenAPI 3.1 Contracts `0-diff` & `lint-imports`)**:
  - Verify `scripts/export_openapi.py --check` (`0-diff`) and `.venv/bin/lint-imports` (`5/5` contracts).
- **Security / Red-Team Layer (`tests/security/`)**:
  - Add `tests/security/test_story_29_2_confidential_isolation.py` testing all 5 `CONFIDENTIAL_RESTRICTED` isolation surfaces (`evaluator`, `ontology/permissions`, `POST /rag/search`, `workspace_governance`, `workspace_datasources`, `sql_federated_search`) + `PATCH` `OBSERVER` / cross-team / `PRIVATE_USER` rejections.

---

## 3. Summary of Changes & Results (Post-Implementation)

### 3.1 Created and Modified Files

| File | Action | Lines | Summary of Changes |
| :--- | :--- | :---: | :--- |
| `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_workspace_patch.py` | Created | `262` | Added `patch_workspace_on_postgres18(...)` atomic SQL transaction (`workspaces` update, `settings_jsonb` `lifecycle_phase`/`ui_visibility_mode` merge, `PRIVATE_USER` immutability lock, explicit actor `workspace_memberships` upsert on `CONFIDENTIAL_RESTRICTED`, and `platform_settings` sync). |
| `packages/orcia-core/src/orcia_core/bootstrap/workspaces_patch.py` | Created | `10` | Exposed public hexagonal entrypoint `patch_workspace_on_postgres18` for `apps/api` without `_internal` cross-package imports. |
| `packages/orcia-core/src/orcia_core/bootstrap/_internal/_sql_workspaces_sync.py`, `sql_workspaces.py`, `sql_platform_setup_reconcilers.py`, `sql_platform_setup_relational_sync.py` | Modified | `223` / `207` / `270` / `416` | Preserved creator explicit membership on `CONFIDENTIAL_RESTRICTED` without granting unrelated `PLATFORM_ADMIN` silent access; aligned reconcilers, relational sync, and workspace summaries. |
| `packages/orcia-core/src/orcia_core/permissions/evaluator.py`, `_default_service.py`, `models.py` | Modified | `394` / `237` / `230` | Guarded `DIRECT_TEAM` branch against `CONFIDENTIAL_RESTRICTED` bypass (while preserving `compute_finops_rollup_usd`); added explicit `marc` membership on `_WS_CONF` and hardened `resolve_workspace_access`. |
| `packages/orcia-core/src/orcia_core/permissions/errors.py` & `_error_catalog.py` | Modified | `384` / `295` | Added `PrivateWorkspaceVisibilityLockedError` (`403 ERR_PRIVATE_WORKSPACE_VISIBILITY_LOCKED`) with bilingual FR/EN RFC 9457 catalog entries. |
| `packages/orcia-core/src/orcia_core/ontology/permissions.py`, `_promotion_permissions.py`, `_promotion_runner.py`, `_internal/sql_ontology_mappers.py` | Modified | `294` / `192` / `186` / `248` | Hydrated `personal_owner_user_id` and `ui_visibility_mode`; enforced strict `PRIVATE_USER` and `CONFIDENTIAL_RESTRICTED` isolation across `can_read_ontology_item`, `can_write_ontology_level`, and promotion helpers. |
| `packages/orcia-core/src/orcia_core/orchestration/control_center.py` & `_control_center_helpers.py` | Modified | `279` / `213` | Masked `CONFIDENTIAL_RESTRICTED` run metadata (`workspace_name`, `workflow_key`, `title`, `current_step_key`, `access_mode="READ_ONLY_OBSERVER"`, cleared claimer fields), excluded masked runs from `contributor_runs` and datasources from `datasources` list. |
| `packages/orcia-core/src/orcia_core/rag/_internal/sql_federated_search.py`, `_sql_federated_search_queries.py`, `_two_speed_search_helpers.py`, `_two_speed_search_models.py`, `two_speed_search.py` | Modified / Created | `155` / `299` / `194` / `169` / `262` | Extracted `_sql_federated_search_queries.py`; removed `:is_admin` / `*_ADMIN_ONLY_ROLES` bypass on `CONFIDENTIAL_RESTRICTED` workspaces and `WORKSPACE_OPEN` folders inside `⌘K` Federated Search and two-speed search. |
| `apps/api/src/orcia_api/schemas/org_and_workspaces.py` & `auth_and_org.py` | Created / Modified | `41` / `285` | Added `WorkspacePatchRequest` and `WorkspacePatchResponse` schemas in dedicated `org_and_workspaces.py` module. |
| `apps/api/src/orcia_api/routers/org_and_workspaces.py`, `_workspace_patch_helpers.py`, `_workspace_summary_serializer.py` | Modified / Created | `303` / `266` / `54` | Wired `PATCH /api/v1/workspaces/{workspace_id}` with `ScopeAccessGuard` (`OBSERVER` 403, org/team governance, `PRIVATE_USER` 403, self-lockout protection, `audit_ledger` `WORKSPACE_UPDATED`, evaluator sync). |
| `apps/api/src/orcia_api/routers/ontology_and_rag.py`, `_ontology_rag_guards.py`, `_ontology_resolve_guards.py`, `_ontology_promotions_{decide,handlers,helpers}.py`, `control_center.py`, `workspace_governance.py`, `_workspace_governance_helpers.py`, `workspace_datasources.py`, `_workspace_datasources_helpers.py`, `codegraph_mcp.py`, `datasource_webhooks.py`, `dna_and_glossary.py`, `enterprise_connectors.py`, `portal_and_help.py`, `workspace_leases.py`, `_auth_pg_helpers.py`, `_auth_bearer_rehydration.py`, `_bootstrap_evaluator_sync.py`, `dependencies/_topology_sync.py`, `errors/_registry_classes.py` | Modified / Created | `266` / `295` / `275` / `215` / `290` / `242` / `274` / `279` / `147` / `259` / `208` / `219` / `309` / `286` / `498` / `246` / `171` / `278` / `72` / `157` / `201` / `275` | Extracted `_ontology_rag_guards.py`, `_ontology_resolve_guards.py`, `_workspace_governance_helpers.py`, `_workspace_datasources_helpers.py`, and `_auth_bearer_rehydration.py`; enforced fail-closed workspace/lineage isolation across `/ontology/resolve` and `/ontology/what-if`, promotion proposal/decision guards (`_ontology_promotions_{decide,handlers,helpers}.py`), `GLOBAL`/empty-scope write guards (`enforce_ontology_rag_workspace_access` rejecting `OBSERVER` and `BU_DIRECTOR` or zero writable workspaces), `POST /ontology-rag/rag/search`, `GET /ontology-rag/state`, PG topology sync in `control_center.py`, all `workspace_governance` routes (removing `PLATFORM_ADMIN` bypass), all `workspace_datasources` routes, CodeGraph MCP, DNA/glossary, connectors, webhooks, portal/help, and leases. |
| `packages/api-client/openapi.json`, `src/domains/authAndShell.ts`, `src/generated/auth_and_org.ts`, `src/generated/schema.ts` | Regenerated / Modified | — / `197` / `41` / `7320` | Regenerated OpenAPI 3.1 contract (`0-diff`) and added typed `patchWorkspace(...)` client operation. |
| `apps/web/src/components/platformSetupWorkspaces.ts`, `platformSetupWorkspaceActions.ts`, `platformSetupScopeAndDatasources.ts`, `platformSetupStore.tsx`, `platformSetupContextTypes.ts`, `usePlatformSetupHydrationEffect.ts`, `ShellAuthFallbackView.tsx`, `platformSetupGovernanceActions.ts`, `platformSetupHydration.ts`, `platformSetupHydrationMappers.ts`, `platformSetupOrgAndRbacActions.ts` | Modified / Created | `221` / `175` / `116` / `256` / `192` / `239` / `94` / `245` / `258` / `261` / `244` | Wired `updateWorkspaceVisibility` and `updateWorkspacePhase` to `client.patchWorkspace(...)` with transactional state rollback on HTTP error, zero premature `localStorage` mutation, suppressed duplicate global `lastSyncError`, extracted `platformSetupScopeAndDatasources.ts`, and aligned banner inset. |
| `apps/web/src/features/workspaces/WorkspaceCompactHeader.tsx`, `index.tsx`, `workspaceFeedbackTypes.ts`, `WorkspaceDnaAndWaiversSection.tsx`, `WorkspaceGlossaryAndOntologyTab.tsx`, `WorkspaceMembersAndSettingsTab.tsx`, `WorkspaceMembersInstructionsCard.tsx`, `WorkspaceSourcesRagTab.tsx`, `WorkspaceStudioCardsAndDetailView.tsx`, `useWorkspaceDnaAndWaivers.ts`, `apps/web/src/i18n/locales/rfc9457_banner_labels_{fr,en}.ts`, `shell_chrome_labels*.ts` | Modified / Created | `300` / `219` / `19` / `233` / `298` / `116` / `245` / `298` / `99` / `296` / `141` / `132` / `104–110` | Replaced `"⚠️ "` string prefix hacks with typed `WorkspaceAlertFeedback` (`tone: "crimson" \| "emerald"`), routed `WorkspaceGlossaryAndOntologyTab.tsx` errors via `onFeedback` into the single aligned parent banner (`reportError`), and ensured bilingual FR/EN RFC 9457 remediation copy. |
| `tests/unit/test_story_29_2_workspace_patch_and_isolation.py`, `test_story_29_2_workspace_patch_and_sync.py`, `test_story_29_2_ontology_guards.py`, `test_story_29_2_sql_patch_and_evaluator_cov.py`, `test_story_29_2_workspace_hydration_sync.py`, `test_story_29_2_security_hardening.py`, `test_permissions_and_auth.py`, `test_story_23_5_search_coverage.py`, `test_epic_11_story_11_{1,2}_*.py`, `connectors/test_story_18_3_*.py` | Created / Modified | `298` / `219` / `296` / `291` / `145` / `239` / `531` / `417` / `348` / `209` / `416` | Split and added Story 29.2 unit tests (`<= 298` L each) covering `PATCH` governance, sync, SQL patch helpers, evaluator isolation, ontology resolve/what-if/promotion/GLOBAL guards, hydration sync, and security hardening. |
| `tests/security/_story_29_2_fixtures.py` & `tests/security/test_story_29_2_confidential_isolation.py` | Created | `140` / `263` | Extracted `_story_29_2_fixtures.py` and added Red-Team security suite covering all `CONFIDENTIAL_RESTRICTED` isolation surfaces plus `OBSERVER`, cross-team, and `PRIVATE_USER` rejections. |
| `tests/integration/api/_story_29_2_pg18_boot.py`, `test_story_29_2_workspace_patch_and_isolation_pg18.py`, `test_story_18_1_workspace_sources_postgres18.py`, `test_story_23_5_federated_search_postgres18.py` | Created / Modified | `135` / `281` / `287` / `723` | Extracted `_story_29_2_pg18_boot.py` and verified real `create_app()` PG18 integration for `PATCH /api/v1/workspaces/{id}`, SQL persistence (`workspaces`, `workspace_memberships`, `audit_ledger`), and `CONFIDENTIAL_RESTRICTED` runtime isolation. |
| `apps/web/src/__tests__/story-29-2-workspace-patch-rollback-and-banner.test.tsx`, `story-29-2-subtab-single-alert-and-i18n.test.tsx`, `story-29-2-glossary-single-alert.test.tsx`, `workspaces-en-contributor-and-alert-audit.test.tsx`, `workspacesAndCatalogMockHandlers.ts`, `i18n-and-shell.test.tsx`, `story-22-1`, `story-24-2`, `story-28-3`, `workspaces-single-tabs-anti-stacking-audit.test.tsx`, `e2e/07`, `e2e/13`, `e2e/support/*` | Created / Modified | `270` / `288` / `157` / `176` / `409` / ... | Added Vitest rollback, sub-tab single-alert, glossary `onFeedback` single-alert, and FR/EN i18n tests (`<= 288` L each), updated mock handlers, and aligned E2E support helpers. |

### 3.2 Quantitative Metrics, Coverage & Static Quality
- **Story 29.2 Combined 11-Module Branch Coverage (Distinct Final Re-Test Run via `coverage run --branch` + `--no-cov`)**: **`97%`** (`706` statements, `15` missed, `238` branches, `16` partial across `83 passed` tests in `45.82s`):
  - `sql_workspace_patch.py`: `99%`, `workspaces_patch.py`: `100%`, `ontology/_promotion_permissions.py`: `93%`, `orchestration/_control_center_helpers.py`: `80%`, `orchestration/control_center.py`: `95%`, `permissions/_error_catalog.py`: `100%`, `permissions/errors.py`: `100%`, `permissions/evaluator.py`: `100%`, `rag/_internal/_sql_federated_search_queries.py`: `100%`, `rag/_internal/sql_federated_search.py`: `100%`, `rag/_two_speed_search_helpers.py`: `93%`.
- **Static Quality & Contracts**:
  - `.venv/bin/pytest --no-cov tests/unit/test_i18n_backend_catalog_and_english_dev_audit.py`: **`3 passed in 8.09s`**
  - `.venv/bin/ruff check .`: `All checks passed!` (`0` errors)
  - `.venv/bin/ruff format --check .`: `1737 files already formatted`
  - `.venv/bin/mypy --strict packages/orcia-core packages/orcia-connectors apps/api apps/worker`: `Success: no issues found in 856 source files`
  - `.venv/bin/lint-imports`: `Contracts: 5 kept, 0 broken.` (`899` files, `6482` dependencies)
  - `.venv/bin/python .agent/skills/bmad-architecture/scripts/lint_spine.py --workspace docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24`: `ok: true, total_findings: 0`
  - `.venv/bin/python scripts/export_openapi.py --check`: `0-diff` (`exit 0`)
  - Line-count control: All `29` newly created/split `.py`, `.ts`, `.tsx`, and `.md` files are strictly `<= 299` lines (`_sql_federated_search_queries.py` `299`, `test_story_29_2_workspace_patch_and_isolation.py` `298`, `test_story_29_2_ontology_guards.py` `296`, `_ontology_rag_guards.py` `295`, `test_story_29_2_sql_patch_and_evaluator_cov.py` `291`, `story-29-2-subtab-single-alert-and-i18n.test.tsx` `288`, `test_story_29_2_workspace_patch_and_isolation_pg18.py` `281`, `_ontology_resolve_guards.py` `275`, `story-29-2-workspace-patch-rollback-and-banner.test.tsx` `270`, `_workspace_patch_helpers.py` `266`, `test_story_29_2_confidential_isolation.py` `263`, `sql_workspace_patch.py` `262`).

### 3.3 AD-17 Test Pyramid, Guardrails & GitNexus Output
- **Layer 1a (Python Unit, Security, Contract & Evals)**:
  - `tests/security tests/contract tests/evals`: **`181 passed in 58.61s`** (`--no-cov`, including `test_story_29_2_confidential_isolation.py`).
  - Combined branch-coverage unit batch (`test_story_29_2_*.py`, `test_story_20_2_ontology_permissions_and_promotions.py`, `test_permissions_and_auth.py`, `test_story_22_1_workspaces_permissions_and_bootstrap.py`, `test_story_23_5_search_coverage.py`, `test_hybrid_rag_and_tripartite.py`, `test_epic_9_story_9_3_two_speed_search.py`, `test_story_5_2_control_center_and_run_access_guard.py`, `test_ontology_and_what_if.py`, `test_epic_11_story_11_2_dna_starlark_and_glossary.py`, `test_story_17_3_iam_accounts_and_role_matrix.py`, `test_story_19_6_rag_blocking_and_embedding_model.py`): **`83 passed in 45.82s`**.
  - Remaining targeted unit suite (`test_story_18_3_codegraph_mcp_tools_and_providers.py`, `test_openapi_security.py`): **`45 passed in 8.72s`**.
- **Layer 1b (Frontend Vitest & Turbo Monorepo)**:
  - `pnpm --filter @orcia/web exec vitest run --maxWorkers=4`: **`Test Files 84 passed (84), Tests 311 passed (311)`**.
  - `pnpm turbo run lint typecheck test --concurrency=1`: **`9 successful, 9 total`** (`@orcia/api-client`, `@orcia/ui`, `@orcia/web`).
- **Layer 2 (`HTTP ➔ PostgreSQL 18` `create_app()` Integration, `--no-cov`)**:
  - `test_story_29_2_workspace_patch_and_isolation_pg18.py`, `test_story_18_1_workspace_sources_postgres18.py`, `test_story_23_5_federated_search_postgres18.py`, `test_story_22_1_workspaces_permissions_pg18.py`: **`5 passed in 51.33s`**.
- **Layer 3 (OpenAPI 3.1 & `AD-19` Boundaries)**:
  - `scripts/export_openapi.py --check` (`0-diff`) and `.venv/bin/lint-imports` (`5 kept, 0 broken`).
- **Layer 5 (Playwright Desktop E2E, `env -u ORCIA_E2E_SEED_FIXTURES`)**:
  - `playwright test --project=desktop-cockpit` on `07-spaces-org-and-workspace-persistence.spec.ts`, `17-workspace-sources-codegraph-dna-and-ontology.spec.ts`, `11-screens-smoke-without-server-errors.spec.ts`, and `20-process-studio-v2-finops-and-log-sink.spec.ts`: **`8 passed (1.8m)`** against real ephemeral PostgreSQL 18 + Redis 7.4 (clean shutdown, zero leftover E2E Vite/API processes).
- **GitNexus & Diff Summary**:
  - `npx gitnexus analyze --index-only .`: `46,033 nodes | 78,979 edges | 795 clusters | 1529 flows` (`38.6s`).
  - `git diff --stat`: `87 files changed, 2659 insertions(+), 1951 deletions(-)` plus `29` newly created files.
