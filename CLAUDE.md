# Tech Lead / Senior Dev Protocol & Permanent Implementation Report (Mandatory)

For **every User Story (`Story N.M`)** AND **every ad-hoc request requiring adjustments, bugfixes, or evolutions to ORCIA**, the agent MUST strictly:

1. **Enforce the Language & Bilingual Application Policy**:
   - **English-Only Development & Documentation**: Conduct all chat conversations, planning docs, Tech Lead reports, commit messages, and code comments/docstrings in **English** (historical reports remain immutable).
   - **100% Bilingual FR/EN Web App & API**: Keep `apps/web`, `@orcia/ui`, RFC 9457 `problem+json` error catalogs (`Accept-Language`), and Assistant prompt locale bundles 100% bilingual (`fr` and `en`), with zero hardcoded UI strings or inline `locale === "fr" ? ... : ...` ternaries.
2. **Author a Tech Lead Report BEFORE modifying any code** in `docs/implementation-artifacts/tech-lead-reports/` using the official template [`docs/implementation-artifacts/TECH-LEAD-REPORT-TEMPLATE.md`](file:///home/romain/Documents/Projects/ORCIA/docs/implementation-artifacts/TECH-LEAD-REPORT-TEMPLATE.md):
   - **File Naming**: prefix the filename with today's date in `YYYY-MM-DD` followed by a short `kebab-case` summary:
     `docs/implementation-artifacts/tech-lead-reports/{YYYY-MM-DD}-{short-slug}-tech-lead-report.md` (or `{story-key}-tech-lead-report.md` for a sprint Story).
   - **Mandatory Pre-Implementation Authoring**: complete **Section 1 (`Needs Analysis & Tech Lead Impact Study`)** and **Section 2 (`Implementation Plan`)** **before** editing any code file, then complete **Section 3 (`Summary of Changes & Results`)** after passing all verification gates, register the report in `docs/implementation-artifacts/tech-lead-reports/README.md`, and run **`pnpm site:sync`** (`.venv/bin/python infra/scripts/sync_site_catalog.py`) to update `/showcase` and the standalone export `docs/site-catalog/index.html`.
3. **Respect the Vertical Wiring Guardrails (Zero UI / API / SQL Silos)**:
   - **Zero Orphan SQL Adapters**: every SQL function (`_internal/sql_*.py`, `adapters/postgres_*.py`) must have an active caller in `apps/api` or `apps/worker` (verified via `gitnexus_impact({direction: "upstream", repo: "ORCIA"})` $\rightarrow$ `impactedCount >= 1` outside `tests/`).
   - **Vertical Integration Test `HTTP ➔ PostgreSQL 18`**: `testcontainers` integration tests must call the real FastAPI route (`create_app()`, zero `dependency_overrides` or manual `app.state.*` injection) and verify actual database persistence via SQL `SELECT`.
   - **Zero Ephemeral Business `useState` Stores & F5 Survival Test (`apps/web`)**: any user-mutated business state in `apps/web` must persist via `@orcia/api-client`, rehydrate on startup via `GET`, and be tested across full unmount/remount (`unmount()` then `render()`).
   - **Day-0 Reset (`pnpm db:reset`)**: run `.venv/bin/python infra/scripts/maintenance/09_reset_db_first_boot.py --apply` (`pnpm db:reset`) to reset to initial boot state (`0` rows in `users`).
   - Consult [`GEMINI.md`](file:///home/romain/Documents/Projects/ORCIA/GEMINI.md) / [`AGENTS.md`](file:///home/romain/Documents/Projects/ORCIA/AGENTS.md) for all architecture decisions (`AD-1` to `AD-25`) and the 11 fundamental UX/UI rules.
4. **Strictly Enforce the 3 User-Centric Microcopy & Contextual Help (`ⓘ`) Rules**:
   - **Zero internal ORCIA plumbing or jargon in the UI**: always adopt the end user's business vocabulary; no internal implementation terms (`DBOS`, `PostgreSQL 18`, `pgvector`, `halfvec`, `Outbox`, `Wasmtime`, `Starlark`, `Argon2id`, `OIDC PKCE`, `Passthrough`, `Service Principal`, `Tie-Break`, `Rubber-stamping`, `What-If`, `Verrou V1..V5`, `AD-*`, `RFC 9457`, raw status codes) may appear in `apps/web/src/i18n/locales/*.ts` or UI components.
   - **Self-explanatory labels (< 2 seconds)**: every title, button, tab, or field must be immediately understandable without abstract jargon.
   - **Zero explanatory prose walls in the workspace — Systematic `ⓘ` (`ContextualInfoTriggerButton`) links**: replace long explanatory paragraphs in the central workspace with a discrete `ⓘ` button (`<ContextualInfoTriggerButton sectionId="..." />` from `@orcia/ui`) that automatically opens the right contextual help column and highlights the targeted help section (`data-testid="help-section-${sectionId}"`).

---

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

## Capabilities Registry & Full Test Pyramid Review (Mandatory)
- Full test strategy and 10 anti-test-debt locks: [`docs/testing-strategy.md`](file:///home/romain/Documents/Projects/ORCIA/docs/testing-strategy.md).
- Consult and update `docs/product/capabilities.yaml` for every evolution (see `AGENTS.md` §5); record `Capacité(s)` and `tests:` in the Tech Lead report and registry; `pnpm site:check` must pass (no `live` capability without a referenced test).
- For every Story or ad-hoc request, systematically verify impact across **all layers of the `AD-17` test pyramid down to End-to-End tests** (see `AGENTS.md` §6):
  1. **Layer 1a — Python Unit Tests** (`.venv/bin/pytest tests/unit --cov=packages/orcia-kernel --cov=packages/orcia-core --cov-fail-under=90`)
  2. **Layer 1b — TS/React Unit & Component Tests without `isJsdom` short-circuits** (`pnpm turbo run lint typecheck test`, simulated HTTP/SSE transport in `vitest.setup.ts`)
  3. **Layer 2 — Vertical Integration `HTTP ➔ PostgreSQL 18`** (`.venv/bin/pytest tests/integration` with `AsyncClient` + PG18 `SELECT`)
  4. **Layer 3 — OpenAPI 3.1 Contract (`0-diff`) & Hexagonal Boundaries** (`.venv/bin/pytest tests/contract tests/conformance` + `.venv/bin/lint-imports`)
  5. **Layer 4 — AI Orchestration & `$0` Golden Dataset Evals** (`.venv/bin/pytest tests/evals`)
  6. **Security / Red-Team Layer** (`.venv/bin/pytest tests/security`: SSRF, `403 ERR_OBSERVER_MODE_READ_ONLY`, RBAC/ABAC, `CONFIDENTIAL_RESTRICTED` masking, zero plaintext secrets)
  7. **Layer 5 — Dual-Server Playwright Browser E2E** (`pnpm e2e` across `apps/web/e2e/*.spec.ts`: update any E2E spec impacted by a route, `data-testid`, or API flow change, verifying bilingual `fr`/`en` UI compatibility)
