import {
  createOrciaApiClient,
  type DelegateGrantRequest,
  type IamAccountCreateRequest,
  type IamAccountPatchRequest,
  type IamAccountResponse,
  type RoleMatrixEntryResponse,
  type RolePermissionGrantResponse,
} from "@orcia/api-client";
import type { ConfiguredRbacGrant } from "../../../components/platformSetupStorageHelpers";
import { extractLocalizedApiError } from "../../../lib/formatRfc9457ErrorToBanner";
import { useAuthSessionStore } from "../../../stores/authSessionStore";

export type OfficialIamRoleKey =
  | "PLATFORM_ADMIN"
  | "SECOPS"
  | "BU_LEAD"
  | "TEAM_LEAD"
  | "ONTOLOGY_LEAD"
  | "CONTRIBUTOR"
  | "OBSERVER";

export const OFFICIAL_IAM_ROLES: readonly OfficialIamRoleKey[] = [
  "PLATFORM_ADMIN",
  "SECOPS",
  "BU_LEAD",
  "TEAM_LEAD",
  "ONTOLOGY_LEAD",
  "CONTRIBUTOR",
  "OBSERVER",
] as const;

export type GrantResourceKindKey =
  | "ALL"
  | "WORKFLOW"
  | "AGENT"
  | "DATASOURCE"
  | "CONNECTOR";

export const GRANT_RESOURCE_KINDS: readonly GrantResourceKindKey[] = [
  "ALL",
  "WORKFLOW",
  "AGENT",
  "DATASOURCE",
  "CONNECTOR",
] as const;

export type IamAccountsListApiResult =
  | { readonly ok: true; readonly accounts: readonly IamAccountResponse[] }
  | { readonly ok: false; readonly errorMessage: string; readonly errorCode?: string };

export type IamAccountMutationApiResult =
  | {
      readonly ok: true;
      readonly account: IamAccountResponse;
      readonly temporaryPassword?: string | null;
    }
  | { readonly ok: false; readonly errorMessage: string; readonly errorCode?: string };

export type IamAccountTemporaryPasswordResetApiResult =
  | {
      readonly ok: true;
      readonly temporaryPassword: string;
      readonly expiresAtIso?: string;
    }
  | { readonly ok: false; readonly errorMessage: string; readonly errorCode?: string };

export type IamAccountDeleteApiResult =
  | { readonly ok: true; readonly deletedId: string }
  | { readonly ok: false; readonly errorMessage: string; readonly errorCode?: string };

export type IamRoleMatrixApiResult =
  | {
      readonly ok: true;
      readonly secretVisibility: string;
      readonly roles: readonly RoleMatrixEntryResponse[];
    }
  | { readonly ok: false; readonly errorMessage: string; readonly errorCode?: string };

export type IamGrantsListApiResult =
  | { readonly ok: true; readonly grants: readonly ConfiguredRbacGrant[] }
  | { readonly ok: false; readonly errorMessage: string; readonly errorCode?: string };

export type IamGrantDeleteApiResult =
  | { readonly ok: true; readonly deletedId: string }
  | { readonly ok: false; readonly errorMessage: string; readonly errorCode?: string };

export function mapGrantDtoToConfigured(dto: RolePermissionGrantResponse): ConfiguredRbacGrant {
  return {
    id: dto.id,
    subjectType: dto.subject_type,
    subjectId: dto.subject_id,
    scopePath: dto.scope_path,
    verb: dto.verb,
    effect: dto.effect,
    resourceKind: dto.resource_kind ?? "ALL",
  };
}

function buildIamClient(locale: "fr" | "en") {
  const { readOnlyObserver, activeHat } = useAuthSessionStore.getState();
  return createOrciaApiClient({
    baseUrl: "",
    locale,
    extraHeaders: () => ({
      ...(readOnlyObserver ? { "X-Orcia-Access-Mode": "READ_ONLY_OBSERVER" } : {}),
      "X-Orcia-Active-Hat": activeHat,
    }),
  });
}

function extractIamApiError(
  err: unknown,
  locale: "fr" | "en",
): { readonly errorMessage: string; readonly errorCode?: string } {
  return extractLocalizedApiError(err, locale, "ERR_CLIENT_IAM_NETWORK");
}

export async function fetchIamRoleMatrixFromApi(
  locale: "fr" | "en",
): Promise<IamRoleMatrixApiResult> {
  try {
    const client = buildIamClient(locale);
    const resp = await client.getIamRoleMatrix();
    const roles = Array.isArray(resp.roles) ? resp.roles : [];
    return {
      ok: true,
      secretVisibility: roles[0]?.secret_visibility ?? "WRITE_ONLY_NEVER_READABLE",
      roles,
    };
  } catch (err: unknown) {
    return { ok: false, ...extractIamApiError(err, locale) };
  }
}

export async function fetchIamAccountsFromApi(
  locale: "fr" | "en",
): Promise<IamAccountsListApiResult> {
  try {
    const client = buildIamClient(locale);
    const resp = await client.listIamAccounts();
    return {
      ok: true,
      accounts: Array.isArray(resp.accounts) ? resp.accounts : [],
    };
  } catch (err: unknown) {
    return { ok: false, ...extractIamApiError(err, locale) };
  }
}

export async function createIamAccountViaApi(
  payload: IamAccountCreateRequest,
  locale: "fr" | "en",
): Promise<IamAccountMutationApiResult> {
  try {
    const client = buildIamClient(locale);
    const rawResp = (await client.createIamAccount(payload)) as unknown as Record<string, unknown>;
    const account = (rawResp.account ?? rawResp) as IamAccountResponse;
    const temporaryPassword =
      (rawResp.temporary_password as string | undefined) ??
      (account as unknown as { temporary_password?: string }).temporary_password ??
      null;
    return {
      ok: true,
      account,
      temporaryPassword,
    };
  } catch (err: unknown) {
    return { ok: false, ...extractIamApiError(err, locale) };
  }
}

export async function resetIamAccountTemporaryPasswordViaApi(
  accountId: string,
  locale: "fr" | "en",
): Promise<IamAccountTemporaryPasswordResetApiResult> {
  try {
    const client = buildIamClient(locale);
    const resp = await client.resetIamAccountTemporaryPassword(accountId);
    return {
      ok: true,
      temporaryPassword: resp.temporary_password,
      expiresAtIso: (resp as unknown as { expires_at_iso?: string }).expires_at_iso,
    };
  } catch (err: unknown) {
    return { ok: false, ...extractIamApiError(err, locale) };
  }
}

export async function updateIamAccountViaApi(
  accountId: string,
  payload: IamAccountPatchRequest,
  locale: "fr" | "en",
): Promise<IamAccountMutationApiResult> {
  try {
    const client = buildIamClient(locale);
    const account = await client.updateIamAccount(accountId, payload);
    return { ok: true, account };
  } catch (err: unknown) {
    return { ok: false, ...extractIamApiError(err, locale) };
  }
}

export async function deleteIamAccountViaApi(
  accountId: string,
  locale: "fr" | "en",
): Promise<IamAccountDeleteApiResult> {
  try {
    const client = buildIamClient(locale);
    const resp = await client.deleteIamAccount(accountId);
    return { ok: true, deletedId: resp.deleted_id };
  } catch (err: unknown) {
    return { ok: false, ...extractIamApiError(err, locale) };
  }
}

export async function fetchIamGrantsFromApi(
  locale: "fr" | "en",
): Promise<IamGrantsListApiResult> {
  try {
    const client = buildIamClient(locale);
    const resp = await client.listIamGrants();
    return {
      ok: true,
      grants: Array.isArray(resp) ? resp.map(mapGrantDtoToConfigured) : [],
    };
  } catch (err: unknown) {
    return { ok: false, ...extractIamApiError(err, locale) };
  }
}

export async function createIamGrantsViaApi(
  input: Omit<DelegateGrantRequest, "actor_persona">,
  locale: "fr" | "en",
): Promise<IamGrantsListApiResult> {
  try {
    const { roles, activeHat } = useAuthSessionStore.getState();
    const actorPersona =
      roles.includes("SECOPS") || activeHat === "SECOPS" ? "karim" : "marc";
    const client = buildIamClient(locale);
    const created = await client.createIamGrant({
      ...input,
      actor_persona: actorPersona,
    });
    return {
      ok: true,
      grants: Array.isArray(created) ? created.map(mapGrantDtoToConfigured) : [],
    };
  } catch (err: unknown) {
    return { ok: false, ...extractIamApiError(err, locale) };
  }
}

export async function deleteIamGrantViaApi(
  grantId: string,
  locale: "fr" | "en",
): Promise<IamGrantDeleteApiResult> {
  try {
    const { roles, activeHat } = useAuthSessionStore.getState();
    const actorPersona =
      roles.includes("SECOPS") || activeHat === "SECOPS" ? "karim" : "marc";
    const client = buildIamClient(locale);
    const resp = await client.deleteIamGrant(grantId, actorPersona);
    return { ok: true, deletedId: resp.deleted_id };
  } catch (err: unknown) {
    return { ok: false, ...extractIamApiError(err, locale) };
  }
}
