import { createOrciaApiClient } from "@orcia/api-client";
import type {
  ControlCenterDatasourceItem,
  ControlCenterOverrideItem,
  ControlCenterRunItem,
  ControlCenterWorkspaceGovItem,
  UiCatalogExplorerItemView,
  UiOntologyConceptView,
} from "@orcia/ui";
import React, { createContext, useContext, useEffect, useRef, useState } from "react";
import { formatRfc9457ErrorToBanner } from "../lib/formatRfc9457ErrorToBanner";
import { resolveWebApiBaseUrl, useAuthSessionStore } from "../stores/authSessionStore";
import { createPlatformGovernanceActions } from "./platformSetupGovernanceActions";
import {
  buildWorkflowOverridesFromWorkflows,
  computeAccostageProgressSummary,
} from "./platformSetupAccostage";
import {
  appendPlatformSetupAuditEvent,
  createPlatformWorkspaceActions,
  EMPTY_CACHED_PLATFORM_SETUP_STATE,
  type PlatformSetupContextValue,
} from "./platformSetupContextTypes";
import {
  buildAccostageCountsFromStatus,
  fetchAndBuildHydrationOutcome,
  savePlatformSetupSnapshotToApi,
  type AccostagePg18CountsView,
} from "./platformSetupHydration";
import {
  readCachedPlatformAdmin,
  readCachedPlatformSetupState,
  writeCachedPlatformSetupState,
  type CachedPlatformSetupState,
  type ConfiguredAuditEvent,
  type ConfiguredLlmTierMapping,
  type ConfiguredOrgUnit,
  type ConfiguredPackItem,
  type ConfiguredPlatformAdmin,
  type ConfiguredRbacGrant,
  type ConfiguredWorkflowItem,
} from "./platformSetupStorageHelpers";
import { buildScopeNodes } from "./platformSetupWorkspaces";

export {
  cleanAuditSummaryJargon,
  clearPlatformSetupStorage,
  deduplicateConfiguredPacks,
  formatHumanReadableScopePath,
  normalizeConfiguredAuditEvent,
  PLATFORM_ADMIN_STORAGE_KEY,
  PLATFORM_SETUP_STATE_STORAGE_KEY,
  type CachedPlatformSetupState,
  type ConfiguredAuditEvent,
  type ConfiguredLlmTierMapping,
  type ConfiguredOrgUnit,
  type ConfiguredPackItem,
  type ConfiguredPlatformAdmin,
  type ConfiguredRbacGrant,
  type ConfiguredWorkflowItem,
  type LlmAuthMode,
} from "./platformSetupStorageHelpers";
export type { PlatformSetupContextValue };

const isVitest =
  typeof process !== "undefined" &&
  (process.env?.NODE_ENV === "test" || process.env?.VITEST === "true");

const PlatformSetupContext = createContext<PlatformSetupContextValue | null>(null);

export function PlatformSetupProvider({ children }: { children: React.ReactNode }) {
  const [isInitialLoading, setIsInitialLoading] = useState<boolean>(() => !isVitest);
  const [lastSyncError, setLastSyncError] = useState<string | null>(null);
  const [platformAdmin, setPlatformAdmin] = useState<ConfiguredPlatformAdmin | null>(() =>
    readCachedPlatformAdmin(),
  );
  const [initialCache] = useState<CachedPlatformSetupState>(() => readCachedPlatformSetupState());
  const [orgUnits, setOrgUnits] = useState<readonly ConfiguredOrgUnit[]>(initialCache.orgUnits);
  const [rbacGrants, setRbacGrants] = useState<readonly ConfiguredRbacGrant[]>(
    initialCache.rbacGrants,
  );
  const [llmTiers, setLlmTiers] = useState<readonly ConfiguredLlmTierMapping[]>(
    initialCache.llmTiers,
  );
  const [workspaces, setWorkspaces] = useState<readonly ControlCenterWorkspaceGovItem[]>(
    initialCache.workspaces,
  );
  const [datasources, setDatasources] = useState<readonly ControlCenterDatasourceItem[]>(
    initialCache.datasources,
  );
  const [packs, setPacks] = useState<readonly ConfiguredPackItem[]>(initialCache.packs);
  const [workflows, setWorkflows] = useState<readonly ConfiguredWorkflowItem[]>(
    initialCache.workflows,
  );
  const [runs, setRuns] = useState<readonly ControlCenterRunItem[]>(initialCache.runs);
  const [catalogItems, setCatalogItems] = useState<readonly UiCatalogExplorerItemView[]>(
    initialCache.catalogItems,
  );
  const [ontologyConcepts, setOntologyConcepts] = useState<readonly UiOntologyConceptView[]>(
    initialCache.ontologyConcepts,
  );
  const [auditEvents, setAuditEvents] = useState<readonly ConfiguredAuditEvent[]>(
    initialCache.auditEvents,
  );
  const [accostageCounts, setAccostageCounts] = useState<AccostagePg18CountsView | null>(null);
  const hasMutatedSinceMountRef = useRef(false);
  const isAuthHydrating = useAuthSessionStore((s) => s.isHydrating);
  const isAuthenticated = useAuthSessionStore((s) => s.isAuthenticated);

  const applySnapshotToState = (next: CachedPlatformSetupState) => {
    setOrgUnits(next.orgUnits);
    setRbacGrants(next.rbacGrants);
    setLlmTiers(next.llmTiers);
    setWorkspaces(next.workspaces);
    setDatasources(next.datasources);
    setPacks(next.packs);
    setWorkflows(next.workflows);
    setRuns(next.runs);
    setCatalogItems(next.catalogItems);
    setOntologyConcepts(next.ontologyConcepts);
    setAuditEvents(next.auditEvents);
  };

  const resetAllSetupState = () => {
    setPlatformAdmin(null);
    setAccostageCounts(null);
    applySnapshotToState(EMPTY_CACHED_PLATFORM_SETUP_STATE);
  };

  const persistSnapshotStrict = async (next: CachedPlatformSetupState): Promise<void> => {
    hasMutatedSinceMountRef.current = true;
    writeCachedPlatformSetupState(next);
    try {
      await savePlatformSetupSnapshotToApi(next);
      setLastSyncError(null);
    } catch (err: unknown) {
      setLastSyncError(
        formatRfc9457ErrorToBanner(err, "fr", "Synchronisation plateforme").fullText,
      );
      throw err;
    }
  };

  const persistSnapshot = (next: CachedPlatformSetupState) => {
    void persistSnapshotStrict(next).catch((err: unknown) => {
      setLastSyncError(
        formatRfc9457ErrorToBanner(err, "fr", "Synchronisation plateforme").fullText,
      );
    });
  };

  const refreshAccostage = async (): Promise<void> => {
    try {
      const client = createOrciaApiClient({ baseUrl: resolveWebApiBaseUrl() });
      const status = await client.getAccostageStatus();
      const nextCounts = buildAccostageCountsFromStatus(status, orgUnits);
      setAccostageCounts(nextCounts);
      if (nextCounts.modelsCount === 0 && llmTiers.length > 0) {
        setLlmTiers([]);
        writeCachedPlatformSetupState(buildSnapshot({ llmTiers: [] }));
      }
    } catch (err: unknown) {
      console.warn("[orcia:platformSetup.refreshAccostage]", err);
    }
  };

  useEffect(() => {
    if (isAuthHydrating) {
      return;
    }
    let cancelled = false;
    let safetyTimer: ReturnType<typeof setTimeout> | undefined = setTimeout(() => {
      if (!cancelled) setIsInitialLoading(false);
    }, 5000);

    void fetchAndBuildHydrationOutcome({
      hasMutatedSinceMount: hasMutatedSinceMountRef.current,
      currentAdmin: platformAdmin,
      isAuthenticated,
    })
      .then((outcome) => {
        if (cancelled) return;
        if (outcome.kind === "BOOT_EPOCH_RESET") {
          hasMutatedSinceMountRef.current = false;
          useAuthSessionStore.getState().resetAuthSession();
          resetAllSetupState();
          return;
        }
        if (outcome.kind === "DAY0_CLEAN_RESET") {
          if (hasMutatedSinceMountRef.current) return;
          resetAllSetupState();
          return;
        }
        if (outcome.kind === "HYDRATED") {
          setAccostageCounts(outcome.accostageCounts);
          if (outcome.admin) setPlatformAdmin(outcome.admin);
          if (outcome.snapshot) applySnapshotToState(outcome.snapshot);
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setLastSyncError(
            formatRfc9457ErrorToBanner(err, "fr", "Chargement initial plateforme").fullText,
          );
        }
      })
      .finally(() => {
        if (!cancelled) {
          if (safetyTimer) {
            clearTimeout(safetyTimer);
            safetyTimer = undefined;
          }
          setIsInitialLoading(false);
        }
      });

    return () => {
      cancelled = true;
      if (safetyTimer) clearTimeout(safetyTimer);
    };
  }, [isAuthHydrating, isAuthenticated]);

  const buildSnapshot = (
    overrides: Partial<CachedPlatformSetupState>,
  ): CachedPlatformSetupState => ({
    orgUnits: overrides.orgUnits ?? orgUnits,
    rbacGrants: overrides.rbacGrants ?? rbacGrants,
    llmTiers: overrides.llmTiers ?? llmTiers,
    workspaces: overrides.workspaces ?? workspaces,
    datasources: overrides.datasources ?? datasources,
    packs: overrides.packs ?? packs,
    workflows: overrides.workflows ?? workflows,
    runs: overrides.runs ?? runs,
    catalogItems: overrides.catalogItems ?? catalogItems,
    ontologyConcepts: overrides.ontologyConcepts ?? ontologyConcepts,
    auditEvents: overrides.auditEvents ?? auditEvents,
  });

  const appendAudit = (
    eventType: string,
    summary: string,
    meta?: {
      readonly actorName?: string;
      readonly actorEmail?: string;
      readonly scopeId?: string;
      readonly scopePath?: string;
      readonly scopeLabel?: string;
    },
  ): readonly ConfiguredAuditEvent[] =>
    appendPlatformSetupAuditEvent({
      auditEvents,
      platformAdmin,
      eventType,
      summary,
      meta,
    });

  const governanceActions = createPlatformGovernanceActions({
    platformAdmin,
    orgUnits,
    rbacGrants,
    llmTiers,
    workspaces,
    packs,
    workflows,
    runs,
    catalogItems,
    ontologyConcepts,
    setPlatformAdmin,
    setOrgUnits,
    setRbacGrants,
    setLlmTiers,
    setPacks,
    setWorkflows,
    setRuns,
    setCatalogItems,
    setOntologyConcepts,
    setAuditEvents,
    setLastSyncError,
    markMutated: () => {
      hasMutatedSinceMountRef.current = true;
    },
    appendAudit,
    buildSnapshot,
    persistSnapshot,
  });

  const workspaceActions = createPlatformWorkspaceActions({
    platformAdmin,
    orgUnits,
    workflows,
    workspaces,
    datasources,
    setWorkspaces,
    setDatasources,
    setAuditEvents,
    markMutated: () => {
      hasMutatedSinceMountRef.current = true;
    },
    appendAudit,
    buildSnapshot,
    persistSnapshotStrict,
  });

  const scopes = buildScopeNodes(orgUnits, workspaces);
  const accostageSummary = computeAccostageProgressSummary({
    accostageCounts,
    platformAdmin,
    orgUnits,
    llmTiers,
    workspaces,
    datasources,
    workflows,
    packs,
  });
  const completedSetupStepsCount = accostageSummary.completedCount;
  const isDay0Complete = accostageSummary.isDay0Complete;
  const workflowOverrides: ControlCenterOverrideItem[] =
    buildWorkflowOverridesFromWorkflows(workflows);

  return (
    <PlatformSetupContext.Provider
      value={{
        isInitialLoading,
        lastSyncError,
        platformAdmin,
        orgUnits,
        rbacGrants,
        llmTiers,
        workspaces,
        datasources,
        packs,
        workflows,
        runs,
        catalogItems,
        ontologyConcepts,
        workflowOverrides,
        auditEvents,
        scopes,
        accostageCounts,
        accostageSummary,
        isDay0Complete,
        completedSetupStepsCount,
        refreshAccostage,
        ...governanceActions,
        ...workspaceActions,
      }}
    >
      {children}
    </PlatformSetupContext.Provider>
  );
}

export function usePlatformSetup(): PlatformSetupContextValue {
  const ctx = useContext(PlatformSetupContext);
  if (!ctx) {
    throw new Error("usePlatformSetup must be used inside PlatformSetupProvider");
  }
  return ctx;
}

export function useOptionalPlatformSetup(): PlatformSetupContextValue | null {
  return useContext(PlatformSetupContext);
}
