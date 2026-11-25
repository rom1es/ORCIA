import type { FinopsDictionarySection } from "./finops_labels";
import {
  HUMAN_MASTERY_EN_LABELS,
} from "./finops_human_mastery_labels";
import {
  REMOTE_SERVICES_EN_LABELS,
} from "./finops_remote_labels";

export const FINOPS_EN_LABELS: FinopsDictionarySection = {
  finops: {
    pageTitle: "FinOps and Economic Governance",
    pageSubtitle:
      "Monitor your complete process economic equation, track model and remote connector usage, and maintain human reversibility.",
    infoButtonAriaLabel: "Learn about the FinOps dashboard and economic equation",
    scopeSelector: {
      currentWorkspace: "This Workspace",
      currentTeam: "This Team or Business Unit",
      entirePlatform: "Entire Platform",
    },
    configureBudgetButton: "+ Configure Budget Ceiling",
    tabsAriaLabel: "FinOps governance tabs",
    emptyStateText:
      "No usage has been recorded in this scope yet. Costs and metrics will appear upon the first workflow execution or test bench run.",
    kpis: {
      consolidatedCostTitle: "CONSOLIDATED COST",
      verifiedInternalSubtitle: "Verified internal cost",
      reportedExternalSubtitle: "Reported external cost",
      tokensTitle: "LLM TOKENS",
      internalTokensSubtitle: "internal models",
      remoteTokensSubtitle: "remote agents",
      externalCallsTitle: "EXTERNAL CALLS AND UNITS",
      externalUnitsSubtitle: "remote tool units",
      savingsTitle: "SAVINGS AND CIRCUIT BREAKERS",
      activeBreakersBadge: "active circuit breakers",
      pausedRunsBadge: "paused runs",
    },
    tabs: {
      processes: "Overview and Processes",
      tiers: "By Model and Effort Level",
      externalServices: "External Services and Agents",
      cognitiveGovernance: "Human Mastery and Quality",
    },
    processesTable: {
      title: "Processes and Economic Equation",
      workflowCol: "Process",
      runsCol: "Executions",
      setupCostCol: "Amortized Setup",
      runCostCol: "Run Cost",
      humanTimeCol: "Valorized Human Time",
      totalCostCol: "Complete Cost",
      ttmCol: "TTM Reduction",
      statusCol: "Status",
      actionsCol: "Actions",
      pausedBadgeBudget: "Paused · Budget exceeded",
      pausedBadgeRetries: "Paused · Max retries reached",
      activeBadge: "Operational",
      overrideButton: "Grant budget extension",
      emptyProcessesText: "No active process recorded in this scope.",
    },
    tiersTable: {
      title: "Usage by Cognitive Tier and Effort",
      tierCol: "Cognitive Tier",
      effortCol: "Effort Level",
      invocationsCol: "Invocations",
      inputTokensCol: "Input Tokens",
      outputTokensCol: "Output Tokens",
      totalTokensCol: "Total Tokens",
      costCol: "Consolidated Cost",
      emptyTiersText: "No model or effort level consumption recorded yet.",
      tierLabels: {
        simple: "Fast",
        standard: "Standard",
        reasoning: "Deep reasoning",
        embedding: "Vector indexing",
      },
      effortLabels: {
        low: "Low",
        medium: "Medium",
        high: "High",
        max: "Maximum",
      },
    },
    modals: {
      budgetTitle: "Configure Budget Ceiling",
      budgetDescription:
        "Define monthly spending caps, preventive warning, and hard-stop pause thresholds for this scope.",
      monthlyLimitLabel: "Monthly ceiling (€)",
      warningThresholdLabel: "Preventive warning threshold percentage",
      hardStopLabel: "Hard stop threshold percentage",
      scopeLabel: "Target Scope",
      scopeGlobalLabel: "Entire platform",
      scopeBuLabel: "Business unit",
      scopeTeamLabel: "Team",
      scopeWorkspaceLabel: "Workspace",
      saveButton: "Save Budget Ceiling",
      cancelButton: "Cancel",
      overrideTitle: "Grant Budget Extension",
      overrideDescription:
        "Extend the budget ceiling of the paused execution to resume workflow processing immediately.",
      overrideAmountLabel: "Extension amount (€)",
      overrideReasonLabel: "Business justification",
      overrideSubmitButton: "Approve and Resume",
    },
    remoteServices: REMOTE_SERVICES_EN_LABELS,
    humanMastery: HUMAN_MASTERY_EN_LABELS,
  },
};
