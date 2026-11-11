import type {
  CatalogResourceInspectionResponse,
  CatalogResourceSourceResponse,
  OrgUnitCreateRequest,
  OrgUnitDeleteResponse,
  OrgUnitPatchRequest,
  OrgUnitResponse,
  OrgUnitsListResponse,
} from "../generated/auth_and_org";
import type {
  BmadSkillPackImportRequest,
  BmadSkillPackImportResponse,
  CasObjectResponse,
  CatalogItemsListResponse,
  CatalogPromoteRequest,
  CatalogPromoteResponse,
  CatalogUriResolveRequest,
  CatalogUriResolveResponse,
  EffectiveWorkflowResolveRequest,
  EffectiveWorkflowResolveResponse,
} from "../generated/catalog";
import type {
  IamAccountCreateRequest,
  IamAccountDeleteResponse,
  IamAccountPatchRequest,
  IamAccountResponse,
  IamAccountsListResponse,
  RoleMatrixResponse,
} from "../generated/iam_accounts";
import type {
  PermissionBrokerStateResponse,
  PermissionCheckRequest,
  PermissionCheckResponse,
  PermissionPolicyImportMarkdownRequest,
  PermissionPolicyImportMarkdownResponse,
  PermissionTicketActionRequest,
  PermissionTicketActionResponse,
} from "../generated/permission_broker";
import type { components } from "../generated/schema";
import { buildPersonaQuery, type createRequestJson } from "../helpers";

type RequestJsonFn = ReturnType<typeof createRequestJson>;
type DelegateGrantRequest = components["schemas"]["DelegateGrantRequest"];
type RolePermissionGrantResponse = components["schemas"]["RolePermissionGrantResponse"];
type GrantDeleteResponse = components["schemas"]["GrantDeleteResponse"];

export function createCatalogAndPermissionsDomainClient(requestJson: RequestJsonFn) {
  return {
    listOrgUnits(personaKey?: string): Promise<OrgUnitsListResponse> {
      return requestJson<OrgUnitsListResponse>(`/api/v1/org-units${buildPersonaQuery(personaKey)}`);
    },
    createOrgUnit(
      payload: OrgUnitCreateRequest,
      personaKey?: string,
    ): Promise<OrgUnitResponse> {
      return requestJson<OrgUnitResponse>(
        `/api/v1/org-units${buildPersonaQuery(personaKey)}`,
        "POST",
        payload,
      );
    },
    updateOrgUnit(
      orgUnitId: string,
      payload: OrgUnitPatchRequest,
      personaKey?: string,
    ): Promise<OrgUnitResponse> {
      return requestJson<OrgUnitResponse>(
        `/api/v1/org-units/${encodeURIComponent(orgUnitId)}${buildPersonaQuery(personaKey)}`,
        "PATCH",
        payload,
      );
    },
    deleteOrgUnit(
      orgUnitId: string,
      personaKey?: string,
    ): Promise<OrgUnitDeleteResponse> {
      return requestJson<OrgUnitDeleteResponse>(
        `/api/v1/org-units/${encodeURIComponent(orgUnitId)}${buildPersonaQuery(personaKey)}`,
        "DELETE",
      );
    },
    getIamRoleMatrix(): Promise<RoleMatrixResponse> {
      return requestJson<RoleMatrixResponse>("/api/v1/settings/iam/role-matrix");
    },
    listIamAccounts(personaKey?: string): Promise<IamAccountsListResponse> {
      return requestJson<IamAccountsListResponse>(
        `/api/v1/settings/iam/accounts${buildPersonaQuery(personaKey)}`,
      );
    },
    createIamAccount(
      payload: IamAccountCreateRequest,
      personaKey?: string,
    ): Promise<IamAccountResponse> {
      return requestJson<IamAccountResponse>(
        `/api/v1/settings/iam/accounts${buildPersonaQuery(personaKey)}`,
        "POST",
        payload,
      );
    },
    updateIamAccount(
      accountId: string,
      payload: IamAccountPatchRequest,
      personaKey?: string,
    ): Promise<IamAccountResponse> {
      return requestJson<IamAccountResponse>(
        `/api/v1/settings/iam/accounts/${encodeURIComponent(accountId)}${buildPersonaQuery(personaKey)}`,
        "PATCH",
        payload,
      );
    },
    deleteIamAccount(
      accountId: string,
      personaKey?: string,
    ): Promise<IamAccountDeleteResponse> {
      return requestJson<IamAccountDeleteResponse>(
        `/api/v1/settings/iam/accounts/${encodeURIComponent(accountId)}${buildPersonaQuery(personaKey)}`,
        "DELETE",
      );
    },
    listIamGrants(scopePath?: string): Promise<RolePermissionGrantResponse[]> {
      const qs = scopePath ? `?scope_path=${encodeURIComponent(scopePath)}` : "";
      return requestJson<RolePermissionGrantResponse[]>(`/api/v1/settings/iam/grants${qs}`);
    },
    createIamGrant(payload: DelegateGrantRequest): Promise<RolePermissionGrantResponse[]> {
      return requestJson<RolePermissionGrantResponse[]>(
        "/api/v1/settings/iam/grants",
        "POST",
        payload,
      );
    },
    deleteIamGrant(grantId: string, actorPersona?: string): Promise<GrantDeleteResponse> {
      const qs = actorPersona ? `?actor_persona=${encodeURIComponent(actorPersona)}` : "";
      return requestJson<GrantDeleteResponse>(
        `/api/v1/settings/iam/grants/${encodeURIComponent(grantId)}${qs}`,
        "DELETE",
      );
    },
    inspectCatalogResource(
      resourceId: string,
      personaKey?: string,
    ): Promise<CatalogResourceInspectionResponse> {
      return requestJson<CatalogResourceInspectionResponse>(
        `/api/v1/catalog/resources/${encodeURIComponent(resourceId)}/inspect${buildPersonaQuery(personaKey)}`,
      );
    },
    getCatalogResourceSource(
      resourceId: string,
      personaKey?: string,
    ): Promise<CatalogResourceSourceResponse> {
      return requestJson<CatalogResourceSourceResponse>(
        `/api/v1/catalog/resources/${encodeURIComponent(resourceId)}/source${buildPersonaQuery(personaKey)}`,
      );
    },
    listCatalogItems(personaKey?: string): Promise<CatalogItemsListResponse> {
      return requestJson<CatalogItemsListResponse>(
        `/api/v1/catalog/items${buildPersonaQuery(personaKey)}`,
      );
    },
    promoteCatalogItem(
      resourceId: string,
      payload: CatalogPromoteRequest,
      personaKey?: string,
    ): Promise<CatalogPromoteResponse> {
      return requestJson<CatalogPromoteResponse>(
        `/api/v1/catalog/items/${encodeURIComponent(resourceId)}/promote${buildPersonaQuery(personaKey)}`,
        "POST",
        payload,
      );
    },
    resolveFederatedUri(
      payload: CatalogUriResolveRequest,
      personaKey?: string,
    ): Promise<CatalogUriResolveResponse> {
      return requestJson<CatalogUriResolveResponse>(
        `/api/v1/catalog/resolve${buildPersonaQuery(personaKey)}`,
        "POST",
        payload,
      );
    },
    getCasObject(sha256: string, personaKey?: string): Promise<CasObjectResponse> {
      return requestJson<CasObjectResponse>(
        `/api/v1/cas/${encodeURIComponent(sha256)}${buildPersonaQuery(personaKey)}`,
      );
    },
    resolveEffectiveWorkflow(
      payload: EffectiveWorkflowResolveRequest,
      personaKey?: string,
    ): Promise<EffectiveWorkflowResolveResponse> {
      return requestJson<EffectiveWorkflowResolveResponse>(
        `/api/v1/catalog/workflows/resolve-effective${buildPersonaQuery(personaKey)}`,
        "POST",
        payload,
      );
    },
    importBmadSkillPack(
      payload: BmadSkillPackImportRequest,
      personaKey?: string,
    ): Promise<BmadSkillPackImportResponse> {
      return requestJson<BmadSkillPackImportResponse>(
        `/api/v1/catalog/bmad-packs/import${buildPersonaQuery(personaKey)}`,
        "POST",
        payload,
      );
    },
    getPermissionBrokerState(
      personaKey?: string,
      workspaceId?: string,
    ): Promise<PermissionBrokerStateResponse> {
      const params = new URLSearchParams();
      if (personaKey) params.set("persona_key", personaKey);
      if (workspaceId) params.set("workspace_id", workspaceId);
      const qs = params.toString();
      return requestJson<PermissionBrokerStateResponse>(
        `/api/v1/permissions/broker/state${qs ? `?${qs}` : ""}`,
      );
    },
    importPermissionPolicyMarkdown(
      payload: PermissionPolicyImportMarkdownRequest,
      personaKey?: string,
    ): Promise<PermissionPolicyImportMarkdownResponse> {
      return requestJson<PermissionPolicyImportMarkdownResponse>(
        `/api/v1/permissions/broker/policies/import-markdown${buildPersonaQuery(personaKey)}`,
        "POST",
        payload,
      );
    },
    checkConnectorAccess(
      payload: PermissionCheckRequest,
      personaKey?: string,
    ): Promise<PermissionCheckResponse> {
      return requestJson<PermissionCheckResponse>(
        `/api/v1/permissions/broker/check-access${buildPersonaQuery(personaKey)}`,
        "POST",
        payload,
      );
    },
    applyPermissionTicketAction(
      ticketId: string,
      payload: PermissionTicketActionRequest,
      personaKey?: string,
    ): Promise<PermissionTicketActionResponse> {
      return requestJson<PermissionTicketActionResponse>(
        `/api/v1/permissions/broker/tickets/${encodeURIComponent(ticketId)}/action${buildPersonaQuery(personaKey)}`,
        "POST",
        payload,
      );
    },
  };
}
