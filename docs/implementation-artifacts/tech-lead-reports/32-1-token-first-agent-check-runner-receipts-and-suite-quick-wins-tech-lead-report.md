# Story 32.1 — Token-First `agent_check.py` Runner, Worktree Receipts, Bounce Rule & Suite Quick Wins

- **Date**: 2026-11-27
- **Story / Sprint Key**: `32-1-token-first-agent-check-runner-receipts-and-suite-quick-wins` (`Epic 32` / Lot 1)
- **Capability(ies)**: `none (hygiene/NFR)` — classification: `hygiene`
- **Author / Context**: `T-D4`, `T-D5`, `T-D6` from `docs/planning-artifacts/sprint-change-proposal-2026-11-27-epic-32-test-pyramid-token-economy.md` and profiling evidence in `docs/implementation-artifacts/test-optimization-2026-11-27/06-profiling-epic31-head.md` & `04-token-economy-challenge-review.md`
- **Associated Commits**: *(pending completion)*

---

## 1. Needs Analysis & Tech Lead Impact Study (Pre-Implementation)

### 1.1 Context & Problem Statement
- Across Epics 30–31, test execution consumed 40–45% of agent wall time (`tests/unit` grew to `391.61 s`, `evals+security+contract` to `137.47 s`) and test-related turns consumed 39–43% of billed input tokens (~250 k tokens/turn). Agents run unstandardized chained commands, repeat static/unit runs when nothing deterministic changed, and trigger slow infrastructure/network paths inside `tests/unit`.
- **Expected behavior**:
  1. One canonical check runner (`scripts/agent_check.py` + `scripts/agent_check_lib/`) auto-resolving `.venv` and `pyproject.toml` `pythonpath`, supporting `static | impact | full | all | fuzz` (`--files`, `--no-skip`, `--maxfail N`, `--explain`), auto-fixing touched Python files via `ruff format` / `ruff check --fix` (no `--unsafe-fixes`) with `AUTOFIXED:` output, emitting one line on `PASS` / `SKIP` and a bounded failure digest (every failing ID, ≤ 3 compact tracebacks, `LOG:` path) from `--junitxml` / Vitest JSON on `FAIL`.
  2. Deterministic worktree receipts under `.agent_check/receipts/<stage>-<digest>.json` keyed by tracked blob IDs, modified/untracked non-ignored contents, `.venv` installed distributions, `pnpm-lock.yaml`, Python/Node versions, hashed `ORCIA_*` vars, `PYTHONPATH`, and runner source hash; plus the bounce rule (`docs/`-only edits re-run only the failed check; anything else re-runs Stage 1 + Stage 2 + failed check).
  3. Suite quick wins: extract the 6 PG18 `DockerContainer` migration tests from `tests/unit/` into `tests/integration/`; mock DNS (`down-host.local`), OTLP shutdown export (`.orcia.local:4318`), and `pytest`/`ruff` subprocess spawns in `test_story_19_5`, `test_story_7_0b`, and `test_story_4_1a`; isolate Schemathesis fuzzing behind `@pytest.mark.contract_fuzz`; parse/compile `openapi.json` once per Vitest worker; remove duplicate `tsc --noEmit` from workspace `lint` scripts; ensure testcontainers Unix sockets live under `/tmp`; document the runner in `docs/testing-strategy.md` and amend `.agents/rules/bmad-model-routing.md` §6 for receipt skipping.

### 1.2 Exploration, GitNexus Impact Analysis, Refactoring & Technical Debt
- **GitNexus Impact Analysis (`gitnexus_query`, `gitnexus_impact` on `repo: /home/romain/Documents/Projects/ORCIA`)**:
  - `post_pinned_embedding_json` (`packages/orcia-core/src/orcia_core/rag/adapters/embedding_httpx_helpers.py`): 8 upstream callers (`HttpxOpenAiCompatibleEmbeddingAdapter`, `HttpxGeminiNativeEmbeddingAdapter`), `risk: LOW`. It invokes `prepare_pinned_http_request` → `resolve_and_pin_safe_endpoint_url` → `socket.getaddrinfo`, causing 2 × 5 s DNS timeouts on `down-host.local` in `test_story_19_5_embedding_port_and_adapters.py` (measured baseline: `10.09 s`). Mocking `socket.getaddrinfo` in that unit test preserves adapter behavior without touching production SSRF pinning.
  - `shutdown_tracing` (`packages/orcia-core/src/orcia_core/observability/tracing.py`): `OTLPSpanExporter.export` causes a 6.42 s network/DNS wait during `BatchSpanProcessor.shutdown()` on `http://otel-collector.orcia.local:4318` in `test_story_7_0b_log_sink_and_otel_tracing.py`. Mocking `OTLPSpanExporter.export` in that test preserves `TracerProvider` / `InMemorySpanExporter` / `_BrokenProvider` behavior.
  - `BimodalSandboxAdapter` / `ContainerSandboxRunner` (`packages/orcia-core/src/orcia_core/gates/tier2_sandbox.py`): `test_story_4_1a_bimodal_sandbox_and_roles.py` measured `8.09 s + 4.55 s + 4.47 s` due to child `pytest`/`ruff` subprocesses in `tdd_red_green`. Stubbing only the child `pytest`/`ruff` `subprocess.run` inside `tier2_runner.py` via a test-only shim keeps `ContainerSandboxRunner.execute`, `python -I` process creation, network/FS jails, CAS reading, and exit-code handling genuinely exercised.
  - `validateRequestAgainstOpenApi` (`apps/web/src/__tests__/setup/openApiRequestValidator.ts`): loaded `packages/api-client/openapi.json` (2.1 MB) and compiled path regexes at top-level import on every Vitest file (`7.02 s` setup on single file baseline `8.79 s`). Lazy worker-scoped caching on `globalThis[Symbol.for(...)]` avoids repeated parses per worker, and splitting `openApiSchemaChecker.ts` keeps both setup files `<= 230` lines.
- **Exploration & Key Metrics**:
  - The 6 PG18 files in `tests/unit/` (`3_2e`, `3_4`, `3_5`, `4_1`, `4_4`, `5_1`) all mix pure unit/API tests (including `app.state.*` overrides in `3_4`, `3_5`, `5_1`) with one `DockerContainer("pgvector/pgvector:pg18")` migration test each. Splitting **only** the 6 PG18 migration tests into 2 domain-named files under `tests/integration/db/` (`test_alembic_migrations_core_pg18.py` and `test_alembic_migrations_governance_pg18.py`) preserves pure unit tests in `tests/unit/`, keeps `capabilities.yaml` test references valid, and complies with `test_integration_no_manual_app_state_audit.py`.
  - Baseline timings measured pre-change:
    - `test_story_19_5_embedding_port_and_adapters.py::test_httpx_embedding_adapters_edge_cases_and_network_errors`: `10.09 s`
    - `test_story_7_0b_log_sink_and_otel_tracing.py::test_otel_tracing_config_and_structlog_span_correlation`: `6.42 s`
    - `test_story_4_1a_bimodal_sandbox_and_roles.py`: `8.09 s` + `4.55 s` + `4.47 s`
    - `tests/contract/test_openapi_contract.py::test_schemathesis_openapi_contract_compliance`: `42.33 s` (`test_openapi_client_zero_diff_gate`: `8.64 s`)
    - `apps/web/src/__tests__/vitest-transport-fail-closed-openapi.test.ts`: `8.79 s` (`setup 7.02 s`)
  - Older integration files (`test_real_containers.py`, `test_story_3_2b`, `3_2c`, `3_2s`, `11_4`, `11_5`) place sockets/dirs under `REPO_ROOT / ".pytest_cache" / ...`, which exceeds the 107-byte `AF_UNIX` limit in worktrees.
- **Refactoring Opportunities & Emerging Technical Debt Mitigation**:
  - Extract shared `prepare_tc_sock_dir` and `open_pg18_alembic_container` helpers in `tests/integration/_tc_socket_helpers.py` targeting `/tmp` (`tempfile.gettempdir()`) reused by both domain-named PG18 migration files and updated legacy integration tests.
  - Keep every `scripts/agent_check_lib/*.py` module strictly `<= 300` lines.

---

## 2. Implementation Plan

### 2.1 Data Schema & Alembic Migrations
- None (`hygiene` story; existing Alembic tests `0013..0021` are relocated unchanged in behavior from `tests/unit/` to `tests/integration/db/`).

### 2.2 Hexagonal Core, Orchestration & Runner Tooling (`scripts/agent_check.py`, `scripts/agent_check_lib/`)
- `scripts/agent_check.py` (`<= 150` L): thin CLI entrypoint (`static | impact | full | all | fuzz`, `--files`, `--no-skip`, `--maxfail`, `--explain`).
- `scripts/agent_check_lib/` (all modules `<= 300` L):
  - `env.py`: auto-resolve `.venv` (`ORCIA_VENV` fallback), `pnpm`, `node`, and `PYTHONPATH` from `pyproject.toml` `[tool.pytest.ini_options].pythonpath`.
  - `changes.py`: detect git working-tree + untracked non-ignored changes (or `--files`), plus file-content snapshot comparison for the bounce rule.
  - `receipts.py`: compute deterministic SHA-256 worktree+toolchain+env digest (including `scripts/agent_check.py` + all sorted `scripts/agent_check_lib/*.py`), read/write `.agent_check/receipts/<stage>-<digest>.json`, and manage `.agent_check/state/last_failure.json` for the bounce rule (`SKIPPABLE_STAGES`: `static`, `full-unit`, `full-vitest`).
  - `output.py`: parse pytest `--junitxml` and Vitest JSON reports + static tool outputs into the strict token-first digest (`PASS`/`SKIP`/`FAIL`, all failing IDs one per line, ≤ 3 compact tracebacks, `LOG:` path).
  - `impact.py`: static `ast` Python import graph over `pythonpath` roots + `tests/`, FastAPI router prefix/path literal mapping to HTTP tests, fast always-run audit set (`<= 30 s`), and `vitest related` invocation list with `--explain` reasons (excluding slow `tests/integration/` container suites).
  - `static_gates.py`: Stage 1 gate builders (`ruff check`, `ruff format --check`, touched `mypy --strict`, `lint-imports`, `export_openapi.py --check`, touched TS `lint` + `typecheck` or all on `--no-skip`, `lint_spine.py`, and `detect-secrets-hook` on touched files with graceful warn if `.secrets.baseline` absent) + `autofix_touched_python`.
  - `runner_exec.py` & `stages.py`: Stage 1 (`static`: autofix first, then compute post-autofix digest before check-only gates), Stage 2 (`impact`: `--maxfail` supported), Stage 3 (`full`: skippable `full-unit` + `evals security contract` without `--maxfail` + skippable `full-vitest` + `check_implementation_docs.py` + `pnpm site:check`, clean extension point for `32-3-combined-coverage-diff-cover-shared-pg18-infra-and-ratchet-lint`), and `fuzz` (`tests/contract -m contract_fuzz`).
- `.gitignore`: ignore `.agent_check/`.
- `pyproject.toml`: register `contract_fuzz` pytest marker under `[tool.pytest.ini_options].markers`.
- Suite quick wins:
  - Move the 6 PG18 `DockerContainer` migration tests into 2 domain-named files `<= 300` lines each: `tests/integration/db/test_alembic_migrations_core_pg18.py` (`0013_0014`, `0015`, `0016`) and `tests/integration/db/test_alembic_migrations_governance_pg18.py` (`0017`, `0019_0020`, `0021`) using `tests/integration/_tc_socket_helpers.py` under `/tmp`.
  - Update `test_real_containers.py`, `test_story_3_2b`, `3_2c`, `3_2s`, `11_4`, `11_5` to use `prepare_tc_sock_dir` under `/tmp`.
  - Mock DNS (`socket.getaddrinfo`) in `test_story_19_5`, OTLP export (`OTLPSpanExporter.export`) in `test_story_7_0b`, and stub only child `pytest`/`ruff` `subprocess.run` inside `tier2_runner.py` via `tests/unit/fakes/sandbox_tdd_fake.py` in `test_story_4_1a`.
  - Mark `test_schemathesis_openapi_contract_compliance` with `@pytest.mark.contract_fuzz`.

### 2.3 Backend API, Security & Contracts
- No API schema or route changes (`0-diff` preserved).

### 2.4 User Interface, Package Scripts & Documentation (`apps/web/`, `packages/`, `docs/`, `.agents/rules/`)
- `apps/web/src/__tests__/setup/openApiRequestValidator.ts` + `openApiSchemaChecker.ts`: split `<= 230` L each and cache parsed `openapi.json`, schemas, and compiled path entries lazily on `globalThis[Symbol.for("orcia.vitest.openApiValidatorCache")]` once per Vitest worker.
- `apps/web/package.json`, `packages/ui/package.json`, `packages/api-client/package.json`: remove duplicate `tsc --noEmit` from `lint` scripts (keeping `check-feature-boundaries.mjs` in `apps/web` and silent no-op in `packages/ui` & `packages/api-client` so `pnpm turbo run lint typecheck test` preserves task graph semantics).
- `docs/testing-strategy.md`: add Section 8 ("Agent Check Runner (`scripts/agent_check.py`)") covering stages, output contract, receipts, bounce rule, and banning chained one-liners.
- `.agents/rules/bmad-model-routing.md`: amend §6 solely to allow verifier skip on matching deterministic `agent_check.py` receipts for standard stories while requiring `--no-skip` on the final story of an epic.

### 2.5 Test Pyramid Impact Analysis (`AD-17` — Layers 1 to 5 + Security, Mandatory)
- **Layer 1a (`tests/unit/`)**: new domain-named runner tests under `tests/unit/tooling/` (`test_agent_check_receipts_and_bounce.py`, `test_agent_check_output_and_impact.py`, `test_agent_check_stages.py`) using temp git repos/fixtures; re-run `test_story_19_5`, `test_story_7_0b`, `test_story_4_1a`, and the 6 trimmed `tests/unit/test_story_*` files (`--no-cov`).
- **Layer 1b (`Vitest`)**: re-run `apps/web/src/__tests__/vitest-transport-fail-closed-openapi.test.ts` and `runtime-env-guard-audit.test.ts`, plus `pnpm --filter @orcia/web run lint typecheck`.
- **Layer 2 (`tests/integration/`)**: verify `test_integration_no_manual_app_state_audit.py` passes and run the 2 domain-named PG18 migration files (`6` tests) under `tests/integration/db/` (`--no-cov`).
- **Layer 3 (`tests/contract/`)**: verify `test_openapi_contract.py -m "not contract_fuzz"` runs only `test_openapi_client_zero_diff_gate`.
- **Layer 4 (`tests/evals/`) & Security (`tests/security/`)**: untouched; executed by Testing Verifier.
- **Layer 5 (`apps/web/e2e/`)**: untouched (`hygiene` story; no UI runtime behavior altered).

---

## 3. Summary of Changes & Results (Closed — Independent Testing Verifier Verified)

### 3.1 Created & Modified Files
| File | Action | Concise Summary |
| :--- | :--- | :--- |
| `scripts/agent_check.py` | Created (`74` L) | Thin CLI (`static \| impact \| full \| all \| fuzz`, `--files`, `--no-skip`, `--maxfail`, `--explain`). |
| `scripts/agent_check_lib/*.py` | Created (`9` modules, `<= 275` L each) | `env.py` (`111` L), `changes.py` (`104` L), `receipts.py` (`232` L), `output.py` (`128` L), `impact.py` (`206` L), `runner_exec.py` (`178` L), `static_gates.py` (`148` L), `stages.py` (`275` L), `__init__.py` (`3` L). |
| `tests/unit/tooling/*.py` | Created (`5` test files + `__init__.py`, `<= 284` L each) | `test_agent_check_receipts_and_bounce.py` (`176` L), `test_agent_check_output_and_impact.py` (`164` L), `test_agent_check_stages.py` (`132` L), `test_agent_check_runner_exec_and_gates.py` (`218` L), `test_agent_check_stages_and_edge_cases.py` (`284` L) — 21 unit tests covering env/PYTHONPATH, digest determinism, 1-byte invalidation, bounce rule, JUnit/Vitest parsing, AST/router impact, Stage 1/3 behavior, and edge cases. |
| `.gitignore`, `pyproject.toml` | Modified | Added `.agent_check/` ignore and registered `contract_fuzz` marker. |
| `tests/integration/_tc_socket_helpers.py` | Created (`68` L) | Shared `/tmp` testcontainers socket & Alembic PG18 helper preventing `AF_UNIX` > 107 B. |
| `tests/integration/db/test_alembic_migrations_{core,governance}_pg18.py` | Created (`145`, `146` L) | Relocated the 6 PG18 Alembic migration tests (`0013..0021`) into 2 domain-named files. |
| `tests/unit/test_story_{3_2e,3_4,3_5,4_1,4_4,5_1}_*.py` | Modified | Extracted the 6 PG18 `DockerContainer` migration functions while retaining pure unit/API tests. |
| `tests/integration/test_{real_containers,story_3_2b,3_2c,3_2s,11_4,11_5}_*.py` | Modified | Switched `.pytest_cache` socket/volume dirs to `prepare_tc_sock_dir` under `/tmp`. |
| `tests/unit/test_story_{19_5,7_0b,4_1a}_*.py` + `tests/unit/fakes/sandbox_tdd_fake.py` | Modified / Created (`80` L) | Mocked DNS (`getaddrinfo`), OTLP export, and child `pytest`/`ruff` `subprocess.run` inside `tier2_runner.py`, plus isolated OTel global `HTTPXClientInstrumentor` / `TracerProvider` state in `test_story_7_0b`. |
| `tests/contract/test_openapi_contract.py` | Modified | Tagged `test_schemathesis_openapi_contract_compliance` with `@pytest.mark.contract_fuzz`. |
| `apps/web/src/__tests__/setup/openApi{RequestValidator,SchemaChecker}.ts` | Modified / Created (`227`, `156` L) | Lazy worker-scoped `openapi.json` + compiled path cache on `globalThis`. |
| `{apps/web,packages/ui,packages/api-client}/package.json` | Modified | Removed duplicate `tsc --noEmit` from `lint` scripts. |
| `docs/testing-strategy.md`, `.agents/rules/bmad-model-routing.md` | Modified | Documented `agent_check.py` (§8) and receipt-skip policy for verifiers (§6). |

### 3.2 Measured Before/After Wall-Time Comparison & Runner Checks
| Suite / Check | Epic 31 Baseline | Story 32.1 Measured | Delta |
| :--- | :--- | :--- | :--- |
| Full `tests/unit` (`--no-cov`) | `391.61 s` | `333.05 s` (`1,323 passed` via `agent_check.py full --no-skip`) | **−58.56 s (−15.0%)** |
| `tests/evals tests/security tests/contract -m "not contract_fuzz"` | `137.47 s` | `97.00 s` (`198 passed, 1 deselected`) / `101.67 s` in `full` | **−40.47 s (−29.4%)** |
| `pnpm turbo run lint typecheck test --concurrency=2` | — | `79.02 s` (`9/9` tasks; Vitest: `@orcia/ui` `41/159` `12.74 s`, `@orcia/api-client` `4/23` `1.14 s`, `@orcia/web` `98/375` `56.12 s` = **`557` JS/TS tests**; `70.39 s` via `full-vitest`) | Clean |
| Relocated PG18 migrations + audit | Inside `tests/unit` | `8/8 passed` (`test_integration_no_manual_app_state_audit.py` + `test_alembic_migrations_{core,governance}_pg18.py`) | Isolated in `tests/integration/db/` |
| `agent_check.py static --no-skip` → `static` | N/A | `PASS [static]: 13 gates in 54.67s` (then `61.71s`) → `SKIP [static]: receipt 5a02fc131247` (`< 1s`) | Deterministic receipt hit |
| `agent_check.py impact --explain` | N/A | `PASS [impact]: 18 py + 3 vitest pkg(s) in 103.55s` | AST + router + `vitest related` |

- **Quick-win micro-timings (Coding local `--no-cov --durations=0`)**:
  - `test_story_19_5` (`test_httpx_embedding_adapters_edge_cases_and_network_errors`): `10.09 s` → `0.06 s` (**−10.03 s**)
  - `test_story_7_0b` (`test_otel_tracing_config_and_structlog_span_correlation`): `6.42 s` → `0.12 s` (**−6.30 s**)
  - `test_story_4_1a` (3 tests, keeping real `ContainerSandboxRunner.execute`): `17.11 s` → `1.47 s` (**−15.64 s**)
  - `tests/contract/test_openapi_contract.py -m contract_fuzz --collect-only`: collects `test_schemathesis_openapi_contract_compliance` (`1/2` tests collected).

### 3.3 AD-17 Full Verification & Closure Gates
- **Line-count hygiene**: All newly created `.py`/`.ts`/`.tsx` files `<= 284` L (`stages.py` `275` L, `test_agent_check_stages_and_edge_cases.py` `284` L, `openApiRequestValidator.ts` `227` L, `openApiSchemaChecker.ts` `156` L); pre-existing `>300` L unit/integration test files had net-negative diffs from test extraction/cleanup.
- **Scoped branch coverage (`scripts/agent_check_lib/`)**: `.venv/bin/coverage run --branch --source=scripts/agent_check_lib -m pytest --no-cov -q tests/unit/tooling/` → **`21 passed`**, **`93%`** total branch coverage (`743` stmts, `26` miss, `272` branches, `39` partial; `--fail-under=90` passed, `.coverage*` cleaned).
- **Stage 3 (`scripts/agent_check.py full --no-skip`)**:
  - `PASS [full-unit]: 1 target(s) in 333.05s`
  - `PASS [full]: 3 target(s) in 101.67s`
  - `PASS [full-vitest]: 3 pkg(s) in 70.39s`
  - `PASS [full-docs-site]: 2 checks in 1.97s`
- **Docs, Showcase & GitNexus Closure**:
  - `pnpm site:sync && pnpm site:check`: clean (`255` tech-lead reports, `66/66` capabilities, `20/20` UJs, `63/63` E2E).
  - `.venv/bin/python scripts/check_implementation_docs.py`: clean.
  - `npx gitnexus analyze --index-only .`: `50,382` nodes | `87,002` edges | `875` clusters | `1,534` flows (`59.4s`).
  - `gitnexus_detect_changes(repo="/home/romain/.gemini/antigravity/worktrees/ORCIA/epic30_test_duration_optimization", scope="all")`: `changed_count: 9`, `affected_count: 0`, `changed_files: 28`, `risk_level: "low"`.
