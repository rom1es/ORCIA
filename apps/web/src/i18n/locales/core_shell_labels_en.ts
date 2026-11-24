import type { TranslationDictionary } from "../types";

export const CORE_SHELL_EN_LABELS: Pick<
  TranslationDictionary,
  "shell" | "humanAnchor" | "arbitrationTieBreak" | "modulePages"
> = {
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
    placeholderText:
      "Enter your guiding directions and key assumptions (personal authoring required)...",
    submitLabel: "Confirm and sign my entry",
    defaultSectionTitle: "Business Intent & Guidelines",
    defaultAuthorName: "Lead Owner",
    defaultValue: "Definition of priority goals and expected acceptance criteria.",
  },
  arbitrationTieBreak: {
    badgeTitle: "⚖️ DECISION REQUIRED",
    policyPrefixLabel: "Decision rule",
    policyLabels: {
      pauseAndEscalate: "Pause and escalate to human",
      ontologyAxiomFirst: "Business rule priority",
      deferWithAssumption: "Proceed with assumption",
    },
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
      uriBadgeExample: "Administration",
    },
  },
};
