<!-- bmad:context -->
<!-- Verified 2026-11-27 against 1b5557c. Managed by bmad-project-context; edits inside this block are replaced on refresh. Keep anything you want preserved outside the markers. -->

## ORCIA

Orchestration of Processes, Context, and Intelligent Agents — hybrid TypeScript (`pnpm 10.6` + `Turborepo 2.4`, `Vite 6.4` + `TanStack Router 1.166`, `React 19.1`, `Tailwind 4.3`) and Python (`3.12+` in `.venv/` across `uv` workspace `packages/orcia-core`, `packages/orcia-connectors`, `apps/api`, `apps/worker`; `FastAPI 0.143`, `DBOS Transact 3.6` + `Dramatiq`, `SQLAlchemy 2.1` Asyncio, `PostgreSQL 18` + `pgvector`, `Redis 7.4`, `SeaweedFS`). Planning lives in `docs/planning-artifacts/`, sprint tracking in `docs/implementation-artifacts/sprint-status.yaml`, Tech Lead reports in `docs/implementation-artifacts/tech-lead-reports/`, and delivered capabilities in `docs/product/capabilities.yaml`.

## Core Invariants

- **[R-CORE-01]** Use `.venv/bin/*` (`python`, `pytest`, `ruff`, `mypy`, `alembic`, `lint-imports`) for every Python command; never use system `python3` or global `pip`/`pytest`.
- **[R-CORE-02]** Enforce strict TDD (`Red -> Green -> Refactor`), `>= 90%` coverage policy (`AD-17` 5 layers + security in `docs/testing-strategy.md`), and full vertical wiring (`apps/web -> @orcia/api-client -> apps/api -> orcia_core -> PostgreSQL 18`).
- **[R-CORE-03]** Never mock PostgreSQL (with SQLite) or Redis in integration tests; use real `testcontainers-python` + `DeterministicCassetteLLM` (`0 $` CI), and never combine `pytest --cov` with `testcontainers`.
- **[R-CORE-04]** Enforce `AD-19`/`AD-20` modular monolith boundaries (`lint-imports`): `orcia_kernel <- orcia_core <- orcia_connectors <- orcia_api/orcia_worker`; zero cycles, zero cross-domain `_internal` imports, zero framework SDKs in `kernel`/`domain`/`ports`; HTTP `*Request`/`*Response` schemas only in `apps/api/src/orcia_api/schemas/`; per-domain errors in `<domain>/errors.py`; Composition Root DI only (`apps/api/src/orcia_api/dependencies/`, `apps/worker`); `InMemory*` fakes only in `tests/unit/fakes/`; non-blocking side effects via `domain_events_outbox`.
- **[R-CORE-05]** Never hand-edit `packages/api-client/src/generated/` or write untyped `fetch()` in `apps/web`; regenerate the OpenAPI 3.1 SDK (`0-diff` gate).
- **[R-CORE-06]** Never add third-party dependencies outside `ARCHITECTURE-SPINE.md` without updating the spine and passing `lint_spine.py` (`0` findings).
- **[R-CORE-07]** Never leave orphan `TODO`/`FIXME` comments; every `TODO(key)` must reference an active story or `action_items` entry in `sprint-status.yaml`.
- **[R-CORE-08]** Database & API invariants: use `UUIDv7` PKs; immutable raw-SQL Alembic migrations (`Expand -> Backfill -> Contract`, never import ORM models); preserve append-only `audit_ledger` & `blackboard_snapshots` triggers; return RFC 9457 `application/problem+json` with `trace_id`; enforce `RunAccessGuard`/`ScopeAccessGuard` (`403 ERR_OBSERVER_MODE_READ_ONLY`); keep DBOS/Dramatiq/Outbox steps idempotent with zero blocking I/O in ASGI or `N+1` SQL loops.
- **[R-CORE-09]** FastAPI, SSE & Security (`TID251`): zero sync HTTP/DB clients in routers (`app.state.http_client`, `AsyncSession`); SSE `/stream` must use real network `AsyncIterator` (no `.split(" ")`); keep LLM adapters, ontology (`OntologyGovernanceService`), and `locale` vendor/hat/language-agnostic; zero silent `except Exception:` blocks; validate external URLs with `is_safe_llm_endpoint_url`.
- **[R-CORE-10]** UI & Bilingual policy: keep Direction C tokens (`tokens.css`) and components in `@orcia/ui` (no router/API imports, `#6D28D9` reserved for `HumanLedAnchorCard`); zero internal jargon, `< 2 s` labels, systematic `ⓘ` contextual help; keep all chat, docs, commits, and code comments in **English** while keeping the web app and RFC 9457 errors 100% bilingual `fr`/`en` via typed `i18n` dicts (never inline `locale === "fr"` ternaries).
- **[R-CORE-11]** Governance & Traceability: check `docs/product/capabilities.yaml` before coding; author Tech Lead Report §1–§2 in `docs/implementation-artifacts/tech-lead-reports/` **before** any code edit and register in `README.md`; complete §3, update `capabilities.yaml`, and run `pnpm site:sync && pnpm site:check` before closure. Keep files `<= 300–400` lines.
- **[R-CORE-12]** Runner-only checks & GitNexus: invoke `.venv/bin/python scripts/agent_check.py {static|impact|full|all|fuzz}` under `timeout -k 10s` (never chained `ruff && mypy && pytest`, never `manage_task` polling loops, never loosen E2E/integration assertions or timeouts); scope GitNexus calls to the active ORCIA worktree path (never `list_repos`) and run `impact` pre-edit + `detect-changes` pre-commit.

## Read Discipline

- **[R-READ-01]** Read by symbol or bounded `StartLine`/`EndLine` (`<= 150` L for files `> 200` L); never re-read an unchanged file already in context.
- **[R-READ-02]** Never full-read `packages/api-client/src/generated/`, `openapi.json`, `pnpm-lock.yaml`, or `uv.lock`; use `grep` + bounded line ranges only.
- **[R-READ-03]** Consult `tests/README.md` for shared fixtures, fakes, and Vitest setup helpers before searching `tests/`.
- **[R-READ-04]** For files already edited in-session (where GitNexus lines drift), use `grep -n` + bounded line-range read; always read the exact target function and types immediately before editing.

## Where Things Are

- Architecture Spine & ERD: `docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24/{ARCHITECTURE-SPINE,architecture}.md`
- PRD, UX, Epics: `docs/planning-artifacts/prds/prd-ORCIA-2026-10-24/prd.md`, `docs/planning-artifacts/ux-designs/ux-ORCIA-2026-10-24/{DESIGN,EXPERIENCE}.md`, `docs/planning-artifacts/epics.md`
- Testing Strategy & Check Runner: `docs/testing-strategy.md`, `scripts/agent_check.py`, `tests/README.md`
- Day-0 DB Reset: `pnpm db:reset` (`infra/scripts/maintenance/09_reset_db_first_boot.py --apply`)

<!-- /bmad:context -->

## On-Demand Role Playbooks

Load only the playbook matching your assigned role (do not preload all roles):

| Role | Playbook | Scope |
| :--- | :--- | :--- |
| Coding Agent | [`docs/agent-playbooks/coder.md`](docs/agent-playbooks/coder.md) | `.agent_check/story_intent.md`, vertical wiring, `< 60 s` runner checks |
| Small-Context Fixer | [`docs/agent-playbooks/fixer.md`](docs/agent-playbooks/fixer.md) | Sequential bounce repair (`1` attempt, `<= 3`/story, `pro` escalation) |
| Testing Verifier | [`docs/agent-playbooks/verifier.md`](docs/agent-playbooks/verifier.md) | Full `AD-17`, `<= 20`-line bounce digest, KPIs & closure gates |
| Architect / Reviewer | [`docs/agent-playbooks/architect.md`](docs/agent-playbooks/architect.md) | `pro` boundaries, `T-D3` epic cadence, `VALIDATE` diff review |
