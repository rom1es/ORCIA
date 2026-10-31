/**
 * AUTO-GENERATED FILE FROM FASTAPI OPENAPI 3.1 SCHEMA — DO NOT EDIT MANUALLY.
 * Regenerate via: `.venv/bin/python scripts/export_openapi.py`
 */

export interface components {
  schemas: {
    AccostageStatusResponse: {
      agentic_gates_ad10_enabled: boolean;
      amber_warning_badge?: string | null;
      assistant_trial_enabled: boolean;
      badge_label: string;
      completed_count: number;
      completed_milestone_keys: (string)[];
      distinct_families: (string)[];
      llm_tier_mode: "UNCONFIGURED" | "QUICK_TRIAL_SINGLE_FAMILY" | "FULL_ORTHOGONAL_AD10";
      total_count: number;
      trace_id: string;
    };
    AcquireResourceLeasesRequest: {
      ancestor_run_ids?: (string)[];
      holder_parent_run_id?: string | null;
      holder_root_run_id: string;
      holder_run_id: string;
      holder_step_execution_id: string;
      resource_uris: (string)[];
      ttl_seconds?: number;
    };
    AcquireResourceLeasesResponse: {
      canonical_order: (string)[];
      leases: (components["schemas"]["ResourceLeaseItemResponse"])[];
      trace_id: string;
    };
    AgenticGateEvaluateRequest: {
      anonymize_pii_reversible?: boolean;
      candidate_artifact?: Record<string, unknown>;
      custom_pii_entities?: (string)[];
      data_classification?: "PUBLIC" | "INTERNAL" | "SENSITIVE" | "RESTRICTED";
      evaluator_model_family: string;
      evaluator_model_id?: string;
      executor_model_family: string;
      fact_confidence_threshold?: number;
      ontology_facts?: Record<string, string>;
      pass_score_threshold?: number;
      pinned_kb_facts?: Record<string, string>;
      run_id: string;
      step1_prd_invariants?: (string)[];
      step2_arch_invariants?: (string)[];
      step_execution_id: string;
      step_key: string;
      step_memlog_markers?: (Record<string, string>)[];
      workspace_id: string;
    };
    AgenticGateEvaluateResponse: {
      briefing_4blocks: Record<string, unknown>;
      cot_items_purged: number;
      evaluation: components["schemas"]["GateEvaluationSchemaItem"];
      lens_results: (Record<string, unknown>)[];
      pii_tokens_redacted: number;
      rehydrated_summary: string;
      routed_model_family: string;
      routed_model_id: string;
      routed_to_local_sovereign_model: boolean;
      trace_id: string;
    };
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
    ChunkApprovalSchemaItem: {
      challenge_reason?: string | null;
      chunk_key: string;
      content_markdown?: string;
      gate_evaluation_id: string;
      human_anchor_sha256?: string | null;
      human_anchor_signature_id?: string | null;
      human_authored_required?: boolean;
      id: string;
      reviewed_at?: string | null;
      reviewer_user_id?: string | null;
      run_id: string;
      section_index?: number;
      section_title: string;
      status?: "PENDING" | "APPROVED" | "CO_EDITED" | "CHALLENGED";
      step_execution_id: string;
      word_count?: number;
      workspace_id: string;
    };
    ClaimTaskRequest: {
      force?: boolean;
      step_key?: string;
      ttl_seconds?: number;
      workspace_id?: string;
    };
    ClaimTaskResponse: {
      lock_key?: string | null;
      notification: components["schemas"]["TaskNotificationItemResponse"];
      peer_presence_state: "UNCLAIMED" | "CLAIMED_BY_ME" | "CLAIMED_BY_PEER";
      sse_event: components["schemas"]["SseEventEnvelopeResponse"];
      trace_id: string;
      viewer_presence_state: "UNCLAIMED" | "CLAIMED_BY_ME" | "CLAIMED_BY_PEER";
    };
    CognitiveRoutingOutcomeResponse: {
      attempts: (components["schemas"]["InferenceAttemptResponse"])[];
      effort: "default" | "fast" | "balanced" | "deep";
      final_resolved_tier: "simple" | "medium" | "complex";
      model_family: string;
      model_name: string;
      paused_budget_exceeded: boolean;
      requested_tier: "simple" | "medium" | "complex" | "auto";
      response_content: string;
      run_id: string;
      step_execution_id: string;
      total_cost_usd: number;
    };
    CommandPaletteEntryResponse: {
      access_mode?: "CONTRIBUTOR_ACTION_REQUIRED" | "READ_ONLY_OBSERVER" | null;
      category: "RUN" | "WORKSPACE" | "NAVIGATION" | "ONTOLOGY" | "CATALOG";
      entry_id: string;
      label_fr: string;
      shortcut: string;
      subtitle_fr: string;
      target_route: string;
    };
    CommandPaletteSearchResponse: {
      items: (components["schemas"]["CommandPaletteEntryResponse"])[];
      query: string;
      trace_id: string;
    };
    CommitStagedJiraActionRequest: {
      gate_status: "PASS" | "FAIL" | "WAITING_HUMAN";
      run_lock_sha256: string;
      staged_action_id: string;
    };
    CommitStagedJiraActionResponse: {
      executed_action: components["schemas"]["StagedJiraActionItemSchema"];
      trace_id: string;
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
    ConnectorTestConnectionResponse: {
      connector_id: string;
      diagnostic_message: string;
      latency_ms: number;
      scheme: string;
      status: "HEALTHY" | "DEGRADED" | "UNREACHABLE";
      tested_at_iso: string;
      timeout_budget_ms: number;
      uri: string;
    };
    ControlCenterOverviewResponse: {
      consolidated_finops_usd: number;
      contributor_runs: (components["schemas"]["SupervisedRunItemResponse"])[];
      datasources: (components["schemas"]["SupervisedDatasourceItemResponse"])[];
      guidance_steps: (components["schemas"]["GuidanceStepItemResponse"])[];
      observer_banner_fr?: string | null;
      observer_runs: (components["schemas"]["SupervisedRunItemResponse"])[];
      org_units: (components["schemas"]["OrgUnitSummaryResponse"])[];
      scope_id: string;
      scope_label: string;
      scope_type: "GLOBAL" | "BU" | "TEAM" | "WORKSPACE";
      trace_id: string;
      viewer_access_mode: "CONTRIBUTOR_ACTION_REQUIRED" | "READ_ONLY_OBSERVER";
      workflow_overrides: (components["schemas"]["DeclarativeOverrideLayerResponse"])[];
      workspaces_governance: (components["schemas"]["WorkspaceGovernanceItemResponse"])[];
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
    DeclarativeOverrideLayerResponse: {
      base_layer: string;
      spine_contract_ref: string;
      team_override: string;
      title: string;
      user_override: string;
      workflow_key: string;
      workspace_override: string;
    };
    DelegateGrantRequest: {
      actor_persona?: string;
      conditions?: Record<string, unknown>;
      effect?: "ALLOW" | "DENY";
      hidden_when_unauthorized?: boolean;
      inheritance_block?: boolean;
      scope_path?: string;
      subject_id?: string;
      subject_type?: "USER" | "ROLE" | "SERVICE_PRINCIPAL";
      verbs?: ("create" | "read" | "update" | "delete" | "execute" | "grant")[];
      workspace_id?: string | null;
    };
    DemoWorkspaceProvisionResponse: {
      kb_documents_indexed: number;
      ontology_concepts_seeded: number;
      plaintext_secrets_count: number;
      published_workflow_uri: string;
      rag_reciprocity_verified: boolean;
      workspace_id: string;
      workspace_name: string;
      workspace_slug: string;
    };
    DeploymentRoleSchemaItem: {
      description: string;
      entrypoint_command: (string)[];
      forbidden_modules_in_process: (string)[];
      loads_docling: boolean;
      required_extras: (string)[];
      role: string;
      supported_sandbox_tiers: (string)[];
    };
    DeploymentRolesListResponse: {
      roles: (components["schemas"]["DeploymentRoleSchemaItem"])[];
      trace_id: string;
    };
    DeterministicGateEvaluateRequest: {
      allowed_dependencies?: (string)[] | null;
      artifact_payload?: Record<string, unknown>;
      max_memory_mb?: number;
      ontology_axioms?: (components["schemas"]["OntologyAxiomRuleInputItem"])[];
      raise_on_failure?: boolean;
      required_sections?: (string)[];
      run_id: string;
      simulate_fs_escape_path?: string | null;
      simulate_memory_alloc_mb?: number;
      simulate_network_escape?: boolean;
      simulate_timeout_sleep_ms?: number;
      simulate_tmp_overflow_mb?: number;
      step_execution_id: string;
      step_key: string;
      timeout_ms?: number;
      workspace_id: string;
    };
    DeterministicGateEvaluateResponse: {
      evaluation: components["schemas"]["GateEvaluationSchemaItem"];
      trace_id: string;
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
    DocumentIngestionRequest: {
      actor_persona?: string;
      classification?: "C0_C2_STANDARD" | "C3_CONFIDENTIAL_RESTRICTED";
      pii_decision?: "PSEUDONYMIZE" | "INDEX_AS_IS_AUDITED" | "CANCEL_IMPORT" | null;
      raw_extracted_text?: string;
      title?: string;
      uri?: string;
      workspace_id?: string;
    };
    DocumentIngestionResponse: {
      arbitration_options: ("PSEUDONYMIZE" | "INDEX_AS_IS_AUDITED" | "CANCEL_IMPORT")[];
      audit_derogation_recorded: boolean;
      classification: "C0_C2_STANDARD" | "C3_CONFIDENTIAL_RESTRICTED";
      document_id: string;
      extracted_char_count: number;
      indexed_chunk_id?: string | null;
      pii_categories: (string)[];
      pii_detected: boolean;
      pseudonymized: boolean;
      status: "INDEXED" | "WAITING_FOR_PII_ARBITRATION" | "CANCELLED";
      title: string;
      uri: string;
      workspace_id: string;
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
    EvaluateResourceAccessRequest: {
      context?: Record<string, unknown>;
      require_execute?: boolean;
      require_secret_read?: boolean;
      roles?: (string)[];
      scope_path?: string;
      subject_id?: string;
      subject_type?: "USER" | "ROLE" | "SERVICE_PRINCIPAL";
      title?: string;
    };
    EvaluationLensItem: {
      code: string;
      threshold: number;
      weight: number;
    };
    ExecuteTierRoutingRequest: {
      effort?: "default" | "fast" | "balanced" | "deep";
      evaluator_model_family?: string | null;
      fail_simple_tier_gate?: boolean;
      inference_tier?: "simple" | "medium" | "complex" | "auto";
      run_id?: string;
      scope_id?: string;
      step_execution_id?: string;
      system_prompt?: string;
      user_prompt?: string;
    };
    GateEvaluationSchemaItem: {
      duration_ms: number;
      evaluated_at: string;
      gate_type: "DETERMINISTIC" | "AGENTIC" | "HUMAN";
      id: string;
      missing_sections: (string)[];
      ontology_axioms_passed: boolean;
      outbox_event_id?: string | null;
      pattern_drift_findings: (components["schemas"]["PatternDriftFindingSchemaItem"])[];
      pattern_drift_passed: boolean;
      run_id: string;
      sandbox_exit_code?: number;
      sandbox_stderr?: string;
      sandbox_tier: "TIER_1_WASM" | "TIER_2_CONTAINER" | "NONE";
      schema_validation_passed: boolean;
      score: number;
      status: "PASS" | "FAIL" | "ERROR" | "PENDING_HUMAN_REVIEW";
      step_execution_id: string;
      step_key: string;
      violated_axioms: (Record<string, string>)[];
      workspace_id: string;
    };
    GateEvaluationsListResponse: {
      evaluations: (components["schemas"]["GateEvaluationSchemaItem"])[];
      trace_id: string;
    };
    GuidanceStepItemResponse: {
      action_command: string;
      description_fr: string;
      step_number: number;
      title_fr: string;
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
    HumanGateChunkDecideRequest: {
      action: "APPROVE" | "CO_EDIT" | "CHALLENGE";
      challenge_reason?: string | null;
      co_edited_content?: string | null;
    };
    HumanGateChunkDecideResponse: {
      chunk: components["schemas"]["ChunkApprovalSchemaItem"];
      evaluation: components["schemas"]["HumanGateEvaluationSchemaItem"];
      trace_id: string;
    };
    HumanGateEvaluateRequest: {
      agentic_score?: number;
      artifact_payload?: Record<string, unknown>;
      briefing_4blocks_jsonb?: Record<string, unknown> | null;
      deterministic_status?: string;
      ontology_conflicts?: number;
      policy?: "mandatory_full" | "risk_or_exception_based" | "sampling";
      run_id: string;
      sampling_override?: boolean | null;
      stale_warnings?: number;
      step_execution_id: string;
      step_key: string;
      workspace_id: string;
    };
    HumanGateEvaluateResponse: {
      evaluation: components["schemas"]["HumanGateEvaluationSchemaItem"];
      trace_id: string;
    };
    HumanGateEvaluationSchemaItem: {
      agentic_score: number;
      auto_passed: boolean;
      briefing_4blocks_jsonb: Record<string, unknown>;
      chunks: (components["schemas"]["ChunkApprovalSchemaItem"])[];
      deterministic_status: string;
      evaluated_at: string;
      fast_approval_warning: boolean;
      hypotheses_block_inspected: boolean;
      id: string;
      ontology_conflicts: number;
      outbox_event_id?: string | null;
      policy: "mandatory_full" | "risk_or_exception_based" | "sampling";
      review_duration_ms: number;
      reviewer_user_id?: string | null;
      run_id: string;
      stale_warnings: number;
      status: "PASS" | "FAIL" | "PENDING_HUMAN_REVIEW";
      step_execution_id: string;
      step_key: string;
      total_word_count: number;
      workspace_id: string;
    };
    HumanGateFinalizeRequest: {
      explicit_hypotheses_confirmation?: boolean;
      review_duration_ms: number;
    };
    HumanGateFinalizeResponse: {
      evaluation: components["schemas"]["HumanGateEvaluationSchemaItem"];
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
    InboxNotificationListResponse: {
      amber_badge_count: number;
      items: (components["schemas"]["TaskNotificationItemResponse"])[];
      trace_id: string;
      viewer_user_id: string;
      workspace_id: string;
    };
    InferenceAttemptResponse: {
      attempt_index: number;
      cost_usd: number;
      deterministic_gate_passed: boolean;
      effort: "default" | "fast" | "balanced" | "deep";
      failure_reason: string;
      id: string;
      idempotency_key: string;
      model_family: string;
      model_name: string;
      requested_tier: "simple" | "medium" | "complex" | "auto";
      resolved_tier: "simple" | "medium" | "complex";
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
    InitExistingProjectRequest: {
      architecture_paradigm: string;
      detected_dependencies: (string)[];
      human_anchor_justification: string;
      human_anchor_signature: string;
      repository_uri: string;
      spine_version?: string;
      workspace_id: string;
    };
    InitExistingProjectResponse: {
      catalog_item: components["schemas"]["CatalogItemResponse"];
      run: components["schemas"]["SystemBootstrapRunItem"];
      spine_baseline: components["schemas"]["WorkspaceSpineBaselineSchemaItem"];
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
    InitSkillRequest: {
      description: string;
      max_memory_mb?: number;
      required_sections?: (string)[];
      simulate_fs_escape_path?: string | null;
      simulate_memory_alloc_mb?: number;
      simulate_network_escape?: boolean;
      simulate_timeout_sleep_ms?: number;
      skill_key: string;
      skill_uri: string;
      test_payload?: Record<string, unknown>;
      timeout_ms?: number;
      title: string;
      version?: string;
      visibility_scope?: "SHARED_WORKSPACE" | "SHARED_TEAM";
      workspace_id: string;
    };
    InitSkillResponse: {
      catalog_item: components["schemas"]["CatalogItemResponse"];
      gate_evaluation: components["schemas"]["GateEvaluationSchemaItem"];
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
    JiraIssueUpdatedWebhookRequest: {
      issue_key: string;
      new_status: string;
      run_id: string;
      step_execution_id: string;
      webhook_event?: string;
      workspace_id: string;
    };
    JiraIssueUpdatedWebhookResponse: {
      issue_key: string;
      new_status: string;
      outbox_event_id: string | null;
      processing_ms: number;
      project_key: string;
      replay_triggered: boolean;
      run_id: string;
      sse_channel: string;
      step_execution_id: string;
      trace_id: string;
      webhook_event: string;
      workspace_id: string;
    };
    JiraJqlSearchRequest: {
      jql: string;
      project_alias: string;
      workspace_id: string;
    };
    JiraJqlSearchResponse: {
      issues: (Record<string, unknown>)[];
      project_alias: string;
      project_key: string;
      trace_id: string;
      workspace_id: string;
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
    LlmTierMappingResponse: {
      draining: boolean;
      effort: "default" | "fast" | "balanced" | "deep";
      fallback_order: number;
      id: string;
      inference_tier: "simple" | "medium" | "complex";
      is_active: boolean;
      max_cost_usd: number;
      max_tokens_budget: number;
      model_family: string;
      model_name: string;
      provider_slug: string;
      scope_id: string;
      scope_level: "GLOBAL" | "BU" | "TEAM" | "WORKSPACE";
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
    McpToolCallRequest: {
      arguments?: Record<string, unknown>;
      execution_identity?: string;
      ide_client?: string;
      tool_name: string;
      workspace_id: string;
    };
    McpToolCallResponse: {
      data: Record<string, unknown>;
      execution_identity: "passthrough";
      ide_client: string;
      status: "OK";
      tool_name: string;
      trace_id: string;
      workspace_id: string;
    };
    McpToolDescriptorSchema: {
      blocks_human_authored_sections: boolean;
      description: string;
      mode: "READ_ONLY" | "GOVERNED_DRAFT_WRITE";
      name: string;
      passthrough_required: boolean;
    };
    McpToolsListResponse: {
      tools: (components["schemas"]["McpToolDescriptorSchema"])[];
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
    OntologyAxiomRuleInputItem: {
      axiom_key: string;
      forbidden_term?: string;
      required_term?: string;
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
    OrgUnitSummaryResponse: {
      id: string;
      name: string;
      parent_id?: string | null;
      slug: string;
      unit_type: "ENTERPRISE" | "BU" | "TRIBE" | "TEAM" | "SUB_TEAM";
    };
    OrgUnitTreeItem: {
      id: string;
      name: string;
      parent_id?: string | null;
      slug: string;
      unit_type: "ENTERPRISE" | "BU" | "TRIBE" | "TEAM" | "SUB_TEAM";
    };
    OutboxReplayRequest: {
      actor_persona?: string;
      consumer_name?: string;
      dry_run?: boolean;
      event_ids?: (string)[];
      max_events?: number;
    };
    OutboxReplayResponse: {
      consumer_name: string;
      dry_run: boolean;
      event_ids: (string)[];
      replayed_count: number;
      scanned_count: number;
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
    PatchPlatformSettingRequest: {
      actor_persona?: string;
      category?: "iam" | "connectors" | "ai-models" | "packs" | "workflows" | "audit";
      key?: string;
      scope_id?: string;
      scope_level?: "GLOBAL" | "BU" | "TEAM" | "WORKSPACE";
      secret_input?: components["schemas"]["SecretInputPayload"] | null;
      value_jsonb?: Record<string, unknown>;
    };
    PatternDriftFindingSchemaItem: {
      forbidden_symbol: string;
      message: string;
      rule_id: string;
      severity: string;
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
      request_url: string;
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
    PlatformSettingResponse: {
      category: "iam" | "connectors" | "ai-models" | "packs" | "workflows" | "audit";
      etag: string;
      id: string;
      key: string;
      scope_id: string;
      scope_level: "GLOBAL" | "BU" | "TEAM" | "WORKSPACE";
      secret_status: components["schemas"]["SecretStatusResponse"];
      updated_at: string;
      updated_by: string;
      value_jsonb: Record<string, unknown>;
      version: number;
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
    ProgressiveLlmEndpointRequest: {
      endpoint_key: string;
      endpoint_uri: string;
      model_family: string;
      model_name: string;
      provider_slug: string;
    };
    PromptLayerBlockSchemaItem: {
      content_sha256: string;
      immutable: boolean;
      layer_id: "1_CONSTITUTIONAL_IMMUTABLE" | "2_ONTOLOGY_AND_AXIOMS_L1_L4" | "3_HUMAN_PROFILE_ADAPTATION" | "4_FEDERATED_CONTEXT_FANOUT" | "5_CONVERSATIONAL_INTENT_AND_COMPOSER";
      layer_order: number;
    };
    RagReciprocityResponse: {
      cited_chunk_id: string;
      cited_uri: string;
      control_query: string;
      document_id: string;
      passed: boolean;
      response_markdown: string;
      uri: string;
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
    ReleaseTaskClaimRequest: {
      force?: boolean;
    };
    ResourceDiscoveryResponse: {
      allowed_verbs: ("create" | "read" | "update" | "delete" | "execute" | "grant")[];
      can_request_access: boolean;
      locked: boolean;
      reason?: string | null;
      scope_path: string;
      secret_config_visible: boolean;
      title: string;
    };
    ResourceLeaseItemResponse: {
      acquired_at: string;
      expires_at: string;
      fencing_token: number;
      holder_parent_run_id?: string | null;
      holder_root_run_id: string;
      holder_run_id: string;
      holder_step_execution_id: string;
      id: string;
      resource_class: string;
      resource_uri: string;
    };
    RolePermissionGrantResponse: {
      conditions: Record<string, unknown>;
      created_at_iso: string;
      effect: "ALLOW" | "DENY";
      granted_by_user_id?: string | null;
      hidden_when_unauthorized: boolean;
      id: string;
      inheritance_block: boolean;
      scope_path: string;
      subject_id: string;
      subject_type: "USER" | "ROLE" | "SERVICE_PRINCIPAL";
      verb: "create" | "read" | "update" | "delete" | "execute" | "grant";
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
    RunMutationGuardCheckRequest: {
      action?: string;
    };
    RunMutationGuardCheckResponse: {
      access_mode: "CONTRIBUTOR_ACTION_REQUIRED" | "READ_ONLY_OBSERVER";
      allowed?: boolean;
      run_id: string;
      step_execution_id: string;
      trace_id: string;
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
    SecretInputPayload: {
      action?: "keep" | "set" | "clear";
      plaintext_value?: string | null;
    };
    SecretStatusResponse: {
      configured: boolean;
      fingerprint?: string | null;
      updated_at: string;
      updated_by: string;
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
    SseEventEnvelopeResponse: {
      channel: string;
      dispatch_latency_ms: number;
      event_id: string;
      event_name: string;
      payload?: Record<string, unknown>;
      published_at_iso: string;
      run_id: string;
      step_execution_id: string;
      workspace_id: string;
    };
    StageJiraActionRequest: {
      action_type: "create_issue" | "update_issue" | "add_comment" | "transition_issue";
      fields_payload?: Record<string, unknown>;
      issue_key?: string | null;
      project_alias: string;
      run_id: string;
      step_execution_id: string;
      summary: string;
      target_transition?: string | null;
      workspace_id: string;
    };
    StageJiraActionResponse: {
      draft_artifact_jsonb: Record<string, unknown>;
      staged_action: components["schemas"]["StagedJiraActionItemSchema"];
      trace_id: string;
    };
    StagedJiraActionItemSchema: {
      action_type: "create_issue" | "update_issue" | "add_comment" | "transition_issue";
      executed_issue_key?: string | null;
      fields_payload: Record<string, unknown>;
      idempotency_key: string;
      issue_key: string | null;
      project_alias: string;
      project_key: string;
      provenance_run_lock_sha256?: string | null;
      provenance_run_lock_uri?: string | null;
      replayed_from_cache?: boolean;
      run_id: string;
      staged_action_id: string;
      status: "STAGED" | "EXECUTED";
      step_execution_id: string;
      summary: string;
      target_transition: string | null;
      workspace_id: string;
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
    StepReplayRequest: {
      revised_section_payload?: Record<string, unknown> | null;
      sub_workflow_step_key?: string | null;
    };
    StepReplayResponse: {
      replay: components["schemas"]["StepReplayResultSchemaItem"];
      trace_id: string;
    };
    StepReplayResultSchemaItem: {
      new_active_snapshot_ids: (string)[];
      replayed_from_step_key: string;
      reused_upstream_snapshot_ids: (string)[];
      run_id: string;
      run_lock_sha256: string;
      sub_workflow_step_key?: string | null;
      superseded_snapshot_ids: (string)[];
      upstream_steps_reexecuted_count: number;
      upstream_tokens_consumed: number;
    };
    StudioDryRunRequest: {
      input_values?: Record<string, unknown>;
      preview_markdown_output?: string | null;
    };
    StudioDryRunResponse: {
      deterministic_structure_gate_passed: boolean;
      executed_steps: (string)[];
      external_writes_count: number;
      missing_markdown_sections: (string)[];
      revision_id: string;
      skipped_layers: (string)[];
      version: string;
      workflow_uri: string;
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
    SupervisedDatasourceItemResponse: {
      alias: string;
      execution_identity: string;
      freshness_ttl_days: number;
      id: string;
      role: string;
      scheme: string;
      tripartite_status: "ALIGNED" | "STALE_WARNING" | "INDEXING";
      uri: string;
      workspace_id: string;
      workspace_name: string;
    };
    SupervisedRunItemResponse: {
      access_mode: "CONTRIBUTOR_ACTION_REQUIRED" | "READ_ONLY_OBSERVER";
      blackboard_payload_masked?: boolean;
      blackboard_summary: string;
      budget_consumed_usd: number;
      claimed_by_display_name?: string | null;
      claimed_by_user_id?: string | null;
      current_step_id: string;
      current_step_key: string;
      execution_mode: "COACHING" | "FAST_PATH";
      run_id: string;
      status: "RUNNING" | "PAUSED_HUMAN_GATE" | "PAUSED_ARBITRATION" | "COMPLETED";
      title: string;
      workflow_key: string;
      workspace_id: string;
      workspace_name: string;
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
    TaskNotificationItemResponse: {
      can_force_unclaim?: boolean;
      claimed_at?: string | null;
      claimed_by_display_name?: string | null;
      claimed_by_user_id?: string | null;
      created_at: string;
      id: string;
      lock_expires_at?: string | null;
      notification_type: "HUMAN_GATE" | "HUMAN_ARBITRATION" | "HUMAN_ANCHOR" | "UPSTREAM_CHALLENGE" | "PERMISSION_ALERT" | "STALE_WARNING" | "AUTONOMOUS_ESCALATION" | "POST_HOC_AUDIT_SAMPLE";
      peer_opacity?: number;
      presence_state: "UNCLAIMED" | "CLAIMED_BY_ME" | "CLAIMED_BY_PEER";
      run_id: string;
      scope_kind: "PERSONAL" | "TEAM";
      status: "OPEN" | "CLAIMED" | "RESOLVED";
      step_execution_id: string;
      step_key: string;
      summary: string;
      target_team_id?: string | null;
      target_user_id?: string | null;
      title: string;
      workspace_id: string;
    };
    Tier2TddVerifyRequest: {
      buggy_files?: Record<string, string>;
      cas_readonly_dir?: string | null;
      max_memory_mb?: number;
      patched_files?: Record<string, string>;
      raise_on_failure?: boolean;
      run_id: string;
      step_key: string;
      test_files?: Record<string, string>;
      timeout_ms?: number;
      tools?: (string)[];
      workspace_id: string;
    };
    Tier2TddVerifyResponse: {
      container_cli_args: (string)[];
      duration_ms: number;
      green_tool_runs: (Record<string, unknown>)[];
      green_verified: boolean;
      passed: boolean;
      red_exit_code: number;
      red_reproduced: boolean;
      red_stdout: string;
      trace_id: string;
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
    UpdateWorkspaceLifecycleRequest: {
      lifecycle_phase: "RUN" | "BUILD" | "MIGRATION";
    };
    UpstreamChallengePreviewRequest: {
      challenge_reason: string;
      challenged_section_key?: string;
      target_profile_archetype?: "PM_BUSINESS" | "ARCHITECT" | "TECH_LEAD" | "DEVELOPER" | "SECOPS" | "EXECUTIVE";
      target_upstream_step_key: string;
    };
    UpstreamChallengePreviewResponse: {
      preview: components["schemas"]["UpstreamChallengePreviewSchemaItem"];
      trace_id: string;
    };
    UpstreamChallengePreviewSchemaItem: {
      challenge_reason: string;
      challenged_section_key: string;
      challenger_step_key: string;
      invalidated_artifact_sections: (string)[];
      invalidated_downstream_step_keys: (string)[];
      invalidated_ontology_axiom_keys: (string)[];
      preserved_upstream_step_keys: (string)[];
      run_id: string;
      target_profile_archetype: "PM_BUSINESS" | "ARCHITECT" | "TECH_LEAD" | "DEVELOPER" | "SECOPS" | "EXECUTIVE";
      target_upstream_step_key: string;
      translated_summary: string;
      upstream_tokens_saved: number;
    };
    UpstreamChallengeSchemaItem: {
      challenge_key: string;
      challenge_reason: string;
      challenged_section_key: string;
      challenger_step_key: string;
      created_by_user_id: string;
      id: string;
      invalidated_artifact_sections: (string)[];
      invalidated_downstream_step_keys: (string)[];
      invalidated_ontology_axiom_keys: (string)[];
      outbox_event_id: string;
      preserved_upstream_step_keys: (string)[];
      revised_artifact_version?: string | null;
      run_id: string;
      status: "OPEN" | "RESOLVED_REVISED" | "REPLAYED";
      target_profile_archetype: "PM_BUSINESS" | "ARCHITECT" | "TECH_LEAD" | "DEVELOPER" | "SECOPS" | "EXECUTIVE";
      target_upstream_step_key: string;
      translated_summary: string;
      workspace_id: string;
    };
    UpstreamChallengeSubmitRequest: {
      challenge_reason: string;
      challenged_section_key?: string;
      proposed_upstream_revision?: string | null;
      target_profile_archetype?: "PM_BUSINESS" | "ARCHITECT" | "TECH_LEAD" | "DEVELOPER" | "SECOPS" | "EXECUTIVE";
      target_upstream_step_key: string;
    };
    UpstreamChallengeSubmitResponse: {
      challenge: components["schemas"]["UpstreamChallengeSchemaItem"];
      preview: components["schemas"]["UpstreamChallengePreviewSchemaItem"];
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
    ValidateFencedWriteRequest: {
      fencing_token: number;
      payload?: Record<string, unknown>;
      resource_uri: string;
    };
    ValidateFencedWriteResponse: {
      fencing_token: number;
      payload?: Record<string, unknown>;
      resource_class: string;
      resource_uri: string;
      status: "COMMITTED_FENCED";
      trace_id: string;
    };
    WelcomeSetupFirstAdminRequest: {
      bootstrap_token?: string | null;
      display_name: string;
      email: string;
      orcia_env?: string;
      password: string;
    };
    WelcomeSetupFirstAdminResponse: {
      display_name: string;
      email: string;
      orcia_env: string;
      platform_role: "PLATFORM_ADMIN";
      sql_lock_statement: string;
      trace_id: string;
      user_id: string;
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
    WizardAdvanceStepRequest: {
      actor_persona?: string;
      secret_input?: components["schemas"]["SecretInputPayload"] | null;
      step_index?: number;
      step_payload?: Record<string, unknown>;
    };
    WizardSessionRequest: {
      actor_persona?: string;
      scope_id?: string;
      wizard_type?: "sdlc_tech_lead" | "ops_manager" | "secops_admin";
    };
    WizardSessionResponse: {
      completed_steps: (number)[];
      current_step_index: number;
      dbos_workflow_id: string;
      id: string;
      rag_reciprocity_verified: boolean;
      scope_id: string;
      state_jsonb: Record<string, unknown>;
      status: "IN_PROGRESS" | "COMPLETED" | "ABANDONED";
      total_steps: number;
      user_id: string;
      wizard_type: "sdlc_tech_lead" | "ops_manager" | "secops_admin";
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
    WorkspaceGovernanceItemResponse: {
      access_mode: "CONTRIBUTOR_ACTION_REQUIRED" | "READ_ONLY_OBSERVER";
      blackboard_payload_masked?: boolean;
      finops_cost_usd?: number | null;
      lifecycle_phase: "RUN" | "BUILD" | "MIGRATION";
      name: string;
      owner_org_unit_id: string;
      slug: string;
      suggested_workflows: (string)[];
      visibility_mode: "STANDARD" | "CONFIDENTIAL_RESTRICTED";
      workspace_id: string;
    };
    WorkspaceSpineBaselineSchemaItem: {
      allowed_dependencies: (string)[];
      content_sha256: string;
      human_anchor_signature: string;
      signed_by_user_id: string;
      spine_markdown: string;
      spine_version: string;
      status: "ADOPTED";
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
  "/api/v1/admin/outbox/replays": {
    post: {
      responses: {
        200: components["schemas"]["OutboxReplayResponse"];
      };
    };
  };
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
  "/api/v1/bootstrap/accostage-status": {
    get: {
      responses: {
        200: components["schemas"]["AccostageStatusResponse"];
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
  "/api/v1/bootstrap/init-existing-project": {
    post: {
      responses: {
        200: components["schemas"]["InitExistingProjectResponse"];
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
  "/api/v1/bootstrap/init-skill": {
    post: {
      responses: {
        200: components["schemas"]["InitSkillResponse"];
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
  "/api/v1/bootstrap/welcome-setup/first-admin": {
    post: {
      responses: {
        200: components["schemas"]["WelcomeSetupFirstAdminResponse"];
      };
    };
  };
  "/api/v1/bootstrap/welcome-setup/progressive-llm": {
    post: {
      responses: {
        200: components["schemas"]["AccostageStatusResponse"];
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
  "/api/v1/control-center/command-palette": {
    get: {
      responses: {
        200: components["schemas"]["CommandPaletteSearchResponse"];
      };
    };
  };
  "/api/v1/control-center/overview": {
    get: {
      responses: {
        200: components["schemas"]["ControlCenterOverviewResponse"];
      };
    };
  };
  "/api/v1/control-center/runs/{run_id}/steps/{step_id}/mutate-check": {
    post: {
      responses: {
        200: components["schemas"]["RunMutationGuardCheckResponse"];
      };
    };
  };
  "/api/v1/control-center/workspaces/{workspace_id}/lifecycle": {
    patch: {
      responses: {
        200: components["schemas"]["WorkspaceGovernanceItemResponse"];
      };
    };
  };
  "/api/v1/events/stream": {
    get: {
      responses: {
        200: unknown;
      };
    };
  };
  "/api/v1/gates/agentic/evaluate": {
    post: {
      responses: {
        200: components["schemas"]["AgenticGateEvaluateResponse"];
      };
    };
  };
  "/api/v1/gates/deterministic/evaluate": {
    post: {
      responses: {
        200: components["schemas"]["DeterministicGateEvaluateResponse"];
      };
    };
  };
  "/api/v1/gates/evaluations": {
    get: {
      responses: {
        200: components["schemas"]["GateEvaluationsListResponse"];
      };
    };
  };
  "/api/v1/gates/human/evaluate": {
    post: {
      responses: {
        200: components["schemas"]["HumanGateEvaluateResponse"];
      };
    };
  };
  "/api/v1/gates/human/{gate_evaluation_id}/chunks/{chunk_key}/decide": {
    post: {
      responses: {
        200: components["schemas"]["HumanGateChunkDecideResponse"];
      };
    };
  };
  "/api/v1/gates/human/{gate_evaluation_id}/finalize": {
    post: {
      responses: {
        200: components["schemas"]["HumanGateFinalizeResponse"];
      };
    };
  };
  "/api/v1/gates/human/{gate_evaluation_id}/inspect-hypotheses": {
    post: {
      responses: {
        200: components["schemas"]["HumanGateEvaluateResponse"];
      };
    };
  };
  "/api/v1/gates/sandbox/deployment-roles": {
    get: {
      responses: {
        200: components["schemas"]["DeploymentRolesListResponse"];
      };
    };
  };
  "/api/v1/gates/sandbox/tier2/tdd-verify": {
    post: {
      responses: {
        200: components["schemas"]["Tier2TddVerifyResponse"];
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
  "/api/v1/inbox/notifications": {
    get: {
      responses: {
        200: components["schemas"]["InboxNotificationListResponse"];
      };
    };
  };
  "/api/v1/jira/actions/commit": {
    post: {
      responses: {
        200: components["schemas"]["CommitStagedJiraActionResponse"];
      };
    };
  };
  "/api/v1/jira/actions/stage": {
    post: {
      responses: {
        200: components["schemas"]["StageJiraActionResponse"];
      };
    };
  };
  "/api/v1/jira/jql/search": {
    post: {
      responses: {
        200: components["schemas"]["JiraJqlSearchResponse"];
      };
    };
  };
  "/api/v1/mcp/call": {
    post: {
      responses: {
        200: components["schemas"]["McpToolCallResponse"];
      };
    };
  };
  "/api/v1/mcp/tools": {
    get: {
      responses: {
        200: components["schemas"]["McpToolsListResponse"];
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
  "/api/v1/orchestration/runs/{run_id}/steps/{step_key}/challenge": {
    post: {
      responses: {
        200: components["schemas"]["UpstreamChallengeSubmitResponse"];
      };
    };
  };
  "/api/v1/orchestration/runs/{run_id}/steps/{step_key}/challenge/preview": {
    post: {
      responses: {
        200: components["schemas"]["UpstreamChallengePreviewResponse"];
      };
    };
  };
  "/api/v1/orchestration/runs/{run_id}/steps/{step_key}/replay": {
    post: {
      responses: {
        200: components["schemas"]["StepReplayResponse"];
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
  "/api/v1/resource-leases/acquire": {
    post: {
      responses: {
        200: components["schemas"]["AcquireResourceLeasesResponse"];
      };
    };
  };
  "/api/v1/resource-leases/fenced-write": {
    post: {
      responses: {
        200: components["schemas"]["ValidateFencedWriteResponse"];
      };
    };
  };
  "/api/v1/runs/{run_id}/steps/{step_id}/claim": {
    post: {
      responses: {
        200: components["schemas"]["ClaimTaskResponse"];
      };
    };
  };
  "/api/v1/settings/ai-models/mappings": {
    get: {
      responses: {
        200: (components["schemas"]["LlmTierMappingResponse"])[];
      };
    };
  };
  "/api/v1/settings/ai-models/mappings/{mapping_id}": {
    delete: {
      responses: {
        200: Record<string, string>;
      };
    };
  };
  "/api/v1/settings/ai-models/route": {
    post: {
      responses: {
        200: components["schemas"]["CognitiveRoutingOutcomeResponse"];
      };
    };
  };
  "/api/v1/settings/connectors/documents/{document_id}/verify-reciprocity": {
    post: {
      responses: {
        200: components["schemas"]["RagReciprocityResponse"];
      };
    };
  };
  "/api/v1/settings/connectors/ingest": {
    post: {
      responses: {
        200: components["schemas"]["DocumentIngestionResponse"];
      };
    };
  };
  "/api/v1/settings/connectors/{connector_id}/test-connection": {
    post: {
      responses: {
        200: components["schemas"]["ConnectorTestConnectionResponse"];
      };
    };
  };
  "/api/v1/settings/entries": {
    get: {
      responses: {
        200: (components["schemas"]["PlatformSettingResponse"])[];
      };
    };
    patch: {
      responses: {
        200: components["schemas"]["PlatformSettingResponse"];
      };
    };
  };
  "/api/v1/settings/iam/evaluate": {
    post: {
      responses: {
        200: components["schemas"]["ResourceDiscoveryResponse"];
      };
    };
  };
  "/api/v1/settings/iam/grants": {
    post: {
      responses: {
        200: (components["schemas"]["RolePermissionGrantResponse"])[];
      };
    };
  };
  "/api/v1/studio/revisions/{revision_id}/dry-run": {
    post: {
      responses: {
        200: components["schemas"]["StudioDryRunResponse"];
      };
    };
  };
  "/api/v1/tasks/{task_id}/claim": {
    post: {
      responses: {
        200: components["schemas"]["ClaimTaskResponse"];
      };
    };
  };
  "/api/v1/tasks/{task_id}/release": {
    post: {
      responses: {
        200: components["schemas"]["ClaimTaskResponse"];
      };
    };
  };
  "/api/v1/webhooks/jira/issue-updated": {
    post: {
      responses: {
        200: components["schemas"]["JiraIssueUpdatedWebhookResponse"];
      };
    };
  };
  "/api/v1/wizards/demo-workspace": {
    post: {
      responses: {
        200: components["schemas"]["DemoWorkspaceProvisionResponse"];
      };
    };
  };
  "/api/v1/wizards/sessions": {
    post: {
      responses: {
        200: components["schemas"]["WizardSessionResponse"];
      };
    };
  };
  "/api/v1/wizards/sessions/{session_id}/steps": {
    post: {
      responses: {
        200: components["schemas"]["WizardSessionResponse"];
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

export type AccostageStatusResponse = components["schemas"]["AccostageStatusResponse"];
export type AcquireResourceLeasesRequest = components["schemas"]["AcquireResourceLeasesRequest"];
export type AcquireResourceLeasesResponse = components["schemas"]["AcquireResourceLeasesResponse"];
export type AgenticGateEvaluateRequest = components["schemas"]["AgenticGateEvaluateRequest"];
export type AgenticGateEvaluateResponse = components["schemas"]["AgenticGateEvaluateResponse"];
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
export type ChunkApprovalSchemaItem = components["schemas"]["ChunkApprovalSchemaItem"];
export type ClaimTaskRequest = components["schemas"]["ClaimTaskRequest"];
export type ClaimTaskResponse = components["schemas"]["ClaimTaskResponse"];
export type CognitiveRoutingOutcomeResponse = components["schemas"]["CognitiveRoutingOutcomeResponse"];
export type CommandPaletteEntryResponse = components["schemas"]["CommandPaletteEntryResponse"];
export type CommandPaletteSearchResponse = components["schemas"]["CommandPaletteSearchResponse"];
export type CommitStagedJiraActionRequest = components["schemas"]["CommitStagedJiraActionRequest"];
export type CommitStagedJiraActionResponse = components["schemas"]["CommitStagedJiraActionResponse"];
export type CompiledArtifactTemplateSchemaItem = components["schemas"]["CompiledArtifactTemplateSchemaItem"];
export type CompiledMarkdownChunkSchemaItem = components["schemas"]["CompiledMarkdownChunkSchemaItem"];
export type ConnectorTestConnectionResponse = components["schemas"]["ConnectorTestConnectionResponse"];
export type ControlCenterOverviewResponse = components["schemas"]["ControlCenterOverviewResponse"];
export type DbDdlIndexRequest = components["schemas"]["DbDdlIndexRequest"];
export type DeclarativeOverrideLayerResponse = components["schemas"]["DeclarativeOverrideLayerResponse"];
export type DelegateGrantRequest = components["schemas"]["DelegateGrantRequest"];
export type DemoWorkspaceProvisionResponse = components["schemas"]["DemoWorkspaceProvisionResponse"];
export type DeploymentRoleSchemaItem = components["schemas"]["DeploymentRoleSchemaItem"];
export type DeploymentRolesListResponse = components["schemas"]["DeploymentRolesListResponse"];
export type DeterministicGateEvaluateRequest = components["schemas"]["DeterministicGateEvaluateRequest"];
export type DeterministicGateEvaluateResponse = components["schemas"]["DeterministicGateEvaluateResponse"];
export type DocVsCodeAuditRequest = components["schemas"]["DocVsCodeAuditRequest"];
export type DocVsCodeAuditResponse = components["schemas"]["DocVsCodeAuditResponse"];
export type DocumentIngestionRequest = components["schemas"]["DocumentIngestionRequest"];
export type DocumentIngestionResponse = components["schemas"]["DocumentIngestionResponse"];
export type EffectiveWorkflowResolveRequest = components["schemas"]["EffectiveWorkflowResolveRequest"];
export type EffectiveWorkflowResolveResponse = components["schemas"]["EffectiveWorkflowResolveResponse"];
export type EvaluateResourceAccessRequest = components["schemas"]["EvaluateResourceAccessRequest"];
export type EvaluationLensItem = components["schemas"]["EvaluationLensItem"];
export type ExecuteTierRoutingRequest = components["schemas"]["ExecuteTierRoutingRequest"];
export type GateEvaluationSchemaItem = components["schemas"]["GateEvaluationSchemaItem"];
export type GateEvaluationsListResponse = components["schemas"]["GateEvaluationsListResponse"];
export type GuidanceStepItemResponse = components["schemas"]["GuidanceStepItemResponse"];
export type HealthResponse = components["schemas"]["HealthResponse"];
export type HumanAnchorSignRequest = components["schemas"]["HumanAnchorSignRequest"];
export type HumanAnchorSignResponse = components["schemas"]["HumanAnchorSignResponse"];
export type HumanAnchorSignatureSchemaItem = components["schemas"]["HumanAnchorSignatureSchemaItem"];
export type HumanArbitrationCreateRequest = components["schemas"]["HumanArbitrationCreateRequest"];
export type HumanArbitrationCreateResponse = components["schemas"]["HumanArbitrationCreateResponse"];
export type HumanArbitrationRequestSchemaItem = components["schemas"]["HumanArbitrationRequestSchemaItem"];
export type HumanArbitrationResolveRequest = components["schemas"]["HumanArbitrationResolveRequest"];
export type HumanArbitrationResolveResponse = components["schemas"]["HumanArbitrationResolveResponse"];
export type HumanGateChunkDecideRequest = components["schemas"]["HumanGateChunkDecideRequest"];
export type HumanGateChunkDecideResponse = components["schemas"]["HumanGateChunkDecideResponse"];
export type HumanGateEvaluateRequest = components["schemas"]["HumanGateEvaluateRequest"];
export type HumanGateEvaluateResponse = components["schemas"]["HumanGateEvaluateResponse"];
export type HumanGateEvaluationSchemaItem = components["schemas"]["HumanGateEvaluationSchemaItem"];
export type HumanGateFinalizeRequest = components["schemas"]["HumanGateFinalizeRequest"];
export type HumanGateFinalizeResponse = components["schemas"]["HumanGateFinalizeResponse"];
export type HumanProfileBadge = components["schemas"]["HumanProfileBadge"];
export type HybridRagHitSchemaItem = components["schemas"]["HybridRagHitSchemaItem"];
export type HybridRagSearchRequest = components["schemas"]["HybridRagSearchRequest"];
export type HybridRagSearchResponse = components["schemas"]["HybridRagSearchResponse"];
export type HydratedStepContextSchemaItem = components["schemas"]["HydratedStepContextSchemaItem"];
export type InboxNotificationListResponse = components["schemas"]["InboxNotificationListResponse"];
export type InferenceAttemptResponse = components["schemas"]["InferenceAttemptResponse"];
export type InitDatasourceRequest = components["schemas"]["InitDatasourceRequest"];
export type InitDatasourceResponse = components["schemas"]["InitDatasourceResponse"];
export type InitExistingProjectRequest = components["schemas"]["InitExistingProjectRequest"];
export type InitExistingProjectResponse = components["schemas"]["InitExistingProjectResponse"];
export type InitOrganizationRequest = components["schemas"]["InitOrganizationRequest"];
export type InitOrganizationResponse = components["schemas"]["InitOrganizationResponse"];
export type InitSkillRequest = components["schemas"]["InitSkillRequest"];
export type InitSkillResponse = components["schemas"]["InitSkillResponse"];
export type InitUserPassthroughSecretItem = components["schemas"]["InitUserPassthroughSecretItem"];
export type InitUserRequest = components["schemas"]["InitUserRequest"];
export type InitUserResponse = components["schemas"]["InitUserResponse"];
export type InitWorkspaceRequest = components["schemas"]["InitWorkspaceRequest"];
export type InitWorkspaceResponse = components["schemas"]["InitWorkspaceResponse"];
export type JiraIssueUpdatedWebhookRequest = components["schemas"]["JiraIssueUpdatedWebhookRequest"];
export type JiraIssueUpdatedWebhookResponse = components["schemas"]["JiraIssueUpdatedWebhookResponse"];
export type JiraJqlSearchRequest = components["schemas"]["JiraJqlSearchRequest"];
export type JiraJqlSearchResponse = components["schemas"]["JiraJqlSearchResponse"];
export type KbDocumentSchemaItem = components["schemas"]["KbDocumentSchemaItem"];
export type KbStaleAlertSchemaItem = components["schemas"]["KbStaleAlertSchemaItem"];
export type LlmModelEndpointItem = components["schemas"]["LlmModelEndpointItem"];
export type LlmTierMappingResponse = components["schemas"]["LlmTierMappingResponse"];
export type LocalLoginRequest = components["schemas"]["LocalLoginRequest"];
export type LogoutResponse = components["schemas"]["LogoutResponse"];
export type McpToolCallRequest = components["schemas"]["McpToolCallRequest"];
export type McpToolCallResponse = components["schemas"]["McpToolCallResponse"];
export type McpToolDescriptorSchema = components["schemas"]["McpToolDescriptorSchema"];
export type McpToolsListResponse = components["schemas"]["McpToolsListResponse"];
export type MemberInvitationInputItem = components["schemas"]["MemberInvitationInputItem"];
export type OidcLoginRequest = components["schemas"]["OidcLoginRequest"];
export type OntologyAndRagStateResponse = components["schemas"]["OntologyAndRagStateResponse"];
export type OntologyAxiomRuleInputItem = components["schemas"]["OntologyAxiomRuleInputItem"];
export type OntologyConceptSchemaItem = components["schemas"]["OntologyConceptSchemaItem"];
export type OntologyPromoteRequest = components["schemas"]["OntologyPromoteRequest"];
export type OntologyPromotionProposalSchemaItem = components["schemas"]["OntologyPromotionProposalSchemaItem"];
export type OntologyRelationSchemaItem = components["schemas"]["OntologyRelationSchemaItem"];
export type OntologyResolveRequest = components["schemas"]["OntologyResolveRequest"];
export type OntologyResolveResponse = components["schemas"]["OntologyResolveResponse"];
export type OntologyTermInputItem = components["schemas"]["OntologyTermInputItem"];
export type OntologyUpsertConceptRequest = components["schemas"]["OntologyUpsertConceptRequest"];
export type OrchestrationSetupStateResponse = components["schemas"]["OrchestrationSetupStateResponse"];
export type OrgUnitSummaryResponse = components["schemas"]["OrgUnitSummaryResponse"];
export type OrgUnitTreeItem = components["schemas"]["OrgUnitTreeItem"];
export type OutboxReplayRequest = components["schemas"]["OutboxReplayRequest"];
export type OutboxReplayResponse = components["schemas"]["OutboxReplayResponse"];
export type PassthroughSecretMetadataResponse = components["schemas"]["PassthroughSecretMetadataResponse"];
export type PassthroughSecretStoreRequest = components["schemas"]["PassthroughSecretStoreRequest"];
export type PatchPlatformSettingRequest = components["schemas"]["PatchPlatformSettingRequest"];
export type PatternDriftFindingSchemaItem = components["schemas"]["PatternDriftFindingSchemaItem"];
export type PermissionBrokerPolicyItem = components["schemas"]["PermissionBrokerPolicyItem"];
export type PermissionBrokerStateResponse = components["schemas"]["PermissionBrokerStateResponse"];
export type PermissionBrokerTicketItem = components["schemas"]["PermissionBrokerTicketItem"];
export type PermissionCheckRequest = components["schemas"]["PermissionCheckRequest"];
export type PermissionCheckResponse = components["schemas"]["PermissionCheckResponse"];
export type PermissionPolicyImportMarkdownRequest = components["schemas"]["PermissionPolicyImportMarkdownRequest"];
export type PermissionPolicyImportMarkdownResponse = components["schemas"]["PermissionPolicyImportMarkdownResponse"];
export type PermissionTicketActionRequest = components["schemas"]["PermissionTicketActionRequest"];
export type PermissionTicketActionResponse = components["schemas"]["PermissionTicketActionResponse"];
export type PlatformSettingResponse = components["schemas"]["PlatformSettingResponse"];
export type ProblemDetails = components["schemas"]["ProblemDetails"];
export type ProgressiveLlmEndpointRequest = components["schemas"]["ProgressiveLlmEndpointRequest"];
export type PromptLayerBlockSchemaItem = components["schemas"]["PromptLayerBlockSchemaItem"];
export type RagReciprocityResponse = components["schemas"]["RagReciprocityResponse"];
export type RecursiveRunLockManifestSchemaItem = components["schemas"]["RecursiveRunLockManifestSchemaItem"];
export type ReleaseTaskClaimRequest = components["schemas"]["ReleaseTaskClaimRequest"];
export type ResourceDiscoveryResponse = components["schemas"]["ResourceDiscoveryResponse"];
export type ResourceLeaseItemResponse = components["schemas"]["ResourceLeaseItemResponse"];
export type RolePermissionGrantResponse = components["schemas"]["RolePermissionGrantResponse"];
export type RunBlackboardStateResponse = components["schemas"]["RunBlackboardStateResponse"];
export type RunLockManifestItem = components["schemas"]["RunLockManifestItem"];
export type RunLockSourceTripletItem = components["schemas"]["RunLockSourceTripletItem"];
export type RunMutationGuardCheckRequest = components["schemas"]["RunMutationGuardCheckRequest"];
export type RunMutationGuardCheckResponse = components["schemas"]["RunMutationGuardCheckResponse"];
export type ScopeMutationCheckResponse = components["schemas"]["ScopeMutationCheckResponse"];
export type ScopeNode = components["schemas"]["ScopeNode"];
export type SecretInputPayload = components["schemas"]["SecretInputPayload"];
export type SecretStatusResponse = components["schemas"]["SecretStatusResponse"];
export type ShellModuleItem = components["schemas"]["ShellModuleItem"];
export type ShellNavigationResponse = components["schemas"]["ShellNavigationResponse"];
export type SseEventEnvelopeResponse = components["schemas"]["SseEventEnvelopeResponse"];
export type StageJiraActionRequest = components["schemas"]["StageJiraActionRequest"];
export type StageJiraActionResponse = components["schemas"]["StageJiraActionResponse"];
export type StagedJiraActionItemSchema = components["schemas"]["StagedJiraActionItemSchema"];
export type StepExecuteRequest = components["schemas"]["StepExecuteRequest"];
export type StepExecuteResponse = components["schemas"]["StepExecuteResponse"];
export type StepExecutionSchemaItem = components["schemas"]["StepExecutionSchemaItem"];
export type StepHumanResumeRequest = components["schemas"]["StepHumanResumeRequest"];
export type StepHydrateRequest = components["schemas"]["StepHydrateRequest"];
export type StepHydrateResponse = components["schemas"]["StepHydrateResponse"];
export type StepMemlogSchemaItem = components["schemas"]["StepMemlogSchemaItem"];
export type StepReplayRequest = components["schemas"]["StepReplayRequest"];
export type StepReplayResponse = components["schemas"]["StepReplayResponse"];
export type StepReplayResultSchemaItem = components["schemas"]["StepReplayResultSchemaItem"];
export type StudioDryRunRequest = components["schemas"]["StudioDryRunRequest"];
export type StudioDryRunResponse = components["schemas"]["StudioDryRunResponse"];
export type SubWorkflowLockSchemaItem = components["schemas"]["SubWorkflowLockSchemaItem"];
export type SupervisedDatasourceItemResponse = components["schemas"]["SupervisedDatasourceItemResponse"];
export type SupervisedRunItemResponse = components["schemas"]["SupervisedRunItemResponse"];
export type SystemBootstrapRunItem = components["schemas"]["SystemBootstrapRunItem"];
export type SystemBootstrapStateResponse = components["schemas"]["SystemBootstrapStateResponse"];
export type SystemBootstrapWorkflowItem = components["schemas"]["SystemBootstrapWorkflowItem"];
export type TaskNotificationItemResponse = components["schemas"]["TaskNotificationItemResponse"];
export type Tier2TddVerifyRequest = components["schemas"]["Tier2TddVerifyRequest"];
export type Tier2TddVerifyResponse = components["schemas"]["Tier2TddVerifyResponse"];
export type TripartiteTraceEdgeSchemaItem = components["schemas"]["TripartiteTraceEdgeSchemaItem"];
export type UpdateWorkspaceLifecycleRequest = components["schemas"]["UpdateWorkspaceLifecycleRequest"];
export type UpstreamChallengePreviewRequest = components["schemas"]["UpstreamChallengePreviewRequest"];
export type UpstreamChallengePreviewResponse = components["schemas"]["UpstreamChallengePreviewResponse"];
export type UpstreamChallengePreviewSchemaItem = components["schemas"]["UpstreamChallengePreviewSchemaItem"];
export type UpstreamChallengeSchemaItem = components["schemas"]["UpstreamChallengeSchemaItem"];
export type UpstreamChallengeSubmitRequest = components["schemas"]["UpstreamChallengeSubmitRequest"];
export type UpstreamChallengeSubmitResponse = components["schemas"]["UpstreamChallengeSubmitResponse"];
export type UserMeResponse = components["schemas"]["UserMeResponse"];
export type UserOnboardingStateItem = components["schemas"]["UserOnboardingStateItem"];
export type ValidateFencedWriteRequest = components["schemas"]["ValidateFencedWriteRequest"];
export type ValidateFencedWriteResponse = components["schemas"]["ValidateFencedWriteResponse"];
export type WelcomeSetupFirstAdminRequest = components["schemas"]["WelcomeSetupFirstAdminRequest"];
export type WelcomeSetupFirstAdminResponse = components["schemas"]["WelcomeSetupFirstAdminResponse"];
export type WhatIfSimulationRequest = components["schemas"]["WhatIfSimulationRequest"];
export type WhatIfSimulationResponse = components["schemas"]["WhatIfSimulationResponse"];
export type WizardAdvanceStepRequest = components["schemas"]["WizardAdvanceStepRequest"];
export type WizardSessionRequest = components["schemas"]["WizardSessionRequest"];
export type WizardSessionResponse = components["schemas"]["WizardSessionResponse"];
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
export type WorkspaceGovernanceItemResponse = components["schemas"]["WorkspaceGovernanceItemResponse"];
export type WorkspaceSpineBaselineSchemaItem = components["schemas"]["WorkspaceSpineBaselineSchemaItem"];
export type WorkspaceSummaryItem = components["schemas"]["WorkspaceSummaryItem"];
export type WorkspacesListResponse = components["schemas"]["WorkspacesListResponse"];
export type XyFlowEdgeSchemaItem = components["schemas"]["XyFlowEdgeSchemaItem"];
export type XyFlowNodeSchemaItem = components["schemas"]["XyFlowNodeSchemaItem"];
