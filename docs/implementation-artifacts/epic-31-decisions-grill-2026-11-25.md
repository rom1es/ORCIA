# Architecture & Governance Decisions — Epic 31 (Declarative APM-Compatible Packs, Database Source of Truth, Composer & Scoped Import/Export)

- **Date:** `2026-11-25`
- **Branch:** `pack_import_export_analysis` (ready to branch/rename to `feat/epic-31-declarative-apm-packs-import-export` once Epic 30 merges into `main`)
- **Sequencing Gate:** **Starts strictly AFTER `Epic 30` (`feat/epic-30-assistant-processes-and-agents-ux-hardening`) merges into `main`**
- **Method:** Interactive `/grill-me` alignment & edge-case hardening session (`D1–D6`, refined by `R1–R5`, amended by `A1–A4`)
- **Related Artifacts:**
  - Architecture Blueprint & Sprint Proposal: [`sprint-change-proposal-2026-11-25-epic-31-declarative-apm-packs-import-export.md`](../planning-artifacts/sprint-change-proposal-2026-11-25-epic-31-declarative-apm-packs-import-export.md)
  - Active Preceding Epic (Do Not Collide): [`sprint-change-proposal-2026-11-25-epic-30-assistant-processes-and-agents-ux-hardening.md`](../planning-artifacts/sprint-change-proposal-2026-11-25-epic-30-assistant-processes-and-agents-ux-hardening.md)
  - Architecture Spine: [`ARCHITECTURE-SPINE.md`](../planning-artifacts/architecture/architecture-ORCIA-2026-10-24/ARCHITECTURE-SPINE.md) (`AD-2`, `AD-3`, `AD-5`, `AD-6`, `AD-7`, `AD-9`, `AD-15`, `AD-17`, `AD-19`, `AD-20`, `AD-21`, `AD-23`, `AD-24`)

---

## 1. Consolidated Active Decisions (`D1–D6` as Refined by `R1–R5` and Amended by `A1–A4`)

| ID | Topic | Effective Decision | Impacted Surfaces & ADs |
| :--- | :--- | :--- | :--- |
| **`D1`** | PG18 single source of truth & Day-0 seed boundary | **PostgreSQL 18 + SeaweedFS CAS (`cas/<sha256>`)** is the **100% runtime source of truth** for all Packs and their contents (agents, skills, workflows v2, VSMs v2, gates, ontology/DNA Starlark, Permission Broker policies, help articles). On-disk `packs/<domain>/` folders are used strictly as **Day-0 bootstrap seeds** fed into the exact same transactional import pipeline. All runtime disk reads (`packs.py`, `workflows.py`) and frontend `apps/web/src/features/catalog/packAgentsCatalog.ts` hardcoding are eliminated. | `AD-1`, `AD-20`, `AD-23` (`readOnlyRootFilesystem`) |
| **`D2` + `A1`** | Decoupled 4-level catalog visibility vs. `WORKSPACE`-only runtime activation | **Catalog Visibility & Authorship Governance** retains the 4 hierarchical scopes (`GLOBAL \| BU \| TEAM \| WORKSPACE`) on `declarative_pack_bundles` under 6-verb RBAC (`AD-21`, `HTTP 403 ERR_OBSERVER_MODE_READ_ONLY` for observers), governing who can discover, install, compose, or export a Pack. **Runtime Activation & Slot Binding** exist **strictly at the `WORKSPACE` level** (`workspace_pack_activations` + `workspace_pack_slot_bindings`) — zero runtime activation inheritance tree across `GLOBAL/BU/TEAM`. `dry_run=true` preview, SemVer immutability (`AD-21`), identical SHA-256 idempotency (`200 OK`), same-SemVer conflict (`409 ERR_PACK_VERSION_CONFLICT`), and active-run pinning guard (`409 ERR_RESOURCE_PINNED_BY_ACTIVE_RUNS`). | `AD-21`, `AD-20`, `AD-19` |
| **`D3`** | Visible APM-compatible superset layout (`Option A1`) | Root `apm.yml` (Microsoft APM fields + `x-orcia:` governance metadata & `connector_slots`) + `apm.lock.yaml` (deterministic per-file `SHA-256` lockfile) + visible root folders: `agents/*.agent.md` (YAML frontmatter + Markdown prompt), `skills/<slug>/SKILL.md` (Agent Skills spec + `x-orcia` frontmatter), `instructions/*.instructions.md`, `workflows/{vsm-*,wf-*}.yaml`, `ontology/glossary.yaml`, `ontology/mechanisms/*.star`, `gates/*.yaml`, `policies/*.policy.md`, `help/{fr,en}/*.md`. Importer also accepts `.apm/` paths and legacy `pack.yaml` / root `glossary.yaml`. Rejects `.apm/hooks/` & any executable scripts (`.py`, `.sh`, `.js`, `.ts`, `.wasm`). Parsed 100% natively in `PyYAML` + `Pydantic v2` (`0` new third-party dependency). | `AD-9`, `AD-20`, `ARCHITECTURE-SPINE.md` |
| **`D4`** | Smart readiness classification on import | Atomic PostgreSQL rollback (`HTTP 422`) on archive corruption, zip-slip/path-traversal, size/entry-count limits, `apm.lock.yaml` SHA-256 mismatch, broken internal `orcia://packs/...` references, missing `human_authored_required: true` on `HUMAN_ANCHOR` (`AD-3`), or failing Starlark `.star` `PASS`/`FAIL` vectors (`AD-9` `< 2 ms`). Certified `x-orcia:` entities passing all deterministic checks land directly as **`ACTIVE` / `PUBLISHED`** (usable immediately upon Workspace activation); incomplete external APM items lacking `x-orcia:` governance contracts (or marked `draft`) land safely as **`DRAFT` (`UNTESTED`)**, gated until validated in Studio (reusing Epic `30.5`). | `AD-3`, `AD-9`, `Epic 30.5` |
| **`D5`** | Safe & simple connector boundary (`Option B`) | Packs bind exclusively to ORCIA's pre-installed platform connectors (`packages/orcia-connectors`: `jira`, `confluence`, `git`, `db`, `codegraph`) via abstract `connector_slots` + declarative `PermissionBroker` policies (`policies/*.policy.md` -> `permission_broker_policies`). `apm.yml` `mcp:` declarations are preserved as requirement metadata with readiness badges (`0` new outbound HTTP/MCP transport attack surface added by Pack upload). Real outbound `httpx` MCP transport is deferred to `ACTION_ITEM-31.1`. | `AD-5`, `AD-6`, `AD-20` |
| **`D6.a` + `R1` + `A1`** | Strict runtime namespacing, structured-only rewriting & flat `WORKSPACE_PACK` ontology CTE | Runtime handles & canonical URIs are strictly namespaced (`@workspace/<slug>` vs `@<pack_slug>/<slug>`, `orcia://packs/<pack_slug>/<kind>/<slug>@<semver>`, aliasing legacy `pack://` on read). Snapshot rewriting touches **only structured AST/Pydantic reference fields** and runs a non-mutating prose linter warning on bare `@slug`/`/slug` in Markdown bodies. Publishing a Pack in an authoring Workspace does **not** auto-activate a duplicate copy back onto that Workspace unless explicitly requested. Flat `OntologyHierarchyResolver` precedence: `4_RUN_EPHEMERAL -> 3_WORKSPACE -> WORKSPACE_PACK (ordered by workspace_pack_activations.priority_order ASC) -> 3_TEAM -> 2_DOMAIN -> 1_ENTERPRISE`, enforced by `UNIQUE (workspace_id, priority_order) DEFERRABLE INITIALLY DEFERRED`. | `AD-7`, `AD-15`, `AD-21` |
| **`D6.b` + `R2`** | Pack Composer, `409` draft delete guard, anti-hostage unlink & `422` publish closure | Users can create a `DRAFT` Pack and cherry-pick existing Workspace Agents, Skills, Workflows/VSMs, and Ontology/Starlark items (`pack_draft_memberships` with `ON DELETE RESTRICT`). Deleting a referenced entity raises `HTTP 409 ERR_ENTITY_REFERENCED_BY_PACK_DRAFT` naming the blocking draft pack(s), paired with a 1-click atomic **"Unlink from draft & delete"** (`?unlink_from_draft_packs=true`) authorized for the entity owner, delegated `TEAM_LEAD`/`BU_LEAD`, or `PLATFORM_ADMIN` (preventing stale peer drafts from hostaging workspace entities; audited in `audit_ledger`). `Publish` enforces a `HTTP 422` transitive dependency & `ACTIVE`-status closure gate before freezing the immutable SemVer snapshot. | `AD-12`, `AD-21` |
| **`D6.c` + `R3–R5` + `A2–A3`** | `ConnectorSlot` de-binding, `O(1)` tokenized scrubber, explicit slot bind & `run-lock.json` slot pinning | Snapshot/Export replaces concrete `workspace_datasources` / `enterprise_connectors` UUIDs with `slot://<slot_key>` (`x-orcia.connector_slots` with `required: bool = true`) and normalizes `model_override` to `llm_model_tier: simple \| medium \| complex`. **`O(1)` Single-Pass Tokenized Export Scanner (`A3`)** checks extracted tokens against pre-loaded `frozenset` tenant infra IDs/URLs/emails, allows standard `$schema` namespaces, blocks RFC 1918/loopback/link-local/`.internal`/`.local` hosts & secrets, and rejects any email literal outside `apm.yml` `author`/`maintainers`. Slot Mapping Drawer pre-selects candidates visually only (**zero silent auto-bind `R4`**). Pre-execution `PackSlotReadinessGuard` rejects unbound `required: true` slots with `HTTP 422 ERR_PACK_SLOT_UNBOUND`, freezes `BOUND` concrete IDs into `run-lock.json` (`resolved_pack_slots`), and strips unbound `required: false` slots while logging `optional_unbound` (`null`) in `run-lock.json`. | `AD-2`, `AD-3`, `AD-5`, `AD-6`, `AD-21`, `NFR-SEC-4` |
| **`A4`** | Explicit `Story 30.5` coordination rule (zero throwaway work) | **Epic 30 executes first; Epic 31 executes right after Epic 30 merges to `main`.** `Story 30.5` is scoped strictly to `AgentDetailAndSandboxModal` UX deduplication, inline `[role="alert"]`, explicit Save/rollback semantics, `PATCH .../governance` PG18 sync on real DB agents, and `lifecycle_status: DRAFT \| ACTIVE` + `test_bench_status: UNTESTED \| PASSED \| FAILED` (guarding/disabling external MCP toggle on legacy read-only TS pack presets in `30.5` rather than building temporary `packAgentsCatalog.ts`-to-PG18 sync glue that Epic 31 `D1` deletes). | Epic 30 (`Story 30.5`) $\rightarrow$ Epic 31 (`Stories 31.1`–`31.7`) |

---

## 2. Detailed Active Architectural & Governance Specifications

### `D1` — PostgreSQL 18 Single Source of Truth (Zero Runtime Disk Reads, Zero Frontend Pack Hardcoding)
- **Context:** Today, Pack data is fragmented across disk YAML/Markdown files (`packs/sdlc/`, `packs/orcia-docs/`), shallow metadata in `declarative_pack_bundles` (omitting agent/skill/gate/glossary bodies), hardcoded TypeScript arrays (`apps/web/src/features/catalog/packAgentsCatalog.ts`), `platform_settings` JSONB (`platform_setup_state_v1.packs`), and in-memory `FederatedCatalogService` / `WorkflowStudioAndPackService` singletons.
- **Effective Rule:**
  1. `DeclarativePackLoader` reads `packs/<domain>/` strictly during Day-0 startup/reset (`startup_declarative_packs_and_dbos` and `09_reset_db_first_boot.py`), feeding the exact same transactional `PackImportService` exposed to users via `POST /api/v1/packs/import`.
  2. All runtime endpoints (`GET /api/v1/packs`, `GET /api/v1/vsm`, `GET /api/v1/workflows/v2`, `GET /api/v1/agents-and-skills/*`, `POST /api/v1/packs/{id}/export`) and UI catalogs read exclusively from PostgreSQL 18 (and SeaweedFS CAS for raw `.zip`/blob storage), compatible with `readOnlyRootFilesystem: true` (`AD-23`).
  3. `apps/web/src/features/catalog/packAgentsCatalog.ts` and runtime disk merging in `apps/api/src/orcia_api/routers/_workflows_helpers.py` and `packs.py` are deleted in `Story 31.2`.
- **Rejected Alternative:** Hybrid disk + DB overlay (perpetuates split-brain drift and blocks exporting/editing built-in pack assets).

### `D2` + `A1` — 4-Level Catalog Visibility vs. `WORKSPACE`-Only Runtime Activation
- **Context:** Keeping multi-level runtime inheritance (`GLOBAL -> BU -> TEAM -> WORKSPACE`) for active packs would force complex cross-scope activation deduplication, multi-level `ConnectorSlot` mapping, and multi-level Ontology `priority_order` merges.
- **Effective Rule:**
  1. **Catalog Visibility (`declarative_pack_bundles`):** Retains `(visibility_scope IN ('GLOBAL', 'BU', 'TEAM', 'WORKSPACE'), owner_scope_id UUID NULL)` under 6-verb RBAC (`AD-21`), strictly controlling who can browse, inspect, author, export, or activate a Pack bundle.
  2. **Runtime Activation & Slot Binding (`WORKSPACE`-Only):** `workspace_pack_activations` and `workspace_pack_slot_bindings` are keyed strictly by `workspace_id` (matching `workspace_datasources`). No `GLOBAL`, `BU`, or `TEAM` runtime activation inheritance exists. Organization-wide defaults on new Workspace creation are deferred as a simple bootstrap template insertion (`ACTION_ITEM-31.2`).
  3. **Upgrade & Pinning Semantics:**
     - `dry_run=true` computes a non-mutating diff (`added`, `updated`, `unchanged`, `conflicts`, `lint_warnings`, `required_slots`).
     - Re-importing identical `(visibility_scope, owner_scope_id, pack_slug, version, bundle_sha256)` is an idempotent no-op (`200 OK`).
     - Importing different `bundle_sha256` under an already-`PUBLISHED` SemVer returns `HTTP 409 ERR_PACK_VERSION_CONFLICT`.
     - Deleting a Pack version referenced by active `workflow_runs` (`run_lock_manifests`) returns `HTTP 409 ERR_RESOURCE_PINNED_BY_ACTIVE_RUNS` (`AD-21`).

### `D3` — Visible APM-Compatible Superset Format (`Option A1`)
- **Context:** Microsoft's open-source APM (`apm.yml` + `apm.lock.yaml` + `SKILL.md` + `.agent.md` + `.instructions.md`) aligns cleanly with ORCIA's Agent/Skill/Instruction/Checksum layers, while ORCIA additionally requires DBOS `WorkflowDefinitionV2`, `ValueStreamMapSpec`, 4-level Ontology + Starlark Tier 1b DNA mechanisms, Gates, Permission Broker policies, and bilingual Contextual Help.
- **Effective Rule:**
  ```text
  <pack-slug>/
  ├── apm.yml                        # Standard APM manifest + `x-orcia:` (bilingual title/desc, connector_slots, quick_actions)
  ├── apm.lock.yaml                  # Canonical per-file SHA-256 lockfile + pack bundle_sha256
  ├── agents/*.agent.md              # YAML frontmatter (APM fields + `x-orcia:` 6-block Studio governance) + Markdown prompt body
  ├── skills/<slug>/SKILL.md         # Agent Skills spec + `x-orcia:` (command_handle, input_parameters, is_si_write, human_authored_required)
  ├── instructions/*.instructions.md # Mode A governance instructions (`applyTo`, `x-orcia` scope hints)
  ├── workflows/
  │   ├── vsm-*.yaml                 # ValueStreamMapSpec (zero hardcoded workspace IDs)
  │   └── wf-*.yaml                  # WorkflowDefinitionV2 (`deterministic_dbos` | `non_deterministic`)
  ├── ontology/
  │   ├── glossary.yaml              # Bilingual concepts, relations, axioms, 6 profile translations
  │   └── mechanisms/*.star          # Certified Tier 1b Starlark scripts + YAML metadata/test vectors
  ├── gates/*.yaml                   # Deterministic & probabilistic gate definitions
  ├── policies/*.policy.md           # Permission Broker policies (`uri_pattern`, `required_role`, `sla_hours`)
  └── help/{fr,en}/*.md              # Contextual help articles (`bound_routes` frontmatter)
  ```
  - **Compatibility Aliases:** Importer accepts `.apm/{agents,skills,instructions}/` paths for third-party APM packages and legacy `pack.yaml` / root `glossary.yaml` during Day-0 migration.
  - **Security & Zero New Deps:** `.apm/hooks/` and any executable file extension (`.py`, `.sh`, `.bash`, `.js`, `.ts`, `.wasm`) are rejected on import (`HTTP 422 ERR_PACK_EXECUTABLE_HOOK_FORBIDDEN`) or stripped with explicit warning on external third-party compatibility mode (never executed). Parsing uses existing `PyYAML` + `Pydantic v2` without calling any `apm` CLI binary (`0` additions to `ARCHITECTURE-SPINE.md`).

### `D4` — Smart Readiness Classification & Import Validation Gates
- **Effective Rule:**
  1. **Transactional Reject (`HTTP 422`):** Reject entire `.zip` before any commit on zip-slip (`..` or symlink entries), archive size/entry/uncompressed-ratio bounds (anti-zip-bomb), invalid YAML/frontmatter schema, `apm.lock.yaml` hash mismatch (when lockfile is present), missing internal `orcia://packs/...` cross-reference, missing `human_authored_required: true` on `HUMAN_ANCHOR` steps (`AD-3`), or failure of any `mechanisms/*.star` embedded `passing_test_payload` (`PASS`) / `failing_test_payload` (`FAIL`) in `StarlarkMechanismSandbox` (`AD-9`, `< 2 ms`).
  2. **Readiness Assignment:**
     - Complete `x-orcia:` entities passing all deterministic checks are persisted with `lifecycle_status = 'ACTIVE'` (`status = 'published'` for workflows) — immediately usable on Workspace activation.
     - External community APM `.agent.md` / `SKILL.md` files missing `x-orcia:` governance contracts (or explicitly flagged `status: draft`) are persisted safely with `lifecycle_status = 'DRAFT'` and `test_bench_status = 'UNTESTED'`, blocked from `@agent` / Process / MCP execution (`Epic 30.5`) until reviewed and activated in Studio. Vendor-specific `model:` strings in external `.agent.md` files map to abstract `llm_model_tier: medium` (`AD-21` Rule 4).

### `D5` — Safe Connector Boundary (`Option B`)
- **Effective Rule:** Packs do **not** declare executable Python connectors or arbitrary live outbound HTTP/MCP server destinations inside uploaded archives.
  - Built-in connector needs use `x-orcia.connector_slots` referencing pre-installed platform adapters (`jira`, `confluence`, `git`, `db`, `codegraph` in `packages/orcia-connectors`).
  - Access-request guidance ships declaratively via `policies/*.policy.md` into `permission_broker_policies`.
  - Standard APM `mcp:` blocks in `apm.yml` are parsed and stored as informational requirement descriptors (mapping known adapters or surfacing `"External MCP server not installed on platform"` in UI readiness). Real outbound `httpx` MCP transport (`McpClientBridgeConnector`) with 4-step Anti-SSRF Test Bench persistence is tracked separately as `ACTION_ITEM-31.1`.

### `D6.a` + `R1` + `A1` — Qualified Runtime Namespacing, Flat `WORKSPACE_PACK` Ontology & Prose Linter
- **Effective Rule:**
  1. **Qualified Handles & URIs:**
     - Workspace standalone entities: `@workspace/<slug>` and `/workspace/<slug>`, URI `orcia://workspaces/<ws_id>/{agents|skills}/<slug>`.
     - Pack-bundled entities: `@<pack_slug>/<slug>` and `/<pack_slug>/<slug>` (resolved to the single active version of `<pack_slug>` on that Workspace, or pinned `@<pack_slug>/<slug>:<semver>` inside workflows and `run-lock.json`), URI `orcia://packs/<pack_slug>/{agents|skills|workflows|gates}/<slug>@<semver>`. Legacy `pack://` URIs normalize to `orcia://packs/` on parse.
  2. **Structured-Only Snapshot Rewriting & Prose Linter:** Compiling a `DRAFT` Pack into an immutable `PUBLISHED` snapshot rewrites **only structured Pydantic/AST fields** (`agent_ref`, `skill_refs`, `skill_ids`, `linked_workflow_id`, `target_workflow_slug`, `allowed_delegate_agents`, `knowledge_feedback_target_agent`, `allowed_rag_sources`, `toolbox_mcp_permissions`). Markdown instructions are never auto-mutated; a deterministic linter flags unqualified `@slug`/`/slug` tokens matching Workspace entities as non-blocking `publish_warnings` in the `dry_run` / Publish dialog.
  3. **Authoring Workspace Non-Duplication:** Publishing a Pack from Workspace `W` does **not** auto-insert a row into `workspace_pack_activations` for `W` unless the author explicitly activates it.
  4. **Flat `WORKSPACE_PACK` Ontology Resolution:** `OntologyHierarchyResolver` resolves `4_RUN_EPHEMERAL -> 3_WORKSPACE -> WORKSPACE_PACK -> 3_TEAM (org tree) -> 2_DOMAIN -> 1_ENTERPRISE`. Within `WORKSPACE_PACK`, ties between two active Packs defining the same `canonical_term` are broken deterministically via `workspace_pack_activations.priority_order ASC`, backed by PostgreSQL constraint `UNIQUE (workspace_id, priority_order) DEFERRABLE INITIALLY DEFERRED` enabling atomic single-transaction rank swaps.

### `D6.b` + `R2` — Pack Composer, `409` Delete Guard, Anti-Hostage Unlink & `422` Closure Gate
- **Effective Rule:**
  1. **Draft Composition:** Authorized authors create a `DRAFT` Pack and add/remove existing Workspace entities via `pack_draft_memberships` (`ON DELETE RESTRICT` against live targets).
  2. **Delete Guard & Anti-Hostage Unlink (`R2`):** Attempting to delete an entity referenced by one or more `DRAFT` Packs returns `HTTP 409 ERR_ENTITY_REFERENCED_BY_PACK_DRAFT` listing the blocking draft pack keys. Calling `DELETE ...?unlink_from_draft_packs=true` atomically deletes the `pack_draft_memberships` link(s) and the entity in one PostgreSQL transaction (`audit_ledger`: `PACK_DRAFT_MEMBER_UNLINKED_ON_ENTITY_DELETE`), authorized whenever the caller holds `delete` permission on the target entity (`owner`, `TEAM_LEAD`/`BU_LEAD` of the scope, or `PLATFORM_ADMIN`, excluding `READ_ONLY_OBSERVER`) **and** every blocking Pack is in `DRAFT` within the caller's visible/delegated scope — preventing stale peer drafts from hostaging Workspace assets.
  3. **Transitive Closure Gate at Publish:** Publishing (`POST /api/v1/packs/{id}/publish`) verifies (`HTTP 422 ERR_PACK_CLOSURE_INCOMPLETE`) that all referenced agents/skills/workflows/gates included transitively are present in the Pack and in `ACTIVE` / `published` state.

### `D6.c` + `R3–R5` + `A2–A3` — `ConnectorSlot` De-Binding, `O(1)` Scanner, Explicit Bind & `run-lock.json` Pinning
- **Effective Rule:**
  1. **Structural De-Binding:** Snapshot/Export converts concrete `workspace_datasources` / `enterprise_connectors` UUIDs into abstract `slot://<slot_key>` declarations (`x-orcia.connector_slots`: `slot_key`, `scheme`, `connector_kind`, `source_nature`, `required_access`, `required: bool = true`) and normalizes concrete `model_override` strings to `llm_model_tier: simple | medium | complex`.
  2. **`O(1)` Single-Pass Tokenized Scanner (`A3`):** Prior to building `apm.lock.yaml` and `.zip`, the Export Scrubber:
     - Loads tenant DB identifiers (`workspaces.id`, `org_units.id`, `users.id`, `users.email`, `enterprise_connectors.{id,base_url}`, `workspace_datasources.{id,uri}`, `llm_model_endpoints.{id,endpoint_url}`) once into normalized in-memory `frozenset[str]` hash sets.
     - Scans each rendered file in a single `O(bytes)` pass extracting UUIDs, URLs/hosts, email literals, and credential patterns, testing tenant-infra hits in `O(1)` per token.
     - Allows standard schema/spec namespaces (`json-schema.org`, `spdx.org`, `orcia://`, `slot://`) while rejecting RFC 1918/loopback/link-local/`.internal`/`.local`/`.corp`/`.lan` hosts, `ORCIA_LLM_ALLOWED_PRIVATE_HOSTS` entries, secret prefixes/high-entropy strings (`NFR-SEC-4`), and **any** email literal outside `apm.yml` `author`/`maintainers` (`HTTP 422 ERR_PACK_PII_OR_INFRA_LEAK`).
  3. **Zero Silent Auto-Bind (`R4`):** On Workspace activation, `workspace_pack_slot_bindings` initializes with `bound_target_id = NULL` (`UNBOUND`). The Slot Mapping Drawer visually pre-selects matching `(scheme, source_nature, alias)` candidates for convenience, but persists bindings **only** on explicit confirmation (`PUT /api/v1/workspaces/{ws_id}/packs/{pack_id}/slot-bindings` -> `audit_ledger`: `PACK_SLOTS_BOUND`).
  4. **Fail-Closed Pre-Execution & `run-lock.json` Slot Pinning (`R5` + `A2`):** Before `AssistantTurnEngine`, `ProcessExecutionDispatcher`, or `GovernedMcpServerService` allocates a run or spends LLM tokens:
     - `PackSlotReadinessGuard` inspects all `slot://<key>` references against `workspace_pack_slot_bindings`:
       - **`required: true` + `UNBOUND`/disabled target** $\rightarrow$ rejects immediately with **`HTTP 422 ERR_PACK_SLOT_UNBOUND`** (`unbound_slots` payload + drawer CTA).
       - **`BOUND`** $\rightarrow$ resolves and freezes concrete `{slot_key, target_kind, target_id, target_uri, version_or_sha256}` inside `run_lock_manifests.run_lock_jsonb.resolved_pack_slots`, enforcing `409 ERR_RESOURCE_PINNED_BY_ACTIVE_RUNS` if that bound datasource/connector is deleted mid-run, and ensuring DBOS `HITL` resumes / `Replay Step N` never drift if slot bindings are later edited.
       - **`required: false` + `UNBOUND`** $\rightarrow$ cleanly strips `slot://<key>` from runtime tool/RAG inputs and records `{slot_key, status: "optional_unbound", target_id: null}` in `run-lock.json`.

### `A4` — Coordination Boundary with Concurrent Epic 30 (`Story 30.5`)
- **Context:** `feat/epic-30-assistant-processes-and-agents-ux-hardening` is executing concurrently (`Story 30.1` already committed). `Story 30.5` addresses `AgentDetailAndSandboxModal` UX bugs and pack-agent `PATCH .../governance` 404s.
- **Effective Rule:** To prevent throwaway work that Epic 31 (`D1`) deletes:
  - Keep `Story 30.5` strictly limited to: (a) removing duplicate `<AgentIdentityAndSkillsFields />`, (b) inline modal `[role="alert"]` and truthful explicit Save/rollback, (c) `await _sync_from_postgres18_if_enabled(request, svc)` on `PATCH /api/v1/agents-and-skills/agents/{id}/governance` for real PG18 agents, and (d) adding `lifecycle_status: DRAFT | ACTIVE` + factual `test_bench_status: UNTESTED | PASSED | FAILED` with runtime `DRAFT` exclusion.
  - **Do NOT** refactor `apps/web/src/features/catalog/packAgentsCatalog.ts` into a temporary TS-to-PG18 sync pipeline during `Story 30.5`; instead guard/disable external MCP exposure toggles on legacy read-only TS pack presets in `30.5`, leaving full PG18 Pack materialization and `packAgentsCatalog.ts` removal cleanly to Epic 31 (`Story 31.2`).

---

## 3. Revision & Amendment Audit Trail (`R1–R5`, `A1–A4`) & Deferred Action Items

| Ref | Supersedes / Refines | Summary | Action Item (To Register at Epic 31 Kickoff) |
| :--- | :--- | :--- | :--- |
| **`R1`** | `D6.a` | Explicit `priority_order` tie-breaking for multi-pack Ontology conflicts + structured-only snapshot URI rewriting with non-mutating prose `@slug` linter. | — |
| **`R2`** | `D6.b` | Anti-hostage RBAC: entity owner / scope lead / admin can atomically unlink & delete an entity referenced by another member's `DRAFT` Pack (`audit_ledger` traced). | — |
| **`R3`** | `D6.c` | Precision scanner avoids false positives on standard `$schema` URLs and Starlark test fixtures; checks tenant infra IDs/URLs + SSRF host rules + secret patterns. | — |
| **`R4`** | `D6.c` | Zero silent auto-binding on import/activation; pre-select candidates visually in Slot Mapping Drawer, require explicit confirmation (`AD-3`, `AD-6`). | — |
| **`R5`** | `D6.c` | Pre-execution `PackSlotReadinessGuard` rejects unbound `required: true` slots (`422 ERR_PACK_SLOT_UNBOUND`), preventing silent RAG drops & LLM hallucination. | — |
| **`A1`** | `D2`, `R1`, `R4` | Decouple 4-level Catalog Visibility (`declarative_pack_bundles`) from `WORKSPACE`-only Runtime Activation (`workspace_pack_activations` with `DEFERRABLE` `priority_order`) & Slot Binding (`workspace_pack_slot_bindings`). | `ACTION_ITEM-31.2` (Org-wide default Pack templates on Workspace creation) |
| **`A2`** | `R5` | Freeze concrete slot targets into DBOS `run-lock.json` (`resolved_pack_slots`) at run start; strip `required: false` unbound slots cleanly and log `optional_unbound` (`null`). | — |
| **`A3`** | `R3` | Single-pass `O(bytes)` token extractor + `O(1)` `frozenset` tenant infra lookup + ban all email literals outside `apm.yml` `author`/`maintainers`. | — |
| **`A4`** | Sequencing | Run Epic 30 first, Epic 31 immediately after; keep `Story 30.5` free of throwaway `packAgentsCatalog.ts` -> PG18 sync refactoring. | — |
| **`D5`** | Connector scope | Defer real outbound `httpx` `McpClientBridgeConnector` & persistent 4-step Anti-SSRF Test Bench registrations out of Pack Import/Export. | `ACTION_ITEM-31.1` (Outbound MCP HTTP/OpenAPI Connector Runtime & Persistence) |
