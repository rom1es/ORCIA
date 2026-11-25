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
import type { AccostageProgressSummary } from "./platformSetupAccostage";
import type { AccostagePg18CountsView } from "./platformSetupHydration";
import {
  formatHumanReadableScopePath,
  normalizeConfiguredAuditEvent,
  type CachedPlatformSetupState,
  type ConfiguredAuditEvent,
  type ConfiguredLlmTierMapping,
  type ConfiguredOrgUnit,
  type ConfiguredPackItem,
  type ConfiguredPlatformAdmin,
  type ConfiguredRbacGrant,
  type ConfiguredWorkflowItem,
} from "./platformSetupStorageHelpers";
import type {
  CreateWorkspaceInput,
  RegisterDatasourceInput,
} from "./platformSetupWorkspaces";
export { createPlatformWorkspaceActions } from "./platformSetupWorkspaceActions";

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
  readonly accostageCounts: AccostagePg18CountsView | null;
  readonly accostageSummary: AccostageProgressSummary;
  readonly isDay0Complete: boolean;
  readonly completedSetupStepsCount: number;
  readonly refreshAccostage: () => Promise<void>;
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

export const EMPTY_CACHED_PLATFORM_SETUP_STATE: CachedPlatformSetupState = {
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
};

export function appendPlatformSetupAuditEvent(params: {
  readonly auditEvents: readonly ConfiguredAuditEvent[];
  readonly platformAdmin: ConfiguredPlatformAdmin | null;
  readonly eventType: string;
  readonly summary: string;
  readonly meta?: {
    readonly actorName?: string;
    readonly actorEmail?: string;
    readonly scopeId?: string;
    readonly scopePath?: string;
    readonly scopeLabel?: string;
  };
}): readonly ConfiguredAuditEvent[] {
  const { auditEvents, platformAdmin, eventType, summary, meta } = params;
  return [
    normalizeConfiguredAuditEvent(
      {
        id: `evt-${auditEvents.length + 1}`,
        timestampIso: new Date().toISOString(),
        eventType,
        summary,
        actorName: meta?.actorName ?? platformAdmin?.displayName ?? "",
        actorEmail: meta?.actorEmail ?? platformAdmin?.email,
        scopeId: meta?.scopeId,
        scopePath: meta?.scopePath ?? "GLOBAL",
        scopeLabel: meta?.scopeLabel ?? formatHumanReadableScopePath(meta?.scopePath ?? "GLOBAL"),
      },
      platformAdmin,
    ),
    ...auditEvents,
  ];
}

export function createSnapshotSliceSetters(
  latestSnapshotRef: { current: CachedPlatformSetupState },
  setSnapshot: (next: CachedPlatformSetupState) => void,
) {
  const updateSlice = <K extends keyof CachedPlatformSetupState>(
    key: K,
    value: CachedPlatformSetupState[K],
  ) => {
    const next = { ...latestSnapshotRef.current, [key]: value };
    latestSnapshotRef.current = next;
    setSnapshot(next);
  };
  return {
    setOrgUnits: (v: CachedPlatformSetupState["orgUnits"]) => updateSlice("orgUnits", v),
    setRbacGrants: (v: CachedPlatformSetupState["rbacGrants"]) => updateSlice("rbacGrants", v),
    setLlmTiers: (v: CachedPlatformSetupState["llmTiers"]) => updateSlice("llmTiers", v),
    setWorkspaces: (v: CachedPlatformSetupState["workspaces"]) => updateSlice("workspaces", v),
    setDatasources: (v: CachedPlatformSetupState["datasources"]) => updateSlice("datasources", v),
    setPacks: (v: CachedPlatformSetupState["packs"]) => updateSlice("packs", v),
    setWorkflows: (v: CachedPlatformSetupState["workflows"]) => updateSlice("workflows", v),
    setRuns: (v: CachedPlatformSetupState["runs"]) => updateSlice("runs", v),
    setCatalogItems: (v: CachedPlatformSetupState["catalogItems"]) =>
      updateSlice("catalogItems", v),
    setOntologyConcepts: (v: CachedPlatformSetupState["ontologyConcepts"]) =>
      updateSlice("ontologyConcepts", v),
    setAuditEvents: (v: CachedPlatformSetupState["auditEvents"]) => updateSlice("auditEvents", v),
  };
}
