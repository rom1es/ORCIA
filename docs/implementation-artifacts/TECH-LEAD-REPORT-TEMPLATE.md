---
date: YYYY-MM-DD
story: "{story-key}"
domain: "[Domain / Modules] (feature|hygiene|ux|doc)"
summary: "[One-line summary <= 200 chars for the auto-generated README index]"
status: draft # draft | ready-for-dev | in-progress | in-review | done
route: dispatch # oneshot | dispatch
baseline_commit: ""
review_loop_iteration: 0
---

# [Story N.M or YYYY-MM-DD — Implementation / Adjustment / Feature Name]

> **Mandatory File Naming Convention (Must be created BEFORE any code modification)**:
> - Ad-hoc adjustment, bugfix, or evolution outside a Story: `docs/implementation-artifacts/tech-lead-reports/{YYYY-MM-DD}-{short-slug}-tech-lead-report.md`
> - Sprint User Story: `docs/implementation-artifacts/tech-lead-reports/{story-key}-tech-lead-report.md`
> - **Language Policy**: Author all new Tech Lead reports in **English** (historical reports remain immutable).
> - **Index**: Never read or edit `tech-lead-reports/README.md` manually; `pnpm site:sync` regenerates it.

| BMAD Build Section | Target TLR Section |
| :--- | :--- |
| Frontmatter `status` / `route` / `baseline_commit` / `review_loop_iteration` | YAML Frontmatter above |
| `<frozen-after-approval>` block | `<!-- frozen-after-approval:start -->` .. `<!-- frozen-after-approval:end -->` wrapping `## 1` |
| `## Intent` / `## Boundaries & Constraints` | `### 1.1` & `### 1.2` |
| `## I/O & Edge-Case Matrix` / Acceptance Criteria | `### 1.3` & `### 1.4` |
| `## Code Map` & `## Tasks & Acceptance` | `## 2. Implementation Plan` (`- [ ]` checkboxes) |
| `## Spec Change Log` & `## Review Triage Log` | `### 3.5` |

- **Date**: YYYY-MM-DD
- **Story / Sprint Key**: `{story-key}` or `{YYYY-MM-DD}-{short-slug}` (`Epic N` / `Cross-Cutting Adjustment`)
- **Capability(ies)**: `CAP-xxx` (existing to update / new to create in `docs/product/capabilities.yaml`) or `none (hygiene/NFR/UX)` — classification: `feature | hygiene | ux | doc` (see `AGENTS.md`)
- **Author / Context**: [Business context, primary goal, problem solved, `FR-*`, `NFR-*`, `AD-*`, `UX-DR*` requirements covered]
- **Associated Commits**: `hash1`, `hash2`

---

<!-- frozen-after-approval:start -->
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
- **Refactoring Opportunities & Emerging Technical Debt Mitigation**:
  - [Shared primitives extracted or reused (`packages/orcia-core`, `packages/api-client`, `@orcia/ui` components)]
  - [File line-count control (`<= 300–400` lines) and modular splits performed]
  - [Technical debt / refactoring tickets created (`action_items` entries in `sprint-status.yaml`)]

### 1.3 Acceptance Criteria *(optional for trivial changes)*
| # | Given / When / Then Criterion |
| :--- | :--- |
| AC1 | [Measurable criterion] |

### 1.4 I/O & Edge Cases *(optional for trivial changes)*
| Input / Condition | Expected Output / Guard |
| :--- | :--- |
| [Edge case] | [Expected behavior / error code] |
<!-- frozen-after-approval:end -->

---

## 2. Implementation Plan

### 2.1 Data Schema & Alembic Migrations (`infra/migrations/versions/...`, if applicable)
- [ ] `infra/migrations/versions/XXXX_migration_name.py`: tables, `UUIDv7` PKs, triggers, indexes, reversibility (`upgrade`/`downgrade`).

### 2.2 Hexagonal Core, Orchestration & Workers (`packages/orcia-core/`, `apps/worker/`, `infra/sandbox/`)
- [ ] `packages/orcia-core/<domain>/...`: domain invariants (zero framework imports), McCabe <= 10, `AD-1..AD-25` isolation rules.
- [ ] `apps/worker/...`: Dramatiq actors, retry idempotency, error handling.

### 2.3 Backend API, Security & Contracts (`apps/api/`, `packages/api-client/`)
- [ ] `apps/api/repositories/...` & `services/...`: recursive CTEs / zero `N+1`, multi-level scope filters, `UnitOfWork`.
- [ ] `apps/api/routers/...` & `dependencies/...`: endpoints, RBAC/ABAC (`RunAccessGuard`, `403 READ_ONLY_OBSERVER`), RFC 9457 bilingual errors, OpenTelemetry `trace_id`.
- [ ] `packages/api-client/`: regenerate SDK via `openapi-typescript` (`0-diff`).

### 2.4 User Interface & Experience (`apps/web/`, `packages/ui/`)
- [ ] TanStack Router routes & React 19 / `@orcia/ui` components, Direction C tokens, bilingual `fr`/`en` dictionaries, vertical wiring via `@orcia/api-client` (`F5` survival).

### 2.5 Test Pyramid Impact Analysis (`AD-17` — Layers 1 to 5 + Security, Mandatory)
- [ ] **Layer 1a & 1b**: `tests/unit/` (`pytest` >= 90%) & `Vitest` (no `isJsdom` short-circuits).
- [ ] **Layer 2**: `tests/integration/` (`HTTP FastAPI -> PostgreSQL 18` + `SELECT` verification).
- [ ] **Layer 3**: OpenAPI 3.1 `0-diff`, Schemathesis, `lint-imports`.
- [ ] **Layer 4 & Security**: `$0` Golden Dataset evals (`tests/evals/`) & `tests/security/` (SSRF, RBAC, Observer `403`, secrets).
- [ ] **Layer 5**: Dual-server Playwright E2E (`apps/web/e2e/*.spec.ts`) & `capabilities.yaml` `tests:` update.

---

## 3. Summary of Changes & Results (Post-Implementation)

### 3.1 Created & Modified Files
| File | Action (Created / Modified / Refactored) | Concise Summary |
| :--- | :--- | :--- |
| `...` | Created / Modified | ... |

### 3.2 Quantitative Metrics, Coverage & Static Quality
- **Test coverage**: [Unit test coverage (`pytest` / `Vitest`, >= 90% required)]
- **Static Quality & Architecture**:
  - `ruff check` & `ruff format --check`: `0` warnings
  - `mypy --strict` & `pnpm typecheck`: `0` errors
  - `lint-imports`: `5 contracts kept, 0 broken`
  - `lint_spine.py`: `ok: true, 0 findings`

### 3.3 AD-17 Test Pyramid & Vertical Wiring Verification
- **Layer 1a / 1b / 2 / 3 / 4 / Security / 5**: [Exact commands run and observed pass counts]

### 3.4 Token, Duration KPIs & Flake Log (`T-D9` / Epic 32 Instrumentation)
- **Token & Duration KPIs** *(via `.venv/bin/python scripts/agent_token_report.py --story <prefix>` + `scripts/agent_check.py` timings)*:

| KPI | Epic 30–31 Baseline | Target | Measured (This Story) |
| :--- | :--- | :--- | :--- |
| Billed input tokens / story | median 66.6 M | <= 40 M (-40%) | — |
| Test-related tokens / story | median 27.4 M | <= 14 M (-50%) | — |
| Always-on rules bytes / truncation | `36,416 B` (`12,464 B` trunc.) | `AGENTS.md` <= 3.5 KB, 0 truncated | — |

- **Flake Log**:

| Date | Test / Check ID | Stage | Symptom | Root Cause / Resolution | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| — | *(none observed)* | — | — | — | — |

### 3.5 Spec Change Log & Review Triage *(optional)*
- **Spec changes**: [Approved amendments to frozen §1]
- **Review findings**: [Triaged blocker/major/minor dispositions]
