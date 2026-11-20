import {
  createOrciaApiClient,
  type CognitiveImpactDashboardResponse,
  type FinopsBreakdownResponse,
  type RemoteServicesListResponse,
  type UpdateScopeBudgetRequest,
} from "@orcia/api-client";
import type { UpdateConnectorQuotaInput } from "@orcia/ui";
import { useCallback, useEffect, useMemo, useState } from "react";
import { usePlatformSetup } from "../../components/platformSetupStore";
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

export function useFinopsDashboardController(activeScopeId: string) {
  const { dictionary, locale } = useI18n();
  const { scopes, workspaces, orgUnits } = usePlatformSetup();

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
      if (level === "GLOBAL") return null;
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
  const apiClient = useMemo(() => createOrciaApiClient({ baseUrl: "" }), []);

  const reportMutationError = useCallback(
    (err: unknown, frLabel: string, enLabel: string) => {
      setErrorMessage(
        formatRfc9457ErrorToBanner(err, locale, locale === "fr" ? frLabel : enLabel).fullText,
      );
    },
    [locale],
  );

  const loadDashboard = useCallback(async () => {
    try {
      setErrorMessage(null);
      const targetScopeId = resolveValidScopeIdForLevel(selectedScope);
      const effectiveScopeType =
        selectedScope !== "GLOBAL" && !targetScopeId ? "GLOBAL" : selectedScope;
      const [data, cog, remote] = await Promise.all([
        apiClient.getFinopsDashboard({ scopeType: effectiveScopeType, scopeId: targetScopeId }),
        apiClient.getCognitiveImpact({ scopeType: effectiveScopeType, scopeId: targetScopeId, timeWindow: "30D" }),
        apiClient.getFinopsRemoteServices({ scopeType: effectiveScopeType, scopeId: targetScopeId }),
      ]);
      setDashboardData(data);
      setCognitiveData(cog);
      setRemoteData(remote);
    } catch (err: unknown) {
      reportMutationError(err, "Tableau de bord FinOps", "FinOps dashboard");
    }
  }, [apiClient, selectedScope, resolveValidScopeIdForLevel, reportMutationError]);

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
        reportMutationError(err, "Plafond budgétaire", "Budget ceiling");
      }
    },
    [apiClient, dictionary.finops.modals.saveButton, reportMutationError],
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
        reportMutationError(err, "Dérogation budgétaire", "Budget override");
      }
    },
    [apiClient, dictionary.finops.modals.overrideSubmitButton, reportMutationError, resolvedScopeIdsByLevel.WORKSPACE],
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
        reportMutationError(err, "Recommandation FinOps", "FinOps recommendation");
      }
    },
    [apiClient, dictionary.finops.humanMastery.appliedBadge, reportMutationError],
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
        reportMutationError(err, "Quota de service distant", "Remote service quota");
      }
    },
    [apiClient, selectedScope, resolveValidScopeIdForLevel, dictionary.finops.remoteServices.quotaModal.saveButton, reportMutationError],
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
        reportMutationError(err, "Réarmement du connecteur", "Connector circuit reset");
      }
    },
    [apiClient, selectedScope, resolveValidScopeIdForLevel, dictionary.finops.remoteServices.circuitStates.closed, reportMutationError],
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
        reportMutationError(err, "Audit exécution autonome", "Autonomous run review");
      }
    },
    [apiClient, dictionary.autonomousSupervision.restoreSuccessBanner, dictionary.autonomousSupervision.reviewValidatedBanner, reportMutationError, resolvedScopeIdsByLevel.WORKSPACE],
  );

  const mappedProcesses = useMemo(() => mapProcessesRows(dashboardData), [dashboardData]);
  const mappedTiers = useMemo(() => mapTiersRows(dashboardData), [dashboardData]);
  const mappedRemoteServices = useMemo(() => mapRemoteServicesRows(remoteData), [remoteData]);
  const mappedCognitiveProps = useMemo(
    () => mapCognitiveTabProps(cognitiveData, dictionary.finops.humanMastery, dictionary.autonomousSupervision.finops),
    [cognitiveData, dictionary.autonomousSupervision.finops, dictionary.finops.humanMastery],
  );

  return {
    selectedScope,
    setSelectedScope,
    resolvedActiveScopeId,
    resolvedScopeIdsByLevel,
    overview: dashboardData?.overview,
    unitsBreakdown: remoteData?.units_breakdown,
    openCircuitsCount: remoteData?.open_circuits_count,
    mappedProcesses,
    mappedTiers,
    mappedRemoteServices,
    mappedCognitiveProps,
    errorMessage,
    successMessage,
    handleSaveBudget,
    handleSubmitOverride,
    handleApplyRecommendation,
    handleUpdateConnectorQuota,
    handleResetConnectorCircuit,
    handleReviewPostHocSample,
  };
}
