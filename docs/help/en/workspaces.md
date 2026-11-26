---
resource_id: help-base-workspaces-en
uri: orcia://system/help/workspaces/en
title: "Workspace Details: sources, packs, and rules"
version: "1.1.0"
lang: en
layer: BASE
bound_routes:
  - /workspaces
  - /workspaces/$wsId
  - /workspaces/$wsId/sources
summary_what_for: "Manage individual Workspaces, their connected knowledge sources, per-workspace pack activation and priority with connector slot binding, and local glossary definitions."
---

## What this screen is for

Control the full lifecycle of a Workspace here: its owning organization unit, connected document and tool sources, active business packs with priority ordering and connector slot bindings, inherited business rules, and direct access to the Glossary.

## In 4 steps

1. Select or create the target Workspace and check its owning Team and visibility mode.
2. Open the "Sources" tab to connect a code repository, documentation space, or issue tracker and run a sync.
3. Under "Governance & Packs", activate packs for the Workspace, adjust their priority order, and open the slot binding drawer to connect required pack slots to live Workspace sources.
4. Review "Glossary & Rules" to inspect active team definitions or log a justified exception when needed.

## A real example

Before drafting an architecture brief, Marc opens the "Customer Portal" Workspace, connects the front-end repository under Sources, binds the required slot of the "SDLC" pack to that source, and activates the pack on his Workspace.

## Common pitfalls

- **A pack refuses to activate on the Workspace**: open the slot binding drawer and make sure every required slot is bound to an active source or connector.
- **An external source fails to connect**: double-check the URL and make sure your personal credentials are saved in My Account › Tool Connections.
- **Changes in a confidential Workspace are hidden elsewhere**: isolation is enforced intentionally to protect sensitive data.
- **Need the Space glossary?** Open the "Glossary" tab directly inside My Spaces.
