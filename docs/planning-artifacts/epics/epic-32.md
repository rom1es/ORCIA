## Epic 32: Test Pyramid Pruning, Token Economy & Anti-Bloat Tech Debt (`Stories 32.1`..`32.5`)

Cut test execution time, LLM token consumption, and test maintenance churn across the entire repository without losing real defect detection: a single token-first check runner with machine-verifiable receipts, a lean agent protocol and rules diet, combined Unit + PostgreSQL 18 coverage enforced once per story via `diff-cover`, shared PG18 test infrastructure with `pytest-xdist`, repo-wide pyramid pruning behind a coverage safety gate, and strict anti-bloat rules preventing regrowth. Locked decisions `T-D1`..`T-D11`, the KPI baseline (Epics 30–31, evaluated on Epic 33 feature stories with `Real bugs caught >= 3.0` as non-regression floor), and the evidence base are tracked in `docs/planning-artifacts/sprint-change-proposal-2026-11-27-epic-32-test-pyramid-token-economy.md` and `docs/implementation-artifacts/test-optimization-2026-11-27/`.

### Story 32.1: Token-First `agent_check.py` Runner, Worktree Receipts, Bounce Rule & Suite Quick Wins (`T-D4`, `T-D5`, `T-D6`)

As an ORCIA Maintainer orchestrating coding and verifier agents (`Winston`, `Amelia`),
I want one deterministic staged check runner (`scripts/agent_check.py`) that auto-fixes formatting silently, prints one line on success and a bounded failure digest otherwise, selects impacted existing tests, writes machine-verifiable receipts keyed by the exact worktree/toolchain state, plus the low-risk suite quick wins (container tests out of `tests/unit`, mocked network timeouts, slow contract fuzzing split, Vitest OpenAPI parse cache, duplicate `tsc` removal, environment hardening),
So that every check costs at most one agent turn, verifiers never re-run identical deterministic stages, and `tests/unit` drops from `392 s` toward `~230 s` before the infrastructure work of `32.3`.

**Lot:** 1 — Runner, Receipts & Quick Wins. **Dependencies:** `Epic 31`. **Agent:** `bmad-dev-worker` (`flash`).
**Findings covered:** `T-D4`, `T-D5`, `T-D6`; analysis `O1`, `O4`, `T2`, `T6`, `T10`.
**CAPs covered:** none (hygiene / NFR).
**Impacted files:** `scripts/agent_check.py` + `scripts/agent_check_lib/` (new, `<= 300` lines per module), `.gitignore` (`.agent_check/`), `pyproject.toml` (pytest markers `contract_fuzz`), `tests/unit/` (6 PG18 container files moved to `tests/integration/`; `test_story_19_5`, `test_story_7_0b`, `test_story_4_1a` network/CLI mocks), `tests/contract/test_openapi_contract.py`, `apps/web/src/__tests__/setup/` (OpenAPI validator parse cache), `apps/web/package.json`, `packages/ui/package.json`, `packages/api-client/package.json` (`lint` without duplicate `tsc`), testcontainers socket/port helpers, `docs/testing-strategy.md`, `.agents/rules/bmad-model-routing.md` (§6 verifier-independence amendment only).
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/32-1-token-first-agent-check-runner-receipts-and-suite-quick-wins-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** `scripts/agent_check.py {static|impact|full|all} [--files ...] [--no-skip] [--maxfail N]` executed from any worktree (auto-resolving the project `.venv` and the `pyproject.toml` `pythonpath` without manual `PYTHONPATH` prefixes)
**When** Stage 1 runs
**Then** it first applies `ruff format` + `ruff check --fix` (never `--unsafe-fixes`) on touched Python files only and prints the list of auto-fixed files, then runs `ruff check`, `ruff format --check`, `mypy --strict` (touched packages), `lint-imports`, and `export_openapi.py --check` in check-only mode, stopping at the first failing gate; each passing stage prints exactly one line `PASS [stage]: <summary> in <s>s`, and each failing stage prints every failing test/check ID (one line each), at most 3 compact tracebacks, and the path of the full log under the gitignored `.agent_check/logs/`.

**Given** Stage 2 (`impact`) with a set of touched files (default: `git diff` vs `HEAD` + untracked non-ignored)
**When** selecting tests
**Then** it runs touched test files plus existing tests selected deterministically via a static Python import graph (reverse dependencies from touched modules), FastAPI router→route-prefix mapping for HTTP tests, an always-run fast audit set, and `vitest related` for touched `apps/web` / `packages/ui` sources; `--explain` lists why each test was selected; `--maxfail` applies only here; Stage 3 (`full`) runs full `tests/unit` + `tests/evals` + `tests/security` + `tests/contract` without `--maxfail`.

**Given** a stage passing on a worktree state
**When** the runner writes `.agent_check/receipts/<stage>-<digest>.json` (digest = tracked + modified + untracked non-ignored file contents + `.venv` installed-distribution digest + `pnpm-lock.yaml` + Python/Node versions + sorted `ORCIA_*` and `PYTHONPATH` + runner source hash)
**Then** a later invocation of a deterministic stage (`static`, unit part of `full`) with an identical digest prints `SKIP [stage]: receipt <digest12>` unless `--no-skip`; any single-byte difference re-runs; integration and E2E are never skippable; and the bounce rule re-runs only the failed check when solely `docs/` changed since the failing run, else Stage 1 + Stage 2 + the failed check.

**Given** the suite quick wins
**When** running `tests/unit` and `evals + security + contract` with `--no-cov`
**Then** the 6 PG18 `DockerContainer` tests live under `tests/integration/`, DNS / OTLP / `pytest`/`ruff` subprocess waits in `test_story_19_5`, `test_story_7_0b`, `test_story_4_1a` are mocked, Schemathesis fuzzing runs only under the `contract_fuzz` marker (the OpenAPI 0-diff gate stays in the default run), Vitest parses `openapi.json` once per worker, `lint` no longer re-runs `tsc --noEmit` when `typecheck` does, testcontainers Unix sockets live under `/tmp` (no `AF_UNIX path too long`), and the measured wall times before/after are recorded in the Tech Lead report with zero test lost (moved tests still run in their new layer).

---

### Story 32.2: Agent Protocol, Small-Context Fixer, Rules Diet & Read Discipline (`T-D7`, `T-D8`, `T-D9`)

As an ORCIA Maintainer paying ~250 k tokens of re-sent context per coding turn,
I want a lean agent protocol (runner-only commands, no polling, ≤ 20-line verifier digests, small-context fixer on bounces with a story intent header), a canonical byte-bounded `AGENTS.md` rules core with role rules loaded only by their role, read discipline, a generated shared fixture & helper index, and a dev-only token report,
So that test-related turns and context size shrink measurably while agents never lose story intent or mandatory policies.

**Lot:** 2 — Agent Protocol & Rules Diet. **Dependencies:** `32.1` (dogfoods the runner). **Agent:** `bmad-dev-worker` (`flash`).
**Findings covered:** `T-D7`, `T-D8`, `T-D9`; analysis `T1`, `T2`, `T3`, `T4`, `T7`, `T9`, `O7`, `O8`, `O10`.
**CAPs covered:** none (hygiene / NFR).
**Impacted files:** `AGENTS.md`, `GEMINI.md`, `.agents/rules/*.md`, subagent definitions (`bmad-dev-worker`, `bmad-architect-worker`, `bmad-scout`, fixer), `.agent/skills/bmad-project-context/` inputs, `docs/implementation-artifacts/TECH-LEAD-REPORT-TEMPLATE.md` (flake log, token KPIs), `scripts/agent_check_lib/` (rule-size + rule-ID uniqueness + fixture-index `--check` in Stage 1), `scripts/generate_test_fixture_index.py` (new), `tests/README.md` (generated index), dev token report tool.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/32-2-agent-protocol-small-context-fixer-and-rules-diet-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** the always-on rule files (`AGENTS.md`, `GEMINI.md`, `.agents/rules/*.md`)
**When** Stage 1 runs
**Then** every rule file is `< 24,000 B` (`<= 20 KB` margin, counting expanded `@[...](...)` includes), the canonical core in `AGENTS.md` (incl. the refreshed `bmad:context` block and a short "never" list) is `<= 12 KB`, every rule ID exists exactly once across core and role files, and the `GEMINI.md` handling (pointer or removal) is chosen after verifying Antigravity deduplication and the 20,000-token always-on budget against `rules.md`, with zero `<truncated ...>` on any rule file.

**Given** a verifier bounce on a story
**When** the coordinator dispatches the small-context fixer
**Then** the fixer receives `.agent_check/story_intent.md` (written once at story start, `< 500` tokens) + failure digest + target file ranges, runs sequentially, makes one attempt per failure (≤ 3 calls per story), never edits contracts/schemas or legacy tests without an approved `B` classification, returns a structured diagnosis + partial patch on failure, and the same-root-cause 2-failure escalation to `pro` takes strict priority.

**Given** coding, fixer, verifier, and architect role briefs
**When** agents read code and run checks
**Then** briefs mandate runner-only check commands (no chained shell one-liners, no `manage_task` polling, no loosened E2E selectors/timeouts), symbol or line-range reads (line-range only on `generated/` and lockfiles; `grep -n` + bounded read for files edited in-session; read the exact target before editing), a generated `tests/README.md` fixture & helper index validated by `--check` in Stage 1, and a dev-only token report (transcript path via env var, never in CI) recording turns / billed tokens / activity breakdown in Tech Lead report §3.

---

### Story 32.3: Combined Unit + PG18 Coverage, `diff-cover`, Shared PG18 & App Fixtures, `pytest-xdist` & `lint_tests.py` Ratchet (`T-D1`, `T-D2`, `T-D10`)

As an ORCIA Maintainer,
I want coverage measured on Unit + real PostgreSQL 18 integration combined and enforced once per story on changed lines via `diff-cover`, canonical shared test fixtures (seeded app, lifespan runner, typed PG18 seeds, session PG18 + per-worker template databases), parallel `pytest-xdist` execution, lazy heavy imports, validated impact selection, and `scripts/lint_tests.py` in ratchet mode,
So that SQL code is covered by real PG18 instead of fake engines, `tests/unit` runs `<= 120 s`, and no new test bloat appears while pruning proceeds.

**Lot:** 3 — Coverage Policy & Shared Test Infrastructure. **Dependencies:** `32.2` (dogfoods the new rules). **Agent:** `bmad-dev-worker` (`flash`).
**Findings covered:** `T-D1`, `T-D2`, `T-D10` (ratchet); analysis `O2`, `O3`, `O7` (recall), Phase 3 levers.
**CAPs covered:** none (hygiene / NFR).
**Impacted files:** `docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24/ARCHITECTURE-SPINE.md` (`pytest-xdist`, `diff-cover`, `AD-17` coverage policy), `docs/testing-strategy.md`, `pyproject.toml` (`[tool.coverage]`), `tests/conftest.py`, `tests/integration/conftest.py` (new), `tests/unit/conftest.py`, `apps/api/src/orcia_api/main.py` & heavy modules (lazy imports), `scripts/agent_check_lib/` (Stage 3 `coverage combine` + `diff-cover`), `scripts/lint_tests.py` (new) + baseline allow-list.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/32-3-combined-coverage-diff-cover-shared-pg18-infra-and-ratchet-lint-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** Stage 3 of `agent_check.py`
**When** a story completes
**Then** unit and impacted PG18 integration suites run under `coverage run --parallel-mode` (never `pytest --cov` with testcontainers), are merged with `coverage combine`, and `diff-cover` enforces `>= 90 %` on changed lines once; the `greenlet` concurrency decision is backed by a measured with/without comparison on the PG18 suite recorded in the Tech Lead report; `lint_spine.py` passes with the spine listing `pytest-xdist` and `diff-cover`.

**Given** the shared test infrastructure
**When** running `tests/unit` with `pytest-xdist -n 4 --dist loadfile` and integration with a session-scoped PG18 + Redis + SeaweedFS topology
**Then** canonical `create_seeded_test_app()`, `run_with_lifespan()`, typed seed helpers (`seed_org_workspace_admin()`, `activate_pack_with_slots()`), a session-scoped app fixture, and a cached repo AST/file index replace per-file duplicates; each xdist worker gets its own template database (`CREATE DATABASE ... TEMPLATE`), DBOS system database, Redis DB index, and S3 bucket prefix; `import orcia_api.main` drops from `7.7 s` toward `<= 4 s`; and `tests/unit` wall time is `<= 120 s`.

**Given** `scripts/lint_tests.py` in ratchet mode (Stage 1) and the impact selector
**When** new or modified tests are checked
**Then** new fake SQL engines in `tests/unit`, new `test_story_*` files (traceability via `@pytest.mark.story`), removed assertions in pre-existing tests without a redundancy-audit entry, and unguarded `workspace_id` / `run_id` routes fail, while existing violations are listed in a shrinking allow-list; the impact selector's recall is validated by replaying the Epic 30–31 `A2` / `B` episodes and recorded in the report.

---

### Story 32.4: Repo-Wide Test Pyramid Pruning with Coverage Safety Gate & Mutation Sample (`T-D11`)

As an ORCIA Maintainer,
I want a deterministic per-test coverage-context audit (Unit + PG18 combined) across all layers and safe pruning of zero-unique-contribution tests, fake-SQL harnesses, mock tautologies, scattered guard duplicates, duplicate PG18 scenarios, brittle structural Vitest tests, and E2E validation permutations,
So that the pyramid keeps exactly one owner layer per behavior with zero loss of real business or security branch coverage.

**Lot:** 4 — Repo-Wide Pruning. **Dependencies:** `32.3`. **Agent:** `bmad-dev-worker` (`flash`) + dedicated `bmad-architect-worker` (`pro`) pruning review.
**Findings covered:** `T-D11`; analysis audits of Epics 30–31 (padding 21–37.5 %, duplicates 11–18 %).
**CAPs covered:** none (hygiene / NFR).
**Impacted files:** `tests/unit/`, `tests/unit/packs/`, `tests/security/`, `tests/contract/`, `tests/integration/`, `apps/web/src/__tests__/`, `packages/ui/src/__tests__/`, `apps/web/e2e/`, `scripts/test_redundancy_audit.py` (new), `docs/implementation-artifacts/test-optimization-2026-11-27/` (audit reports).
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/32-4-repo-wide-test-pyramid-pruning-with-coverage-safety-gate-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** `coverage run` with `dynamic_context = test_function` over Unit + PG18 integration
**When** `scripts/test_redundancy_audit.py` computes each test's unique branch contribution
**Then** tests with zero unique contribution, all fake-SQL harnesses (with any needed coverage moved to PG18), and mock-tautology tests are deleted; repetitive guard checks (`ScopeAccessGuard`, `READ_ONLY_OBSERVER -> 403`, `ERR_PACK_SLOT_UNBOUND`, anti-hostage `409`) become compact table-driven `@pytest.mark.parametrize` suites; duplicate PG18 vertical scenarios merge by domain aggregate; brittle Vitest structural assertions (exact DOM counts, CSS classes, raw copy) are removed; and E2E `400/422` permutations move to FastAPI + PG18 integration tests.

**Given** the pruning safety gate
**When** comparing before/after
**Then** combined (Unit + PG18) branch coverage shows zero loss on production business/security branches, every test with a recorded real-defect catch (`A`/`A2` list) is preserved, a one-off mutation sample on pruned modules kills at least as many mutants as before, the dedicated Architect review approves the deletion list, and the report records deleted test lines, wall time, and tokens per layer.

---

### Story 32.5: Strict Anti-Bloat Lint, OpenAPI-Generated Vitest Mocks, `i18n-and-shell` Survivor Split, Budgets & Epic 32 Closure (`T-D2`, `T-D3`, `T-D10`)

As an ORCIA Maintainer and Product Owner,
I want `lint_tests.py` strict (empty allow-list), hand-maintained Vitest mock handlers replaced by in-house deterministic OpenAPI-generated mocks (stateful overrides only), the surviving `i18n-and-shell.test.tsx` split per route, test-time budgets enforced, and Epic 32 closed under the new epic review protocol,
So that the pyramid cannot regrow bloat and future epics inherit the lean, token-first testing step.

**Lot:** 5 — Strict Rules, Mocks & Closure (final story). **Dependencies:** `32.4`. **Agent:** `bmad-dev-worker` (`flash`) + `bmad-architect-worker` (`pro`) epic review at story start + diff-only review at story end.
**Findings covered:** `T-D2`, `T-D3`, `T-D10` (strict); analysis `O5`, `O6`, Phase 4 budgets.
**CAPs covered:** none (hygiene / NFR).
**Impacted files:** `scripts/lint_tests.py`, `apps/web/src/__tests__/setup/` (generated mock factories), `scripts/generate_vitest_openapi_mocks.py` (new), `apps/web/src/__tests__/i18n-and-shell*.test.tsx`, `tests/unit/test_e2e_sql_coverage_audit.py`, `docs/testing-strategy.md`, `docs/implementation-artifacts/sprint-status.yaml`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/32-5-strict-anti-bloat-lint-openapi-vitest-mocks-and-survivor-split-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** `lint_tests.py` with an empty allow-list and the OpenAPI mock generator (`--check` in Stage 1)
**When** Stage 1 runs on the repository
**Then** zero anti-bloat violations remain, Vitest default responses come from deterministic schema examples generated from `openapi.json` (hand-written handlers limited to stateful overrides), `i18n-and-shell.test.tsx` survivors are split into route-scoped files `<= 300` lines, exact-count assertions are removed from `test_e2e_sql_coverage_audit.py`, and budgets hold (`tests/unit <= 120 s`, `evals + security + contract <= 45 s`, no unit test `> 1 s` outside an allow-list).

**Given** the Epic 32 closure (`--no-skip` full verification)
**When** the epic-level Architect review (at story start) and the diff-only review (at story end) complete
**Then** all `AD-17` gates pass through `agent_check.py` without receipt skipping, the KPI instrumentation is ready for Epic 33 evaluation against the locked baseline (`Real bugs caught >= 3.0` floor), and `epic-32` transitions to `done`.
