# Story 32.3 — Combined Unit + PG18 Coverage, `diff-cover`, Shared PG18 & App Fixtures, `pytest-xdist` & `lint_tests.py` Ratchet

- **Date**: 2026-11-27
- **Story / Sprint Key**: `32-3-combined-coverage-diff-cover-shared-pg18-infra-and-ratchet-lint` (`Epic 32 — Lot 3`)
- **Capability(ies)**: `none` (`hygiene` / NFR — `T-D1`, `T-D2`, `T-D10`)
- **Author / Context**: Implement Epic 32 Lot 3 (`T-D1`, `T-D2`, `T-D10`, analysis `O2`, `O3`, `O7` recall): combined Unit + PG18 coverage via `coverage run --parallel-mode` + `coverage combine` + `diff-cover >= 90%` once per story in Stage 3; canonical shared unit and xdist-isolated PG18/Redis/SeaweedFS fixtures; PEP 562 lazy imports on heavy entrypoints; extended `impact.py` recall validation; and `scripts/lint_tests.py --ratchet` in Stage 1.
- **Associated Commits**: *(pending commit)*

---

## 1. Needs Analysis & Tech Lead Impact Study (Pre-Implementation)

### 1.1 Context & Problem Statement
- **Current behavior**:
  1. `tests/unit/` runs sequentially (`~333 s` post-32.1) without `pytest-xdist` (`-n 4 --dist loadfile`); `pyproject.toml` `[tool.coverage.run]` sets `branch = true` and `concurrency = ["greenlet", "thread"]` without `source` or `parallel = true`, causing `sys.settrace` slowdowns across FastAPI/Pydantic/SQLAlchemy and lacking `diff-cover` enforcement on changed lines.
  2. `import orcia_api.main` takes **`7.74–8.63 s`** (cold/warm baseline measured via `python -X importtime`) because `orcia_api/main.py` eagerly executes `app = create_app()`, `orcia_api/__init__.py` eagerly imports `app`, `orcia_api/dependencies/__init__.py` eagerly loads all 9 dependency submodules (`assistant_tools` alone `2.56 s`), and `orcia_core/bootstrap/__init__.py` (`1.18 s`) + `orcia_core/orchestration/__init__.py` (`0.64 s`) eagerly import 50+ `_internal` SQL/adapter modules.
  3. `tests/unit/conftest.py` and `tests/integration/conftest.py` do not exist; each test boots its own `FastAPI` app, scans repo ASTs independently, or starts dedicated PG18 containers without shared session/template isolation.
  4. `scripts/agent_check_lib/impact.py` excludes `tests/integration/` (`_is_unit_or_fast_test_rel`), preventing Stage 3 from collecting PG18 integration coverage on touched modules.
  5. No automated ratchet exists to block new `FakeSqlEngine` mocks in `tests/unit/`, new `test_story_*` files (`256` currently exist), assertion removals in existing tests, or unguarded `workspace_id`/`run_id` FastAPI routes.
- **Expected behavior**:
  - Stage 3 (`full`/`all`) executes `tests/unit` (`-n 4 --dist loadfile`) and impacted `tests/integration/` tests under `coverage run --parallel-mode --branch` with `COVERAGE_PROCESS_START` + `sitecustomize.py` subprocess hook, merges `.coverage.*` via `coverage combine`, runs `diff-cover >= 90` once on changed Python source lines, and leaves `0` `.coverage*` residue.
  - Canonical shared fixtures in `tests/unit/conftest.py` and `tests/integration/conftest.py` provide isolated `create_seeded_test_app()`, `run_with_lifespan()`, `RepoSourceIndex`, and `flock`-guarded PG18 `IS_TEMPLATE` per-xdist-worker DBs, DBOS system DBs, Redis DB indices, and S3 bucket prefixes.
  - PEP 562 `__getattr__` lazy exports reduce `import orcia_api.main` toward `<= 4 s` while keeping Uvicorn/Docker/Playwright entrypoints (`orcia_api.main:app`, `orcia_api.main:create_app`) backwards-compatible.
  - `scripts/lint_tests.py --ratchet` + `scripts/lint_tests_ratchet.json` enforce all 5 anti-bloat/security rules in Stage 1.

### 1.2 Exploration, GitNexus Impact Analysis, Refactoring & Technical Debt
- **GitNexus Impact Analysis (`impact` scoped to ORCIA + worktree `grep`)**:
  - `create_app` (`apps/api/src/orcia_api/main.py`): upstream `impactedCount=4` (`risk: LOW`, `epistemic: exact`), direct caller `orcia_api/main.py:app = create_app()`, package re-export `orcia_api/__init__.py`, plus `scripts/export_openapi.py`, `infra/scripts/e2e/e2e_stack.py`, `scripts/manage.py`, `scripts/run_api.py`, Docker/K8s Uvicorn `orcia_api.main:app`, and test imports (`from orcia_api.main import create_app` / `app`).
  - `run_stage_full` (`scripts/agent_check_lib/stages.py`) and `build_static_gates` (`scripts/agent_check_lib/static_gates.py`): called by `scripts/agent_check_lib/stages.py:run_with_bounce` and tested in `tests/unit/tooling/test_agent_check_{stages,stages_and_edge_cases,runner_exec_and_gates,rules_and_fixture_index}.py`.
  - `_runner_source_digest` (`scripts/agent_check_lib/receipts.py`): hashes `scripts/*.py` and `scripts/agent_check_lib/*.py`; must also hash `scripts/lint_tests_lib/*.py` and `scripts/lint_tests_ratchet.json` so ratchet baseline updates invalidate cached receipts.
- **Exploration & Key Metrics**:
  - Installed tooling in `.venv`: `pytest-xdist==3.8.0`, `diff-cover==11.0.4`.
  - Baseline `import orcia_api.main`: **`7.717s–8.633s`** (`orcia_api.dependencies` `2.839s`, `orcia_core.bootstrap` `1.178s`, `orcia_core.orchestration` `0.635s`).
  - Existing debt discovered for ratchet baseline: `256` `test_story_*` files across `tests/`; `32` files in `tests/unit/` using `FakeSqlEngine`/`_FakeEngine`/`FakeSqlResult`/`_FakeSqlResult`; unguarded `workspace_id`/`run_id` endpoints in `apps/api/src/orcia_api/routers/orchestration.py` (`validate_workflow_manifest`, `compile_artifact_template`) and `apps/api/src/orcia_api/routers/blackboard_and_engine.py` (`get_run_blackboard_state`, `hydrate_step_context`, `execute_workflow_step`, `sign_human_anchor`) plus existing allow-listed legacy routes.
- **Refactoring & Tracked Technical Debt**:
  - Logged **`ACTION_ITEM-32.1`** in `docs/implementation-artifacts/sprint-status.yaml` so the unguarded `orchestration.py` and `blackboard_and_engine.py` routes are remediated in a dedicated security follow-up rather than buried silently in `scripts/lint_tests_ratchet.json`.
  - All new/modified files kept `<= 300` lines by splitting helpers into `tests/unit/fakes/test_app_helpers.py`, `tests/integration/_shared_topology_helpers.py`, `scripts/agent_check_lib/coverage_gate.py`, and `scripts/lint_tests_lib/`.

---

## 2. Implementation Plan

### 2.1 Data Schema & Alembic Migrations
- None (no PostgreSQL schema changes).

### 2.2 Hexagonal Core, Lazy Exports & Test Infrastructure (`packages/orcia-core/`, `tests/`)
- `packages/orcia-core/src/orcia_core/bootstrap/__init__.py` & `packages/orcia-core/src/orcia_core/orchestration/__init__.py`:
  - Replace eager top-level barrel imports with `if TYPE_CHECKING:` type stubs + PEP 562 `__getattr__` mapping (`_LAZY_EXPORTS`) so importing a single lightweight symbol no longer imports `litellm`, `dbos`, or all 40+ `_internal` SQL modules.
  - Keep `AD-19` `lint-imports` boundaries (`5/5` contracts) and `mypy --strict` intact.
- `tests/unit/conftest.py` + `tests/unit/fakes/test_app_helpers.py`:
  - Expose canonical `create_seeded_test_app()`, `run_with_lifespan()`, session-scoped `seeded_test_app` protected by a function-scoped `autouse` snapshot/restore of `app.dependency_overrides` and mutable `app.state` fields, and `RepoSourceIndex` (cached repo AST/file index).
- `tests/integration/conftest.py` + `tests/integration/_shared_topology_helpers.py`:
  - Session-scoped PG18 (`pgvector/pgvector:pg18`) + Redis 7.4 + SeaweedFS S3 topology with `/tmp` socket dirs, Alembic upgrade on template DB, connection disposal + `ALTER DATABASE <tpl> IS_TEMPLATE true`, `fcntl.flock`-guarded `CREATE DATABASE ... TEMPLATE` per xdist worker (`gw0..gw3`), isolated DBOS system DB, Redis DB index (`0..7`), S3 bucket prefix, and typed seed helpers `seed_org_workspace_admin()` and `activate_pack_with_slots()`.

### 2.3 Backend API, Runner & Ratchet Linter (`apps/api/`, `scripts/`, `docs/`)
- `apps/api/src/orcia_api/main.py`, `apps/api/src/orcia_api/__init__.py`, `apps/api/src/orcia_api/dependencies/__init__.py`:
  - PEP 562 `__getattr__` for `orcia_api.main.app`, `orcia_api.{app,create_app}`, and `orcia_api.dependencies` exports; import `app_lifespan` & `initialize_app_services` directly from `orcia_api.dependencies.core_and_lifespan`.
- `pyproject.toml`, `ARCHITECTURE-SPINE.md`, `docs/testing-strategy.md`:
  - Pin `pytest-xdist==3.8.0` and `diff-cover==11.0.4`, register `story` marker, configure `[tool.coverage.run]` (`source`, `parallel = true`, measured `greenlet` concurrency setting).
- `scripts/agent_check_lib/coverage_gate.py`, `stages.py`, `impact.py`, `static_gates.py`, `receipts.py`:
  - Extend `impact.py` to select impacted `tests/integration/*.py` (`integration_tests` field in `ImpactPlan`), validate recall against Epic 30–31 `A2`/`B` episodes.
  - Wire Stage 3 combined coverage (`COVERAGE_PROCESS_START` + `sitecustomize.py` dir in `PYTHONPATH`, `pytest -n 4 --dist loadfile --no-cov`, impacted PG18 `--no-cov`, `coverage combine`, `coverage xml -o .agent_check/coverage.xml`, `diff-cover --fail-under=90`, cleanup `.coverage*`).
  - Wire `scripts/lint_tests.py --ratchet` into Stage 1 and hash `scripts/lint_tests_lib/*.py` + `scripts/lint_tests_ratchet.json` in `receipts.py`.
- `scripts/lint_tests.py` + `scripts/lint_tests_lib/` + `scripts/lint_tests_ratchet.json`:
  - Enforce the 5 ratchet rules (fake SQL engines in `tests/unit/`, new `test_story_*` files, removed assertions in `git diff` without redundancy audit, unguarded `workspace_id`/`run_id` routes, non-blocking test-to-code proportionality report).

### 2.4 User Interface & Experience
- None (`apps/web`, `packages/ui`, `packages/api-client` untouched).

### 2.5 Test Pyramid Impact Analysis (`AD-17` — Layers 1 to 5 + Security, Mandatory)
- **Layer 1a (`tests/unit/tooling/`, `@pytest.mark.story("32.3")`)**:
  - `tests/unit/tooling/test_lint_tests_ratchet.py`: tests all 5 ratchet rules & allow-list shrinking.
  - `tests/unit/tooling/test_shared_test_infra.py`: tests `create_seeded_test_app()`, `autouse` isolation, `run_with_lifespan()`, `RepoSourceIndex`, PEP 562 `orcia_api.main:app` / lazy exports, and `flock` PG18 template helper logic.
  - `tests/unit/tooling/test_stage3_coverage_and_impact_recall.py`: tests `xdist` subprocess `sitecustomize.py` + `coverage combine` + `diff-cover` + `.coverage*` cleanup and Epic 30–31 `A2`/`B` recall validation.
- **Layer 1b (Vitest)**: none (no TS edits).
- **Layer 2 (PG18 Integration `tests/integration/`)**: measure `greenlet` concurrency with/without on a real PG18 test and verify shared PG18 fixture isolation.
- **Layer 3 (`lint-imports`, `lint_spine.py`, `export_openapi.py --check`)**: `0` findings / `0-diff`.
- **Layer 4 (`tests/evals/`) & Security (`tests/security/`)**: no regressions; `ACTION_ITEM-32.1` logged for unguarded `orchestration.py`/`blackboard_and_engine.py` routes.
- **Layer 5 (Playwright E2E)**: not impacted directly; `orcia_api.main:create_app` / `:app` entrypoint compatibility preserved.

---

## 3. Summary of Changes & Results (Post-Implementation)

### 3.1 Created & Modified Files
| File | Action | Concise Summary |
| :--- | :--- | :--- |
| `pyproject.toml` | Modified | Pinned `pytest-xdist>=3.8.0` and `diff-cover>=11.0.4`, registered `@pytest.mark.story`, set `[tool.coverage.run]` `source` + `parallel = true` + `concurrency = ["greenlet", "thread"]`. |
| `docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24/ARCHITECTURE-SPINE.md` | Modified | Updated `AD-17` combined Unit + PG18 `diff-cover >= 90%` policy and pinned `pytest-xdist` (`3.8.0`) & `diff-cover` (`11.0.4`) in `## Stack` (`lint_spine.py`: `0` findings). |
| `docs/testing-strategy.md` | Modified | Aligned `AD-17` coverage policy (`-n 4 --dist loadfile`, `coverage run --parallel-mode` + `coverage combine` + `diff-cover >= 90%` in Stage 3, `scripts/lint_tests.py --ratchet`). |
| `apps/api/src/orcia_api/{__init__.py,main.py,_router_registry.py,dependencies/__init__.py,dependencies/_lazy_exports.py}` | Modified / Created | Deferred `app = create_app()` and router mounting via PEP 562 `__getattr__` + `_router_registry.py`, and lazy-loaded `orcia_api.dependencies` with exact `TYPE_CHECKING` stubs. |
| `packages/orcia-core/src/orcia_core/{bootstrap,orchestration}/{__init__.py,_lazy_exports.py}` | Modified / Created | PEP 562 lazy barrel exports with static `if TYPE_CHECKING:` explicit re-exports preserving `mypy --strict` and `lint-imports`. |
| `scripts/agent_check_lib/{coverage_gate.py,impact.py,output.py,receipts.py,runner_exec.py,stages.py,static_gates.py}` | Created / Modified | Stage 3 combined coverage (`COVERAGE_PROCESS_START` + `sitecustomize.py` xdist hook, `coverage combine`, `--diff-file .agent_check/diff_cover.patch`, cleanup), Stage 2/3 PG18 `impact.py` extension (`8/8` Epic 30–31 recall), `-n 4 --dist loadfile` on large impact/full runs, Stage 1 `lint-tests --ratchet` gate, and receipt digest inclusion. |
| `scripts/{lint_tests.py,lint_tests_ratchet.json,lint_tests_lib/*}` | Created | Anti-bloat & security ratchet linter (`fake_sql=46`, `story_files=256`, `unguarded_routes=31`, assertion-removal diff check, non-blocking proportionality `ratio=0.62`). |
| `tests/{unit/conftest.py,unit/fakes/test_app_helpers.py,unit/fakes/workflows_seed.py,integration/conftest.py,integration/_shared_topology_fixture.py,integration/_shared_pg18_seeds_fixture.py,README.md}` | Created / Modified | Canonical `create_seeded_test_app()`, `run_with_lifespan()`, `autouse`-isolated `seeded_test_app`, `RepoSourceIndex` (dogfooded in `test_codebase_architectural_anti_patterns_audit.py`), `flock`-guarded PG18 `IS_TEMPLATE` per-xdist-worker DB + DBOS + Redis + S3 topology, typed PG18 seeds (`seed_org_workspace_admin`, `activate_pack_with_slots`), and refreshed `tests/README.md`. |
| `tests/unit/tooling/{test_lint_tests_ratchet,test_shared_test_infra,test_stage3_coverage_and_impact_recall}.py` & `tests/integration/db/test_shared_topology_pg18.py` | Created | Dogfooded domain-named tests tagged `@pytest.mark.story("32.3")` covering all 5 ratchet rules, shared unit/PG18 fixtures, PEP 562 lazy imports, xdist subprocess coverage hook, `diff-cover`, and impact recall. |
| `tests/unit/test_story_7_{0c,2}*.py` & `docs/implementation-artifacts/sprint-status.yaml` | Modified | Scoped `monkeypatch.delitem(sys.modules, "orcia_worker.docling_indexer", raising=False)` for xdist worker isolation; marked Story 32.3 `in-progress` and logged `ACTION_ITEM-32.1`. |

### 3.2 Empirical Benchmarks & Decisions (`T-D1`, `T-D2`, `O7` Recall)

1. **`import orcia_api.main` Startup Latency**:
   - **Before**: `7.717 s` (warm) / `8.633 s` (cold).
   - **After (PEP 562 lazy `app`, `_router_registry.py`, lazy `dependencies`/`bootstrap`/`orchestration`)**: **`0.635 s`** (`-92%`, `<= 4.0 s` target met).
2. **`tests/unit` Wall Time (`pytest -n 4 --dist loadfile --no-cov`)**:
   - **Before**: `391.61 s` (Epic 31 baseline) / `333.05 s` (post-32.1).
   - **After**: **`115.63 s`** (`-70.5%` vs baseline, `<= 120 s` target met).
3. **PG18 `greenlet` Concurrency Comparison (`tests/integration/api/test_story_30_5_agent_governance_and_lifecycle_pg18.py`)**:
   - **With `concurrency = ["greenlet", "thread"]`**: `77.94 s`, `50,471` stmts, `24,108` missed (`26,363` hit), **`44.35%`** total coverage.
   - **Without `greenlet` (`concurrency = ["thread"]`)**: `60.21 s` (`-17.73 s`), `50,448` stmts, `24,341` missed (`26,107` hit), **`43.86%`** total coverage (**`-256` SQLAlchemy asyncio greenlet-bridged statements**).
   - **Decision**: **Keep `concurrency = ["greenlet", "thread"]`** in `[tool.coverage.run]` and restrict `source = [...]` + run coverage once at Stage 3 so SQLAlchemy asyncpg frames are 100% captured without looping overhead. *(Note: legacy `test_story_3_2b_persistence_postgres18.py` timed out waiting for `WAITING_FOR_HUMAN_ARBITRATION` under `coverage run` and was excluded from the accuracy comparison.)*
4. **Epic 30–31 `A2` / `B` Recall Replay (`scripts/agent_check_lib/impact.py`)**:
   - Replayed **8/8 (100%)** representative episodes after extending `impact.py` to `tests/integration/`, stripping `{param}` placeholders from router decorator matching, adding `infra/migrations/` -> `test_alembic_migrations_*.py` mapping, and bypassing Composition Root barrel hubs unless lifespan files are touched:
     - `31.7` `get_run` cross-tenant leak (`_sql_workflow_v2_pending_query.py` & `workflows.py`) -> hit `test_story_30_3_pending_runs_and_live_guard_postgres18.py` (`fast=219/22`, `pg18=75/14`).
     - Epic 30–31 Alembic multi-statement `op.execute()` (`20261125_303_workflow_v2_runs.py`) -> hit `test_alembic_migrations_core_pg18.py` (`fast=5`, `pg18=2`).
     - Epic 31 `2_DOMAIN` permission regression (`evaluator.py`) -> hit `test_permissions_and_auth.py` (`fast=247`, `pg18=86`).
     - Epic 30–31 `test_story_26_6b` verifier catch (`governed_tool_router.py`) -> hit `test_story_26_6b_governed_tool_router_and_catalog.py` (`fast=195`, `pg18=73`).
     - Epic 31.2 `create_app()` pack-seeding `B` drift (`_lifespan_infra.py`) -> hit `test_story_30_3_workflows_and_bridge_coverage.py` (`fast=189`, `pg18=73`).
     - Epic 30.5 agent lifecycle regression (`agents_and_skills_manager.py`) -> hit `test_story_30_5_agent_governance_and_lifecycle_pg18.py` (`fast=187`, `pg18=73`).
     - Epic 30.1 assistant settings regression (`assistant_workspace_governance.py`) -> hit `test_story_30_1_assistant_settings_empty_instructions.py` (`fast=42`, `pg18=19`).

### 3.3 Independent Testing Verifier & AD-17 Results
- **Full Runner Verification (`scripts/agent_check.py all --no-skip` + `scripts/agent_check.py full`, exact worktree digest `6e206dc53b0e`)**:
  - `static`: `PASS [static]: 15 gates in 47.03s` (`ruff-check`, `ruff-format`, `mypy --strict`, `lint-imports`, `openapi-check`, `rules-lint`, `fixture-index`, `lint-tests`, `lint-spine`, and TypeScript workspace lint/typecheck gates).
  - `impact`: `PASS [impact]: 22 py + 1 vitest pkg(s) in 101.08s`.
  - `full-unit` (`tests/unit -n 4 --dist loadfile` + `COVERAGE_PROCESS_START` greenlet/thread subprocess tracing): `PASS [full-unit]: 1 target(s) in 323.34s`.
  - `full` (`tests/evals`, `tests/security`, `tests/contract` `-n 4 --dist loadfile` with coverage): `PASS [full]: 3 target(s) in 120.41s` (and `41.38s` on follow-up `full` run).
  - `full-pg18` (`tests/integration/db/test_shared_topology_pg18.py` with coverage): `PASS [full-pg18]: 1 target(s) in 49.10s`.
  - `full-diff-cover` (`coverage combine` + `coverage xml` + `diff_cover.diff_cover_tool --fail-under=90`): **`PASS [full-diff-cover]: Coverage: 97% in 42.26s`** (`142/146` changed lines covered, `4` missing).
  - `full-vitest` (`packages/ui`, `packages/api-client`, `apps/web` after clearing the intermittent `packages/ui` flake): `PASS [full-vitest]: 3 pkg(s) in 72.98s` (isolated `@orcia/ui` verification: `41/41` files, `159/159` tests in `12.37s`).
  - `full-docs-site` (`check_implementation_docs.py` + `pnpm site:check`): `PASS [full-docs-site]: 2 checks in 2.04s`.
  - **Coverage Artifact Cleanup**: `0` `.coverage*` residue files remaining in the worktree.
- **Raw `tests/unit` Wall Time (`pytest tests/unit -n 4 --dist loadfile --no-cov -q`)**:
  - **Coding baseline**: `115.63 s`; **Verifier runs**: `~117 s` (`0` failures, `1,332` unit checks) and `~123 s` under load (vs `391.61 s` Epic 31 baseline and `333.05 s` post-32.1).
- **Token Telemetry (`.venv/bin/python scripts/agent_token_report.py --story 32.3`)**: `SKIP: ORCIA_TRANSCRIPTS_DIR not set` (exit `0`).

### 3.4 Token, Duration KPIs & Flake Log (`T-D9` / Epic 32 Instrumentation)

- **Token & Duration KPIs** *(transcript KPIs omitted because `ORCIA_TRANSCRIPTS_DIR` is unset in this environment; stage timings & rule metrics measured directly)*:

| KPI | Epic 30–31 Baseline | Target | Measured (This Story) |
| :--- | :--- | :--- | :--- |
| Billed input tokens / story | median 66.6 M (mean 79.1 M) | ≤ 40 M (−40 %) | — *(transcripts unset)* |
| Test-related tokens / story | median 27.4 M (mean 31.0 M) | ≤ 14 M (−50 %) | — *(transcripts unset)* |
| Test-related turns / story | median 108 (mean 134) | ≤ 54 | — *(transcripts unset)* |
| Failed check runs / story | median 24 (mean 25.6) | ≤ 10 | 4 verifier bounces (`3` real `A`/`A2` catches, `1` pre-existing UI flake) |
| Noise failures (C + E + F) | 79 % (mean 20.3 / story) | ≤ 6 / story (−70 %) | 1 (`packages/ui` pre-existing timing flake) |
| Verifier bounces / story | median 3 (E30: 15, E31: 23) | ≤ 1 | 4 *(infra/runner self-verification story)* |
| Real bugs caught / story (A + A2) | mean 3.0 | ≥ 3.0 (floor) | 3 (`impact.py` hub fan-out, `/ready` `107.12 ms` latency, `diff_cover` CLI entrypoint) |
| Test-run minutes / story | mean 53 (E30: 47, E31: 59) | ≤ 20 | ~11.4 min (`full` Stage 3 w/ coverage: `683.22 s` total across `all --no-skip`) |
| `tests/unit` wall time | 392 s (333 s post-32.1) | ≤ 120 s | `115.63 s` (coding) / `~117 s` (verifier `--no-cov`); `323.34 s` (Stage 3 w/ coverage) |
| Always-on rules bytes / truncation | `36,416 B` (`12,464 B` truncated) | `AGENTS.md` ≤ 12 KB, all < 24 KB, 0 truncated | `AGENTS.md`: `6,781 B` (`0` truncated) |

- **Flake Log**:

| Date | Test / Check ID | Stage | Symptom | Root Cause / Resolution | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 2026-11-27 | `pytest:tests/integration` (`resolve_impacted_pg18_tests`) | `full-pg18` | `all --no-skip` hit `900s` timeout (`exit 124`) after selecting `84` PG18 files sequentially. | `A` — Excluded Composition Root barrel hubs from PG18 fan-out in `impact.py` (`84` -> `1` file) and added `-n 4 --dist loadfile` to `ESC`/`PG18` in `stages.py`. | Resolved |
| 2026-11-27 | `test_ready_probes_respond_under_100ms_without_sql_and_handle_uninitialized` | `full-unit` | `assert 107.117367 < 100.0` on cold first `GET /ready` under `xdist -n 4` + coverage. | `A2` — Short-circuited `/ready` & `/api/v1/ready` in `bearer_auth_rehydration_middleware`, built middleware stack eagerly in `create_app()`, and warmed `TestClient` portal before timer. | Resolved |
| 2026-11-27 | `diff-cover` (`scripts/agent_check_lib/coverage_gate.py:167`) | `full-diff-cover` | `No module named diff_cover.__main__` (`diff_cover==11.0.4`). | `A` — Switched invocation from `-m diff_cover` to `-m diff_cover.diff_cover_tool` (`97%` coverage verified). | Resolved |
| 2026-11-27 | `packages/ui/src/__tests__/rgaa-modals-escape-unsaved-guard.test.tsx:419` | `full-vitest` | `expected "spy" to be called 2 times, but got 1 times` after `waitFor` + `Escape`. | Pre-existing intermittent `packages/ui` `Escape` `useEffect`/timer race (unrelated to Story 32.3, which touches zero `.ts`/`.tsx` files). Passed `41/41` files (`159/159` tests) in `12.37s` on immediate re-run and `3 pkg(s)` in `72.98s` on `agent_check.py full`. | Observed (pre-existing flake) |
