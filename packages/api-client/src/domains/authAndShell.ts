import type {
  AuthTokenResponse,
  KnownOrgUsersSearchResponse,
  LocalLoginRequest,
  LogoutResponse,
  OidcLoginRequest,
  OrgUnitCreateRequest,
  OrgUnitDeleteResponse,
  OrgUnitPatchRequest,
  OrgUnitResponse,
  OrgUnitsListResponse,
  PassthroughSecretMetadataResponse,
  PassthroughSecretStoreRequest,
  ScopeMutationCheckResponse,
  UserMeResponse,
  WorkspaceCreateRequest,
  WorkspaceCreateResponse,
  WorkspacesListResponse,
} from "../generated/auth_and_org";
import type {
  AuthSessionBootstrapResponse,
  OidcAuthorizeUrlResponse,
  OidcCallbackExchangeRequest,
  PublicAuthConfigResponse,
  ResendLoginTwoFactorRequest,
  ResendLoginTwoFactorResponse,
  VerifyLoginTwoFactorRequest,
} from "../generated/auth_policy";
import type {
  ChangePasswordRequest,
  ChangePasswordResponse,
} from "../generated/iam_password_models";
import type { HealthResponse, ShellNavigationResponse } from "../generated/shell";
import type { UserProfileSummaryResponse } from "../generated/user_profile";
import {
  buildKnownOrgUsersQuery,
  buildOrgUnitsQuery,
  buildPersonaQuery,
  type createRequestJson,
  type ListKnownOrgUsersParams,
  type ListOrgUnitsParams,
} from "../helpers";

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
    getPublicAuthConfig(): Promise<PublicAuthConfigResponse> {
      return requestJson<PublicAuthConfigResponse>("/api/v1/auth/public-config");
    },
    getSessionBootstrap(): Promise<AuthSessionBootstrapResponse> {
      return requestJson<AuthSessionBootstrapResponse>("/api/v1/auth/session");
    },
    loginLocal(payload: LocalLoginRequest): Promise<AuthTokenResponse> {
      return requestJson<AuthTokenResponse>("/api/v1/auth/login/local", "POST", payload);
    },
    verifyLoginTwoFactor(payload: VerifyLoginTwoFactorRequest): Promise<AuthTokenResponse> {
      return requestJson<AuthTokenResponse>("/api/v1/auth/login/verify-2fa", "POST", payload);
    },
    resendLoginTwoFactor(
      payload: ResendLoginTwoFactorRequest,
    ): Promise<ResendLoginTwoFactorResponse> {
      return requestJson<ResendLoginTwoFactorResponse>(
        "/api/v1/auth/login/resend-2fa",
        "POST",
        payload,
      );
    },
    getOidcAuthorizeUrl(): Promise<OidcAuthorizeUrlResponse> {
      return requestJson<OidcAuthorizeUrlResponse>("/api/v1/auth/oidc/authorize");
    },
    exchangeOidcCallback(payload: OidcCallbackExchangeRequest): Promise<AuthTokenResponse> {
      return requestJson<AuthTokenResponse>("/api/v1/auth/oidc/callback", "POST", payload);
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
    changePassword(payload: ChangePasswordRequest): Promise<ChangePasswordResponse> {
      return requestJson<ChangePasswordResponse>("/api/v1/auth/change-password", "POST", payload);
    },
    getMe(personaKey?: string): Promise<UserMeResponse> {
      return requestJson<UserMeResponse>(`/api/v1/auth/me${buildPersonaQuery(personaKey)}`);
    },
    listWorkspaces(personaKey?: string): Promise<WorkspacesListResponse> {
      return requestJson<WorkspacesListResponse>(
        `/api/v1/workspaces${buildPersonaQuery(personaKey)}`,
      );
    },
    createWorkspace(
      payload: WorkspaceCreateRequest,
      personaKey?: string,
    ): Promise<WorkspaceCreateResponse> {
      return requestJson<WorkspaceCreateResponse>(
        `/api/v1/workspaces${buildPersonaQuery(personaKey)}`,
        "POST",
        payload,
      );
    },
    listOrgUnits(params?: ListOrgUnitsParams | string): Promise<OrgUnitsListResponse> {
      return requestJson<OrgUnitsListResponse>(
        `/api/v1/org-units${buildOrgUnitsQuery(params)}`,
      );
    },
    searchKnownOrgUsers(
      params?: ListKnownOrgUsersParams | string,
    ): Promise<KnownOrgUsersSearchResponse> {
      return requestJson<KnownOrgUsersSearchResponse>(
        `/api/v1/org-units/known-users${buildKnownOrgUsersQuery(params)}`,
      );
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
    getUserProfileSummary(personaKey?: string): Promise<UserProfileSummaryResponse> {
      return requestJson<UserProfileSummaryResponse>(
        `/api/v1/users/me/profile-summary${buildPersonaQuery(personaKey)}`,
      );
    },
  };
}
