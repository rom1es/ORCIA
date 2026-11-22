# Story 26.8 — `CONTINUE_IN_PROCESS` Wired to Durable DBOS + PG18 & Human Anchors (`WAITING_FOR_HUMAN_ANCHOR`), Direct Deletion of `/workflows/save-and-launch`

- **Date**: 2026-11-22
- **Story / Sprint Key**: `26-8-continue-in-process-dbos-pg18-and-human-anchors` (`Epic 26` / `Lot 6`)
- **Capabilities**: `CAP-022`, `CAP-073`, `CAP-160`, `CAP-260` (classification: `feature`)
- **Author / Context**: Continuation from `Mon Assistant` proposals (`POST /api/v1/assistant/turns/{turn_id}/approve`) and thematic folders (`POST /api/v1/assistant/folders/{folder_id}/launch-process`) into durable DBOS + PostgreSQL 18 orchestration (`AD-2`, `AD-3`, `AD-19`, `AD-20`, `AD-25`, `D6`, `R4`, `H-05`), plus direct deletion of legacy `POST /api/v1/assistant/workflows/save-and-launch`.

---

## 1. Need Analysis & Tech Lead Impact Study (Analyse du Besoin)

### 1.1 Context & Problem Statement
- **Observed gap (`H-05`, `D6`, `R4`)**:
  - `POST /api/v1/assistant/workflows/save-and-launch` (`apps/api/src/orcia_api/routers/assistant.py` -> `AssistantAgentService.save_and_launch_workflow_async` -> `_assistant_workflow_launch.py`) bypassed `AD-2` (durable DBOS + PG18 persistence) and `AD-3` (executing all steps with `commit_immediately=True` without initializing or enforcing `WAITING_FOR_HUMAN_ANCHOR` for `human_authored_required: true` steps).
  - `POST /api/v1/assistant/turns/{turn_id}/approve` (`_assistant_turn_controls_routes.py`) only wrote an `audit_ledger` entry (`record_turn_approval_audit`) without instantiating or launching a durable DBOS + PostgreSQL 18 workflow run when approving `CONTINUE_IN_PROCESS` proposals.
  - `POST /api/v1/assistant/folders/{folder_id}/launch-process` (`assistant_workspace_folders.py`) only assembled `prefilled_contract_inputs` without instantiating or launching a durable DBOS + PostgreSQL 18 workflow run.
  - `DbosDurableWorkflowEngine` (`_internal/dbos_engine.py`, `_internal/_dbos_workflow_defs.py`) did not yet initialize anchored steps in `WAITING_FOR_HUMAN_ANCHOR` or suspend execution at the first `WAITING_*` state prior to human signature, nor was `DbosDurableWorkflowEngine` launched/unbound inside FastAPI `app_lifespan`.
- **Expected behavior**:
  - Both `POST /api/v1/assistant/turns/{turn_id}/approve` (on `approved=True`) and `POST /api/v1/assistant/folders/{folder_id}/launch-process` wire cleanly into durable DBOS + PostgreSQL 18 orchestration (`workflow_runs`, `run_lock_manifests`, `step_executions`, `blackboard_snapshots`, `domain_events_outbox`).
  - Every step with `human_authored_required: true` initializes in `WAITING_FOR_HUMAN_ANCHOR`; execution halts at the first `WAITING_*` state (never auto-advancing downstream steps prior to human signature); unsigned step commits are rejected with `HTTP 422 ERR_HUMAN_ANCHOR_REQUIRED`; observer mutations are rejected with `HTTP 403 ERR_OBSERVER_MODE_READ_ONLY`; signed anchors (`>= 30` chars, `author_type="HUMAN"`) resume durable downstream execution cleanly.
  - Legacy `POST /api/v1/assistant/workflows/save-and-launch`, `_assistant_workflow_launch.py`, `save_and_launch_workflow*`, `AssistantSaveAndLaunch*` schemas, and SDK entries are deleted directly (`0-diff` OpenAPI, zero `deprecated` window).

### 1.2 Exploration, GitNexus Impact Analysis, Factorization & Technical Debt
- **GitNexus Impact Analysis (`repo: "/home/romain/Documents/Projects/ORCIA"`)**:
  - `save_and_launch_workflow_async` (`assistant_agent.py`): called only by `apps/api/src/orcia_api/routers/assistant.py`, `packages/api-client/src/domains/_epics4To7Operations.ts`, and legacy unit/security tests (`test_story_3_3_assistant_agent_5_nodes_and_context_ports.py`, `test_story_26_1_assistant_security_hardening.py`). Zero live UI callers.
  - `launch_process_from_folder_endpoint` (`assistant_workspace_folders.py`): exposed via OpenAPI; `apps/web/src/features/inbox/InboxAuxiliaryPanels.tsx` currently routes folder CTA only to `/processes` without invoking `POST /api/v1/assistant/folders/{folder_id}/launch-process`.
  - `DurableOrchestrationEngine` (`engine.py`): `MEDIUM` risk (`18` impacted modules across `orcia_core/orchestration/`). All new launch/pause/resume logic stays strictly modular (`<= 300` lines/file) and preserves existing `/api/v1/orchestration/*` contracts.
- **Database & Schema Findings**:
  - Existing PG18 tables `workflow_runs`, `run_lock_manifests`, `step_executions`, `blackboard_snapshots`, `human_anchor_signatures`, and `domain_events_outbox` already carry the required columns and CHECK constraints (`WAITING_FOR_HUMAN_ANCHOR` on `step_executions.status`; `WAITING_FOR_HUMAN_ARBITRATION` on `workflow_runs.status`; `StepCompleted`, `ArtifactProduced`, `HumanArbitrationRequested`, `RunTerminated` on `domain_events_outbox.event_type`). No new Alembic migration is required.
  - `DbosDurableWorkflowEngine.persist_step_and_commit_snapshot` previously hardcoded a static `workspace_id` and omitted `StepCompleted`/`ArtifactProduced` outbox events; fixing it to resolve the real `workflow_runs` metadata and emit transactional outbox events ensures full PG18 auditability.
- **Factorization & Volumetry Control**:
  - Extract shared durable assistant process launching into a dedicated pure hexagonal service `packages/orcia-core/src/orcia_core/orchestration/assistant_process_launcher.py` (`<= 280` L) and SQL/DBOS wiring helpers into `apps/api/src/orcia_api/routers/_assistant_process_wiring.py` (`<= 240` L) so `assistant_turns.py`, `_assistant_turn_controls_routes.py`, `assistant_workspace_folders.py`, and `orchestration_sql_wiring.py` remain `<= 300` lines.

---

## 2. Implementation Plan (Plan d'Implémentation)

### 2.1 Data Schema & Alembic Migrations
- Reuse existing immutable PG18 schema (`workflow_runs`, `run_lock_manifests`, `step_executions`, `blackboard_snapshots`, `human_anchor_signatures`, `domain_events_outbox`). Zero schema changes needed.

### 2.2 Hexagonal Core, Orchestration & Workers (`packages/orcia-core/`)
- Add pure hexagonal `DurableProcessLaunchPort` & `AssistantProcessLauncherService` (`packages/orcia-core/src/orcia_core/orchestration/assistant_process_launcher.py`) with zero framework/SDK imports and zero SDLC vocabulary (`AD-19`, `AD-20`).
- Enhance `_engine_step_helpers.initialize_run_steps_helper` and `WorkflowOrchestrationSetupService.instantiate_workflow_run` with opt-in `initialize_anchored_as_waiting: bool = False` so launched assistant processes initialize every `human_authored_required: true` step in `WAITING_FOR_HUMAN_ANCHOR` while preserving existing `/orchestration/runs/instantiate` behavior.
- Enhance `DbosDurableWorkflowEngine` (`_internal/dbos_engine.py` & `_internal/_dbos_workflow_defs.py`) to:
  - Support `anchored_step_keys` and halt durably at the first `WAITING_*` step via `DBOS.recv_async(topic=HUMAN_ANCHOR_TOPIC)`, updating `workflow_runs.status = "WAITING_FOR_HUMAN_ARBITRATION"` and enqueuing `HumanArbitrationRequested` into `domain_events_outbox`.
  - Verify `human_anchor_signatures` in PostgreSQL 18 on `DBOS.send_async` wake-up before executing the signed step and advancing downstream `@DBOS.step()` checkpoints (`blackboard_snapshots`, `StepCompleted`, `ArtifactProduced`, `RunTerminated`).
  - Resolve real `workspace_id` / `workflow_uri` / `execution_regime` from `workflow_runs` instead of hardcoded constants.
- Delete `packages/orcia-core/src/orcia_core/orchestration/_assistant_workflow_launch.py` and remove `save_and_launch_workflow*` / `SavedAndLaunchedWorkflowResult` from `assistant_agent.py`, `assistant_agent_models.py`, `assistant_composer.py`, and `__init__.py`.

### 2.3 Backend API, Security & Contracts (`apps/api/`, `packages/api-client/`)
- Delete `apps/api/src/orcia_api/routers/assistant.py`, remove `assistant_router` from `apps/api/src/orcia_api/main.py`, and remove `AssistantSaveAndLaunchRequest` / `AssistantSaveAndLaunchResponse` from `apps/api/src/orcia_api/schemas/assistant.py`.
- Wire `DbosDurableWorkflowEngine` lifecycle cleanly inside `_lifespan_infra.py` (`startup_declarative_packs_and_dbos` + `shutdown_app_resources`) when `db_engine` is active, enabling real DBOS durable workflows in `create_app()` without any `dependency_overrides`.
- Wire `POST /api/v1/assistant/turns/{turn_id}/approve` (`_assistant_turn_controls_routes.py`) and `POST /api/v1/assistant/folders/{folder_id}/launch-process` (`assistant_workspace_folders.py`) via `_assistant_process_wiring.py` to launch durable DBOS + PG18 processes, enforcing `ScopeAccessGuard` and `HTTP 403 ERR_OBSERVER_MODE_READ_ONLY`.
- Wire `POST /api/v1/orchestration/runs/anchors/sign` (`blackboard_and_engine.py`) to send `DBOS.send_async(..., topic=HUMAN_ANCHOR_TOPIC)` when resuming a paused `assistant-process:*` DBOS workflow, plus non-DBOS unit fallback resume.
- Extend `AssistantTurnApproveRequest` / `AssistantTurnApproveResponse` and `LaunchProcessFromFolderResponse` with typed optional durable run metadata (`run_id`, `run_status`, `workflow_uri`, `dbos_workflow_id`, `waiting_step_keys`, `executed_step_keys`, `snapshot_count`), preserving backward compatibility.
- Regenerate OpenAPI 3.1 & `@orcia/api-client` (`scripts/export_openapi.py`, removing `assistantSaveAndLaunchWorkflow` and adding `launchProcessFromFolder`).

### 2.4 User Interface & Experience (`apps/web/`, `docs/product/capabilities.yaml`)
- Wire `useServerAssistantFolders.launchProcess` -> `createOrciaApiClient().launchProcessFromFolder` inside `InboxAuxiliaryPanels.tsx` / `InboxFeaturePanel` (`index.tsx`) and update `assistantAndInboxMockHandlers.ts` for fail-closed Vitest compatibility, surfacing RFC 9457 errors without `.catch(() => undefined)`.
- Update `docs/product/capabilities.yaml` (`CAP-022`, `CAP-073`, `CAP-190`, `CAP-260`) to remove stale `assistant.py` / `/workflows/save-and-launch` references and record Story 26.8 tests (keeping `CAP-260` `verification: api` until Story 26.10).

### 2.5 Test Pyramid Impact (`AD-17`)
- **Layer 1a (Python Unit `tests/unit/test_story_26_8_continue_in_process_and_human_anchors.py`)**: Verify DBOS launch wiring, `WAITING_FOR_HUMAN_ANCHOR` initialization, halt on first `WAITING_*`, `422 ERR_HUMAN_ANCHOR_REQUIRED`, signed resume, `403 ERR_OBSERVER_MODE_READ_ONLY`, and `404`/`405` on `/workflows/save-and-launch`; update legacy tests referencing deleted `/workflows/save-and-launch`.
- **Layer 1b (TS Unit `Vitest`)**: Verify `launchProcessFromFolder` wiring in `@orcia/api-client` and `apps/web` fail-closed handlers.
- **Layer 2 (PG18 Integration `tests/integration/api/test_story_26_8_continue_in_process_dbos_postgres18.py`)**: Real `create_app()` Composition Root (`0` overrides) verifying `/turns/{id}/approve` and `/folders/{id}/launch-process`, SQL `SELECT` across `workflow_runs`, `step_executions` (`WAITING_FOR_HUMAN_ANCHOR`), `blackboard_snapshots`, `domain_events_outbox`, `422 ERR_HUMAN_ANCHOR_REQUIRED`, signed anchor resume across cold restart (`app1` -> `app2`), and `404`/`405` on `/workflows/save-and-launch`.
- **Layer 3 (Contracts & Architecture)**: `scripts/export_openapi.py --check` (`0-diff`), `lint-imports`, `pnpm site:sync && pnpm site:check`.

---

## 3. Change Summary & Verification Results (Bilan des Modifications)

### 3.1 Inventory of Modified, Added, and Deleted Files (`wc -l <= 300` Non-Barrel Compliance)
- **Hexagonal Core, DBOS Engine & Seeds (`packages/orcia-core/src/orcia_core/`)**:
  - **Created**:
    - `orchestration/assistant_process_launcher.py` (`283` L) — Pure hexagonal `DurableProcessBackendPort` and `AssistantProcessLauncherService` with zero framework/SDK imports and zero SDLC vocabulary (`AD-19`, `AD-20`).
    - `orchestration/dbos_engine_ports.py` (`17` L) — Public non-`_internal` runtime waiter registration surface (`register_run_state_waiter`, `clear_run_state_waiter`) preventing `._internal` imports in `apps/api/src/`.
    - `orchestration/_internal/_sql_dbos_launch_helpers.py` (`212` L) — Raw SQLAlchemy async helpers for `WAITING_FOR_HUMAN_ANCHOR` step enforcement, `human_anchor_signatures` checks, `workflow_runs` execution context lookup, and transactional `domain_events_outbox` persistence.
  - **Modified**:
    - `orchestration/_internal/_dbos_workflow_defs.py` (`261` L) — Durable `@DBOS.workflow()` `WAITING_FOR_HUMAN_ANCHOR` pause/resume via `DBOS.recv_async(topic=HUMAN_ANCHOR_TOPIC)` and `HumanArbitrationRequested` / `RunTerminated` outbox events; preserves deterministic `@DBOS.step` / `DBOS.recv_async` replay order on server restart (skipping pre-committed steps only when explicitly requested via immutable `skip_committed_steps` launch input, never altering replay order of `pause_for_arbitration_after_step`).
    - `orchestration/_internal/dbos_engine.py` (`298` L) — Real `workflow_runs` workspace/context resolution, `anchored_step_keys`, `step_types_by_key`, `emit_outbox_events`, and `send_human_anchor_signed`.
    - `orchestration/engine.py` (`298` L), `orchestration/_engine_step_helpers.py` (`277` L), `orchestration/seeds.py` (`120` L), `bootstrap/orchestration_seeds.py` (`232` L) — Opt-in `initialize_anchored_as_waiting`, baseline 3-workflow seed invariance, and on-demand `DEFAULT_FOLDER_PILOT_WORKFLOW_YAML` registration.
    - `orchestration/assistant_agent.py` (`194` L), `orchestration/assistant_agent_models.py` (`104` L), `orchestration/assistant_composer.py` (`217` L), `orchestration/__init__.py` (`520` L, reduced from `522` L baseline barrel) — Removed `save_and_launch_workflow*` / `SavedAndLaunchedWorkflowResult`.
  - **Deleted**: `orchestration/_assistant_workflow_launch.py`.
- **FastAPI Composition Root, Routers & Schemas (`apps/api/src/orcia_api/`)**:
  - **Created**:
    - `routers/_assistant_dbos_backend.py` (`209` L) — DBOS backend adapter, run wait-for-pause/completion bridge, and SQL run snapshot synchronization.
    - `routers/_assistant_process_wiring.py` (`131` L) — Shared Composition Root wiring for `/turns/{turn_id}/approve` and `/folders/{folder_id}/launch-process` using `dbos_engine_ports` (zero `._internal` imports).
  - **Modified**:
    - `dependencies/__init__.py` (`162` L), `dependencies/_lifespan_infra.py` (`240` L), `dependencies/orchestration_and_settings.py` (`222` L), `main.py` (`228` L) — DBOS lifecycle startup/shutdown inside `app_lifespan` and `get_assistant_process_launcher_service` DI; removed `assistant_router`.
    - `routers/_assistant_turn_controls_routes.py` (`207` L), `routers/assistant_workspace_folders.py` (`287` L), `routers/blackboard_and_engine.py` (`223` L), `routers/_orchestration_sql_hydration.py` (`165` L) — Wired `CONTINUE_IN_PROCESS` approve, folder launch, `DBOS.send_async` human-anchor resume, and lazy folder pilot workflow hydration.
    - `schemas/assistant.py` (`58` L), `schemas/assistant_citations_and_folders.py` (`185` L), `schemas/assistant_governance_and_three_speed.py` (`256` L) — Added typed durable run metadata; removed `AssistantSaveAndLaunchRequest` / `AssistantSaveAndLaunchResponse`.
  - **Deleted**: `routers/assistant.py` (direct deletion of `POST /api/v1/assistant/workflows/save-and-launch`).
- **OpenAPI SDK, Web SPA & Governance (`packages/api-client/`, `apps/web/`, `docs/`)**:
  - **Modified**: `packages/api-client/openapi.json`, `packages/api-client/src/generated/schema.ts`, `domains/_epics1To7Types.ts` (`78` L), `domains/_epics4To7Operations.ts` (`275` L), `domains/assistantStreaming.ts` (`246` L), `src/__tests__/client.test.ts` (`628` L).
  - **Created / Modified (`apps/web/`)**: `src/features/inbox/InboxAuxiliaryPanels.tsx` (`226` L), `src/features/inbox/index.tsx` (`255` L), `src/features/inbox/useServerAssistantFolders.ts` (`178` L), `src/__tests__/setup/assistantAndInboxMockHandlers.ts` (`258` L), `src/__tests__/setup/inboxAndBrokerMockHandlers.ts` (`172` L, split from mock setup).
  - **Documentation & Capabilities**: `docs/product/capabilities.yaml`, `docs/implementation-artifacts/sprint-status.yaml`, `docs/implementation-artifacts/tech-lead-reports/README.md`, `apps/web/src/generated/orciaSiteManifest.ts`, `docs/site-catalog/index.html`.
- **Tests Created & Updated (`tests/`)**:
  - **Created**:
    - `tests/unit/test_story_26_8_continue_in_process_and_human_anchors.py`
    - `tests/unit/test_story_26_8_dbos_lifecycle_coverage.py`
    - `tests/unit/test_story_26_8_dbos_wiring_and_hydration.py`
    - `tests/unit/test_story_26_8_hydration_fallbacks.py`
    - `tests/integration/api/test_story_26_8_continue_in_process_dbos_postgres18.py`
  - **Modified**: `tests/security/test_story_26_1_assistant_security_hardening.py`, `tests/unit/test_story_26_3_turn_reliability_and_async_loop.py`, `tests/unit/test_story_3_3_assistant_agent_5_nodes_and_context_ports.py`.

### 3.2 Verification Gates & Exact Post-Final-Edit Results (`AD-17`)
1. **Static Analysis, Hygiene & Contracts**:
   - Line-count check (`wc -l`): All newly created and refactored non-barrel production files are `<= 300` lines (max `298` L in `dbos_engine.py` and `engine.py`; `orchestration/__init__.py` reduced to `520` L).
   - `.venv/bin/ruff check .` & `.venv/bin/ruff format --check .`: **PASS** (`All checks passed`, `1545` files formatted).
   - `.venv/bin/mypy --strict packages/orcia-core packages/orcia-connectors apps/api apps/worker`: **PASS** (`Success: no issues found in 720 source files`).
   - `.venv/bin/lint-imports`: **PASS** (`Contracts: 5 kept, 0 broken` across `762` files / `5596` dependencies).
   - `lint_spine.py`: **PASS** (`ok: true`, `total_findings: 0`).
   - `.venv/bin/python scripts/export_openapi.py --check`: **PASS** (`0-diff`; `/api/v1/assistant/workflows/save-and-launch` absent from OpenAPI and routers).
   - `detect-secrets-hook`: **PASS** (`0` unbaselined secrets); `git diff --stat -- docs/implementation-artifacts/e2e-campaign-epic-*` empty.
2. **Python Non-Integration Suites & Branch Coverage (`--branch`, `--fail-under=90`)**:
   - `tests/unit` (non-PG18, non-standalone): **`995 passed`**.
   - Standalone timing-sensitive unit suites (`--no-cov`): `test_story_7_0c_openshift_scc_kustomize_and_ready.py` (**`5 passed`**), `test_epic_11_story_11_2_dna_starlark_and_glossary.py` (**`4 passed`**).
   - `tests/evals`: **`31 passed`**; `tests/security`: **`125 passed`**; `tests/contract`: **`2 passed`**.
   - PG18 unit testcontainer suites (`6` files, `--no-cov`): **`25 passed`**.
   - **Total Python Non-Integration Tests**: **`1187 passed`**, `0 failed`.
   - **Branch Coverage** (`.venv/bin/coverage run --branch` across non-PG18 `tests/unit` + `tests/security`, `--no-cov`, `.coverage*`/`/tmp/.cov_*` cleaned): **`92%`** (`1641` stmts, `100` missed, `262` branches, `47` partial across all `25` Story `26.8` touched/added Python modules — `_assistant_dbos_backend.py` `100%`, `_assistant_process_wiring.py` `100%`, `dbos_engine_ports.py` `100%`, `assistant_process_launcher.py` `98%`, `_orchestration_sql_hydration.py` `98%`, `_sql_dbos_launch_helpers.py` `98%`, `_dbos_workflow_defs.py` `97%`, `dbos_engine.py` `90%`, `engine.py` `98%`, `blackboard_and_engine.py` `100%`, `main.py` `99%`, `_assistant_turn_controls_routes.py` `96%`, `assistant_workspace_folders.py` `91%`).
3. **PG18 + Redis Integration Suites (`--no-cov`)**:
   - Story `26.x` (`12` files: `26_1`, `26_3`, `26_4a`, `26_4b` x3, `26_5` x2, `26_6a`, `26_6b`, `26_7`, `26_8`): **`15 passed`**.
   - Non-regression PG18 + Redis batch (`25_5`, `16_2`, `20_4`, `23_5`, `10_1..10_4`): **`10 passed`** (`test_story_16_2` re-verified `2/2` standalone after transient PG18 initdb `BrokenPipeError` during container startup).
   - DBOS & Orchestration PG18 suites (`22_1`, `22_3`, `23_2`, `test_story_3_2f_real_api_run_and_restart_postgres18.py`, `test_story_3_2s_dbos_postgres18.py`, `test_orchestration_anchors_challenges_gates_postgres18.py`, `test_dbos_return_loops_and_claim_check.py`, `test_story_25_3_orchestration_zero_demo_postgres18.py`): **`11 passed`** (confirming deterministic DBOS replay fix across server restarts).
   - **Total PG18 + Redis Integration Tests Verified**: **`36 passed`**, `0 failed`.
4. **TypeScript, Vitest & Playwright Desktop (`env -u ORCIA_E2E_SEED_FIXTURES`)**:
   - Solo `pnpm turbo run lint typecheck test --force`: **`9/9` tasks passed** (`1m1.26s`): `@orcia/api-client` (`3` files, `20` tests), `@orcia/ui` (`34` files, `136` tests), `@orcia/web` (`67` files, `261` tests) = **`417` JS/TS tests passed**.
   - Playwright `desktop-cockpit` (`00`, `02`, `12-finops`, `12-epic16`, `16`, `21`): **`15 passed, 1 skipped, 0 failed` (`3.1m`)**.
5. **Documentation, Catalog Sync & GitNexus Closure**:
   - `pnpm site:sync && pnpm site:check`: verified clean.
   - `.venv/bin/python scripts/check_implementation_docs.py`: verified clean.
   - `npx gitnexus analyze --index-only .` & `gitnexus check`: zero new dependency cycles.
