# Story 26.4a — Redis Thread Turn Locks, Outbox Domain Event Emission, Hub Snapshot Invalidation, Prompt-Cache Removal (`R6`) & Alembic DDL Migration

- **Date:** 2026-11-22
- **Story / Sprint Key:** `26-4a-redis-thread-locks-outbox-hub-invalidation-and-alembic-ddl` (`Epic 26`, Lot 3)
- **Capabilities:** `CAP-071`, `CAP-073` — classification: `feature`
- **Author / Context:** Tech Lead / Senior Dev implementation of Story `26.4a` covering findings `H-09` (thread turn locks), `H-19` (resolved by removal per `R6`), `H-22` (Outbox emission), `H-32` (per-request DDL & ephemeral `httpx.AsyncClient` removal), and `H-35` (`platform_setup_snapshot` bounded TTL + AI Hub mutation invalidation). Aligns with `AD-15`, `AD-19`, `AD-24`, `AD-25`, and `epic-26-decisions-grill-2026-11-21.md` (`R6`, `D2`, `D9`).
- **Associated Commits:** Pending atomic commit on branch `feat/epic-26-assistant-harness-debt-remediation`

---

## 1. Requirements & Tech Lead Impact Analysis (Analyse du Besoin)

### 1.1 Context & Problem Statement
- **Thread Turn Locks (`H-09`):** `AssistantFoldersAndSharingService` currently stores collaborative thread turn locks (`lock:thread:<thread_id>`) in an in-memory dictionary (`_turn_locks: dict[str, _ActiveTurnLockEntry]`), failing cross-worker mutual exclusion and leaking lock state across restarts.
- **Premature Prompt-Cache & Forged Outbox ID (`H-19`, `R6`):** `AssistantThreeSpeedRouterService` relies on `InMemoryPromptCacheStore` / `AssembledPromptCachePort` and `_assistant_three_speed_cache.py`, while `invalidate_prompt_cache()` fabricates a random UUIDv7 `outbox_event_id=new_uuid7_str()` without persisting anything into `domain_events_outbox`. Under the measure-first policy `R6`, prompt caching and Outbox cache-invalidation consumers must be deleted until SQL assembly `p95 > 50 ms` is empirically measured (`ACTION_ITEM-26.3`).
- **Missing Outbox Lifecycle Events (`H-22`):** Assistant harness lifecycle transitions (turn start/completion/stop/failure and governance settings updates) do not persist real `DomainEvent` entries via `SqlDomainEventsOutboxRepository` into PostgreSQL 18 `domain_events_outbox`.
- **Infinite `platform_setup_snapshot` Cache (`H-35`):** `app.state.platform_setup_snapshot` has no TTL and is not invalidated across workers when AI Hub model mappings are created, updated, deleted, or activated.
- **Per-Request DDL & Ephemeral `httpx.AsyncClient` (`H-32`):** `ensure_ai_model_mappings_schema_on_postgres18` executes `CREATE TABLE` / `ALTER TABLE` / `CREATE INDEX` DDL on every request in `llm_endpoint_resolver.py`, `_rag_availability_guards.py`, `ai_models_hub.py`, `_ai_models_helpers.py`, `_ai_models_test_and_reindex_routes.py`, and `_ai_models_reindex_helpers.py`. In addition, `_ai_models_helpers.py` and `_bootstrap_llm_routes.py` instantiate ephemeral `httpx.AsyncClient()` instances outside `app.state.http_client`.

### 1.2 Exploration, GitNexus Impact Analysis, Factorization & Technical Debt
- **GitNexus Impact Analysis (`repo: "/home/romain/Documents/Projects/ORCIA"`):**
  - Queried `RedisThreadTurnLock`, `InMemoryPromptCacheStore`, `AssembledPromptCachePort`, `outbox_event_id`, `platform_setup_snapshot`, `ensure_ai_model_mappings_schema_on_postgres18`, `assistant_three_speed_router`, `assistant_folders_and_sharing`, `_rag_availability_guards`, `assistant_llm_resolver`, `ai_models_hub`.
  - Key execution flows identified: `execute_turn_producer_task` -> `Stream_chat_sse` (`proc_127_execute_turn_produce`), `AssistantFoldersAndSharingService.send_collaborative_thread_turn_async`, `resolve_configured_llm_endpoint_from_sources`, `get_embedding_port`, and `ai_models_hub` mutations.
  - Note: GitNexus index is 1 commit behind `HEAD`; direct `grep` across `packages/`, `apps/`, `infra/`, and `tests/` verified every call site of `ensure_ai_model_mappings_schema_on_postgres18`, `InMemoryPromptCacheStore`, `AssembledPromptCachePort`, `get_or_assemble_cached_prompt`, `invalidate_prompt_cache`, `platform_setup_snapshot`, and `httpx.AsyncClient`.
- **Line-Count Audit (Target `<= 300 L` per touched/created non-generated source file):**
  - `assistant_three_speed_router.py` (275 L), `assistant_three_speed_models.py` (165 L), `assistant_three_speed_steps.py` (288 L), `_assistant_three_speed_cache.py` (68 L — to delete), `assistant_folders_and_sharing.py` (253 L), `_assistant_folders_sync.py` (289 L), `_assistant_folders_async_ops.py` (171 L), `_assistant_folders_models.py` (162 L), `llm_endpoint_resolver.py` (165 L), `sql_ai_model_queries.py` (296 L), `portal_and_assistant.py` (196 L), `_rag_availability_guards.py` (165 L), `assistant_llm_resolver.py` (105 L), `ai_models_hub.py` (293 L), `_ai_models_helpers.py` (264 L), `_ai_models_test_and_reindex_routes.py` (244 L), `_ai_models_reindex_helpers.py` (196 L), `_bootstrap_llm_routes.py` (257 L), `_bootstrap_setup_state.py` (264 L), `_assistant_workspace_controls.py` (103 L), `assistant_workspace_governance.py` (266 L), `_assistant_turn_producer.py` (287 L), `_assistant_turn_producer_helpers.py` (210 L), `assistant_background_turns.py` (258 L).
- **Factorization & Debt Resolution:**
  - Extract `ThreadTurnLockPort` (`packages/orcia-core/src/orcia_core/ports/assistant_turn_stream_port.py` or `thread_lock_port.py`) and `RedisThreadTurnLock` (`packages/orcia-core/src/orcia_core/orchestration/redis_thread_lock.py`), removing `_turn_locks` and `_ActiveTurnLockEntry` completely and moving `InMemoryThreadTurnLock` solely into `tests/unit/fakes/`.
  - Centralize `platform_setup_snapshot` bounded TTL + Redis version marker invalidation in `packages/orcia-core/src/orcia_core/bootstrap/setup_snapshot_cache.py`, reused by `assistant_llm_resolver.py`, `_bootstrap_setup_state.py`, `ai_models_hub.py`, `_ai_models_test_and_reindex_routes.py`, `_bootstrap_llm_routes.py`, and `e2e_test_hooks.py`.
  - Reuse `get_or_create_async_http_client(request)` from `orcia_api.dependencies._llm_streaming_providers` across `_ai_models_helpers.py`, `_bootstrap_llm_routes.py`, and `_rag_availability_guards.py` so zero ephemeral `httpx.AsyncClient()` instances exist on assistant/RAG/AI Hub paths.

---

## 2. Implementation Plan (Plan d'Implémentation)

### 2.1 Data Schema & Alembic Migrations (`infra/migrations/versions/`)
- **`infra/migrations/versions/20261122_264a_story_26_4a_ai_models_schema_and_assistant_outbox.py` (`down_revision = "20261120_2403"`):**
  - Idempotently enforce all `workspace_llm_tier_mappings` columns and indexes (`idx_llm_tier_mappings_scope_tier_active`, `idx_llm_tier_mappings_single_active_global_embedding`) plus add partial lookup index `idx_llm_tier_mappings_active_chat_lookup` on `(scope_level, scope_id, inference_tier, fallback_order, created_at) WHERE (usage = 'chat' AND is_active = TRUE AND draining = FALSE)` so runtime resolution never issues DDL.
  - Expand `domain_events_outbox_event_type_check` to permit `AssistantTurnStarted`, `AssistantTurnCompleted`, `AssistantTurnStopped`, `AssistantTurnFailed` alongside existing event types.
  - Pure raw SQL (`op.execute(sa.text(...))`), zero ORM imports, fully reversible `downgrade()` removing the new index, deleting Story `26.4a` outbox event types if present, and restoring the `20261120_2403` check constraint.
  - Keep `audit_ledger`/`blackboard_snapshots` append-only triggers untouched and verify `09_reset_db_first_boot.py` compatibility.

### 2.2 Hexagonal Core, Orchestration & Workers (`packages/orcia-core/`)
- **Domain Events (`packages/orcia-core/src/orcia_core/kernel/`):**
  - Add `AssistantTurnStarted`, `AssistantTurnCompleted`, `AssistantTurnStopped`, `AssistantTurnFailed` immutable dataclasses inheriting from `DomainEvent` and re-exported from `orcia_core.kernel.events`.
- **Redis Thread Turn Lock (`H-09`):**
  - Define pure `ThreadTurnLockPort` (`ports/assistant_turn_stream_port.py` or `ports/thread_lock_port.py`, zero SDK imports).
  - Implement `RedisThreadTurnLock` (`orchestration/redis_thread_lock.py`) using atomic Redis `SET lock:thread:<thread_id> <holder_token> NX EX <ttl>` and Lua token/owner-checked release (`DEL` only if owner/token matches), wired to `app.state.redis_client` with `set_redis_client()`.
  - Remove `_turn_locks` and `_ActiveTurnLockEntry` from `assistant_folders_and_sharing.py`, `_assistant_folders_sync.py`, and `_assistant_folders_models.py`; wire `RedisThreadTurnLock` into `AssistantFoldersAndSharingService` (`send_collaborative_thread_turn_async` awaits `acquire_async`/`release_async`).
  - Place `InMemoryThreadTurnLock` strictly in `tests/unit/fakes/in_memory_thread_lock.py`.
- **Prompt-Cache & Forged Outbox ID Deletion (`H-19`, `R6`):**
  - Delete `InMemoryPromptCacheStore`, `AssembledPromptCachePort`, `_assistant_three_speed_cache.py`, and `outbox_event_id=new_uuid7_str()` generation from `assistant_three_speed_models.py` and `assistant_three_speed_router.py`.
  - Keep `AssistantThreeSpeedRouterService` assembling 5-layer prompts directly without caching (`cache_hit=False`, `ttl_seconds=0`, measured via `perf_counter()`).
- **Outbox Lifecycle Emission (`H-22`):**
  - Create `packages/orcia-core/src/orcia_core/orchestration/assistant_outbox_emitter.py` wrapping `SqlDomainEventsOutboxRepository` (`DbosSqlAlchemyUnitOfWork`) to enqueue `AssistantTurnStarted`, `AssistantTurnCompleted`, `AssistantTurnStopped`, `AssistantTurnFailed`, and `SettingsChanged` cleanly (coercing workspace UUIDs safely and never raising raw SQL errors on non-UUID test slugs).
- **Snapshot Cache & Runtime DDL Removal (`H-32`, `H-35`):**
  - Create `packages/orcia-core/src/orcia_core/bootstrap/setup_snapshot_cache.py` providing bounded TTL (`ORCIA_PLATFORM_SETUP_SNAPSHOT_TTL_S`, default `30.0s`) and Redis version marker (`orcia:platform_setup_snapshot:version`) checks & invalidation.
  - Remove `ensure_ai_model_mappings_schema_on_postgres18` from `llm_endpoint_resolver.py`, `sql_ai_model_queries.py`, `sql_ai_model_mappings.py`, and `orchestration/__init__.py` (preserving Story `25.5` & `[P0-2]` PG18 resolver priority).

### 2.3 Backend API, Composition Root & OpenAPI Contracts (`apps/api/`, `packages/api-client/`)
- **Composition Root (`portal_and_assistant.py`, `core_and_lifespan.py`, `_lifespan_infra.py`):**
  - Wire `app.state.redis_client` into `AssistantFoldersAndSharingService` (`RedisThreadTurnLock`) and `AssistantOutboxEmitter` (`SqlDomainEventsOutboxRepository`) via `dbos_uow`.
- **Routers & Guards:**
  - Remove all `ensure_ai_model_mappings_schema_on_postgres18` calls from `_rag_availability_guards.py`, `ai_models_hub.py`, `_ai_models_helpers.py`, `_ai_models_test_and_reindex_routes.py`, `_ai_models_reindex_helpers.py`.
  - Remove ephemeral `httpx.AsyncClient()` calls from `_ai_models_helpers.py` and `_bootstrap_llm_routes.py` by reusing `get_or_create_async_http_client(request)`.
  - Invalidate `platform_setup_snapshot` (local + Redis version key) on AI Hub mutations (`create_ai_model_mapping`, `update_ai_model_mapping`, `delete_ai_model_mapping`, `register_welcome_setup_progressive_llm`) and read/refresh with bounded TTL in `assistant_llm_resolver.py` and `_bootstrap_setup_state.py`.
  - Emit real `domain_events_outbox` rows from assistant v2 turn producer (`_assistant_turn_producer.py` / `_assistant_turn_producer_helpers.py`) and governance updates (`assistant_workspace_governance.py`).
  - Keep `POST /api/v1/assistant/three-speed/invalidate-cache` as a safe no-op returning `invalidated_keys_count=0`, `outbox_event_id=None` (updating `InvalidatePromptCacheResponse` and regenerating `@orcia/api-client` with `0-diff` check).

### 2.4 SPA Interface (`apps/web/`)
- No functional UI changes required in Story `26.4a` (UI turn transport cutover is scoped to `26.7`/`26.9`). Verify `apps/web` TypeScript build, `vitest`, and `capabilities.yaml` remain green with updated `@orcia/api-client` schema if `InvalidatePromptCacheResponse` changes.

### 2.5 Test Pyramid Impact Analysis (`AD-17` — Layers 1–5 + Security)
- **Layer 1a (Python Unit `tests/unit/test_story_26_4a_*.py`) & Layer 1b (TS `Vitest`):**
  - AST invariants: zero `InMemory*` stores outside `tests/unit/fakes/` (for assistant locks/cache), `InMemoryPromptCacheStore` / `AssembledPromptCachePort` / `_assistant_three_speed_cache.py` / forged `outbox_event_id` deleted, zero runtime `CREATE`/`ALTER`/`CREATE INDEX` DDL in `orcia_api` / `llm_endpoint_resolver.py`, zero ephemeral `httpx.AsyncClient()` on assistant/RAG/AI Hub paths, all touched/created source files `<= 300 L`.
  - Unit tests for `RedisThreadTurnLock`, `setup_snapshot_cache` TTL & invalidation, `AssistantOutboxEmitter`, and `25.5` PG18 resolver priority preservation.
  - Amend `test_epic_10_story_10_2_three_speed_router.py`, `test_story_24_6_cmdk_locale_and_microcopy.py`, `test_epic_25_guards_and_helpers_coverage.py`, and `test_story_25_5_assistant_without_embedding_and_datasource_guard.py` for `R6` & runtime DDL removal.
- **Layer 2 (Vertical Integration `HTTP -> PostgreSQL 18 + Redis 7.4` `tests/integration/api/test_story_26_4a_redis_locks_outbox_ddl_postgres18.py`):**
  - Real `create_app()` with zero `dependency_overrides`, real `PostgresContainer("pgvector/pgvector:pg18")` + `RedisContainer("redis:7.4-alpine")`:
    - Alembic `upgrade -> downgrade -> upgrade` verification on `20261122_264a`.
    - Multi-worker thread lock contention (`SET NX EX` + Lua release) across 2 `create_app()` instances sharing Redis.
    - `SELECT` verification of real `domain_events_outbox` rows emitted during assistant turns and governance mutations.
    - AI Hub mutation (`POST/PATCH/DELETE /api/v1/settings/ai-models/mappings`) immediately invalidating `platform_setup_snapshot` across 2 `create_app()` instances sharing Redis + TTL expiration check.
- **Layer 3 (OpenAPI 3.1 `0-diff`, `lint-imports`, `lint_spine.py`):** Verify `export_openapi.py --check`, `5/5` `import-linter` contracts, and `0` findings.
- **Layer 4 (`tests/evals/`) & Security (`tests/security/`):** Full non-regression run including `test_zero_orphan_sql_adapters_audit.py` and `detect-secrets`.
- **Layer 5 (`apps/web/e2e`):** Preserve Playwright `02`, `12`, `16`, `21` guarantees without breaking `/three-speed/*` routes.

---

## 3. Modifications Summary & Verification Results (Bilan des Modifications)

### 3.1 Delivered Files, Symbols & Line Counts
- **Deleted:**
  - `packages/orcia-core/src/orcia_core/orchestration/_assistant_three_speed_cache.py` (deleted per `R6`)
  - Removed `InMemoryPromptCacheStore`, `AssembledPromptCachePort`, and forged `outbox_event_id=new_uuid7_str()` generation (`H-19`, `R6`)
  - Removed `_turn_locks` and `_ActiveTurnLockEntry` RAM lock dictionaries (`H-09`)
  - Removed runtime `ensure_ai_model_mappings_schema_on_postgres18` DDL function and all per-request callers (`H-32`)
- **Created:**
  - `infra/migrations/versions/20261122_264a_story_26_4a_ai_models_schema_and_assistant_outbox.py` (`159` L, revision `20261122_264a`, down_revision `20261120_2403`) — pure raw-SQL migration consolidating `workspace_llm_tier_mappings`, adding `idx_llm_tier_mappings_active_chat_lookup`, and expanding `domain_events_outbox_event_type_check` (`AssistantTurnStarted`, `AssistantTurnCompleted`, `AssistantTurnStopped`, `AssistantTurnFailed`)
  - `packages/orcia-core/src/orcia_core/kernel/_assistant_events.py` (`167` L) — immutable `DomainEvent` dataclasses for assistant turn lifecycle
  - `packages/orcia-core/src/orcia_core/orchestration/redis_thread_lock.py` (`150` L) — `RedisThreadTurnLock` (`SET lock:thread:<id> <user>:<token> NX EX <ttl>`, Lua owner-refresh, Lua token/owner-checked `DEL`)
  - `packages/orcia-core/src/orcia_core/orchestration/assistant_outbox_emitter.py` (`193` L) — `AssistantOutboxEmitter` & `coerce_optional_uuid` persisting real rows via `SqlDomainEventsOutboxRepository`
  - `packages/orcia-core/src/orcia_core/bootstrap/setup_snapshot_cache.py` (`142` L) — `get_valid_platform_setup_snapshot_async`, `set_cached_platform_setup_snapshot_async`, `invalidate_platform_setup_snapshot_async` (`ORCIA_PLATFORM_SETUP_SNAPSHOT_TTL_S`, default `30.0s`, Redis marker `orcia:platform_setup_snapshot:version`)
  - `tests/unit/fakes/in_memory_thread_lock.py` (`73` L) — `InMemoryThreadTurnLock` isolated strictly under `tests/unit/fakes/`
  - `tests/unit/test_story_26_4a_locks_outbox_cache_removal_and_ddl_audit.py` (`253` L) & `tests/unit/test_story_26_4a_locks_and_snapshot_cache_branches.py` (`146` L) — Layer 1 unit, AST guard & branch coverage suites
  - `tests/integration/api/test_story_26_4a_redis_locks_outbox_ddl_postgres18.py` (`384` L) — Layer 2 PG18 + Redis 7.4 real `create_app()` vertical integration suite (`upgrade -> downgrade -> upgrade` + 2-worker contention/outbox/Hub invalidation)
- **Modified Source Modules (all functional modules `<= 296` L; pre-existing barrel `orchestration/__init__.py` reduced by 2 lines to `522` L):**
  - Core & Ports: `assistant_turn_stream_port.py` (`201` L, `ThreadTurnLockPort`), `kernel/events.py` (`91` L), `assistant_folders_and_sharing.py` (`271` L), `_assistant_folders_sync.py` (`275` L), `_assistant_folders_async_ops.py` (`225` L), `_assistant_folders_models.py` (`155` L), `assistant_three_speed_models.py` (`118` L), `assistant_three_speed_router.py` (`251` L), `llm_endpoint_resolver.py` (`164` L), `sql_ai_model_queries.py` (`210` L), `sql_ai_model_mappings.py` (`33` L)
  - API & Schemas: `portal_and_assistant.py` (`200` L), `core_and_lifespan.py` (`264` L), `_rag_availability_guards.py` (`163` L), `assistant_llm_resolver.py` (`114` L), `ai_models_hub.py` (`296` L), `_ai_models_helpers.py` (`237` L), `_ai_models_test_and_reindex_routes.py` (`245` L), `_ai_models_reindex_helpers.py` (`192` L), `_bootstrap_llm_routes.py` (`247` L), `_bootstrap_setup_state.py` (`278` L), `e2e_test_hooks.py` (`117` L), `_assistant_workspace_controls.py` (`103` L), `assistant_workspace_governance.py` (`287` L), `assistant_background_turns.py` (`270` L), `_assistant_turns_v2_routes.py` (`229` L), `_assistant_turn_producer.py` (`291` L, idempotent `_flush_once` committing PG18 FinOps + Outbox + TTL before terminal `append_event` and `update_turn`), `_assistant_turn_producer_helpers.py` (`294` L, `handle_turn_cancelled` / `handle_turn_failure` / `emit_stream_error_and_outbox` terminal ordering fix), `_assistant_usage_telemetry.py` (`63` L), `assistant_governance_and_three_speed.py` (`288` L, `InvalidatePromptCacheResponse.outbox_event_id: str | None = None`)
  - OpenAPI SDK & Governance: `packages/api-client/openapi.json` & `packages/api-client/src/generated/schema.ts` (regenerated `0-diff`), `docs/product/capabilities.yaml` (`CAP-071`, `CAP-073`), `docs/implementation-artifacts/sprint-status.yaml` (`done`)
  - Updated Legacy Tests: `test_epic_10_story_10_2_three_speed_router.py`, `test_epic_25_guards_and_helpers_coverage.py`, `test_story_25_5_assistant_without_embedding_and_datasource_guard.py`, `test_story_10_2_redis_prompt_cache_and_outbox.py`, `test_story_20_4_profile_summary_postgres18.py`, `test_story_26_1_assistant_security_postgres18.py`, `test_epics_1_7_vertical_sql_wiring_postgres18.py`, `tests/unit/fakes/__init__.py`

### 3.2 Verification Gates & Metrics (`AD-17`)
- **Layer 1 & 2 Story 26.4a Standalone Coverage (`--cov-fail-under=90`):** **11 passed**, **98.97%** total coverage (`233` stmts / `58` branches across `redis_thread_lock.py` `100%`, `assistant_outbox_emitter.py` `100%`, `_assistant_events.py` `100%`, `setup_snapshot_cache.py` `97%`, incl. real `pgvector:pg18` + `redis:7.4.2-alpine` two-worker suite).
- **Combined Epic 25.5 / 26.1 / 26.3 / 26.4a Suite:** **50 passed** (unit + security + PG18/Redis multi-worker integration, plus repeat verification of `test_story_26_3_redis_multi_worker_turns_postgres18.py` -> **1 passed**).
- **Full Layer 1, Security, Evals & Contract Suite:** `.venv/bin/pytest tests/unit tests/security tests/evals tests/contract --no-cov -q` -> **1112 passed** (zero failures, incl. `test_zero_orphan_sql_adapters_audit.py` and `test_codebase_architectural_anti_patterns_audit.py`).
- **Affected PG18 + Redis Integration Non-Regression:**
  - `test_story_26_4a_redis_locks_outbox_ddl_postgres18.py` -> **2 passed** (`alembic upgrade -> downgrade -> upgrade` + 2-worker Redis lock, Outbox `SELECT`, AI Hub snapshot invalidation)
  - `test_story_10_2_redis_prompt_cache_and_outbox.py` + `test_story_26_3_redis_multi_worker_turns_postgres18.py` -> **2 passed**
  - `test_story_20_4_profile_summary_postgres18.py` + `test_story_26_1_assistant_security_postgres18.py` -> **2 passed**
- **TypeScript & Frontend (`pnpm turbo run lint typecheck test`):** **9/9 tasks passed** (`@orcia/api-client` 20/20, `@orcia/ui` 136/136, `@orcia/web` 67/67 files / 261/261 tests).
- **Static, Modularity, Contract & Security Gates:**
  - `.venv/bin/alembic -c infra/migrations/alembic.ini heads` -> single head `20261122_264a (head)`
  - `.venv/bin/ruff check . && .venv/bin/ruff format --check .` -> **All checks passed (`1445` files formatted)**
  - `.venv/bin/mypy --strict packages/orcia-core apps/api apps/worker` -> **Success: no issues found in 619 source files**
  - `.venv/bin/lint-imports` -> **5/5 contracts kept, 0 broken** (`704` files, `5089` dependencies)
  - `.venv/bin/python scripts/export_openapi.py --check` -> **0-diff**
  - `.venv/bin/python .agent/skills/bmad-architecture/scripts/lint_spine.py --workspace docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24` -> **ok: true, 0 findings**
  - `.venv/bin/detect-secrets-hook --baseline .secrets.baseline` -> **exit code 0**
  - `pnpm site:sync && pnpm site:check` -> **Manifest in sync (`65/65` live capabilities, `58` Alembic migrations, `211` reports)**
- **GitNexus Post-Edit Check:** Refreshed via `npx gitnexus analyze --index-only .` after all final verification and doc sync edits (`npx gitnexus status --repo .` verified up-to-date).
