---
resource_id: help-pack-sdlc-spaces-sources-en
uri: orcia://packs/orcia-pack-sdlc/help/spaces-sources/en
title: "SDLC Sources (Git, Jira & Confluence) of the Space"
version: "1.1.0"
lang: en
layer: PACK
pack_name: orcia-pack-sdlc
bound_routes:
  - /mes-espaces/$id/sources
  - /workspaces/$wsId/sources
  - /spaces/sources
summary_what_for: "Connect your Git repositories, Jira projects, and Confluence spaces to power the SDLC tripartite graph."
---
### What this screen is for
Connect the engineering sources of a Space (Git repositories, Jira projects, Confluence spaces) to ground summaries and track code changes reliably.

### Step-by-Step
1. Link your primary Git repository and your sprint Jira project.
2. Enable automatic staleness detection between Confluence and Git.

### A real example
The Payments team links its main Git repository and Jira project: whenever an interface changes, the related documentation is flagged for human review.

### Common pitfalls
- **A source stays pending synchronization**: verify your personal token or connector configuration in Configuration › Connectors.

### Key Terms
- **Tripartite Graph**: Verified causal links across Confluence pages, Jira issues, and Git commits.
- **Human Anchor**: Architectural decision authored and signed by a human (human sign-off required).

### Frequently Asked Questions
- **Why is a Jira transition pending validation?** Jira transitions are pre-validated and executed only after human approval.
