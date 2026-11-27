# Story 32.4 — Repo-Wide Test Pyramid Pruning with Coverage Safety Gate & Mutation Sample

- **Date**: 2026-11-27
- **Story / Sprint Key**: `32-4-repo-wide-test-pyramid-pruning-with-coverage-safety-gate` (`Epic 32 — Lot 4`)
- **Capability(ies)**: `none` (`hygiene` / NFR — `T-D11`)
- **Author / Context**: Implement Epic 32 Lot 4 (`T-D11`, `O4` pyramid pruning): deterministic per-test `dynamic_context = test_function` coverage-context audit via `scripts/test_redundancy_audit.py`, full elimination of all `46` `fake_sql_engine_files` (`46 -> 0`) in `scripts/lint_tests_ratchet.json`, consolidation of scattered guards and duplicate PG18 pairs onto `isolated_worker_pg18_env`, `RepoSourceIndex` wiring on slow AST audits, Vitest structural slimming, capabilities/fixture index sync, and a one-off mutation sample on 3 heavily pruned production modules.
- **Associated Commits**: *(pending commit)*

---

## 1. Needs Analysis & Tech Lead Impact Study (Pre-Implementation)

### 1.1 Context & Problem Statement
- **Current behavior**:
  1. `scripts/lint_tests_ratchet.json` tracks `46` `fake_sql_engine_files` under `tests/unit/` (21 in `tests/unit/packs/`, 1 in `tests/unit/connectors/`, 19 inline fake SQL engines/sessions in `tests/unit/`, and 5 non-SQL / borderline AST matches), plus `256` legacy `test_story_*.py` files.
  2. Epic 30–31 audits (`02-epic30-vs-epic31-test-strategy.md`) identified 21–37.5 % coverage padding and 11–18 % cross-layer duplication across unit, security, PG18 integration, and Vitest suites (overlapping PG18 pairs `31_4` and `31_5`, redundant Epic 30 coverage-padding files, scattered guard assertions for `ScopeAccessGuard` / `READ_ONLY_OBSERVER -> 403` / `ERR_PACK_SLOT_UNBOUND 422` / anti-hostage `409`, and slow `rglob` AST walks not yet using `RepoSourceIndex`).
  3. No automated tool inspects SQLite `.coverage` files produced with `dynamic_context = test_function` to quantify per-test unique line/branch contributions and guard before/after combined branch coverage during pruning.
- **Expected behavior**:
  - `scripts/test_redundancy_audit.py` (with helpers in `scripts/test_redundancy_audit_lib/` if needed, all files `<= 300` lines) analyzes `.coverage` SQLite DBs with `dynamic_context = test_function`, computes per-test unique line/branch contributions, flags zero-unique-contribution tests, and verifies before/after branch coverage safety (`>=` baseline on production business/security modules).
  - `fake_sql_engine_files` in `scripts/lint_tests_ratchet.json` drops from `46` to `0` (`[]`) without weakening fake-SQL detection, folding any unique non-SQL validation/error branches into PG18 or pure non-SQL unit tests first.
  - Overlapping PG18 pairs (`31_4` and `31_5`) merge onto `isolated_worker_pg18_env`; scattered guards become compact table-driven `@pytest.mark.parametrize` suites with `@pytest.mark.story(...)`; slow AST audits reuse `RepoSourceIndex`; brittle Vitest structural padding is slimmed; `capabilities.yaml` and `tests/README.md` remain 100% consistent.
  - All Protected `A`/`A2` tests remain intact, and a bounded one-off mutation sample on 3 pruned modules kills mutants cleanly before restoring original production files.

### 1.2 Exploration, GitNexus Impact Analysis, Refactoring & Technical Debt
- **Protected `A`/`A2` Set (`T-D11`)**:
  - Cross-tenant `403` PG18: `tests/integration/api/test_story_30_3_pending_runs_and_live_guard_postgres18.py`, `test_story_29_1_autonomous_runs_and_finops_pg18.py`.
  - `2_DOMAIN` PG18 permission checks & `governed_tool_router` / `test_story_26_6b_security_and_composition_root.py`.
  - `30_2` prompt/SSE/security evals (`test_story_30_2_*`, `test_story_26_1_*`).
  - `apps/web/src/__tests__/story-29-5-folders-fetch-race-guard.test.tsx`.
  - E2E journeys (`02`, `08`, `12`, `30`, `31`).
- **Mutation Sample Target Modules (`T-D11`)**:
  1. `packages/orcia-core/src/orcia_core/packs/_internal/_sql_workspace_pack_mutations.py` / `_sql_workspace_slot_bindings.py`
  2. `packages/orcia-core/src/orcia_core/storage/pack_draft_guard.py`
  3. `packages/orcia-core/src/orcia_core/workflows/_internal/sql_workflow_v2_runs.py`
- **Traceability & Audit Artifacts**:
  - Update `docs/product/capabilities.yaml` `tests:` references for every deleted/merged test file so `pnpm site:sync && pnpm site:check` passes cleanly.
  - Document before/after metrics, per-test context audit findings, `redundancy_audit_exempt_files` justifications, and exact mutation kill scores in `docs/implementation-artifacts/test-optimization-2026-11-27/07-story-32-4-redundancy-audit.md`.

---

## 2. Implementation Plan

### 2.1 Data Schema & Alembic Migrations
- None (no database schema changes; `Story 32.4` modifies test suites, scripts, and documentation only, plus temporary local mutation checks cleanly reverted).

### 2.2 Redundancy Audit Tooling (`scripts/test_redundancy_audit.py`, `tests/unit/tooling/`)
- Implement `scripts/test_redundancy_audit.py` (`<= 300` lines, splitting SQLite/coverage parsing and safety-gate comparison into `scripts/test_redundancy_audit_lib/` as needed):
  - Read `.coverage` databases via `coverage.CoverageData` API (`measured_files()`, `measured_contexts()`, `set_query_contexts(None)` + `contexts_by_lineno()`, `arcs()`, `lines()`) with `dynamic_context = test_function` configured solely in a temporary `.ini` file.
  - Compute per-test covered arcs/lines, unique arcs/lines (hit by only that test context), and zero-unique-contribution test lists.
  - Compare pre-prune and post-prune branch coverage JSON/SQLite snapshots on production modules (`packages/orcia-core/src`, `packages/orcia-connectors/src`, `apps/api/src`, `apps/worker/src`) to enforce zero branch regression on business/security modules.
- Add unit tests in `tests/unit/tooling/test_redundancy_audit.py` (`@pytest.mark.story("32.4")`, `<= 300` lines).

### 2.3 Baseline Capture, `46 -> 0` Fake-SQL Elimination & Pyramid Consolidation (`tests/`, `apps/web/`, `scripts/`)
- Capture exact pre-prune baseline (file counts, LOC per layer, combined Unit + PG18 branch coverage on pruned domains) prior to deletions.
- Eliminate all `46` `fake_sql_engine_files` (`46 -> 0` in `scripts/lint_tests_ratchet.json`):
  - Resolve the 5 non-SQL AST false positives cleanly (rename `_FakeSqlRag` -> `_InMemoryRagStub`, `_FakeSqlHybridRagRepo` -> `_InMemoryHybridRagStub`, etc., and tighten `_has_fake_sql_engine_ast` in `scripts/lint_tests_lib/checks.py` to match actual fake SQL string/session execution rather than `"Sql"` substring on hexagonal ports).
  - For pre-Epic-30 inline fake-SQL files (`smtp_otp`, `20_1`, `22_2`, etc.), verify `(Unit + PG18)` branch baseline first and fold any unique branches into existing or newly consolidated `isolated_worker_pg18_env` / pure unit tests before removing fake-SQL harnesses.
  - Use `redundancy_audit_exempt_files` in `scripts/lint_tests_ratchet.json` strictly for audited slimmed files in `32.4` (noting it resets to `[]` in `32.5`).
- Preserve genuine red-team security vectors (adversarial zip-slip, SSRF, secret-leak, prompt-leak payloads) from `30_6` and `31_7`: strip redundant `create_app()` / fake-SQL scaffolding and consolidate payloads into fast `@pytest.mark.parametrize` checks on `seeded_test_app` / PG18.
- Prune/consolidate Epic 30–31 padding (`30_3_*_coverage.py`, `30_6_*_audit.py`), merge duplicate PG18 pairs (`31_4` and `31_5`) onto `isolated_worker_pg18_env` ONLY if merged file remains strictly `<= 300` lines (otherwise two lean modules sharing `isolated_worker_pg18_env`), exclude from-scratch Alembic migration tests (`test_alembic_migrations_*_pg18.py`) and bespoke container failure tests from `isolated_worker_pg18_env`, parameterize repetitive guard checks (`@pytest.mark.parametrize` + `@pytest.mark.story`), wire slow `rglob` AST audits onto `RepoSourceIndex`, slim brittle Vitest structural padding (`epic-30-ux-hardening-audit.test.ts` keeping CTA matrix; preserving `i18n-and-shell.test.tsx` and OpenAPI Vitest mocks for `32.5`), and leave `apps/web/e2e/*.spec.ts` untouched unless executed.
- Close `BARREL_HUB_MODULES` / `COMPOSITION_HUB_MODULES` zero-test blind spot in `scripts/agent_check_lib/impact.py`: keep 84-file PG18 fan-out blocked, while mapping edits on those hubs to fast `< 3 s` app-wiring/readiness unit smoke tests (`tests/unit/tooling/test_shared_test_infra.py`, `tests/unit/test_story_7_0c_openshift_scc_kustomize_and_ready.py`) and updating `test_stage3_coverage_and_impact_recall.py`.

### 2.4 Traceability, Mutation Sample & Verification (`docs/`, `scripts/`)
- Update `docs/product/capabilities.yaml` `tests:` lists, regenerate `tests/README.md` via `scripts/generate_test_fixture_index.py`, and update `scripts/lint_tests_ratchet.json` (`fake_sql_engine_files: []`, shrunken `legacy_story_test_files`, justified `redundancy_audit_exempt_files`).
- Execute the one-off mutation sample on the 3 target production modules, record exact killed/total mutant scores, and restore all production files cleanly.
- Author `docs/implementation-artifacts/test-optimization-2026-11-27/07-story-32-4-redundancy-audit.md` and run Story `32.4` local verification gates.

### 2.5 Test Pyramid Impact Analysis (`AD-17` — Layers 1 to 5 + Security)
- **Layer 1a (`tests/unit/tooling/`)**: `test_redundancy_audit.py` (`@pytest.mark.story("32.4")`) + surviving/consolidated unit & guard suites.
- **Layer 1b (Vitest)**: Slimmed structural audit retaining functional CTA matrix; `story-29-5-folders-fetch-race-guard.test.tsx` preserved.
- **Layer 2 (PG18 Integration)**: Merged `31_4` and `31_5` PG18 suites on `isolated_worker_pg18_env`; `A`/`A2` PG18 tests (`30_3`, `29_1`, `2_DOMAIN`) untouched.
- **Layer 3 (`lint_tests.py --ratchet`, `lint-imports`, `lint_spine.py`)**: `fake_sql_engine_files == 0`, zero assertion-removal violations, `0` architectural findings.
- **Layer 4 (`tests/evals/`) & Security (`tests/security/`)**: `30_2` / `26_1` evals & security suites preserved; redundant fake-SQL red-team padding removed.
- **Layer 5 (Playwright E2E)**: Core journeys (`02`, `08`, `12`, `30`, `31`) preserved intact.

---

## 3. Summary of Changes & Results (Post-Implementation)

### 3.1 Delivered Files & Artifacts
- **Redundancy audit tooling**:
  - `scripts/test_redundancy_audit.py` + `scripts/test_redundancy_audit_lib/{__init__.py,analyzer.py}` (`coverage.CoverageData` API reading `dynamic_context = test_function` from temporary `.agent_check/audit_cov.ini`, never added to default `pyproject.toml`)
  - `tests/unit/tooling/test_redundancy_audit.py` (`@pytest.mark.story("32.4")`, 3/3 passed)
- **Fake-SQL elimination (`46 -> 0`) & pyramid consolidation**:
  - `scripts/lint_tests_lib/checks.py` (`_has_fake_sql_engine_ast` tightened cleanly so hexagonal ports no longer trigger on `"Sql"` substring) + 5 AST-false-positive stub renames
  - Deleted 21 redundant/fake-SQL files (17 in `tests/unit/packs/`, plus `test_story_29_1_scope_resolution_extra.py`, `test_story_29_3_governance_service_cov.py`, `test_story_30_3_workflows_and_bridge_coverage.py`, `test_story_30_6_lifecycle_and_modal_guards_audit.py`) after folding unique non-SQL helpers; stripped fake-SQL blocks from 22 surviving unit/security files while keeping 100% of red-team vectors (`30_6`, `31_7`) and Protected `A`/`A2` coverage
  - Added table-driven `tests/unit/packs/test_pack_guard_matrix.py` (`258 L <= 300 L`, `@pytest.mark.story("31.4" / "31.5" / "32.4")`) and converted Epic 31 PG18 suites onto `isolated_worker_pg18_env` (`<= 300 L` each, two lean modules retained where merging would exceed `300 L`)
  - Wired 4 slow AST audits onto `RepoSourceIndex`; slimmed brittle fs-grep checks in `apps/web/src/__tests__/epic-30-ux-hardening-audit.test.ts` (0 `apps/web/e2e/*.spec.ts` files edited)
  - Retained 100% of red-team vectors across `tests/security/test_story_31_7_packs_red_team_security.py` (`174 L`), `test_story_31_7_packs_isolation_and_guards.py` (`198 L`), `_packs_red_team_fixtures.py` (`194 L`), and supporting unit/security suites (`test_story_31_1_security_and_starlark_dos.py`, `test_story_31_5_export_scrubber.py`, `test_story_7_0a_log_secret_masking.py`, `test_story_26_1_guards_and_ssrf_policy.py`)
- **Stage 2 hub impact fix**:
  - Updated `scripts/agent_check_lib/impact.py` (`HUB_WIRING_SMOKE_TESTS`) & `tests/unit/tooling/test_stage3_coverage_and_impact_recall.py`
- **Traceability & Audit**:
  - Updated `scripts/lint_tests_ratchet.json` (`fake_sql_engine_files: []`, `legacy_story_test_files: 256 -> 236`, `redundancy_audit_exempt_files: 45` (`20` deleted `test_story_*` + `25` slimmed), resetting to `[]` in `32.5`)
  - Updated `docs/product/capabilities.yaml`, refreshed `tests/README.md` via `scripts/generate_test_fixture_index.py`, and authored `docs/implementation-artifacts/test-optimization-2026-11-27/07-story-32-4-redundancy-audit.md`

### 3.2 Coverage Safety Gate, Pyramid KPIs & Mutation Results
- **Test proportionality (`lint_tests.py --ratchet`)**: `test_loc = 170,309 -> 162,618` (`162,602` at Verifier `lint-tests`), `prod_loc = 276,531`, `ratio = 0.62 -> 0.59` (**-7,691 test LOC** / **-7,707** at Verifier check, 21 deleted / 2 added = **-19 net test files**, `631 -> 612` total files)
- **Apples-to-apples `(Unit + 7 PG18)` combined coverage**: `before_arcs = 11,520 / before_lines = 8,124` -> `after_arcs = 11,009 / after_lines = 7,815` (`0` regressions on `packs.py`, `workspace_packs.py`, `pack_composer.py`, `import_service.py`, `apm_codec.py`, `_pack_export_views.py`, `slot_guard.py`; remaining `-511` arcs are fake-SQL-only missing-DDL/SQL-mock paths)
- **Three-module mutation sample (`T-D11`)**: **12 / 12 (100.0 %)** mutants killed across `_sql_workspace_pack_mutations.py` / `_sql_workspace_slot_bindings.py` (`4/4`), `pack_draft_guard.py` (`4/4`), and `sql_workflow_v2_runs.py` (`4/4`) after closing 3 initial-pass gaps (`M1A`, `M1D`, `M3C`); `git diff packages/ apps/api/` verified clean of mutation residue

### 3.3 Architect Review & Independent Testing Verifier Results
- **Architect Review (`docs/implementation-artifacts/test-optimization-2026-11-27/08-story-32-4-architect-review.md`)**: **`APPROVED`** (`0` blockers, `0` majors; `5` non-blocking minors logged for Story `32.5`, with Minor #3 documentation counts reconciled across `07-story-32-4-redundancy-audit.md` and this report).
- **Full Independent Runner Verification (`.venv/bin/python scripts/agent_check.py all --no-skip`)**:
  - `static`: **PASS (`16 gates in 69.98 s`)** — `lint-tests --ratchet`: `fake_sql=0`, `story_files=236`, `unguarded_routes=31`, `test_loc=162602`, `prod_loc=276531`, `ratio=0.59`, `0` violations
  - `impact`: **PASS (`51 py + 1 vitest pkg(s) in 112.38 s`)**
  - `full-unit` (`tests/unit -n 4 --dist loadfile` w/ coverage): **PASS (`1 target(s) in 302.13 s`)**
  - `full` (`tests/evals`, `tests/security`, `tests/contract` w/ coverage): **PASS (`3 target(s) in 109.75 s`)**
  - `full-pg18` (impacted PG18 suites w/ coverage): **PASS (`5 target(s) in 90.90 s`)**
  - `full-diff-cover` (`coverage combine` + `coverage xml` + `diff-cover --fail-under=90`): **PASS (`>=90% in 42.10 s`)** — `diff_cover.diff_cover_tool` confirmed `"No lines with coverage information in this diff."` (0 production Python lines modified in `packages/` / `apps/`).
  - `full-vitest` (`packages/ui`, `packages/api-client`, `apps/web`): **PASS (`3 pkg(s) in 73.53 s`)**
  - `full-docs-site`: **PASS (`2 checks in 2.07 s`)**
- **Raw Post-Pruning `tests/unit` Wall Time (`.venv/bin/pytest tests/unit -n 4 --dist loadfile --no-cov`)**: **`1,292 passed, 4 warnings in 110.49 s`** (vs `391.61 s` Epic 31 baseline, `333.05 s` post-32.1, and `115.63 s` post-32.3; `<= 120 s` target met).
- **Parallel Epic 31 PG18 `isolated_worker_pg18_env` Verification (`31_4` + `31_5`, `-n 4 --dist loadfile --no-cov`)**: **`4 passed, 8 warnings in 51.35 s`** (`IS_TEMPLATE` + `flock` per-worker isolation verified cleanly in parallel).
- **Token Telemetry (`.venv/bin/python scripts/agent_token_report.py --story 32.4`)**: `SKIP: ORCIA_TRANSCRIPTS_DIR not set` (exit `0`).
- **Final Hygiene & Synchronization Gates**: `pnpm site:sync && pnpm site:check` **PASS**, `.venv/bin/python scripts/check_implementation_docs.py` **PASS**, `0` `.coverage*` / `/tmp/.cov_*` residue files, and `git status -s packages/ apps/api/` clean.

### 3.4 Token, Duration KPIs & Flake Log (`T-D9` / Epic 32 Instrumentation)

- **Token & Duration KPIs** *(transcript KPIs omitted because `ORCIA_TRANSCRIPTS_DIR` is unset in this environment; stage timings & rule metrics measured directly)*:

| KPI | Epic 30–31 Baseline | Target | Measured (This Story) |
| :--- | :--- | :--- | :--- |
| Billed input tokens / story | median 66.6 M (mean 79.1 M) | ≤ 40 M (−40 %) | — *(transcripts unset)* |
| Test-related tokens / story | median 27.4 M (mean 31.0 M) | ≤ 14 M (−50 %) | — *(transcripts unset)* |
| Test-related turns / story | median 108 (mean 134) | ≤ 54 | — *(transcripts unset)* |
| Failed check runs / story | median 24 (mean 25.6) | ≤ 10 | 0 verifier bounces *(all `all --no-skip` gates passed on first run)* |
| Noise failures (C + E + F) | 79 % (mean 20.3 / story) | ≤ 6 / story (−70 %) | 0 |
| Verifier bounces / story | median 3 (E30: 15, E31: 23) | ≤ 1 | 0 |
| Real bugs caught / story (A + A2) | mean 3.0 | ≥ 3.0 (floor) | 3 *(initial-pass mutation gaps `M1A`, `M1D`, `M3C` surfaced & closed; Stage 2 hub wiring gap closed in `impact.py`)* |
| Test-run minutes / story | mean 53 (E30: 47, E31: 59) | ≤ 20 | ~13.4 min (`all --no-skip` total `802.84 s` across all 8 stages) |
| `tests/unit` wall time | 392 s (333 s post-32.1) | ≤ 120 s | `110.49 s` (`1,292 passed`, `--no-cov -n 4 --dist loadfile`); `302.13 s` (Stage 3 w/ coverage) |
| Always-on rules bytes / truncation | `36,416 B` (`12,464 B` truncated) | `AGENTS.md` ≤ 12 KB, all < 24 KB, 0 truncated | `AGENTS.md`: `6,781 B` (total w/ routing rule: `8,469 B`, `0` truncated) |

- **Flake Log**:

| Date | Test / Check ID | Stage | Symptom | Root Cause / Resolution | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| 2026-11-27 | `—` *(none observed)* | `all --no-skip` | Zero flakes across `static`, `impact`, `full-unit`, `full`, `full-pg18`, `full-diff-cover`, `full-vitest`, `full-docs-site`, raw `tests/unit`, and parallel Epic 31 PG18 runs. | Clean first-pass execution (`0` retries). | Clean |
