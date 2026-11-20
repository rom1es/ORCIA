---
resource_id: help-base-agents-en
uri: orcia://system/help/agents/en
title: "My Agents: AI specialists, skills, and tool access"
version: "1.0.0"
lang: en
layer: BASE
bound_routes:
  - /agents
summary_what_for: "My Agents centralizes your specialized AI agents and reusable skills along with their posture, guardrails, and connected tool permissions."
---

## What this screen is for

Create, configure, and dry-run test specialized agents for specific domains (product analysis, document review, security compliance) as well as reusable skills shared across workspaces.

## In 3 steps

1. Browse active agents and skills configured for your Workspace or organization.
2. Click "+ New agent" to define its role, default reasoning effort, authorized knowledge sources, and guardrails.
3. Open an agent card to run a quick dry-run test before wiring it into a process or calling it from My Assistant.

## A real example

Yanis creates a "DORA Compliance Analyst" agent, grants read-only access to the Space's regulatory baseline while prohibiting unapproved external writes, and invokes it directly inside My Assistant via "@".

## Common pitfalls

- **An agent is missing from "@" suggestions in My Assistant**: check that the agent is published to your active Workspace or a parent team scope.
- **A skill cannot reach an external tool**: verify tool permissions on the agent and check your personal tool connections under My Account.
- **Agent menus are locked at first boot**: configure at least one AI model in Configuration › AI Models to unlock agent execution.
