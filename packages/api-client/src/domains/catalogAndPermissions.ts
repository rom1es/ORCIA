import type {
  CatalogResourceInspectionResponse,
  CatalogResourceSourceResponse,
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
  PermissionBrokerStateResponse,
  PermissionCheckRequest,
  PermissionCheckResponse,
  PermissionPolicyImportMarkdownRequest,
  PermissionPolicyImportMarkdownResponse,
  PermissionTicketActionRequest,
  PermissionTicketActionResponse,
} from "../generated/permission_broker";
import { buildPersonaQuery, type createRequestJson } from "../helpers";

type RequestJsonFn = ReturnType<typeof createRequestJson>;

export function createCatalogAndPermissionsDomainClient(requestJson: RequestJsonFn) {
  return {
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
