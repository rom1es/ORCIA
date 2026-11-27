## Epic 30: Honest Save Semantics, Clean Conversational Prompts, Real PG18 Process Runs & Focus Review, and Agent Lifecycle Hardening (`Stories 30.1`..`30.6`)

Eliminate broken auto-save + explicit Save hybrids across `"Réglages de Mon Assistant"` and `"Mes Agents & Compétences"`, decouple `Mon Assistant`'s conversational LLM prompt from UI governance preview cards with conditional provenance and an explicit empty-evidence anti-hallucination guard, replace hardcoded `Mes Processus` pending validations and cassette fallbacks with real PostgreSQL 18 runs behind a tabbed hub and a clear 3-zone Focus Review (`/processes/runs/$runId`), and enforce PG18 persistence, inline modal alerts, and real `DRAFT` vs `ACTIVE` lifecycle gating for agents (`UX30-01`..`UX30-16`, tracked in `docs/planning-artifacts/sprint-change-proposal-2026-11-25-epic-30-assistant-processes-and-agents-ux-hardening.md`).

### Story 30.1: `Mon Assistant` Settings Explicit Save, Honest Dirty Guard, Inline Modal Errors & Empty Personal Instructions (`UX30-01`, `UX30-02`, `UX30-03`)

As an ORCIA User configuring `"Réglages de Mon Assistant"` (`Hélène UJ-1`, `Lucas UJ-7`),
I want an explicit bottom-right `Enregistrer` button (`Annuler` / `Fermer` + primary Cobalt `Enregistrer`), baseline-diff `isDirty` tracking without keystroke auto-save storms, honest `✓ Enregistré` feedback shown only after PostgreSQL 18 confirms, inline error alerts inside the modal, and the ability to leave `"Mes consignes personnelles permanentes"` empty,
So that `"Annuler"` genuinely discards unsubmitted changes without false `"Modifications non enregistrées"` warnings after saving, and personal instructions stay free of forced default `[S1]` boilerplate.

**Lot:** 1 — `Mon Assistant` Settings & Prompt Hardening. **Dependencies:** `Epic 29`. **Agent:** `bmad-dev-worker` (`flash`).
**Findings covered:** `UX30-01`, `UX30-02`, `UX30-03`.
**CAPs covered:** `CAP-070`, `CAP-100`.
**Impacted files:** `packages/ui/src/primitives/AssistantGovernanceModalAndStudio.tsx`, `packages/ui/src/primitives/AssistantGovernanceModeATabs.tsx`, `packages/ui/src/primitives/AssistantGovernanceTypes.ts`, `apps/web/src/features/inbox/InboxAuxiliaryPanels.tsx`, `apps/web/src/features/inbox/useServerAssistantGovernance.ts`, `apps/web/src/features/inbox/assistantFoldersAndPrefsStore.ts`, `apps/api/src/orcia_api/schemas/assistant_governance_and_three_speed.py`, `packages/orcia-core/src/orcia_core/orchestration/_assistant_locales.py`, `packages/orcia-core/src/orcia_core/orchestration/assistant_governance_models.py`, `packages/orcia-core/src/orcia_core/orchestration/_internal/sql_assistant_governance.py`, `packages/api-client/src/generated/`, `packages/ui/src/__tests__/rgaa-modals-escape-unsaved-guard.test.tsx`, `apps/web/e2e/22-assistant-tool-loop-approval-and-reattach.spec.ts`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/30-1-assistant-settings-explicit-save-dirty-guard-and-empty-instructions-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** an authenticated user editing dropdowns or `"Mes consignes personnelles permanentes"` / `"Réglages de l'Espace"` inside `"Réglages de Mon Assistant"`
**When** typing or switching values before clicking `Enregistrer`
**Then** zero auto-save `PUT` calls fire on keystroke or selection changes, `isDirty` is computed strictly by comparing Tab 1 and Tab 2 drafts against hydrated server baselines, clicking `Annuler` or pressing `Escape` opens `<RgaaUnsavedChangesAlert />` where `"Quitter sans enregistrer"` discards only unsubmitted React edits without touching PostgreSQL 18, and the 3-column select width displays `"Équilibré & Structuré (Recommandé)"` without clipping.

**Given** the user clicks the bottom-right primary Cobalt `Enregistrer` button (`<RgaaDialogFooterActions />`)
**When** `PUT /api/v1/assistant/governance/mode-a/user` and/or `/workspace` succeeds (or fails with HTTP `4xx`/`5xx`)
**Then** on success `await onSave*` completes before showing `"✓ Enregistré"`, resets `isDirty` to `false`, refreshes Tab 3 (`Consignes actives`), keeps the modal open so `Fermer` / `Escape` exits with zero false warning, and removes all 4 hidden `display: none` Save buttons, 3 legacy duplicate `<select>` nodes, and the E2E `.evaluate()` click workaround; on failure, `✓ Enregistré` never appears, `isDirty` stays `true`, and a localized `[role="alert"]` renders **inside** the modal body; and empty (`""`) `personal_instructions` (`min_length=0` in `UpdateUserLayerPreferencesRequest`, empty backend default, `0-diff` OpenAPI SDK) persists cleanly to PG18 (`AD-17` Layer 2 verified).

---

### Story 30.2: `Mon Assistant` Clean Conversational System Prompt, Single Layer Injection & Empty-Evidence Anti-Hallucination Guard (`UX30-04`, `UX30-05`)

As an ORCIA User conversing with `Mon Assistant` (`Hélène UJ-1`, `Lucas UJ-7`),
I want the live conversational LLM system prompt strictly decoupled from UI governance preview cards, stripped of raw internal tags and duplicate layers, given a natural-speech confidentiality directive, and protected by a conditional empty-evidence guard when zero sources match,
So that simple greetings and everyday replies sound natural and never invent `orcia://system/status/ready`, `[Citation non vérifiée]`, or `SHA-256("")` proofs.

**Lot:** 1 — `Mon Assistant` Settings & Prompt Hardening. **Dependencies:** `30.1`. **Agent:** `bmad-dev-worker` (`flash`).
**Findings covered:** `UX30-04`, `UX30-05`.
**CAPs covered:** `CAP-022`, `CAP-070`, `CAP-071`, `CAP-072`, `CAP-074`.
**Impacted files:** `apps/api/src/orcia_api/routers/_assistant_context_assembly.py`, `packages/orcia-core/src/orcia_core/orchestration/assistant_prompt_builder.py`, `packages/orcia-core/src/orcia_core/orchestration/assistant_prompt_preview.py`, `packages/orcia-core/src/orcia_core/orchestration/assistant_prompt_locales.py`, `packages/orcia-core/src/orcia_core/orchestration/_assistant_profile_locales.py`, `packages/orcia-core/src/orcia_core/orchestration/assistant_evidence_table.py`, `packages/orcia-core/src/orcia_core/orchestration/_assistant_citations_verifier.py`, `tests/unit/`, `tests/evals/`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/30-2-assistant-conversational-prompt-cleanup-and-empty-evidence-guard-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** `_assistant_context_assembly.py` assembling the system prompt for a live `/api/v1/assistant/turns` request
**When** building the conversational prompt in French (`fr`) or English (`en`)
**Then** `build_five_layers_preview_items` remains strictly for Tab 3 UI preview while live turns receive a dedicated conversational system prompt with single (non-duplicated) Workspace and User instructions, the real active `pack_key`, human-readable `PROFILE_LABELS_LOCALES` (removing `"Topologie DAG, Dépendances, Hashes SHA-256 & Exécution N3"` and `"DAG Steps & Verrous run-lock.json"` plumbing), zero raw internal tags (`[CONSTITUTIONAL_IMMUTABLE_LAYER_1]`, `[NO_HUMAN_ANCHOR_WRITE]`, `human_authored_required: true`, `[EXPLICIT_PROVENANCE_URI]`, `[ACTIVE_DOMAIN_PACK: ...]`, `[ADAPTATION_RUNTIME_METADATA]`), and an explicit prompt-confidentiality / natural-speech rule forbidding repeating system instructions or internal tokens.

**Given** an Assistant turn whose `EvidenceTable` contains `0` sources and `0` ontology glossary items (e.g., greeting or RAG inactive)
**When** assembling the prompt and finalizing the streamed response
**Then** citation/URI/SHA-256 rules activate **only** when `EvidenceTable` is non-empty; when empty, `format_evidence_table_for_layer_4` / `AssistantPromptBuilder` injects an explicit localized (`fr`/`en`) empty-evidence guard instructing the model to answer conversationally without citing `[S#]`, `orcia://`, or `sha256:`, and post-stream `CitationGuard` + golden evals verify zero fabricated `orcia://` URIs, `SHA-256("")` digests, or `[Citation non vérifiée]` leaks.

---

### Story 30.3: `Mes Processus` Real PG18 Pending Validations, Live Workspace LLM Execution & Coalesced Reasoning Trace (`UX30-06`, `UX30-07`, `UX30-08`)

As an ORCIA Team Lead or Contributor (`Marc UJ-5`, `Nadia UJ-4`) opening `Mes Processus` (`/processes`),
I want pending validations hydrated strictly from real workspace-scoped PostgreSQL 18 runs (`0` on clean Day-0), zero `localStorage` auto-launched cassette traces referencing `docs/product/capabilities.yaml`, and cleanly coalesced reasoning blocks,
So that `Mes Processus` never fabricates leftover test validations or splits thoughts mid-token every 64 characters.

**Lot:** 2 — `Mes Processus` Real Persistence & Focus Review. **Dependencies:** `Epic 29`. **Agent:** `bmad-dev-worker` (`flash`).
**Findings covered:** `UX30-06`, `UX30-07`, `UX30-08`.
**CAPs covered:** `CAP-020`, `CAP-021`, `CAP-140`, `CAP-160`.
**Impacted files:** `apps/web/src/features/processes/ProcessesHubPage.tsx`, `apps/web/src/features/processes/ProcessesActiveDossiersCard.tsx`, `apps/web/src/features/processes/execution/useInteractiveProcessRunController.ts`, `apps/api/src/orcia_api/routers/workflows.py`, `apps/api/src/orcia_api/routers/executions_trace.py`, `packages/orcia-core/src/orcia_core/agents/process_dispatcher.py`, `packages/orcia-core/src/orcia_core/agents/llm_adapter.py`, `packages/ui/src/components/AgentExecutionTrace.tsx`, `packages/ui/src/components/AgentExecutionTraceItems.tsx`, `packages/api-client/src/generated/`, `tests/integration/`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/30-3-processes-real-pg18-pending-runs-live-llm-and-coalesced-trace-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** a workspace (or global `"Tous mes espaces"`) with `0` active/pending process runs in PostgreSQL 18 (`workflow_runs` / `reflexive_execution_sessions`)
**When** opening `Mes Processus` (`/processes`)
**Then** `ProcessesActiveDossiersCard` / `ProcessesHubPage` hydrates pending validations strictly from a workspace-scoped PG18 endpoint (`0-diff` OpenAPI SDK), never renders the hardcoded `"1 validation en attente de votre décision"` badge or promotes `workflows[0]` (`wf-generate-orcia-documentation`), removes `localStorage["orcia.processes.active_run_workflow_id.v1"]` sticky auto-launch on mount, and reflects truthful backend run status (`RUNNING`, `WAITING_SUBSTEP_HITL`, `WAITING_FINAL_ANCHOR`, `WAITING_WRITE_PREVIEW`, `COMPLETED`, `PAUSED`).

**Given** a user explicitly launching a goal-driven process run in production
**When** `ProcessExecutionDispatcher` and `GatewayReflexiveLlmAdapter` execute and stream the run
**Then** production execution strictly uses the workspace's configured LLM and real attached workspace datasources (returning a clear localized RFC 9457 error when no LLM/datasource is configured, with zero fallback to `DeterministicCassetteLLM` or `_DEFAULT_FALLBACK_RESOURCE = "docs/product/capabilities.yaml"`, keeping cassettes strictly under `tests/`), and `AgentExecutionTrace` / `AgentExecutionTraceItems` coalesce consecutive `THOUGHT_DELTA` chunks within each phase group into a single continuous thought block instead of rendering separate `"Réflexion en cours"` headers every 64 characters (`AD-17` Layer 2 PG18 verified).

---

### Story 30.4: `Mes Processus` Tabbed Hub (`<OrciaTabStrip />`), Dedicated Focus Review (`/processes/runs/$runId`) & Single State-Gated Decision Bar (`UX30-09`, `UX30-10`)

As an ORCIA Team Lead or Reviewer (`Marc UJ-5`, `Sophie UJ-6`) managing workflows and reviewing deliverables,
I want `Mes Processus` organized into distinct `<OrciaTabStrip />` tabs (`Validations & Exécutions` | `Processus métiers` | `Chaîne de valeur`) and individual run reviews moved onto a dedicated 3-zone Focus Review route (`/processes/runs/$runId`),
So that I can see available business processes cleanly, immediately identify the single expected decision, read the formatted deliverable without scrolling past trace logs, and consult agent reasoning on demand.

**Lot:** 2 — `Mes Processus` Real Persistence & Focus Review. **Dependencies:** `30.3`. **Agent:** `bmad-dev-worker` (`flash`).
**Findings covered:** `UX30-09`, `UX30-10`.
**CAPs covered:** `CAP-020`, `CAP-021`, `CAP-140`, `CAP-160`, `CAP-200`.
**Impacted files:** `apps/web/src/router.tsx`, `apps/web/src/features/processes/ProcessesHubPage.tsx`, `apps/web/src/features/processes/ProcessesActiveDossiersCard.tsx`, `apps/web/src/features/processes/ProcessesValueStreamOverviewCard.tsx`, `apps/web/src/features/processes/execution/InteractiveRunDrawer.tsx`, `apps/web/src/features/processes/execution/InteractiveRunDeliverableAndHitlPanels.tsx`, `apps/web/src/features/processes/processStudioV2StructuralVsm.ts`, `apps/web/src/i18n/locales/process_catalog_vsm_p1_{fr,en}.ts`, `apps/web/src/i18n/locales/process_studio_ui_labels_{fr,en}.ts`, `apps/web/src/__tests__/`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/30-4-processes-tabbed-hub-and-focus-review-action-artifact-reasoning-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** `Mes Processus` (`/processes`)
**When** rendered inside `<OrciaPageHeader />`
**Then** Tier-2 `<OrciaTabStrip />` separates **`Validations & Exécutions (N)`** | **`Processus métiers`** | **`Chaîne de valeur`** (omitting the `(N)` badge and defaulting to `Processus métiers` when `N === 0`), removing the inline run drawer from the catalog page, integrating autonomous runs supervision cleanly into Tab 1 without unrelated 403/empty clutter, and removing hardcoded `"Mon Compte"` VSM titles/slugs from `process_catalog_vsm_p1_{fr,en}.ts` and `processStudioV2StructuralVsm.ts`.

**Given** a user inspecting a run on `/processes/runs/$runId` (navigated from `Validations & Exécutions`, Cockpit, or launch)
**When** rendered on Desktop (`>= 1280px`) and Laptop (`< 1280px`)
**Then** the Focus Review view displays: (1) **Zone 1 — Sticky Expected Action Banner** (semantic Amber `#D97706` for validation/arbitration, Violet `#6D28D9` exclusively for mandatory human anchors) with **strictly ONE primary Cobalt CTA** state-gated between substep approval and final publication (eliminating the stacked duplicate Bar 1/Bar 2 and duplicate Edit button, and hiding correction step/comment controls inside a `"Demander une correction"` popover until clicked); (2) **Zone 2 — Primary Artifact Consultation** (~65% width left pane) rendering formatted Markdown, clickable source chips, and a clean `Lecture` / `Édition` toggle; and (3) **Zone 3 — Secondary Reasoning Rail** (~35% width right pane, switching to 2 sub-tabs below `1280px`) with `defaultCollapsedWhenCompleted={true}` once waiting/completed and live-expanded only while `RUNNING`.

---

### Story 30.5: `Mes Agents` PG18 Pack-Agent Governance Sync, Clean 6-Block Modal Save/Errors & Real `DRAFT` vs `ACTIVE` Lifecycle Gating (`UX30-11`..`UX30-15`)

As an ORCIA Team Lead or Agent Author (`Karim UJ-9`, `Marc UJ-5`) configuring agents in `"Mes Agents & Compétences"`,
I want Pack agents persisted/synced in PostgreSQL 18 so `"Exposer en outil externe"` never throws 404, errors displayed inline inside the modal, a single non-duplicated 6-block editor with an honest explicit Save footer, and a real `DRAFT` vs `ACTIVE` lifecycle enforced across `Mon Assistant`, `Mes Processus`, and MCP exposure,
So that configuring and governing agents behaves reliably and `"Validé au Banc de Test"` is never faked.

**Lot:** 3 — `Mes Agents` PG18 Persistence, Modal & Lifecycle Hardening. **Dependencies:** `Epic 29`. **Agent:** `bmad-dev-worker` (`flash`) + `bmad-architect-worker` (`pro`) review on lifecycle & MCP exposure contract.
**Findings covered:** `UX30-11`, `UX30-12`, `UX30-13`, `UX30-14`, `UX30-15`.
**CAPs covered:** `CAP-082`, `CAP-090`, `CAP-091`, `CAP-100`.
**Impacted files:** `apps/api/src/orcia_api/routers/agents_and_skills.py`, `packages/orcia-core/src/orcia_core/orchestration/agents_and_skills_manager.py`, `packages/orcia-core/src/orcia_core/orchestration/_agents_and_skills_executor.py`, `packages/orcia-core/src/orcia_core/bootstrap/seeder.py`, `apps/web/src/features/catalog/packAgentsCatalog.ts`, `apps/web/src/features/catalog/useManagedAgentActions.ts`, `apps/web/src/features/catalog/index.tsx`, `apps/web/src/features/inbox/assistantAutocompleteHelpers.ts`, `packages/ui/src/components/AgentDetailAndSandboxModal.tsx`, `packages/ui/src/components/AgentStudioCardItem.tsx`, `packages/ui/src/components/AgentTestBenchSection.tsx`, `packages/api-client/src/generated/`, `tests/integration/`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/30-5-agents-pg18-mcp-sync-clean-modal-save-and-draft-active-lifecycle-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** an authorized user toggling `"Exposer en outil externe"` or editing a Pack or custom agent in `AgentDetailAndSandboxModal`
**When** `PATCH /api/v1/agents-and-skills/agents/{agent_id}/governance` or `POST /api/v1/agents-and-skills/agents` runs
**Then** active Pack agents exist in PostgreSQL 18 (via idempotent seeding / workspace activation sync) and `update_agent_governance_endpoint` calls `await _sync_from_postgres18_if_enabled(request, svc)`, eliminating the HTTP `404 ERR_RESOURCE_NOT_FOUND` (`Exposition MCP`) across cold worker restarts; any API failure rolls back optimistic checkbox state and renders an inline `[role="alert"]` **inside** `AgentDetailAndSandboxModal` (never hidden behind the dimmed backdrop); duplicated `<AgentIdentityAndSkillsFields />` summary fields above `<AgentSixBlocksEditorBody />` are removed; and clicking explicit bottom-right `Enregistrer` (`<RgaaDialogFooterActions />` + `useUnsavedChangesDialogGuard`) awaits real API persistence without `useEffect([agent])` wiping `"Modifications enregistrées"` feedback.

**Given** an agent's lifecycle and test-bench state across `Mes Agents`, `Mon Assistant`, `Mes Processus`, and external MCP exposure
**When** inspecting cards, opening the modal, mentioning `@agent`, selecting workflow delegates, or enabling external MCP exposure
**Then** cosmetic hardcoded `"Validé au Banc de Test"` (`|| isPack` in `AgentStudioCardItem`, `testBenchValidated: true` in `packAgentsCatalog.ts` and `.catch()` in `useManagedAgentActions.ts`, and forced `True` in `_agents_and_skills_executor.py`) is replaced by explicit **`lifecycle_status` (`DRAFT` vs `ACTIVE`)** and factual **`test_bench_status` (`UNTESTED` | `PASSED` | `FAILED`)**; `DRAFT` agents are strictly blocked (both UI and backend) from `@agent` Assistant selection/invocation, Process execution, and external MCP exposure (`HTTP 422`), whereas `ACTIVE` agents are selectable and executable (`AD-17` Layer 2 PG18 `create_app()` verified).

---

### Story 30.6: Epic 30 Anti-Regression CI Guards, Bilingual FR/EN Playwright E2E Lock, Contextual Help & Doc Sync, and Closure (`UX30-16`)

As an ORCIA Maintainer and Product Owner (`Sally`, `Winston`, `Hélène UJ-1`),
I want automated CI audits locking every Epic 30 guarantee, synchronized Zone 4 help & UX specs, full 5-layer `AD-17` verification including bilingual (`fr`/`en`) Desktop Playwright E2E, and formal `bmad-architect-worker` (`pro`) sign-off,
So that save-state contradictions, prompt leaks, cassette fallbacks, and fake validation states can never regress.

**Lot:** 4 — Regression Lock & Epic 30 Closure. **Dependencies:** `30.2`, `30.4`, `30.5`. **Agent:** `bmad-dev-worker` (`flash`) + mandatory `bmad-architect-worker` (`pro`) closure gate.
**Findings covered:** `UX30-16` (and full `UX30-01`..`UX30-15` end-to-end verification).
**CAPs covered:** `CAP-022`, `CAP-070`, `CAP-071`, `CAP-072`, `CAP-082`, `CAP-090`, `CAP-091`, `CAP-100`, `CAP-140`, `CAP-160`.
**Impacted files:** `apps/web/src/__tests__/`, `tests/evals/`, `tests/security/`, `apps/web/e2e/`, `docs/help/{fr,en}/*.md`, `docs/planning-artifacts/ux-designs/ux-ORCIA-2026-10-24/{DESIGN,EXPERIENCE}.md`, `docs/product/capabilities.yaml`, `docs/implementation-artifacts/sprint-status.yaml`.
**Tech Lead Report:** `docs/implementation-artifacts/tech-lead-reports/30-6-epic-30-anti-regression-audits-bilingual-e2e-and-closure-tech-lead-report.md`.

**Acceptance Criteria:**

**Given** the Epic 30 automated CI guardrails and documentation updates
**When** running static audits, golden evals, and Zone 4 contextual help checks
**Then** automated tests lock: (a) inline `[role="alert"]` error rendering on every edit modal (`AssistantGovernanceModalAndStudio`, `AgentDetailAndSandboxModal`), (b) single primary decision CTA in `/processes/runs/$runId` Focus Review, (c) zero raw internal markers (`[CONSTITUTIONAL_IMMUTABLE_LAYER_1]`, `[NO_HUMAN_ANCHOR_WRITE]`, `human_authored_required`) and zero `SHA-256("")` / `orcia://` fabrication in empty-evidence Assistant golden evals, and (d) strict `DRAFT` agent exclusion across Assistant/Processes/MCP; and `docs/help/{fr,en}/{assistant,processes,agents}.md` plus `DESIGN.md`/`EXPERIENCE.md` reflect the updated UI flows accurately.

**Given** full `AD-17` 5-layer closure verification and `bmad-architect-worker` (`pro`) review
**When** closing Epic 30
**Then** all production files remain `<= 300` lines, `.venv/bin/ruff check .`, `ruff format --check .`, `mypy --strict`, `lint-imports` (`5/5`), `lint_spine.py` (`0 findings`), `export_openapi.py --check` (`0-diff`), i18n Gates 1–4 (`0` baseline), full `tests/unit` + `tests/evals` + `tests/security` + `tests/contract` + impacted PG18+Redis `testcontainers` (`>= 90%` branch coverage), `pnpm turbo run lint typecheck test`, bilingual (`fr` & `en`) Desktop Playwright E2E (`env -u ORCIA_E2E_SEED_FIXTURES`, zero `.evaluate()` hidden-button workarounds), `scripts/check_implementation_docs.py`, `pnpm site:sync && pnpm site:check`, and `npx gitnexus analyze` all pass, `CAP-xxx` entries remain `runtime`, and `epic-30` becomes `done`.

---
