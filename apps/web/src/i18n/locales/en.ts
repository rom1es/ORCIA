import type { TranslationDictionary } from "../types";
import { ADMIN_AND_STUDIO_EN_LABELS } from "./admin_and_studio_labels";
import { ASSISTANT_EN_LABELS } from "./assistant_labels";
import { GOVERNANCE_AND_PACKS_EN_LABELS } from "./governance_and_packs_labels";
import { INBOX_AND_COCKPIT_EN_LABELS } from "./inbox_and_cockpit_labels";
import { SHELL_AND_SEARCH_EN_LABELS } from "./shell_and_search_labels";

export const enDictionary: TranslationDictionary = {
  ...INBOX_AND_COCKPIT_EN_LABELS,
  ...ADMIN_AND_STUDIO_EN_LABELS,
  ...SHELL_AND_SEARCH_EN_LABELS,
  ...ASSISTANT_EN_LABELS,
  ...GOVERNANCE_AND_PACKS_EN_LABELS,
  locale: "en",
  shell: {
    brandTitle: "ORCIA",
    brandSubtitle: "",
    sidebarNavigationAriaLabel: "Main navigation",
    sidebarToggleExpandLabel: "Expand sidebar",
    sidebarToggleCollapseLabel: "Collapse sidebar",
    scopeSwitcherButtonLabel: "Workspace Switcher (⌘W)",
    scopeSwitcherDialogTitle: "Workspace & Organization Switcher (⌘W)",
    scopeSwitcherCloseLabel: "Close",
    scopeLevels: {
      GLOBAL: "Global Platform",
      BU: "Division / Department",
      TEAM: "Team",
      WORKSPACE: "Workspace",
    },
    accessModes: {
      CONTRIBUTOR_ACTION_REQUIRED: "Contributor (Action required)",
      READ_ONLY_OBSERVER: "Read-only (Observer)",
    },
    modules: {
      cockpit: "Cockpit & Decisions",
      inbox: "My Assistant",
      catalog: "Agents & Skills",
      ontology: "Knowledge & Glossary",
      gates: "Processes & Reviews",
      finops: "Costs & Activity Log",
      admin: "My Spaces",
      bootstrap: "Initial Setup",
    },
    staleWarningBadgeLabel: "! Needs review (source updated)",
    humanProfilePrefixLabel: "Business Role",
    assistantDockTitle: "Assistant & Source Access",
    assistantDockSubtitle: "Secure execution under your account",
    assistantDockToggleExpandLabel: "Expand Assistant panel",
    assistantDockToggleCollapseLabel: "Collapse Assistant panel",
    assistantPermissionBrokerReadyLabel: "Access assistance active",
    assistantInputPlaceholder: "Ask the Assistant or request a missing source access...",
    assistantSendLabel: "Send to Assistant",
    localeSwitchLabel: "Language",
    topbarSearchAriaLabel: "Global search",
    topbarSearchPlaceholder: "Search... (⌘K)",
    darkModeToggleLabel: "🌙 Dark mode",
    mobileNavigationAriaLabel: "Mobile navigation",
    mobileTabs: {
      inbox: "🔔 To Do",
      chat: "💬 Decisions / Chat",
      briefing: "📄 Summary",
    },
  },
  humanAnchor: {
    badgeTitle: "✍️ PERSONAL AUTHORING REQUIRED",
    authorLabel: "Author",
    placeholderText: "Enter your guiding directions and key assumptions (personal authoring required)...",
    submitLabel: "Confirm and sign my entry",
    defaultSectionTitle: "Business Intent & Guidelines",
    defaultAuthorName: "Lead Owner",
    defaultValue: "Definition of priority goals and expected acceptance criteria.",
  },
  arbitrationTieBreak: {
    badgeTitle: "⚖️ DECISION REQUIRED",
    policyPrefixLabel: "Decision rule",
    recommendedBadgeLabel: "★ Recommended",
    prosLabel: "Pros",
    consLabel: "Cons",
    siImpactLabel: "Business & tool impact",
    finopsImpactLabel: "Estimated cost",
    justificationPlaceholder: "Optional justification or additional guidance...",
    selectOptionButtonLabel: "Choose this option",
    resolvedBannerPrefix: "✅ Decision recorded for the next steps of the process",
    defaultQuestionTitle: "Choice between two directions",
    defaultContextSummary:
      "Two equivalent options have been prepared and require your decision.",
  },
  workspaceTopology: {
    panelTitle: "Team Organization, Workspaces and Access Rights",
    panelSubtitle:
      "Review your organization structure, attached workspaces, and source visibility.",
    personaSelectorLabel: "Preview from a role's perspective",
    personas: {
      karim: "Karim — Platform Administrator (Organization)",
      claire: "Claire — Division Director (Consolidated view)",
      marc: "Marc — Team Lead (Payments Team)",
      nadia: "Nadia — Contributor (Delivery)",
      partenaire: "External Partner (Restricted to Workspace 1)",
    },
    finopsRollupPrefix: "Consolidated budget tracking",
    confidentialExcludedNotice:
      "Workspaces marked as confidential do not expose any business content to parent levels.",
    datasourcesCountPrefix: "Connected document sources and tools",
    catalogPermissionsTitle: "Source Access Rights & Confidential Content Protection",
    sourceMaskedBadgeLabel: "🔒 Unauthorized source",
    sourceOpenBadgeLabel: "📖 Accessible source",
    inspectSourceButtonLabel: "View source",
    sourceDeniedErrorBanner: "Access denied — You do not have read permission for this source",
    sourceAllowedBannerPrefix: "Access granted — Source available",
    mutationGuardButtonLabel: "Check edit permission",
    mutationAllowedBanner: "Editing allowed (active Contributor role)",
    mutationDeniedObserverBanner:
      "Action denied — Your current role is limited to read-only access",
  },
  catalogExplorer: {
    panelTitle: "Catalog of Agents, Skills and Process Templates",
    panelSubtitle:
      "Browse available resources across your workspaces and tailor them to your needs.",
    filterAllSchemesLabel: "All sources",
    maskedSourceBadgeLabel: "🔒 Restricted source",
    openSourceBadgeLabel: "📖 Accessible source",
    resolveCasButtonLabel: "Verify version",
    casResolvedBannerPrefix: "Version verified and ready to use",
    promoteScopeButtonLabel: "Share to a higher level",
    promotedBannerPrefix: "Resource shared successfully",
    promoteDeniedObserverBanner:
      "Sharing denied — Your current role is limited to read-only access",
    overrideSectionTitle: "Customization by Level (Standard -> Team -> Workspace -> Personal)",
    overrideSectionSubtitle:
      "Adapt settings at each level while preserving full traceability of the versions used.",
    overrideLayers: {
      base: "1. Reference standard",
      teamParent: "2a. Parent team",
      teamSub: "2b. Sub-team",
      workspace: "3. Workspace",
      user: "4. Personal preferences",
    },
    runLockTitle: "Reference versions used for this execution",
    bmadAdapterTitle: "External skill pack import",
    bmadImportButtonLabel: "Import skill pack",
    bmadImportedBanner:
      "Skill pack imported and ready to use in your processes",
    workflowStudio: {
      studioTitle:
        "Process Design Studio & Deliverable Templates",
      studioSubtitle:
        "Verify step consistency, required review checkpoints, and deliverable structure.",
      validateNominalLabel: "Verify a valid process",
      simulateCriticalAutonomousLabel: "Test a critical process without human review",
      simulateMissingIntentionLabel: "Test delivery without prior framing",
      simulateMaxDepthLabel: "Test excessive nested sub-processes",
      validDagBanner:
        "Valid process: step sequence is consistent and prior framing is present",
      criticalAutonomousErrorBanner:
        "Review required [Line 6] — A critical process must include a human review step",
      missingIntentionErrorBanner:
        "Framing required [Line 18] — This step requires a prior goal-setting step",
      maxDepthErrorBanner:
        "Structure too deep [Line 24] — Nested sub-processes exceed the maximum allowed depth (3)",
      templatePreviewTitle:
        "Deliverable Template Preview by Audience",
      humanMarkdownTabLabel: "Reading View (Structured document)",
      agentSchemaTabLabel: "Structured View (Expected fields)",
      sampleHumanMarkdown:
        "## 1. Goals & Guidelines [✍️ PERSONAL AUTHORING REQUIRED]\nGuiding directions for the deliverable",
      sampleAgentJsonSchema:
        '{"$schema":"https://json-schema.org/draft/2020-12/schema","x-bound-ontology-terms":["Strategic Asset"]}',
      subWorkflowLocksTitle: "Linked sub-processes and associated versions",
    },
  },
  permissionBroker: {
    cardBadgeTitle: "⚠️ SOURCE ACCESS REQUIRED",
    passthroughBadgeLabel: "Account used: your personal account",
    servicePrincipalBadgeLabel: "Account used: shared technical account",
    targetUriLabel: "Inaccessible external source",
    requiredRoleLabel: "Required permission or group",
    approverTeamLabel: "Team responsible for access",
    slaHoursPrefix: "Typical turnaround",
    rfcHintLabel: "Resolution guidance",
    jiraRequestButtonLabel: "Request access from the responsible team",
    pauseStepButtonLabel: "Put step on hold",
    replayStepButtonLabel: "Restart step",
    pausedStateBanner: "⏸️ Step placed on hold until access is granted",
    replayedStateBanner: "✅ Access confirmed — Step restarted successfully",
    simulatorTitle:
      "External Source Access Management & Permission Requests",
    simulatorSubtitle:
      "Automatic detection of missing permissions, owner identification, and step restart once unlocked.",
    simulateGitDenialLabel: "Test missing access on a code repository",
    simulateConfluenceDenialLabel: "Test missing access on a documentation space",
    simulateJiraDenialLabel: "Test missing access on a tracking project",
    simulateConfusedDeputyLabel: "Test an unauthorized technical account",
    confusedDeputyBlockedBanner:
      "Execution blocked — This shared technical account has not been approved by an administrator",
    observerDeniedBanner:
      "Action denied — Your current role is limited to read-only access",
  },
  bootstrapOnboarding: {
    panelTitle: "Initial Setup Assistant & Team Onboarding",
    panelSubtitle:
      "Guided steps to configure your organization, create workspaces, and connect your sources.",
    orthogonalityTitle: "Step 1 — Configure at least two independent AI model providers",
    orthogonalityPassBadge: "AI model diversity verified (3 independent providers configured)",
    orthogonalityFailBanner:
      "Incomplete setup — Configure at least 2 distinct AI model providers to cross-check reviews",
    simulateSingleFamilyLabel: "Test with a single AI provider",
    simulateDualFamilyLabel: "Verify with at least 2 distinct AI providers",
    initWorkspaceTitle: "Autonomous Team and Workspace Creation",
    initWorkspaceButtonLabel: "Create team and workspaces",
    initWorkspaceSuccessBanner:
      "Team, workspaces, and invitations created successfully",
    initDatasourceTitle: "Connect a New Document Source or Tool",
    initDatasourceButtonLabel: "Save and publish source",
    initDatasourceSuccessBanner:
      "Source connected to the workspace with its justification and update frequency",
    humanAnchorErrorBanner:
      "Justification required — Please write a justification of at least 30 characters and sign",
    initUserTitle: "Profile Setup & Personal Tool Connections",
    initUserButtonLabel: "Save my profile and personal connections",
    initUserSuccessBanner:
      "Business role confirmed and personal credentials saved securely",
    observerDeniedBanner:
      "Action denied — Your current role is limited to read-only access",
    humanAnchorCardLabels: {
      badgeTitle: "✍️ PERSONAL AUTHORING REQUIRED",
      authorLabel: "Signer",
      sectionTitle: "Business justification and usage scope for this source",
      placeholderText: "Explain why this source is connected to the workspace (at least 30 characters)...",
      signatureLabel: "Responsible person's name or signature",
      signaturePlaceholder: "e.g. Workspace Lead",
      submitLabel: "Confirm and sign",
    },
  },
  ontologyExplorer: {
    panelTitle: "Business Glossary, Organization Rules & Document Links",
    panelSubtitle:
      "Browse shared definitions across every level of the organization and preview the impact of changes.",
    emptyStateMessage:
      "No business terms or documents indexed yet. Create a workspace or connect a source to enrich the knowledge base.",
    columns: {
      "1_ENTERPRISE": "1. Organization (Global)",
      "2_DOMAIN": "2. Division / Department",
      "3_TEAM": "3a. Team",
      "3_WORKSPACE": "3b. Workspace",
      "4_RUN_EPHEMERAL": "4. Current execution",
    },
    profileSelectorLabel: "Adapt wording to role:",
    whatIfButtonLabel: "Preview change impact",
    promoteButtonLabel: "Propose term to higher level",
    promotedBannerPrefix: "Impact preview calculated for:",
    immutableConflictBanner: "Change rejected: this parent organization rule cannot be contradicted.",
    hybridRagTitle: "Knowledge Base Search",
    hybridRagSearchPlaceholder: "Search a business term, document, or reference...",
    hybridRagSearchButtonLabel: "Search",
    tripartiteTitle: "Links between Documentation, Activity Tracking and Deliverables",
    staleAlertsTitle: "Document Freshness Monitoring",
    docObsoleteBadgeLabel: "Update recommended",
  },
  modulePages: {
    cockpit: {
      subtitle: "Your dashboard for priority decisions and actions",
      description:
        "Monitor active processes, write required framing inputs, and resolve pending decisions.",
      uriBadgeExample: "Cockpit",
    },
    inbox: {
      subtitle: "Your conversational assistant grounded in your sources",
      description:
        "Ask questions, organize topic folders, and draft deliverables with verified citations.",
      uriBadgeExample: "My Assistant",
    },
    catalog: {
      subtitle: "Directory of agents, skills, and connected services",
      description:
        "Browse, test, and configure specialized agents and tools available to your workspaces.",
      uriBadgeExample: "Agents & Skills",
    },
    ontology: {
      subtitle: "Shared business glossary and knowledge base",
      description:
        "Manage your organization's business terms and monitor the freshness of reference documents.",
      uriBadgeExample: "Knowledge",
    },
    gates: {
      subtitle: "Process design and review checkpoint tracking",
      description:
        "Build business processes, verify quality checks, and review deliverables step by step.",
      uriBadgeExample: "Processes",
    },
    finops: {
      subtitle: "Usage cost tracking and activity log",
      description:
        "Track usage by workspace and step, and review the complete history of validated decisions.",
      uriBadgeExample: "Costs & Activity",
    },
    admin: {
      subtitle: "Manage your workspaces, sources, and business rules",
      description:
        "Organize workspaces, connect document sources, and manage your team glossary and rules.",
      uriBadgeExample: "My Spaces",
    },
    bootstrap: {
      subtitle: "Guided initial setup workflows",
      description:
        "Configure your organization, initial workspaces, and tool connections step by step.",
      uriBadgeExample: "Setup",
    },
  },
  upstreamChallengeModal: {
    modalTitle: "Request a Correction on a Previous Step",
    modalSubtitle:
      "Point out what needs adjustment in an earlier step, preview which subsequent steps are affected, and restart only what needs updating.",
    targetStepLabel: "Previous step concerned",
    sectionKeyLabel: "Section or rule to adjust",
    reasonLabel: "Reason for the correction request (at least 10 characters)",
    reasonPlaceholder: "Explain the discrepancy or clarification needed on the previous step...",
    whatIfTitle: "Preview of items that will be updated",
    invalidatedStepsLabel: "Subsequent steps to recalculate",
    invalidatedSectionsLabel: "Impacted deliverable sections",
    invalidatedAxiomsLabel: "Related business rules",
    preservedStepsLabel: "Earlier steps preserved without reprocessing",
    translatedSummaryLabel: "Adapted explanation for the previous step owner",
    submitChallengeCta: "Send correction request",
    replayStepCta: "Restart from this step",
    closeCta: "Close",
    challengeSubmittedFeedback: "Correction request sent to the step owner ✓",
    replayTriggeredFeedback: "Restart completed from the selected step ✓",
  },
  humanGates: {
    briefing: {
      gridTitle: "Pre-Approval Review Summary (4 Key Points)",
      block1Title: "1. Executive Summary",
      block2Title: "2. Key Points & Cross-Checks",
      block3Title: "3. Proposed Decisions",
      block4Title: "4. Retained Assumptions",
      inspectHypothesesButtonLabel: "Confirm reading of assumptions",
      hypothesesInspectedBadgeLabel: "Assumptions reviewed",
      hypothesesPendingBadgeLabel: "Review required (Point 4)",
    },
    chunkValidation: {
      sectionListTitle: "Section-by-Section Review",
      keyboardNavHint: "Keyboard shortcut: Alt + ↑ / ↓",
      approveSectionLabel: "Approve section",
      coEditSectionLabel: "Edit section",
      challengeSectionLabel: "Request upstream correction",
      finalizeGateButtonLabel: "Confirm final approval",
      pendingSectionsNotice:
        "Every required section as well as Point 4 (Retained Assumptions) must be checked before final approval.",
      guardModalTitle: "Careful Review Confirmation",
      guardModalDescription:
        "You approved this document very quickly. Please confirm that you have carefully reviewed the retained assumptions.",
      guardConfirmCheckboxLabel:
        "I confirm I have reviewed the retained assumptions and key sections",
      guardConfirmButtonLabel: "Confirm and record my approval",
      guardCancelButtonLabel: "Resume reading",
    },
  },
  inboxAndClaims: {
    filterAllLabel: "All requests",
    filterPersonalLabel: "Assigned to me",
    filterTeamLabel: "For my team",
    amberCounterPrefix: "Pending actions:",
    contributorSectionTitle: "Actions Required from You",
    observerSectionTitle: "Following — Read-Only",
    observerBannerText:
      "👁️ Read-Only Mode — You are following this execution without edit permissions",
    presencePill: {
      claimActionLabel: "Take ownership",
      claimedByMeBadge: "🔒 Handled by you",
      claimedByPeerPrefix: "🔒 Handled by:",
      releaseActionLabel: "Release",
      forceUnclaimActionLabel: "Take over (after 15 min)",
      readOnlyObserverNotice: "Read-only",
      sseLatencyPrefix: "Sync:",
    },
  },
};
