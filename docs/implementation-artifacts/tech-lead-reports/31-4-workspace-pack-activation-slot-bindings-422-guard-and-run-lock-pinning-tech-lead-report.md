# Story 31.4 — Workspace Pack Activation, Slot Bindings, 422 Unbound Guard & Run Lock Pinning

- **Date**: 2026-11-26
- **Story / Sprint Key**: `31-4-workspace-pack-activation-slot-bindings-422-guard-and-run-lock-pinning` (`Epic 31` — Lot 3)
- **Capability(ies)**: `CAP-055`, `CAP-056`, `CAP-082`, `CAP-140`, `CAP-160` — classification: `feature`
- **Author / Context**: `bmad-dev-worker` (Coding Worker) — Workspace-scoped runtime pack activation (`workspace_pack_activations`), explicit human-confirmed connector slot bindings (`workspace_pack_slot_bindings`), fail-closed `HTTP 422 ERR_PACK_SLOT_UNBOUND` guard on activation and workflow-v2 run start (`D2`, `D5`, `R4`, `R5`, `A1`), immutable `run_lock_manifests` pinning (`A2`, `R5`), and active-run bundle deletion protection (`409 ERR_RESOURCE_PINNED_BY_ACTIVE_RUNS`).
- **Associated Commits**: Pending (Coding implementation in progress)

---

## 1. Needs Analysis & Tech Lead Impact Study (Pre-Implementation)

### 1.1 Context & Problem Statement
- **Current state**:
  - Stories `31.1`–`31.3` introduced the v2 PostgreSQL 18 DDL (`declarative_pack_bundles`, `workspace_pack_activations`, `workspace_pack_slot_bindings`, `pack_dna_mechanisms`, `pack_draft_memberships`), `PackImportService` + SeaweedFS CAS, and qualified `@pack:entity` namespacing + flat `WORKSPACE_PACK` ontology/DNA/policy resolution.
  - However, **no REST endpoints or domain services yet exist** to list workspace-visible packs, activate/deactivate packs per workspace, atomically reorder active priorities via the `DEFERRABLE` unique constraint (`uq_workspace_pack_priority`), or explicitly bind declared logical connector slots (`workspace_pack_slot_bindings`) with `audit_ledger` tracing (`PACK_SLOTS_BOUND`).
  - Furthermore, `POST /api/v1/workflows/v2/{workflow_id}/runs` (`_workflows_pending_runs.py`) and `POST /api/v1/orchestration/runs/instantiate` (`orchestration.py`) do not yet evaluate `workspace_pack_activations` / `workspace_pack_slot_bindings` before launching runs, nor do workflow-v2 runs persist immutable `(pack_bundle_id, pack_slug, version, archive_sha256, priority_order, resolved_pack_slots)` snapshots in `run_lock_manifests`.
- **Expected behavior**:
  1. Single-truth `WORKSPACE`-only activation (`workspace_pack_activations`), enforcing `chk_workspace_pack_activation_active_priority` (`(is_active AND priority_order IS NOT NULL) OR (NOT is_active AND priority_order IS NULL)`), cross-workspace scope isolation (`trg_workspace_pack_activations_scope_guard` + pre-check -> `HTTP 403`), and atomic `DEFERRABLE` priority reordering.
  2. Explicit slot binding (`PUT /api/v1/workspaces/{workspace_id}/packs/{slug}/slots`) validating declared slots and concrete `workspace_datasources` (same workspace) / `enterprise_connectors` (enabled) / `INTERNAL`, emitting `audit_ledger` `PACK_SLOTS_BOUND`, and preserving optional (`required: false`) unbound slots.
  3. Fail-closed `HTTP 422 ERR_PACK_SLOT_UNBOUND` (listing `missing_slots`) on pack activation AND workflow run start whenever any required slot is `UNBOUND`, disabled, or cleared by `ON DELETE SET NULL` after datasource/connector deletion.
  4. Immutable `run_lock_manifests` pinning at run start (`pinned_packs`, `resolved_pack_slots`, `manifest_sha256`), untouched by subsequent pack deactivation, priority reorder, or slot rebinding, and enforced by `409 ERR_RESOURCE_PINNED_BY_ACTIVE_RUNS` on `DELETE /api/v1/packs/{bundle_id}`.
- **Architectural constraints (`ARCHITECTURE-SPINE.md`, `AD-19`, `test_core_domain_isolation.py`)**:
  - Strict `AD-19` layering (`orcia_kernel` <- `orcia_core` lower domains <- `packs` / `orchestration` <- `orcia_api`): `packs` must NOT import `orchestration`, `bootstrap`, or `agents` (same layer in `pyproject.toml`).
  - Zero forbidden isolation tokens (`\b(jira|confluence|git_branch|wsjf|rovo|copilot|safe|prd)\b`) anywhere inside `packages/orcia-core/src/`.
  - Every modified/created `.py` file strictly `<= 300` lines (`wc -l`).

### 1.2 Exploration, GitNexus Impact Analysis, Refactoring & Technical Debt
- **GitNexus Impact Analysis (`repo: "/home/romain/.gemini/antigravity/worktrees/ORCIA/consignes_personnelles_save_button"`)**:
  - `gitnexus_impact({target: "PackImportService", direction: "upstream"})`: `impactedCount: 126`, `risk: CRITICAL`, `direct: 107`, `processes_affected: 6` (`Resolve_effective_workflow`, `Replay_workflow_from_step`, `Import_bmad_skill_pack`, `Promote_catalog_item`, `get_effective_workspace_ontology`, `Resolve_contextual_help`).
  - `gitnexus_query("workspace pack activation slot binding run lock manifest")`: surfaced `active_pack_priorities` (`_ontology_resolve_guards.py`), `sql_pack_ontology_resolution.py`, `_sql_agents_pack_queries.py`, `_sql_pack_lifecycle.py`, and `_sql_pack_delete_tx.py`.
- **Exploration & Key Schema Invariants**:
  - `20261126_311_declarative_packs_v2.py`:
    - `workspace_pack_activations`: `UNIQUE (workspace_id, pack_slug)`, `chk_workspace_pack_activation_active_priority` XOR constraint, `uq_workspace_pack_priority UNIQUE (workspace_id, priority_order) DEFERRABLE INITIALLY DEFERRED`, and `trg_workspace_pack_activations_scope_guard`.
    - `workspace_pack_slot_bindings`: `UNIQUE (workspace_id, pack_slug, slot_key)`, `bound_datasource_id ... ON DELETE SET NULL`, `bound_connector_id ... ON DELETE SET NULL`, `connector_scheme ... REFERENCES connector_schemes(scheme)`.
  - `0010_story_3_1_workflow_runs_triggers_and_run_lock.py`: `run_lock_manifests.run_id` references `workflow_runs(id) ON DELETE CASCADE`, and `_sql_pack_delete_tx.py` checks `run_lock_manifests JOIN workflow_runs WHERE wr.status NOT IN ('COMPLETED', 'FAILED', 'CANCELLED')`. Persisting `workflow_runs` + `run_lock_manifests` alongside `workflow_v2_runs` unifies run locking and active-run delete protection across v2 and orchestration runs without requiring any new Alembic migration.
- **Refactoring Opportunities & File Line-Count Control**:
  - Split workspace pack SQL queries (`_sql_workspace_pack_queries.py`), mutations (`_sql_workspace_pack_mutations.py`), and run-lock pinning (`_sql_run_lock_pinning.py`) cleanly under `packages/orcia-core/src/orcia_core/packs/_internal/`, plus pure domain evaluator `slot_guard.py` and facade `workspace_packs_service.py` (all `<= 300` L).
  - Split HTTP schemas into `apps/api/src/orcia_api/schemas/_workspace_packs.py` (re-exported by `schemas/packs.py`), and mount a dedicated `apps/api/src/orcia_api/routers/workspace_packs.py` + `_workspace_packs_guards.py`.

---

## 2. Implementation Plan

### 2.1 Data Schema & Alembic Migrations
- No new Alembic revision needed: `20261126_311_declarative_packs_v2.py` already provides `workspace_pack_activations`, `workspace_pack_slot_bindings`, `trg_workspace_pack_activations_scope_guard`, and `uq_workspace_pack_priority DEFERRABLE INITIALLY DEFERRED`, and `0010_story_3_1` provides `workflow_runs` + `run_lock_manifests`.

### 2.2 Hexagonal Core, Orchestration & Workers (`packages/orcia-core/`)
- `packages/orcia-core/src/orcia_core/packs/slot_guard.py`: pure domain models (`ResolvedPackSlotEntry`, `PinnedPackManifestEntry`, `WorkspacePackView`, `SlotBindingInput`) and deterministic evaluator `evaluate_pack_slot_readiness(...)` (detecting unbound required slots, cleared `ON DELETE SET NULL` FKs, disabled connectors, and `optional_unbound` slots).
- `packages/orcia-core/src/orcia_core/packs/errors.py` & `_error_catalog.py`: extend `PackSlotUnboundError` with `missing_slots` / `pack_slug` / `ERR_PACK_SLOT_UNBOUND_DETAIL` (FR/EN), plus `PackActivationInvalidError` & `PackSlotBindingInvalidError`.
- `packages/orcia-core/src/orcia_core/packs/_internal/_sql_workspace_pack_queries.py`: list visible packs + activation + slot bindings + readiness, resolve bundle with org-hierarchy/workspace visibility guard, and load active pack snapshot for run start.
- `packages/orcia-core/src/orcia_core/packs/_internal/_sql_workspace_pack_mutations.py`: transactional `upsert_pack_slot_bindings_sql` (validating slot keys, workspace datasource ownership, enabled connectors, `audit_ledger` `PACK_SLOTS_BOUND`), `activate_workspace_pack_sql`, `deactivate_workspace_pack_sql` (`is_active=FALSE, priority_order=NULL`), and `reorder_workspace_packs_sql` (`SET CONSTRAINTS uq_workspace_pack_priority DEFERRED`).
- `packages/orcia-core/src/orcia_core/packs/_internal/_sql_run_lock_pinning.py`: persist `workflow_runs` + `run_lock_manifests` (`pinned_packs`, `resolved_pack_slots`, `manifest_sha256`), read immutable `run_lock_manifests` by `run_id`, and sync terminal status on completion/failure.
- `packages/orcia-core/src/orcia_core/packs/workspace_packs_service.py`: Composition-Root service (`WorkspacePacksService`) exposing list, activate, deactivate, reorder, bind slots, pre-run guard & pinning, and run-lock read.
- `packages/orcia-core/src/orcia_core/packs/_internal/_sql_pack_delete_tx.py`: align terminal statuses (`ROLLED_BACK`) and verify `409 ERR_RESOURCE_PINNED_BY_ACTIVE_RUNS` against `run_lock_manifests`.
- `packages/orcia-core/src/orcia_core/orchestration/models.py` & `_run_lock_helpers.py`: add optional `pinned_packs` / `resolved_pack_slots` fields on `RecursiveRunLockManifest` while preserving 100% deterministic hash backward compatibility when empty.

### 2.3 Backend API, Security & Contracts (`apps/api/`, `packages/api-client/`)
- `apps/api/src/orcia_api/schemas/_workspace_packs.py` & `schemas/packs.py`: Pydantic v2 OpenAPI 3.1 transport schemas for workspace pack listing, activation, deactivation, atomic reorder, slot binding, and run-lock read.
- `apps/api/src/orcia_api/dependencies/pack_import_deps.py` & `_lifespan_services.py`: add `get_workspace_packs_service(request)` wired to `app.state.db_engine` in Composition Root.
- `apps/api/src/orcia_api/routers/_workspace_packs_guards.py` & `workspace_packs.py`: mount `/api/v1/workspaces/{workspace_id}/packs` endpoints (`GET ""`, `PUT "/reorder"`, `POST "/{slug}/activate"`, `DELETE "/{slug}/deactivate"`, `PUT "/{slug}/slots"`) with strict `ScopeAccessGuard` (`403 ERR_OBSERVER_MODE_READ_ONLY`, `403 ERR_SCOPE_ACCESS_DENIED`).
- `apps/api/src/orcia_api/routers/_workflows_pending_runs.py` & `workflows.py` & `orchestration.py`: enforce fail-closed `422 ERR_PACK_SLOT_UNBOUND` before run creation, snapshot active packs into `run_lock_manifests`, sync status on HITL completion, and expose `GET /api/v1/runs/{run_id}/lock`.
- Regenerate OpenAPI 3.1 + `@orcia/api-client` TS SDK (`scripts/export_openapi.py`, `0-diff`).

### 2.4 User Interface & Experience (`apps/web/`, `packages/ui/`)
- Out of scope for Story 31.4 (owned by Story 31.6); only `@orcia/api-client` OpenAPI SDK regeneration is performed here.

### 2.5 Test Pyramid Impact Analysis (`AD-17`)
- **Layer 1a (`tests/unit/packs/`)**: unit tests for `slot_guard.py`, `WorkspacePacksService`, domain errors & FR/EN catalog, `workspace_packs.py` router guards/responses, workflow-v2 run start fail-closed guard, and `test_core_domain_isolation.py`.
- **Layer 2 (`tests/integration/test_story_31_4_workspace_pack_activation_slots_postgres18.py`)**: real `testcontainers` PG18 `create_app()` vertical test (`dependency_overrides == {}`) verifying slot binding + `audit_ledger` (`PACK_SLOTS_BOUND`), `422 ERR_PACK_SLOT_UNBOUND` on activation & run start (including `ON DELETE SET NULL`), optional slots `optional_unbound`, `DEFERRABLE` priority reorder, deactivation XOR check, immutable `run_lock_manifests` mid-run isolation, `409 ERR_RESOURCE_PINNED_BY_ACTIVE_RUNS` bundle delete protection, and `403 ERR_OBSERVER_MODE_READ_ONLY` / cross-workspace guards.
- **Layer 3 (`scripts/export_openapi.py --check`, `lint-imports`, `@orcia/api-client`)**: `0-diff` OpenAPI 3.1 SDK and `5/5` `import-linter` contracts.

---

## 3. Summary of Changes & Results (Post-Implementation)

- **Architect Review Verdict (`bmad-architect-worker`, `pro`)**: **`APPROVED`** (`AD-19` unidirectional boundaries preserved, zero cross-domain `_internal` leaks, all production and test `.py` files strictly `<= 300` lines, fail-closed `422 ERR_PACK_SLOT_UNBOUND`, atomic `DEFERRABLE` priority reorder, and immutable `run_lock_manifests` snapshot verified).

### 3.1 Created & Modified Files

| Area | File | Lines | Role |
| --- | --- | --- | --- |
| Domain / Core | `packages/orcia-core/src/orcia_core/packs/slot_guard.py` | 269 | Pure slot-readiness evaluator (`evaluate_pack_slot_readiness`), `ResolvedPackSlotEntry`, `PinnedPackManifestEntry`, `WorkspacePackView`, `SlotBindingInput` |
| Domain / Core | `packages/orcia-core/src/orcia_core/packs/workspace_packs_service.py` | 236 | Composition-Root facade (`WorkspacePacksService`) for listing, activation, deactivation, reorder, slot binding, pre-run guard & run-lock read |
| Domain / Core | `packages/orcia-core/src/orcia_core/packs/errors.py` & `_error_catalog.py` | 204 / 194 | Extended `PackSlotUnboundError` (`missing_slots`, `pack_slug`, FR/EN details), `PackActivationInvalidError`, `PackSlotBindingInvalidError` |
| Domain / Core | `packages/orcia-core/src/orcia_core/packs/_internal/_sql_workspace_pack_queries.py` | 294 | Visible pack listing, workspace/org-ancestor resolution, active pack snapshot loading |
| Domain / Core | `packages/orcia-core/src/orcia_core/packs/_internal/_sql_workspace_pack_views.py` | 270 | Hydrated `WorkspacePackView` & slot binding projection queries |
| Domain / Core | `packages/orcia-core/src/orcia_core/packs/_internal/_sql_workspace_pack_mutations.py` | 288 | Transactional activation/deactivation (`chk_workspace_pack_activation_active_priority` XOR) |
| Domain / Core | `packages/orcia-core/src/orcia_core/packs/_internal/_sql_workspace_pack_reorder.py` | 111 | Atomic priority reorder (`SET CONSTRAINTS uq_workspace_pack_priority DEFERRED`) |
| Domain / Core | `packages/orcia-core/src/orcia_core/packs/_internal/_sql_workspace_slot_bindings.py` | 293 | Explicit slot binding upsert + `audit_ledger` `PACK_SLOTS_BOUND` emission |
| Domain / Core | `packages/orcia-core/src/orcia_core/packs/_internal/_sql_run_lock_pinning.py` & `_sql_run_lock_reads.py` | 252 / 177 | Immutable `run_lock_manifests` persistence (`pinned_packs`, `resolved_pack_slots`, `manifest_sha256`), terminal status sync, read queries |
| Domain / Core | `packages/orcia-core/src/orcia_core/packs/_internal/_sql_pack_delete_tx.py` & `_sql_pack_lifecycle.py` | 146 / 209 | Active-run deletion protection (`409 ERR_RESOURCE_PINNED_BY_ACTIVE_RUNS`) & lifecycle alignment |
| Domain / Core | `packages/orcia-core/src/orcia_core/storage/run_lock_guard.py` | 135 | Run-lock manifest guard & immutable pinning primitives |
| Domain / Core | `packages/orcia-core/src/orcia_core/kernel/errors.py`, `_error_catalog.py`, `orchestration/errors.py`, `permissions/errors.py`, `bootstrap/_internal/sql_*.py` | <= 290 | Kernel/domain error alignment and datasource/connector cleanup guards |
| API / SDK | `apps/api/src/orcia_api/routers/workspace_packs.py` & `_workspace_packs_guards.py` | 238 / 147 | `/api/v1/workspaces/{workspace_id}/packs` REST routes + `ScopeAccessGuard` (`403 ERR_OBSERVER_MODE_READ_ONLY`, `403 ERR_SCOPE_ACCESS_DENIED`) |
| API / SDK | `apps/api/src/orcia_api/routers/_workflows_pack_lock_helpers.py` & `_workflows_run_state_helpers.py` | 146 / 89 | Pre-run fail-closed `422 ERR_PACK_SLOT_UNBOUND` guard, `run_lock_manifests` pinning & state sync |
| API / SDK | `apps/api/src/orcia_api/routers/_workflows_pending_runs.py`, `orchestration.py`, `_orchestration_v1_serializers.py`, `_workflows_helpers.py` | <= 269 | Workflow-v2 & orchestration run start pinning + `GET /api/v1/runs/{run_id}/lock` |
| API / SDK | `apps/api/src/orcia_api/schemas/_workspace_packs.py`, `schemas/packs.py`, `dependencies/*`, `errors/_registry_extra_classes.py`, `main.py` | <= 203 | OpenAPI 3.1 transport schemas, Composition Root DI (`get_workspace_packs_service`), error registry & router mounting |
| API / SDK | `packages/api-client/openapi.json`, `src/generated/packs.ts`, `src/generated/schema.ts` | — | Regenerated OpenAPI 3.1 contract & TypeScript SDK (`0-diff`) |
| Tests | `tests/unit/packs/_fake_sql_engine.py` + `tests/unit/packs/test_story_31_4_*.py` (9 files) | <= 297 | Comprehensive unit & router/SQL helper coverage |
| Tests | `tests/integration/_story_31_4_pack_fixture.py` + `test_story_31_4_workspace_pack_activation_slots_postgres18.py` + `test_story_31_4_hardening_guards_postgres18.py` | <= 300 | Real PG18 `create_app()` vertical E2E API/SQL tests (`dependency_overrides == {}`) |

### 3.2 Quantitative Metrics & Scoped Branch Coverage (`>= 90%`)

- **Line-count guard (`wc -l <= 300`)**: `29/29` new `.py` files `<= 300` lines (`6,373` lines total; max `300` L); all modified production `.py` files `<= 290` lines.
- **Static & Security Gates**:
  - `.venv/bin/ruff check .`: `All checks passed!`
  - `.venv/bin/ruff format --check .`: `1864 files already formatted`
  - `.venv/bin/mypy --strict packages/orcia-core packages/orcia-connectors apps/api apps/worker`: `Success: no issues found in 917 source files`
  - `.venv/bin/lint-imports`: `Analyzed 907 files, 6581 dependencies. Contracts: 5 kept, 0 broken.`
  - `lint_spine.py`: `{"ok": true, "total_findings": 0}`
  - `scripts/export_openapi.py --check`: exit `0` (`0-diff`)
  - `.venv/bin/detect-secrets-hook --baseline .secrets.baseline`: exit `0`
- **Scoped `--branch` Coverage (`114 passed` in `tests/unit/packs/` + `tests/unit/core/test_core_domain_isolation.py`)**:

| Module | Stmts | Miss | Branch | BrPart | Cover |
| --- | --- | --- | --- | --- | --- |
| `apps/api/src/orcia_api/routers/_workflows_pack_lock_helpers.py` | 59 | 4 | 22 | 2 | 90% |
| `apps/api/src/orcia_api/routers/_workflows_run_state_helpers.py` | 44 | 0 | 14 | 2 | 97% |
| `apps/api/src/orcia_api/routers/_workspace_packs_guards.py` | 51 | 2 | 16 | 2 | 94% |
| `apps/api/src/orcia_api/routers/workspace_packs.py` | 55 | 0 | 0 | 0 | 100% |
| `packages/orcia-core/src/orcia_core/packs/_internal/_sql_run_lock_pinning.py` | 52 | 3 | 14 | 1 | 94% |
| `packages/orcia-core/src/orcia_core/packs/_internal/_sql_run_lock_reads.py` | 73 | 1 | 28 | 1 | 98% |
| `packages/orcia-core/src/orcia_core/packs/_internal/_sql_workspace_pack_mutations.py` | 65 | 0 | 16 | 2 | 98% |
| `packages/orcia-core/src/orcia_core/packs/_internal/_sql_workspace_pack_queries.py` | 98 | 0 | 40 | 1 | 99% |
| `packages/orcia-core/src/orcia_core/packs/_internal/_sql_workspace_pack_reorder.py` | 37 | 0 | 8 | 0 | 100% |
| `packages/orcia-core/src/orcia_core/packs/_internal/_sql_workspace_pack_views.py` | 74 | 0 | 22 | 0 | 100% |
| `packages/orcia-core/src/orcia_core/packs/_internal/_sql_workspace_slot_bindings.py` | 102 | 1 | 34 | 1 | 99% |
| `packages/orcia-core/src/orcia_core/packs/slot_guard.py` | 129 | 0 | 32 | 1 | 99% |
| `packages/orcia-core/src/orcia_core/packs/workspace_packs_service.py` | 57 | 4 | 16 | 4 | 89% |
| `packages/orcia-core/src/orcia_core/storage/run_lock_guard.py` | 34 | 0 | 12 | 1 | 98% |
| **TOTAL** | **930** | **15** | **274** | **18** | **97%** |

### 3.3 `AD-17` 5-Layer Verification

- **Layer 1 (`tests/unit`)**: `114 passed` in `tests/unit/packs/` + `test_core_domain_isolation.py` (`97%` branch coverage); full `tests/unit` gate executed after `capabilities.yaml` & `site:sync` closeout.
- **Layer 2 (`testcontainers` PG18 + Redis + SeaweedFS S3, `--no-cov`)**:
  - Batch 1 (`test_story_31_4_workspace_pack_activation_slots_postgres18.py`, `test_story_31_4_hardening_guards_postgres18.py`, `test_story_31_3_qualified_namespacing_and_ontology_postgres18.py`, `test_story_31_2_pack_import_and_day0_postgres18_s3.py`, `test_declarative_packs_and_wizards_postgres18.py`, `test_story_31_1_declarative_packs_v2_postgres18.py`): **`6 passed` (`101.25s`)**.
  - Batch 2 (`test_story_17_4_connectors_passthrough_and_rag_referent_postgres18.py`, `test_story_18_1_workspace_sources_postgres18.py`, `test_story_29_1_autonomous_runs_and_finops_pg18.py`, `test_story_11_4_pack_builder_postgres18_s3.py`, `test_story_30_5_agent_governance_and_lifecycle_pg18.py`): **`5 passed` (`77.72s`)**.
  - *Follow-up fixture note (Story 31.7)*: Pre-existing fixture issues unrelated to Story 31.4 were observed by the initial verifier on `test_story_3_2f` (`AF_UNIX path too long` in worktree `.pytest_cache`) and `test_story_30_3` / `test_story_16_3` (`ASGITransport` without `lifespan` missing Day-0 `packs/` seeding since Story 31.2); tracked for cleanup in Story 31.7.
- **Layer 3 / 4 / 5 (`evals`, `security`, `contract`, `turbo`)**:
  - `tests/evals tests/security tests/contract`: **`193 passed` (`0` failures)**.
  - `pnpm turbo run lint typecheck test --concurrency=2`: **`9/9` tasks successful** (`@orcia/api-client` `3` files/`20` tests, `@orcia/ui`, `@orcia/web` `96` files/`370` tests).

### 3.4 GitNexus Index & Change Impact

- `npx gitnexus analyze --index-only .`: **`49,879 nodes | 196,291 edges | 831 clusters | 1,524 flows`** (`65.0s`).
- `gitnexus_detect_changes({scope: "all"})`: **`changed_count: 3, affected_count: 1523, changed_files: 29, risk_level: "critical"`** (driven by OpenAPI SDK `packages/api-client/src/generated/schema.ts` `components` & `paths` regeneration).
