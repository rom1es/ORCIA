/**
 * Localized labels for FinOps Governance Dashboard (`Story 6.2`, `Direction C`).
 *
 * Strict anti-jargon enforcement:
 * - No 'Rubber-Stamping' (use 'Validations expéditives' / 'Quick-pass approvals')
 * - No 'Pattern Drift' (use 'Écarts d'architecture' / 'Architecture deviations')
 * - No '_meta.usage' (use 'Télémétrie déclarée par le service')
 * - No 'CIRCUIT_OPEN' (use 'Connecteur suspendu' / 'Connector suspended')
 * - No 'PAUSED_BUDGET_EXCEEDED' (use 'En pause · Plafond atteint' / 'Paused · Budget exceeded')
 * - No 'PAUSED_MAX_RETRIES' (use 'En pause · Tentatives max atteintes' / 'Paused · Max retries reached')
 * - No raw latency or database names in user-facing French text
 */

import type { HumanMasteryLabels, RemoteServicesTabLabels } from "@orcia/ui";

export interface FinopsDictionarySection {
  finops: {
    pageTitle: string;
    pageSubtitle: string;
    infoButtonAriaLabel: string;
    scopeSelector: {
      currentWorkspace: string;
      currentTeam: string;
      entirePlatform: string;
    };
    configureBudgetButton: string;
    tabsAriaLabel: string;
    emptyStateText: string;
    kpis: {
      consolidatedCostTitle: string;
      verifiedInternalSubtitle: string;
      reportedExternalSubtitle: string;
      tokensTitle: string;
      internalTokensSubtitle: string;
      remoteTokensSubtitle: string;
      externalCallsTitle: string;
      externalUnitsSubtitle: string;
      savingsTitle: string;
      activeBreakersBadge: string;
      pausedRunsBadge: string;
    };
    tabs: {
      processes: string;
      tiers: string;
      externalServices: string;
      cognitiveGovernance: string;
    };
    processesTable: {
      title: string;
      workflowCol: string;
      runsCol: string;
      setupCostCol: string;
      runCostCol: string;
      humanTimeCol: string;
      totalCostCol: string;
      ttmCol: string;
      statusCol: string;
      actionsCol: string;
      pausedBadgeBudget: string;
      pausedBadgeRetries: string;
      activeBadge: string;
      overrideButton: string;
      emptyProcessesText: string;
    };
    tiersTable: {
      title: string;
      tierCol: string;
      effortCol: string;
      invocationsCol: string;
      inputTokensCol: string;
      outputTokensCol: string;
      totalTokensCol: string;
      costCol: string;
      emptyTiersText: string;
      tierLabels: Record<string, string>;
      effortLabels: Record<string, string>;
    };
    modals: {
      budgetTitle: string;
      budgetDescription: string;
      monthlyLimitLabel: string;
      warningThresholdLabel: string;
      hardStopLabel: string;
      scopeLabel: string;
      scopeGlobalLabel: string;
      scopeBuLabel: string;
      scopeTeamLabel: string;
      scopeWorkspaceLabel: string;
      saveButton: string;
      cancelButton: string;
      overrideTitle: string;
      overrideDescription: string;
      overrideAmountLabel: string;
      overrideReasonLabel: string;
      overrideSubmitButton: string;
    };
    remoteServices: RemoteServicesTabLabels;
    humanMastery: HumanMasteryLabels;
  };
}

export { FINOPS_EN_LABELS } from "./finops_labels_en";
export { FINOPS_FR_LABELS } from "./finops_labels_fr";
