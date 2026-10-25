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
    BmadSkillPackImportRequest: {
      customize_toml?: string;
      skill_markdown: string;
      steps: (components["schemas"]["BmadSkillStepInputItem"])[];
      uri: string;
      workspace_id?: string | null;
    };
    BmadSkillPackImportResponse: {
      catalog_item: components["schemas"]["CatalogItemResponse"];
      trace_id: string;
      workflow_definition: components["schemas"]["WorkflowDefinitionResponseItem"];
    };
    BmadSkillStepInputItem: {
      content_markdown: string;
      filename: string;
    };
    CasObjectResponse: {
      cas_key: string;
      content_text: string;
      content_type: string;
      sha256: string;
      trace_id: string;
    };
    CatalogItemResponse: {
      cas_key: string;
      description: string;
      granted_permissions: ("DISCOVER" | "EXECUTE" | "READ_SOURCE" | "EDIT" | "ADMIN")[];
      id: string;
      resource_id: string;
      resource_type: "workflow" | "agent" | "skill" | "template" | "datasource";
      scheme: "git" | "nexus" | "db" | "confluence" | "jira" | "orcia";
      sha256: string;
      sha256_short: string;
      source_format: "ORCIA" | "BMAD_PACK";
      source_masked: boolean;
      title: string;
      uri: string;
      version: string;
      visibility_scope: "DRAFT" | "SHARED_WORKSPACE" | "SHARED_TEAM" | "SHARED_BU" | "PUBLISHED_ORG" | "PENDING_APPROVAL";
    };
    CatalogItemsListResponse: {
      items: (components["schemas"]["CatalogItemResponse"])[];
      trace_id: string;
    };
    CatalogPromoteRequest: {
      target_scope: "DRAFT" | "SHARED_WORKSPACE" | "SHARED_TEAM" | "SHARED_BU" | "PUBLISHED_ORG" | "PENDING_APPROVAL";
      workspace_id?: string | null;
    };
    CatalogPromoteResponse: {
      item: components["schemas"]["CatalogItemResponse"];
      previous_scope: "DRAFT" | "SHARED_WORKSPACE" | "SHARED_TEAM" | "SHARED_BU" | "PUBLISHED_ORG" | "PENDING_APPROVAL";
      trace_id: string;
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
    CatalogUriResolveRequest: {
      expected_sha256?: string | null;
      uri: string;
    };
    CatalogUriResolveResponse: {
      cache_hit: boolean;
      cas_key: string;
      content_text: string;
      resolution_ms: number;
      resolved_version: string;
      scheme: "git" | "nexus" | "db" | "confluence" | "jira" | "orcia";
      sha256: string;
      trace_id: string;
      uri: string;
    };
    EffectiveWorkflowResolveRequest: {
      workflow_uri: string;
      workspace_id: string;
    };
    EffectiveWorkflowResolveResponse: {
      applied_override_keys: (string)[];
      base_workflow: components["schemas"]["WorkflowDefinitionResponseItem"];
      effective_workflow: components["schemas"]["WorkflowDefinitionResponseItem"];
      run_lock: components["schemas"]["RunLockManifestItem"];
      trace_id: string;
    };
    EvaluationLensItem: {
      code: string;
      threshold: number;
      weight: number;
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
    InitDatasourceRequest: {
      alias: string;
      cql_filter?: string | null;
      execution_identity?: "passthrough" | "service_principal";
      freshness_ttl_days: number;
      human_anchor_author_id?: string | null;
      human_anchor_justification: string;
      human_anchor_signature: string;
      jql_filter?: string | null;
      permission_broker_markdown: string;
      role: string;
      scheme: "git" | "jira" | "confluence" | "db" | "nexus";
      uri: string;
      visibility_scope?: "SHARED_WORKSPACE" | "SHARED_TEAM";
      workspace_id: string;
    };
    InitDatasourceResponse: {
      catalog_item: components["schemas"]["CatalogItemResponse"];
      datasource: components["schemas"]["WorkspaceDatasourceItem"];
      policy: components["schemas"]["PermissionBrokerPolicyItem"];
      run: components["schemas"]["SystemBootstrapRunItem"];
      trace_id: string;
    };
    InitOrganizationRequest: {
      llm_endpoints: (components["schemas"]["LlmModelEndpointItem"])[];
      local_argon2id_enabled?: boolean;
      oidc_enabled?: boolean;
      organization_name: string;
      rbac_role_mappings?: Record<string, string>;
    };
    InitOrganizationResponse: {
      orthogonal_families: (string)[];
      run: components["schemas"]["SystemBootstrapRunItem"];
      trace_id: string;
    };
    InitUserPassthroughSecretItem: {
      connector_scheme: "git" | "jira" | "confluence" | "db" | "nexus";
      plaintext_secret: string;
      target_host: string;
    };
    InitUserRequest: {
      confirmed_human_profile_archetype: string;
      passthrough_secrets: (components["schemas"]["InitUserPassthroughSecretItem"])[];
      user_email?: string | null;
    };
    InitUserResponse: {
      credentials: (components["schemas"]["PassthroughSecretMetadataResponse"])[];
      onboarding_state: components["schemas"]["UserOnboardingStateItem"];
      run: components["schemas"]["SystemBootstrapRunItem"];
      trace_id: string;
    };
    InitWorkspaceRequest: {
      invited_members?: (components["schemas"]["MemberInvitationInputItem"])[];
      parent_org_unit_id: string;
      subteam_name?: string | null;
      subteam_slug?: string | null;
      team_name: string;
      team_ontology_terms?: (components["schemas"]["OntologyTermInputItem"])[];
      team_override_scalars?: Record<string, string | number | boolean>;
      team_slug: string;
      workspaces: (components["schemas"]["WorkspaceBootstrapInputItem"])[];
    };
    InitWorkspaceResponse: {
      onboarding_states: (components["schemas"]["UserOnboardingStateItem"])[];
      run: components["schemas"]["SystemBootstrapRunItem"];
      trace_id: string;
      workspaces: (components["schemas"]["WorkspaceSummaryItem"])[];
    };
    LlmModelEndpointItem: {
      connectivity_verified?: boolean;
      endpoint_key: string;
      endpoint_uri: string;
      id: string;
      is_active?: boolean;
      model_family: string;
      model_name: string;
      provider_slug: string;
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
    MemberInvitationInputItem: {
      display_name: string;
      email: string;
      human_profile_archetype: string;
      role?: "PLATFORM_ADMIN" | "BU_DIRECTOR" | "TEAM_LEAD" | "CONTRIBUTOR" | "GATE_REVIEWER" | "ONTOLOGY_STEWARD_L3" | "OBSERVER";
    };
    OidcLoginRequest: {
      email?: string | null;
      oidc_subject: string;
    };
    OntologyTermInputItem: {
      definition: string;
      level?: "1_ENTERPRISE" | "2_DOMAIN" | "3_TEAM" | "3_WORKSPACE";
      term_key: string;
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
    PermissionBrokerPolicyItem: {
      approved_by_admin_id?: string | null;
      approver_team: string;
      connector_scheme: "git" | "jira" | "confluence" | "db" | "nexus" | "mcp";
      freshness_ttl_days?: number;
      human_anchor_author_id?: string | null;
      human_anchor_signature?: string | null;
      id: string;
      policy_key: string;
      procedure_markdown?: string;
      request_url_template: string;
      required_role: string;
      service_principal_allowed?: boolean;
      sla_hours: number;
      uri_pattern: string;
    };
    PermissionBrokerStateResponse: {
      policies: (components["schemas"]["PermissionBrokerPolicyItem"])[];
      tickets: (components["schemas"]["PermissionBrokerTicketItem"])[];
      trace_id: string;
    };
    PermissionBrokerTicketItem: {
      approver_team: string;
      connector_scheme: "git" | "jira" | "confluence" | "db" | "nexus" | "mcp";
      execution_identity: "passthrough" | "service_principal";
      id: string;
      jira_request_url: string;
      permission_broker_hint: string;
      policy_id: string;
      procedure_markdown?: string;
      requester_user_id: string;
      required_role: string;
      sla_hours: number;
      status: "WAITING_FOR_PERMISSION" | "PAUSED" | "REPLAYED" | "GRANTED";
      step_key: string;
      step_number: number;
      step_state: "PERMISSION_DENIED_STEP" | "PAUSED" | "REPLAYED" | "GRANTED";
      target_uri: string;
      ticket_key: string;
      upstream_http_status: 401 | 403;
      workspace_id?: string | null;
    };
    PermissionCheckRequest: {
      execution_identity?: "passthrough" | "service_principal";
      granted_external_roles?: (string)[];
      raise_on_denied?: boolean;
      resource_id?: string | null;
      simulated_upstream_status?: 200 | 401 | 403 | null;
      step_key?: string;
      step_number?: number;
      target_uri: string;
      workspace_id?: string | null;
    };
    PermissionCheckResponse: {
      allowed: boolean;
      connector_scheme: "git" | "jira" | "confluence" | "db" | "nexus" | "mcp";
      execution_identity: "passthrough" | "service_principal";
      permission_broker_hint?: string | null;
      policy: components["schemas"]["PermissionBrokerPolicyItem"];
      status: "GRANTED" | "WAITING_FOR_PERMISSION";
      target_uri: string;
      ticket?: components["schemas"]["PermissionBrokerTicketItem"] | null;
      trace_id: string;
    };
    PermissionPolicyImportMarkdownRequest: {
      markdown_text: string;
      policy_key?: string | null;
      workspace_id?: string | null;
    };
    PermissionPolicyImportMarkdownResponse: {
      policy: components["schemas"]["PermissionBrokerPolicyItem"];
      trace_id: string;
    };
    PermissionTicketActionRequest: {
      action: "PAUSE" | "REPLAY";
      workspace_id?: string | null;
    };
    PermissionTicketActionResponse: {
      ticket: components["schemas"]["PermissionBrokerTicketItem"];
      trace_id: string;
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
    RunLockManifestItem: {
      applied_override_keys: (string)[];
      effective_workflow_sha256: string;
      manifest_sha256: string;
      sources: (components["schemas"]["RunLockSourceTripletItem"])[];
      workflow_sha256: string;
      workflow_uri: string;
      workflow_version: string;
      workspace_id: string;
    };
    RunLockSourceTripletItem: {
      alias: string;
      cas_key: string;
      resolved_version: string;
      scheme: "git" | "nexus" | "db" | "confluence" | "jira" | "orcia";
      sha256: string;
      uri: string;
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
    SystemBootstrapRunItem: {
      execution_payload: Record<string, unknown>;
      gate_passed: boolean;
      gate_report: Record<string, unknown>;
      id: string;
      run_key: string;
      scope_level: "GLOBAL" | "BU" | "TEAM" | "WORKSPACE";
      status: "COMPLETED" | "BLOCKED_BY_GATE" | "FAILED";
      target_org_unit_id?: string | null;
      target_workspace_id?: string | null;
      triggered_by_user_id: string;
      workflow_uri: string;
    };
    SystemBootstrapStateResponse: {
      is_model_orthogonal: boolean;
      llm_endpoints: (components["schemas"]["LlmModelEndpointItem"])[];
      onboarding_states: (components["schemas"]["UserOnboardingStateItem"])[];
      orthogonal_families: (string)[];
      runs: (components["schemas"]["SystemBootstrapRunItem"])[];
      trace_id: string;
      workflows: (components["schemas"]["SystemBootstrapWorkflowItem"])[];
    };
    SystemBootstrapWorkflowItem: {
      description: string;
      deterministic_gate_rules: (string)[];
      id: string;
      required_role: string;
      scope_level: "GLOBAL" | "BU" | "TEAM" | "WORKSPACE";
      sha256: string;
      title: string;
      uri: string;
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
    UserOnboardingStateItem: {
      assigned_role: "PLATFORM_ADMIN" | "BU_DIRECTOR" | "TEAM_LEAD" | "CONTRIBUTOR" | "GATE_REVIEWER" | "ONTOLOGY_STEWARD_L3" | "OBSERVER";
      human_profile_archetype: string;
      id: string;
      init_user_completed: boolean;
      invited_by_user_id?: string | null;
      linked_connectors: ("git" | "jira" | "confluence" | "db" | "nexus")[];
      org_unit_id: string;
      user_email: string;
      user_id?: string | null;
      workspace_ids: (string)[];
    };
    WorkflowDefinitionResponseItem: {
      adaptive_gate_policy: "STRICT" | "STANDARD" | "FAST_TRACK";
      datasources: (string)[];
      description: string;
      facts: (string)[];
      id: string;
      lenses: (components["schemas"]["EvaluationLensItem"])[];
      rules: (string)[];
      scalars: Record<string, string | number | boolean>;
      sha256: string;
      source_format: "ORCIA" | "BMAD_PACK";
      steps: (components["schemas"]["WorkflowStepItem"])[];
      title: string;
      uri: string;
      version: string;
      workspace_id?: string | null;
    };
    WorkflowStepItem: {
      human_authored_required: boolean;
      instructions: string;
      step_key: string;
      title: string;
    };
    WorkspaceBootstrapInputItem: {
      name: string;
      notification_channel?: string;
      slug: string;
      visibility_mode?: "STANDARD" | "CONFIDENTIAL_RESTRICTED";
      workspace_ontology_terms?: (components["schemas"]["OntologyTermInputItem"])[];
      workspace_override_scalars?: Record<string, string | number | boolean>;
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
  "/api/v1/bootstrap/init-datasource": {
    post: {
      responses: {
        200: components["schemas"]["InitDatasourceResponse"];
      };
    };
  };
  "/api/v1/bootstrap/init-organization": {
    post: {
      responses: {
        200: components["schemas"]["InitOrganizationResponse"];
      };
    };
  };
  "/api/v1/bootstrap/init-user": {
    post: {
      responses: {
        200: components["schemas"]["InitUserResponse"];
      };
    };
  };
  "/api/v1/bootstrap/init-workspace": {
    post: {
      responses: {
        200: components["schemas"]["InitWorkspaceResponse"];
      };
    };
  };
  "/api/v1/bootstrap/state": {
    get: {
      responses: {
        200: components["schemas"]["SystemBootstrapStateResponse"];
      };
    };
  };
  "/api/v1/cas/{sha256}": {
    get: {
      responses: {
        200: components["schemas"]["CasObjectResponse"];
      };
    };
  };
  "/api/v1/catalog/bmad-packs/import": {
    post: {
      responses: {
        200: components["schemas"]["BmadSkillPackImportResponse"];
      };
    };
  };
  "/api/v1/catalog/items": {
    get: {
      responses: {
        200: components["schemas"]["CatalogItemsListResponse"];
      };
    };
  };
  "/api/v1/catalog/items/{resource_id}/promote": {
    post: {
      responses: {
        200: components["schemas"]["CatalogPromoteResponse"];
      };
    };
  };
  "/api/v1/catalog/resolve": {
    post: {
      responses: {
        200: components["schemas"]["CatalogUriResolveResponse"];
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
  "/api/v1/catalog/workflows/resolve-effective": {
    post: {
      responses: {
        200: components["schemas"]["EffectiveWorkflowResolveResponse"];
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
  "/api/v1/permissions/broker/check-access": {
    post: {
      responses: {
        200: components["schemas"]["PermissionCheckResponse"];
      };
    };
  };
  "/api/v1/permissions/broker/policies/import-markdown": {
    post: {
      responses: {
        200: components["schemas"]["PermissionPolicyImportMarkdownResponse"];
      };
    };
  };
  "/api/v1/permissions/broker/state": {
    get: {
      responses: {
        200: components["schemas"]["PermissionBrokerStateResponse"];
      };
    };
  };
  "/api/v1/permissions/broker/tickets/{ticket_id}/action": {
    post: {
      responses: {
        200: components["schemas"]["PermissionTicketActionResponse"];
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
export type BmadSkillPackImportRequest = components["schemas"]["BmadSkillPackImportRequest"];
export type BmadSkillPackImportResponse = components["schemas"]["BmadSkillPackImportResponse"];
export type BmadSkillStepInputItem = components["schemas"]["BmadSkillStepInputItem"];
export type CasObjectResponse = components["schemas"]["CasObjectResponse"];
export type CatalogItemResponse = components["schemas"]["CatalogItemResponse"];
export type CatalogItemsListResponse = components["schemas"]["CatalogItemsListResponse"];
export type CatalogPromoteRequest = components["schemas"]["CatalogPromoteRequest"];
export type CatalogPromoteResponse = components["schemas"]["CatalogPromoteResponse"];
export type CatalogResourceInspectionResponse = components["schemas"]["CatalogResourceInspectionResponse"];
export type CatalogResourceSourceResponse = components["schemas"]["CatalogResourceSourceResponse"];
export type CatalogUriResolveRequest = components["schemas"]["CatalogUriResolveRequest"];
export type CatalogUriResolveResponse = components["schemas"]["CatalogUriResolveResponse"];
export type EffectiveWorkflowResolveRequest = components["schemas"]["EffectiveWorkflowResolveRequest"];
export type EffectiveWorkflowResolveResponse = components["schemas"]["EffectiveWorkflowResolveResponse"];
export type EvaluationLensItem = components["schemas"]["EvaluationLensItem"];
export type HealthResponse = components["schemas"]["HealthResponse"];
export type HumanProfileBadge = components["schemas"]["HumanProfileBadge"];
export type InitDatasourceRequest = components["schemas"]["InitDatasourceRequest"];
export type InitDatasourceResponse = components["schemas"]["InitDatasourceResponse"];
export type InitOrganizationRequest = components["schemas"]["InitOrganizationRequest"];
export type InitOrganizationResponse = components["schemas"]["InitOrganizationResponse"];
export type InitUserPassthroughSecretItem = components["schemas"]["InitUserPassthroughSecretItem"];
export type InitUserRequest = components["schemas"]["InitUserRequest"];
export type InitUserResponse = components["schemas"]["InitUserResponse"];
export type InitWorkspaceRequest = components["schemas"]["InitWorkspaceRequest"];
export type InitWorkspaceResponse = components["schemas"]["InitWorkspaceResponse"];
export type LlmModelEndpointItem = components["schemas"]["LlmModelEndpointItem"];
export type LocalLoginRequest = components["schemas"]["LocalLoginRequest"];
export type LogoutResponse = components["schemas"]["LogoutResponse"];
export type MemberInvitationInputItem = components["schemas"]["MemberInvitationInputItem"];
export type OidcLoginRequest = components["schemas"]["OidcLoginRequest"];
export type OntologyTermInputItem = components["schemas"]["OntologyTermInputItem"];
export type OrgUnitTreeItem = components["schemas"]["OrgUnitTreeItem"];
export type PassthroughSecretMetadataResponse = components["schemas"]["PassthroughSecretMetadataResponse"];
export type PassthroughSecretStoreRequest = components["schemas"]["PassthroughSecretStoreRequest"];
export type PermissionBrokerPolicyItem = components["schemas"]["PermissionBrokerPolicyItem"];
export type PermissionBrokerStateResponse = components["schemas"]["PermissionBrokerStateResponse"];
export type PermissionBrokerTicketItem = components["schemas"]["PermissionBrokerTicketItem"];
export type PermissionCheckRequest = components["schemas"]["PermissionCheckRequest"];
export type PermissionCheckResponse = components["schemas"]["PermissionCheckResponse"];
export type PermissionPolicyImportMarkdownRequest = components["schemas"]["PermissionPolicyImportMarkdownRequest"];
export type PermissionPolicyImportMarkdownResponse = components["schemas"]["PermissionPolicyImportMarkdownResponse"];
export type PermissionTicketActionRequest = components["schemas"]["PermissionTicketActionRequest"];
export type PermissionTicketActionResponse = components["schemas"]["PermissionTicketActionResponse"];
export type ProblemDetails = components["schemas"]["ProblemDetails"];
export type RunLockManifestItem = components["schemas"]["RunLockManifestItem"];
export type RunLockSourceTripletItem = components["schemas"]["RunLockSourceTripletItem"];
export type ScopeMutationCheckResponse = components["schemas"]["ScopeMutationCheckResponse"];
export type ScopeNode = components["schemas"]["ScopeNode"];
export type ShellModuleItem = components["schemas"]["ShellModuleItem"];
export type ShellNavigationResponse = components["schemas"]["ShellNavigationResponse"];
export type SystemBootstrapRunItem = components["schemas"]["SystemBootstrapRunItem"];
export type SystemBootstrapStateResponse = components["schemas"]["SystemBootstrapStateResponse"];
export type SystemBootstrapWorkflowItem = components["schemas"]["SystemBootstrapWorkflowItem"];
export type UserMeResponse = components["schemas"]["UserMeResponse"];
export type UserOnboardingStateItem = components["schemas"]["UserOnboardingStateItem"];
export type WorkflowDefinitionResponseItem = components["schemas"]["WorkflowDefinitionResponseItem"];
export type WorkflowStepItem = components["schemas"]["WorkflowStepItem"];
export type WorkspaceBootstrapInputItem = components["schemas"]["WorkspaceBootstrapInputItem"];
export type WorkspaceDatasourceItem = components["schemas"]["WorkspaceDatasourceItem"];
export type WorkspaceSummaryItem = components["schemas"]["WorkspaceSummaryItem"];
export type WorkspacesListResponse = components["schemas"]["WorkspacesListResponse"];
