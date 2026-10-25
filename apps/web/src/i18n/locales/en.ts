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
  workspaceTopology: {
    panelTitle: "OrgUnit Team Tree, Multi-Source Workspaces & 5 Dissociated Permissions",
    panelSubtitle:
      "Hybrid Bi-Mode Authentication (OIDC + Local Argon2id/TOTP), Upward Roll-up and inter-Workspace isolation.",
    personaSelectorLabel: "Simulate active RBAC persona",
    personas: {
      karim: "Karim — PLATFORM_ADMIN (Enterprise)",
      claire: "Claire — BU_DIRECTOR (Observer Roll-up)",
      marc: "Marc — TEAM_LEAD (Checkout Sub-Team)",
      nadia: "Nadia — CONTRIBUTOR (Developer)",
      partenaire: "External Partner (Invited Workspace 1)",
    },
    finopsRollupPrefix: "Consolidated FinOps Roll-up",
    confidentialExcludedNotice:
      "Workspaces marked CONFIDENTIAL_RESTRICTED block upward roll-up on business content.",
    datasourcesCountPrefix: "Attached federated datasources",
    catalogPermissionsTitle: "5 Dissociated Catalog Permissions & Black-Box Protection",
    sourceMaskedBadgeLabel: "🔒 Masked source (READ_SOURCE=False)",
    sourceOpenBadgeLabel: "📖 Accessible source (READ_SOURCE=True)",
    inspectSourceButtonLabel: "Inspect source",
    sourceDeniedErrorBanner: "HTTP 403 ERR_READ_SOURCE_DENIED — READ_SOURCE permission required",
    sourceAllowedBannerPrefix: "HTTP 200 OK — Source authorized",
    mutationGuardButtonLabel: "Test ScopeAccessGuard (Mutation)",
    mutationAllowedBanner: "HTTP 200 OK — Mutation allowed (Contributor)",
    mutationDeniedObserverBanner:
      "HTTP 403 ERR_OBSERVER_MODE_READ_ONLY — Mutation rejected in Observer mode",
  },
  catalogExplorer: {
    panelTitle: "Multi-Source Federated Catalog, SHA-256 CAS Cache & 4-Layer Overrides",
    panelSubtitle:
      "On-the-fly resolution (< 50 ms on hot cas/<sha256> cache), governed publication lifecycle, and BMAD Adapter.",
    filterAllSchemesLabel: "All schemes",
    maskedSourceBadgeLabel: "🔒 Masked source",
    openSourceBadgeLabel: "📖 Open source",
    resolveCasButtonLabel: "Resolve CAS (< 50 ms)",
    casResolvedBannerPrefix: "HTTP 200 OK — Immutable object resolved",
    promoteScopeButtonLabel: "Promote scope",
    promotedBannerPrefix: "HTTP 200 OK — Scope promoted",
    promoteDeniedObserverBanner:
      "HTTP 403 ERR_OBSERVER_MODE_READ_ONLY — Promotion rejected in Observer mode",
    overrideSectionTitle: "4-Layer Declarative Merge (Base -> Team -> Workspace -> User)",
    overrideSectionSubtitle:
      "Pure non-mutating hierarchy with deterministic cryptographic run-lock.json generation.",
    overrideLayers: {
      base: "1. Base (db://workflow)",
      teamParent: "2a. Parent Team (Architecture)",
      teamSub: "2b. Sub-Team (Checkout)",
      workspace: "3. Workspace (3 git + 2 jira + 2 confluence)",
      user: "4. User (Marc Tech Lead)",
    },
    runLockTitle: "run-lock.json Manifest (SHA-256 pinned sources)",
    bmadAdapterTitle: "Lossless BMAD Adapter (SKILL.md + customize.toml + steps/*.md)",
    bmadImportButtonLabel: "Import BMAD Pack",
    bmadImportedBanner:
      "HTTP 200 OK — BMAD Pack converted to WorkflowDefinitionEntity (source_format=BMAD_PACK) and pinned in cas/<sha256>",
  },
  permissionBroker: {
    cardBadgeTitle: "⚠️ PERMISSION BROKER",
    passthroughBadgeLabel: "Identity: passthrough",
    servicePrincipalBadgeLabel: "Identity: service_principal",
    targetUriLabel: "Blocked external source",
    requiredRoleLabel: "Required role or group (KB)",
    approverTeamLabel: "Approver team",
    slaHoursPrefix: "SLA",
    rfcHintLabel: "RFC 9457 hint (permission_broker_hint)",
    jiraRequestButtonLabel: "Request access in Atlassian Jira",
    pauseStepButtonLabel: "Pause step",
    replayStepButtonLabel: "Replay step",
    pausedStateBanner: "⏸️ Step paused pending Jira approval",
    replayedStateBanner: "✅ Access granted — Step replayed successfully (REPLAYED)",
    simulatorTitle:
      "Passthrough vs Service Principal Execution & Jira-Connected AI Permission Broker",
    simulatorSubtitle:
      "401/403 interception, Markdown/YAML KB resolution, automatic right Dock opening, and Replay Step N.",
    simulateGitDenialLabel: "Simulate 403 Git (passthrough)",
    simulateConfluenceDenialLabel: "Simulate 403 Confluence (passthrough)",
    simulateJiraDenialLabel: "Simulate 403 Jira SecOps (passthrough)",
    simulateConfusedDeputyLabel: "Test unapproved Service Principal",
    confusedDeputyBlockedBanner:
      "HTTP 403 ERR_CONFUSED_DEPUTY_BLOCKED — Unapproved service_principal execution blocked",
    observerDeniedBanner:
      "HTTP 403 ERR_OBSERVER_MODE_READ_ONLY — Permission Broker action rejected in Observer mode",
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
