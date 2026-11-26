# Story 31.5 — Pack Composer (`CUSTOM` Drafts), Anti-Hostage Unlink Guard, Dependency Closure Gate & PII/Infra-Scrubbed `.zip` Export

- **Date**: 2026-11-26
- **Story / Sprint Key**: `31-5-pack-composer-anti-hostage-unlink-closure-gate-and-scrubbed-zip-export` (`Epic 31` — Lot 4)
- **Capability(ies)**: `CAP-055`, `CAP-056`, `CAP-082`, `CAP-090`, `CAP-140`, `CAP-200` — classification: `feature`
- **Author / Context**: `bmad-dev-worker` (Coding Worker) — `CUSTOM` draft pack composition (`pack_draft_memberships` with 8 typed `ON DELETE RESTRICT` FKs), anti-hostage entity deletion guard (`409 ERR_ENTITY_REFERENCED_BY_PACK_DRAFT` + `?unlink_from_draft_packs=true` + `audit_ledger` `PACK_DRAFT_MEMBER_UNLINKED_ON_ENTITY_DELETE`), transitive dependency closure gate (`422 ERR_PACK_CLOSURE_INCOMPLETE` + `auto_include_dependencies=true`), structured-only snapshot URI compiler + prose bare-handle linter (`D6.a`, `R1`), connector slot & tier de-binding, single-pass `O(1)` tokenized PII/infra/secret export scanner (`422 ERR_PACK_PII_OR_INFRA_LEAK`, `A3`), deterministic `.zip` + `apm.lock.yaml` export & publish, and OpenAPI 3.1 `@orcia/api-client` regeneration (`0-diff`).
- **Associated Commits**: Worktree `consignes_personnelles_save_button` — Architect Reviewer (`51e21868`, `pro`) `APPROVED` (`0` P0/P1 findings); Testing Verifier (`bmad-dev-worker`) `PASS`.

---

## 1. Needs Analysis & Tech Lead Impact Study (Pre-Implementation)

### 1.1 Context & Problem Statement
- **Current state**:
  - Stories `31.1`–`31.4` delivered v2 PostgreSQL 18 DDL (`declarative_pack_bundles`, `pack_draft_memberships`, `pack_dna_mechanisms`, `workspace_pack_activations`, `workspace_pack_slot_bindings`), `ApmPackCodec`, `PackImportService` + SeaweedFS CAS, qualified `@pack/entity` namespacing, and `WORKSPACE`-only activation + slot pinning in `run_lock_manifests`.
  - However, teams cannot yet compose `CUSTOM` `DRAFT` packs from existing Workspace assets (`catalog_items`, `workflow_definitions_v2`, `vsm_definitions_v2`, `ontology_concepts`, `ontology_relations`, `ontology_axioms`, `pack_dna_mechanisms`, `permission_broker_policies`), nor do entity `DELETE` endpoints guard against `pack_draft_memberships` `ON DELETE RESTRICT` constraints (`409 ERR_ENTITY_REFERENCED_BY_PACK_DRAFT` vs raw `IntegrityError` 500) or support atomic `?unlink_from_draft_packs=true`.
  - Additionally, `POST /api/v1/packs/export/{workspace_id}` only streams raw CAS bytes or a manifest-only fallback without reconstructing PG18 pack/draft members, enforcing transitive dependency closure (`422 ERR_PACK_CLOSURE_INCOMPLETE`), rewriting workspace URIs/connectors into `slot://<key>`, or scanning output files for PII/infra/secret leaks (`422 ERR_PACK_PII_OR_INFRA_LEAK`).
- **Expected behavior**:
  1. Full `/api/v1/packs/composer` CRUD (`POST`, `GET`, `GET /{draft_id}`, `PATCH /{draft_id}`, `PUT /{draft_id}/members`, `DELETE /{draft_id}`, `POST /{draft_id}/publish`, `POST /{draft_id}/export`) plus `POST /api/v1/packs/{bundle_id}/export`, populating all 8 typed `ON DELETE RESTRICT` FK columns and `chk_pack_draft_membership_typed_fk` in `pack_draft_memberships`.
  2. Anti-hostage guard on entity `DELETE` endpoints (`agents`, `skills`, `workflows/v2`, `vsm`, `ontology/concepts|relations|axioms`, `permissions/broker/policies`, `dna-mechanisms`): returns `HTTP 409 ERR_ENTITY_REFERENCED_BY_PACK_DRAFT` with `draft_packs` list when `unlink_from_draft_packs=false`, and atomically unlinks + emits `PACK_DRAFT_MEMBER_UNLINKED_ON_ENTITY_DELETE` to `audit_ledger` + deletes the entity when `?unlink_from_draft_packs=true`. Unhandled `DBAPIError` FK/constraint errors map cleanly to RFC 9457 (never raw 500).
  3. Transitive closure analyzer failing closed (`422 ERR_PACK_CLOSURE_INCOMPLETE`) unless `auto_include_dependencies=true` expands in-scope dependencies; non-mutating bare-handle prose linter; structured-only URI/slot/tier scrubbing + single-pass `O(1)` tokenized leak scanner (`422 ERR_PACK_PII_OR_INFRA_LEAK`); deterministic `.zip` + `apm.lock.yaml` archive bytes round-tripping 100% through `/api/v1/packs/import` into a fresh workspace.
- **Architectural constraints (`ARCHITECTURE-SPINE.md`, `AD-19`, `test_core_domain_isolation.py`)**:
  - `AD-19 Contract 2`: `orcia_core.packs` and `orcia_core.orchestration` sit at the same top core layer and MUST NOT import each other; shared SQL anti-hostage draft membership helpers live in `orcia_core.storage.pack_draft_guard`.
  - Strict `test_core_domain_isolation.py` regex: zero occurrences of `\b(jira|confluence|git_branch|wsjf|rovo|copilot|safe|prd)\b` anywhere inside `packages/orcia-core/src/`.
  - Every new or Story-31.5-modified `.py` file strictly `<= 300` lines (`wc -l`).

### 1.2 Exploration, GitNexus Impact Analysis, Refactoring & Technical Debt
- **GitNexus Impact Analysis (`repo: "/home/romain/.gemini/antigravity/worktrees/ORCIA/consignes_personnelles_save_button"`)**:
  - `gitnexus_context({name: "PackImportService"})`: `PackImportService` is wired in `apps/api/src/orcia_api/dependencies/pack_import_deps.py` and consumed by `apps/api/src/orcia_api/routers/packs.py` and `packages/orcia-core/src/orcia_core/packs/loader.py`; exported `.zip` bundles must decode identically through `ApmPackCodec.decode_zip_bytes` and `PackImportService.import_zip_bytes`.
  - `gitnexus_impact({target: "EntityReferencedByPackDraftError", direction: "upstream"})`: registered in `orcia_core/packs/errors.py`, `_error_catalog.py`, `apps/api/src/orcia_api/errors/_registry_extra_classes.py`, and `trace_and_error.py`.
  - `gitnexus_query("pack draft membership export scrubber closure gate")`: confirmed `pack_draft_memberships` references in `_sql_pack_delete_tx.py` and `_sql_pack_lifecycle.py`, and identified dead unreachable code in `apps/api/src/orcia_api/routers/pack_builder.py` (lines 213–228) after `return ExportFromWorkspaceToPackResponse(...)`.
- **Exploration & Key Schema Invariants**:
  - `20261126_311_declarative_packs_v2.py`: `pack_draft_memberships` has `CHECK (entity_type IN ('AGENT','SKILL','INSTRUCTION','WORKFLOW_V2','VSM_V2','ONTOLOGY_CONCEPT','ONTOLOGY_RELATION','ONTOLOGY_AXIOM','DNA_MECHANISM','POLICY','HELP_ARTICLE'))` and `chk_pack_draft_membership_typed_fk` requiring the corresponding typed UUID FK (`catalog_item_id`, `workflow_v2_id`, `vsm_v2_id`, `ontology_concept_id`, `ontology_relation_id`, `ontology_axiom_id`, `dna_mechanism_id`, `policy_id`).
  - Domain IDs in `catalog_items` (`resource_id`), `workflow_definitions_v2` (`workflow_id`/`slug`), and `vsm_definitions_v2` (`vsm_id`/`slug`) differ from their surrogate `id UUID` PKs; member resolution must resolve surrogate `id::text` cleanly.
  - `ProblemDetails` (`apps/api/src/orcia_api/schemas/problem_details.py`) uses `extra="forbid"`; optional RFC 9457 extension fields (`draft_packs`, `missing_dependencies`, `leak_findings`) will be added cleanly alongside `permission_broker_hint` and `progress_percentage`.
- **Refactoring Opportunities & Technical Debt Control**:
  - Extract shared anti-hostage guard (`check_or_unlink_pack_draft_memberships_conn`) into `packages/orcia-core/src/orcia_core/storage/pack_draft_guard.py` so `orchestration`, `workflows`, `ontology`, `permissions`, and `packs` share one transactional SQL primitive (`DRY`, zero `AD-19` violations).
  - Clean unreachable dead code in `apps/api/src/orcia_api/routers/pack_builder.py` (lines 213–228) while keeping existing `/api/v1/pack-builder/*` endpoints backward-compatible.
  - Keep every module `<= 280–300` lines by splitting composer queries/mutations, closure analyzer, export scrubber, and bundle renderer under `packages/orcia-core/src/orcia_core/packs/_internal/`.

---

## 2. Implementation Plan

### 2.1 Data Schema & Alembic Migrations
- No new Alembic revision required: `20261126_311_declarative_packs_v2.py` already defines `declarative_pack_bundles` v2 (`bundle_kind='CUSTOM'`, `status='DRAFT'`, `source_origin='ORCIA_COMPOSER'`), `pack_draft_memberships` (8 typed `ON DELETE RESTRICT` FKs + `chk_pack_draft_membership_typed_fk`), and `audit_ledger` (`append_pack_audit_event`).

### 2.2 Hexagonal Core, Orchestration & Workers (`packages/orcia-core/`)
- `packages/orcia-core/src/orcia_core/storage/pack_draft_guard.py`: shared transactional anti-hostage helper (`ENTITY_TYPE_TO_FK_COLUMN`, `list_referencing_pack_drafts_conn`, `guard_or_unlink_pack_drafts_conn`) raising `EntityReferencedByPackDraftError` (`draft_packs`) or unlinking rows + appending `PACK_DRAFT_MEMBER_UNLINKED_ON_ENTITY_DELETE` to `audit_ledger`.
- `packages/orcia-core/src/orcia_core/packs/errors.py` & `_error_catalog.py`: enrich `EntityReferencedByPackDraftError` (`draft_packs`), `PackClosureIncompleteError` (`missing_dependencies`), `PackPiiOrInfraLeakError` (`leak_findings`), and bilingual FR/EN error messages.
- `packages/orcia-core/src/orcia_core/packs/composer_models.py`: pure Pydantic domain models for draft composition, resolved members, closure diagnostics, prose lint warnings, and export results.
- `packages/orcia-core/src/orcia_core/packs/_internal/_sql_pack_composer_targets.py` & `_sql_pack_composer.py`: CRUD for `CUSTOM` `DRAFT` packs, surrogate UUID FK resolution across all 8 target tables with workspace isolation checks, and atomic `pack_draft_memberships` replacement.
- `packages/orcia-core/src/orcia_core/packs/_internal/_pack_closure_analyzer.py` & `_pack_closure_helpers.py`: transitive dependency BFS (`Workflow -> Agent/Skill/VSM/DNA/Axiom/Slot`, `VSM -> Workflow/Agent`, `Agent -> Skill/Concept/Slot`, `Relation/Axiom -> Concept`), `auto_include_dependencies` expansion, `ACTIVE` readiness gate on publish, and non-mutating bare-handle prose linter.
- `packages/orcia-core/src/orcia_core/packs/_internal/_pack_export_scrubber.py` & `_pack_export_renderer.py`: structured-only URI/slot/tier rewriting, `LoadedPackBundleV2` reconstruction from PG18 (`DRAFT` memberships or `PUBLISHED`/`SYSTEM` `pack_bundle_id` rows), tenant DB `frozenset` loader, single-pass `O(1)` tokenized PII/infra/secret leak scanner (`422 ERR_PACK_PII_OR_INFRA_LEAK`), and deterministic `.zip` + `apm.lock.yaml` emission.
- `packages/orcia-core/src/orcia_core/packs/composer_service.py`: Composition-Root service (`PackComposerService`) orchestrating draft CRUD, closure check/expansion, publish (including CAS upload & materialization), and scrubbed `.zip` export.
- `packages/orcia-core/src/orcia_core/orchestration/_internal/sql_agents_and_skills.py` (+ `workflows/_internal/sql_vsm_v2.py` / `sql_workflows_v2.py`): wire `guard_or_unlink_pack_drafts_conn` into PG18 delete paths cleanly.

### 2.3 Backend API, Security & Contracts (`apps/api/`, `packages/api-client/`)
- `apps/api/src/orcia_api/schemas/problem_details.py` & `middleware/trace_and_error.py`: add optional RFC 9457 extension fields (`draft_packs`, `missing_dependencies`, `leak_findings`) and `DBAPIError` / `IntegrityError` handler so FK/constraint errors return structured `409`/`422` RFC 9457 envelopes (never raw 500).
- `apps/api/src/orcia_api/schemas/_pack_composer.py` & `schemas/packs.py`: Pydantic v2 OpenAPI 3.1 schemas for composer CRUD, members, closure report, publish, export, and guarded entity delete responses.
- `apps/api/src/orcia_api/dependencies/pack_import_deps.py` & `__init__.py`: Composition-Root `get_pack_composer_service(request)` DI provider.
- `apps/api/src/orcia_api/routers/pack_composer.py` & `_pack_composer_helpers.py` (+ `packs.py`, `main.py`): mount `/api/v1/packs/composer` CRUD/members/publish/export endpoints and `POST /api/v1/packs/{bundle_id}/export` with `ScopeAccessGuard` + `READ_ONLY_OBSERVER` `403`.
- Wire `?unlink_from_draft_packs=bool` anti-hostage guard onto `DELETE` endpoints across `agents_and_skills.py`, `_agents_and_skills_skills_routes.py`, `workflows.py` (`/workflows/v2/{workflow_id}`, `/vsm/{vsm_id}`), `ontology_promotions.py` (`/concepts/{id}`, `/relations/{id}`, `/axioms/{id}`), `permission_broker.py` (`/policies/{id}`), and `pack_composer.py` (`/dna-mechanisms/{id}`).
- Clean unreachable dead code in `apps/api/src/orcia_api/routers/pack_builder.py`.
- Regenerate `packages/api-client/openapi.json` & `@orcia/api-client` TS SDK (`0-diff` verified via `scripts/export_openapi.py --check`).

### 2.4 User Interface & Experience (`apps/web/`, `packages/ui/`)
- Out of scope for Story 31.5 (Direction C UI is owned by Story 31.6); only `@orcia/api-client` OpenAPI 3.1 SDK regeneration is performed here.

### 2.5 Test Pyramid Impact Analysis (`AD-17`)
- **Layer 1a (`tests/unit/packs/`)**: unit tests (`<= 300` L each) covering `PackComposerService`, 8 typed FK target resolution, anti-hostage `409` + `?unlink_from_draft_packs=true` + `audit_ledger`, transitive closure & `auto_include_dependencies`, `O(1)` PII/infra/secret export scrubber, deterministic `.zip` + `apm.lock.yaml`, `pack_composer.py` & delete router guards, `DBAPIError` handler, and `test_core_domain_isolation.py` (`>= 90%` scoped `--branch` coverage).
- **Layer 2 (`tests/integration/test_story_31_5_pack_composer_and_export_postgres18.py`)**: real `testcontainers` PG18 + SeaweedFS S3 `create_app()` vertical test (`dependency_overrides == {}`) verifying draft CRUD + all 8 typed FK SQL `SELECT` checks, anti-hostage `409` + `?unlink_from_draft_packs=true` + `audit_ledger` `PACK_DRAFT_MEMBER_UNLINKED_ON_ENTITY_DELETE` SQL check, `422 ERR_PACK_CLOSURE_INCOMPLETE` + `auto_include_dependencies=true`, `422 ERR_PACK_PII_OR_INFRA_LEAK`, deterministic scrubbed `.zip` + `apm.lock.yaml` export -> fresh-workspace `/api/v1/packs/import` -> slot binding -> activation round-trip, and `403 ERR_OBSERVER_MODE_READ_ONLY` / cross-workspace `403`.
- **Layer 3 (`scripts/export_openapi.py --check`, `lint-imports`, `@orcia/api-client`)**: `0-diff` OpenAPI 3.1 SDK, `tsc --noEmit` & `vitest`, and `5/5` `import-linter` contracts.

---

## 3. Summary of Changes & Results

### 3.1 Created & Modified Files Inventory
- **Hexagonal Core (`packages/orcia-core/`)**:
  - Created (`22` modules, all non-barrel `.py` `<= 278` L): `storage/pack_draft_guard.py` (`243` L), `storage/entity_delete_tx.py` (`278` L), `orchestration/_internal/_sql_agents_delete.py` (`242` L), `packs/composer_models.py` (`124` L), `packs/composer_service.py` (`253` L), `packs/_internal/_sql_pack_composer*.py` (`7` modules: `142`–`262` L), `packs/_internal/_sql_pack_publish_export.py` (`253` L), `packs/_internal/_pack_closure_analyzer.py` (`265` L), `packs/_internal/_pack_closure_helpers.py` (`234` L), `packs/_internal/_pack_closure_lint.py` (`121` L), `packs/_internal/_pack_export_*.py` (`7` modules: `115`–`256` L).
  - Modified (`6` modules): `kernel/errors.py`, `packs/__init__.py`, `packs/errors.py`, `packs/_error_catalog.py`, `packs/_internal/_apm_entry_router.py`, `orchestration/__init__.py` (barrel re-exports), `orchestration/_internal/sql_agents_and_skills.py`.
- **FastAPI Backend & OpenAPI SDK (`apps/api/`, `packages/api-client/`)**:
  - Created (`8` modules, all `<= 258` L): `routers/pack_composer.py` (`258` L), `routers/_pack_composer_publish_routes.py` (`138` L), `routers/_pack_composer_helpers.py` (`219` L), `routers/_packs_export_legacy_route.py` (`131` L), `routers/_entity_delete_rbac.py` (`250` L), `routers/_catalog_delete_routes.py` (`65` L), `routers/_workflows_delete_routes.py` (`111` L), `schemas/_pack_composer.py` (`223` L).
  - Modified (`15` backend + `3` SDK files): `main.py`, `dependencies/__init__.py`, `dependencies/pack_import_deps.py`, `middleware/trace_and_error.py`, `schemas/{agents_and_skills,packs,problem_details}.py`, `routers/{agents_and_skills,_agents_and_skills_skills_routes,ontology_promotions,pack_builder,packs,permission_broker,portal_and_help,workflows}.py`, `packages/api-client/{openapi.json,src/generated/packs.ts,src/generated/schema.ts}`.
- **Tests (`tests/unit/packs/`, `tests/integration/`)**:
  - Created (`19` files, all `<= 289` L): `15` unit suites (`test_story_31_5_*.py`), `2` PG18+S3 fixtures (`_story_31_5_fixture*.py`), and `2` real `create_app()` PG18+SeaweedFS S3 integration suites (`test_story_31_5_pack_composer_and_export_postgres18.py` `284` L, `test_story_31_5_rbac_and_roundtrip_postgres18.py` `268` L).
  - Modified (`4` test files): `tests/unit/packs/_fake_sql_engine.py`, `test_story_31_2_branch_coverage.py`, `test_story_24_3_mcp_bench_audit_and_redis.py`, `tests/integration/test_declarative_packs_and_wizards_postgres18.py`.
- **Capabilities & Living Site**: Updated `docs/product/capabilities.yaml` (`CAP-055`, `CAP-056`, `CAP-082`, `CAP-090`, `CAP-140`, `CAP-200`, `verified_at: "2026-11-26"`), `docs/implementation-artifacts/sprint-status.yaml` (`31-5: done`), `docs/implementation-artifacts/tech-lead-reports/README.md`, and regenerated `orciaSiteManifest.ts` / `docs/site-catalog/index.html` (`66/66` live capabilities).

### 3.2 Quantitative Metrics & `AD-17` 5-Layer Verification
- **Line-Count & Security Audit**:
  - Every new/modified non-barrel Story 31.5 production `.py` file is `<= 299` lines (`max: 299` L in `apps/api/src/orcia_api/routers/agents_and_skills.py`); every new `.ts` file in `packages/api-client/src/generated/` is auto-generated (`packs.ts` `42` L, `schema.ts` `7,936` L).
  - `.venv/bin/detect-secrets-hook --baseline .secrets.baseline`: **PASS** (`exit 0`, zero potential secrets).
- **Static Quality, Strict Typing, Boundaries & OpenAPI**:
  - `.venv/bin/ruff check .`: **PASS** (`All checks passed!`).
  - `.venv/bin/ruff format --check .`: **PASS** (`1,915 files already formatted`).
  - `.venv/bin/mypy --strict packages/orcia-core packages/orcia-connectors apps/api apps/worker`: **PASS** (`Success: no issues found in 948 source files`).
  - `.venv/bin/lint-imports`: **PASS** (`5 kept, 0 broken` across `907` files and `6,581` dependencies).
  - `lint_spine.py`: **PASS** (`0` findings).
  - `scripts/export_openapi.py --check`: **PASS** (`0-diff`).
- **Scoped `--branch` Coverage (`>= 90%`)**:
  - `coverage run --branch` across `tests/unit/packs/` + `tests/unit/core/test_core_domain_isolation.py` (`136` tests): **`94%` TOTAL** (`2,095` Stmts, `64` Miss, `790` Branch, `110` BrPart across all `31` Story 31.5 modules; all pack/storage/API modules `90%`–`100%`, zero `.coverage*` leftover).
- **Full `AD-17` Test Pyramid**:
  - **Layer 1 (Full Unit, Post-Sync)**: `.venv/bin/pytest --no-cov -q tests/unit` $\rightarrow$ **`1,296 passed`** (`0` failures, incl. AST, i18n Gate 4, OpenAPI, capabilities registry, and site sync).
  - **Layer 2 (Real `testcontainers` PG18 + Redis 7.4 + SeaweedFS S3, `--no-cov`)**:
    - Batch 1 (`test_story_31_5_*`, `31_4_*`, `31_3_*`, `31_2_*`): **`6 passed` in `118.45s`**.
    - Batch 2 (`test_story_11_4_*`, `test_declarative_packs_and_wizards_*`, `30_5_*`, `20_2_*`, `test_http_vertical_day0_and_agents_postgres18.py`): **`9 passed` in `83.76s`**.
  - **Layer 3 (`@orcia/*` Turbo + OpenAPI SDK)**: `pnpm turbo run lint typecheck test --concurrency=2` $\rightarrow$ **`9/9` tasks passed** (`@orcia/ui` `40` files/`154` tests, `@orcia/api-client` `3` files/`20` tests, `@orcia/web` `96` files/`370` tests = `544` JS/TS tests).
  - **Layer 4 (`evals`, `security`, `contract`)**: `.venv/bin/pytest --no-cov -q tests/evals tests/security tests/contract` $\rightarrow$ **`193 passed`**.
- **Architect Review**: `bmad-architect-worker` (`51e21868`, `pro`) returned **`APPROVED`** (`0` P0/P1 findings) on both initial implementation and post-regression fixes.
- **GitNexus Delta (`npx gitnexus analyze --index-only .` + `gitnexus_detect_changes`)**:
  - Index refreshed: **`50,631` nodes | `218,736` edges | `849` clusters | `1,527` flows**.
  - `gitnexus_detect_changes({scope: "all"})`: `changed_count: 24`, `changed_files: 34`, `affected_count: 1,527`, `risk_level: critical` (due to shared `ProblemDetails`, `orcia_api/main.py`, `agents_and_skills`, `workflows`, `packs` delete/export hubs).
- **Living Site & Documentation Gates**:
  - `sync_site_catalog.py --check`: **`66/66` live capabilities**, `252` reports, `29` routes, `134` UI primitives in sync.
  - `check_implementation_docs.py`: **PASS**.
