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
import { formatRfc9457ErrorToBanner } from "../../lib/formatRfc9457ErrorToBanner";
import {
  mapCognitiveTabProps,
  mapProcessesRows,
  mapRemoteServicesRows,
  mapTiersRows,
} from "./finopsMappers";

const UUID_REGEX =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function isValidUuid(value: string | null | undefined): value is string {
  return Boolean(value && UUID_REGEX.test(value));
}

export function FinopsFeaturePanel() {
  const { dictionary, locale } = useI18n();
  const { activeScopeId, openHelpSection, navigateToRoute } = useShellNavigation();
  const { scopes, workspaces, orgUnits } = usePlatformSetup();
  const isFr = locale === "fr";

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

  const resolveValidScopeIdForLevel = useCallback(
    (level: "GLOBAL" | "BU" | "TEAM" | "WORKSPACE"): string | null => {
      if (level === "GLOBAL") {
        return null;
      }
      if (activeScopeNode?.level === level && isValidUuid(activeScopeNode.id)) {
        return activeScopeNode.id;
      }
      if (level === "WORKSPACE") {
        return (
          scopes.find((s) => s.level === "WORKSPACE" && isValidUuid(s.id))?.id ??
          workspaces.find((w) => isValidUuid(w.workspaceId))?.workspaceId ??
          null
        );
      }
      return (
        scopes.find((s) => s.level === level && isValidUuid(s.id))?.id ??
        orgUnits.find((o) => o.level === level && isValidUuid(o.id))?.id ??
        null
      );
    },
    [activeScopeNode, scopes, workspaces, orgUnits],
  );

  const resolvedScopeIdsByLevel = useMemo(
    () => ({
      BU: resolveValidScopeIdForLevel("BU"),
      TEAM: resolveValidScopeIdForLevel("TEAM"),
      WORKSPACE: resolveValidScopeIdForLevel("WORKSPACE"),
    }),
    [resolveValidScopeIdForLevel],
  );

  const resolvedActiveScopeId = resolveValidScopeIdForLevel(selectedScope);

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
      const targetScopeId = resolveValidScopeIdForLevel(selectedScope);
      const effectiveScopeType =
        selectedScope !== "GLOBAL" && !targetScopeId ? "GLOBAL" : selectedScope;
      const [data, cog, remote] = await Promise.all([
        apiClient.getFinopsDashboard({
          scopeType: effectiveScopeType,
          scopeId: targetScopeId,
        }),
        apiClient.getCognitiveImpact({
          scopeType: effectiveScopeType,
          scopeId: targetScopeId,
          timeWindow: "30D",
        }),
        apiClient.getFinopsRemoteServices({
          scopeType: effectiveScopeType,
          scopeId: targetScopeId,
        }),
      ]);
      setDashboardData(data);
      setCognitiveData(cog);
      setRemoteData(remote);
    } catch (err: unknown) {
      setErrorMessage(
        formatRfc9457ErrorToBanner(
          err,
          locale,
          locale === "fr" ? "Tableau de bord FinOps" : "FinOps dashboard",
        ).fullText,
      );
    }
  }, [apiClient, locale, selectedScope, resolveValidScopeIdForLevel]);

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
        setErrorMessage(
          formatRfc9457ErrorToBanner(
            err,
            locale,
            locale === "fr" ? "Plafond budgétaire" : "Budget ceiling",
          ).fullText,
        );
      }
    },
    [apiClient, dictionary.finops.modals.saveButton, locale],
  );

  const handleSubmitOverride = useCallback(
    async (runId: string, amountUsd: number, reason: string) => {
      try {
        setErrorMessage(null);
        setSuccessMessage(null);
        await apiClient.applyBudgetOverride(runId, {
          override_amount_usd: amountUsd,
          reason,
          workspace_id: resolvedScopeIdsByLevel.WORKSPACE ?? undefined,
        });
        setSuccessMessage(dictionary.finops.modals.overrideSubmitButton + " ✓");
        setReloadTrigger((prev) => prev + 1);
      } catch (err: unknown) {
        setErrorMessage(
          formatRfc9457ErrorToBanner(
            err,
            locale,
            locale === "fr" ? "Dérogation budgétaire" : "Budget override",
          ).fullText,
        );
      }
    },
    [
      apiClient,
      dictionary.finops.modals.overrideSubmitButton,
      locale,
      resolvedScopeIdsByLevel.WORKSPACE,
    ],
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
        setErrorMessage(
          formatRfc9457ErrorToBanner(
            err,
            locale,
            locale === "fr" ? "Recommandation FinOps" : "FinOps recommendation",
          ).fullText,
        );
      }
    },
    [apiClient, dictionary.finops.humanMastery.appliedBadge, locale],
  );

  const handleUpdateConnectorQuota = useCallback(
    async (input: UpdateConnectorQuotaInput) => {
      try {
        setErrorMessage(null);
        setSuccessMessage(null);
        const targetScopeId = resolveValidScopeIdForLevel(selectedScope);
        const effectiveScopeType =
          selectedScope !== "GLOBAL" && !targetScopeId ? "GLOBAL" : selectedScope;
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
        setSuccessMessage(dictionary.finops.remoteServices.quotaModal.saveButton + " ✓");
        setReloadTrigger((prev) => prev + 1);
      } catch (err: unknown) {
        setErrorMessage(
          formatRfc9457ErrorToBanner(
            err,
            locale,
            locale === "fr" ? "Quota de service distant" : "Remote service quota",
          ).fullText,
        );
      }
    },
    [
      apiClient,
      selectedScope,
      resolveValidScopeIdForLevel,
      dictionary.finops.remoteServices.quotaModal.saveButton,
      locale,
    ],
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
        setSuccessMessage(dictionary.finops.remoteServices.circuitStates.closed + " ✓");
        setReloadTrigger((prev) => prev + 1);
      } catch (err: unknown) {
        setErrorMessage(
          formatRfc9457ErrorToBanner(
            err,
            locale,
            locale === "fr" ? "Réarmement du connecteur" : "Connector circuit reset",
          ).fullText,
        );
      }
    },
    [
      apiClient,
      selectedScope,
      resolveValidScopeIdForLevel,
      dictionary.finops.remoteServices.circuitStates.closed,
      locale,
    ],
  );

  const handleReviewPostHocSample = useCallback(
    async (runId: string, decision: "VALIDATED" | "INVALIDATED_ROLLED_BACK") => {
      try {
        setErrorMessage(null);
        setSuccessMessage(null);
        await apiClient.reviewPostHocAutonomousRun(runId, {
          decision,
          comment: "",
          workspace_id: resolvedScopeIdsByLevel.WORKSPACE ?? undefined,
        });
        setSuccessMessage(
          decision === "VALIDATED"
            ? dictionary.autonomousSupervision.reviewValidatedBanner
            : dictionary.autonomousSupervision.restoreSuccessBanner,
        );
        setReloadTrigger((prev) => prev + 1);
      } catch (err: unknown) {
        setErrorMessage(
          formatRfc9457ErrorToBanner(
            err,
            locale,
            locale === "fr" ? "Audit exécution autonome" : "Autonomous run review",
          ).fullText,
        );
      }
    },
    [
      apiClient,
      dictionary.autonomousSupervision.restoreSuccessBanner,
      dictionary.autonomousSupervision.reviewValidatedBanner,
      locale,
      resolvedScopeIdsByLevel.WORKSPACE,
    ],
  );

  const mappedProcesses = useMemo(() => mapProcessesRows(dashboardData), [dashboardData]);
  const mappedTiers = useMemo(() => mapTiersRows(dashboardData), [dashboardData]);
  const mappedRemoteServices = useMemo(() => mapRemoteServicesRows(remoteData), [remoteData]);
  const mappedCognitiveProps = useMemo(
    () =>
      mapCognitiveTabProps(
        cognitiveData,
        dictionary.finops.humanMastery,
        dictionary.autonomousSupervision.finops,
      ),
    [cognitiveData, dictionary.autonomousSupervision.finops, dictionary.finops.humanMastery],
  );

  const overview = dashboardData?.overview;

  return (
    <div
      data-testid="finops-feature-panel"
      style={{ display: "flex", flexDirection: "column", gap: "16px", width: "100%", minWidth: 0 }}
    >
      <div className="flex flex-wrap items-center justify-end gap-2">
        <button
          type="button"
          data-testid="finops-open-activity-link"
          onClick={() => navigateToRoute("/activity")}
          className="orcia-ds-btn orcia-ds-btn-secondary orcia-ds-btn-sm"
        >
          {dictionary.fourZoneShell.activityMenuLabel ?? (isFr ? "Journal d'Activité" : "Activity Log")} →
        </button>
      </div>
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
        scopeId={resolvedActiveScopeId}
        scopeIdsByLevel={resolvedScopeIdsByLevel}
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
        onReviewPostHocSample={handleReviewPostHocSample}
        onUpdateConnectorQuota={handleUpdateConnectorQuota}
        onResetConnectorCircuit={handleResetConnectorCircuit}
      />
    </div>
  );
}
