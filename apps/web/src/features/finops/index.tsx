import { FinopsGovernanceDashboardView, OrciaAlertBanner } from "@orcia/ui";
import React from "react";
import { useShellNavigation } from "../../components/ShellContainer";
import { useI18n } from "../../i18n";
import { useFinopsDashboardController } from "./useFinopsDashboardController";

export function FinopsFeaturePanel() {
  const { dictionary } = useI18n();
  const { activeScopeId, openHelpSection, navigateToRoute } = useShellNavigation();
  const ctrl = useFinopsDashboardController(activeScopeId);
  const overview = ctrl.overview;

  const alertBannerNode =
    ctrl.errorMessage || ctrl.successMessage ? (
      <>
        {ctrl.errorMessage && (
          <OrciaAlertBanner tone="crimson" role="alert" testId="finops-error-banner">
            {ctrl.errorMessage}
          </OrciaAlertBanner>
        )}
        {ctrl.successMessage && (
          <OrciaAlertBanner tone="emerald" role="status" testId="finops-success-banner">
            {ctrl.successMessage}
          </OrciaAlertBanner>
        )}
      </>
    ) : null;

  return (
    <div
      data-testid="finops-feature-panel"
      style={{ display: "flex", flexDirection: "column", gap: "16px", width: "100%", minWidth: 0 }}
    >
      <FinopsGovernanceDashboardView
        scopeType={ctrl.selectedScope}
        scopeId={ctrl.resolvedActiveScopeId}
        scopeIdsByLevel={ctrl.resolvedScopeIdsByLevel}
        allowedScopes={ctrl.allowedScopePills}
        allowedModalScopes={ctrl.allowedModalScopes}
        error={ctrl.errorMessage}
        alertSlot={alertBannerNode}
        onScopeChange={ctrl.setSelectedScope}
        totalRuns={overview?.accounted_runs_count ?? 0}
        totalCostEur={overview?.total_cost_eur ?? 0}
        verifiedInternalCostEur={overview?.verified_internal_cost_eur ?? 0}
        reportedExternalCostEur={overview?.reported_external_cost_eur ?? 0}
        totalLlmTokens={overview?.total_llm_tokens ?? 0}
        internalTokens={overview?.internal_tokens ?? 0}
        remoteTokens={overview?.remote_tokens ?? 0}
        totalExternalCalls={overview?.total_external_calls ?? 0}
        externalUnitsBreakdown={overview?.external_units_breakdown ?? ctrl.unitsBreakdown}
        cacheSavingsEur={overview?.cache_savings_eur}
        activeCircuitBreakersCount={overview?.active_circuit_breakers_count ?? ctrl.openCircuitsCount}
        pausedRunsCount={overview?.paused_runs_count}
        processes={ctrl.mappedProcesses}
        tiers={ctrl.mappedTiers}
        remoteServices={ctrl.mappedRemoteServices}
        labels={dictionary.finops}
        cognitiveData={ctrl.mappedCognitiveProps}
        headerActions={
          <button
            type="button"
            data-testid="finops-open-activity-link"
            onClick={() => navigateToRoute("/activity")}
            className="orcia-ds-btn orcia-ds-btn-secondary orcia-ds-btn-sm orcia-ds-nowrap"
          >
            {dictionary.fourZoneShell.activityMenuLabel} →
          </button>
        }
        onOpenHelpSection={openHelpSection}
        onSaveBudget={ctrl.handleSaveBudget}
        onSubmitOverride={ctrl.handleSubmitOverride}
        onApplyRecommendation={ctrl.handleApplyRecommendation}
        onReviewPostHocSample={ctrl.handleReviewPostHocSample}
        onUpdateConnectorQuota={ctrl.handleUpdateConnectorQuota}
        onResetConnectorCircuit={ctrl.handleResetConnectorCircuit}
      />
    </div>
  );
}
