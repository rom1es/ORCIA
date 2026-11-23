import type { FeatureCockpitGatesDictionary } from "./feature_cockpit_gates_labels";

export const FEATURE_COCKPIT_GATES_EN: FeatureCockpitGatesDictionary = {
  cockpit: {
    workflowPreviewNodes: {
      intentRouter: "1. Intent Router",
      queryPlanner: "2. Query Planner & Ontology",
      parallelFanOut: "3. Parallel Fan-Out",
      criticalTriage: "4. Critical Triage & Axioms",
      profileSynthesizer: "5. Profile Adaptive Synthesizer",
    },
    runsSection: {
      emptyTitle: "No Workspace or active process yet",
      emptyDescription:
        "Create your first Workspace to run processes, use My Assistant, and track your reviews.",
      createWorkspaceCta: "+ Create a Workspace",
      assistantOptionLabel: "ORCIA Assistant",
      runTitlePlaceholder: "Execution title...",
      startProcessBtn: "Start process",
    },
    stepStatus: {
      pending: "Pending",
      running: "Running",
      completed: "Completed",
      staleNeedsReview: "Needs review",
      waitingHumanAnchor: "Human anchor required",
      waitingHumanArbitration: "Arbitration required",
      pausedHumanGate: "Human review required",
    },
    stepKeyLabels: {
      "frame-architecture-intent": "Architecture intent framing",
      "delegate-remediation-subworkflow": "Remediation sub-process",
      "post-deploy-verification": "Post-deployment verification",
      "step-architecture-gate": "Architecture review gate",
      "inbox-review-step": "Inbox review step",
    },
    upstreamChallenge: {
      defaultSummary:
        "Impact simulation: targeted re-evaluation from architecture intent without re-consuming upstream steps.",
      defaultPreviewReason:
        "The upstream business rule contradicts partner API v3 contract (15-min max window).",
      staleReplayTemplate:
        'Stale notice: targeted replay executed from "{stepKey}" — linked downstream artifacts flagged for revalidation.',
      openModalBtn: "Open impact simulation modal",
      defaultStaleBanner:
        "Stale notice: upstream replay detected — linked downstream artifacts are flagged for revalidation.",
    },
    onboardingChecklist: {
      title: "Platform Getting Started Checklist",
      subtitle:
        "Complete each step from the dedicated settings screens or launch a step-by-step guided assistant.",
      guidedAssistantsBtn: "Guided Assistants",
      statusConfigured: "Configured",
      statusToConfigure: "To configure",
    },
  },
  gates: {
    panel: {
      activeScopeLabel: "Active review scope:",
      emptyTitle: "No review checkpoint currently awaiting approval",
      emptyDescription:
        "Automated checks, cross-checked reviews, and human approval steps appear here during process runs.",
      openProcessesBtn: "Open My Processes",
    },
    headerCard: {
      title: "Adaptive Human Review (4-Point Summary & Section-by-Section Review)",
      gatePrefix: "Gate",
      statusPendingReview: "Pending human review",
      statusPassed: "Passed",
      jiraStaged: "Prepared (pending)",
      jiraExecuted: "Executed",
      prepareReviewBtn: "Prepare Human Review (4 blocks + Jira)",
    },
    humanReview: {
      defaultExecutiveSummary: "Executive summary of the step awaiting human review.",
      step1AlignmentTemplate: "Step 1 Alignment: {status}",
      alignmentAligned: "Aligned",
      alignmentConflict: "Conflict",
      totalVolumeTemplate: "Total volume: {count} words",
      loadErrorFallback: "Gate load error",
      loadErrorBannerTemplate: "⚠️ Unable to load human gate reviews ({msg}).",
      openReviewSuccess: "✅ 4-block review briefing and section chunks ready for validation.",
      openReviewErrorFallback: "Review open error",
      inspectHypothesesSuccess: "✅ Block 4 (Retained Assumptions) marked as inspected.",
      inspectHypothesesErrorFallback: "Inspection error",
      chunkStatusLabels: {
        APPROVED: "Approved",
        CO_EDITED: "Co-edited",
        CHALLENGED: "Challenged",
        PENDING: "Pending",
      },
      chunkUpdatedTemplate: "✅ Section updated ({status}).",
      chunkErrorFallback: "Section error",
      finalizeSuccess: "✅ Human review approved and staged Jira action executed.",
      finalizeErrorFallback: "Gate finalization error",
      defaultChallengeReason: "Clarification requested on upstream alignment.",
      seedPhrase:
        "Cross-checked architectural compliance verification, snapshot lock traceability, and L1-L4 ontology axiom validation.",
      seedDecisions: [
        "Service contract validation and secure persistence.",
        "Deferred execution of Jira transitions after human approval.",
      ],
      seedHypotheses: [
        "H1: PAYBUILD-101 Jira transitions stay pending until final approval.",
        "H2: Review fingerprint covers any human section modification.",
      ],
      seedSec1Title: "Section 1 — Architecture & Hexagonal Boundaries",
      seedSec1Prefix: "Section 1: Modular architecture and port separation",
      seedSec2Title: "Section 2 — Security & Pre-Validated Jira Actions",
      seedSec2Prefix: "Section 2: Access control and conditional Jira execution",
      seedJiraSummary: "Submit PAYBUILD-101 for review upon human gate approval",
    },
    challengeModal: {
      defaultSummary:
        "Impact simulation: targeted re-evaluation of the challenged section without reprocessing validated upstream steps.",
      challengeSubmittedBanner: "⚠️ Upstream challenge recorded and dispatched for revision.",
      replayBannerTemplate: 'Stale notice: replay triggered from "{stepKey}".',
      errorContextLabel: "Process replay",
    },
    docProcess: {
      cardTitle: "📚 ORCIA Pack Process — ORCIA Documentation Generation",
      cardDescription:
        "Generates, verifies, and updates functional screen guides (FR/EN), the architecture FAQ, and the ORCIA documentation site in 4 steps.",
      badgeLabel: "📦 ORCIA Documentation Pack · Agent: @Rédacteur-Documentation-Orcia",
      runBtn: "▶️ Run ORCIA documentation generation",
      loadInBuilderBtn: "✏️ Load in Process Studio",
      stepsSummaryTitle: "Summary of the 4 executed steps:",
      stepCompletedBadge: "✓ Completed",
      publishSuccessBanner:
        '✅ Process "ORCIA Documentation Generation" published and executed in 4 steps.',
      localValidationFallback: "Local validation applied",
      publishWithDetailTemplate:
        '✅ Process "ORCIA Documentation Generation" executed in 4 steps ({detail}).',
      loadedInBuilderBanner:
        '✏️ Template "ORCIA Documentation Generation" loaded into the Process Studio for customization.',
      steps: [
        {
          stepNumber: 1,
          title: "Step 1 — ORCIA Repository Inventory",
          agentHandle: "@Rédacteur-Documentation-Orcia",
          summary:
            "20 UI screens, 16 UI primitives, bilingual help guides, architecture FAQ, and technical reports inventoried.",
        },
        {
          stepNumber: 2,
          title: "Step 2 — Screen Guides & Architecture FAQ Generation",
          agentHandle: "@Rédacteur-Documentation-Orcia & @Architecte-Métier-Pack",
          summary:
            "Mandatory sections structured: Objective, Functional Screen Guide, Architecture & Domain Model, Frequently Asked Questions (FAQ).",
        },
        {
          stepNumber: 3,
          title: "Step 3 — Deterministic Quality Check (validate_help_article)",
          agentHandle: "@Certificateur-Sécurité-et-Sandbox",
          summary:
            "Bound routes verified, mandatory sections present, and zero secrets or internal jargon confirmed.",
        },
        {
          stepNumber: 4,
          title: "Step 4 — Hot Attachment & Publication (/showcase & docs/help/)",
          agentHandle: "@Rédacteur-Documentation-Orcia",
          summary:
            "Full summary of generated/verified documents published to bilingual help guides and synchronized with the showcase.",
        },
      ],
      workflowTitle:
        "Process 6 — Generate and Synchronize Full ORCIA Documentation (Screen Guides, Architecture FAQ & Catalog)",
      workflowPrePrompt:
        "Inventory ORCIA screens and routes, author and synchronize bilingual screen guides (FR/EN) and the architecture FAQ, run deterministic quality checks, then publish help articles and the catalog.",
      workflowLayers: [
        {
          layerId: "layer-doc-inventory",
          label: "1. ORCIA repository inventory (20 UI screens, FR/EN guides, FAQ & reports)",
          zone: "inputs",
          orderIndex: 1,
          enabled: true,
        },
        {
          layerId: "layer-doc-authoring",
          label:
            "2. Screen guides & FAQ authoring (@Rédacteur-Documentation-Orcia & @Architecte-Métier-Pack)",
          zone: "capabilities",
          orderIndex: 2,
          enabled: true,
        },
        {
          layerId: "layer-doc-validation",
          label: "3. Deterministic quality check (bound routes, mandatory sections, zero secret or internal jargon)",
          zone: "capabilities",
          orderIndex: 3,
          enabled: true,
        },
        {
          layerId: "layer-doc-publish",
          label: "4. Hot attachment & publication (FR/EN help guides & documentation showcase)",
          zone: "deliverables",
          orderIndex: 4,
          enabled: true,
        },
      ],
      generatedMarkdown: [
        "# ORCIA Complete Documentation — Screen Guides, Architecture & FAQ",
        "",
        "## Objective",
        "Provide a unified, up-to-date reference covering every ORCIA screen, the organizational domain model, and frequently asked questions.",
        "",
        "## Functional Screen Guide",
        "- **Cockpit**: Monitor active processes, pending human decisions, and workspace indicators.",
        "- **My Assistant**: Converse with your AI assistant, select reasoning effort, and organize work into folders.",
        "- **My Spaces**: Manage project sources, business rules, glossary terms, and deliverables.",
        "- **My Agents & My Processes**: Configure specialized agents, skills, and reusable multi-step processes.",
        "- **Administration & Activity Log**: Govern user accounts, authentication, AI models, connectors, packs, and full audit history.",
        "",
        "## Architecture & Business Model",
        "- **Business Units (BU) & Billing Teams**: Teams group members and carry AI consumption budgets.",
        "- **Workspaces**: Every workspace (shared, private, or confidential) is attached to a billing team and inherits organization rules.",
        "",
        "## Frequently Asked Questions (FAQ)",
        "- **What is the difference between a Team and a Workspace?** A Team represents people and budget ownership; a Workspace isolates project documents, glossary terms, and deliverables.",
        "- **How do I refresh contextual help across screens?** Run the « ORCIA Documentation Generation » process from `☍ My Processes`.",
      ].join("\n"),
    },
  },
};
