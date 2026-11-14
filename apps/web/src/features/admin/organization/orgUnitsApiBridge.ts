import {
  createOrciaApiClient,
  OrciaProblemError,
  type OrgUnitCreateRequest,
  type OrgUnitPatchRequest,
  type OrgUnitResponse,
} from "@orcia/api-client";
import type { KnownUserOption } from "@orcia/ui";
import type { ConfiguredOrgUnit } from "../../../components/platformSetupStorageHelpers";
import { useAuthSessionStore } from "../../../stores/authSessionStore";

export type OrgUnitsApiListResult =
  | {
      readonly ok: true;
      readonly units: readonly ConfiguredOrgUnit[];
      readonly knownUsers: readonly KnownUserOption[];
    }
  | { readonly ok: false; readonly errorMessage: string; readonly errorCode?: string };

export type OrgUnitApiMutationResult =
  | { readonly ok: true; readonly unit: ConfiguredOrgUnit }
  | { readonly ok: false; readonly errorMessage: string; readonly errorCode?: string };

export type OrgUnitApiDeleteResult =
  | { readonly ok: true; readonly deletedId: string }
  | { readonly ok: false; readonly errorMessage: string; readonly errorCode?: string };

export function mapOrgUnitDtoToConfigured(dto: OrgUnitResponse): ConfiguredOrgUnit {
  return {
    id: dto.id,
    name: dto.name,
    slug: dto.slug,
    level: dto.kind,
    parentId: dto.parent_id ?? "scope-global",
    billingEnabled: dto.billing_enabled ?? true,
    leadUserId: dto.lead_user_id ?? null,
    memberUserIds: dto.member_user_ids ?? [],
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
      return { ok: true, units: [], knownUsers: [] };
    }
    const mappedKnownUsers: KnownUserOption[] = Array.isArray(response.known_users)
      ? response.known_users.map((u) => ({
          principalId: u.principal_id,
          displayName: u.display_name,
          email: u.email ?? null,
        }))
      : [];
    return {
      ok: true,
      units: response.org_units.map(mapOrgUnitDtoToConfigured),
      knownUsers: mappedKnownUsers,
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
    const dto = await client.createOrgUnit(payload);
    return { ok: true, unit: mapOrgUnitDtoToConfigured(dto) };
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
    return { ok: true, unit: mapOrgUnitDtoToConfigured(dto) };
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
      return { ok: true, units: [], knownUsers: [] };
    }
    const mappedKnownUsers: KnownUserOption[] = Array.isArray(response.known_users)
      ? response.known_users.map((u) => ({
          principalId: u.principal_id,
          displayName: u.display_name,
          email: u.email ?? null,
        }))
      : [];
    return {
      ok: true,
      units: response.org_units.map(mapOrgUnitDtoToConfigured),
      knownUsers: mappedKnownUsers,
    };
  } catch (err: unknown) {
    return { ok: false, ...extractApiError(err, locale) };
  }
}
