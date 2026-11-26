export interface ConnectorHealthItem {
  connector_type: string;
  required_scopes: string[];
  used_for: string;
  health: {
    connector_type: string;
    ok: boolean;
    latency_ms: number;
    error_message?: string | null;
  };
}

export interface DeclarativePackItem {
  id: string;
  slug: string;
  name: string;
  version: string;
  description: string;
  rbac_namespace: string;
  bundle_sha256: string;
  agents_count: number;
  skills_count: number;
  gates_count: number;
  vsm_count: number;
  workflows_count: number;
  agents_slugs: string[];
  skills_slugs: string[];
  gates_slugs: string[];
  connector_health: ConnectorHealthItem[];
}

export interface DeterministicSubStepItem {
  id: string;
  name: string;
  short_label: string;
  trigger_condition_label: string;
  role_description: string;
  instruction_prompt_or_ref: string;
  output_description: string;
  mcp_tools_allowed: string[];
  write_preview_required: boolean;
  requires_human_checkpoint: boolean;
  human_authored_required?: boolean;
  checkpoint_question?: string | null;
  enabled: boolean;
}

export interface WorkflowDefinitionV2Item {
  id: string;
  slug: string;
  title: string;
  pack_id: string;
  vsm_step_num?: string | null;
  version: string;
  status: "draft" | "published" | "archived";
  orchestration_type?: "non_deterministic" | "deterministic_dbos";
  reflexive_objective?: string | null;
  allowed_delegate_agents?: string[];
  effort?: "default" | "low" | "medium" | "high";
  execution_mode: "native_orcia" | "external_delegated";
  human_authored_required?: boolean;
  external_tool_label?: string | null;
  external_completion_event?: string | null;
  agent_ref: string;
  skills_refs: string[];
  knowledge_base_refs: string[];
  triggers: Array<{
    trigger_type: string;
    source_label: string;
    condition_expression?: string | null;
  }>;
  contract: {
    inputs: string[];
    outputs: string[];
    exit_criteria: string[];
    expected_format?: string;
  };
  sub_steps: DeterministicSubStepItem[];
  controls: {
    deterministic_gates: Array<{
      id: string;
      name: string;
      runner:
        | "markdown_contract_runner"
        | "json_schema_runner"
        | "cli_sandbox_runner"
        | "catalog_invariant_runner";
      config: Record<string, unknown>;
      blocking: boolean;
      max_self_heal_retries: number;
    }>;
    probabilistic_evaluations: Array<{
      id: string;
      name: string;
      agent_ref: string;
      rubric_ref: string;
      blocking: boolean;
      trigger_condition: string;
    }>;
  };
  guardrails: string[];
}
