import {
  createOrciaApiClient,
  type CognitiveImpactDashboardResponse,
  type FinopsBreakdownResponse,
  type RemoteServicesListResponse,
} from "@orcia/api-client";
import { useCallback, useEffect, useMemo, useState } from "react";
import { usePlatformSetup } from "../../components/platformSetupStore";
import { resolveEffectiveWorkspaceId } from "../../components/shellScopeOptions";
import { useI18n } from "../../i18n";
import { formatRfc9457ErrorToBanner } from "../../lib/formatRfc9457ErrorToBanner";
import { useAuthSessionStore } from "../../stores/authSessionStore";
import {
  mapCognitiveTabProps,
  mapProcessesRows,
  mapRemoteServicesRows,
  mapTiersRows,
} from "./finopsMappers";
import {
  deriveAuthorizedFinopsScope,
  resolveFinopsScopeCapabilities,
  type FinopsScopeLevel,
} from "./finopsScopeResolver";
import { useFinopsDashboardMutations } from "./useFinopsDashboardMutations";

const UUID_REGEX =
  /^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$/i;

function isValidUuid(value: string | null | undefined): value is string {
  return Boolean(value && UUID_REGEX.test(value));
}

export function useFinopsDashboardController(activeScopeId: string) {
  const { dictionary, locale } = useI18n();
  const { scopes, workspaces, orgUnits } = usePlatformSetup();
  const authEmail = useAuthSessionStore((s) => s.email);
  const authRoles = useAuthSessionStore((s) => s.roles);

  const scopeCapabilities = useMemo(
    () => resolveFinopsScopeCapabilities(authRoles),
    [authRoles],
  );
  const activeScopeNode = useMemo(
    () => scopes.find((s) => s.id === activeScopeId),
    [scopes, activeScopeId],
  );

  const resolveValidScopeIdForLevel = useCallback(
    (level: FinopsScopeLevel): string | null => {
      if (level === "GLOBAL") return null;
      if (activeScopeNode?.level === level && isValidUuid(activeScopeNode.id)) {
        return activeScopeNode.id;
      }
      if (level === "WORKSPACE") {
        const effectiveWsId = resolveEffectiveWorkspaceId(activeScopeId, workspaces, authEmail);
        if (isValidUuid(effectiveWsId)) return effectiveWsId;
        return (
          scopes.find((s) => s.level === "WORKSPACE" && isValidUuid(s.id))?.id ??
          workspaces.find((w) => isValidUuid(w.workspaceId))?.workspaceId ??
          null
        );
      }
      if (level === "TEAM" && activeScopeNode?.level === "WORKSPACE") {
        const ws = workspaces.find((w) => w.workspaceId === activeScopeNode.id);
        if (ws?.ownerOrgUnitId && isValidUuid(ws.ownerOrgUnitId)) {
          return ws.ownerOrgUnitId;
        }
      }
      return (
        scopes.find((s) => s.level === level && isValidUuid(s.id))?.id ??
        orgUnits.find((o) => o.level === level && isValidUuid(o.id))?.id ??
        null
      );
    },
    [activeScopeId, activeScopeNode, authEmail, scopes, workspaces, orgUnits],
  );

  const resolvedScopeIdsByLevel = useMemo(
    () => ({
      BU: resolveValidScopeIdForLevel("BU"),
      TEAM: resolveValidScopeIdForLevel("TEAM"),
      WORKSPACE: resolveValidScopeIdForLevel("WORKSPACE"),
    }),
    [resolveValidScopeIdForLevel],
  );

  const defaultScopeForSelection = useMemo(
    () =>
      deriveAuthorizedFinopsScope({
        activeScopeNodeLevel: activeScopeNode?.level,
        capabilities: scopeCapabilities,
        hasBuId: resolvedScopeIdsByLevel.BU !== null,
        hasTeamId: resolvedScopeIdsByLevel.TEAM !== null,
      }),
    [activeScopeNode?.level, scopeCapabilities, resolvedScopeIdsByLevel.BU, resolvedScopeIdsByLevel.TEAM],
  );

  const [selectedScope, setSelectedScope] = useState<FinopsScopeLevel>(
    () => defaultScopeForSelection,
  );
  const [dashboardData, setDashboardData] = useState<FinopsBreakdownResponse | null>(null);
  const [cognitiveData, setCognitiveData] = useState<CognitiveImpactDashboardResponse | null>(null);
  const [remoteData, setRemoteData] = useState<RemoteServicesListResponse | null>(null);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [successMessage, setSuccessMessage] = useState<string | null>(null);
  const [reloadTrigger, setReloadTrigger] = useState<number>(0);

  useEffect(() => {
    setSelectedScope(defaultScopeForSelection);
  }, [activeScopeId, defaultScopeForSelection]);

  const handleScopeChange = useCallback(
    (nextScope: FinopsScopeLevel) => {
      if (nextScope === "GLOBAL" && !scopeCapabilities.canViewGlobal) return;
      if (nextScope === "TEAM") {
        if (
          (activeScopeNode?.level === "BU" || !resolvedScopeIdsByLevel.TEAM) &&
          scopeCapabilities.canViewBu &&
          resolvedScopeIdsByLevel.BU
        ) {
          setSelectedScope("BU");
          return;
        }
      }
      setSelectedScope(nextScope);
    },
    [
      activeScopeNode?.level,
      resolvedScopeIdsByLevel.BU,
      resolvedScopeIdsByLevel.TEAM,
      scopeCapabilities.canViewBu,
      scopeCapabilities.canViewGlobal,
    ],
  );

  const resolvedActiveScopeId = resolveValidScopeIdForLevel(selectedScope);
  const apiClient = useMemo(() => createOrciaApiClient({ baseUrl: "" }), []);

  const reportMutationError = useCallback(
    (err: unknown, resourceLabel: string) => {
      setErrorMessage(formatRfc9457ErrorToBanner(err, locale, resourceLabel).fullText);
    },
    [locale],
  );

  const finopsResources = dictionary.categoryAControllers.finopsResources;

  const resolveEffectiveReadTarget = useCallback((): {
    scopeType: FinopsScopeLevel;
    scopeId: string | null;
  } | null => {
    const targetScopeId = resolveValidScopeIdForLevel(selectedScope);
    if (selectedScope === "GLOBAL" || targetScopeId !== null) {
      return { scopeType: selectedScope, scopeId: targetScopeId };
    }
    if (resolvedScopeIdsByLevel.TEAM) {
      return { scopeType: "TEAM", scopeId: resolvedScopeIdsByLevel.TEAM };
    }
    if (resolvedScopeIdsByLevel.WORKSPACE) {
      return { scopeType: "WORKSPACE", scopeId: resolvedScopeIdsByLevel.WORKSPACE };
    }
    return scopeCapabilities.canViewGlobal ? { scopeType: "GLOBAL", scopeId: null } : null;
  }, [
    resolveValidScopeIdForLevel,
    resolvedScopeIdsByLevel.TEAM,
    resolvedScopeIdsByLevel.WORKSPACE,
    scopeCapabilities.canViewGlobal,
    selectedScope,
  ]);

  const loadDashboard = useCallback(async () => {
    const target = resolveEffectiveReadTarget();
    if (!target) {
      setErrorMessage(null);
      setDashboardData(null);
      setCognitiveData(null);
      setRemoteData(null);
      return;
    }
    try {
      setErrorMessage(null);
      const [data, cog, remote] = await Promise.all([
        apiClient.getFinopsDashboard({ scopeType: target.scopeType, scopeId: target.scopeId }),
        apiClient.getCognitiveImpact({ scopeType: target.scopeType, scopeId: target.scopeId, timeWindow: "30D" }),
        apiClient.getFinopsRemoteServices({ scopeType: target.scopeType, scopeId: target.scopeId }),
      ]);
      setDashboardData(data);
      setCognitiveData(cog);
      setRemoteData(remote);
    } catch (err: unknown) {
      setDashboardData(null);
      setCognitiveData(null);
      setRemoteData(null);
      reportMutationError(err, finopsResources.dashboard);
    }
  }, [apiClient, resolveEffectiveReadTarget, reportMutationError, finopsResources.dashboard]);

  useEffect(() => {
    void loadDashboard();
  }, [loadDashboard, reloadTrigger]);

  const triggerReload = useCallback(() => setReloadTrigger((prev) => prev + 1), []);
  const explicitWorkspaceScopeId = useMemo(() => {
    if (selectedScope !== "WORKSPACE") return null;
    const scopeRaw = activeScopeId.startsWith("scope-ws-")
      ? activeScopeId.slice("scope-ws-".length)
      : activeScopeId;
    if (!isValidUuid(scopeRaw)) return null;
    const matchingScope = scopes.find((s) => s.id === activeScopeId || s.id === scopeRaw);
    if (
      matchingScope?.level === "WORKSPACE" ||
      workspaces.some((w) => w.workspaceId === scopeRaw || w.slug === scopeRaw)
    ) {
      return scopeRaw;
    }
    return null;
  }, [activeScopeId, scopes, selectedScope, workspaces]);

  const resolveSampleWorkspaceId = useCallback(
    (runId: string): string | null => {
      const sample = cognitiveData?.autonomous_governance?.pending_samples?.find(
        (s) => s.run_id === runId,
      );
      return isValidUuid(sample?.workspace_id) ? sample.workspace_id : null;
    },
    [cognitiveData],
  );

  const mutations = useFinopsDashboardMutations({
    selectedScope,
    resolveValidScopeIdForLevel,
    explicitWorkspaceScopeId,
    resolveSampleWorkspaceId,
    canViewGlobal: scopeCapabilities.canViewGlobal,
    reportMutationError,
    setErrorMessage,
    setSuccessMessage,
    triggerReload,
    labels: {
      budgetSaveSuccess: dictionary.finops.modals.saveButton,
      overrideSubmitSuccess: dictionary.finops.modals.overrideSubmitButton,
      recommendationApplied: dictionary.finops.humanMastery.appliedBadge,
      quotaSaveSuccess: dictionary.finops.remoteServices.quotaModal.saveButton,
      circuitResetSuccess: dictionary.finops.remoteServices.circuitStates.closed,
      reviewValidatedBanner: dictionary.autonomousSupervision.reviewValidatedBanner,
      restoreSuccessBanner: dictionary.autonomousSupervision.restoreSuccessBanner,
      resources: finopsResources,
    },
  });

  const mappedProcesses = useMemo(() => mapProcessesRows(dashboardData), [dashboardData]);
  const mappedTiers = useMemo(() => mapTiersRows(dashboardData), [dashboardData]);
  const mappedRemoteServices = useMemo(() => mapRemoteServicesRows(remoteData), [remoteData]);
  const mappedCognitiveProps = useMemo(
    () => mapCognitiveTabProps(cognitiveData, dictionary.finops.humanMastery, dictionary.autonomousSupervision.finops),
    [cognitiveData, dictionary.autonomousSupervision.finops, dictionary.finops.humanMastery],
  );

  return {
    selectedScope,
    setSelectedScope: handleScopeChange,
    allowedScopePills: scopeCapabilities.allowedScopePills,
    allowedModalScopes: scopeCapabilities.allowedModalScopes,
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
    ...mutations,
  };
}
