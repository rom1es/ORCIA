import {
  createOrciaApiClient,
  type AccostageStatusResponse,
  type PlatformSetupStatePutRequest,
  type PlatformSetupStateResponse,
} from "@orcia/api-client";

type ApiClient = ReturnType<typeof createOrciaApiClient>;
type OrgUnitsTreeResult = Awaited<ReturnType<ApiClient["listOrgUnits"]>>;
type RbacGrantsResult = Awaited<ReturnType<ApiClient["listIamGrants"]>>;
type WorkspacesResult = Awaited<ReturnType<ApiClient["listWorkspaces"]>>;
import type { ControlCenterWorkspaceGovItem } from "@orcia/ui";
import { resolveWebApiBaseUrl } from "../stores/authSessionStore";
import type {
  CachedPlatformSetupState,
  ConfiguredOrgUnit,
  ConfiguredRbacGrant,
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
    workspaces: next.workspaces.filter(
      (ws) => !ws.slug?.startsWith("personal-"),
    ) as unknown as Record<string, unknown>[],
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
  readonly platformAdminDisplayName?: string | null;
  readonly visibleMilestoneKeys?: readonly string[] | null;
}

export function buildAccostageCountsFromStatus(
  status: AccostageStatusResponse,
  orgUnits: readonly ConfiguredOrgUnit[] = [],
): AccostagePg18CountsView {
  const visibleMilestoneKeys = Array.isArray(status.visible_milestones)
    ? status.visible_milestones
        .filter((m) => m.is_accessible !== false)
        .map((m) => m.key)
    : null;
  const platformAdminDisplayName =
    status.platform_admin_display_name ?? status.first_admin_display_name ?? null;

  return {
    adminCreated: Boolean(status.admin_created ?? status.first_admin_initialized),
    usersCount: status.users_count ?? (status.first_admin_initialized ? 1 : 0),
    orgUnitsCount:
      status.org_units_count ??
      orgUnits.filter((u) => u.level === "BU" || u.level === "TEAM").length,
    workspacesCount: status.workspaces_count ?? 0,
    modelsCount: status.models_count ?? 0,
    sourcesCount: status.sources_count ?? 0,
    workflowsCount: status.workflows_count ?? 0,
    platformAdminDisplayName,
    visibleMilestoneKeys,
  };
}

export function mapRemoteApiOrgUnits(
  resp: OrgUnitsTreeResult | null,
): ConfiguredOrgUnit[] {
  return (resp?.org_units ?? []).map((dto) => {
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
  });
}

export function mapRemoteApiRbacGrants(
  resp: RbacGrantsResult | null,
): ConfiguredRbacGrant[] {
  return Array.isArray(resp)
    ? resp.map((g) => ({
        id: g.id,
        subjectType: g.subject_type,
        subjectId: g.subject_id,
        scopePath: g.scope_path,
        verb: g.verb,
        effect: g.effect,
        resourceKind: g.resource_kind ?? "ALL",
      }))
    : [];
}

export function mapRemoteApiWorkspaces(params: {
  readonly resp: WorkspacesResult | null;
  readonly orgUnits: readonly ConfiguredOrgUnit[];
  readonly snapWorkspaces: readonly ControlCenterWorkspaceGovItem[];
  readonly fallbackOwnerEmail: string;
}): ControlCenterWorkspaceGovItem[] {
  return (params.resp?.workspaces ?? []).map((wsDto) => {
    const matchedOrg = params.orgUnits.find((u) => u.id === wsDto.owner_org_unit_id);
    const snapMatch = params.snapWorkspaces.find(
      (s) => s.workspaceId === wsDto.id || (wsDto.slug && s.slug === wsDto.slug),
    );
    return {
      workspaceId: wsDto.id,
      slug: wsDto.slug,
      name: wsDto.name,
      visibilityMode: wsDto.visibility_mode,
      ownerOrgUnitId: wsDto.owner_org_unit_id,
      ...(matchedOrg
        ? { ownerOrgUnitName: matchedOrg.name }
        : snapMatch?.ownerOrgUnitName
          ? { ownerOrgUnitName: snapMatch.ownerOrgUnitName }
          : {}),
      ...(wsDto.is_personal ? { ownerUserId: params.fallbackOwnerEmail } : {}),
      lifecyclePhase: snapMatch?.lifecyclePhase ?? "BUILD",
      suggestedWorkflows: snapMatch?.suggestedWorkflows ?? [],
      accessMode: wsDto.access_mode,
      finopsCostUsd: wsDto.finops_cost_usd ?? 0,
    };
  });
}
