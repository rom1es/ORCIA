# ORCIA Backend Layer Rules (`apps/api`, `apps/worker`, `packages/orcia-*`, `infra/migrations`)

Load before editing backend packages, workers, routers, or Alembic migrations.

- **[R-CORE-08]** Database & API invariants: use `UUIDv7` PKs; immutable raw-SQL Alembic migrations (`Expand -> Backfill -> Contract`, never import ORM models); preserve append-only `audit_ledger` & `blackboard_snapshots` triggers; return RFC 9457 `application/problem+json` with `trace_id`; enforce `RunAccessGuard`/`ScopeAccessGuard` (`403 ERR_OBSERVER_MODE_READ_ONLY`); keep DBOS/Dramatiq/Outbox steps idempotent with zero blocking I/O in ASGI or `N+1` SQL loops.
- **[R-CORE-09]** FastAPI, SSE & Security (`TID251`): zero sync HTTP/DB clients in routers (`app.state.http_client`, `AsyncSession`); SSE `/stream` must use real network `AsyncIterator` (no `.split(" ")`); keep LLM adapters, ontology (`OntologyGovernanceService`), and `locale` vendor/hat/language-agnostic; zero silent `except Exception:` blocks; validate external URLs with `is_safe_llm_endpoint_url`.
