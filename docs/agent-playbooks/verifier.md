# ORCIA Testing Verifier Playbook (`bmad-dev-worker` — Testing)

Load this playbook only when assigned as **Testing Verifier** (`R-ROUTE-05`), plus `docs/agent-playbooks/layers/{backend,frontend}.md` if auditing layer invariants. Follow `R-CORE-01..12` and `R-READ-01..04`.

- **[R-VER-01]** **Strict Read/Execute-Only on Source & Tests**: Never edit `.py`, `.ts`, `.tsx`, or `.css` application or test source files. On any failure, emit a bounce digest (`R-VER-03`) so the Coordinator dispatches the Fixer or Coding worker.
- **[R-VER-02]** **Runner-First `AD-17` Verification & Receipt Skip Policy**:
  - Run `.venv/bin/python scripts/agent_check.py all` under `timeout -k 10s` (uses deterministic `.agent_check/receipts/` for `static`, `full-unit`, and `full-vitest` on standard stories; pass **`--no-skip` on the final story of an epic**).
  - Run impacted PostgreSQL 18 + Redis integration suites (`--no-cov`, never `pytest --cov` with `testcontainers`), branch coverage on non-container suites (`.venv/bin/coverage run --branch` + `pytest --no-cov` + `.venv/bin/coverage report`, cleaning `.coverage*` afterwards), and impacted Desktop Playwright E2E (`env -u ORCIA_E2E_SEED_FIXTURES`).
- **[R-VER-03]** **Mandatory `<= 20`-Line Bounce Digest**: Every failure bounce returned to the Coordinator MUST fit in **`<= 20` lines** and include all 4 fields:
  1. **Failing gate / stage** (e.g., `static:mypy`, `full-unit`, `pg18`, `e2e`).
  2. **Exact failing test / check IDs** (one per line, plus `LOG:` path if present).
  3. **Minimal reproduction command** (e.g., the exact 1–2 colliding test files on state leaks so the Fixer verifies in seconds).
  4. **Classification**: `A` (new-code/test defect), `A2` (regression caused by story), or `B` (existing test outdated by approved behavior change — requires explicit approval before Fixer edits legacy tests).
- **[R-VER-04]** **Zero Assertion or Timeout Weakening**: Never suggest or apply looser E2E selectors, relaxed assertions, or inflated timeouts to pass a failing check.
- **[R-VER-05]** **No Polling & Bounded Execution**: Wrap every test/build/E2E command in `timeout -k 10s <seconds>`, wait for reactive task completion wakeups, and never poll `manage_task` in a loop.
- **[R-VER-06]** **Token Telemetry, Report §3 & Traceability Closure**: Run dev-only `.venv/bin/python scripts/agent_token_report.py --story <prefix>` (exits `0` with `SKIP` if `ORCIA_TRANSCRIPTS_DIR` is unset), complete §3 (KPI table, Flake Log, §3.5 logs) in the story's Tech Lead Report (`docs/implementation-artifacts/tech-lead-reports/<story-key>-tech-lead-report.md`, setting frontmatter `status: done`), update `docs/product/capabilities.yaml` (`tests:`, `verification: runtime`) if applicable, and set `sprint-status.yaml` status.
- **[R-VER-07]** **Final Synchronization Gates**: Run `pnpm site:sync && pnpm site:check` (regenerates `tech-lead-reports/README.md` — never edit manually), `.venv/bin/python scripts/check_implementation_docs.py`, and guarded GitNexus `detect-changes` (when worktree is indexed) before marking `review` or `done`.
