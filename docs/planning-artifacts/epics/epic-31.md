## Epic 31: Declarative APM-Compatible Business Packs, Unified Workspace Activation, Qualified Namespacing & Pack Composer (`Stories 31.1`..`31.7`)

Eliminate disk-to-memory pack silos and hardcoded TypeScript pack catalogs (`packs/` vs `packAgentsCatalog*.ts` vs `processStudioV2StructuralVsm.ts` vs orphan `declarative_pack_bundles` / `sql_declarative_packs.py`), replace dual runtime/draft sources with an **APM-Superset PostgreSQL 18 + SeaweedFS CAS bundle engine** (`declarative_pack_bundles` v2 + `pack_bundle_id` lineage across agents, skills, instructions, VSM/DAG workflows, ontology terms, DNA Starlark mechanisms, and policies), enforce **Workspace-only pack activation (`workspace_pack_activations`) with connector slot bindings (`workspace_pack_slot_bindings`) and `run_lock_manifests` SHA-256 pinning**, introduce **strict `{pack_slug}:{entity_slug}` qualified namespacing** with flat priority-ordered ontology resolution, and ship an **Authoring Pack Composer** (`CUSTOM` draft membership, anti-hostage unlink, dependency closure gate, PII/infra scrubbing) plus full bilingual Direction C UI (`Mes Packs`, Slot Binding Drawer, Composer Modal, `@pack:agent` / `/pack:skill` autocomplete), tracked in `docs/planning-artifacts/sprint-change-proposal-2026-11-25-epic-31-declarative-apm-packs-import-export.md` and `docs/implementation-artifacts/epic-31-decisions-grill-2026-11-25.md`.

### Story 31.1: `declarative_pack_bundles` v2 DDL & Native APM-Superset Manifest/Archive Codec (`D1`, `D3`, `D4`, `D6`)

As an ORCIA Platform Architect (`Winston`, `Karim UJ-9`),
I want an immutable PostgreSQL 18 schema v2 for declarative pack bundles (`declarative_pack_bundles` v2, `pack_bundle_id` FKs `ON DELETE CASCADE`, `pack_dna_mechanisms`, `pack` connector scheme + `orcia://packs/`, `pack_draft_memberships` `ON DELETE RESTRICT`, `workspace_pack_activations`, `workspace_pack_slot_bindings`) and a dependency-free YAML+Markdown frontmatter codec (`ApmPackCodec`),
So that ORCIA and GitHub APM packs parse, validate, canonicalize, and fail-closed on executable hooks in Python without any external Node runtime or new third-party dependency.

**Lot:** 1 — PG18 Schema v2 & Native APM Codec. **Dependencies:** `Epic 30`. **Agent:** `bmad-dev-worker` (`flash`) + `bmad-architect-worker` (`pro`) architecture contract review.
**Findings covered:** `D1`, `D3`, `D4`, `D6`, `A1`.
**CAPs covered:** `CAP-055`, `CAP-056`, `CAP-082`, `CAP-090`.
**Impacted files:** `infra/migrations/versions/20261126_311_declarative_packs_v2.py` (new), `infra/scripts/maintenance/_first_boot_reset_guards.py`, `packages/orcia-core/src/orcia_core/packs/` (domain models, ports, `errors.py`, `_internal/apm_codec.py`, `_internal/sql_declarative_packs.py`), `docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24/`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/31-1-pack-bundles-v2-ddl-and-native-apm-codec-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** Alembic migration `20261126_311_declarative_packs_v2.py` (`upgrade()` and tested `downgrade()`)
**When** applied on PostgreSQL 18 and checked against `first_boot_reset_guards` and `test_migrations.py`
**Then** `declarative_pack_bundles` v2 includes `bundle_kind` (`SYSTEM` | `ORG` | `IMPORTED` | `CUSTOM`), `archive_sha256`, `cas_object_key`, `manifest_yaml`, `source_origin`, `declared_slots_jsonb`, and `UNIQUE uq_pack_bundle_scope_slug_ver (scope_type, scope_id, slug, version)`; child tables (`catalog_items`, `workflow_definitions_v2`, `vsm_definitions_v2`, `ontology_*`, `permission_broker_policies`) carry nullable `pack_bundle_id` FK `ON DELETE CASCADE`; `pack_dna_mechanisms`, `pack_draft_memberships` (`ON DELETE RESTRICT`), `workspace_pack_activations` (`WORKSPACE` scope check + `DEFERRABLE INITIALLY DEFERRED` priority uniqueness), `workspace_pack_slot_bindings`, and `pack` scheme (`orcia://packs/`) in `connector_schemes` are created cleanly via raw SQL `op.execute(sa.text(...))`.

**Given** an incoming APM-Superset `.zip` archive or directory (`apm.yml`, optional `apm.lock.yaml`, `agents/*.agent.md`, `skills/<slug>/SKILL.md`, `instructions/*.instructions.md`, `workflows/{vsm-*,wf-*}.yaml`, `ontology/glossary.yaml`, `ontology/mechanisms/*.star`, `gates/*.yaml`, `policies/*.policy.md`, `help/{fr,en}/*.md`)
**When** parsed by `ApmPackCodec` (`orcia_core/packs`)
**Then** valid archives produce deterministic canonical `PackManifestV2` structures (`CAP-055` zero new third-party dependencies, `PyYAML` + `Pydantic v2` + stdlib `zipfile`/`ast`), reject zip-slip path traversal / oversize bombs, fail-closed with `HTTP 422 ERR_PACK_EXECUTABLE_HOOK_FORBIDDEN` (`AD-11` / `A1`) on any hook/script payload (`scripts/`, `hooks:`, executable extensions), and validate Starlark `.star` mechanisms against `AST` constraints (`AD-17` Layer 1/2 PG18 verified).

---

### Story 31.2: Transactional Pack Import Service, Day-0 System Pack Seeding & Purge of Disk/TS Pack Hardcoding (`D1`, `D2`, `D6`, `R1`)

As an ORCIA Platform Engineer and Workspace Lead (`Marc UJ-5`, `Karim UJ-9`),
I want a single transactional `PackImportService` (CAS upload to SeaweedFS + atomic PostgreSQL 18 upsert/version check + Day-0 seeding of `packs/sdlc` & `packs/orcia-docs`) and complete removal of runtime disk/TS pack catalogs (`packAgentsCatalog*.ts`, `_load_all_pack_definitions()`),
So that PostgreSQL 18 + SeaweedFS CAS is the single source of truth for packs, imports reject duplicate `(slug, version)` with `409 ERR_PACK_VERSION_CONFLICT`, and deleting/replacing pack bundles safely respects `run_lock_manifests`.

**Lot:** 2 — Transactional Import, Day-0 Seed & Single PG18 Source of Truth. **Dependencies:** `31.1`. **Agent:** `bmad-dev-worker` (`flash`).
**Findings covered:** `D1`, `D2`, `D6`, `R1`.
**CAPs covered:** `CAP-055`, `CAP-056`, `CAP-082`, `CAP-090`, `CAP-140`, `CAP-200`.
**Impacted files:** `packages/orcia-core/src/orcia_core/packs/`, `packages/orcia-core/src/orcia_core/bootstrap/seeder.py`, `infra/scripts/maintenance/09_reset_db_first_boot.py`, `apps/api/src/orcia_api/routers/packs.py`, `apps/api/src/orcia_api/routers/_workflows_helpers.py`, `apps/api/src/orcia_api/schemas/`, `apps/web/src/features/catalog/packAgentsCatalog*.ts` (deleted), `apps/web/src/features/processes/processStudioV2StructuralVsm.ts`, `packages/api-client/src/generated/`, `tests/integration/`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/31-2-transactional-pack-import-day0-seed-and-purge-disk-ts-hardcoding-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** `PackImportService` invoked during Day-0 bootstrap (`seeder.py` / `09_reset_db_first_boot.py`) or `POST /api/v1/packs/import` (`.zip` upload or JSON/YAML bundle)
**When** importing a validated bundle inside a single PostgreSQL 18 transaction (paired with SeaweedFS CAS storage of the archive)
**Then** all constituent entities (`agents`, `skills`, `instructions`, `workflows_v2`, `vsm_v2`, `ontology_terms`, `dna_mechanisms`, `policies`, bilingual `help`) upsert idempotently with `pack_bundle_id` set; re-uploading the same `(scope, slug, version)` with a different `archive_sha256` fails with `HTTP 409 ERR_PACK_VERSION_CONFLICT` (unless `replace_draft=true` on a `CUSTOM` draft); deleting an unused bundle cascades cleanly (`ON DELETE CASCADE`), whereas deleting a bundle pinned by an active run fails with `HTTP 409 ERR_RESOURCE_PINNED_BY_ACTIVE_RUNS` (`R1`).

**Given** a clean Day-0 reset (`pnpm db:reset`) and runtime boot of `apps/api` and `apps/web`
**When** querying pack agents, skills, processes, and VSM definitions
**Then** `packs/sdlc` and `packs/orcia-docs` are served exclusively from PostgreSQL 18 (`packAgentsCatalog.ts`, `packAgentsCatalogData.ts`, and runtime disk scans `_load_all_pack_definitions()` are purged, leaving zero TypeScript-hardcoded pack agent definitions or fallback VSM arrays in `apps/web` or `apps/api`) (`AD-17` Layer 2 PG18 + SeaweedFS verified).

---

### Story 31.3: Qualified `{pack_slug}:{entity_slug}` Namespacing & Flat Priority-Ordered Workspace Pack Ontology (`R3`, `R4`)

As an ORCIA User or Agent Author (`Hélène UJ-1`, `Karim UJ-9`) activating multiple packs in the same workspace,
I want canonical `{pack_slug}:{entity_slug}` identity across agents, skills, workflows, VSMs, and ontology keys (`@pack:agent`, `/pack:skill`) plus flat workspace pack resolution ordered by activation `priority_order` (with `workspace_overrides > priority_order ASC > SYSTEM`),
So that two packs with overlapping entity slugs never collide or silently overwrite each other, while local edits cleanly override without modifying upstream immutable bundles.

**Lot:** 2 — Qualified Namespacing & Flat Pack Resolution. **Dependencies:** `31.2`. **Agent:** `bmad-dev-worker` (`flash`).
**Findings covered:** `R3`, `R4`.
**CAPs covered:** `CAP-070`, `CAP-082`, `CAP-090`, `CAP-100`, `CAP-140`, `CAP-200`.
**Impacted files:** `packages/orcia-core/src/orcia_core/packs/`, `packages/orcia-core/src/orcia_core/orchestration/agents_and_skills_manager.py`, `packages/orcia-core/src/orcia_core/ontology/`, `apps/api/src/orcia_api/routers/agents_and_skills.py`, `apps/api/src/orcia_api/routers/ontology.py`, `apps/api/src/orcia_api/routers/assistant_workspace_governance.py`, `apps/web/src/features/inbox/assistantAutocompleteHelpers.ts`, `tests/integration/`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/31-3-qualified-pack-namespacing-and-flat-workspace-pack-ontology-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** two packs installed/activated in a workspace (`sdlc` and `legal-audit`) both declaring an agent or skill named `@reviewer` / `/compliance-check`
**When** persisting, listing, resolving `@` mentions / `/` skills, or executing agent/workflow references
**Then** backend resolution parses canonical `{pack_slug}:{entity_slug}` (`sdlc:reviewer`, `legal-audit:reviewer`), resolves ambiguous unqualified short names deterministically according to flat workspace priority (`workspace_overrides > priority_order ASC > SYSTEM`) or surfaces structured disambiguation candidates without crashing or mutating upstream `pack_bundle_id` rows (`R3`).

**Given** ontology glossary terms, business rules, DNA mechanisms, and pack instructions contributed by activated packs in a workspace
**When** resolving the effective workspace knowledge graph & ontology (`OntologyGovernanceService`, Assistant Layer 2, VSM/Process execution)
**Then** resolution evaluates strictly flat per-workspace activated packs in priority order (`workspace_overrides > priority_order ASC > SYSTEM`) using `DEFERRABLE` priority ordering without pack-to-pack inheritance graphs (`R4`, `AD-17` Layer 2 PG18 verified).

---

### Story 31.4: Workspace-Only Pack Activation, Connector Slot Bindings, `422 ERR_PACK_SLOT_UNBOUND` Gate & `run_lock_manifests` Pinning (`D2`, `D5`, `R2`, `R5`, `A3`)

As an ORCIA Workspace Lead (`Marc UJ-5`, `Sophie UJ-6`),
I want single-truth Workspace Pack Activation (`workspace_pack_activations` at `WORKSPACE` scope only), interactive binding of pack-declared logical connector slots (`git_repo`, `issue_tracker`, `wiki_space`, etc.) to concrete `workspace_datasources` / `enterprise_connectors`, a fail-closed `422 ERR_PACK_SLOT_UNBOUND` guard on activation/run start, and immutable SHA-256 + `resolved_pack_slots` pinning in `run_lock_manifests`,
So that activating or running a pack is deterministic, fail-closed on missing required integrations, and immune to background pack upgrades mid-run.

**Lot:** 3 — Workspace Activation, Slot Bindings & Run Pinning. **Dependencies:** `31.2`, `31.3`. **Agent:** `bmad-dev-worker` (`flash`) + `bmad-architect-worker` (`pro`) activation/lock contract review.
**Findings covered:** `D2`, `D5`, `R2`, `R5`, `A3`.
**CAPs covered:** `CAP-055`, `CAP-056`, `CAP-082`, `CAP-140`, `CAP-160`.
**Impacted files:** `packages/orcia-core/src/orcia_core/packs/`, `packages/orcia-core/src/orcia_core/orchestration/`, `packages/orcia-core/src/orcia_core/workflows/`, `apps/api/src/orcia_api/routers/packs.py`, `apps/api/src/orcia_api/routers/workflows.py`, `apps/api/src/orcia_api/schemas/packs.py`, `apps/api/src/orcia_api/errors/`, `packages/api-client/src/generated/`, `tests/integration/`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/31-4-workspace-pack-activation-slot-bindings-422-guard-and-run-lock-pinning-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** a pack declaring `slots` (required or optional logical capabilities, `connector_types`, `scheme`) and a Workspace Lead enabling or binding slots on a workspace (`POST /api/v1/workspaces/{id}/packs/{slug}/activate`, `PUT /api/v1/workspaces/{id}/packs/{slug}/slots`, `PUT /api/v1/workspaces/{id}/packs/reorder`)
**When** activating a pack or triggering a pack workflow run (`POST /api/v1/workflows-v2/runs`)
**Then** activating a pack or starting a workflow with any **required** slot unbound fails with `HTTP 422 ERR_PACK_SLOT_UNBOUND` listing exact `missing_slots`; successful slot binding writes `workspace_pack_slot_bindings`, emits `audit_ledger` `PACK_SLOTS_BOUND`, allows optional slots (`required: false`) to remain `optional_unbound`, and enforces `ScopeAccessGuard` (`READ_ONLY_OBSERVER` -> `403`, workspace role RBAC).

**Given** a workflow run started inside a workspace with active bound packs (`run_lock_manifests`)
**When** persisting the run lock manifest and later upgrading/deactivating the pack bundle in the workspace
**Then** `run_lock_manifests` records pinned `(bundle_id, slug, version, archive_sha256, resolved_pack_slots)` (`R5`), subsequent workspace pack upgrades/reorders do not mutate already running/paused workflow executions, and `PackBundle` deletion checks reject deleting bundles referenced by live pinned runs (`409 ERR_RESOURCE_PINNED_BY_ACTIVE_RUNS`, `AD-17` Layer 2 PG18 verified).

---

### Story 31.5: Pack Composer (`CUSTOM` Drafts), Anti-Hostage Unlink Guard, Dependency Closure Gate & PII/Infra-Scrubbed `.zip` Export (`D1`, `D4`, `A2`)

As an ORCIA Team Lead or Pack Author (`Karim UJ-9`, `Marc UJ-5`),
I want to compose custom packs (`CUSTOM` bundles) in PG18 from selected agents, skills, workflows, VSMs, ontology terms, DNA rules, and policies, enforce an anti-hostage guard when deleting member entities, block incomplete exports with `422 ERR_PACK_CLOSURE_INCOMPLETE`, and export deterministic, PII/infra-scrubbed APM `.zip` + `apm.lock.yaml` bundles,
So that teams can package, share, and safely re-import reusable ORCIA business packs without leaking workspace secrets, personal instructions, or broken dependencies.

**Lot:** 4 — Pack Composer, Anti-Hostage & Scrubbed Export. **Dependencies:** `31.1`, `31.4`. **Agent:** `bmad-dev-worker` (`flash`) + `bmad-architect-worker` (`pro`) export sanitizer & deletion-guard review.
**Findings covered:** `D1`, `D4`, `A2`.
**CAPs covered:** `CAP-055`, `CAP-056`, `CAP-090`, `CAP-140`, `CAP-200`.
**Impacted files:** `packages/orcia-core/src/orcia_core/packs/`, `packages/orcia-core/src/orcia_core/orchestration/agents_and_skills_manager.py`, `apps/api/src/orcia_api/routers/packs.py`, `apps/api/src/orcia_api/routers/agents_and_skills.py`, `apps/api/src/orcia_api/routers/workflows.py`, `apps/api/src/orcia_api/schemas/packs.py`, `packages/api-client/src/generated/`, `tests/integration/`, `tests/security/`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/31-5-pack-composer-anti-hostage-unlink-closure-gate-and-scrubbed-zip-export-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** a `CUSTOM` draft pack with selected entities recorded in `pack_draft_memberships` (`ON DELETE RESTRICT`)
**When** a user attempts to delete a member agent, skill, workflow, or VSM via standard entity `DELETE` endpoints
**Then** `DELETE` rejects with `HTTP 409 ERR_ENTITY_REFERENCED_BY_PACK_DRAFT` listing referencing draft packs; passing explicit confirmation `?unlink_from_draft_packs=true` detaches the draft memberships, logs `PACK_DRAFT_MEMBER_UNLINKED_ON_ENTITY_DELETE` in `audit_ledger`, and completes deletion cleanly (`A2`).

**Given** a pack export request (`POST /api/v1/packs/{bundle_id}/export`)
**When** computing the transitive dependency closure and generating the downloadable APM `.zip` archive (`application/zip` + `apm.yml` + `apm.lock.yaml` + clean asset files)
**Then** any missing cross-reference (`agent` -> missing `skill` / `workflow` -> missing `agent` / missing `ontology` or `policy`) blocks export with `HTTP 422 ERR_PACK_CLOSURE_INCOMPLETE` listing exact missing entities (or includes transitive dependencies when `auto_include_dependencies=true`); PII (`email`, personal instructions), `SecretRef`s, datasource URLs, workspace UUIDs, and model provider keys are strictly scrubbed (`422 ERR_PACK_PII_OR_INFRA_LEAK` if un-scrubbable secret/PII patterns remain in authored text); and re-importing the exported `.zip` into an isolated workspace round-trips `100%` faithfully (`AD-17` Layer 2 PG18 verified).

---

### Story 31.6: Direction C Bilingual FR/EN UI (`Mes Packs`, Slot Binding Drawer, Composer Modal & `@pack:agent` / `/pack:skill` Autocomplete) (`D1`, `D2`, `D5`, `R3`)

As an ORCIA End User and Workspace Lead (`Hélène UJ-1`, `Marc UJ-5`, `Karim UJ-9`),
I want a sober Direction C bilingual (`fr`/`en`) UI for discovering/importing/exporting packs, activating packs per workspace with priority ordering, binding logical connector slots via an interactive Drawer, composing `CUSTOM` packs via a step-by-step Composer modal (including anti-hostage unlink confirmation), and using qualified `@pack:agent` / `/pack:skill` autocomplete cleanly across `Mon Assistant` and `Mes Agents`,
So that the entire declarative APM pack lifecycle works smoothly in the browser, passes `F5` cold reload from PG18, and shows zero raw HTTP errors or dead buttons.

**Lot:** 5 — Direction C Bilingual UI & Full Frontend Wiring. **Dependencies:** `31.4`, `31.5`. **Agent:** `bmad-dev-worker` (`flash`).
**Findings covered:** `D1`, `D2`, `D5`, `R3`, `A2`.
**CAPs covered:** `CAP-055`, `CAP-056`, `CAP-070`, `CAP-082`, `CAP-090`, `CAP-100`, `CAP-140`, `CAP-200`.
**Impacted files:** `packages/ui/src/components/` (Pack registry table/cards, Slot Binding Drawer, Pack Composer Modal, Unlink confirmation dialog), `apps/web/src/features/packs/` or `settings/` & `workspaces/` & `catalog/`, `apps/web/src/features/inbox/assistantAutocompleteHelpers.ts`, `apps/web/src/i18n/locales/{fr,en}.ts`, `packages/api-client/src/generated/`, `apps/web/src/__tests__/`, `packages/ui/src/__tests__/`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/31-6-direction-c-bilingual-pack-registry-composer-slot-drawer-and-autocomplete-ui-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** `"Mes Packs"` (Settings Registry & Workspace Tab / Activation view) rendered in `fr` and `en`
**When** importing a `.zip` / YAML pack, activating/reordering workspace packs, binding slots in the Slot Binding Drawer, or creating/exporting a `CUSTOM` pack in the Pack Composer Modal
**Then** all flows strictly use `@orcia/api-client` (zero client business stores or hardcoded TypeScript packs), display inline `[role="alert"]` errors inside drawers/modals (highlighting missing required slots on `422 ERR_PACK_SLOT_UNBOUND` or closure gaps on `422 ERR_PACK_CLOSURE_INCOMPLETE` and prompting explicit unlink confirmation on `409 ERR_ENTITY_REFERENCED_BY_PACK_DRAFT`), survive full `F5` reload from PG18, obey `@orcia/ui` tokens & `<= 300`-line file modularity, and enforce `READ_ONLY_OBSERVER` read-only disabled controls.

**Given** `@` agent and `/` skill autocomplete in `Mon Assistant` and `Mes Processus` / `Mes Agents` cards
**When** packs with overlapping entity slugs are active in a workspace
**Then** UI badges display clear origin pack attribution + qualified `@pack:agent` / `/pack:skill` insertion on collision (concise friendly display when unique) with `0` console warnings or dead callbacks (`AD-17` Layer 1/3 Vitest + Playwright ready).

---

### Story 31.7: Epic 31 Security Red-Team, Export→Fresh-Workspace Round-Trip E2E, Contextual Help Sync & Closure (`D1`..`D6`, `A1`..`A4`)

As an ORCIA Maintainer, SecOps Reviewer & Product Owner (`Sophie UJ-6`, `Winston`, `Hélène UJ-1`),
I want full security red-team tests (zip-slip, executable hooks, PII/infra leaks, `ScopeAccessGuard` observer/cross-tenant isolation), clean bilingual Playwright Desktop E2E covering import → workspace activate → slot bind → compose → export → fresh-workspace re-import, updated Zone 4 help & architecture spine alignment, and formal `bmad-architect-worker` (`pro`) closure sign-off,
So that Epic 31's declarative APM pack platform ships verified across all 5 `AD-17` layers with zero regressions and `0` debt.

**Lot:** 6 — Security Lock, Round-Trip E2E & Epic 31 Closure. **Dependencies:** `31.6`. **Agent:** `bmad-dev-worker` (`flash`) + mandatory `bmad-architect-worker` (`pro`) final `VALIDATE` gate.
**Findings covered:** `D1`..`D6`, `R1`..`R5`, `A1`..`A4`.
**CAPs covered:** `CAP-055`, `CAP-056`, `CAP-070`, `CAP-082`, `CAP-090`, `CAP-091`, `CAP-100`, `CAP-140`, `CAP-160`, `CAP-200`, `CAP-260`.
**Impacted files:** `tests/security/`, `tests/evals/`, `apps/web/e2e/31-epic-31-declarative-apm-packs-roundtrip.spec.ts` (new), `docs/help/{fr,en}/*.md`, `docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24/`, `docs/product/capabilities.yaml`, `docs/implementation-artifacts/sprint-status.yaml`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/31-7-epic-31-red-team-security-roundtrip-e2e-help-sync-and-closure-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** the Epic 31 security red-team & bilingual E2E suite (`env -u ORCIA_E2E_SEED_FIXTURES`)
**When** executed against real PostgreSQL 18 + Redis + SeaweedFS containers and running SPA + FastAPI Composition Root
**Then** zip-slip traversal, `.sh`/`.py`/hook executable payloads (`422 ERR_PACK_EXECUTABLE_HOOK_FORBIDDEN`), PII/secret leaks in export (`422 ERR_PACK_PII_OR_INFRA_LEAK`), cross-workspace pack activation leaks, and `READ_ONLY_OBSERVER` `403` guards all fail closed; Day-0 `pnpm db:reset` boots `packs/sdlc` & `packs/orcia-docs` cleanly from PG18; and bilingual (`fr` & `en`) Desktop Playwright proves end-to-end compose -> export `.zip` -> fresh-workspace import -> slot bind -> `@pack:agent` execution -> `F5` cold reload.

**Given** full `AD-17` 5-layer verification and `bmad-architect-worker` (`pro`) `VALIDATE` review
**When** closing Epic 31
**Then** all production files remain `<= 300` lines, `.venv/bin/ruff check .`, `ruff format --check .`, `mypy --strict`, `lint-imports` (`5/5`), `lint_spine.py` (`0 findings`), `export_openapi.py --check` (`0-diff`), i18n Gates 1–4 (`0`), full `tests/unit` + `tests/evals` + `tests/security` + `tests/contract` + PG18+Redis+SeaweedFS integration (`>= 90%` branch coverage), `pnpm turbo run lint typecheck test`, Playwright Desktop E2E, `scripts/check_implementation_docs.py`, `pnpm site:sync && pnpm site:check`, and `npx gitnexus analyze` all pass, `CAP-xxx` entries remain `runtime`, `ACTION_ITEM-31.1..31.2` are tracked cleanly, and `epic-31` transitions to `done`.

---
