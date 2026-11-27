# ORCIA Small-Context Fixer Playbook (`bmad-fixer-worker`)

Load this playbook only when dispatched to repair a localized check or bounce failure (`T-D7`). Follow `R-CORE-01..12` and `R-READ-01..04`.

- **[R-FIX-01]** **Sequential Bounce Rollout**: Dispatched sequentially by the Coordinator on verifier bounces (one fixer active at a time, rolled out on bounces before any mid-coding use).
- **[R-FIX-02]** **Minimal Bounded Context**: Read **only**:
  1. `.agent_check/story_intent.md` (`< 500` tokens — goal, ACs, invariants, non-goals).
  2. Verifier's `<= 20`-line failure digest (failing stage, test IDs, minimal reproduction command, `A`/`A2`/`B` classification).
  3. Exact target file line ranges (`StartLine`/`EndLine`) specified in the digest or traceback.
  Do **not** load full planning docs, epics, or unrelated modules.
- **[R-FIX-03]** **Single-Attempt Bound & Minimal Reproducer**: Make **1 focused fix attempt** per failure, then verify using **only** the minimal reproduction command from the digest plus `.venv/bin/python scripts/agent_check.py static` (or `impact --files <touched>`), wrapped in `timeout -k 10s`. Never run full suites.
- **[R-FIX-04]** **Story Budget & `pro` Escalation Priority**: Maximum **`<= 3` fixer calls per story**. **Same-root-cause 2-failure escalation to `pro` (`R-ROUTE-03`) takes strict priority** over any remaining fixer budget — if this is the second failure on the same root cause, stop immediately.
- **[R-FIX-05]** **Contract & Legacy-Test Guard**: **Never** edit API transport contracts/schemas (`apps/api/src/orcia_api/schemas/`, `packages/api-client/openapi.json`, `packages/api-client/src/generated/`), Alembic migrations (`infra/migrations/versions/`), or existing legacy test assertions/timeouts **unless** the Verifier digest explicitly carries an approved **`B` (intentional behavior change)** classification.
- **[R-FIX-06]** **Structured Failure Handback**: If the single fix attempt fails verification, stop immediately (no retry loop) and return:
  1. Exact minimal reproducer output (`<= 10` lines).
  2. Structured diagnosis (root cause + why the patch did not resolve it).
  3. Partial patch status (touched file paths + line ranges, or reverted clean state).
- **[R-FIX-07]** **Runner-Only & No Polling**: Use `scripts/agent_check.py` or the minimal pytest/vitest reproducer command under `timeout -k 10s`; never chain `&&` one-liners, never poll `manage_task`, and never loosen assertions or timeouts.
