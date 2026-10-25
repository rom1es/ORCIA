export type * from "./generated/schema";
export { OrciaProblemError, type OrciaApiClientOptions } from "./helpers";

import type {
  AuthTokenResponse,
  BmadSkillPackImportRequest,
  BmadSkillPackImportResponse,
  CasObjectResponse,
  CatalogItemsListResponse,
  CatalogPromoteRequest,
  CatalogPromoteResponse,
  CatalogResourceInspectionResponse,
  CatalogResourceSourceResponse,
  CatalogUriResolveRequest,
  CatalogUriResolveResponse,
  EffectiveWorkflowResolveRequest,
  EffectiveWorkflowResolveResponse,
  HealthResponse,
  InitDatasourceRequest,
  InitDatasourceResponse,
  InitOrganizationRequest,
  InitOrganizationResponse,
  InitUserRequest,
  InitUserResponse,
  InitWorkspaceRequest,
  InitWorkspaceResponse,
  LocalLoginRequest,
  LogoutResponse,
  OidcLoginRequest,
  PassthroughSecretMetadataResponse,
  PassthroughSecretStoreRequest,
  PermissionBrokerStateResponse,
  PermissionCheckRequest,
  PermissionCheckResponse,
  PermissionPolicyImportMarkdownRequest,
  PermissionPolicyImportMarkdownResponse,
  PermissionTicketActionRequest,
  PermissionTicketActionResponse,
  ScopeMutationCheckResponse,
  ShellNavigationResponse,
  SystemBootstrapStateResponse,
  UserMeResponse,
  WorkspacesListResponse,
} from "./generated/schema";
import { buildPersonaQuery, createRequestJson, type OrciaApiClientOptions } from "./helpers";

export function createOrciaApiClient(options: OrciaApiClientOptions) {
  const requestJson = createRequestJson(options);

  return {
    getHealth(): Promise<HealthResponse> {
      return requestJson<HealthResponse>("/api/v1/health");
    },
    getShellNavigation(scopeId?: string, personaKey?: string): Promise<ShellNavigationResponse> {
      const params = new URLSearchParams();
      if (scopeId) params.set("scope_id", scopeId);
      if (personaKey) params.set("persona_key", personaKey);
      const qs = params.toString();
      return requestJson<ShellNavigationResponse>(
        `/api/v1/navigation/shell${qs ? `?${qs}` : ""}`,
      );
    },
    loginLocal(payload: LocalLoginRequest): Promise<AuthTokenResponse> {
      return requestJson<AuthTokenResponse>("/api/v1/auth/login/local", "POST", payload);
    },
    loginOidc(payload: OidcLoginRequest): Promise<AuthTokenResponse> {
      return requestJson<AuthTokenResponse>("/api/v1/auth/login/oidc", "POST", payload);
    },
    refreshSession(): Promise<AuthTokenResponse> {
      return requestJson<AuthTokenResponse>("/api/v1/auth/refresh", "POST");
    },
    logoutSession(): Promise<LogoutResponse> {
      return requestJson<LogoutResponse>("/api/v1/auth/logout", "POST");
    },
    getMe(personaKey?: string): Promise<UserMeResponse> {
      return requestJson<UserMeResponse>(`/api/v1/auth/me${buildPersonaQuery(personaKey)}`);
    },
    listWorkspaces(personaKey?: string): Promise<WorkspacesListResponse> {
      return requestJson<WorkspacesListResponse>(
        `/api/v1/workspaces${buildPersonaQuery(personaKey)}`,
      );
    },
    checkWorkspaceMutation(
      workspaceId: string,
      personaKey?: string,
    ): Promise<ScopeMutationCheckResponse> {
      return requestJson<ScopeMutationCheckResponse>(
        `/api/v1/workspaces/${encodeURIComponent(workspaceId)}/mutations/check${buildPersonaQuery(personaKey)}`,
        "POST",
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
    storePassthroughCredential(
      payload: PassthroughSecretStoreRequest,
      personaKey?: string,
    ): Promise<PassthroughSecretMetadataResponse> {
      return requestJson<PassthroughSecretMetadataResponse>(
        `/api/v1/auth/passthrough-credentials${buildPersonaQuery(personaKey)}`,
        "POST",
        payload,
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
    getSystemBootstrapState(personaKey?: string): Promise<SystemBootstrapStateResponse> {
      return requestJson<SystemBootstrapStateResponse>(
        `/api/v1/bootstrap/state${buildPersonaQuery(personaKey)}`,
      );
    },
    executeInitOrganization(
      payload: InitOrganizationRequest,
      personaKey?: string,
    ): Promise<InitOrganizationResponse> {
      return requestJson<InitOrganizationResponse>(
        `/api/v1/bootstrap/init-organization${buildPersonaQuery(personaKey)}`,
        "POST",
        payload,
      );
    },
    executeInitWorkspace(
      payload: InitWorkspaceRequest,
      personaKey?: string,
    ): Promise<InitWorkspaceResponse> {
      return requestJson<InitWorkspaceResponse>(
        `/api/v1/bootstrap/init-workspace${buildPersonaQuery(personaKey)}`,
        "POST",
        payload,
      );
    },
    executeInitDatasource(
      payload: InitDatasourceRequest,
      personaKey?: string,
    ): Promise<InitDatasourceResponse> {
      return requestJson<InitDatasourceResponse>(
        `/api/v1/bootstrap/init-datasource${buildPersonaQuery(personaKey)}`,
        "POST",
        payload,
      );
    },
    executeInitUser(payload: InitUserRequest, personaKey?: string): Promise<InitUserResponse> {
      return requestJson<InitUserResponse>(
        `/api/v1/bootstrap/init-user${buildPersonaQuery(personaKey)}`,
        "POST",
        payload,
      );
    },
  };
}
