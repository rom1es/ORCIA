import type {
  ShellBreadcrumbsAndScopeDictionary,
  ShellNotificationsDictionary,
} from "./shell_notifications_labels";

export const SHELL_NOTIFICATIONS_EN: ShellNotificationsDictionary = {
  tempPassword: {
    badge: "Security required",
    title: "Temporary password active — change required",
    description:
      "Your account is using a temporary password. To secure your access, set a personal password now.",
    cta: "Change my password →",
  },
  llmMissing: {
    badge: "Prerequisite required",
    title: "No AI model configured (My Assistant & My Agents menus locked)",
    description:
      "Register at least one AI provider and model in Configuration to unlock My Assistant, My Agents, and My Processes.",
    cta: "Configure →",
  },
  billingTeamMissing: {
    badge: "Billing Team",
    title: "No billing Team attached (AI calls locked)",
    description:
      "Every AI call must be attached to a billing Team and a Workspace. Create a Team in Configuration › Organization and attach your account.",
    cta: "Create a Team →",
  },
  orgMissing: {
    badge: "Organization",
    title: "Organization structure (Divisions / BUs & Teams) to define",
    description:
      "Create at least one Division (BU) or Team in Configuration to unlock permission rule grants.",
    cta: "Structure →",
  },
  workspaceMissing: {
    badge: "Workspace required",
    title: "No Workspace created (My Processes menu locked)",
    description:
      "Create your first Workspace (team or private attached to a billing Team) in My Spaces to attach document sources and launch processes.",
    cta: "Create Workspace →",
  },
  decisionWaiting: {
    badge: "Decision pending",
    cta: "Open →",
  },
  inboxTask: {
    openBadge: "Action required",
    claimedBadge: "Claimed",
    cta: "Open inbox →",
  },
  autonomous: {
    escalationBadge: "Autonomous escalation",
    triggerPausedBadge: "Trigger paused",
    qualitySampleBadge: "Quality sample",
    sampleDescriptionTemplate: "Run selected for quality sampling review ({triggerLabel}).",
    attentionDescriptionTemplate: "Automated run requiring attention ({triggerLabel}).",
    reviewCta: "Review →",
    nominalBadge: "Automated under contract",
    inspectCta: "Inspect →",
  },
  livePresence: {
    badge: "Live presence",
    claimedTitleTemplate: "Step claimed ({stepExecutionId})",
    releasedTitleTemplate: "Step released ({stepExecutionId})",
    cta: "View →",
  },
};

export const SHELL_BREADCRUMBS_AND_SCOPE_EN: ShellBreadcrumbsAndScopeDictionary = {
  breadcrumbs: {
    inbox: "Inbox",
    studio: "Studio",
    valueStream: "Value Stream",
    runReview: "Run Review",
    qualityGates: "Quality Gates",
    catalog: "Catalog",
    glossary: "Glossary",
    sources: "Sources",
    activityLog: "Activity Log",
    organization: "My Organization",
    guidedWizards: "Guided Wizards",
    profile: "Profile",
    showcase: "ORCIA Showcase",
    redundantAllSpacesLabels: ["All spaces", "All my spaces"],
  },
  accostageMilestones: {
    firstAdmin: "1. Admin Account",
    aiModels: "2. AI Models",
    organization: "3. Organization",
    firstTeamSpace: "4. First Team Space",
    firstSource: "5. First Source",
    firstProcess: "6. First Process",
    activeLayersTemplate: "{count} active layers",
  },
  disabledMenuReasons: {},
};
