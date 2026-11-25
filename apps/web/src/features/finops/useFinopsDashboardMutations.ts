import { createOrciaApiClient, type UpdateScopeBudgetRequest } from "@orcia/api-client";
import type { UpdateConnectorQuotaInput } from "@orcia/ui";
import { useCallback, useMemo } from "react";
import type { FinopsScopeLevel } from "./finopsScopeResolver";

export function useFinopsDashboardMutations(params: {
  readonly selectedScope: FinopsScopeLevel;
  readonly resolveValidScopeIdForLevel: (level: FinopsScopeLevel) => string | null;
  readonly explicitWorkspaceScopeId: string | null;
  readonly resolveSampleWorkspaceId?: (runId: string) => string | null;
  readonly canViewGlobal: boolean;
  readonly reportMutationError: (err: unknown, resourceLabel: string) => void;
  readonly setErrorMessage: (v: string | null) => void;
  readonly setSuccessMessage: (v: string | null) => void;
  readonly triggerReload: () => void;
  readonly labels: {
    readonly budgetSaveSuccess: string;
    readonly overrideSubmitSuccess: string;
    readonly recommendationApplied: string;
    readonly quotaSaveSuccess: string;
    readonly circuitResetSuccess: string;
    readonly reviewValidatedBanner: string;
    readonly restoreSuccessBanner: string;
    readonly resources: {
      readonly budgetCeiling: string;
      readonly budgetOverride: string;
      readonly recommendation: string;
      readonly remoteQuota: string;
      readonly circuitReset: string;
      readonly autonomousReview: string;
    };
  };
}) {
  const {
    selectedScope,
    resolveValidScopeIdForLevel,
    explicitWorkspaceScopeId,
    resolveSampleWorkspaceId,
    canViewGlobal,
    reportMutationError,
    setErrorMessage,
    setSuccessMessage,
    triggerReload,
    labels,
  } = params;
  const apiClient = useMemo(() => createOrciaApiClient({ baseUrl: "" }), []);

  const handleSaveBudget = useCallback(
    async (
      scopeType: FinopsScopeLevel,
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
        setSuccessMessage(`${labels.budgetSaveSuccess} ✓`);
        triggerReload();
      } catch (err: unknown) {
        reportMutationError(err, labels.resources.budgetCeiling);
      }
    },
    [apiClient, labels.budgetSaveSuccess, labels.resources.budgetCeiling, reportMutationError, setErrorMessage, setSuccessMessage, triggerReload],
  );

  const handleSubmitOverride = useCallback(
    async (runId: string, amountUsd: number, reason: string) => {
      try {
        setErrorMessage(null);
        setSuccessMessage(null);
        await apiClient.applyBudgetOverride(runId, {
          override_amount_usd: amountUsd,
          reason,
          workspace_id: explicitWorkspaceScopeId ?? undefined,
        });
        setSuccessMessage(`${labels.overrideSubmitSuccess} ✓`);
        triggerReload();
      } catch (err: unknown) {
        reportMutationError(err, labels.resources.budgetOverride);
      }
    },
    [apiClient, explicitWorkspaceScopeId, labels.overrideSubmitSuccess, labels.resources.budgetOverride, reportMutationError, setErrorMessage, setSuccessMessage, triggerReload],
  );

  const handleApplyRecommendation = useCallback(
    async (recommendationId: string) => {
      try {
        setErrorMessage(null);
        setSuccessMessage(null);
        await apiClient.applyGatePolicyRecommendation(recommendationId);
        setSuccessMessage(labels.recommendationApplied);
        triggerReload();
      } catch (err: unknown) {
        reportMutationError(err, labels.resources.recommendation);
      }
    },
    [apiClient, labels.recommendationApplied, labels.resources.recommendation, reportMutationError, setErrorMessage, setSuccessMessage, triggerReload],
  );

  const handleUpdateConnectorQuota = useCallback(
    async (input: UpdateConnectorQuotaInput) => {
      try {
        setErrorMessage(null);
        setSuccessMessage(null);
        const targetScopeId = resolveValidScopeIdForLevel(selectedScope);
        const effectiveScopeType =
          selectedScope !== "GLOBAL" && !targetScopeId && canViewGlobal ? "GLOBAL" : selectedScope;
        await apiClient.updateConnectorQuota(input.connectorKey, {
          scope_type: effectiveScopeType,
          scope_id: targetScopeId,
          valuation_mode: input.valuationMode,
          max_reported_cost_per_call_eur: input.maxReportedCostPerCallEur,
          fixed_cost_per_call_eur: input.fixedCostPerCallEur,
          unit_tariff_eur: input.unitTariffEur,
          default_unit_name: input.defaultUnitName,
          max_daily_calls: input.maxDailyCalls,
          max_monthly_cost_eur: input.maxMonthlyCostEur,
        });
        setSuccessMessage(`${labels.quotaSaveSuccess} ✓`);
        triggerReload();
      } catch (err: unknown) {
        reportMutationError(err, labels.resources.remoteQuota);
      }
    },
    [apiClient, canViewGlobal, labels.quotaSaveSuccess, labels.resources.remoteQuota, reportMutationError, resolveValidScopeIdForLevel, selectedScope, setErrorMessage, setSuccessMessage, triggerReload],
  );

  const handleResetConnectorCircuit = useCallback(
    async (connectorKey: string) => {
      try {
        setErrorMessage(null);
        setSuccessMessage(null);
        const targetScopeId = resolveValidScopeIdForLevel(selectedScope);
        await apiClient.resetConnectorCircuit(connectorKey, {
          target_state: "CLOSED",
          scope_id: targetScopeId,
        });
        setSuccessMessage(`${labels.circuitResetSuccess} ✓`);
        triggerReload();
      } catch (err: unknown) {
        reportMutationError(err, labels.resources.circuitReset);
      }
    },
    [apiClient, labels.circuitResetSuccess, labels.resources.circuitReset, reportMutationError, resolveValidScopeIdForLevel, selectedScope, setErrorMessage, setSuccessMessage, triggerReload],
  );

  const handleReviewPostHocSample = useCallback(
    async (runId: string, decision: "VALIDATED" | "INVALIDATED_ROLLED_BACK") => {
      try {
        setErrorMessage(null);
        setSuccessMessage(null);
        const targetSampleWorkspaceId = resolveSampleWorkspaceId?.(runId) ?? null;
        await apiClient.reviewPostHocAutonomousRun(runId, {
          decision,
          comment: "",
          workspace_id: explicitWorkspaceScopeId ?? targetSampleWorkspaceId ?? undefined,
        });
        setSuccessMessage(
          decision === "VALIDATED" ? labels.reviewValidatedBanner : labels.restoreSuccessBanner,
        );
        triggerReload();
      } catch (err: unknown) {
        reportMutationError(err, labels.resources.autonomousReview);
      }
    },
    [apiClient, explicitWorkspaceScopeId, labels.resources.autonomousReview, labels.restoreSuccessBanner, labels.reviewValidatedBanner, reportMutationError, resolveSampleWorkspaceId, setErrorMessage, setSuccessMessage, triggerReload],
  );

  return {
    handleSaveBudget,
    handleSubmitOverride,
    handleApplyRecommendation,
    handleUpdateConnectorQuota,
    handleResetConnectorCircuit,
    handleReviewPostHocSample,
  };
}
