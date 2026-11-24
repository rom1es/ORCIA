import type { CategoryAControllersDictionary } from "./category_a_controller_labels";

export const CATEGORY_A_CONTROLLER_EN_LABELS: CategoryAControllersDictionary = {
  assistantThinking: {
    code: [
      {
        stepCode: "STEP_1_SPEC_EDGE_CASES",
        label: "Specification and edge cases",
        durationMs: 1100,
        intermediateOutput:
          "Framing inputs/outputs, complexity, and edge cases for the request.",
      },
      {
        stepCode: "STEP_2_IMPLEMENTATION_DESIGN",
        label: "Implementation design",
        durationMs: 1400,
        intermediateOutput: "Code structuring and technical choices.",
      },
      {
        stepCode: "STEP_3_VERIFICATION_EXAMPLE",
        label: "Verification and usage example",
        durationMs: 900,
        intermediateOutput: "Validity check and test case preparation.",
      },
    ],
    explain: [
      {
        stepCode: "STEP_1_KEY_POINTS_EXTRACTION",
        label: "Extracting key points",
        durationMs: 1100,
        intermediateOutput: "Identifying main ideas and structure.",
      },
      {
        stepCode: "STEP_2_WORKSPACE_CONTEXT_CROSS",
        label: "Cross-referencing workspace context",
        durationMs: 1300,
        intermediateOutput: "Aligning with glossary and business rules.",
      },
      {
        stepCode: "STEP_3_PEDAGOGICAL_STRUCTURING",
        label: "Pedagogical structuring",
        durationMs: 900,
        intermediateOutput: "Clear organization of the explanation.",
      },
    ],
    compare: [
      {
        stepCode: "STEP_1_EVALUATION_CRITERIA",
        label: "Evaluation criteria",
        durationMs: 1000,
        intermediateOutput: "Defining relevant comparison axes.",
      },
      {
        stepCode: "STEP_2_OPTIONS_AND_RISKS",
        label: "Analyzing options and watchpoints",
        durationMs: 1400,
        intermediateOutput: "Weighing pros and limitations of each option.",
      },
      {
        stepCode: "STEP_3_ARGUED_RECOMMENDATION",
        label: "Reasoned recommendation",
        durationMs: 900,
        intermediateOutput: "Structured decision summary.",
      },
    ],
    fallback: [
      {
        stepCode: "STEP_1_REQUEST_FRAMING",
        label: "Framing the request",
        durationMs: 1000,
        intermediateOutput: "Identifying objectives and scope of the question.",
      },
      {
        stepCode: "STEP_2_DEEP_ANALYSIS_SOURCES",
        label: "In-depth analysis and sources",
        durationMs: 1400,
        intermediateOutput: "Detailed exploration of answer elements and references.",
      },
      {
        stepCode: "STEP_3_RESPONSE_CONSOLIDATION",
        label: "Response consolidation",
        durationMs: 900,
        intermediateOutput: "Structured and concise formatting.",
      },
    ],
  },
  cockpit: {
    defaultArbitrationJustification:
      "Justified human decision recorded from the Cockpit.",
  },
  finopsResources: {
    dashboard: "FinOps dashboard",
    budgetCeiling: "Budget ceiling",
    budgetOverride: "Budget override",
    recommendation: "FinOps recommendation",
    remoteQuota: "Remote service quota",
    circuitReset: "Connector circuit reset",
    autonomousReview: "Autonomous run review",
  },
  connectors: {
    registeredSuccess: "Enterprise connector registered.",
    deletedSuccess: "Connector deleted.",
  },
  packsRegistry: {
    healthEmpty:
      "MCP connector healthchecks refreshed: no required connectors configured.",
    healthAllOk:
      "MCP connector healthchecks refreshed: {healthy}/{total} required connectors healthy.",
    archiveExported: "Declarative archive {archive} generated.",
    workspaceOptionPrefix: "Space: {name}",
  },
  processes: {
    executionDefaultName: "Execution",
    defaultReturnRemarks:
      "Specify business value assumptions for the enterprise segment.",
    writePreviewPrompt:
      "Pre-publication check: please confirm creation in the target tool.",
    stepApprovedAdvance: 'Step "{step}" approved. Advancing to "{nextStep}".',
    stepActivatedWord: "enabled",
    stepSkippedWord: "skipped",
    readyForFinalSignoff:
      "All steps and quality checks passed. Ready for final sign-off.",
    deliverableApprovedBanner:
      "Deliverable approved, signed, and published.",
    deliverableDiffSavedBanner: "Deliverable changes saved.",
    returnLoopMarkdown:
      "## Correction Cycle ({cycle} → Step {step})\nNotes addressed: {remarks}",
    returnLoopBanner:
      "Returned to Step {step} with your correction notes (Cycle {cycle}).",
    processResource: "Process",
    processSaveResource: "Process save",
    delegatedAgentsUpdated: "Mobilizable specialist agents updated.",
    subStepDraftUpdated: 'Step "{step}" {state} in your working draft.',
    executionModeSwitched: 'Execution mode switched to "{mode}".',
    externalIdeLabel: "Team IDE / Git",
    nativeOrciaLabel: "ORCIA",
    draftSavedBanner: "Draft saved ({version}).",
    publishedBanner: "Process published as version {version}.",
    whatIfDoneBanner:
      "Dry-run completed: {count} step(s) verified, 0 external writes executed.",
    packCreatedBanner:
      '✅ Business Pack "{slug}" created and registered with the provided intent.',
    assetPromotedBanner: '✅ Asset promoted to Business Pack "{pack}".',
    helpArticleAttachedBanner:
      '✅ Help article "{article}" generated, verified, and attached.',
  },
  workspaceSources: {
    updated: "Source updated.",
    attached: "Source attached.",
    syncTriggered: "✅ Sync triggered ({status}).",
    deleted: "✅ Source deleted.",
    gitNexusEnabled: "✅ GitNexus active.",
    gitNexusDisabled: "GitNexus disabled.",
    referentRenewed: "Referent renewed.",
    reconciled:
      "✅ Freshness reconciled ({evaluated} evaluated, {stale} stale).",
    coldStartBanner:
      "Nominative attribution: Jira / GitLab rights apply.",
    myAccountCta: "👤 My Account › Connections",
    sourcesTitle: 'Sources for "{name}"',
    newReferentPlaceholder: "New referent email...",
    confirmRenewalCta: "Confirm renewal",
    cancelCta: "Cancel",
  },
  wizards: {
    profileSelectorAriaLabel: "Choose a Guided Setup Journey",
  },
};
