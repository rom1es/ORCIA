import type { UiContextualHelpSectionItem } from "@orcia/ui";

const WORKFLOW_SECTIONS_EN: readonly UiContextualHelpSectionItem[] = [
  {
    sectionId: "workflows-overview",
    title: "What is the Process Studio for?",
    body: "A Process is a reusable sequence of steps combining your AI agents and human approval checkpoints to produce a reliable deliverable (e.g. contract review, customer request analysis). Save it as a draft and publish it when ready to run.",
    category: "steps",
  },
  {
    sectionId: "workflows-instructions",
    title: "How to write the process goal and instructions?",
    body: "Describe in plain language what your agents should accomplish step by step: which sources to consult, which points of attention to verify, and what tone to use in the summary.",
    category: "steps",
  },
  {
    sectionId: "workflows-deliverable-contract",
    title: "Launch inputs and deliverable structure (optional)",
    body: "Specify the inputs requested from the user when launching the process (e.g. supplier name, amount) as well as the main headings required in the final deliverable.",
    category: "terms",
  },
  {
    sectionId: "workflows-steps-layers",
    title: "The 3 main execution steps of a process",
    body: "Each process runs in 3 stages: 1) Gather documents and Workspace context, 2) AI agent analysis and cross-checking of business rules, 3) Final human approval before sharing the deliverable.",
    category: "steps",
  },
  {
    sectionId: "autonomy-contract",
    title: "Governed autonomy contract",
    body: "An autonomy contract authorizes a non-critical process to run end-to-end through a workspace-scoped service account, bounded by a budget ceiling and automatic team escalation whenever any quality check or ambiguity arises.",
    category: "terms",
  },
  {
    sectionId: "autonomous-supervision",
    title: "Supervision, emergency stop & restore",
    body: "Every automated execution under contract is marked by a distinct cyan badge. If needed, you can trigger an immediate emergency stop or cancel and restore the previous version of a deliverable or help guide in one click.",
    category: "terms",
  },
  {
    sectionId: "workflow-triggers",
    title: "Automated triggers and scheduled runs",
    body: "Configure the events or schedules that automatically start a governed process (incoming request, document update, periodic review) within your approved budget limits.",
    category: "steps",
  },
  {
    sectionId: "orcia-doc-generation-process",
    title: "Help documentation generation and sync",
    body: "This process refreshes screen help guides and publishes them to your Help Center without overwriting validated customizations.",
    category: "steps",
  },
];

export const CONFIGURATION_SECTIONS_EN: readonly UiContextualHelpSectionItem[] = [
  {
    sectionId: "iam-org-tree",
    title: "Organization structure (Divisions / BUs & Teams)",
    body: "Structure your company into Divisions (BUs) and Teams. Project/product Workspaces are managed separately in 📦 My Workspaces. An organization unit can only be deleted once no child teams or access rules depend on it.",
    category: "steps",
  },
  {
    sectionId: "iam-role-grants",
    title: "Access rules: Who? and On what?",
    body: "Each rule links a beneficiary (Role or User, e.g. Role: Product Manager) to a target scope (Entire platform, BU, Team, or Workspace, e.g. Payments Team) and specifies granted permissions (Create, Read & view resources, Update, Delete, Execute / Use, Delegate rights). Secrets are strictly write-only and never readable.",
    category: "terms",
  },
  {
    sectionId: "iam-target-scope",
    title: "What is Target scope ('On what?')?",
    body: "The target scope identifies the exact level of your organization where the permission rule applies: either the entire platform, a whole Division (BU) and its teams, a Team, or a single Workspace. For instance, granting a permission to 'Product Manager' on target scope 'Team: Payments' means that right only applies inside the Payments team.",
    category: "terms",
  },
  {
    sectionId: "iam-inheritance-block",
    title: "Rule effect (Allow, Deny, Isolate this scope)",
    body: "'Allow' grants the selected actions. 'Deny' always takes priority. 'Isolate this scope' stops broad permissions inherited from a parent BU on a confidential team or workspace.",
    category: "terms",
  },
  {
    sectionId: "connectors-overview",
    title: "Connecting your tools and document sources",
    body: "Register your documentation spaces, project trackers, or code repositories. Access keys are protected upon saving and never displayed in plain text again.",
    category: "steps",
  },
  {
    sectionId: "ai-models-overview",
    title: "AI Models: Provider, API URL, Authentication & Connection Test",
    body: "For each usage level (Simple, Standard, In-Depth), specify: 1) AI Provider (e.g. Anthropic, OpenAI, Mistral AI, local Ollama), 2) primary model ID (and optional backup model), 3) API Endpoint URL, and 4) authentication mode. Click '🔌 Test model connection' before saving to verify server response.",
    category: "steps",
  },
  {
    sectionId: "packs-overview",
    title: "Ready-to-use Business Packs",
    body: "Business Packs are provided by the platform (or authored in My Processes) and bundle processes, specialized agents, and a domain glossary. Select a target scope (Entire Platform, Division, or Workspace) and enable or disable a Pack in 1 click.",
    category: "terms",
  },
];

export const SECTIONS_BY_ROUTE_EN: Readonly<Record<string, readonly UiContextualHelpSectionItem[]>> = {
  "/cockpit": [
    {
      sectionId: "cockpit-decisions",
      title: "Pending decisions and reviews",
      body: "The Cockpit gathers only items requiring your input: personal authoring entries, quick choices between two options, or detailed deliverable reviews.",
      category: "steps",
    },
    {
      sectionId: "module-overview",
      title: "Cockpit overview",
      body: "Track platform onboarding milestones, resolve pending decisions, or start a governed process.",
      category: "whatFor",
    },
  ],
  "/assistant": [
    {
      sectionId: "assistant-modes",
      title: "AI model and thinking mode (Standard or In-Depth)",
      body: "Pick your model (Fast, Versatile, or Advanced Reasoning) and switch between 'Standard' (direct grounded reply, e.g. 'Versatile · Standard') and 'In-Depth' (multi-step reasoning with verified citations).",
      category: "steps",
    },
    {
      sectionId: "assistant-folders",
      title: "Thematic folders and permanent notes in My Assistant",
      body: "Organize discussions by topic in a folder and pin permanent instructions so they are automatically applied to every question you ask inside that folder.",
      category: "steps",
    },
  ],
  "/inbox": [
    {
      sectionId: "inbox-claims",
      title: "Task claims and team coordination",
      body: "Claim an available request to signal to your team that you are handling it, and release it anytime if a teammate needs to take over.",
      category: "steps",
    },
    {
      sectionId: "inbox-vs-activity",
      title: "Inbox vs Activity Log",
      body: "The Inbox displays only operational notifications and pending tasks for your active Space; the Activity Log keeps the full history of past actions.",
      category: "terms",
    },
  ],
  "/spaces": [
    {
      sectionId: "workspace-sources",
      title: "Reference sources and organizational units",
      body: "Each Workspace is linked to an organizational unit (Division or Team) and isolates its document sources and default deliverable output targets.",
      category: "terms",
    },
    {
      sectionId: "glossary-rules",
      title: "Workspace business glossary",
      body: "Define your team's key terms and turn business rules into automated checks executed at every step.",
      category: "terms",
    },
  ],
  "/processes": WORKFLOW_SECTIONS_EN,
  "/gates": [
    {
      sectionId: "orcia-doc-generation-process",
      title: "Help documentation generation and sync",
      body: "This process refreshes screen help guides and publishes them to your Help Center without overwriting validated customizations.",
      category: "steps",
    },
    {
      sectionId: "autonomous-supervision",
      title: "Supervision, emergency stop & restore",
      body: "Every automated execution under contract is marked by a distinct cyan badge. Trigger an emergency stop or restore the previous version if needed.",
      category: "terms",
    },
  ],
  "/agents": [
    {
      sectionId: "connectors-overview",
      title: "Specialized agents and tool connections",
      body: "Browse available agents and test authorized connectors on your active scope.",
      category: "steps",
    },
  ],
  "/catalog": [
    {
      sectionId: "showcase-packs",
      title: "Catalog of packs, templates, and agents",
      body: "Browse business packs, process templates, and agents available on the platform.",
      category: "terms",
    },
  ],
  "/finops": [
    {
      sectionId: "finops-overview",
      title: "Cost governance and budget thresholds",
      body: "Track the complete economic equation of your processes: amortized initial setup cost, execution run cost across AI model levels, and 80%/100% budget thresholds.",
      category: "whatFor",
    },
    {
      sectionId: "finops-human-mastery",
      title: "Human mastery, quality, and architecture reversibility",
      body: "Preserve active expert critical thinking and compliance with locked architectural decisions.",
      category: "whatFor",
    },
    {
      sectionId: "finops-remote-services",
      title: "External services & agents telemetry",
      body: "Track reported external tool and agent costs and isolated connector circuit breaker states separately from internal models.",
      category: "terms",
    },
    {
      sectionId: "autonomous-supervision",
      title: "Autonomous execution supervision",
      body: "Audit contract-backed autonomous runs and restore a previous version in one click if needed.",
      category: "terms",
    },
  ],
  "/activity": [
    {
      sectionId: "audit-overview",
      title: "Activity log: authors, timestamps, and observation filters",
      body: "The Activity Log tracks who performed each action, when, and on which scope (filtered by default to your active observation level). Cost tracking and workspace budgets are managed separately in FinOps.",
      category: "faq",
    },
  ],
  "/ontology": [
    {
      sectionId: "glossary-rules",
      title: "Business glossary and automated rules",
      body: "Define your team's key terms and turn business rules into automated checks executed at every step.",
      category: "terms",
    },
  ],
  "/settings": CONFIGURATION_SECTIONS_EN,
  "/settings/packs": [...CONFIGURATION_SECTIONS_EN, ...WORKFLOW_SECTIONS_EN],
  "/showcase": [
    {
      sectionId: "showcase-overview",
      title: "ORCIA living showcase",
      body: "Explore the Human-Led vision, delivered capabilities, and architecture decisions.",
      category: "whatFor",
    },
    {
      sectionId: "showcase-packs",
      title: "Installed business packs on the platform",
      body: "Business packs bundle ready-to-use processes, specialized agents, and a domain glossary tailored to an operational area.",
      category: "terms",
    },
  ],
};
