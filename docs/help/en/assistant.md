---
resource_id: help-base-assistant-en
uri: orcia://system/help/assistant/en
title: "My Assistant: questions, folders, and verified citations"
version: "1.0.0"
lang: en
layer: BASE
bound_routes:
  - /assistant
  - /inbox
summary_what_for: "My Assistant answers questions grounded in your active Workspace documents, cites every verified source, and organizes discussions into folders with permanent notes."
---

## What this screen is for

This screen provides a conversational partner grounded in your team's knowledge. Ask direct questions, mention a specialized agent with `@`, organize threads into topic folders, or turn a reply into a governed process draft.

## In 3 steps

1. Choose your analysis depth using the model and effort picker next to the send button (Fast, Balanced, or In-Depth).
2. Type your question (use `@` to mention an agent or `/` to run a skill) and send.
3. Open "Folders" to attach your conversation to a topic and pin permanent instructions that stay active across questions.

## A real example

Marc selects the "Payments Product" Space, opens the "2026 Compliance" folder with its pinned guidelines, and asks for a risk summary: My Assistant responds with clickable citation pills pointing straight to the verified Space documents.

## Common pitfalls

- **The prompt input is locked**: verify that both a document indexing model and a chat model are configured in Configuration › AI Models.
- **A draft suggests updating an external tool**: for safety, My Assistant never writes directly to external tools; confirm the action or continue inside a governed process.
- **Folder notes do not seem applied**: click "Save notes" inside the active folder drawer before sending your next question.
