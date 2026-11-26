---
resource_id: help-base-settings-en
uri: orcia://system/help/settings/en
title: "Configuration: access rules, authentication, AI models, and packs"
version: "1.1.0"
lang: en
layer: BASE
bound_routes:
  - /settings
  - /configuration
  - /settings/packs
  - /settings/ai-models
  - /bootstrap
summary_what_for: "Configuration centralizes platform settings: user accounts and permissions, SSO and two-factor authentication, AI model providers, tool connectors, and declarative business packs."
---

## What this screen is for

Accessible to administrators, security officers, and architects according to their permissions, this hub configures ORCIA's governance and AI foundation. The "Business Packs" tab and registry view also let you import `.zip` archives, compose custom packs, check dependency closure, and export sanitized archives portable across workspaces.

## In 4 steps

1. Open "Accounts & Permissions" to invite users, review the 7-role matrix, or define targeted access rules ("Who?" and "On what?").
2. Under "Authentication", pick local or enterprise SSO sign-in and configure your two-factor policy.
3. Under "AI Models", register chat and document indexing providers and click "Test connection" before saving.
4. Under "Connectors" and "Business Packs", import a `.zip` bundle, compose and publish a custom pack, export a sanitized archive, and activate packs per Workspace after binding required connector slots.

## A real example

During initial setup, Alice opens Administration › AI Models, configures a primary chat provider and an indexing model, runs a live connection test, and opens "Business Packs" to compose a custom pack, export its `.zip` archive, and import it into a fresh Workspace.

## Common pitfalls

- **A secret key disappears after saving**: by design, API keys and tokens are write-only and never displayed in plain text again.
- **Pack publishing or export reports missing dependencies**: enable automatic dependency inclusion in the Pack Composer or promote referenced agents to "Active".
- **A `.zip` export rejects internal addresses or credentials**: remove internal emails, tokens, or private hostnames so exported packs stay portable; bind live workspace sources separately in the Slot Binding Drawer.
- **Activating a pack on a Workspace is blocked**: open the pack's slot drawer to bind every required connector slot to an active source or connector in that Workspace.
