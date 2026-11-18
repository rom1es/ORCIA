import {
  createOrciaApiClient,
  OrciaProblemError,
  type OrgUnitCreateRequest,
  type OrgUnitInviteUserRequest,
  type OrgUnitInviteUserResponse,
  type OrgUnitPatchRequest,
  type OrgUnitResponse,
} from "@orcia/api-client";
import type { KnownUserOption } from "@orcia/ui";
import type { ConfiguredOrgUnit } from "../../../components/platformSetupStorageHelpers";
import { useAuthSessionStore } from "../../../stores/authSessionStore";

export interface OrgUnitServerCapabilities {
  readonly canEdit: boolean;
  readonly canCreateChild: boolean;
  readonly canDelete: boolean;
  readonly canManageMembers: boolean;
  readonly canManageOntologyLeads: boolean;
  readonly canInviteUsers: boolean;
}

export type OrgUnitsApiListResult =
  | {
      readonly ok: true;
      readonly units: readonly ConfiguredOrgUnit[];
      readonly knownUsers: readonly KnownUserOption[];
      readonly capabilitiesById: Record<string, OrgUnitServerCapabilities>;
    }
  | { readonly ok: false; readonly errorMessage: string; readonly errorCode?: string };

export type OrgUnitApiMutationResult =
  | {
      readonly ok: true;
      readonly unit: ConfiguredOrgUnit;
      readonly capabilities?: OrgUnitServerCapabilities;
    }
  | { readonly ok: false; readonly errorMessage: string; readonly errorCode?: string };

export type OrgUnitInviteApiResult =
  | {
      readonly ok: true;
      readonly invitation: OrgUnitInviteUserResponse;
      readonly unit: ConfiguredOrgUnit;
      readonly capabilities: OrgUnitServerCapabilities;
    }
  | { readonly ok: false; readonly errorMessage: string; readonly errorCode?: string };

export type OrgUnitApiDeleteResult =
  | { readonly ok: true; readonly deletedId: string }
  | { readonly ok: false; readonly errorMessage: string; readonly errorCode?: string };

export function extractOrgUnitCapabilities(dto: OrgUnitResponse): OrgUnitServerCapabilities {
  return {
    canEdit: dto.can_edit ?? true,
    canCreateChild: dto.can_create_child ?? dto.kind === "BU",
    canDelete: dto.can_delete ?? true,
    canManageMembers: dto.can_manage_members ?? dto.kind === "TEAM",
    canManageOntologyLeads: dto.can_manage_ontology_leads ?? dto.kind === "BU",
    canInviteUsers: dto.can_invite_users ?? true,
  };
}

export function mapOrgUnitDtoToConfigured(dto: OrgUnitResponse): ConfiguredOrgUnit {
  const rawLeads = Array.isArray(dto.lead_user_ids) ? dto.lead_user_ids : [];
  const leadUserIds = rawLeads.length > 0
    ? rawLeads
    : dto.lead_user_id ? [dto.lead_user_id] : [];
  const ontologyLeadUserIds =
    dto.kind === "BU" && Array.isArray(dto.ontology_lead_user_ids)
      ? dto.ontology_lead_user_ids
      : [];
  return {
    id: dto.id,
    name: dto.name,
    slug: dto.slug,
    level: dto.kind,
    parentId: dto.parent_id ?? "scope-global",
    billingEnabled: dto.billing_enabled ?? true,
    leadUserId: leadUserIds[0] ?? dto.lead_user_id ?? null,
    leadUserIds,
    ontologyLeadUserIds,
    memberUserIds: dto.kind === "BU" ? [] : (dto.member_user_ids ?? []),
    attachedWorkspacesCount: dto.attached_workspaces_count ?? 0,
    attachedWorkspaces: dto.attached_workspaces
      ? dto.attached_workspaces.map((w) => ({ id: w.id, slug: w.slug, name: w.name }))
      : [],
  };
}

function buildOrgUnitsClient(locale: "fr" | "en") {
  const { readOnlyObserver, activeHat } = useAuthSessionStore.getState();
  const customFetch: typeof fetch = (input, init) => {
    const headers = new Headers(init?.headers);
    if (readOnlyObserver) {
      headers.set("X-Orcia-Access-Mode", "READ_ONLY_OBSERVER");
    }
    headers.set("X-Orcia-Active-Hat", activeHat);
    return globalThis.fetch(input, { ...init, headers });
  };
  return createOrciaApiClient({
    baseUrl: "",
    locale,
    fetchImpl: customFetch,
  });
}

function extractApiError(
  err: unknown,
  locale: "fr" | "en",
): { readonly errorMessage: string; readonly errorCode?: string } {
  if (err instanceof OrciaProblemError) {
    return {
      errorMessage: err.problem.detail || err.problem.title,
      errorCode: err.problem.error_code,
    };
  }
  if (err instanceof Error && err.message.trim().length > 0) {
    return { errorMessage: err.message };
  }
  return {
    errorMessage:
      locale === "fr"
        ? "Une erreur réseau est survenue lors de la mise à jour de l'organigramme."
        : "A network error occurred while updating the organization hierarchy.",
  };
}

export function isKnownUserIdentifier(
  identifier: string,
  knownUsers: readonly KnownUserOption[],
): boolean {
  const trimmed = identifier.trim().toLowerCase();
  if (!trimmed) return true;
  return knownUsers.some(
    (u) =>
      u.principalId.trim().toLowerCase() === trimmed ||
      (u.email ? u.email.trim().toLowerCase() === trimmed : false),
  );
}

export async function fetchOrgUnitsFromApi(
  locale: "fr" | "en",
): Promise<OrgUnitsApiListResult> {
  try {
    const client = buildOrgUnitsClient(locale);
    const response = await client.listOrgUnits();
    if (!Array.isArray(response.org_units)) {
      return { ok: true, units: [], knownUsers: [], capabilitiesById: {} };
    }
    const mappedKnownUsers: KnownUserOption[] = Array.isArray(response.known_users)
      ? response.known_users.map((u) => ({
          principalId: u.principal_id,
          displayName: u.display_name,
          email: u.email ?? null,
        }))
      : [];
    const capabilitiesById: Record<string, OrgUnitServerCapabilities> = {};
    for (const dto of response.org_units) {
      capabilitiesById[dto.id] = extractOrgUnitCapabilities(dto);
    }
    return {
      ok: true,
      units: response.org_units.map(mapOrgUnitDtoToConfigured),
      knownUsers: mappedKnownUsers,
      capabilitiesById,
    };
  } catch (err: unknown) {
    return { ok: false, ...extractApiError(err, locale) };
  }
}

export const fetchOrgUnitsWithKnownUsersFromApi = fetchOrgUnitsFromApi;

export async function createOrgUnitViaApi(
  payload: OrgUnitCreateRequest,
  locale: "fr" | "en",
): Promise<OrgUnitApiMutationResult> {
  try {
    const client = buildOrgUnitsClient(locale);
    const sanitizedPayload: OrgUnitCreateRequest = {
      ...payload,
      member_user_ids: payload.kind === "BU" ? [] : payload.member_user_ids,
      ontology_lead_user_ids: payload.kind === "BU" ? (payload.ontology_lead_user_ids ?? []) : [],
    };
    const dto = await client.createOrgUnit(sanitizedPayload);
    return {
      ok: true,
      unit: mapOrgUnitDtoToConfigured(dto),
      capabilities: extractOrgUnitCapabilities(dto),
    };
  } catch (err: unknown) {
    return { ok: false, ...extractApiError(err, locale) };
  }
}

export async function patchOrgUnitViaApi(
  orgUnitId: string,
  payload: OrgUnitPatchRequest,
  locale: "fr" | "en",
): Promise<OrgUnitApiMutationResult> {
  try {
    const client = buildOrgUnitsClient(locale);
    const dto = await client.updateOrgUnit(orgUnitId, payload);
    return {
      ok: true,
      unit: mapOrgUnitDtoToConfigured(dto),
      capabilities: extractOrgUnitCapabilities(dto),
    };
  } catch (err: unknown) {
    return { ok: false, ...extractApiError(err, locale) };
  }
}

export async function inviteOrgUnitUserViaApi(
  payload: OrgUnitInviteUserRequest,
  locale: "fr" | "en",
): Promise<OrgUnitInviteApiResult> {
  try {
    const client = buildOrgUnitsClient(locale);
    const res = await client.inviteOrgUnitUser(payload);
    return {
      ok: true,
      invitation: res,
      unit: mapOrgUnitDtoToConfigured(res.org_unit),
      capabilities: extractOrgUnitCapabilities(res.org_unit),
    };
  } catch (err: unknown) {
    return { ok: false, ...extractApiError(err, locale) };
  }
}

export async function deleteOrgUnitViaApi(
  orgUnitId: string,
  locale: "fr" | "en",
): Promise<OrgUnitApiDeleteResult> {
  try {
    const client = buildOrgUnitsClient(locale);
    const dto = await client.deleteOrgUnit(orgUnitId);
    return { ok: true, deletedId: dto.deleted_id };
  } catch (err: unknown) {
    return { ok: false, ...extractApiError(err, locale) };
  }
}

export async function searchParentBuUnitsFromApi(
  query: string,
  limit = 10,
  locale: "fr" | "en" = "fr",
): Promise<OrgUnitsApiListResult> {
  try {
    const client = buildOrgUnitsClient(locale);
    const response = await client.listOrgUnits({
      q: query.trim() || undefined,
      kind: "BU",
      limit,
    });
    if (!Array.isArray(response.org_units)) {
      return { ok: true, units: [], knownUsers: [], capabilitiesById: {} };
    }
    const mappedKnownUsers: KnownUserOption[] = Array.isArray(response.known_users)
      ? response.known_users.map((u) => ({
          principalId: u.principal_id,
          displayName: u.display_name,
          email: u.email ?? null,
        }))
      : [];
    const capabilitiesById: Record<string, OrgUnitServerCapabilities> = {};
    for (const dto of response.org_units) {
      capabilitiesById[dto.id] = extractOrgUnitCapabilities(dto);
    }
    return {
      ok: true,
      units: response.org_units.map(mapOrgUnitDtoToConfigured),
      knownUsers: mappedKnownUsers,
      capabilitiesById,
    };
  } catch (err: unknown) {
    return { ok: false, ...extractApiError(err, locale) };
  }
}

export type KnownOrgUsersSearchResult =
  | {
      readonly ok: true;
      readonly items: readonly KnownUserOption[];
      readonly hasMore: boolean;
    }
  | {
      readonly ok: false;
      readonly items: readonly KnownUserOption[];
      readonly hasMore: boolean;
      readonly errorMessage: string;
      readonly errorCode?: string;
    };

export async function searchKnownOrgUsersFromApi(
  query: string,
  limit = 10,
  locale: "fr" | "en" = "fr",
): Promise<KnownOrgUsersSearchResult> {
  try {
    const client = buildOrgUnitsClient(locale);
    const response = await client.searchKnownOrgUsers({
      q: query.trim() || undefined,
      limit,
    });
    const items: KnownUserOption[] = Array.isArray(response.items)
      ? response.items.map((u) => ({
          principalId: u.principal_id,
          displayName: u.display_name,
          email: u.email ?? null,
        }))
      : [];
    return {
      ok: true,
      items,
      hasMore: Boolean(response.has_more),
    };
  } catch (err: unknown) {
    return { ok: false, items: [], hasMore: false, ...extractApiError(err, locale) };
  }
}
