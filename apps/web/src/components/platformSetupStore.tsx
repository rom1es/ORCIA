import type {
  ControlCenterDatasourceItem,
  ControlCenterOverrideItem,
  ControlCenterRunItem,
  ControlCenterWorkspaceGovItem,
  ProductLifecyclePhaseType,
  UiCatalogExplorerItemView,
  UiOntologyConceptView,
  UiOntologyLevel,
  UiScopeNode,
} from "@orcia/ui";
import React, { createContext, useContext, useEffect, useRef, useState } from "react";
import { useAuthSessionStore } from "../stores/authSessionStore";
import { createPlatformGovernanceActions } from "./platformSetupGovernanceActions";
import {
  fetchAndBuildHydrationOutcome,
  savePlatformSetupSnapshotToApi,
} from "./platformSetupHydration";
import {
  cleanAuditSummaryJargon,
  clearPlatformSetupStorage,
  deduplicateConfiguredPacks,
  formatHumanReadableScopePath,
  normalizeConfiguredAuditEvent,
  PLATFORM_ADMIN_STORAGE_KEY,
  PLATFORM_SETUP_STATE_STORAGE_KEY,
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
  type LlmAuthMode,
} from "./platformSetupStorageHelpers";
import {
  applyRegisterDatasource,
  applyWorkspacePhaseUpdate,
  applyWorkspaceVisibilityUpdate,
  buildScopeNodes,
  createWorkspaceViaServer,
  type CreateWorkspaceInput,
  type RegisterDatasourceInput,
} from "./platformSetupWorkspaces";

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
};

const isVitest =
  typeof process !== "undefined" &&
  (process.env?.NODE_ENV === "test" || process.env?.VITEST === "true");

export interface PlatformSetupContextValue {
  readonly isInitialLoading: boolean;
  readonly lastSyncError: string | null;
  readonly platformAdmin: ConfiguredPlatformAdmin | null;
  readonly orgUnits: readonly ConfiguredOrgUnit[];
  readonly rbacGrants: readonly ConfiguredRbacGrant[];
  readonly llmTiers: readonly ConfiguredLlmTierMapping[];
  readonly workspaces: readonly ControlCenterWorkspaceGovItem[];
  readonly datasources: readonly ControlCenterDatasourceItem[];
  readonly packs: readonly ConfiguredPackItem[];
  readonly workflows: readonly ConfiguredWorkflowItem[];
  readonly runs: readonly ControlCenterRunItem[];
  readonly catalogItems: readonly UiCatalogExplorerItemView[];
  readonly ontologyConcepts: readonly UiOntologyConceptView[];
  readonly workflowOverrides: readonly ControlCenterOverrideItem[];
  readonly auditEvents: readonly ConfiguredAuditEvent[];
  readonly scopes: readonly UiScopeNode[];
  readonly isDay0Complete: boolean;
  readonly completedSetupStepsCount: number;
  readonly createPlatformAdmin: (input: {
    displayName: string;
    email: string;
    password?: string;
  }) => void;
  readonly toggleAdminTeamMembership: (teamId: string) => void;
  readonly addOrgUnit: (
    input: Omit<ConfiguredOrgUnit, "id"> & { readonly attachCurrentAdmin?: boolean },
  ) => void;
  readonly removeOrgUnit: (orgUnitId: string) => {
    readonly deleted: boolean;
    readonly blockedReason: string | null;
  };
  readonly syncOrgUnitsFromServer: (
    units: readonly ConfiguredOrgUnit[],
    auditMeta?: {
      readonly eventType: string;
      readonly summary: string;
      readonly scopeId?: string;
      readonly scopePath?: string;
      readonly scopeLabel?: string;
    },
  ) => void;
  readonly addRbacGrant: (input: Omit<ConfiguredRbacGrant, "id">) => void;
  readonly removeRbacGrant: (grantId: string) => void;
  readonly syncRbacGrantsFromServer: (
    grants: readonly ConfiguredRbacGrant[],
    auditMeta?: {
      readonly eventType: string;
      readonly summary: string;
      readonly scopePath?: string;
      readonly scopeLabel?: string;
    },
  ) => void;
  readonly upsertLlmTier: (input: ConfiguredLlmTierMapping) => void;
  readonly createWorkspace: (
    input: CreateWorkspaceInput,
  ) => Promise<ControlCenterWorkspaceGovItem>;
  readonly updateWorkspacePhase: (
    workspaceId: string,
    phase: ProductLifecyclePhaseType,
  ) => Promise<void>;
  readonly updateWorkspaceVisibility: (
    workspaceId: string,
    visibilityMode: "STANDARD" | "CONFIDENTIAL_RESTRICTED" | "PRIVATE_USER",
  ) => Promise<void>;
  readonly registerDatasource: (input: RegisterDatasourceInput) => Promise<void>;
  readonly registerPack: (input: ConfiguredPackItem) => void;
  readonly removePack: (packKey: string, scopePath?: string) => void;
  readonly upsertWorkflow: (input: ConfiguredWorkflowItem) => void;
  readonly launchRun: (input: {
    workspaceId: string;
    workspaceName: string;
    title: string;
    workflowKey: string;
  }) => void;
  readonly addOntologyConcept: (input: UiOntologyConceptView) => void;
  readonly promoteOntologyConcept: (
    conceptKey: string,
    targetLevel: UiOntologyLevel,
    targetScopeId?: string,
  ) => void;
}

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
  const hasMutatedSinceMountRef = useRef(false);

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
    applySnapshotToState({
      orgUnits: [],
      rbacGrants: [],
      llmTiers: [],
      workspaces: [],
      datasources: [],
      packs: [],
      workflows: [],
      runs: [],
      catalogItems: [],
      ontologyConcepts: [],
      auditEvents: [],
    });
  };

  const persistSnapshotStrict = async (next: CachedPlatformSetupState): Promise<void> => {
    hasMutatedSinceMountRef.current = true;
    writeCachedPlatformSetupState(next);
    try {
      await savePlatformSetupSnapshotToApi(next);
      setLastSyncError(null);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Erreur de synchronisation plateforme.";
      setLastSyncError(msg);
      throw err;
    }
  };

  const persistSnapshot = (next: CachedPlatformSetupState) => {
    void persistSnapshotStrict(next).catch((err: unknown) => {
      const msg = err instanceof Error ? err.message : "Erreur de synchronisation plateforme.";
      setLastSyncError(msg);
    });
  };

  useEffect(() => {
    let cancelled = false;
    let safetyTimer: ReturnType<typeof setTimeout> | undefined = setTimeout(() => {
      if (!cancelled) setIsInitialLoading(false);
    }, 5000);

    void fetchAndBuildHydrationOutcome({
      hasMutatedSinceMount: hasMutatedSinceMountRef.current,
      currentAdmin: platformAdmin,
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
          if (outcome.admin) setPlatformAdmin(outcome.admin);
          if (outcome.snapshot) applySnapshotToState(outcome.snapshot);
        }
      })
      .catch((err: unknown) => {
        if (!cancelled) {
          setLastSyncError(
            err instanceof Error ? err.message : "Chargement initial plateforme interrompu.",
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
  }, []);

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
  ): readonly ConfiguredAuditEvent[] => [
    normalizeConfiguredAuditEvent(
      {
        id: `evt-${auditEvents.length + 1}`,
        timestampIso: new Date().toISOString(),
        eventType,
        summary,
        actorName:
          meta?.actorName ?? platformAdmin?.displayName ?? "Administrateur de la plateforme",
        actorEmail: meta?.actorEmail ?? platformAdmin?.email,
        scopeId: meta?.scopeId,
        scopePath: meta?.scopePath ?? "GLOBAL",
        scopeLabel: meta?.scopeLabel ?? formatHumanReadableScopePath(meta?.scopePath ?? "GLOBAL"),
      },
      platformAdmin,
    ),
    ...auditEvents,
  ];

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

  const createWorkspace = async (
    input: CreateWorkspaceInput,
  ): Promise<ControlCenterWorkspaceGovItem> => {
    hasMutatedSinceMountRef.current = true;
    const { workspace, auditEvent } = await createWorkspaceViaServer({
      input,
      orgUnits,
      workflows,
      platformAdmin,
    });
    const nextWorkspaces = [...workspaces, workspace];
    const nextAudit = appendAudit(auditEvent.eventType, auditEvent.summary, {
      scopeId: auditEvent.scopeId,
      scopePath: auditEvent.scopePath,
      scopeLabel: auditEvent.scopeLabel,
    });
    setWorkspaces(nextWorkspaces);
    setAuditEvents(nextAudit);
    await persistSnapshotStrict(
      buildSnapshot({ workspaces: nextWorkspaces, auditEvents: nextAudit }),
    );
    return workspace;
  };

  const updateWorkspacePhase = async (
    workspaceId: string,
    phase: ProductLifecyclePhaseType,
  ): Promise<void> => {
    const { nextWorkspaces, nextAudit } = applyWorkspacePhaseUpdate({
      workspaces,
      workspaceId,
      phase,
      appendAudit,
    });
    setWorkspaces(nextWorkspaces);
    setAuditEvents(nextAudit);
    await persistSnapshotStrict(
      buildSnapshot({ workspaces: nextWorkspaces, auditEvents: nextAudit }),
    );
  };

  const updateWorkspaceVisibility = async (
    workspaceId: string,
    visibilityMode: "STANDARD" | "CONFIDENTIAL_RESTRICTED" | "PRIVATE_USER",
  ): Promise<void> => {
    const { nextWorkspaces, nextAudit } = applyWorkspaceVisibilityUpdate({
      workspaces,
      workspaceId,
      visibilityMode,
      appendAudit,
    });
    setWorkspaces(nextWorkspaces);
    setAuditEvents(nextAudit);
    await persistSnapshotStrict(
      buildSnapshot({ workspaces: nextWorkspaces, auditEvents: nextAudit }),
    );
  };

  const registerDatasource = async (input: RegisterDatasourceInput): Promise<void> => {
    const { nextDatasources, nextAudit } = applyRegisterDatasource({
      datasources,
      input,
      appendAudit,
    });
    setDatasources(nextDatasources);
    setAuditEvents(nextAudit);
    await persistSnapshotStrict(
      buildSnapshot({ datasources: nextDatasources, auditEvents: nextAudit }),
    );
  };

  const scopes = buildScopeNodes(orgUnits, workspaces);
  const completedSetupStepsCount = [
    llmTiers.length > 0,
    orgUnits.length > 0 || rbacGrants.length > 0,
    workspaces.length > 0,
    datasources.length > 0,
    workflows.length > 0 || packs.length > 0,
  ].filter(Boolean).length;
  const isDay0Complete = completedSetupStepsCount === 5;
  const workflowOverrides: ControlCenterOverrideItem[] = workflows.map((wf) => ({
    workflowKey: wf.workflowKey,
    title: wf.title,
    baseLayer: `v${wf.version}`,
    teamOverride: "—",
    workspaceOverride: `${wf.layers.filter((l) => l.enabled).length} couches actives`,
    userOverride: "—",
    spineContractRef: "—",
  }));

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
        isDay0Complete,
        completedSetupStepsCount,
        ...governanceActions,
        createWorkspace,
        updateWorkspacePhase,
        updateWorkspaceVisibility,
        registerDatasource,
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
