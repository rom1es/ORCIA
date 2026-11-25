---
resource_id: help-base-workspaces-en
uri: orcia://system/help/workspaces/en
title: "Workspace Details: sources, rules, and deliverables"
version: "1.0.0"
lang: en
layer: BASE
bound_routes:
  - /workspaces
  - /workspaces/$wsId
  - /workspaces/$wsId/sources
summary_what_for: "Manage individual Workspaces, their connected knowledge sources, architecture rule exceptions, and local glossary definitions."
---

## What this screen is for

Control the full lifecycle of a Workspace here: its owning organization unit, connected document and tool sources, inherited business rules, and direct access to the Glossary.

## In 3 steps

1. Select or create the target Workspace and check its owning Team and visibility mode.
2. Open the "Sources" tab to connect a code repository, documentation space, or issue tracker and run a sync.
3. Review "Glossary & Rules" to inspect active team definitions or log a justified exception when needed.

## A real example

Before drafting an architecture brief, Marc opens the "Customer Portal" Workspace, connects the front-end repository under Sources, and verifies that team glossary terms are inherited properly.

## Common pitfalls

- **An external source fails to connect**: double-check the URL and make sure your personal credentials are saved in My Account › Tool Connections.
- **Changes in a confidential Workspace are hidden elsewhere**: isolation is enforced intentionally to protect sensitive data.
- **Need the Space glossary?** Open the "Glossary" tab directly inside My Spaces.
