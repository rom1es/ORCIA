# Story 26.6b — Governed Assistant Tool Router (Dynamic PG18/RBAC/MCP Catalog, PermissionBroker, Lock V5, Deterministic Human Anchors, Sandboxed Execution, Idempotency & Audit)

- **Date**: 2026-11-22
- **Story / Sprint Key**: `26-6b-governed-assistant-tool-router-broker-v5-anchors-and-audit` (`Epic 26` / `Lot 5.2`)
- **Capability(ies)**: `CAP-160`, `CAP-022`, `CAP-260` (new `verification: api` entry in `docs/product/capabilities.yaml`) — classification: `feature`
- **Author / Context**: Dedicated Coding Sub-Agent (`bmad-dev-worker`) — Remediating Epic 26 audit findings `H-03` (governed tool execution), `H-22` (per-tool `audit_ledger` & outbox), `H-27` (dynamic workspace catalog replacing stub + 10-item cap), `H-28` (idempotency & timeout-capped sandbox), and `H-29` (untrusted tool-output delimiters & `ASSISTANT` profile structural isolation of `ConnectorReflexiveWriteGateAdapter`), aligned with `AD-3`, `AD-6`, `AD-9`, `AD-12`, `AD-15`, `AD-19`, `AD-20`, `AD-24`, `AD-25`, `FR-33`, and Decisions `D1`/`D9`/`R9`.
- **Associated Commits**: Pending Testing Sub-Agent & `pro` review before commit.

---

## 1. Need Analysis & Tech Lead Impact Study (Analyse du Besoin)

### 1.1 Context & Problem Statement
- **Current behavior**:
  1. `apps/api/src/orcia_api/routers/_assistant_llm_tools_and_budget.py` exposes a hardcoded single-tool stub (`query_workspace_knowledge_and_glossary`) plus at most 10 in-memory skills (`[:10]`) with generic `{"input_text": string}` schemas instead of real PG18 `enabled_in_workspace` skills, `SurgicalContextExplorer` `#Lstart-end` primitives, conditional `kb.search`, ontology lookup, and RBAC/MCP-filtered tools (`H-27`).
  2. `_assistant_turn_producer.py` receives `tool_calls` from `LlmStreamingPort` (`Story 26.6a`) without executing a governed tool loop, while `assistant_llm_bridge.py` injects a synthetic placeholder tool result string (`"Workspace context verified..."`) (`H-03`).
  3. No `AssistantToolExecutorPort` or `GovernedAssistantToolRouter` enforces `PermissionBrokerService` (`passthrough`, `READ_SOURCE`), Lock V5 (forbidding direct enterprise writes in chat), deterministic per-tool human-anchor checks (`human_authored_required`), Redis/store idempotency (`idem:{turn_id}:{iteration}:{tool_call_id}`), `asyncio.wait_for` timeout-capped sandboxed execution, `scrub_connector_secrets`, `<untrusted_tool_output>` anti-injection delimiters, and per-tool `audit_ledger` (`ASSISTANT_TOOL_INVOKED` / `ASSISTANT_TOOL_DENIED`) + `domain_events_outbox` (`HumanArbitrationRequested`) (`H-22`, `H-28`, `H-29`).
  4. `NonDeterministicReflexiveRuntime` exposes `ConnectorReflexiveWriteGateAdapter` (`ReflexiveWriteGatePort`) without an `execution_profile="ASSISTANT"` structural barrier, and `assistant_agent_synthesis.py` relies on a lexical phrase heuristic (`HUMAN_ANCHOR_WRITE_REFUSAL`) on user text (`H-29`).
- **Target behavior**:
  - Define hexagonal `AssistantToolExecutorPort` in `orcia_core/ports/` and `GovernedAssistantToolRouter` in `orcia_core/agents/` wired through `apps/api` Composition Root (`dependencies/assistant_tools.py`), active turn producer, and SSE stream.
  - Dynamically assemble each turn's authorized tool catalog (`4` `SurgicalContextExplorer` primitives, conditional `kb.search` only when RAG is active, `ontology.lookup`, all PG18 `enabled_in_workspace` skills with real `input_parameters` JSON Schemas, and MCP-exposed tools filtered by `mcp_tool_permissions` + workspace RBAC).
  - Execute every LLM tool call strictly through: Step A `PermissionBrokerService` (`passthrough` + `READ_SOURCE` + observer/scope guards) -> Step B Lock V5 & deterministic per-tool Human-Anchor guard (`approval_required` -> `CONTINUE_IN_PROCESS` + `HumanArbitrationRequested` outbox) -> Step C idempotency (`idem:{turn_id}:{iteration}:{tool_call_id}`) -> Step D `asyncio.wait_for` sandboxed execution -> Step E `scrub_connector_secrets` + delimited `<untrusted_tool_output>` neutralization + immutable `audit_ledger` + canonical SSE events (`tool_call`, `tool_result`, `approval_required`).
  - Add `ExecutionProfile = Literal["PROCESS", "ASSISTANT"]` ensuring `ConnectorReflexiveWriteGateAdapter` is structurally unreachable in `ASSISTANT` profile while keeping `PROCESS` defaults and `test_story_16_2_*` / `process_dispatcher` completely intact.
- **Architectural constraints (`ARCHITECTURE-SPINE.md`)**:
  - `AD-19` Contract 2 places `orcia_core.agents` and `orcia_core.orchestration` on the same horizontal layer (`bootstrap | orchestration | packs | agents`). Therefore `orcia_core.agents` must NOT import `orcia_core.orchestration`, and `orcia_core.orchestration` must NOT import `orcia_core.agents`. Both depend downward on `orcia_core.ports`, `blackboard`, `ontology`, `rag`, `gates`, `audit_finops`, `workflows`, `catalog`, `permissions`, `observability`, and `kernel`, while `apps/api` wires them together in the Composition Root.
  - `AD-20` (`test_core_domain_isolation.py`) forbids SDLC tokens (`jira`, `confluence`, `git_branch`, `wsjf`, `rovo`, `copilot`, `safe`, `prd`) anywhere in `orcia_core/{workflows,packs,storage,kernel,orchestration,gates,ports,agents}/`.
  - Every touched/created non-generated source file must stay `<= 300` lines (`wc -l`).

### 1.2 Exploration, GitNexus Impact Analysis, Factorization & Technical Debt
- **GitNexus & Codebase Impact Analysis**:
  - Inspected `PermissionBrokerService` (`packages/orcia-core/src/orcia_core/permissions/broker.py`, `605` L), `SurgicalContextExplorer` (`packages/orcia-connectors/src/orcia_connectors/surgical.py`, `353` L), `ConnectorReflexiveWriteGateAdapter` (`packages/orcia-connectors/src/orcia_connectors/reflexive_write_gate.py`, `160` L), `NonDeterministicReflexiveRuntime` (`packages/orcia-core/src/orcia_core/agents/reflexive_runtime.py`, `298` L), `AssistantCitationAndV5GuardService` (`263` L), `HumanAnchorAndArbitrationService` (`291` L), `AgentsAndSkillsManagementService` (`479` L) + `sql_agents_and_skills.py` (`433` L), `GovernedMcpExposureService` (`351` L), `SqlAuditLedgerService` (`203` L), `AssistantOutboxEmitter` (`193` L), `_assistant_llm_tools_and_budget.py` (`83` L), `_assistant_turn_producer.py` (`297` L), and `assistant_llm_bridge.py` (`298` L).
  - Direct upstream callers of `build_workspace_tools_schema` are `_assistant_turns_v2_routes.py`, `_assistant_llm_stream_bridge.py`, `assistant_llm_bridge.py`, `assistant_llm_prompts.py`, and `tests/unit/test_assistant_agnostic_async_llm_bridge.py`.
  - Direct callers of `HUMAN_ANCHOR_WRITE_REFUSAL` are `assistant_agent_synthesis.py` (`classify_assistant_intent`), `test_story_3_3`, `test_story_3_4`, and `test_assistant_and_ontology_evals.py` (which continue testing the legacy `AssistantAgentService` until `Story 26.7` deletes legacy routes).
- **Key Findings & Edge Cases**:
  - `SqlDomainEventsOutboxRepository.insert_event_in_session` casts `:run_id` and `:workspace_id` to `uuid` in PostgreSQL 18 (`CAST(:run_id AS uuid)`). Assistant turn IDs use `"turn-<hex>"` (non-UUID strings), so `HumanArbitrationRequested.create(...)` for an assistant tool call must pass `run_id=coerce_optional_uuid(turn_id)` (`None` when non-UUID) and store `turn_id` in `payload` / `aggregate_id` to prevent PG18 `DataError`.
  - `SqlAuditLedgerService.record_entry` enforces `ON CONFLICT (source_event_id) DO NOTHING` with `CAST(:source_event_id AS uuid)`. Deterministic `uuid5(NAMESPACE_URL, f"assistant-tool:{turn_id}:{iteration}:{tool_call_id}")` guarantees idempotent ledger rows without duplicate-key failures.
  - `reflexive_runtime.py` is already at `298` lines; profile guard logic is extracted to `_assistant_profile_guard.py` (`<= 60` L) so `reflexive_runtime.py` remains `<= 300` lines.
- **Factorization & Debt Control**:
  - Reuses existing `SurgicalExplorerPort`, `PermissionBrokerService`, `MatrixPermissionEvaluator`, `SubprocessTier1SandboxAdapter`, `scrub_connector_secrets`, `SqlAuditLedgerService`, `SqlDomainEventsOutboxRepository`, `llm_tool_dialects.format_tool_result_message`, and `assistant_loop_budgets.run_bounded_tool_loop` rather than duplicating logic.
  - Splits `GovernedAssistantToolRouter` into cohesive `< 260`-line modules (`_assistant_tool_catalog.py`, `_assistant_tool_guards.py`, `_assistant_tool_idempotency.py`, `_assistant_tool_execution.py`, `_assistant_tool_audit.py`, `governed_tool_router.py`) and keeps `_assistant_turn_producer_tool_loop.py` separate from `_assistant_turn_producer.py`.

---

## 2. Implementation Plan (Plan d'Implémentation)

### 2.1 Data Schema & Alembic Migrations
- **Not applicable**: Story `26.6b` introduces zero schema migrations (`HEAD` remains `20261122_266a`) and reuses existing PG18 tables (`catalog_items`, `permission_broker_policies`, `permission_broker_tickets`, `audit_ledger`, `domain_events_outbox`, `mcp_exposed_agents`, `reflexive_execution_sessions`) plus Redis 7.4 keys (`idem:{turn_id}:{iteration}:{tool_call_id}`).

### 2.2 Hexagonal Core, Tool Router & Profile Isolation (`packages/orcia-core/`)
- `packages/orcia-core/src/orcia_core/ports/assistant_tool_executor_port.py` (re-exported in `ports/__init__.py`):
  - Pure Protocol `AssistantToolExecutorPort`, `ToolIdempotencyStorePort`, `AuthorizedToolDescriptor`, `SkillCatalogEntry`, `McpExposedToolSpec`, `AssistantToolCatalogContext`, `AssistantToolExecutionRequest`, `AssistantToolExecutionResult`, and `AssistantToolSseEvent` (zero framework/SDK imports).
- `packages/orcia-core/src/orcia_core/agents/`:
  - `reflexive_schemas.py`, `_runtime_helpers.py`, `_assistant_profile_guard.py`, `reflexive_runtime.py`: introduce `ExecutionProfile = Literal["PROCESS", "ASSISTANT"]` (default `"PROCESS"`) and make `ConnectorReflexiveWriteGateAdapter` / `ReflexiveWriteGatePort` structurally unreachable in `"ASSISTANT"` profile while keeping `"PROCESS"` untouched.
  - `_assistant_tool_catalog.py`: dynamically assembles authorized tools (4 `SurgicalContextExplorer` primitives with `#Lstart-end` args, conditional `kb.search` when `rag_active=True`, `ontology.lookup`, unbounded PG18 `enabled_in_workspace` skills with real JSON Schema `input_parameters`, and MCP tools filtered by `mcp_tool_permissions` + RBAC).
  - `_assistant_tool_guards.py`: implements Step A (`PermissionBrokerService` `passthrough` + `READ_SOURCE` + observer/scope check), Step B (deterministic Lock V5 + per-tool `human_authored_required` guard producing `CONTINUE_IN_PROCESS` proposal + `HumanArbitrationRequested` outbox event), and `<untrusted_tool_output>` wrapper neutralizing closing tags and `[LAYER_*]` / `[CONSTITUTIONAL_*]` markers.
  - `_assistant_tool_idempotency.py`: `RedisToolIdempotencyStore` enforcing `idem:{turn_id}:{iteration}:{tool_call_id}` single execution.
  - `_assistant_tool_execution.py`: timeout-capped (`asyncio.wait_for`) dispatcher for surgical primitives, RAG search, ontology lookup, Tier 1/2 sandboxed skills (`SandboxPort`), and read-only MCP tools.
  - `_assistant_tool_audit.py`: secret-masked `audit_ledger` writer (`ASSISTANT_TOOL_INVOKED` / `ASSISTANT_TOOL_DENIED`), `HumanArbitrationRequested` outbox emitter, and canonical SSE event builder (`tool_call`, `tool_result`, `approval_required`).
  - `governed_tool_router.py`: `GovernedAssistantToolRouter` composing Steps A -> B -> C -> D -> E.
- `packages/orcia-core/src/orcia_core/orchestration/assistant_citations_and_v5_guard.py` & `assistant_agent_synthesis.py`:
  - Expose deterministic `evaluate_tool_v5_and_human_anchor_guard` and mark the legacy lexical `HUMAN_ANCHOR_WRITE_REFUSAL` intent branch deprecated for `Story 26.7` cleanup without breaking existing `3.3`/`3.4` evals.

### 2.3 Backend API, Composition Root & Capabilities Registry (`apps/api/`, `docs/product/`)
- `apps/api/src/orcia_api/dependencies/assistant_tools.py` (re-exported in `dependencies/__init__.py`):
  - Composition Root provider `get_governed_assistant_tool_router(request)` wiring `PermissionBrokerService`, `MatrixPermissionEvaluator`, `SurgicalContextExplorer`, `SubprocessTier1SandboxAdapter`, `SqlAuditLedgerService`, `RedisToolIdempotencyStore`, `SqlHybridRagRepository`, PG18 `OntologyGovernanceService`, `SqlDomainEventsOutboxRepository`, and `GovernedMcpExposureService`.
  - Async catalog context loader `build_assistant_tool_catalog_context_async(request, ...)` reading PG18 skills (`load_agents_and_skills_from_postgres18`) and MCP exposure specs without any 10-item cap.
- `apps/api/src/orcia_api/routers/_assistant_llm_tools_and_budget.py`, `_assistant_turn_producer_tool_loop.py`, `_assistant_turn_producer.py`, `assistant_background_turns.py`, `_assistant_turns_v2_routes.py`, `_assistant_llm_stream_bridge.py`, `assistant_llm_bridge.py`:
  - Replace hardcoded single tool & `[:10]` skill cap with `GovernedAssistantToolRouter.build_authorized_catalog(...)`.
  - Execute multi-step tool loops through `AssistantToolExecutorPort` -> `GovernedAssistantToolRouter`, pushing `tool_call`, `tool_result`, and `approval_required` SSE events to the Redis Stream and re-injecting `<untrusted_tool_output>` tool messages.
- `docs/product/capabilities.yaml`:
  - Add `CAP-260` ("Governed Tool Loop for Mon Assistant") with `verification: api`, `origin: epic`, `origin_ref: "26-6b-governed-assistant-tool-router-broker-v5-anchors-and-audit"`, `e2e_remediation_ref: "Story 26.10 (E2E spec 22 runtime promotion per D9)"`, and `pnpm site:sync && pnpm site:check` verification.

### 2.4 User Interface (`apps/web/`)
- **No frontend UI changes in Story `26.6b`**: UI wiring and E2E spec `22` cutover occur in Stories `26.7` and `26.10`.

### 2.5 Test Pyramid Impact Analysis (`AD-17` — Layers 1 to 5 + Security)
- **Layer 1a (`tests/unit/`)**: `tests/unit/test_story_26_6b_governed_tool_router_and_catalog.py` covering dynamic catalog assembly, conditional `kb.search`, >10 PG18 skills, MCP RBAC filtering, Steps A/B/C/D/E, `asyncio.wait_for` timeout handling, `ASSISTANT` profile unreachability of `ConnectorReflexiveWriteGateAdapter`, and `test_core_domain_isolation.py` / `test_zero_orphan_sql_adapters_audit.py` / `test_story_16_2_*`.
- **Layer 2 (`tests/integration/api/`)**: `tests/integration/api/test_story_26_6b_tool_router_audit_outbox_postgres18.py` booting real `create_app()` (0 `dependency_overrides`) against PG18 + Redis 7.4 `testcontainers` and verifying `audit_ledger` (`ASSISTANT_TOOL_INVOKED`, `ASSISTANT_TOOL_DENIED`), `domain_events_outbox` (`HumanArbitrationRequested`), and Redis idempotency via SQL `SELECT`.
- **Layer 3 (Contracts & Architecture)**: `ruff check`, `ruff format --check`, `mypy --strict`, `lint-imports` (5/5 contracts), `export_openapi.py --check`, `pnpm site:sync && pnpm site:check`.
- **Layer 4 (`tests/evals/`)**: `tests/evals/golden/assistant_tool_output_injection.jsonl` + `tests/evals/test_assistant_tool_output_injection.py` validating `0 $` anti-injection neutralization via `DeterministicCassetteLLM`.
- **Layer Security**: `detect-secrets-hook`, `scrub_connector_secrets`, SSRF & passthrough confused-deputy checks, `READ_ONLY_OBSERVER` denial, and prompt-injection tag neutralization.
- **Layer 5 (Playwright E2E)**: Deferred to Story `26.7` / `26.10` (`CAP-260` stays `verification: api` per `D9`).

---

## 3. Summary of Modifications & Results (Bilan des Modifications)

### 3.1 Files Created & Modified
All `56` created and modified non-generated source files under `packages/` and `apps/api/` comply strictly with the `<= 300` lines limit (maximum `300` lines in `apps/api/src/orcia_api/routers/_assistant_turn_producer.py`; `0` schema migrations, single linear Alembic head `20261122_266a (head)`):

| Layer / Area | Created or Modified Files | Max Lines | Summary |
| :--- | :--- | :--- | :--- |
| **Ports & Kernel Events** | `packages/orcia-core/src/orcia_core/ports/{__init__.py,assistant_tool_executor_port.py}`, `packages/orcia-core/src/orcia_core/kernel/_orchestration_events.py` | `214` | Pure hexagonal `AssistantToolExecutorPort` & `ToolIdempotencyStorePort` protocols (zero SDK imports) and `HumanArbitrationRequested` outbox event support. |
| **Governed Tool Router (`orcia_core.agents`)** | `governed_tool_router.py`, `_assistant_tool_{catalog,guards,idempotency,execution,sanitization,audit}.py`, `__init__.py` | `297` | Dynamic authorized catalog (`4` `SurgicalContextExplorer` primitives, conditional `kb.search`, `ontology.lookup`, unbounded PG18 `enabled_in_workspace` skills, RBAC-filtered MCP tools) and Steps A->E pipeline (`PermissionBrokerService` `passthrough`/`READ_SOURCE`, Lock V5 & deterministic Human-Anchor guard with `HumanArbitrationRequested` outbox, Redis `idem:{turn_id}:{iteration}:{tool_call_id}`, `asyncio.wait_for` sandboxed dispatch, `scrub_connector_secrets`, `<untrusted_tool_output>` neutralization, and `audit_ledger`). |
| **Execution Profile Isolation (`orcia_core.agents`)** | `reflexive_schemas.py`, `_runtime_helpers.py`, `_assistant_profile_guard.py`, `reflexive_runtime.py` | `299` | Added `ExecutionProfile = Literal["PROCESS", "ASSISTANT"]` ensuring `ConnectorReflexiveWriteGateAdapter` / `ReflexiveWriteGatePort` is structurally unreachable in `"ASSISTANT"` profile while keeping `"PROCESS"` defaults intact. |
| **Orchestration, MCP & Cassettes** | `assistant_citations_and_v5_guard.py`, `_assistant_citations_verifier.py`, `assistant_outbox_emitter.py`, `assistant_agent_synthesis.py`, `governed_mcp_exposure.py`, `_governed_mcp_helpers.py`, `remote_test_bench_and_mcp_exposure.py`, `agents_and_skills_models.py`, `_agents_and_skills_{builders,outcomes,types}.py`, `_internal/{sql_agents_and_skills.py,_sql_agents_hydration.py}`, `testing/_cassette_tool_cassettes.py` | `297` | Deterministic `evaluate_tool_v5_and_human_anchor_guard`, `AD-20`-clean `get_args(AgentOutputContractFormat)` hydration split (`197` L), MCP tool RBAC filtering, and deterministic `0 $` tool cassettes. |
| **Composition Root & FastAPI Routers (`apps/api/`)** | `dependencies/{__init__.py,assistant_tools.py,_assistant_tools_helpers.py,_assistant_tools_ontology.py,_assistant_guards.py,reflexive_execution.py,workspace_and_packs.py,_telemetry_sinks.py,_topology_sync.py}`, `routers/{_assistant_llm_tools_and_budget.py,_assistant_turn_producer.py,_assistant_turn_producer_tool_loop.py,_assistant_tool_loop_rounds.py,_assistant_turns_v2_routes.py,_assistant_llm_stream_bridge.py,_assistant_background_registry.py,_assistant_turn_consumer.py,_assistant_prompt_sanitization.py,_assistant_usage_telemetry.py,_agents_and_skills_helpers.py,_executions_trace_helpers.py,_finops_topology_sync.py,assistant_background_turns.py,assistant_llm_bridge.py,assistant_llm_prompts.py,assistant_workspace.py,executions_trace.py}` | `300` | Composition Root wiring for `GovernedAssistantToolRouter`, unbounded PG18/MCP catalog assembly, real tool-loop execution inside turn producer & bridges, and `<= 300` L helper splits. |
| **Capabilities, Docs & Tests** | `docs/product/capabilities.yaml` (`CAP-260`), `docs/implementation-artifacts/tech-lead-reports/26-6b-...-tech-lead-report.md`, `tests/unit/test_story_26_6b_*.py`, `tests/evals/{golden/assistant_tool_output_injection.jsonl,test_assistant_tool_output_injection.py}`, `tests/integration/api/test_story_26_6b_tool_router_audit_outbox_postgres18.py`, plus `4` updated existing unit specs & `site:sync` artifacts | — | Registered `CAP-260` (`verification: api`, `D9` E2E promotion in Story `26.10`) and comprehensive unit, eval, security, and PG18+Redis integration suites. |

### 3.2 Metrics, Coverage & Static Quality Results
- **21-Module Story `26.6b` Branch Coverage (`>= 90%`)**: **`93%`** (`1156` statements, `52` missed, `242` branches, `32` partial branches; `COVERAGE_FILE=/tmp/.cov_26_6b .venv/bin/coverage report --fail-under=90` **PASSED**).
- **Module-level coverage highlights**: `governed_tool_router.py` (`100%`), `_assistant_tool_catalog.py` (`100%`), `_assistant_tool_idempotency.py` (`100%`), `_assistant_tool_audit.py` (`100%`), `_assistant_profile_guard.py` (`100%`), `assistant_tool_executor_port.py` (`100%`), `_orchestration_events.py` (`100%`), `agents/__init__.py` (`100%`), `governed_mcp_exposure.py` (`100%`), `remote_test_bench_and_mcp_exposure.py` (`100%`), `assistant_agent_synthesis.py` (`98%`), `assistant_citations_and_v5_guard.py` (`98%`), `assistant_outbox_emitter.py` (`95%`), `_assistant_citations_verifier.py` (`94%`), `_assistant_tool_sanitization.py` (`93%`), `reflexive_schemas.py` (`93%`), `_assistant_tool_guards.py` (`92%`), `_governed_mcp_helpers.py` (`90%`).
- **Source File Volumetry**: `56/56` modified and created non-generated backend source files `<= 300` lines (`wc -l`).
- **Alembic Schema Head**: `.venv/bin/alembic -c infra/migrations/alembic.ini heads` = `20261122_266a (head)` (single linear head).

### 3.3 Full Test Pyramid Validation (`AD-17`)
All verification checks were independently executed post-final-edit with zero source modifications:

| Verification Layer / Gate | Command / Scope | Result |
| :--- | :--- | :--- |
| **Layer 3 Static, Typing, Boundaries & Secrets** | `ruff check .`, `ruff format --check .`, `mypy --strict packages/orcia-core packages/orcia-connectors apps/api apps/worker`, `lint-imports`, `lint_spine.py`, `scripts/export_openapi.py --check`, `detect-secrets-hook --baseline .secrets.baseline` | **PASSED** (`0` ruff errors across `1529` formatted files; `0` mypy issues across `714` source files; `5/5` `lint-imports` contracts kept across `756` files / `5500` dependencies; `0` spine findings; `0-diff` OpenAPI; `0` secret findings). |
| **Layer 1 & Layer 4 + Security/Contract Suites (`--no-cov`)** | `tests/unit` (`136` pure unit files chunked across `6` runs = `923 passed` + `6` unit-dir `testcontainers` files `test_story_3_2e..5_1` = `25 passed`), plus `tests/evals`, `tests/security`, `tests/contract`, `test_story_7_0c`, `test_epic_11_story_11_2` (`166 passed`) | **PASSED** (`1114 passed` across Python unit/evals/security/contract suites, `0` failures). |
| **Layer 2 PG18 + Redis Integration (`--no-cov`)** | `test_story_26_6b_tool_router_audit_outbox_postgres18.py`, `test_story_26_6a_supports_tools_postgres18.py`, `test_story_26_5_*.py`, `test_story_16_2_reflexive_runtime_and_sse_postgres18.py` (`7 passed`) + `test_story_26_4a_*.py`, `test_story_26_4b_*.py`, `test_story_26_3_*.py`, `test_story_26_1_*.py`, `test_story_25_5_*.py` (`8 passed`) | **PASSED** (`15 passed`, `0` failures on ephemeral PostgreSQL 18 + Redis 7.4 `testcontainers` with real `create_app()`). |
| **TypeScript / SPA Suites** | `pnpm turbo run lint typecheck test` (`@orcia/api-client`, `@orcia/ui`, `@orcia/web`) | **PASSED** (`9/9` Turbo tasks, `261` `@orcia/web` tests in `67` files). |
| **Layer 5 Playwright Desktop E2E** | `playwright test --project=desktop-cockpit` (`00`, `02`, `12-finops`, `12-epic16`, `16`, `21`, `ORCIA_E2E_SEED_FIXTURES` unset, isolated `ORCIA_E2E_CAMPAIGN_DIR`) | **PASSED** (`15 passed, 1 skipped (mobile-only), 0 failed (2.9m)`; `git diff docs/implementation-artifacts/e2e-campaign-epic-*` empty). |
| **Docs, Site & GitNexus Sync** | `pnpm site:sync && pnpm site:check`, `.venv/bin/python scripts/check_implementation_docs.py`, `npx gitnexus analyze --index-only .` | **PASSED**. |
