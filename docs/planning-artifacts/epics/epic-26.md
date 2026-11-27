## Epic 26: Unified, Governed & Persistent "Mon Assistant" Harness — Single Turn Engine, Governed Tool Loop, Real Context, Scope Security & Zero RAM State (AD-3, AD-15, AD-19, AD-24, proposed AD-25)

Remediate the "Mon Assistant" harness debt identified by [`2026-11-21-audit-harnais-assistant-et-plan-remediation-tech-lead-report.md`](../implementation-artifacts/tech-lead-reports/2026-11-21-audit-harnais-assistant-et-plan-remediation-tech-lead-report.md) (38 findings `H-01..H-38`, including 14 P0). The master plan is [`sprint-change-proposal-2026-11-21-epic-26-harnais-assistant-remediation-plan.md`](./sprint-change-proposal-2026-11-21-epic-26-harnais-assistant-remediation-plan.md) (**8 lots, 13 stories**), governed by [`epic-26-decisions-grill-2026-11-21.md`](../implementation-artifacts/epic-26-decisions-grill-2026-11-21.md) (`D1–D11` amended by `R1–R9`).

The target converges the three existing execution paths into **one unified turn engine** (`AssistantTurnEngine`):
- **Speed 1** via a single-shot fast-path (`TTFT p95 < 1.2 s`);
- **Speed 2 / Speed 3** on the `ASSISTANT` profile of `NonDeterministicReflexiveRuntime`;
- **Single-process hosting (`R1`)** inside `apps/api` (`asyncio.Task` + `SIGTERM` drain, Redis registry/streams/`stop`, no Dramatiq worker);
- **Fixed `N1–N5` phases** with sealed constitutional guards (`Layer 1`, `N1`, `V5`, `CitationGuard`), Mode A 3-level text governance only (`R2` Mode B deferred in `ACTION_ITEM-26.1`), and a UI **"Deepen"** button after Speed 1 instead of auto-escalation (`R3`);
- **Direct atomic cutover (`R4`)** in `26.7` without a legacy facade (`ACTION_ITEM-26.2`), **audit ledger** phantom tracking without a drafts table (`R5`), **measure-first** prompt assembly without a Redis prompt cache (`R6`, `ACTION_ITEM-26.3`), **3 text adapters** + **2 native tool-calling dialects** (`R7`, `ACTION_ITEM-26.4`), and **env-var SSRF allowlist + DNS pinning** (`R8`, `ACTION_ITEM-26.5`).

All changes preserve `25-5` decoupling invariants (assistant active with `1` `chat` model without `embedding`) and default `PROCESS` behavior in `NonDeterministicReflexiveRuntime`.

**Execution order (`R9`, sequential Lot 3 & risk-tiered workers):**
- Lot 0: `26.0` (`bmad-architect-worker` `pro` → STOP)
- Lot 1: `26.1` (2 `flash` workers + `pro` review)
- Lot 2: `26.2` (1 `flash` worker)
- Lot 3 (sequential on `workspace: "inherit"`, linear Alembic chain): `26.3` → `26.4a` → `26.4b` (1 `flash` worker each)
- Lot 4: `26.5` (1 `flash` worker)
- Lot 5: `26.6a` (1 `flash`) → `26.6b` (2 `flash` workers + `pro` review)
- Lot 6: `26.7` (2 `flash` workers + mandatory `pro` review) → `26.8` (1 `flash` worker)
- Lot 7: `26.9` (1 `flash` worker) → `26.10` (1 `flash` worker + mandatory final `pro` closure gate)

No story starts until its dependencies are `done`. Each story produces one atomic local commit, followed by a STOP and user GO check at the end of each lot.

---

### Story 26.0: ADR Unified Assistant Turn Engine (`AD-25`), `AD-15`/`AD-21`/`AD-24` Updates, SSE v2 Contract & Env-Var SSRF Policy

As a Principal Architect (`Winston`),
I want to ratify and record decisions `D1–D11` as amended by `R1–R9` in the Architecture Spine and ERD, and freeze the OpenAPI/SSE v2 turn contract,
So that all 12 implementation stories execute against an unambiguous, linted architectural contract.

**Lot:** 0 — Framing. **Dependencies:** Epic 25 closed (`epic-25: done`). **Agent:** `bmad-architect-worker` (`pro`).
**Findings covered:** `H-38` + prerequisites `D1–D11` / `R1–R9`.
**CAPs covered:** `none (doc)`.
**Impacted files:** `docs/implementation-artifacts/epic-26-decisions-grill-2026-11-21.md` (input), `docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24/ARCHITECTURE-SPINE.md`, `docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24/architecture.md` (ERD), `docs/planning-artifacts/sprint-change-proposal-2026-11-21-epic-26-harnais-assistant-remediation-plan.md`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/26-0-adr-unified-turn-engine-sse-v2-and-ssrf-policy-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** the Epic 26 master plan, consolidated decisions `D1–D11` + `R1–R9`, and audit `H-01..H-38`
**When** the ADR is authored
**Then** `ARCHITECTURE-SPINE.md` adds `AD-25` ("Unified Assistant Turn Engine") locking: Speed 1 single-shot fast-path (`TTFT p95 < 1.2 s`, post-first-byte persistence); Speed 2/3 `ASSISTANT` profile on `NonDeterministicReflexiveRuntime`; single-process `apps/api` `asyncio.Task` hosting with Redis Streams/registry/`stop` and `SIGTERM` graceful drain (crashed turns flagged `ERR_ASSISTANT_TURN_INTERRUPTED`, no Dramatiq worker, `R1`); **"Deepen"** UI button creating linked Speed 2 turns (`parent_turn_id`, deterministic `low_evidence`, no auto-escalation, `R3`); fixed `N1–N5` phases with sealed constitutional guards and Mode B graphical studio deferred (`R2`); 3 preserved text streaming adapters + 2 native tool-calling dialects (`OpenAI-compatible` & `Anthropic`, `R7`); no assembled-prompt Redis cache until measured p95 `> 50 ms` (`R6`, `FR-33` / Story `10.2` deferral note); no drafts persistence table & phantom citations routed to `audit_ledger` (`R5`); direct cutover without strangler facade (`R4`); and forbidden `ConnectorReflexiveWriteGateAdapter` in `ASSISTANT` profile.

**Given** security, data model, and MCP requirements
**When** `AD-15`, `AD-21`, `AD-24`, and `architecture.md` ERD are updated
**Then** `AD-15` references `AD-25`; `AD-21`/`AD-24` specify ops env-var SSRF allowlist `ORCIA_LLM_ALLOWED_PRIVATE_HOSTS` (`localhost` only when `ORCIA_ENV in ("local", "test")`), permanent cloud-metadata/link-local/internal-port blocks, connection-time DNS pinning (`R8`), public Day-0 `GET /bootstrap/platform-setup-state` projection `{is_initialized, step}`, and 0-token `supports_tools` Hub discovery (`+ PLATFORM_ADMIN` override, `D5`); and the ERD specifies `assistant_thread_messages` (`D4`) and `assistant_turn_feedback` upsert table (`R5`, no Mode B or drafts tables).

**Given** the SSE v2 and canonical REST contract
**When** the specification is frozen and checks run
**Then** SSE events `thinking_delta`, `tool_call`, `tool_result`, `approval_required`, `token_delta`, `citation_map`, `turn_completed` (with `low_evidence`), `turn_stopped`, and `stream_error` (RFC 9457 + `trace_id`, including `ERR_ASSISTANT_TURN_INTERRUPTED` and `422 ERR_MODEL_TOOLS_UNSUPPORTED`) and routes `POST /api/v1/assistant/turns`, `GET /api/v1/assistant/turns/{turn_id}/stream?after=`, `GET /api/v1/assistant/turns/active`, `POST /api/v1/assistant/turns/{turn_id}/{stop,approve,synthesize-now,feedback}`, and `GET /api/v1/assistant/threads/{thread_id}/messages` are fully specified; `npx gitnexus analyze` refreshes cleanly (`0` `assistant_*` symbol with empty `filePath`); and `lint_spine.py` passes with `0 findings`.

---

### Story 26.1: Immediate Security Hardening — Pre-Stream Scope & Observer Guards, Server-Side `READ_SOURCE` / `CONFIDENTIAL_RESTRICTED`, Layer 1 Immutability, Env-Var SSRF + DNS Pinning & Secret Hygiene

As a SecOps Lead (`Sophie`) and Workspace User,
I want every `/api/v1/assistant/*` mutation route to enforce workspace scope access and `READ_ONLY_OBSERVER` checks before opening any response stream, filter `READ_SOURCE` and `CONFIDENTIAL_RESTRICTED` context server-side, prevent Layer 1 overrides, enforce DNS-pinned SSRF checks, and protect setup state and secrets,
So that no user can trigger cross-workspace IDOR, crash ASGI mid-stream, leak confidential data or API keys, or inject privileged instructions.

**Lot:** 1 — Security. **Dependencies:** `26.0`. **Agent:** 2 distinct `bmad-dev-worker` (`flash`: Impl + Independent Verification) + `bmad-architect-worker` (`pro` review, `R9`).
**Findings covered:** `H-06`, `H-07`, `H-08`, `H-15`, `H-16`, `H-17`, `H-30` (prod `assert`).
**CAPs covered:** `CAP-022`, `CAP-070`, `CAP-071`, `CAP-072`, `CAP-073`, `CAP-074` (`D9`: downgrade `CAP-022`, `CAP-070`, `CAP-072` to `verification: api` in `docs/product/capabilities.yaml`).
**Impacted files:** `apps/api/src/orcia_api/routers/assistant_workspace.py`, `assistant_workspace_governance.py`, `assistant_workspace_citations.py`, `assistant_workspace_folders.py`, `assistant.py`, `assistant_llm_prompts.py`, `assistant_llm_providers.py`, `assistant_llm_resolver.py`, `assistant_background_turns.py`, `bootstrap_accostage.py`, `apps/api/src/orcia_api/schemas/assistant_citations_and_folders.py`, `packages/orcia-core/src/orcia_core/orchestration/assistant_governance.py`, `assistant_three_speed_router.py`, `packages/orcia-core/src/orcia_core/observability/_internal/ecs_formatter.py`, `tests/security/`, `docs/product/capabilities.yaml`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/26-1-immediate-security-hardening-scope-observer-and-ssrf-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** a `READ_ONLY_OBSERVER` user or a user lacking access to the target workspace (addressed by UUID **or** slug)
**When** they call any mutating `/api/v1/assistant/*` endpoint (`three-speed/stream|turn|stop|feedback`, `chat*`, `governance*`, `citations/*`, `artifacts/action`, `folders*`, `threads*`, `launch-process`)
**Then** FastAPI dependencies (`resolve_workspace_access` / `ScopeAccessGuard` resolving both slugs and UUIDs via `evaluator`) reject the call with `HTTP 403` (`ERR_OBSERVER_MODE_READ_ONLY` or scope-denied RFC 9457 + `trace_id`) **before HTTP `200` headers or any SSE byte**, governance edits are scoped strictly to the caller's authorized workspaces, and cross-workspace IDOR security tests pass.

**Given** an assistant turn on a workspace containing `CONFIDENTIAL_RESTRICTED` or unauthorized sources
**When** prompt context is assembled and citations are checked
**Then** `READ_SOURCE` permissions are resolved strictly server-side (`PermissionBrokerService` / `evaluator`), client field `reader_allowed_source_uris` is removed from schemas and SDK (`0-diff`), zero unauthorized or confidential content appears in captured LLM payloads, and model endpoint resolution uses the real workspace `scope_id` (removing the hardcoded UUID).

**Given** a turn payload containing `system_instructions_override`, `role: "tool"` history messages, or `[LAYER_*]`/`[CONSTITUTIONAL_*]` tags in user/workspace/folder text
**When** instructions are built
**Then** Layer 1 cannot be overridden on assistant routes, history is restricted to `user|assistant`, user/folder blocks are delimited and sanitized, and `agents_and_skills.py` retains its existing behavior under regression tests.

**Given** an LLM endpoint in PG18 targeting cloud metadata, link-local, internal ORCIA ports (`5432`, `6379`, S3), or a hostname resolving via DNS rebinding to `169.254.169.254`
**When** saved in Hub or connected at runtime
**Then** validation rejects it both on save and at connection time using **DNS resolution pinning** (`getaddrinfo`), while hosts/CIDRs declared in ops env var `ORCIA_LLM_ALLOWED_PRIVATE_HOSTS` (`localhost` permitted only when `ORCIA_ENV in ("local", "test")`, `R8`) remain reachable; `GET /bootstrap/platform-setup-state` returns only `{is_initialized, step}` unauthenticated (`0` sensitive values, `0` internal URIs, `pnpm db:reset` intact) with detailed view gated to `PLATFORM_ADMIN`; provider credential field is excluded from `platform_setup_snapshot`; `str(exc)` passes through the redaction scrubber with bounded `_REGISTERED_SECRET_VALUES`; production `assert det_ms < 80.0` is deleted; and `CAP-022`, `CAP-070`, `CAP-072` move to `verification: api` (`pnpm site:sync && pnpm site:check` passes).

---

### Story 26.2: Core LLM Streaming Extraction (`LlmStreamingPort`, All 3 Text Adapters Preserved), Unified Localized `AssistantPromptBuilder`, Removal of Prod Test Branches & `< 300 L` Splits

As a Tech Lead (`Amelia`),
I want to extract LLM streaming, prompt building, and usage telemetry out of `apps/api/routers/` into `orcia_core` ports/adapters, unify the three prompt builders into one localized `AssistantPromptBuilder`, derive default hats from user profiles, remove production `testclient`/`pytest` branches, and split oversized harness files,
So that the harness complies with `AD-1` / `AD-19` and provides a clean core foundation for persistence and convergence.

**Lot:** 2 — Core Foundations. **Dependencies:** `26.1`. **Agent:** 1 dedicated `bmad-dev-worker` (`flash`, `R9`).
**Findings covered:** `H-24`, `H-25`, `H-30` (P2 hardcoded literals), `H-31`, `H-34`.
**CAPs covered:** `CAP-069`, `CAP-074`, `CAP-076`.
**Impacted files:** `apps/api/src/orcia_api/routers/assistant_llm_{bridge,prompts,providers,resolver,gemini_adapter}.py`, `assistant_background_turns.py`, `_assistant_usage_telemetry.py`, `_assistant_workspace_context.py`, `agents_and_skills.py`, `apps/api/src/orcia_api/dependencies/portal_and_assistant.py`, `core_and_lifespan.py`, `packages/orcia-core/src/orcia_core/ports/`, `packages/orcia-core/src/orcia_core/orchestration/assistant_harness.py`, `assistant_governance.py`, `assistant_three_speed_router.py`, `assistant_agent.py`, `assistant_citations_and_v5_guard.py`, `assistant_folders_and_sharing.py`, `apps/api/src/orcia_api/schemas/assistant.py`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/26-2-core-llm-streaming-extraction-and-unified-prompt-builder-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** ~2,100 L of LLM bridge, prompt, provider, and telemetry logic currently inside `apps/api/routers/`
**When** extracted to `orcia_core`
**Then** `LlmStreamingPort` lives in `orcia_core/ports/` (zero SDK imports) with concrete `httpx` adapters in `orcia_core` preserving all **3** text/reasoning streaming adapters (OpenAI-compatible, Anthropic, and native Gemini `CAP-076`, `R7`) following `embedding_httpx.py`; routers become thin HTTP handlers; `orcia_api` imports zero `_internal` modules; `orcia_core` imports zero `testing.cassette_llm`; inter-router import `agents_and_skills.py` → `assistant_llm_bridge` is replaced by the port; and `lint-imports` holds `5/5` contracts.

**Given** the three existing prompt builders (`AssistantHarness.assemble_prompt`, `build_assistant_system_instructions`, `assemble_five_layers_preview`)
**When** unified into `AssistantPromptBuilder`
**Then** a single builder assembles all 5 layers (Layer 1 immutable), localized cleanly via `fr`/`en` dictionaries (`0` French leakage when `locale="en"`), resolving default `active_hat` from `user.human_profile_archetype` (never RBAC `PLATFORM_ADMIN`), and replacing hardcoded `pack_key`, pilot URIs, and synthetic latencies with real values and `perf_counter()` timings.

**Given** production harness source files
**When** audited
**Then** zero `client_host == "testclient"`, `"pytest" in sys.modules`, or `ORCIA_FORCE_LIVE_LLM_IN_TESTS` branches remain (Cassette LLM injected strictly at test Composition Root), and all touched Python/TS harness files stay `<= 300` lines.

---

### Story 26.3: Turn Reliability — Redis Registry `(workspace, user, turn_id)`, Graceful Drain & Liveness Key, Cursor SSE Reattachment, 100% Async Loop & Rate Limiting

As a Multi-Tab Assistant User and Platform Operator,
I want every turn to be tracked in Redis, cleanly stoppable with partial FinOps accounting, resumable via SSE cursor across workers and F5, and executed on a strictly non-blocking async event loop with bounded retries and rate limits,
So that concurrent tabs never overwrite each other, API pods remain responsive, and `--workers > 1` works reliably.

**Lot:** 3 — Reliability & Persistence (1st of 3 sequential stories on `workspace: "inherit"`, `R9`). **Dependencies:** `26.2`. **Agent:** 1 dedicated `bmad-dev-worker` (`flash`, `R9`).
**Findings covered:** `H-10`, `H-11`, `H-20`, `H-21`, `H-23`, `H-33`.
**CAPs covered:** `CAP-069`, `CAP-075`.
**Impacted files:** core turn orchestrator from `26.2`, `apps/api/src/orcia_api/routers/assistant_workspace.py`, `assistant.py`, `packages/orcia-core/src/orcia_core/orchestration/step_executors.py`, `assistant_agent.py`, `packages/orcia-core/src/orcia_core/rag/context_adapters.py`, `hybrid_rag_service.py`, `apps/api/src/orcia_api/dependencies/core_and_lifespan.py` (`SIGTERM` drain), `tests/integration/`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/26-3-turn-reliability-redis-registry-async-loop-and-rate-limit-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** two concurrent turns started on the same workspace by different tabs or users
**When** they execute inside `apps/api` (`R1`)
**Then** each turn is indexed in Redis by `(workspace_id, user_id, turn_id)` with TTL and a refreshed liveness key; active `asyncio.Task` handles are held in a tracked set with `add_done_callback` (zero task overwrite or premature GC); event streams are bounded in Redis Streams with post-completion TTL; module-level `ACTIVE_WORKSPACE_TURNS` is deleted; and `SIGTERM` triggers bounded graceful draining capped by the profile wall-clock budget (crashed/orphaned turns emit `stream_error` `ERR_ASSISTANT_TURN_INTERRUPTED` on reattach without auto-retry, no Dramatiq worker).

**Given** a running turn where the user invokes `stop` or reloads/reconnects SSE across workers
**When** `stop` or `GET …/stream?after=<cursor>` runs
**Then** `stop` propagates via Redis, emits terminal `turn_stopped`, and persists partial streamed tokens in `audit_ledger` inside `finally` (`turn_id` idempotency preserved); cursor reattachment replays missed events without duplicates; and a 2-instance integration test sharing Redis verifies cross-worker `stop`, reattachment, and orphan crash detection.

**Given** all execution and RAG paths
**When** turns run
**Then** zero blocking calls hit the event loop (remove `ThreadPoolExecutor(...).result()`, convert SSE generators and hybrid RAG search to `async`, remove `if loop.is_running(): pass`); provider/empty-stream failures emit structured `stream_error` (RFC 9457 + `trace_id`); bounded pre-first-byte retry (2x backoff on `429/502/503`) + inter-chunk idle timeout apply; and Redis sliding-window rate limits + per-user concurrency semaphores enforce `HTTP 429` RFC 9457.

---

### Story 26.4a: Redis Thread Turn Locks, Outbox Domain Event Emission, Hub Snapshot Invalidation, Prompt-Cache Removal (`R6`) & Alembic DDL Migration

As a Platform Operator,
I want thread turn locks and AI Hub snapshots coordinated via Redis and invalidated cleanly, per-request DDL migrated to Alembic, and dead in-memory prompt-cache machinery removed pending latency measurement (`R6`),
So that multi-worker coordination is consistent without degrading PostgreSQL on every request or maintaining premature cache invalidation complexity.

**Lot:** 3 — Reliability & Persistence (2nd of 3 sequential stories on `workspace: "inherit"`, `R9`). **Dependencies:** `26.3`. **Agent:** 1 dedicated `bmad-dev-worker` (`flash`, `R9`).
**Findings covered:** `H-09` (thread locks), `H-19` (resolved by removal), `H-22` (Outbox), `H-32`, `H-35`.
**CAPs covered:** `CAP-071`, `CAP-073`.
**Impacted files:** `packages/orcia-core/src/orcia_core/orchestration/assistant_three_speed_router.py`, `_assistant_folders_sync.py`, `assistant_folders_and_sharing.py`, `apps/api/src/orcia_api/dependencies/portal_and_assistant.py`, `_rag_availability_guards.py`, `apps/api/src/orcia_api/routers/assistant_llm_resolver.py` (or core successor), `infra/migrations/versions/`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/26-4a-redis-thread-locks-outbox-hub-invalidation-and-alembic-ddl-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** thread turn locking and legacy prompt-cache code (`R6`)
**When** the application boots from the real Composition Root
**Then** thread locks use `RedisThreadTurnLock` (`SET NX EX`) wired to `app.state.redis_client` (`InMemory*` kept solely under `tests/unit/fakes/`); `InMemoryPromptCacheStore`, `AssembledPromptCachePort`, and forged `outbox_event_id` generation are **deleted** (no Redis assembled-prompt cache or Outbox cache consumer built under measure-first policy `R6`, tracked via `ACTION_ITEM-26.3`).

**Given** AI Hub updates and harness domain events
**When** models change or assistant events occur
**Then** `platform_setup_snapshot` uses a bounded Redis/local TTL invalidated upon AI Hub mutations, and harness lifecycle events emit through `SqlDomainEventsOutboxRepository` (`domain_events_outbox`).

**Given** `ensure_ai_model_mappings_schema_on_postgres18` and `_rag_availability_guards.py`
**When** a turn executes
**Then** zero runtime `CREATE`/`ALTER`/`CREATE INDEX` DDL runs per request (schema managed by an incremental raw-SQL Alembic revision with tested `upgrade()`/`downgrade()`), and zero ephemeral `httpx.AsyncClient()` instances are created (all reuse `app.state.http_client`).

---

### Story 26.4b: PG18 Persistence for Mode A 3-Level Governance, Turn Feedback, Folder Metadata & `audit_ledger` Phantom Citation Logging — Mode B Deleted & Drafts Omitted (`R2`, `R5`)

As a Workspace Admin (`Claire`) and Assistant User,
I want Mode A 3-level governance instructions, turn feedback, and folder attachments/tags persisted in PostgreSQL 18, phantom citations logged to the append-only `audit_ledger`, and unused RAM-only Mode B routes removed,
So that assistant configuration, feedback, and compliance logs survive restarts and multi-worker deployments without creating orphan SQL tables.

**Lot:** 3 — Reliability & Persistence (3rd of 3 sequential stories on `workspace: "inherit"`, linear Alembic `down_revision` chained on `26.4a`, `R9`). **Dependencies:** `26.4a`. **Agent:** 1 dedicated `bmad-dev-worker` (`flash`, `R9`).
**Findings covered:** `H-09` (governance, phantom audit, feedback, folders), `H-37` (partial: `BUG-E2E-01b`).
**CAPs covered:** `CAP-070`, `CAP-072`, `CAP-073`.
**Impacted files:** `infra/migrations/versions/`, `packages/orcia-core/src/orcia_core/orchestration/assistant_governance.py`, `assistant_citations_and_v5_guard.py`, `assistant_folders_and_sharing.py`, `_internal/_sql_assistant_folders_queries.py`, new `_internal/sql_assistant_*.py`, `apps/api/src/orcia_api/dependencies/portal_and_assistant.py`, `apps/api/src/orcia_api/routers/assistant_workspace.py`, `assistant_workspace_governance.py`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/26-4b-pg18-persistence-mode-a-governance-feedback-and-folders-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** a reset database (`pnpm db:reset`) upgraded with Story `26.4b` Alembic migrations (chained linearly on `26.4a`, single `alembic heads`)
**When** `upgrade()` and `downgrade()` execute
**Then** Mode A governance (`USER`, `WORKSPACE`, `TEAM`) persists in existing `workspace_customization_overrides` (migration `0003`); new `UUIDv7` raw-SQL table `assistant_turn_feedback` (`UNIQUE (turn_id, user_id)` upsert) stores turn feedback; `assistant_folders` adds `working_attachments_uris JSONB` and `evidence_tags TEXT[]`; and **neither** a Mode B studio table (`R2`, `ACTION_ITEM-26.1`) **nor** a citation drafts table (`R5`) is created.

**Given** RAM-only Mode B routes and `_phantom_audit_log` (`R2`, `R4`, `R5`)
**When** the story completes
**Then** `POST /api/v1/assistant/governance/mode-b/{save,reset}` (zero UI callers), their schemas, SDK entries (`0-diff`), and `_studio_graphs` RAM state are deleted; `GET /governance` returns Mode A configuration only; `AssistantCitationAndV5GuardService._phantom_audit_log` RAM list is replaced by idempotent `audit_ledger` events (`ASSISTANT_PHANTOM_CITATION_PURGED` via `SqlAuditLedgerService`); and `execute_artifact_card_action` / `_saved_drafts` remain temporarily intact solely to keep E2E spec `21` (`/artifacts/action`) passing until deleted together in `26.7`.

**Given** Mode A updates, turn feedback, folder attachments/tags, and phantom citation events
**When** verified on the real Composition Root `create_app()` (zero `dependency_overrides`) after cold cache eviction
**Then** PG18 `SELECT` integration tests prove full durability across restarts, zero business state remains in `AssistantFourLevelGovernanceService` or `_folder_meta`, and `test_zero_orphan_sql_adapters_audit.py` passes with zero orphan SQL adapters.

---

### Story 26.5: Real Context — PG18 Ontology Relevance (`ProfileSemanticTranslator` & Axioms), Async `SqlHybridRagRepository`, Active Blackboard Snapshots, Server `EvidenceTable`, `assistant_thread_messages` & Token Budget Trimmer

As a Business User (`Thomas`, `Lucas`),
I want the assistant to reason over my workspace's real PG18 ontology (relevant concepts, axioms, profile-adapted terms), real indexed workspace sources (hybrid PG18 RAG), and active Blackboard snapshots within a controlled token budget,
So that responses are grounded in verifiable organizational truth rather than test seeds or the first eight arbitrary concepts.

**Lot:** 4 — Real Context. **Dependencies:** `26.4b`. **Agent:** 1 dedicated `bmad-dev-worker` (`flash`, `R9`).
**Findings covered:** `H-12`, `H-13`, `H-18` (server history & budget), `R6` prompt-assembly latency measurement.
**CAPs covered:** `CAP-022`, `CAP-190`.
**Impacted files:** `AssistantPromptBuilder` (from `26.2`), `packages/orcia-core/src/orcia_core/ontology/`, `packages/orcia-core/src/orcia_core/rag/`, `apps/api/src/orcia_api/dependencies/core_and_lifespan.py`, `_core_providers.py`, `apps/api/src/orcia_api/routers/_assistant_workspace_context.py` (or successor), `infra/migrations/versions/` (`assistant_thread_messages`, `D4`).
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/26-5-real-context-ontology-hybrid-rag-blackboard-and-context-budget-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** a workspace whose PG18 ontology defines L1–L4 concepts and axioms
**When** prompt Layer 2 is assembled
**Then** it queries `OntologyGovernanceService.resolve_snapshot(workspace_scope_id=…)`, ranks concepts by lexical (+ vector when embedding is active) relevance to the query, applies `ProfileSemanticTranslator` for `active_hat`, injects applicable axioms, removes `list(concepts)[:8]` on an empty bundle, and passes a golden ontology eval (`0 $`).

**Given** a workspace with indexed sources (with an active `embedding` model, **or without** one per `25-5`)
**When** federated context (`N3`/`N4`) is built
**Then** async `SqlHybridRagRepository.search_hybrid_rrf` feeds the assistant pipeline when an embedding model is active, and cleanly skips vector retrieval without error when none exists (`get_optional_embedding_port`); `build_seeded_rag_service()` is disconnected from production; a real SQL provider supplies active Blackboard snapshots (replacing `lambda _ws: ()`); and a server `EvidenceTable` (filtered by `READ_SOURCE` & `CONFIDENTIAL_RESTRICTED`, sorted by authority and freshness, `[STALE_WARNING]`) feeds Layer 4.

**Given** a long conversation thread and a model with known context window and `max_tokens_budget`
**When** multi-turn messages are built and assembly latency is measured
**Then** Alembic migration adds `assistant_thread_messages` (`UUIDv7` PK, `thread_id` FK `ON DELETE CASCADE`, `turn_id`, `role CHECK IN ('user', 'assistant')`, `content`, `citation_map JSONB`, `token_count`, `created_at`, index `(thread_id, created_at)`); history is loaded from PG18 (eliminating `" | "` splitting of `thread_summary`) and trimmed within `max_tokens_budget`; and `perf_counter()` records SQL prompt-assembly latency (`R6` baseline for `ACTION_ITEM-26.3`).

---

### Story 26.6a: `LlmStreamingPort` Native Tool Calls on 2 Dialects (OpenAI-Compatible & Anthropic), `supports_tools` Flag & Loop Budgets

As an Agentic Loop Developer,
I want the streaming port to parse and re-inject native `tool_calls` cleanly across OpenAI-compatible and Anthropic dialects, persist each model's `supports_tools` capability, and enforce iteration, token, and wall-clock budgets,
So that tool execution builds on a deterministic, bounded transport without breaking native Gemini text streaming.

**Lot:** 5 — Tool Loop. **Dependencies:** `26.5`. **Agent:** 1 dedicated `bmad-dev-worker` (`flash`, `R9`).
**Findings covered:** `H-03` (transport), `H-04`, `H-27` (dialects).
**CAPs covered:** `CAP-074`, `CAP-076`, `CAP-190` (`supports_tools` discovery).
**Impacted files:** `LlmStreamingPort` & adapters (from `26.2`), AI Hub (`packages/orcia-core/src/orcia_core/orchestration/_internal/sql_ai_model_*.py`, `apps/api/src/orcia_api/routers/ai_models_hub.py`), `packages/orcia-core/src/orcia_core/testing/` (cassettes), `infra/migrations/versions/` (`supports_tools` column).
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/26-6a-llm-streaming-port-tool-calls-and-loop-budgets-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** recorded streamed and non-streamed payloads for **OpenAI-compatible** (`delta.tool_calls`, covering OpenAI, vLLM, Ollama `/v1`, Azure) and **Anthropic** (`tool_use` / `input_json_delta`), per `R7`
**When** processed by `LlmStreamingPort` adapters
**Then** the port emits typed `ContentDelta | ReasoningDelta | ToolCallDelta | Usage | Finish` events, reassembles arguments by `id`/index, stops on `finish_reason=tool_calls` / `stop_reason=tool_use`, formats tool results cleanly (`role: "tool"` / `tool_result`), preserves `tools` on OpenAI 404 fallback, and preserves `reasoning`/`content` separation (with all 3 text streaming adapters including native Gemini `CAP-076` intact).

**Given** a model configured in the AI Models Hub
**When** 0-token discovery or connection testing runs
**Then** `supports_tools` is persisted in PG18 with manual `PLATFORM_ADMIN` override; native Gemini REST and non-`/v1` native Ollama endpoints default to `supports_tools=false` (`ACTION_ITEM-26.4`); `supports_tools=false` models never receive `tools` (zero XML/ReAct prompt emulation), expose Speed 2/3 as unavailable, and return `HTTP 422 ERR_MODEL_TOOLS_UNSUPPORTED` (RFC 9457) if Speed 2/3 is requested via API (`D5`).

**Given** a multi-step tool loop hitting profile budgets (iterations, tokens, wall-clock duration)
**When** any limit is reached
**Then** execution terminates cleanly with forced synthesis or explicit `stream_error` (`TurnBudgetExceededError`, RFC 9457), and extended `DeterministicCassetteLLM` cassettes validate both tool-calling dialects at `>= 90%` unit coverage.

---

### Story 26.6b: Governed Assistant Tool Router — Dynamic PG18/RBAC/MCP Catalog, `PermissionBroker` → Lock V5 / Human Anchor → Sandboxed Executor → `audit_ledger` & Outbox, Idempotency & Anti-Injection

As a SecOps Lead (`Sophie`) and Tool-Enabled User,
I want every assistant tool derived from an authorized workspace catalog and routed sequentially through Permission Broker, Lock V5, deterministic human-anchor guards, timeout-capped sandboxed execution, secret scrubbing, and `audit_ledger`,
So that Speed 2/3 can investigate reliably (surgical reads, RAG, ontology, skills, read-only connectors) without ever writing directly to enterprise systems or drafting human-anchored deliverables.

**Lot:** 5 — Tool Loop. **Dependencies:** `26.6a`. **Agent:** 2 distinct `bmad-dev-worker` (`flash`: Impl + Independent Verification) + `bmad-architect-worker` (`pro` review, `R9`).
**Findings covered:** `H-03` (execution), `H-22` (per-tool ledger), `H-27` (catalog), `H-28`, `H-29`.
**CAPs covered:** `CAP-160`, `CAP-022`; new **`CAP-260`** ("Governed Tool Loop for Mon Assistant") created in `verification: api` (`D9`).
**Impacted files:** `packages/orcia-core/src/orcia_core/ports/` (`AssistantToolExecutorPort`), `packages/orcia-core/src/orcia_core/agents/` (`GovernedAssistantToolRouter`, `ASSISTANT` profile), `packages/orcia-core/src/orcia_core/permissions/broker.py`, `orchestration/assistant_citations_and_v5_guard.py`, `orchestration/human_anchors_and_arbitration.py`, `orchestration/agents_and_skills_manager.py`, `packages/orcia-connectors/src/orcia_connectors/surgical.py`, `reflexive_write_gate.py`, `docs/product/capabilities.yaml`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/26-6b-governed-assistant-tool-router-broker-v5-anchors-and-audit-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** a user in a workspace
**When** the turn's tool catalog is built
**Then** it includes only authorized tools: the 4 `SurgicalContextExplorer` primitives (`#Lstart-end`), `kb.search` (when RAG is active), ontology lookup, PG18 `enabled_in_workspace` skills with real `input_parameters`, and MCP-exposed tools filtered by `mcp_tool_permissions` + RBAC; the hardcoded single tool and 10-item RAM skill cap are removed.

**Given** any LLM-requested tool call
**When** handled by `GovernedAssistantToolRouter`
**Then** it enforces: `PermissionBrokerService` (`passthrough`, `READ_SOURCE`) → Lock V5 & deterministic per-tool anchor guard (SI write or `human_authored_required=true` → rejected or surfaced as `approval_required` → `CONTINUE_IN_PROCESS`, with `HumanArbitrationRequested` written to `domain_events_outbox`) → executor (Tier 1/2 sandbox for skills) under `asyncio.wait_for` → `scrub_connector_secrets` → `audit_ledger` `ASSISTANT_TOOL_INVOKED` / `ASSISTANT_TOOL_DENIED` (masked args, verdict, latency, cost), emitting `tool_call`, `tool_result`, and `approval_required` SSE events.

**Given** a replayed call (`idem:{turn_id}:{iteration}:{tool_call_id}`), injected prompt directives inside tool output, or attempt to bind `ConnectorReflexiveWriteGateAdapter`
**When** processed
**Then** duplicate calls execute once; tool outputs are wrapped in delimited untrusted blocks that cannot alter Layer 1 or guards (verified by `assistant_tool_output_injection.jsonl` golden eval); `ASSISTANT` profile tests prove `ConnectorReflexiveWriteGateAdapter` is unreachable; lexical `HUMAN_ANCHOR_WRITE_REFUSAL` heuristic is replaced by deterministic tool-level gating; and `CAP-260` is added to `capabilities.yaml` (`verification: api`).

---

### Story 26.7: Unified Turn Engine Convergence (`AssistantTurnEngine`), Atomic Direct UI & E2E Cutover Without Facade (`R4`), Server Citations (`citation_map`) & Deletion of Legacy Routes

As a User of "Mon Assistant",
I want every message to trigger a single, end-to-end governed turn execution with server-verified citations and direct UI cutover (zero parallel double execution, zero strangler facade),
So that displayed answers reflect ORCIA's actual guarantees without double LLM spend or legacy surface duplication.

**Lot:** 6 — Convergence. **Dependencies:** `26.6b`. **Agent:** 2 distinct `bmad-dev-worker` (`flash`: Impl + Independent Verification) + mandatory `bmad-architect-worker` (`pro` review, `R9`).
**Findings covered:** `H-01`, `H-02`, `H-09` (`_saved_drafts` deleted), `H-14` (server).
**CAPs covered:** `CAP-022`, `CAP-071`, `CAP-072`, `CAP-160`, `CAP-260`.
**Impacted files:** `packages/orcia-core/src/orcia_core/orchestration/` (`AssistantTurnEngine`, `assistant_three_speed_router.py`, `assistant_agent.py`, `assistant_citations_and_v5_guard.py`), `packages/orcia-core/src/orcia_core/agents/reflexive_runtime.py`, `apps/api/src/orcia_api/routers/assistant_turns.py` (new), `assistant_workspace.py`, `assistant_workspace_citations.py`, `assistant.py`, `mcp_and_test_bench.py` / `governed_mcp_exposure.py` (`assistant.ask`), `apps/api/src/orcia_api/schemas/assistant_turns.py`, `packages/api-client/`, `infra/migrations/versions/` (`reflexive_execution_sessions.execution_profile`), `apps/web/src/features/inbox/` (`useInboxPanelController.ts`, `useAssistantStreamingTurn.ts`, `assistantBackgroundStreamStore.ts`, `inboxTurnSyncHelpers.ts`), `apps/web/e2e/` (`02`, `12`, `16`, `21`).
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/26-7-unified-turn-engine-convergence-direct-cutover-and-citations-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** a Speed 1, Speed 2, or Speed 3 turn submitted via `POST /api/v1/assistant/turns`
**When** executed by `AssistantTurnEngine` inside `apps/api` (`R1`)
**Then** Speed 1 takes the single-shot fast-path (`TTFT p95 < 1.2 s` and prompt-assembly p95 `< 50 ms` verified in real PG18 Layer 2 without a prompt cache per `R6`, post-first-byte persistence, `turn_completed.low_evidence` set deterministically on empty `EvidenceTable`, `parent_turn_id` supported for linked Speed 2 "Deepen" turns per `R3`), Speed 2/3 run on `NonDeterministicReflexiveRuntime` with `execution_profile = 'ASSISTANT'` (fixed `N1–N5` phases, `PROCESS` default unchanged and `16-2` / `process_dispatcher` green), and exactly one LLM execution path triggers per user turn (ending parallel `three-speed` + `reflexive` calls).

**Given** a synthesizing response and MCP `assistant.ask`
**When** the response completes
**Then** `AssistantCitationAndV5GuardService.verify_and_sanitize_citations` runs server-side **before** `turn_completed` against the server `EvidenceTable`, strips and logs ungrounded `[Sn]`/`[Gn]`/`[On]` tags to `audit_ledger` (`ASSISTANT_PHANTOM_CITATION_PURGED`), and emits `citation_map` SSE; golden evals prove `0` phantom citations on the live path; and `assistant.ask` (`POST /mcp/spaces/{ws}/invoke`, `D7`) executes synchronously via `AssistantTurnEngine` Speed 1 read-only under all 7 MCP locks + `QuotaGuard` + `ScopeAccessGuard` + `CitationGuard`.

**Given** `apps/web` is the sole turn API consumer (`R4`)
**When** direct cutover completes in one atomic commit
**Then** `apps/web` turn transport (`POST /assistant/turns`, `GET …/stream?after=<cursor>`, `GET /assistant/turns/active`, `POST /assistant/turns/{id}/{stop,feedback}`) and Playwright specs `02`, `12`, `16`, `21` migrate directly to the canonical v2 routes (`ACTION_ITEM-26.2` tracks any future facade); legacy routes `/three-speed/*` (`stream`, `turn`, `active-turn`, `stop`, `feedback`, `invalidate-cache`), `/chat`, `/chat/stream`, `/citations/verify-turn`, and `/artifacts/action` — together with `_saved_drafts` and `execute_artifact_card_action` (`R5`) — are **deleted** with their schemas, tests, and OpenAPI SDK entries (`0-diff`).

---

### Story 26.8: `CONTINUE_IN_PROCESS` Wired to Durable DBOS + PG18 & Human Anchors (`WAITING_FOR_HUMAN_ANCHOR`), Direct Deletion of `/workflows/save-and-launch`

As a Human-Led Contributor,
I want assistant proposals requiring SI writes or human-authored deliverables to launch durable DBOS + PG18 processes that pause at human anchors and Gates,
So that the assistant can never bypass `AD-2` / `AD-3` / V5 and conversation-to-process continuity is fully auditable.

**Lot:** 6 — Convergence. **Dependencies:** `26.7`. **Agent:** 1 dedicated `bmad-dev-worker` (`flash`, `R9`).
**Findings covered:** `H-05`.
**CAPs covered:** `CAP-022`, `CAP-160`, `CAP-260`.
**Impacted files:** `packages/orcia-core/src/orcia_core/orchestration/assistant_agent.py` (`save_and_launch_workflow`), `engine.py`, `human_anchors_and_arbitration.py`, `orchestration_sql_wiring.py`, `apps/api/src/orcia_api/routers/assistant.py`, `assistant_turns.py`, `assistant_workspace_folders.py`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/26-8-continue-in-process-dbos-pg18-and-human-anchors-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** an `approval_required` turn proposal approved via `POST /api/v1/assistant/turns/{id}/approve` or a process launched via `POST /api/v1/assistant/folders/{id}/launch-process` containing a `human_authored_required: true` step
**When** launched
**Then** execution runs on durable DBOS + PG18 (`workflow_runs`, `step_executions`, `blackboard_snapshots`, `domain_events_outbox` verified by SQL `SELECT`), initializes anchored steps in `WAITING_FOR_HUMAN_ANCHOR`, halts at the first `WAITING_*` state, and rejects unsigned commits with `HTTP 422 ERR_HUMAN_ANCHOR_REQUIRED`.

**Given** legacy `POST /api/v1/assistant/workflows/save-and-launch` (`D6`, `R4`)
**When** the story completes
**Then** the route and its in-memory `WorkflowEngineService` execution path are **deleted directly** with SDK entries (`0-diff`, zero `deprecated` window), and real Composition Root PG18 integration tests verify turn → approval → human-anchor pause → resume after signature.

---

### Story 26.9: UI & SDK Wiring — Mode A Governance API, `citation_map` Pills, PG18 Thread History, Tool Trace, Approval Cards, "Deepen" Button & F5 Cold Survival

As a User of "Mon Assistant",
I want the workspace screen to rely exclusively on the unified backend APIs for Mode A governance, server citations, PG18 thread history, tool traces, approval cards, and one-click "Deepen", without local business state,
So that what I see matches persisted server truth and survives hard refreshes.

**Lot:** 7 — UI & Closure. **Dependencies:** `26.7`, `26.8`. **Agent:** 1 dedicated `bmad-dev-worker` (`flash`, `R9`).
**Findings covered:** `H-14` (UI), `H-18` (UI), `H-26`.
**CAPs covered:** `CAP-070`, `CAP-071`, `CAP-072`, `CAP-073`, `CAP-260`.
**Impacted files:** `apps/web/src/features/inbox/` (`useInboxPanelController.ts`, `useAssistantStreamingTurn.ts`, `assistantBackgroundStreamStore.ts`, `assistantTurnPayloadHelper.ts`, `assistantAutocompleteHelpers.ts`, `inboxCitationHelpers.ts`, `InboxAuxiliaryPanels.tsx`, `index.tsx`), `packages/ui/src/` (`AssistantToolCallTrace`, `AssistantApprovalRequiredCard`, Deepen button, `supports_tools=false` notice), `apps/web/src/i18n/locales/{fr,en}.ts`, `apps/api/src/orcia_api/routers/assistant_workspace_folders.py`, `packages/api-client/`, `apps/web/e2e/`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/26-9-ui-and-sdk-wiring-mode-a-citations-history-and-deepen-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** a user on `/assistant`
**When** sending turns, refreshing (F5), and navigating threads
**Then** history and `thread_id` rehydrate from `GET /api/v1/assistant/threads/{id}/messages` in PG18 (`0` `localStorage` history sent in payloads), duplicate route `POST /threads/{id}/turns` is **deleted** (`R4`, `0-diff` SDK), `AssistantToolCallTrace` renders jargon-free tool activity, and after a Speed 1 turn UI renders a localized **"Deepen"** button (visible when `supports_tools=true`, emphasized when `low_evidence`, `R3`) creating a linked Speed 2 turn (`parent_turn_id`) verified by `RouterProvider` Vitest tests and Playwright `22-assistant-tool-loop-approval-and-reattach.spec.ts` (`reloadColdFromPg`).

**Given** citations, approval proposals, or a model with `supports_tools=false`
**When** rendered
**Then** citation pills come exclusively from server `citation_map` (deleting `filterUsedRagSourcesForTurn` and client-fabricated `[Sn]`/`REFERENCE`/`FRESH` logic), `AssistantApprovalRequiredCard` routes to Process Gates, Speed 2/3 controls disable cleanly with localized microcopy, all strings live in `i18n/locales/{fr,en}.ts` (French default), and zero-dead-buttons + `data-testid` sync audits pass.

**Given** Mode A governance controls and `launch-process`
**When** modified by the user
**Then** reads/writes use `@orcia/api-client` (PG18 Mode A endpoints, `POST /folders/{id}/launch-process`, `assembledLayers` populated from server, zero business `localStorage`), **no Mode B Studio UI** is shipped (`R2`, `ACTION_ITEM-26.1`, studio trigger removed without leaving dead buttons), and cold-PG18 F5 survival holds end-to-end.

---

### Story 26.10: Golden Evals, Red-Team & Multi-Worker Verification, Anti-Regression AST Audits, 0-Uncalled Route Check, `runtime` Promotion & Epic 26 Closure

As a Tech Lead and QA Lead,
I want to lock all Epic 26 guarantees with golden evals, security/red-team tests, multi-worker Redis integration tests, AST audits, and honest capability promotion after E2E proof,
So that harness debt cannot regress and Epic 26 closes cleanly across all `AD-17` verification layers.

**Lot:** 7 — UI & Closure. **Dependencies:** `26.9`. **Agent:** 1 `bmad-dev-worker` (`flash`) + mandatory final `bmad-architect-worker` (`pro`) closure gate (`R9`).
**Findings covered:** `H-36`, `H-37`.
**CAPs covered:** `CAP-022`, `CAP-069`..`CAP-076`, `CAP-160`, `CAP-190`, `CAP-260`.
**Impacted files:** `tests/evals/golden/` (`assistant_tool_loop.jsonl`, `assistant_anchor_and_v5.jsonl`, `assistant_tool_output_injection.jsonl`), `tests/security/`, `tests/integration/`, `tests/unit/` (AST audits), `docs/product/capabilities.yaml`, `docs/implementation-artifacts/sprint-status.yaml`, `docs/implementation-artifacts/tech-lead-reports/2026-11-21-audit-harnais-assistant-et-plan-remediation-tech-lead-report.md`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/26-10-golden-evals-red-team-multi-worker-and-epic-26-closure-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** Stories `26.0`–`26.9` implemented
**When** the full verification suite runs
**Then** golden evals (`assistant_tool_loop.jsonl`, `assistant_anchor_and_v5.jsonl`, `assistant_tool_output_injection.jsonl`, `0` phantom citations) pass at `0 $` via `DeterministicCassetteLLM`; security tests verify cross-workspace IDOR (`UUID` + slug), pre-stream `403` Observer, `ORCIA_LLM_ALLOWED_PRIVATE_HOSTS` + DNS-rebinding SSRF, Day-0 `platform-setup-state` non-leak, and `CONFIDENTIAL_RESTRICTED` masking; 2-instance API + Redis integration tests verify cross-worker `stop`, cursor reattachment, and `ERR_ASSISTANT_TURN_INTERRUPTED` crash detection (`R1`); and new AST audits forbid module-level mutable state, unguarded `/assistant/*` mutation routes, and `testclient` branches in `src/`.

**Given** route deletions across `26.4b`–`26.9` and open legacy items (`H-36`, `H-37`)
**When** closure audits execute
**Then** an endpoint inventory audit confirms `0` assistant route without an active UI or documented MCP caller (`0` legacy `deprecated` routes), `require_rag_available` and `dependency_overrides` are absent from assistant tests, `BUG-E2E-01b` and `AUTH-01` are closed (or explicit remaining scope is tracked cleanly), and the `2026-11-21` audit report Section 3 records final status for `H-01..H-38`.

**Given** Stories `26.0`–`26.9` are `done` and Playwright `02`, `12`, `16`, `21`, `22` pass on the real unified engine
**When** Epic 26 closes
**Then** `CAP-022`, `CAP-070`, `CAP-072`, and `CAP-260` promote to `verification: runtime` in `docs/product/capabilities.yaml`, all DoD exit metrics hold (`1` LLM path/turn, `1` prompt builder, `0` business RAM state, `0` harness file `> 300 L`, `>= 90%` unit coverage), `ruff`, `mypy --strict`, `lint-imports` (`5/5`), `pytest --cov-fail-under=90`, `pnpm turbo run lint typecheck test`, `lint_spine.py` (`0 findings`), and `pnpm site:sync && pnpm site:check` pass, and `epic-26` becomes `done`.

---
