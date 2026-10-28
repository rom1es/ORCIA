import type {
  AuthTokenResponse,
  LocalLoginRequest,
  LogoutResponse,
  OidcLoginRequest,
  PassthroughSecretMetadataResponse,
  PassthroughSecretStoreRequest,
  ScopeMutationCheckResponse,
  UserMeResponse,
  WorkspacesListResponse,
} from "../generated/auth_and_org";
import type { HealthResponse, ShellNavigationResponse } from "../generated/shell";
import { buildPersonaQuery, type createRequestJson } from "../helpers";

type RequestJsonFn = ReturnType<typeof createRequestJson>;

export function createAuthAndShellDomainClient(requestJson: RequestJsonFn) {
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
  };
}
