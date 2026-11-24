import type { ShowcasePublicDictionary } from "./showcase_labels";
import { SHOWCASE_CHANGELOG_EN } from "./showcase_changelog_labels";

export const SHOWCASE_LABELS_EN: ShowcasePublicDictionary = {
  heroTitle: "🌐 ORCIA Living Product & Architecture Showcase Site",
  heroSubtitle:
    "Explore ORCIA across 4 structured spaces: Macro Human-Led Vision, Functional Guide to the 9 Screens, Under-the-Hood Engineering Architecture, and the automatically synchronized Evolution Changelog.",
  heroHelpLabel: "Understand the 4-tab layout of the ORCIA showcase site",
  syncedBadgePrefix: "Synced:",
  exportStandaloneButton: "⬇ Export standalone HTML site",
  exportBannerMessage:
    "Standalone HTML5 export ready: file downloaded for offline browsing.",
  tabsAriaLabel: "ORCIA Showcase Site 4-space navigation",
  tabMacroLabel: "1. Vision & Human-Led Governance (Macro)",
  tabFeaturesLabel: "2. Features & Screens (Functional Guide)",
  tabArchitectureLabel: "3. Architecture & Engineering Choices (Under the Hood)",
  tabChangelogLabelTemplate: "4. 🔄 Evolution Changelog ({count})",
  macro: {
    whyTitle:
      "1.1 Why ORCIA? Orchestrating Processes, Documentary Context, and Specialized Agents under Human Leadership",
    whySubtitle:
      "Move beyond isolated ephemeral chats to build reliable, traceable enterprise deliverables governed by your teams.",
    whyCards: [
      {
        title: "☍ Structured Business Processes",
        description:
          "Your complex workflows progress step by step under clear deliverable contracts, able to pause for human decisions and resume without losing context.",
      },
      {
        title: "📚 Documentary Context & Living Glossary",
        description:
          "Every step relies on the documentary sources bound to your Workspace and your organization's official business glossary, with immediate alerts when a document is outdated.",
      },
      {
        title: "🤖 Governed Specialized Agents",
        description:
          "Specialized agents equipped with targeted skills prepare analyses, verify consistency, and synthesize options while strictly enforcing each team member's access rights.",
      },
    ],
    humanLedTitle:
      "1.2 The Founding 'Human-Led' Principle: Humans in Command, Never Spectators",
    humanLedSubtitle:
      "Four methodological safeguards guarantee that AI prepares and illuminates work without ever stripping human experts of their authority.",
    humanAnchorCard: {
      title:
        "✍️ 1. Mandatory Human-Authored Anchors (Violet visual identity)",
      badge: "Human Exclusive",
      description:
        "Initial intent, strategic objectives, and foundational assumptions belong exclusively to the human author. Highlighted by a dedicated Violet visual identity across the app, these sections can never be authored or altered by an AI agent.",
    },
    antiRubberStampingCard: {
      title: "🛑 2. Zero Mechanical Approval ('Anti-Ghost Validation')",
      badge: "Active Review",
      description:
        "No more 20-page walls of text approved blindly: every step produces a 4-block decision briefing (Summary, Key Elements, Decisions Taken, Assumptions Retained), requires section-by-section validation (Approve / Co-edit / Challenge), and enforces a minimum active reading time.",
    },
    humanArbitrationCard: {
      title:
        "⚖️ 3. Systematic Human Arbitration on Dilemmas or Contradictions",
      badge: "Pause & Options",
      description:
        "When an agent detects a contradiction between two reference documents or faces multiple equivalent options, it is forbidden from inventing an implicit compromise: the process pauses and clearly presents the decision matrix to the human.",
    },
    noWildWritesCard: {
      title: "🛡️ 4. Zero Unapproved Writes to Enterprise Tools",
      badge: "Staged Actions",
      description:
        "No publication or update to your external tools can ever be triggered directly from a quick chat: external actions are always staged pending human approval. And if a colleague later edits a document outside the platform, ORCIA respects and reconciles their human edits without ever overwriting them.",
    },
    doubleBarrierTitle:
      "1.3 The Double Anti-Hallucination & Error-Containment Barrier (Deterministic + Probabilistic)",
    doubleBarrierSubtitle:
      "How ORCIA breaks the snowball effect where an error in Step 1 contaminates the entire downstream process.",
    snowballWarningPrefix:
      "⚠️ The trap of classic AI chains (the snowball effect): ",
    snowballWarningBody:
      "when a first agent makes a slight approximation or cites a non-existent source in Step 1, Step 2 treats it as established truth, and Step 3 builds an entire flawed deliverable on top of it. ORCIA stops this propagation with three successive barriers:",
    deterministicBarrier: {
      badge: "Barrier #1 · 100% Certainty · $0 Cost",
      title: "Deterministic Controls (Instant & Mathematical)",
      items: [
        "Exact verification of deliverable structure and all required sections.",
        "Automatic execution of codified business rules from your organization's glossary.",
        "Immediate detection of any drift against enterprise reference templates.",
        "Mathematical check that every citation ([S1], [G1], [O1]) points to a real, accessible source.",
      ],
    },
    probabilisticBarrier: {
      badge: "Barrier #2 · Independent Judge · 5 Angles",
      title: "Cross-Family Probabilistic Controls (Never Judge and Party)",
      items: [
        "Strict ban on an AI model reviewing its own work: the verifier must belong to a different model family than the author.",
        "Complete purge of intermediate reasoning drafts so only the factual deliverable is judged.",
        "Parallel review across 5 independent angles: Step 1 alignment, claim-by-claim fact checking, edge cases, business/security compliance, and synthesis.",
      ],
    },
    rewindBarrier: {
      badge: "Barrier #3 · Impact Simulation & Targeted Replay",
      title: "Upstream Challenge ('What if we fixed the previous step?')",
      items: [
        "At any point, an expert can challenge an assumption or rule originating from an earlier step.",
        "The simulator previews the exact list of downstream steps and deliverables that will be impacted.",
        "Recalculation restarts strictly from the corrected step while preserving all validated upstream work and full history.",
      ],
    },
    orgPacksTitle:
      "1.4 Real-World Organizational Governance & 1-Click Business Pack Activation",
    orgPacksSubtitle:
      "A natural hierarchy (Entire Platform ➔ Divisions / BUs ➔ Teams ➔ Workspaces) enriched by ready-to-use Business Packs.",
    orgHierarchyCard: {
      title:
        "🏢 Organization Hierarchy: Entire Platform ➔ Divisions (BUs) ➔ Teams",
      description:
        "Enterprise directives apply automatically across the organization, each Division (BU) or Team layers its domain standards, and each Workspace gathers the sources and runs of a specific project or product.",
    },
    packsCard: {
      title: "📦 Ready-to-Use Business Packs & Smart Deduplication",
      description:
        "A Business Pack bundles coherent processes, specialized agents, control rules, and help guides for a given domain. Enable or disable it in 1 click on your chosen scope.",
    },
  },
  features: {
    devicesTitle:
      "Part A — The 6 Concrete Human-Led & Reliability Devices in the Interface",
    devicesSubtitle:
      "Every methodological guarantee translates into a visual component immediately recognizable by teams.",
    device1HumanAnchor: {
      title:
        "1. Human-Led Anchor Card (Violet visual identity reserved for human authoring)",
      badge: "Device 1",
      description:
        "Visually highlights sections that only a human can author and sign (objectives, constraints, autonomy contract). Until the human author enters and signs their intent, the step cannot start.",
    },
    device2Arbitration: {
      title: "2. 1-Click Arbitration Decision Card",
      badge: "Device 2",
      description:
        "Clearly exposes a dilemma or contradiction between two sources by comparing options, impacts, and evidence. The decision-maker resolves it in 1 click or adds a custom directive.",
    },
    device3BriefingGrid: {
      title: "3. 4-Block Review Briefing Grid & Section-by-Section Validation",
      badge: "Device 3",
      description:
        "Summarizes every deliverable into 4 boxes (Summary, Key Elements, Decisions Taken, Assumptions Retained) paired with document chunks where each section is Approved, Co-edited, or Challenged.",
    },
    device4ImpactSimulator: {
      title: "4. Upstream Impact Simulator & Targeted Rewind",
      badge: "Device 4",
      description:
        "Lets you amend a decision made in an earlier step by first previewing all impacted downstream steps, then re-running only the affected branch.",
    },
    device5VerifiedCitations: {
      title:
        "5. Verified Citations ([S1], [G1], [O1]) & Business Glossary (To Validate)",
      badge: "Device 5",
      description:
        "Links every statement to documentary sources ([S1]), glossary terms ([G1]), and tool checks ([O1]). Newly proposed business terms are capped at 15 in the 'To Validate' queue.",
    },
    device6TeamClaim: {
      title:
        "6. Exclusive Team Claim & Observation Levels (Contributor vs Observer)",
      badge: "Device 6",
      description:
        "Prevents two team members from editing the same step simultaneously through a real-time claim badge, and protects supervised scopes in read-only Observer mode.",
    },
    screensTitle: "Part B — The 9 Screens of the ORCIA Menu Explained One by One",
    screensSubtitle:
      "Click 'Open this screen' to navigate directly to the corresponding feature in the application.",
    screens: [
      {
        id: "cockpit",
        title: "1. ◈ Cockpit",
        route: "/cockpit",
        summary:
          "Operational dashboard gathering your pending human decisions, initial setup progress, and quick process launch.",
        keyActions: [
          "Resolve urgent arbitrations in 1 click without leaving the dashboard",
          "Open the focused review workshop for a step with exclusive team claim",
          "Launch a new process run on the active Workspace",
        ],
        openRouteLabel: "Open /cockpit →",
      },
      {
        id: "assistant",
        title: "2. 💬 My Assistant",
        route: "/assistant",
        summary:
          "3-speed conversational workspace organized in shareable thematic folders with verified citations and 4-level customization.",
        keyActions: [
          "Switch between fast reply, agent/skill invocation, and deep reasoning",
          "Verify every claim through [S1], [G1], and [O1] citation pills",
          "Organize and share threads inside Private, Shared, or Workspace folders",
        ],
        openRouteLabel: "Open /assistant →",
      },
      {
        id: "processes",
        title: "3. ☍ My Processes",
        route: "/processes",
        summary:
          "Step-by-step business process builder and tracker, Business Pack studio, and help guide generator.",
        keyActions: [
          "Build a guided process with instructions, deliverable contract, and steps",
          "Assemble and certify a complete Business Pack with impact simulation",
          "Author and hot-attach a contextual help guide to any screen",
        ],
        openRouteLabel: "Open /processes →",
      },
      {
        id: "agents",
        title: "4. 🤖 My Agents",
        route: "/agents",
        summary:
          "Catalog and management of specialized agents, reusable skills, and external service connection test bench.",
        keyActions: [
          "Create a specialized agent and attach business skills in 1 click",
          "Test an agent or skill immediately on a concrete input",
          "Qualify and live-test an external service across 4 safety steps",
        ],
        openRouteLabel: "Open /agents →",
      },
      {
        id: "spaces",
        title: "5. 📦 My Spaces",
        route: "/spaces",
        summary:
          "5-tab workspace control center: executions, documentary sources, business glossary and rules, external reconciliation, and team.",
        keyActions: [
          "Manage the business glossary lifecycle and validate proposed rules (capped at 15 terms)",
          "Inspect and reconcile edits made by humans in external tools",
          "Govern attached documentary sources and acknowledged exceptions",
        ],
        openRouteLabel: "Open /spaces →",
      },
      {
        id: "finops",
        title: "6. 📊 Cost Tracking",
        route: "/finops",
        summary:
          "Transparent budget tracking across divisions, workspaces, processes, and steps, with spending caps and automatic circuit-breakers.",
        keyActions: [
          "Visualize cost breakdown by workspace and execution",
          "Set preventive budget caps per run and per trigger",
          "Explicitly authorize a budget extension when a step is paused",
        ],
        openRouteLabel: "Open /finops →",
      },
      {
        id: "activity",
        title: "7. 📜 Activity Log",
        route: "/activity",
        summary:
          "Timestamped, tamper-evident history of all actions performed on the platform, filtered by default to your active observation scope.",
        keyActions: [
          "Audit who performed which action, at what exact time, and on which scope",
          "Filter by observed scope, author, volume (50 to 500), or time window",
          "Reset in 1 click to your connected session's observation scope",
        ],
        openRouteLabel: "Open /activity →",
      },
      {
        id: "settings",
        title: "8. ⚙ Configuration",
        route: "/settings",
        summary:
          "Unified administration of organization tree, permissions, AI models with connectivity test, connectors, and Business Packs.",
        keyActions: [
          "Structure Divisions (BUs) and Teams, then grant permissions on each target scope",
          "Configure AI model providers and live-test connectivity",
          "Enable or disable Business Packs in 1 click on the platform, a Division, or a Workspace",
        ],
        openRouteLabel: "Open /settings →",
      },
      {
        id: "help",
        title: "9. ❓ Contextual Help (ⓘ) & Global Search (⌘K)",
        route: "/help",
        summary:
          "Contextual help center bound to every screen header via the ⓘ trigger button, shared glossary, and 2-speed instant search (⌘K).",
        keyActions: [
          "Click any ⓘ icon to open and highlight the targeted explanation in the right column",
          "Search instantly (⌘K) across folders, processes, glossary terms, and guides",
          "Restore the previous version of a help guide in 1 click or ask My Assistant about the active screen",
        ],
        openRouteLabel: "Open /help →",
      },
    ],
  },
  changelog: SHOWCASE_CHANGELOG_EN,
};
