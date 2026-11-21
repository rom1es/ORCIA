import type {
  ControlCenterDatasourceItem,
  ControlCenterOverrideItem,
  ControlCenterRunItem,
  ControlCenterWorkspaceGovItem,
  UiCatalogExplorerItemView,
  UiOntologyConceptView,
} from "@orcia/ui";
import React, { createContext, useContext, useRef, useState } from "react";
import { useAuthSessionStore } from "../stores/authSessionStore";
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
import { type AccostagePg18CountsView } from "./platformSetupHydration";
import {
  executeRefreshAccostage,
  mergeCachedPlatformSetupSnapshot,
  persistSetupSnapshotStrict,
  usePlatformSetupHydrationEffect,
} from "./usePlatformSetupHydrationEffect";
import {
  readCachedPlatformAdmin,
  readCachedPlatformSetupState,
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
  const currentUserEmail = useAuthSessionStore((s) => s.email);

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

  const persistSnapshotStrict = async (next: CachedPlatformSetupState): Promise<void> =>
    persistSetupSnapshotStrict({ next, hasMutatedSinceMountRef, setLastSyncError });

  const persistSnapshot = (next: CachedPlatformSetupState) => {
    void persistSnapshotStrict(next).catch((err: unknown) => {
      console.warn("[orcia:platformSetup.persistSnapshot]", err instanceof Error ? err.message : String(err));
    });
  };

  const refreshAccostage = async (): Promise<void> =>
    executeRefreshAccostage({ orgUnits, llmTiers, setAccostageCounts, setLlmTiers, buildSnapshot });

  usePlatformSetupHydrationEffect({
    isAuthHydrating,
    isAuthenticated,
    currentUserEmail,
    platformAdmin,
    hasMutatedSinceMountRef,
    applySnapshotToState,
    resetAllSetupState,
    setIsInitialLoading,
    setPlatformAdmin,
    setAccostageCounts,
    setLastSyncError,
  });

  const buildSnapshot = (
    overrides: Partial<CachedPlatformSetupState>,
  ): CachedPlatformSetupState =>
    mergeCachedPlatformSetupSnapshot(
      {
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
        auditEvents,
      },
      overrides,
    );

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
