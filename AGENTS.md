<!-- bmad:context -->
<!-- Verified 2026-11-27 against db3afb5. Managed by bmad-project-context; edits inside this block replace on refresh. -->

## ORCIA

Hybrid TS (`pnpm`/`Turborepo`, `Vite`/`TanStack Router`, `React`, `Tailwind`) + Python (`uv`: `orcia-core`, `orcia-connectors`, `apps/api`, `apps/worker`; `FastAPI`, `DBOS`, `Dramatiq`, `SQLAlchemy`, `PG18`+`pgvector`, `Redis`, `SeaweedFS`).

## Core Invariants

- **[R-CORE-01]** Use `.venv/bin/*` (`python`, `pytest`, `ruff`, `mypy`, `alembic`, `lint-imports`); never system `python3` or global `pip`/`pytest`.
- **[R-CORE-02]** Strict TDD, `>=90%` coverage (`AD-17` 5 layers + security in `docs/testing-strategy.md`), vertical wiring (`apps/web->@orcia/api-client->apps/api->orcia_core->PG18`).
- **[R-CORE-03]** Never mock PG18 (SQLite) or Redis in integration tests (`testcontainers-python` + `DeterministicCassetteLLM`, `$0`); never combine `pytest --cov` with `testcontainers`.
- **[R-CORE-04]** Modular DAG (`lint-imports`): `orcia_kernel<-orcia_core<-orcia_connectors<-orcia_api/orcia_worker`; zero cycles, cross-domain `_internal`, or SDKs in `kernel`/`domain`/`ports`; DTOs in `orcia_api/schemas/`, errors in `<domain>/errors.py`, DI at Composition Root, `InMemory*` in `tests/unit/fakes/`, side effects via `domain_events_outbox`.
- **[R-CORE-06]** No deps outside `ARCHITECTURE-SPINE.md` without updating it (`lint_spine.py` = `0`).
- **[R-CORE-07]** No orphan `TODO`/`FIXME`; every `TODO(key)` cites an active story or `action_items` in `sprint-status.yaml`.
- **[R-CORE-11]** Sole committed story artifact: Tech Lead Report (`docs/implementation-artifacts/tech-lead-reports/`). For stories/non-trivial code/schema/API changes (docs/config/hygiene exempt), author §1–§2 pre-edit and §3 at closure; **never read or edit `tech-lead-reports/README.md`** (`pnpm site:sync` generates it). Grep `docs/product/capabilities.yaml` by ID; run `pnpm site:sync && pnpm site:check` when capabilities/spine/routes change. Files `<= 300–400` L.
- **[R-CORE-12]** Run checks via `.venv/bin/python scripts/agent_check.py {static|impact|full|all|fuzz}` under `timeout -k 10s` (no chained `ruff && mypy && pytest`, no `manage_task` polling, no loosening assertions/timeouts); scope GitNexus to active worktree (`impact` pre-edit, `detect-changes` pre-commit).
- **Worktree bootstrap**: If `.venv`, `.secrets.baseline`, or `_bmad/custom` is missing in the current checkout/worktree, run `bash scripts/init_worktree.sh` once before any Python, `pre-commit`, or BMAD command (idempotent).
- **Layer rules (on demand)**: backend (`apps/api`, `apps/worker`, `packages/orcia-*`, `infra/migrations`) → `docs/agent-playbooks/layers/backend.md`; frontend (`apps/web`, `packages/ui`, `packages/api-client`) → `docs/agent-playbooks/layers/frontend.md`.

## Read Discipline

- **[R-READ-01]** Read by symbol or bounded lines (`<=150` L if `>200` L); never re-read unchanged context.
- **[R-READ-02]** Never full-read `packages/api-client/src/generated/`, `openapi.json`, lockfiles, `epics.md`, `architecture.md`, or `tech-lead-reports/README.md`.
- **[R-READ-03]** Check `tests/README.md` before searching `tests/`.
- **[R-READ-04]** On edited files, `grep -n` + bounded read target symbols before editing.

## Where Things Are

- Spine/ADRs: `docs/planning-artifacts/architecture/architecture-ORCIA-2026-10-24/{ARCHITECTURE-SPINE.md,adr/}`
- Epics/Tracking: `docs/planning-artifacts/epics{.md,/}`, `docs/implementation-artifacts/sprint-status.yaml`, `docs/product/capabilities.yaml`
- Testing/Reset: `docs/testing-strategy.md`, `scripts/{agent_check.py,init_worktree.sh}`, `tests/README.md`, `pnpm db:reset`

<!-- /bmad:context -->

## On-Demand Role Playbooks

Load only your role: `docs/agent-playbooks/{coder,fixer,verifier,architect}.md`.
