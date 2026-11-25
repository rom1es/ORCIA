# Story 30.2 — `Mon Assistant` Clean Conversational System Prompt, Single Layer Injection & Empty-Evidence Anti-Hallucination Guard

- **Date**: 2026-11-25
- **Story / Sprint Key**: `30-2-assistant-conversational-prompt-cleanup-and-empty-evidence-guard` (`Epic 30`, Lot 1)
- **Capability(ies)**: `CAP-022`, `CAP-070`, `CAP-071`, `CAP-072`, `CAP-074` — classification: `feature` / `ux`
- **Author / Context**: `bmad-dev-worker` (`UX30-04`, `UX30-05`, `AD-15`, `AD-17`, `EXPERIENCE.md` §1.2 #1)
- **Associated Commits**: Pending (coding phase in progress)

---

## 1. Needs Analysis & Tech Lead Impact Study (Pre-Implementation)

### 1.1 Context & Problem Statement
- **Live prompt contamination & duplication (`UX30-04`)**: Currently, live `/api/v1/assistant/turns` requests invoke `gov.assemble_five_layers_preview_async()` in `apps/api/src/orcia_api/routers/_assistant_context_assembly.py` without `pack_key` (always printing `[ACTIVE_DOMAIN_PACK: core]`) and format the 5 Tab 3 UI preview cards (`### 1. 🔒 Constitution ...`, `[TEAM_AND_HAT: ...]`, `[WORKSPACE: ...]`, `[USER: ...]`) verbatim into `assembled_5_layers_prompt`. `AssistantPromptBuilder.build_system_instructions()` then calls `format_governance_and_folder_sections()`, injecting Layer 4 Workspace instructions and Layer 5 User preferences a second time under raw markers (`[LAYER_4_WORKSPACE_INSTRUCTIONS]`, `[LAYER_5_USER_PREFERENCES]`, `[ADAPTATION_RUNTIME_METADATA]`).
- **Internal plumbing leakage & missing confidentiality rule (`UX30-04`)**: `assistant_prompt_locales.py` and `_assistant_profile_locales.py` inject raw markers (`[CONSTITUTIONAL_IMMUTABLE_LAYER_1]`, `[NO_HUMAN_ANCHOR_WRITE]`, `[NO_GATE_SELF_APPROVAL]`, `[EXPLICIT_PROVENANCE_URI]`, `human_authored_required: true`) and low-level runtime jargon (`"Topologie DAG, Dépendances, Hashes SHA-256 & Exécution N3"`, `"DAG Steps & Verrous run-lock.json"`) with no natural-speech or prompt-confidentiality directive. On simple greetings, models echo internal rules and URIs.
- **Unconditional provenance demands on empty Evidence Tables (`UX30-05`)**: When an Assistant turn retrieves `0` RAG/Blackboard sources and `0` ontology glossary items, `format_evidence_table_for_layer_4()` returns `""` and `format_system_instructions_text()` omits the evidence block silently, while Layer 1 still demands `orcia://` URIs and `sha256:` digests. Models hallucinate `[S1]` (rewritten to `[Citation non vérifiée]`), `orcia://system/status/ready`, and `sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (`SHA-256("")`), and `_assistant_citations_verifier.py` leaves raw `orcia://` and `SHA-256("")` strings intact.
- **Expected behavior**:
  1. Strictly keep `build_five_layers_preview_items()` for Tab 3 UI Governance Preview (`GET /api/v1/assistant/governance`) while assembling a dedicated, non-duplicated conversational system prompt for live turns.
  2. Inject Workspace instructions and User preferences (`tone`, `format`, and non-empty `personal_instructions`) once; omit `personal_instructions` completely when `""`; resolve and propagate the genuinely active `pack_key` when available.
  3. Strip all raw internal bracket markers and `TECH_LEAD` DAG/run-lock plumbing from conversational prompts in both `fr` and `en`, while preserving untrusted prompt-injection sanitization in `_assistant_prompt_sanitization.py` and adding an explicit Natural-Speech & System-Prompt Confidentiality rule.
  4. Make provenance citation rules (`[S#]`, `[G#]`, `[O#]`, `orcia://`, `sha256:`) strictly conditional on `has_evidence=True`; emit an explicit localized (`fr`/`en`) Empty-Evidence Guard when `has_evidence=False`; and harden `_assistant_citations_verifier.py` to scrub fabricated `SHA-256("")`, ungrounded `orcia://system/*`, and phantom `[S#]` tags cleanly without emitting `[Citation non vérifiée]` when `EvidenceTable` is empty.

### 1.2 Exploration, GitNexus Impact Analysis, Refactoring & Technical Debt
- **GitNexus Impact Analysis (`gitnexus_query`, `gitnexus_context`, `gitnexus_impact` scoped to `repo: "/home/romain/Documents/Projects/ORCIA"`) + Worktree Caller Audit**:
  - GitNexus index is 13 commits behind `HEAD` (`AssistantPromptBuilder` resolved in `packages/orcia-core/src/orcia_core/orchestration/assistant_prompt_builder.py`, imported by `_assistant_turn_engine_plan.py`). Worktree grep across `apps/` and `packages/` confirmed all live callers:
    - `format_system_instructions_text`: defined in `assistant_prompt_preview.py:L234`, called by `AssistantPromptBuilder.build_system_instructions` (`assistant_prompt_builder.py:L239`).
    - `build_five_layers_preview_items`: defined in `assistant_prompt_preview.py:L129`, wrapped by `assistant_governance_layers.py:L15`, `AssistantPromptBuilder.build_five_layers_preview` (`assistant_prompt_builder.py:L265`), `_assistant_governance_sync.py:L163`, and `assistant_governance.py:L215,L257`.
    - `AssistantPromptBuilder`: instantiated in `apps/api/src/orcia_api/dependencies/portal_and_assistant.py:L178`, `apps/api/src/orcia_api/routers/assistant_llm_prompts.py:L34`, `assistant_turn_engine.py:L60`, `assistant_harness.py:L32`, and `assistant_governance_layers.py:L12`.
    - `build_assistant_system_instructions`: facade in `assistant_llm_prompts.py:L57`, re-exported by `assistant_llm_bridge.py:L28` and invoked by `resolve_assembled_turn_context_and_instructions_async` (`assistant_llm_prompts.py:L195`) and `resolve_assembled_system_instructions_for_turn` (`assistant_llm_prompts.py:L282`), which serve `assistant_turns.py`, `_assistant_llm_stream_bridge.py`, and `_mcp_assistant_ask_bridge.py`.
    - `verify_and_sanitize_citations_impl`: defined in `_assistant_citations_verifier.py:L97`, delegated by `AssistantCitationAndV5GuardService.verify_and_sanitize_citations` (`assistant_citations_and_v5_guard.py:L118`), called in N6 (`_assistant_turn_engine_citations.py`).
  - **Risk level**: Medium — shared prompt pipeline across Speed 1, Speed 2/3, and MCP `assistant.ask`, plus existing security/unit/eval assertions (`test_story_26_1_*`, `test_story_26_2_*`, `test_story_26_10_*`, `test_story_29_3_*`, `test_i18n_backend_catalog_and_english_dev_audit.py`).
- **File Line-Count Control (`<= 300` lines) & Modular Splits**:
  - Current sizes of target files are very close to the 300-line ceiling: `_assistant_context_assembly.py` (`298 L`), `assistant_llm_prompts.py` (`297 L`), `assistant_prompt_preview.py` (`296 L`), `assistant_governance.py` (`282 L`), `assistant_evidence_table.py` (`277 L`), `assistant_prompt_builder.py` (`275 L`), `assistant_prompt_locales.py` (`270 L`), `_assistant_citations_verifier.py` (`186 L`), `_assistant_profile_locales.py` (`173 L`).
  - To strictly honor `<= 300` lines per production file without bloating `assistant_prompt_preview.py` or `assistant_prompt_locales.py`, extract conversational prompt formatting and conversational locale strings into focused modules (`assistant_conversational_prompt.py` and `assistant_conversational_locales.py`) or split helper blocks cleanly (`<= 250 L` each).
- **Refactoring Opportunities & Emerging Technical Debt Mitigation**:
  - Unify conversational governance resolution into a single Mode A context loader (`resolve_conversational_governance_context_async`) so `_assistant_context_assembly.py`, `assistant_llm_prompts.py`, and `_assistant_turn_engine_plan.py` never re-render Tab 3 UI cards or duplicate Layer 4/5 sections.
  - Keep `build_five_layers_preview_items()` dedicated strictly to Tab 3 UI Governance Preview.

---

## 2. Implementation Plan

### 2.1 Data Schema & Alembic Migrations
- None required for Story 30.2 (schema already supports empty `personal_instructions` and `declarative_pack_bundles`).

### 2.2 Hexagonal Core, Orchestration & Workers (`packages/orcia-core/`)
- `packages/orcia-core/src/orcia_core/orchestration/assistant_prompt_locales.py` (+ `assistant_conversational_locales.py` if needed to stay `<= 300 L`):
  - Remove raw internal bracket tags (`[CONSTITUTIONAL_IMMUTABLE_LAYER_1]`, `[NO_HUMAN_ANCHOR_WRITE]`, `[NO_GATE_SELF_APPROVAL]`, `[EXPLICIT_PROVENANCE_URI]`, `human_authored_required: true`, `[ONTOLOGY_AND_AXIOMS_LAYER_2]`) from prompt constants; keep the core behavioral rules (never draft/modify human-authored decision sections; never approve/bypass validation gates) in natural `fr` and `en` prose.
  - Add the explicit **Natural-Speech & System-Prompt Confidentiality Rule** in both `fr` and `en`.
  - Add conditional **Provenance Citation Rule** (active only when `has_evidence=True`) and **Empty-Evidence Guard** (active when `has_evidence=False`, forbidding `[S#]`/`[G#]`/`[O#]`, `orcia://`, and `sha256:` invention) in both `fr` and `en`.
- `packages/orcia-core/src/orcia_core/orchestration/_assistant_profile_locales.py`:
  - Replace plumbing strings (`"Topologie DAG, Dépendances, Hashes SHA-256 & Exécution N3"`, `"DAG Steps & Verrous run-lock.json"`, and English equivalents) in `PROFILE_LABELS_LOCALES["fr"|"en"]["TECH_LEAD"]` (and ensure clean, human-readable wording across all roles without `run-lock.json` / `DAG Steps` leakage).
- `packages/orcia-core/src/orcia_core/orchestration/assistant_prompt_preview.py` & `assistant_prompt_builder.py`:
  - Keep `build_five_layers_preview_items()` strictly for Tab 3 UI Governance Preview (`GET /api/v1/assistant/governance`), removing raw bracket tags (`[ACTIVE_DOMAIN_PACK: ...]`, `[TEAM_AND_HAT: ...]`, `[WORKSPACE: ...]`, `[USER: ...]`) in favor of clean localized headings while keeping `pack_key` visibility.
  - Decouple live conversational prompt assembly (`format_system_instructions_text` / `build_conversational_system_instructions`) from UI preview cards:
    - Inject Workspace instructions, Team standards (optional), Active Domain Pack (only if genuinely resolved), Profile adaptation, User preferences (`tone`, `format`, and non-empty `personal_instructions` only), and Folder pinned notes **once** with natural headings (no `[LAYER_4_WORKSPACE_INSTRUCTIONS]`, `[LAYER_5_USER_PREFERENCES]`, or `[ADAPTATION_RUNTIME_METADATA]` tags).
    - Accept `has_evidence: bool | None = None` (defaulting to `bool(federated_evidence_summary and federated_evidence_summary.strip())` when omitted) so citation provenance rules activate strictly when `has_evidence=True`, and the Empty-Evidence Guard activates when `has_evidence=False`.
- `packages/orcia-core/src/orcia_core/orchestration/assistant_governance.py` & `_assistant_governance_sync.py`:
  - Provide `load_conversational_governance_async()` / `load_conversational_governance()` returning resolved Mode A fields (`UserLayerPreferences`, `WorkspaceLayerSettings`, `team_instructions`, `workspace_label`, `user_label`) without constructing UI preview cards.
- `packages/orcia-core/src/orcia_core/orchestration/_assistant_turn_engine_plan.py`:
  - When `assembled_5_layers_prompt` is not pre-assembled, assemble clean conversational base context (not Tab 3 UI cards) and propagate `has_evidence` / `pack_key` cleanly to `prompt_builder.build_system_instructions(...)`.
- `packages/orcia-core/src/orcia_core/orchestration/assistant_evidence_table.py`:
  - Update `format_evidence_table_for_layer_4()` to use clean localized headings (no `[SERVER_EVIDENCE_TABLE_LAYER_4]` / `[TABLE_PREUVES_SERVEUR_COUCHE_4]` raw bracket tokens) when evidence exists, and return empty string (or delegate Empty-Evidence Guard signaling cleanly via `has_evidence`) when `table.sources` and `table.glossary_items` and `table.tool_outputs` are all empty.
- `packages/orcia-core/src/orcia_core/orchestration/_assistant_citations_verifier.py`:
  - When `known_tags` is empty: strip phantom `[S#]`/`[G#]`/`[O#]` tags cleanly without emitting `[Citation non vérifiée]`, scrub `sha256:e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855` (`SHA-256("")`), and scrub ungrounded `orcia://system/...` (and ungrounded `orcia://...` proof lines/tokens) cleanly while preserving all verified behavior when `known_tags` is non-empty.

### 2.3 Backend API, Security & Contracts (`apps/api/`)
- `apps/api/src/orcia_api/routers/_assistant_context_assembly.py`:
  - Resolve the genuinely active `pack_key` from workspace/platform context (`studio_and_packs_service` / `app.state.declarative_pack_bundles`) without hardcoding `"core"`.
  - Load conversational governance settings (`load_conversational_governance_async`) instead of calling `assemble_five_layers_preview_async()` for live turns, and pass `has_evidence = bool(evidence_res.evidence_table.sources or evidence_res.evidence_table.glossary_items)` and `pack_key` through `AssembledTurnContext`.
- `apps/api/src/orcia_api/routers/assistant_llm_prompts.py` & `apps/api/src/orcia_api/routers/assistant_turns.py`:
  - Propagate `has_evidence`, `pack_key`, and non-duplicated Workspace/User instructions (`payload` overriding hydrated Mode A values when explicitly provided, otherwise hydrated once from `turn_ctx`) into `build_assistant_system_instructions` / `turn_engine.n2_plan_and_assemble_async`.
  - Preserve untrusted input escaping in `_assistant_prompt_sanitization.py` so user-supplied `[CONSTITUTIONAL_*]` / `[LAYER_*]` injection payloads continue to be neutralized (`(escaped:...)`).
- `apps/api/src/orcia_api/routers/assistant_workspace_governance.py`:
  - Resolve active `pack_key` when query param `pack_key` is omitted on `GET /api/v1/assistant/governance` so Tab 3 UI reflects the active pack too.

### 2.4 User Interface & Experience (`apps/web/`, `packages/ui/`)
- No frontend changes required for Story 30.2 (Tab 3 UI preview contract `GET /api/v1/assistant/governance` remains intact).

### 2.5 Test Pyramid Impact Analysis (`AD-17`)
- **Layer 1a (Python Unit `tests/unit/`)**:
  - Add `tests/unit/test_story_30_2_assistant_conversational_prompt.py` (`<= 300 L`) validating: zero raw internal tokens in live conversational prompts (`fr` & `en`), single Workspace/User injection, omitted empty `personal_instructions`, active `pack_key`, sanitized `TECH_LEAD` profile phrasing, conditional citation rules + explicit Empty-Evidence Guard when `EvidenceTable` is empty vs active citations when non-empty, and `_assistant_citations_verifier` scrubbing `SHA-256("")` and ungrounded `orcia://system/*`.
  - Update legacy assertions in `test_story_26_2_core_llm_streaming_and_prompt_builder.py`, `test_story_26_10_epic_26_closure_ast_and_routes_audit.py`, `test_story_29_3_assistant_prompt_sanitization.py`, `test_story_29_3_turn_plan_and_preview_cov.py`, `test_assistant_agnostic_async_llm_bridge.py`, and `test_epic_10_story_10_2_three_speed_tier_routing.py` where they previously checked old raw bracket markers.
  - Run `test_i18n_backend_catalog_and_english_dev_audit.py` to guarantee zero French leakage into `en` prompts or code comments/docstrings.
- **Security Layer (`tests/security/`) & Evals (`tests/evals/`)**:
  - Verify `test_story_26_1_assistant_security_hardening.py` (updating only old raw bracket tag expectation while keeping Layer 1 immutability & injection-escaping intact), `test_story_26_10_assistant_security_redteam.py`, and `tests/evals/*`.
- **Layers 2, 3, 4, 5 (Deferred to Testing Sub-Agent)**:
  - Full repo-wide `ruff`, `mypy --strict`, `lint-imports`, `>= 90%` branch coverage, PG18 integration, and Playwright E2E executed by Testing Sub-Agent.

---

## 3. Summary of Changes & Results (Post-Implementation)

### 3.1 Created & Modified Files

Every Story 30.2 production and new test Python file complies with the `<= 300` line limit (max `300` lines):

| File | Action | Line Count | Concise Summary |
| :--- | :--- | :--- | :--- |
| `packages/orcia-core/src/orcia_core/orchestration/_assistant_conversational_locales.py` | Created | `86` L | Bilingual (`fr` / `en`) conversational prompt rules: Natural-Speech & System-Prompt Confidentiality rule, conditional Provenance Citation rule, and Empty-Evidence Guard. |
| `packages/orcia-core/src/orcia_core/orchestration/_assistant_conversational_prompt.py` | Created | `162` L | Dedicated single-injection conversational prompt formatter (`format_conversational_system_instructions`), emitting active `pack_key`, Workspace/User preferences once, omitting empty `personal_instructions`, and gating provenance vs. Empty-Evidence Guard on `has_evidence`. |
| `packages/orcia-core/src/orcia_core/orchestration/_assistant_governance_async_views.py` | Created | `230` L | Async Mode A governance views & conversational context loader extracted to keep `assistant_governance.py <= 300` L. |
| `packages/orcia-core/src/orcia_core/orchestration/assistant_prompt_locales.py` | Modified | `270` L | Removed raw internal bracket tags (`[CONSTITUTIONAL_*]`, `[NO_HUMAN_ANCHOR_WRITE]`, `[NO_GATE_SELF_APPROVAL]`, `[EXPLICIT_PROVENANCE_URI]`, `human_authored_required: true`, `[ONTOLOGY_AND_AXIOMS_LAYER_2]`) while keeping behavioral rules in natural `fr`/`en` prose. |
| `packages/orcia-core/src/orcia_core/orchestration/_assistant_profile_locales.py` | Modified | `182` L | Replaced `TECH_LEAD` DAG/SHA-256/`run-lock.json` plumbing jargon with clean human-readable `fr`/`en` wording. |
| `packages/orcia-core/src/orcia_core/orchestration/assistant_prompt_preview.py` | Modified | `261` L | Kept `build_five_layers_preview_items()` dedicated to Tab 3 UI Governance Preview (clean localized headings, `pack_key` visibility) and delegated live prompt formatting to `_assistant_conversational_prompt.py`. |
| `packages/orcia-core/src/orcia_core/orchestration/assistant_prompt_builder.py` | Modified | `284` L | Added `has_evidence: bool | None` and `pack_key` propagation on `AssistantPromptBuilder.build_system_instructions()` without duplicating Layer 4/5 sections. |
| `packages/orcia-core/src/orcia_core/orchestration/assistant_governance_models.py` | Modified | `167` L | Added `ConversationalGovernanceContext` model for Mode A single-pass loading. |
| `packages/orcia-core/src/orcia_core/orchestration/_assistant_governance_sync.py` | Modified | `244` L | Added synchronous `load_conversational_governance()` alongside Tab 3 preview assembly. |
| `packages/orcia-core/src/orcia_core/orchestration/assistant_governance.py` | Modified | `199` L | Delegated async governance views and added `load_conversational_governance_async()`. |
| `packages/orcia-core/src/orcia_core/orchestration/_assistant_turn_engine_plan.py` | Modified | `173` L | Propagated `has_evidence` and `pack_key` cleanly during N2 planning when assembling conversational prompts. |
| `packages/orcia-core/src/orcia_core/orchestration/assistant_turn_engine.py` | Modified | `299` L | Wired `has_evidence` / `pack_key` parameters through turn orchestration. |
| `packages/orcia-core/src/orcia_core/orchestration/assistant_evidence_table.py` | Modified | `275` L | Replaced raw `[SERVER_EVIDENCE_TABLE_LAYER_4]` / `[TABLE_PREUVES_SERVEUR_COUCHE_4]` bracket markers with clean localized headings and empty return when no evidence exists. |
| `packages/orcia-core/src/orcia_core/orchestration/_assistant_citations_verifier.py` | Modified | `236` L | Scrubbed phantom `[S#]`/`[G#]`/`[O#]` tags without `[Citation non vérifiée]`, `SHA-256("")` (`e3b0c44...`), and ungrounded `orcia://system/*` URIs when `known_tags` is empty. |
| `apps/api/src/orcia_api/routers/_assistant_ontology_context.py` | Created | `100` L | Extracted active `pack_key` & ontology context resolution helper to keep `_assistant_context_assembly.py <= 300` L. |
| `apps/api/src/orcia_api/routers/_assistant_context_assembly.py` | Modified | `292` L | Replaced `assemble_five_layers_preview_async()` in live turns with `load_conversational_governance_async()`, resolved genuine `pack_key`, and computed `has_evidence`. |
| `apps/api/src/orcia_api/routers/_assistant_prompt_sanitization.py` | Modified | `105` L | Preserved untrusted prompt-injection bracket escaping (`(escaped:...)`) for `[CONSTITUTIONAL_*]` and `[LAYER_*]` user inputs. |
| `apps/api/src/orcia_api/routers/assistant_llm_prompts.py` | Modified | `270` L | Propagated single-injected Workspace/User instructions, `has_evidence`, and active `pack_key` into `build_assistant_system_instructions`. |
| `apps/api/src/orcia_api/routers/assistant_turns.py` | Modified | `300` L | Passed `has_evidence` and `pack_key` from `turn_ctx` into `n2_plan_and_assemble_async`. |
| `apps/api/src/orcia_api/routers/assistant_workspace_governance.py` | Modified | `180` L | Resolved active `pack_key` when omitted on `GET /api/v1/assistant/governance`. |
| `tests/unit/test_story_30_2_assistant_conversational_prompt.py` | Created | `239` L | Dedicated Story 30.2 unit suite covering FR/EN clean conversational prompts, single Mode A injection, empty `personal_instructions`, active `pack_key`, `TECH_LEAD` wording, Empty-Evidence Guard, and citation scrubber. |
| `tests/unit/test_story_26_2_core_llm_streaming_and_prompt_builder.py`, `tests/unit/test_story_26_10_epic_26_closure_ast_and_routes_audit.py`, `tests/unit/test_story_29_3_turn_plan_and_preview_cov.py`, `tests/unit/test_assistant_agnostic_async_llm_bridge.py`, `tests/unit/test_epic_10_story_10_2_three_speed_tier_routing.py`, `tests/security/test_story_26_1_assistant_security_hardening.py` | Modified | — | Aligned legacy bracket-tag assertions with clean conversational prompt wording while preserving Layer 1 immutability and injection escaping checks. |

### 3.2 Quantitative Metrics, Coverage & Static Quality
- **Scoped Python branch coverage (`--branch`, `--fail-under=90`)**: **`92%`** overall (`1003` statements / `174` branches, `143 passed in 221.71s`) across the 20 Story 30.2 production modules:
  - `100%`: `_assistant_conversational_locales.py`, `_assistant_conversational_prompt.py`, `_assistant_profile_locales.py`, `_assistant_turn_engine_plan.py`, `assistant_evidence_table.py`, `assistant_governance.py`, `assistant_governance_models.py`, `assistant_prompt_builder.py`, `assistant_prompt_locales.py`, `assistant_prompt_preview.py`, `_assistant_ontology_context.py`
  - `98%` `assistant_turns.py`, `96%` `assistant_turn_engine.py`, `95%` `_assistant_governance_sync.py`, `91%` `assistant_workspace_governance.py`, `90%` `_assistant_governance_async_views.py`, `83%` `_assistant_citations_verifier.py`, `77%` `assistant_llm_prompts.py`, `67%` `_assistant_prompt_sanitization.py`, `65%` `_assistant_context_assembly.py`
- **Static Quality & Architecture**:
  - `.venv/bin/ruff check .`: `All checks passed!` (`0` errors)
  - `.venv/bin/ruff format --check .`: `1755 files already formatted`
  - `.venv/bin/mypy --strict packages/orcia-core packages/orcia-connectors apps/api apps/worker`: `Success: no issues found in 860 source files`
  - `.venv/bin/lint-imports`: `Contracts: 5 kept, 0 broken` (`903 files, 6515 dependencies`)
  - `.venv/bin/python .agent/skills/bmad-architecture/scripts/lint_spine.py`: `ok: true, total_findings: 0`
  - `.venv/bin/python scripts/export_openapi.py --check`: `0-diff` (`exit 0`)
  - `gitnexus_detect_changes(repo: "ORCIA", scope: "all", worktree: ".../consignes_personnelles_save_button")`: `changed_count: 19`, `affected_count: 13`, `changed_files: 23`, `risk_level: "high"` (shared `AssistantPromptBuilder` / `assistant_turns` pipeline; verified across all 5 `AD-17` layers).

### 3.3 AD-17 Test Pyramid & Vertical Wiring Verification
- **Layer 1a — Python Unit Tests (`tests/unit/`, `--no-cov`)**: **`1132 passed in 328.62s`** (including `test_story_30_2_assistant_conversational_prompt.py` and `test_i18n_backend_catalog_and_english_dev_audit.py`).
- **Layer 1b — TypeScript / React (`pnpm turbo run lint typecheck test --concurrency=2`)**: **`9/9` tasks successful** (`@orcia/api-client`: `3 files / 20 tests`; `@orcia/ui`: `38 files / 149 tests`; `@orcia/web`: `91 files / 356 tests`, including i18n Gates 1–3, `zero-dead-buttons-and-silent-catches-audit`, and `e2e-testids-sync-audit`).
- **Layer 2 — Vertical Integration `HTTP ➔ PostgreSQL 18 + Redis 7.4` (`testcontainers`, `--no-cov`)**: **`6 passed in 101.43s`** (`test_story_25_5_assistant_chat_only_and_rag_guard_postgres18.py`, `test_story_26_1_assistant_security_postgres18.py`, `test_story_26_4b_pg18_persistence_governance_feedback_folders.py`, `test_story_26_5_real_context_and_history_postgres18.py`, `test_story_26_7_unified_turn_engine_postgres18.py`).
- **Layer 3 — API Contracts (`export_openapi --check`, `tests/contract`, `lint-imports`, `lint_spine.py`)**: All passed (`0-diff`, `5 kept / 0 broken`, `0` findings).
- **Layer 4 — AI Evals (`tests/evals/`) & Security / Red-Team (`tests/security/`) + Contracts (`tests/contract/`)**: **`181 passed in 110.69s`**.
- **Layer 5 — Desktop Playwright E2E (`env -u ORCIA_E2E_SEED_FIXTURES`, `--project=desktop-cockpit`)**: **`6 passed (1.8m)`** across `e2e/02-assistant-streaming-and-folders.spec.ts`, `e2e/21-assistant-citations-v5-audit-help-showcase.spec.ts`, and `e2e/22-assistant-tool-loop-approval-and-reattach.spec.ts` against real ephemeral PG18 + Redis 7.4 (auto-generated E2E screenshots cleaned after verification).
