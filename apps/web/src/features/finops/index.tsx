import {
  createOrciaApiClient,
  type CognitiveImpactDashboardResponse,
  type FinopsBreakdownResponse,
  type UpdateScopeBudgetRequest,
} from "@orcia/api-client";
import {
  FinopsGovernanceDashboardView,
  OrciaAlertBanner,
  type FinopsHumanMasteryTabProps,
  type FinopsProcessRowData,
  type FinopsTierRowData,
} from "@orcia/ui";
import React, { useCallback, useEffect, useMemo, useState } from "react";
import { usePlatformSetup } from "../../components/platformSetupStore";
import { useShellNavigation } from "../../components/ShellContainer";
import { useI18n } from "../../i18n";

export function FinopsFeaturePanel() {
  const { dictionary } = useI18n();
  const { activeScopeId, openHelpSection } = useShellNavigation();
  const { scopes } = usePlatformSetup();

  const [selectedScope, setSelectedScope] = useState<"GLOBAL" | "BU" | "TEAM" | "WORKSPACE">("GLOBAL");
  const [dashboardData, setDashboardData] = useState<FinopsBreakdownResponse | null>(null);
  const [cognitiveData, setCognitiveData] = useState<CognitiveImpactDashboardResponse | null>(null);
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
      const [data, cog] = await Promise.all([
        apiClient.getFinopsDashboard({
          scopeType: selectedScope,
          scopeId: targetScopeId,
        }),
        apiClient.getCognitiveImpact({
          scopeType: selectedScope,
          scopeId: targetScopeId,
          timeWindow: "30D",
        }),
      ]);
      setDashboardData(data);
      setCognitiveData(cog);
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

  const mappedProcesses: readonly FinopsProcessRowData[] = useMemo(() => {
    if (!dashboardData?.processes) return [];
    return dashboardData.processes.map((p) => ({
      workflowId: p.workflow_id,
      workflowTitle: p.workflow_title,
      runsCount: p.runs_count,
      amortizedSetupCostEur: p.amortized_setup_cost_eur,
      runCostEur: p.run_cost_eur,
      humanTimeCostEur: p.human_time_cost_eur,
      totalCostEur: p.total_cost_eur,
      ttmReductionPct: p.ttm_reduction_pct,
      activeBudgetOverride: p.active_budget_override,
      pausedRunsCount: p.paused_runs_count,
      pausedReason: p.paused_runs_count && p.paused_runs_count > 0 ? "BUDGET" : null,
      samplePausedRunId: undefined,
    }));
  }, [dashboardData?.processes]);

  const mappedTiers: readonly FinopsTierRowData[] = useMemo(() => {
    if (!dashboardData?.tiers) return [];
    return dashboardData.tiers.map((t) => ({
      inferenceTier: t.inference_tier,
      effort: t.effort,
      invocationsCount: t.invocations_count,
      inputTokens: t.input_tokens,
      outputTokens: t.output_tokens,
      totalTokens: t.total_tokens,
      costEur: t.cost_eur,
    }));
  }, [dashboardData?.tiers]);

  const mappedCognitiveProps: FinopsHumanMasteryTabProps | null = useMemo(() => {
    if (!cognitiveData) return null;
    return {
      activeFramingRatio: cognitiveData.active_framing_ratio,
      activeFramingAlert: cognitiveData.active_framing_alert,
      quickPassRate: cognitiveData.quick_pass_rate,
      quickPassAlert: cognitiveData.quick_pass_alert,
      architectureDeviationIndex: cognitiveData.architecture_deviation_index,
      architectureDeviationAlert: cognitiveData.architecture_deviation_alert,
      uncoveredDeviationsCount: cognitiveData.uncovered_deviations_count,
      workflows: (cognitiveData.workflow_breakdowns ?? []).map((w) => ({
        workflowId: w.workflow_id,
        workflowTitle: w.workflow_title,
        criticality: w.criticality,
        humanGatesCount: w.human_gates_count,
        humanPassesCount: w.human_passes_count,
        quickPassesCount: w.quick_passes_count,
        quickPassRate: w.quick_pass_rate,
        medianReviewDurationMs: w.median_review_duration_ms,
        uncoveredDriftCount: w.uncovered_drift_count,
        hasAlert: w.has_alert,
      })),
      recommendations: (cognitiveData.recommendations ?? []).map((r) => ({
        id: r.id,
        workflowId: r.workflow_id,
        workflowTitle: r.workflow_title,
        recommendationType: r.recommendation_type,
        title: r.title,
        description: r.description,
        actionLabel: r.action_label,
        suggestedPolicy: r.suggested_policy,
        status: (r.status as "PROPOSED" | "APPLIED" | "DISMISSED") || "PROPOSED",
        appliedAt: r.applied_at,
      })),
      labels: dictionary.finops.humanMastery,
    };
  }, [cognitiveData, dictionary.finops.humanMastery]);

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
        cacheSavingsEur={overview?.cache_savings_eur}
        activeCircuitBreakersCount={overview?.active_circuit_breakers_count}
        pausedRunsCount={overview?.paused_runs_count}
        processes={mappedProcesses}
        tiers={mappedTiers}
        labels={dictionary.finops}
        cognitiveData={mappedCognitiveProps}
        onOpenHelpSection={openHelpSection}
        onSaveBudget={handleSaveBudget}
        onSubmitOverride={handleSubmitOverride}
        onApplyRecommendation={handleApplyRecommendation}
      />
    </div>
  );
}
