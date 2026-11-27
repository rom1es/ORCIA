# Epic 31 Final Architecture & Security `VALIDATE` Report

- **Date:** `2026-11-26` (Round 1) / `2026-11-27` (Round 2 Closure)
- **Reviewer:** `bmad-architect-worker` (`pro`)
- **Branch / Worktree:** `feat/epic-31-declarative-apm-packs-import-export` (`/home/romain/.gemini/antigravity/worktrees/ORCIA/consignes_personnelles_save_button`, compared to local `main` at `cf36f3c`; remediated through commits `552fd146` and `6c51e40e`)
- **Scope:** Story 31.7 deliverables + Cross-story Epic 31 (`Stories 31.1–31.7`, Decisions `D1–D6`, `R1–R5`, `A1–A4`)
- **Round 1 Verdict (`2026-11-26`):** `CHANGES_REQUESTED` (historical findings retained below in Sections 1–5)
- **Current Verdict (`2026-11-27`):** **`Verdict: APPROVED`**

---

## 1. Executive Decision

Epic 31 establishes a strong hexagonal foundation (`declarative_pack_bundles` v2 DDL, `ApmPackCodec`, `PackImportService` + SeaweedFS CAS, flat `WORKSPACE_PACK` ontology priority, `run_lock_manifests` slot pinning, Pack Composer closure + `O(1)` PII/infra export scrubber, anti-hostage `409` unlink guard, bilingual `@orcia/ui` primitives, `<= 300 L` file discipline, and `0` GitNexus import cycles).

However, **final `VALIDATE` closure is blocked** by **1 `P0` security/RBAC isolation gap** and **3 `P1` cross-story contract/isolation/regression findings** observed directly in the current codebase:

| ID | Severity | Area | Short Summary |
| :--- | :---: | :--- | :--- |
| **`P0-1`** | **`P0`** | Security / `packs.py` | Unauthenticated `GET /api/v1/packs` & `/health`, missing `ScopeAccessGuard` on `POST /api/v1/packs/import` (including omitted/archive-override scopes) and `DELETE /api/v1/packs/{bundle_id}`, omitted from Story 31.7 red-team `cross_calls`. |
| **`P1-1`** | **`P1`** | Isolation / `Story 31.3` | `load_agents_and_skills_from_postgres18` & `resolve_pack_tier_for_row` leak unactivated custom packs and cross-workspace agents/skills into `?workspace_id=` listing & `@`/`/` resolution (`WORKSPACE_PACK` beats `SYSTEM_PACK`). |
| **`P1-2`** | **`P1`** | Contract / `D6.c`+`R5` | `PackSlotReadinessGuard` (`422 ERR_PACK_SLOT_UNBOUND`) is wired to Workflow/Orchestration run start only — missing pre-execution enforcement on `AssistantTurnEngine` (`POST /api/v1/assistant/turns`) and `GovernedMcpExposureService` (`POST /api/v1/mcp/spaces/*/invoke`). |
| **`P1-3`** | **`P1`** | Regression / `31.4 -> 31.7` | 3 Story 31.4-deferred PG18 integration test regressions (`test_story_16_3`, `test_story_30_3`, `test_story_3_2f`) remain unpatched and omitted from Story 31.7 `AD-17` verification. |

*(Plus 4 non-blocking `P2` observations documented in Section 4.)*

---

## 2. Verified Passing Invariants & Story 31.7 Fixes Checked

Note on verification boundary: the architect worker environment has file-read and GitNexus MCP inspection tools only (no shell tool); CLI/test execution claims below cite Story 31.7 Report §3.2 verbatim where not directly observable from source inspection.

1. **Circular Imports & `AD-19` Boundaries (Directly Verified via GitNexus)**:
   - `gitnexus:check({cycles: true})` on worktree repo: `status: "clean"`, `cycleCount: 0`, `cycles: []`.
   - `packages/orcia-core/src/orcia_core/packs/` and `domain/namespacing.py` keep pure evaluator/scrubber/namespacing modules (`slot_guard.py`, `namespacing.py`, `_pack_export_scrubber*.py`) free of FastAPI/SQLAlchemy imports.
2. **File Size Discipline (`<= 300 L`, Directly Verified on Inspected Files)**:
   - Story 31.7 files directly inspected: `_pack_export_scrubber_mappers.py` (`266 L`), `PackComposerModal.tsx` (`293 L`), `PackSlotBindingDrawer.tsx` (`285 L`), `packMappers.ts` (`188 L`), `useWorkspacePacksController.ts` (`224 L`), `DeclarativePacksRegistrySection.tsx` (`291 L`), `WorkspacePacksTabSection.tsx` (`75 L`), `test_story_31_7_packs_red_team_security.py` (`279 L`), `31-epic-31-declarative-apm-packs-roundtrip.spec.ts` (`298 L`), `test_e2e_sql_coverage_audit.py` (`297 L`), `story-31-6-pack-ui-primitives.test.tsx` (`283 L`).
   - Cross-story Epic 31 production files directly inspected all measure `<= 299 L` (`import_service.py` `295 L`, `sql_agents_and_skills.py` `293 L`, `_sql_workspace_pack_queries.py` `294 L`, `workflows.py` `294 L`, `assistant_turns.py` `297 L`, `agents_and_skills.py` `299 L`, `packs.py` `254 L`, `pack_composer.py` `258 L`, `workspace_packs.py` `238 L`, `composer_service.py` `253 L`, `entity_delete_tx.py` `278 L`, `packages/api-client/src/domains/packs.ts` `286 L`).
3. **Story 31.7 Production Bugfixes Verified**:
   - `_pack_export_scrubber_mappers.py:108-135`: `build_scrubbed_catalog_specs` pre-populates `skill_id_to_slug` for both `resource_id` and `id` of `USER_SKILL` / `skill` rows before mapping `skill_ids` / `skill_refs` on exported agents.
   - `PackComposerModal.tsx:82-128` & `PackSlotBindingDrawer.tsx:73-93`: `prevOpenRef` + `lastDraftIdRef` (+ `scopeId` backfill `useEffect`) and `initKeyRef` (`${pack.bundleId}:${pack.slug}`) prevent `scopeOptions` / parent rerenders from wiping typed draft metadata or slot selections.
   - `useWorkspacePacksController.ts:44-53` & `packMappers.ts:116-140`: `Promise.allSettled([listWorkspacePacks, listWorkspaceDatasources])` merges workspace PG18 datasources with fallback slot candidates via `mergeWorkspaceAndFallbackSlotCandidates`.
   - `PackComposerService` (`composer_service.py`), `_pack_closure_analyzer.py`, `pack_draft_guard.py`, `entity_delete_tx.py`, `_sql_agents_delete.py`, `_pack_export_scrubber.py`, `sql_pack_ontology_resolution.py`, and `_workflows_pack_lock_helpers.py` cleanly implement closure, `409` anti-hostage unlink + `audit_ledger`, `O(1)` PII/infra leak scanning, flat `WORKSPACE_PACK` ontology priority, and `run_lock_manifests` pinning.
4. **Domain Isolation & Doc/Registry Sync**:
   - `test_core_domain_isolation.py:47-80` locks zero forbidden domain keywords (`git_branch|wsjf|rovo|copilot|prd` globally in `orcia_core`; `jira|confluence|...` in isolated core subpackages).
   - `architecture.md:399, 416-420, 436` records the Epic 31 PG18 tables and API/SPA surfaces.
   - `sprint-status.yaml:1623-1653` tracks `ACTION_ITEM-31.1` (`P2`) and `ACTION_ITEM-31.2` (`P3`) cleanly as `open`.
   - Story 31.7 Tech Lead Report §3.2 records passing `ruff`, `mypy --strict`, `lint-imports` (`5/5`), `lint_spine.py` (`0` findings), `export_openapi.py --check` (`0-diff`), `detect-secrets-hook`, `94%` scoped branch coverage (`136 passed`), `196 passed` evals/security/contract, `12 passed` Epic-31 PG18+Redis+S3 integration, `9/9` Turbo (`556` tests), `8 passed` Playwright Desktop (`31`, `18`, `09`), and `site:sync`/`site:check`.

---

## 3. Blocking Findings (`P0` / `P1` — Must Fix Before Approval)

### `P0-1` — Missing Authentication & `ScopeAccessGuard` on `/api/v1/packs*` Catalog, Import & Bundle Delete (`Story 31.2` / `31.7`)
- **Affected Files & Lines:**
  - `apps/api/src/orcia_api/routers/packs.py:82-130` (`list_declarative_packs`, `check_packs_connectors_health`)
  - `apps/api/src/orcia_api/routers/packs.py:158-223` (`import_declarative_pack_archive`, `delete_declarative_pack_bundle`)
  - `apps/api/src/orcia_api/routers/_packs_router_helpers.py:43-58` (`enforce_pack_mutation_guard`)
  - `packages/orcia-core/src/orcia_core/packs/import_service.py:177-204` (`_apply_scope_overrides`)
  - `tests/security/test_story_31_7_packs_red_team_security.py:228-242` (`cross_calls`)
- **Observed Vulnerability:**
  1. `GET /api/v1/packs` (`packs.py:82-93`) and `GET /api/v1/packs/health` (`packs.py:96-130`) neither call `resolve_request_user(request)` nor filter `declarative_pack_bundles` rows by caller visibility (`GLOBAL` vs authorized `WORKSPACE`/`BU`/`TEAM`), leaking all tenant-scoped `CUSTOM` and `IMPORTED` bundles across workspaces/org units (contradicting `D2`).
  2. `enforce_pack_mutation_guard` (`_packs_router_helpers.py:43-58`) only inspects `ws_access.access_mode == "READ_ONLY_OBSERVER"` **when `ws_access is not None`**. When `ws_access is None` (e.g., `marc` importing into unauthorized `WS_B`), or `PRIVATE_USER` owned by another user, or `scope_type` in `("BU", "TEAM", "GLOBAL")`, **no `ScopeAccessDeniedError` (`403`) is raised**, and `sync_evaluator_topology_from_pg` is not invoked.
  3. Worse, if a caller omits `scope_type` / `scope_id` from `POST /api/v1/packs/import` (`parse_pack_import_payload` returns `None, None`), `packs.py:165` passes `None` to `enforce_pack_mutation_guard`, and `PackImportService._apply_scope_overrides` (`import_service.py:186-187`) falls back to `m.scope_type` / `m.scope_id` from inside the uploaded `.zip`'s `apm.yml`, allowing an unprivileged user to import directly into another tenant's `WS_B` or `ORG_B`.
  4. `DELETE /api/v1/packs/{bundle_id}` (`packs.py:201-223`) runs `enforce_pack_mutation_guard(request)` without fetching the bundle's `(scope_type, scope_id)` or checking `ScopeAccessGuard`, allowing any non-observer tenant user to delete another workspace's or org unit's bundle.
  5. `tests/security/test_story_31_7_packs_red_team_security.py:228-242` omitted `GET /api/v1/packs`, `POST /api/v1/packs/import`, `DELETE /api/v1/packs/{bundle_id}`, and `POST /api/v1/packs/{bundle_id}/export` from `cross_calls`.
- **Concrete Remediation:**
  1. Protect `GET /api/v1/packs` and `GET /api/v1/packs/health` using `compute_caller_composer_scopes` (`_pack_composer_helpers.py:36-61`) + bundle visibility filtering (`GLOBAL` or `scope_type`/`scope_id` within caller's `allowed_ws` / `allowed_orgs`, or `is_admin`).
  2. On `POST /api/v1/packs/import`: resolve effective `(scope_type, scope_id)` **before** persisting (including inspecting manifest defaults when request fields are omitted) and enforce `enforce_composer_scope_access(..., require_write=True)` (rejecting `GLOBAL` or unauthorized `WORKSPACE` / `PRIVATE_USER` / `BU` / `TEAM` with `403 ERR_SCOPE_ACCESS_DENIED`).
  3. On `DELETE /api/v1/packs/{bundle_id}`: look up the target bundle first via `import_svc.get_bundle(bundle_id)` and enforce `enforce_composer_scope_access(..., scope_type=bundle["scope_type"], scope_id=bundle["scope_id"], require_write=True)` (plus `403` if `GLOBAL` non-admin / `SYSTEM`).
  4. Expand `test_story_31_7_packs_red_team_security.py:cross_calls` to cover cross-tenant `GET /api/v1/packs` visibility, `POST /api/v1/packs/import` (both explicit `scope_id=WS_B`/`ORG_B` and `apm.yml`-embedded `scope_id=WS_B` with omitted form/JSON scope), `DELETE /api/v1/packs/{bundle_id}`, and `POST /api/v1/packs/{bundle_id}/export`.

### `P1-1` — Cross-Workspace & Unactivated Custom Pack Leakage in Agents & Skills Hydration (`Story 31.3`)
- **Affected Files & Lines:**
  - `packages/orcia-core/src/orcia_core/orchestration/_internal/_sql_agents_pack_queries.py:13-23, 26-80`
  - `packages/orcia-core/src/orcia_core/orchestration/_internal/sql_agents_and_skills.py:41-70`
  - `packages/orcia-core/src/orcia_core/orchestration/_agents_namespacing.py:26-93`
- **Observed Defect:**
  - `SQL_LOAD_AGENTS_AND_SKILLS_WITH_PACKS` (`_sql_agents_pack_queries.py:13-23`) selects all `USER_SKILL` and `USER_AGENT` rows across `catalog_items` with zero workspace/scope filtering.
  - `load_workspace_pack_priorities_pg` (`_sql_agents_pack_queries.py:26-63`) populates `inactive` **only** from existing `workspace_pack_activations` rows where `is_active = FALSE`. Any `CUSTOM` or `IMPORTED` pack that has never been activated in `WS_A` (including packs scoped to `WS_B` or `ORG_B`) is absent from `inactive_packs`, stays `enabled_in_workspace = True` (`sql_agents_and_skills.py:65-67`), and `resolve_pack_tier_for_row` (`_sql_agents_pack_queries.py:78-80`) falls through to `return "WORKSPACE_PACK"`.
  - Standalone `USER_AGENT` / `USER_SKILL` items owned by `WS_B` (`owner_workspace_id = WS_B`, `pack_bundle_id IS NULL`) also load unconditionally as `WORKSPACE_OVERRIDE` with `enabled_in_workspace = True`.
  - Result: `GET /api/v1/agents-and-skills?workspace_id=WS_A` and `/resolve?workspace_id=WS_A` expose foreign-workspace and unactivated custom packs, and `rank_workspace_entity_candidates` ranks an unactivated custom `WORKSPACE_PACK` above active `SYSTEM_PACK` entries.
- **Concrete Remediation:**
  - When `workspace_id` is passed to `load_agents_and_skills_from_postgres18`:
    1. Filter standalone entities (`pack_bundle_id IS NULL`) to `owner_workspace_id IS NULL` or matching `ws_uuid` (and check `ScopeAccessGuard` when `workspace_id` is supplied to `GET /api/v1/agents-and-skills` and `/resolve`).
    2. For pack-backed entities (`pack_slug IS NOT NULL`): require non-`SYSTEM` bundles to be both **visible** to `ws_uuid` and **explicitly active** (`pack_slug in active_priorities`); only `bundle_kind == "SYSTEM"` packs default active unless in `inactive_packs`. Mark unactivated/foreign pack rows `enabled_in_workspace = False` (or filter them out in workspace-scoped queries) so they never surface or win tie-breaks in `rank_workspace_entity_candidates`.

### `P1-2` — `PackSlotReadinessGuard` (`422 ERR_PACK_SLOT_UNBOUND`) Not Wired to `AssistantTurnEngine` or `GovernedMcpExposureService` (`D6.c` / `R5` / `A2`)
- **Affected Files & Lines:**
  - `docs/implementation-artifacts/epic-31-decisions-grill-2026-11-25.md:25, 110-114` (`D6.c`, `R5`, `A2`)
  - `apps/api/src/orcia_api/routers/assistant_turns.py:81-100` (`create_assistant_turn_endpoint`)
  - `apps/api/src/orcia_api/routers/mcp_and_test_bench.py:242-277` & `apps/api/src/orcia_api/routers/_mcp_assistant_ask_bridge.py:35-107`
  - `apps/api/src/orcia_api/routers/_workflows_pack_lock_helpers.py:27-44`
- **Observed Gap:**
  - Decision `D6.c` / `R5` / `A2` (`epic-31-decisions-grill-2026-11-25.md:110-114`) explicitly mandates `PackSlotReadinessGuard` (`HTTP 422 ERR_PACK_SLOT_UNBOUND`) prior to token spend/execution across **all three** runtimes: `ProcessExecutionDispatcher`, `AssistantTurnEngine`, and `GovernedMcpServerService`.
  - GitNexus call-graph and router inspections confirm `enforce_run_start_readiness` is wired only to `ProcessExecutionDispatcher` v2 (`_workflows_pending_runs.py:154`) and v1 orchestration (`orchestration.py:202`). `POST /api/v1/assistant/turns` and `POST /api/v1/mcp/spaces/{workspace_slug}/invoke` do not enforce `PackSlotReadinessGuard` before invoking pack-backed agents/skills/active workspace packs with unbound `required: true` connector slots.
- **Concrete Remediation:**
  - Wire a shared readiness preflight helper calling `WorkspacePacksService.enforce_run_start_readiness(...)` (scoped to invoked pack agent/skill or active workspace packs declaring required slots) in `assistant_turns.py` (pre-background task enqueue in `POST /api/v1/assistant/turns`) and `mcp_and_test_bench.py` / `_mcp_assistant_ask_bridge.py` (`POST /api/v1/mcp/spaces/{workspace_slug}/invoke`), plus unit + PG18 integration coverage asserting `422 ERR_PACK_SLOT_UNBOUND` before LLM invocation.

### `P1-3` — Story 31.4-Deferred PG18 Integration Test Regressions Still Unresolved
- **Affected Files & Lines:**
  - `docs/implementation-artifacts/tech-lead-reports/31-4-workspace-pack-activation-slot-bindings-422-guard-and-run-lock-pinning-tech-lead-report.md:140`
  - `tests/integration/api/test_story_16_3_dual_mode_processes_api.py:140-147`
  - `tests/integration/api/test_story_30_3_pending_runs_and_live_guard_postgres18.py:126-147`
  - `tests/integration/test_story_3_2f_real_api_run_and_restart_postgres18.py:42`
- **Observed Regression:**
  - Story 31.4 Report (`L140`) explicitly deferred 3 pre-existing PG18 integration fixture failures to Story 31.7 cleanup:
    1. `test_story_16_3_dual_mode_processes_api.py:140-147` and `test_story_30_3_pending_runs_and_live_guard_postgres18.py:126-147` build `create_app()` + `httpx.ASGITransport(app=...)` without entering `async with app.router.lifespan_context(app):`, so `seed_system_packs_on_engine` never populates `workflow_definitions_v2` (empty after Story 31.2 purged runtime disk fallback in `_workflows_helpers.py:54-66`).
    2. `test_story_3_2f_real_api_run_and_restart_postgres18.py:42` places PostgreSQL Unix sockets under `REPO_ROOT / ".pytest_cache" / "tc_3_2f"`, exceeding `AF_UNIX` path-length limits inside git worktree paths.
  - All 3 files remain untouched and excluded from Story 31.7 Report §3.2 Layer 2 batches.
- **Concrete Remediation:**
  - Enter `async with app.router.lifespan_context(app):` (or seed Day-0 system packs cleanly in test setup) in `test_story_16_3` and `test_story_30_3`, switch `test_story_3_2f` socket directory to `tempfile.mkdtemp(prefix="orcia_3_2f_")`, and re-execute all 3 PG18 suites cleanly (`--no-cov`).

---

## 4. Non-Blocking Observations (`P2`)

- **`P2-1` — Permissive Fallback in Standalone Workflow/VSM Delete Authorizer (`apps/api/src/orcia_api/routers/_entity_delete_rbac.py:149-150`):**
  When a standalone `WORKFLOW_V2` / `VSM_V2` row has no `owner_workspace_id`/`scope_type`/`scope_id` in `spec_jsonb` and no `workspace:`/`ws:` `pack_id`, `build_wf_vsm_target_authorizer` allows any `TEAM_LEAD` or `ARCHITECT` to delete it. Recommend failing closed to `PLATFORM_ADMIN` unless scope ownership is established.
- **`P2-2` — Conditional Target Auth Guard in Non-PG Mode (`apps/api/src/orcia_api/routers/agents_and_skills.py:206-207`, `_agents_and_skills_skills_routes.py:79-80`):**
  PG18 path (`_sql_agents_delete.py:95-96, 161-162`) enforces `authorize_target_cb(ws_id, vis)` unconditionally, whereas router pre-checks skip `target_auth(...)` when `existing.owner_workspace_id` is empty (`None`) in non-PG unit mode. Calling `target_auth(existing.owner_workspace_id or "", existing.visibility_scope)` unconditionally removes the asymmetry.
- **`P2-3` — E2E Execution Depth & Story 31.7 Report Evidence Precision:**
  - `docs/planning-artifacts/epics.md:4255` specifies `@pack:agent execution` and bilingual (`fr` & `en`) round-trip E2E; `apps/web/e2e/31-epic-31-declarative-apm-packs-roundtrip.spec.ts:204-218` verifies `@pack-qa` / `/pack-qa` autocomplete click without submitting an execution turn, and the `EN` test (`L266-297`) checks English Direction C labels + `ERR_PACK_SLOT_UNBOUND` drawer without running an EN compose/export/import cycle.
  - Story 31.7 Report §3.1 (`L75`) states `story-31-6-pack-ui-primitives.test.tsx` added regression tests for *both* `PackComposerModal` and `PackSlotBindingDrawer`, whereas `story-31-6-pack-ui-primitives.test.tsx:244-282` covers only `PackComposerModal`. Report §2.4 (`L55`) mentions `docs/help/{fr,en}/processes.md`, which was not modified in §3.1 (`L83`).
- **`P2-4` — Architecture Mermaid ERD Sync & Legacy Export Workspace Parameter:**
  - `architecture.md` updated Section 4 (`L399, 416-420`) and Section 5 (`L436`), while Section 8 Q1 Mermaid ERD (`L586-685`) does not yet render the 5 new Epic 31 tables.
  - `apps/web/src/features/settings/packs/usePacksRegistryHealthchecks.ts:148-150` routes `PackCardItem` ZIP download through legacy `exportWorkspacePackZip(selectedWorkspaceId || "platform", packId)` instead of `exportPackBundleZip(bundle_id)` (`"platform"` rejects non-admin users at `_packs_export_legacy_route.py:72`).

---

## 5. Closure Checklist Before Re-Running `VALIDATE`

1. Fix **`P0-1`** (`packs.py`, `_packs_router_helpers.py`, `import_service.py` scope check, and `test_story_31_7_packs_red_team_security.py` cross-tenant assertions).
2. Fix **`P1-1`** (`_sql_agents_pack_queries.py`, `sql_agents_and_skills.py`, `agents_and_skills.py` workspace/activation filtering + tests).
3. Fix **`P1-2`** (wire `PackSlotReadinessGuard` to `assistant_turns.py` + `mcp_and_test_bench.py`/`_mcp_assistant_ask_bridge.py` + tests).
4. Fix **`P1-3`** (`test_story_16_3`, `test_story_30_3`, `test_story_3_2f` fixtures and verify passing PG18+Redis runs).
5. Re-run `AD-17` impacted gates (`tests/unit`, `tests/security`, `tests/evals`, `tests/contract`, PG18+Redis+S3 integration including `16.3`/`30.3`/`3.2f`, `pnpm turbo`, `ruff`, `mypy --strict`, `lint-imports`, `export_openapi --check`, `check_implementation_docs.py`, `site:sync && site:check`, `gitnexus analyze`).

---

## 6. Round 2 Re-Verification & Closure Decision (`2026-11-27`)

Following remediation commit `552fd146` and Testing Verifier run `6c51e40e`, all **4 blocking findings** (`P0-1`, `P1-1`, `P1-2`, `P1-3`) and **`P2-3` / `P2-4`** items have been audited via direct file inspection and `gitnexus:check`.

### 6.1 Resolution Matrix

| Finding | Status | Directly Verified Remediation Evidence |
| :--- | :---: | :--- |
| **`P0-1`** | **RESOLVED** | Created `apps/api/src/orcia_api/routers/_packs_scope_guards.py` (`189 L`): `filter_visible_pack_rows` (`compute_caller_composer_scopes` + `GLOBAL`/`SYSTEM`/`PRIVATE_USER`/`WORKSPACE`/`BU`/`TEAM` visibility), `resolve_and_authorize_import_scope` (peeks archive `apm.yml` via `ApmPackCodec().decode_zip_bytes` when request scope is omitted, blocks `SYSTEM`/`GLOBAL` escalation with `403`, enforces `enforce_composer_scope_access(..., require_write=True)`), and `enforce_pack_bundle_delete_guard` (`enforce_pack_mutation_guard` + `get_bundle` `404` + `403 PackSystemDeleteForbiddenError` + `enforce_composer_scope_access`). Wired into `packs.py` (`285 L`); `_packs_router_helpers.py` (`277 L`) adds `persona_key` + `READ_ONLY_OBSERVER` checks; `_pack_composer_helpers.py` (`225 L`) rejects foreign `PRIVATE_USER` and empty `scope_id`. Covered by `tests/security/_packs_red_team_fixtures.py` (`202 L`), `tests/security/test_story_31_7_packs_red_team_security.py` (`161 L`), `tests/security/test_story_31_7_packs_isolation_and_guards.py` (`295 L`), and `tests/unit/packs/test_story_31_7_scope_and_pack_queries_cov.py` (`289 L`). |
| **`P1-1`** | **RESOLVED** | Updated `packages/orcia-core/src/orcia_core/orchestration/_internal/_sql_agents_pack_queries.py` (`299 L`), `sql_agents_and_skills.py` (`297 L`), and `_agents_namespacing.py` (`235 L`): `SQL_LOAD_AGENTS_AND_SKILLS_WITH_PACKS` selects `pack_bundle_id`, `scope_type`, `scope_id`; `load_workspace_scope_context_pg` resolves `(ws_uuid, ancestor_org_unit_ids)` via bounded CTE `WHERE anc.depth < 8`; `should_include_catalog_row` excludes foreign standalone `owner_workspace_id`, foreign-scope pack bundles, and unactivated non-`SYSTEM` custom packs when `workspace_id` is passed (and filters non-admin callers when `workspace_id` is `None`); `resolve_pack_tier_for_row(..., workspace_scoped=ws_scoped)` returns `None` for unactivated custom packs; `_agents_namespacing.py` passes `bundle_kind` to `infer_record_pack_slug_and_tier`. Wired into `agents_and_skills.py` (`298 L`) and `_agents_and_skills_helpers.py` (`287 L`) via `authorize_agents_skills_scope` and `filter_scoped_catalog_records`, verified by `test_p1_1_agents_skills_block_unactivated_custom_and_foreign_workspace_leak`. |
| **`P1-2`** | **RESOLVED** | Created `apps/api/src/orcia_api/routers/_pack_readiness_preflight.py` (`88 L`) with `enforce_pack_slot_readiness_preflight` extracting `@pack/agent`, `/pack/skill`, `pack:slug`, and catalog-resolved bare handles and invoking `packs_svc.enforce_run_start_readiness(workspace_id=workspace_id, workflow_pack_id=pslug_or_None, instance=inst)`. Wired into `assistant_turns.py:92-94` (`POST /api/v1/assistant/turns`) and `_mcp_assistant_ask_bridge.py:76-78, 163-168` (`assistant.ask` and `agent.*` MCP invocations), verified against `llm_called is False` by `test_p1_2_slot_readiness_guard_blocks_assistant_and_mcp_before_llm_spend`. |
| **`P1-3`** | **RESOLVED** | Fixed PG18 socket path in `tests/integration/test_story_3_2f_real_api_run_and_restart_postgres18.py:45-48` (`229 L`) using `tempfile.mkdtemp(prefix=f"orcia_3_2f_{name}_")`; added `connector_schemes` upsert (`ON CONFLICT (scheme) DO NOTHING`) in `infra/scripts/maintenance/03_backfill_permission_broker.py:109-155` (`295 L`); wrapped `create_app()` in `app.router.lifespan_context(app)` + Day-0 slot bindings (`activate_system_packs_with_slots_in_ws`) in `test_story_16_3_dual_mode_processes_api.py:130-136, 261-268` (`300 L`) and `test_story_30_3_pending_runs_and_live_guard_postgres18.py` (`260 L`) + `_story_30_3_fixtures.py` (`256 L`). Fixed 2 production PG18 bugs uncovered during execution: `sql_workflow_v2_runs.py:131-132` (`180 L`) restores authoritative `workspace_id::text` on cold `get_run` rehydration, and `_sql_workflow_v2_pending_query.py:131-136` (`233 L`) deduplicates `workflow_runs` already materialized in `workflow_v2_runs`. |
| **`P2-3` / `P2-4`** | **LARGELY RESOLVED** | `story-31-6-pack-ui-primitives.test.tsx:284-296` (`297 L`) adds `PackSlotBindingDrawer` rerender preservation coverage; `epic31PackHelpers.ts` (`74 L`) + `31-epic-31-declarative-apm-packs-roundtrip.spec.ts:148-157` (`238 L`) executes a real `POST /api/v1/assistant/turns` submission & streamed response assertion; `architecture.md:600-605, 691-738` renders all 5 Epic 31 tables and relationships in the Section 8 Q1 Mermaid ERD. |

### 6.2 Architecture, Hygiene & Registry Gates (Round 2)

1. **GitNexus Circular Import Check (Directly Verified)**: `gitnexus:check({cycles: true})` returned `status: "clean"`, `cycleCount: 0`, `cycles: []`.
2. **File Size Discipline (`<= 300 L`, Directly Verified)**: Every remediated production file (`88 L`–`299 L`) and test file (`74 L`–`300 L`) complies with the `<= 300 L` modular threshold.
3. **Governance & Registry Alignment (Directly Verified)**:
   - `docs/implementation-artifacts/sprint-status.yaml:352-359, 1623-1653`: `epic-31: done`, `31-1` through `31-7: done`, `ACTION_ITEM-31.1` (`P2`) and `ACTION_ITEM-31.2` (`P3`) tracked cleanly as `open`.
   - `docs/product/capabilities.yaml`: `CAP-055`, `CAP-056`, and `CAP-260` registered `status: live`, `verification: runtime`, `verified_at: "2026-11-26"` with Story 31.7 test & surface traceability.
   - `docs/implementation-artifacts/tech-lead-reports/31-7-epic-31-red-team-security-roundtrip-e2e-help-sync-and-closure-tech-lead-report.md` (`153 L`): updated with remediation scope, files, and §3.2 evidence.
4. **Testing Verifier Execution Evidence (Cited from Run `6c51e40e` / Report §3.2; not locally runnable from architect toolset)**:
   - `1,295/1,295` unit tests (`97%` scoped branch coverage), `199/199` evals/security/contract tests, `17/17` PG18+Redis+S3 integration tests (including `test_story_3_2f`, `test_story_16_3`, `test_story_30_3`), `9/9` Turbo tasks (`557` JS/TS tests), `8/8` Desktop Playwright E2E scenarios, and `254/254` synchronized Tech Lead reports.

### 6.3 Remaining Non-Blocking Observations (`P2` / `P3`)

- **`P2-1` / `P2-2`** from Section 4 remain open as non-blocking hardening enhancements (`_entity_delete_rbac.py:149-150`, `agents_and_skills.py:206-207`, `_agents_and_skills_skills_routes.py:79-80`).
- **Residual `P2-3` / `P2-4` notes**: `31-epic-31-declarative-apm-packs-roundtrip.spec.ts` covers English Direction C labels and `422` drawer while running full compose/export/import round-trip in the FR flow; `usePacksRegistryHealthchecks.ts:148-150` legacy export workspace fallback (`selectedWorkspaceId || "platform"`) and minor illustrative Mermaid ERD column naming (`mechanism_slug` vs `mechanism_key` in `architecture.md`) plus minor section label ordering in `31-7-...-tech-lead-report.md` are purely non-blocking P2/P3 hygiene notes.

**`Verdict: APPROVED`**
