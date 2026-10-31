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
  - /spaces
summary_what_for: "Connect your Git repositories, Jira projects, and Confluence spaces to power the SDLC tripartite graph."
---
### Step-by-Step
1. Link your primary Git repository and your sprint Jira project.
2. Enable automatic staleness detection (`[STALE_WARNING]`) between Confluence and Git.

### Key Terms
- **Tripartite Graph**: Verified causal links across Confluence pages, Jira issues, and Git commits.
- **Human Anchor**: Architectural decision authored and signed by a human (`human_authored_required`).

### Frequently Asked Questions
- **Why is a Jira transition in Staged mode?** Jira transitions are pre-validated and executed only after Gate approval.
