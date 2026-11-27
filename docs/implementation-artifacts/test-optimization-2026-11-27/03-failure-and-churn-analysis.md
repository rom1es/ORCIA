# Epics 30 and 31: which test failures found real bugs, and which tests had to be rewritten after code changes

Adds to [epic30_vs_epic31_test_strategy.md](02-epic30-vs-epic31-test-strategy.md).

**Data:** 371 events were extracted from the agent transcripts: 333 failed check runs plus 38 times a coding agent received fix requests from the coordinator (a "bounce"). For each failed run, the extraction recorded what was edited before the next run. Every event was then classified by hand by root cause. Separately, the git diffs of existing test files were analysed for Epics 28–31.
Scripts and data: [failure_episodes.py](local transcript-analysis data, not versioned), [episodes_e30.jsonl](local transcript-analysis data, not versioned), [episodes_e31.jsonl](local transcript-analysis data, not versioned), [churn/](local transcript-analysis data, not versioned).

---

## 1. Why the checks failed

| Root cause | Epic 30 (117 failures) | Epic 31 (216 failures) | What it means |
|---|---:|---:|---|
| **A: real bug in this story's new code**, fixed in the code | 5 | 18 | value |
| **A2: an existing test caught a regression**, fixed in the code | 8 | 8 | value |
| B: an existing test was outdated by an intentional behaviour change | 10 | 11 | maintenance |
| C: the story's own new test was wrong | 28 | **81** | noise |
| D: an existing test broke on a structure change, not a behaviour change | 5 | 4 | maintenance |
| E: environment, flaky test or infrastructure | **29** | 16 | noise |
| F: quality gate (lint, format, type check, 90 % coverage, file length) | 32 | **78** | noise |
| **Share that caught a real bug (A + A2)** | **11 %** | **12 %** | |

**The clearest finding: only about 1 failure in 9 points to a real bug.** The rest are:
- **New-test bugs (C):** in Epic 31, mostly fake SQL engines and hand-written SQL fixtures.
- **Lint, format and coverage-threshold loops (F)**, often hidden inside chained `ruff && mypy && coverage && pytest` commands, so a formatting error forces a full test re-run.
- **Environment problems (E):** `AF_UNIX path too long`, ports 8100/3101 already in use, wrong `coverage --source` flags, stale paths in prompts, `pg_isready` not awaited.

**Time to get back to green, by root cause:**
- **Epic 30:** environment 88 min, outdated existing tests 57 min, quality gates 54 min, new-test bugs 22 min, real bugs (A + A2) 18 min.
- **Epic 31:** quality gates about 360 min (this includes the waits around chained commands), new-test bugs 173 min, real bugs (A + A2) 133 min, environment 49 min.

> [!NOTE]
> The two classifiers measured time differently: Epic 30 counts active time until the next green run, Epic 31 counts non-overlapping waiting time. Compare shares within an epic, not absolute minutes across epics.

## 2. Which layers caught real bugs

| Layer | Catch rate, Epic 30 | Catch rate, Epic 31 | Bugs that no earlier layer caught |
|---|---:|---:|---|
| evals / security / contract | **40 %** | 25 % | Prompt, SSE streaming and security regressions (30.2) |
| PG18 integration | 16 % | **21 %** | **Real PostgreSQL behaviour that fakes can't show:** an Alembic step running several SQL statements in one `op.execute()`; `FOR UPDATE` on a nullable outer join; a **cross-tenant leak** (`get_run` without `workspace_id` returned 200 instead of 403, caught by an *Epic 30* PG18 test during 31.7); the `2_DOMAIN` permission regression |
| E2E (Playwright) | 8 % | **33 %** | Front-end/API ID mismatches (`bundle_id` vs `pack.id`); React `useEffect` wiping form state; data lost on page reload (F5); the export-scrubber round trip |
| Full `tests/unit` (in the verifier) | 22 % | 14 % | A regression the coding agent's targeted runs missed (`test_story_26_6b`) |
| Vitest | 20 % | 11 % | React hook races and SSE state bugs |
| **Coverage runs** | **0 %** | **6 %** | none, in 65 failures across both epics |
| turbo / lint / typecheck | 0 % | 0 % | none (needed, but a style gate) |
| **Architect review** (not automated) | **3 bugs** | **6 bugs** | Security and API-contract bugs missed by every automated layer: missing `ScopeAccessGuard`, export-read permissions, a client payload that no longer matched the API, a lock overwrite |

**What this shows:**
- **Real PostgreSQL tests and E2E catch the bugs that matter**, and they find the bugs fake SQL engines and mocked Vitest hide. This confirms the plan to replace fake SQL with PG18 rather than add more unit tests.
- **Coverage runs catch almost nothing.** They should be a single measurement at the end of a story, not something agents loop on.
- **The existing regression suite is worth keeping.** It caught 8 regressions per epic, including a cross-tenant security hole. The aim is to run it smarter (see O7 below), not to shrink it blindly.
- **Architecture review is the only thing that catches permission and contract bugs.** Bugs it finds repeatedly should be turned into automated checks (O9).
- **In 31.7, an E2E test was "fixed" by loosening it** (a timeout/filter workaround), which hid a real React bug until the verifier found it.

## 3. Existing tests that had to be rewritten after code changes

### From git (existing test files changed per epic)
| Epic | Existing test files changed | Lines (+/−) | Behaviour change (B) | Structure coupling (D) | Padding (P) | Fixture/bootstrap drift (F) | Real improvement (R) |
|---|---:|---:|---:|---:|---:|---:|---:|
| 28 | 16 / 20 | +328 / −161 | 5 | **9** | 0 | 0 | 2 |
| 29 | 36 / 69 | +646 / −735 | 11 | **17** | 0 | 5 | 3 |
| 30 | 35 / 56 | +679 / −176 | 13 | **15** | 1 | 4 | 2 |
| 31 | 25 / 93 | +294 / −630 | 5 | 7 | 1 | **11** | 1 |

- **Structure coupling (D) is the most common reason in Epics 28–30.** Tests check `data-testid`s, labels, route counts, AST/source strings or mock handlers, not behaviour.
- **In Epic 31, fixture drift (F) dominates (44 %).** `create_app()` stopped seeding packs in memory, which broke 11 existing tests: 5 swapped to `create_seeded_test_app`, and lifespan and slot seeding were added in PG18 tests. The underlying problem is that there's no single canonical test-app fixture.
- **Hand-written Vitest mock handlers changed in all 4 epics** (+425 / −338 lines). Every backend contract change means editing mock handlers by hand, and an endpoint nobody mocked breaks unrelated test suites.

### Files that keep needing changes
| File | Size | Epics touched | Why it keeps breaking |
|---|---:|---:|---|
| `apps/web/src/__tests__/i18n-and-shell.test.tsx` | **2,309 lines** | 4 / 4 | One huge file asserting test IDs, tabs and labels on every route; also the slowest Vitest file (26 s) |
| `tests/unit/test_e2e_sql_coverage_audit.py` | 307 | 3 | Hard-coded exact counts (`len(specs)==N`, `total_blocks==M`) and an allow-list of tables |
| `apps/web/src/__tests__/setup/workspacesAndCatalogMockHandlers.ts` | 477 | 3 | Re-implements FastAPI business rules by hand |
| `apps/web/src/__tests__/setup/mockBackendState.ts` | 366 | 3 | One global mutable state object |
| `e2e/12-epic16-reflexive-trace…spec.ts` | – | broke 7 times during Epic 30 | Inline setup (datasources), and the collapsed-by-default UX change |

### Padding costs again later
- 7 Epic 30 test files had to change during Epic 31. **3 of them are padding files** that were already flagged (`30_3_workflows_and_bridge_coverage`, `30_4_workflows_helpers_coverage`, `30_6_…_audit`). They break because they're tied to private helpers.
- The other 4 broke because of fixture drift.

## 4. New optimizations these findings point to

| # | Optimization | Failures it removes | Phase |
|---|---|---|---|
| O1 | **Auto-fix before running anything:** one `make precheck` / `scripts/precheck.sh` running `ruff format` + `ruff check --fix` + `mypy`/`tsc` on touched files. **Ban chained `lint && coverage && pytest` commands** | F: 32 + 78 | 0 |
| O2 | **Canonical test fixtures:** `create_seeded_test_app()`, `run_with_lifespan()` and typed PG18 seed helpers (`seed_org_workspace_admin()`, `activate_pack_with_slots()`) in a shared `conftest.py` | C (hand-written SQL), F drift (11 in Epic 31) | 1 |
| O3 | **Coverage measured once, not looped on:** coding agents never run `--fail-under` loops; one diff-coverage run per story that also counts PG18 runs | 65 coverage failures, 0–6 % catch rate | 2 |
| O4 | **Harden the environment:** sockets under `/tmp`, per-runner E2E ports and lock files, wait for `pg_isready`, worktree `PYTHONPATH` via a `.pth` file, one `scripts/run_cov.sh` (correct `--source`), remove stale paths (`orcia-kernel`) from agent briefs | E: 29 + 16 | 1 |
| O5 | **Mocks generated from the API schema:** a Vitest fallback responder generated from `openapi.json`, with hand-written handlers kept only for stateful overrides | D + B in Vitest; mock churn in 4 / 4 epics | 3 |
| O6 | **Make brittle tests robust:** split `i18n-and-shell.test.tsx` per route; remove exact counts from `test_e2e_sql_coverage_audit.py`; narrow the word-matching audits (`"safe"`, `@` in docs) | D: 5 + 4 recurring | 1 |
| O7 | **Run the impacted existing tests before handing over:** a "legacy impact" step in the coding agent (GitNexus upstream impact → the existing tests that import touched modules) | 12 existing-test failures found only by the verifier in Epic 31, each costing a bounce | 0 |
| O8 | **No-workaround rule for E2E:** never loosen timeouts or selectors to get green; fix the root cause or escalate | the hidden React bug in 31.7 | 0 |
| O9 | **Turn recurring architect findings into automated checks:** for example "every route that takes `workspace_id` / `run_id` enforces `ScopeAccessGuard`", and "client payload builders match the OpenAPI schemas" | 9 architect-only bugs, including the cross-tenant leak | 3 |
| O10 | **Rebalance the verifier:** drop its coverage re-run and its broad PG18 batches (0 % catch rate in Epic 30). Keep the full unit run, impacted PG18 tests, impacted E2E and security evals | – | 0 |

## 5. Further things worth measuring

| What to measure | How | Why |
|---|---|---|
| **Flaky tests** | 13 (Epic 30) and 11 (Epic 31) failures passed on re-run with no edit. Keep a flake log in each Tech Lead report, plus a quarantine list | Avoid re-running whole sequences because of flakes |
| **Real test effectiveness** | One-off mutation testing (e.g. `mutmut`, run from scratch, not added as a project dependency) on 3 modules: a SQL adapter, a guard, a pure parser | Show objectively whether padding and fake-SQL tests catch any deliberately injected bugs, compared with PG18 tests |
| **Redundant tests** | `coverage run --context=test`, then list tests that cover no line nothing else covers | Automatically find candidates to prune |
| **Catch rate per test file over time** | Keep `failure_episodes.py` running each epic; flag tests that never failed in N epics and are slow | Move them to a nightly run |
| **How good the test selection would be** | Replay the Epic 30/31 A2 and B failures: would GitNexus impact selection (O7) have picked those tests? | Validate O7 before relying on it |
| **Agent overhead** | Each extra re-run adds turns, and the whole context is re-sent each turn. Test output itself is small (about 1 M tokens per epic) compared with 405–623 M input tokens | The number of runs matters much more than how verbose the output is |
| **Verifier time to first failure** | Today 1–15 min (median about 4) | Track it after the gate-order change |
| **Overlap between coding agent and verifier** | Checked: no identical command was re-run after the last edit; the overlap is at the layer level | No action needed beyond O10 |
| **Docker and container start-up cost** | Image pulls, Ryuk disabled, no container reuse | Feeds the session-container work in Phase 3 |
| **Wrong commands in agent briefs** | Count failures caused by a bad flag or path (e.g. `coverage --source`, `orcia-kernel`) | Fix briefs and templates once |

## 6. Changes to the 5-phase plan

- **Phase 0 (agent rules):** add O1 precheck, O7 impacted existing tests, O8 no workarounds, O10 verifier rebalance, and a flake log.
- **Phase 1 (quick fixes):** add O2 canonical fixtures, O4 environment hardening, O6 split the brittle files.
- **Phase 2 (coverage and pruning):** O3 makes "coverage measured once" explicit. This phase is **confirmed by the data**: fake SQL caught 0 of the real PostgreSQL bugs, while PG18 caught 8.
- **Phase 3 (shared infrastructure):** add O5 schema-generated mocks and O9 automated checks from recurring architect findings.
- **Phase 4 (budgets):** track catch rate and flake rate per epic, alongside the time budgets.

> [!IMPORTANT]
> Expected effect, beyond the time savings already estimated: about 70–80 % fewer noise failures (types C, E and F) and 10–15 fewer bounces per epic. Real-bug detection should stay the same or improve, because effort moves from padding to PG18 and E2E, which together caught 17 of the 39 automated real-bug catches, including every bug that depends on real PostgreSQL behaviour or on the full UI-to-API path.
