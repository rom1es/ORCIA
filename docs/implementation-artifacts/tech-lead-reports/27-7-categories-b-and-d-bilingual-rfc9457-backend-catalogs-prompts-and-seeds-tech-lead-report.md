# Story 27.7 — Categories B & D Remediation: Bilingual RFC 9457 Backend Error Catalogs, Prompts & Seeds (Gate 4 Baseline = 0)

- **Date**: 2026-11-24
- **Story / Sprint Key**: `27-7-categories-b-and-d-bilingual-rfc9457-backend-catalogs-prompts-and-seeds` (`Epic 27` / Lot 4)
- **Capability(ies)**: `CAP-001`..`CAP-260` (cross-cutting backend RFC 9457, LLM prompt & seed localization — classification: `hygiene`)
- **Author / Context**: `Amelia` (`bmad-dev-worker` Coding Sub-Agent) — Remediates Epic 27 Decisions `D2`, `D3` (Gate 4), and `D4` (Categories B `577` + D `193` backend hits; `757` non-catalog French literals across `153` files + `3` missing error catalog codes) while enforcing English-only code comments/docstrings and strict `<= 300`-line modularity.
- **Associated Commits**: `3e7d7f7` (`feat(story-27.7): localize Category B/D backend RFC 9457 error catalogs and prompts in FR/EN and lock Gate 4 to zero`) on branch `feat/epic-27-bilingual-i18n-and-deterministic-locale-guards`

---

## 1. Needs Analysis & Tech Lead Impact Study (Pre-Implementation)

### 1.1 Context & Problem Statement
- **Problem**: Gate 4 (`tests/unit/test_i18n_backend_catalog_and_english_dev_audit.py`) currently records `3` unregistered `OrciaDomainError` codes (`ERR_HELP_ARTICLE_VALIDATION_FAILED`, `ERR_INVALID_MCP_TOKEN_CONFIG`, `ERR_PACK_BUILDER_VALIDATION_FAILED`) and `757` non-catalog French string literals across `153` backend Python files (`packages/orcia-core`, `apps/api`). Additionally, many domain errors pass hardcoded French `detail_override` strings that bypass `Accept-Language: en` resolution in `trace_and_error.py`, and several LLM prompts, user-facing markdown outputs, notifications, provenance reports, and seed display labels lack bilingual `fr`/`en` bundles.
- **Expected vs Current Behavior**:
  - Current: `OrciaDomainError` subclasses or router `HTTPException` raises pass hardcoded French strings into `detail_override`, preventing `Accept-Language: en` from returning English RFC 9457 details; Category D prompts, governance texts, and seed labels embed French literals directly inside core/router logic.
  - Expected: Every `error_code` is registered in `*_error_catalog.py` with jargon-free `fr` and `en` templates (supporting parameterized interpolation via `detail_params` without overriding `Accept-Language` translation); user-facing backend outputs, prompts, and seed display copies resolve cleanly from explicit `fr`/`en` locale bundles (`*_locales.py` / `*_locale_messages.py` defaulting to `"fr"` to preserve existing FR contracts and `Accept-Language: en` switching); internal non-user-facing diagnostics, comments, and docstrings are strictly English-only; Gate 4 (`i18n_backend_audit_baseline.json`) reaches `0` across all metrics.
- **Constraints (`ARCHITECTURE-SPINE.md` / `AGENTS.md`)**:
  - Preserve `5/5` `lint-imports` contracts (`AD-19`, `AD-20`) — zero framework imports in `orcia_core.kernel`, `domain`, or `ports`, and zero cross-domain `_internal` imports.
  - Preserve `0-diff` OpenAPI 3.1 (`scripts/export_openapi.py --check`) by regenerating `openapi.json` and `packages/api-client/src/generated/` if any Pydantic schema defaults change.
  - Keep every created or modified Python file `<= 300` lines (`wc -l`), splitting the `50` oversized target files and oversized error catalogs cleanly into `<domain>/_*.py` modules.
  - Preserve all `test_codebase_architectural_anti_patterns_audit.py` invariants (`TID251`, SSRF guard, zero vendor names, zero silent `except Exception:`).

### 1.2 Exploration, GitNexus Impact Analysis, Refactoring & Technical Debt
- **GitNexus Impact Analysis (`repo: "/home/romain/Documents/Projects/ORCIA"`)**:
  - `OrciaDomainError` (`packages/orcia-core/src/orcia_core/kernel/errors.py`): `impactedCount: 125` (`110` direct subclasses/callers at depth 1, `15` at depth 2), risk `CRITICAL`. All extensions to `OrciaDomainError` (`detail_params` support) must remain 100% backward-compatible with existing `detail_override`, `instance`, and `permission_broker_hint` keyword arguments.
  - `AssistantHarness` (`packages/orcia-core/src/orcia_core/orchestration/assistant_harness.py`): context resolved cleanly (`__init__`, `assemble_prompt`), already delegates Layer 1–5 prompt strings to `assistant_prompt_locales.py`.
  - `get_localized_error_text` / `get_prompt_locale_bundle`: `UNKNOWN` in slightly stale index (7 commits behind HEAD from 27.1–27.6); confirmed upstream callers via text search in `apps/api/src/orcia_api/middleware/trace_and_error.py`, `apps/api/src/orcia_api/errors/registry.py`, and `packages/orcia-core/src/orcia_core/orchestration/`.
- **Exploration & Key Metrics**:
  - `tests/unit/i18n_backend_audit_baseline.json`: `3` missing error catalog codes, `0` prompt directive violations, `757` non-catalog French literals across `153` files (`50` of which exceed `300` lines, led by `notifications_and_claims.py` at `930` L, `pack_builder_processes.py` at `669` L, `permissions/broker.py` at `605` L, `studio_and_packs.py` at `582` L, `gates/human.py` at `576` L, plus `kernel/errors.py` `394` L, `orchestration/errors.py` `387` L, `permissions/_error_catalog.py` `406` L).
  - Downstream test audit across `tests/` and `apps/web/e2e/` identified exact string contracts that must preserve `"fr"` as default locale: `provenance_exporter.py` (`CONFORME (100 % ALIGNÉ)`), `ontology/__init__.py` (`Actif Stratégique` in golden evals & PG18 tests), `progressive_accostage.py` (`4. Premier Espace d'équipe` in E2E `01-day0`), `_mcp_token_helpers.py` (`Clé personnelle d'éditeur`), `_governed_mcp_helpers.py` (`💻 Appelé via MCP (IDE)`), `assistant_citations_and_v5_guard.py`, `assistant_profile_adaptation.py`, `_assistant_prompt_sanitization.py`, and `notifications_and_claims.py`.
- **Refactoring Opportunities & Emerging Technical Debt Mitigation**:
  - Add additive `detail_params: dict[str, str | int] | None = None` support on `OrciaDomainError` and `get_localized_error_text()` so parameterized errors localize dynamically in both `fr` and `en` without `detail_override` bypassing `Accept-Language`.
  - Split oversized error catalogs (`kernel/_error_catalog.py`, `orchestration/_error_catalog.py`, `permissions/_org_error_catalog.py`) and all `50` oversized backend files touched (`> 300` L) into focused `<= 300`-line helper modules.
  - Standardize bilingual backend message bundles under `*_locale_messages.py` / `*_locales.py` (excluded from raw FR-literal scan in Gate 4 while enforcing strict `fr`/`en` parity and English-only comments/docstrings in Gate 4).

---

## 2. Implementation Plan

### 2.1 Data Schema & Alembic Migrations
- None. No database table or Alembic revision changes are required; all persistence schemas and UUIDv7/append-only invariants remain intact.

### 2.2 Hexagonal Core, Orchestration & Workers (`packages/orcia-core/`)
- **`kernel/errors.py` & `kernel/_error_catalog.py`**:
  - Extract `ERROR_CATALOG` into `orcia_core/kernel/_error_catalog.py` (`<= 300` L) and add optional `detail_params` formatting in `get_localized_error_text()` and `OrciaDomainError`.
- **Domain Error Catalogs (`*_error_catalog.py`)**:
  - Register `ERR_HELP_ARTICLE_VALIDATION_FAILED`, `ERR_INVALID_MCP_TOKEN_CONFIG`, `ERR_PACK_BUILDER_VALIDATION_FAILED` and split `permissions/_error_catalog.py` / `orchestration/errors.py` / `orchestration/_ai_models_error_catalog.py` / `orchestration/_assistant_turn_error_catalog.py` so every file stays `<= 300` L and every `OrciaDomainError` code has complete jargon-free `fr`/`en` copies.
  - Replace hardcoded French `detail_override` calls with catalog codes or `detail_params`, and convert internal-only diagnostic `ValueError`/`RuntimeError` messages to English.
- **Category D Prompts, Reports, Notifications & Seeds (`*_locales.py` / `*_locale_messages.py`)**:
  - Extract FR/EN user-facing templates into explicit bilingual `fr`/`en` locale bundles (`_accostage_locales.py`, `_provenance_locale_messages.py`, `_outbox_locale_messages.py`, `_agents_outcomes_locales.py`, `_assistant_sanitization_locales.py`, `_llm_adapter_locales.py`, `_help_docs_locales.py`, `_seeds_locales.py`, etc.) defaulting to `"fr"` and switching cleanly on `locale="en"`.
  - Split all touched modules exceeding `300` lines into clean `_*.py` submodules `<= 300` lines preserving `AD-19` `lint-imports` boundaries.
  - Translate any touched/modified docstrings and comments to English-only.

### 2.3 Backend API, Security & Contracts (`apps/api/`, `packages/api-client/`)
- **`apps/api/src/orcia_api/errors/registry.py` & `middleware/trace_and_error.py`**:
  - Register `HelpArticleValidationError`, `InvalidMcpTokenConfigurationError`, and `PackBuilderValidationError` in `DOMAIN_ERROR_CLASSES` and pass `detail_params` into `build_problem_response`.
- **`apps/api/src/orcia_api/routers/*.py` & `dependencies/*.py`**:
  - Resolve `Accept-Language` via `resolve_locale` on user-facing responses/errors, route errors through `OrciaDomainError` or bilingual router message helpers (`*_locale_messages.py`), convert internal diagnostics/OpenAPI metadata to English, and split oversized routers (`pack_builder.py`, `org_units.py`, `_iam_accounts_passwords.py`, `_ontology_promotions_handlers.py`, `workflows.py`, `org_unit_invitations.py`) `<= 300` lines.
- **`apps/api/src/orcia_api/schemas/*.py` & `packages/api-client/`**:
  - Clean French schema defaults, split oversized schemas (`settings_and_studio.py`, `auth_and_org.py`, `blackboard.py`) `<= 300` L preserving re-exports for `SCHEMA_DOMAIN_MODULES`, and run `scripts/export_openapi.py` if OpenAPI metadata changed so `--check` returns `0-diff`.

### 2.4 User Interface & Experience (`apps/web/`, `packages/ui/`)
- No UI component changes expected unless `packages/api-client` OpenAPI default regeneration impacts typecheck (verified by Testing Sub-Agent).

### 2.5 Test Pyramid Impact Analysis (`AD-17` — Layers 1 to 5 + Security, Mandatory)
- **Layer 1a (`tests/unit/`)**:
  - Lock `tests/unit/i18n_backend_audit_baseline.json` (`missingErrorCatalogCodes: []`, `totalPromptDirectiveViolations: 0`, `totalNonCatalogFrenchLiterals: 0`, `nonCatalogFrenchFiles: {}`).
  - Strengthen `tests/unit/test_i18n_backend_catalog_and_english_dev_audit.py` to enforce FR/EN parity on all `*_locales.py` / `*_locale_messages.py` modules.
  - Add `tests/unit/test_story_27_7_bilingual_backend_errors_and_prompts.py` (`<= 300` L) verifying `Accept-Language: fr` vs `Accept-Language: en` on `ERR_HELP_ARTICLE_VALIDATION_FAILED`, `ERR_INVALID_MCP_TOKEN_CONFIG`, `ERR_PACK_BUILDER_VALIDATION_FAILED`, parameterized domain errors, and prompt/seed locale bundles.
- **Layer 1b / Layer 2 / Layer 3 / Layer 4 / Security / Layer 5**:
  - Full cross-layer verification (`tests/unit`, `>= 90%` branch coverage, PG18 integration, `tests/evals`, `tests/security`, `tests/contract`, `pnpm turbo`, Playwright E2E) delegated to the independent Testing Sub-Agent after Coding completes.

---

## 3. Summary of Changes & Results (Post-Implementation)

### 3.1 Created & Modified Files
A total of **`299` files** (`180` modified, `119` created) were touched across the workspace while keeping **all `284` hand-written non-test production files `<= 300` lines** (`orciaSiteManifest.ts` is generated by `pnpm site:sync`):

| Area | Counts | Concise Summary |
| :--- | :--- | :--- |
| `packages/orcia-core` | `138` modified, `98` created | Added `detail_params` interpolation on `OrciaDomainError` and `get_localized_error_text()` (`kernel/errors.py`, `kernel/_error_catalog.py`); registered `ERR_HELP_ARTICLE_VALIDATION_FAILED`, `ERR_INVALID_MCP_TOKEN_CONFIG`, `ERR_PACK_BUILDER_VALIDATION_FAILED` and split oversized error catalogs into `<= 300`-line domain `*_error_catalog.py` modules; extracted bilingual `fr`/`en` bundles (`*_locales.py` / `*_locale_messages.py` defaulting to `"fr"` and resolving `locale="en"` cleanly) across `agents`, `audit_finops`, `bootstrap`, `catalog`, `gates`, `ontology`, `orchestration`, `permissions`, `rag`, and `testing`; split all touched oversized core modules `<= 300` lines while preserving `AD-19` `lint-imports` boundaries; converted internal diagnostics/comments/docstrings to English. |
| `apps/api` | `32` modified, `16` created | Registered `HelpArticleValidationError`, `InvalidMcpTokenConfigurationError`, and `PackBuilderValidationError` in `errors/_registry_classes.py` / `errors/registry.py`; wired `detail_params` and `Accept-Language` resolution in `middleware/trace_and_error.py` (`build_problem_response`); migrated router/dependency errors to `OrciaDomainError` and immutable `MappingProxyType` bilingual router message bundles (`locales/_router_locale_messages.py`, `routers/_assistant_turn_locale_messages.py`); split oversized routers and schemas `<= 300` lines (`_pack_builder_help_routes.py`, `_org_units_*`, `_iam_accounts_*`, `_ontology_promotions_*`, `schemas/settings_and_studio.py`, `auth_and_org.py`, `blackboard.py`). |
| `packages/api-client` & `apps/web` | `2` modified (`openapi.json`, `orciaSiteManifest.ts`) | Regenerated OpenAPI 3.1 contract (`0-diff` on `scripts/export_openapi.py --check`) and synchronized `/showcase` manifest (`pnpm site:sync`). |
| `docs/` | `4` modified, `1` created | Updated `docs/product/capabilities.yaml` (registered `_pack_builder_help_routes.py` under `CAP-034`), `docs/site-catalog/index.html`, `docs/implementation-artifacts/sprint-status.yaml`, `docs/implementation-artifacts/tech-lead-reports/README.md`, and this Tech Lead report. |
| `tests/unit` & `tests/integration` | `4` modified, `4` created | Locked `tests/unit/i18n_backend_audit_baseline.json` to `0` (`missingErrorCatalogCodes: []`, `totalPromptDirectiveViolations: 0`, `totalNonCatalogFrenchLiterals: 0`, `nonCatalogFrenchFiles: {}`); strengthened Gate 4 parity/English-dev audit (`test_i18n_backend_catalog_and_english_dev_audit.py`); added `test_story_27_7_bilingual_backend_errors_and_prompts.py` & `test_story_27_7_locale_bundles_coverage.py`; aligned `test_contextual_help_and_accostage_postgres18.py` (`194` L) + `_contextual_help_accostage_pg18_helpers.py` (`267` L) `workspaces_count` raw SQL filter with `sql_accostage_counts.py#L43-L50`. |

### 3.2 Quantitative Metrics, Coverage & Static Quality
- **Gate 4 (`tests/unit/i18n_backend_audit_baseline.json`)**: `missingErrorCatalogCodes: []` (`3 -> 0`), `totalPromptDirectiveViolations: 0`, `totalNonCatalogFrenchLiterals: 0` (`757 -> 0`), `nonCatalogFrenchFiles: {}` (`153 -> 0`).
- **Scoped Branch Coverage (`>= 90%` required)**: **99%** across `51` Story 27.7 catalog/locale/registry modules (`813` statements, `1` missed, `84` branches, `2` partial; `coverage run --branch` on `21` targeted unit suites, `125 passed`; `.coverage*` cleaned up).
- **Line-Count Guard (`<= 300` lines)**: `284/284` hand-written non-test `.py`/`.ts`/`.tsx`/`.json` files `<= 300` lines (`test_contextual_help_and_accostage_postgres18.py`: `194` L; `_contextual_help_accostage_pg18_helpers.py`: `267` L).
- **Static Quality & Architecture**:
  - `.venv/bin/ruff check . && .venv/bin/ruff format --check .`: `0` issues (`1695 files already formatted`).
  - `.venv/bin/mypy --strict packages/orcia-core packages/orcia-connectors apps/api apps/worker`: `0` errors (`837 source files`).
  - `.venv/bin/lint-imports`: `5 contracts kept, 0 broken` (`880 files, 6306 dependencies`).
  - `lint_spine.py`: `ok: true, 0 findings`.
  - `scripts/export_openapi.py --check`: `0-diff` (exit `0`).
  - `detect-secrets-hook`: `0` findings (exit `0`).
  - `gitnexus_detect_changes({repo: "/home/romain/Documents/Projects/ORCIA", scope: "all"})` (after `npx gitnexus analyze --index-only .` indexing `45,156 nodes | 77,653 edges | 753 clusters | 1540 flows`): `changed_count: 442`, `affected_count: 295`, `changed_files: 180`, `risk_level: "critical"` (expected for cross-cutting `OrciaDomainError` and multi-domain localization).

### 3.3 AD-17 Test Pyramid & Vertical Wiring Verification
- **Layer 1a — Python Unit Tests (`tests/unit/`)**: `.venv/bin/pytest tests/unit --no-cov -q` **PASSED** (`100%` pass, including post-edit re-run of `test_i18n_backend_catalog_and_english_dev_audit.py`).
- **Layer 1b — Frontend TS (`pnpm turbo run lint typecheck test`)**: **PASSED** (`9/9` Turbo tasks; `@orcia/ui` `35` test files / `139` tests, `@orcia/web` `75` test files / `290` tests, `@orcia/api-client` `20` tests).
- **Layer 2 — Vertical Integration `HTTP ➔ PostgreSQL 18 + Redis` (`tests/integration/`, `--no-cov`)**: **11/11 suites PASSED** (`test_composition_root_zero_ram_silo_postgres18.py`, `test_declarative_packs_and_wizards_postgres18.py`, `test_story_11_3_mcp_and_test_bench_postgres18_redis.py`, `test_story_11_4_pack_builder_postgres18_s3.py`, `test_story_17_2_org_units_hierarchy_postgres18.py`, `test_story_17_5_ai_models_hub_postgres18.py`, `test_story_25_5_assistant_chat_only_and_rag_guard_postgres18.py`, `test_story_26_10_multi_worker_sse_stop_recovery_postgres18.py`, and post-fix `test_contextual_help_and_accostage_postgres18.py`).
- **Layer 3 — API Contract (`tests/contract/`, `lint-imports`, `export_openapi.py --check`)**: **PASSED** (`2/2` contract tests + `0-diff` OpenAPI).
- **Layer 4 — AI Orchestration & Golden Evals (`tests/evals/`) & Security (`tests/security/`)**: `.venv/bin/pytest tests/security tests/evals tests/contract --no-cov -v` **PASSED** (`180 passed` in `91.99s`).
- **Layer 5 — Documentation & Showcase Governance**: Verified `scripts/check_implementation_docs.py` and `pnpm site:sync && pnpm site:check`. Full bilingual Playwright Desktop E2E verification (`Gate 1–4` locked at `0`) is covered in Story `27.8`.
