# Story 26.0 — ADR Unified Assistant Turn Engine (`AD-25`), `AD-15`/`AD-21`/`AD-24` Updates, SSE v2 Contract & Env-Var SSRF Policy

- **Date:** 2026-11-21
- **Story / Sprint Key:** `26-0-adr-unified-turn-engine-sse-v2-and-ssrf-policy` (`Epic 26`)
- **Capabilities:** `none (doc)` — classification: `doc` (architectural framing for `CAP-022`, `CAP-069`, `CAP-070`, `CAP-071`, `CAP-072`, `CAP-073`, `CAP-074`, `CAP-075`, `CAP-076`, `CAP-160`, and future `CAP-260` implemented across Stories `26.1`–`26.10`)
- **Author / Context:** Principal Architect (`Winston` / `bmad-architect-worker`) — ratify consolidated Epic 26 decisions `D1–D11` as amended by `R1–R9`, resolve `H-38` GitNexus staleness/index verification, and freeze the Spine (`AD-25`, `AD-15`, `AD-21`, `AD-24`), ERD (`architecture.md` §4 & §8), and canonical REST v2 / SSE v2 contracts (`architecture.md` §3.6.3) covering `AD-2`, `AD-3`, `AD-6`, `AD-12`, `AD-15`, `AD-19`, `AD-21`, `AD-24`, `AD-25`, `FR-33`, and Speed 1 `TTFT p95 < 1.2 s`.
- **Associated Commits:** `none` (uncommitted working tree on branch `feat/epic-26-assistant-harness-debt-remediation`; coordinator commits after independent verification)

---

## 1. Requirements & Tech Lead Impact Analysis (Analyse du Besoin)

### 1.1 Context & Problem Statement
- **Audit Baseline (`H-01..H-38`):** The comprehensive audit recorded in [`2026-11-21-audit-harnais-assistant-et-plan-remediation-tech-lead-report.md`](./2026-11-21-audit-harnais-assistant-et-plan-remediation-tech-lead-report.md) revealed 38 findings (14 P0 [13 confirmed, 1 partial], 16 P1, 6 P2, 2 P3):
  - **Three divergent execution paths (`H-01`, `H-02`):** The UI calls `/api/v1/assistant/three-speed/stream` (bypassing `AssistantHarness`, RAG, server citation checks, and `AD-3` human anchor enforcement) while firing `POST /api/v1/executions/reflexive` in parallel in `deep`/`@agent` mode (double LLM execution), leaving the 5-node DAG (`AssistantAgentService` on `/chat*`) with zero UI callers.
  - **Broken/mocked tool loop & bypassed anchors (`H-03`, `H-04`, `H-05`, `H-27..H-29`):** Non-streaming turns inject synthetic `"Workspace context verified"` results; streaming turns discard `tool_calls` deltas; `save_and_launch_workflow` runs `human_authored_required: true` steps in memory without `AD-3` signatures or DBOS persistence.
  - **Security & isolation gaps (`H-06..H-08`, `H-15..H-17`, `H-23`):** `READ_ONLY_OBSERVER` executes mid-SSE after HTTP `200` headers; `ScopeAccessGuard` is missing on most `/assistant/*` routes (workspace UUID/slug IDOR); `reader_allowed_source_uris` comes from the client; Layer 1 is overridable; LLM SSRF validation lacks connection-time DNS pinning (`getaddrinfo`); unauthenticated `GET /api/v1/bootstrap/platform-setup-state` exposes full platform setup snapshots; `platform_setup_snapshot` carries raw `apiKey` values and `str(exc)` bypasses redaction.
  - **In-memory state & scale-out blockers (`H-09..H-11`, `H-18..H-21`, `H-32`, `H-35`):** `ACTIVE_WORKSPACE_TURNS` (indexed solely by `workspace_id`), governance prefs, `_phantom_audit_log`, `_saved_drafts`, `_folder_meta`, thread locks, and `InMemoryPromptCacheStore` live in RAM, breaking `F5` reload, container restarts, and `--workers > 1`.
  - **Stale GitNexus index (`H-38`):** Index lagged 6 commits behind `HEAD` with `assistant_*` symbols missing `filePath`.
- **Expected vs Current Target:** Ratify and freeze an unambiguous architectural contract (`D1–D11` amended by `R1–R9`) in `ARCHITECTURE-SPINE.md` (`AD-25` + `AD-15`, `AD-21`, `AD-24` amendments) and `architecture.md` (Section `3.6.3` REST v2 / SSE v2 contract, Section `4` & `8` ERD) before any code story (`26.1`–`26.10`) begins.
- **Preservation Constraints (`ARCHITECTURE-SPINE.md` & Master Plan §5):**
  - Preserve Story `25.5` invariants: `"Mon Assistant"` remains unlocked with `1` active `chat` model and `0` `embedding` models (`get_optional_embedding_port`, `ensure_active_chat_model_if_live`); non-code RAG datasources remain blocked with `422 ERR_NO_ACTIVE_EMBEDDING_MODEL`; `require_rag_available` must never return to assistant routes.
  - Preserve default `PROCESS` behavior in `NonDeterministicReflexiveRuntime` (`process_dispatcher`, `test_story_16_2_*`).
  - Maintain `AD-19` unidirectional modular monolith boundaries, `audit_ledger` / `blackboard_snapshots` append-only triggers, and `apps/web/src/i18n/locales/{fr,en}.ts` dictionary isolation.

### 1.2 Exploration, GitNexus Impact Analysis, Consolidation & Technical Debt
- **GitNexus Index Verification (`H-38`) & Impact Queries (`repo: "/home/romain/Documents/Projects/ORCIA"`):**
  - *Observed pre-refresh state (stale index):* Both `cypher` and `query` reported `staleness: { status: "behind", commitsBehind: 6 }`.
  - `cypher` check `MATCH (n) WHERE n.name CONTAINS 'assistant' OR n.name CONTAINS 'Assistant' RETURN labels(n) AS labels, count(n) AS total, sum(CASE WHEN n.filePath IS NULL OR n.filePath = '' THEN 1 ELSE 0 END) AS missingFilePath`: returned **138 matching nodes across 10 labels**, of which **119 had null or empty `filePath`** (`Class: 41/41`, `Interface: 44/44`, `Method: 11/11`, `Function: 6/7`, `Variable: 10/10`, `Section: 5/10`, `Property: 2/2`; `File: 0/4`, `Const: 0/1`, `Route: 0/9`).
  - `cypher` check `MATCH (n) WHERE n.name STARTS WITH 'assistant_' AND (n.filePath IS NULL OR n.filePath = '')` returned `0` rows (`1` matching `File` node `assistant_llm_gemini_adapter.py` had a valid `filePath`), while `query("assistant_")` returned `_ASSISTANT_TEMPLATE_LOCK` (`Variable:packages/orcia-core/src/orcia_core/kernel/context_ports.py:_ASSISTANT_TEMPLATE_LOCK`) with missing `filePath`, and `impact("is_safe_llm_endpoint_url")` returned `"Target 'is_safe_llm_endpoint_url' not found"` due to index staleness.
  - `context("NonDeterministicReflexiveRuntime")` -> `packages/orcia-core/src/orcia_core/agents/reflexive_runtime.py` (`L51-L343`); `impact(..., direction="upstream")` -> `impactedCount: 2` (`__init__.py`, `process_dispatcher.py`, `risk: LOW`, `epistemic: exact`).
  - `context("AssistantHarness")` -> `packages/orcia-core/src/orcia_core/orchestration/assistant_harness.py` (`L179-L306`), `epistemic: lower-bound`, `dispatchBoundary: 98`.
  - *Execution constraint:* `bmad-architect-worker` has no terminal execution tool (`run_command`); therefore `node .gitnexus/run.cjs analyze` and post-refresh `assistant_*` verification are flagged for execution by the coordinator / independent Verification Sub-Agent.
- **Codebase & Tooling Parser Inspection (First-Pass Compliance):**
  - Read `.agent/skills/bmad-architecture/scripts/lint_spine.py`: enforces monotonic `AD-n` headings, mandatory `Binds`/`Prevents`/`Rule` keywords per AD block, zero `TBD`/`TODO`/`FIXME`/`XXX` or `similar to AD-n`, pinned `## Stack` table rows, and zero `{lowercase}` `TEMPLATE_TOKEN` patterns outside triple-backtick fences (requiring `<turn_id>`, `<thread_id>`, `<ws>`, `<cursor>` angle-bracket path placeholders in `ARCHITECTURE-SPINE.md`).
  - Read `infra/scripts/sync_site_catalog.py`, `infra/scripts/_site_repo_parsers.py`, and `scripts/check_implementation_docs.py`: verified `### AD-25 — ... [ADOPTED]` heading format, `README.md` `| **2026-11-21** |` 5-column table parsing, zero raw hex colors in parsed manifest strings, and `check_implementation_docs.py` mandatory section heading anchors (`analyse du besoin`, `plan d'implémentation`, `bilan des modifications`).
  - Inspected target schemas and routers directly: `assistant_threads` PK is `thread_id` (`_sql_assistant_folders_queries.py`), `reflexive_execution_sessions` columns (`id`, `execution_id`, `workspace_id`, `actor_slug`, `orchestration_mode`, `effort_level`, `status`, `snapshot_jsonb`, `expires_at` in `20261111_01_reflexive_execution_sessions.py`), `bootstrap_accostage.py:/platform-setup-state`, `mcp_and_test_bench.py:/mcp/spaces/{workspace_slug}/invoke`, `assistant_llm_providers.py:is_safe_llm_endpoint_url`, and `assistant_llm_resolver.py`.
- **Consolidation & Deferred Scope Governance:**
  - Unifies 3 paths into 1 `AssistantTurnEngine` + 1 `AssistantPromptBuilder` + 2 native tool-calling dialects (`openai_compatible`, `anthropic`) atop 3 preserved `httpx` text streaming adapters.
  - Defers speculative complexity to tracked `action_items` in `sprint-status.yaml`: `ACTION_ITEM-26.1` (Mode B graphical studio), `ACTION_ITEM-26.2` (`/three-speed/*` strangler facade), `ACTION_ITEM-26.3` (Redis assembled-prompt cache under measure-first policy `R6`), `ACTION_ITEM-26.4` (native Gemini REST & non-`/v1` Ollama tool parsers), and `ACTION_ITEM-26.5` (PG18/Admin UI SSRF allowlist).

---

## 2. Implementation Plan (Plan d'Implémentation)

### 2.1 Data Schema & Alembic Plan (`architecture.md` §4 & §8, no migrations executed in `26.0`)
- Specify two new PostgreSQL 18 tables in the ERD (`architecture.md` §4 & §8, to be migrated sequentially in Lot 3 `26.4a`/`26.4b` and Lot 4 `26.5`):
  - `assistant_thread_messages`: `id` (`UUIDv7` PK), `thread_id` (FK `REFERENCES assistant_threads(thread_id) ON DELETE CASCADE`), `workspace_id` (FK `REFERENCES workspaces(id) ON DELETE CASCADE`), `turn_id` (`UUID NOT NULL`), `parent_turn_id` (`UUID NULL` for **"Deepen"** chains), `role VARCHAR(16) NOT NULL CHECK (role IN ('user', 'assistant'))`, `content TEXT NOT NULL`, `citation_map JSONB NOT NULL DEFAULT '{}'::jsonb`, `token_count INTEGER NOT NULL DEFAULT 0`, `created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`, composite index `(thread_id, created_at)`. Detailed tool execution traces stay isolated in `reflexive_execution_sessions` keyed by `turn_id` and are never stored or re-injected as `role: 'tool'` (`D4`).
  - `assistant_turn_feedback`: `id` (`UUIDv7` PK), `turn_id` (`UUID NOT NULL`), `workspace_id` (FK `REFERENCES workspaces(id) ON DELETE CASCADE`), `user_id` (FK `REFERENCES users(id) ON DELETE CASCADE`), `rating VARCHAR(8) NOT NULL CHECK (rating IN ('up', 'down'))`, `reason_code VARCHAR(64) NULL`, `comment TEXT NULL`, `created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`, `updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`, `UNIQUE (turn_id, user_id)` for idempotent upsert (`R5`).
- Explicitly document absence of `assistant_studio_graphs` (`R2`) and `assistant_citation_drafts` (`R5`), routing phantom citation stripping events (`ASSISTANT_PHANTOM_CITATION_PURGED`) and per-tool execution audit events (`ASSISTANT_TOOL_INVOKED`, `ASSISTANT_TOOL_DENIED`) to append-only `audit_ledger`.

### 2.2 Hexagonal Core, Orchestration & Spine Updates (`ARCHITECTURE-SPINE.md`)
- Update frontmatter `updated: '2026-11-21'`.
- Author **`AD-25`** (`[ADOPTED]`) directly after `AD-24` locking:
  - Hybrid `AssistantTurnEngine` (Speed 1 fast-path `< 50 ms` RAG pre-fetch, direct SSE, post-first-byte PG18 persistence, `TTFT p95 < 1.2 s`, deterministic `low_evidence`, no pre-LLM auto-escalation; UI **"Deepen"** launching linked Speed 2 via `parent_turn_id`; Speed 2/3 on `ASSISTANT` profile of `NonDeterministicReflexiveRuntime`).
  - Single-process `apps/api` `asyncio.Task` hosting (`SIGTERM` graceful drain, no Dramatiq worker) backed by Redis Streams (`?after=<cursor>`), `(workspace_id, user_id, turn_id)` registry, `stop` signal, and refreshed liveness key emitting `stream_error` `ERR_ASSISTANT_TURN_INTERRUPTED` on crashed pods (`R1`).
  - Fixed `N1–N5` constitutional phases (`N1 IntentGuard -> N2 Planner & Ontology -> N3 Pre-fetch / Tool Loop -> N4 Server EvidenceTable -> N5 Synthesis (AssistantPromptBuilder) -> CitationGuard`) with sealed guards, Mode B deferred (`ACTION_ITEM-26.1`), Mode A 3-level overrides in `workspace_customization_overrides` (`R2`).
  - Governed tool chain (`PermissionBroker -> V5/human-anchor -> sandboxed executor + asyncio.wait_for -> secret scrub -> audit_ledger + domain_events_outbox`), `ConnectorReflexiveWriteGateAdapter` barred in `ASSISTANT` profile, SI mutation / workflow launch routed via `approval_required` -> `CONTINUE_IN_PROCESS` (DBOS + PG18 enforcing `WAITING_FOR_HUMAN_ANCHOR` / `422 ERR_HUMAN_ANCHOR_REQUIRED`), and MCP `assistant.ask` wired to Speed 1 read-only governed mode (`D6`, `D7`).
  - `LlmStreamingPort` (`orcia_core/ports/`) preserving 3 `httpx` text/reasoning adapters + scoping native `tool_calls` to 2 dialects (`openai_compatible`, `anthropic`; `gemini_native` REST & non-`/v1` Ollama default `supports_tools=false`, `422 ERR_MODEL_TOOLS_UNSUPPORTED`, `R7`).
  - Zero RAM state, measure-first prompt assembly without Redis prompt cache (`R6`, `FR-33` note / `ACTION_ITEM-26.3`), no `assistant_citation_drafts` (`R5`), direct cutover in `26.7` without `/three-speed/*` facade (`R4`, `ACTION_ITEM-26.2`).
- Append English Epic 26 amendments to **`AD-15`**, **`AD-21`** (ops env-var `ORCIA_LLM_ALLOWED_PRIVATE_HOSTS`, `localhost` restricted to `local`/`test`, permanent cloud metadata/link-local/internal-port blocks, `getaddrinfo` DNS pinning, minimal public `GET /api/v1/bootstrap/platform-setup-state` projection, credential stripping from `platform_setup_snapshot`, `str(exc)` scrubbing), and **`AD-24`** (0-token `supports_tools` Hub discovery + override, 2 tool dialects vs 3 text adapters, DNS-pinned SSRF, `AD-24.6` invariant preserved).
- Update `Capability → Architecture Map` and `Deferred` sections (`ACTION_ITEM-26.1..26.5`).

### 2.3 Backend REST v2 & SSE v2 Contract (`architecture.md` §3.6.3)
- Add `#### 3.6.3. Unified Assistant Turn Engine, Canonical REST v2 & SSE v2 Contract (AD-25, Epic 26)` defining:
  - All 8 canonical REST v2 routes (`POST /api/v1/assistant/turns`, `GET /api/v1/assistant/turns/{turn_id}/stream?after=<cursor>`, `GET /api/v1/assistant/turns/active`, `POST /api/v1/assistant/turns/{turn_id}/{stop,approve,synthesize-now,feedback}`, `GET /api/v1/assistant/threads/{thread_id}/messages`) plus synchronous MCP `POST /api/v1/mcp/spaces/{workspace_slug}/invoke` (`assistant.ask`), with exact pre-stream guard, status code, and payload contracts.
  - All 9 canonical SSE v2 events (`thinking_delta`, `tool_call`, `tool_result`, `approval_required`, `token_delta`, `citation_map`, `turn_completed`, `turn_stopped`, `stream_error` RFC 9457 + `trace_id`).

### 2.4 User Interface & Experience Impact Reference (`apps/web/`, `@orcia/ui`)
- Documentation-only reference alignment for Stories `26.7` and `26.9`:
  - Atomic UI turn transport cutover to `/api/v1/assistant/turns*` (`26.7`), Mode A API persistence, server `citation_map` pills, PG18 thread history hydration, tool trace inspector, `approval_required` cards, `supports_tools=false` Speed 2/3 disablement, and **"Deepen"** CTA button on Speed 1 completion (`26.9`). No TypeScript or UI files are modified in `26.0`.

### 2.5 Test Pyramid Impact Analysis (`AD-17` — Layers 1–5 & Security)
- **Layer 1 & 3 (Static, Doc & Spine Verification):** `lint_spine.py` (`0 findings`), `scripts/check_implementation_docs.py` (`0` errors), `pnpm site:sync && pnpm site:check` (manifest & standalone catalog sync), and GitNexus index refresh (`node .gitnexus/run.cjs analyze` + `assistant_*` `filePath` audit for `H-38`).
- **Layers 1, 2, 4, Security & 5 (Runtime/App Code):** Deferred to implementation Stories `26.1`–`26.10` (`26.0` makes zero application code, migration, or runtime test changes).

---

## 3. Modifications Summary & Verification Results (Bilan des Modifications)

### 3.1 Created & Modified Files
| File | Kind | Summary |
| :--- | :--- | :--- |
| `docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24/ARCHITECTURE-SPINE.md` | Modification | Updated frontmatter `updated: '2026-11-21'`; authored **`AD-25`** (`[ADOPTED]`) locking `AssistantTurnEngine`, Speed 1 fast-path + **"Deepen"** (`parent_turn_id`, deterministic `low_evidence`), Speed 2/3 `ASSISTANT` profile on `NonDeterministicReflexiveRuntime`, single-process `apps/api` `asyncio.Task` + `SIGTERM` drain + Redis Streams/liveness (`ERR_ASSISTANT_TURN_INTERRUPTED`, no Dramatiq worker), fixed `N1–N5` phases & sealed guards, Mode A only (Mode B deferred `ACTION_ITEM-26.1`), forbidden `ConnectorReflexiveWriteGateAdapter` + `CONTINUE_IN_PROCESS` DBOS/PG18, MCP `assistant.ask`, 3 text streaming adapters + 2 native tool dialects, measure-first no prompt cache (`ACTION_ITEM-26.3`), no drafts table (`R5`), and direct cutover (`R4`); added Epic 26 amendments to **`AD-15`**, **`AD-21`** (`ORCIA_LLM_ALLOWED_PRIVATE_HOSTS` + `getaddrinfo` DNS pinning + minimal public `GET /api/v1/bootstrap/platform-setup-state`), and **`AD-24`** (0-token `supports_tools`, 2 tool dialects, DNS-pinned SSRF, `AD-24.6` preserved); updated `Capability → Architecture Map` (`FR-33 / CAP-070..076, CAP-260`) and `Deferred` items `8..12`. |
| `docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24/architecture.md` | Modification | Added Section `3.6.3` locking all 8 canonical REST v2 routes (`/api/v1/assistant/turns*`, `/api/v1/assistant/threads/{thread_id}/messages`), MCP `assistant.ask` contract, and all 9 canonical SSE v2 events (`thinking_delta`, `tool_call`, `tool_result`, `approval_required`, `token_delta`, `citation_map`, `turn_completed`, `turn_stopped`, `stream_error` RFC 9457 + `trace_id`); updated Section `4` table and Section `8` Mermaid ERD + `8.5` for `assistant_thread_messages` (`D4`) and `assistant_turn_feedback` (`R5`), explicitly recording absence of `assistant_studio_graphs` (`R2`) and `assistant_citation_drafts` (`R5`). |
| `docs/planning-artifacts/sprint-change-proposal-2026-11-21-epic-26-harnais-assistant-remediation-plan.md` | Modification | Updated status header to record Lot 0 (`26.0`) ADR, ERD, and REST/SSE v2 specification authoring (`epic-26: in-progress`). |
| `docs/implementation-artifacts/sprint-status.yaml` | Modification | Transitioned `epic-26` to `in-progress` and `26-0-adr-unified-turn-engine-sse-v2-and-ssrf-policy` from `ready-for-dev` -> `in-progress` -> `review` -> `done` after verification. |
| `docs/implementation-artifacts/tech-lead-reports/26-0-adr-unified-turn-engine-sse-v2-and-ssrf-policy-tech-lead-report.md` | Creation | Permanent English Tech Lead Report (`Sections 1 & 2` written before Spine/ERD edits; `Section 3` finalized with verified CLI and gate outputs). |
| `docs/implementation-artifacts/tech-lead-reports/README.md` | Modification | Appended `Story 26.0` chronological index row (`2026-11-21`, strict English, `_site_repo_parsers.py` compatible). |

### 3.2 Verified Metrics, Static Quality & GitNexus Refresh (`H-38`)
- **GitNexus Index Refresh (`npx gitnexus analyze`, commit `c546732`):**
  - `Repository indexed successfully (48.5s): 43,411 nodes | 295,078 edges | 710 clusters | 1509 flows`, `0` commits behind `HEAD` (`staleness` cleared, confirmed via MCP `cypher`).
  - `n.name STARTS WITH 'assistant_'`: `1` node (`File`: `apps/api/src/orcia_api/routers/assistant_llm_gemini_adapter.py`), `0` missing `filePath` (**PASS** on `assistant_*` prefix).
  - `H-38` analyzer schema note: across the full repository in GitNexus `1.6.12`, `n.filePath` is left null/empty on most code symbol labels (`Function: 4933/5479`, `Class: 1437/1492`, `Method: 2119/2181`, `Interface: 513/581`), so `n.name STARTS WITH 'Assistant'` (`71/71`) and `query("assistant_")` (`_ASSISTANT_TEMPLATE_LOCK`) reflect GitNexus `1.6.12` property schema rather than stale commit indexing.
- **Architecture Spine & Documentation Gates:**
  - `.venv/bin/python .agent/skills/bmad-architecture/scripts/lint_spine.py --workspace docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24`: `exit 0` -> `{"ok": true, "spine": "ARCHITECTURE-SPINE.md", "total_findings": 0, "by_severity": {}, "findings": []}`.
  - `.venv/bin/python scripts/check_implementation_docs.py`: `exit 0` -> `207` Tech Lead reports comply with standards and are indexed in `README.md`.
  - `pnpm site:sync`: `exit 0` -> `activeRoutesCount: 28`, `uiPrimitivesCount: 137`, `installedPacksCount: 2`, `alembicMigrationsCount: 57`, `architectureDecisionsCount: 25`, `stackComponentsCount: 44`, `techLeadReportsCount: 207`, `capabilitiesCount: 65`, `liveCapabilitiesCount: 65`, `verifiedCapabilitiesCount: 64`, `userJourneysCount: 20`, `coveredUserJourneysCount: 20`, `e2eCoveredCapabilitiesCount: 62`.
  - `pnpm site:check`: `exit 0` -> `65/65` live capabilities, `62/62` E2E, `20/20` UJ, `207` reports, `28` routes, and `137` UI primitives in sync.
- **Static & Unit Suites Run:**
  - `.venv/bin/ruff check .`: `exit 0` -> `All checks passed!`
  - `.venv/bin/pytest tests/unit/test_capabilities_registry.py tests/unit/test_uj_prd_experience_consistency.py`: `exit 0` -> `19 passed in 0.94s`.
  - `pnpm turbo run lint typecheck test`: `exit 0` -> `9 successful, 9 total` (`@orcia/web:test`: `66` files, `260 passed`).

### 3.3 Validation Across the 5-Layer Pyramid (`AD-17`)
- **Layer 1 (Unit & Static):** No Python/TypeScript source code touched in `26.0`; verified `.venv/bin/ruff check .` (`0` errors), `.venv/bin/pytest tests/unit/test_capabilities_registry.py tests/unit/test_uj_prd_experience_consistency.py` (`19 passed in 0.94s`), `pnpm turbo run lint typecheck test` (`9/9` tasks, `66` files / `260 passed` in `@orcia/web:test`), and `scripts/check_implementation_docs.py` (`207/207`).
- **Layer 2 (PG18/Redis Integration):** Not applicable in `26.0` (schema ERD locked in `architecture.md` §4 & §8; Alembic migrations & `testcontainers` integration tests begin in Lot 3 `26.3`–`26.4b` and Lot 4 `26.5`).
- **Layer 3 (OpenAPI 3.1 / `lint_spine.py` / `site:check`):** OpenAPI REST v2 & SSE v2 contract frozen in `architecture.md` §3.6.3; verified `lint_spine.py` (`exit 0`, `ok: true`, `total_findings: 0`) and `pnpm site:sync` + `pnpm site:check` (`exit 0`, `25` ADs, `207` reports, `65/65` capabilities).
- **Layer 4 (`0 $` Evals) & Security Layer:** Architectural invariants (`ScopeAccessGuard`, pre-stream `READ_ONLY_OBSERVER`, server-side `READ_SOURCE` / `CONFIDENTIAL_RESTRICTED`, immutable Layer 1, DNS-pinned SSRF, public `platform-setup-state` projection, governed tool chain) locked in `AD-25` and `AD-21`/`AD-24` amendments; executable tests scheduled for `26.1`–`26.10`.
- **Layer 5 (Playwright E2E):** Not applicable in `26.0`; atomic UI/E2E cutover scheduled in `26.7` (`specs 02/12/16/21`) and new `F5` / `"Deepen"` coverage in `26.9` (`spec 22`).
