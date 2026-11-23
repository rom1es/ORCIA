import type { ContextualHelpDictionarySection } from "./contextual_help_labels";
import {
  CONFIGURATION_SECTIONS_EN,
  SECTIONS_BY_ROUTE_EN,
  WORKFLOW_SECTIONS_EN,
} from "./contextual_help_sections_en";

export const CONTEXTUAL_HELP_EN: ContextualHelpDictionarySection = {
  configurationSections: CONFIGURATION_SECTIONS_EN,
  workflowSections: WORKFLOW_SECTIONS_EN,
  sectionsByRoute: SECTIONS_BY_ROUTE_EN,
  settingsArticle: {
    summaryWhatFor:
      "This screen structures your organization (BUs and Teams), manages the accounts directory, and governs permission rules, AI models, and connectors.",
    stepByStepItems: [
      "Manage human and service accounts in the directory, then review the native 7-role matrix.",
      "In SecOps Exceptions & Isolation, specify Who? (Role or Account) and select On what? (Target scope).",
      "In AI Models, configure your chat and document indexing providers and test the connection before saving.",
    ],
    realExampleText:
      "During initial setup, Alice opens Configuration › AI Models, adds her primary provider and an indexing model, tests the connection, then opens My Organization to create the Product Division and Payments Team.",
    commonPitfallsItems: [
      "A secret key disappears after saving: for security, API keys and tokens are strictly write-only and never displayed again.",
      "Cannot delete a Division or Team: remove dependent child Teams or permission rules first.",
    ],
  },
  routeFallbacks: {
    "/cockpit": {
      summaryWhatFor:
        "The Cockpit brings together decisions awaiting your review, quick process launches, and your platform onboarding progress in one place.",
      steps: [
        "Check your active context (Team or Space) at the top of the left sidebar to filter visible decisions.",
        "Follow the onboarding guide if setup steps remain open, or launch a process directly from the action bar.",
        "Handle pending items: write your human framing anchor or resolve option tie-breaks with a short justification.",
      ],
      realExampleText:
        "After an automated compliance check, Nadia opens the Cockpit in the morning, sees a pending choice between two architecture options, writes a one-sentence justification, and confirms: the process immediately resumes to completion.",
      commonPitfallsItems: [
        "The submit button on the violet card stays disabled: verify that your personal authoring text has at least 30 characters.",
        "No workspace available to start a process: create a Workspace first in \"My Spaces\" and link it to a Team.",
      ],
    },
    "/assistant": {
      summaryWhatFor:
        "My Assistant answers questions grounded in your active Workspace documents, cites every verified source, and organizes discussions into folders with permanent notes.",
      steps: [
        "Choose your model (Fast, Versatile, or Advanced Reasoning) and your thinking mode (Standard or In-Depth — e.g. \"Versatile · Standard\") using the selector next to the send button.",
        "Type your question (use @ to mention an agent or / to run a skill) and send.",
        "Open \"Folders\" to attach your conversation to a topic and pin permanent instructions that stay active across questions.",
      ],
      realExampleText:
        "Marc selects the \"Payments Product\" Space, opens the \"2026 Compliance\" folder with its pinned guidelines, and asks for a risk summary: My Assistant responds with clickable citation pills pointing straight to the verified Space documents.",
      commonPitfallsItems: [
        "The prompt input is locked: verify that both a document indexing model and a chat model are configured in Configuration › AI Models.",
        "Folder notes do not seem applied: click \"Save notes\" inside the active folder drawer before sending your next question.",
      ],
    },
    "/inbox": {
      summaryWhatFor:
        "The Inbox gathers claimed tasks, review requests, and team alerts for your active Space so your team coordinates work without duplication.",
      steps: [
        "Check your active Space in the left sidebar to filter the displayed notifications.",
        "Claim an available task so teammates immediately know you are handling it.",
        "Release the task if you need to hand it off, or open the Cockpit directly to finalize the decision.",
      ],
      realExampleText:
        "When a compliance review arrives in the \"Payments Product\" Space, Nadia clicks \"Claim\" in the Inbox: her teammates instantly see the review is in progress, preventing duplicate work.",
      commonPitfallsItems: [
        "No tasks appear in the list: verify that a Space is selected or that a process has emitted a team notification.",
        "Looking for the full historical audit trail: open the Activity Log to inspect past operations.",
      ],
    },
    "/spaces": {
      summaryWhatFor:
        "My Spaces gathers your team, private, or confidential Workspaces, their document sources, rules inherited from your organizational unit, and access to the Business Glossary.",
      steps: [
        "Filter between \"All\", \"Team Spaces\", and \"My Private Spaces\", or create a new Workspace linked to an existing Team.",
        "Open a Workspace to adjust its confidentiality level (Standard, Confidential isolated, or Private) and lifecycle phase.",
        "Use the \"Sources\" tab to connect your documents, or click \"Business Glossary\" to inspect and enrich Space definitions.",
      ],
      realExampleText:
        "The Claims team creates a \"Q4 Partner Audit\" Space linked to Operations, sets it to Confidential isolated so no external user can read it, and connects its dedicated tracking folder.",
      commonPitfallsItems: [
        "Difference between an organizational unit and a Workspace: the organizational unit defines who works and owns the budget; the Workspace holds your sources and deliverables.",
        "Cannot create a team Space: make sure at least one Team exists first in Configuration › My Organization.",
      ],
    },
  },
  defaultSteps: [
    "Verify your active Space or scope in the left sidebar.",
    "Use global search (⌘K) to quickly find documents and processes.",
    "Review the main actions on this screen and ask My Assistant if needed.",
  ],
  routeTitleFallbacks: {
    inbox: "Inbox",
    showcase: "ORCIA Showcase",
    organization: "My Organization",
  },
};
