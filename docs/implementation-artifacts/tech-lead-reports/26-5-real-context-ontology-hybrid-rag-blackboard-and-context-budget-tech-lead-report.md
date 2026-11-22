# Story 26.5 — Real Context: PG18 Ontology Relevance (`ProfileSemanticTranslator` & Axioms), Async `SqlHybridRagRepository`, Active Blackboard Snapshots, Server `EvidenceTable`, `assistant_thread_messages` & Token Budget Trimmer

- **Date**: 2026-11-22
- **Story / Sprint Key**: `26-5-real-context-ontology-hybrid-rag-blackboard-and-context-budget` (`Epic 26`, Lot 4)
- **Capability(ies)**: `CAP-022`, `CAP-190` — Classification: `feature`
- **Author / Context**: Dedicated Coding Sub-Agent (`bmad-dev-worker`) implementing Lot 4 of Epic 26 (`AD-7`, `AD-8`, `AD-15`, `AD-19`, `AD-24`, `AD-25`, `D4`, `H-12`, `H-13`, `H-18`, `R6`)
- **Associated Commits**: Pending Testing Sub-Agent verification and coordinator commit on `feat/epic-26-assistant-harness-debt-remediation`

---

## 1. Need Analysis & Tech Lead Impact Study (Analyse du Besoin)

### 1.1 Context & Problem Statement
- **Current Defects (`H-12`, `H-13`, `H-18`, `D4`, `R6`):**
  1. **Arbitrary / Empty Ontology Context (`H-12`):** `apps/api/src/orcia_api/routers/assistant_llm_prompts.py` currently pulls `list(getattr(ont_svc, "concepts", ()))[:8]` from `get_ontology_and_rag_services(request)`, which in `_core_providers.py` calls `build_empty_ontology_service()` in production (`fixture=False`). It never loads PG18 `ontology_concepts`, `ontology_relations`, or `ontology_axioms`, never calls `OntologyGovernanceService.resolve_snapshot(workspace_scope_id=...)`, never ranks concepts by lexical/vector relevance to the user query, never applies `ProfileSemanticTranslator` for `active_hat`, and never injects applicable axioms into Layer 2 of `AssistantPromptBuilder`.
  2. **Seeded / Disconnected RAG & Dummy Blackboard (`H-12`, `H-13`):** `apps/api/src/orcia_api/dependencies/_lifespan_services.py` wires `app.state.assistant_service` with `build_seeded_rag_service()` and `blackboard_snapshots_provider=lambda _ws: ()` instead of real PostgreSQL 18 `SqlHybridRagRepository.search_hybrid_rrf` and active workspace `blackboard_snapshots`. Furthermore, `SqlHybridRagRepository.search_hybrid_rrf` currently requires `query_embedding` unconditionally, whereas Story `25.5` requires Mon Assistant to remain operational with `1` active chat model and `0` active embedding models (`get_optional_embedding_port() -> None`).
  3. **Missing Server `EvidenceTable` in Assistant Turn Layer 4 (`H-13`):** Retrieved RAG chunks, active Blackboard snapshots, and catalog/permission slices are not consolidated by a deterministic server-side `EvidenceTable` helper enforcing `READ_SOURCE` & `CONFIDENTIAL_RESTRICTED` masking/filtering, `REFERENCE > ACTIVE` authority + freshness sorting, and `[STALE_WARNING]` markers before Layer 4 prompt injection.
  4. **Ephemeral History Splitting & Missing Token Budget Trimmer (`H-18`, `D4`, `R6`):** `_assistant_workspace_context.py` reconstructs thread history by splitting `target_thread.thread_summary.split(" | ")`, and no `assistant_thread_messages` table exists yet in PG18 (`D4`). Additionally, `build_multi_turn_messages` does not trim conversation history against the active model's `max_tokens_budget` (`workspace_llm_tier_mappings`), and SQL prompt-assembly latency (`R6` baseline for `ACTION_ITEM-26.3`) is not yet measured and logged.
- **Architectural & Invariant Constraints:**
  - Strict unidirectional `AD-19` boundaries (`lint-imports` 5/5 kept, zero framework/SDK imports in `orcia_kernel`, `orcia_core/domain`, or `orcia_core/ports`, zero cross-domain `_internal` imports).
  - Preserve Story `25.5` invariant (`get_optional_embedding_port` only; never add `require_rag_available` to assistant routes).
  - All touched non-generated source files must stay `<= 300` lines.
  - Zero orphan SQL adapters (`test_zero_orphan_sql_adapters_audit.py`).

### 1.2 Exploration, GitNexus Impact Analysis, Factorization & Technical Debt
- **GitNexus & Codebase Impact Findings:**
  - `gitnexus_query` (`AssistantPromptBuilder build prompt layer 2 layer 4 ontology rag blackboard`) and targeted `grep` identified the active callers:
    - `AssistantPromptBuilder` (`packages/orcia-core/src/orcia_core/orchestration/assistant_prompt_builder.py`, 296 L) is used by `AssistantHarness` and `apps/api/src/orcia_api/routers/assistant_llm_prompts.py`.
    - `OntologyGovernanceService` (`impact_and_promotion.py`), `ProfileSemanticTranslator` (`resolver.py`), and `sql_ontology_repository.py` (`list_concepts_pg`) currently lack PG18 loaders for `ontology_axioms` and `ontology_relations`.
    - `SqlHybridRagRepository.search_hybrid_rrf` (`packages/orcia-core/src/orcia_core/rag/_internal/sql_repository.py`, 315 L) is called by `ontology_and_rag.py` and needs optional-embedding support (`query_embedding: tuple[float, ...] | None = None`) plus wiring into `HybridRagVectorStoreAdapter` and the assistant federated context pipeline.
    - `_core_providers.py` (181 L) and `_lifespan_services.py` (146 L) import `build_empty_ontology_service()` and `build_seeded_rag_service()`.
    - `_assistant_workspace_context.py` (207 L), `_assistant_turns_v2_routes.py` (270 L), `_assistant_turn_producer.py` (294 L), and `_assistant_turn_producer_helpers.py` (294 L) drive turn history resolution, background SSE v2 turn execution, and telemetry flush.
- **Database Schema & Key Measurements:**
  - `assistant_threads` (`0025_story_10_4`) uses `thread_id UUID PRIMARY KEY`, `workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE`.
  - `blackboard_snapshots` (`0011_story_3_2`) links to `workspace_id` via `run_id UUID NOT NULL REFERENCES workflow_runs(id)`, with `branch_status IN ('ACTIVE', 'SUPERSEDED')` and `superseded_snapshot_ids_jsonb`.
  - `workspace_llm_tier_mappings` (`0022_epic_8`) carries `max_tokens_budget INTEGER NOT NULL DEFAULT 8192`.
  - Latest Alembic head is `20261122_264b`.
- **Factorization & Size Control Opportunities:**
  - Reuse existing `build_evidence_table_impl` (`_assistant_citations_verifier.py`), `filter_allowed_source_uris_with_evaluator` (`_assistant_guards.py`), `ProfileSemanticTranslator` (`ontology/resolver.py`), `OntologyHierarchyResolver.resolve_effective_ontology`, and `estimate_tokens_deterministic` (`llm_usage_telemetry.py`).
  - Split new capabilities into cohesive `<= 300`-line modules (`ontology/context_ranker.py`, `orchestration/assistant_evidence_table.py`, `orchestration/assistant_context_budget.py`, `orchestration/_internal/sql_assistant_thread_messages.py`, `blackboard/_internal/sql_blackboard_queries.py`, `apps/api/src/orcia_api/routers/_assistant_context_assembly.py`).

---

## 2. Implementation Plan (Plan d'Implémentation)

### 2.1 Data Schema & Alembic Migrations (`infra/migrations/versions/`)
- `infra/migrations/versions/20261122_265_story_26_5_assistant_thread_messages.py` (`down_revision = "20261122_264b"`):
  - Pure raw-SQL `op.execute(sa.text(...))` creating `assistant_thread_messages`:
    - `id UUID PRIMARY KEY` (`UUIDv7`)
    - `thread_id UUID NOT NULL REFERENCES assistant_threads(thread_id) ON DELETE CASCADE`
    - `workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE`
    - `turn_id UUID NOT NULL`
    - `parent_turn_id UUID NULL`
    - `role VARCHAR(16) NOT NULL CONSTRAINT assistant_thread_messages_role_check CHECK (role IN ('user', 'assistant'))`
    - `content TEXT NOT NULL`
    - `citation_map JSONB NOT NULL DEFAULT '{}'::jsonb`
    - `token_count INTEGER NOT NULL DEFAULT 0`
    - `created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`
    - `CONSTRAINT uq_assistant_thread_messages_turn_role UNIQUE (turn_id, role)` for retry idempotency (`AD-15` / `D4`)
  - Index `idx_assistant_thread_messages_thread_created ON assistant_thread_messages (thread_id, created_at)`.
  - Reversible `downgrade()` dropping index and table cleanly.
- Register `"assistant_thread_messages"` in `infra/scripts/maintenance/_first_boot_reset_guards.py` inside `ORDERED_MUTABLE_TABLES_TO_CLEAR` prior to `"assistant_threads"`.

### 2.2 Hexagonal Core, Context Pipeline & Adapters (`packages/orcia-core/`)
- **Ontology PG18 Loader & Relevance Ranker (`packages/orcia-core/src/orcia_core/ontology/`):**
  - Extend `_internal/sql_ontology_queries.py`, `_internal/sql_ontology_mappers.py`, and `_internal/sql_ontology_repository.py` with `list_relations_pg`, `list_axioms_pg`, and `load_ontology_governance_service_pg(engine)` (3 flat queries, zero N+1).
  - Add pure-domain `ontology/context_ranker.py` (`rank_ontology_snapshot_for_query`): resolves workspace hierarchy (`OntologyGovernanceService.resolve_snapshot`), computes lexical relevance (+ cosine similarity against embedded concept texts when an active `EmbeddingPort` provides embeddings), applies `ProfileSemanticTranslator.translate_concept(concept, active_hat)`, and extracts applicable axioms without any `list(concepts)[:8]` fallback on empty bundles.
- **Blackboard PG18 Workspace Provider (`packages/orcia-core/src/orcia_core/blackboard/`):**
  - Add `_internal/sql_blackboard_queries.py` (`list_active_workspace_blackboard_snapshots_pg(engine, workspace_id=..., limit=...)`) executing a single `JOIN workflow_runs` query (`workspace_id` isolation, filtering out `SUPERSEDED` snapshots and `superseded_snapshot_ids_jsonb`). Re-export cleanly via `orcia_core.blackboard`.
- **Hybrid RAG & Context Adapters (`packages/orcia-core/src/orcia_core/rag/`):**
  - Update `SqlHybridRagRepository.search_hybrid_rrf` (`sql_repository.py`) to accept `query_embedding: tuple[float, ...] | None = None`: when provided, execute full `halfvec(1024)` + `ts_rank_cd` RRF (`k=60`); when `None`, cleanly skip the vector `<=>` leg and rank lexically via `ts_rank_cd` without raising `NoActiveEmbeddingModelError` (`Story 25.5` invariant).
  - Update `HybridRagVectorStoreAdapter` and `CatalogAndBlackboardContextSourceAdapter` (`context_adapters.py`) to support optional `SqlHybridRagRepository` and async `blackboard_snapshots_provider` / `fetch_context_slices_async`.
- **Server `EvidenceTable` & Token Budget Trimmer (`packages/orcia-core/src/orcia_core/orchestration/`):**
  - Create `assistant_evidence_table.py`: merges retrieved RAG hits (`HybridRagHit`/`VectorSearchHitRecord`), Blackboard & catalog slices (`ContextSliceRecord`), and ranked ontology glossary/axioms (`RawGlossaryCandidate`), enforces `READ_SOURCE` & `CONFIDENTIAL_RESTRICTED` server filtering/masking via `allowed_source_uris` and `AssistantCitationAndV5GuardService.filter_citation_map_for_reader`, sorts by `REFERENCE > ACTIVE` and `FRESH > STALE_WARNING`, preserves `[STALE_WARNING]` markers, and formats Layer 4 prompt context for `AssistantPromptBuilder`.
  - Create `assistant_context_budget.py`: trims `conversation_history` deterministically (preserving newest turns first and never truncating Layer 1 constitutional rules) within `max_tokens_budget` (derived from `workspace_llm_tier_mappings` / `LlmEndpointConfig.max_tokens_budget`).
  - Create `_internal/sql_assistant_thread_messages.py` + `assistant_thread_messages.py` facade: `SqlAssistantThreadMessagesRepository` (`UUIDv7` PKs, idempotent `append_message`, ordered `list_messages_for_thread`).

### 2.3 Backend API, Security & Contracts (`apps/api/`, `packages/api-client/`)
- **Composition Root (`_core_providers.py`, `_lifespan_services.py`, `portal_and_assistant.py`):**
  - Disconnect `build_empty_ontology_service()` from `_core_providers.py` (`fixture=False` uses `OntologyGovernanceService()` or PG18-loaded governance) and disconnect `build_seeded_rag_service()` from `_lifespan_services.py`.
  - Replace `blackboard_snapshots_provider=lambda _ws: ()` in `_lifespan_services.py` with a real PG18 `blackboard_snapshots` provider (`list_active_workspace_blackboard_snapshots_pg`) and attach `SqlHybridRagRepository` when `session_maker` / `db_engine` is available.
  - Add `get_assistant_thread_messages_repository` provider in `portal_and_assistant.py`.
- **Federated Prompt Assembly & Latency Benchmark (`_assistant_context_assembly.py`, `assistant_llm_prompts.py`, `assistant_llm_resolver.py`):**
  - Assemble Layer 2 (PG18 ontology + `ProfileSemanticTranslator` + axioms), Layer 4 (server `EvidenceTable` from PG18 `SqlHybridRagRepository` + PG18 `blackboard_snapshots` + `READ_SOURCE` guard), and Mode A overrides using `time.perf_counter()` to measure and log SQL prompt-assembly latency (`R6` baseline).
  - Propagate `max_tokens_budget` from `AiModelMappingRecord` onto `LlmEndpointConfig` and trim `build_multi_turn_messages` cleanly within budget.
- **PG18 Thread History Persistence & Endpoint (`_assistant_workspace_context.py`, `_assistant_turns_v2_routes.py`, `_assistant_turn_producer.py`, `_assistant_turn_producer_helpers.py`):**
  - Replace `thread_summary.split(" | ")` in `resolve_turn_history` with `SqlAssistantThreadMessagesRepository.list_messages_for_thread` (after folder ACL checks).
  - Persist `user` and `assistant` messages (`turn_id`, `parent_turn_id`, `citation_map`, `token_count`) on turn completion.
  - Expose `GET /api/v1/assistant/threads/{thread_id}/messages` (`ScopeAccessGuard` + `enforce_assistant_workspace_guard` + folder ACL) with Pydantic v2 schemas in `apps/api/src/orcia_api/schemas/assistant_governance_and_three_speed.py` (re-exported in `schemas/assistant.py`), then regenerate `packages/api-client` (`0-diff` gate).

### 2.4 User Interface & Experience (`apps/web/`)
- N/A for SPA changes in Story `26.5` (UI & SDK wiring for thread history and Deepen is scoped to `Story 26.9`; `packages/api-client` generated schema stays in sync with `0-diff`).

### 2.5 Test Pyramid Impact Analysis (`AD-17` — Layers 1 to 5 + Security)
- **Layer 1a (Python Unit `tests/unit/`)**: Unit tests for `rank_ontology_snapshot_for_query` (lexical + embedding similarity, `ProfileSemanticTranslator`, axioms, empty bundle), `assistant_evidence_table` (`READ_SOURCE` & `CONFIDENTIAL_RESTRICTED` masking, authority/freshness ordering, `[STALE_WARNING]`), `assistant_context_budget` (newest-turns-preserved trimming), and `SqlAssistantThreadMessagesRepository` fallback behavior.
- **Layer 2 (Vertical Integration `HTTP FastAPI -> PG18` `tests/integration/api/`)**: Real `testcontainers` PG18 + Redis test using `create_app()` with zero `dependency_overrides` verifying:
  - Alembic `20261122_265` `upgrade -> downgrade -> upgrade` and Day-0 reset compatibility;
  - PG18 ontology ranking + axioms + `ProfileSemanticTranslator` in assembled system prompt;
  - Async `SqlHybridRagRepository.search_hybrid_rrf` with active embedding model AND clean skip/lexical path when `0` embedding models exist (`25.5` invariant);
  - Active `blackboard_snapshots` injection with strict `workspace_id` isolation;
  - `assistant_thread_messages` persistence (`SELECT` verification), `GET /api/v1/assistant/threads/{thread_id}/messages` (including folder ACL `403` enforcement), token budget trimming, and `perf_counter()` SQL prompt-assembly latency measurement (`R6`).
- **Layer 3 (API Contracts & Architectural Audits)**: `export_openapi.py --check` (`0-diff`), `lint-imports` (`5/5`), `test_zero_orphan_sql_adapters_audit.py`, `test_assistant_and_rag_routes_require_rag_guard_audit.py`, `test_integration_no_manual_app_state_audit.py`, `test_codebase_architectural_anti_patterns_audit.py`.
- **Layer 4 (`0 $` Golden Evals `tests/evals/`)**: Golden ontology eval in `tests/evals/` verifying relevant L1–L4 concept & axiom selection and `ProfileSemanticTranslator` hat adaptation.
- **Security Layer (`tests/security/`)**: `READ_SOURCE` & `CONFIDENTIAL_RESTRICTED` filtering in `EvidenceTable` + thread folder ACL enforcement on `GET /threads/{thread_id}/messages`.
- **Layer 5 (Playwright E2E)**: No UI routes modified; existing Playwright E2E compatibility preserved.

---

## 3. Summary of Modifications & Results (Bilan des Modifications)

### 3.1 Files Created & Modified

| Component / Layer | File(s) | Status | Lines | Key Changes |
| :--- | :--- | :--- | :--- | :--- |
| **Alembic & Day-0 Reset (`infra/`)** | `infra/migrations/versions/20261122_265_story_26_5_assistant_thread_messages.py` | Created | 61 | Raw-SQL `assistant_thread_messages` table (`UUIDv7` PK, `role` check, `uq_assistant_thread_messages_turn_role`, `idx_assistant_thread_messages_thread_created`, reversible `downgrade()`) |
| | `infra/scripts/maintenance/_first_boot_reset_guards.py` | Modified | 173 | Registered `"assistant_thread_messages"` ahead of `"assistant_threads"` in `ORDERED_MUTABLE_TABLES_TO_CLEAR` |
| **Ontology PG18 & Ranker (`orcia_core.ontology`)** | `packages/orcia-core/src/orcia_core/ontology/context_ranker.py` | Created | 291 | Query-driven concept relevance ranker (lexical + optional embedding cosine), `ProfileSemanticTranslator`, axiom extraction, `build_websearch_or_query` |
| | `packages/orcia-core/src/orcia_core/ontology/_internal/sql_ontology_context.py` | Created | 91 | Flat PG18 loaders (`list_relations_pg`, `list_axioms_pg`, `load_ontology_governance_service_pg`) |
| | `packages/orcia-core/src/orcia_core/ontology/translator.py` | Created | 163 | Extracted `ProfileSemanticTranslator` & hat translation helpers under `<= 300` lines |
| | `packages/orcia-core/src/orcia_core/ontology/__init__.py`, `resolver.py`, `_internal/sql_ontology_mappers.py`, `_internal/sql_ontology_queries.py` | Modified | 287 / 244 / 237 / 166 | Re-exports, concurrent `load_org_and_workspaces_context` with safe row/table checks, relation/axiom SQL mappers |
| **Blackboard & Hybrid RAG (`orcia_core`)** | `packages/orcia-core/src/orcia_core/blackboard/_internal/sql_blackboard_queries.py` | Created | 160 | `list_active_workspace_blackboard_snapshots_pg` (`JOIN workflow_runs`, `workspace_id` isolation, excludes `SUPERSEDED`) |
| | `packages/orcia-core/src/orcia_core/blackboard/__init__.py` | Modified | 34 | Public export of `list_active_workspace_blackboard_snapshots_pg` |
| | `packages/orcia-core/src/orcia_core/rag/_internal/sql_hybrid_search_helpers.py` | Created | 229 | Optional-embedding RRF & lexical-only (`ts_rank_cd`) PG18 search SQL helpers (`Story 25.5` invariant) |
| | `packages/orcia-core/src/orcia_core/rag/_internal/sql_repository.py`, `context_adapters.py`, `_context_adapters_helpers.py`, `models.py` | Modified | 232 / 290 / 175 / 206 | Async `SqlHybridRagRepository.search_hybrid_rrf(query_embedding=None)`, async Blackboard/RAG context adapters, `build_blackboard_slices` |
| **EvidenceTable, History & Budget (`orcia_core.orchestration`, `ports`, `permissions`)** | `packages/orcia-core/src/orcia_core/orchestration/assistant_evidence_table.py` | Created | 277 | Server `EvidenceTable` consolidation (`READ_SOURCE` / `CONFIDENTIAL_RESTRICTED` filtering, `REFERENCE > ACTIVE`, `[STALE_WARNING]`) |
| | `packages/orcia-core/src/orcia_core/orchestration/assistant_context_budget.py` | Created | 101 | Deterministic history trimmer respecting `max_tokens_budget` while preserving Layer 1 & newest turns |
| | `packages/orcia-core/src/orcia_core/orchestration/_internal/sql_assistant_thread_messages.py` & `assistant_thread_messages.py` | Created | 218 / 15 | Idempotent `SqlAssistantThreadMessagesRepository` (`UUIDv7` PKs, `(turn_id, role)` conflict guard, ordered listing) |
| | `assistant_prompt_builder.py`, `assistant_prompt_preview.py`, `assistant_agent.py`, `_assistant_agent_nodes.py`, `assistant_governance.py`, `_internal/sql_assistant_governance.py`, `_internal/_sql_assistant_governance_queries.py`, `llm_endpoint_resolver.py`, `ports/*`, `permissions/_internal/sql_permission_broker.py` | Modified | 1–292 (all `<= 292`) | Wired budget trimming, `max_tokens_budget` propagation, async context/governance queries, and broker read-check helpers |
| **API Composition Root, Context & History Routes (`apps/api/`)** | `apps/api/src/orcia_api/routers/_assistant_context_assembly.py` | Created | 300 | Concurrent PG18 ontology/RAG/Blackboard/Mode A assembly + `EvidenceTable` + `time.perf_counter()` `R6` benchmark |
| | `apps/api/src/orcia_api/routers/_assistant_thread_messages_routes.py` | Created | 170 | `GET /api/v1/assistant/threads/{thread_id}/messages` (`ScopeAccessGuard` + workspace/folder ACL enforcement) |
| | `apps/api/src/orcia_api/routers/_assistant_llm_tools_and_budget.py`, `_assistant_turn_liveness_watchdog.py`, `_finops_topology_sync.py` | Created | 83 / 46 / 183 | Extracted budget trimming, turn liveness watchdog, and PG18 FinOps topology sync so all files remain `<= 300` lines |
| | `dependencies/*.py`, `routers/assistant*.py`, `routers/_assistant_*.py`, `routers/_finops_scope_guards.py`, `routers/_ontology_promotions_helpers.py`, `schemas/assistant*.py` | Modified | 126–296 (all `<= 296`) | Disconnected `build_empty_ontology_service()` & `build_seeded_rag_service()`, wired PG18 `blackboard_snapshots` + `SqlHybridRagRepository` + `SqlAssistantThreadMessagesRepository`, persisted user/assistant messages on turn completion |
| **OpenAPI, Tests & Governance** | `packages/api-client/openapi.json` & `packages/api-client/src/generated/schema.ts` | Regenerated | 72,929 / 7,563 | Zero-diff OpenAPI 3.1 schema & TypeScript types including `GET /api/v1/assistant/threads/{thread_id}/messages` |
| | `tests/unit/test_story_26_5_*.py`, `tests/evals/test_story_26_5_*.py`, `tests/integration/api/test_story_26_5_*.py`, `_pg18_story_26_5_helpers.py` | Created | 142–491 | Unit, eval, Alembic reversibility, and real `create_app()` PG18/Redis vertical integration + `R6` benchmark tests |
| | `tests/integration/api/test_story_26_4b_pg18_migration.py`, `tests/unit/test_epic_25_guards_and_helpers_coverage.py` | Modified | — | Head revision check compatibility & updated `_finops_topology_sync.get_configured_db_engine` monkeypatch target |
| | `docs/product/capabilities.yaml`, `apps/web/src/generated/orciaSiteManifest.ts`, `docs/site-catalog/index.html` | Modified | — | Updated `CAP-022` surfaces/tables/tests and synchronized site catalog |

### 3.2 Quantitative Results & 5-Layer (`AD-17`) Verification

- **Line-Count Audit:** Every modified and untracked non-generated source file under `packages/`, `apps/api/`, `apps/worker/`, and `infra/` is **`<= 300` lines** (`_assistant_context_assembly.py` = `300` L, `sql_ontology_mappers.py` = `237` L).
- **Story `26.5` Branch Coverage (`11` target modules via `COVERAGE_FILE=/tmp/.cov_26_5 coverage run --branch --no-cov` across chunked `tests/unit`, `tests/evals`, `tests/security`, `tests/contract`):** **`91%`** (`526` statements, `43` missed, `146` branches, `12` partial — **`--fail-under=90` PASSED**). Per-file breakdown: `assistant_evidence_table.py` `100%`, `assistant_thread_messages.py` `100%`, `_context_adapters_helpers.py` `100%`, `sql_hybrid_search_helpers.py` `100%`, `context_ranker.py` `98%`, `sql_assistant_thread_messages.py` `98%`, `assistant_context_budget.py` `98%`, `sql_blackboard_queries.py` `95%`, `assistant_prompt_builder.py` `93%`, `sql_ontology_context.py` `64%`, `sql_assistant_governance.py` `56%` (the latter two SQL modules are additionally exercised by PG18 Layer 2 integration tests).
  - *Note on overall `orcia_kernel + orcia_core` unit/eval/security/contract coverage (excluding `tests/integration` & `tests/conformance`):* `83%` across `26,752` statements (`6,168` branches) due to PG18/container-only adapters (`workflows/gates/runners.py` `12%`, `_internal/sql_*` modules) covered in `tests/integration`.
- **Unit, Security, Evals & Contract Suites (`--no-cov`, chunked post-final-edit):**
  - `tests/unit` chunked (`a-d`, `e-m`, `n-r`, `site..story20`, `story22-26`, `story3-5`, `story6-7+t-z`, `7_0a+7_0c`): **100% passed** across all `138` unit test files (including `test_zero_orphan_sql_adapters_audit.py` and `test_codebase_architectural_anti_patterns_audit.py`; `test_epic_11_story_11_2` and `test_story_7_0c` verified standalone under `--no-cov` without CPU/OTel cross-file interference).
  - `tests/evals` + `tests/security`: **`148` items passed** (including `tests/evals/test_story_26_5_ontology_relevance_evals.py`).
  - `tests/contract`: **`2 passed`** (Schemathesis OpenAPI contract suite).
  - Dedicated Story `26.5` unit + evals (`test_story_26_5_*.py`): **`18 passed in 9.43s`**.
- **PostgreSQL 18 + Redis 7.4 Integration Suite (`testcontainers`, `create_app()` with `0` overrides, `--no-cov`):**
  - Post-final-edit `test_story_26_4b_pg18_migration.py` + `test_story_26_5_migration_pg18.py` + `test_story_26_5_real_context_and_history_postgres18.py`: **`3 passed in 48.76s`**.
  - **Measured `R6` PG18 Prompt-Assembly Latency (`assistant_prompt_assembly_benchmarked`):**
    - Cold first turn (`embedding_active=false`): **`160.321 ms`** (`mode_a_ms=31.903`, `ontology_ms=72.036`, `rag_ms=14.969`, `blackboard_ms=53.779`).
    - Turn 2 (`embedding_active=true`): **`69.587 ms`** (`mode_a_ms=21.146`, `ontology_ms=34.666`, `rag_ms=31.706`, `blackboard_ms=17.936`).
    - Warm 5-turn PG18 benchmark: **`p50 = 62.759 ms`**, **`p95 = 68.447 ms`** (`<= 100.0 ms` gate PASSED; samples: `[44.413, 56.630, 62.759, 63.356, 68.447]`).
    - **`ACTION_ITEM-26.3` Decision:** Remains **deferred** under measure-first policy (`R6`); final Redis assembled-prompt caching decision awaits Story `26.7` end-to-end Speed 1 `TTFT < 1.2 s` benchmark.
  - Story `25.5`, `26.1`, `26.3`, `26.4a`, `26.4b` PG18/Redis non-regression suite: **`7 passed in 109.95s`**.
- **Static, Type, Architecture, OpenAPI & Secret Gates:**
  - `.venv/bin/alembic -c infra/migrations/alembic.ini heads` -> single linear head `20261122_265 (head)` (PG18 `upgrade -> downgrade -> upgrade` verified).
  - `.venv/bin/ruff check .` -> `All checks passed!`; `.venv/bin/ruff format --check .` -> `1486 files already formatted`.
  - `.venv/bin/mypy --strict packages/orcia-core apps/api apps/worker` -> `Success: no issues found in 641 source files` (covers `orcia_kernel` and `orcia_core`).
  - `.venv/bin/lint-imports` -> `Contracts: 5 kept, 0 broken` (`725` files, `5264` dependencies).
  - `.venv/bin/python .agent/skills/bmad-architecture/scripts/lint_spine.py --workspace docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24` -> `{"ok": true, "total_findings": 0}`.
  - `.venv/bin/python scripts/export_openapi.py --check` -> exit `0` (`0-diff`).
  - `.venv/bin/detect-secrets-hook --baseline .secrets.baseline ...` -> exit `0` (`0` findings).
- **TypeScript / SPA & Playwright Desktop E2E (`AD-17` L5):**
  - `pnpm turbo run lint typecheck test` -> **`9/9` tasks successful** (`@orcia/api-client`: `20/20`, `@orcia/ui`: `34` files, `@orcia/web`: `67/67` files / `261/261` tests).
  - Playwright Desktop (`--project=desktop-cockpit`, `00-stack-smoke`, `02-assistant-streaming-and-folders`, `12-finops-and-audit-provenance`, `12-epic16-reflexive-trace-and-line-inspector`, `16-ai-models-reindex-connectors-and-broker`, `21-assistant-citations-v5-audit-help-showcase`, `env -u ORCIA_E2E_SEED_FIXTURES`) -> **`15 passed / 1 skipped / 0 failed (2.7m)`** (`git diff docs/implementation-artifacts/e2e-campaign-epic-*` empty).
- **Docs, Site Catalog & GitNexus Sync:** Verified via `scripts/check_implementation_docs.py`, `pnpm site:sync && pnpm site:check`, and `npx gitnexus analyze --index-only .` with zero stray `.coverage*` or `uv.lock` artifacts.

### 3.3 Final Closure Decision (`done`)

- Story `26.5` passed 100% of independent post-final-edit verification gates (`91%` 11-module Story `26.5` branch coverage, all `138` unit files + `148` eval/security + `2` contract tests passed, `3/3` Story `26.4b`/`26.5` PG18 tests + `7/7` non-regression PG18/Redis tests passed, `R6` warm PG18 `p50 = 62.759 ms` / `p95 = 68.447 ms <= 100 ms` with `ACTION_ITEM-26.3` deferred to Story `26.7`, `9/9` Turbo, `15 passed / 1 skipped / 0 failed` Playwright Desktop E2E, all non-generated touched source files `<= 300` L, `0-diff` OpenAPI, `5/5` `lint-imports`). Story `26.5` is closed as **`done`**.
