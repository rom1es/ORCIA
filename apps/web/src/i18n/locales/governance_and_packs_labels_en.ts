import { AGENT_GOVERNANCE_STUDIO_LABELS_EN } from "./agents_and_skills_studio_labels_en";
import type { GovernanceAndPacksDictionarySection } from "./governance_and_packs_labels";

export const GOVERNANCE_AND_PACKS_EN_LABELS: GovernanceAndPacksDictionarySection = {
  workspaceFiveTabs: {
    heading: "📦 My Spaces — Sources, Deliverables, Glossary & Team",
    tabOverview: "1. Overview",
    tabDocumentsSources: "2. Documents & Sources",
    tabDeliverablesArtifacts: "3. Deliverables & Produced Documents",
    tabGlossaryRules: "4. Glossary & Business Rules",
    tabMembersTeam: "5. Members & Team",
    defaultDestinationTitle: "Default save location for deliverables:",
    roleReferenceBadge: "📚 REFERENCE (Official document)",
    roleActiveBadge: "✏️ WORK IN PROGRESS",
    modeReadOnlyBadge: "👁️ Read-only",
    modeReadWriteBadge: "✍️ Publishing allowed",
    waiverSectionTitle: "Local Adaptations and Exceptions",
    inviolableEnterpriseLockNotice:
      "🔒 Organization-wide rules apply to all workspaces and cannot be bypassed locally.",
    externalRebaseTitle: "Syncing Direct Edits Made to Your Documents",
    humanAmendedBadge:
      "✍️ Edited directly by a team member — Protected against automatic overwrite",
    supersededMemlogNotice:
      "Previous drafts have been archived in favor of the latest validated edit.",
    registerWaiverCta: "+ Request a local adaptation for this space",
    overviewSummaryText:
      "Overview of connected sources, business rules, deliverables, and active local adaptations for this space.",
    overviewEmptyStateHint:
      "This workspace is ready: connect a first document in Documents & Sources or define business rules in the Glossary.",
    teamBillingLabel: "Billing team",
    visibilityLabel: "Visibility",
    roleLabel: "Effective role",
    phaseLabel: "Active phase",
    emptyDeliverablesText:
      "No deliverable edited directly yet. Outputs are saved to the default target location.",
    emptyGlossaryRulesText:
      "No local adaptation active yet on glossary rules.",
    membersAccessHint:
      "Team invitations and workspace access permissions are managed from My Organization and workspace settings.",
  },
  dnaStarlarkGlossary: {
    heading: "🧬 Automated Business Rules & Glossary Terms to Review",
    generateStarlarkCta: "⚙ Generate automated check",
    signAndActivateCta: "✍️ Confirm and activate rule",
    runtimeZeroTokenBadge:
      "⚡ Instant verification without calling an AI model",
    queueSectionTitle:
      "✨ Suggested new terms and rules (up to 15 pending)",
    inFlowBriefingTitle: "Quick Glossary Addition During Review",
    promoteInFlowCheckboxLabel: "Add to the official Space glossary",
    promoteSelectedCta: "✓ Approve selected",
    rejectCandidateCta: "✕ Dismiss",
    emptyCompiledControlText:
      "No automated check compiled for this Space yet. Add a business rule to automatically generate and verify this check.",
  },
  remoteServiceTestBench: {
    heading: "🔌 External Tool Connection Testing & Code Editor Access",
    testAndDiscoverCta: "🔌 Test connection and discover actions",
    testingInProgressCta: "⏳ Checking connection…",
    testingInProgressNotice:
      "⏳ Checking remote service connectivity and recording audit trace…",
    activateConnectorCta: "✓ Enable this service in the Space",
    activateDisabledReason:
      "Complete the 4 test bench verification steps to enable this connector.",
    testWithPersonalTokenCta: "🔑 Test with my personal account",
    mcpExposureHeading: "External Code Editor Access",
    exposeMcpToggleLabel:
      "Allow usage from an external code editor (Cursor, VS Code, Claude Desktop)",
    mcpIdeBadge: "🔌 Secure editor access · separate read and execute permissions",
    ipProtectionNotice:
      "🔒 Confidentiality: Internal process settings and verification rules remain protected.",
    stepLabels: {
      "1_NETWORK_TLS_ANTI_SSRF": "Network, TLS & Address Guard",
      "2_AUTHENTICATION": "Authentication & Access Control",
      "3_CONTRACT_DISCOVERY": "Actions & Contract Discovery",
      "4_HOT_DRY_RUN": "Hot Dry-Run Verification",
    },
    statusLabels: {
      PASS: "Passed",
      FAIL: "Failed",
      WAITING_USER_PASSTHROUGH_TOKEN: "Waiting for personal token",
      SKIPPED: "Skipped",
    },
  },
  packBuilderStudio: {
    studioTitle: "🏗️ Business Pack Creation and Evolution",
    agentsSectionTitle: "Pack Design Assistants",
    humanAnchorSectionTitle:
      "Step 1 — Define Business Pack Goals (Personal Authoring)",
    humanAnchorPlaceholder:
      "Describe the business goal, target domain, and key rules for this Pack (at least 30 characters)...",
    process1CreatePackButtonLabel: "1. Create Business Pack",
    process2WhatIfTitle: "2. New Version Impact Preview",
    runLocksPreservedBadgeLabel:
      "🔒 In-progress executions keep their current version without interruption",
    process3CertifyTitle: "3. Compliance and Security Verification",
    certifiedBadgeLabel: "✅ VERIFIED AND READY TO PUBLISH",
    process4PromoteButtonLabel:
      "4. Turn this Space's settings into a reusable Pack",
    durationMsUnit: "ms",
  },
  helpArticleGenerator: {
    heading: "❓ Authoring and Updating Contextual Help Articles",
    triggerRegimeLabel: "Publishing mode:",
    stagedRegimeBadge: "👤 Review before publishing",
    autonomousRegimeBadge: "⚡ Publish directly after checks",
    validationChecksHeading: "Automated quality checks",
    checkBoundRoutesLabel: "Valid target screens and section anchors",
    checkUiComponentsSectionsLabel: "Complete structure with 3 clear sections",
    checkGlossaryZeroSecretLabel:
      "Vocabulary aligned with glossary and zero confidential data", // pragma: allowlist secret
    passedBadge: "PASSED",
    failedBadge: "NEEDS FIX",
    hotAttachmentHeading: "Immediate Publishing to Contextual Help",
    authorityReferenceBadge: "📚 Official reference guide",
    generateAndAttachCta: "⚡ Generate, verify, and publish help guide",
    durationMsUnit: "ms",
  },
  agentsAndSkillsManager: {
    heading: "🤖 My Agents & Skills",
    subtitle:
      "Create reusable business skills, attach them in 1 click to your specialized agents, and execute them immediately on concrete tasks.",
    tabAgents: "🤖 My Agents",
    tabSkills: "🛠️ Skills",
    tabConnections: "🔌 Tool Servers & MCP",
    emptyAgentsTitle: "No agent configured yet",
    emptyAgentsDescription:
      "Create your first agent above to attach skills and run it in 1 click.",
    emptySkillsTitle: "No skills saved yet",
    emptySkillsDescription:
      "Create your first skill above to test it or attach it to your agents.",
    createAgentSectionTitle: "Create a specialized Agent",
    agentNameLabel: "Agent name",
    agentNamePlaceholder: "e.g., Supplier Risk Analyst",
    agentRoleLabel: "Business role & mission",
    agentRolePlaceholder:
      "e.g., Evaluate compliance and contractual risks in supplier files",
    agentInstructionsLabel: "Working instructions",
    agentInstructionsPlaceholder:
      "Specify the posture, analysis steps, and expected quality criteria...",
    agentThinkingLevelLabel: "Default thinking depth",
    thinkingLevels: {
      simple: "⚡ Fast (Direct tasks)",
      medium: "⚖️ Balanced (Standard analysis)",
      complex: "🧠 Deep (Complex trade-offs)",
      auto: "✨ Automatic (Adaptive)",
    },
    attachedSkillsLabel: "Attached Skills",
    noSkillsAvailableHint:
      "No skills created yet. Open the '🛠️ Skills' tab to create your first reusable skill.",
    createAgentButtonLabel: "+ Save Agent",
    testAgentInputPlaceholder:
      "Enter a concrete request to assign to this agent...",
    runAgentButtonLabel: "▶ Run Agent",
    deleteAgentButtonLabel: "Delete",
    mobilizedSkillsLabel: "Mobilized skills",
    createSkillSectionTitle: "Create a reusable Skill",
    skillUsageBanner:
      "💡 A Skill is a modular business capability. Once saved, you can attach it in 1 click to one or more Agents, or invoke it directly in My Assistant and your Processes.",
    skillNameLabel: "Skill name",
    skillNamePlaceholder: "e.g., Supplier compliance summary",
    skillObjectiveLabel: "Business goal (When to use this skill?)",
    skillObjectivePlaceholder:
      "e.g., Check critical contract clauses and highlight deviations...",
    skillParamsLabel: "Expected input parameters (comma-separated)",
    skillParamsPlaceholder: "e.g., contract, special_terms",
    skillInstructionsLabel: "Execution method & instructions",
    skillInstructionsPlaceholder:
      "Describe step by step how to process the input and which rules to verify...",
    skillOutputFormatLabel: "Expected output format",
    skillOutputFormatPlaceholder:
      "e.g., Risk summary table + Go / No-Go recommendation",
    createSkillButtonLabel: "+ Save Skill",
    testSkillInputPlaceholder: "Enter a sample input to test this skill...",
    runSkillButtonLabel: "▶ Test Skill",
    deleteSkillButtonLabel: "Delete",
    studio: AGENT_GOVERNANCE_STUDIO_LABELS_EN,
  },
};
