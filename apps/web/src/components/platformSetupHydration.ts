import {
  createOrciaApiClient,
  type PlatformSetupStatePutRequest,
  type PlatformSetupStateResponse,
} from "@orcia/api-client";
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

export function buildPlatformSetupPutPayload(
  next: CachedPlatformSetupState,
): PlatformSetupStatePutRequest {
  return {
    org_units: next.orgUnits as unknown as Record<string, unknown>[],
    rbac_grants: next.rbacGrants as unknown as Record<string, unknown>[],
    llm_tiers: next.llmTiers.map((t) => ({
      tier: t.tier,
      tierKey: t.tier,
      primaryModel: t.primaryModel,
      secondaryModel: t.secondaryModel,
      modelFamily: t.modelFamily,
      defaultEffort: t.defaultEffort,
      provider: t.modelFamily,
      model: t.primaryModel,
      endpointUrl: t.endpointUrl ?? "",
      authMode: t.authMode ?? "api_key",
      apiKeyConfigured: Boolean(t.apiKeyConfigured),
    })),
    workspaces: next.workspaces as unknown as Record<string, unknown>[],
    datasources: next.datasources as unknown as Record<string, unknown>[],
    packs: next.packs as unknown as Record<string, unknown>[],
    workflows: next.workflows as unknown as Record<string, unknown>[],
    runs: next.runs as unknown as Record<string, unknown>[],
    catalog_items: next.catalogItems as unknown as Record<string, unknown>[],
    ontology_concepts: next.ontologyConcepts as unknown as Record<string, unknown>[],
    audit_events: next.auditEvents as unknown as Record<string, unknown>[],
  };
}

export async function savePlatformSetupSnapshotToApi(
  next: CachedPlatformSetupState,
): Promise<PlatformSetupStateResponse> {
  const client = createOrciaApiClient({ baseUrl: resolveWebApiBaseUrl() });
  return client.savePlatformSetupState(buildPlatformSetupPutPayload(next));
}

export interface AccostagePg18CountsView {
  readonly adminCreated: boolean;
  readonly usersCount: number;
  readonly orgUnitsCount: number;
  readonly workspacesCount: number;
  readonly modelsCount: number;
  readonly sourcesCount: number;
  readonly workflowsCount: number;
}

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
}): Promise<HydrationOutcome> {
  const client = createOrciaApiClient({ baseUrl: resolveWebApiBaseUrl() });
  const status = await client.getAccostageStatus();
  const [setupSettled, orgUnitsSettled, iamGrantsSettled] = params.isAuthenticated
    ? await Promise.allSettled([
        client.getPlatformSetupState(),
        client.listOrgUnits(),
        client.listIamGrants(),
      ])
    : ([
        { status: "rejected", reason: null },
        { status: "rejected", reason: null },
        { status: "rejected", reason: null },
      ] as const);
  if (params.isAuthenticated) {
    const queryNames = ["getPlatformSetupState", "listOrgUnits", "listIamGrants"] as const;
    [setupSettled, orgUnitsSettled, iamGrantsSettled].forEach((settled, idx) => {
      if (settled.status === "rejected") {
        console.warn(`[orcia:hydration.${queryNames[idx]}]`, settled.reason);
      }
    });
    if (setupSettled.status === "rejected") {
      throw setupSettled.reason instanceof Error
        ? setupSettled.reason
        : new Error("Échec d'hydratation de l'état plateforme.");
    }
  }
  const remoteState = setupSettled.status === "fulfilled" ? setupSettled.value : null;
  const remoteOrgUnitsResp = orgUnitsSettled.status === "fulfilled" ? orgUnitsSettled.value : null;
  const remoteIamGrantsResp = iamGrantsSettled.status === "fulfilled" ? iamGrantsSettled.value : null;

  if (syncBrowserBootEpoch(status.boot_epoch)) {
    return { kind: "BOOT_EPOCH_RESET" };
  }

  const mappedApiOrgUnits: ConfiguredOrgUnit[] = (remoteOrgUnitsResp?.org_units ?? []).map(
    (dto) => {
      const rawLeads = Array.isArray(dto.lead_user_ids) ? dto.lead_user_ids : [];
      const leadUserIds =
        rawLeads.length > 0 ? rawLeads : dto.lead_user_id ? [dto.lead_user_id] : [];
      return {
        id: dto.id,
        name: dto.name,
        slug: dto.slug,
        level: dto.kind,
        parentId: dto.parent_id ?? "scope-global",
        billingEnabled: dto.billing_enabled ?? true,
        leadUserId: leadUserIds[0] ?? dto.lead_user_id ?? null,
        leadUserIds,
        ontologyLeadUserIds:
          dto.kind === "BU" && Array.isArray(dto.ontology_lead_user_ids)
            ? dto.ontology_lead_user_ids
            : [],
        memberUserIds: dto.kind === "BU" ? [] : (dto.member_user_ids ?? []),
        attachedWorkspacesCount: dto.attached_workspaces_count ?? 0,
        attachedWorkspaces: Array.isArray(dto.attached_workspaces)
          ? dto.attached_workspaces.map((w) => ({ id: w.id, slug: w.slug, name: w.name }))
          : [],
      };
    },
  );

  const mappedApiGrants: ConfiguredRbacGrant[] = Array.isArray(remoteIamGrantsResp)
    ? remoteIamGrantsResp.map((g) => ({
        id: g.id,
        subjectType: g.subject_type,
        subjectId: g.subject_id,
        scopePath: g.scope_path,
        verb: g.verb,
        effect: g.effect,
        resourceKind: g.resource_kind ?? "ALL",
      }))
    : [];

  const accostageCounts: AccostagePg18CountsView = {
    adminCreated: Boolean(status.admin_created ?? status.first_admin_initialized),
    usersCount: status.users_count ?? (status.first_admin_initialized ? 1 : 0),
    orgUnitsCount:
      status.org_units_count ??
      mappedApiOrgUnits.filter((u) => u.level === "BU" || u.level === "TEAM").length,
    workspacesCount: status.workspaces_count ?? 0,
    modelsCount: status.models_count ?? 0,
    sourcesCount: status.sources_count ?? 0,
    workflowsCount: status.workflows_count ?? 0,
  };

  if (
    status.first_admin_initialized === false &&
    mappedApiOrgUnits.length === 0 &&
    mappedApiGrants.length === 0
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

  if (!remoteState && mappedApiOrgUnits.length === 0 && mappedApiGrants.length === 0) {
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
  const rWorkspaces = remoteState?.workspaces ?? [];
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
