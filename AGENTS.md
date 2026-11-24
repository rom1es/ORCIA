<!-- bmad:context -->
<!-- Verified 2026-10-27 against 420a171. Managed by bmad-project-context; edits inside this block are replaced on refresh. Keep anything you want preserved outside the markers. -->

## ORCIA

Orchestration of Processes, Context, and Intelligent Agents — hybrid TypeScript (`pnpm 10.6` + `Turborepo 2.4`, `Vite 6.4` + `TanStack Router 1.166` SPA, `React 19.1`, `Tailwind CSS 4.3`) and Python (`3.12+` in `.venv/` across a 4-package `uv 0.13.5` workspace: `packages/orcia-kernel`, `packages/orcia-core`, `apps/api`, `apps/worker`; `FastAPI 0.143`, `DBOS Transact 2.14` + `Dramatiq 2.1`, `SQLAlchemy 2.1` Asyncio, `PostgreSQL 18.0` + `pgvector 0.8.7`, `Redis 7.4`, `SeaweedFS 4.17`) modular monolith. Planning lives in `docs/planning-artifacts/`, sprint tracking in `docs/implementation-artifacts/sprint-status.yaml`, and Tech Lead implementation reports in `docs/implementation-artifacts/tech-lead-reports/`.

## Policy

- Always use the project virtual environment `/home/romain/Documents/Projects/ORCIA/.venv` (`.venv/bin/python`, `.venv/bin/pytest`, `.venv/bin/ruff`, `.venv/bin/mypy`, `.venv/bin/alembic`, `.venv/bin/lint-imports`) for every Python command; never use system `python3` or global `pip`/`pytest`.
- Before implementing any User Story or evolution, act as a Tech Lead / Senior Dev: study the US, run a GitNexus impact analysis (`gitnexus_query`, `gitnexus_context`, `gitnexus_impact`), check for code factorization opportunities (`DRY` / shared primitives), split any file approaching `300–400` lines, and proactively add dedicated technical debt / refactoring tickets (`Story N.Ma` in `docs/planning-artifacts/epics.md` + `docs/implementation-artifacts/sprint-status.yaml` or entries under `action_items:` in `sprint-status.yaml`).
- For every User Story (`Story N.M`) **AND for every ad-hoc user request / bugfix / adjustment that modifies ORCIA**, generate **BEFORE making any code modification** a permanent Tech Lead Analysis & Implementation Report in `docs/implementation-artifacts/tech-lead-reports/` following `docs/implementation-artifacts/TECH-LEAD-REPORT-TEMPLATE.md`:
  - Named `docs/implementation-artifacts/tech-lead-reports/{YYYY-MM-DD}-{short-slug}-tech-lead-report.md` (prefixed with the current date `YYYY-MM-DD` and a short kebab-case description of the changes) for ad-hoc adjustments, bugfixes, or evolutions outside a numbered story; or `docs/implementation-artifacts/tech-lead-reports/{story-key}-tech-lead-report.md` for sprint stories.
  - Sections 1 (`Analyse du Besoin & Étude d'Impact Tech Lead`) and 2 (`Plan d'Implémentation`) MUST be written **before** editing application code, and Section 3 (`Bilan des Modifications & Résultats`) MUST be completed after passing all verification gates.
- Enforce strict TDD (`Red → Green → Refactor`) with a mandatory minimum unit test coverage of `>= 90%` (`--cov-fail-under=90`), full vertical wiring (`apps/web` $\rightarrow$ `@orcia/api-client` $\rightarrow$ `apps/api` $\rightarrow$ `orcia_core` $\rightarrow$ PostgreSQL 18), and all 5 testing layers (`AD-17`) before marking any Story or change `review` or `done`.
- Never mock PostgreSQL (with SQLite) or Redis in integration tests; always run against real ephemeral containers via `testcontainers-python` (PostgreSQL 18 + `pgvector`, Redis 7.4, SeaweedFS S3) and use `DeterministicCassetteLLM` (`0 $` external LLM calls in CI).
- Enforce unidirectional modular monolith boundaries (`AD-19`, verified by `.venv/bin/lint-imports`): `orcia_kernel` $\leftarrow$ `orcia_core` domains $\leftarrow$ `orcia_api` / `orcia_worker`, with zero circular dependencies between domain modules (`blackboard`, `catalog`, `permissions`, `orchestration`, `ontology`, `audit_finops`, `identity`, `bootstrap`), zero cross-domain `_internal` imports (`orcia_core.<domaine>._internal`), and zero framework/SDK imports (`fastapi`, `sqlalchemy`, `dbos`, `dramatiq`, `redis`, `litellm`, `docling`, `wasmtime`) inside `orcia_kernel`, `orcia_core/domain`, or `orcia_core/ports`.
- Keep HTTP/OpenAPI transport schemas (`*Request`, `*Response`) exclusively in `apps/api/src/orcia_api/schemas/<domaine>.py` — never inside `packages/orcia-core` — and define domain errors per bounded context in `packages/orcia-core/src/orcia_core/<domaine>/errors.py` inheriting from `orcia_kernel.errors.OrciaDomainError` (no central `domain/exceptions.py` catch-all).
- Wire all services and concrete adapters exclusively in the application Composition Root (`lifespan` + `Depends(get_*_service)` in `apps/api/src/orcia_api/dependencies.py` and `apps/worker`); never instantiate `_DEFAULT_*_SERVICE` singletons at module import time, and keep `InMemory*` stores exclusively under `tests/unit/fakes/`.
- Route non-blocking cross-domain side effects (`StepCompleted`, `ArtifactProduced`, `GateEvaluated`, `RunTerminated`, `HumanArbitrationRequested`) through the transactional PostgreSQL Outbox table `domain_events_outbox` (`orcia_kernel.events`); reserve synchronous cross-domain calls strictly for blocking workflow decisions (`permissions`, `gates`, human arbitration).
- Never hand-edit `packages/api-client/src/generated/` or write untyped `fetch()` in `apps/web`; regenerate the domain-sharded OpenAPI 3.1 SDK from FastAPI/Pydantic v2 (`0-diff` gate).
- Never add a third-party dependency outside `ARCHITECTURE-SPINE.md` without updating the spine and passing `.venv/bin/python .agent/skills/bmad-architecture/scripts/lint_spine.py --workspace docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24` (`0 findings`).
- Never leave orphan `TODO` or `FIXME` comments in code; every `TODO(key)` must reference an active story key or `action_items` entry in `docs/implementation-artifacts/sprint-status.yaml`.

## Where things are

- Architecture Spine (19 locked ADs & stack versions): `docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24/ARCHITECTURE-SPINE.md`
- Detailed Architecture & Core ERD (18 tables including `workspace_datasources` & `domain_events_outbox`): `docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24/architecture.md`
- Stack Review, Modularity Analysis & Sprint Change Proposal: `docs/planning-artifacts/research/stack-review-2026-10-27.md`, `docs/planning-artifacts/research/modularity-analysis-2026-10-27.md`, and `docs/planning-artifacts/sprint-change-proposal-2026-10-27.md`
- PRD v2.0 (36 FRs, 13 NFRs, 12 UJs): `docs/planning-artifacts/prds/prd-ORCIA-2026-10-24/prd.md`
- UX Design Tokens & Experience (Direction C, 16 UX-DRs): `docs/planning-artifacts/ux-designs/ux-ORCIA-2026-10-24/DESIGN.md` and `EXPERIENCE.md`
- Epics & 33 User Stories (`status: final`, 7 Epics): `docs/planning-artifacts/epics.md`
- Capabilities Registry (source of truth for delivered features, checked by `pnpm site:check`): `docs/product/capabilities.yaml`
- Testing Strategy & Zero-Test-Debt Governance (`AD-17` 5 Layers + Security & 10 Automated Anti-Debt Gates): `docs/testing-strategy.md`
- Sprint Tracking File: `docs/implementation-artifacts/sprint-status.yaml`
- Tech Lead Report Template: `docs/implementation-artifacts/TECH-LEAD-REPORT-TEMPLATE.md`
- Tech Lead Reports Directory: `docs/implementation-artifacts/tech-lead-reports/`

## Running and verifying

- Python commands must run through `.venv/bin/`: `.venv/bin/ruff check .`, `.venv/bin/ruff format --check .`, `.venv/bin/mypy --strict packages/orcia-kernel packages/orcia-core apps/api apps/worker`, `.venv/bin/lint-imports`, `.venv/bin/pytest --cov=packages/orcia-kernel --cov=packages/orcia-core --cov-fail-under=90`.
- TypeScript commands run via `pnpm`: `pnpm turbo run lint typecheck test`.
- Reset database to Day-0 initial boot state (`0` users, system bootstrap preserved): `pnpm db:reset` (or `.venv/bin/python infra/scripts/maintenance/09_reset_db_first_boot.py --apply`).
- Living Product & Architecture Showcase Site synchronization (`/showcase`, `apps/web/src/generated/orciaSiteManifest.ts` & standalone `docs/site-catalog/index.html` / `dist/orcia-site/index.html`): `pnpm site:sync` (and `pnpm site:check` for CI verification).
- Architecture spine lint: `.venv/bin/python .agent/skills/bmad-architecture/scripts/lint_spine.py --workspace docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24`.
- GitNexus index refresh: `npx gitnexus analyze` (run after structural changes and before `gitnexus_detect_changes()`).

## Conventions that differ from defaults

- All database primary keys use `UUIDv7` (`uuid-utils`), never `SERIAL` or `UUIDv4`.
- All schema evolutions go through incremental, immutable Alembic revisions in `infra/migrations/versions/` (with tested `upgrade()` and `downgrade()`); never edit a revision from a completed story, and never import application ORM models inside an Alembic migration — use raw SQL (`op.execute(sa.text(...))`) following the `Expand → Backfill SQL → Contract` pattern.
- Reference/system seed data (`orcia://system/bootstrap/*`, `assistant-agent` DAG, default Human Profile archetypes) uses idempotent upserts (`INSERT ... ON CONFLICT DO UPDATE`) in `packages/orcia-core/bootstrap/seeder.py`, and operational data transformations or backfills outside schema migrations live in `infra/scripts/maintenance/XX_*.py` with a mandatory `--dry-run` mode (default rollback unless `--apply` is passed) and batched idempotent transactions.
- Tables `audit_ledger` and `blackboard_snapshots` are strictly append-only (protected by PostgreSQL `BEFORE UPDATE OR DELETE RAISE EXCEPTION` triggers); never disable these triggers in migrations or maintenance scripts — draft artifacts live in `step_executions.draft_artifact_jsonb` and intermediate reasoning in `step_executions.step_memlog_jsonb`.
- Every API error returns an `application/problem+json` envelope (**RFC 9457 Problem Details**) carrying the W3C OpenTelemetry `trace_id`.
- Every mutation endpoint enforces `RunAccessGuard` / `ScopeAccessGuard` (`GLOBAL | BU | TEAM | WORKSPACE`) and rejects `READ_ONLY_OBSERVER` with `HTTP 403 ERR_OBSERVER_MODE_READ_ONLY`.
- All UX/UI components and Direction C semantic CSS tokens (`DESIGN.md`) MUST live in the dedicated Design System library `packages/ui` (`@orcia/ui`), isolated from `apps/web` routing, feature modules (`apps/web/src/features/<domaine>/`), stores, and API calls (`packages/ui` must never import `@tanstack/react-router`, `next/*`, or `@orcia/api-client`); never use raw hex colors outside `packages/ui/src/styles/tokens.css`, and reserve Violet `#6D28D9` (`human-led-violet`) exclusively for `HumanLedAnchorCard` (`human_authored_required: true`).
- **Language & Bilingual Application Policy (Mandatory)**:
  - **English-Only Development & Documentation**: All chat conversations, documentation (`docs/planning-artifacts/`, `docs/implementation-artifacts/`, ADRs, Epics, Stories, Tech Lead Reports), commit messages, and code comments/docstrings in Python and TypeScript MUST be written in **English**. Historical Tech Lead reports remain immutable.
  - **100% Bilingual FR/EN Web Application & API**: The web application (`apps/web` + `@orcia/ui`) and user-facing backend responses (`Accept-Language` RFC 9457 `problem+json` error catalogs and Assistant prompt locale bundles) MUST remain **100% compatible with both French (`fr`) and English (`en`)**, defaulting UI labels to French (`fr`) unless overridden by user preference or `Accept-Language`, backed by the typed zero-dependency `i18n` dictionary (`apps/web/src/i18n/locales/{fr,en}.ts` injected as typed props into `@orcia/ui`) and invariant RFC 9457 `error_code`s — never hardcode raw user-facing strings or inline `locale === "fr" ? ... : ...` ternaries in JSX, bridges, or controllers.

## Known pitfalls

- Never run blocking calls (`time.sleep`, `requests`, synchronous disk I/O, or synchronous `subprocess.run`) inside FastAPI's `asyncio` event loop or execute SQL queries inside Python `for` loops (`N+1`); use `selectinload`/`joinedload` or bounded recursive CTEs (`WITH RECURSIVE ... WHERE depth <= 2`).
- `DBOS Transact` steps and `Dramatiq` workers (`apps/worker`) may retry on transient failures — every workflow step, Outbox consumer, and actor must be idempotent and never duplicate `audit_ledger`, `blackboard_snapshots`, or `domain_events_outbox` rows.
- Never copy or extend the 3 legacy circular dependencies (`packages/orcia-core/src/orcia_core/blackboard/models.py:L15` $\leftrightarrow$ `orchestration/engine.py:L17-26`, `catalog/service.py:L14` $\leftrightarrow$ `bootstrap/workflows.py:L21`, `permissions/broker.py:L14` $\leftrightarrow$ `bootstrap/workflows.py:L29`) or the 3 import-time router singletons (`apps/api/src/orcia_api/routers/auth.py:L25`, `catalog.py:L27`, `orchestration.py:L39`) scheduled for removal in `Story 3.2a`.
- Always scope every GitNexus MCP tool call and resource lookup explicitly to `repo: "ORCIA"` (`gitnexus://repo/ORCIA/...` or `--repo .`) and never call `list_repos` or inspect other repositories registered in the user's global `~/.gitnexus/registry.json`.

<!-- /bmad:context -->

---

# Tech Lead / Senior Dev Protocol & Permanent Implementation Report

For **every User Story (`Story N.M`)** AND **every ad-hoc adjustment, bugfix, or evolution request in ORCIA**, the agent acts as **Tech Lead / Senior Dev** following the mandatory 3-phase cycle below. All chat communications, planning/architecture docs, Tech Lead reports, commit messages, and code comments/docstrings MUST be written in **English** (historical Tech Lead reports remain immutable), while the ORCIA web application (`apps/web`, `@orcia/ui`) and user-facing API outputs (`Accept-Language` RFC 9457 error catalogs, Assistant prompt bundles) remain **100% bilingual compatible in French (`fr`) and English (`en`)**.

## 1. Pre-Coding Impact Study, Factorization & Technical Debt
1. **Critical review of the requirement or US**: Verify Acceptance Criteria (`epics.md`), architecture decisions (`ARCHITECTURE-SPINE.md`, `architecture.md`), and UX specifications (`DESIGN.md`, `EXPERIENCE.md`).
2. **GitNexus impact analysis**: Run `gitnexus_query`, `gitnexus_context`, and `gitnexus_impact({target, direction: "upstream"})` on all affected existing symbols.
3. **Factorization opportunities & file-size control**:
   - Identify any reusable building block across `packages/orcia-kernel`, `packages/orcia-core`, `packages/api-client`, `apps/api`, or `apps/web` to eliminate duplication.
   - If any touched file approaches or exceeds **300–400 lines** (or mixes multiple responsibilities), plan an immediate modular split.
4. **Proactive technical debt / refactoring tickets**:
   - If the refactoring is small ($< 20\%$ of the US), execute it as **Step 0 (Pre-Story Refactoring)** of the current US.
   - If an emerging technical debt or structural refactoring exceeds the immediate US scope, **proactively create**:
     - either an intercalary **Story `Story N.Ma`** in `docs/planning-artifacts/epics.md` and `docs/implementation-artifacts/sprint-status.yaml`,
     - or a ticket under `action_items:` in `docs/implementation-artifacts/sprint-status.yaml`.

## 2. Pre-Implementation Tech Lead Report (`docs/implementation-artifacts/tech-lead-reports/`) — MANDATORY BEFORE CODE EDITS
**Before making any code modification in ORCIA**, always generate a Tech Lead report in **`docs/implementation-artifacts/tech-lead-reports/`** following the official template [TECH-LEAD-REPORT-TEMPLATE.md](file:///home/romain/Documents/Projects/ORCIA/docs/implementation-artifacts/TECH-LEAD-REPORT-TEMPLATE.md):
- **Mandatory naming convention**:
  - For any ad-hoc adjustment, bugfix, or evolution outside a Story: **`docs/implementation-artifacts/tech-lead-reports/{YYYY-MM-DD}-{short-slug}-tech-lead-report.md`** (prefixed by today's date `YYYY-MM-DD` followed by a short `kebab-case` summary, e.g., `2026-11-04-persistance-admin-jour0-et-reinit-bdd-tech-lead-report.md`).
  - For a sprint User Story: **`docs/implementation-artifacts/tech-lead-reports/{story-key}-tech-lead-report.md`** (or `{YYYY-MM-DD}-{story-key}-tech-lead-report.md`).
- **2-phase authoring cycle (in English)**:
  1. **BEFORE any code modification**: create the report file with **Section 1 (`Needs Analysis & Tech Lead Impact Study`)** and **Section 2 (`Implementation Plan`: `2.1` Alembic, `2.2` Hexagonal core & workers, `2.3` Backend FastAPI & OpenAPI SDK, `2.4` Vite + TanStack Router Direction C SPA, `2.5` `AD-17` Test Pyramid Impact)**.
  2. **AFTER implementation and passing all 5 test layers**: complete **Section 3 (`Summary of Changes & Results`)** (created/modified files table, quantitative metrics & coverage $\ge 90\%$, `AD-17` 5-layer validation, and `gitnexus_detect_changes()` output), register the report in `docs/implementation-artifacts/tech-lead-reports/README.md`, and run **`pnpm site:sync`** (`.venv/bin/python infra/scripts/sync_site_catalog.py`) to synchronize the `/showcase` manifest and standalone site `docs/site-catalog/index.html`.

## 3. Five Mandatory Vertical Wiring Guardrails (Zero UI / API / SQL Silos)
To prevent partially wired features (orphan SQL adapters, ephemeral `useState` stores lost on `F5` reload, or dead buttons missing an optional callback):
1. **Zero Orphan SQL Adapters (GitNexus Gate & AST Audit)**: Every SQL function/class in `_internal/sql_*.py` or `adapters/postgres_*.py` MUST have at least one active caller in `apps/api` or `apps/worker` (`gitnexus_impact({target, direction: "upstream", repo: "ORCIA"})` $\rightarrow$ `impactedCount >= 1` outside `tests/` — enforced by `Story 22.8a` AST audit).
2. **Vertical Integration Test `HTTP ➔ PostgreSQL 18` on Real Composition Root (Layer 2 `AD-17`)**: `testcontainers` PostgreSQL 18 integration tests MUST boot the real `create_app()` Composition Root **without `dependency_overrides` or manual `app.state.*` injection** (verified in `Story 22.8a`), invoke the FastAPI HTTP route **AND** verify persistence via a direct SQL `SELECT` on PostgreSQL 18 (plus cold re-read after memory cache eviction).
3. **Ban Ephemeral Business `useState` Stores & Enforce F5 / Cold PG18 Survival Gate (`apps/web`)**: Every user-created or user-mutated business state in `apps/web` MUST call `@orcia/api-client` (typed payloads against `packages/api-client`, never raw untyped `page.request.post/put/patch`), rehydrate on startup via `GET`, and survive `reload()` / `unmount()` after memory cache eviction (`reloadColdFromPg` in `Story 22.8`).
4. **Day-0 Ground Truth (`pnpm db:reset`) without Hidden Fixtures**: Any change affecting Day-0 bootstrap or initial setup MUST be verified after resetting via `pnpm db:reset` ([`infra/scripts/maintenance/09_reset_db_first_boot.py`](file:///home/romain/Documents/Projects/ORCIA/infra/scripts/maintenance/09_reset_db_first_boot.py)), without `ORCIA_E2E_SEED_FIXTURES` (purged in `Story 22.8`).
5. **Zero Dead Buttons, Zero Forgotten Optional Callbacks, `data-testid` Sync & Zero `.catch(() => undefined)` on User Actions (`apps/web/src/__tests__/zero-dead-buttons-and-silent-catches-audit.test.tsx`)**: Every interactive `@orcia/ui` component mounted in `apps/web` MUST receive all of its action callbacks, be audited under a real `<RouterProvider>` without neutral short-circuits, maintain synchronized E2E↔UI `data-testid` attributes (`e2e-testids-sync-audit.test.ts`), and never swallow network errors (`[role="alert"]` visible on `>= 400`).

## 4. Four Anti-Regression Invariants for FastAPI, SSE Streaming, Multi-Provider & Security (Mandatory)
To guarantee `100%` non-blocking execution, AI provider agnosticism, fidelity to the ORCIA Ontology, and zero silent failures (enforced by [`tests/unit/test_codebase_architectural_anti_patterns_audit.py`](file:///home/romain/Documents/Projects/ORCIA/tests/unit/test_codebase_architectural_anti_patterns_audit.py) and Ruff rule `TID251` in `pyproject.toml`):
1. **Rule 1 — Zero Synchronous HTTP or DB Clients in the ASGI Event Loop (`TID251`)**: Strictly forbidden to use `httpx.Client`, `requests`, `urllib.request`, `concurrent.futures.ThreadPoolExecutor`, `asyncio.run()`, or ad-hoc `create_async_engine()` inside `apps/api/src/orcia_api/routers/`. Every outbound HTTP call uses `request.app.state.http_client` (`httpx.AsyncClient` initialized in `app_lifespan`), and every SQL query uses `request.app.state.db_engine` / `request.app.state.session_maker` (`AsyncSession`) or an injected `Depends(...)` service.
2. **Rule 2 — Zero "Fake Streaming" & Full Markdown Preservation**: Every SSE endpoint (`/stream`) MUST be `async def` and consume a real network `AsyncIterator` (`resp.aiter_lines()` with `"stream": True`). Never await the full response and split via `.split(" ")` (which destroys TTFT and strips `\n` newlines and code indentation).
3. **Rule 3 — Zero Hardcoded Provider (`ollama`/`openai`), Locale (`fr`), or Role (`HAT`) Coupling in `apps/api`**:
   - No router/bridge helper may be named after a specific LLM vendor (`_is_ollama_endpoint`, `_build_ollama_root_url`). Use provider-agnostic adapters (`OpenAI-compatible` `/v1/chat/completions`, `Anthropic` `/v1/messages`, `Gemini`, etc.).
   - Strictly separate the reasoning channel (`thinking` / `reasoning_content` / `<think>`) from `content` (never inject `raw_reasoning` into `content` when `content` is empty, and never hardcode `"think": False` on reasoning models).
   - Always resolve the role (`active_hat`), business concepts (`L1–L4`), and context via the ORCIA Ontology (`OntologyGovernanceService`, `ProfileSemanticTranslator`) and the 5-layer prompt (`AssistantHarness`), never via hardcoded dictionaries in `orcia_api`.
   - Always propagate `locale` (`Accept-Language` / user profile) and instruct the model to respond in the user's message language (zero hardcoded `"Réponds toujours en français"` or `"Always reply in English"` outside `PROMPT_LOCALES`).
4. **Rule 4 — Zero Silent `except Exception:` Blocks & Mandatory SSRF Guard**:
   - No `except Exception:` block in `apps/api`, `apps/worker`, or `packages/orcia-core` may silently swallow errors (`pass` / `return None`) without structured logging via `get_logger(...)` (`logger.warning` / `logger.error`) or explicit benign-teardown annotation, nor return hardcoded fake latencies.
   - Every database-configured external endpoint URL MUST be validated by an SSRF guard (`is_safe_llm_endpoint_url`) blocking cloud metadata / link-local IPs (`169.254.0.0/16`, `169.254.169.254`, `fe80::/10`, `metadata.google.internal`, `100.100.100.200`) while respecting allowed private hosts configured via `ORCIA_LLM_ALLOWED_PRIVATE_HOSTS`.

## 5. Capabilities Registry & PRD ↔ Epics ↔ Delivered Traceability (MANDATORY — Anti-Dispersion)
Single source of truth for "what is live": [`docs/product/capabilities.yaml`](file:///home/romain/Documents/Projects/ORCIA/docs/product/capabilities.yaml) (one `CAP-xxx` entry per capability: `fr`, `fr_proposed`, `origin: epic|adhoc`, `origin_ref`, `status`, `surfaces`). The PRD captures intent (`FR`), `epics.md` / `sprint-status.yaml` capture planning, Tech Lead reports record history, and the registry links them to actual code surfaces.
1. **Before any work (Story, evolution, bugfix, adjustment)**: consult `capabilities.yaml` (+ `FR Coverage Map` in `epics.md` and `sprint-status.yaml`) to locate the relevant capability, avoid duplicates, and detect overlaps with `backlog` Stories. If a need overlaps a `backlog` Story, report and rebase it instead of building in parallel.
2. **In the Tech Lead report (Section 1)**: specify `Capability(ies)` (`CAP-xxx` existing, new `CAP-xxx` to create, or `none (hygiene/NFR/UX)`) and classification `feature | hygiene | ux | doc`.
3. **After implementation (before `done` / task completion)**: create or update the `CAP-xxx` entry (`status`, `origin_ref` = story-key or report slug, route/API/UI/migration surfaces, verification date) and run `pnpm site:check`: any SPA route or FastAPI router lacking an associated capability fails the check.
4. **Every functional evolution outside a Story** must map to a PRD `FR`, a `proposed_fr` (`FR-3x` in the registry), or Epic 13 "Continuous Evolutions" (retroactive Story `13.x`); never leave an orphan feature. Hygiene work (cleanup, a11y, wiring, refactoring) is classified under NFR / guardrails, not features.
5. **Documentation consistency**: an `FR` added to the PRD must be added to `epics.md`'s `FR Coverage Map`; a Story status change must be reflected in both `sprint-status.yaml` AND `capabilities.yaml`; the `FR` count cited in this file must match the PRD.
6. **`verification` status**: `docs` (inferred from reports/routers) is not proof; upgrade to `runtime` only after a real end-to-end execution (E2E test / `pnpm db:reset`), and always populate `tests:` in `docs/product/capabilities.yaml` (checked in CI by `pnpm site:check`: no `live` capability may lack a referenced test).

## 6. Systematic Impact Review Across the Full Test Pyramid (`AD-17` — Layers 1 to 5 + Security, MANDATORY)
Full testing strategy and 10 anti-test-debt locks: [`docs/testing-strategy.md`](file:///home/romain/Documents/Projects/ORCIA/docs/testing-strategy.md).
For **every User Story (`Story N.M`)** AND **every ad-hoc request (evolution, bugfix, UX/API/SQL refactoring)**, the agent MUST conduct a cross-cutting impact review across all **6 test layers** **before coding** (in Tech Lead report Section 1/2) AND **after coding** (in Section 3.3):
1. **Layer 1a — Python Unit & Router Tests (`tests/unit/`, `>= 90%` required including combined coverage)**:
   - `.venv/bin/pytest tests/unit --cov=packages/orcia-kernel --cov=packages/orcia-core --cov-fail-under=90`
2. **Layer 1b — Frontend TS/React Unit & Component Tests without `isJsdom` short-circuits or permissive mocks (`packages/ui/src/__tests__/`, `apps/web/src/__tests__/`, `packages/api-client/src/__tests__/`)**:
   - `pnpm turbo run lint typecheck test`
   - Strictly forbidden to introduce `if (isJsdom) return;` in `apps/web/src/`: every `@orcia/api-client` call under Vitest traverses the simulated HTTP/SSE transport (`apps/web/src/__tests__/vitest.setup.ts`, hardened *Fail-Closed* against `openapi.json` in `Story 22.8a`, guarded by `runtime-env-guard-audit.test.ts`, `e2e-testids-sync-audit.test.ts`, `zero-dead-buttons-and-silent-catches-audit.test.tsx`, and the Epic 27 i18n AST/parity/error-code audits).
3. **Layer 2 — Vertical Integration `HTTP FastAPI ➔ PostgreSQL 18 / Redis 7.4 / SeaweedFS` without overrides or manual `app.state.*` (`tests/integration/`)**:
   - `.venv/bin/pytest tests/integration`
   - Every router creation/modification or SQL persistence change MUST be verified via the real `create_app()` Composition Root without `dependency_overrides` or manual `app.state.*` injection (`test_composition_root_zero_ram_silo_postgres18.py`, `test_http_vertical_day0_and_agents_postgres18.py`, `test_epics_1_7_vertical_sql_wiring_postgres18.py`) followed by a direct SQL `SELECT` on PostgreSQL 18.
4. **Layer 3 — OpenAPI 3.1 Contracts (`0-diff`), Conformance & Hexagonal Boundaries (`tests/contract/`, `tests/conformance/`)**:
   - `.venv/bin/pytest tests/contract tests/conformance` + `.venv/bin/lint-imports` + `lint_spine.py`.
5. **Layer 4 — Deterministic AI Orchestration & `$0` "Golden Dataset" Evals (`tests/evals/`)**:
   - `.venv/bin/pytest tests/evals`
   - Any change touching the 5-layer prompt (`AssistantHarness`), `[S1]/[G1]/[O1]` citations, 3-speed routing, or `L1–L4` Ontology MUST update and pass the golden datasets (`tests/evals/golden/*.jsonl`).
6. **Security / Red-Team Layer (`tests/security/`)**:
   - `.venv/bin/pytest tests/security`
   - Always verify: SSRF guard (`is_safe_llm_endpoint_url`), `HTTP 403 ERR_OBSERVER_MODE_READ_ONLY` rejection for `READ_ONLY_OBSERVER` on every new mutation route, RBAC/ABAC confinement (`403 ERR_GRANT_ESCALATION_FORBIDDEN`), `CONFIDENTIAL_RESTRICTED` masking, and zero plaintext secret leaks (`DEC-SEC-01`).
7. **Layer 5 — Dual-Server Playwright Browser End-to-End Tests (`apps/web/e2e/*.spec.ts`, Desktop `1440×900` + Mobile `390×844`)**:
   - `pnpm e2e` (automatically starts ephemeral PostgreSQL 18 + Redis 7.4, runs `09_reset_db_first_boot.py --apply` without `ORCIA_E2E_SEED_FIXTURES`, starts FastAPI `:8100` with `ORCIA_USE_CASSETTE_LLM=true` and `ORCIA_ENV=e2e` plus Vite `:3101` on dedicated ports).
   - **Shift-Left E2E Alignment Duty**: any modification to a screen, `data-testid` selector, Day-0 modal, SPA route, locale dictionary, or API flow MUST inspect and update impacted Playwright specs (`apps/web/e2e/*.spec.ts` via `typedApiRequest.ts` and `reloadColdFromPg()` in `Story 22.8`) as well as the `tests:` list of the corresponding capability in `docs/product/capabilities.yaml`.

---

# Fundamental UX & UI Rules (Design Invariants)

Every design, review, or implementation in `@orcia/ui` (`packages/ui`) and `apps/web` MUST strictly follow these **11 fundamental rules** ([`EXPERIENCE.md`](file:///home/romain/Documents/Projects/ORCIA/docs/planning-artifacts/ux-designs/ux-ORCIA-2026-10-24/EXPERIENCE.md) and [`DESIGN.md`](file:///home/romain/Documents/Projects/ORCIA/docs/planning-artifacts/ux-designs/ux-ORCIA-2026-10-24/DESIGN.md)):

## 1. The 6 Fundamental UX Rules (User Experience)
UX governs the user journey, fluidity, and portal navigation logic:
1. **User-centered design**: Design for target users' real needs (by **Human Profile**), never internal team preferences.
2. **Aim for simplicity (Hick's Law / Minimalism)**: Remove superfluous elements to avoid cognitive overload (1 module = 1 clear intent; no out-of-context panel stacking).
3. **Follow web standards**: Use familiar navigation patterns (top-left logo/identity linking home, structured header and navigation).
4. **Provide clear feedback**: Every user action (click, submit, error) must produce immediate visual or textual feedback (localized in both `fr` and `en`).
5. **Offer clear exits**: Users must always be able to cancel an action, close a modal/drawer (`Escape`), collapse a panel, or go back cleanly.
6. **Optimize performance and Mobile-First**: Prioritize loading/rendering speed and design mobile views without horizontal overflow (Mobile Companion).

## 2. The 5 Fundamental UI Rules (User Interface)
UI translates UX into tangible, aesthetic, functional visual elements:
1. **Visual hierarchy**: Guide the eye using scale, contrast, spacing, and font weight to separate primary from secondary content.
2. **Typography cap (Max 2)**: Restrict to **at most two font families** — one primary (`Inter` / `Geist Sans` for UI, headings, and prose) and one secondary (`JetBrains Mono` / `Geist Mono` for URIs, hashes, and code) — for clean readability.
3. **Visual consistency**: Use one unified component library in `@orcia/ui` (buttons, cards, and badges strictly consistent for identical actions).
4. **Grid discipline**: Structure pages with consistent columns, gutters (`gap`), and margins to align all elements cleanly.
5. **Contrast & accessibility (WCAG AA)**: Ensure text and background color combinations meet WCAG AA contrast standards.

## 3. The 3 Mandatory User-Centric Microcopy & Targeted Contextual Help (`ⓘ`) Rules
All UI texts, labels, tooltips, and screens in `@orcia/ui` and `apps/web` (`apps/web/src/i18n/locales/*.ts`, supporting both `fr` and `en`) MUST obey these 3 rules without exception:
1. **Zero internal ORCIA plumbing or implementation jargon in the UI**: Always write from the end user's business perspective. No internal engineering term, SQL table name, engine name, or architecture token (`DBOS`, `PostgreSQL 18`, `PG18`, `pgvector`, `halfvec`, `Outbox`, `domain_events_outbox`, `Wasmtime`, `Starlark`, `Argon2id`, `OIDC PKCE`, `Passthrough`, `Service Principal`, `Tie-Break`, `Rubber-stamping`, `What-If`, `Rebase`, `Verrou V1..V5`, `RRF`, `BM25`, `HNSW`, `CTE`, `AD-10`, `AD-15`, `RFC 9457`, `human_authored_required`, `WAITING_FOR_HUMAN_ARBITRATION`, `CONTRIBUTOR_ACTION_REQUIRED`, `READ_ONLY_OBSERVER`, `ORCIA_BOOTSTRAP_TOKEN`, etc.) may ever appear in user-visible texts.
2. **Self-explanatory immediate labels (< 2 seconds)**: Every page heading, tab, card, button, or form field must enable the user to understand in under 2 seconds what is displayed and what action is expected, without wordy prose or abstract jargon.
3. **Zero explanatory prose walls in the workspace — Systematic `ⓘ` (`ContextualInfoTriggerButton`) link to the right help column**: Never clutter a central workspace screen, card, or form with an explanatory paragraph. Place a discrete `ⓘ` button beside the title or label (`<ContextualInfoTriggerButton sectionId="..." />` from `@orcia/ui`, `18px × 18px` circle) whose click **automatically opens the right contextual help column** (Zone 4) and **scrolls to / highlights the matching help section** (`data-testid="help-section-${sectionId}"`, `data-active="true"`).


<!-- gitnexus:start -->
# GitNexus — Code Intelligence

This project is indexed by GitNexus as **ORCIA** (541 symbols, 699 relationships, 17 execution flows).

> Index stale? Run `node .gitnexus/run.cjs analyze --index-only` from the project root — it auto-selects an available runner. No `.gitnexus/run.cjs` yet? Bootstrap with `npx`, `bunx`, or `pnpm dlx` — e.g. `bunx gitnexus@latest analyze` (npm 11 npx crash; #1939).

## Always Do

- **MUST run impact before editing.** Use `impact({target: "symbolName", direction: "upstream"})` or `node .gitnexus/run.cjs impact "symbolName" --direction upstream --repo .`; report callers, processes, and risk. Never substitute grep for graph analysis.
- **MUST analyze graph changes before committing.** Use `detect_changes({scope: "all"})` (MCP) or `node .gitnexus/run.cjs detect-changes --scope all --repo .` (CLI fallback). `partial: true` or `truncated: true` is not a clean check — a zero means unseen, not unaffected; re-run it. For regression review: `detect_changes({scope: "compare", base_ref: "main"})` or `node .gitnexus/run.cjs detect-changes --scope compare --base-ref "main" --repo .`.
- MUST warn on HIGH/CRITICAL `risk` pre-edit; never use `riskSharedAxes` to waive a HIGH/CRITICAL `risk` warning. Compare File/symbol: MCP File omits axes; Graph-RAG expands File.
- **MUST treat `risk: UNKNOWN` as unresolved, not as low.** An empty caller set is not evidence the symbol is unused — it can also mean the callers are not resolvable by the index (plain-object property access, dynamic dispatch, cross-language calls). `impact` pairs `UNKNOWN` with a `riskNote` saying so. Confirm with a text search before treating the symbol as safe to change or delete; do not proceed on the strength of a zero.
- **MUST use `query({search_query: "concept"})` for concepts/flows, `context({name: "symbolName"})` for a named symbol, or `impact` for blast radius, on read-only callers, dependencies, imports, or execution flow.** Graph first; text search only for empty/`UNKNOWN`/literals.
- For security review, `explain({target: "fileOrSymbol"})` lists taint findings (source→sink flows; needs `analyze --pdg`).

## Never Do

- NEVER edit a function, class, or method before MCP/CLI impact analysis.
- NEVER ignore HIGH or CRITICAL risk warnings from impact analysis, and never read `UNKNOWN` as an all-clear — it means the walk could not answer, which is the one verdict that requires confirming by other means.
- NEVER rename symbols with find-and-replace — use `rename` which understands the call graph.
- NEVER commit before MCP/CLI graph change analysis.

## Resources

| Resource | Use for |
| --- | --- |
| `gitnexus://repo/ORCIA/context` | Codebase overview, check index freshness |
| `gitnexus://repo/ORCIA/clusters` | All functional areas |
| `gitnexus://repo/ORCIA/processes` | All execution flows |
| `gitnexus://repo/ORCIA/process/{name}` | Step-by-step execution trace |

## CLI

| Task | Read this skill file |
| --- | --- |
| Understand architecture / "How does X work?" | `.claude/skills/gitnexus-exploring/SKILL.md` |
| Blast radius / "What breaks if I change X?" | `.claude/skills/gitnexus-impact-analysis/SKILL.md` |
| Trace bugs / "Why is X failing?" | `.claude/skills/gitnexus-debugging/SKILL.md` |
| Rename / extract / split / refactor | `.claude/skills/gitnexus-refactoring/SKILL.md` |
| Tools, resources, schema reference | `.claude/skills/gitnexus-guide/SKILL.md` |
| Index, status, clean, wiki CLI commands | `.claude/skills/gitnexus-cli/SKILL.md` |

<!-- gitnexus:end -->
