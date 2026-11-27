# Sprint Change Proposal — Epic 26 Master Remediation Plan: Unified, Governed & Persistent "Mon Assistant" Harness

- **Date:** 2026-11-21
- **Author:** Tech Lead (multi-agent audit + `VALIDATE` review by `bmad-architect-worker`)
- **Status:** `in-progress` (`/grill-me` `55b4642` + simplification `R1–R4` `fdc7cb7` + Recommended Set `R5–R9`). Epic active (`epic-26: in-progress`); Lot 0 (`26.0`) is ratified (`AD-25`, `AD-15`/`AD-21`/`AD-24` amendments, ERD, and canonical REST v2 / SSE v2 contracts in `ARCHITECTURE-SPINE.md` and `architecture.md`) and verified (`26-0: done`), awaiting user GO for Lot 1 (`26.1`). Stories `26.1`–`26.10` remain `ready-for-dev`.
- **Trigger:** Deep audit of the "Mon Assistant" harness showing that the path actually served to the UI bypasses ORCIA's core governance, security, persistence, and citation guarantees.
- **Evidence & linked documents:**
  - Decisions record: [`epic-26-decisions-grill-2026-11-21.md`](../implementation-artifacts/epic-26-decisions-grill-2026-11-21.md) (active decisions `D1–D11` as amended by `R1–R9`)
  - Source audit: [`2026-11-21-audit-harnais-assistant-et-plan-remediation-tech-lead-report.md`](../implementation-artifacts/tech-lead-reports/2026-11-21-audit-harnais-assistant-et-plan-remediation-tech-lead-report.md) (`H-01..H-38`: 14 P0 [13 confirmed, 1 partial], 16 P1, 6 P2, 2 P3; 13/22 assistant endpoints uncalled by UI; ~2,100 L business logic in `apps/api/routers/`)
  - Backlog: [`epics/epic-26.md`](./epics/epic-26.md) (13 stories with acceptance criteria)
  - Sprint status: [`sprint-status.yaml`](../implementation-artifacts/sprint-status.yaml#L275)
  - Architecture spine: [`ARCHITECTURE-SPINE.md`](./architecture/architecture-ORCIA-2026-10-24/ARCHITECTURE-SPINE.md) (`AD-2`, `AD-3`, `AD-8`, `AD-10`, `AD-12`, `AD-15`, `AD-17`, `AD-19`, `AD-21`, `AD-23`, `AD-24`)

---

## 1. Executive Decision Summary

The conceptual model of the harness (5-layer constitutional prompt, role hats, L1–L4 ontology, 3 speeds, authority-tiered citations, Lock V5, human anchors) fits ORCIA. Its production runtime implementation does not:

1. **Three divergent execution paths:** The UI calls `/three-speed/stream`, bypassing `AssistantHarness`, RAG, server citation checks, and human anchor enforcement. In `deep`/`@agent` mode, `NonDeterministicReflexiveRuntime` runs in parallel (double LLM execution).
2. **Broken/mocked tool loop & bypassed anchors:** Non-stream turns inject fake tool results; streaming turns discard `tool_calls` deltas and fail with `stream_error`. `save_and_launch_workflow` executes `human_authored_required` steps without human approval (`AD-3`).
3. **Security gaps:** `READ_ONLY_OBSERVER` checks run after HTTP `200` SSE headers; `ScopeAccessGuard` is missing on most `/assistant/*` routes (IDOR); `reader_allowed_source_uris` comes from the client; Layer 1 can be overridden; SSRF lacks DNS pinning.
4. **In-memory state:** Active turns, governance settings, thread locks, phantom audit logs, and feedback live in RAM—failing F5 reloads, container restarts, and `--workers > 1`.

Core building blocks already exist (`NonDeterministicReflexiveRuntime`, `PermissionBrokerService`, `SurgicalContextExplorer`, V5 Guard, `SqlHybridRagRepository`, Tier 1/2 sandbox, governed MCP). Epic 26 is therefore a **convergence and wiring** effort.

---

## 2. Target Architecture & Effective Decisions (`D1–D11` Amended by `R1–R9`)

- **Single turn engine (`AssistantTurnEngine` in `orcia_core`, `D1` + `R1` + `R2` + `R3`):**
  - **Speed 1:** Single-shot fast-path without tool loop—bounded RAG pre-fetch (`< 50 ms`), direct SSE streaming, post-first-byte PG18 persistence, `TTFT p95 < 1.2 s`. No auto-escalation: `turn_completed` emits deterministic `low_evidence` (`EvidenceTable` empty), and UI offers a **"Deepen"** button (when `supports_tools=true`) launching a linked Speed 2 turn (`parent_turn_id`).
  - **Speed 2 / Speed 3:** Driven by the `ASSISTANT` profile of `NonDeterministicReflexiveRuntime` (bounded tool loop, budgets, `cancel`, `synthesize_now`).
  - **Single-process hosting (`R1`):** All speeds run in bounded `asyncio.Task` inside `apps/api` with `SIGTERM` graceful drain. Active turn registry, Redis Streams event buffer (cursor reattachable across F5/workers), and `stop` signals live in Redis. A Redis liveness key detects crashed pods and emits `ERR_ASSISTANT_TURN_INTERRUPTED` on reattach. **No Dramatiq worker for assistant turns.**
- **Five `AD-15` nodes become fixed phases (`N1–N5`):** `N1 IntentGuard → N2 Planner & Ontology → N3 Pre-fetch / Tool Loop → N4 Server EvidenceTable → N5 Synthesis (AssistantPromptBuilder) → CitationGuard`. Constitutional guards (`Layer 1`, `N1`, `V5`, `CitationGuard`) are sealed. Mode B graphical studio is deferred (`ACTION_ITEM-26.1`); only Mode A 3-level text instructions feed context assembly (`R2`).
- **Governed tool chain & zero direct SI writes:** `PermissionBroker` → `V5` / deterministic human-anchor guard → sandboxed executor (`asyncio.wait_for`) → secret scrub → `audit_ledger` + `domain_events_outbox`. `ConnectorReflexiveWriteGateAdapter` is blocked in the `ASSISTANT` profile. Any SI mutation routes via `approval_required` → `CONTINUE_IN_PROCESS` (DBOS + PG18 Gate).
- **Zero business RAM state (`R5`, `R6`):**
  - **PG18:** `reflexive_execution_sessions`, `assistant_thread_messages` (`D4`), `workspace_customization_overrides` (Mode A), `assistant_turn_feedback`, folder attachments/tags, `audit_ledger` (including `ASSISTANT_PHANTOM_CITATION_PURGED` & `ASSISTANT_TOOL_INVOKED`/`DENIED`), `domain_events_outbox`. No Mode B studio table and no drafts persistence table (`R5`).
  - **Redis:** Reattachable turn streams, turn registry + liveness keys, thread turn locks (`SET NX EX`), rate limiter, concurrency semaphore. **No assembled-prompt Redis cache (`R6` measure-first)**: measure SQL prompt-assembly latency first; only revisit via `ACTION_ITEM-26.3` if assembly p95 exceeds `50 ms`.
- **LLM providers & tool calling (`R7`):** Preserve all **3** native `httpx` text/reasoning streaming adapters (OpenAI-compatible, Anthropic, native Gemini `CAP-076`). Support native `tool_calls` parsing/re-injection on **2 dialects** (OpenAI-compatible and Anthropic); native Gemini REST and non-`/v1` Ollama default to `supports_tools=false` (`422 ERR_MODEL_TOOLS_UNSUPPORTED` on Speed 2/3, deferred to `ACTION_ITEM-26.4`).
- **SSRF & setup state (`D3` + `R8`):** Ops env var `ORCIA_LLM_ALLOWED_PRIVATE_HOSTS` (`localhost` only in `local`/`test`), permanent metadata/link-local/internal-port blocks, and connection-time DNS pinning (`getaddrinfo`). DB/UI allowlist deferred to `ACTION_ITEM-26.5`. `GET /bootstrap/platform-setup-state` public Day-0 response restricted to `{is_initialized, step}` (`0` secrets).
- **Direct cutover without strangler facade (`R4`, `ACTION_ITEM-26.2`):** Backend, `apps/web` turn transport, and Playwright specs `02/12/16/21` cut over atomically in **`26.7`** to `/api/v1/assistant/turns*`. Legacy/uncalled routes are deleted directly when replaced (`26.4b` Mode B; `26.7` `/three-speed/*`, `/chat*`, `/verify-turn`, `/artifacts/action` + `_saved_drafts`; `26.8` `/save-and-launch`; `26.9` duplicate `POST /threads/{id}/turns`).

### 2.1 Decision Reference Matrix

| ID | Summary | Stories |
| :--- | :--- | :--- |
| `D1`+`R2`+`R3` | Hybrid `AssistantTurnEngine`, "Deepen" button (`low_evidence`), fixed `N1–N5`, Mode B deferred | `26.0`, `26.4b`, `26.6b`, `26.7`, `26.9` |
| `D2`+`R1` | `202` + Redis Streams `?after=cursor`, all speeds in bounded `asyncio.Task` (`apps/api`), no Dramatiq | `26.0`, `26.3`, `26.7`, `26.9` |
| `D3`+`R8` | `ORCIA_LLM_ALLOWED_PRIVATE_HOSTS` env allowlist + DNS pinning + minimal public setup-state | `26.0`, `26.1`, `26.10` |
| `D4` | `assistant_thread_messages` (`user`\|`assistant`) separate from `reflexive_execution_sessions` traces | `26.0`, `26.5`, `26.7`, `26.9` |
| `D5`+`R7` | `supports_tools` 0-token Hub discovery + 3 text adapters + 2 tool-call dialects (OpenAI-compat, Anthropic) | `26.0`, `26.2`, `26.6a`, `26.7`, `26.9` |
| `D6`+`R4` | `CONTINUE_IN_PROCESS` via DBOS + PG18 (`WAITING_FOR_HUMAN_ANCHOR`); delete `/save-and-launch` in `26.8` | `26.0`, `26.8`, `26.10` |
| `D7` | MCP `assistant.ask` wired to `AssistantTurnEngine` Speed 1 read-only governed mode | `26.0`, `26.7`, `26.10` |
| `D8`+`R4` | No v1 facade; atomic cutover in `26.7`; direct route deletions across `26.4b`/`26.7`/`26.8`/`26.9` | `26.4b`, `26.7`, `26.8`, `26.9`, `26.10` |
| `D9` | Downgrade `CAP-022`/`070`/`072` (`26.1`), create `CAP-260` (`26.6b`), promote `runtime` after E2E (`26.10`) | `26.1`, `26.6b`, `26.10` |
| `R5` | Drop drafts table; phantom citations to `audit_ledger`; keep `assistant_turn_feedback` PG18 table | `26.0`, `26.4b`, `26.7`, `26.10` |
| `R6` | Drop Redis prompt cache & Outbox cache invalidation; measure assembly p95 & TTFT first | `26.0`, `26.4a`, `26.5`, `26.7` |
| `R9` | Sequential Lot 3 (`26.3 → 26.4a → 26.4b`); 2 dev workers + `pro` review on `26.1`, `26.6b`, `26.7` | §3, §4, `epics.md`, `sprint-status.yaml` |

---

## 3. Lot Breakdown (8 Lots, 13 Stories — Sequential Execution)

| Lot | Stories | Scope | Execution Mode | Size |
| :--- | :--- | :--- | :--- | :---: |
| **Lot 0 — ADR & Contracts** | `26.0` | `AD-25` + `AD-15`/`21`/`24` updates, ERD (`D4`, `R5`), SSE v2 contract, `gitnexus analyze` | `bmad-architect-worker` (`pro`) → STOP | S |
| **Lot 1 — Immediate Security** | `26.1` | Pre-stream Scope/Observer guards, IDOR fix, server `READ_SOURCE`/`CONFIDENTIAL`, Layer 1, env SSRF + DNS pinning, Day-0 setup state, remove prod `assert`, `D9` cap downgrade | 2 `flash` workers + `pro` review | M |
| **Lot 2 — Core Extraction** | `26.2` | Extract LLM/prompts/telemetry to `orcia_core` (`LlmStreamingPort` + 3 text adapters), unified localized `AssistantPromptBuilder`, remove `testclient` branches, `< 300 L` splits | 1 `flash` worker | L |
| **Lot 3 — Reliability & Persistence** | `26.3` → `26.4a` → `26.4b` | `26.3` Redis turn registry + liveness + async loop + rate limit → `26.4a` Redis thread locks, Outbox emission, Hub TTL, Alembic DDL (no prompt cache) → `26.4b` PG18 Mode A governance, `assistant_turn_feedback`, folders, phantom citations to `audit_ledger`, delete Mode B routes | **Sequential** (`workspace: "inherit"`, linear Alembic chain) | M + S + M |
| **Lot 4 — Real Context** | `26.5` | PG18 ontology relevance + `ProfileSemanticTranslator` + axioms, async `SqlHybridRagRepository`, SQL Blackboard, server `EvidenceTable`, `assistant_thread_messages` + budget trimmer, measure assembly p95 | 1 `flash` worker | L |
| **Lot 5 — Tool Loop** | `26.6a` → `26.6b` | `26.6a` 2-dialect `tool_calls` (OpenAI-compat, Anthropic), `supports_tools`, loop budgets (`S`) → `26.6b` `GovernedAssistantToolRouter`, Broker → V5/anchor → sandbox → `audit_ledger` + Outbox, anti-injection, `CAP-260` (`M`) | `26.6a`: 1 `flash` · `26.6b`: 2 `flash` + `pro` review | S + M |
| **Lot 6 — Convergence** | `26.7` → `26.8` | `26.7` `AssistantTurnEngine`, `CitationGuard`, `assistant.ask` MCP, atomic cutover of UI + E2E `02/12/16/21`, delete `/three-speed/*`, `/chat*`, `/verify-turn`, `/artifacts/action` (`_saved_drafts`) → `26.8` `CONTINUE_IN_PROCESS` DBOS + `WAITING_FOR_HUMAN_ANCHOR`, delete `/save-and-launch` | `26.7`: 2 `flash` + `pro` review · `26.8`: 1 `flash` | L + M |
| **Lot 7 — UI & Closure** | `26.9` → `26.10` | `26.9` Mode A API, `citation_map` pills, PG18 history (`GET /threads/{id}/messages`, drop `POST /threads/{id}/turns`), tool trace, approval cards, "Deepen" button, F5 `spec 22` → `26.10` golden evals, red-team, multi-worker Redis test, AST audits, 0 uncalled route check, `BUG-E2E-01b`/`AUTH-01`, `runtime` promotion, closure | `26.9`: 1 `flash` · `26.10`: 1 `flash` + final `pro` architect gate | M + M |

```mermaid
flowchart LR
    L0["Lot 0: 26.0 ADR"] --> L1["Lot 1: 26.1 Security"]
    L1 --> L2["Lot 2: 26.2 Core Extraction"]
    L2 --> S3["Lot 3.1: 26.3 Reliability"]
    S3 --> S4a["Lot 3.2: 26.4a Redis & DDL"]
    S4a --> S4b["Lot 3.3: 26.4b PG18 & Ledger"]
    S4b --> L4["Lot 4: 26.5 Real Context"]
    L4 --> S6a["Lot 5.1: 26.6a 2-Dialect Tools"]
    S6a --> S6b["Lot 5.2: 26.6b Tool Router"]
    S6b --> S7["Lot 6.1: 26.7 Convergence & Cutover"]
    S7 --> S8["Lot 6.2: 26.8 DBOS & Anchors"]
    S7 --> S9["Lot 7.1: 26.9 UI & SDK"]
    S8 --> S9
    S9 --> S10["Lot 7.2: 26.10 Evals & Closure"]
```

### 3.1 Findings-to-Stories Matrix (`H-01..H-38`)

| Story | Findings Covered |
| :--- | :--- |
| `26.0` | `H-38` + prerequisites `D1–D11` / `R1–R9` |
| `26.1` | `H-06`, `H-07`, `H-08`, `H-15`, `H-16`, `H-17`, `H-30` (prod `assert`) |
| `26.2` | `H-24`, `H-25`, `H-30` (P2 hardcoded literals), `H-31`, `H-34` |
| `26.3` | `H-10`, `H-11`, `H-20`, `H-21`, `H-23`, `H-33` |
| `26.4a` | `H-09` (locks), `H-19` (removed), `H-22` (Outbox), `H-32`, `H-35` |
| `26.4b` | `H-09` (governance, phantom audit, feedback, folders), `H-37` (`BUG-E2E-01b` part) |
| `26.5` | `H-12`, `H-13`, `H-18` (server history/budget), assembly latency baseline |
| `26.6a` | `H-03` (transport), `H-04`, `H-27` (dialects) |
| `26.6b` | `H-03` (execution), `H-22` (per-tool ledger), `H-27` (catalog), `H-28`, `H-29` |
| `26.7` | `H-01`, `H-02`, `H-09` (`_saved_drafts` deleted), `H-14` (server) |
| `26.8` | `H-05` |
| `26.9` | `H-14` (UI), `H-18` (UI), `H-26` |
| `26.10` | `H-36`, `H-37` |

---

## 4. Definition of Ready & Launch Protocol

All 13 stories are `ready-for-dev`: acceptance criteria, dependencies, findings, CAPs, impacted files, and Tech Lead report paths live in `epics.md`. At launch time (not started yet), execute sequentially per lot:

1. Verify all dependency keys are `done` in `sprint-status.yaml`.
2. Create `docs/implementation-artifacts/tech-lead-reports/<story-key>-tech-lead-report.md` (Sections 1 & 2) **before any code edit**, after `npx gitnexus analyze` and `gitnexus_impact` (`repo: "ORCIA"`).
3. Route agents per `.agents/rules/bmad-model-routing.md` and **`R9`**:
   - **`26.0`**: `bmad-architect-worker` (`pro`) → STOP for user review (`lint_spine.py`).
   - **High-risk stories (`26.1`, `26.6b`, `26.7`)**: **2 distinct `bmad-dev-worker` (`flash`)** agents (#1 TDD Implementation + #2 Independent `AD-17` 5-layer Verification & Report §3) + mandatory `bmad-architect-worker` (`pro`) `bmad-code-review`.
   - **Standard dev stories (`26.2`, `26.3`, `26.4a`, `26.4b`, `26.5`, `26.6a`, `26.8`, `26.9`, `26.10`)**: **1 dedicated `bmad-dev-worker` (`flash`)** handling TDD implementation, all 5 `AD-17` layers, and Report §1–§3 (`26.10` also gets final `pro` closure review).
   - Automatic escalation to `pro` after 2 consecutive `flash` failures on the same root cause.
4. Enforce strict TDD, 5 `AD-17` layers (`>= 90%` unit coverage), `ruff`, `mypy --strict`, `lint-imports` (`5/5`), OpenAPI `0-diff`, `pnpm turbo run lint typecheck test`, `lint_spine.py` (`0 findings`), and `< 300 L` file threshold.
5. Set story to `review` → run `bmad-code-review` (mandatory on `26.1`, `26.6b`, `26.7`, `26.10`) → set `done`, update `capabilities.yaml`, run `pnpm site:sync && pnpm site:check`, create **1 atomic local Git commit per story**, and **STOP for user GO at each lot boundary**.

`epic-26` transitions automatically to `in-progress` when `26.0` starts.

---

## 5. Non-Regression Invariants (Entire Epic)

- **Story `25.5` preservation:** "Mon Assistant" remains unlocked from `1` active `chat` model without an `embedding` model (`get_optional_embedding_port`, `ensure_active_chat_model_if_live`); RAG non-code datasource blocking (`422 ERR_NO_ACTIVE_EMBEDDING_MODEL`) remains intact; `require_rag_available` must never return to assistant routes.
- **Process runtime isolation:** `PROCESS` behavior in `NonDeterministicReflexiveRuntime` remains unchanged by default (`process_dispatcher`, `test_story_16_2_*`).
- **`agents_and_skills` migration:** Migrate `agents_and_skills.py` off `assistant_llm_bridge` and `system_instructions_override` before removing legacy bridge endpoints.
- **Continuous E2E green bar:** Specs `02`, `12`, `16`, and `21` (including `/artifacts/action` tested in `21` until `26.7`) stay green at every story commit.
- **Append-only & UI i18n rules:** Never disable `audit_ledger` or `blackboard_snapshots` triggers; preserve typed `apps/web/src/i18n/locales/{fr,en}.ts` dictionary (French default UI copy, zero hardcoded JSX user strings).

---

## 6. Measurable Exit Criteria (Definition of Done)

| Metric | Target |
| :--- | :--- |
| LLM execution paths per user turn | **1** |
| Prompt builders | **1** (`Layer 1` immutable, localized) |
| Mutating `/assistant/*` routes lacking scope + observer guard | **0** (AST audit) |
| Module-level mutable business dicts or `InMemory*` stores in harness prod | **0** (AST audit) |
| `testclient` / `pytest in sys.modules` branches in `src/` | **0** |
| Assistant endpoints without active UI/MCP caller | **0** |
| Tool calls audited in `audit_ledger` | **100%** |
| Citations emitted without server `EvidenceTable` entry | **0** (golden eval) |
| Speed 1 `TTFT p95` (cassette, real PG18) | **`< 1.2 s`** |
| Multi-worker `stop` & cursor SSE reattachment | **Pass** |
| Harness files `> 300 L` | **0** |
| Unit test coverage | **`>= 90%`** |

---

## 7. Risks, Mitigations & Deferred Action Items

| Risk | Mitigation |
| :--- | :--- |
| Regression in `PROCESS` runtime | Profile composition (`ASSISTANT` vs `PROCESS`), default unchanged, `16-2` & `process_dispatcher` guards. |
| Speed 1 TTFT degradation without prompt cache (`R6`) | Fast-path skips `reflexive_execution_sessions` pre-creation; RAG pre-fetch capped `< 50 ms`; assembly latency measured in `26.5` & TTFT p95 in `26.7`; `ACTION_ITEM-26.3` triggered only if p95 `> 50 ms`. |
| Atomic direct cutover in `26.7` (`R4`) | Single atomic commit covering engine + UI transport + E2E `02/12/16/21`, mandatory `pro` review, instant rollback via `git revert`. |
| Long turn lost on brutal pod crash (`R1`, accepted risk) | `SIGTERM` graceful drain on deploys; Redis liveness key emits explicit `ERR_ASSISTANT_TURN_INTERRUPTED` on reattach. |
| On-prem private host onboarding requires env update (`R8`) | Clean `ORCIA_LLM_ALLOWED_PRIVATE_HOSTS` config + DNS pinning; `ACTION_ITEM-26.5` tracks optional PG18/Admin UI later. |
| Native tool calling on non-OpenAI-compatible Ollama / Gemini REST (`R7`) | `supports_tools` 0-token Hub flag + explicit `422 ERR_MODEL_TOOLS_UNSUPPORTED` + Ollama `/v1` works natively; `ACTION_ITEM-26.4` tracks native parsers. |
| Divergent `26.0` ADR discovery | Existing `D1–D11` + `R1–R9` already rebased; any newly discovered ADR divergence triggers `bmad-correct-course` before `26.1`. |
| Overstated `capabilities.yaml` status | Immediate `api` downgrade in `26.1`; `runtime` promotion only after `spec 22` passes in `26.10` (`D9`). |

**Deferred `action_items` registered in `sprint-status.yaml`:**
- `ACTION_ITEM-26.1` — Mode B graphical studio (`@xyflow/react`) for `N2–N5` (`R2`).
- `ACTION_ITEM-26.2` — Legacy `/three-speed/*` compatibility facade if an external non-SPA consumer emerges (`R4`).
- `ACTION_ITEM-26.3` — Redis assembled-prompt cache & Outbox invalidation if assembly p95 `> 50 ms` (`R6`).
- `ACTION_ITEM-26.4` — Native Gemini REST `functionCall` & native Ollama `/api/chat` tool-call parsers (`R7`).
- `ACTION_ITEM-26.5` — PG18 / Admin UI dynamic SSRF allowlist management (`R8`).
