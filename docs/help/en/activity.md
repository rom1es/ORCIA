---
resource_id: help-base-activity-en
uri: orcia://system/help/activity/en
title: "Activity Log: immutable history and provenance"
version: "1.0.0"
lang: en
layer: BASE
bound_routes:
  - /activity
summary_what_for: "The Activity Log chronologically records who performed every action across your scopes and lets you export full provenance reports."
---

## What this screen is for

This screen provides a tamper-proof audit trail for team leads, auditors, and administrators. While the Notification Center tracks what awaits your action, the Activity Log preserves the complete history of everything already done.

## In 3 steps

1. Filter events by observation scope, author (dropdown or search), maximum recent count, or date window.
2. Browse the timeline: each entry displays the timestamp, actor name, scope, and plain-language summary.
3. Click "Provenance" on an execution row to inspect linked sources and signatures and export JSON or Markdown reports.

## A real example

During a quarterly review, a security lead filters the Activity Log to the last 7 days on the "Payments" Space, verifies who updated an access rule, and exports the provenance dossier for an approved deliverable.

## Common pitfalls

- **A recent event is missing**: check that the scope or author filter at the top is not restricting the view.
- **Notifications vs Activity Log**: the Notifications bell shows pending tasks; the Activity Log archives completed operations.
- **Non-admin users do not see the whole platform**: for privacy, each user only sees activity for Divisions, Teams, and Workspaces they are authorized to observe.
