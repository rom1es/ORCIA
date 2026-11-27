# Story 32.5 — End-of-Story Diff-Only Architect Review (`T-D3`)

- **Date**: 2026-11-27
- **Reviewer**: `bmad-architect-worker` (`pro` tier)
- **Scope**: Story `32.5` diff vs `efdff04` (Majors #1–#7 remediation, quick Minors, survivor split, `test_e2e_sql_coverage_audit.py`, suite budgets, and delta verification of `10-story-32-5-diff-review` remediation)
- **Verdict**: **`APPROVED`**

---

## 1. Triaged Findings

- **Blocker (`0`)**: None.
- **Major (`0`)**: None (all initial Majors resolved; see Section 2).
- **Minor (`1`)**:
  1. **`[minor]` Deferred optional PG18 concurrency test (`09-epic-32-architecture-review.md:41`)**:
     `SqlWorkflowV2RunsStore.get_run()` `strict_sql=True` coverage was added (`test_story_30_3_processes_live_llm_and_pending_runs.py:318-319`); the optional two-task `asyncio.gather` PG18 race test for `SqlPermissionBrokerRepository.ensure_policies_seeded` remains deferred (non-blocking). *(Note: `scripts/test_budgets.json` `slow_unit_test_allowlist` contains 130 verified JUnit entries primarily from `TestClient(create_app())` modules and can be shrunk monotonically in future epics as suites migrate to `seeded_test_app`.)*

---

## 2. Delta Verification of `CHANGES_REQUESTED` Fixes

| Item | Resolution Verified | Evidence |
| :--- | :--- | :--- |
| **Review Major #1** (CI coverage asymmetry) | **PASS** | `.github/workflows/ci.yml:109-111` traces all 4 packages (`packages/orcia-core`, `packages/orcia-connectors`, `apps/api`, `apps/worker`); `.github/workflows/ci.yml:152-162` runs `coverage run --parallel-mode` across the same 4 sources and scopes `coverage report --fail-under=90` to `--include="packages/orcia-core/*"`. |
| **Review Major #2** (Uncalibrated `test_budgets.json`) | **PASS** | `scripts/agent_check_lib/budgets.py:88-111,167-179` adds `find_stale_allowlist_ids()` failing on missing JUnit IDs; `scripts/test_budgets.json` (`138 L`) purged the 3 nonexistent IDs and calibrated `slow_unit_test_allowlist` against live JUnit output (`agent_check.py budget` passing: `tests/unit 112.61s <= 120.00s`, `evals_security_contract 36.63s <= 45.00s`); covered by `test_runner_budgets_and_hardening.py:254-288`. |
| **Review Minor #1** (`check_removed_assertions` split check) | **PASS** | `scripts/lint_tests_lib/diff_and_routes.py:111,130-161` tracks `new_file_added_by_dir` and requires cumulative added assertions `>= removed_cnt` per directory; covered by `test_lint_tests_ratchet.py:128-142`. |
| **Review Minor #2** (`bounce.py` empty PG18 fallback) | **PASS** | `scripts/agent_check_lib/bounce.py:106-118` falls back to `resolve_junit_test_file` on `bounce.failed_tests` before returning `0`; covered by `test_runner_budgets_and_hardening.py:144-183`. |
| **Review Minor #3** (Module-scoped helper ASTs) | **PASS** | `scripts/lint_tests_lib/diff_and_routes.py:190-327` scopes helpers per module (`module_helpers`), resolves `orcia_api.*` and relative imports (`module_imports`), and avoids cross-router name collisions; covered by `test_runner_budgets_and_hardening.py:217-251`. |
| **Review Minor #4** (`docs/testing-strategy.md`) | **PASS** | `docs/testing-strategy.md:58,140` updated to `225` Python / `147` TS/TSX files and strict default `scripts/lint_tests.py`. |

---

## 3. Full Story 32.5 Verification Matrix (Diff vs `efdff04`)

| Scope Item | Status | Evidence |
| :--- | :--- | :--- |
| **Epic Review Major #1** (`--files` static receipt) | **PASS** | `scripts/agent_check.py:80`, `stages.py:54-88`, `bounce.py:141,181`, `test_runner_budgets_and_hardening.py:55-69` |
| **Epic Review Major #2** (`T-D5` bounce & class JUnit) | **PASS** | `receipts.py:212-224`, `stages.py:89,133`, `bounce.py:29-206`, `test_runner_budgets_and_hardening.py:72-183` |
| **Epic Review Major #3** (`coverage_gate.py -uall`) | **PASS** | `coverage_gate.py:107-109,192-204`, `test_runner_budgets_and_hardening.py:186-205` |
| **Epic Review Major #4** (`lint-spine` JSON `"ok"`) | **PASS** | `static_gates.py:175-195`, `stages.py:81`, `.github/workflows/ci.yml:49-63`, `test_runner_budgets_and_hardening.py:208-214` |
| **Epic Review Major #5** (`isolated_worker_pg18_env`) | **PASS** | `tests/integration/conftest.py:19-66` (`S3_ENDPOINT_URL`, `SEAWEEDFS_ENDPOINT_URL`, `S3_BUCKET_NAME`, `ORCIA_ENV_FILE`, Redis `FLUSHDB`) |
| **Epic Review Major #6** (`lint_tests.py` strict & CI) | **PASS** | `lint_tests.py:72-80,160`, `lint_tests_ratchet.json` (`fake_sql: []`, `redundancy_exempt: []`, `legacy_story: 236`, `unguarded_routes: 18`, `0` `assistant_*`), `checks.py:43-46`, `diff_and_routes.py:111-368`, `.github/workflows/ci.yml:44,68-78,109-162` |
| **Epic Review Major #7** (OpenAPI Vitest mocks) | **PASS** | `scripts/generate_vitest_openapi_mocks.py`, `synthesizer.py`, `generatedOpenApiMocks.ts` (`661 L`), `static_gates.py:106-112`, `receipts.py:82-84`, `ci.yml:68-69`, `transportAndOpenApiValidator.ts` + `vitest-transport-fail-closed-openapi.test.ts` preserved |
| **Deliverable 1** (`i18n-and-shell` split) | **PASS** | `i18n-and-shell.test.tsx` deleted; `shellTestHelpers.tsx` (`179 L`) + 5 route-scoped files (`144 L`, `145 L`, `193 L`, `193 L`, `180 L`) all `<= 300 L` with invariants intact |
| **Deliverable 2** (`test_e2e_sql_coverage_audit.py`) | **PASS** | `test_e2e_sql_coverage_audit.py:236,258` (`>= 1`, `>= len(specs)`), domain/SQL/cold-reload checks intact |
| **Deliverable 3** (`budgets.py` & `test_budgets.json`) | **PASS** | `scripts/agent_check_lib/budgets.py` (`223 L`), `scripts/agent_check.py:70-83`, `scripts/test_budgets.json` (`138 L`), `test_runner_budgets_and_hardening.py:254-288` |
| **Quick Minors #1–#8** | **PASS** | `impact.py:46`, `checks.py:43-46` + `test_lint_tests_ratchet.py:77-84`, `test_story_30_3_...:318-319`, `_packs_red_team_fixtures.py:1`, `tests/unit/conftest.py:40-51,77-88`, `coverage_gate.py:192-204`, `AGENTS.md:13`, `orcia_api/main.py:147` |
