---
resource_id: help-base-settings-en
uri: orcia://system/help/settings/en
title: "Configuration: access rules, authentication, AI models, and packs"
version: "1.0.0"
lang: en
layer: BASE
bound_routes:
  - /settings
  - /configuration
  - /settings/packs
  - /settings/ai-models
  - /bootstrap
summary_what_for: "Configuration centralizes platform settings: user accounts and permissions, SSO and two-factor authentication, AI model providers, tool connectors, and business packs."
---

## What this screen is for

Accessible to administrators, security officers, and architects according to their permissions, this hub configures ORCIA's governance and AI foundation. It also provides a direct tab to "My Organization" to manage Divisions and Teams.

## In 4 steps

1. Open "Accounts & Permissions" to invite users, review the 7-role matrix, or define targeted access rules ("Who?" and "On what?").
2. Under "Authentication", pick local or enterprise SSO sign-in and configure your two-factor policy.
3. Under "AI Models", register chat and document indexing providers and click "Test connection" before saving.
4. Under "Connectors" and "Business Packs", connect platform tools and activate ready-to-use domain packs.

## A real example

During initial setup, Alice opens Administration › AI Models, configures a primary chat provider and an indexing model, runs a live connection test, and switches to "My Organization" to create the Product Division and Payments Team.

## Common pitfalls

- **A secret key disappears after saving**: by design, API keys and tokens are write-only and never displayed in plain text again.
- **Some tabs are hidden**: displayed tabs adapt to your active role (for example, only Security Officers can create isolation exceptions).
- **My Assistant says no indexing model is active**: configure a global document indexing model under Administration › AI Models.
