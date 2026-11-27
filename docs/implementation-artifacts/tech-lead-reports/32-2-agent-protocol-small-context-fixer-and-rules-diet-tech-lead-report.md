# Story 32.2 — Agent Protocol, Small-Context Fixer, Rules Diet & Read Discipline

- **Date**: 2026-11-27
- **Story / Sprint Key**: `32-2-agent-protocol-small-context-fixer-and-rules-diet` (`Epic 32` / Lot 2)
- **Capability(ies)**: `none (hygiene/NFR)` — classification: `hygiene`
- **Author / Context**: `T-D7`, `T-D8`, `T-D9` from `docs/planning-artifacts/sprint-change-proposal-2026-11-27-epic-32-test-pyramid-token-economy.md` and token-economy evidence in `docs/implementation-artifacts/test-optimization-2026-11-27/04-token-economy-challenge-review.md` (`T1`–`T4`, `T7`, `T9`, `O7`, `O8`, `O10`)
- **Associated Commits**: *(pending completion)*

---

## 1. Needs Analysis & Tech Lead Impact Study (Pre-Implementation)

### 1.1 Context & Problem Statement
- **Problem**: Across Epics 30–31 (13 stories), coding agents re-sent ~250 k context tokens per turn (median 66.6 M input tokens/story), `read_file` accounted for 64–65% of context bytes (38% duplicate reads, 6% generated SDK/`openapi.json` reads), and 119 turns in Epic 30 were `manage_task` polling. Meanwhile, `AGENTS.md` (36,416 B) and its symlink `GEMINI.md -> AGENTS.md` (36,416 B) exceeded Antigravity's 24,000 B per-file rule cap (`12,464 B` truncated on every conversation), while `.agents/rules/bmad-model-routing.md` added 5,998 B.
- **Expected behavior**:
  1. Canonical `AGENTS.md` core trimmed to `<= 12,288 B` (`<= 12 KB`), with refreshed `<!-- bmad:context -->` block (`~6–7 KB`) and stable unique Rule IDs (`[R-CORE-01]`..`[R-CORE-12]`, `[R-READ-01]`..`[R-READ-04]`).
  2. Role-specific rules extracted into on-demand playbooks under `docs/agent-playbooks/{coder,fixer,verifier,architect}.md` (`<= 8 KB` each), referenced by `.agents/agents/*.md` and a lean `.agents/rules/bmad-model-routing.md` (`<= 4 KB`).
  3. `GEMINI.md` duplicate resolution verified against Antigravity's `agy-customizations/docs/rules.md`.
  4. New Stage 1 hygiene gates (`scripts/check_agent_rules.py` and `scripts/generate_test_fixture_index.py --check`) wired into `scripts/agent_check_lib/static_gates.py`, with `scripts/agent_check_lib/receipts.py` hashing all `scripts/*.py` files.
  5. Small-context fixer protocol (`fixer.md` + `.agent_check/story_intent.md` `< 500` tokens), `<= 20`-line verifier bounce digests with minimal reproducer, read discipline, updated `TECH-LEAD-REPORT-TEMPLATE.md` §3 (KPIs & Flake Log), and dev-only `scripts/agent_token_report.py` (`ORCIA_TRANSCRIPTS_DIR` env var, graceful no-op when unset).

### 1.2 Exploration, GitNexus Impact Analysis, Refactoring & Technical Debt
- **GitNexus Impact Analysis (`repo: /home/romain/.gemini/antigravity/worktrees/ORCIA/epic30_test_duration_optimization` + grep verification)**:
  - `build_static_gates` (`scripts/agent_check_lib/static_gates.py:74`): single production caller `scripts/agent_check_lib/stages.py:58` and test caller `tests/unit/tooling/test_agent_check_runner_exec_and_gates.py:205`. Adding guarded `rules-lint` and `fixture-index` gates (checking `.is_file()`, matching `export_openapi.py` and `lint_spine.py`) preserves temp-repo unit test isolation.
  - `compute_worktree_digest` / `_runner_source_digest` (`scripts/agent_check_lib/receipts.py:68,91`): callers `scripts/agent_check_lib/stages.py:40,53,131` and `tests/unit/tooling/test_agent_check_receipts_and_bounce.py`. Expanding `_runner_source_digest` to hash all sorted `scripts/*.py` + `scripts/agent_check_lib/*.py` ensures any edit to `check_agent_rules.py` or `generate_test_fixture_index.py` invalidates stale receipts.
- **`GEMINI.md` Verification against `agy-customizations/docs/rules.md`**:
  - `rules.md` states: Antigravity automatically discovers both `AGENTS.md` and `GEMINI.md` at repository root, deduplicates identical rule contents (`GEMINI.md -> AGENTS.md` symlink currently deduplicates to one copy, which was truncated by 12,464 B at the 24,000 B cap), and enforces a shared 20,000-token `defaultRulesBudget` where `@[label](path)` includes expand inline before counting.
  - Repo-wide grep across `tests/`, `scripts/`, `infra/scripts/`, and `.agent/` confirms **zero** tests or scripts require `GEMINI.md` to exist (only 3 test docstrings and 3 maintenance headers mention `GEMINI.md` in prose, while `bmad-project-context` explicitly targets `AGENTS.md`).
  - **Decision**: Remove `GEMINI.md` cleanly so Antigravity discovers only the canonical `AGENTS.md` (`<= 12,288 B`), eliminating symlink divergence risk, non-deduplicated pointer overhead, and `@[...]` double-counting against the 20k budget (**0** duplicate tokens).
- **Refactoring Opportunities & File-Size Control**:
  - Keep every new script (`check_agent_rules.py`, `generate_test_fixture_index.py`, `agent_token_report.py`) and every new `tests/unit/tooling/test_*.py` module strictly `<= 300` lines.
  - Ensure Rule IDs `[R-<GROUP>-<NN>]` are globally unique by using bracketed IDs solely at rule definition sites and unbracketed `R-<GROUP>-<NN>` for cross-references.

---

## 2. Implementation Plan

### 2.1 Data Schema & Alembic Migrations
- None (`hygiene` story; no database tables or migrations touched).

### 2.2 Hexagonal Core, Tooling Scripts & Agent Playbooks (`scripts/`, `docs/`, `.agents/`)
- `AGENTS.md` (`<= 12,288 B`): refresh `<!-- bmad:context -->` against `1b5557c`, assign `[R-CORE-01]`..`[R-CORE-12]` and `[R-READ-01]`..`[R-READ-04]`, preserve every mandatory "never" invariant, and point to `docs/agent-playbooks/*.md`. Remove `GEMINI.md`.
- `.agents/rules/bmad-model-routing.md` (`<= 4,096 B`): keep `trigger: always_on`, `[R-ROUTE-01]`..`[R-ROUTE-06]`, routing matrix, 2-failure `pro` escalation, zero polling, runner-only rule, and on-demand playbook links.
- `docs/agent-playbooks/{coder,fixer,verifier,architect}.md` (`<= 8,192 B` each):
  - `coder.md` (`[R-CODE-01..07]`): `.agent_check/story_intent.md` (`< 500` tokens), pre-edit Report §1–2 + `CAP-xxx`, 5 vertical wiring guardrails, 4 anti-regression invariants, read discipline, `< 60 s` local checks via `agent_check.py`.
  - `fixer.md` (`[R-FIX-01..07]`): sequential dispatch on verifier bounces, inputs (`story_intent.md` + `<= 20`-line digest with minimal reproducer + target line ranges), 1 attempt per failure, `<= 3` calls/story, strict priority of 2-failure `pro` escalation, zero schema/OpenAPI/migration or unapproved legacy-test edits, structured diagnosis + partial patch on failure.
  - `verifier.md` (`[R-VER-01..07]`): read/execute-only, full `AD-17` via `agent_check.py` (receipt skip vs `--no-skip` on final story), `<= 20`-line bounce digest (failing stage, test IDs, minimal reproducer command, `A`/`A2`/`B` classification), never loosen assertions/timeouts, Report §3 KPIs/Flake Log + `agent_token_report.py` + `site:sync`/`site:check`.
  - `architect.md` (`[R-ARCH-01..05]`): `pro` tier, docs/ADR/review only, `T-D3` review timing, `validate` checklist.
- `.agents/agents/bmad-{dev,architect,scout,fixer}-worker.md`: wire on-demand playbook references (`bmad-fixer-worker.md` added for sequential bounce fixing).
- `scripts/check_agent_rules.py` (`<= 300` L): expand `@[label](path)` includes recursively (with cycle detection), assert every always-on rule file `< 24,000 B` (`<= 20,480 B` margin), `AGENTS.md <= 12,288 B`, global Rule ID uniqueness across always-on rules + `docs/agent-playbooks/*.md`, and zero `<truncated` markers.
- `scripts/generate_test_fixture_index.py` (`<= 300` L): scan `tests/**/conftest.py`, `tests/unit/fakes/`, `tests/integration/_*fixture*.py`, `tests/integration/_tc_socket_helpers.py`, `apps/web/src/__tests__/setup/` to generate deterministic `tests/README.md` (`--check` fails on drift).
- `scripts/agent_check_lib/static_gates.py` & `receipts.py`: wire `rules-lint` and `fixture-index` into `build_static_gates`, and hash all `scripts/*.py` in `_runner_source_digest`.
- `docs/implementation-artifacts/TECH-LEAD-REPORT-TEMPLATE.md`: add §3.4 Token & Duration KPIs (10-row Epic 30–31 baseline) and Flake Log table.
- `scripts/agent_token_report.py` (`<= 300` L, dev-only): read `ORCIA_TRANSCRIPTS_DIR` (or `--transcripts-dir`), exit `0` (`SKIP: ORCIA_TRANSCRIPTS_DIR not set`) when unset, filter by `--story` / `--conv`, emit markdown or JSON with turns, fresh vs cached input tokens, output tokens, activity breakdown (`read_src`, `write_src`, `run_test_or_check`, `read_test`, `write_test`, `poll_task`, etc.), duplicate `read_file` rate, and `generated/` full-read count.

### 2.3 Backend API, Security & Contracts
- None (`0-diff` OpenAPI preserved).

### 2.4 User Interface & Experience (`apps/web/`, `packages/ui/`)
- None (`hygiene` story; no runtime UI or `apps/web` changes).

### 2.5 Test Pyramid Impact Analysis (`AD-17` — Layers 1 to 5 + Security, Mandatory)
- **Layer 1a (`tests/unit/tooling/`)**:
  - `test_agent_rules_and_fixture_index.py` (`<= 300` L): `@[...]` expansion, cycle detection, `24,000 B` / `20,480 B` / `12,288 B` size gates, duplicate Rule ID rejection, `tests/README.md` generation & `--check` drift failure, and `static_gates.py` + `receipts.py` integration.
  - `test_agent_token_report.py` (`<= 300` L): unset env var graceful `SKIP` exit `0`, synthetic Epic 31 / Story 32.1 JSONL parsing, fresh vs cached token split, activity breakdown, duplicate `read_file` rate, `generated/` full-read count, and markdown/JSON formatting.
  - Existing `tests/unit/tooling/test_agent_check_*.py` re-run via `agent_check.py impact`.
- **Layer 1b / 2 / 3 / 4 / Security / 5**: no runtime app, DB, API, AI prompt, or E2E behavior altered; verified by `agent_check.py static` and `agent_check.py impact` locally (`full` deferred to Testing Verifier per role split).

---

## 3. Summary of Changes & Results (Post-Implementation)

### 3.1 Created & Modified Files
| File | Action | Concise Summary |
| :--- | :--- | :--- |
| `AGENTS.md`, `GEMINI.md` | Modified / Removed | Trimmed canonical `AGENTS.md` (`6,781 B <= 12,288 B`) with refreshed `bmad:context` (`1b5557c`), `[R-CORE-01..12]`, `[R-READ-01..04]`; removed `GEMINI.md` symlink (`0` duplicate tokens). |
| `.agents/rules/bmad-model-routing.md` | Modified (`1,688 B`) | Lean `always_on` routing (`[R-ROUTE-01..06]`), `2`-failure `pro` escalation priority, and playbook pointers (total always-on: `8,469 B`, `0` truncated). |
| `docs/agent-playbooks/{coder,fixer,verifier,architect}.md` | Created (`3,245` / `2,481` / `2,842` / `1,540 B`) | Role-scoped playbooks (`[R-CODE-01..07]`, `[R-FIX-01..07]`, `[R-VER-01..07]`, `[R-ARCH-01..05]`). |
| `.agents/agents/bmad-{dev,architect,scout,fixer}-worker.md` | Modified / Created | Wired on-demand playbook links and added `bmad-fixer-worker.md`. |
| `scripts/check_agent_rules.py` | Created (`165` L) | Stage 1 gate checking `@[...]` expansion, `< 24,000 B` (`<= 20,480 B` margin), `AGENTS.md <= 12,288 B`, global Rule ID uniqueness, and zero `<truncated`. |
| `scripts/generate_test_fixture_index.py`, `tests/README.md` | Created (`226` L, `7,860 B`) | Deterministic shared fixture/fake/Vitest-setup indexer with `--check` mode. |
| `scripts/agent_check_lib/{static_gates,receipts}.py` | Modified (`159`, `232` L) | Wired `rules-lint` and `fixture-index` into Stage 1; hashed all `scripts/*.py` in `_runner_source_digest`. |
| `scripts/agent_token_report.py` | Created (`299` L) | Dev-only token & read-discipline report (`ORCIA_TRANSCRIPTS_DIR`, graceful `SKIP` exit `0` when unset, never wired in CI). |
| `tests/unit/tooling/test_agent_{rules_and_fixture_index,token_report}.py` | Created (`198`, `241` L) | Unit tests for rule budgets, include expansion/cycles, Rule ID uniqueness, `tests/README.md --check`, `static_gates` + `receipts`, and JSONL token telemetry. |
| `docs/implementation-artifacts/TECH-LEAD-REPORT-TEMPLATE.md` | Modified | Added §3.4 Token, Duration KPIs (10-row Epic 30–31 baseline) & Flake Log table. |

### 3.2 Quantitative Metrics, Coverage & Static Quality
- **Line-count & rule-size sanity**: all new/modified `.py` files `<= 300` L (`scripts/agent_token_report.py` `105` L + `scripts/agent_check_lib/token_parser.py` `244` L); `AGENTS.md = 6,781 B <= 12,288 B`; `.agents/rules/bmad-model-routing.md = 1,688 B < 24,000 B`; `GEMINI.md` removed with zero broken references.
- **Stage 1 (`agent_check.py static --no-skip`)**: `PASS [static]: 15 gates` (`rules-lint` and `fixture-index` active); immediate rerun `agent_check.py static` -> `SKIP [static]: receipt ...`.
- **Tooling branch coverage** (`.venv/bin/coverage run --branch --source=scripts.agent_check_lib,scripts.check_agent_rules,scripts.generate_test_fixture_index,scripts.agent_token_report -m pytest --no-cov -q tests/unit/tooling/`): **`28 passed`**, **`>= 92%`** total (`agent_token_report.py`, `token_parser.py`, `check_agent_rules.py`, `generate_test_fixture_index.py`, `receipts.py`, `static_gates.py`).
- **Story 32.1 Token Telemetry Smoke Test** (`ORCIA_TRANSCRIPTS_DIR=<transcripts_root> .venv/bin/python scripts/agent_token_report.py --conv 872c28d2 --conv 1836c694 --format markdown`, aligned 1:1 with Epic 30–31 `PLANNER_RESPONSE` `input_tokens + cache_read_tokens` formula):
  - Conversations: `2`, Turns: `164`, Billed Input: `33,859,829` (fresh `1,622,060`, cached `32,237,769`, avg/turn `206,462`), Output: `188,115`, Duplicate `read_file`: `12.7%` (`9/71`), `generated/`: `0`.
  - Test-related turns/tokens (`run_test_or_check` + `poll_task` + `read_test` + `write_test`): `81` turns, `19,362,698` billed input tokens.
  - Unset `ORCIA_TRANSCRIPTS_DIR`: `SKIP: ORCIA_TRANSCRIPTS_DIR not set` (exit `0`).
- **Story 32.2 Token Telemetry** (`--conv 663220b9 --conv 95bf053c`):
  - Conversations: `2`, Turns: `113`, Billed Input: `20,607,919` (fresh `971,760`, cached `19,636,159`, avg/turn `182,371`), Output: `97,968`, Duplicate `read_file`: `18.5%` (`12/65`), `generated/`: `0`, `poll_task`: `0` turns.
  - Test-related turns/tokens: `40` turns, `7,606,324` billed input tokens.

### 3.3 AD-17 Full Verification & Closure Gates
- **Stage 3 Full Runner (`agent_check.py full --no-skip`)**:
  - `PASS [full-unit]: 1 target(s) in 321.47s`
  - `PASS [full]: 3 target(s) in 98.86s`
  - `PASS [full-vitest]: 3 pkg(s) in 73.18s`
  - `PASS [full-docs-site]: 2 checks in 2.25s`
- **Implementation Docs & Site Sync**: `pnpm site:sync`, `pnpm site:check`, `.venv/bin/python scripts/check_implementation_docs.py`, and `gitnexus analyze --index-only .` executed at closure with `0` `.coverage*` residue.

### 3.4 Token, Duration KPIs & Flake Log (`T-D9` / Epic 32 Instrumentation)

- **Token & Duration KPIs**:

| KPI | Epic 30–31 Baseline | Target | Measured (This Story) |
| :--- | :--- | :--- | :--- |
| Billed input tokens / story | median 66.6 M (mean 79.1 M) | ≤ 40 M (−40 %) | **`20.6 M`** (`20,607,919` across 2 convs, avg `182k`/turn) |
| Test-related tokens / story | median 27.4 M (mean 31.0 M) | ≤ 14 M (−50 %) | **`7.6 M`** (`7,606,324`; `0` `poll_task` turns) |
| Test-related turns / story | median 108 (mean 134) | ≤ 54 | **`40`** (`29` check + `7` read_test + `4` write_test) |
| Failed check runs / story | median 24 (mean 25.6) | ≤ 10 | `0` verifier check failures |
| Noise failures (C + E + F) | 79 % (mean 20.3 / story) | ≤ 6 / story (−70 %) | `0` |
| Verifier bounces / story | median 3 (E30: 15, E31: 23) | ≤ 1 | `0` |
| Real bugs caught / story (A + A2) | mean 3.0 | ≥ 3.0 (floor) | *N/A (hygiene story; 0 defects on verification)* |
| Test-run minutes / story | mean 53 (E30: 47, E31: 59) | ≤ 20 | `9.09` min verifier checks (`49.23s` static + `495.76s` full) |
| `tests/unit` wall time | 392 s (333 s post-32.1) | ≤ 120 s | `321.47 s` (`full-unit` `--no-skip`; Epic 32 Lot 4 pruning target) |
| Always-on rules bytes / truncation | `36,416 B` (`12,464 B` truncated) | `AGENTS.md` ≤ 12 KB, all < 24 KB, 0 truncated | `AGENTS.md` `6,781 B`, `bmad-model-routing.md` `1,688 B`, `0` truncated |

- **Flake Log**:

| Date | Test / Check ID | Stage | Symptom | Root Cause / Resolution | Status |
| :--- | :--- | :--- | :--- | :--- | :--- |
| — | *(none observed)* | — | — | — | — |
