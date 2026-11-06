---
id: spaces-sources
title: Connect and synchronize your document sources and tools
version: 1.1.0
lang: en
layer: BASE
bound_routes:
  - /mes-espaces/$id/sources
  - /spaces/sources
  - /workspaces
  - /settings
---

## What is this screen for?

This screen lets you connect your team's knowledge sources (code repositories, documentation spaces, project trackers, or databases) to your **Workspace** and choose where approved deliverables are saved by default.

## How to proceed step by step

1. Select the type of source to connect (code, documentation, project tracking, or database) and give it a clear display name for your team.
2. Choose the connection mode: **Each member's personal account** (every user only sees documents they are allowed to access) or **Shared team account** (approved by an administrator).
3. Write a short business justification, sign the addition, and test the connection in one click.

## Key concepts & pointers

- **Reference source vs Working document**: A reference source serves as an authoritative reading baseline; a working document hosts deliverables currently being drafted.
- **Personal account connection**: Ensures no team member can view a confidential document they do not have permission to read in the source tool.
- **Confidential workspace isolation**: Prevents sensitive workspace content from rolling up to parent levels of the organization.

## Frequently asked questions

- **What is the link between an organization entity (Business Unit, Team) and a Workspace?** The organization (Enterprise $\rightarrow$ Business Unit $\rightarrow$ Team) represents *who you are* (the organizational chart to which members belong), whereas a **Workspace** represents *what you are working on* (a project, product, or initiative where your document sources are connected and your processes run). Every Workspace is owned by a primary Team or Business Unit (a single team can manage multiple workspaces), can invite other teams to collaborate, and inherits governance rules from its parent team and business unit (unless configured in isolated confidential mode).
- **How do I view the explanation for a specific setting?** Click the `ⓘ` icon next to any heading: this help column opens and highlights the matching explanation section.
- **What happens if a document is edited directly in our external tool?** Your direct edits are always preserved and never overwritten by an automated draft.
