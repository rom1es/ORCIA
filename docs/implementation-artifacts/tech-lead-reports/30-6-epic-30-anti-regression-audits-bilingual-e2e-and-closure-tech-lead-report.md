# Story 30.6 — Epic 30 Anti-Regression CI Guards, Bilingual FR/EN Playwright E2E Lock, Contextual Help & Doc Sync, and Closure (`UX30-16`)

- **Date**: 2026-11-26
- **Story / Sprint Key**: `30-6-epic-30-anti-regression-audits-bilingual-e2e-and-closure` (`Epic 30`, Lot 4)
- **Capability(ies)**: `CAP-022`, `CAP-070`, `CAP-071`, `CAP-072`, `CAP-082`, `CAP-090`, `CAP-091`, `CAP-100`, `CAP-140`, `CAP-160` — classification: `feature`
- **Author / Context**: `UX30-16` (Epic 30 Regression Lock & Closure covering `UX30-01`..`UX30-16`, `FR-1`, `FR-4`, `FR-7`..`FR-9`, `FR-13`, `FR-24`, `FR-33`, `FR-35`, `FR-36`, `AD-15`, `AD-17`, `AD-22`)
- **Associated Commits**: pending (`feat/epic-30-assistant-processes-and-agents-ux-hardening`)

---

## 1. Needs Analysis & Tech Lead Impact Study (Pre-Implementation)

### 1.1 Context & Problem Statement
Stories `30.1` through `30.5` resolved the 15 live-captured defects (`UX30-01`..`UX30-15`) across `Mon Assistant`, `Mes Processus`, and `Mes Agents & Compétences`. However, `UX30-16` identifies a residual risk: without dedicated CI anti-regression guards, golden empty-evidence prompt evals, bilingual (`fr`/`en`) Day-0 Playwright E2E coverage, and synchronized Zone 4 contextual help & UX documentation, future changes could reintroduce:
1. Hidden `display: none` modal Save buttons, off-modal error banners instead of inline `[role="alert"]` inside `AssistantGovernanceModalAndStudio` / `AgentDetailAndSandboxModal`, or `.evaluate()` hidden-button E2E workarounds.
2. Competing Bar 1/Bar 2 validation banners or redundant primary Edit CTAs inside `/processes/runs/$runId` (`ProcessRunActionBanner` / `ProcessRunFocusReviewPage`).
3. `DRAFT` agents leaking into Assistant `@agent` autocomplete, Processes delegate/step selection, or external MCP exposure without `HTTP 422` enforcement.
4. Internal prompt markers (`[CONSTITUTIONAL_IMMUTABLE_LAYER_1]`, `[NO_HUMAN_ANCHOR_WRITE]`, `human_authored_required`, `[EXPLICIT_PROVENANCE_URI]`, `[ACTIVE_DOMAIN_PACK:`, `[ADAPTATION_RUNTIME_METADATA]`), fabricated `orcia://` URIs, `[Citation non vérifiée]`, or empty-string `SHA-256("")` digests in empty-evidence Assistant prompts/responses.
5. Stale Zone 4 contextual help articles (`docs/help/{fr,en}/{assistant,processes,agents}.md`) and UX specs (`DESIGN.md`, `EXPERIENCE.md`) that fail to describe explicit modal Save, tabbed `/processes`, `/processes/runs/$runId` Focus Review, and the `DRAFT` vs `ACTIVE` agent lifecycle.

### 1.2 Exploration, GitNexus Impact Analysis, Refactoring & Technical Debt
- **GitNexus Impact Analysis (`gitnexus_query`, `gitnexus_context` scoped to `/home/romain/.gemini/antigravity/worktrees/ORCIA/consignes_personnelles_save_button`)**:
  - `AssistantCitationAndV5GuardService` / `_scrub_empty_evidence_artifacts` (`packages/orcia-core/src/orcia_core/orchestration/_assistant_citations_verifier.py`): post-stream citation sanitizer verified by `tests/evals/` and `tests/unit/test_story_30_2_assistant_conversational_prompt.py`.
  - `_agents_lifecycle_guards.py` (`apps/api/src/orcia_api/routers/_agents_lifecycle_guards.py`): centralized `DRAFT` blocking across `agents_and_skills.py`, `assistant_turns.py`, `executions_trace.py`, and `_workflows_pending_runs.py`.
  - `AssistantGovernanceModalAndStudio`, `AgentDetailAndSandboxModal`, `ProcessRunFocusReviewPage`, and `ProcessRunActionBanner`: canonical UI targets audited structurally and behaviorally by Vitest and Playwright E2E.
- **Exploration & Key Metrics**:
  - `tests/unit/test_e2e_sql_coverage_audit.py` enforces exact counts (`len(specs) == 27`, `total_blocks == 60`) and domain-table allowlists (`SPEC_ALLOWED_DOMAIN_TABLES`); adding `30-epic-30-ux-hardening-and-lifecycle.spec.ts` requires registering its `SPEC_ALLOWED_DOMAIN_TABLES` entry and updating those exact counts.
  - `apps/web/src/__tests__/e2e-testids-sync-audit.test.ts` enforces that every `getByTestId(...)` / `[data-testid=...]` in `apps/web/e2e/` resolves to UI source files.
  - `tests/unit/test_site_catalog_sync.py` and `infra/scripts/sync_site_catalog.py` check `docs/product/capabilities.yaml`, `docs/help/{fr,en}/*.md`, and Tech Lead report sync.
  - `detect-secrets` flags literal 64-char SHA-256 hex strings; all tests must compute `hashlib.sha256(b"").hexdigest()` dynamically.
- **Refactoring Opportunities & Emerging Technical Debt Mitigation**:
  - Keep all new Vitest, Python, and Playwright test files modular (`<= 300` lines each), sharing helper functions locally without touching unrelated production code unless an actual audit gap is uncovered.
  - Ensure zero `.evaluate()` hidden-button workarounds exist anywhere in `apps/web/e2e/`.

---

## 2. Implementation Plan

### 2.1 Data Schema & Alembic Migrations
- No schema changes required in Story 30.6; the new E2E spec will assert real PG18 persistence across `user_preferences`, `assistant_threads`, `assistant_thread_messages`, `workflow_v2_runs`, `workspace_datasources`, and `catalog_items`.

### 2.2 Hexagonal Core, Orchestration & Workers (`tests/evals/`, `tests/security/`, `tests/unit/`)
- `tests/unit/test_story_30_6_lifecycle_and_modal_guards_audit.py`:
  - Structural & FastAPI guard audit locking `DRAFT` agent `HTTP 422` exclusion across Assistant `@agent`, Processes workflow/run/reflexive routes, and MCP exposure (`PATCH .../governance`, `PUT /api/v1/mcp/exposure`), plus verifying zero `display: none` hidden Save buttons in `AssistantGovernanceModalAndStudio` / `AgentDetailAndSandboxModal` and zero `.evaluate(` hidden-button click workarounds in `apps/web/e2e/`.
- `tests/evals/test_story_30_6_assistant_clean_prompt_golden.py` (+ `tests/evals/golden/assistant_clean_prompt_30_6.jsonl`) and `tests/security/test_story_30_6_prompt_leak_and_draft_redteam.py`:
  - `$0` deterministic golden evals in `fr` and `en` verifying clean empty-evidence system prompts and post-stream citation scrubbing against `[CONSTITUTIONAL_IMMUTABLE_LAYER_1]`, `[NO_HUMAN_ANCHOR_WRITE]`, `human_authored_required`, `[EXPLICIT_PROVENANCE_URI]`, `[ACTIVE_DOMAIN_PACK:`, `[ADAPTATION_RUNTIME_METADATA]`, fabricated `orcia://`, `[Citation non vérifiée]`, and `hashlib.sha256(b"").hexdigest()`.

### 2.3 Backend API, Security & Contracts (`tests/unit/test_e2e_sql_coverage_audit.py`, `docs/product/capabilities.yaml`)
- Update `SPEC_ALLOWED_DOMAIN_TABLES` and exact spec/block counts in `tests/unit/test_e2e_sql_coverage_audit.py` for `30-epic-30-ux-hardening-and-lifecycle.spec.ts`.
- Register `apps/web/e2e/30-epic-30-ux-hardening-and-lifecycle.spec.ts` and Story 30.6 audits in `docs/product/capabilities.yaml` (`CAP-022`, `CAP-070`, `CAP-071`, `CAP-072`, `CAP-082`, `CAP-090`, `CAP-091`, `CAP-100`, `CAP-140`, `CAP-160`).

### 2.4 User Interface, Contextual Help & UX Docs (`apps/web/`, `docs/help/`, `docs/planning-artifacts/ux-designs/`)
- `apps/web/src/__tests__/epic-30-ux-hardening-audit.test.ts`:
  - Structural & behavioral audit verifying: (a) inline `[role="alert"]` errors inside `AssistantGovernanceModalAndStudio` & `AgentDetailAndSandboxModal` with zero `display: none` Save buttons and zero `.evaluate(` hidden-button workarounds in `apps/web/e2e/`; (b) single state-gated primary Cobalt CTA on `/processes/runs/$runId` (`ProcessRunActionBanner` / `ProcessRunFocusReviewPage`, no Bar 1/Bar 2 duplication); (c) `DRAFT` agent exclusion in `buildAssistantAutocompleteSuggestions` and `getDelegateAgents`.
- `apps/web/e2e/30-epic-30-ux-hardening-and-lifecycle.spec.ts`:
  - Bilingual (`fr` and `en`) Day-0 Playwright E2E spec (`resetDay0()` + `createFirstAdminViaUi`, `env -u ORCIA_E2E_SEED_FIXTURES`) covering Assistant governance explicit Save / Cancel / Escape / empty personal instructions, clean greeting reply without prompt leaks or `orcia://` hallucination, `/processes` default `Business Processes` / `Processus métiers` tab with zero fake pending badges + explicit run launch with attached datasource opening `/processes/runs/$runId` Focus Review, and `Mes Agents` `DRAFT` -> `ACTIVE` lifecycle + inline modal alert + explicit Save persisted to PG18.
- Update `docs/help/{fr,en}/{assistant,processes,agents}.md` and `docs/planning-artifacts/ux-designs/ux-ORCIA-2026-10-24/{DESIGN,EXPERIENCE}.md`, then run `sync_site_catalog.py`.

### 2.5 Test Pyramid Impact Analysis (`AD-17` — Layers 1 to 5 + Security)
- **Layer 1a & 1b**: `test_story_30_6_lifecycle_and_modal_guards_audit.py`, `test_e2e_sql_coverage_audit.py`, `epic-30-ux-hardening-audit.test.ts`, `e2e-testids-sync-audit.test.ts`, `zero-dead-buttons-and-silent-catches-audit.test.tsx`.
- **Layer 2**: Existing PG18 suites (`30.1`..`30.5`) + full PG18 assertions inside `30-epic-30-ux-hardening-and-lifecycle.spec.ts`.
- **Layer 3**: `test_site_catalog_sync.py` + `sync_site_catalog.py --check`.
- **Layer 4**: `tests/evals/test_story_30_6_assistant_clean_prompt_golden.py` (`$0` golden dataset `assistant_clean_prompt_30_6.jsonl`).
- **Security**: `tests/security/test_story_30_6_prompt_leak_and_draft_redteam.py`.
- **Layer 5**: `apps/web/e2e/30-epic-30-ux-hardening-and-lifecycle.spec.ts` (`desktop-cockpit`, `fr` & `en`, `env -u ORCIA_E2E_SEED_FIXTURES`).

---

## 3. Summary of Changes & Results (Independent Testing Verifier Closure)

### 3.1 Created & Modified Files
| File | Action | Concise Summary |
| :--- | :--- | :--- |
| `apps/web/src/__tests__/epic-30-ux-hardening-audit.test.ts` | Created | Structural & behavioral UI audit locking inline `[role="alert"]` errors inside `AssistantGovernanceModalAndStudio` / `AgentDetailAndSandboxModal`, zero `display: none` Save buttons, zero E2E `.evaluate(...click())`, single state-gated Cobalt CTA in `ProcessRunActionBanner`, and `DRAFT` exclusion in Assistant/Processes helpers (`284` L). |
| `tests/unit/test_story_30_6_lifecycle_and_modal_guards_audit.py` | Created | Python structural & FastAPI guard audit verifying zero `display: none` / `.evaluate(...click())`, Focus Review single banner without Bar 1/Bar 2 stacking, `0` Day-0 pending runs, and `422 ERR_DRAFT_AGENT_LIFECYCLE_BLOCKED` across Assistant/Processes/MCP (`154` L). |
| `tests/evals/golden/assistant_clean_prompt_30_6.jsonl` | Created | `$0` bilingual `fr`/`en` empty-evidence golden dataset (`6` cases) covering greetings, no-source Q&A, and empty personal instructions. |
| `tests/evals/test_story_30_6_assistant_clean_prompt_golden.py` | Created | Golden eval suite asserting clean `fr`/`en` empty-evidence system prompts and post-stream scrubbing of `[CONSTITUTIONAL_IMMUTABLE_LAYER_1]`, `[NO_HUMAN_ANCHOR_WRITE]`, `human_authored_required`, `[EXPLICIT_PROVENANCE_URI]`, `[ACTIVE_DOMAIN_PACK:`, `[ADAPTATION_RUNTIME_METADATA]`, fabricated `orcia://`, `[Citation non vérifiée]`, and `hashlib.sha256(b"").hexdigest()` (`146` L). |
| `tests/security/test_story_30_6_prompt_leak_and_draft_redteam.py` | Created | Red-team suite verifying `AssistantTurnEngine.n6_verify_citations_async` scrubbing on empty evidence and bilingual `fr`/`en` `422` refusal for `DRAFT` agents (`90` L). |
| `apps/web/e2e/30-epic-30-ux-hardening-and-lifecycle.spec.ts` | Created | Bilingual (`fr` & `en`) Day-0 Desktop Playwright E2E spec (`env -u ORCIA_E2E_SEED_FIXTURES`) verifying Assistant Settings explicit Save/Cancel/Escape, clean greeting reply, `/processes` default tab & `/processes/runs/$runId` Focus Review, `DRAFT` -> `ACTIVE` agent lifecycle & PG18 SQL persistence across `user_preferences`, `workspace_customization_overrides`, `workspace_datasources`, `assistant_threads`, `workflow_v2_runs`, and `catalog_items`. |
| `tests/unit/test_e2e_sql_coverage_audit.py` | Modified | Registered `30-epic-30-ux-hardening-and-lifecycle.spec.ts` domain tables (`len(specs) == 28`, `total_blocks == 62`). |
| `docs/product/capabilities.yaml` | Modified | Registered `30-epic-30-ux-hardening-and-lifecycle.spec.ts` and Story 30.6 audit tests under `CAP-022`, `CAP-070`..`CAP-072`, `CAP-082`, `CAP-090`, `CAP-091`, `CAP-100`, `CAP-140`, and `CAP-160`. |
| `docs/help/{fr,en}/{assistant,processes,agents}.md` | Modified | Synced Zone 4 contextual help articles with explicit modal Save, empty default personal instructions, conditional citations, `/processes` tabs & `/processes/runs/$runId` Focus Review, and `DRAFT`/`ACTIVE` agent lifecycle. |
| `docs/planning-artifacts/ux-designs/ux-ORCIA-2026-10-24/{DESIGN,EXPERIENCE}.md` | Modified | Documented Epic 30 modal save semantics, Focus Review layout, and `DRAFT`/`ACTIVE` lifecycle invariants. |
| `docs/implementation-artifacts/sprint-status.yaml` | Modified | Closed `30-6-epic-30-anti-regression-audits-bilingual-e2e-and-closure: done` and `epic-30: done`. |
| `docs/implementation-artifacts/tech-lead-reports/README.md` | Modified | Registered Story 30.6 closure metrics and Epic 30 completion. |
| `apps/web/src/generated/orciaSiteManifest.ts` & `docs/site-catalog/index.html` | Regenerated | Synchronized via `infra/scripts/sync_site_catalog.py`. |

### 3.2 Full Epic 30 Closure Verification Results (`AD-17` Post-`P1-1`/`P2-1`/`P2-4` Re-Verification)
- **File Line-Count Gate (`wc -l <= 300`)**:
  - Post-remediation production Python files: `apps/api/src/orcia_api/routers/workflows.py` (`292` L), `apps/api/src/orcia_api/routers/_workflows_pending_runs.py` (`295` L), `apps/api/src/orcia_api/dependencies/reflexive_execution.py` (`274` L); all Epic 30 handwritten production files remain `<= 299` L.
- **Python Static & Boundary Gates**:
  - `.venv/bin/ruff check .`: passed (`All checks passed!`).
  - `.venv/bin/ruff format --check .`: passed (`1776 files already formatted`).
  - `.venv/bin/mypy --strict packages/orcia-core packages/orcia-connectors apps/api apps/worker`: passed (`Success: no issues found in 866 source files`).
  - `.venv/bin/lint-imports`: passed (`907 files, 6581 dependencies`, `Contracts: 5 kept, 0 broken`).
  - `lint_spine.py`: passed (`total_findings: 0`).
  - `scripts/export_openapi.py --check`: passed (`0-diff`).
  - `.venv/bin/detect-secrets-hook --baseline .secrets.baseline`: passed (`0` findings).
- **Scoped Branch Coverage (`>= 90%`)**:
  - `coverage run --branch` across `dependencies/reflexive_execution.py` (`93%`), `routers/_workflows_pending_runs.py` (`90%`), and `routers/workflows.py` (`90%`): **`91%` total** (`345` Stmts / `80` Branch, `44` targeted unit tests; `.coverage*` cleaned).
- **Full Split Python Suites (`--no-cov`)**:
  - `tests/evals tests/security tests/contract`: **`193 passed`**.
  - `tests/unit`: **`1154 passed`**.
  - Impacted PG18 + Redis `testcontainers` integration (`test_story_30_3_pending_runs_and_live_guard_postgres18.py`, `test_story_30_5_agent_governance_and_lifecycle_pg18.py`, `test_dbos_return_loops_and_claim_check.py`, `test_story_16_3_dual_mode_processes_api.py`): **`7 passed`** (plus **`11 passed`** across full Epic 30 integration batch prior to `P1-1`/`P2-1`/`P2-4`).
- **Full TypeScript Monorepo (`pnpm turbo run lint typecheck test --concurrency=2`)**:
  - **`9/9` Turbo tasks passed** (`@orcia/api-client` `3 files / 20 tests`, `@orcia/ui` `40 files / 154 tests`, `@orcia/web` `95 files / 369 tests` = **`543` JS/TS tests**; i18n Gates 1–4 locked at `0` baseline).
- **Desktop Playwright E2E Closure (`env -u ORCIA_E2E_SEED_FIXTURES`, `--project=desktop-cockpit`)**:
  - Post-`P1-1`/`P2-1`/`P2-4` `/processes` & Focus Review re-verification (`12-epic16-reflexive-trace-and-line-inspector.spec.ts`, `20-process-studio-v2-finops-and-log-sink.spec.ts`, `30-epic-30-ux-hardening-and-lifecycle.spec.ts`): **`5 passed, 0 failed (1.9m)`** (completing the full 15-spec Epic 30 closure pass of **`30 passed, 1 skipped (mobile-only), 0 failed`**); temporary `docs/implementation-artifacts/e2e-campaign-epic-22/` cleaned up.
- **Registry, Docs & GitNexus Sync**:
  - `npx gitnexus analyze --index-only .`: indexed cleanly (`47,932 nodes | 141,600 edges | 786 clusters | 1533 flows`, `38.6s`).
  - `infra/scripts/sync_site_catalog.py`, `infra/scripts/sync_site_catalog.py --check`, `scripts/check_implementation_docs.py`, and `tests/unit/test_site_catalog_sync.py` executed cleanly (`0` errors).
