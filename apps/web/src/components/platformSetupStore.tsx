import type { ControlCenterOverrideItem } from "@orcia/ui";
import React, { createContext, useContext, useRef, useState } from "react";
import { useI18n } from "../i18n";
import { ClientCodedError } from "../lib/clientErrorCodes";
import { useAuthSessionStore } from "../stores/authSessionStore";
import { createPlatformGovernanceActions } from "./platformSetupGovernanceActions";
import {
  buildWorkflowOverridesFromWorkflows,
  computeAccostageProgressSummary,
} from "./platformSetupAccostage";
import {
  appendPlatformSetupAuditEvent,
  createPlatformWorkspaceActions,
  createSnapshotSliceSetters,
  EMPTY_CACHED_PLATFORM_SETUP_STATE,
  type PlatformSetupContextValue,
} from "./platformSetupContextTypes";
import { type AccostagePg18CountsView } from "./platformSetupHydration";
import {
  executeRefreshAccostage,
  mergeCachedPlatformSetupSnapshot,
  persistSetupSnapshotStrict,
  usePlatformSetupHydrationEffect,
  type PlatformSetupMutatedSlice,
} from "./usePlatformSetupHydrationEffect";
import {
  readCachedPlatformAdmin,
  readCachedPlatformSetupState,
  writeCachedPlatformSetupState,
  type CachedPlatformSetupState,
  type ConfiguredPlatformAdmin,
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
  const { locale } = useI18n();
  const [isInitialLoading, setIsInitialLoading] = useState<boolean>(() => !isVitest);
  const [lastSyncError, setLastSyncError] = useState<string | null>(null);
  const [platformAdmin, setPlatformAdmin] = useState<ConfiguredPlatformAdmin | null>(() =>
    readCachedPlatformAdmin(),
  );
  const [snapshot, setSnapshot] = useState<CachedPlatformSetupState>(() =>
    readCachedPlatformSetupState(),
  );
  const [accostageCounts, setAccostageCounts] = useState<AccostagePg18CountsView | null>(null);
  const hasMutatedSinceMountRef = useRef(false);
  const mutatedSlicesRef = useRef<Set<PlatformSetupMutatedSlice>>(new Set());
  const latestSnapshotRef = useRef<CachedPlatformSetupState>(snapshot);
  const latestAdminRef = useRef<ConfiguredPlatformAdmin | null>(platformAdmin);
  const isAuthHydrating = useAuthSessionStore((s) => s.isHydrating);
  const isAuthenticated = useAuthSessionStore((s) => s.isAuthenticated);
  const currentUserEmail = useAuthSessionStore((s) => s.email);

  const updatePlatformAdmin = (next: ConfiguredPlatformAdmin | null) => {
    latestAdminRef.current = next;
    setPlatformAdmin(next);
  };

  const persistLocalSnapshot = (next: CachedPlatformSetupState) => {
    latestSnapshotRef.current = next;
    writeCachedPlatformSetupState(next);
  };

  const markMutated = (slices?: readonly PlatformSetupMutatedSlice[]) => {
    hasMutatedSinceMountRef.current = true;
    slices?.forEach((slice) => mutatedSlicesRef.current.add(slice));
  };

  const applySnapshotToState = (next: CachedPlatformSetupState) => {
    latestSnapshotRef.current = next;
    setSnapshot(next);
  };

  const sliceSetters = createSnapshotSliceSetters(latestSnapshotRef, setSnapshot);

  const resetAllSetupState = () => {
    updatePlatformAdmin(null);
    setAccostageCounts(null);
    applySnapshotToState(EMPTY_CACHED_PLATFORM_SETUP_STATE);
  };

  const persistSnapshotStrict = async (next: CachedPlatformSetupState): Promise<void> =>
    persistSetupSnapshotStrict({
      locale,
      next,
      hasMutatedSinceMountRef,
      mutatedSlicesRef,
      latestSnapshotRef,
      setLastSyncError,
    });

  const persistSnapshot = (next: CachedPlatformSetupState) => {
    void persistSnapshotStrict(next).catch((err: unknown) => {
      console.warn("[orcia:platformSetup.persistSnapshot]", err instanceof Error ? err.message : String(err));
    });
  };

  const refreshAccostage = async (): Promise<void> =>
    executeRefreshAccostage({
      locale,
      orgUnits: snapshot.orgUnits,
      llmTiers: snapshot.llmTiers,
      setAccostageCounts,
      setLlmTiers: sliceSetters.setLlmTiers,
      buildSnapshot,
      persistLocalSnapshot,
    });

  usePlatformSetupHydrationEffect({
    locale,
    isAuthHydrating,
    isAuthenticated,
    currentUserEmail,
    platformAdmin,
    hasMutatedSinceMountRef,
    mutatedSlicesRef,
    latestSnapshotRef,
    latestAdminRef,
    applySnapshotToState,
    resetAllSetupState,
    setIsInitialLoading,
    setPlatformAdmin: updatePlatformAdmin,
    setAccostageCounts,
    setLastSyncError,
  });

  const buildSnapshot = (
    overrides: Partial<CachedPlatformSetupState>,
  ): CachedPlatformSetupState => mergeCachedPlatformSetupSnapshot(latestSnapshotRef.current, overrides);

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
  ): CachedPlatformSetupState["auditEvents"] =>
    appendPlatformSetupAuditEvent({
      auditEvents: latestSnapshotRef.current.auditEvents,
      platformAdmin,
      eventType,
      summary,
      meta,
    });

  const governanceActions = createPlatformGovernanceActions({
    locale,
    platformAdmin,
    ...snapshot,
    ...sliceSetters,
    setPlatformAdmin: updatePlatformAdmin,
    setLastSyncError,
    markMutated,
    appendAudit,
    buildSnapshot,
    persistLocalSnapshot,
    persistSnapshot,
  });

  const workspaceActions = createPlatformWorkspaceActions({
    locale,
    platformAdmin,
    orgUnits: snapshot.orgUnits,
    workflows: snapshot.workflows,
    workspaces: snapshot.workspaces,
    datasources: snapshot.datasources,
    getLatestSnapshot: () => latestSnapshotRef.current,
    setWorkspaces: sliceSetters.setWorkspaces,
    setDatasources: sliceSetters.setDatasources,
    setAuditEvents: sliceSetters.setAuditEvents,
    markMutated,
    appendAudit,
    buildSnapshot,
    persistLocalSnapshot,
    persistSnapshotStrict,
    setLastSyncError,
  });

  const scopes = buildScopeNodes(snapshot.orgUnits, snapshot.workspaces, locale);
  const accostageSummary = computeAccostageProgressSummary({
    accostageCounts,
    platformAdmin,
    orgUnits: snapshot.orgUnits,
    llmTiers: snapshot.llmTiers,
    workspaces: snapshot.workspaces,
    datasources: snapshot.datasources,
    workflows: snapshot.workflows,
    packs: snapshot.packs,
  });
  const completedSetupStepsCount = accostageSummary.completedCount;
  const isDay0Complete = accostageSummary.isDay0Complete;
  const workflowOverrides: ControlCenterOverrideItem[] =
    buildWorkflowOverridesFromWorkflows(snapshot.workflows);

  return (
    <PlatformSetupContext.Provider
      value={{
        isInitialLoading,
        lastSyncError,
        platformAdmin,
        ...snapshot,
        workflowOverrides,
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
  if (!ctx) throw new ClientCodedError("ERR_CLIENT_CONTEXT_MISSING", { detail: "PlatformSetupProvider" });
  return ctx;
}

export function useOptionalPlatformSetup(): PlatformSetupContextValue | null {
  return useContext(PlatformSetupContext);
}
