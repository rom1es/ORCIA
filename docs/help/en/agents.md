---
resource_id: help-base-agents-en
uri: orcia://system/help/agents/en
title: "My Agents: AI specialists, skills, and tool access"
version: "1.1.0"
lang: en
layer: BASE
bound_routes:
  - /agents
summary_what_for: "My Agents centralizes your specialized AI agents and reusable skills (including entries from active workspace packs) along with their posture, guardrails, and connected tool permissions."
---

## What this screen is for

Create, configure, and dry-run test specialized agents for specific domains (product analysis, document review, security compliance), inspect specialists contributed by packs active in your Workspace, and manage reusable skills.

## In 3 steps

1. Browse available agents and skills: every newly created or duplicated agent starts in "Draft" status ("Untested"), while pack-contributed items show their pack provenance badge.
2. Click "+ New agent" or open "Configure & Test (6 blocks)" to define its role, knowledge sources, and guardrails, then confirm edits explicitly with the bottom-right "Save" button.
3. Run a passing check in the built-in Test Bench to promote the agent to "Active" before invoking it via "@" (or "@pack/agent" when slugs overlap), wiring it into a process, or bundling it in a custom pack.

## A real example

Yanis creates the "DORA Compliance Analyst" agent (initially "Draft"), updates its blocks and clicks "Save", then runs a passing Test Bench verification: the agent promotes to "Active" and becomes selectable in My Assistant and custom packs.

## Common pitfalls

- **An agent is missing from suggestions or My Processes**: while an agent remains "Draft" or "Untested", it is blocked from My Assistant, Processes, and pack publishing; run a passing Test Bench check to activate it.
- **Deleting an agent or skill prompts to unlink from draft packs**: the entity is referenced by one or more custom pack drafts; confirm explicit unlinking to detach it cleanly from those drafts before deletion.
- **The "Expose as external tool" option is disabled**: only "Active" workspace agents can be exposed externally (duplicate a read-only pack template first if you need to customize and expose it).
- **Agent execution fails at first boot**: configure at least one active AI model in Administration › AI Models before running the Test Bench.
