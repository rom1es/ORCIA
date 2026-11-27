# ORCIA Coding Agent Playbook (`bmad-dev-worker` — Coding)

Load this playbook only when assigned as **Coding Worker** (`R-ROUTE-05`), plus `docs/agent-playbooks/layers/{backend,frontend}.md` for the layers you touch. Follow `R-CORE-01..12` and `R-READ-01..04`.

- **[R-CODE-01]** **Story Intent Header (`< 500` tokens)**: At story start, write `.agent_check/story_intent.md` (`< 500` tokens) summarizing: (1) story goal, (2) Acceptance Criteria, (3) domain/security/bilingual invariants, and (4) explicit non-goals. Reserved strictly for downstream `bmad-fixer-worker` bounce calls.
- **[R-CODE-02]** **Pre-Edit Governance & GitNexus Impact**: Grep `docs/product/capabilities.yaml` and `epics.md` for overlaps (never full-read); run GitNexus `impact` / `context` scoped to the active worktree path (confirm `UNKNOWN` with `grep`); keep every new/edited source and test file `<= 300` lines; ensure the Tech Lead Report (`docs/implementation-artifacts/tech-lead-reports/<story-key>-tech-lead-report.md`, sole committed story artifact) has §1–§2 frozen before editing code, and mark `in-progress` in `sprint-status.yaml` (never read/edit `tech-lead-reports/README.md`).
- **[R-CODE-03]** **Five Vertical Wiring Guardrails**:
  1. Zero orphan SQL adapters (`_internal/sql_*.py`, `adapters/postgres_*.py` must have active callers in `apps/api` or `apps/worker`).
  2. Integration tests (`tests/integration/`) boot real `create_app()` on PostgreSQL 18 without `dependency_overrides` or manual `app.state.*` injection and verify persistence via SQL `SELECT`.
  3. Zero ephemeral `useState` business stores in `apps/web`: persist via `@orcia/api-client`, rehydrate via `GET`, and verify `F5` cold survival (`unmount()` + `render()` / `reloadColdFromPg`).
  4. Verify Day-0 flows after `pnpm db:reset` without `ORCIA_E2E_SEED_FIXTURES`.
  5. Zero dead buttons, zero forgotten optional callbacks, synchronized `data-testid` attributes, and zero `.catch(() => undefined)` on user actions.
- **[R-CODE-04]** **Four FastAPI / SSE / Security Invariants**:
  1. Zero sync HTTP/DB clients (`httpx.Client`, `requests`, `ThreadPoolExecutor`, `create_async_engine()`) in routers (`TID251`).
  2. Real `AsyncIterator` SSE streaming (`resp.aiter_lines()`), never `.split(" ")`.
  3. Zero hardcoded LLM vendor (`ollama`/`openai`), hat, or locale (`fr`) strings outside `PROMPT_LOCALES`.
  4. Zero silent `except Exception:` without `get_logger(...)` logging; validate DB-configured URLs with `is_safe_llm_endpoint_url`.
- **[R-CODE-05]** **UX/UI & Bilingual Discipline**: Keep Direction C tokens (`tokens.css`) and primitives inside `@orcia/ui` (`#6D28D9` reserved for `HumanLedAnchorCard`), obey the 11 UX/UI rules and 3 microcopy/`ⓘ` rules (zero internal plumbing jargon, `< 2 s` labels, `ContextualInfoTriggerButton`), and maintain 100% `fr`/`en` dictionary parity in `apps/web/src/i18n/locales/`.
- **[R-CODE-06]** **Runner-Only `< 60 s` Local Checks**: Run `.venv/bin/python scripts/agent_check.py static` and `.venv/bin/python scripts/agent_check.py impact --explain --maxfail 3` under `timeout -k 10s`. Do **not** run full `tests/unit`, unrelated legacy PG18 suites, full `pnpm turbo`, Playwright E2E, or chained shell one-liners.
- **[R-CODE-07]** **Fail-Fast Escalation**: On 2 consecutive failures on the same root cause, stop editing and return a 3-point diagnostic to the Coordinator (`R-ROUTE-03`). Never `git commit` or `git push`.
