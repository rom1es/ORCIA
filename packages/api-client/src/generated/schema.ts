/**
 * AUTO-GENERATED FILE FROM FASTAPI OPENAPI 3.1 SCHEMA — DO NOT EDIT MANUALLY.
 * Regenerate via: `.venv/bin/python scripts/export_openapi.py`
 */

export interface components {
  schemas: {
    AuthTokenResponse: {
      access_token: string;
      display_name: string;
      email: string;
      expires_in_seconds?: number;
      human_profile_archetype: string;
      platform_role: "PLATFORM_ADMIN" | "BU_DIRECTOR" | "TEAM_LEAD" | "CONTRIBUTOR" | "GATE_REVIEWER" | "ONTOLOGY_STEWARD_L3" | "OBSERVER";
      primary_org_unit_id: string;
      token_type?: "Bearer";
      trace_id: string;
      user_id: string;
    };
    CatalogResourceInspectionResponse: {
      granted_permissions: ("DISCOVER" | "EXECUTE" | "READ_SOURCE" | "EDIT" | "ADMIN")[];
      resource_id: string;
      resource_uri: string;
      source_masked: boolean;
      title: string;
      trace_id: string;
      visibility_scope: "DRAFT" | "SHARED_WORKSPACE" | "SHARED_TEAM" | "SHARED_BU" | "PUBLISHED_ORG" | "PENDING_APPROVAL";
    };
    CatalogResourceSourceResponse: {
      resource_id: string;
      resource_uri: string;
      system_prompt_secret: string;
      trace_id: string;
    };
    HealthResponse: {
      status?: "ok";
      trace_id: string;
      version: string;
    };
    HumanProfileBadge: {
      access_mode: "CONTRIBUTOR_ACTION_REQUIRED" | "READ_ONLY_OBSERVER";
      archetype_key: string;
      display_name: string;
      org_unit_id?: string;
      org_unit_name?: string;
      role?: string;
    };
    LocalLoginRequest: {
      email: string;
      password: string;
      totp_code?: string | null;
    };
    LogoutResponse: {
      revoked?: boolean;
      trace_id: string;
    };
    OidcLoginRequest: {
      email?: string | null;
      oidc_subject: string;
    };
    OrgUnitTreeItem: {
      id: string;
      name: string;
      parent_id?: string | null;
      slug: string;
      unit_type: "ENTERPRISE" | "BU" | "TRIBE" | "TEAM" | "SUB_TEAM";
    };
    PassthroughSecretMetadataResponse: {
      connector_scheme: "git" | "jira" | "confluence" | "db" | "nexus";
      encrypted_at_rest?: boolean;
      id: string;
      key_version: number;
      target_host: string;
      trace_id: string;
      user_id: string;
    };
    PassthroughSecretStoreRequest: {
      connector_scheme: "git" | "jira" | "confluence" | "db" | "nexus";
      plaintext_secret: string;
      target_host: string;
    };
    ProblemDetails: {
      detail: string;
      error_code: string;
      instance?: string | null;
      permission_broker_hint?: string | null;
      status: number;
      title: string;
      trace_id: string;
      type?: string;
    };
    ScopeMutationCheckResponse: {
      access_mode: "CONTRIBUTOR_ACTION_REQUIRED" | "READ_ONLY_OBSERVER";
      allowed?: boolean;
      effective_role: "PLATFORM_ADMIN" | "BU_DIRECTOR" | "TEAM_LEAD" | "CONTRIBUTOR" | "GATE_REVIEWER" | "ONTOLOGY_STEWARD_L3" | "OBSERVER";
      trace_id: string;
      workspace_id: string;
    };
    ScopeNode: {
      access_mode?: "CONTRIBUTOR_ACTION_REQUIRED" | "READ_ONLY_OBSERVER";
      id: string;
      level: "GLOBAL" | "BU" | "TEAM" | "WORKSPACE";
      name: string;
      parent_id?: string | null;
    };
    ShellModuleItem: {
      contributor_badge_count?: number;
      enabled?: boolean;
      has_stale_warning?: boolean;
      icon: string;
      key: "cockpit" | "inbox" | "catalog" | "ontology" | "gates" | "finops" | "admin";
      order: number;
      route: string;
    };
    ShellNavigationResponse: {
      active_scope_id: string;
      human_profile: components["schemas"]["HumanProfileBadge"];
      modules: (components["schemas"]["ShellModuleItem"])[];
      scopes: (components["schemas"]["ScopeNode"])[];
      trace_id: string;
    };
    UserMeResponse: {
      auth_mode: "OIDC" | "LOCAL" | "HYBRID";
      consolidated_finops_usd: number;
      display_name: string;
      email: string;
      human_profile_archetype: string;
      id: string;
      modules: Record<string, boolean>;
      org_units: (components["schemas"]["OrgUnitTreeItem"])[];
      platform_role: "PLATFORM_ADMIN" | "BU_DIRECTOR" | "TEAM_LEAD" | "CONTRIBUTOR" | "GATE_REVIEWER" | "ONTOLOGY_STEWARD_L3" | "OBSERVER";
      primary_org_unit_id: string;
      totp_enabled: boolean;
      trace_id: string;
      transverse_groups: (string)[];
      workspaces: (components["schemas"]["WorkspaceSummaryItem"])[];
    };
    WorkspaceDatasourceItem: {
      alias: string;
      execution_identity: "passthrough" | "service_principal";
      freshness_ttl_days: number;
      id: string;
      role: string;
      scheme: "git" | "jira" | "confluence" | "db" | "nexus";
      uri: string;
      workspace_id: string;
    };
    WorkspaceSummaryItem: {
      access_mode: "CONTRIBUTOR_ACTION_REQUIRED" | "READ_ONLY_OBSERVER";
      access_origin: "DIRECT_TEAM" | "ROLLUP_PARENT" | "PARTNER_INVITE" | "GLOBAL_ADMIN";
      datasources: (components["schemas"]["WorkspaceDatasourceItem"])[];
      effective_role: "PLATFORM_ADMIN" | "BU_DIRECTOR" | "TEAM_LEAD" | "CONTRIBUTOR" | "GATE_REVIEWER" | "ONTOLOGY_STEWARD_L3" | "OBSERVER";
      finops_cost_usd?: number | null;
      id: string;
      name: string;
      owner_org_unit_id: string;
      slug: string;
      visibility_mode: "STANDARD" | "CONFIDENTIAL_RESTRICTED";
    };
    WorkspacesListResponse: {
      consolidated_finops_usd: number;
      trace_id: string;
      workspaces: (components["schemas"]["WorkspaceSummaryItem"])[];
    };
  };
}

export interface paths {
  "/api/v1/auth/login/local": {
    post: {
      responses: {
        200: components["schemas"]["AuthTokenResponse"];
      };
    };
  };
  "/api/v1/auth/login/oidc": {
    post: {
      responses: {
        200: components["schemas"]["AuthTokenResponse"];
      };
    };
  };
  "/api/v1/auth/logout": {
    post: {
      responses: {
        200: components["schemas"]["LogoutResponse"];
      };
    };
  };
  "/api/v1/auth/me": {
    get: {
      responses: {
        200: components["schemas"]["UserMeResponse"];
      };
    };
  };
  "/api/v1/auth/passthrough-credentials": {
    post: {
      responses: {
        200: components["schemas"]["PassthroughSecretMetadataResponse"];
      };
    };
  };
  "/api/v1/auth/refresh": {
    post: {
      responses: {
        200: components["schemas"]["AuthTokenResponse"];
      };
    };
  };
  "/api/v1/catalog/resources/{resource_id}/inspect": {
    get: {
      responses: {
        200: components["schemas"]["CatalogResourceInspectionResponse"];
      };
    };
  };
  "/api/v1/catalog/resources/{resource_id}/source": {
    get: {
      responses: {
        200: components["schemas"]["CatalogResourceSourceResponse"];
      };
    };
  };
  "/api/v1/health": {
    get: {
      responses: {
        200: components["schemas"]["HealthResponse"];
      };
    };
  };
  "/api/v1/navigation/shell": {
    get: {
      responses: {
        200: components["schemas"]["ShellNavigationResponse"];
      };
    };
  };
  "/api/v1/workspaces": {
    get: {
      responses: {
        200: components["schemas"]["WorkspacesListResponse"];
      };
    };
  };
  "/api/v1/workspaces/{workspace_id}/mutations/check": {
    post: {
      responses: {
        200: components["schemas"]["ScopeMutationCheckResponse"];
      };
    };
  };
}

export type AuthTokenResponse = components["schemas"]["AuthTokenResponse"];
export type CatalogResourceInspectionResponse = components["schemas"]["CatalogResourceInspectionResponse"];
export type CatalogResourceSourceResponse = components["schemas"]["CatalogResourceSourceResponse"];
export type HealthResponse = components["schemas"]["HealthResponse"];
export type HumanProfileBadge = components["schemas"]["HumanProfileBadge"];
export type LocalLoginRequest = components["schemas"]["LocalLoginRequest"];
export type LogoutResponse = components["schemas"]["LogoutResponse"];
export type OidcLoginRequest = components["schemas"]["OidcLoginRequest"];
export type OrgUnitTreeItem = components["schemas"]["OrgUnitTreeItem"];
export type PassthroughSecretMetadataResponse = components["schemas"]["PassthroughSecretMetadataResponse"];
export type PassthroughSecretStoreRequest = components["schemas"]["PassthroughSecretStoreRequest"];
export type ProblemDetails = components["schemas"]["ProblemDetails"];
export type ScopeMutationCheckResponse = components["schemas"]["ScopeMutationCheckResponse"];
export type ScopeNode = components["schemas"]["ScopeNode"];
export type ShellModuleItem = components["schemas"]["ShellModuleItem"];
export type ShellNavigationResponse = components["schemas"]["ShellNavigationResponse"];
export type UserMeResponse = components["schemas"]["UserMeResponse"];
export type WorkspaceDatasourceItem = components["schemas"]["WorkspaceDatasourceItem"];
export type WorkspaceSummaryItem = components["schemas"]["WorkspaceSummaryItem"];
export type WorkspacesListResponse = components["schemas"]["WorkspacesListResponse"];
