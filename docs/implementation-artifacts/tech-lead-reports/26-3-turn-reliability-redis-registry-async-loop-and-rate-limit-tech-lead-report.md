# Story 26.3 — Turn Reliability: Redis Registry `(workspace, user, turn_id)`, Graceful Drain & Liveness Key, Cursor SSE Reattachment, 100% Async Loop & Rate Limiting

- **Date:** 2026-11-21
- **Story / Sprint Key:** `26-3-turn-reliability-redis-registry-async-loop-and-rate-limit` (`Epic 26`)
- **Capabilities:** `CAP-069`, `CAP-075` — classification: `feature`
- **Author / Context:** Tech Lead & Senior Dev implementation of Epic 26 Lot 3 Story 26.3 (`H-10`, `H-11`, `H-20`, `H-21`, `H-23`, `H-33`, `AD-19`, `AD-25`, `D2 + R1`), eliminating RAM-only `ACTIVE_WORKSPACE_TURNS`, event-loop blocking (`ThreadPoolExecutor`, sync SSE generators, `if loop.is_running(): pass`), silent error swallowing, and missing stream resilience/rate-limiting.
- **Commits:** pending on `feat/epic-26-assistant-harness-debt-remediation`

---

## 1. Requirements & Tech Lead Impact Analysis (Analyse du Besoin)

### 1.1 Context & Problem Statement
- **RAM-only turn registry collision & leaks (`H-10`, `H-21`):** `ACTIVE_WORKSPACE_TURNS` in `apps/api/src/orcia_api/routers/_assistant_background_registry.py` is indexed solely by `workspace_id`. Concurrent tabs or different users on the same workspace overwrite each other's active turn, lose `asyncio.Task` references (risking premature GC), never bound or expire event buffers, cannot propagate `/stop` across API workers (`--workers > 1`), skip `_finalize()` FinOps `audit_ledger` accounting on cancellation, and lack cursor-based SSE reattachment (`?after=<cursor>`).
- **Single-process hosting & liveness detection (`D2 + R1`):** Per `AD-25` (`R1`), all assistant turns execute inside `apps/api` in tracked `asyncio.Task` handles (`add_done_callback`) with bounded `SIGTERM` graceful drain capped by profile wall-clock budget, backed by Redis Streams (`XADD MAXLEN ~`, post-completion TTL), a refreshed Redis liveness key (`ERR_ASSISTANT_TURN_INTERRUPTED` on pod crash without auto-retry), and Redis `stop` propagation.
- **Event-loop blocking (`H-11`):** `step_executors.py` (`524` lines, exceeding the `300`-line cap) uses `ThreadPoolExecutor(max_workers=1).result()` via `_run_llm_sync`; `assistant.py` and `assistant_three_speed_router.py` expose sync SSE generators; `context_adapters.py` and `hybrid_rag_service.py` contain `if loop.is_running(): pass`, silently skipping embedding generation inside async FastAPI handlers.
- **Silent errors, stream fragility & missing rate limits (`H-20`, `H-23`, `H-33`):** `step_executors.py` swallows cognitive router failures (`except Exception: pass`), `llm_streaming_base_httpx.py` swallows HTTP/stream exceptions without emitting structured `stream_error` events and lacks pre-first-byte retry (`429/502/503`) and inter-chunk idle timeouts, and assistant endpoints lack Redis sliding-window rate limits and per-user concurrency semaphores (`HTTP 429` RFC 9457 + `trace_id`).

### 1.2 GitNexus Impact Analysis, Refactoring & Technical Debt
- **GitNexus & Cross-Repo Call-Site Impact (`repo: "/home/romain/Documents/Projects/ORCIA"`):**
  - `ACTIVE_WORKSPACE_TURNS` & `_assistant_background_registry.py`: imported by `assistant_background_turns.py`, `assistant_llm_bridge.py`, `_assistant_workspace_controls.py`, and `_assistant_workspace_context.py` (zero direct test imports of `ACTIVE_WORKSPACE_TURNS`).
  - `step_executors.py` (`524` lines): `register_default_step_executors` and `_DEFAULT_AGENT_EXECUTOR` used by `engine.py`, `dbos_engine.py`, `core_and_lifespan.py`, and unit/integration tests (`test_story_3_2f_*`, `test_story_3_3_*`, `test_durable_orchestration_and_blackboard.py`); `_run_llm_sync` used by `step_executors.py` and `assistant_agent_synthesis.py`.
  - `HybridRagService` & `HybridRagVectorStoreAdapter`: used by `ontology_and_rag.py`, `assistant_agent.py`, `tripartite_and_freshness.py`, and unit/eval tests (`test_hybrid_rag_and_tripartite.py`, `test_story_19_6_*`, `test_story_25_5_*`, `test_story_3_3_*`).
  - `assistant_workspace.py` & `_assistant_workspace_controls.py`: active UI SSE `/three-speed/stream`, `/three-speed/active-turn`, `/three-speed/stop` (Playwright E2E `02`, `12`, `16`, `21` compatibility must be preserved until Story `26.7` atomic cutover).
- **Refactoring & File Size Control (`<= 300` lines):**
  - Split `step_executors.py` (`524` lines) into `step_executors.py` (`AgentStepExecutor`, `SkillStepExecutor`, registry/exports `<= 260` lines) and `_step_executors_actions.py` (`SubWorkflowStepExecutor`, `HumanTaskStepExecutor`, `HttpActionStepExecutor`, `PostActionVerificationStepExecutor` `<= 220` lines).
  - Keep all new/modified Python modules `<= 300` lines (`assistant_turn_stream_port.py`, `redis_turn_registry.py`, `redis_rate_limiter.py`, `assistant_turn_errors.py`, `_assistant_turns_v2_routes.py`, `assistant_background_turns.py`, `_assistant_background_registry.py`, `llm_streaming_base_httpx.py`).
  - Preserve `AD-19` unidirectional boundaries (`orcia_core/ports/` zero Redis/FastAPI/SQLAlchemy imports) and avoid the word `simulated` in `packages/orcia-core/src/orcia_core/orchestration/` (`test_story_3_2f` `AC-F2` invariant).

---

## 2. Implementation Plan (Plan d'Implémentation)

### 2.1 Database Schema & Alembic Migrations
- None required for Story `26.3` (ephemeral turn registry, streams, liveness, stop coordination, and rate-limiting live in Redis 7.4; FinOps accounting reuses existing idempotent `audit_ledger` table).

### 2.2 Hexagonal Core, Ports & Async Execution (`packages/orcia-core/`)
- `packages/orcia-core/src/orcia_core/ports/assistant_turn_stream_port.py`: pure Protocol interfaces (`AssistantTurnRegistryPort`, `AssistantTurnStreamPort`, `AssistantRateLimiterPort`) and immutable dataclasses (`AssistantTurnRecord`, `AssistantTurnStreamEvent`) with zero SDK/framework imports.
- `packages/orcia-core/src/orcia_core/orchestration/assistant_turn_errors.py`: domain errors inheriting `OrciaDomainError` (`AssistantTurnInterruptedError` `503 ERR_ASSISTANT_TURN_INTERRUPTED`, `AssistantRateLimitExceededError` `429 ERR_ASSISTANT_RATE_LIMITED`, `AssistantConcurrencyLimitError` `429 ERR_ASSISTANT_CONCURRENCY_LIMIT`) with localized FR/EN catalog entries.
- `packages/orcia-core/src/orcia_core/orchestration/redis_turn_registry.py` & `redis_rate_limiter.py`:
  - Redis-backed turn metadata (`turn:{turn_id}`), `(workspace_id, user_id, turn_id)` sorted-set index (`turns:idx:{ws}:{user}`), refreshed liveness key (`turn:live:{turn_id}`), bounded Redis Streams (`XADD MAXLEN ~`, `XREAD` cursor replay, post-completion `EXPIRE`), cross-worker `stop` key + Pub/Sub channel, and RFC 9457 `stream_error` builder.
  - Redis sliding-window rate limiter (`ZREMRANGEBYSCORE`/`ZCARD`/`ZADD`) and per-user concurrency semaphore with TTL lease pruning.
  - Instance-scoped local fallback when `redis_client is None` (zero module-level global dicts).
- `packages/orcia-core/src/orcia_core/orchestration/step_executors.py` + `_step_executors_actions.py` + `engine.py` + `challenge_and_replay.py` + `_internal/dbos_engine.py`:
  - Split `step_executors.py <= 300` lines, delete `_run_llm_sync` and `ThreadPoolExecutor`, add `execute_step_async` and `replay_from_step_async`, log cognitive router resolution failures via `get_logger`, and preserve sync entrypoints only when no event loop is running.
- `packages/orcia-core/src/orcia_core/orchestration/assistant_agent.py` + `assistant_agent_synthesis.py` + `assistant_three_speed_router.py`:
  - Add `run_conversation_turn_async`, `stream_conversation_turn_sse_async`, and `stream_three_speed_turn_sse_async` using native `await` and async generators.
- `packages/orcia-core/src/orcia_core/rag/context_adapters.py` + `hybrid_rag_service.py`:
  - Remove `if loop.is_running(): pass` silent bypass; add `hybrid_search_async` and `search_hybrid_rrf_async` awaiting `EmbeddingPort.embed_query` natively.
- `packages/orcia-core/src/orcia_core/orchestration/llm_streaming_base_httpx.py` & `ports/llm_streaming_port.py`:
  - Add bounded pre-first-byte retry (`max_retries=2`, 2x exponential backoff on HTTP `429/502/503`), configurable inter-chunk idle timeout (`asyncio.wait_for`), and structured `stream_error` delta emission on HTTP/timeout/network failures.

### 2.3 Backend API, Composition Root & OpenAPI Contracts (`apps/api/`, `packages/api-client/`)
- `apps/api/src/orcia_api/dependencies/_lifespan_services.py`, `core_and_lifespan.py`, `_lifespan_infra.py`:
  - Instantiate `app.state.assistant_turn_registry`, `app.state.assistant_rate_limiter`, and tracked `app.state.assistant_turn_tasks: set[asyncio.Task[None]]` in Composition Root; bind `redis_client` when initialized.
  - Implement bounded graceful `drain_assistant_turn_tasks(app)` during lifespan shutdown (`SIGTERM`) capped by profile wall-clock budget before closing Redis/HTTP/DB resources.
- `apps/api/src/orcia_api/routers/assistant_background_turns.py` & `_assistant_background_registry.py`:
  - Delete `ACTIVE_WORKSPACE_TURNS`; track `asyncio.Task` handles on `app.state.assistant_turn_tasks` with `add_done_callback`; run liveness heartbeat + cross-worker Redis `stop` listener; emit terminal `turn_stopped` and flush partial streamed token FinOps accounting to `audit_ledger` inside `finally` (`turn_id` idempotent); emit structured RFC 9457 + `trace_id` `stream_error` on empty-stream/provider failure or expired pod liveness (`ERR_ASSISTANT_TURN_INTERRUPTED`).
- `apps/api/src/orcia_api/routers/assistant_workspace.py`, `_assistant_workspace_controls.py`, `_assistant_turns_v2_routes.py`, `assistant.py`, `blackboard_and_engine.py`, `challenge_and_replay.py`:
  - Enforce Redis sliding-window rate limit + per-user concurrency semaphore (`HTTP 429` RFC 9457 + `trace_id`).
  - Expose `POST /api/v1/assistant/turns` (`202 Accepted`), `GET /api/v1/assistant/turns/{turn_id}/stream?after=<cursor>`, `GET /api/v1/assistant/turns/active`, `POST /api/v1/assistant/turns/{turn_id}/stop` while preserving `/three-speed/*` UI compatibility until Story `26.7`.
  - Switch `assistant.py`, `blackboard_and_engine.py`, `challenge_and_replay.py` to async generators and `*_async` methods.
- Regenerate `packages/api-client/src/generated/` via `scripts/export_openapi.py` if OpenAPI schemas change (`0-diff` gate).

### 2.4 Frontend SPA (`apps/web/`)
- No UI transport cutover in Story `26.3` (cutover occurs in Story `26.7`); existing `/three-speed/*` contract remains backwards-compatible so E2E `02`, `12`, `16`, `21` remain green.

### 2.5 Test Pyramid Impact (`AD-17` Layers 1–5 + Security)
- **Layer 1 (`tests/unit/test_story_26_3_turn_reliability_and_async_loop.py`):** Multi-tab `(workspace_id, user_id, turn_id)` isolation, zero `ACTIVE_WORKSPACE_TURNS`, `add_done_callback` task tracking + bounded `SIGTERM` drain, async RAG/step executors (`0` `ThreadPoolExecutor.result()`, `0` `if loop.is_running(): pass`), bounded pre-first-byte retry (`429/502/503`) + inter-chunk idle timeout, RFC 9457 `stream_error` + `trace_id` on empty/provider error, sliding-window rate limit & per-user concurrency `429`, and `<= 300`-line file cap AST check.
- **Layer 2 (`tests/integration/api/test_story_26_3_redis_multi_worker_turns_postgres18.py`):** Two independent `create_app()` FastAPI instances sharing real `testcontainers` PostgreSQL 18 + Redis 7.4 verifying cross-worker `?after=<cursor>` replay without duplicates, cross-worker `stop` + partial FinOps `audit_ledger` SQL `SELECT`, concurrent multi-tab isolation, Redis `429` rate limit/concurrency enforcement, and expired liveness `ERR_ASSISTANT_TURN_INTERRUPTED` detection after simulated pod crash.
- **Layer 3 (`tests/contract/test_openapi_contract.py` & `lint-imports`):** OpenAPI `0-diff` and `5/5` unidirectional contracts.
- **Layers 4 & Security & 5:** Existing evals, security suites, `pnpm turbo run lint typecheck test` non-regression, and Playwright E2E `02/12/16/21` compatibility preserved.

---

## 3. Modifications Summary & Verification Results (Bilan des Modifications)

### 3.1 Delivered Modules & Splits (`<= 300` Lines Cap)
- **Hexagonal Ports & Domain Errors (`orcia_core`):**
  - Created `packages/orcia-core/src/orcia_core/ports/assistant_turn_stream_port.py` (`175` L): `AssistantTurnRegistryPort`, `AssistantTurnStreamPort`, `AssistantRateLimiterPort`, `AssistantTurnRecord`, `AssistantTurnStreamEvent`, and `AssistantTurnStatus` with zero SDK/framework imports (re-exported in `ports/__init__.py`, `121` L).
  - Updated `packages/orcia-core/src/orcia_core/ports/llm_streaming_port.py` (`89` L): added `inter_chunk_timeout_s`, `error_code`, and `http_status`.
  - Created `packages/orcia-core/src/orcia_core/orchestration/assistant_turn_errors.py` (`91` L): `AssistantTurnInterruptedError` (`503 ERR_ASSISTANT_TURN_INTERRUPTED`), `AssistantRateLimitExceededError` (`429 ERR_ASSISTANT_RATE_LIMITED`), and `AssistantConcurrencyLimitError` (`429 ERR_ASSISTANT_CONCURRENCY_LIMIT`) registered in FR/EN `ERROR_CATALOG` and mapped in `apps/api/src/orcia_api/errors/registry.py` (`286` L).
- **Redis Registry, Streams, Liveness & Rate Limiter:**
  - Created `packages/orcia-core/src/orcia_core/orchestration/redis_turn_registry.py` (`277` L) & `_redis_turn_helpers.py` (`91` L): `(workspace_id, user_id, turn_id)` indexing (`turns:idx:{ws}:{user}`), turn TTL (`turn:{id}`), liveness key (`turn:live:{id}`), cross-worker `stop` + Pub/Sub channel, bounded Redis Streams (`XADD MAXLEN ~`, `XREAD` `?after=<cursor>`, post-completion TTL), and `build_rfc9457_stream_error_payload`.
  - Created `packages/orcia-core/src/orcia_core/orchestration/redis_rate_limiter.py` (`137` L): sliding-window ZSET rate limiter and per-user concurrency semaphore with TTL lease pruning.
- **Stream Resilience & 100% Non-Blocking Async Loop:**
  - Updated `llm_streaming_base_httpx.py` (`294` L), `llm_streaming_sse_utils.py` (`174` L), `llm_streaming_httpx.py` (`145` L): pre-first-byte retry (`max_retries=2`, 2x backoff on HTTP `429/502/503` and connect errors), configurable inter-chunk idle timeout (`asyncio.wait_for`), and structured `stream_error` deltas.
  - Split `step_executors.py` (`524` L -> `265` L) + `_step_executors_skill.py` (`125` L) + `_step_executors_actions.py` (`191` L); split `_internal/dbos_engine.py` (`348` L -> `261` L) + `_internal/_dbos_workflow_defs.py` (`120` L); split `engine.py` (`293` L) + `_engine_fast_path.py` (`268` L) + `_engine_step_helpers.py` (`246` L); split `challenge_and_replay.py` (`230` L) + `_challenge_replay_models.py` (`244` L) + `_challenge_replay_executors.py` (`188` L); split `human_anchors_and_arbitration.py` (`291` L) + `_human_anchors_models.py` (`125` L) + `_human_anchors_arbitration_ops.py` (`266` L); removed `_run_llm_sync` and `ThreadPoolExecutor` blocking calls across `step_executors.py`, `assistant_agent.py` (`221` L), `assistant_agent_synthesis.py` (`253` L), `_assistant_workflow_launch.py` (`80` L), `_assistant_agent_nodes.py` (`248` L), `assistant_three_speed_router.py` (`275` L), `_assistant_three_speed_cache.py` (`68` L), and `apps/worker/src/orcia_worker/dbos_workflow_runner.py` (`280` L).
  - Updated `rag/context_adapters.py` (`258` L), `_context_adapters_helpers.py` (`86` L), and `hybrid_rag_service.py` (`264` L): removed `if loop.is_running(): pass` and added `hybrid_search_async` / `search_hybrid_rrf_async`.
- **FastAPI Composition Root, Tracked Tasks, Graceful Drain & v2 Turn Routes (`apps/api/`):**
  - Updated `dependencies/_lifespan_services.py` (`146` L), `_lifespan_infra.py` (`215` L), `core_and_lifespan.py` (`260` L): tracked `app.state.assistant_turn_tasks` (`add_done_callback`) and bounded `SIGTERM` graceful `drain_assistant_turn_tasks(app)`.
  - Deleted `ACTIVE_WORKSPACE_TURNS`; created `_assistant_turn_consumer.py` (`76` L), `_assistant_turn_producer.py` (`287` L), `_assistant_turn_producer_helpers.py` (`210` L), `_assistant_turns_v2_routes.py` (`225` L), and refactored `_assistant_background_registry.py` (`138` L), `assistant_background_turns.py` (`258` L), `_assistant_llm_stream_bridge.py` (`112` L), `_assistant_workspace_controls.py` (`103` L), `assistant_workspace.py` (`260` L), `assistant_llm_bridge.py` (`293` L), `assistant.py` (`224` L), `blackboard_and_engine.py` (`212` L), `challenge_and_replay.py` (`227` L), `_blackboard_arbitration_routes.py` (`222` L), and `schemas/{assistant,assistant_governance_and_three_speed}.py` (`194` L, `288` L).
  - Regenerated `@orcia/api-client` OpenAPI schemas (`0-diff` verified via `export_openapi.py --check`) and updated `docs/product/capabilities.yaml` (`CAP-069`, `CAP-075`).
- **Tests Created:**
  - `tests/unit/test_story_26_3_turn_reliability_and_async_loop.py` (`9` tests covering ports, AST non-blocking/silent-except/line-cap invariants, multi-tab isolation, liveness + `SIGTERM` drain, retries/idle timeout, empty stream `stream_error` + `trace_id`, rate limiting & concurrency limits, background wrappers & telemetry upsert).
  - `tests/integration/api/test_story_26_3_redis_multi_worker_turns_postgres18.py` (`1` end-to-end test across `2` independent `create_app()` FastAPI instances with zero overrides/`app.state` tampering against real `testcontainers` PG18 + Redis 7.4 verifying cursor replay `?after=<cursor>`, cross-worker `stop` + idempotent partial FinOps `audit_ledger` SQL `SELECT`, expired liveness `ERR_ASSISTANT_TURN_INTERRUPTED`, and cross-worker Redis `429` rate/concurrency limits).

### 3.2 Verification Gates & Metrics (`AD-17`)
- **Story `26.3` Combined Coverage (`unit + real PG18/Redis 7.4 integration`):** **`94%`** (`93.88%` exact across `788` statements / `192` branches in the `11` Story `26.3` turn-reliability modules via `coverage run --branch` + `--fail-under=90` **PASS**: `9 passed` unit + `1 passed` 2-instance PG18/Redis 7.4 integration).
- **Layer 1 + 3 + 4 + Security (`pytest tests/unit tests/security tests/evals tests/contract`):** **`1103` collected / `100%` pass** (`exit 0`, including `test_codebase_architectural_anti_patterns_audit`, `test_integration_no_manual_app_state_audit`, `test_capabilities_registry`, `test_openapi_contract`).
- **Layer 2 PG18 Non-Regression (`test_story_26_1_assistant_security_postgres18.py` + `test_story_25_5_assistant_chat_only_and_rag_guard_postgres18.py`):** **`2/2` passed (`exit 0`)**.
- **Layer 5 Playwright Desktop E2E (`00, 02, 12-finops, 12-epic16, 16, 21`):** **`15 passed, 1 skipped, 0 failed`** (`Story 26.3 Testing Sub-Agent` verification).
- **Architecture & Static Gates:**
  - `ruff check .` & `ruff format --check .`: **`0` errors** (`1436` files formatted).
  - `mypy --strict`: **`0` errors across `657` source files**.
  - `lint-imports`: **`5/5` contracts kept, `0` broken** (`701` files analyzed).
  - `scripts/export_openapi.py --check`: **`0-diff` (`exit 0`)**.
  - `wc -l <= 300` across all `53` modified/created non-generated source files: **max `294` lines** (`0` files over `300` lines).
  - `pnpm turbo run lint typecheck test`: **`9/9` tasks successful** (`67` `@orcia/web` files / `261` tests + `@orcia/ui` + `@orcia/api-client`).
  - `detect-secrets-hook --baseline .secrets.baseline`: **clean (`exit 0`, zero credentials)**.

### 3.3 Final Review Closure & Post-Sync Audit
- Story `26.3` validated (`done` in `sprint-status.yaml`), `README.md` updated, `scripts/check_implementation_docs.py` verified, `pnpm site:sync && pnpm site:check` green, and `npx gitnexus analyze --index-only` refreshed after all documentation & manifest edits.
