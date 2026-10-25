export type {
  AuthTokenResponse,
  BmadSkillPackImportRequest,
  BmadSkillPackImportResponse,
  BmadSkillStepInputItem,
  CasObjectResponse,
  CatalogItemResponse,
  CatalogItemsListResponse,
  CatalogPromoteRequest,
  CatalogPromoteResponse,
  CatalogResourceInspectionResponse,
  CatalogResourceSourceResponse,
  CatalogUriResolveRequest,
  CatalogUriResolveResponse,
  components,
  EffectiveWorkflowResolveRequest,
  EffectiveWorkflowResolveResponse,
  EvaluationLensItem,
  HealthResponse,
  HumanProfileBadge,
  LocalLoginRequest,
  LogoutResponse,
  OidcLoginRequest,
  OrgUnitTreeItem,
  PassthroughSecretMetadataResponse,
  PassthroughSecretStoreRequest,
  paths,
  ProblemDetails,
  RunLockManifestItem,
  RunLockSourceTripletItem,
  ScopeMutationCheckResponse,
  ScopeNode,
  ShellModuleItem,
  ShellNavigationResponse,
  UserMeResponse,
  WorkflowDefinitionResponseItem,
  WorkflowStepItem,
  WorkspaceDatasourceItem,
  WorkspacesListResponse,
  WorkspaceSummaryItem,
} from "./generated/schema";

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
  LocalLoginRequest,
  LogoutResponse,
  OidcLoginRequest,
  PassthroughSecretMetadataResponse,
  PassthroughSecretStoreRequest,
  ProblemDetails,
  ScopeMutationCheckResponse,
  ShellNavigationResponse,
  UserMeResponse,
  WorkspacesListResponse,
} from "./generated/schema";

export interface OrciaApiClientOptions {
  baseUrl: string;
  locale?: "fr" | "en";
  traceId?: string;
  accessToken?: string;
  fetchImpl?: typeof fetch;
}

export class OrciaProblemError extends Error {
  public readonly problem: ProblemDetails;

  constructor(problem: ProblemDetails) {
    super(problem.detail);
    this.name = "OrciaProblemError";
    this.problem = problem;
  }
}

export function createOrciaApiClient(options: OrciaApiClientOptions) {
  const fetcher = options.fetchImpl ?? globalThis.fetch;
  const baseHeaders: Record<string, string> = {
    Accept: "application/json, application/problem+json",
    "Accept-Language": options.locale ?? "fr",
  };
  if (options.traceId) {
    baseHeaders["X-Trace-Id"] = options.traceId;
  }
  if (options.accessToken) {
    baseHeaders.Authorization = `Bearer ${options.accessToken}`;
  }

  async function requestJson<T>(
    path: string,
    method: "GET" | "POST" = "GET",
    body?: unknown,
  ): Promise<T> {
    const headers: Record<string, string> = { ...baseHeaders };
    const init: RequestInit = { method, headers };
    if (body !== undefined) {
      headers["Content-Type"] = "application/json";
      init.body = JSON.stringify(body);
    }
    const response = await fetcher(`${options.baseUrl}${path}`, init);
    if (!response.ok) {
      const fallbackTraceId =
        response.headers?.get?.("x-trace-id") ??
        options.traceId ??
        "00000000000000000000000000000000";
      const problem = (await Promise.resolve()
        .then(() => response.json())
        .catch(
          (): ProblemDetails => ({
            type: "about:blank",
            title: response.statusText || "HTTP Error",
            status: response.status || 500,
            detail: response.statusText || "Unexpected non-JSON error response",
            instance: path,
            error_code: "ERR_INTERNAL_SERVER_ERROR",
            trace_id: fallbackTraceId,
          }),
        )) as ProblemDetails;
      throw new OrciaProblemError(problem);
    }
    return (await response.json()) as T;
  }

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
      const query = personaKey ? `?persona_key=${encodeURIComponent(personaKey)}` : "";
      return requestJson<UserMeResponse>(`/api/v1/auth/me${query}`);
    },
    listWorkspaces(personaKey?: string): Promise<WorkspacesListResponse> {
      const query = personaKey ? `?persona_key=${encodeURIComponent(personaKey)}` : "";
      return requestJson<WorkspacesListResponse>(`/api/v1/workspaces${query}`);
    },
    checkWorkspaceMutation(
      workspaceId: string,
      personaKey?: string,
    ): Promise<ScopeMutationCheckResponse> {
      const query = personaKey ? `?persona_key=${encodeURIComponent(personaKey)}` : "";
      return requestJson<ScopeMutationCheckResponse>(
        `/api/v1/workspaces/${encodeURIComponent(workspaceId)}/mutations/check${query}`,
        "POST",
      );
    },
    inspectCatalogResource(
      resourceId: string,
      personaKey?: string,
    ): Promise<CatalogResourceInspectionResponse> {
      const query = personaKey ? `?persona_key=${encodeURIComponent(personaKey)}` : "";
      return requestJson<CatalogResourceInspectionResponse>(
        `/api/v1/catalog/resources/${encodeURIComponent(resourceId)}/inspect${query}`,
      );
    },
    getCatalogResourceSource(
      resourceId: string,
      personaKey?: string,
    ): Promise<CatalogResourceSourceResponse> {
      const query = personaKey ? `?persona_key=${encodeURIComponent(personaKey)}` : "";
      return requestJson<CatalogResourceSourceResponse>(
        `/api/v1/catalog/resources/${encodeURIComponent(resourceId)}/source${query}`,
      );
    },
    storePassthroughCredential(
      payload: PassthroughSecretStoreRequest,
      personaKey?: string,
    ): Promise<PassthroughSecretMetadataResponse> {
      const query = personaKey ? `?persona_key=${encodeURIComponent(personaKey)}` : "";
      return requestJson<PassthroughSecretMetadataResponse>(
        `/api/v1/auth/passthrough-credentials${query}`,
        "POST",
        payload,
      );
    },
    listCatalogItems(personaKey?: string): Promise<CatalogItemsListResponse> {
      const query = personaKey ? `?persona_key=${encodeURIComponent(personaKey)}` : "";
      return requestJson<CatalogItemsListResponse>(`/api/v1/catalog/items${query}`);
    },
    promoteCatalogItem(
      resourceId: string,
      payload: CatalogPromoteRequest,
      personaKey?: string,
    ): Promise<CatalogPromoteResponse> {
      const query = personaKey ? `?persona_key=${encodeURIComponent(personaKey)}` : "";
      return requestJson<CatalogPromoteResponse>(
        `/api/v1/catalog/items/${encodeURIComponent(resourceId)}/promote${query}`,
        "POST",
        payload,
      );
    },
    resolveFederatedUri(
      payload: CatalogUriResolveRequest,
      personaKey?: string,
    ): Promise<CatalogUriResolveResponse> {
      const query = personaKey ? `?persona_key=${encodeURIComponent(personaKey)}` : "";
      return requestJson<CatalogUriResolveResponse>(
        `/api/v1/catalog/resolve${query}`,
        "POST",
        payload,
      );
    },
    getCasObject(sha256: string, personaKey?: string): Promise<CasObjectResponse> {
      const query = personaKey ? `?persona_key=${encodeURIComponent(personaKey)}` : "";
      return requestJson<CasObjectResponse>(
        `/api/v1/cas/${encodeURIComponent(sha256)}${query}`,
      );
    },
    resolveEffectiveWorkflow(
      payload: EffectiveWorkflowResolveRequest,
      personaKey?: string,
    ): Promise<EffectiveWorkflowResolveResponse> {
      const query = personaKey ? `?persona_key=${encodeURIComponent(personaKey)}` : "";
      return requestJson<EffectiveWorkflowResolveResponse>(
        `/api/v1/catalog/workflows/resolve-effective${query}`,
        "POST",
        payload,
      );
    },
    importBmadSkillPack(
      payload: BmadSkillPackImportRequest,
      personaKey?: string,
    ): Promise<BmadSkillPackImportResponse> {
      const query = personaKey ? `?persona_key=${encodeURIComponent(personaKey)}` : "";
      return requestJson<BmadSkillPackImportResponse>(
        `/api/v1/catalog/bmad-packs/import${query}`,
        "POST",
        payload,
      );
    },
  };
}
