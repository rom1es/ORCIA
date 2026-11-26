# Story 31.2 — Transactional Pack Import Service, Day-0 System Pack Seeding & Purge of Disk/TS Pack Hardcoding

- **Date**: 2026-11-26
- **Story / Sprint Key**: `31-2-transactional-pack-import-day0-seed-and-purge-disk-ts-hardcoding` (`Epic 31` / `Lot 2`)
- **Capability(ies)**: `CAP-055`, `CAP-056`, `CAP-082`, `CAP-090`, `CAP-140`, `CAP-200` — classification: `feature`
- **Author / Context**: Implement `PackImportService` (SeaweedFS CAS upload + atomic PostgreSQL 18 upsert/version conflict guard + transactional materialization of all pack constituent entities + guarded `delete_bundle`), cut over Day-0 startup & `09_reset_db_first_boot.py` to seed `packs/sdlc` & `packs/orcia-docs` via `PackImportService`, eliminate runtime disk reads in `packs.py` / `_workflows_helpers.py`, expose `GET /api/v1/packs`, `POST /api/v1/packs/import`, `DELETE /api/v1/packs/{bundle_id}` with OpenAPI SDK `0-diff`, and purge hardcoded TypeScript pack catalogs (`packAgentsCatalog*.ts`, `processStudioV2StructuralPacks.ts`, `settingsPacksPresets.ts`, `sdlcDefaults` in `assistantAutocompleteHelpers.ts`) (`D1`, `D2`, `D6`, `R1`, `AD-19`, `AD-20`, `AD-21`, `AD-23`).
- **Associated Commits**: *(pending implementation)*

---

## 1. Needs Analysis & Tech Lead Impact Study (Pre-Implementation)

### 1.1 Context & Problem Statement
- **Current silos (`D1`)**:
  1. `apps/api/src/orcia_api/routers/packs.py` (`load_declarative_pack_bundles`) and `apps/api/src/orcia_api/routers/_workflows_helpers.py` (`load_workflows_store`, `load_vsm_definitions_from_pg18`) still call `DeclarativePackLoader(resolve_default_packs_root()).load_all_packs()` on every HTTP request, violating `readOnlyRootFilesystem` / single PG18 source of truth (`AD-23`).
  2. `packages/orcia-core/src/orcia_core/packs/_internal/sql_declarative_packs.py` only persists the `declarative_pack_bundles` header and `pack_dna_mechanisms`, without transactionally materializing `agents`, `skills`, `instructions`, `workflows_v2`, `vsm_v2`, `ontology_terms`, `policies`, and `help` into PostgreSQL 18 or storing the raw `.zip` archive in SeaweedFS CAS.
  3. Frontend `apps/web/src/features/catalog/packAgentsCatalog.ts` and `packAgentsCatalogData.ts` hardcode `PACK_AGENTS_BY_PACK_KEY`, `PACK_SKILLS_BY_PACK_KEY`, and synthesize fallback `"Expert ${key}"` items client-side (`mergeManagedStateWithActivePacks`), while `processStudioV2StructuralPacks.ts`, `settingsPacksPresets.ts`, and `assistantAutocompleteHelpers.ts` (`sdlcDefaults`) duplicate pack metadata in TypeScript.
  4. Standalone SQL queries on the 7 child tables (`sql_ontology_queries.py`, `_sql_permission_broker_queries.py`, `sql_contextual_help.py`, `sql_agents_and_skills.py`) lack `AND pack_bundle_id IS NULL` filters on lookup/update/delete statements, creating collision risk once pack-owned rows (`pack_bundle_id IS NOT NULL`) coexist in those tables.
- **Expected behavior**:
  - `PackImportService` atomically validates via `ApmPackCodec`, stores archive bytes in SeaweedFS CAS (`packs/{slug}/{version}/{archive_sha256}.zip`), checks `(scope_type, scope_id, slug, version)` (`200` idempotent upsert on matching `archive_sha256`, `409 ERR_PACK_VERSION_CONFLICT` on mismatch unless `replace_draft=True` on `CUSTOM` + `DRAFT`, or `allow_system_kind=True` bootstrap), and materializes all constituent entities with `pack_bundle_id = bundle.id` inside a single PostgreSQL 18 transaction.
  - `delete_bundle` blocks `SYSTEM` packs (`403`), active workspace activations or `run_lock_manifests`-pinned packs (`409 ERR_RESOURCE_PINNED_BY_ACTIVE_RUNS`), and cross-draft memberships (`409 ERR_ENTITY_REFERENCED_BY_PACK_DRAFT`), deletes inactive activation rows and the bundle (`ON DELETE CASCADE`), and appends an `audit_ledger` entry.
  - Day-0 startup (`_lifespan_infra.py`) and `09_reset_db_first_boot.py` seed `packs/sdlc` & `packs/orcia-docs` via `PackImportService` (`bundle_kind='SYSTEM'`, `scope_type='GLOBAL'`, `scope_id='global'`), and all API routes (`packs.py`, `_workflows_helpers.py`) and `apps/web` catalogs read exclusively from PostgreSQL 18.
- **Architectural constraints (`ARCHITECTURE-SPINE.md`, `AD-19`, `AD-21`)**:
  - `AD-19` (`lint-imports` 5/5): `orcia_core.packs` may import `orcia_core.{catalog,ontology,workflows,gates,permissions,storage,kernel}`, while `orcia_core.bootstrap` must not import `orcia_core.packs` (same layer).
  - `TID251`: No synchronous `httpx.Client`, `requests`, or `urllib.request` in `apps/api/src/orcia_api/routers/`; SeaweedFS CAS port in `orcia_core.packs` will use async `httpx.AsyncClient`.
  - Every modified/created source and test file must remain `<= 300` lines (`wc -l`).
  - Zero raw `fetch()` in `apps/web`, `0-diff` OpenAPI SDK regeneration, and 100% bilingual `fr`/`en` RFC 9457 Problem Details + UI labels.

### 1.2 Exploration, GitNexus Impact Analysis, Refactoring & Technical Debt
- **GitNexus Impact Analysis (`gitnexus_query`, `gitnexus_context`, `gitnexus_impact` on `repo: "ORCIA"`)**:
  - `SqlPackBundleV2Repository` (`packages/orcia-core/src/orcia_core/packs/_internal/sql_declarative_packs.py`): Referenced in `apps/api/src/orcia_api/dependencies/_lifespan_services.py`. Adding transactional import materialization on top of `declarative_pack_bundles` keeps the existing repository contract intact.
  - `delete_pack_bundle_sql` (`packages/orcia-core/src/orcia_core/packs/_internal/_sql_pack_lifecycle.py`): GitNexus `impact({direction: "upstream"})` reports `CRITICAL` blast radius (`322` transitive dependents across `198` execution flows / `20` modules) because it touches `workflow_runs`, `run_lock_manifests`, `catalog_items`, and `workflow_definitions_v2`. Guarding `SYSTEM` packs, active runs, cross-draft references, and `audit_ledger` insertion requires deterministic testing against real PG18.
  - `PACK_AGENTS_BY_PACK_KEY` (`apps/web/src/features/catalog/packAgentsCatalogData.ts`): Direct consumers in `packAgentsCatalog.ts`, `useManagedAgentsAndSkills.ts`, `useManagedAgentActions.ts`, `useManagedAgentGovernanceActions.ts`, `useManagedAgentExecutionActions.ts`, `managedAgentsHelpers.ts`, and `features/catalog/index.tsx`. Removing `packAgentsCatalog*.ts` requires migrating `slugifyIdentifier`, `CachedAgentsAndSkillsState` re-exports, and removing `mergeManagedStateWithActivePacks` / `PACK_SKILLS_BY_PACK_KEY` fallbacks.
- **Exploration & Key Metrics**:
  - `20261126_311_declarative_packs_v2.py` already established `pack_bundle_id UUID NULL REFERENCES declarative_pack_bundles(id) ON DELETE CASCADE` and split partial unique indexes (`WHERE pack_bundle_id IS NULL` vs `WHERE pack_bundle_id IS NOT NULL`) on all 7 child tables (`catalog_items`, `workflow_definitions_v2`, `vsm_definitions_v2`, `ontology_concepts`, `ontology_relations`, `ontology_axioms`, `permission_broker_policies`), plus `pack_dna_mechanisms`, `pack_draft_memberships`, `workspace_pack_activations`, and `workspace_pack_slot_bindings`.
  - `ontology_concepts.level` CHECK constraint (`20261117_2002`) allows `'1_ENTERPRISE'`, `'2_DOMAIN'`, `'3_TEAM'`, `'3_WORKSPACE'`, `'4_WORKSPACE'`, `'4_RUN_EPHEMERAL'`. Pack-imported glossary concepts must map to `'2_DOMAIN'` (or `'1_ENTERPRISE'` for `GLOBAL` system packs) with `scope_id = pack_slug`.
  - `permission_broker_policies.connector_scheme` CHECK constraint (`0004`) allows `'git'`, `'jira'`, `'confluence'`, `'db'`, `'nexus'`, `'mcp'`.
  - `catalog_items.resource_type` CHECK constraint (`0003`) allows `'workflow'`, `'agent'`, `'skill'`, `'template'`, `'datasource'` (plus `'help'` / `item_type = 'HELP_ARTICLE'` added in `0024` / `20261117_0702`).
  - Existing tests `test_declarative_packs_loading.py` and `test_story_16_1_sources_surgical_api.py` expect `packs/sdlc/pack.yaml`, `packs/sdlc/agents/*.md`, and `packs/sdlc/skills/*.md` to remain readable by `DeclarativePackLoader` and surgical line reader; adding `apm.yml` + `x-orcia:` YAML frontmatter to `packs/sdlc` and `packs/orcia-docs` while preserving `pack.yaml` satisfies both `ApmPackCodec` (`ACTIVE` classification) and legacy unit/integration tests.
- **Refactoring Opportunities & Emerging Technical Debt Mitigation**:
  - Split `PackImportService` cleanly into focused `<= 300`-line modules under `packages/orcia-core/src/orcia_core/packs/`:
    - `ports.py`: add `PackCasStoragePort` (`put_archive_zip`, `get_archive_zip`, `head_archive_zip`).
    - `_internal/seaweedfs_pack_cas.py`: async SeaweedFS S3 v4 adapter (`httpx.AsyncClient` reusing `build_s3_sigv4_headers` from `catalog/_internal/seaweedfs_adapter.py`).
    - `_internal/_sql_pack_entity_materializer.py`: atomic `AsyncConnection` materialization helpers for `catalog_items` (`USER_AGENT`, `USER_SKILL`, `INSTRUCTION`, `HELP_ARTICLE`), `workflow_definitions_v2`, `vsm_definitions_v2`, `ontology_concepts`/`relations`/`axioms`, `pack_dna_mechanisms`, `permission_broker_policies`, and `audit_ledger`.
    - `_internal/_sql_pack_import_tx.py`: transactional header upsert, `(scope_type, scope_id, slug, version)` SHA-256 conflict detection, `replace_draft` / `allow_system_kind` checks, and `delete_bundle` `SYSTEM`/pinning/cross-draft guards + `audit_ledger`.
    - `import_service.py`: `PackImportService` facade (`import_zip_bytes`, `import_directory`, `delete_bundle`, `list_bundles`, `get_bundle`).
  - Extract `apps/api/src/orcia_api/schemas/packs.py` (`<= 300` L) for `GET /api/v1/packs`, `POST /api/v1/packs/import`, `DELETE /api/v1/packs/{bundle_id}` transport schemas, keeping `process_studio_v2.py` under `300` L.
  - Extract shared `slugifyIdentifier` + `CachedAgentsAndSkillsState` re-exports in `apps/web/src/features/catalog/managedAgentsHelpers.ts` so `packAgentsCatalog.ts` and `packAgentsCatalogData.ts` can be deleted cleanly without duplicating helper logic.

---

## 2. Implementation Plan

### 2.1 Data Schema & Alembic Migrations
- No new Alembic revision needed (`20261126_311_declarative_packs_v2.py` already created all v2 tables, `pack_bundle_id` FKs with `ON DELETE CASCADE`, and partial unique indexes `WHERE pack_bundle_id IS NULL` / `WHERE pack_bundle_id IS NOT NULL`).
- Update standalone SQL queries on the 7 child tables to include `AND pack_bundle_id IS NULL` where standalone rows are queried/updated/deleted:
  - `packages/orcia-core/src/orcia_core/ontology/_internal/sql_ontology_queries.py`: `SQL_FIND_CONCEPT_FOR_UPSERT`, `SQL_SELECT_COLLIDING_DEF`.
  - `packages/orcia-core/src/orcia_core/permissions/_internal/_sql_permission_broker_queries.py`: `upsert_policy_on_conn` lookup query.
  - `packages/orcia-core/src/orcia_core/catalog/_internal/sql_contextual_help.py`: `publish_hot_help_article_sql`, `rollback_help_article_sql`.
  - `packages/orcia-core/src/orcia_core/orchestration/_internal/sql_agents_and_skills.py`: `_delete_catalog_item`.
- Ensure `packs/sdlc/` and `packs/orcia-docs/` include `apm.yml` (`bundle_kind: SYSTEM`, `scope_type: GLOBAL`, `scope_id: global`, `x-orcia.connector_slots`, `x-orcia.quick_actions`) and `x-orcia:` YAML frontmatter in `agents/*.md` and `skills/*.md` (so all Day-0 agents/skills materialize with `lifecycle_status='ACTIVE'`) while preserving `pack.yaml` compatibility.

### 2.2 Hexagonal Core, Orchestration & Workers (`packages/orcia-core/`, `infra/scripts/maintenance/`)
- `packages/orcia-core/src/orcia_core/packs/ports.py`: Add `PackCasStoragePort` (`async put_archive_zip`, `async get_archive_zip`, `async head_archive_zip`).
- `packages/orcia-core/src/orcia_core/packs/errors.py` & `_error_catalog.py`: Ensure `PackSystemDeleteForbiddenError` (`403 ERR_PACK_SYSTEM_DELETE_FORBIDDEN`) or `ObserverModeReadOnlyError` / `ValidationDomainError` bilingual RFC 9457 entries exist cleanly.
- `packages/orcia-core/src/orcia_core/packs/_internal/seaweedfs_pack_cas.py`: Async `SeaweedFsPackCasAdapter` implementing `PackCasStoragePort` using `httpx.AsyncClient` and `build_s3_sigv4_headers`, storing archives at `packs/{slug}/{version}/{archive_sha256}.zip` (no `TID251` sync client).
- `packages/orcia-core/src/orcia_core/packs/_internal/_sql_pack_entity_materializer.py`: Single-connection (`AsyncConnection`) upserts/replacements of pack-owned rows (`pack_bundle_id = bundle_id`) across `catalog_items`, `workflow_definitions_v2`, `vsm_definitions_v2`, `ontology_concepts`/`ontology_relations`/`ontology_axioms`, `pack_dna_mechanisms`, and `permission_broker_policies`.
- `packages/orcia-core/src/orcia_core/packs/_internal/_sql_pack_import_tx.py`: Single PG18 transaction header upsert + SHA-256 conflict guard + child materialization + `delete_bundle` (`SYSTEM` check, `run_lock_manifests` / `workspace_pack_activations` pinning check, `pack_draft_memberships` cross-draft check, `audit_ledger` append).
- `packages/orcia-core/src/orcia_core/packs/import_service.py`: `PackImportService` (`import_zip_bytes`, `import_directory`, `delete_bundle`, `list_bundles`, `get_bundle`).
- `packages/orcia-core/src/orcia_core/bootstrap/seeder.py` & `infra/scripts/maintenance/09_reset_db_first_boot.py`: Route Day-0 system pack seeding through `PackImportService.import_directory(..., allow_system_kind=True)` on `packs/sdlc` and `packs/orcia-docs`.

### 2.3 Backend API, Security & Contracts (`apps/api/`, `packages/api-client/`)
- `apps/api/src/orcia_api/dependencies/_lifespan_infra.py`, `_lifespan_services.py`, `workspace_and_packs.py`, `__init__.py`: Wire `SeaweedFsPackCasAdapter` (when `SEAWEEDFS_ENDPOINT_URL` / `S3_ENDPOINT_URL` configured) and `PackImportService` on `app.state` in the Composition Root, and run Day-0 `PackImportService.import_directory` in `startup_declarative_packs_and_dbos`.
- `apps/api/src/orcia_api/schemas/packs.py`: Request/Response transport schemas (`PackImportRequest`, `PackImportResponse`, `PackDeleteResponse`, `PackBundleV2SummaryResponse`, `DeclarativePacksListResponse`, etc.) exported in `scripts/export_openapi.py` (`SCHEMA_DOMAIN_MODULES`).
- `apps/api/src/orcia_api/routers/packs.py` & `routers/_workflows_helpers.py`:
  - Eliminate all runtime calls to `DeclarativePackLoader().load_all_packs()` in HTTP request handlers.
  - `GET /api/v1/packs` reads bundles + entity counts + declared slots from PostgreSQL 18 (`SqlPackBundleV2Repository`) and evaluates connector health against PG18 connectors.
  - `POST /api/v1/packs/import` accepts multipart `.zip` upload OR JSON `{zip_base64, scope_type, scope_id, replace_draft}`, enforces `ScopeAccessGuard` / non-observer (`403 ERR_OBSERVER_MODE_READ_ONLY`), rejects `SYSTEM`/`GLOBAL` escalation, invokes `PackImportService.import_zip_bytes`.
  - `DELETE /api/v1/packs/{bundle_id}` enforces `ScopeAccessGuard` / non-observer (`403`), rejects `SYSTEM` pack deletion (`403`), and invokes `PackImportService.delete_bundle` (`409 ERR_RESOURCE_PINNED_BY_ACTIVE_RUNS` / `409 ERR_ENTITY_REFERENCED_BY_PACK_DRAFT`).
  - `_workflows_helpers.py` (`load_workflows_store`, `load_vsm_definitions_from_pg18`, `get_vsm_definition_from_pg18`) reads strictly from PostgreSQL 18 (`SqlWorkflowDefinitionsV2Store`, `SqlVsmDefinitionsV2Store`).
- `packages/api-client/`: Regenerate OpenAPI 3.1 schema + TS client (`scripts/export_openapi.py` + domain wrappers in `packages/api-client/src/domains/workflowsV2.ts`), verifying `scripts/export_openapi.py --check` (`0-diff`).

### 2.4 User Interface & Experience (`apps/web/`, `packages/ui/`)
- Delete `apps/web/src/features/catalog/packAgentsCatalog.ts` and `apps/web/src/features/catalog/packAgentsCatalogData.ts`.
- Refactor `useManagedAgentsAndSkills.ts`, `useManagedAgentActions.ts`, `useManagedAgentGovernanceActions.ts`, `useManagedAgentExecutionActions.ts`, `managedAgentsHelpers.ts`, and `features/catalog/index.tsx` to rely exclusively on backend PG18 `agents-and-skills` & `packs` API responses via `@orcia/api-client` (zero client-side `"Expert ${key}"` synthesis).
- Refactor `processStudioV2StructuralPacks.ts`, `processStudioV2Data.ts`, `useProcessesHubData.ts`, `SettingsPacksSection.tsx` / `settingsPacksPresets.ts`, and `assistantAutocompleteHelpers.ts` so pack/workflow/VSM/autocomplete data hydrates from `@orcia/api-client` (with empty arrays on initial load and real loading/error states rather than hardcoded TS pack catalogs).
- Update `apps/web/src/__tests__/setup/` mock handlers (`vitestPacksAndWizardsMockHandlers.ts`, `workspacesAndCatalogMockHandlers.ts`, `mockBackendState.ts`) and impacted frontend tests so Vitest runs truthfully against the OpenAPI contract.

### 2.5 Test Pyramid Impact Analysis (`AD-17` — Layers 1 to 5 + Security, Mandatory)
- **Layer 1a (`tests/unit/packs/test_story_31_2_*.py`) & Layer 1b (`Vitest`)**:
  - Unit tests (`>= 90%` branch coverage on new `packs` import service modules using an `InMemoryPackCasStorage` fake under `tests/unit/fakes/`): archive validation, idempotent re-import, `409 ERR_PACK_VERSION_CONFLICT`, `replace_draft=True` on `CUSTOM` `DRAFT`, `allow_system_kind=False` rejection, `delete_bundle` `SYSTEM`/`409` pin/draft guards.
  - Updated Vitest tests (`story-30-5-agent-lifecycle-and-errors.test.tsx`, `story-27-5-bilingual-process-studio-and-vsm.test.tsx`, `epics-14-15-process-studio-v2-and-declarative-packs.test.tsx`) confirming `packAgentsCatalog*.ts` absence and backend-hydrated pack/agent/VSM rendering.
- **Layer 2 (`tests/integration/test_story_31_2_pack_import_and_day0_postgres18_s3.py`)**:
  - Real `create_app()` + `testcontainers` PostgreSQL 18 + SeaweedFS S3 (`--no-cov`, zero `dependency_overrides`): Day-0 boot seeding of `packs/sdlc` & `packs/orcia-docs`, `GET /api/v1/packs`, `GET /api/v1/agents-and-skills`, `POST /api/v1/packs/import` (zip + S3 CAS verification + PG18 `SELECT` across child tables), `409 ERR_PACK_VERSION_CONFLICT`, `DELETE /api/v1/packs/{bundle_id}` cascade & `409 ERR_RESOURCE_PINNED_BY_ACTIVE_RUNS`, and `09_reset_db_first_boot.py --apply` re-seeding verification.
- **Layer 3 (Contracts & Boundaries)**: `scripts/export_openapi.py --check` (`0-diff`), `lint-imports` (`5/5`), `mypy --strict`, `ruff check` & `ruff format --check`, `pnpm --filter @orcia/api-client test`, `pnpm --filter @orcia/web typecheck`.
- **Layer 4 (`tests/evals/`)**: N/A for new eval datasets (existing deterministic workflow/agent tests preserved).
- **Security**: `403 ERR_OBSERVER_MODE_READ_ONLY` on `POST /api/v1/packs/import` & `DELETE /api/v1/packs/{bundle_id}`, `403` on `SYSTEM`/`GLOBAL` escalation & `SYSTEM` deletion, `422 ERR_PACK_EXECUTABLE_HOOK_FORBIDDEN` / zip-slip rejection on upload.
- **Layer 5 (Playwright E2E)**: Covered at full `AD-17` gate by Testing Verifier.

---

## 3. Summary of Changes & Results (Post-Implementation)

### 3.1 Created, Modified & Deleted Files
- **Hexagonal Core (`packages/orcia-core/src/orcia_core/packs/`, `catalog/`, `ontology/`, `orchestration/`, `permissions/`, `workflows/`)**:
  - Created `import_service.py` (`295` L), `_internal/seaweedfs_pack_cas.py` (`121` L), `_internal/_sql_pack_import_tx.py` (`239` L), `_internal/_sql_pack_delete_tx.py` (`158` L), `_internal/_sql_pack_entity_materializer.py` (`297` L), `_internal/_sql_pack_ontology_materializer.py` (`190` L), `_internal/_sql_pack_ontology_policy_materializer.py` (`187` L, dynamic `connector_schemes` lookup), and `_internal/_sql_pack_workflows_materializer.py` (`113` L).
  - Updated `ports.py` (`87` L), `loader.py` (`215` L), `errors.py` (`125` L), `_error_catalog.py` (`136` L), `__init__.py` (`123` L), and `_internal/sql_declarative_packs.py` (`268` L).
  - Added `AND pack_bundle_id IS NULL` standalone isolation filters in `sql_contextual_help.py` (`295` L), `sql_ontology_queries.py` (`169` L), `sql_agents_and_skills.py` (`299` L), `_sql_permission_broker_queries.py` (`270` L), and `sql_workflows_v2.py` (`142` L).
- **System Packs & Day-0 Scripts (`packs/`, `infra/scripts/`)**:
  - Added `packs/sdlc/apm.yml`, `packs/orcia-docs/apm.yml`, and `x-orcia:` YAML frontmatter metadata to system `agents/*.md` and `skills/*.md`.
  - Updated `infra/scripts/maintenance/09_reset_db_first_boot.py` (`290` L) and `infra/scripts/e2e/reset_day0.py` (`297` L) to seed system packs via `PackImportService` on Day-0 reset.
- **FastAPI Backend & OpenAPI SDK (`apps/api/`, `packages/api-client/`, `scripts/`)**:
  - Created `apps/api/src/orcia_api/dependencies/pack_import_deps.py` (`82` L), `apps/api/src/orcia_api/routers/_packs_router_helpers.py` (`271` L), `apps/api/src/orcia_api/schemas/packs.py` (`67` L), and `packages/api-client/src/generated/packs.ts` (`11` L).
  - Updated `dependencies/__init__.py` (`172` L), `_lifespan_infra.py` (`241` L), `_lifespan_services.py` (`207` L), `openapi_security.py` (`96` L), `routers/packs.py` (`274` L), `routers/_workflows_helpers.py` (`123` L), `schemas/process_studio_v2.py` (`158` L), `scripts/export_openapi.py` (`278` L), `packages/api-client/openapi.json`, `packages/api-client/src/generated/schema.ts`, `packages/api-client/src/domains/workflowsV2.ts` (`186` L), and `packages/api-client/src/index.ts` (`231` L).
- **Frontend SPA (`apps/web/`)**:
  - **Deleted** hardcoded TypeScript pack catalogs: `features/catalog/packAgentsCatalog.ts`, `features/catalog/packAgentsCatalogData.ts`, `features/processes/processStudioV2StructuralPacks.ts`, and `routes/settingsPacksPresets.ts`.
  - Updated `features/catalog/{index.tsx,managedAgentsHelpers.ts,useManagedAgentActions.ts,useManagedAgentExecutionActions.ts,useManagedAgentGovernanceActions.ts,useManagedAgentsAndSkills.ts}`, `features/inbox/assistantAutocompleteHelpers.ts`, `features/processes/{processStudioV2Data.ts,useProcessesHubData.ts}`, and `routes/SettingsPacksSection.tsx` (all `<= 276` L).
- **Tests & Fakes (`tests/`, `apps/web/src/__tests__/`)**:
  - Created `tests/unit/fakes/in_memory_pack_cas.py` (`40` L), `tests/unit/fakes/workflows_seed.py` (`35` L), `tests/unit/packs/test_story_31_2_{pack_import_service,packs_router,packs_router_and_materializer,branch_coverage}.py` (`77`–`287` L), `tests/integration/test_story_31_2_pack_import_and_day0_postgres18_s3.py` (`262` L), and `apps/web/src/__tests__/setup/installedPacksMockHandler.ts` (`52` L).
  - Updated impacted Story 16.x/24.x/27.x/30.x unit, PG18 integration, and Vitest test files/mocks.

### 3.2 Quantitative Metrics & Branch Coverage
- **Line-Count Guard (`wc -l <= 300`)**: `100%` of created/modified Python and TypeScript production modules (max `299` L) and all newly created test/fake files (max `287` L) comply with `<= 300` lines.
- **Scoped `--branch` Coverage (`>= 90%`)**: **`93%`** across `26` scoped modules (`packages/orcia-core/src/orcia_core/packs/*`, `apps/api/src/orcia_api/routers/packs.py`, `_packs_router_helpers.py`, `_workflows_helpers.py`: `1,732` Stmts, `85` Miss, `442` Branch, `63` BrPart across `114` tests; `--fail-under=90` passed).
- **Static & Architecture Gates**:
  - `.venv/bin/ruff check .`: `All checks passed!`
  - `.venv/bin/ruff format --check .`: `1819 files already formatted`
  - `.venv/bin/mypy --strict packages/orcia-core packages/orcia-connectors apps/api apps/worker`: `Success: no issues found in 892 source files`
  - `.venv/bin/lint-imports`: `Contracts: 5 kept, 0 broken.` (`935` files, `6,770` deps)
  - `.venv/bin/python .agent/skills/bmad-architecture/scripts/lint_spine.py`: `total_findings: 0`
  - `.venv/bin/python scripts/export_openapi.py --check`: `exit 0` (`0-diff`)
  - `.venv/bin/detect-secrets-hook --baseline .secrets.baseline`: `exit 0` across all changed/added files.

### 3.3 AD-17 Test Pyramid & Vertical Wiring Verification
- **Layer 1a — Python Unit Tests (`tests/unit`)**: **`1,232 passed`** (`0` failures), including `test_core_domain_isolation.py`, Story `31.2` `PackImportService` / router / materializer suites, and `test_site_catalog_sync.py`.
- **Layer 1b & Frontend Monorepo (`pnpm turbo run lint typecheck test --concurrency=2`)**: **`9/9` tasks passed** (`@orcia/api-client`: `3` files / `20` tests; `@orcia/ui`: `40` files / `154` tests; `@orcia/web`: `95` files / `369` tests = **`543` JS/TS tests**).
- **Layer 2 — Real PostgreSQL 18 + Redis 7.4 + SeaweedFS S3 `testcontainers` Integration (`--no-cov`)**: **`10 passed`** across `test_story_31_2_pack_import_and_day0_postgres18_s3.py`, `test_declarative_packs_and_wizards_postgres18.py`, `test_story_11_4_pack_builder_postgres18_s3.py`, `test_e2e_reset_day0_postgres18_and_redis.py`, `test_http_vertical_day0_and_agents_postgres18.py`, and `test_story_30_5_agent_governance_and_lifecycle_pg18.py`.
- **Layer 3, 4 & Security (`tests/evals`, `tests/security`, `tests/contract`)**: **`193 passed`** (`0` failures).
- **Layer 5 — Desktop Playwright E2E (`env -u ORCIA_E2E_SEED_FIXTURES`, `--project=desktop-cockpit`)**: **`6 passed (1.3m)`** across `e2e/08-agents-skills-persistence.spec.ts` and `e2e/18-catalog-packs-wizards-and-mcp-bench.spec.ts` on real ephemeral PG18 + Redis (`e2e-campaign-epic-22/` artifacts cleaned).

### 3.4 GitNexus Verification
- `npx gitnexus analyze --index-only .`: `48,913 nodes | 167,209 edges | 798 clusters | 1526 flows`.
- `gitnexus_detect_changes({scope: "all"})`: `changed_count: 16`, `affected_count: 1526`, `changed_files: 64`, `risk_level: "critical"` (expected blast radius across pack/workflow schemas, Day-0 seeding, and core SQL standalone guards; all 5 `AD-17` layers passed).
