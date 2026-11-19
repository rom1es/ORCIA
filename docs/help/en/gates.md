---
resource_id: help-base-gates-en
uri: orcia://system/help/gates/en
title: "Quality Gates & Human Reviews: section-by-section sign-off"
version: "1.0.0"
lang: en
layer: BASE
bound_routes:
  - /gates
summary_what_for: "This screen manages automated quality checks, independent model cross-reviews, and section-by-section human sign-off before any deliverable is published."
---

## What this screen is for

Before a workflow deliverable is approved or pushed to an external tool, ORCIA runs three layers of verification: deterministic checks, independent cross-model review, and section-by-section human review with safeguards against rushed approval.

## In 3 steps

1. Review the execution briefing, retained assumptions, and any flagged discrepancies.
2. Walk through the deliverable chunk by chunk to approve each section, co-edit text directly, or request revisions.
3. Submit your final decision (approve or loop back to an earlier stage) once all sections are checked.

## A real example

When reviewing a technical specification, Nadia inspects the 4 generated sections, co-edits the security paragraph directly to sharpen a requirement, approves the rest, and finalizes the gate to release the staged actions.

## Common pitfalls

- **A confirmation dialog blocks instant finalization**: if a review is submitted too quickly without inspecting sections, ORCIA asks for explicit confirmation to protect review quality.
- **Cross-review notes only one provider**: add a second independent AI provider in Configuration › AI Models to unlock orthogonal cross-reviews.
- **An external action stays staged**: no update to Jira, GitLab, or Confluence is sent until final human approval is signed.
