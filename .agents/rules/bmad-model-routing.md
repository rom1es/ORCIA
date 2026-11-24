---
trigger: always_on
---

# BMAD Model Routing & Token Discipline

Mandatory orchestration and context-isolation directives for every BMAD workflow:

## 1. Zero Read-Ahead by Parent
- The main orchestrating BMAD agent is **prohibited** from directly reading application source code to prepare a task.
- The parent reads only indexes, status files, and stories under `_bmad/` or `docs/` (e.g., `sprint-status.yaml`, `epics.md`, `capabilities.yaml`), and delegates all codebase exploration, symbol search, or log analysis to `bmad-scout` via `invoke_subagent`.

## 2. Automatic Routing Matrix (`invoke_subagent`)
- **Codebase exploration, symbol search, log inspection** $\rightarrow$ `bmad-scout` (`model: flash`).
- **Architecture design, ADR arbitration, complex decomposition, final review / `VALIDATE`** $\rightarrow$ `bmad-architect-worker` (`model: pro`).
- **Validated story development, localized refactoring, test execution/fixing** $\rightarrow$ `bmad-dev-worker` (`model: flash`).

## 3. Controlled Escalation
- If `bmad-dev-worker` fails **2 consecutive times** on the same root cause and stops (Fail-Fast rule), re-invoke targeted resolution at the `pro` tier (`model: pro`) **solely** on the exact failing scope described in the 3-point diagnostic.

## 4. Disk-Based State Handoff
- Intermediate artifacts (plans, specs, stories, diagnostics, review reports) must be written to files on disk and passed **by file path** between agents rather than copied verbatim in the main thread.

## 5. Output Discipline
- Zero conversational filler (no preamble or restating the request).
- Targeted line-range reads only (grep/search before reading; line ranges for files $> 200$ lines).

## Mandatory Sub-Agent Gate Triggers

You MUST call `invoke_subagent` (and are forbidden from acting inline) as soon as ANY of these conditions holds:
1. **Exploration threshold (> 2 files):** You need to inspect more than 2 source files or run a repo-wide grep -> Launch `bmad-scout` (`flash`).
2. **Story -> Code transition:** The user runs `*develop-story`, approves an implementation plan, or asks to code an existing story -> Launch ONE dedicated `bmad-dev-worker` (`flash`) per story (never code multiple stories in the same sub-agent).
3. **Terminal noise threshold:** A test, build, or linter command is likely to emit > 30 lines of output -> Delegate execution and filtering to `bmad-dev-worker` (`flash`).
4. **Architecture Gate Check:** The user requests an ADR arbitration, interface contract validation, or end-of-story review (`*code-review` / `VALIDATE`) -> Launch `bmad-architect-worker` (`pro`), passing only the story path and `git diff`.
5. **Two consecutive failures:** A `flash` worker reports 2 failures on the same error -> Immediately re-launch a targeted `pro` sub-agent on the single failing file.

## 6. Zero-Duplication Test Split & Process Monitoring

Strict role separation across Coding and Testing sub-agents applies to every story and code change:

1. **Coding Sub-Agent Scope (`bmad-dev-worker`):**
   - Authors production code, tests, OpenAPI/SDK regeneration, and pre-edit Report Sections 1-2.
   - Runs **only fast `< 60 s` local sanity checks** on directly touched files: line-count guard (`wc -l <= 300`), `ruff check` / `ruff format --check` on touched paths, targeted `mypy --strict` on modified modules, `lint-imports` (if domain boundaries touched), `scripts/export_openapi.py --check` (only if API schemas/routes changed), and **only** the new/directly edited unit test (`test_story_* --no-cov`) or Vitest file.
   - **Forbidden from duplicating Testing gates:** Coding must NOT run full `tests/unit`, unrelated legacy PG18 integration batches, full `pnpm turbo`, or Playwright E2E suites.
2. **Testing Sub-Agent Scope (`bmad-dev-worker`):**
   - Strictly read/execute-only on all application source and test files (never edits `.py`/`.ts`/`.tsx`; fails fast and bounces back to Coding on failure).
   - **Sole runner** of full `AD-17` verification after final code edits: repo-wide `ruff`, `format`, `mypy --strict`, `lint-imports`, `lint_spine.py`, `detect-secrets-hook`, full `tests/unit` + `tests/evals` + `tests/security` + `tests/contract`, `>= 90%` branch coverage (`coverage run --branch` + `--no-cov` — never `pytest --cov` with `testcontainers`), impacted PG18+Redis integration suites (`--no-cov`), `pnpm turbo run lint typecheck test`, impacted Playwright Desktop E2E (`env -u ORCIA_E2E_SEED_FIXTURES`), plus Report §3, `sprint-status.yaml`, `pnpm site:sync && pnpm site:check`, `scripts/check_implementation_docs.py`, and `npx gitnexus analyze --index-only .`.
3. **Mandatory Bounded Monitoring (Coordinator & Sub-Agents):**
   - Every test, build, or long-running script started by a sub-agent MUST run under a bounded OS timeout (`timeout -k 10s <seconds>`) and be actively monitored (using `manage_task` / reactive task notifications, never unbounded runs or polling `sleep` loops) so no script hangs indefinitely.
   - The Coordinator monitors every background task and active sub-agent using bounded `schedule` timers (`TimerCondition`) until clean completion or fail-fast handback.

## 7. Language Discipline
- All agent-to-user chat, sub-agent briefs, Tech Lead reports, planning docs, commit messages, and code comments/docstrings MUST be written in **English** (historical reports remain immutable).
- The ORCIA web application UI (`apps/web` + `@orcia/ui`) and user-facing API responses (`Accept-Language` RFC 9457 error catalogs, Assistant prompt locale bundles) MUST remain **100% bilingual compatible in French (`fr`) and English (`en`)**.
