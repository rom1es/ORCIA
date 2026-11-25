import type {
  ControlCenterDatasourceItem,
  ControlCenterWorkspaceGovItem,
  ProductLifecyclePhaseType,
} from "@orcia/ui";
import type { SupportedWebLocale } from "../i18n";
import type {
  CachedPlatformSetupState,
  ConfiguredAuditEvent,
  ConfiguredOrgUnit,
  ConfiguredPlatformAdmin,
  ConfiguredWorkflowItem,
} from "./platformSetupStorageHelpers";
import {
  applyRegisterDatasource,
  applyWorkspacePhaseUpdate,
  applyWorkspaceVisibilityUpdate,
  createWorkspaceViaServer,
  patchWorkspaceViaServer,
  type CreateWorkspaceInput,
  type RegisterDatasourceInput,
} from "./platformSetupWorkspaces";
import type { PlatformSetupMutatedSlice } from "./usePlatformSetupHydrationEffect";

export function createPlatformWorkspaceActions(params: {
  readonly locale?: SupportedWebLocale;
  readonly platformAdmin: ConfiguredPlatformAdmin | null;
  readonly orgUnits: readonly ConfiguredOrgUnit[];
  readonly workflows: readonly ConfiguredWorkflowItem[];
  readonly workspaces: readonly ControlCenterWorkspaceGovItem[];
  readonly datasources: readonly ControlCenterDatasourceItem[];
  readonly getLatestSnapshot?: () => CachedPlatformSetupState;
  readonly setWorkspaces: (next: readonly ControlCenterWorkspaceGovItem[]) => void;
  readonly setDatasources: (next: readonly ControlCenterDatasourceItem[]) => void;
  readonly setAuditEvents: (next: readonly ConfiguredAuditEvent[]) => void;
  readonly markMutated: (slices?: readonly PlatformSetupMutatedSlice[]) => void;
  readonly appendAudit: (
    eventType: string,
    summary: string,
    meta?: {
      readonly scopeId?: string;
      readonly scopePath?: string;
      readonly scopeLabel?: string;
    },
  ) => readonly ConfiguredAuditEvent[];
  readonly buildSnapshot: (
    overrides: Partial<CachedPlatformSetupState>,
  ) => CachedPlatformSetupState;
  readonly persistLocalSnapshot: (next: CachedPlatformSetupState) => void;
  readonly persistSnapshotStrict: (next: CachedPlatformSetupState) => Promise<void>;
  readonly setLastSyncError?: (v: string | null) => void;
}) {
  const {
    locale = "fr",
    platformAdmin,
    orgUnits,
    workflows,
    workspaces,
    datasources,
    getLatestSnapshot,
    setWorkspaces,
    setDatasources,
    setAuditEvents,
    markMutated,
    appendAudit,
    buildSnapshot,
    persistLocalSnapshot,
    persistSnapshotStrict,
    setLastSyncError,
  } = params;

  const readLatestWorkspaces = (): readonly ControlCenterWorkspaceGovItem[] =>
    getLatestSnapshot ? getLatestSnapshot().workspaces : workspaces;

  const readLatestDatasources = (): readonly ControlCenterDatasourceItem[] =>
    getLatestSnapshot ? getLatestSnapshot().datasources : datasources;

  const createWorkspace = async (
    input: CreateWorkspaceInput,
  ): Promise<ControlCenterWorkspaceGovItem> => {
    const { workspace, auditEvent } = await createWorkspaceViaServer({
      locale,
      input,
      orgUnits: getLatestSnapshot ? getLatestSnapshot().orgUnits : orgUnits,
      workflows: getLatestSnapshot ? getLatestSnapshot().workflows : workflows,
      platformAdmin,
    });
    markMutated(["workspaces", "auditEvents"]);
    const currentWorkspaces = readLatestWorkspaces();
    const nextWorkspaces = [
      ...currentWorkspaces.filter((ws) => ws.workspaceId !== workspace.workspaceId),
      workspace,
    ];
    const nextAudit = appendAudit(auditEvent.eventType, auditEvent.summary, {
      scopeId: auditEvent.scopeId,
      scopePath: auditEvent.scopePath,
      scopeLabel: auditEvent.scopeLabel,
    });
    setWorkspaces(nextWorkspaces);
    setAuditEvents(nextAudit);
    persistLocalSnapshot(buildSnapshot({ workspaces: nextWorkspaces, auditEvents: nextAudit }));
    setLastSyncError?.(null);
    return workspace;
  };

  const updateWorkspacePhase = async (
    workspaceId: string,
    phase: ProductLifecyclePhaseType,
  ): Promise<void> => {
    const patched = await patchWorkspaceViaServer({
      locale,
      workspaceId,
      payload: { lifecycle_phase: phase },
    });
    markMutated(["workspaces", "auditEvents"]);
    const { nextWorkspaces, nextAudit } = applyWorkspacePhaseUpdate({
      locale,
      workspaces: readLatestWorkspaces(),
      workspaceId,
      phase: patched.lifecycle_phase,
      appendAudit,
    });
    setWorkspaces(nextWorkspaces);
    setAuditEvents(nextAudit);
    persistLocalSnapshot(buildSnapshot({ workspaces: nextWorkspaces, auditEvents: nextAudit }));
    setLastSyncError?.(null);
  };

  const updateWorkspaceVisibility = async (
    workspaceId: string,
    visibilityMode: "STANDARD" | "CONFIDENTIAL_RESTRICTED" | "PRIVATE_USER",
  ): Promise<void> => {
    const patched = await patchWorkspaceViaServer({
      locale,
      workspaceId,
      payload: { visibility_mode: visibilityMode },
    });
    markMutated(["workspaces", "auditEvents"]);
    const { nextWorkspaces, nextAudit } = applyWorkspaceVisibilityUpdate({
      locale,
      workspaces: readLatestWorkspaces(),
      workspaceId,
      visibilityMode: patched.visibility_mode,
      appendAudit,
    });
    const syncedWorkspaces = nextWorkspaces.map((ws) =>
      ws.workspaceId === workspaceId ? { ...ws, accessMode: patched.access_mode } : ws,
    );
    setWorkspaces(syncedWorkspaces);
    setAuditEvents(nextAudit);
    persistLocalSnapshot(buildSnapshot({ workspaces: syncedWorkspaces, auditEvents: nextAudit }));
    setLastSyncError?.(null);
  };

  const registerDatasource = async (input: RegisterDatasourceInput): Promise<void> => {
    const { nextDatasources, nextAudit } = applyRegisterDatasource({
      locale,
      datasources: readLatestDatasources(),
      input,
      appendAudit,
    });
    setDatasources(nextDatasources);
    setAuditEvents(nextAudit);
    await persistSnapshotStrict(
      buildSnapshot({ datasources: nextDatasources, auditEvents: nextAudit }),
    );
  };

  return {
    createWorkspace,
    updateWorkspacePhase,
    updateWorkspaceVisibility,
    registerDatasource,
  };
}
