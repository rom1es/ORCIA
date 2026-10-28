import type { TranslationDictionary } from "../types";

export const enDictionary: TranslationDictionary = {
  locale: "en",
  shell: {
    brandTitle: "ORCIA",
    brandSubtitle: "",
    sidebarNavigationAriaLabel: "7-Module Global Navigation",
    sidebarToggleExpandLabel: "Expand sidebar",
    sidebarToggleCollapseLabel: "Collapse sidebar",
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
      bootstrap: "Initialization & Onboarding",
    },
    staleWarningBadgeLabel: "! [STALE_WARNING]",
    humanProfilePrefixLabel: "Human Profile",
    assistantDockTitle: "Assistant Agent & Permission Broker",
    assistantDockSubtitle: "Governed Passthrough execution",
    assistantDockToggleExpandLabel: "Expand Assistant Dock",
    assistantDockToggleCollapseLabel: "Collapse Assistant Dock",
    assistantPermissionBrokerReadyLabel: "Permission Broker active",
    assistantInputPlaceholder: "Ask the Assistant or diagnose a 403 access denial...",
    assistantSendLabel: "Send to Assistant",
    localeSwitchLabel: "Language",
    topbarSearchAriaLabel: "Global search",
    topbarSearchPlaceholder: "Search... (⌘K)",
    darkModeToggleLabel: "🌙 Dark mode",
    mobileNavigationAriaLabel: "Mobile Companion Navigation",
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
  arbitrationTieBreak: {
    badgeTitle: "⚖️ HUMAN ARBITRATION REQUIRED (WAITING_FOR_HUMAN_ARBITRATION)",
    policyPrefixLabel: "Tie-break policy",
    recommendedBadgeLabel: "★ Recommended",
    prosLabel: "Pros",
    consLabel: "Cons",
    siImpactLabel: "IT Impact",
    finopsImpactLabel: "FinOps",
    justificationPlaceholder: "Optional justification or additional guidance...",
    selectOptionButtonLabel: "Select option",
    resolvedBannerPrefix: "✅ Arbitration decision recorded in Blackboard",
    defaultQuestionTitle: "Multi-currency FX rate guarantee: 15-min Spot Rate vs 48-hr Locked Rate",
    defaultContextSummary:
      "Two equivalent technical and business options identified by the Executor Agent (FR-5, UX-DR6).",
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
    workflowStudio: {
      studioTitle:
        "Workflow-as-Code YAML/JSON Studio (SUB_WORKFLOW <= 3), Intention -> Code Discipline & Multi-Audience Templates",
      studioSubtitle:
        "Line-numbered static validation, HIGH_CRITICAL vs AUTONOMOUS_CONTRACT guard, and recursive sub_workflow_locks pinning.",
      validateNominalLabel: "Validate nominal DAG (depth=2 <= 3)",
      simulateCriticalAutonomousLabel: "Test HIGH_CRITICAL + AUTONOMOUS_CONTRACT (422)",
      simulateMissingIntentionLabel: "Test code write without upstream Intention (422)",
      simulateMaxDepthLabel: "Test SUB_WORKFLOW depth=4 > 3 (422)",
      validDagBanner:
        "HTTP 200 OK — Valid DAG: 3 topological steps, Intention -> Code satisfied, max_nesting_depth=2 <= 3",
      criticalAutonomousErrorBanner:
        "HTTP 422 ERR_CRITICAL_WORKFLOW_REQUIRES_HUMAN_GATE [Line 6] — HIGH_CRITICAL workflow cannot use AUTONOMOUS_CONTRACT",
      missingIntentionErrorBanner:
        "HTTP 422 ERR_INTENTION_BEFORE_CODE_REQUIRED [Line 18] — Step writes_code=true lacks upstream declares_intention=true",
      maxDepthErrorBanner:
        "HTTP 422 ERR_SUB_WORKFLOW_MAX_DEPTH_EXCEEDED [Line 24] — SUB_WORKFLOW depth 4 > 3",
      templatePreviewTitle:
        "Multi-Audience Artifact Template Compiler (tpl-architecture-decision-record)",
      humanMarkdownTabLabel: "Human View (Markdown + Chunks)",
      agentSchemaTabLabel: "Agent View (Ontology JSON Schema)",
      sampleHumanMarkdown:
        "## 1. Strategic Intent & Human Arbitration [✍️ ANCRE HUMAINE OBLIGATOIRE]\nGuiding intent for **Claims Core Engine** (Issue `PAY-142`)",
      sampleAgentJsonSchema:
        '{"$schema":"https://json-schema.org/draft/2020-12/schema","x-bound-ontology-terms":["Actif Stratégique","Exemption 3DS Frictionless TRA"]}',
      subWorkflowLocksTitle: "Recursive sub_workflow_locks tree pinned in run-lock.json",
    },
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
  bootstrapOnboarding: {
    panelTitle: "Day-0 Governed System Bootstrap Workflows & Autonomous Team Onboarding",
    panelSubtitle:
      "6 pre-embedded workflows (orcia://system/bootstrap/*), LLM orthogonality (>= 2 families), TEAM_LEAD self-service, and Human Anchor.",
    orthogonalityTitle: "Day-0 Gate (init-organization) — ModelRouterService (>= 2 LLM families)",
    orthogonalityPassBadge: "LLM Orthogonality verified (3 families: anthropic-claude, mistral-large, openai-gpt)",
    orthogonalityFailBanner:
      "HTTP 422 ERR_MODEL_ORTHOGONALITY_VIOLATION — At least 2 orthogonal LLM families are required",
    simulateSingleFamilyLabel: "Test single LLM family (Reject 422)",
    simulateDualFamilyLabel: "Validate >= 2 orthogonal LLM families",
    initWorkspaceTitle: "Autonomous Team & Multi-Workspace Onboarding (init-workspace, TEAM_LEAD)",
    initWorkspaceButtonLabel: "Execute init-workspace (Multi-Workspaces)",
    initWorkspaceSuccessBanner:
      "HTTP 200 OK — Team, 2 Solution Workspaces, 4-layer overrides, and invitations created without IT ticket",
    initDatasourceTitle: "Governed Multi-Source Attachment (init-datasource) & Human Anchor",
    initDatasourceButtonLabel: "Publish federated datasource (init-datasource)",
    initDatasourceSuccessBanner:
      "HTTP 200 OK — Datasource published in Federated Catalog with signed Human Anchor and freshness TTL",
    humanAnchorErrorBanner:
      "HTTP 422 ERR_HUMAN_ANCHOR_REQUIRED — Human justification (>= 30 chars) and signature required",
    initUserTitle: "First-Login Onboarding & AES-256-GCM Passthrough Pairing (init-user)",
    initUserButtonLabel: "Execute init-user (Passthrough Pairing)",
    initUserSuccessBanner:
      "HTTP 200 OK — Human Profile confirmed & Passthrough tokens (Git, Jira, Confluence) encrypted AES-256-GCM",
    observerDeniedBanner:
      "HTTP 403 ERR_OBSERVER_MODE_READ_ONLY — Bootstrap workflow execution rejected in Observer mode",
    humanAnchorCardLabels: {
      badgeTitle: "✍️ MANDATORY HUMAN ANCHOR (human_authored_required: true)",
      authorLabel: "Human signer",
      sectionTitle: "Federated connector security & scope justification",
      placeholderText: "Enter mandatory human justification (>= 30 characters)...",
      signatureLabel: "Human author signature",
      signaturePlaceholder: "e.g. Marc (Checkout Tech Lead)",
      submitLabel: "Sign human anchor",
    },
  },
  ontologyExplorer: {
    panelTitle: "4-Level Ontology Explorer, What-If Simulator & Tripartite Graph",
    panelSubtitle:
      "CTE Inheritance (Enterprise -> Domain -> Team/Workspace -> Run), Hybrid RAG halfvec(1024)+BM25, and [STALE_WARNING] alerts.",
    emptyStateMessage:
      "No ontology concepts or indexed documents in initial state (0 sample rows by default). Run init-workspace or init-datasource to populate the ontology and Hybrid RAG.",
    columns: {
      "1_ENTERPRISE": "1. Enterprise (Global)",
      "2_DOMAIN": "2. Domain (BU)",
      "3_TEAM": "3a. Team (Tree)",
      "3_WORKSPACE": "3b. Solution Workspace",
      "4_RUN_EPHEMERAL": "4. Ephemeral Run (Branch)",
    },
    profileSelectorLabel: "Human Profile Translation:",
    whatIfButtonLabel: "Simulate Impact (What-If)",
    promoteButtonLabel: "Promote concept",
    promotedBannerPrefix: "What-If simulation executed for:",
    immutableConflictBanner: "ERR_ONTOLOGY_CONFLICT (HTTP 422): parent axiom immutable=true cannot be overridden.",
    hybridRagTitle: "Hybrid RAG Search (halfvec(1024) + BM25 RRF)",
    hybridRagSearchPlaceholder: "Search concept, Jira issue (PAY-142), or AST symbol...",
    hybridRagSearchButtonLabel: "Search",
    tripartiteTitle: "Multi-Source Tripartite Graph (Confluence <-> Jira <-> Git)",
    staleAlertsTitle: "data-freshness Brick & [STALE_WARNING] Alerts",
    docObsoleteBadgeLabel: "[DOC_OBSOLETE_SUSPECTED]",
  },
  modulePages: {
    cockpit: {
      subtitle: "Human-Led, Agent-Accelerated Co-Design Space",
      description:
        "Drive durable Workflows, author Mandatory Human Anchors, and resolve tie-break arbitration matrices.",
      uriBadgeExample: "orcia://system/workflows/assistant-agent",
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
        "Manage the OrgUnit team tree, multi-source Solution Workspaces, and their access permissions.",
      uriBadgeExample: "orcia://system/workspaces/topology",
    },
    bootstrap: {
      subtitle: "Day-0 System Bootstrap Workflows & Team Onboarding",
      description:
        "Initialize the organization (init-organization), Solution Workspaces (init-workspace), federated datasources, and users.",
      uriBadgeExample: "orcia://system/bootstrap/init-workspace",
    },
  },
};
