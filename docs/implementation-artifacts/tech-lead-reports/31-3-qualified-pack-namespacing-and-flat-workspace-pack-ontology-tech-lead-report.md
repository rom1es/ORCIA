# Story 31.3 — Qualified `{pack_slug}:{entity_slug}` Namespacing & Flat Priority-Ordered Workspace Pack Ontology (`R3`, `R4`)

- **Date**: 2026-11-26
- **Story / Sprint Key**: `31-3-qualified-pack-namespacing-and-flat-workspace-pack-ontology` (`Epic 31` / Lot 2)
- **Capability(ies)**: `CAP-070`, `CAP-082`, `CAP-090`, `CAP-100`, `CAP-140`, `CAP-200` — classification: `feature`
- **Author / Context**: Tech Lead / Senior Dev (`bmad-dev-worker`) — Story 31.3 implementing findings `R3` (Qualified runtime namespacing & collision transparency) and `R4` / `D6.a` / `R1` (Flat priority-ordered workspace pack ontology, instructions, DNA mechanisms & broker policies without pack-to-pack inheritance graphs). Covers `AD-7`, `AD-15`, `AD-19`, `AD-20`, `AD-21`, `D6.a`, `R1`, `R3`, `R4`.
- **Associated Commits**: Pending implementation commit

---

## 1. Needs Analysis & Tech Lead Impact Study (Pre-Implementation)

### 1.1 Context & Problem Statement
- **Current behavior**:
  1. Story 31.1 & 31.2 introduced `declarative_pack_bundles` v2, `workspace_pack_activations` (with `UNIQUE (workspace_id, priority_order) DEFERRABLE INITIALLY DEFERRED`), and `pack_bundle_id`-scoped uniqueness on `catalog_items`, `workflow_definitions_v2`, `vsm_definitions_v2`, `ontology_concepts`, `ontology_relations`, `ontology_axioms`, and `permission_broker_policies`.
  2. However, runtime entity listing and resolution (`AgentsAndSkillsManagementService`, `sql_agents_and_skills.py`, `_agents_lifecycle_guards.py`, `_assistant_tool_catalog.py`, `parse_federated_uri`, and frontend `assistantAutocompleteHelpers.ts`) still operate on bare unqualified `slug` / `@slug` / `/slug` tokens (`handle = f"@{agent.slug}"`, `command_handle = f"/{skill.slug}"`). When two packs (e.g., `sdlc` and `legal-audit`) both declare `reviewer` or `compliance-check`, frontend autocomplete deduplicates via `seenTokens.has(ag.handle)` and drops the second entry, while backend resolution cannot disambiguate or report collision metadata.
  3. On the ontology & governance side, `OntologyHierarchyResolver`, `sql_ontology_queries.py`, `ontology_and_rag.py`, `_assistant_ontology_context.py`, and `assistant_workspace_governance.py` do not yet resolve `WORKSPACE_PACK` concepts, relations, axioms, `pack_dna_mechanisms`, `permission_broker_policies`, and `INSTRUCTION` items flatly by `workspace_pack_activations.priority_order ASC` with precedence `workspace_overrides > priority_order ASC > SYSTEM`.
- **Expected behavior**:
  1. Canonical `D6.a` qualified namespacing across agents, skills, workflows, VSMs, and ontology keys: `@<pack_slug>/<slug>`, `/<pack_slug>/<slug>`, `orcia://packs/<pack_slug>/<kind>/<slug>` (plus `pack://` alias normalization in `parse_federated_uri`), transparent `<pack_slug>:<entity_slug>` input normalization, and `@workspace/<slug>` / `/workspace/<slug>` for workspace standalone items.
  2. Unqualified `@slug` / `/slug` resolution follows deterministic flat workspace priority (`WORKSPACE_OVERRIDE` > `WORKSPACE_PACK` ordered by `priority_order ASC` > `SYSTEM_PACK`) and exposes `pack_slug`, `qualified_ref`, `is_colliding`, `collision_pack_slugs`, and `resolution_tier`, plus `409 ERR_PACK_ENTITY_AMBIGUOUS` when strict disambiguation is requested on collision.
  3. Flat priority-ordered workspace pack ontology & instructions resolution (`workspace_overrides > priority_order ASC > SYSTEM`, zero pack-to-pack inheritance graphs), immediately reflecting `DEFERRABLE INITIALLY DEFERRED` priority swaps on subsequent cold PG18 reads without mutating immutable `pack_bundle_id` rows.
- **Architectural constraints**:
  - `AD-19` Contract 2 (`lint-imports` `5/5`): `orcia_core.packs` and `orcia_core.orchestration` are sibling top-layer modules and MUST NOT import each other; `orcia_core.ontology` sits below `packs`. Shared pure namespacing primitives must live in `orcia_core.domain.namespacing` (with `orcia_core.packs.namespacing` re-exporting and adding `PackEntityCollisionError`), and flat SQL ontology resolution lives in `orcia_core.packs._internal.sql_pack_ontology_resolution` / `orcia_core.ontology.resolver` respecting unidirectional layers.
  - Zero forbidden domain keywords (`jira|confluence|git_branch|wsjf|rovo|copilot|safe|prd`) in `packages/orcia-core/src/` (`test_core_domain_isolation.py`).
  - All files `<= 300` lines (`wc -l`).

### 1.2 Exploration, GitNexus Impact Analysis, Refactoring & Technical Debt
- **GitNexus Impact Analysis (`gitnexus_query`, `gitnexus_context`, `gitnexus_impact` scoped to worktree `/home/romain/.gemini/antigravity/worktrees/ORCIA/consignes_personnelles_save_button`)**:
  - `OntologyHierarchyResolver`: `131` impacted upstream symbols (`113` direct `d=1`, `18` `d=2`, `CRITICAL` risk, `10` affected processes including `Resolve_effective_workflow`, `create_assistant_turn_endpoint`, `stream_assistant_turn_endpoint`, `Replay_workflow_from_step`).
  - `AgentsAndSkillsManagementService`: `12` symbol matches, `maxRisk: CRITICAL`, `131` impacted symbols (`agents_and_skills.py`, `_agents_lifecycle_guards.py`, `assistant_tools.py`, `_agents_and_skills_helpers.py`).
  - `materialize_pack_ontology` & `materialize_pack_catalog_items`: direct PG18 bundle materialization pipelines in `packages/orcia-core/src/orcia_core/packs/_internal/`.
- **Exploration & Key Metrics**:
  - Verified Alembic schema in `20261126_311_declarative_packs_v2.py`: `workspace_pack_activations` enforces `UNIQUE (workspace_id, priority_order) DEFERRABLE INITIALLY DEFERRED` and `UNIQUE (workspace_id, pack_slug)`; `catalog_items` enforces partial unique index `(pack_bundle_id, resource_id) WHERE pack_bundle_id IS NOT NULL`; `ontology_concepts`, `ontology_relations`, `ontology_axioms`, and `permission_broker_policies` all carry `pack_bundle_id`.
  - `_sql_pack_entity_materializer.py` already keys `catalog_items.resource_id` as `{pack_slug}:{entity_slug}`, allowing overlapping entity slugs across distinct bundles in PG18.
  - `packages/ui/src/primitives/AssistantAutocompleteDropdown.tsx` regex `/(?:^|\s)(@|\/)([a-zA-Z0-9_-]*)$/` blocks `/` inside query tokens after `@`; extending it to allow `/` and `:` supports typing `@pack/slug` and `pack:slug`.
- **Refactoring Opportunities & Emerging Technical Debt Mitigation**:
  - Extract pure `QualifiedEntityRef` parsing/formatting/flat candidate resolution into `packages/orcia-core/src/orcia_core/domain/namespacing.py` (`<= 220` L), wrapped and re-exported with `PackEntityCollisionError` in `packages/orcia-core/src/orcia_core/packs/namespacing.py` (`<= 120` L) — reusable by `packs`, `orchestration`, `agents`, `workflows`, `catalog`, and `apps/api`.
  - Keep `sql_agents_and_skills.py` (`299` L) and `agents_and_skills_manager.py` (`295` L) under `300` lines by delegating hydration/SQL query extensions to `_sql_agents_hydration.py` and `domain/namespacing.py`.

---

## 2. Implementation Plan

### 2.1 Data Schema & Alembic Migrations
- **No new Alembic revision required**: `20261126_311_declarative_packs_v2.py` already provisioned `workspace_pack_activations` (with `DEFERRABLE INITIALLY DEFERRED` priority ordering), `pack_dna_mechanisms`, and `pack_bundle_id` partial unique indexes on `catalog_items`, `ontology_concepts`, `ontology_relations`, `ontology_axioms`, and `permission_broker_policies`.

### 2.2 Hexagonal Core, Orchestration & Workers (`packages/orcia-core/`)
- `packages/orcia-core/src/orcia_core/domain/namespacing.py` & `packages/orcia-core/src/orcia_core/packs/namespacing.py` (`<= 300` L each):
  - `parse_qualified_entity_ref`: parses `@<pack_slug>/<slug>`, `/<pack_slug>/<slug>`, `orcia://packs/<pack_slug>/<kind>/<slug>` (including `@<semver>` / `:<semver>`), normalizes `pack://` alias and `<pack_slug>:<entity_slug>` alias into `(pack_slug, slug, is_qualified, is_workspace_scope)`.
  - `format_agent_mention`, `format_skill_command`, `format_pack_resource_uri`: canonical `D6.a` formatters.
  - `resolve_workspace_entity_candidates`: evaluates flat precedence (`WORKSPACE_OVERRIDE` > active `WORKSPACE_PACK` by `priority_order ASC` > `SYSTEM_PACK`), computes `is_colliding` & `collision_pack_slugs`, and optionally raises `PackEntityCollisionError` (`409 ERR_PACK_ENTITY_AMBIGUOUS`) on ambiguous strict disambiguation.
- `packages/orcia-core/src/orcia_core/packs/errors.py` & `_error_catalog.py`: add `PackEntityCollisionError` (`409 ERR_PACK_ENTITY_AMBIGUOUS`) with bilingual `fr`/`en` RFC 9457 copy.
- `packages/orcia-core/src/orcia_core/catalog/cas_resolver.py`: normalize `pack://...` alias to `orcia://packs/...` inside `parse_federated_uri`.
- `packages/orcia-core/src/orcia_core/orchestration/`:
  - Extend `ManagedAgentRecord` & `ManagedSkillRecord` with `pack_slug`, `qualified_ref`, `is_colliding`, `collision_pack_slugs`, `resolution_tier`.
  - Update `sql_agents_and_skills.py` & `_sql_agents_hydration.py` to `LEFT JOIN declarative_pack_bundles` and optional workspace pack activations so PG18 loads preserve `pack_slug`, compute `qualified_ref` (`@<pack>/<slug>` or `@workspace/<slug>`), and detect cross-pack slug collisions without mutating `pack_bundle_id` rows.
  - Update `AgentsAndSkillsManagementService` to annotate collision/resolution metadata and resolve entities by qualified ref or flat priority order.
- `packages/orcia-core/src/orcia_core/ontology/resolver.py` & `packages/orcia-core/src/orcia_core/packs/_internal/sql_pack_ontology_resolution.py` (`<= 300` L):
  - Extend `OntologyHierarchyResolver` to support `WORKSPACE_PACK` concepts/relations/axioms ordered strictly flat (`4_RUN_EPHEMERAL > 3_WORKSPACE (workspace overrides) > WORKSPACE_PACK (priority_order ASC) > 3_TEAM > 2_DOMAIN > 1_ENTERPRISE > SYSTEM_PACK`).
  - Add `resolve_workspace_pack_ontology_pg` in `sql_pack_ontology_resolution.py` returning effective ontology concepts, relations, axioms, `pack_dna_mechanisms`, `permission_broker_policies`, and pack `INSTRUCTION` items for a workspace, strictly honoring `workspace_pack_activations.priority_order ASC` and `DEFERRABLE` priority swaps.

### 2.3 Backend API, Security & Contracts (`apps/api/`, `packages/api-client/`)
- `apps/api/src/orcia_api/errors/_registry_extra_classes.py`: expose `PackEntityCollisionError`.
- `apps/api/src/orcia_api/schemas/agents_and_skills.py`, `apps/api/src/orcia_api/routers/agents_and_skills.py`, `_agents_and_skills_helpers.py`, `_agents_lifecycle_guards.py`:
  - Expose `pack_slug`, `qualified_ref`, `is_colliding`, `collision_pack_slugs`, `resolution_tier` on `AgentItemResponse` and `SkillItemResponse`, plus optional `workspace_id` / `strict_disambiguation` resolution query/endpoint support.
  - Support qualified `@<pack_slug>/<slug>` and `<pack_slug>:<slug>` in `_agents_lifecycle_guards.py` and `_assistant_tool_catalog.py`.
- `apps/api/src/orcia_api/routers/ontology_and_rag.py`, `_ontology_resolve_guards.py`, `schemas/ontology_and_rag.py`, `assistant_workspace_governance.py`, `_assistant_ontology_context.py`, `dependencies/workspace_and_packs.py`:
  - Wire flat workspace-pack ontology, DNA mechanisms, policies, and pack instructions into `/api/v1/ontology-rag/ontology/resolve`, `/api/v1/assistant/governance`, and live Assistant turn context assembly.
- Regenerate `packages/api-client` OpenAPI JSON & TypeScript SDK (`0-diff` verified via `scripts/export_openapi.py --check`).

### 2.4 User Interface & Experience (`apps/web/`, `packages/ui/`)
- `packages/ui/src/components/AgentsAndSkillsTypes.ts` & `packages/ui/src/primitives/AssistantAutocompleteDropdown.tsx`:
  - Add optional `packSlug`, `qualifiedRef`, `isColliding`, `collisionPackSlugs`, `resolutionTier` to `UiManagedAgentItem` / `UiManagedSkillItem`; allow `/` and `:` in autocomplete trigger/replacement regexes and sanitize `data-testid` safely.
- `apps/web/src/components/agentDtoMappers.ts`, `apps/web/src/features/inbox/assistantAutocompleteHelpers.ts`, and `apps/web/src/__tests__/setup/workspacesAndCatalogMockHandlers.ts`:
  - Map `pack_slug`, `qualified_ref`, `is_colliding`, `collision_pack_slugs`, `resolution_tier` from `@orcia/api-client` DTOs.
  - Display origin attribution (`pack_slug`) in autocomplete badges and insert canonical qualified `@<pack_slug>/<slug>` / `/<pack_slug>/<slug>` whenever a slug collides, while keeping short `@<slug>` / `/<slug>` when unique.

### 2.5 Test Pyramid Impact Analysis (`AD-17` — Layers 1 to 5 + Security)
- **Layer 1a (Python Unit `tests/unit/packs/`)**:
  - `tests/unit/packs/test_story_31_3_namespacing_and_flat_ontology.py`: parsing (`@pack/slug`, `/pack/slug`, `pack:slug`, `orcia://packs/...`, `pack://` alias), formatting, collision detection, `409 ERR_PACK_ENTITY_AMBIGUOUS`, flat priority resolution (`workspace_override > priority 1 > priority 2 > SYSTEM`), zero pack-to-pack inheritance.
  - `tests/unit/packs/test_story_31_3_ontology_and_autocomplete.py`: `OntologyHierarchyResolver` flat `WORKSPACE_PACK` tie-breaking, `AgentsAndSkillsManagementService` qualified resolution, `_assistant_tool_catalog` collision safety, `test_core_domain_isolation.py` green.
- **Layer 1b (Frontend Vitest `apps/web/`)**:
  - Targeted Vitest unit test covering `assistantAutocompleteHelpers` collision insertion (`@<pack>/<slug>` and `/<pack>/<slug>` on collision vs unique `@<slug>` / `/<slug>`, plus origin attribution badge).
- **Layer 2 (Vertical Integration `HTTP FastAPI -> PostgreSQL 18` `tests/integration/`)**:
  - `tests/integration/test_story_31_3_qualified_namespacing_and_ontology_postgres18.py`: real `create_app()` + `testcontainers` PostgreSQL 18 (`/tmp` sockets, `--no-cov`), importing 2 overlapping packs (`sdlc` & `legal-audit`), activating both at priority `1` vs `2`, verifying qualified listing & resolution, swapping priority atomically via `DEFERRABLE` constraint, verifying workspace override beats pack term, and verifying cold PG18 reads leave `pack_bundle_id` rows unmutated.
- **Layer 3 (OpenAPI 3.1 & Boundaries)**: `scripts/export_openapi.py --check` (`0-diff`), `lint-imports` (`5/5`), `mypy --strict`, `ruff`.

---

## 3. Summary of Changes & Results (Post-Implementation)

### 3.1 Created & Modified Files
- **Hexagonal Core (`packages/orcia-core/src/orcia_core/`)**:
  - **Domain & Catalog**: Created `domain/namespacing.py` (`131` L), `domain/_namespacing_parser.py` (`218` L), and `catalog/_uri_parser.py` (`85` L); updated `catalog/cas_resolver.py` (`258` L) to normalize `pack://` aliases to `orcia://packs/`.
  - **Packs**: Created `packs/namespacing.py` (`120` L), `packs/_internal/_sql_pack_flat_loaders.py` (`208` L), and `packs/_internal/sql_pack_ontology_resolution.py` (`146` L); updated `packs/__init__.py` (`153` L), `packs/errors.py` (`163` L), `packs/_error_catalog.py` (`160` L), and `packs/_internal/_sql_pack_entity_materializer.py` (`300` L).
  - **Ontology**: Updated `ontology/__init__.py` (`284` L), `ontology/models.py` (`188` L), `ontology/resolver.py` (`263` L), `ontology/translator.py` (`223` L), `ontology/context_ranker.py` (`293` L), `ontology/impact_and_promotion.py` (`235` L), `ontology/_internal/sql_ontology_mappers.py` (`255` L), and `ontology/_internal/sql_ontology_queries.py` (`174` L).
  - **Orchestration & Agents**: Created `orchestration/_agents_namespacing.py` (`232` L) and `orchestration/_internal/_sql_agents_pack_queries.py` (`118` L); updated `orchestration/_agents_and_skills_types.py` (`176` L), `orchestration/_agents_and_skills_executor.py` (`277` L), `orchestration/_agents_and_skills_mixin.py` (`226` L), `orchestration/agents_and_skills_manager.py` (`293` L), `orchestration/_internal/_sql_agents_hydration.py` (`261` L), `orchestration/_internal/sql_agents_and_skills.py` (`287` L), and `agents/_assistant_tool_catalog.py` (`287` L).
- **FastAPI Backend & OpenAPI SDK (`apps/api/`, `packages/api-client/`)**:
  - Created `apps/api/src/orcia_api/schemas/_ontology_search.py` (`51` L); updated `dependencies/assistant_tools.py` (`213` L), `dependencies/_topology_sync.py` (`205` L), `errors/_registry_extra_classes.py` (`29` L), `routers/agents_and_skills.py` (`263` L), `routers/_agents_and_skills_helpers.py` (`280` L), `routers/_agents_lifecycle_guards.py` (`147` L), `routers/assistant_workspace_governance.py` (`201` L), `routers/_assistant_ontology_context.py` (`106` L), `routers/ontology_and_rag.py` (`283` L), `routers/ontology_rag_helpers.py` (`275` L), `routers/_ontology_resolve_guards.py` (`270` L), `schemas/agents_and_skills.py` (`297` L), and `schemas/ontology_and_rag.py` (`276` L).
  - Regenerated `packages/api-client/openapi.json`, `packages/api-client/src/generated/agents_and_skills.ts`, `packages/api-client/src/generated/schema.ts`, and updated `packages/api-client/src/domains/{agentsAndSkills,bootstrapAndOntology}.ts` (`145` L / `272` L).
- **Frontend UI & SPA (`packages/ui/`, `apps/web/`)**:
  - Updated `packages/ui/src/components/AgentsAndSkillsTypes.ts` (`217` L), `packages/ui/src/primitives/AssistantAutocompleteDropdown.tsx` (`79` L), `packages/ui/src/primitives/AssistantPromptPlusAndAutocomplete.tsx` (`267` L), `apps/web/src/components/agentDtoMappers.ts` (`112` L), and `apps/web/src/features/inbox/assistantAutocompleteHelpers.ts` (`236` L).
- **Tests & Mocks (`tests/`, `apps/web/src/__tests__/`)**:
  - Created `tests/unit/packs/test_story_31_3_namespacing_and_flat_ontology.py` (`267` L), `tests/unit/packs/test_story_31_3_ontology_and_autocomplete.py` (`184` L), `tests/unit/packs/test_story_31_3_flat_loaders_and_parser_edges.py` (`254` L), `tests/integration/_story_31_3_pack_fixture.py` (`80` L), `tests/integration/test_story_31_3_qualified_namespacing_and_ontology_postgres18.py` (`257` L), `apps/web/src/__tests__/story-31-3-autocomplete-collision.test.ts` (`142` L), `apps/web/src/__tests__/setup/agentsAndSkillsMockHandlers.ts` (`200` L), and `apps/web/src/__tests__/setup/dnaMechanismsMockHandlers.ts` (`122` L); updated `apps/web/src/__tests__/setup/workspacesAndCatalogMockHandlers.ts` (`220` L) and unit test stubs (`test_agents_and_skills_router_and_service.py`, `test_story_20_2_ontology_permissions_and_promotions.py`, `test_story_26_6b_security_and_composition_root.py`).

### 3.2 Quantitative Metrics & Branch Coverage
- **Line-Count Guard (`wc -l <= 300`)**: `100%` of created/modified non-generated `.py`, `.ts`, and `.tsx` production files (max `300` L) and all newly created Story `31.3` test/fixture/mock files (max `267` L) comply with `<= 300` lines.
- **Scoped `--branch` Coverage (`>= 90%`)**: **`98%`** across the `7` Story `31.3` core/API namespacing & flat ontology modules (`domain/_namespacing_parser.py` `96%`, `domain/namespacing.py` `100%`, `orchestration/_agents_namespacing.py` `96%`, `orchestration/_internal/_sql_agents_pack_queries.py` `100%`, `packs/_internal/_sql_pack_flat_loaders.py` `100%`, `packs/_internal/sql_pack_ontology_resolution.py` `100%`, `packs/namespacing.py` `100%`; `304` Stmts, `2` Miss, `110` Branch, `7` BrPart across `95` tests in `tests/unit/packs/` + `tests/unit/core/test_core_domain_isolation.py`; `--fail-under=90` passed).
- **Static & Architecture Gates**:
  - `.venv/bin/ruff check .`: `All checks passed!`
  - `.venv/bin/ruff format --check .`: `1834 files already formatted`
  - `.venv/bin/mypy --strict packages/orcia-core packages/orcia-connectors apps/api apps/worker`: `Success: no issues found in 901 source files`
  - `.venv/bin/lint-imports`: `Contracts: 5 kept, 0 broken.` (`944` files, `6,839` dependencies)
  - `.venv/bin/python .agent/skills/bmad-architecture/scripts/lint_spine.py --workspace docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24`: `total_findings: 0`
  - `.venv/bin/python scripts/export_openapi.py --check`: `exit 0` (`0-diff`)
  - `.venv/bin/detect-secrets-hook --baseline .secrets.baseline`: `exit 0` across all changed/added files.

### 3.3 AD-17 Test Pyramid & Vertical Wiring Verification
- **Layer 1a — Python Unit Tests (`tests/unit`)**: **`1,242 passed`** (`0` failures), including `test_core_domain_isolation.py`, Story `31.3` namespacing/flat-loader/ontology suites, AST anti-pattern audits, and `test_site_catalog_sync.py`.
- **Layer 1b & Frontend Monorepo (`pnpm turbo run lint typecheck test --concurrency=2`)**: **`9/9` tasks passed** (`@orcia/api-client`: `3` files / `20` tests; `@orcia/ui`: `40` files / `154` tests; `@orcia/web`: `96` files / `370` tests = **`544` JS/TS tests**, including `story-31-3-autocomplete-collision.test.ts`).
- **Layer 2 — Real PostgreSQL 18 + Redis 7.4 + SeaweedFS S3 `testcontainers` Integration (`--no-cov`)**: **`9 passed`** (`96.12s`, `0` failures) across `test_story_31_3_qualified_namespacing_and_ontology_postgres18.py`, `test_story_31_2_pack_import_and_day0_postgres18_s3.py`, `test_story_30_5_agent_governance_and_lifecycle_pg18.py`, `test_http_vertical_day0_and_agents_postgres18.py`, and `test_story_20_2_ontology_promotions_postgres18.py`.
- **Layer 3, 4 & Security (`tests/evals`, `tests/security`, `tests/contract`)**: **`193 passed`** (`0` failures).
- **Layer 5 — Playwright E2E**: Deferred to Epic `31` Story `31.7` closure E2E & security sweep (`sprint-status.yaml`), while Story `31.3` autocomplete & PG18 vertical contracts are covered by Vitest + PG18 `create_app()` tests.

### 3.4 GitNexus Verification
- `npx gitnexus analyze --index-only .`: `49,317 nodes | 180,705 edges | 805 clusters | 1520 flows`.
- `gitnexus_detect_changes({scope: "all"})`: `changed_count: 21`, `affected_count: 1519`, `changed_files: 47`, `risk_level: "critical"` (expected blast radius across `OntologyHierarchyResolver`, `AgentsAndSkillsManagementService`, and API ontology/agents/assistant context wiring; all `AD-17` Layers 1–4 & PG18 integration gates passed).
