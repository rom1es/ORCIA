import type { TranslationDictionary } from "../types";

export const enDictionary: TranslationDictionary = {
  locale: "en",
  shell: {
    brandTitle: "ORCIA",
    brandSubtitle: "Obsidian Cockpit & Daylight Studio",
    sidebarNavigationAriaLabel: "7-Module Global Navigation",
    sidebarToggleExpandLabel: "Expand sidebar ([)",
    sidebarToggleCollapseLabel: "Collapse sidebar ([)",
    scopeSwitcherButtonLabel: "Scope Switcher (⌘W)",
    scopeSwitcherDialogTitle: "Hierarchical Scope Switcher (⌘W)",
    scopeSwitcherCloseLabel: "Close",
    scopeLevels: {
      GLOBAL: "Global Platform",
      BU: "BU / Tribe",
      TEAM: "Team",
      WORKSPACE: "Solution Workspace",
    },
    accessModes: {
      CONTRIBUTOR_ACTION_REQUIRED: "Contributor (Action required)",
      READ_ONLY_OBSERVER: "Read-only (Observer)",
    },
    modules: {
      cockpit: "Cockpit & Chat",
      inbox: "Inbox & My Runs",
      catalog: "Federated Catalog",
      ontology: "Ontology & KB",
      gates: "Gates & Permissions",
      finops: "FinOps & Audit",
      admin: "Workspace Administration & Control",
    },
    staleWarningBadgeLabel: "! [STALE_WARNING]",
    humanProfilePrefixLabel: "Human Profile",
    conciergeDockTitle: "Concierge Agent & Permission Broker",
    conciergeDockSubtitle: "Governed Passthrough execution",
    conciergeDockToggleExpandLabel: "Expand Concierge Dock (])",
    conciergeDockToggleCollapseLabel: "Collapse Concierge Dock (])",
    conciergePermissionBrokerReadyLabel: "Permission Broker active",
    conciergeInputPlaceholder: "Ask the Concierge or diagnose a 403 access denial...",
    conciergeSendLabel: "Send to Concierge",
    localeSwitchLabel: "Language",
    mobileTabs: {
      inbox: "🔔 Inbox",
      chat: "💬 Arbitration/Chat",
      briefing: "📄 Briefing",
    },
  },
  humanAnchor: {
    badgeTitle: "✍️ MANDATORY HUMAN ANCHOR (human_authored_required: true)",
    authorLabel: "Human author",
    placeholderText: "Enter your foundational assumptions (mandatory human authoring)...",
    submitLabel: "Sign human anchor",
    defaultSectionTitle: "Architectural Intent & Constraints",
    defaultAuthorName: "System Architect / Tech Lead",
    defaultValue: "Strict hexagonal isolation and zero-drift OpenAPI 3.1 contract (0-diff).",
  },
  modulePages: {
    cockpit: {
      subtitle: "Human-Led, Agent-Accelerated Co-Design Space",
      description:
        "Drive durable Workflows, author Mandatory Human Anchors, and resolve tie-break arbitration matrices.",
      uriBadgeExample: "orcia://system/workflows/concierge-agent",
    },
    inbox: {
      subtitle: "Unified Notification Inbox & Real-Time Presence Lock (< 500ms)",
      description:
        "Inspect active Workflow Runs in Contributor or Observer mode and claim pending steps.",
      uriBadgeExample: "orcia://runs/active/inbox",
    },
    catalog: {
      subtitle: "Multi-Source Federated Catalog & SHA-256 CAS Cache",
      description:
        "Browse federated resources (git://, jira://, confluence://, db://, nexus://) and 4-layer overrides.",
      uriBadgeExample: "git://orcia-core/skills/bmad-pack@sha256:8f4e2b",
    },
    ontology: {
      subtitle: "4-Level Dynamic Ontology & Hybrid RAG Knowledge Base",
      description:
        "Govern semantic concepts (Enterprise, Domain, Team/Workspace, Ephemeral Run) and resolve [STALE_WARNING] alerts.",
      uriBadgeExample: "confluence://ARCHI/ontology-v1@v12",
    },
    gates: {
      subtitle: "Deterministic, Cross-Model Agentic Gates & Permission Broker",
      description:
        "Audit orthogonal lens DAG evaluations and unblock 401/403 access denials via Jira.",
      uriBadgeExample: "jira://IAM/PERM-403",
    },
    finops: {
      subtitle: "Immutable Audit Ledger & FinOps Budget Circuit Breaker",
      description:
        "Track token costs per model/step and verify cryptographic run-lock.json provenance.",
      uriBadgeExample: "db://orcia/audit_ledger",
    },
    admin: {
      subtitle: "Unified Workspace Control Center & Organizational Units",
      description:
        "Manage the OrgUnit team tree, multi-source Solution Workspaces, and Day-0 bootstrap workflows.",
      uriBadgeExample: "orcia://system/bootstrap/init-workspace",
    },
  },
};
