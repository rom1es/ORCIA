/**
 * AUTO-GENERATED FILE FROM FASTAPI OPENAPI 3.1 SCHEMA — DO NOT EDIT MANUALLY.
 * Regenerate via: `.venv/bin/python scripts/export_openapi.py`
 */

export interface components {
  schemas: {
    ArbitrationOptionSchemaItem: {
      cons?: (string)[];
      finops_impact: string;
      ontology_concept_key?: string | null;
      option_key: string;
      pros?: (string)[];
      recommended?: boolean;
      si_impact: string;
      title: string;
    };
    ArtifactTemplateCompileRequest: {
      template_key: string;
      variables?: Record<string, string>;
      workspace_id?: string;
    };
    ArtifactTemplateCompileResponse: {
      compiled_template: components["schemas"]["CompiledArtifactTemplateSchemaItem"];
      trace_id: string;
    };
    AssistantChatRequest: {
      allowed_datasource_aliases?: (string)[];
      human_profile_archetype?: string | null;
      user_prompt: string;
      workspace_id: string;
    };
    AssistantChatResponse: {
      cited_uris: (string)[];
      constitutional_sha256: string;
      first_token_latency_ms: number;
      highlighted_indicators: (string)[];
      human_profile_archetype: string;
      intent: string;
      node_traces: (components["schemas"]["AssistantNodeTraceSchemaItem"])[];
      prompt_layers: (components["schemas"]["PromptLayerBlockSchemaItem"])[];
      register_label: string;
      response_text: string;
      stale_warnings: (string)[];
      turn_id: string;
      vocabulary_tier: string;
      workflow_proposal?: components["schemas"]["AssistantWorkflowProposalSchemaItem"] | null;
      workflow_uri: string;
      workspace_id: string;
    };
    AssistantNodeTraceSchemaItem: {
      duration_ms: number;
      node_id: "1_INTENT_ROUTER" | "2_QUERY_PLANNER_AND_ONTOLOGY_EXPANSION" | "3_PARALLEL_FAN_OUT" | "4_CRITICAL_TRIAGE_AND_AXIOM_VERIFICATION" | "5_PROFILE_ADAPTIVE_SYNTHESIZER";
      node_order: number;
      output_metadata?: Record<string, unknown>;
      status: "COMPLETED";
      summary: string;
    };
    AssistantSaveAndLaunchRequest: {
      manifest_yaml: string;
      workspace_id: string;
    };
    AssistantSaveAndLaunchResponse: {
      executed_step_keys: (string)[];
      execution_regime: string;
      run_id: string;
      run_status: string;
      snapshot_count: number;
      version: string;
      workflow_uri: string;
    };
    AssistantWorkflowProposalSchemaItem: {
      description: string;
      edges: (components["schemas"]["XyFlowEdgeSchemaItem"])[];
      execution_regime: string;
      manifest_yaml: string;
      nodes: (components["schemas"]["XyFlowNodeSchemaItem"])[];
      proposal_id: string;
      title: string;
      workflow_uri: string;
    };
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
    BackgroundAuditReportSchemaItem: {
      assumptions: (components["schemas"]["StepMemlogSchemaItem"])[];
      run_id: string;
      sse_event_topic: string;
      sse_latency_ms: number;
      suspected_code_bugs: (components["schemas"]["StepMemlogSchemaItem"])[];
      suspected_obsolete_docs: (components["schemas"]["StepMemlogSchemaItem"])[];
      total_steps_committed: number;
      workflow_uri: string;
    };
    BackgroundAuditRunRequest: {
      divergence_note?: string;
      run_id: string;
    };
    BackgroundAuditRunResponse: {
      report: components["schemas"]["BackgroundAuditReportSchemaItem"];
      trace_id: string;
    };
    BlackboardSnapshotSchemaItem: {
      artifact_cas_key: string;
      artifact_payload: Record<string, unknown>;
      artifact_sha256: string;
      branch_status: "ACTIVE" | "SUPERSEDED";
      id: string;
      memlog_summary?: (components["schemas"]["StepMemlogSchemaItem"])[];
      parent_snapshot_id?: string | null;
      run_id: string;
      snapshot_key: string;
      step_execution_id: string;
      step_key: string;
      superseded_snapshot_ids?: (string)[];
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
      scheme: string;
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
      scheme: string;
      sha256: string;
      trace_id: string;
      uri: string;
    };
    CompiledArtifactTemplateSchemaItem: {
      agent_json_schema: Record<string, unknown>;
      bound_ontology_terms: (string)[];
      cognitive_chunks: (components["schemas"]["CompiledMarkdownChunkSchemaItem"])[];
      human_markdown_view: string;
      sha256: string;
      template_key: string;
      uri: string;
      version: string;
    };
    CompiledMarkdownChunkSchemaItem: {
      chunk_index: number;
      human_authored_required: boolean;
      markdown_content: string;
      section_key: string;
      section_title: string;
      word_count: number;
    };
    DbDdlIndexRequest: {
      datasource_alias: string;
      datasource_id: string;
      db_uri: string;
      ddl_sql: string;
      ontology_concepts?: (string)[];
      schema_version: string;
      workspace_id: string;
    };
    DocVsCodeAuditRequest: {
      code_rule_summary: string;
      confluence_uri: string;
      doc_rule_summary: string;
      git_repo_uri: string;
      git_symbol: string;
      newer_done_jira_key?: string | null;
    };
    DocVsCodeAuditResponse: {
      confluence_uri: string;
      explanation: string;
      git_repo_uri: string;
      git_symbol: string;
      justifying_jira_key?: string | null;
      qualification_marker: "[DOC_OBSOLETE_SUSPECTED]" | "[BUG_CODE_SUSPECTED]" | "[ALIGNED]";
      trace_id?: string | null;
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
    HumanAnchorSignRequest: {
      author_type?: "HUMAN" | "AGENT";
      content_text: string;
      run_id: string;
      section_key?: string;
      signature_text?: string;
      step_key: string;
    };
    HumanAnchorSignResponse: {
      signature: components["schemas"]["HumanAnchorSignatureSchemaItem"];
      step_execution: components["schemas"]["StepExecutionSchemaItem"];
      trace_id: string;
    };
    HumanAnchorSignatureSchemaItem: {
      author_display_name: string;
      authored_by_user_id: string;
      char_length: number;
      content_sha256: string;
      content_text: string;
      id: string;
      run_id: string;
      section_key: string;
      signature_hash: string;
      signature_key: string;
      step_execution_id: string;
      step_key: string;
      workspace_id: string;
    };
    HumanArbitrationCreateRequest: {
      context_summary?: string;
      options_matrix: (components["schemas"]["ArbitrationOptionSchemaItem"])[];
      question_title: string;
      tie_break_policy?: "ONTOLOGY_AXIOM_FIRST" | "DEFER_AND_CONTINUE_WITH_ASSUMPTION" | "PAUSE_AND_ESCALATE" | null;
    };
    HumanArbitrationCreateResponse: {
      arbitration: components["schemas"]["HumanArbitrationRequestSchemaItem"];
      step_execution: components["schemas"]["StepExecutionSchemaItem"];
      trace_id: string;
    };
    HumanArbitrationRequestSchemaItem: {
      arbitration_key: string;
      context_summary: string;
      human_justification?: string | null;
      id: string;
      options_matrix: (components["schemas"]["ArbitrationOptionSchemaItem"])[];
      outbox_event_id?: string | null;
      question_title: string;
      resolved_by_axiom_key?: string | null;
      resolved_by_user_id?: string | null;
      run_id: string;
      selected_option_key?: string | null;
      status: "PENDING" | "RESOLVED_BY_HUMAN" | "RESOLVED_BY_AXIOM" | "DEFERRED_WITH_ASSUMPTION";
      step_execution_id: string;
      step_key: string;
      tie_break_policy: "ONTOLOGY_AXIOM_FIRST" | "DEFER_AND_CONTINUE_WITH_ASSUMPTION" | "PAUSE_AND_ESCALATE";
      workspace_id: string;
    };
    HumanArbitrationResolveRequest: {
      arbitration_id: string;
      human_justification?: string | null;
      selected_option_key: string;
    };
    HumanArbitrationResolveResponse: {
      arbitration: components["schemas"]["HumanArbitrationRequestSchemaItem"];
      committed_snapshot?: components["schemas"]["BlackboardSnapshotSchemaItem"] | null;
      step_execution: components["schemas"]["StepExecutionSchemaItem"];
      trace_id: string;
    };
    HumanProfileBadge: {
      access_mode: "CONTRIBUTOR_ACTION_REQUIRED" | "READ_ONLY_OBSERVER";
      archetype_key: string;
      display_name: string;
      org_unit_id?: string;
      org_unit_name?: string;
      role?: string;
    };
    HybridRagHitSchemaItem: {
      bm25_rank: number;
      chunk_key: string;
      contextual_header: string;
      datasource_alias: string;
      document_key: string;
      injected_content: string;
      is_stale: boolean;
      parent_chunk_key: string;
      revision_tag: string;
      rrf_score: number;
      source_uri: string;
      stale_warning_marker?: string | null;
      vector_rank: number;
    };
    HybridRagSearchRequest: {
      allowed_datasource_aliases?: (string)[] | null;
      query_text: string;
      top_k?: number;
      workspace_id: string;
    };
    HybridRagSearchResponse: {
      detected_banned_terms: (string)[];
      expanded_terms: (string)[];
      hits: (components["schemas"]["HybridRagHitSchemaItem"])[];
      trace_id?: string | null;
    };
    HydratedStepContextSchemaItem: {
      declared_input_uris: (string)[];
      execution_mode: "INTERACTIVE_COACHING" | "BACKGROUND_FAST_PATH" | "AUTONOMOUS_CONTRACT";
      future_step_instructions_leaked?: number;
      resolved_inputs: Record<string, unknown>;
      run_id: string;
      step_directive: string;
      step_key: string;
      step_title: string;
      step_type: "AGENT" | "SKILL" | "SUB_WORKFLOW" | "HUMAN_TASK" | "HTTP_ACTION" | "POST_ACTION_VERIFICATION";
      undeclared_artifacts_leaked?: number;
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
      scheme: string;
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
      connector_scheme: string;
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
    KbDocumentSchemaItem: {
      age_days: number;
      content_sha256: string;
      datasource_alias: string;
      datasource_id: string;
      doc_key: string;
      freshness_ttl_days: number;
      id: string;
      indexing_regime: string;
      is_stale: boolean;
      revision_tag: string;
      source_scheme: string;
      source_uri: string;
      title: string;
      workspace_id: string;
    };
    KbStaleAlertSchemaItem: {
      alert_key: string;
      alert_reason: "TTL_EXPIRED" | "NEWER_JIRA_CONTRADICTION" | "CODE_DRIFT_DETECTED";
      diagnostic_marker: string;
      document_key: string;
      id: string;
      impacted_run_ids: (string)[];
      justifying_jira_key?: string | null;
      resolved: boolean;
      source_uri: string;
      workspace_id: string;
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
    OntologyAndRagStateResponse: {
      concepts: (components["schemas"]["OntologyConceptSchemaItem"])[];
      documents: (components["schemas"]["KbDocumentSchemaItem"])[];
      promotions: (components["schemas"]["OntologyPromotionProposalSchemaItem"])[];
      relations: (components["schemas"]["OntologyRelationSchemaItem"])[];
      stale_alerts: (components["schemas"]["KbStaleAlertSchemaItem"])[];
      trace_id?: string | null;
      tripartite_edges: (components["schemas"]["TripartiteTraceEdgeSchemaItem"])[];
    };
    OntologyConceptSchemaItem: {
      banned_terms: (string)[];
      canonical_term: string;
      concept_key: string;
      definition_text: string;
      expected_schema: Record<string, string>;
      id: string;
      introduced_in_snapshot_id?: string | null;
      level: "1_ENTERPRISE" | "2_DOMAIN" | "3_TEAM" | "3_WORKSPACE" | "4_RUN_EPHEMERAL";
      parent_concept_id?: string | null;
      profile_translations: Record<string, string>;
      scope_id: string;
      snapshot_branch_status: "ACTIVE" | "SUPERSEDED";
      synonyms: (string)[];
    };
    OntologyPromoteRequest: {
      proposal_key: string;
    };
    OntologyPromotionProposalSchemaItem: {
      badge_color_token?: string;
      canonical_term: string;
      concept_key: string;
      id: string;
      impact_report: components["schemas"]["WhatIfSimulationResponse"];
      proposal_key: string;
      proposed_by_user_id: string;
      source_level: "1_ENTERPRISE" | "2_DOMAIN" | "3_TEAM" | "3_WORKSPACE" | "4_RUN_EPHEMERAL";
      status: "PENDING_REVIEW" | "APPROVED" | "REJECTED";
      target_level: "1_ENTERPRISE" | "2_DOMAIN" | "3_TEAM" | "3_WORKSPACE" | "4_RUN_EPHEMERAL";
      target_scope_id: string;
    };
    OntologyRelationSchemaItem: {
      cardinality: string;
      id: string;
      relation_key: string;
      relation_type: string;
      source_concept_key: string;
      target_concept_key: string;
    };
    OntologyResolveRequest: {
      domain_scope_id?: string;
      enterprise_scope_id?: string;
      human_profile?: string;
      run_scope_id?: string | null;
      team_chain_scope_ids?: (string)[];
      workspace_scope_id?: string;
    };
    OntologyResolveResponse: {
      concepts: (components["schemas"]["OntologyConceptSchemaItem"])[];
      profile_labels: Record<string, string>;
      relations: (components["schemas"]["OntologyRelationSchemaItem"])[];
      trace_id?: string | null;
    };
    OntologyTermInputItem: {
      definition: string;
      level?: "1_ENTERPRISE" | "2_DOMAIN" | "3_TEAM" | "3_WORKSPACE";
      term_key: string;
    };
    OntologyUpsertConceptRequest: {
      banned_terms?: (string)[];
      canonical_term: string;
      concept_key: string;
      definition_text: string;
      expected_schema?: Record<string, string>;
      introduced_in_snapshot_id?: string | null;
      level: "1_ENTERPRISE" | "2_DOMAIN" | "3_TEAM" | "3_WORKSPACE" | "4_RUN_EPHEMERAL";
      parent_concept_id?: string | null;
      profile_translations?: Record<string, string>;
      scope_id: string;
      synonyms?: (string)[];
    };
    OrchestrationSetupStateResponse: {
      compiled_default_template: components["schemas"]["CompiledArtifactTemplateSchemaItem"];
      runs: (components["schemas"]["WorkflowRunSchemaItem"])[];
      trace_id: string;
      workflows: (components["schemas"]["WorkflowAsCodeDefinitionSchemaItem"])[];
    };
    OrgUnitTreeItem: {
      id: string;
      name: string;
      parent_id?: string | null;
      slug: string;
      unit_type: "ENTERPRISE" | "BU" | "TRIBE" | "TEAM" | "SUB_TEAM";
    };
    PassthroughSecretMetadataResponse: {
      connector_scheme: string;
      encrypted_at_rest?: boolean;
      id: string;
      key_version: number;
      target_host: string;
      trace_id: string;
      user_id: string;
    };
    PassthroughSecretStoreRequest: {
      connector_scheme: string;
      plaintext_secret: string;
      target_host: string;
    };
    PermissionBrokerPolicyItem: {
      approved_by_admin_id?: string | null;
      approver_team: string;
      connector_scheme: string;
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
      connector_scheme: string;
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
      connector_scheme: string;
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
    PromptLayerBlockSchemaItem: {
      content_sha256: string;
      immutable: boolean;
      layer_id: "1_CONSTITUTIONAL_IMMUTABLE" | "2_ONTOLOGY_AND_AXIOMS_L1_L4" | "3_HUMAN_PROFILE_ADAPTATION" | "4_FEDERATED_CONTEXT_FANOUT" | "5_CONVERSATIONAL_INTENT_AND_COMPOSER";
      layer_order: number;
    };
    RecursiveRunLockManifestSchemaItem: {
      applied_override_keys: (string)[];
      effective_workflow_sha256: string;
      kb_snapshot_hash: string;
      manifest_sha256: string;
      overrides_sha256: string;
      run_id: string;
      sources: (components["schemas"]["RunLockSourceTripletItem"])[];
      sub_workflow_locks: (components["schemas"]["SubWorkflowLockSchemaItem"])[];
      workflow_sha256: string;
      workflow_uri: string;
      workflow_version: string;
      workspace_id: string;
    };
    RunBlackboardStateResponse: {
      accumulated_root_cost_usd: number;
      active_snapshots: (components["schemas"]["BlackboardSnapshotSchemaItem"])[];
      root_run_id: string;
      run_id: string;
      run_status?: string;
      step_executions: (components["schemas"]["StepExecutionSchemaItem"])[];
      trace_id: string;
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
      scheme: string;
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
      key: "cockpit" | "inbox" | "catalog" | "ontology" | "gates" | "finops" | "admin" | "bootstrap";
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
    StepExecuteRequest: {
      author_type?: "HUMAN" | "AGENT";
      commit_immediately?: boolean;
      cost_usd?: number;
      divergence_note?: string | null;
      human_decision?: string | null;
      require_human_anchor?: boolean;
      run_id: string;
      simulated_divergence?: string | null;
      step_key: string;
    };
    StepExecuteResponse: {
      committed_snapshot?: components["schemas"]["BlackboardSnapshotSchemaItem"] | null;
      step_execution: components["schemas"]["StepExecutionSchemaItem"];
      trace_id: string;
    };
    StepExecutionSchemaItem: {
      attempt_count: number;
      child_run_id?: string | null;
      committed_snapshot_id?: string | null;
      cost_usd: number;
      draft_artifact: Record<string, unknown>;
      draft_cas_key?: string | null;
      execution_mode: "INTERACTIVE_COACHING" | "BACKGROUND_FAST_PATH" | "AUTONOMOUS_CONTRACT";
      hydrated_input_uris?: (string)[];
      id: string;
      max_agent_retries: number;
      run_id: string;
      status: "PENDING" | "WAITING_FOR_HUMAN_ANCHOR" | "EXECUTING_AGENT" | "WAITING_FOR_HUMAN_ARBITRATION" | "EVALUATING_GATES" | "WAITING_FOR_HUMAN_GATE" | "COMMITTED" | "CHALLENGED_REWIND" | "FAILED";
      step_execution_key: string;
      step_index: number;
      step_key: string;
      step_memlog?: (components["schemas"]["StepMemlogSchemaItem"])[];
      step_type: "AGENT" | "SKILL" | "SUB_WORKFLOW" | "HUMAN_TASK" | "HTTP_ACTION" | "POST_ACTION_VERIFICATION";
    };
    StepHumanResumeRequest: {
      decision: string;
    };
    StepHydrateRequest: {
      run_id: string;
      step_key: string;
    };
    StepHydrateResponse: {
      hydrated_context: components["schemas"]["HydratedStepContextSchemaItem"];
      trace_id: string;
    };
    StepMemlogSchemaItem: {
      details: string;
      entry_id: string;
      marker_type: string;
      source_uris?: (string)[];
      step_key: string;
      summary: string;
    };
    SubWorkflowLockSchemaItem: {
      applied_override_keys: (string)[];
      effective_workflow_sha256: string;
      nesting_depth: number;
      sources: (components["schemas"]["RunLockSourceTripletItem"])[];
      step_key: string;
      sub_workflow_locks?: (components["schemas"]["SubWorkflowLockSchemaItem"])[];
      workflow_sha256: string;
      workflow_uri: string;
      workflow_version: string;
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
    TripartiteTraceEdgeSchemaItem: {
      edge_key: string;
      id: string;
      jira_issue_key?: string | null;
      relation_type: "DOCUMENTS" | "SPECIFIES" | "FIXES" | "BLOCKS" | "IMPLEMENTS_ISSUE" | "AFFECTS_CONCEPT";
      source_node_type: "CONFLUENCE_PAGE" | "JIRA_ISSUE" | "GIT_SYMBOL" | "GIT_COMMIT" | "ONTOLOGY_CONCEPT";
      source_uri: string;
      target_node_type: "CONFLUENCE_PAGE" | "JIRA_ISSUE" | "GIT_SYMBOL" | "GIT_COMMIT" | "ONTOLOGY_CONCEPT";
      target_uri: string;
      workspace_id: string;
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
      linked_connectors: (string)[];
      org_unit_id: string;
      user_email: string;
      user_id?: string | null;
      workspace_ids: (string)[];
    };
    WhatIfSimulationRequest: {
      concept_key: string;
      proposed_change: string;
    };
    WhatIfSimulationResponse: {
      canonical_term: string;
      concept_key: string;
      has_immutable_axiom_conflict: boolean;
      impacted_active_run_ids: (string)[];
      impacted_artifact_templates: (string)[];
      impacted_workflow_uris: (string)[];
      proposed_change: string;
      trace_id?: string | null;
      transitively_affected_concepts: (string)[];
    };
    WorkflowAsCodeDefinitionSchemaItem: {
      adaptive_gate_policy: "STRICT" | "STANDARD" | "FAST_TRACK";
      criticality: "LOW_NON_CRITICAL" | "STANDARD" | "HIGH_CRITICAL";
      datasources: (string)[];
      description: string;
      execution_regime: "INTERACTIVE_COACHING" | "BACKGROUND_FAST_PATH" | "AUTONOMOUS_CONTRACT";
      facts: (string)[];
      id: string;
      max_cost_usd: number;
      max_nesting_depth: number;
      mode: string;
      rules: (string)[];
      scalars: Record<string, string | number | boolean>;
      sha256: string;
      steps: (components["schemas"]["WorkflowStepSpecSchemaItem"])[];
      tie_break_policy: "ONTOLOGY_AXIOM_FIRST" | "DEFER_AND_CONTINUE_WITH_ASSUMPTION" | "PAUSE_AND_ESCALATE";
      title: string;
      uri: string;
      version: string;
      workspace_id?: string | null;
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
    WorkflowManifestRegisterRequest: {
      raw_manifest: string;
      workspace_id?: string | null;
    };
    WorkflowManifestRegisterResponse: {
      trace_id: string;
      workflow: components["schemas"]["WorkflowAsCodeDefinitionSchemaItem"];
    };
    WorkflowManifestValidateRequest: {
      raw_manifest: string;
      workspace_id?: string | null;
    };
    WorkflowManifestValidateResponse: {
      findings: (components["schemas"]["WorkflowValidationFindingSchemaItem"])[];
      resolved_max_nesting_depth: number;
      topological_order: (string)[];
      trace_id: string;
      valid: boolean;
      workflow?: components["schemas"]["WorkflowAsCodeDefinitionSchemaItem"] | null;
    };
    WorkflowRunInstantiateRequest: {
      execution_identity_mode?: "passthrough" | "service_principal";
      parent_run_id?: string | null;
      parent_step_execution_id?: string | null;
      trigger_id?: string | null;
      trigger_idempotency_key?: string | null;
      workflow_uri: string;
      workspace_id: string;
    };
    WorkflowRunInstantiateResponse: {
      run: components["schemas"]["WorkflowRunSchemaItem"];
      trace_id: string;
    };
    WorkflowRunSchemaItem: {
      budget_max_usd: number;
      criticality: "LOW_NON_CRITICAL" | "STANDARD" | "HIGH_CRITICAL";
      execution_identity_mode: "passthrough" | "service_principal";
      execution_regime: "INTERACTIVE_COACHING" | "BACKGROUND_FAST_PATH" | "AUTONOMOUS_CONTRACT";
      id: string;
      initiated_by_user_id?: string | null;
      nesting_depth: number;
      parent_run_id?: string | null;
      parent_step_execution_id?: string | null;
      root_run_id: string;
      run_key: string;
      run_lock: components["schemas"]["RecursiveRunLockManifestSchemaItem"];
      status: "INITIALIZED" | "RUNNING" | "WAITING_FOR_HUMAN_ARBITRATION" | "WAITING_FOR_HUMAN_GATE" | "PAUSED_CIRCUIT_BREAKER" | "PAUSED_BUDGET_EXCEEDED" | "COMPLETED" | "FAILED" | "ROLLED_BACK";
      trigger_id?: string | null;
      trigger_idempotency_key?: string | null;
      workflow_def_id: string;
      workflow_uri: string;
      workspace_id: string;
    };
    WorkflowStepItem: {
      human_authored_required: boolean;
      instructions: string;
      step_key: string;
      title: string;
    };
    WorkflowStepSpecSchemaItem: {
      agent_uri?: string | null;
      declares_intention: boolean;
      depends_on: (string)[];
      feedback_target_step_key?: string | null;
      human_authored_required: boolean;
      input_mapping: Record<string, string>;
      instructions: string;
      kb_uris: (string)[];
      line_number: number;
      max_agent_retries: number;
      output_mapping: Record<string, string>;
      policies?: (string)[];
      requires_human_gate: boolean;
      reverse_doc_from_code: boolean;
      skill_uri?: string | null;
      step_key: string;
      step_type: "AGENT" | "SKILL" | "SUB_WORKFLOW" | "HUMAN_TASK" | "HTTP_ACTION" | "POST_ACTION_VERIFICATION";
      sub_workflow_uri?: string | null;
      tags?: (string)[];
      template_key?: string | null;
      title: string;
      verification_window_seconds?: number | null;
      writes_code: boolean;
    };
    WorkflowValidationFindingSchemaItem: {
      field_path: string;
      line: number;
      message: string;
      rule_code: string;
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
      scheme: string;
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
    XyFlowEdgeSchemaItem: {
      animated?: boolean;
      id: string;
      source: string;
      target: string;
    };
    XyFlowNodeSchemaItem: {
      human_authored_required: boolean;
      id: string;
      label: string;
      position_x: number;
      position_y: number;
      step_type: string;
    };
  };
}

export interface paths {
  "/api/v1/assistant/chat": {
    post: {
      responses: {
        200: components["schemas"]["AssistantChatResponse"];
      };
    };
  };
  "/api/v1/assistant/chat/stream": {
    post: {
      responses: {
        200: unknown;
      };
    };
  };
  "/api/v1/assistant/workflows/save-and-launch": {
    post: {
      responses: {
        200: components["schemas"]["AssistantSaveAndLaunchResponse"];
      };
    };
  };
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
  "/api/v1/ontology-rag/ontology/concepts": {
    post: {
      responses: {
        200: components["schemas"]["OntologyConceptSchemaItem"];
      };
    };
  };
  "/api/v1/ontology-rag/ontology/promote": {
    post: {
      responses: {
        200: components["schemas"]["OntologyPromotionProposalSchemaItem"];
      };
    };
  };
  "/api/v1/ontology-rag/ontology/resolve": {
    post: {
      responses: {
        200: components["schemas"]["OntologyResolveResponse"];
      };
    };
  };
  "/api/v1/ontology-rag/ontology/what-if": {
    post: {
      responses: {
        200: components["schemas"]["WhatIfSimulationResponse"];
      };
    };
  };
  "/api/v1/ontology-rag/rag/index-db-ddl": {
    post: {
      responses: {
        200: components["schemas"]["KbDocumentSchemaItem"];
      };
    };
  };
  "/api/v1/ontology-rag/rag/search": {
    post: {
      responses: {
        200: components["schemas"]["HybridRagSearchResponse"];
      };
    };
  };
  "/api/v1/ontology-rag/state": {
    get: {
      responses: {
        200: components["schemas"]["OntologyAndRagStateResponse"];
      };
    };
  };
  "/api/v1/ontology-rag/tripartite/audit-doc-vs-code": {
    post: {
      responses: {
        200: components["schemas"]["DocVsCodeAuditResponse"];
      };
    };
  };
  "/api/v1/orchestration/runs/anchors/sign": {
    post: {
      responses: {
        200: components["schemas"]["HumanAnchorSignResponse"];
      };
    };
  };
  "/api/v1/orchestration/runs/fast-path-audit": {
    post: {
      responses: {
        200: components["schemas"]["BackgroundAuditRunResponse"];
      };
    };
  };
  "/api/v1/orchestration/runs/instantiate": {
    post: {
      responses: {
        200: components["schemas"]["WorkflowRunInstantiateResponse"];
      };
    };
  };
  "/api/v1/orchestration/runs/steps/execute": {
    post: {
      responses: {
        200: components["schemas"]["StepExecuteResponse"];
      };
    };
  };
  "/api/v1/orchestration/runs/steps/hydrate": {
    post: {
      responses: {
        200: components["schemas"]["StepHydrateResponse"];
      };
    };
  };
  "/api/v1/orchestration/runs/{run_id}/blackboard": {
    get: {
      responses: {
        200: components["schemas"]["RunBlackboardStateResponse"];
      };
    };
  };
  "/api/v1/orchestration/runs/{run_id}/steps/{step_key}/arbitration": {
    post: {
      responses: {
        200: components["schemas"]["HumanArbitrationCreateResponse"];
      };
    };
  };
  "/api/v1/orchestration/runs/{run_id}/steps/{step_key}/arbitration/resolve": {
    post: {
      responses: {
        200: components["schemas"]["HumanArbitrationResolveResponse"];
      };
    };
  };
  "/api/v1/orchestration/runs/{run_id}/steps/{step_key}/resume": {
    post: {
      responses: {
        200: components["schemas"]["StepExecuteResponse"];
      };
    };
  };
  "/api/v1/orchestration/state": {
    get: {
      responses: {
        200: components["schemas"]["OrchestrationSetupStateResponse"];
      };
    };
  };
  "/api/v1/orchestration/templates/compile": {
    post: {
      responses: {
        200: components["schemas"]["ArtifactTemplateCompileResponse"];
      };
    };
  };
  "/api/v1/orchestration/workflows/register": {
    post: {
      responses: {
        200: components["schemas"]["WorkflowManifestRegisterResponse"];
      };
    };
  };
  "/api/v1/orchestration/workflows/validate": {
    post: {
      responses: {
        200: components["schemas"]["WorkflowManifestValidateResponse"];
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

export type ArbitrationOptionSchemaItem = components["schemas"]["ArbitrationOptionSchemaItem"];
export type ArtifactTemplateCompileRequest = components["schemas"]["ArtifactTemplateCompileRequest"];
export type ArtifactTemplateCompileResponse = components["schemas"]["ArtifactTemplateCompileResponse"];
export type AssistantChatRequest = components["schemas"]["AssistantChatRequest"];
export type AssistantChatResponse = components["schemas"]["AssistantChatResponse"];
export type AssistantNodeTraceSchemaItem = components["schemas"]["AssistantNodeTraceSchemaItem"];
export type AssistantSaveAndLaunchRequest = components["schemas"]["AssistantSaveAndLaunchRequest"];
export type AssistantSaveAndLaunchResponse = components["schemas"]["AssistantSaveAndLaunchResponse"];
export type AssistantWorkflowProposalSchemaItem = components["schemas"]["AssistantWorkflowProposalSchemaItem"];
export type AuthTokenResponse = components["schemas"]["AuthTokenResponse"];
export type BackgroundAuditReportSchemaItem = components["schemas"]["BackgroundAuditReportSchemaItem"];
export type BackgroundAuditRunRequest = components["schemas"]["BackgroundAuditRunRequest"];
export type BackgroundAuditRunResponse = components["schemas"]["BackgroundAuditRunResponse"];
export type BlackboardSnapshotSchemaItem = components["schemas"]["BlackboardSnapshotSchemaItem"];
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
export type CompiledArtifactTemplateSchemaItem = components["schemas"]["CompiledArtifactTemplateSchemaItem"];
export type CompiledMarkdownChunkSchemaItem = components["schemas"]["CompiledMarkdownChunkSchemaItem"];
export type DbDdlIndexRequest = components["schemas"]["DbDdlIndexRequest"];
export type DocVsCodeAuditRequest = components["schemas"]["DocVsCodeAuditRequest"];
export type DocVsCodeAuditResponse = components["schemas"]["DocVsCodeAuditResponse"];
export type EffectiveWorkflowResolveRequest = components["schemas"]["EffectiveWorkflowResolveRequest"];
export type EffectiveWorkflowResolveResponse = components["schemas"]["EffectiveWorkflowResolveResponse"];
export type EvaluationLensItem = components["schemas"]["EvaluationLensItem"];
export type HealthResponse = components["schemas"]["HealthResponse"];
export type HumanAnchorSignRequest = components["schemas"]["HumanAnchorSignRequest"];
export type HumanAnchorSignResponse = components["schemas"]["HumanAnchorSignResponse"];
export type HumanAnchorSignatureSchemaItem = components["schemas"]["HumanAnchorSignatureSchemaItem"];
export type HumanArbitrationCreateRequest = components["schemas"]["HumanArbitrationCreateRequest"];
export type HumanArbitrationCreateResponse = components["schemas"]["HumanArbitrationCreateResponse"];
export type HumanArbitrationRequestSchemaItem = components["schemas"]["HumanArbitrationRequestSchemaItem"];
export type HumanArbitrationResolveRequest = components["schemas"]["HumanArbitrationResolveRequest"];
export type HumanArbitrationResolveResponse = components["schemas"]["HumanArbitrationResolveResponse"];
export type HumanProfileBadge = components["schemas"]["HumanProfileBadge"];
export type HybridRagHitSchemaItem = components["schemas"]["HybridRagHitSchemaItem"];
export type HybridRagSearchRequest = components["schemas"]["HybridRagSearchRequest"];
export type HybridRagSearchResponse = components["schemas"]["HybridRagSearchResponse"];
export type HydratedStepContextSchemaItem = components["schemas"]["HydratedStepContextSchemaItem"];
export type InitDatasourceRequest = components["schemas"]["InitDatasourceRequest"];
export type InitDatasourceResponse = components["schemas"]["InitDatasourceResponse"];
export type InitOrganizationRequest = components["schemas"]["InitOrganizationRequest"];
export type InitOrganizationResponse = components["schemas"]["InitOrganizationResponse"];
export type InitUserPassthroughSecretItem = components["schemas"]["InitUserPassthroughSecretItem"];
export type InitUserRequest = components["schemas"]["InitUserRequest"];
export type InitUserResponse = components["schemas"]["InitUserResponse"];
export type InitWorkspaceRequest = components["schemas"]["InitWorkspaceRequest"];
export type InitWorkspaceResponse = components["schemas"]["InitWorkspaceResponse"];
export type KbDocumentSchemaItem = components["schemas"]["KbDocumentSchemaItem"];
export type KbStaleAlertSchemaItem = components["schemas"]["KbStaleAlertSchemaItem"];
export type LlmModelEndpointItem = components["schemas"]["LlmModelEndpointItem"];
export type LocalLoginRequest = components["schemas"]["LocalLoginRequest"];
export type LogoutResponse = components["schemas"]["LogoutResponse"];
export type MemberInvitationInputItem = components["schemas"]["MemberInvitationInputItem"];
export type OidcLoginRequest = components["schemas"]["OidcLoginRequest"];
export type OntologyAndRagStateResponse = components["schemas"]["OntologyAndRagStateResponse"];
export type OntologyConceptSchemaItem = components["schemas"]["OntologyConceptSchemaItem"];
export type OntologyPromoteRequest = components["schemas"]["OntologyPromoteRequest"];
export type OntologyPromotionProposalSchemaItem = components["schemas"]["OntologyPromotionProposalSchemaItem"];
export type OntologyRelationSchemaItem = components["schemas"]["OntologyRelationSchemaItem"];
export type OntologyResolveRequest = components["schemas"]["OntologyResolveRequest"];
export type OntologyResolveResponse = components["schemas"]["OntologyResolveResponse"];
export type OntologyTermInputItem = components["schemas"]["OntologyTermInputItem"];
export type OntologyUpsertConceptRequest = components["schemas"]["OntologyUpsertConceptRequest"];
export type OrchestrationSetupStateResponse = components["schemas"]["OrchestrationSetupStateResponse"];
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
export type PromptLayerBlockSchemaItem = components["schemas"]["PromptLayerBlockSchemaItem"];
export type RecursiveRunLockManifestSchemaItem = components["schemas"]["RecursiveRunLockManifestSchemaItem"];
export type RunBlackboardStateResponse = components["schemas"]["RunBlackboardStateResponse"];
export type RunLockManifestItem = components["schemas"]["RunLockManifestItem"];
export type RunLockSourceTripletItem = components["schemas"]["RunLockSourceTripletItem"];
export type ScopeMutationCheckResponse = components["schemas"]["ScopeMutationCheckResponse"];
export type ScopeNode = components["schemas"]["ScopeNode"];
export type ShellModuleItem = components["schemas"]["ShellModuleItem"];
export type ShellNavigationResponse = components["schemas"]["ShellNavigationResponse"];
export type StepExecuteRequest = components["schemas"]["StepExecuteRequest"];
export type StepExecuteResponse = components["schemas"]["StepExecuteResponse"];
export type StepExecutionSchemaItem = components["schemas"]["StepExecutionSchemaItem"];
export type StepHumanResumeRequest = components["schemas"]["StepHumanResumeRequest"];
export type StepHydrateRequest = components["schemas"]["StepHydrateRequest"];
export type StepHydrateResponse = components["schemas"]["StepHydrateResponse"];
export type StepMemlogSchemaItem = components["schemas"]["StepMemlogSchemaItem"];
export type SubWorkflowLockSchemaItem = components["schemas"]["SubWorkflowLockSchemaItem"];
export type SystemBootstrapRunItem = components["schemas"]["SystemBootstrapRunItem"];
export type SystemBootstrapStateResponse = components["schemas"]["SystemBootstrapStateResponse"];
export type SystemBootstrapWorkflowItem = components["schemas"]["SystemBootstrapWorkflowItem"];
export type TripartiteTraceEdgeSchemaItem = components["schemas"]["TripartiteTraceEdgeSchemaItem"];
export type UserMeResponse = components["schemas"]["UserMeResponse"];
export type UserOnboardingStateItem = components["schemas"]["UserOnboardingStateItem"];
export type WhatIfSimulationRequest = components["schemas"]["WhatIfSimulationRequest"];
export type WhatIfSimulationResponse = components["schemas"]["WhatIfSimulationResponse"];
export type WorkflowAsCodeDefinitionSchemaItem = components["schemas"]["WorkflowAsCodeDefinitionSchemaItem"];
export type WorkflowDefinitionResponseItem = components["schemas"]["WorkflowDefinitionResponseItem"];
export type WorkflowManifestRegisterRequest = components["schemas"]["WorkflowManifestRegisterRequest"];
export type WorkflowManifestRegisterResponse = components["schemas"]["WorkflowManifestRegisterResponse"];
export type WorkflowManifestValidateRequest = components["schemas"]["WorkflowManifestValidateRequest"];
export type WorkflowManifestValidateResponse = components["schemas"]["WorkflowManifestValidateResponse"];
export type WorkflowRunInstantiateRequest = components["schemas"]["WorkflowRunInstantiateRequest"];
export type WorkflowRunInstantiateResponse = components["schemas"]["WorkflowRunInstantiateResponse"];
export type WorkflowRunSchemaItem = components["schemas"]["WorkflowRunSchemaItem"];
export type WorkflowStepItem = components["schemas"]["WorkflowStepItem"];
export type WorkflowStepSpecSchemaItem = components["schemas"]["WorkflowStepSpecSchemaItem"];
export type WorkflowValidationFindingSchemaItem = components["schemas"]["WorkflowValidationFindingSchemaItem"];
export type WorkspaceBootstrapInputItem = components["schemas"]["WorkspaceBootstrapInputItem"];
export type WorkspaceDatasourceItem = components["schemas"]["WorkspaceDatasourceItem"];
export type WorkspaceSummaryItem = components["schemas"]["WorkspaceSummaryItem"];
export type WorkspacesListResponse = components["schemas"]["WorkspacesListResponse"];
export type XyFlowEdgeSchemaItem = components["schemas"]["XyFlowEdgeSchemaItem"];
export type XyFlowNodeSchemaItem = components["schemas"]["XyFlowNodeSchemaItem"];
