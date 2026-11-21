import { createOrciaApiClient } from "@orcia/api-client";
import type {
  ControlCenterDatasourceItem,
  ControlCenterRunItem,
  ControlCenterWorkspaceGovItem,
  UiCatalogExplorerItemView,
  UiInferenceEffort,
  UiInferenceTier,
  UiOntologyConceptView,
} from "@orcia/ui";
import { resolveWebApiBaseUrl } from "../stores/authSessionStore";
import {
  buildAccostageCountsFromStatus,
  buildPlatformSetupPutPayload,
  mapRemoteApiOrgUnits,
  mapRemoteApiRbacGrants,
  mapRemoteApiWorkspaces,
  savePlatformSetupSnapshotToApi,
  type AccostagePg18CountsView,
} from "./platformSetupHydrationMappers";
import {
  deduplicateConfiguredPacks,
  normalizeConfiguredAuditEvent,
  readCachedPlatformAdmin,
  syncBrowserBootEpoch,
  writeCachedPlatformAdmin,
  writeCachedPlatformSetupState,
  type CachedPlatformSetupState,
  type ConfiguredAuditEvent,
  type ConfiguredOrgUnit,
  type ConfiguredPackItem,
  type ConfiguredPlatformAdmin,
  type ConfiguredRbacGrant,
  type ConfiguredWorkflowItem,
  type LlmAuthMode,
} from "./platformSetupStorageHelpers";

export {
  buildAccostageCountsFromStatus,
  buildPlatformSetupPutPayload,
  savePlatformSetupSnapshotToApi,
  type AccostagePg18CountsView,
};

export type HydrationOutcome =
  | { readonly kind: "BOOT_EPOCH_RESET" }
  | { readonly kind: "DAY0_CLEAN_RESET" }
  | {
      readonly kind: "HYDRATED";
      readonly admin: ConfiguredPlatformAdmin | null;
      readonly snapshot: CachedPlatformSetupState | null;
      readonly accostageCounts: AccostagePg18CountsView;
    }
  | { readonly kind: "NOOP" };

export async function fetchAndBuildHydrationOutcome(params: {
  readonly hasMutatedSinceMount: boolean;
  readonly currentAdmin: ConfiguredPlatformAdmin | null;
  readonly isAuthenticated: boolean;
  readonly currentUserEmail?: string | null;
}): Promise<HydrationOutcome> {
  const client = createOrciaApiClient({ baseUrl: resolveWebApiBaseUrl() });
  const status = await client.getAccostageStatus();
  const [setupSettled, orgUnitsSettled, iamGrantsSettled, workspacesSettled] =
    params.isAuthenticated
      ? await Promise.allSettled([
          client.getPlatformSetupState(),
          client.listOrgUnits(),
          client.listIamGrants(),
          client.listWorkspaces(),
        ])
      : ([
          { status: "rejected", reason: null },
          { status: "rejected", reason: null },
          { status: "rejected", reason: null },
          { status: "rejected", reason: null },
        ] as const);
  if (params.isAuthenticated) {
    const queryNames = [
      "getPlatformSetupState",
      "listOrgUnits",
      "listIamGrants",
      "listWorkspaces",
    ] as const;
    [setupSettled, orgUnitsSettled, iamGrantsSettled, workspacesSettled].forEach((settled, idx) => {
      if (settled.status === "rejected") {
        console.warn(`[orcia:hydration.${queryNames[idx]}]`, settled.reason);
      }
    });
    if (setupSettled.status === "rejected") {
      const err = setupSettled.reason;
      const problemStatus =
        typeof err === "object" && err !== null && "problem" in err
          ? (err as { problem?: { status?: number } }).problem?.status
          : undefined;
      if (problemStatus !== 403 && problemStatus !== 401) {
        throw err instanceof Error
          ? err
          : new Error("Échec d'hydratation de l'état plateforme.");
      }
    }
  }
  const rawSetup = setupSettled.status === "fulfilled" ? setupSettled.value : null;
  const remoteState = rawSetup && "workspaces" in rawSetup ? rawSetup : null;
  const remoteOrgUnitsResp = orgUnitsSettled.status === "fulfilled" ? orgUnitsSettled.value : null;
  const remoteIamGrantsResp = iamGrantsSettled.status === "fulfilled" ? iamGrantsSettled.value : null;
  const remoteWorkspacesResp =
    workspacesSettled.status === "fulfilled" ? workspacesSettled.value : null;

  if (syncBrowserBootEpoch(status.boot_epoch)) {
    return { kind: "BOOT_EPOCH_RESET" };
  }

  const mappedApiOrgUnits = mapRemoteApiOrgUnits(remoteOrgUnitsResp);
  const mappedApiGrants = mapRemoteApiRbacGrants(remoteIamGrantsResp ?? null);
  const accostageCounts = buildAccostageCountsFromStatus(status, mappedApiOrgUnits);
  const snapWsList = (remoteState?.workspaces ??
    []) as unknown as ControlCenterWorkspaceGovItem[];
  const mappedApiWorkspaces = mapRemoteApiWorkspaces({
    resp: remoteWorkspacesResp,
    orgUnits: mappedApiOrgUnits,
    snapWorkspaces: snapWsList,
    fallbackOwnerEmail:
      (params.currentUserEmail ?? "").trim() || status.first_admin_email || "session-user",
  });

  if (
    status.first_admin_initialized === false &&
    mappedApiOrgUnits.length === 0 &&
    mappedApiGrants.length === 0 &&
    mappedApiWorkspaces.length === 0
  ) {
    if (params.hasMutatedSinceMount || readCachedPlatformAdmin() !== null) {
      return { kind: "NOOP" };
    }
    writeCachedPlatformAdmin(null);
    writeCachedPlatformSetupState(null);
    return { kind: "DAY0_CLEAN_RESET" };
  }

  let syncedAdmin: ConfiguredPlatformAdmin | null = params.currentAdmin;
  if (status.first_admin_initialized && status.first_admin_email) {
    const existingLocal = readCachedPlatformAdmin();
    syncedAdmin = {
      displayName: status.first_admin_display_name ?? status.first_admin_email,
      email: status.first_admin_email,
      role: "PLATFORM_ADMIN",
      ...(existingLocal?.memberTeamIds ? { memberTeamIds: existingLocal.memberTeamIds } : {}),
    };
    writeCachedPlatformAdmin(syncedAdmin);
  }

  if (
    !remoteState &&
    mappedApiOrgUnits.length === 0 &&
    mappedApiGrants.length === 0 &&
    mappedApiWorkspaces.length === 0
  ) {
    return { kind: "HYDRATED", admin: syncedAdmin, snapshot: null, accostageCounts };
  }

  const rOrgUnits =
    mappedApiOrgUnits.length > 0
      ? mappedApiOrgUnits
      : ((remoteState?.org_units ?? []) as unknown as ConfiguredOrgUnit[]);
  const rRbacGrants =
    mappedApiGrants.length > 0
      ? mappedApiGrants
      : ((remoteState?.rbac_grants ?? []) as unknown as ConfiguredRbacGrant[]);
  const rLlmTiers = remoteState?.llm_tiers ?? [];
  const rWorkspaces =
    mappedApiWorkspaces.length > 0
      ? mappedApiWorkspaces
      : (remoteState?.workspaces ?? []);
  const rDatasources = remoteState?.datasources ?? [];
  const rPacks = remoteState?.packs ?? [];
  const rWorkflows = remoteState?.workflows ?? [];
  const rRuns = remoteState?.runs ?? [];
  const rCatalogItems = remoteState?.catalog_items ?? [];
  const rOntologyConcepts = remoteState?.ontology_concepts ?? [];
  const rAuditEvents = remoteState?.audit_events ?? [];

  const hasRemoteEntities =
    rOrgUnits.length > 0 ||
    rRbacGrants.length > 0 ||
    rLlmTiers.length > 0 ||
    rWorkspaces.length > 0 ||
    rDatasources.length > 0 ||
    rPacks.length > 0 ||
    rWorkflows.length > 0 ||
    rRuns.length > 0 ||
    rCatalogItems.length > 0 ||
    rOntologyConcepts.length > 0;

  if (!hasRemoteEntities) {
    return { kind: "HYDRATED", admin: syncedAdmin, snapshot: null, accostageCounts };
  }

  const hydrated: CachedPlatformSetupState = {
    orgUnits: rOrgUnits,
    rbacGrants: rRbacGrants,
    llmTiers: rLlmTiers.map((raw) => ({
      tier: (raw.tier ?? raw.tierKey ?? "medium") as UiInferenceTier,
      primaryModel: String(raw.primaryModel ?? raw.model ?? ""),
      secondaryModel: String(raw.secondaryModel ?? ""),
      modelFamily: String(raw.modelFamily ?? raw.provider ?? "Anthropic"),
      defaultEffort: (raw.defaultEffort ?? "balanced") as UiInferenceEffort,
      endpointUrl: raw.endpointUrl ? String(raw.endpointUrl) : undefined,
      authMode: (raw.authMode ?? "api_key") as LlmAuthMode,
      apiKeyConfigured: Boolean(raw.apiKeyConfigured),
    })),
    workspaces: rWorkspaces as unknown as ControlCenterWorkspaceGovItem[],
    datasources: rDatasources as unknown as ControlCenterDatasourceItem[],
    packs: deduplicateConfiguredPacks(rPacks as unknown as ConfiguredPackItem[]),
    workflows: rWorkflows as unknown as ConfiguredWorkflowItem[],
    runs: rRuns as unknown as ControlCenterRunItem[],
    catalogItems: rCatalogItems as unknown as UiCatalogExplorerItemView[],
    ontologyConcepts: rOntologyConcepts as unknown as UiOntologyConceptView[],
    auditEvents: (
      rAuditEvents as unknown as Array<Partial<ConfiguredAuditEvent> & Record<string, unknown>>
    ).map((ev) => normalizeConfiguredAuditEvent(ev, syncedAdmin)),
  };

  writeCachedPlatformSetupState(hydrated);

  if (
    !params.hasMutatedSinceMount &&
    status.first_admin_initialized &&
    status.first_admin_email
  ) {
    const remoteTeamIds = hydrated.orgUnits
      .filter((u) => u.level === "TEAM")
      .map((u) => u.id);
    const existingLocal = readCachedPlatformAdmin();
    const validLocalTeams = (existingLocal?.memberTeamIds ?? []).filter((id) =>
      remoteTeamIds.includes(id),
    );
    const effectiveTeamIds =
      validLocalTeams.length > 0 ? validLocalTeams : remoteTeamIds;
    if (effectiveTeamIds.length > 0) {
      syncedAdmin = {
        displayName: status.first_admin_display_name ?? status.first_admin_email,
        email: status.first_admin_email,
        role: "PLATFORM_ADMIN",
        memberTeamIds: effectiveTeamIds,
      };
      writeCachedPlatformAdmin(syncedAdmin);
    }
  }

  return { kind: "HYDRATED", admin: syncedAdmin, snapshot: hydrated, accostageCounts };
}
