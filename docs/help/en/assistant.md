---
resource_id: help-base-assistant-en
uri: orcia://system/help/assistant/en
title: "My Assistant: questions, folders, and verified citations"
version: "1.0.0"
lang: en
layer: BASE
bound_routes:
  - /assistant
summary_what_for: "My Assistant answers questions grounded in your active Workspace documents, cites every verified source, and organizes discussions into folders with permanent notes."
---

## What this screen is for

This screen provides a conversational partner grounded in your team's knowledge. Ask direct questions, mention a specialized agent with @, organize threads into topic folders, or turn a reply into a governed process draft.

## In 3 steps

1. Choose your model (Fast, Versatile, or Advanced Reasoning) and your thinking mode (Standard or In-Depth — e.g. "Versatile · Standard") using the selector next to the send button.
2. Open "Assistant Settings" to customize tone, format, or personal instructions (left empty by default), then confirm explicitly with the bottom-right "Save" button.
3. Type your question (use @ to mention an active agent or / to run a skill) or open "Folders" to attach your conversation to a topic and pin permanent notes.

## A real example

Marc selects the "Payments Product" Space, updates his preferred response format in Settings and clicks "Save" (the cancel control switches to "Close" once saved), opens the "2026 Compliance" folder, and asks for a risk summary: My Assistant responds with clickable citation pills pointing straight to the verified Space documents.

## Common pitfalls

- **The prompt input is locked**: verify that both a document indexing model and a chat model are configured in Administration › AI Models.
- **No citation pills appear in the reply**: when a turn does not retrieve Space documents or glossary rules (such as a simple greeting), My Assistant replies naturally without fabricating sources.
- **A draft suggests updating an external tool**: for safety, My Assistant never writes directly to external tools; confirm the action or continue inside a governed process.
- **Updated settings or folder notes are not applied**: make sure you clicked "Save" inside "Assistant Settings" ("Cancel" discards only unsubmitted edits) or "Save notes" inside the active folder drawer.
