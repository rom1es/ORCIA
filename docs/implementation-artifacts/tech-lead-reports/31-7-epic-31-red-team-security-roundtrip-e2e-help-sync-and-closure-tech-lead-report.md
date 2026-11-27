# Story 31.7 — Epic 31 Red-Team Security, Round-Trip E2E, Contextual Help Sync & Closure

- **Date**: 2026-11-26
- **Story / Sprint Key**: `31-7-epic-31-red-team-security-roundtrip-e2e-help-sync-and-closure` (`Epic 31`)
- **Capability(ies)**: `CAP-055`, `CAP-056`, `CAP-070`, `CAP-082`, `CAP-090`, `CAP-091`, `CAP-100`, `CAP-140`, `CAP-160`, `CAP-200`, `CAP-260` — classification: `feature` (`security` + `e2e` + `doc` closure)
- **Author / Context**: Coding & Security Closure Worker (`FR-1..FR-31`, `NFR-SEC-*`, `AD-1..AD-25`, `UX-DR1..16`, Grill Decisions `D1`..`D6`, `R1`..`R5`, `A1`..`A4`). Provide exhaustive fail-closed security red-team tests, bilingual (`fr` & `en`) Day-0 Desktop Playwright round-trip E2E, Zone 4 contextual help documentation updates, architecture ERD synchronization (`architecture.md`), and formal closure readiness.
- **Associated Commits**: pending (on `feat/epic-31-declarative-apm-packs-import-export`)

---

## 1. Needs Analysis & Tech Lead Impact Study (Pre-Implementation)

### 1.1 Context & Problem Statement
- Stories 31.1 through 31.6 delivered the full APM-Superset declarative pack platform: Starlark DNA & `.zip` codec (`31.1`), transactional PG18 + SeaweedFS CAS pack import and Day-0 `sdlc` / `orcia-docs` seeding (`31.2`), qualified `@pack/agent` & `/pack:skill` namespacing with workspace-priority resolution (`31.3`), workspace-scoped pack activation, slot binding, `422 ERR_PACK_SLOT_UNBOUND` guard, and `run_lock_manifests` pinning (`31.4`), Pack Composer CRUD, closure gate, PII/secret scrubber, scrubbed `.zip` export, and `409 ERR_ENTITY_REFERENCED_BY_PACK_DRAFT` anti-hostage unlink (`31.5`), and Direction C bilingual UI across Settings, Workspaces, Agents, and Assistant (`31.6`).
- Before closing Epic 31, Story 31.7 must prove end-to-end security isolation and user journeys under real runtime boundaries:
  1. **Security Red-Team (`tests/security/test_story_31_7_packs_red_team_security.py`)**: exercise real FastAPI Composition Root + RBAC personas (`karim`, `marc`, `claire`, cross-tenant actors, `READ_ONLY_OBSERVER`) against zip-slip path traversal / symlinks (`422`), executable hooks/scripts (`422 ERR_PACK_EXECUTABLE_HOOK_FORBIDDEN`), PII/secret/infra leaks on export (`422 ERR_PACK_PII_OR_INFRA_LEAK`), cross-workspace scope isolation (`403 ERR_SCOPE_ACCESS_DENIED`), and `READ_ONLY_OBSERVER` (`403 ERR_OBSERVER_MODE_READ_ONLY`) across all pack import, activate, deactivate, reorder, slot bind, composer CRUD/members/publish/export, and unlink delete endpoints.
  2. **Bilingual FR & EN Desktop Playwright E2E Round-Trip (`apps/web/e2e/31-epic-31-declarative-apm-packs-roundtrip.spec.ts`)**: run under `env -u ORCIA_E2E_SEED_FIXTURES` with `--project=desktop-cockpit` after `resetDay0()`, verifying Day-0 packs (`sdlc`, `orcia-docs`), full compose -> closure -> publish -> export `.zip` -> fresh-workspace import -> activate -> slot binding (`[role="alert"]` on missing required slot, then bind & save) -> `@pack/agent` / `/pack:skill` qualified autocomplete + `F5` cold PG18 persistence, anti-hostage `409` unlink confirmation, and bilingual `fr`/`en` labels.
  3. **Zone 4 Contextual Help & Architecture Alignment**: update `docs/help/{fr,en}/{settings,workspaces,agents}.md` with 4-section structure covering Declarative APM Packs, Workspace Activation & Slot Binding, Pack Composer & Anti-Hostage Unlink, and Scrubbed `.zip` Round-Trip; align `docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24/architecture.md` Section 4 & Section 8 Q1 Mermaid ERD with all Epic 31 tables (`declarative_pack_bundles`, `pack_dna_mechanisms`, `pack_draft_memberships`, `workspace_pack_activations`, `workspace_pack_slot_bindings`, `run_lock_manifests.manifest_jsonb.active_packs`); verify `ACTION_ITEM-31.1..31.2` remain cleanly tracked (`open`) in `sprint-status.yaml`.

### 1.3 Post-Validate Remediation Scope (`P0-1`, `P1-1`, `P1-2`, `P1-3`, `P2-3`, `P2-4`)
- Following `docs/implementation-artifacts/epic-31-validate-report-2026-11-26.md` (`Verdict: CHANGES_REQUESTED`), Story 31.7 remediation addresses all blocking findings and report precision cleanups:
  1. **`P0-1` — Auth & `ScopeAccessGuard` on `/api/v1/packs*`**: enforce `compute_caller_composer_scopes` + bundle visibility filtering on `GET /api/v1/packs` and `GET /api/v1/packs/health`; enforce `enforce_composer_scope_access(..., require_write=True)` on `POST /api/v1/packs/import` (resolving effective `(scope_type, scope_id)` from archive `apm.yml` when request fields are omitted) and on `DELETE /api/v1/packs/{bundle_id}` (loading target bundle first, rejecting `SYSTEM` with `403 ERR_PACK_SYSTEM_DELETE_FORBIDDEN` and cross-tenant/unauthorized callers with `403 ERR_SCOPE_ACCESS_DENIED`); expand `test_story_31_7_packs_red_team_security.py`.
  2. **`P1-1` — Agents & Skills Workspace/Activation Filtering**: enforce `ScopeAccessGuard` on `GET /api/v1/agents-and-skills` and `/resolve` when `workspace_id` is supplied; filter standalone (`pack_bundle_id IS NULL`) rows by `owner_workspace_id` and non-`SYSTEM` pack rows by both bundle visibility and explicit `workspace_pack_activations.is_active = TRUE` in `load_agents_and_skills_from_postgres18`, ensuring unactivated custom packs never appear as `WORKSPACE_PACK` or outrank `SYSTEM_PACK`.
  3. **`P1-2` — `PackSlotReadinessGuard` Preflight on Assistant & Governed MCP**: wire shared `enforce_pack_slot_readiness_preflight` (`422 ERR_PACK_SLOT_UNBOUND`) before LLM execution/token spend on `POST /api/v1/assistant/turns` and `POST /api/v1/mcp/spaces/{workspace_slug}/invoke`.
  4. **`P1-3` — Story 31.4-Deferred PG18 Integration Fixtures**: wrap `create_app()` in `async with app.router.lifespan_context(app):` in `test_story_16_3_dual_mode_processes_api.py` and `test_story_30_3_pending_runs_and_live_guard_postgres18.py`, and move `test_story_3_2f_real_api_run_and_restart_postgres18.py` PG18 socket path to `tempfile.mkdtemp(prefix="orcia_3_2f_")`.
  5. **`P2-3` / `P2-4` Cleanups**: add `PackSlotBindingDrawer` rerender preservation test in `story-31-6-pack-ui-primitives.test.tsx`, execute a prompt submission after `@` / `/` autocomplete in `31-epic-31-declarative-apm-packs-roundtrip.spec.ts`, add the 5 Epic 31 tables to `architecture.md` Section 8 Q1 Mermaid ERD, and align Section 3 accurately.

### 1.2 Exploration, GitNexus Impact Analysis, Refactoring & Technical Debt
- **GitNexus Impact Analysis (`gitnexus_query`, `gitnexus_context` scoped to worktree repo)**:
  - Queried `declarative_pack_bundles workspace_pack_activations pack_draft_memberships apm pack composer` and inspected `export_bundle_tx` context.
  - Verified existing API surfaces and security guards: `apps/api/src/orcia_api/routers/packs.py`, `pack_composer.py`, `_pack_composer_publish_routes.py`, `workspace_packs.py`, `_packs_router_helpers.py`, `_pack_composer_helpers.py`, `_workspace_packs_guards.py`, plus core guards `_apm_security_guards.py`, `_pack_export_scrubber.py`, and `pack_draft_guard.py`.
  - Verified existing UI `data-testid`s across `DeclarativePacksRegistrySection.tsx`, `WorkspacePacksTabSection.tsx`, `PackSlotBindingDrawer.tsx`, `PackComposerModal.tsx`, `PackImportModal.tsx`, and `EntityUnlinkConfirmDialog.tsx`.
- **Exploration & Key Metrics**:
  - `docs/help/{fr,en}/*.md` contains 19 French + 19 English help sheets; `tests/unit/test_contextual_help_route_resolution.py` enforces that every markdown file under `docs/help/{fr,en}/` parses cleanly with all 4 sections (`summary_what_for`, step-by-step, real example, common pitfalls) and zero forbidden placeholders (`Chef1`, `aqwZSX`).
  - `lint_spine.py` currently passes with `0` findings on `docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24`.
- **Refactoring Opportunities & Emerging Technical Debt Mitigation**:
  - Keep every new test/spec file strictly `<= 300` lines (`wc -l <= 300`) by splitting helper fixtures or using concise parameterized assertions.
  - Keep `ACTION_ITEM-31.1` (Outbound MCP HTTP/OpenAPI Connector Runtime) and `ACTION_ITEM-31.2` (Org/BU Default Pack Auto-Activation Templates) `open` in `docs/implementation-artifacts/sprint-status.yaml`.

---

## 2. Implementation Plan

### 2.1 Data Schema & Alembic Migrations
- No schema changes or new Alembic migrations required; Story 31.7 aligns `docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24/architecture.md` Section 4 with the delivered Epic 31 PostgreSQL 18 schema (`declarative_pack_bundles` v2, `pack_dna_mechanisms`, `pack_draft_memberships`, `workspace_pack_activations`, `workspace_pack_slot_bindings`, and `run_lock_manifests` pack lock pinning).

### 2.2 Hexagonal Core, Orchestration & Workers
- Zero changes to production `packages/orcia-core/` code (preserving zero forbidden domain keywords `\b(jira|confluence|git_branch|wsjf|rovo|copilot|safe|prd)\b` and `lint-imports` boundaries).
- Verify core guards via real FastAPI Composition Root + service layer calls in `tests/security/test_story_31_7_packs_red_team_security.py`.

### 2.3 Backend API, Security & Contracts
- Implement `tests/security/test_story_31_7_packs_red_team_security.py` (`<= 300` lines) covering:
  1. Zip-slip (`../evil`, `/abs/path`) and symlink `.zip` archive rejection (`HTTP 422`).
  2. Executable hook/script (`.sh`, `.py`, `hooks:` YAML key) rejection (`HTTP 422 ERR_PACK_EXECUTABLE_HOOK_FORBIDDEN`).
  3. PII/secret/internal infra leak detection on composer export (`HTTP 422 ERR_PACK_PII_OR_INFRA_LEAK`, constructed cleanly without `detect-secrets` false positives).
  4. Cross-workspace / unauthorized-org isolation (`HTTP 403 ERR_SCOPE_ACCESS_DENIED`) across workspace pack activation, slot binding, and composer draft read/write routes.
  5. `READ_ONLY_OBSERVER` (`HTTP 403 ERR_OBSERVER_MODE_READ_ONLY` via both header and `OBSERVER` JWT) across pack import, activate, deactivate, reorder, slot bind, composer CRUD/members/publish/export, and unlink delete routes.

### 2.4 User Interface, Experience & Zone 4 Contextual Help
- Implement `apps/web/e2e/31-epic-31-declarative-apm-packs-roundtrip.spec.ts` (`<= 300` lines) targeting `--project=desktop-cockpit` with `env -u ORCIA_E2E_SEED_FIXTURES`:
  - French (`fr`) full Day-0 round-trip: `resetDay0()` -> `createFirstAdminViaUi` -> verify seeded `sdlc` & `orcia-docs` packs -> create Team/Workspace A + Workspace B -> attach `git` datasource to Workspace B -> compose `CUSTOM` pack in `PackComposerModal` (referencing a workspace agent/workflow) -> publish (`auto_include_dependencies` if needed) -> export scrubbed `.zip` download -> switch to Workspace B -> import exported `.zip` -> activate pack -> verify `422 ERR_PACK_SLOT_UNBOUND` `[role="alert"]` when slot unbound on `sdlc` -> bind required slot in `PackSlotBindingDrawer` -> save & activate -> trigger `@` / `/` qualified autocomplete in `Mon Assistant` -> verify `F5` (`reloadColdFromPg`) persistence in PG18 -> verify `409` anti-hostage unlink dialog + confirmation (`?unlink_from_draft_packs=true`).
  - English (`en`) verification flow: switch UI locale to `en`, verify Direction C English pack registry/slot drawer/composer labels and `[role="alert"]` error rendering cleanly.
- Update `docs/help/{fr,en}/{agents,settings,workspaces}.md` symmetrically in French and English while respecting the 4-section parser contract (`test_contextual_help_route_resolution.py`).

### 2.6 Validate Remediation Plan (`P0-1`, `P1-1`, `P1-2`, `P1-3`, `P2-3`, `P2-4`)
- **`P0-1`**: Add `apps/api/src/orcia_api/routers/_packs_scope_guards.py` (`<= 150` L) with `filter_visible_pack_rows`, `resolve_import_target_scope`, and `enforce_pack_bundle_delete_guard`; wire into `packs.py` and `enforce_composer_scope_access` (`_pack_composer_helpers.py` `PRIVATE_USER` guard); expand `tests/security/test_story_31_7_packs_red_team_security.py`.
- **`P1-1`**: Update `SQL_LOAD_AGENTS_AND_SKILLS_WITH_PACKS`, `load_workspace_scope_context_pg`, and `resolve_pack_tier_for_row` (`_sql_agents_pack_queries.py`), filter standalone/pack rows in `sql_agents_and_skills.py`, guard inactive candidates in `_agents_namespacing.py`, and enforce `ScopeAccessGuard` in `agents_and_skills.py` when `workspace_id` is supplied.
- **`P1-2`**: Add `apps/api/src/orcia_api/routers/_pack_readiness_preflight.py` (`<= 120` L) calling `WorkspacePacksService.enforce_run_start_readiness` for active workspace packs and explicitly referenced `@pack/agent` / `/pack/skill` handles, wired into `assistant_turns.py` and `_mcp_assistant_ask_bridge.py`.
- **`P1-3`**: Fix lifespan context in `test_story_16_3_dual_mode_processes_api.py` and `test_story_30_3_pending_runs_and_live_guard_postgres18.py` (extracting fixtures to keep `<= 300` L), and `tempfile.mkdtemp(prefix="orcia_3_2f_")` in `test_story_3_2f_real_api_run_and_restart_postgres18.py`.
- **`P2-3` / `P2-4`**: Add `PackSlotBindingDrawer` rerender test in `story-31-6-pack-ui-primitives.test.tsx`, prompt submit check in `31-epic-31-declarative-apm-packs-roundtrip.spec.ts` (extracting setup helper if needed to stay `<= 300` L), and Epic 31 tables in `architecture.md` Section 8 Q1 Mermaid ERD.

### 2.5 Test Pyramid Impact Analysis (`AD-17` — Layers 1 to 5 + Security)
- **Layer 1a / 1b**: Contextual help markdown parsing tests (`tests/unit/test_contextual_help_route_resolution.py`) pass on updated `docs/help/{fr,en}/*.md`.
- **Layer 2 & Layer 3**: Real Composition Root + PG18 round-trip verified in Playwright; `lint_spine.py` passes with `0` findings after `architecture.md` alignment.
- **Security / Red-Team Layer**: `tests/security/test_story_31_7_packs_red_team_security.py` passes all red-team & RBAC assertions (`--no-cov`).
- **Layer 5 (Playwright E2E)**: `apps/web/e2e/31-epic-31-declarative-apm-packs-roundtrip.spec.ts` passes under `env -u ORCIA_E2E_SEED_FIXTURES --project=desktop-cockpit`; `docs/implementation-artifacts/e2e-campaign-epic-22/` stays untouched/restored.
- Full `AD-17` closure gates, `capabilities.yaml` update, Report Section 3, and `site:sync` will be completed by the Story 31.7 Testing Verifier.

---

## 3. Summary of Changes & Results (Post-Implementation)

### 3.1 Created and Modified Files

| File | Action | Lines | Role / Summary |
| :--- | :--- | :---: | :--- |
| `packages/orcia-core/src/orcia_core/packs/_internal/_pack_export_scrubber_mappers.py` | Modified | `266` | Normalized catalog skill slug resolution inside `build_scrubbed_catalog_specs`. |
| `packages/orcia-core/src/orcia_core/orchestration/_internal/_sql_agents_pack_queries.py` | Modified | `299` | Added bundle scope columns (`scope_type`, `scope_id`), `load_workspace_scope_context_pg`, `is_pack_bundle_visible_in_scope`, `should_include_catalog_row`, `unpack_scoped_catalog_row`, and `workspace_scoped` gating in `resolve_pack_tier_for_row` (`P1-1`). |
| `packages/orcia-core/src/orcia_core/orchestration/_internal/sql_agents_and_skills.py` | Modified | `297` | Enforced scope & explicit activation filtering in `load_agents_and_skills_from_postgres18` (`P1-1`). |
| `packages/orcia-core/src/orcia_core/orchestration/_agents_namespacing.py` | Modified | `235` | Passed `bundle_kind` on `SYSTEM_PACK` candidates and filtered inactive workspace candidates in `_resolve_entity_reference` (`P1-1`). |
| `packages/orcia-core/src/orcia_core/workflows/_internal/_sql_workflow_v2_pending_query.py` | Modified | `233` | Deduplicated `workflow_runs` rows already materialized in `workflow_v2_runs` (`P1-3` fix). |
| `packages/orcia-core/src/orcia_core/workflows/_internal/sql_workflow_v2_runs.py` | Modified | `180` | Restored authoritative `workspace_id::text` in `SqlWorkflowV2RunsStore.get_run` for cold rehydration (`P1-3` fix). |
| `apps/api/src/orcia_api/routers/_packs_scope_guards.py` | Created | `189` | Scope visibility filtering, zip `apm.yml` scope peeking (`resolve_and_authorize_import_scope`), bundle delete guard (`enforce_pack_bundle_delete_guard`), and catalog `ScopeAccessGuard` (`P0-1`, `P1-1`). |
| `apps/api/src/orcia_api/routers/_pack_readiness_preflight.py` | Created | `88` | Shared `enforce_pack_slot_readiness_preflight` calling `WorkspacePacksService.enforce_run_start_readiness` (`P1-2`). |
| `apps/api/src/orcia_api/routers/packs.py` | Modified | `285` | Enforced auth + `ScopeAccessGuard` on `GET /api/v1/packs`, `GET /api/v1/packs/health`, `POST /api/v1/packs/import`, and `DELETE /api/v1/packs/{bundle_id}` (`P0-1`). |
| `apps/api/src/orcia_api/routers/_packs_router_helpers.py` | Modified | `277` | Added `persona_key` + `READ_ONLY_OBSERVER` checks in `enforce_pack_mutation_guard` (`P0-1`). |
| `apps/api/src/orcia_api/routers/_pack_composer_helpers.py` | Modified | `225` | Guarded `PRIVATE_USER` and empty `scope_id` inside `enforce_composer_scope_access` (`P0-1`). |
| `apps/api/src/orcia_api/routers/agents_and_skills.py` | Modified | `298` | Wired `authorize_agents_skills_scope` and `filter_scoped_catalog_records` on `/api/v1/agents-and-skills` and `/resolve` (`P1-1`). |
| `apps/api/src/orcia_api/routers/_agents_and_skills_helpers.py` | Modified | `287` | Propagated `workspace_id` / catalog scoping helpers cleanly (`P1-1`). |
| `apps/api/src/orcia_api/routers/assistant_turns.py` | Modified | `299` | Wired `enforce_pack_slot_readiness_preflight` (`422 ERR_PACK_SLOT_UNBOUND`) before LLM execution (`P1-2`). |
| `apps/api/src/orcia_api/routers/_mcp_assistant_ask_bridge.py` | Modified | `210` | Wired `enforce_pack_slot_readiness_preflight` (`422 ERR_PACK_SLOT_UNBOUND`) on `/api/v1/mcp/spaces/{slug}/invoke` (`P1-2`). |
| `infra/scripts/maintenance/03_backfill_permission_broker.py` | Modified | `295` | Ensured `'harbor'` scheme seed exists in `connector_schemes` before inserting broker policies (`P1-3`). |
| `packages/api-client/openapi.json` | Modified | `—` | Regenerated `0-diff` OpenAPI specification (`export_openapi.py --check`). |
| `packages/ui/src/primitives/PackComposerModal.tsx` | Modified | `293` | Preserved user input across `scopeOptions` re-renders (`open` / `draft?.bundleId` init guard). |
| `packages/ui/src/primitives/PackSlotBindingDrawer.tsx` | Modified | `285` | Preserved selected bindings across parent `pack` refresh via `initKeyRef`. |
| `packages/ui/src/__tests__/story-31-6-pack-ui-primitives.test.tsx` | Modified | `297` | Added `PackComposerModal` and `PackSlotBindingDrawer` rerender preservation tests (`P2-3`). |
| `apps/web/src/features/settings/packs/{packMappers.ts,useWorkspacePacksController.ts,DeclarativePacksRegistrySection.tsx}` | Modified | `188 / 224 / 291` | Unified workspace/fallback slot candidates and cold PG18 slot hydration. |
| `apps/web/src/features/workspaces/WorkspacePacksTabSection.tsx` | Modified | `75` | Wired merged `slotCandidates` into Workspace Packs drawer. |
| `apps/web/e2e/support/epic31PackHelpers.ts` | Created | `74` | Extracted Story 31.7 E2E workspace/datasource seeding helper (`<= 300` L compliance). |
| `apps/web/e2e/31-epic-31-declarative-apm-packs-roundtrip.spec.ts` | Created | `238` | Bilingual (`fr` & `en`) Day-0 Desktop Playwright E2E with `@pack/agent` autocomplete, assistant prompt submit, `F5` cold PG18 reload, `422 [role="alert"]`, and `409` unlink confirmation (`P2-4`). |
| `tests/security/_packs_red_team_fixtures.py` | Created | `202` | Shared FastAPI + `AsyncClient` + persona JWT helpers for Epic 31 red-team suites (`<= 300` L). |
| `tests/security/test_story_31_7_packs_red_team_security.py` | Created | `161` | Red-Team & RBAC suite covering `GET /api/v1/packs`, `/health`, `POST /api/v1/packs/import`, `DELETE /api/v1/packs/{bundle_id}`, zip-slip/executable hooks, PII leak export, and cross-workspace/observer `403`s (`P0-1`). |
| `tests/security/test_story_31_7_packs_isolation_and_guards.py` | Created | `295` | Security regressions for cross-workspace agents/skills leakage, unactivated custom pack blocking (`P1-1`), and `422 ERR_PACK_SLOT_UNBOUND` on `/assistant/turns` and `/mcp/spaces/{slug}/invoke` (`P1-2`). |
| `tests/unit/packs/{_fake_sql_engine.py,test_story_31_2_branch_coverage.py,test_story_31_2_packs_router.py,test_story_31_7_scope_and_pack_queries_cov.py}` | Modified / Created | `111 / 278 / 87 / 289` | Updated router/unit test callers and fake SQL engine `.fetchone()` for `P0-1`, plus branch-coverage tests for `_packs_scope_guards`, `packs.py`, and `_sql_agents_pack_queries.py`. |
| `tests/integration/{test_story_3_2f_real_api_run_and_restart_postgres18.py,test_story_31_2_pack_import_and_day0_postgres18_s3.py,test_story_31_3_qualified_namespacing_and_ontology_postgres18.py}` | Modified | `229 / 283 / 262` | `mkdtemp` socket path fix (`3.2f`, `P1-3`) and authorized persona query/header wiring (`31.2`, `31.3`). |
| `tests/integration/api/{_story_30_3_fixtures.py,test_story_16_3_dual_mode_processes_api.py,test_story_30_3_pending_runs_and_live_guard_postgres18.py}` | Modified | `256 / 300 / 260` | Wrapped `create_app()` in `app.router.lifespan_context(app)` and aligned Day-0 reset checks with Day-0 system pack seeding (`P1-3`). |
| `docs/help/{fr,en}/{agents,settings,workspaces}.md` | Modified | `32–37` | Synchronized bilingual Zone 4 contextual help guides (`<= 4` sections). |
| `docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24/architecture.md` | Modified | `761` | Added the 5 Epic 31 tables + relationships to Section 8 Q1 Mermaid ERD (`P2-4`). |
| `docs/product/capabilities.yaml` | Modified | `—` | Registered `test_story_31_7_packs_red_team_security.py`, `test_story_31_7_packs_isolation_and_guards.py`, `test_story_31_7_scope_and_pack_queries_cov.py`, and `31-epic-31-declarative-apm-packs-roundtrip.spec.ts` across `CAP-055`, `CAP-056`, `CAP-070`, `CAP-082`, `CAP-090`, `CAP-091`, `CAP-100`, `CAP-140`, `CAP-160`, `CAP-200`, `CAP-260` (`verification: runtime`). |
| `docs/implementation-artifacts/sprint-status.yaml` | Modified | `—` | Marked `31-7-epic-31-red-team-security-roundtrip-e2e-help-sync-and-closure: done` and `epic-31: done`, keeping `ACTION_ITEM-31.1..31.2: open`. |

### 3.2 Independent Testing Verifier & Closure Verification Results (`AD-17`)

- **Line-Count Guard (`wc -l <= 300`)**: All created/modified `.py`, `.ts`, and `.tsx` source and test files are `<= 300` lines (`max: 300` in `test_story_16_3_dual_mode_processes_api.py`; `test_story_31_7_scope_and_pack_queries_cov.py` is `289` lines; all production `.py`/`.ts`/`.tsx` `<= 299`; generated `apps/web/src/generated/orciaSiteManifest.ts` is `2330` lines).
- **Static, Typing, Boundary, Spine, Secrets & OpenAPI Gates (Step 1)**:
  - `detect-secrets-hook --baseline .secrets.baseline` on all modified/untracked files: **exit `0`**.
  - `.venv/bin/ruff check .` & `.venv/bin/ruff format --check .`: **All checks passed** (`1925 files already formatted`).
  - `.venv/bin/mypy --strict packages/orcia-core packages/orcia-connectors apps/api apps/worker`: **Success: no issues found in `950` source files**.
  - `.venv/bin/lint-imports`: **`5` kept, `0` broken** (`907` files, `6,581` dependencies).
  - `lint_spine.py`: **`ok: true`**, `total_findings: 0`.
  - `scripts/export_openapi.py --check`: **`0-diff`** (exit `0`).
- **Scoped `--branch` Coverage & Security / Evals / Contract Layers (Step 2.1–2.2)**:
  - Scoped `--branch` coverage across `tests/unit/packs/`, `test_core_domain_isolation.py`, `test_agents_and_skills_router_and_service.py`, `test_story_31_7_packs_red_team_security.py`, and `test_story_31_7_packs_isolation_and_guards.py`: **`159 passed, 0 failed`**, **`97%`** total branch coverage (`448` stmts, `6` miss, `174` branches, `12` partial; `_pack_readiness_preflight.py` `100%`, `_packs_scope_guards.py` `99%`, `packs.py` `100%`, `_agents_namespacing.py` `93%`, `_sql_agents_pack_queries.py` `100%`, `_pack_export_scrubber_mappers.py` `93%`; `.coverage*` and `/tmp/.cov_*` removed immediately).
  - `pytest --no-cov -q tests/evals tests/security tests/contract`: **`199 passed, 0 failed`**.
- **Full Impacted PG18 + Redis + SeaweedFS S3 Integration (`--no-cov`, Step 2.3)**:
  - **Batch 1** (`test_story_31_1..31_5*`, `test_declarative_packs_and_wizards_postgres18.py`, `test_http_vertical_day0_and_agents_postgres18.py`, `test_story_30_5_agent_governance_and_lifecycle_pg18.py`): **`14 passed, 0 failed`**.
  - **Batch 2** (`test_story_3_2f_real_api_run_and_restart_postgres18.py`, `test_story_16_3_dual_mode_processes_api.py`, `test_story_30_3_pending_runs_and_live_guard_postgres18.py`): **`3 passed, 0 failed`**.
- **Full JS/TS Turbo & Bilingual Desktop Playwright E2E (Step 3)**:
  - `pnpm turbo run lint typecheck test --concurrency=2`: **`9/9` tasks successful (`0` cached)** — `@orcia/api-client` (`4` files / `23` tests), `@orcia/ui` (`41` files / `159` tests), `@orcia/web` (`98` files / `375` tests) = **`557` JS/TS tests passed (`0` failures)**.
  - `env -u ORCIA_E2E_SEED_FIXTURES pnpm --filter @orcia/web exec playwright test --project=desktop-cockpit e2e/31-epic-31-declarative-apm-packs-roundtrip.spec.ts e2e/18-catalog-packs-wizards-and-mcp-bench.spec.ts e2e/09-pack-builder-and-contextual-help.spec.ts`: **`8 passed (1.8m), 0 failed`** (`docs/implementation-artifacts/e2e-campaign-epic-22` and `apps/web/test-results/` restored/cleaned).
- **GitNexus & Living Showcase Closure Gates (Step 4)**:
  - `npx gitnexus analyze --index-only .`: **`51,715` nodes | `259,114` edges | `862` clusters | `1,534` flows**.
  - `gitnexus_detect_changes({scope: "all", repo: "<worktree>"})`: `changed_count: 12`, `affected_count: 1534`, `changed_files: 43`, `risk_level: "critical"` (expected cross-cutting security/auth/pack remediation across `packs.py`, `agents_and_skills.py`, `assistant_turns.py`, `_sql_agents_pack_queries.py`, and `orciaSiteManifest.ts`).
  - `pnpm site:sync && pnpm site:check`: **`254` reports, `29` routes, `134` UI primitives, `66/66` live capabilities (`0` without test), `63/63` E2E covered capabilities, `20/20` UJs**.
  - `.venv/bin/python scripts/check_implementation_docs.py`: **`254/254` Tech Lead reports compliant and indexed**.
  - Post-sync `.venv/bin/pytest --no-cov -q tests/unit`: **`1,295 passed, 0 failed` (`CLEAN_ZERO_COV`)**.

### 3.3 Validation (`AD-17` Scope Summary)

- **`P0-1` (`GET /packs`, `/health`, `POST /packs/import`, `DELETE /packs/{bundle_id}`)**: Verified fail-closed `ScopeAccessGuard` (`403 ERR_SCOPE_ACCESS_DENIED`, `403 ERR_OBSERVER_MODE_READ_ONLY`, `403 ERR_PACK_SCOPE_ESCALATION_FORBIDDEN`, `403 ERR_PACK_SYSTEM_DELETE_FORBIDDEN`) across security and PG18 integration tests.
- **`P1-1` (`GET /agents-and-skills`, `/resolve`, `load_agents_and_skills_from_postgres18`)**: Verified standalone workspace isolation and unactivated custom pack blocking so unactivated custom packs never outrank `SYSTEM_PACK` or leak across workspaces.
- **`P1-2` (`AssistantTurnEngine` & `GovernedMcpServerService`)**: Verified `422 ERR_PACK_SLOT_UNBOUND` preflight blocks execution prior to LLM spend on `/api/v1/assistant/turns` and `/api/v1/mcp/spaces/{slug}/invoke` when required pack slots are unbound.
- **`P1-3` (3 Deferred PG18 Fixtures + Real Bugs)**: Verified `test_story_3_2f`, `test_story_16_3`, and `test_story_30_3` pass under real `testcontainers` PG18 + Redis with `app.router.lifespan_context(app)` and `mkdtemp`, resolving real bugs in `sql_workflow_v2_runs.py` (cold `workspace_id` restore), `_sql_workflow_v2_pending_query.py` (`workflow_runs` deduplication), and `03_backfill_permission_broker.py` (`harbor` scheme seed).
