---
resource_id: help-base-processes-en
uri: orcia://system/help/processes/en
title: "My Processes: catalog, studio, and value stream"
version: "1.0.0"
lang: en
layer: BASE
bound_routes:
  - /processes
  - /processes/studio/$workflowId
  - /processes/vsm/$vsmId
  - /processes/runs/$runId
summary_what_for: "My Processes separates pending validations, the business process catalog, and the value stream map, opening every run in a dedicated Focus Review centered on human decisions."
---

## What this screen is for

This screen organizes your work into three tabs ("Validations & Runs", "Business Processes", and "Value Stream"). When zero runs await review, it opens straight onto "Business Processes". Each launched run opens a dedicated Focus Review highlighting the expected action, the primary deliverable, and a collapsible reasoning rail.

## In 3 steps

1. Browse "Business Processes" (selected automatically when no validations are pending) to inspect or launch a process in your active Space.
2. Click "Open Studio" to refine instructions, authorized active agents, and approval gates, then save and publish.
3. Open a run in Focus Review (single expected-action banner on top, deliverable pane on the left, collapsible reasoning on the right) to approve the stage, request targeted changes, or pause.

## A real example

Claire opens "My Processes" for her Space, launches "Request Qualification & Scoping Brief", and reviews the Focus screen: the top banner presents the single expected approval button while the deliverable remains clearly visible without being buried under agent reasoning.

## Common pitfalls

- **A process run refuses to start**: verify that an active chat model is configured under Administration › AI Models and at least one source is attached to the active Space (or provide explicit run inputs).
- **A process remains in draft**: click "Publish" in the Studio so it becomes active across your Space.
- **Studio recommends a desktop screen on mobile**: you can review artifacts and respond to approvals on a phone, while full multi-block design is optimized for desktop monitors.
- **A deliverable needs revisions**: click "Request changes" in the top Focus banner to target an earlier step with your feedback.
