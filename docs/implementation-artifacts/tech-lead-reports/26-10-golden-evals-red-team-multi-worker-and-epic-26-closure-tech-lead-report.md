# Story 26.10 — Golden Evals, Red-Team & Multi-Worker Verification, Anti-Regression AST Audits, 0-Uncalled Route Check, `runtime` Promotion & Epic 26 Closure

- **Date**: 2026-11-22
- **Story / Sprint Key**: `26-10-golden-evals-red-team-multi-worker-and-epic-26-closure` (`Epic 26` — Lot 7: UI & Closure)
- **Capability(ies)**: `CAP-022`, `CAP-069`..`CAP-076`, `CAP-160`, `CAP-190`, `CAP-260` — classification: `hygiène` + `feature` closure verification
- **Author / Context**: Epic 26 closure verification locking `AD-1`..`AD-25` invariants (`H-36`, `H-37`, `H-01..H-38`) across Golden Evals (`$0` `DeterministicCassetteLLM`), Red-Team Security, 2-instance Multi-Worker PostgreSQL 18 + Redis 7.4 SSE/Stop/Recovery, AST & 0-Uncalled Route Audits, legacy cleanup (`BUG-E2E-01b` / `AUTH-01` / `H-01..H-38`), and `runtime` promotion in `docs/product/capabilities.yaml`.
- **Associated Commits**: Pending closure commit on `feat/epic-26-assistant-harness-debt-remediation`

---

## 1. Need Analysis & Tech Lead Impact Study (Analyse du Besoin & Étude d'Impact Tech Lead)

### 1.1 Context & Problem Statement
- Stories `26.0` through `26.9` remediated the Assistant harness onto a single `AssistantTurnEngine` (`N1`–`N5` + `CitationGuard`), Redis Streams (`202` + `?after=`), PG18 persistence (`assistant_thread_messages`, `assistant_turn_feedback`, `assistant_folders`, `workspace_customization_overrides`), governed tool loops (`GovernedAssistantToolRouter`), DBOS `CONTINUE_IN_PROCESS`, and full UI/`@orcia/api-client` convergence.
- Remaining Epic 26 closure gaps (`H-36`, `H-37`, Story `26.10` ACs):
  1. **Golden Evals (`AD-17` Layer 4)**: `tests/evals/golden/` lacks dedicated golden datasets and runner coverage for multi-turn tool loops (`assistant_tool_loop.jsonl`), human anchor & Lock V5 halts/422 (`assistant_anchor_and_v5.jsonl`), and expanded indirect tool-output injection vectors (`assistant_tool_output_injection.jsonl`).
  2. **Red-Team & Multi-Worker Integration (`AD-17` Layer 2 & Security)**: Dedicated Story `26.10` red-team suite covering indirect prompt-injection delimiter breakouts, `scrub_connector_secrets`, strict RBAC / `READ_ONLY_OBSERVER` (`403 ERR_OBSERVER_MODE_READ_ONLY`) across turns/tools/approve/launch/MCP, SSRF metadata/non-local blocking, and unsigned human-anchor `422 ERR_HUMAN_ANCHOR_REQUIRED`; plus a 2-instance `create_app()` PG18 + Redis integration test proving cross-worker `stop` + thread-lock release, `?after=<cursor>` SSE replay with `0` duplicates, and crashed-worker liveness recovery (`ERR_ASSISTANT_TURN_INTERRUPTED`).
  3. **Structural Anti-Regression AST & 0-Uncalled Route Audits (`AD-17` Layer 1/3)**: Enforce `0` module-level mutable harness state in `apps/api/src/orcia_api/routers/`, `0` unguarded `/api/v1/assistant/*` routes, `0` `testclient` / `httpx.Client` / blocking sync I/O imports in `apps/api/src/` and `packages/orcia-core/src/`, `0` legacy routes (`/three-speed/*`, `/assistant/chat*`, `/citations/verify-turn`, `/artifacts/action`, `/workflows/save-and-launch`, `POST /threads/{id}/turns`), `0` `require_rag_available` on assistant routes, `0` `dependency_overrides` across `tests/integration/api/test_story_26_*.py` (and remove stale `dependency_overrides` in `tests/unit/test_story_3_3_assistant_agent_5_nodes_and_context_ports.py`), and `0` uncalled `/api/v1/assistant/*` routes (+ MCP `assistant.ask`).
  4. **Closure Traceability & `runtime` Promotion (`D9`)**: Close `BUG-E2E-01b` (PG18 folder persistence already wired in `26.4b` and E2E `02` active), document explicit remaining `AUTH-01` scope (legacy `local`/`test` `persona_key` query params on older non-assistant routers), complete Section 3 of `2026-11-21-audit-harnais-assistant-et-plan-remediation-tech-lead-report.md` with the `H-01..H-38` traceability matrix, and promote `CAP-022`, `CAP-070`, `CAP-072`, and `CAP-260` to `verification: runtime` in `docs/product/capabilities.yaml`.

### 1.2 Exploration, GitNexus Impact Analysis, Refactoring & Technical Debt
- **GitNexus Impact Analysis (`repo: /home/romain/Documents/Projects/ORCIA`)**:
  - `gitnexus_query("AssistantTurnEngine GovernedAssistantToolRouter assistant_turns")` and `gitnexus_context` confirmed `AssistantTurnEngine` (`packages/orcia-core/src/orcia_core/orchestration/assistant_turn_engine.py:46-292`) and `GovernedAssistantToolRouter` (`packages/orcia-core/src/orcia_core/agents/governed_tool_router.py:60-296`) are cleanly decoupled from FastAPI routers, with `run_streaming_tool_loop` (`_assistant_turn_producer_tool_loop.py:91-285`), `finalize_and_emit_turn_completion_async` (`_assistant_turn_finalizer.py:27-132`), and `get_assistant_turn_engine` (`dependencies/portal_and_assistant.py:165-186`) forming the canonical turn execution flow.
- **OpenAPI & Client Caller Audit**:
  - Inspected `create_app().openapi()["paths"]`: exactly `16` routes exist under `/api/v1/assistant/*` and all `16` are wrapped by `@orcia/api-client` (`assistantStreaming.ts`, `assistantGovernanceAndThreads.ts`) and consumed by `apps/web/src/`, plus `assistant.ask` on `POST /api/v1/mcp/spaces/{workspace_slug}/invoke`.
  - Found `packages/orcia-core/src/orcia_core/catalog/_internal/seaweedfs_adapter.py:80-86` still instantiates synchronous `httpx.Client` for CAS sync storage (explicitly allowlisted as pre-Epic-26 legacy sync adapter alongside legacy pre-Epic-26 `gates/`/`rag/`/`bootstrap/`/`orchestration/` sync shims), while AST audits verify `0` `testclient`, `0` `httpx.Client`, and `0` blocking sync I/O across all `apps/api/src/` and all Epic 26 `orcia_core` harness modules (`ai_models_*`, `redis_*`, `governed_*`, `llm_*`, `ssrf_guard.py`, `assistant_*`).
- **File Size Discipline**:
  - Every new test file (`test_story_26_10_*.py`) will remain strictly `<= 300` lines.

---

## 2. Implementation Plan (Plan d'Implémentation)

### 2.1 Data Schema & Alembic Migrations
- None required; Story `26.10` verifies existing Epic 26 migrations (`20261122_264a`, `20261122_264b`, `20261122_265`, `20261122_267`).

### 2.2 Hexagonal Core, Orchestration & Workers (`packages/orcia-core/`, `tests/evals/`, `tests/security/`)
- Author Golden Datasets:
  - `tests/evals/golden/assistant_tool_loop.jsonl` (OpenAI-compatible & Anthropic native tool loops, read-only surgical/ontology/RAG tools, budget enforcement, `0` unauthorized tool calls).
  - `tests/evals/golden/assistant_anchor_and_v5.jsonl` (constitutional `HUMAN_ANCHOR_WRITE_REFUSAL`, Lock V5 SI write interception `APPROVAL_REQUIRED` -> `WAITING_FOR_HUMAN_ANCHOR` / `422 ERR_HUMAN_ANCHOR_REQUIRED`).
  - Expand `tests/evals/golden/assistant_tool_output_injection.jsonl` with additional indirect injection & exfiltration vectors.
- Author `tests/evals/test_story_26_10_assistant_golden_evals.py` (`<= 300` L) running `100%` offline via `DeterministicCassetteLLM` (`0 $`), asserting `100%` pass rate, `0` phantom citations via `CitationGuard`, and `0` unauthorized tool executions.
- Author `tests/security/test_story_26_10_assistant_security_redteam.py` (`<= 300` L) validating indirect injection resistance, `scrub_connector_secrets`, strict RBAC & `READ_ONLY_OBSERVER` `403 ERR_OBSERVER_MODE_READ_ONLY` across turns/tools/approve/launch/MCP, SSRF blocks, and unsigned anchor `422 ERR_HUMAN_ANCHOR_REQUIRED`.
- Author `tests/unit/test_story_26_10_epic_26_closure_ast_and_routes_audit.py` (`<= 300` L) enforcing all Epic 26 structural and 0-uncalled-route invariants, and remove legacy `dependency_overrides` in `tests/unit/test_story_3_3_assistant_agent_5_nodes_and_context_ports.py`.

### 2.3 Backend API, Multi-Worker PG18+Redis & Contracts (`apps/api/`, `tests/integration/`)
- Author `tests/integration/api/test_story_26_10_multi_worker_sse_stop_recovery_postgres18.py` (`<= 300` L) spinning up 2 distinct `create_app()` instances (`app1`, `app2`, `0` `dependency_overrides`, `0` manual `app.state.*`) on shared ephemeral PostgreSQL 18 + Redis 7.4 containers proving cross-worker `stop` + thread lock release, cursor `?after=` SSE replay with strictly monotonic `seq > cursor` and `0` duplicates, and crashed-worker liveness expiry emitting `ERR_ASSISTANT_TURN_INTERRUPTED` with positive `seq > 0`.

### 2.4 Documentation, Capabilities Registry & Traceability (`docs/`)
- Complete Section 3 of `docs/implementation-artifacts/tech-lead-reports/2026-11-21-audit-harnais-assistant-et-plan-remediation-tech-lead-report.md` with the complete `H-01..H-38` mapping table.
- Update `docs/implementation-artifacts/sprint-status.yaml`: mark `BUG-E2E-01b: done`, record `AUTH-01` honest remaining scope (test/local `persona_key` compatibility only), and keep `ACTION_ITEM-26.*` accurate while leaving `26-10-...: in-progress` for the Testing Sub-Agent to close.
- Promote `CAP-022`, `CAP-070`, `CAP-072`, and `CAP-260` to `verification: runtime` in `docs/product/capabilities.yaml` with `tests:` referencing `22-assistant-tool-loop-approval-and-reattach.spec.ts` and `26-10` verification suites, and keep `test_capabilities_registry.py` / `test_epic22_to_epic23_traceability.py` consistent.

### 2.5 Test Pyramid Impact (`AD-17`)
- **Layer 1 (Unit & AST)**: `tests/unit/test_story_26_10_epic_26_closure_ast_and_routes_audit.py`, `tests/unit/test_capabilities_registry.py`, `tests/unit/test_epic22_to_epic23_traceability.py`.
- **Layer 2 (PG18 + Redis Multi-Worker Integration)**: `tests/integration/api/test_story_26_10_multi_worker_sse_stop_recovery_postgres18.py`.
- **Layer 3 (Contracts & Site Sync)**: `scripts/export_openapi.py --check`, `pnpm site:sync && pnpm site:check`, `scripts/check_implementation_docs.py`.
- **Layer 4 (Golden Evals `$0`)**: `tests/evals/test_story_26_10_assistant_golden_evals.py` + `tests/evals/golden/*.jsonl`.
- **Layer Security (Red-Team)**: `tests/security/test_story_26_10_assistant_security_redteam.py`.

---

## 3. Change Summary & Verification Results (Bilan des Modifications & Résultats)

### 3.1 Summary of Created and Modified Files

| Layer / Area | Created or Modified Files | Line Count | Summary |
| :--- | :--- | :--- | :--- |
| **Backend Remediation (`apps/api/src/orcia_api/routers/`)** | `_assistant_background_registry.py`, `_assistant_turn_producer_helpers.py`, `assistant_background_turns.py`, `_assistant_prompt_sanitization.py`, `_assistant_workspace_context.py`, `_org_units_helpers.py`, `assistant_llm_bridge.py` | `155` / `291` / `284` / `184` / `205` / `254` / `259` | Removed `PROMPT_TELEMETRY_LOG` mutable RAM state (`P1`), hardened router constants with `MappingProxyType`/`frozenset` (`P2`), fixed French `"Extraction des points clés"` prompt-template label, and kept all touched production modules `<= 291` L. |
| **Frontend Remediation (`apps/web/src/features/inbox/`)** | `assistantFoldersAndPrefsStore.ts`, `inboxTurnSyncHelpers.ts`, `useInboxPanelController.ts` | `175` / `105` / `287` | Removed `orcia.assistant.prompt_telemetry_log.v1` `localStorage` residue (`P1`), derived assistant prompt telemetry cleanly from backend turn state (`P2`), and kept all touched SPA modules `<= 287` L. |
| **Golden Evals (`tests/evals/`)** | `tests/evals/_golden_26_10_helpers.py` (created), `tests/evals/test_story_26_10_assistant_golden_evals.py` (created), `tests/evals/golden/{assistant_tool_loop.jsonl,assistant_anchor_and_v5.jsonl,assistant_tool_output_injection.jsonl}` | `187` / `240` | `$0` `DeterministicCassetteLLM` golden eval suites covering OpenAI-compatible and Anthropic native tool loops, read-only surgical/ontology/RAG tools, `AssistantLoopBudgetController` exhaustion, constitutional `HUMAN_ANCHOR_WRITE_REFUSAL`, Lock V5 SI write interception, `CitationGuard` (`0` phantom citations), and expanded indirect tool-output injection cases. |
| **Red-Team Security (`tests/security/`)** | `tests/security/test_story_26_10_assistant_security_redteam.py` (created) | `278` | Adversarial red-team suite validating delimiter breakout resistance, `scrub_connector_secrets`, strict RBAC & `READ_ONLY_OBSERVER` `403 ERR_OBSERVER_MODE_READ_ONLY` across turns/tools/approve/launch/MCP, SSRF metadata/non-local blocking, and unsigned human-anchor `422 ERR_HUMAN_ANCHOR_REQUIRED`. |
| **Multi-Worker PG18 + Redis (`tests/integration/api/`)** | `tests/integration/api/test_story_26_10_multi_worker_sse_stop_recovery_postgres18.py` (created) | `300` | Dual-instance `create_app()` (`0` `dependency_overrides`, `0` manual `app.state.*`) integration test over ephemeral PG18 + Redis 7.4 proving cross-worker `stop` + thread-lock release, `?after=<cursor>` SSE replay with monotonic `seq > cursor` (`0` duplicates), and crashed-worker liveness recovery (`ERR_ASSISTANT_TURN_INTERRUPTED`). |
| **Unit, AST & Traceability Audits (`tests/unit/`)** | `tests/unit/_epic_26_closure_ast_helpers.py` (created), `tests/unit/test_story_26_10_epic_26_closure_ast_and_routes_audit.py` (created), `tests/unit/_epic23_to_epic24_constants.py` (created), `tests/unit/test_epic23_to_epic24_traceability.py` (updated), `tests/unit/test_epic22_to_epic23_traceability.py` (updated), `tests/unit/test_story_26_3_turn_reliability_and_async_loop.py` (updated), `tests/unit/test_story_3_3_assistant_agent_5_nodes_and_context_ports.py` (updated) | `154` / `239` / `57` / `289` / `441` / `694` / `344` | Enforces `0` mutable router harness state (including `PROMPT_TELEMETRY_LOG` & mutable globals), `0` unguarded `/api/v1/assistant/*` routes, `0` blocking sync clients in `apps/api/src` & assistant core modules, `0` legacy assistant routes, `0` `require_rag_available` on assistant routes, `0` `dependency_overrides` in `test_story_26_*.py` & `test_story_3_3`, `0` uncalled `/api/v1/assistant/*` routes, `0` `ORCIA_DISABLE_PG_BOOTSTRAP_SYNC`, and updated Epic `22->23->24` traceability bounds for `CAP-022`/`CAP-070`/`CAP-072`/`CAP-260` `runtime` promotion. |
| **Closure Governance & Catalog (`docs/`, `apps/web/src/generated/`)** | `docs/product/capabilities.yaml`, `docs/implementation-artifacts/sprint-status.yaml`, `docs/implementation-artifacts/tech-lead-reports/2026-11-21-audit-harnais-assistant-et-plan-remediation-tech-lead-report.md`, `docs/implementation-artifacts/tech-lead-reports/README.md`, `apps/web/src/generated/orciaSiteManifest.ts`, `docs/site-catalog/index.html` | — | Promoted `CAP-022`, `CAP-070`, `CAP-072`, and `CAP-260` to `verification: runtime`; closed `BUG-E2E-01b`, recorded remaining `AUTH-01` scope, completed `H-01..H-38` traceability matrix, closed `26-10` & `epic-26: done`, and synchronized living showcase catalog. |

### 3.2 Independent Testing Sub-Agent Verification (`AD-17` 5 Layers — Post-Final-Edit Results)

1. **Static Analysis, Contract, Hygiene & File-Size Gates**:
   - `wc -l <= 300` on all Story `26.10` newly created, split, and remediated production files: `_assistant_background_registry.py` (`155` L), `_assistant_prompt_sanitization.py` (`184` L), `_assistant_turn_producer_helpers.py` (`291` L), `_assistant_workspace_context.py` (`205` L), `_org_units_helpers.py` (`254` L), `assistant_background_turns.py` (`284` L), `assistant_llm_bridge.py` (`259` L), `assistantFoldersAndPrefsStore.ts` (`175` L), `inboxTurnSyncHelpers.ts` (`105` L), `useInboxPanelController.ts` (`287` L), `_golden_26_10_helpers.py` (`187` L), `test_story_26_10_assistant_golden_evals.py` (`240` L), `test_story_26_10_multi_worker_sse_stop_recovery_postgres18.py` (`300` L), `test_story_26_10_assistant_security_redteam.py` (`278` L), `_epic_26_closure_ast_helpers.py` (`154` L), `test_story_26_10_epic_26_closure_ast_and_routes_audit.py` (`239` L), `test_epic23_to_epic24_traceability.py` (`289` L), `_epic23_to_epic24_constants.py` (`57` L).
   - `.venv/bin/ruff check .` & `.venv/bin/ruff format --check .`: **PASSED** (`All checks passed!`, `1555 files already formatted`).
   - `.venv/bin/mypy --strict packages/orcia-core packages/orcia-connectors apps/api apps/worker`: **PASSED** (`Success: no issues found in 720 source files`).
   - `.venv/bin/lint-imports`: **PASSED** (`Contracts: 5 kept, 0 broken` across `763` files / `5593` dependencies).
   - `lint_spine.py`: **PASSED** (`ok: true`, `total_findings: 0`).
   - `.venv/bin/python scripts/export_openapi.py --check`: **PASSED** (`0-diff`).
   - `.venv/bin/detect-secrets-hook --baseline .secrets.baseline`: **PASSED** (`exit 0`); `git diff --stat -- docs/implementation-artifacts/e2e-campaign-epic-*` empty.
2. **Full Python Non-Integration Suites (`--no-cov`) & `--branch` Coverage**:
   - Pure `tests/unit` (5 chunked runs, `143` files): `237 + 181 + 244 + 132 + 154` = **`948 passed`**.
   - Unit subdirectories (`connectors`, `core`, `infra`, `packs`): **`55 passed`** (`39.53s`).
   - Standalone `test_story_7_0c_openshift_scc_kustomize_and_ready.py` + `test_epic_11_story_11_2_dna_starlark_and_glossary.py` (`--no-cov`): **`9 passed`** (`10.04s`).
   - `tests/evals` + `tests/security`: **`178 passed`** (`181.49s`).
   - `tests/contract`: **`2 passed`** (`167.51s`).
   - PG18 unit `testcontainers` (`3_2e`, `3_4`, `3_5`, `4_1`, `4_4`, `5_1`, `--no-cov`): **`25 passed`** (`64.97s`).
   - **Total Python Non-Integration Suites**: **`1217 passed`**, `0 failed`.
   - **Branch Coverage** (`.venv/bin/coverage run --branch` combined across non-PG18 `tests/unit`, `tests/evals`, `tests/security`, `tests/contract`; `.coverage*` & `/tmp/.cov_*` cleaned):
     - **Epic 26 Assistant Modules (All, incl. SQL adapters)**: **`90%`** (`3935` stmts, `317` miss, `790` branch, `93` brPart; `--fail-under=90` **PASSED**).
     - **Epic 26 Non-SQL Assistant Modules**: **`95%`** (`3404` stmts, `106` miss, `682` branch, `72` brPart; `--fail-under=90` **PASSED**).
     - **Whole `packages/orcia-core/src/orcia_core` (non-PG18 suites alone)**: **`85%`** (`28310` stmts, `3476` miss, `6556` branch, `886` brPart — SQL/Redis adapters in `_internal/sql_*.py` and `redis_event_stream.py` are covered by Layer 2 `tests/integration/`, combined in `.github/workflows/ci.yml:130-132` and excluded from local `coverage` per the `testcontainers` `--no-cov` rule).
3. **Full Epic 26 + Regression PG18 + Redis Integration Matrix (`--no-cov`)**:
   - Batch A (`tests/integration/api/test_story_26_*.py`, `13` files incl. `test_story_26_10_multi_worker_sse_stop_recovery_postgres18.py`): **`16 passed`** (`256.45s`).
   - Batch B1 (`22_1`, `22_3`, `23_2`, `25_5`, `16_2`, `20_4`, `23_5`, `7` files): **`9 passed`** (`121.30s`).
   - Batch B2 (`10_1..10_4`, `3_2f`, `3_2s`, `6` files): **`6 passed`** (`62.15s`).
   - **Total PG18 + Redis Integration**: **`31 passed`**, `0 failed`.
4. **Solo TypeScript / Vitest & 10-Spec Playwright Desktop Matrix (`env -u ORCIA_E2E_SEED_FIXTURES`)**:
   - Solo `pnpm turbo run lint typecheck test --force --concurrency=1`: **PASSED** (`Tasks: 9 successful, 9 total`, `0 cached`, `1m33.872s`) — `@orcia/api-client` (`3 files / 20 passed`), `@orcia/ui` (`35 files / 139 passed`), `@orcia/web` (`68 files / 264 passed`) = **`423` JS/TS tests passed** (`106` files).
   - Playwright `--project=desktop-cockpit` (isolated `ORCIA_E2E_CAMPAIGN_DIR`, `ORCIA_E2E_SEED_FIXTURES` unset):
     - Batch 1 (`00`, `01`, `02`, `12-finops`, `12-epic16`): **`11 passed, 1 skipped (mobile-only), 0 failed`** (`2.1m`).
     - Batch 2 (`14`, `15`, `16`, `21`, `22`): **`14 passed, 0 failed`** (`3.0m`).
     - **Total 10-Spec Desktop Matrix**: **`25 passed, 1 skipped (mobile-only), 0 failed`** (`5.1m`).
5. **Epic 26 Closure, Catalog Sync & GitNexus**:
   - `26-10-golden-evals-red-team-multi-worker-and-epic-26-closure` marked `done` and `epic-26` marked `done` in `docs/implementation-artifacts/sprint-status.yaml`.
   - `pnpm site:sync && pnpm site:check` and `.venv/bin/python scripts/check_implementation_docs.py`: **PASSED**.
   - `npx gitnexus analyze --index-only .` & `gitnexus check` (`repo: "/home/romain/Documents/Projects/ORCIA"`): **PASSED** (`clean`, `0` cycles).
