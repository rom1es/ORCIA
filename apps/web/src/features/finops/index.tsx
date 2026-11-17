import {
  createOrciaApiClient,
  type CognitiveImpactDashboardResponse,
  type FinopsBreakdownResponse,
  type RemoteServicesListResponse,
  type UpdateScopeBudgetRequest,
} from "@orcia/api-client";
import {
  FinopsGovernanceDashboardView,
  OrciaAlertBanner,
  type UpdateConnectorQuotaInput,
} from "@orcia/ui";
import React, { useCallback, useEffect, useMemo, useState } from "react";
import { usePlatformSetup } from "../../components/platformSetupStore";
import { useShellNavigation } from "../../components/ShellContainer";
import { useI18n } from "../../i18n";
import {
  mapCognitiveTabProps,
  mapProcessesRows,
  mapRemoteServicesRows,
  mapTiersRows,
} from "./finopsMappers";

export function FinopsFeaturePanel() {
  const { dictionary } = useI18n();
  const { activeScopeId, openHelpSection } = useShellNavigation();
  const { scopes } = usePlatformSetup();

  const [selectedScope, setSelectedScope] = useState<"GLOBAL" | "BU" | "TEAM" | "WORKSPACE">("GLOBAL");
  const [dashboardData, setDashboardData] = useState<FinopsBreakdownResponse | null>(null);
  const [cognitiveData, setCognitiveData] = useState<CognitiveImpactDashboardResponse | null>(null);
  const [remoteData, setRemoteData] = useState<RemoteServicesListResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [reloadTrigger, setReloadTrigger] = useState<number>(0);

  const activeScopeNode = useMemo(
    () => scopes.find((s) => s.id === activeScopeId),
    [scopes, activeScopeId],
  );

  const apiClient = useMemo(
    () =>
      createOrciaApiClient({
        baseUrl: "",
      }),
    [],
  );

  const loadDashboard = useCallback(async () => {
    try {
      setErrorMessage(null);
      const targetScopeId =
        selectedScope === "GLOBAL" ? null : (activeScopeNode?.id ?? null);
      const [data, cog, remote] = await Promise.all([
        apiClient.getFinopsDashboard({
          scopeType: selectedScope,
          scopeId: targetScopeId,
        }),
        apiClient.getCognitiveImpact({
          scopeType: selectedScope,
          scopeId: targetScopeId,
          timeWindow: "30D",
        }),
        apiClient.getFinopsRemoteServices({
          scopeType: selectedScope,
          scopeId: targetScopeId,
        }),
      ]);
      setDashboardData(data);
      setCognitiveData(cog);
      setRemoteData(remote);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : String(err);
      setErrorMessage(msg);
    }
  }, [apiClient, selectedScope, activeScopeNode?.id]);

  useEffect(() => {
    void loadDashboard();
  }, [loadDashboard, reloadTrigger]);

  const handleSaveBudget = useCallback(
    async (
      scopeType: "GLOBAL" | "BU" | "TEAM" | "WORKSPACE",
      scopeId: string | null,
      monthlyBudgetUsd: number,
      warningThresholdPct: number,
      hardStopPct: number,
    ) => {
      try {
        setErrorMessage(null);
        setSuccessMessage(null);
        const payload: UpdateScopeBudgetRequest = {
          scope_type: scopeType,
          scope_id: scopeId,
          monthly_budget_usd: monthlyBudgetUsd,
          warning_threshold_pct: warningThresholdPct,
          hard_stop_pct: hardStopPct,
        };
        await apiClient.updateScopeBudget(payload);
        setSuccessMessage(dictionary.finops.modals.saveButton + " ✓");
        setReloadTrigger((prev) => prev + 1);
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : String(err);
        setErrorMessage(msg);
      }
    },
    [apiClient, dictionary.finops.modals.saveButton],
  );

  const handleSubmitOverride = useCallback(
    async (runId: string, amountUsd: number, reason: string) => {
      try {
        setErrorMessage(null);
        setSuccessMessage(null);
        await apiClient.applyBudgetOverride(runId, {
          override_amount_usd: amountUsd,
          reason,
        });
        setSuccessMessage(dictionary.finops.modals.overrideSubmitButton + " ✓");
        setReloadTrigger((prev) => prev + 1);
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : String(err);
        setErrorMessage(msg);
      }
    },
    [apiClient, dictionary.finops.modals.overrideSubmitButton],
  );

  const handleApplyRecommendation = useCallback(
    async (recommendationId: string) => {
      try {
        setErrorMessage(null);
        setSuccessMessage(null);
        await apiClient.applyGatePolicyRecommendation(recommendationId);
        setSuccessMessage(dictionary.finops.humanMastery.appliedBadge);
        setReloadTrigger((prev) => prev + 1);
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : String(err);
        setErrorMessage(msg);
      }
    },
    [apiClient, dictionary.finops.humanMastery.appliedBadge],
  );

  const handleUpdateConnectorQuota = useCallback(
    async (input: UpdateConnectorQuotaInput) => {
      try {
        setErrorMessage(null);
        setSuccessMessage(null);
        const targetScopeId =
          selectedScope === "GLOBAL" ? null : (activeScopeNode?.id ?? null);
        await apiClient.updateConnectorQuota(input.connectorKey, {
          scope_type: selectedScope,
          scope_id: targetScopeId,
          valuation_mode: input.valuationMode,
          max_reported_cost_per_call_eur: input.maxReportedCostPerCallEur,
          fixed_cost_per_call_eur: input.fixedCostPerCallEur,
          unit_tariff_eur: input.unitTariffEur,
          default_unit_name: input.defaultUnitName,
          max_daily_calls: input.maxDailyCalls,
          max_monthly_cost_eur: input.maxMonthlyCostEur,
        });
        setSuccessMessage(dictionary.finops.remoteServices.quotaModal.saveButton + " ✓");
        setReloadTrigger((prev) => prev + 1);
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : String(err);
        setErrorMessage(msg);
      }
    },
    [apiClient, selectedScope, activeScopeNode?.id, dictionary.finops.remoteServices.quotaModal.saveButton],
  );

  const handleResetConnectorCircuit = useCallback(
    async (connectorKey: string) => {
      try {
        setErrorMessage(null);
        setSuccessMessage(null);
        const targetScopeId =
          selectedScope === "GLOBAL" ? null : (activeScopeNode?.id ?? null);
        await apiClient.resetConnectorCircuit(connectorKey, {
          target_state: "CLOSED",
          scope_id: targetScopeId,
        });
        setSuccessMessage(dictionary.finops.remoteServices.circuitStates.closed + " ✓");
        setReloadTrigger((prev) => prev + 1);
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : String(err);
        setErrorMessage(msg);
      }
    },
    [apiClient, selectedScope, activeScopeNode?.id, dictionary.finops.remoteServices.circuitStates.closed],
  );

  const mappedProcesses = useMemo(() => mapProcessesRows(dashboardData), [dashboardData]);
  const mappedTiers = useMemo(() => mapTiersRows(dashboardData), [dashboardData]);
  const mappedRemoteServices = useMemo(() => mapRemoteServicesRows(remoteData), [remoteData]);
  const mappedCognitiveProps = useMemo(
    () => mapCognitiveTabProps(cognitiveData, dictionary.finops.humanMastery),
    [cognitiveData, dictionary.finops.humanMastery],
  );

  const overview = dashboardData?.overview;

  return (
    <div
      data-testid="finops-feature-panel"
      style={{ display: "flex", flexDirection: "column", gap: "16px", width: "100%" }}
    >
      {errorMessage && (
        <OrciaAlertBanner tone="crimson" role="alert" testId="finops-error-banner">
          {errorMessage}
        </OrciaAlertBanner>
      )}
      {successMessage && (
        <OrciaAlertBanner tone="emerald" role="status" testId="finops-success-banner">
          {successMessage}
        </OrciaAlertBanner>
      )}

      <FinopsGovernanceDashboardView
        scopeType={selectedScope}
        onScopeChange={setSelectedScope}
        totalRuns={overview?.accounted_runs_count ?? 0}
        totalCostEur={overview?.total_cost_eur ?? 0}
        verifiedInternalCostEur={overview?.verified_internal_cost_eur ?? 0}
        reportedExternalCostEur={overview?.reported_external_cost_eur ?? 0}
        totalLlmTokens={overview?.total_llm_tokens ?? 0}
        internalTokens={overview?.internal_tokens ?? 0}
        remoteTokens={overview?.remote_tokens ?? 0}
        totalExternalCalls={overview?.total_external_calls ?? 0}
        externalUnitsBreakdown={overview?.external_units_breakdown ?? remoteData?.units_breakdown}
        cacheSavingsEur={overview?.cache_savings_eur}
        activeCircuitBreakersCount={
          overview?.active_circuit_breakers_count ?? remoteData?.open_circuits_count
        }
        pausedRunsCount={overview?.paused_runs_count}
        processes={mappedProcesses}
        tiers={mappedTiers}
        remoteServices={mappedRemoteServices}
        labels={dictionary.finops}
        cognitiveData={mappedCognitiveProps}
        onOpenHelpSection={openHelpSection}
        onSaveBudget={handleSaveBudget}
        onSubmitOverride={handleSubmitOverride}
        onApplyRecommendation={handleApplyRecommendation}
        onUpdateConnectorQuota={handleUpdateConnectorQuota}
        onResetConnectorCircuit={handleResetConnectorCircuit}
      />
    </div>
  );
}
