---
trigger: always_on
---

# BMAD Model Routing & Token Discipline

- **[R-ROUTE-01]** **Zero Read-Ahead by Parent**: Orchestrator reads only `docs/` indexes/stories (`sprint-status.yaml`, `epics.md`, `capabilities.yaml`); delegate `> 2`-file exploration or repo-wide search to `bmad-scout` (`flash`).
- **[R-ROUTE-02]** **Model Routing Matrix**: `bmad-scout` (`flash`, read-only search/logs); `bmad-dev-worker` (`flash`, 1 story per coding/testing/fixer worker); `bmad-architect-worker` (`pro`, ADR/contracts/final `VALIDATE` review, docs-only).
- **[R-ROUTE-03]** **Strict 2-Failure `pro` Escalation**: After 2 consecutive failures on the same root cause, stop immediately and escalate a concise 3-point diagnostic (exact command/error, probable root cause, attempts/blocker) to `pro` on the failing scope. This takes strict priority over any remaining fixer budget.
- **[R-ROUTE-04]** **Disk Handoff & Zero Filler**: Pass plans, `.agent_check/story_intent.md`, Tech Lead reports, and failure logs by path; zero conversational preamble or restating requests.
- **[R-ROUTE-05]** **Role Playbooks & Runner-Only Discipline**: Each worker loads only its on-demand playbook (`docs/agent-playbooks/{coder,fixer,verifier,architect}.md`). Every check runs via `.venv/bin/python scripts/agent_check.py` under `timeout -k 10s`; chained shell one-liners and `manage_task` polling loops are banned (use reactive completion wakeups).
- **[R-ROUTE-06]** **Sequential Small-Context Fixer on Bounces**: On verifier bounces, dispatch `bmad-fixer-worker` (`flash`) sequentially (1 at a time, `<= 3` calls/story) with `.agent_check/story_intent.md` + verifier's `<= 20`-line digest + target line ranges.
