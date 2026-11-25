# Story 29.1 — Multi-Workspace Scope Resolution (`Mes Processus` 404, `FinOps` 403/Scope-Pill Sync) & Error-vs-Empty Mutual Exclusion

- **Date**: 2026-11-24
- **Story / Sprint Key**: `29-1-multi-workspace-scope-resolution-processes-404-finops-403-and-error-empty-guard` (`Epic 29` / Lot 1)
- **Capability(ies)**: `CAP-140`, `CAP-200`, `CAP-201` (`docs/product/capabilities.yaml`) — classification: `feature`
- **Author / Context**: Resolves findings `UH-01` (`P0`) and `UH-02` (`P0`) from `docs/planning-artifacts/sprint-change-proposal-2026-11-24-epic-29-ui-headers-scope-and-screen-consistency.md`. Ensures `Mes Processus` (`AutonomousRunsSupervisionPanel`) and `FinOps` (`useFinopsDashboardController` / `FinopsGovernanceDashboardView`) cleanly resolve authorized scopes under `"Tous mes espaces"` (`scope-global`), BU/Team nodes, or non-UUID/synthetic IDs without triggering false HTTP 404/403 banners, unselected scope pills, misleading remediation instructions, or contradictory empty-state cards underneath error alerts (`AD-17`, `AD-21`, `DESIGN.md` §2.2).
- **Associated Commits**: `pending (working tree)`

---

## 1. Needs Analysis & Tech Lead Impact Study (Pre-Implementation)

### 1.1 Context & Problem Statement
1. **`UH-01` — `Mes Processus` HTTP 404 & Contradictory Empty State**:
   - **Current behavior**: `AutonomousRunsSupervisionPanel.tsx` (`L14-L66`) accepts synthetic `^ws-\d+$` keys via `SETUP_WS_REGEX` and unconditionally calls `GET /api/v1/workspaces/${ws}/autonomous-runs` even when `"Tous mes espaces"` (`scope-global`) or a synthetic/non-UUID scope is selected. When `ws` is synthetic or unknown in PostgreSQL 18, `autonomous_supervision.py` -> `_finops_scope_guards.py` raises HTTP `422` (`validate_uuid`) or HTTP `404 ERR_RESOURCE_NOT_FOUND`. Moreover, `AutonomousRunsSupervisionPanel.tsx:L155-L162` renders `<p data-testid="processes-autonomous-supervision-empty">` even when `errorMessage !== null`. Similarly, `useShellAutonomousSupervision.ts:L11-L60` permits `^ws-\d+$` keys when polling workspace autonomous runs.
   - **Expected behavior**: Add a dedicated multi-workspace aggregation endpoint `GET /api/v1/autonomous-runs` (with optional `scope_id` filter for BU/Team/Workspace UUIDs) aggregating runs across `auth_svc.evaluator.resolve_accessible_workspaces(user)` while preserving `GET /api/v1/workspaces/{workspace_id}/autonomous-runs`. In the frontend, when `scope-global` (`"Tous mes espaces"`), an org unit (`BU`/`TEAM`), or any non-UUID/synthetic scope ID is active, call `listAutonomousRuns` cleanly (never firing a doomed `GET /api/v1/workspaces/scope-global/autonomous-runs` or `ws-*` 404). Suppress `processes-autonomous-supervision-empty` whenever `errorMessage !== null`.
2. **`UH-02` — `FinOps` HTTP 403, Scope Pill Desync, Misleading Copy & Contradictory Empty Notice**:
   - **Current behavior**:
     - `useFinopsDashboardController.ts:L29-L60` maps `scope-global` (`"Tous mes espaces"`) unconditionally to `"GLOBAL"` regardless of caller RBAC role, and maps `activeScopeNode.level === "BU"` to `"BU"`, while line `L120` silently falls back to `"GLOBAL"` whenever `targetScopeId` is `null`.
     - `FinopsGovernanceDashboardView.tsx:L150-L171` renders fixed `["WORKSPACE", "TEAM", "GLOBAL"]` pills without hiding unauthorized `"Plateforme entière"` (`GLOBAL`) for non-global roles (`TEAM_LEAD`, `CONTRIBUTOR`) and without matching `scopeType === "BU"` (`0` of `3` pills have `aria-selected="true"`).
     - `FinopsGovernanceDashboardView.tsx` + `FinopsKpiStrip.tsx` render the `"Aucune consommation..."` white notice card (`finops-empty-state`) and placeholder empty copy even when `error !== null`.
     - `_finops_scope_guards.py:L124` checks only `user.platform_role` (`not in ("BU_DIRECTOR", "TEAM_LEAD", "OBSERVER")`) and omits `user.roles` (`TEAM_LEAD`, `BU_LEAD`, `SECOPS`).
     - `apps/web/src/i18n/locales/rfc9457_banner_labels_{fr,en}.ts:L11-L16` shows `"Sélectionnez un espace autorisé ou demandez l'habilitation dans Mon Organisation."` / `"Select an authorized space or request access in My Organization."` for `ERR_SCOPE_ACCESS_DENIED`, misdirecting `TEAM_LEAD`/business users to an admin-restricted screen.
   - **Expected behavior**:
     - Under `scope-global` (or an unauthorized `BU`/`TEAM` node), `useFinopsDashboardController.ts` auto-defaults to the caller's highest authorized FinOps scope (`GLOBAL` only for `PLATFORM_ADMIN` / `SECOPS` / global `OBSERVER`, `BU` for `BU_DIRECTOR` / `BU_LEAD`, `TEAM` for `TEAM_LEAD`, `WORKSPACE` otherwise).
     - `FinopsGovernanceDashboardView.tsx` hides unauthorized scope pills (`Plateforme entière` for non-global callers) and maps `"BU"` onto `"Cette Équipe ou Division"` (`finops-scope-team`) so **exactly one** scope pill always has `aria-selected="true"`.
     - Suppress `"Aucune consommation..."` (`finops-empty-state` and placeholder notices) whenever `error !== null`.
     - Update `ERR_SCOPE_ACCESS_DENIED` remediation in `rfc9457_banner_labels_{fr,en}.ts` to bilingual guidance recommending selecting an authorized team/workspace scope or contacting a division or platform administrator.

### 1.2 Exploration, GitNexus Impact Analysis, Refactoring & Technical Debt
- **GitNexus Impact Analysis (`repo: /home/romain/Documents/Projects/ORCIA`, index 5 commits behind HEAD)**:
  - `gitnexus_context(name="get_finops_dashboard")` & `gitnexus_query("resolve_finops_read_scope FinopsGovernanceDashboardView AutonomousRunsSupervisionPanel")`:
    - `apps/api/src/orcia_api/routers/finops.py:get_finops_dashboard` (`L51-L151`), `finops_cognitive.py:get_cognitive_impact`, `finops_remote.py:list_remote_services_telemetry` all depend on `_finops_scope_guards.resolve_finops_read_scope`.
    - `apps/web/src/features/finops/index.tsx` and `apps/web/src/__tests__/story-6-2*`, `story-6-3*`, `story-6-4*`, `story-7-4*` consume `FinopsGovernanceDashboardView` and `useFinopsDashboardController`.
    - `apps/web/src/features/processes/ProcessesHubPage.tsx` and `apps/web/src/components/useShellAutonomousSupervision.ts` consume `listWorkspaceAutonomousRuns` via `@orcia/api-client`.
  - **Blast radius / Risk**: Low-to-Medium; backward compatibility with `GET /api/v1/workspaces/{workspace_id}/autonomous-runs` and existing `PLATFORM_ADMIN` FinOps tests is preserved by making new props optional (`allowedScopes?`, `error?`) and keeping `workspace_id: str | None = None` on `AutonomousRunsListResponse`.
- **Exploration & Key Metrics**:
  - Verified `_sql_scope_filter.py` (`safe_uuid`, `build_scoped_cte_with_acl`) and `sql_autonomous_supervision.py` (`list_autonomous_runs_sql`, 271 lines).
  - Verified existing PG18 tests (`test_story_6_2_finops_postgres18.py:L551`, `test_story_6_3_cognitive_impact_postgres18.py:L483`) expect `200` on `?scope_type=GLOBAL` when a restricted caller has accessible workspaces (scoped strictly to `allowed_workspace_ids=accessible_ids`). Therefore `_finops_scope_guards.py` must preserve that scoped `accessible_ids` behavior while adding `user.roles` (`TEAM_LEAD`, `BU_LEAD`, `SECOPS`) recognition in `resolve_finops_read_scope`.
- **Refactoring Opportunities & File Line-Count Control (`<= 300` lines)**:
  - `packages/orcia-core/src/orcia_core/orchestration/_internal/sql_autonomous_supervision.py` (`271` lines): deduplicate `list_autonomous_runs_sql` by delegating to `list_autonomous_runs_for_workspaces_sql` (`WHERE wr.workspace_id = ANY(:ws_ids)`) instead of duplicating the 65-line SQL CTE/JOIN query.
  - `apps/api/src/orcia_api/routers/autonomous_supervision.py` (`226` lines): extract `_map_runs_to_schema(runs)` shared helper to avoid duplicating the 17-line response item comprehension across single-workspace and multi-workspace endpoints.
  - `apps/web/src/features/finops/useFinopsDashboardController.ts` (`299` lines): extract pure RBAC scope derivation helpers into `apps/web/src/features/finops/finopsScopeResolver.ts` so `useFinopsDashboardController.ts` stays well below `300` lines (`<= 270` lines).

---

## 2. Implementation Plan

### 2.1 Data Schema & Alembic Migrations
- None required. All required tables (`workflow_runs`, `workflow_definitions`, `workflow_triggers`, `autonomous_post_hoc_audits`, `autonomy_contracts`, `workspaces`, `org_units`) already exist.

### 2.2 Hexagonal Core, Orchestration & Workers (`packages/orcia-core/`)
- `packages/orcia-core/src/orcia_core/orchestration/_internal/sql_autonomous_supervision.py`:
  - Add `list_autonomous_runs_for_workspaces_sql(engine, *, workspace_ids: tuple[str, ...], limit: int = 100)` using `WHERE wr.workspace_id = ANY(:ws_ids)` (returning `[]` immediately when `workspace_ids` or parsed UUIDs are empty) and delegate `list_autonomous_runs_sql` to it.
- `packages/orcia-core/src/orcia_core/orchestration/autonomous_supervision.py`:
  - Add `list_autonomous_runs_for_workspaces(self, *, workspace_ids: tuple[str, ...])` supporting both PG18 (`list_autonomous_runs_for_workspaces_sql`) and in-memory unit mode, sorted by `created_at_iso` descending.

### 2.3 Backend API, Security & Contracts (`apps/api/`, `packages/api-client/`)
- `apps/api/src/orcia_api/schemas/autonomous_supervision.py`:
  - Relax `AutonomousRunsListResponse.workspace_id` to `str | None = None`.
- `apps/api/src/orcia_api/routers/autonomous_supervision.py`:
  - Add `GET /api/v1/autonomous-runs` (`list_authorized_autonomous_runs`) with optional `scope_id: str | None = Query(None)` enforcing `auth_svc.evaluator.resolve_accessible_workspaces(user)` (and `resolve_finops_read_scope` / `user_governs_org_unit` when `scope_id` is passed). Preserve `GET /api/v1/workspaces/{workspace_id}/autonomous-runs`.
- `apps/api/src/orcia_api/routers/_finops_scope_guards.py`:
  - Check both `user.platform_role` and `user.roles` (`{"BU_DIRECTOR", "BU_LEAD", "TEAM_LEAD", "OBSERVER", "SECOPS"}`) in `resolve_finops_read_scope` global branch so role-bearing leads without workspaces yet do not hit spurious 403s, while preserving strict `accessible_ids` workspace isolation.
- `packages/api-client/src/domains/autonomousSupervision.ts` + `scripts/export_openapi.py`:
  - Add `listAutonomousRuns(params?: { scopeId?: string | null })` and regenerate `packages/api-client/openapi.json` and `packages/api-client/src/generated/` (`0-diff` verified via `--check`).

### 2.4 User Interface & Experience (`apps/web/`, `packages/ui/`)
- `apps/web/src/features/processes/AutonomousRunsSupervisionPanel.tsx` & `apps/web/src/components/useShellAutonomousSupervision.ts`:
  - Remove synthetic `^ws-\d+$` acceptance; only treat an actual workspace UUID from `scopes`/`workspaces` as an exact workspace target for `listWorkspaceAutonomousRuns(wsUuid)`.
  - For `"Tous mes espaces"` (`scope-global`), `BU`/`TEAM` org units, or any non-UUID/synthetic ID, call `apiClient.listAutonomousRuns(...)` (passing `scopeId` only when `activeScopeId` is a valid org-unit UUID).
  - Suppress `processes-autonomous-supervision-empty` whenever `errorMessage !== null`.
- `apps/web/src/features/finops/finopsScopeResolver.ts` & `useFinopsDashboardController.ts` & `apps/web/src/features/finops/index.tsx`:
  - Compute `allowedScopePills`, `allowedModalScopes`, and `highestAuthorizedScope` from `useAuthSessionStore((s) => s.roles)` (`GLOBAL` only for `PLATFORM_ADMIN` / `SECOPS` / `OBSERVER`, `BU` for `BU_DIRECTOR` / `BU_LEAD`, `TEAM` for `TEAM_LEAD`, `WORKSPACE` fallback).
  - Under `scope-global` (or unauthorized `BU`/`TEAM` nodes), auto-default `selectedScope` to the caller's highest authorized FinOps scope; never fall back to `"GLOBAL"` when `targetScopeId` is null for non-global users.
  - Map `"TEAM"` pill click in `FinopsGovernanceDashboardView` to `"BU"` when `activeScopeNode?.level === "BU"` or when caller is `BU_DIRECTOR`/`BU_LEAD` without a team-specific selection.
  - Pass `error={ctrl.errorMessage}` and `allowedScopes={ctrl.allowedScopePills}` / `allowedModalScopes={ctrl.allowedModalScopes}` to `FinopsGovernanceDashboardView`.
- `packages/ui/src/primitives/finops/FinopsGovernanceDashboardView.tsx`, `FinopsKpiStrip.tsx`, `FinopsBudgetPolicyModal.tsx`:
  - Accept optional `allowedScopes`, `allowedModalScopes`, and `error?: string | null`.
  - Hide unauthorized scope pills when `allowedScopes` is provided, and treat `scopeType === "BU"` as selecting the `"TEAM"` (`Cette Équipe ou Division`) pill so **exactly one** pill has `aria-selected="true"`.
  - Suppress `finops-empty-state` (`"Aucune consommation..."`) and placeholder empty notices whenever `error !== null`.
- `apps/web/src/i18n/locales/rfc9457_banner_labels_{fr,en}.ts`:
  - Replace the misleading `"demandez l'habilitation dans Mon Organisation"` / `"request access in My Organization"` remediation in `ERR_SCOPE_ACCESS_DENIED` with accurate bilingual FR/EN guidance (selecting an authorized team/workspace scope or contacting a division or platform administrator).

### 2.5 Test Pyramid Impact Analysis (`AD-17` — Layers 1 to 5 + Security, Mandatory)
- **Layer 1a (`tests/unit/`)**: Add targeted unit tests in `tests/unit/test_story_29_1_scope_resolution.py` covering `AutonomousSupervisionService.list_autonomous_runs_for_workspaces`, `GET /api/v1/autonomous-runs` RBAC/CONFIDENTIAL_RESTRICTED filtering, and `_finops_scope_guards.resolve_finops_read_scope` role checks.
- **Layer 1b (`apps/web/src/__tests__/` & `packages/ui/src/__tests__/`)**: Update `vitestAutonomousSupervisionMockHandlers.ts` for `/api/v1/autonomous-runs` and add targeted tests in `apps/web/src/__tests__/story-29-1-processes-and-finops-scope.test.tsx` + `packages/ui/src/__tests__/story-29-1-finops-pills-and-error-guard.test.tsx` verifying `scope-global` multi-workspace listing, non-UUID `ws-*` safety, `TEAM_LEAD`/`BU_DIRECTOR`/`PLATFORM_ADMIN` FinOps auto-scoping, single `aria-selected="true"` pill under `BU`, unauthorized pill hiding, `error !== null` empty-state suppression, and bilingual FR/EN error guidance.
- **Layer 2 (`tests/integration/api/`)**: Add PG18 integration test in `tests/integration/api/test_story_29_1_autonomous_runs_and_finops_pg18.py` verifying `GET /api/v1/autonomous-runs` real Composition Root aggregation across authorized workspaces (excluding `CONFIDENTIAL_RESTRICTED`/`PRIVATE_USER` non-member spaces) and `FinOps` `TEAM`/`BU`/`GLOBAL` scope resolution against real PG18.
- **Layer 3 (`OpenAPI 3.1`, `lint-imports`)**: Verify `scripts/export_openapi.py --check` (`0-diff`) after regenerating SDK.
- **Layer 4 & Security**: Covered by existing `tests/security/` and `tests/evals/` (delegated to Testing sub-agent for full verification).
- **Layer 5 (Playwright E2E)**: Delegated to Testing sub-agent (`env -u ORCIA_E2E_SEED_FIXTURES`).

---

## 3. Summary of Changes & Results (Post-Implementation)

### 3.1 Created & Modified Files (All Production Modules `<= 296` Lines)
| File | Action | Line Count | Concise Summary |
| :--- | :--- | :---: | :--- |
| `packages/orcia-core/src/orcia_core/orchestration/_internal/sql_autonomous_supervision.py` | Modified | `284` | Added `list_autonomous_runs_for_workspaces_sql` (`WHERE wr.workspace_id = ANY(:ws_ids)`) and delegated `list_autonomous_runs_sql` to eliminate SQL CTE duplication. |
| `packages/orcia-core/src/orcia_core/orchestration/autonomous_supervision.py` | Modified | `292` | Added `list_autonomous_runs_for_workspaces` supporting both PG18 SQL aggregation and sorted in-memory execution. |
| `apps/api/src/orcia_api/schemas/autonomous_supervision.py` | Modified | `110` | Relaxed `AutonomousRunsListResponse.workspace_id` to `str \| None = None` for multi-workspace aggregation. |
| `apps/api/src/orcia_api/routers/autonomous_supervision.py` | Modified | `284` | Added `GET /api/v1/autonomous-runs` with optional `scope_id` filter (`BU`/`TEAM`/`WORKSPACE`), RBAC `resolve_accessible_workspaces` & `user_governs_org_unit` enforcement, and shared `_map_runs_to_schema` helper. |
| `apps/api/src/orcia_api/routers/_finops_scope_guards.py` | Modified | `181` | Checked both `user.platform_role` and `user.roles` (`BU_DIRECTOR`, `BU_LEAD`, `TEAM_LEAD`, `OBSERVER`, `SECOPS`) in `resolve_finops_read_scope` while preserving strict `accessible_ids` isolation. |
| `packages/api-client/src/domains/autonomousSupervision.ts` | Modified | `76` | Added `listAutonomousRuns(params?: { scopeId?: string \| null })` client operation. |
| `packages/api-client/openapi.json` & `src/generated/schema.ts` | Regenerated | — | Regenerated OpenAPI 3.1 schema and TypeScript SDK (`0-diff` verified via `export_openapi.py --check`). |
| `apps/web/src/features/processes/AutonomousRunsSupervisionPanel.tsx` | Modified | `221` | Removed synthetic `^ws-\d+$` acceptance; routed `scope-global`, `BU`/`TEAM` nodes, and non-UUID IDs through `listAutonomousRuns`, and suppressed `processes-autonomous-supervision-empty` when `errorMessage !== null`. |
| `apps/web/src/components/useShellAutonomousSupervision.ts` & `useShellContainerState.ts` | Modified | `85` / `221` | Synced shell autonomous supervision polling with exact workspace UUIDs / multi-workspace endpoint and scope state. |
| `apps/web/src/features/finops/finopsScopeResolver.ts` | Created | `89` | Extracted pure RBAC scope derivation (`allowedScopePills`, `allowedModalScopes`, `highestAuthorizedScope`, `BU` $\rightarrow$ `TEAM` pill mapping). |
| `apps/web/src/features/finops/useFinopsDashboardController.ts` & `useFinopsDashboardMutations.ts` & `index.tsx` | Modified / Created | `277` / `187` / `74` | Auto-defaulted `scope-global` to caller's highest authorized FinOps scope, prevented non-global `GLOBAL` fallback, and passed `allowedScopes`/`error` to view. |
| `packages/ui/src/primitives/finops/FinopsGovernanceDashboardView.tsx`, `FinopsKpiStrip.tsx`, `FinopsBudgetPolicyModal.tsx` | Modified | `296` / `202` / `202` | Hid unauthorized scope pills (`Plateforme entière` for non-global callers), mapped `BU` onto `"Cette Équipe ou Division"` (single `aria-selected="true"`), and suppressed `finops-empty-state` / placeholder notices when `error !== null`. |
| `apps/web/src/i18n/locales/rfc9457_banner_labels_{fr,en}.ts` | Modified | `135` / `127` | Updated `ERR_SCOPE_ACCESS_DENIED` remediation in FR & EN to guide users to select an authorized team/workspace scope or contact an administrator. |
| `tests/unit/test_story_29_1_scope_resolution.py` & `test_story_29_1_scope_resolution_extra.py` | Created | `251` / `210` | Added 6 unit tests covering multi-workspace aggregation, RBAC/`CONFIDENTIAL_RESTRICTED` filtering, and `_finops_scope_guards`. |
| `tests/integration/api/test_story_29_1_autonomous_runs_and_finops_pg18.py` | Created | `282` | Added PG18 `create_app()` integration test verifying `/api/v1/autonomous-runs` aggregation and FinOps `TEAM`/`BU`/`GLOBAL` scope resolution. |
| `apps/web/src/__tests__/story-29-1-processes-and-finops-scope.test.tsx` & `vitestAutonomousSupervisionMockHandlers.ts` | Created / Modified | `286` / `401` | Added 4 Vitest integration tests + mock handler for `/api/v1/autonomous-runs`. |
| `packages/ui/src/__tests__/story-29-1-finops-pills-and-error-guard.test.tsx` | Created | `141` | Added 2 `@orcia/ui` component tests for `BU` pill mapping and error-vs-empty suppression. |
| `apps/web/e2e/20-process-studio-v2-finops-and-log-sink.spec.ts` | Modified | `256` | Extended Desktop E2E verification for multi-workspace Process Studio supervision and FinOps scope consistency. |

### 3.2 Quantitative Metrics, Coverage & Static Quality
- **Story 29.1 Branch Coverage (Final Verifier Run)**: **`100%`** (`66` statements, `0` missed, `8` branches, `0` partial) on `packages/orcia-core/src/orcia_core/orchestration/autonomous_supervision.py` across `17 passed` unit tests (`test_story_29_1_scope_resolution.py` `3`, `test_story_29_1_scope_resolution_extra.py` `3`, `test_story_7_4_*`, `test_orchestration_governance_gates_and_kill_switch_guard.py`).
- **Static Quality & Contracts (Final Verifier Run)**:
  - `.venv/bin/ruff check .`: `All checks passed!` (`0` warnings)
  - `.venv/bin/ruff format --check .`: `1715 files already formatted`
  - `.venv/bin/mypy --strict packages/orcia-core packages/orcia-connectors apps/api apps/worker`: `Success: no issues found in 845 source files`
  - `.venv/bin/lint-imports`: `Contracts: 5 kept, 0 broken` (`888` files, `6372` dependencies)
  - `.venv/bin/python scripts/export_openapi.py --check`: `0-diff` (`exit 0`)
  - `pnpm --filter @orcia/web run lint` & `typecheck`: `0` errors (`tsc --noEmit` + `check-feature-boundaries.mjs`)
  - `lint_spine.py` (baseline in cycle): `ok: true, 0 findings`
  - Line-count control: All modified and newly created production `.py`/`.ts`/`.tsx` modules `<= 296` lines (`vitestAutonomousSupervisionMockHandlers.ts` test helper `401` lines).

### 3.3 AD-17 Test Pyramid & Non-Regression Verification
- **Earlier Verified Non-Regression Baseline (Same Story 29.1 Cycle)**:
  - `pnpm turbo run lint typecheck test`: **`9/9`** packages green
  - `tests/security` + `tests/contract` + `tests/evals`: **`180/180`** passed
  - Non-PG18 `tests/unit`: Batch 1 **`572 passed`**, Batch 2 (excl. `7_0c`) **`492 passed`**, `7_0c` isolated **`5 passed`**, PG18 unit `testcontainers` **`25/25 passed`**
  - Impacted PG18 integration baseline: **`12/12 passed`**
  - Desktop Playwright E2E baseline (`11`, `12`, `13` with `env -u ORCIA_E2E_SEED_FIXTURES`): **`5 passed / 2 mobile-only skipped`**
  - Architecture spine lint (`lint_spine.py`): **`0 findings`**
- **Final Verifier Post-Edit Suite (`2026-11-25`)**:
  - **Layer 1a (Python Unit Coverage)**: `17 passed in 26.14s` (`autonomous_supervision.py` **`100%`** branch coverage via `coverage run --branch` + `--no-cov`).
  - **Layer 1b (`@orcia/ui` & `@orcia/web` Vitest)**: `@orcia/ui` `story-29-1-finops-pills-and-error-guard.test.tsx` **`2/2 passed`**; `@orcia/web` **`3/3 files, 9/9 passed`** (`e2e-testids-sync-audit.test.ts` `1/1`, `story-29-1-processes-and-finops-scope.test.tsx` `4/4`, `zero-dead-buttons-and-silent-catches-audit.test.tsx` `4/4`).
  - **Layer 2 (`HTTP ➔ PostgreSQL 18` `create_app()` Integration)**: `tests/integration/api/test_story_29_1_autonomous_runs_and_finops_pg18.py` + `test_story_7_4_supervision_rollback_postgres18.py`: **`2 passed in 39.92s`** (`--no-cov`).
  - **Layer 3 (OpenAPI 3.1 & `AD-19` Boundaries)**: `scripts/export_openapi.py --check` (`0-diff`) and `lint-imports` (`5 kept, 0 broken`).
  - **Layer 5 (Playwright Desktop E2E, `env -u ORCIA_E2E_SEED_FIXTURES`)**: `e2e/20-process-studio-v2-finops-and-log-sink.spec.ts` (`--project=desktop-cockpit`): **`2 passed (1.2m)`** against real ephemeral PostgreSQL 18 + Redis 7.4.
