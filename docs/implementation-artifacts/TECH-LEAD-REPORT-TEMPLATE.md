# [Story N.M or YYYY-MM-DD — Implementation / Adjustment / Feature Name]

> **Mandatory File Naming Convention (Must be created BEFORE any code modification)**:
> - Ad-hoc adjustment, bugfix, or evolution outside a Story: `docs/implementation-artifacts/tech-lead-reports/{YYYY-MM-DD}-{short-slug}-tech-lead-report.md`
> - Sprint User Story: `docs/implementation-artifacts/tech-lead-reports/{story-key}-tech-lead-report.md`
> - **Language Policy**: Author all new Tech Lead reports in **English** (historical reports remain immutable).

- **Date**: YYYY-MM-DD
- **Story / Sprint Key**: `{story-key}` or `{YYYY-MM-DD}-{short-slug}` (`Epic N` / `Cross-Cutting Adjustment`)
- **Capability(ies)**: `CAP-xxx` (existing to update / new to create in `docs/product/capabilities.yaml`) or `none (hygiene/NFR/UX)` — classification: `feature | hygiene | ux | doc` (see `AGENTS.md` §5)
- **Author / Context**: [Business context, primary goal, problem solved, `FR-*`, `NFR-*`, `AD-*`, `UX-DR*` requirements covered]
- **Associated Commits**: `hash1`, `hash2`

---

## 1. Needs Analysis & Tech Lead Impact Study (Pre-Implementation)

### 1.1 Context & Problem Statement
- [Description of the business/technical problem or opportunity]
- [Expected behavior vs current behavior]
- [Collateral impacts or specific constraints from `ARCHITECTURE-SPINE.md`]

### 1.2 Exploration, GitNexus Impact Analysis, Refactoring & Technical Debt
- **GitNexus Impact Analysis (`gitnexus_query`, `gitnexus_context`, `gitnexus_impact`)**:
  - [Touched existing symbols, direct upstream callers, impacted processes, risk level]
- **Exploration & Key Metrics (Database / Containers / Benchmarks)**:
  - [SQL queries / CTEs or exploratory scripts executed]
  - [Observed volumes, identified edge cases, measured signals]
  - [Conclusions justifying technical choices]
- **Refactoring Opportunities & Emerging Technical Debt Mitigation**:
  - [Shared primitives extracted or reused (`packages/orcia-core`, `packages/api-client`, `@orcia/ui` components)]
  - [File line-count control (`<= 300–400` lines) and modular splits performed]
  - [Technical debt / refactoring tickets created: `Story N.Ma` in `epics.md` or `action_items` entries in `sprint-status.yaml`]

---

## 2. Implementation Plan

### 2.1 Data Schema & Alembic Migrations (`infra/migrations/versions/...`, if applicable)
- `infra/migrations/versions/XXXX_migration_name.py`:
  - Tables, columns (`UUIDv7`), types, integrity constraints, and PostgreSQL 18 triggers (e.g., Append-Only `audit_ledger` / `blackboard_snapshots`).
  - B-Tree / GIN (`tsvector`) / HNSW (`pgvector halfvec(1024)`) / partial indexes created and performance rationale.
  - Reversibility validation (`upgrade()` and `downgrade()`).

### 2.2 Hexagonal Core, Orchestration & Workers (`packages/orcia-core/`, `apps/worker/`, `infra/sandbox/`)
- `packages/orcia-core/<domain>/...`:
  - Algorithmic logic, complexity (McCabe $\le 10$), data structures, and domain invariants (zero framework imports inside `domain/` and `ports/`).
  - Isolation rules and architectural guardrails (`AD-1` to `AD-25`: e.g., `run-lock.json` immutability, `AD-3` human anchors, `AD-10` model orthogonality, `AD-9` `--unshare-net` sandbox).
- `apps/worker/...`:
  - Dramatiq actors, retry idempotency guarantees, and error handling.

### 2.3 Backend API, Security & Contracts (`apps/api/`, `packages/api-client/`)
- `apps/api/repositories/...` & `apps/api/services/...`:
  - New functions, recursive CTEs (`WITH RECURSIVE`), aggregation queries (zero `N+1`), multi-level scope filters (`GLOBAL | BU | TEAM | WORKSPACE`), pagination, and `Unit of Work` transactions.
- `apps/api/routers/...` & `apps/api/dependencies/...`:
  - Exposed FastAPI endpoints, RBAC/ABAC guards (`RunAccessGuard`, `HTTP 403` rejection in `READ_ONLY_OBSERVER`), Pydantic v2 schemas, bilingual **RFC 9457 Problem Details** error envelopes (`Accept-Language`), and OpenTelemetry `trace_id` correlation (`structlog`).
- `packages/api-client/`:
  - TypeScript SDK regeneration via `openapi-typescript` (`0-diff` verified).

### 2.4 User Interface & Experience (`apps/web/`, `packages/ui/`)
- TanStack Router routes (`apps/web/src/...`) and React 19 / `@orcia/ui` components created or modified.
- Direction C Design Tokens compliance (`DESIGN.md` — zero raw hex colors outside `tokens.css`, Violet `#6D28D9` reserved for `human-led-anchor-card`) and the 11 fundamental UX/UI rules.
- Full bilingual (`fr` / `en`) compatibility via typed dictionaries in `apps/web/src/i18n/locales/` (zero hardcoded strings or `locale === "fr"` ternaries).
- Full vertical wiring via `@orcia/api-client` (zero ephemeral `useState` business stores, zero `isJsdom` short-circuits) and URL reload (`F5`) cold survival.

### 2.5 Test Pyramid Impact Analysis (`AD-17` — Layers 1 to 5 + Security, Mandatory)
- **Layer 1a (Python Unit `tests/unit/`) & Layer 1b (TS/React Unit/Component `Vitest` without `isJsdom`)**: [Unit test files created or updated]
- **Layer 2 (Vertical Integration `HTTP FastAPI ➔ PostgreSQL 18` `tests/integration/`)**: [HTTP routes tested against PostgreSQL 18 + `SELECT` verification]
- **Layer 3 (OpenAPI 3.1 Contracts `0-diff`, Schemathesis & `lint-imports`)**: [Impacts on HTTP schemas / `@orcia/api-client` SDK]
- **Layer 4 (`$0` Golden Dataset AI Evals `tests/evals/`)**: [Golden datasets `tests/evals/golden/*.jsonl` impacted or added]
- **Security / Red-Team Layer (`tests/security/`)**: [SSRF guard, `403 ERR_OBSERVER_MODE_READ_ONLY`, RBAC/ABAC, `CONFIDENTIAL_RESTRICTED` masking, zero plaintext secrets]
- **Layer 5 (Dual-Server Playwright E2E `apps/web/e2e/*.spec.ts`)**: [Impacted Playwright specs and `data-testid` selectors, bilingual `fr`/`en` verification, and `tests:` update in `docs/product/capabilities.yaml`]

---

## 3. Summary of Changes & Results (Post-Implementation)

### 3.1 Created & Modified Files
| File | Action (Created / Modified / Refactored) | Concise Summary |
| :--- | :--- | :--- |
| `infra/migrations/...` | Created | ... |
| `packages/orcia-core/...` | Created / Modified | ... |
| `apps/api/...` | Created / Modified | ... |
| `apps/web/...` | Created / Modified | ... |

### 3.2 Quantitative Metrics, Coverage & Static Quality
- **Test coverage**: [Obtained unit test coverage (`pytest` / `Vitest`, $\ge 90\%$ required)]
- **Measured performance**: [CTE query times (`< 15 ms`), hybrid RAG (`< 50 ms`), SSE broadcast (`< 500 ms`), UI view switching (`< 1 s`)]
- **Static Quality & Architecture**:
  - `ruff check` & `ruff format --check`: `0` warnings
  - `mypy --strict` & `pnpm typecheck`: `0` errors
  - `lint-imports`: `5 contracts kept, 0 broken`
  - `lint_spine.py`: `ok: true, 0 findings`
  - `gitnexus_detect_changes()`: [Verified and compliant scope]

### 3.3 AD-17 Test Pyramid & Vertical Wiring Verification
- **Layer 1a — Python Unit Tests (`pytest` + `hypothesis`, $\ge 90\%$) & Layer 1b — Frontend TS (`Vitest` without `isJsdom`)**: [Details of verified invariants]
- **Layer 2 — Vertical Integration `HTTP ➔ PostgreSQL 18` (`testcontainers-python`: PostgreSQL 18 + `pgvector`, Redis 7.4, SeaweedFS)**: [FastAPI route call (`AsyncClient`) + database `SELECT` verification, zero orphan SQL adapters]
- **Layer 3 — API Contract (`openapi-typescript` `0-diff`, `Schemathesis`, `lint-imports`, `lint_spine.py`)**: [Schema and RFC 9457 error code validation]
- **Layer 4 — AI Orchestration & Golden Dataset Evals (`DeterministicCassetteLLM`, `tests/evals/`)**: [`$0` deterministic verification of agent flows, citations, and Gates]
- **Security / Red-Team Layer (`tests/security/`)**: [SSRF, `403 ERR_OBSERVER_MODE_READ_ONLY`, RBAC/ABAC, `CONFIDENTIAL_RESTRICTED` masking, zero secret leaks]
- **Layer 5 — Dual-Server Playwright E2E (`pnpm e2e`), `F5` Cold Survival (`unmount()` + `render()`) & Day-0 Ground Truth (`pnpm db:reset`)**: [Desktop/Mobile E2E scenarios verified, post-reload persistence, bilingual FR/EN behavior, and `tests:` / `verification: runtime` update in `docs/product/capabilities.yaml`]
