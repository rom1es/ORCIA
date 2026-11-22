# Story 26.4b — PG18 Persistence for Mode A 3-Level Governance, Turn Feedback, Folder Metadata & `audit_ledger` Phantom Citation Logging (Mode B Deleted & Drafts Omitted)

- **Date:** 2026-11-22
- **Story / Sprint Key:** `26-4b-pg18-persistence-mode-a-governance-feedback-and-folders` (`Epic 26`, Lot 3)
- **Capabilities:** `CAP-070`, `CAP-072`, `CAP-073` — classification: `feature`
- **Author / Context:** Tech Lead / Senior Dev implementation of Story `26.4b` resolving findings `H-09` (RAM business state in assistant governance, phantom citation audit log, turn feedback, and folder attachments/tags) and `H-37` (`BUG-E2E-01b` folder metadata). Aligns with `AD-15`, `AD-17`, `AD-19`, `AD-25`, and `epic-26-decisions-grill-2026-11-21.md` (`R2`, `R4`, `R5`, `R9`).
- **Associated Commits:** Pending atomic commit on branch `feat/epic-26-assistant-harness-debt-remediation`

---

## 1. Requirements & Tech Lead Impact Analysis (Analyse du Besoin)

### 1.1 Context & Problem Statement
- **Mode A Governance RAM State & Unused Mode B Studio (`H-09`, `R2`, `R4`):** `AssistantFourLevelGovernanceService` stores `_user_prefs`, `_workspace_settings`, `_team_instructions`, `_team_mcp_frozen`, `_studio_graphs`, and `_overrides` in process-local Python dictionaries instead of persisting `TEAM` / `WORKSPACE` / `USER` Mode A overrides into the existing PostgreSQL 18 table `workspace_customization_overrides` (migration `0003`). Meanwhile, `POST /api/v1/assistant/governance/mode-b/save` and `mode-b/reset` have zero UI callers and must be deleted directly under `R2`/`R4` (`ACTION_ITEM-26.1`), returning Mode A configuration only on `GET /api/v1/assistant/governance`.
- **In-Memory Turn Feedback (`H-09`, `R5`):** `POST /api/v1/assistant/three-speed/feedback` calls `record_prompt_telemetry_entry(...)`, persisting feedback solely in `PROMPT_TELEMETRY_LOG` RAM state, while canonical REST v2 `POST /api/v1/assistant/turns/{turn_id}/feedback` (`architecture.md` §3.6.3 / §4 / §8) is not yet backed by PostgreSQL 18 `assistant_turn_feedback`.
- **Partial Folder Metadata Persistence (`H-09`, `H-37` / `BUG-E2E-01b`):** `assistant_folders` (migration `0025`) lacks `working_attachments_uris` and `evidence_tags` columns, forcing `AssistantFoldersAndSharingService` to maintain `_folder_meta` in process-local RAM.
- **In-Memory Phantom Citation Audit Log (`H-09`, `R5`):** `AssistantCitationAndV5GuardService` appends phantom citation purge events to `_phantom_audit_log` in RAM rather than persisting idempotent `ASSISTANT_PHANTOM_CITATION_PURGED` events to append-only `audit_ledger` via `SqlAuditLedgerService`. Under `R5`, no `assistant_citation_drafts` table is created, and `_saved_drafts` / `execute_artifact_card_action` / `POST /api/v1/assistant/artifacts/action` remain temporarily intact until Story `26.7` so E2E spec `21` stays green.

### 1.2 Exploration, GitNexus Impact Analysis, Factorization & Technical Debt
- **GitNexus Impact Analysis & Exhaustive Caller Audit (`repo: "/home/romain/Documents/Projects/ORCIA"`):**
  - Queried GitNexus across `AssistantFourLevelGovernanceService`, `AssistantCitationAndV5GuardService`, `assistant_folders_and_sharing`, `SqlAuditLedgerService`, `workspace_customization_overrides`, `three-speed/feedback`, and `turns/{turn_id}/feedback`, noting GitNexus index is 1 commit behind `HEAD` and some assistant symbols are absent from the graph.
  - Supplemented with exhaustive `grep` across `packages/`, `apps/`, `infra/`, and `tests/`:
    - Governance callers: `apps/api/src/orcia_api/routers/assistant_workspace_governance.py`, `packages/orcia-core/src/orcia_core/orchestration/assistant_three_speed_router.py`, `apps/api/src/orcia_api/routers/assistant_llm_prompts.py`, `apps/api/src/orcia_api/dependencies/portal_and_assistant.py`.
    - Mode B references: `assistant_workspace_governance.py` (`/governance/mode-b/{save,reset}`), `schemas/assistant_governance_and_three_speed.py`, `schemas/assistant.py`, `assistant_governance*.py`, `apps/web/src/features/inbox/InboxAuxiliaryPanels.tsx` (`canOpenStudioModeB={true}`), `tests/unit/test_epic_10_story_10_1_assistant_governance.py`, `tests/security/test_story_26_1_assistant_security_hardening.py`, and `tests/security/test_story_26_1_review_hardening.py`.
    - Folder metadata callers: `assistant_folders_and_sharing.py`, `_assistant_folders_async_ops.py`, `_assistant_folders_sync.py`, `sql_assistant_folders.py` (currently `322 L` — requires splitting to `<= 300 L`), `_sql_assistant_folders_queries.py`.
    - Phantom citation callers: `assistant_workspace_citations.py`, `assistant_citations_and_v5_guard.py`, `tests/unit/test_epic_10_story_10_3_citations_and_v5_guard.py`.
- **Line-Count Audit (`<= 300 L` Mandatory Cap):**
  - `sql_assistant_folders.py` is currently `322 L` (`> 300 L`). We will extract thread/share SQL repository helpers into `_sql_assistant_folders_mutations.py` (`<= 300 L`) so every touched/created source file stays strictly `<= 300` lines.
- **Factorization & Debt Resolution:**
  - Create `SqlAssistantGovernanceRepository` (`_internal/sql_assistant_governance.py`) reusing `resolve_workspace_uuid` / `resolve_user_uuid` primitives from `_sql_assistant_folders_queries.py` rather than duplicating UUID resolution SQL.
  - Create `SqlAssistantFeedbackRepository` (`_internal/sql_assistant_feedback.py`) shared by both `POST /api/v1/assistant/three-speed/feedback` and `POST /api/v1/assistant/turns/{turn_id}/feedback`.
  - Place `InMemoryAssistantGovernanceStore` and `InMemoryAuditLedgerSink` strictly under `tests/unit/fakes/` (`AD-19`).

---

## 2. Implementation Plan (Plan d'Implémentation)

### 2.1 Data Schema & Alembic Migrations (`infra/migrations/versions/`)
- **`infra/migrations/versions/20261122_264b_story_26_4b_assistant_feedback_and_folder_meta.py` (`down_revision = "20261122_264a"`):**
  - Create `assistant_turn_feedback`: `id UUID PRIMARY KEY` (`UUIDv7`), `turn_id UUID NOT NULL`, `workspace_id UUID NOT NULL REFERENCES workspaces(id) ON DELETE CASCADE`, `user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE`, `rating VARCHAR(8) NOT NULL CHECK (rating IN ('up', 'down'))`, `reason_code VARCHAR(64) NULL`, `comment TEXT NULL`, `created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`, `updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()`, `CONSTRAINT uq_assistant_turn_feedback_turn_user UNIQUE (turn_id, user_id)`.
  - Indexes: `idx_assistant_turn_feedback_workspace_turn` on `(workspace_id, turn_id)` and `idx_assistant_turn_feedback_turn_id` on `(turn_id)`.
  - Alter `assistant_folders`: `ADD COLUMN IF NOT EXISTS working_attachments_uris JSONB NOT NULL DEFAULT '[]'::jsonb`, `ADD COLUMN IF NOT EXISTS evidence_tags TEXT[] NOT NULL DEFAULT '{}'::text[]`.
  - Pure raw SQL (`op.execute(sa.text(...))`), zero ORM imports, fully reversible `downgrade()`, zero Mode B studio table (`R2`), zero citation drafts table (`R5`), and append-only triggers on `audit_ledger`/`blackboard_snapshots` preserved.
  - Update `infra/scripts/maintenance/_first_boot_reset_guards.py` (`ORDERED_MUTABLE_TABLES_TO_CLEAR`) to include `"assistant_turn_feedback"` so Day-0 reset clears cleanly before `workspaces` and `users`.

### 2.2 Hexagonal Core, Orchestration & Workers (`packages/orcia-core/`)
- **Mode A Governance PG18 Repository & Zero RAM State (`H-09`, `R2`):**
  - Create `_internal/sql_assistant_governance.py` (`SqlAssistantGovernanceRepository`, `<= 300 L`) reading/writing `TEAM`, `WORKSPACE`, and `USER` layers into `workspace_customization_overrides` (`ON CONFLICT (override_key) DO UPDATE`).
  - Refactor `assistant_governance.py`, `assistant_governance_models.py`, and `assistant_governance_studio.py` to remove `_user_prefs`, `_workspace_settings`, `_team_instructions`, `_team_mcp_frozen`, `_studio_graphs`, `_overrides`, and Mode B studio validators/methods; add async PG18-backed methods (`get_user_preferences_async`, `update_user_preferences_async`, `get_workspace_settings_async`, `update_workspace_settings_async`, `freeze_mcp_at_upper_layer_async`, `assemble_five_layers_preview_async`, `get_governance_view_async`) while accepting an optional `AssistantGovernanceStorePort` fake for fast unit tests.
- **Turn Feedback PG18 Repository (`H-09`, `R5`):**
  - Create `_internal/sql_assistant_feedback.py` (`SqlAssistantFeedbackRepository`, `<= 300 L`) performing idempotent `ON CONFLICT (turn_id, user_id) DO UPDATE` into `assistant_turn_feedback`.
- **Folder Metadata PG18 Persistence (`H-09`, `H-37`):**
  - Remove `_folder_meta` from `assistant_folders_and_sharing.py`, `_assistant_folders_async_ops.py`, and `_assistant_folders_sync.py`.
  - Update `_sql_assistant_folders_queries.py` and `sql_assistant_folders.py` (splitting thread/share mutations into `_sql_assistant_folders_mutations.py` to stay `<= 300 L`) to persist and hydrate `working_attachments_uris` and `evidence_tags` in `assistant_folders`.
- **Phantom Citation Audit to `audit_ledger` (`H-09`, `R5`):**
  - Remove `_phantom_audit_log` and `phantom_audit_log` from `AssistantCitationAndV5GuardService`; inject `AuditLedgerSinkPort` (`SqlAuditLedgerService` at Composition Root) and add `verify_and_sanitize_citations_async` recording idempotent `ASSISTANT_PHANTOM_CITATION_PURGED` entries (`uuid5` `source_event_id`). Keep `_saved_drafts` and `execute_artifact_card_action` temporarily intact until `26.7`.

### 2.3 Backend API, Composition Root & OpenAPI Contracts (`apps/api/`, `packages/api-client/`)
- **Composition Root (`portal_and_assistant.py`):** Wire `db_engine` into `AssistantFourLevelGovernanceService` (`set_engine`), `SqlAuditLedgerService` into `AssistantCitationAndV5GuardService` (`set_audit_ledger_sink`), and expose `get_assistant_feedback_repository(request)` backed by `SqlAssistantFeedbackRepository`.
- **Mode B Route Deletion & Mode A Wiring (`assistant_workspace_governance.py`, `schemas/assistant_governance_and_three_speed.py`, `schemas/assistant.py`):**
  - Delete `POST /api/v1/assistant/governance/mode-b/save`, `POST /api/v1/assistant/governance/mode-b/reset`, their request/response schemas, and `can_open_studio_mode_b` / `studio_graph` from `AssistantGovernanceViewResponse`.
  - Switch `GET /governance`, `PUT /governance/mode-a/user`, `PUT /governance/mode-a/workspace`, and live prompt assembly (`assistant_three_speed_router.py` / `assistant_llm_prompts.py` / `assistant_llm_bridge.py`) to async PG18-backed governance methods.
- **Feedback & Citation Endpoints (`_assistant_workspace_controls.py`, `_assistant_turns_v2_routes.py`, `assistant_workspace_citations.py`):**
  - Wire `POST /api/v1/assistant/three-speed/feedback` and add `POST /api/v1/assistant/turns/{turn_id}/feedback` (`ScopeAccessGuard` + `403 ERR_OBSERVER_MODE_READ_ONLY`) to `SqlAssistantFeedbackRepository`.
  - Wire `POST /api/v1/assistant/citations/verify-turn` to `await citation_svc.verify_and_sanitize_citations_async(...)` so phantom citations persist to `audit_ledger`.
- **OpenAPI SDK:** Regenerate `packages/api-client` (`0-diff` gate via `scripts/export_openapi.py`).

### 2.4 SPA Interface (`apps/web/`)
- Disable Mode B entry button in `apps/web/src/features/inbox/InboxAuxiliaryPanels.tsx` (`canOpenStudioModeB={false}`) so zero dead Mode B triggers appear in `apps/web` (keeping `@orcia/ui` primitives intact until `ACTION_ITEM-26.1` / `26.9`), and verify `pnpm turbo run lint typecheck test` + E2E specs `00`, `02`, `12-finops`, `12-epic16`, `16`, `21`.

### 2.5 Test Pyramid Impact Analysis (`AD-17` — Layers 1–5 + Security)
- **Layer 1a (Python Unit `tests/unit/test_story_26_4b_*.py`) & Layer 1b (TS `Vitest`):**
  - AST/source checks: zero RAM business dicts in `AssistantFourLevelGovernanceService`, zero `_folder_meta`, zero `_phantom_audit_log`, zero Mode B routes/schemas/`_studio_graphs`, zero `InMemory*` classes outside `tests/unit/fakes/`, all touched/created source files `<= 300 L`.
  - Unit tests for Mode A 3-level merge + Funnel Rule + `InMemoryAssistantGovernanceStore` fake, `InMemoryAuditLedgerSink` phantom citation idempotency, and `execute_artifact_card_action` preservation.
  - Amend `test_epic_10_story_10_1_assistant_governance.py`, `test_epic_10_story_10_3_citations_and_v5_guard.py`, `test_story_26_1_assistant_security_hardening.py`, and `test_story_26_1_review_hardening.py` for Mode B removal and `audit_ledger` phantom audit.
- **Layer 2 (Vertical Integration `HTTP -> PostgreSQL 18` `tests/integration/api/test_story_26_4b_pg18_persistence_governance_feedback_folders.py`):**
  - Real `create_app()` with zero `dependency_overrides` on `PostgresContainer("pgvector/pgvector:pg18")`:
    - Alembic `upgrade -> downgrade -> upgrade` on `20261122_264b` (single `alembic heads`, no Mode B / citation drafts tables).
    - Mode A `USER` / `WORKSPACE` / `TEAM` persistence in `workspace_customization_overrides`, verified by `SELECT` and cold cache eviction (`POST /_e2e/evict-memory-caches` / fresh `create_app()`).
    - Turn feedback upsert via both `/three-speed/feedback` and `/turns/{turn_id}/feedback` in `assistant_turn_feedback`.
    - Folder `working_attachments_uris` & `evidence_tags` persistence & cold reload in `assistant_folders`.
    - Idempotent `ASSISTANT_PHANTOM_CITATION_PURGED` persistence in `audit_ledger` via `/citations/verify-turn`.
    - Mode B endpoints returning `404`/`405` and `/artifacts/action` remaining functional for E2E `21`.
- **Layer 3 (Contracts & Architecture):** `ruff`, `mypy --strict`, `lint-imports`, `export_openapi.py --check`, `test_zero_orphan_sql_adapters_audit.py`, `test_codebase_architectural_anti_patterns_audit.py`.
- **Layer 4 & Security:** `tests/evals` + `tests/security` + `detect-secrets-hook`.
- **Layer 5 (Playwright E2E):** Desktop E2E specs `00`, `02`, `12-finops`, `12-epic16`, `16`, `21` under isolated `ORCIA_E2E_CAMPAIGN_DIR`.

---

## 3. Modifications Summary & Verification Results (Bilan des Modifications)

### 3.1 Inventory of Created, Modified & Deleted Files (All Non-Generated Source Files `<= 299` Lines)

| File | Action | Lines | Role & Key Symbols |
| :--- | :--- | :---: | :--- |
| `infra/migrations/versions/20261122_264b_story_26_4b_assistant_feedback_and_folder_meta.py` | Created | 87 | Raw-SQL Alembic migration `20261122_264b` (`down_revision = "20261122_264a"`): creates `assistant_turn_feedback` (`UUIDv7` PK, `UNIQUE (turn_id, user_id)`) and adds `working_attachments_uris JSONB` + `evidence_tags TEXT[]` to `assistant_folders` |
| `infra/scripts/maintenance/_first_boot_reset_guards.py` | Modified | 172 | Added `"assistant_turn_feedback"` to `ORDERED_MUTABLE_TABLES_TO_CLEAR` |
| `packages/orcia-core/src/orcia_core/orchestration/_internal/_sql_assistant_governance_queries.py` | Created | 155 | Raw SQL queries & serialization helpers for Mode A 3-level `workspace_customization_overrides` |
| `packages/orcia-core/src/orcia_core/orchestration/_internal/sql_assistant_governance.py` | Created | 299 | `SqlAssistantGovernanceRepository` (`USER`, `WORKSPACE`, `TEAM` PG18 persistence) |
| `packages/orcia-core/src/orcia_core/orchestration/_internal/sql_assistant_feedback.py` | Created | 128 | `SqlAssistantFeedbackRepository` (`assistant_turn_feedback` idempotent upsert) |
| `packages/orcia-core/src/orcia_core/orchestration/assistant_feedback.py` | Created | 15 | Public orchestration facade exporting `SqlAssistantFeedbackRepository` |
| `packages/orcia-core/src/orcia_core/orchestration/_assistant_governance_sync.py` | Created | 169 | Synchronous facade mixin for `AssistantFourLevelGovernanceService` |
| `packages/orcia-core/src/orcia_core/orchestration/assistant_governance.py` | Modified | 249 | `AssistantFourLevelGovernanceService` with Mode A PG18 repository delegation & zero RAM business dicts |
| `packages/orcia-core/src/orcia_core/orchestration/assistant_governance_models.py` | Modified | 154 | Mode A dataclasses & `AssistantGovernanceStorePort` (Mode B studio models removed) |
| `packages/orcia-core/src/orcia_core/orchestration/assistant_governance_studio.py` | Modified | 225 | Mode A view/5-layer preview assembly; removed `_studio_graphs` & Mode B save/reset methods |
| `packages/orcia-core/src/orcia_core/orchestration/assistant_three_speed_router.py` | Modified | 280 | Added `get_or_assemble_cached_prompt_async` resolving Mode A PG18 layers asynchronously |
| `packages/orcia-core/src/orcia_core/orchestration/_internal/_sql_assistant_folders_sql.py` | Created | 88 | Folder/thread SQL DDL statement constants (`working_attachments_uris`, `evidence_tags`) |
| `packages/orcia-core/src/orcia_core/orchestration/_internal/_sql_assistant_folders_mutations.py` | Created | 221 | Thread & sharing SQL mutations extracted for modular size hygiene |
| `packages/orcia-core/src/orcia_core/orchestration/_internal/_sql_assistant_folders_queries.py` | Modified | 234 | Updated folder projections and row mappers with `working_attachments_uris` & `evidence_tags` |
| `packages/orcia-core/src/orcia_core/orchestration/_internal/sql_assistant_folders.py` | Modified | 176 | `SqlAssistantFoldersRepository` delegating split query/mutation modules |
| `packages/orcia-core/src/orcia_core/orchestration/assistant_folders_and_sharing.py` | Modified | 269 | Removed `_folder_meta` RAM cache; delegates metadata directly to PG18 |
| `packages/orcia-core/src/orcia_core/orchestration/_assistant_folders_async_ops.py` | Modified | 218 | Async folder memory/launch/sharing ops backed by PG18 `assistant_folders` metadata |
| `packages/orcia-core/src/orcia_core/orchestration/_assistant_folders_sync.py` | Modified | 274 | Sync helper operations preserving domain validation invariants |
| `packages/orcia-core/src/orcia_core/orchestration/_assistant_citations_verifier.py` | Created | 146 | Phantom citation verification helper and `AuditLedgerSinkPort` event payload builder |
| `packages/orcia-core/src/orcia_core/orchestration/assistant_citations_and_v5_guard.py` | Modified | 263 | Replaced `_phantom_audit_log` RAM list with idempotent `audit_ledger` recording (`ASSISTANT_PHANTOM_CITATION_PURGED`); kept `_saved_drafts` / `execute_artifact_card_action` temporarily until `26.7` |
| `apps/api/src/orcia_api/dependencies/portal_and_assistant.py` | Modified | 236 | Composition Root wiring PG18 engine to governance & feedback repos and `SqlAuditLedgerService` to citations guard |
| `apps/api/src/orcia_api/dependencies/__init__.py` | Modified | 150 | Exported `get_assistant_feedback_repository` & `AssistantFeedbackRepoDep` |
| `apps/api/src/orcia_api/schemas/assistant_governance_and_three_speed.py` | Modified | 263 | Deleted Mode B request/response fields and models |
| `apps/api/src/orcia_api/schemas/assistant.py` | Modified | 188 | Added `AssistantTurnFeedbackRequest` / `AssistantTurnFeedbackResponse` |
| `apps/api/src/orcia_api/routers/assistant_workspace_governance.py` | Modified | 189 | Removed `POST /governance/mode-b/save` & `mode-b/reset`; wired async PG18 Mode A handlers |
| `apps/api/src/orcia_api/routers/_assistant_workspace_controls.py` | Modified | 125 | Wired `POST /three-speed/feedback` to PG18 `SqlAssistantFeedbackRepository` upsert |
| `apps/api/src/orcia_api/routers/_assistant_turns_v2_routes.py` | Modified | 270 | Added `POST /api/v1/assistant/turns/{turn_id}/feedback` (`ScopeAccessGuard` + `403 ERR_OBSERVER_MODE_READ_ONLY`) |
| `apps/api/src/orcia_api/routers/assistant_workspace_citations.py` | Modified | 176 | Wired `/citations/verify-turn` to `verify_and_sanitize_citations_async` |
| `apps/api/src/orcia_api/routers/assistant_llm_prompts.py` | Modified | 262 | Added `resolve_assembled_system_instructions_for_turn_async` |
| `apps/api/src/orcia_api/routers/assistant_llm_bridge.py` | Modified | 297 | Wired async 5-layer Mode A resolution on JSON turns |
| `apps/api/src/orcia_api/routers/_assistant_llm_stream_bridge.py` | Modified | 112 | Wired async 5-layer Mode A resolution on SSE streaming turns |
| `apps/api/src/orcia_api/routers/assistant_workspace.py` | Modified | 260 | Re-exported updated workspace prompt/feedback wiring |
| `apps/api/src/orcia_api/routers/e2e_test_hooks.py` | Modified | 118 | Adjusted test hook wiring for PG18 governance repository injection |
| `packages/api-client/openapi.json` & `packages/api-client/src/generated/schema.ts` | Regenerated | — | Zero-diff OpenAPI 3.1 client without Mode B paths/schemas and with v2 turn feedback route |
| `apps/web/src/features/inbox/InboxAuxiliaryPanels.tsx` | Modified | 227 | Set `canOpenStudioModeB={false}` pending UI cleanups (`ACTION_ITEM-26.1`, `26.9`) |
| `tests/unit/fakes/in_memory_audit_ledger.py` & `tests/unit/fakes/in_memory_assistant_governance.py` | Created | 38 / 97 | Unit test fakes isolated under `tests/unit/fakes/` |
| `tests/unit/test_story_26_4b_governance_feedback_folders_and_audit.py` & `tests/unit/test_story_26_4b_branches_coverage.py` | Created | 248 / 165 | Story `26.4b` unit coverage for Mode A PG18/funnel rules, feedback, folder meta & phantom audit |
| `tests/unit/test_epic_10_story_10_1_assistant_governance.py` & `10_3` + `tests/security/test_story_26_1*.py` | Modified | — | Updated unit & security assertions for Mode B removal & async governance/citations |
| `tests/integration/api/_pg18_story_26_4b_helpers.py` & `test_story_26_4b_pg18_*.py` (`migration`, `persistence`, `threads_and_sharing`) | Created | 99 / 78 / 278 / 175 | Layer 2 real PG18 vertical `create_app()` tests (`0` overrides, cold restart survival, Alembic `upgrade -> downgrade -> upgrade`, direct SQL verification) |
| `docs/product/capabilities.yaml` & `apps/web/src/generated/orciaSiteManifest.ts` & `docs/site-catalog/index.html` | Modified | — | Updated `CAP-070`, `CAP-072`, `CAP-073` and synced catalog manifest |

### 3.2 Quantitative Results & 5-Layer (`AD-17`) Verification

- **Story `26.4b` Branch Coverage (`18` target modules via `coverage run --branch ... --no-cov` + `coverage report --fail-under=90`):** **`91%`** (`821` statements, `46` missed, `142` branches, `37` partial; `18 passed` across unit & PG18 `create_app()` suites). Per-file highlights: `assistant_workspace_citations.py` `100%`, `assistant_workspace_governance.py` `98%`, `assistant_governance_models.py` `100%`, `assistant_feedback.py` `100%`, `assistant_citations_and_v5_guard.py` `98%`, `sql_assistant_feedback.py` `98%`, `_sql_assistant_governance_queries.py` `95%`, `sql_assistant_governance.py` `94%`, `_assistant_governance_sync.py` `93%`, `_assistant_citations_verifier.py` `92%`, `assistant_governance_studio.py` `91%`, `sql_assistant_folders.py` `91%`.
- **Unit, Security, Evals & Contract Suites (`--no-cov`):** **`1118 passed`** (`971` unit + `147` security/evals/contract, `0` failures), including `test_zero_orphan_sql_adapters_audit.py` (`0` orphan SQL adapters) and `test_codebase_architectural_anti_patterns_audit.py`.
- **PostgreSQL 18 + Redis 7.4 Integration Suite (`testcontainers`):** **`8/8 passed`** across Story `26.4b` PG18 vertical `create_app()` cold-restart tests (`0` overrides) and Epic 10/25.5/26.1 non-regression tests.
- **Static & Architecture Gates:**
  - `.venv/bin/ruff check .` -> `All checks passed!`; `.venv/bin/ruff format --check .` -> `1463 files already formatted`.
  - `.venv/bin/mypy --strict packages/orcia-core/src packages/orcia-connectors/src apps/api/src apps/worker/src` -> `Success: no issues found in 668 source files`.
  - `.venv/bin/lint-imports` -> `Contracts: 5 kept, 0 broken` (`712` files, `5140` dependencies).
  - `.venv/bin/python scripts/export_openapi.py --check` -> exit `0` (`0-diff`).
  - `.venv/bin/alembic -c infra/migrations/alembic.ini heads` -> single linear head `20261122_264b (head)`; PG18 `upgrade -> downgrade -> upgrade` verified.
- **TypeScript / SPA & Playwright Desktop E2E:**
  - `pnpm turbo run lint typecheck test` -> **`9/9` tasks succeeded** (`@orcia/api-client`: `20/20`, `@orcia/ui`: `34` files, `@orcia/web`: `67/67` files / `261/261` tests).
  - Playwright Desktop E2E (`00`, `02`, `12-finops`, `12-epic16`, `16`, `21`, `env -u ORCIA_E2E_SEED_FIXTURES`) -> **`15 passed / 1 skipped / 0 failed`**.
- **Zero credentials & documentation gates:** verified via `detect-secrets-hook`, `scripts/check_implementation_docs.py`, `pnpm site:sync && pnpm site:check`, and `npx gitnexus analyze --index-only .`.

### 3.3 Final Closure Decision (`done`)

- **Testing Sub-Agent Verification (`ba80fd81`):** Independently verified `100%` PASS across all checks (`91%` 18-module branch coverage, `1118 passed` unit/security/evals/contract, `8/8` PG18+Redis integration, `9/9` Turbo, `15 passed / 1 skipped / 0 failed` Playwright Desktop E2E, all non-generated touched source files `<= 299` L including `sql_assistant_governance.py` at `299` L and `assistant_feedback.py` at `15` L, `0-diff` OpenAPI, `5/5` `lint-imports`). Story `26.4b` is closed as `done`.
