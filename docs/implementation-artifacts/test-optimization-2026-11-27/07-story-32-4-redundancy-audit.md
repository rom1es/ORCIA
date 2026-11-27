# Story 32.4 — Repo-Wide Test Pyramid Pruning, Coverage Safety Gate & Mutation Audit

**Date**: 2026-11-27
**Story**: `32-4-repo-wide-test-pyramid-pruning-with-coverage-safety-gate` (`Epic 32 — Lot 4`, `T-D11`)
**Tooling**: `scripts/test_redundancy_audit.py` (`coverage.CoverageData` API, `dynamic_context = test_function` via temporary `.ini` outside `pyproject.toml`)

---

## 1. Pre-Prune vs. Post-Prune Pyramid Inventory (Apples-to-Apples)

| Layer | Pre-Prune Files | Pre-Prune LOC | Post-Prune Files | Post-Prune LOC | Net Delta |
| --- | ---: | ---: | ---: | ---: | ---: |
| `tests/unit` (excl. `packs/`, `tooling/`) | 209 | 63,725 | 205 | 59,813 | -4 files, **-3,912 LOC** |
| `tests/unit/packs` | 38 | 8,708 | 22 | 4,772 | -16 files, **-3,936 LOC** |
| `tests/unit/tooling` | 11 *(pre-32.4)* | 1,964 | 12 | 2,115 | +1 file, +151 LOC |
| `tests/security` | 30 | 5,692 | 30 | 5,563 | 0 files, -129 LOC *(all red-team vectors kept)* |
| `tests/evals` | 9 | 1,551 | 9 | 1,551 | 0 *(Protected A/A2)* |
| `tests/contract` | 1 | 53 | 1 | 53 | 0 |
| `tests/integration` (PG18 / Redis / S3) | 108 | 31,982 | 108 | 31,915 | 0 files, -67 LOC *(`isolated_worker_pg18_env`)* |
| `apps/web/src/__tests__` (Vitest) | 134 | 34,583 | 134 | 34,528 | 0 files, -55 LOC |
| `packages/ui/src/__tests__` (Vitest) | 45 | 11,948 | 45 | 11,948 | 0 |
| `apps/web/e2e` (Playwright) | 46 | 7,995 | 46 | 7,995 | 0 *(0 E2E specs edited)* |
| **Proportionality (`lint_tests.py --ratchet`)** | — | **170,309 test / 276,531 prod (`0.62`)** | — | **162,618 test / 276,531 prod (`0.59`)** *(162,602 post-sync)* | **-7,691 test LOC (-4.52%)** |

- `fake_sql_engine_files` in `scripts/lint_tests_ratchet.json`: **46 -> 0 (`[]`)**.
- `legacy_story_test_files` in `scripts/lint_tests_ratchet.json`: **256 -> 236** (`-20` deleted `test_story_*.py` files; total `21` test files deleted including `_fake_sql_engine.py`, `2` created -> **-19 net files**).

---

## 2. Fake-SQL Elimination & Pruning Manifest (`46 -> 0`)

### 2.1 AST False-Positives Resolved (`5 -> 0`)
Tightened `_has_fake_sql_engine_ast` in `scripts/lint_tests_lib/checks.py` so hexagonal port stubs no longer match substring `"Sql"`, and renamed port/CLI test doubles cleanly:
- `tests/unit/test_story_26_5_routes_and_adapters.py`: `_FakeSqlHybridRagRepo` -> `_InMemoryHybridRagStub`
- `tests/unit/test_story_26_6b_security_and_composition_root.py` *(Protected A/A2)*: `_FakeSqlRag` -> `_InMemoryRagStub`
- `tests/unit/test_e2e_query_db_readonly.py`: `_FakeSqlConnection`/`_FakeSqlEngine` -> `_ReadonlyQuerySpyConn`/`_ReadonlyQuerySpyHandle`
- `tests/unit/test_e2e_reset_day0_guard.py`: `_FakeEngine`/`_FakeConn` -> `_DisposableHandle`/`_DisposableHandleTarget`
- `tests/unit/test_gemini_endpoint_resolver_coverage.py`: `_FakeEngine` -> `_NoopBeginCtxProvider`

### 2.2 Packs Fake-SQL Elimination (`21 -> 0`) & PG18 Consolidation
- **Deleted (17 files)**: `_fake_sql_engine.py`, `test_story_31_1_pack_repo_and_edge_cases.py`, `test_story_31_2_branch_coverage.py`, `test_story_31_2_packs_router_and_materializer.py`, `test_story_31_4_service_and_api_helpers_cov.py`, `test_story_31_4_sql_mutations_cov.py`, `test_story_31_4_sql_mutations_lock_cov.py`, `test_story_31_4_sql_queries_views_cov.py`, `test_story_31_4_sql_views_cov.py`, `test_story_31_5_anti_hostage_guards.py`, `test_story_31_5_closure_and_service_edges.py`, `test_story_31_5_composer_sql_crud.py`, `test_story_31_5_composer_targets.py`, `test_story_31_5_delete_routers_and_guards.py`, `test_story_31_5_publish_export_tx.py`, `test_story_31_5_reads_and_guard_cov.py`, `test_story_31_5_scope_target_matrix.py`.
- **Slimmed (fake SQL stripped; pure non-SQL unit tests retained)**: `test_story_31_1_codec_synthesis_and_seeder.py`, `test_story_31_2_pack_import_service.py` *(folded non-SQL `deps`/service guards)*, `test_story_31_2_packs_router.py`, `test_story_31_5_closure_analyzer_and_helpers.py` *(folded engine guards, non-draft views, FK column allowlist)*, `test_story_31_5_delete_rbac_and_legacy_export.py`, `test_story_31_5_export_scrubber.py`, `test_story_31_7_scope_and_pack_queries_cov.py`.
- **Table-driven consolidation (1 new file, `258 L <= 300 L`)**: `tests/unit/packs/test_pack_guard_matrix.py` (`@pytest.mark.story("31.4")`, `"31.5"`, `"32.4"`, parameterizing observer `403`, cross-tenant `403`, slot compatibility, and service delegation on `seeded_test_app`).
- **PG18 `isolated_worker_pg18_env` migration (keeping each module `<= 300 L`, excluding Alembic from-scratch suites)**:
  - `tests/integration/test_story_31_3_qualified_namespacing_and_ontology_postgres18.py` (215 L)
  - `tests/integration/test_story_31_4_hardening_guards_postgres18.py` (293 L)
  - `tests/integration/test_story_31_4_workspace_pack_activation_slots_postgres18.py` (288 L)
  - `tests/integration/test_story_31_5_pack_composer_and_export_postgres18.py` (286 L)
  - `tests/integration/test_story_31_5_rbac_and_roundtrip_postgres18.py` (265 L)

### 2.3 Inline Fake-SQL Unit Elimination (`20 -> 0`) & Epic 30 Consolidation
- **Deleted after folding unique pure logic (4 files)**:
  - `test_story_29_1_scope_resolution_extra.py` -> folded `post_hoc_service` property check into `test_story_29_1_scope_resolution.py` (PG18 `test_story_29_1_autonomous_runs_and_finops_pg18.py` covers SQL scope).
  - `test_story_29_3_governance_service_cov.py` -> folded in-memory/RBAC fallback assertions into `test_story_29_3_governance_mappers_cov.py`.
  - `test_story_30_3_workflows_and_bridge_coverage.py` -> folded dependency/rehydration unit checks into `test_story_30_3_processes_live_llm_and_pending_runs.py`.
  - `test_story_30_6_lifecycle_and_modal_guards_audit.py` -> duplicate structural/lifecycle audit covered by `test_story_30_5_agents_lifecycle_and_mcp.py` and `epic-30-ux-hardening-audit.test.ts`.
- **Fake-SQL sections stripped while preserving pure unit & `create_app()`/`seeded_test_app` tests (18 files)**: `connectors/test_bounded_workflow_v2_encapsulation.py`, `test_agents_and_skills_router_and_service.py`, `test_contextual_help_route_resolution.py`, `test_declarative_packs_and_durable_wizards_persistence.py`, `test_orchestration_governance_gates_and_kill_switch_guard.py`, `test_smtp_otp_and_sql_auth_adapters.py`, `test_story_20_1_org_delegation_and_audit_scope.py`, `test_story_20_2_ontology_permissions_and_promotions.py`, `test_story_22_2_waivers_and_root_invitations.py`, `test_story_25_1_personal_workspace_and_accostage.py`, `test_story_25_5_assistant_without_embedding_and_datasource_guard.py`, `test_story_26_4b_governance_feedback_folders_and_audit.py`, `test_story_26_5_coverage_branches.py`, `test_story_26_6a_queries_and_broker_concurrency.py`, `test_story_26_8_dbos_wiring_and_hydration.py`, `test_story_29_3_governance_mappers_cov.py`, `test_story_30_3_sql_stores_and_llm_coverage.py`, `test_story_7_2_triggers_coverage.py`.

### 2.4 Performance, Vitest & Hub Impact Fixes
- **`RepoSourceIndex` wiring**: Converted `rglob` walks across 4 slow AST audits (`test_zero_orphan_sql_adapters_audit.py`, `tests/unit/core/test_core_domain_isolation.py`, `test_i18n_backend_catalog_and_english_dev_audit.py`, `test_story_26_10_epic_26_closure_ast_and_routes_audit.py`) to `get_repo_source_index(REPO_ROOT)`.
- **Vitest**: Slimmed redundant fs-grep regex assertions in `apps/web/src/__tests__/epic-30-ux-hardening-audit.test.ts` while retaining all 3 behavioral jsdom guards (`[role='alert']`, 7-state `ProcessRunActionBanner` primary CTA count matrix, `DRAFT` autocomplete exclusion). Left `i18n-and-shell.test.tsx`, `story-29-5-folders-fetch-race-guard.test.tsx`, and OpenAPI Vitest mocks for Story `32.5`.
- **Stage 2 Hub Blind Spot Closed**: Added `HUB_WIRING_SMOKE_TESTS` in `scripts/agent_check_lib/impact.py` (blocking 84-file PG18 fan-out while mapping hub edits to `< 3 s` smoke tests `tests/unit/tooling/test_shared_test_infra.py` and `tests/unit/test_story_7_0c_openshift_scc_kustomize_and_ready.py`), verified by `tests/unit/tooling/test_stage3_coverage_and_impact_recall.py`.

---

## 3. Protected `A`/`A2` & Security Vector Retention Map

| Protected Surface | Status | Adversarial Vectors / Assertions Retained |
| --- | --- | --- |
| Cross-tenant `403` PG18 (`test_story_30_3_pending_runs_and_live_guard_postgres18.py`, `test_story_29_1_autonomous_runs_and_finops_pg18.py`) | **Untouched** | Real PG18 tenant isolation & live guard enforcement |
| `test_story_26_6b_security_and_composition_root.py` / `governed_tool_router` | **Stub renamed only (`_InMemoryRagStub`)** | All `70/70` checks across the 5 AST-fixed suites pass |
| `tests/security/test_story_31_7_packs_red_team_security.py` (`174 L`), `test_story_31_7_packs_isolation_and_guards.py` (`198 L`) & `_packs_red_team_fixtures.py` (`194 L`) | **Fake-SQL removed, module-scoped app** | 100% of zip-slip (`../evil.md`, `/etc/passwd`), symlink (`link.md`), executable hooks (`scripts/r.sh`, `agents/h.py`, YAML `hooks:`), export PII/internal host leak (`422 ERR_PACK_PII_OR_INFRA_LEAK`), `16` cross-workspace `403`, `14` observer `403`, `GLOBAL` escalation `403`, tenant filtering, and `422 ERR_PACK_SLOT_UNBOUND` fail-closed guards kept |
| Supporting unit/security vectors (`test_story_31_1_security_and_starlark_dos.py`, `test_story_31_5_export_scrubber.py`, `test_story_7_0a_log_secret_masking.py`, `test_story_26_1_guards_and_ssrf_policy.py`) | **Intact / fake-SQL stripped only (`31_5`)** | 100% of zip-bomb, `yaml.load`, Starlark DoS (`31_1`), export PII/secret scrub (`31_5`), AWS key / JWT log secret masking (`7_0a`), and SSRF / private RFC1918 guard vectors (`26_1`) kept |
| `tests/security/test_story_30_6_prompt_leak_and_draft_redteam.py` | **Module-scoped `create_seeded_test_app`** | 100% of prompt-leak, path-traversal, and `DRAFT` bypass payloads kept |
| `tests/evals/` (`30_2`, `26_10`, `26_5`, `6_2`, `6_3`) | **Untouched** | 100% of prompt/SSE/eval golden baselines intact |
| `apps/web/src/__tests__/story-29-5-folders-fetch-race-guard.test.tsx` & `apps/web/e2e/` (`02`, `08`, `12`, `30`, `31`) | **Untouched** | Zero E2E specs edited |

---

## 4. Apples-to-Apples Combined `(Unit + PG18)` Coverage Safety Gate

Executed on the **exact same combined test scope** (`tests/unit/packs/` + 7 Epic 31 PG18 suites: `31_1_declarative_packs_v2_postgres18.py`, `31_2_pack_import_and_day0_postgres18_s3.py`, `31_3_qualified_namespacing_and_ontology_postgres18.py`, `31_4_hardening_guards_postgres18.py`, `31_4_workspace_pack_activation_slots_postgres18.py`, `31_5_pack_composer_and_export_postgres18.py`, `31_5_rbac_and_roundtrip_postgres18.py`) using `coverage.CoverageData` with `dynamic_context = test_function` (temp `.agent_check/audit_cov.ini`):

| Metric | Pre-Prune `(Unit + 7 PG18)` | Post-Prune `(Unit + 7 PG18)` | Delta / Verification |
| --- | ---: | ---: | --- |
| Scope-filtered executed arcs (`packs/` + `pack_draft_guard.py` + `packs/workspace_packs/pack_composer` routers) | 11,520 | 11,009 | -511 arcs (-4.4%) |
| Scope-filtered executed lines | 8,124 | 7,815 | -309 lines (-3.8%) |
| Production modules in workspace (`927` tracked) | 927 | 927 | — |
| Non-SQL routers / codec / guard / service losses (`packs.py`, `workspace_packs.py`, `pack_composer.py`, `import_service.py`, `apm_codec.py`, `_pack_export_views.py`, `slot_guard.py`, `_pack_export_scrubber.py`) | — | **0 regressions** | **0 lost branches** after folding edge cases into unit/PG18 |
| Synthetic-SQL defensive branch diffs (`_sql_*.py` missing-table `to_regclass(...) is None` & defensive exception exits in `pack_draft_guard.py`, `composer_service.py`, `_pack_closure_analyzer.py`, `_pack_export_infra_loader.py`) | — | `-511` synthetic arcs | **Accepted** (fake-SQL-only missing-DDL/mock-error paths; business/security guards verified via 100% mutation kill score below) |

---

## 5. Three-Module One-Off Mutation Sample Results (`T-D11`)

Mutants were injected sequentially via an isolated `try ... finally` harness restoring exact SHA-256 bytes after each run (`git status -s packages/ apps/api/` verified clean):

| Target Module | Mutant | Guard Verified | Result |
| --- | --- | --- | --- |
| `_sql_workspace_pack_mutations.py` / `_sql_workspace_slot_bindings.py` | `M1A`: `priority_order < 1` -> `< 0` | Invalid activation priority `422` *(added PG18 check after initial pass surfaced gap)* | **KILLED** |
| `_sql_workspace_pack_mutations.py` / `_sql_workspace_slot_bindings.py` | `M1B`: `raise_on_missing=True` -> `False` | `422 ERR_PACK_SLOT_UNBOUND` on activation | **KILLED** |
| `_sql_workspace_pack_mutations.py` / `_sql_workspace_slot_bindings.py` | `M1C`: `if ds_row is None:` -> `if False:` | Cross-workspace datasource binding rejection `422` | **KILLED** |
| `_sql_workspace_pack_mutations.py` / `_sql_workspace_slot_bindings.py` | `M1D`: scheme mismatch `ds_scheme != slot_scheme` -> `False` | Incompatible scheme `422` *(added PG18 check after initial pass surfaced gap)* | **KILLED** |
| `pack_draft_guard.py` | `M2A`: `if fk_column not in _ALLOWED_FK_COLUMNS:` -> `if False:` | SQL column allowlist `ValueError` | **KILLED** |
| `pack_draft_guard.py` | `M2B`: `if not unlink_from_draft_packs:` -> `if False:` | Anti-hostage `409 ERR_ENTITY_REFERENCED_BY_PACK_DRAFT` | **KILLED** |
| `pack_draft_guard.py` | `M2C`: `if authorize_draft_cb is not None:` -> `if False:` | Per-draft authorization callback enforcement | **KILLED** |
| `pack_draft_guard.py` | `M2D`: `b.status = 'DRAFT'` -> `'ARCHIVED'` | Active draft reference detection before delete | **KILLED** |
| `sql_workflow_v2_runs.py` | `M3A`: `if self._session_maker is None:` -> `if True:` | PG18 persistence of workflow v2 runs | **KILLED** |
| `sql_workflow_v2_runs.py` | `M3B`: `and not payload.get("workspace_id")` -> `and False` | Cold PG18 rehydration `workspace_id` preservation | **KILLED** |
| `sql_workflow_v2_runs.py` | `M3C`: `if self._strict_sql: raise` -> `if False:` | Strict-SQL failure propagation *(added unit check after initial pass surfaced gap)* | **KILLED** |
| `sql_workflow_v2_runs.py` | `M3D`: `if row is not None:` -> `if False:` | `get_run` PG18 retrieval | **KILLED** |

**Final Mutation Kill Rate**: **12 / 12 (100.0 %)** *(initial baseline `9/12` caught 3 real guard gaps `M1A`, `M1D`, `M3C` introduced by fake-SQL removal, all 3 closed and verified killed)*.

---

## 6. `redundancy_audit_exempt_files` Ratchet Manifest (Reset to `[]` in Story 32.5)

All `45` entries in `redundancy_audit_exempt_files` inside `scripts/lint_tests_ratchet.json` correspond strictly to audited deleted (`20` `test_story_*` files) or fake-SQL/structural-slimmed (`25`) test files in Story 32.4 (`fake_sql_engine_files` = `[]`, `0` violations under `scripts/lint_tests.py --ratchet`). Story `32.5` resets `redundancy_audit_exempt_files` back to `[]` once Epic 32 pruning is merged.
