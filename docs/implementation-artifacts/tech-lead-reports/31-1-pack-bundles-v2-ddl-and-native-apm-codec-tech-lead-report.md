# Story 31.1 — `declarative_pack_bundles` v2 DDL & Native APM-Superset Manifest/Archive Codec

- **Date**: 2026-11-26
- **Story / Sprint Key**: `31-1-pack-bundles-v2-ddl-and-native-apm-codec` (`Epic 31` — Lot 1)
- **Capability(ies)**: `CAP-055`, `CAP-056`, `CAP-082`, `CAP-090` — classification: `feature`
- **Author / Context**: `bmad-dev-worker` (`Story 31.1`), implementing `D1`, `D3`, `D4`, `D6`, `A1` from `epic-31-decisions-grill-2026-11-25.md` and `sprint-change-proposal-2026-11-25-epic-31-declarative-apm-packs-import-export.md`
- **Associated Commits**: pending

---

## 1. Needs Analysis & Tech Lead Impact Study (Pre-Implementation)

### 1.1 Context & Problem Statement
- **Current behavior**:
  - `declarative_pack_bundles` (created in `20261108_0910_declarative_packs_and_workflows_v2.py`) is a shallow metadata table with single-column `UNIQUE(slug)` and `UNIQUE(pack_id)`, lacking `bundle_kind` (`SYSTEM | ORG | IMPORTED | CUSTOM`), scope columns (`scope_type`, `scope_id`), `archive_sha256`, `cas_object_key`, `manifest_yaml`, `source_origin`, and `declared_slots_jsonb`.
  - Constituent entity tables (`catalog_items`, `workflow_definitions_v2`, `vsm_definitions_v2`, `ontology_concepts`, `ontology_relations`, `ontology_axioms`, `permission_broker_policies`) have no `pack_bundle_id` foreign key (`ON DELETE CASCADE`), and no tables exist for pack-scoped Starlark DNA mechanisms (`pack_dna_mechanisms`), draft pack authoring (`pack_draft_memberships`), workspace-only pack activations (`workspace_pack_activations`), or explicit connector slot bindings (`workspace_pack_slot_bindings`).
  - `connector_schemes` (`0013_story_3_2e_connector_schemes_expand.py`) does not register the `'pack'` scheme (`orcia://packs/`).
  - `orcia_core.packs.loader` only reads legacy `pack.yaml` directories (`packs/sdlc`, `packs/orcia-docs`) and has no native APM-Superset (`apm.yml`, `apm.lock.yaml`, `.agent.md`, `SKILL.md`, `.instructions.md`, `.policy.md`, `help/{fr,en}/*.md`, `mechanisms/*.star`) codec, zip-slip/zip-bomb guard, executable hook rejection (`HTTP 422 ERR_PACK_EXECUTABLE_HOOK_FORBIDDEN`), or Starlark AST/sandbox validation.
- **Expected behavior**:
  - Immutable PostgreSQL 18 schema v2 (`20261126_311_declarative_packs_v2.py`) preserving existing `declarative_pack_bundles` rows, extending it to v2, adding `pack_bundle_id` FKs (`ON DELETE CASCADE`) across all 7 constituent entity tables, creating the 4 new pack v2 tables, registering `'pack'` in `connector_schemes`, and keeping `infra/scripts/maintenance/_first_boot_reset_guards.py` synchronized.
  - Pure Python dependency-free `ApmPackCodec` (`PyYAML` + `Pydantic v2` + stdlib `zipfile`/`ast`) supporting both APM-Superset archives/directories and legacy `pack.yaml` bundles, with fail-closed security guards and deterministic `encode_zip_bytes` SHA-256 output.
- **Constraints from `ARCHITECTURE-SPINE.md` & `AD-19` / `AD-20`**:
  - Zero new third-party dependencies.
  - Zero framework/SDK imports (`sqlalchemy`, `fastapi`, `dbos`, `dramatiq`, `redis`, `wasmtime`) in `orcia_core.packs.models`, `errors`, `ports`.
  - Every source file `<= 300` lines; zero orphan SQL adapter modules (`test_zero_orphan_sql_adapters_audit.py`); 100% bilingual FR/EN RFC 9457 error catalog (`test_i18n_backend_catalog_and_english_dev_audit.py`); zero hardcoded 64-hex SHA-256 literals in `.py` files (`detect-secrets`).

### 1.2 Exploration, GitNexus Impact Analysis, Refactoring & Technical Debt
- **GitNexus Impact Analysis (`gitnexus_query`, `gitnexus_context`, `gitnexus_impact` scoped to worktree)**:
  - `DeclarativePackLoader` (`packages/orcia-core/src/orcia_core/packs/loader.py:58-141`): queried and inspected via `context` & `impact` (`epistemic: exact`, methods `__init__`, `load_all_packs`, `load_single_pack`). Direct callers verified via grep: `apps/api/src/orcia_api/routers/packs.py`, `apps/api/src/orcia_api/dependencies/_lifespan_infra.py`, `infra/scripts/e2e/reset_day0.py`, `tests/unit/packs/test_declarative_packs_loading.py`, `tests/unit/test_declarative_packs_and_durable_wizards_persistence.py`.
  - `sql_declarative_packs.py` (`packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_declarative_packs.py`): queried and inspected; `upsert_declarative_pack_bundles_sql` uses `ON CONFLICT (pack_id)` and is mocked in `tests/unit/test_declarative_packs_and_durable_wizards_persistence.py` (9-column tuple). Keeping `pack_id` unique and backward-compatible while adding v2 column awareness ensures zero regression on existing callers.
  - `OrciaDomainError` & `DOMAIN_ERROR_CLASSES` (`packages/orcia-core/src/orcia_core/kernel/errors.py`, `apps/api/src/orcia_api/errors/_registry_classes.py`): inspected; `test_i18n_backend_catalog_and_english_dev_audit.py` enforces AST discovery of every `OrciaDomainError` subclass in `ERROR_CATALOG` with non-empty `fr` & `en` copies.
  - `connector_schemes`: `0013_story_3_2e_connector_schemes_expand.py` seeds `0192c4e0-0000-7000-8000-00000000c001..c007`; `'pack'` uses `0192c4e0-0000-7000-8000-00000000c008`.
- **Exploration & Key Metrics (Database / Schema Verification)**:
  - Latest Alembic head verified: `20261125_303` (`infra/migrations/versions/20261125_303_workflow_v2_runs.py`).
  - Target FK column PK types verified in migrations: `workspaces.id` (`UUID`, `0002`), `catalog_items.id` (`UUID`, `0003`), `permission_broker_policies.id` (`UUID`, `0004`), `ontology_concepts/relations/axioms.id` (`UUID`, `0006`), `declarative_pack_bundles/vsm_definitions_v2/workflow_definitions_v2.id` (`UUID`, `20261108_0910`).
  - `lint-imports` baseline: `5 contracts kept, 0 broken`. `lint_spine.py` baseline: `ok: true, total_findings: 0`.
- **Refactoring Opportunities & Emerging Technical Debt Mitigation**:
  - Split `orcia_core.packs` cleanly into focused modules (`<= 300` lines each): `models.py`, `ports.py`, `errors.py`, `_error_catalog.py`, `_internal/_apm_security_guards.py`, `_internal/_apm_markdown_parser.py`, `_internal/_apm_manifest_parser.py`, `_internal/_apm_entry_router.py`, `_internal/_apm_bundle_synthesizer.py`, `_internal/apm_codec.py`, `_internal/sql_declarative_packs.py`, `_internal/_sql_pack_lifecycle.py`.
  - Share a single strict Starlark AST node & attribute whitelist (`orcia_core.gates._internal._starlark_ast_whitelist.py` exported cleanly via `orcia_core.gates`) across both `StarlarkMechanismSandbox` and `ApmPackCodec` (`AD-19` zero cross-domain `_internal` imports).
  - Note on `D6.a` / `Story 31.5` Pack Composer: `pack_draft_memberships` enforces typed `ON DELETE RESTRICT` FKs across all 8 PG18 entity tables (`catalog_items`, `workflow_definitions_v2`, `vsm_definitions_v2`, `ontology_concepts`, `ontology_relations`, `ontology_axioms`, `pack_dna_mechanisms`, `permission_broker_policies`) via `chk_pack_draft_membership_typed_fk`; Story 31.5 Composer APIs will resolve the surrogate UUID `id` for `WorkflowDefinitionV2.id` / `ValueStreamMapSpec.id` string identifiers when inserting draft memberships.
  - Preserve `orcia_core/packs/loader.py` unchanged for existing `TASK-03` / `Story 22.5` callers until `Story 31.2` executes the Day-0 cutover and purges disk/TS hardcoding.

---

## 2. Implementation Plan

### 2.1 Data Schema & Alembic Migrations (`infra/migrations/versions/`)
- `infra/migrations/versions/20261126_311_declarative_packs_v2.py` (`revision = "20261126_311"`, `down_revision = "20261125_303"`, raw SQL `op.execute(sa.text(...))`, full idempotent `upgrade()` and `downgrade()`):
  - Alter `declarative_pack_bundles` to add `bundle_kind`, `scope_type`, `scope_id`, `status` (`DRAFT | PUBLISHED | DEPRECATED`), `published_at`, `created_by_user_id`, `archive_sha256` (backfilled from `bundle_sha256` then `SET NOT NULL`), `cas_object_key`, `manifest_yaml`, `source_origin`, `declared_slots_jsonb`, `author`, `description`, `updated_at`; drop `declarative_pack_bundles_slug_key` and `declarative_pack_bundles_pack_id_key` (adding non-unique `idx_declarative_pack_bundles_pack_id`); add `CONSTRAINT uq_pack_bundle_scope_slug_ver UNIQUE (scope_type, scope_id, slug, version)`.
  - Add nullable `pack_bundle_id UUID REFERENCES declarative_pack_bundles(id) ON DELETE CASCADE` and B-Tree indexes on `catalog_items`, `workflow_definitions_v2`, `vsm_definitions_v2`, `ontology_concepts`, `ontology_relations`, `ontology_axioms`, `permission_broker_policies`; replace global `UNIQUE` constraints with dual partial unique indexes (`WHERE pack_bundle_id IS NULL` for standalone writes + `(pack_bundle_id, ...)` `WHERE pack_bundle_id IS NOT NULL` for multi-pack coexistence).
  - Create `pack_dna_mechanisms` (with `passing_test_payload_jsonb` / `failing_test_payload_jsonb`), `pack_draft_memberships` (8 typed `ON DELETE RESTRICT` FK columns + `chk_pack_draft_membership_typed_fk`), `workspace_pack_activations` (nullable `priority_order >= 1` when active + `DEFERRABLE INITIALLY DEFERRED` + cross-workspace scope guard trigger), and `workspace_pack_slot_bindings` (`pack_bundle_id`, nullable `bound_datasource_id` / `bound_connector_id`, `connector_scheme` FK).
  - Upsert `'pack'` into `connector_schemes` (`0192c4e0-0000-7000-8000-00000000c008`).
- `infra/scripts/maintenance/_first_boot_reset_guards.py` & `09_reset_db_first_boot.py`: add `'pack'` to `BASE_CONNECTOR_SCHEMES`, register the 4 new mutable tables in `ORDERED_MUTABLE_TABLES_TO_CLEAR`, and purge non-`SYSTEM` rows (`bundle_kind <> 'SYSTEM'`) on Day-0 reset.
- `docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24/architecture.md`: add concise §4 data-model entry for the v2 pack tables and `'pack'` scheme.

### 2.2 Hexagonal Core, Orchestration & Workers (`packages/orcia-core/`)
- `packages/orcia-core/src/orcia_core/packs/_error_catalog.py` & `errors.py`: 8 domain errors inheriting `OrciaDomainError` (`PackExecutableHookForbiddenError`, `PackInvalidArchiveError`, `PackVersionConflictError`, `PackSlotUnboundError`, `PackClosureIncompleteError`, `PackPiiOrInfraLeakError`, `ResourcePinnedByActiveRunsError`, `EntityReferencedByPackDraftError`) with complete FR/EN catalog messages.
- `packages/orcia-core/src/orcia_core/packs/models.py` & `ports.py`: zero-framework Pydantic v2 domain models (`PackManifestV2`, `LoadedPackBundleV2`, `PackSlotSpec`, `PackAgentSpec`, `PackSkillSpec`, `PackInstructionSpec`, `PackDnaMechanismSpec`, `PackPolicySpec`, `PackHelpArticleSpec`, `PackLockSpec`, `WorkspacePackActivation`, `WorkspacePackSlotBinding`, `PackDraftMembership`) and structural `Protocol` ports (`PackCodecPort`, `PackBundleRepositoryPort`).
- `packages/orcia-core/src/orcia_core/packs/_internal/_apm_security_guards.py`: zip-slip/symlink/zip-bomb guards, hook/script rejection (`ERR_PACK_EXECUTABLE_HOOK_FORBIDDEN`), forbidden YAML key recursion, and Starlark AST validation.
- `packages/orcia-core/src/orcia_core/packs/_internal/_apm_markdown_parser.py` & `apm_codec.py`: `ApmPackCodec` supporting native APM-Superset archives/directories + legacy `pack.yaml` fallback, `apm.lock.yaml` verification, `StarlarkMechanismSandbox` test vector validation (`PASS`/`FAIL`), and deterministic `encode_zip_bytes` (sorted paths + fixed ZIP timestamp `(2026, 1, 1, 0, 0, 0)`).
- `packages/orcia-core/src/orcia_core/packs/_internal/sql_declarative_packs.py` & `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_declarative_packs.py`: v2 SQL bundle persistence (`SqlPackBundleV2Repository`) wired via Composition Root, plus backward-compatible v2 column support in bootstrap upsert.

### 2.3 Backend API, Security & Contracts (`apps/api/`)
- `apps/api/src/orcia_api/errors/_registry_classes.py`: register all 8 new `packs.errors` classes into `DOMAIN_ERROR_CLASSES` and `__all__`.
- `apps/api/src/orcia_api/dependencies/_lifespan_services.py`: instantiate and attach `SqlPackBundleV2Repository` on `app.state.pack_bundle_v2_repository` in the Composition Root (ensuring zero orphan SQL adapter modules).

### 2.4 User Interface & Experience (`apps/web/`, `packages/ui/`)
- Not impacted in Story 31.1 (UI integration is scoped to Story 31.6).

### 2.5 Test Pyramid Impact Analysis (`AD-17`)
- **Layer 1a (Python Unit `tests/unit/`)**:
  - `tests/unit/packs/test_story_31_1_apm_codec_and_security.py`: APM-Superset `.zip` + directory decoding, `apm.lock.yaml` verification & tamper rejection, legacy `packs/sdlc` & `packs/orcia-docs` compatibility, deterministic `encode_zip_bytes` SHA-256, zip-slip / symlink / zip-bomb rejection, `ERR_PACK_EXECUTABLE_HOOK_FORBIDDEN` (`422`) on scripts/hooks/YAML keys, Starlark AST & PASS/FAIL vector checks, domain errors + bilingual FR/EN RFC 9457 catalog completeness.
  - `tests/unit/test_first_boot_reset_guards.py`: assert `'pack'` in `BASE_CONNECTOR_SCHEMES` and the 4 new mutable tables in `ORDERED_MUTABLE_TABLES_TO_CLEAR`.
- **Layer 2 (PG18 Integration)**: Alembic `20261126_311` `upgrade()` / `downgrade()` and v2 persistence verified by Testing Verifier against ephemeral PostgreSQL 18.
- **Layer 3 (Contracts & Architecture)**: `lint-imports` (`5/5`), `lint_spine.py` (`0 findings`), `ruff check`, `ruff format --check`, `mypy --strict`.

---

## 3. Summary of Changes & Results (Post-Implementation)

### 3.1 Created & Modified Files
All `40` created/modified `.py` files respect the `<= 300`-line modular limit (max `299` lines).

| File | Action | Lines | Concise Summary |
| :--- | :--- | :---: | :--- |
| `infra/migrations/versions/20261126_311_declarative_packs_v2.py` | Created | 294 | Raw-SQL single-statement Alembic migration (`20261125_303` $\rightarrow$ `20261126_311`): v2 `declarative_pack_bundles` columns & scope constraints, nullable `pack_bundle_id` FK (`ON DELETE CASCADE`) + dual partial unique indexes across 7 constituent tables, 4 new tables (`pack_dna_mechanisms`, `pack_draft_memberships`, `workspace_pack_activations` with `DEFERRABLE` priority + cross-workspace trigger, `workspace_pack_slot_bindings`), and `'pack'` scheme upsert (`0192c4e0-0000-7000-8000-00000000c008`) with full `downgrade()`. |
| `infra/scripts/maintenance/_first_boot_reset_guards.py` | Modified | 182 | Added `'pack'` to `BASE_CONNECTOR_SCHEMES` and registered the 4 new mutable pack v2 tables in `ORDERED_MUTABLE_TABLES_TO_CLEAR`. |
| `infra/scripts/maintenance/09_reset_db_first_boot.py` | Modified | 298 | Purges non-`SYSTEM` (`bundle_kind <> 'SYSTEM'`) declarative pack bundles and scoped constituent rows on Day-0 reset. |
| `infra/scripts/maintenance/05_backfill_ontology_and_rag_graph.py` | Modified | 287 | Aligned ontology backfill SQL with partial non-pack unique indexes (`WHERE pack_bundle_id IS NULL`). |
| `packages/orcia-core/src/orcia_core/packs/__init__.py` | Modified | 98 | Public exports for v2 models, domain errors, ports, `ApmPackCodec`, and `SqlPackBundleV2Repository`. |
| `packages/orcia-core/src/orcia_core/packs/models.py` | Created | 278 | Zero-framework Pydantic v2 domain models (`PackManifestV2`, `LoadedPackBundleV2`, `PackSlotSpec`, `PackAgentSpec`, `PackSkillSpec`, `PackInstructionSpec`, `PackDnaMechanismSpec`, `PackPolicySpec`, `PackHelpArticleSpec`, `PackLockSpec`, `WorkspacePackActivation`, `WorkspacePackSlotBinding`, `PackDraftMembership`). |
| `packages/orcia-core/src/orcia_core/packs/ports.py` | Created | 63 | Structural `Protocol` ports (`PackCodecPort`, `PackBundleRepositoryPort`). |
| `packages/orcia-core/src/orcia_core/packs/errors.py` | Created | 95 | 8 `OrciaDomainError` subclasses (`PackExecutableHookForbiddenError`, `PackInvalidArchiveError`, `PackVersionConflictError`, `PackSlotUnboundError`, `PackClosureIncompleteError`, `PackPiiOrInfraLeakError`, `ResourcePinnedByActiveRunsError`, `EntityReferencedByPackDraftError`). |
| `packages/orcia-core/src/orcia_core/packs/_error_catalog.py` | Created | 106 | Complete bilingual FR/EN RFC 9457 error catalog for all 8 Story 31.1 domain errors. |
| `packages/orcia-core/src/orcia_core/packs/_internal/__init__.py` | Created | 17 | Internal pack v2 package exports (`ApmPackCodec`, `SqlPackBundleV2Repository`). |
| `packages/orcia-core/src/orcia_core/packs/_internal/_apm_security_guards.py` | Created | 229 | Zip-slip, symlink, zip-bomb, executable hook (`HTTP 422 ERR_PACK_EXECUTABLE_HOOK_FORBIDDEN`), forbidden YAML key, and Starlark AST validation guards. |
| `packages/orcia-core/src/orcia_core/packs/_internal/_apm_markdown_parser.py` | Created | 218 | Frontmatter & body parser for `.agent.md`, `SKILL.md`, `.instructions.md`, `.policy.md`, and bilingual `help/{fr,en}/*.md`. |
| `packages/orcia-core/src/orcia_core/packs/_internal/_apm_manifest_parser.py` | Created | 272 | Strict parser for `apm.yml`, `apm.lock.yaml`, and legacy `pack.yaml` fallback manifests. |
| `packages/orcia-core/src/orcia_core/packs/_internal/_apm_entry_router.py` | Created | 106 | Deterministic file-extension/path router across APM-Superset archives and directories. |
| `packages/orcia-core/src/orcia_core/packs/_internal/_apm_bundle_synthesizer.py` | Created | 123 | Synthesizes validated `LoadedPackBundleV2` artifacts and deterministic ZIP entries (`(2026, 1, 1, 0, 0, 0)`). |
| `packages/orcia-core/src/orcia_core/packs/_internal/apm_codec.py` | Created | 266 | `ApmPackCodec` (`decode_directory`, `decode_zip_bytes`, `encode_zip_bytes`, `apm.lock.yaml` SHA-256 verification, and `StarlarkMechanismSandbox` PASS/FAIL vector checks). |
| `packages/orcia-core/src/orcia_core/packs/_internal/sql_declarative_packs.py` | Created | 265 | `SqlPackBundleV2Repository` (`upsert_bundle_v2`, `get_bundle_v2`, `list_bundles_v2`, `list_dna_mechanisms`). |
| `packages/orcia-core/src/orcia_core/packs/_internal/_sql_pack_lifecycle.py` | Created | 222 | `SqlPackBundleV2Repository` lifecycle operations (active-activation delete guard raising `ResourcePinnedByActiveRunsError`, draft membership queries). |
| `packages/orcia-core/src/orcia_core/gates/__init__.py` | Modified | 156 | Exported shared Starlark AST whitelist helpers cleanly at the `gates` public boundary (`AD-19`). |
| `packages/orcia-core/src/orcia_core/gates/_internal/__init__.py` | Modified | 25 | Internal re-export of shared Starlark AST whitelist utilities. |
| `packages/orcia-core/src/orcia_core/gates/_internal/_starlark_ast_whitelist.py` | Created | 224 | Shared strict Starlark AST node & attribute whitelist reused by both `StarlarkMechanismSandbox` and `ApmPackCodec`. |
| `packages/orcia-core/src/orcia_core/gates/_internal/starlark_sandbox.py` | Modified | 299 | Refactored to consume `_starlark_ast_whitelist.py` (`<= 300` lines). |
| `packages/orcia-core/src/orcia_core/bootstrap/_internal/sql_declarative_packs.py` | Modified | 266 | Extended bootstrap upsert with v2 columns (`archive_sha256`, `bundle_kind`, `scope_type`, `scope_id`, `source_origin`, `status`) while keeping legacy 9-column tuple compatibility. |
| `packages/orcia-core/src/orcia_core/bootstrap/seeder.py` | Modified | 229 | Updated conflict targets on `ON CONFLICT` upserts to align with partial non-pack unique indexes (`WHERE pack_bundle_id IS NULL`). |
| `packages/orcia-core/src/orcia_core/catalog/_internal/_sql_contextual_help_seed.py` | Modified | 101 | Updated non-pack `catalog_items` conflict target (`WHERE pack_bundle_id IS NULL`). |
| `packages/orcia-core/src/orcia_core/orchestration/_internal/_sql_help_catalog.py` | Modified | 134 | Updated non-pack `catalog_items` conflict target (`WHERE pack_bundle_id IS NULL`). |
| `packages/orcia-core/src/orcia_core/orchestration/_internal/sql_agents_and_skills.py` | Modified | 298 | Updated non-pack `catalog_items` conflict target (`WHERE pack_bundle_id IS NULL`). |
| `packages/orcia-core/src/orcia_core/orchestration/_internal/sql_mcp_exposure.py` | Modified | 253 | Updated non-pack `catalog_items` conflict target (`WHERE pack_bundle_id IS NULL`). |
| `packages/orcia-core/src/orcia_core/orchestration/_pack_builder_models.py` | Modified | 271 | Added v2 pack metadata fields compatible with `LoadedPackBundleV2` synthesis. |
| `packages/orcia-core/src/orcia_core/workflows/_internal/sql_vsm_v2.py` | Modified | 251 | Updated non-pack `vsm_definitions_v2` conflict target (`WHERE pack_bundle_id IS NULL`). |
| `packages/orcia-core/src/orcia_core/workflows/_internal/sql_workflows_v2.py` | Modified | 142 | Updated non-pack `workflow_definitions_v2` conflict target (`WHERE pack_bundle_id IS NULL`). |
| `apps/api/src/orcia_api/errors/_registry_classes.py` | Modified | 280 | Re-exported Story 31.1 domain error classes via `_registry_extra_classes.py`. |
| `apps/api/src/orcia_api/errors/_registry_extra_classes.py` | Created | 27 | Registered all 8 `orcia_core.packs.errors` classes into `DOMAIN_ERROR_CLASSES`. |
| `apps/api/src/orcia_api/dependencies/_lifespan_services.py` | Modified | 175 | Wired `SqlPackBundleV2Repository` onto `app.state.pack_bundle_v2_repository` in Composition Root (`0` orphan SQL adapters). |
| `docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24/architecture.md` | Modified | 703 | Documented `declarative_pack_bundles` v2, 4 new pack v2 tables, partial unique indexes, and `'pack'` scheme in §4. |
| `tests/unit/test_first_boot_reset_guards.py` | Modified | 219 | Verified `'pack'` scheme protection and the 4 new mutable pack v2 tables in Day-0 reset guards. |
| `tests/unit/packs/test_story_31_1_apm_codec_and_security.py` | Created | 270 | Unit tests for APM `.zip`/directory decoding, `apm.lock.yaml`, legacy `pack.yaml` compatibility, and error catalog coverage. |
| `tests/unit/packs/test_story_31_1_codec_synthesis_and_seeder.py` | Created | 293 | Unit tests for deterministic `encode_zip_bytes` SHA-256 roundtrip, bundle synthesis, and bootstrap seeder v2 compatibility. |
| `tests/unit/packs/test_story_31_1_pack_repo_and_edge_cases.py` | Created | 269 | Unit tests for `SqlPackBundleV2Repository` query paths, active-pinning guards, and manifest edge cases. |
| `tests/unit/packs/test_story_31_1_security_and_starlark_dos.py` | Created | 255 | Unit tests for zip-slip, symlink, zip-bomb, `ERR_PACK_EXECUTABLE_HOOK_FORBIDDEN` (`422`), YAML keys, and Starlark AST/PASS-FAIL vector guards. |
| `tests/integration/db/test_story_31_1_declarative_packs_v2_postgres18.py` | Created | 274 | Real PostgreSQL 18 `testcontainers` test verifying `20261126_311` DDL, `'pack'` scheme, `SqlPackBundleV2Repository` CRUD + DNA mechanisms, typed FK CHECK, cross-workspace trigger, `DEFERRABLE` swap, delete guard, `downgrade 20261125_303`, and `upgrade head`. |

### 3.2 Quantitative Metrics, Coverage & Static Quality
- **Scoped Branch Coverage (`coverage run --branch`)**: **`94%`** (`1238` statements, `49` missed, `342` branches, `39` partial branches; `--fail-under=90` PASSED) across `packages/orcia-core/src/orcia_core/packs/*` and the 4 touched `orcia_core/gates` modules (`90` tests in `tests/unit/packs`, `test_epic_11_story_11_2_dna_starlark_and_glossary.py`, `test_orcia_core_and_api.py`, `test_first_boot_reset_guards.py`). Every new Story 31.1 module reached `90%`–`100%` branch coverage.
- **Line-Count Guard (`wc -l <= 300`)**: `40/40` modified/created `.py` files (production and test) `<= 299` lines.
- **Static Quality & Architecture**:
  - `.venv/bin/ruff check .`: `All checks passed!` (`0` warnings)
  - `.venv/bin/ruff format --check .`: `1800 files already formatted`
  - `.venv/bin/mypy --strict packages/orcia-core packages/orcia-connectors apps/api apps/worker`: `Success: no issues found in 881 source files`
  - `.venv/bin/lint-imports`: `5 contracts kept, 0 broken` (`924` files, `6,681` dependencies)
  - `.venv/bin/python .agent/skills/bmad-architecture/scripts/lint_spine.py`: `ok: true, total_findings: 0`
  - `.venv/bin/detect-secrets-hook --baseline .secrets.baseline`: `exit 0` across all changed/added files
  - `npx gitnexus analyze --index-only .`: `48,449 nodes | 148,607 edges | 803 clusters | 1533 flows`
  - `gitnexus_detect_changes(scope="all")`: `changed_count: 6`, `affected_count: 1517`, `changed_files: 20`, `risk_level: "critical"` (driven by `UpsertSpec` in `seeder.py` touching central bootstrap flows; verified across full `tests/unit` and PG18 integration suites).

### 3.3 AD-17 Test Pyramid & Vertical Wiring Verification
- **Layer 1a — Python Unit Tests (`tests/unit`)**: **`1,221 passed`** across `tests/unit` (excluding `test_site_catalog_sync.py` run post-`site:sync`, which also passed independently after `sync_site_catalog.py`), including core domain isolation AST/regex (`test_core_domain_isolation.py`), zero-orphan SQL adapters audit, and bilingual RFC 9457 error catalog audit.
- **Layer 1b & Frontend Monorepo (`pnpm turbo run lint typecheck test --concurrency=2`)**: **`9/9` tasks passed** (`@orcia/api-client`: `3` files / `20` tests; `@orcia/ui`: `40` files / `154` tests; `@orcia/web`: `95` files / `369` tests = **`543` JS/TS tests**).
- **Layer 2 — Real PostgreSQL 18 + Redis 7.4 + SeaweedFS `testcontainers` Integration (`--no-cov`)**: **`4 passed`** (`tests/integration/db/test_story_31_1_declarative_packs_v2_postgres18.py`, `tests/integration/test_declarative_packs_and_wizards_postgres18.py`, `tests/integration/test_story_11_4_pack_builder_postgres18_s3.py`, `tests/integration/test_e2e_reset_day0_postgres18_and_redis.py`), verifying `20261126_311` `upgrade head`, constraints, triggers, `SqlPackBundleV2Repository`, `downgrade 20261125_303`, re-`upgrade head`, and Day-0 reset guards.
- **Layer 3 & 4 & Security (`tests/evals`, `tests/security`, `tests/contract`)**: **`193 passed`** (`0` failures).
- **Layer 5 — Playwright E2E**: Not impacted in Story 31.1 (no UI/API route changes; UI integration is scoped to Story 31.6).
- **Documentation & Site Catalog Sync**: `infra/scripts/sync_site_catalog.py --check`, `scripts/check_implementation_docs.py`, and `tests/unit/test_site_catalog_sync.py` verified clean after report & sprint-status closure.
