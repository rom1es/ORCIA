# Story 32.5 — Strict Anti-Bloat Lint, OpenAPI-Generated Vitest Mocks, `i18n-and-shell` Survivor Split & Test-Time Budgets

- **Date**: 2026-11-27
- **Story / Sprint Key**: `32-5-strict-anti-bloat-lint-openapi-vitest-mocks-and-survivor-split` (`Epic 32 — Lot 5`)
- **Capability(ies)**: `none` (`hygiene` / NFR — `T-D2`, `T-D3`, `T-D10`)
- **Author / Context**: Implement Epic 32 Lot 5 (`T-D2`, `T-D3`, `T-D10`, Phase 4 budgets) and remediate all 7 Majors plus quick Minors from `09-epic-32-architecture-review.md` prior to Epic 32 `--no-skip` closure.
- **Associated Commits**: *(pending commit)*

---

## 1. Needs Analysis & Tech Lead Impact Study (Pre-Implementation)

### 1.1 Context & Problem Statement
- **Current behavior**:
  1. Epic 32 Architect Review (`09-epic-32-architecture-review.md`) flagged 7 Majors: unsound `static` receipt when `--files` narrows `run_stage_static` (Major #1), premature `last_failure.json` clearing & incomplete `STAGE1_STAGE2_AND_FAILED` / class-qualified JUnit resolution in `stages.py` (Major #2), `coverage_gate.py` missing `.py` files inside new untracked directories (Major #3), `lint-spine` silently passing on exit code `0` despite `"ok": false` JSON output (Major #4), `isolated_worker_pg18_env` missing `S3_ENDPOINT_URL`/`SEAWEEDFS_ENDPOINT_URL`/`S3_BUCKET_NAME`/`ORCIA_ENV_FILE` & Redis `FLUSHDB` (Major #5), `lint_tests.py` defaulting to `--ratchet` with `45` redundancy exemptions and `diff_and_routes.py` AST false positives + missing CI gates (Major #6), and reconciling OpenAPI-generated Vitest mocks with fail-closed unhandled-route enforcement (Major #7).
  2. Hand-written baseline payloads in `apps/web/src/__tests__/setup/` duplicate OpenAPI schemas, while `apps/web/src/__tests__/i18n-and-shell.test.tsx` (`2,313` lines) remains the last oversized test monolith.
  3. `tests/unit/test_e2e_sql_coverage_audit.py` locks exact counts (`len(specs) == 29`, `total_blocks == 64`), and no automated wall-time or per-unit-test (`> 1.0 s`) budget module exists in `scripts/agent_check_lib/`.
- **Expected behavior**:
  - Resolve Majors #1–#7 and quick Minors cleanly (`orcia_api/main.py` `__getattr__` caching, `tests/unit/conftest.py` `auth_service.evaluator` isolation, `HUB_WIRING_SMOKE_TESTS` `test_openapi_security.py`, `SqlWorkflowV2RunsStore.get_run()` `strict_sql=True` unit test, `_StubSql*`/`_MockSql*` AST check, `AGENTS.md` path fix).
  - `scripts/lint_tests.py` defaults to strict mode (`fake_sql_engine_files` hard-locked to `[]`, `redundancy_audit_exempt_files: []`, frozen monotonic-shrink legacy/route sets, CI wired).
  - `scripts/generate_vitest_openapi_mocks.py` (`--check` wired into Stage 1 and `receipts.py` digest) generates `apps/web/src/__tests__/setup/generatedOpenApiMocks.ts`, used by mock handlers for baseline payloads while preserving fail-closed `[vitestFetchTransport FAIL-CLOSED] Route non gérée`.
  - `i18n-and-shell.test.tsx` split into 5 route-scoped `<= 300`-line suites + `shellTestHelpers.tsx`.
  - `test_e2e_sql_coverage_audit.py` checks structural non-empty invariants, and `scripts/agent_check_lib/budgets.py` verifies raw `--no-cov` suite budgets and JUnit `> 1.0 s` slow unit tests.

### 1.2 Exploration, GitNexus Impact Analysis, Refactoring & Technical Debt
- **GitNexus / Caller Verification**:
  - Active worktree `story_thirty_three` is not yet in the GitNexus registry (`Repository not found`); callers confirmed via `grep -rn`:
    - `run_stage_static`, `run_with_bounce`: called from `scripts/agent_check.py`, `scripts/agent_check_lib/stages.py`, and `tests/unit/tooling/test_agent_check_stages.py`.
    - `build_diff_cover_patch`: called from `scripts/agent_check_lib/stages.py`, `scripts/agent_check_lib/coverage_gate.py`, and `tests/unit/tooling/`.
    - `run_ratchet`: called from `scripts/lint_tests.py` and `tests/unit/tooling/test_lint_tests_ratchet.py`.
    - `isolated_worker_pg18_env`: used by `tests/integration/db/test_shared_topology_pg18.py` and `tests/integration/test_story_31_{3,4,5}_*.py`.
    - `vitestFetchTransport`: imported in `apps/web/src/__tests__/vitest.setup.ts` and `apps/web/src/__tests__/vitest-transport-fail-closed-openapi.test.ts`.
    - `i18n-and-shell.test.tsx`: referenced only in `docs/testing-strategy.md:77` (`0` references in `docs/product/capabilities.yaml`).
- **Refactoring & Modularity (`<= 300` lines)**:
  - Keep every new/edited `.py` and `.ts`/`.tsx` file `<= 300` lines (split `generate_vitest_openapi_mocks_lib/` if needed; split `i18n-and-shell.test.tsx` into 5 `<= 300`-line modules).
  - Track `ACTION_ITEM-32.1` (`unguarded_routes_allowlist` for genuine unguarded routes in `orchestration.py` / `blackboard_and_engine.py`) without altering production API routers in Story 32.5.

---

## 2. Implementation Plan

### 2.1 Data Schema & Alembic Migrations
- None (`0` schema or Alembic migration changes).

### 2.2 Runner Hardening, Strict Anti-Bloat Lint, Budgets & CI (`scripts/`, `.github/workflows/ci.yml`, `AGENTS.md`)
- **`scripts/agent_check_lib/`**:
  - `stages.py`, `receipts.py`: skip `static` receipt read/write when `--files` is explicitly provided; preserve `last_failure.json` across `static`/`impact` unless the failing check (or full/all) succeeds; resolve class-qualified JUnit `classname` in `ONLY_FAILED_CHECK` and re-run Stage 1 + Stage 2 + `bounce.failed_check` on `STAGE1_STAGE2_AND_FAILED`.
  - `coverage_gate.py`: pass `-uall` to `git status --porcelain -uall` in `build_diff_cover_patch`.
  - `static_gates.py`: parse `lint_spine.py` JSON stdout (`ok is True` and `total_findings == 0`), run `scripts/lint_tests.py` (strict default), run `scripts/generate_vitest_openapi_mocks.py --check`, and include `packages/orcia-connectors` in `mypy` fallback.
  - `impact.py`: add `tests/unit/test_openapi_security.py` to `HUB_WIRING_SMOKE_TESTS`.
  - `budgets.py` (new, `<= 300` L): check raw `--no-cov` suite wall-time targets (`tests/unit <= 120 s`, `evals+security+contract <= 45 s`) and JUnit XML per-test `> 1.0 s` slowness against a narrow allow-list in `scripts/test_budgets.json`.
- **`scripts/lint_tests.py` & `scripts/lint_tests_lib/`**:
  - Make strict mode the default (`--strict` accepted, `--ratchet` kept optional/aliased); hard-enforce `fake_sql_engine_files == []` regardless of JSON; reset `redundancy_audit_exempt_files` to `[]`; extend `_has_fake_sql_engine_ast` for `_StubSql*`/`_MockSql*`; extend `diff_and_routes.py` AST helper/`Depends(...)` traversal to clear `assistant_*` false positives while keeping `legacy_story_test_files` and `unguarded_routes_allowlist` strictly monotonic-shrink.
- **`.github/workflows/ci.yml` & `AGENTS.md`**:
  - Wire `lint_spine.py` JSON `"ok"` assertion, `packages/orcia-connectors` `mypy --strict`, `scripts/lint_tests.py`, `scripts/check_agent_rules.py`, `scripts/generate_test_fixture_index.py --check`, `scripts/generate_vitest_openapi_mocks.py --check`, and `coverage run --parallel-mode` + `coverage combine` on `tests/integration`.
  - Fix stale `apps/api/dependencies.py` path in `AGENTS.md:13`.

### 2.3 Backend & Fixture Isolation Fixes (`apps/api/`, `tests/`)
- `apps/api/src/orcia_api/main.py`: cache `globals()["app"] = _LAZY_APP` in `__getattr__`.
- `tests/integration/conftest.py`: export `S3_ENDPOINT_URL`, `SEAWEEDFS_ENDPOINT_URL`, `S3_BUCKET_NAME`, isolated `ORCIA_ENV_FILE`, and per-test Redis `FLUSHDB` in `isolated_worker_pg18_env`.
- `tests/unit/conftest.py`: snapshot/restore `auth_service.evaluator` (`_memberships`, `_org_units`, `_workspaces`, `_user_roles` or deep copy) in `_isolate_seeded_test_app_state`.
- `tests/unit/test_story_30_3_processes_live_llm_and_pending_runs.py`: add symmetric `strict_sql=True` error-propagation test on `SqlWorkflowV2RunsStore.get_run()`.
- `tests/unit/test_e2e_sql_coverage_audit.py`: replace `len(specs) == 29` and `total_blocks == 64` with non-empty structural invariants (`>= 1`, `>= len(specs)`).

### 2.4 OpenAPI Vitest Mock Generator & `i18n-and-shell` Survivor Split (`scripts/`, `apps/web/`, `docs/`)
- `scripts/generate_vitest_openapi_mocks.py` (+ `scripts/generate_vitest_openapi_mocks_lib/`): zero-dependency generator reading `packages/api-client/openapi.json` (`$ref` cycle/depth guard, `allOf`/`anyOf`/`oneOf`, `204`, deterministic UUIDv7 & ISO-8601 defaults, valid enums) emitting `apps/web/src/__tests__/setup/generatedOpenApiMocks.ts` with typed per-operation builders accepting partial overrides.
- Refactor high-churn mock handlers in `apps/web/src/__tests__/setup/` to build baseline payloads from `generatedOpenApiMocks.ts`, keeping stateful overrides hand-written and preserving fail-closed `[vitestFetchTransport FAIL-CLOSED] Route non gérée` in `transportAndOpenApiValidator.ts` and `vitest-transport-fail-closed-openapi.test.ts`.
- Delete `apps/web/src/__tests__/i18n-and-shell.test.tsx` and split survivors into 5 `<= 300`-line route-scoped suites + `apps/web/src/__tests__/setup/shellTestHelpers.tsx`; update `docs/testing-strategy.md`.

### 2.5 Test Pyramid Impact Analysis (`AD-17`)
- **Layer 1a (`tests/unit/tooling/`)**: new `@pytest.mark.story("32.5")` tests (not named `test_story_*`) for OpenAPI mock generator, strict `lint_tests.py`, budget checks, and Majors #1–#4, plus updates to `test_stage3_coverage_and_impact_recall.py`, `test_lint_tests_ratchet.py`, and `test_story_30_3_processes_live_llm_and_pending_runs.py`.
- **Layer 1b (`apps/web/src/__tests__/`)**: 5 split shell test suites (`<= 300` L each), generated OpenAPI mock builders, fail-closed transport contract preserved.
- **Layer 2 (`tests/integration/conftest.py`)**: S3 env alignment & per-test Redis `FLUSHDB` verified on PG18 integration runs.
- **Layer 3 (`scripts/lint_tests.py`, `export_openapi.py --check`, `lint-imports`, `lint_spine.py`)**: strict anti-bloat lint, `0`-diff OpenAPI/mocks, JSON `"ok"` spine gate.
- **Layer 4 (`tests/evals/`) & Security (`tests/security/`)**: `<= 45 s` raw budget verified by `budgets.py`.
- **Layer 5 (`apps/web/e2e/`)**: untouched; `test_e2e_sql_coverage_audit.py` preserves domain-table, non-trivial SQL, and cold-reload invariants without brittle counts.

---

## 3. Summary of Changes & Results (Post-Implementation)

### 3.1 Created & Modified Files

| File | Action | Concise Summary |
| :--- | :--- | :--- |
| `scripts/agent_check.py`, `scripts/agent_check_lib/{bounce,budgets,coverage_gate,impact,receipts,stages,static_gates}.py`, `scripts/test_budgets.json` | Created / Modified | Resolved Majors #1–#4 (`--files` static receipt scoping, `T-D5` `last_failure.json` & class JUnit resolution, `-uall` diff-cover patch, `lint-spine` JSON `"ok"` assertion, `orcia-connectors` mypy fallback, `test_openapi_security.py` hub smoke), added raw `--no-cov` suite/per-test wall-time `budgets.py` + `test_budgets.json`. |
| `scripts/lint_tests.py`, `scripts/lint_tests_lib/{checks,diff_and_routes}.py`, `scripts/lint_tests_ratchet.json` | Modified | Made strict mode default (`fake_sql_engine_files: []`, `redundancy_audit_exempt_files: []`, frozen monotonic-shrink sets), added `_StubSql*`/`_MockSql*` AST check, added directory-level assertion split parity, and cleared `assistant_*` AST false positives via module-scoped helper/`Depends` resolution. |
| `scripts/generate_vitest_openapi_mocks.py`, `scripts/generate_vitest_openapi_mocks_lib/`, `apps/web/src/__tests__/setup/{generatedOpenApiMocks.ts,*MockHandlers.ts}` | Created / Modified | Zero-dependency OpenAPI mock generator (`--check` gated in Stage 1 and `receipts.py`), refactored high-churn mock handlers to build baselines from `generatedOpenApiMocks.ts` while preserving fail-closed `[vitestFetchTransport FAIL-CLOSED] Route non gérée`. |
| `apps/web/src/__tests__/i18n-and-shell.test.tsx`, `apps/web/src/__tests__/setup/shellTestHelpers.tsx`, `apps/web/src/__tests__/shell-*.test.tsx` | Deleted / Created | Deleted `2,313`-line `i18n-and-shell.test.tsx` monolith and split into 5 route-scoped `<= 300`-line Vitest suites + `shellTestHelpers.tsx`. |
| `.github/workflows/ci.yml`, `AGENTS.md`, `docs/testing-strategy.md`, `tests/README.md` | Modified | Wired strict `lint_tests.py`, `lint_spine.py` JSON check, `orcia-connectors` `mypy`, `check_agent_rules.py`, `generate_test_fixture_index.py --check`, `generate_vitest_openapi_mocks.py --check`, and `coverage run --parallel-mode` + `coverage combine` on `tests/integration`; fixed `AGENTS.md` path and updated `testing-strategy.md`. |
| `apps/api/src/orcia_api/main.py`, `tests/integration/conftest.py`, `tests/unit/conftest.py`, `tests/security/_packs_red_team_fixtures.py`, `tests/unit/test_e2e_sql_coverage_audit.py`, `tests/unit/test_story_30_3_processes_live_llm_and_pending_runs.py`, `tests/unit/tooling/*.py` | Created / Modified | Cached `_LAZY_APP` in `orcia_api/main.py`; exported S3/SeaweedFS env vars + per-test Redis `FLUSHDB` in `isolated_worker_pg18_env`; isolated `auth_service.evaluator` in `seeded_test_app`; added `strict_sql=True` `get_run()` test and structural `test_e2e_sql_coverage_audit.py` invariants; added Story 32.5 tooling/generator/budget unit tests. |
| `docs/implementation-artifacts/test-optimization-2026-11-27/{09-epic-32-architecture-review,10-story-32-5-diff-review}.md`, `docs/implementation-artifacts/sprint-status.yaml`, `docs/site-catalog/index.html`, `apps/web/src/generated/orciaSiteManifest.ts` | Created / Modified | Architect reviews (`09-epic-32-architecture-review.md`, `10-story-32-5-diff-review.md`), Epic 32 / Story 32.5 closure status, and site catalog/manifest sync. |

### 3.2 Quantitative Metrics, Coverage & Static Quality
- **Architect Reviews (`T-D3`)**:
  - [09-epic-32-architecture-review.md](../test-optimization-2026-11-27/09-epic-32-architecture-review.md): `APPROVED_WITH_32_5_ACTIONS` (all 7 Majors & quick Minors addressed in Story 32.5).
  - [10-story-32-5-diff-review.md](../test-optimization-2026-11-27/10-story-32-5-diff-review.md): **`APPROVED`** (`0` blockers, `0` majors, `1` minor — optional deferred PG18 concurrency test).
- **Mandatory Final `--no-skip` Verification (`timeout -k 10s 900s .venv/bin/python scripts/agent_check.py all --no-skip`)**:
  - `PASS [static]: 17 gates in 64.13s` (includes `ruff`, `mypy --strict`, `lint-imports` `5 kept, 0 broken`, `lint_spine.py` JSON `ok: true, 0 findings`, `lint_tests.py` strict default, `check_agent_rules.py`, `generate_test_fixture_index.py --check`, `generate_vitest_openapi_mocks.py --check`, `export_openapi.py --check`, TS lint/typecheck)
  - `PASS [impact]: 21 py + 1 vitest pkg(s) in 96.15s`
  - `PASS [full-unit]: 1 target(s) in 316.90s`
  - `PASS [full]: 3 target(s) in 118.16s` (`evals+security+contract` + `full-pg18` + container checks)
  - `PASS [full-diff-cover]: Coverage: 100% in 41.85s` (`>= 90%` required)
  - `PASS [full-vitest]: 3 pkg(s) in 76.10s`
  - `PASS [full-docs-site]: 2 checks in 2.06s`
  - `.coverage*` residue after completion: `0` files (`NO_COVERAGE_RESIDUE`)
- **Suite & Per-Test Budget Gate (`timeout -k 10s 240s .venv/bin/python scripts/agent_check.py budget`)**:
  - `PASS [budget:tests/unit]: 107.16s <= 120.00s` (`0` unallowlisted `> 1.0s` unit tests, `0` stale allowlist IDs)
  - `PASS [budget:evals_security_contract]: 40.02s <= 45.00s`
  - `PASS [budget]: raw unit<=120s, esc<=45s, unit_test<=1.0s in 147.19s`

### 3.3 AD-17 Test Pyramid & Vertical Wiring Verification
- **Layer 1a (`tests/unit/`)**: `tests/unit` raw `--no-cov` wall time `107.16s <= 120.00s`, `full-unit` combined branch coverage run `316.90s` (`diff-cover: 100%`). New tooling tests cover runner hardening, bounce rules, JUnit class resolution, budget/stale-ID checks, strict `lint_tests.py`, and deterministic OpenAPI Vitest mock generation.
- **Layer 1b (`apps/web/src/__tests__/`)**: `full-vitest` passed across `3 pkg(s)` in `76.10s`; `i18n-and-shell.test.tsx` split into 5 `<= 300`-line suites using `generatedOpenApiMocks.ts` while preserving fail-closed `[vitestFetchTransport FAIL-CLOSED] Route non gérée`.
- **Layer 2 (`tests/integration/`)**: `full-pg18` passed inside `full` (`118.16s`); `isolated_worker_pg18_env` exports aligned S3/SeaweedFS vars, `ORCIA_ENV_FILE`, and per-test Redis `FLUSHDB`.
- **Layer 3 (Contracts & Architecture)**: `lint-imports` (`5 contracts kept, 0 broken`), `lint_spine.py` (`ok: true, 0 findings`), `export_openapi.py --check`, `generate_vitest_openapi_mocks.py --check`, and `lint_tests.py` strict default all passed in Stage 1 (`17 gates in 64.13s`).
- **Layer 4 (`tests/evals/`) & Security (`tests/security/`)**: Combined `evals_security_contract` raw wall time `40.02s <= 45.00s` and verified in `full` (`118.16s`).
- **Layer 5 (`apps/web/e2e/`)**: `test_e2e_sql_coverage_audit.py` structural non-empty invariants, domain-table SQL checks, and cold-reload checks preserved without hardcoded file/block counts.

### 3.4 Token, Duration KPIs & Flake Log (`T-D9` / Epic 32 Closure Summary)

- **Token & Duration KPIs** (`scripts/agent_token_report.py --story 32.5` exited `0`: `SKIP: ORCIA_TRANSCRIPTS_DIR not set`; deterministic runner/budget & rule-byte KPIs measured directly below):

| KPI | Epic 30–31 Baseline | Target | Measured (Story 32.5 / Epic 32 Closure) |
| :--- | :--- | :--- | :--- |
| Billed input tokens / story | median 66.6 M (mean 79.1 M) | ≤ 40 M (−40 %) | `SKIP: ORCIA_TRANSCRIPTS_DIR not set` (evaluated on Epic 33 feature stories) |
| Test-related tokens / story | median 27.4 M (mean 31.0 M) | ≤ 14 M (−50 %) | `SKIP: ORCIA_TRANSCRIPTS_DIR not set` (evaluated on Epic 33 feature stories) |
| Test-related turns / story | median 108 (mean 134) | ≤ 54 | `SKIP: ORCIA_TRANSCRIPTS_DIR not set` |
| Failed check runs / story | median 24 (mean 25.6) | ≤ 10 | `1` Verifier bounce on `budget` (`test_budgets.json` calibration) |
| Noise failures (C + E + F) | 79 % (mean 20.3 / story) | ≤ 6 / story (−70 %) | `0` noise failures during final `--no-skip` verification |
| Verifier bounces / story | median 3 (E30: 15, E31: 23) | ≤ 1 | `1` (resolved by Fixer #1) |
| Real bugs caught / story (A + A2) | mean 3.0 | ≥ 3.0 (floor) | `1` (`budget` calibration omission; floor evaluated on Epic 33 feature stories) |
| Test-run minutes / story | mean 53 (E30: 47, E31: 59) | ≤ 20 | `agent_check.py budget`: `2.45 min` (`147.19s`); `all --no-skip` final gate: `11.92 min` (`715.35s` across 7 stages) |
| `tests/unit` raw `--no-cov` wall time | `392 s` (`333 s` post-32.1) | ≤ 120 s | **`107.16 s`** (`-72.7%` vs `392 s` baseline) |
| `evals+security+contract` raw `--no-cov` wall time | — | ≤ 45 s | **`40.02 s`** |
| Always-on rules bytes / truncation | `36,416 B` (`12,464 B` truncated) | `AGENTS.md` ≤ 12 KB, all < 24 KB, 0 truncated | `AGENTS.md`: **`6,793 B`**, `bmad-model-routing.md`: **`1,688 B`**, total: **`8,481 B`** (`0` truncated, `-76.7%`) |

- **Flake / Bounce Log**:

| Date | Test / Check ID | Stage | Symptom | Root Cause / Resolution | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 2026-11-27 | `tests.unit.test_story_29_2_ontology_guards::test_p22_control_center_syncs_topology_on_requests` | `budget` | `SLOW (1.68s > 1.0s)` during initial `agent_check.py budget` run (`tests/unit` raw `113.42s <= 120.00s`) | Uses `_make_isolated_app` (`create_app()`) like its 3 already-allowlisted sibling tests in `scripts/test_budgets.json:96-98`. Added to `scripts/test_budgets.json` by Fixer #1; re-verified green in `agent_check.py budget` (`147.19s`) and `agent_check.py all --no-skip`. | Resolved |
