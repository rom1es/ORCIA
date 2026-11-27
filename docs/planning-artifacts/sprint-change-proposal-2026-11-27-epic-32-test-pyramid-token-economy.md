# Sprint Change Proposal — Epic 32: Test Pyramid Pruning, Token Economy & Anti-Bloat Tech Debt

- **Date**: 2026-11-27
- **Type**: Technical debt (hygiene / NFR), classification `hygiene` — no new product capability (`CAP`: none).
- **Evidence base** (versioned under `docs/implementation-artifacts/test-optimization-2026-11-27/`):
  `01-epic30-test-duration-analysis.md`, `02-epic30-vs-epic31-test-strategy.md`, `03-failure-and-churn-analysis.md`,
  `04-token-economy-challenge-review.md`, `05-profiling-epic30-head.md`, `06-profiling-epic31-head.md`.

## 1. Problem Statement

Across Epics 30–31 (13 stories), test execution consumed 40–45 % of agent wall time and test-related LLM turns consumed
39–43 % of billed input tokens (163 M / 213 M). Only 11–12 % of failed check runs revealed real defects; 79 % were noise
(new-test bugs, environment, quality-gate loops). `tests/unit` grew from 322 s to 392 s (+21 % for +12 % tests), 21–37 %
of new test lines were coverage padding (19 fake-SQL files in Epic 31), and every LLM turn re-sends ~250 k tokens of
context in coding agents, so turn count — not stdout size — dominates token cost. The always-on rule file `GEMINI.md`
(36,416 B) exceeds the documented 24,000 B per-file rule cap and loses 12,464 B to truncation.

## 2. Locked Decisions

| ID | Decision |
|---|---|
| `T-D1` | **Coverage policy**: Unit + real PostgreSQL 18 integration coverage combined (`coverage run --parallel` + `coverage combine`, never `pytest --cov` with testcontainers); `diff-cover >= 90 %` on changed lines **once at story end** (Stage 3); never looped on by coding agents; dropped from verifier re-runs. `greenlet` concurrency removal only after a measured PG18 accuracy comparison. |
| `T-D2` | **Tooling**: `pytest-xdist` (capped `-n 4 --dist loadfile`) and `diff-cover` approved as dev/test dependencies (spine update). OpenAPI-generated Vitest mocks are built **in-house** from `openapi.json` with deterministic examples (zero new dependency). |
| `T-D3` | **Epic architecture review**: epic-closure Architect review moves to the **start of the final story** + a short diff-only review of the final story; per-story reviews kept for security-heavy / high-risk stories (`32.4` pruning has its own review). |
| `T-D4` | **Single runner** `scripts/agent_check.py`: Stage 1 (auto-fix touched files + static/AST gates), Stage 2 (targeted + impact-selected existing tests), Stage 3 (full suites + `diff-cover`). Silent on success (one line per stage); on failure **all failing test IDs** (one line each) + first 3 compact tracebacks + full log in `.agent_check/logs/`; `--maxfail` only in Stage 2 inner loops, never in Stage 3; chained `lint && coverage && pytest` one-liners banned. |
| `T-D5` | **Bounce rule**: if only `docs/` changed since the failing run, re-run only the failed check; any other change (incl. tests, migrations, configs, OpenAPI) re-runs Stage 1 + Stage 2 impact selection + the failed check. |
| `T-D6` | **Receipts**: gitignored `.agent_check/receipts/` keyed by working-tree content hash + `.venv` package state + `pnpm-lock.yaml` + Python/Node versions + sorted `ORCIA_*` / `PYTHONPATH` + runner version; file writers run check-only; deterministic stages only (static, unit) may be skipped by the verifier on standard stories; **final story of each epic runs `--no-skip`**; verifier-independence rule amended accordingly. |
| `T-D7` | **Small-context fixer**: `.agent_check/story_intent.md` (< 500 tokens) written once at story start; fixer gets intent + failure digest + target ranges; sequential; ≤ 3 calls/story; one attempt per failure, diagnosis + partial patch handback; no contract/schema or unapproved legacy-test edits; same-root-cause 2-failure escalation to `pro` takes strict priority; rolled out first on verifier bounces. |
| `T-D8` | **Rules diet**: canonical `AGENTS.md` (target of `bmad-project-context`, generator block refreshed/trimmed), core `<= 12 KB` token target, Stage 1 check enforcing every rule file `< 24,000 B` (`<= 20 KB` margin incl. expanded `@[...](...)` includes), rule-ID uniqueness; `GEMINI.md` pointer vs removal decided after verifying Antigravity deduplication against `rules.md`. Role rules move to subagent definitions / conditional rules. |
| `T-D9` | **Read discipline**: symbol / line-range reads; line-range-only on `generated/` and lockfiles; `grep -n` + bounded read for files already edited in-session; generated shared fixture & helper index with `--check` in Stage 1; dev-only token report (transcript path via env var, never in CI). |
| `T-D10` | **Anti-bloat rules** (`scripts/lint_tests.py`, ratchet mode from `32.3`, strict from `32.5`): no fake SQL engines in `tests/unit`; no new `test_story_*` files (traceability via `@pytest.mark.story` / Vitest tags); removed-assertion diff check (deletions only via redundancy-audit report); test-to-code proportionality **flag** (report, not gate); `ScopeAccessGuard` AST rule on `workspace_id` / `run_id` routes; one-owner-layer rule. |
| `T-D11` | **Pruning safety gate**: before/after combined (Unit + PG18) branch coverage with zero loss on production business/security branches; tests with a recorded real-defect catch (A/A2 list) are protected; one-off mutation sample on pruned modules. |

## 3. Execution Plan

| Story | Lot | Scope | Dogfooding |
|---|---|---|---|
| `32.1` | L1 | `agent_check.py` runner + receipts + bounce rule + impact selection v1 + suite quick wins + environment hardening | — |
| `32.2` | L2 | Agent protocol (fixer, digests, no polling, read discipline), rules diet (`AGENTS.md` canonical, size/uniqueness gates), fixture index, token report | uses `32.1` runner |
| `32.3` | L3 | Combined coverage + `diff-cover`, shared PG18/app fixtures, xdist, lazy imports, impact-selection recall validation, `lint_tests.py` ratchet | uses `32.2` rules |
| `32.4` | L4 | Repo-wide pyramid pruning with safety gate (own Architect review + mutation sample) | — |
| `32.5` | L5 (final) | Strict `lint_tests.py`, OpenAPI-generated Vitest mocks, `i18n-and-shell.test.tsx` survivor split, budgets; epic Architect review at start + diff review at end; `--no-skip` verification | — |

## 4. KPI Baseline (Epics 30–31, 13 stories) — evaluated on Epic 33 feature stories

| KPI | Baseline | Target |
|---|---|---|
| Billed input tokens / story | median 66.6 M (mean 79.1 M) | ≤ 40 M (−40 %) |
| Test-related tokens / story | median 27.4 M (mean 31.0 M) | ≤ 14 M (−50 %) |
| Test-related turns / story | median 108 (mean 134) | ≤ 54 |
| Failed check runs / story | median 24 (mean 25.6) | ≤ 10 |
| Noise failures (C + E + F) | 79 % of failures; mean 20.3 / story | ≤ 6 / story (−70 %) |
| Bounces / story | median 3 (E30: 15, E31: 23) | ≤ 1 |
| Real bugs caught / story (A + A2) | mean 3.0 | **≥ 3.0 (non-regression floor)** |
| Test-run minutes / story | mean 53 (E30: 47, E31: 59) | ≤ 20 |
| `tests/unit` wall | 392 s | ≤ 120 s |
| Always-on rules | `GEMINI.md` 36,416 B (12,464 B truncated) + routing rule 5,606 B | core ≤ 12 KB, every file < 24,000 B, zero truncation |

## 5. Exit Criteria

All five stories `done`; KPI instrumentation (`agent_check.py` summaries + dev token report) in place; AD-17 gates green
under the new runner with a final `--no-skip` verification in `32.5`; Epic 33 stories report the KPI table in their Tech
Lead reports §3.
