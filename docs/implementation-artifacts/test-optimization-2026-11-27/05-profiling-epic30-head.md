# ORCIA Test & Gate Duration Profiling Report (HEAD `cf36f3c`)

## 1. Suite Inventory & Baseline Timings

| Suite | Files | Tests | Collect Time | Run Wall Time | Notes |
| --- | ---: | ---: | ---: | ---: | --- |
| `tests/unit` | 194 | 1,154 | 18.04 s | **322.50 s** (5m22s) | Measured sum of phase durations: 294.57 s (`EXIT=0`) |
| `tests/evals` | 8 | 56 | 7.88 s | *(in combined)* | All individual phases `< 1.3 s` |
| `tests/security` | 26 | 135 | 7.98 s | *(in combined)* | Dominated by `create_app()` / `TestClient` boots |
| `tests/contract` | 1 | 2 | 7.62 s | *(in combined)* | **57.45 s** (`test_openapi_contract.py` alone) |
| `evals + security + contract` | 35 | 193 | — | **128.13 s** (2m08s) | `contract` = 44.8% of total wall time (`EXIT=0`) |
| `tests/integration` | 84 | 117 | 14.86 s | *(1 file: 27.19 s)* | 76 `.py` files invoke `testcontainers`; 0 session fixtures |
| `@orcia/web` (Vitest) | 95 | 369 | *(215.50 s CPU)* | **58.07 s** | Vitest `56.49 s`: `setup` 346.3 s, `tests` 292.5 s, `env` 121.3 s CPU |
| `@orcia/ui` (Vitest) | 40 | 154 | *(105.20 s CPU)* | **14.48 s** | Vitest `13.07 s`: `env` 50.8 s, `tests` 33.7 s CPU |

## 2. Why `tests/unit` Takes 322.5 s (Category Breakdown & Top Slow Files)

| Category | Time (sum) | Files | Root Cause |
| --- | ---: | ---: | --- |
| `create_app()` + `TestClient` boots | **129.12 s** | 68 | **118** `create_app()` calls in `tests/unit` (+26 in `evals/security/contract`), each re-running `initialize_app_services()`, `activate_sdlc_pack()`, and mounting ~46 routers |
| AST / repo-wide filesystem audits | **73.42 s** | 26 | Repeated full-repo `rglob("*.py")` / `rglob("*.ts*")` + `ast.parse()` across 26 files, plus `create_app()` / `git` subprocesses |
| Testcontainers (PG18) inside `tests/unit` | **45.73 s** | 6 | `test_story_3_2e`, `3_4`, `3_5`, `4_1`, `4_4`, `5_1` boot real `pgvector/pgvector:pg18` Docker containers + run `alembic` migrations |
| Subprocess Python / CLI spawns | **23.07 s** | 1+ | Fresh Python subprocesses re-paying the **6.0 s** `import orcia_api.main` tax + CLI script checks (`test_platform_auth_policy...`) |
| Real network / DNS / OTLP / CLI timeouts | **~29.0 s** | 3 | DNS lookup (`down-host.local` in `19_5`, **10.08 s**), OTLP flush (`otel-collector.orcia.local` in `7_0b`, **8.19 s**), real `pytest`/`ruff` subprocess (`4_1a`, **10.75 s**) |
| Pure unit tests (remaining ~50 files) | **< 5 s** | ~50 | Fast in-memory unit logic |

**Top 15 Slowest `tests/unit` Files:**
1. `test_platform_auth_policy_2fa_and_runtime_isolation.py` — **23.07 s** (6 tests; `subprocess.run` importing `orcia_api.main` + maintenance scripts)
2. `test_story_26_10_epic_26_closure_ast_and_routes_audit.py` — **14.45 s** (6 tests; multiple `create_app()` + full-repo AST/TS walks)
3. `test_i18n_backend_catalog_and_english_dev_audit.py` — **12.95 s** (3 tests; full-repo AST + `git diff`/`git ls-files` subprocesses)
4. `test_openapi_security.py` — **11.50 s** (3 tests; `create_app()` + full `app.openapi()` schema build)
5. `test_story_4_1a_bimodal_sandbox_and_roles.py` — **10.75 s** (3 tests; `verify_tdd_red_green` spawns real `pytest` + `ruff`)
6. `test_story_7_0b_log_sink_and_otel_tracing.py` — **10.53 s** (4 tests; `shutdown_tracing` OTLP timeout to `.local:4318`)
7. `test_story_19_5_embedding_port_and_adapters.py` — **10.12 s** (5 tests; `_post_pinned_embedding_json` triggers real DNS lookup on `down-host.local`)
8. `test_story_3_4_human_anchors_and_arbitration.py` — **8.92 s** (4 tests; PG18 `DockerContainer` + `create_app()`)
9. `test_story_3_5_challenge_and_replay.py` — **7.97 s** (5 tests; PG18 `DockerContainer` + `create_app()`)
10. `test_story_5_1_notifications_claim_and_resource_leases.py` — **7.50 s** (3 tests; PG18 `DockerContainer` + `create_app()`)
11. `test_story_30_3_workflows_and_bridge_coverage.py` — **7.45 s** (4 tests; repeated `create_app()` + `TestClient`)
12. `test_story_3_2e_sdlc_pack_and_connectors.py` — **7.17 s** (3 tests; PG18 `DockerContainer` + `alembic` + subprocess)
13. `test_story_4_1_sandbox_tier1_and_pattern_drift.py` — **7.11 s** (4 tests; PG18 `DockerContainer` + `create_app()`)
14. `test_story_4_4_jira_staged_actions_and_mcp.py` — **7.06 s** (2 tests; PG18 `DockerContainer`)
15. `test_story_26_9_duplicate_thread_turn_removal.py` — **6.84 s** (2 tests; `create_app()` + `app.openapi()`)

## 3. `tests/evals`, `tests/security`, `tests/contract` (128.13 s)

- **Zero duplicate test names** across `tests/unit` vs `evals`/`security`/`contract` (no double execution).
- **Top slow files**: `tests/contract/test_openapi_contract.py` **57.45 s** (`test_schemathesis_openapi_contract_compliance` **45.98 s** fuzzing every OpenAPI operation sequentially with `max_examples=5`; `test_openapi_client_zero_diff_gate` **11.46 s** running `create_app()` + `app.openapi()` + 27 TS domain shards), `test_story_26_1_assistant_security_hardening.py` **11.12 s**, `test_story_26_1_review_hardening.py` **4.70 s**, `test_story_30_6_prompt_leak_and_draft_redteam.py` **3.82 s**, `test_story_7_4_observer_and_rbac_guards.py` **3.69 s**.

## 4. Import-Time & `coverage run --branch` Bottlenecks

`python -X importtime -c "import orcia_api.main"` takes **5,990.4 ms (~6.0 s)** per fresh Python process (explaining `~7.6–8.0 s` minimum collection time even on 1-file suites):
- Top cumulative: `orcia_api.main` **5990 ms** (`self 419.5 ms`), `orcia_api.dependencies` **2302 ms**, `...assistant_tools` **2232 ms**, `..._assistant_tools_helpers` **2192 ms**, `..._assistant_guards` **1600 ms**, `..._core_providers` **1024 ms**, `orcia_core.bootstrap` **1001 ms**, `fastapi` **589 ms**, `orcia_core.orchestration` **575 ms**, `...litellm_adapter` **558 ms**, `fastapi.applications` **544 ms**, `fastapi.routing` **514 ms**, `orcia_api.middleware.trace_and_error` **420 ms**, `orcia_api.schemas.problem_details` **420 ms**, `sqlalchemy.ext.asyncio` **390 ms**.
- **Coverage timeout cause**: `[tool.coverage.run]` in `pyproject.toml` enables `branch = true` and `concurrency = ["greenlet", "thread"]` without restricting `source`. On Python 3.12, `greenlet` concurrency disables PEP 669 `sys.monitoring` and forces `sys.settrace` across FastAPI/Pydantic/SQLAlchemy. Single-file benchmark (`test_agents_and_skills_router_and_service.py`): `--no-cov` **16.88 s** vs `coverage run --branch` **23.59 s** (**+40%**, scaling past 300–600 s across router batches).

## 5. Vitest & Turborepo Profiling

- **Vitest `@orcia/web`** (**58.07 s** wall; 95 files, 369 tests): `vitest.setup.ts` runs in all 95 isolated `jsdom` workers, importing `openApiRequestValidator.ts` which eagerly reads & `JSON.parse()`s the **1.99 MB** `openapi.json` and compiles path regexes **95 times** (`setup` **346.28 s** + `env` **121.25 s** + `collect` **215.50 s** = **67%** of total CPU time).
  - Top slow files: `i18n-and-shell.test.tsx` **25.65 s** (26 tests, 2,309 lines), `zero-dead-buttons-and-silent-catches-audit.test.tsx` **8.28 s**, `story-20-1-mon-organisation...` **7.99 s**, `story-17-2-org-hierarchy...` **7.73 s**, `story-16-4-reflexive-trace...` **7.63 s**, `story-17-3-iam-accounts-matrix...` **7.37 s**, `page-header-structure...` **7.33 s**, `story-22-2-portals...` **6.98 s**, `story-25-2-shell-9-items...` **6.17 s**, `story-17-3-iam-accounts-directory...` **5.95 s**, `epics-14-15-process-studio...` **5.61 s**, `direction-c-shell...` **5.46 s**, `anti-jargon-and-secrets-ui-audit.test.ts` **5.37 s**, `story-20-3-sidebar-account...` **5.14 s**, `story-25-5-assistant-unlocked...` **4.95 s**.
- **Vitest `@orcia/ui`** (**14.48 s** wall; 40 files, 154 tests): `four-zone-shell-and-cockpit.test.tsx` **3.29 s**, `assistant-workspace.test.tsx` **2.77 s**, `agents-and-skills-studio...` **2.75 s**, `rgaa-modals-escape-unsaved-guard.test.tsx` **2.36 s**, `agents-and-skills.test.tsx` **2.35 s**, `story-24-4-css-modals...` **1.93 s**.
- **Turbo (`turbo.json`)**: `lint`, `typecheck`, `test` have `outputs: []` (log-only caching) and no `inputs` narrowing. On clean `HEAD`, `--dry=json` shows all 9 tasks are cache `HIT` (saving ~101 s; `@orcia/web#test` = 49.3 s). During Epic 30, every edit to `@orcia/ui` invalidated all 6 UI+Web tasks, every edit to `@orcia/web` invalidated all 3 Web tasks, and `lint` runs `tsc --noEmit` redundantly alongside `typecheck` in all 3 TS packages (`api-client`, `ui`, `web`).

## 6. PG18 Integration Timing (`test_story_30_5_..._pg18.py`)

- **27.19 s** wall (`24.39 s` pytest): **5.33 s** Docker lifecycle (`4.20 s` setup + `1.13 s` teardown for `pgvector:pg18` + `redis:7.4.2-alpine` via Unix sockets) + **12.44 s** call (`alembic upgrade head` + `create_app()` lifespan + cold re-read) + **~7 s** Python/import startup.
- **No `tests/integration/conftest.py`**, **0** `scope="session"` fixtures, **59** `scope="module"` fixtures, **48+** `alembic` subprocess invocations, `TESTCONTAINERS_RYUK_DISABLED=true`, and no `~/.testcontainers.properties` reuse configured.

## 7. `pytest-xdist` Parallelism Safety Risks

- **Env mutations without `monkeypatch`**: `tests/unit/test_no_raw_enum_codes_in_ui_streams.py`, `tests/security/test_api_security_baseline.py`, `tests/security/test_epic_18_sources_and_codegraph_security.py` mutate `os.environ[...]` directly (safe across separate xdist worker *processes*, unsafe under `pytest-run-parallel` threads).
- **Shared filesystem paths**: 6 `tests/unit/` container tests write Unix sockets to `REPO_ROOT/.pytest_cache/tc_*` (`os.getpid()` avoids collision, but Ryuk is disabled).
- **Coverage data collision**: `coverage run` without `parallel = true` / unique `--data-file` corrupts `.coverage` under `xdist`.
- **Docker pressure**: 0 fixed host ports (`with_bind_ports` = 0), but running 76 integration files across N xdist workers without a session-scoped PG/Redis fixture would spawn N× containers + Alembic runs concurrently.
- **Global singletons**: `tests/conftest.py` only sets `ORCIA_ENV=test`; `orcia_api.main` executes `app = create_app()` at import time (safe per worker process, adds 6 s to every worker boot).

## 8. Concrete Optimization Levers & Estimated Savings

| Lever | Target Suite | Est. Savings | Risk / Effort |
| --- | --- | ---: | --- |
| 1. Move 6 PG18 testcontainer tests out of `tests/unit` into `tests/integration` | `tests/unit` | **-45 s** | Low / Trivial |
| 2. Session-scoped `app` / `TestClient` (or lightweight `create_app(skip_bootstrap=...)` / router-slice fixture) instead of 118+ per-test `create_app()` calls | `tests/unit` + `security` | **-80 to -100 s** | Medium (ensure clean state reset) |
| 3. Mock DNS pinning (`post_pinned_embedding_json`) in `test_story_19_5`, set `OTEL_TRACES_EXPORTER=none` / mock exporter in `test_story_7_0b`, unit-mock `pytest`/`ruff` in `4_1a` | `tests/unit` | **-26 s** | Low |
| 4. Consolidate 26 AST/repo-audit tests into 1 cached AST/file-index fixture (`session` scope) | `tests/unit` | **-45 to -55 s** | Low–Medium |
| 5. Lazy/in-process import checks instead of `subprocess.run` in `test_platform_auth_policy...` + `test_i18n...` | `tests/unit` | **-18 s** | Low |
| 6. Enable `pytest -n auto` (`pytest-xdist`) after levers 1–5 (`tests/unit` + `security`/`evals`/`contract`) | `tests/unit` + `e/s/c` | **-60% to -75% wall** | Low (add `parallel=true` for cov) |
| 7. Split `test_schemathesis_openapi_contract_compliance` (`contract-fuzz` slow gate, or `max_examples=2` / `xdist` per tag) | `tests/contract` | **-30 to -45 s** | Low |
| 8. Narrow `--source=packages/orcia-core/src,apps/api/src,...` and drop `greenlet` from `concurrency` on non-gevent runs (unlocks Python 3.12 `sys.monitoring`) | `coverage` gates | **2–4× faster cov** | Low (verify async accuracy) |
| 9. Vitest: lazy-load `openapi.json` only on fetch + cache parsed validator / use `--pool=threads` or `isolate: false` for pure tests; remove duplicate `tsc --noEmit` from `lint` in `package.json` | `@orcia/web` + `turbo` | **-25 to -35 s** | Medium (check global state isolation) |
| 10. Shared `scope="session"` PG18 + Redis7.4 + template-DB (`CREATE DATABASE ... TEMPLATE`) or schema-reset in `tests/integration/conftest.py` (1 container boot + 1 Alembic run instead of 59+) | `tests/integration` | **-350 to -500 s** across full integration | Medium (clean DB isolation per file) |
