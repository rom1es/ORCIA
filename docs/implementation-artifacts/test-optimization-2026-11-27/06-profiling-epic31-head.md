# ORCIA Test & Gate Duration Profiling Report — Epic 31 HEAD (`720b07f`)

Baseline comparison against Epic 30 HEAD (`cf36f3c`) in [profiling_report.md](local transcript-analysis data, not versioned). All runs executed sequentially with `--no-cov` and `EXIT=0`.

## 1. Epic 30 vs Epic 31 Comparison & Collection Inventory

| Suite | E30 Files / Tests | E30 Wall (s/test) | E31 Files / Tests | E31 Collect | E31 Wall (s/test) | Growth Delta |
| --- | ---: | ---: | ---: | ---: | ---: | --- |
| `tests/unit` | 194 / 1,154 | 322.50 s (0.279) | 230 / 1,295 | 14.24 s | **391.61 s** (0.302) | +141 tests (+12.2%), **+69.11 s (+21.4%)** |
| `tests/evals` | 8 / 56 | *(in combined)* | 8 / 56 | 10.25 s | *(in combined)* | +0 tests, collect +2.37 s |
| `tests/security` | 26 / 135 | *(in combined)* | 28 / 141 | 10.86 s | *(in combined)* | +2 files, +6 tests (`test_story_31_7_*`) |
| `tests/contract` | 1 / 2 | *(57.45 s)* | 1 / 2 | 10.19 s | *(45.61 s)* | +0 tests, -11.84 s |
| `evals+security+contract` | 35 / 193 | 128.13 s (0.664) | 37 / 199 | — | **137.47 s** (0.691) | +6 tests (+3.1%), **+9.34 s (+7.3%)** |
| `tests/integration` | 84 / 117 | *(1 f: 27.19 s)* | 91 / 124 | 13.72 s | *(6 f: 132.39 s)* | +7 files (+74 `testcontainers` files), +7 tests |
| `@orcia/web` (Vitest) | 95 / 369 | 58.07 s (0.157) | 98 / 375 | *(203.25 s CPU)* | **56.67 s** (0.151) | +6 tests (+1.6%), -1.40 s (-2.4%) |
| `@orcia/ui` (Vitest) | 40 / 154 | 14.48 s (0.094) | 41 / 159 | *(111.38 s CPU)* | **14.88 s** (0.094) | +5 tests (+3.2%), +0.40 s (+2.8%) |

- **Import time (`import orcia_api.main`)**: **7,699.4 ms (~7.70 s)** cumulative (vs Epic 30 **5,990.4 ms / 5.99 s**, **+1.71 s / +28.5%**). Top cumulative: `orcia_api.main` 7699 ms (`self 399 ms`), `orcia_api.dependencies` 2953 ms, `assistant_tools` 2667 ms, `_assistant_tools_helpers` 2621 ms, `_assistant_guards` 1950 ms, `_core_providers` 1263 ms, `orcia_core.bootstrap` 1233 ms, `orcia_core.orchestration` 687 ms, `litellm_adapter` 668 ms, `fastapi` 627 ms.

## 2. `tests/unit` Breakdown (391.61 s wall; 373.74 s sum of 520 measured phases)

| Category | E31 Files | E31 Tests | E31 Sum | Root Cause |
| --- | ---: | ---: | ---: | --- |
| `create_app()` + `TestClient` boots | 63 | 299 | **159.68 s** | **129** `create_app(` calls across **89** `tests/unit` files (+28 in `e/s/c`), up from 118 |
| Testcontainers (PG18) in `tests/unit` | 6 | 25 | **54.24 s** | `3_2e`, `3_4`, `3_5`, `4_1`, `4_4`, `5_1` boot `pgvector:pg18` + `alembic` (+8.51 s vs E30) |
| AST / repo audits + `create_app()` | 17 | 111 | **54.02 s** | Combined `create_app()` + full-repo `rglob`/AST/route walks (`26_10`, `26_9`, `i18n`, etc.) |
| Real network / OTLP / CLI timeouts | 3 | 27 | **35.73 s** | DNS `down-host.local` (`19_5`, 10.13 s), OTLP `.local:4318` (`7_0b`, 10.07 s), `pytest`/`ruff` CLI (`4_1a`, 15.53 s) |
| AST / repo-wide audits (no `create_app`) | 14 | 67 | **28.19 s** | Full-repo `rglob("*.py")` / `rglob("*.ts*")` + `ast.parse()` across growing codebase |
| Pure unit tests | 126 | 758 | **22.54 s** | Fast in-memory unit logic (0.030 s/test) |
| Subprocess Python / CLI spawns | 1 | 8 | **19.34 s** | `test_platform_auth_policy_2fa_and_runtime_isolation.py` paying 7.7 s import tax per spawn |

**Top 30 Slowest `tests/unit` Test Phases:**
1. `10.09s call` `test_story_19_5_embedding_port_and_adapters.py::test_httpx_embedding_adapters_edge_cases_and_network_errors`
2. `8.79s call` `test_platform_auth_policy_2fa_and_runtime_isolation.py::test_runtime_persona_isolation_and_oidc_state_replay_protection`
3. `8.69s call` `test_story_26_10_epic_26_closure_ast_and_routes_audit.py::test_zero_legacy_routes_zero_require_rag_and_zero_story26_overrides`
4. `8.56s call` `test_openapi_security.py::test_real_create_app_openapi_enforces_bearer_auth_on_all_protected_operations`
5. `8.37s call` `test_story_26_9_duplicate_thread_turn_removal.py::test_send_collaborative_thread_turn_schemas_and_openapi_path_removed`
6. `8.24s call` `test_story_26_10_epic_26_closure_ast_and_routes_audit.py::test_zero_uncalled_assistant_routes_and_mcp_ask_exposure`
7. `7.25s call` `test_story_4_1a_bimodal_sandbox_and_roles.py::test_story_4_1a_container_spec_and_bimodal_tdd_red_green`
8. `7.07s call` `test_story_5_1_notifications_claim_and_resource_leases.py::test_alembic_0021_story_5_1_migration_on_real_postgres18`
9. `6.78s call` `test_story_3_2e_sdlc_pack_and_connectors.py::test_ac_e5_alembic_0013_and_0014_expand_contract_with_existing_rows`
10. `6.73s call` `test_story_4_4_jira_staged_actions_and_mcp.py::test_alembic_0019_expand_backfill_and_0020_contract_on_postgres`
11. `6.48s call` `test_story_4_1_sandbox_tier1_and_pattern_drift.py::test_story_4_1_migration_0017_real_postgres_container`
12. `6.18s call` `test_story_7_0b_log_sink_and_otel_tracing.py::test_otel_tracing_config_and_structlog_span_correlation`
13. `5.99s call` `test_story_3_4_human_anchors_and_arbitration.py::test_story_3_4_migration_0015_real_postgres_container`
14. `5.72s call` `test_story_3_5_challenge_and_replay.py::test_story_3_5_migration_0016_real_postgres_container`
15. `4.94s call` `test_i18n_backend_catalog_and_english_dev_audit.py::test_backend_prompt_locale_neutrality_and_french_literal_ratchet`
16. `4.34s call` `packs/test_story_31_5_delete_routers_and_guards.py::test_guarded_delete_routers_409_unlink_and_observer_403`
17. `4.17s call` `test_story_4_1a_bimodal_sandbox_and_roles.py::test_story_4_1a_five_deployment_roles_and_docling_isolation_and_api`
18. `4.11s call` `test_story_4_1a_bimodal_sandbox_and_roles.py::test_story_4_1a_tier2_isolation_network_fs_memory_and_timeout`
19. `4.01s call` `test_story_3_2s_dbos_spike.py::test_spike_steps_and_dramatiq_cohabitation_unit`
20. `3.85s call` `test_codebase_architectural_anti_patterns_audit.py::test_rule_2_zero_fake_word_split_streaming_in_sse_generators`
21. `3.77s call` `test_zero_orphan_sql_adapters_audit.py::test_every_core_internal_sql_adapter_is_wired_to_api_or_worker_runtime`
22. `3.76s call` `test_story_7_0b_log_sink_and_otel_tracing.py::test_ad23_reversibility_invariants_no_otel_log_exporter_and_compose_profiles`
23. `3.47s call` `test_story_26_10_epic_26_closure_ast_and_routes_audit.py::test_zero_testclient_or_blocking_sync_io_in_src_and_assistant_core`
24. `3.46s call` `test_i18n_backend_catalog_and_english_dev_audit.py::test_rfc9457_error_catalog_bilingual_completeness`
25. `2.92s call` `core/test_core_domain_isolation.py::test_core_domain_isolation_ast_and_regex`
26. `2.87s call` `test_story_3_4_human_anchors_and_arbitration.py::test_story_3_4_mandatory_human_anchor_and_agent_rejection`
27. `2.87s call` `test_story_26_7_unified_turn_engine_and_mcp.py::test_canonical_sse_v2_sequence_synthesize_now_approve_and_legacy_404`
28. `2.82s call` `test_story_30_6_lifecycle_and_modal_guards_audit.py::test_backend_draft_agent_blocked_across_assistant_processes_and_mcp`
29. `2.82s call` `test_story_26_8_continue_in_process_and_human_anchors.py::test_api_continue_in_process_folder_launch_anchor_sign_and_legacy_removal`
30. `2.75s call` `packs/test_story_31_5_composer_routers.py::test_pack_composer_router_and_dbapi_error_handlers`

**Top 15 Slowest `tests/unit` Files (per-file aggregate):** `test_story_26_10_epic_26_closure_ast_and_routes_audit.py` **21.61 s** (6t), `test_platform_auth_policy_2fa_and_runtime_isolation.py` **19.34 s** (8t), `test_story_4_1a_bimodal_sandbox_and_roles.py` **15.53 s** (3t), `test_story_3_4_human_anchors_and_arbitration.py` **11.26 s** (4t), `test_story_26_9_duplicate_thread_turn_removal.py` **10.69 s** (2t), `test_i18n_backend_catalog_and_english_dev_audit.py` **10.63 s** (3t), `test_story_19_5_embedding_port_and_adapters.py` **10.13 s** (8t), `test_story_3_5_challenge_and_replay.py` **10.12 s** (5t), `test_story_7_0b_log_sink_and_otel_tracing.py` **10.07 s** (16t), `test_story_26_7_unified_turn_engine_and_mcp.py` **9.69 s** (8t), `test_openapi_security.py` **8.81 s** (37t), `test_story_5_1_notifications_claim_and_resource_leases.py` **8.37 s** (5t), `test_story_4_1_sandbox_tier1_and_pattern_drift.py` **8.29 s** (4t), `test_story_4_4_jira_staged_actions_and_mcp.py` **8.27 s** (4t), `test_story_3_2e_sdlc_pack_and_connectors.py` **7.93 s** (3t). Note: non-`packs` files also slowed by +39.09 s due to heavier `create_app()` (new pack routes/services), +8.51 s on PG18 tests, and larger AST repo walks.

**NEW `tests/unit/packs/` Quantification:** **37 test files** (38 `.py` total), **144 tests**, **30.02 s** measured sum (**26.50 s / 88.3%** comes from the 9 files calling `create_app()`):
1. `test_story_31_4_p0_guards.py` — **5.28 s** (3 tests, `create_app`)
2. `test_story_31_4_workspace_packs_router.py` — **4.40 s** (2 tests, `create_app`)
3. `test_story_31_5_delete_routers_and_guards.py` — **4.34 s** (1 test, `create_app`)
4. `test_story_31_5_composer_routers.py` — **2.75 s** (1 test, `create_app`)
5. `test_story_31_5_delete_rbac_and_legacy_export.py` — **2.24 s** (2 tests, `create_app`)
6. `test_story_31_2_branch_coverage.py` — **2.06 s** (3 tests, `create_app`)
7. `test_story_31_2_packs_router.py` — **1.88 s** (1 test, `create_app`)
8. `test_story_31_5_reads_and_guard_cov.py` — **1.80 s** (2 tests, `create_app`)
9. `test_story_31_5_rbac_and_helpers_coverage.py` — **1.75 s** (1 test, `create_app`)
10. `test_story_31_1_apm_codec_and_security.py` — **1.65 s** (3 tests, no `create_app`)

## 3. `tests/evals`, `tests/security`, `tests/contract` (137.47 s wall, 199 tests)

- **Top slow files**: `tests/contract/test_openapi_contract.py` **45.61 s** (`schemathesis` **37.27 s** + `zero_diff_gate` **8.34 s**; 33.2% of suite), `test_story_26_1_assistant_security_hardening.py` **9.40 s**, `test_story_31_7_packs_red_team_security.py` **6.22 s**, `test_story_30_6_prompt_leak_and_draft_redteam.py` **3.83 s**, `test_story_31_7_packs_isolation_and_guards.py` **3.78 s**.
- **NEW `tests/security/test_story_31_7_*`**: **2 files, 6 tests**, **10.00 s** inside combined run (standalone wall **20.95 s** including ~7.7 s import; `packs_red_team_security.py` 6.33 s + `packs_isolation_and_guards.py` 3.93 s).

## 4. `tests/integration` & `test_story_31_*` (132.39 s for 6 files)

- **Inventory**: **91 test files** (`101 *.py`), **124 tests**; **74 `test_*.py` files** (`81 *.py`) invoke `testcontainers`. Still **0** `tests/integration/conftest.py`, **0** `scope="session"` fixtures, **62** `scope="module"` fixtures (up from 59).
- **NEW `tests/integration/test_story_31_*` (6 files, 6 tests, 132.39 s wall = 22.07 s/test)**:
  - Measured pytest phases = **128.41 s**: **container lifecycle** (`setup` 44.46 s + `teardown` 5.68 s) = **50.14 s (39.0%)**; **`call`** (`alembic upgrade head` + `create_app()` + SQL/S3 assertions) = **78.27 s (61.0%)**; ~4 s import startup.
  - Per-file: `31_5_pack_composer_and_export_postgres18.py` **28.68 s** (`7.37s setup / 20.35s call / 0.96s td`), `31_5_rbac_and_roundtrip_postgres18.py` **28.55 s** (`7.18s / 20.16s / 1.21s`), `31_2_pack_import_and_day0_postgres18_s3.py` **25.59 s** (`7.53s / 16.97s / 1.09s`), `31_4_hardening_guards_postgres18.py` **15.67 s** (`7.27s / 7.40s / 1.00s`), `31_4_workspace_pack_activation_slots_postgres18.py` **15.47 s** (`7.23s / 7.60s / 0.64s`), `31_3_qualified_namespacing_and_ontology_postgres18.py` **14.45 s** (`7.88s / 5.79s / 0.78s`).

## 5. Vitest `@orcia/web` & `@orcia/ui`

- **`@orcia/web`** (**56.67 s** wall; Vitest **55.03 s**; 98 files, 375 tests; `setup` 320.87 s + `collect` 203.25 s + `tests` 298.15 s + `env` 116.61 s CPU; `openapi.json` now **2.1 MB**). Top 10 slow files: `i18n-and-shell.test.tsx` **26.25 s** (26t), `zero-dead-buttons-and-silent-catches-audit.test.tsx` **9.77 s** (4t), `page-header-structure-and-visual-grammar-audit.test.tsx` **8.76 s** (25t), `story-17-2-org-hierarchy-and-modals.test.tsx` **8.00 s** (6t), `story-17-3-iam-accounts-matrix-and-secops-drawer.test.tsx` **7.47 s** (4t), `story-20-1-mon-organisation-and-scoped-activity.test.tsx` **7.24 s** (5t), `story-22-2-portals-tailwind-and-routes.test.tsx` **6.82 s** (6t), `story-16-4-reflexive-trace-wiring-and-f5.test.tsx` **6.42 s** (4t), `story-25-2-shell-9-items-org-admin-and-unified-scope.test.tsx` **5.92 s** (4t), `story-24-3-mcp-bench-packs-health-and-cockpit-wfkey.test.tsx` **5.68 s** (4t).
- **`@orcia/ui`** (**14.88 s** wall; Vitest **13.18 s**; 41 files, 159 tests; `collect` 111.38 s + `env` 48.22 s + `tests` 30.53 s CPU). Top 10 slow files: `assistant-workspace.test.tsx` **2.46 s** (10t), `agents-and-skills-studio-and-governance.test.tsx` **2.38 s** (2t), `four-zone-shell-and-cockpit.test.tsx` **2.27 s** (11t), `agents-and-skills.test.tsx` **2.08 s** (1t), `rgaa-modals-escape-unsaved-guard.test.tsx` **1.76 s** (10t), `story-30-5-agent-modal-save-and-status.test.tsx` **1.69 s** (3t), `story-24-4-css-modals-contrast-and-tabs.test.tsx` **1.42 s** (3t), `story-31-6-pack-ui-primitives.test.tsx` **1.03 s** (5t), `searchable-select.test.tsx` **0.92 s** (5t), `shell.test.tsx` **0.91 s** (3t).
