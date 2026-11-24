import { DICTIONARIES, type SupportedWebLocale } from "../../i18n";
import type { WorkflowDefinitionV2Item } from "./processStudioV2Types";

interface WorkflowStructureSpec {
  readonly id: string;
  readonly slug: string;
  readonly pack_id: string;
  readonly vsm_step_num: string | null;
  readonly version: string;
  readonly status: "draft" | "published" | "archived";
  readonly orchestration_type: "non_deterministic" | "deterministic_dbos";
  readonly allowed_delegate_agents?: readonly string[];
  readonly execution_mode: "native_orcia" | "external_delegated";
  readonly external_completion_event: string | null;
  readonly agent_ref: string;
  readonly skills_refs: readonly string[];
  readonly knowledge_base_refs: readonly string[];
  readonly triggers: ReadonlyArray<{ readonly trigger_type: string; readonly condition_expression: string | null }>;
  readonly subSteps: ReadonlyArray<{
    readonly id: string;
    readonly instruction_prompt_or_ref: string;
    readonly mcp_tools_allowed: readonly string[];
    readonly write_preview_required: boolean;
    readonly requires_human_checkpoint: boolean;
  }>;
  readonly deterministicGates: ReadonlyArray<{
    readonly id: string;
    readonly runner: WorkflowDefinitionV2Item["controls"]["deterministic_gates"][number]["runner"];
    readonly config: Record<string, unknown>;
    readonly blocking: boolean;
    readonly max_self_heal_retries: number;
  }>;
  readonly probabilisticEvaluations: ReadonlyArray<{
    readonly id: string;
    readonly agent_ref: string;
    readonly blocking: boolean;
    readonly trigger_condition: string;
  }>;
}

const WORKFLOW_STRUCTURES: readonly WorkflowStructureSpec[] = [
  {
    id: "wf-01-qualification-prd",
    slug: "wf-01-qualification-prd",
    pack_id: "orcia-pack-sdlc",
    vsm_step_num: "01",
    version: "1.0.0",
    status: "published",
    orchestration_type: "deterministic_dbos",
    execution_mode: "native_orcia",
    external_completion_event: null,
    agent_ref: "pack://sdlc/agents/orchestrateur-produit.md",
    skills_refs: ["pack://sdlc/skills/qualification-besoin", "pack://sdlc/skills/redaction-prd-wsjf"],
    knowledge_base_refs: ["pack://sdlc/agents/crl-socle-generateur.md"],
    triggers: [{ trigger_type: "vsm_step_entry", condition_expression: "STATUT_PRECEDENT == VALIDE" }],
    subSteps: [
      { id: "qualification", instruction_prompt_or_ref: "pack://sdlc/agents/orchestrateurProduit#qualification", mcp_tools_allowed: ["mcp:atlassian-confluence (read)"], write_preview_required: false, requires_human_checkpoint: true },
      { id: "prd", instruction_prompt_or_ref: "pack://sdlc/agents/orchestrateurProduit#prd", mcp_tools_allowed: ["mcp:atlassian-confluence (read)"], write_preview_required: false, requires_human_checkpoint: true },
      { id: "jira", instruction_prompt_or_ref: "pack://sdlc/agents/orchestrateurProduit#jira", mcp_tools_allowed: ["mcp:atlassian-jira (write_preview)"], write_preview_required: true, requires_human_checkpoint: true },
    ],
    deterministicGates: [{ id: "det-02-1", runner: "markdown_contract_runner", config: { required_headings: ["# "], min_chars_per_section: 20 }, blocking: true, max_self_heal_retries: 3 }],
    probabilisticEvaluations: [{ id: "ndet-02-1", agent_ref: "pack://sdlc/gates/hunter-archi-contradicteur", blocking: false, trigger_condition: "after_deterministic_pass" }],
  },
  {
    id: "wf-03-etude-architecture",
    slug: "wf-03-etude-architecture",
    pack_id: "orcia-pack-sdlc",
    vsm_step_num: "03",
    version: "1.0.0",
    status: "published",
    orchestration_type: "deterministic_dbos",
    execution_mode: "native_orcia",
    external_completion_event: null,
    agent_ref: "pack://sdlc/agents/crl-etude-archi.md",
    skills_refs: ["pack://sdlc/skills/qualification-besoin", "pack://sdlc/skills/redaction-prd-wsjf"],
    knowledge_base_refs: ["pack://sdlc/agents/crl-socle-generateur.md"],
    triggers: [{ trigger_type: "vsm_step_entry", condition_expression: "STATUT_PRECEDENT == VALIDE" }],
    subSteps: [
      { id: "comprendre", instruction_prompt_or_ref: "pack://sdlc/agents/etudeArchi#comprendre", mcp_tools_allowed: ["mcp:atlassian-confluence (read)"], write_preview_required: false, requires_human_checkpoint: true },
      { id: "concevoir", instruction_prompt_or_ref: "pack://sdlc/agents/etudeArchi#concevoir", mcp_tools_allowed: ["mcp:atlassian-confluence (read)"], write_preview_required: false, requires_human_checkpoint: true },
      { id: "rediger", instruction_prompt_or_ref: "pack://sdlc/agents/etudeArchi#rediger", mcp_tools_allowed: ["mcp:atlassian-confluence (read)"], write_preview_required: false, requires_human_checkpoint: true },
      { id: "controler", instruction_prompt_or_ref: "pack://sdlc/agents/etudeArchi#controler", mcp_tools_allowed: ["mcp:atlassian-confluence (read)"], write_preview_required: false, requires_human_checkpoint: true },
    ],
    deterministicGates: [],
    probabilisticEvaluations: [
      { id: "ndet-03-1", agent_ref: "pack://sdlc/gates/hunter-archi-contradicteur", blocking: false, trigger_condition: "after_deterministic_pass" },
      { id: "ndet-03-2", agent_ref: "pack://sdlc/gates/hunter-archi-contradicteur", blocking: false, trigger_condition: "after_deterministic_pass" },
    ],
  },
  {
    id: "wf-06-decoupe-us",
    slug: "wf-06-decoupe-us",
    pack_id: "orcia-pack-sdlc",
    vsm_step_num: "06",
    version: "1.0.0",
    status: "published",
    orchestration_type: "deterministic_dbos",
    execution_mode: "native_orcia",
    external_completion_event: null,
    agent_ref: "pack://sdlc/agents/agent-us.md",
    skills_refs: ["pack://sdlc/skills/qualification-besoin", "pack://sdlc/skills/redaction-prd-wsjf"],
    knowledge_base_refs: ["pack://sdlc/agents/crl-socle-generateur.md"],
    triggers: [{ trigger_type: "vsm_step_entry", condition_expression: "STATUT_PRECEDENT == VALIDE" }],
    subSteps: [
      { id: "analyse", instruction_prompt_or_ref: "pack://sdlc/agents/agentUS#analyse", mcp_tools_allowed: ["mcp:atlassian-confluence (read)"], write_preview_required: false, requires_human_checkpoint: true },
      { id: "epic", instruction_prompt_or_ref: "pack://sdlc/agents/agentUS#epic", mcp_tools_allowed: ["mcp:atlassian-confluence (read)"], write_preview_required: false, requires_human_checkpoint: true },
      { id: "decoupe", instruction_prompt_or_ref: "pack://sdlc/agents/agentUS#decoupe", mcp_tools_allowed: ["mcp:atlassian-confluence (read)"], write_preview_required: false, requires_human_checkpoint: true },
      { id: "controle", instruction_prompt_or_ref: "pack://sdlc/agents/agentUS#controle", mcp_tools_allowed: ["mcp:atlassian-confluence (read)"], write_preview_required: false, requires_human_checkpoint: true },
      { id: "creation", instruction_prompt_or_ref: "pack://sdlc/agents/agentUS#creation", mcp_tools_allowed: ["mcp:atlassian-jira (write_preview)"], write_preview_required: true, requires_human_checkpoint: true },
    ],
    deterministicGates: [],
    probabilisticEvaluations: [{ id: "ndet-06-1", agent_ref: "pack://sdlc/gates/hunter-archi-contradicteur", blocking: false, trigger_condition: "after_deterministic_pass" }],
  },
  {
    id: "wf-08-dev-external-gate",
    slug: "wf-08-dev-external-gate",
    pack_id: "orcia-pack-sdlc",
    vsm_step_num: "08",
    version: "1.0.0",
    status: "published",
    orchestration_type: "deterministic_dbos",
    execution_mode: "external_delegated",
    external_completion_event: "git:pr_opened",
    agent_ref: "pack://sdlc/agents/crl-socle-generateur.md",
    skills_refs: ["pack://sdlc/skills/decoupe-us-invest"],
    knowledge_base_refs: ["confluence://mon-compte/socle-architecture"],
    triggers: [{ trigger_type: "vsm_step_entry", condition_expression: "STATUT_PRECEDENT == VALIDE" }],
    subSteps: [
      { id: "expose-mcp-context", instruction_prompt_or_ref: "Expose MCP context bundle for IDE assistant.", mcp_tools_allowed: ["mcp:git-provider (read)"], write_preview_required: false, requires_human_checkpoint: false },
      { id: "external-pr-gatekeeper", instruction_prompt_or_ref: "Verify PR diff alignment.", mcp_tools_allowed: ["mcp:git-provider (read)"], write_preview_required: false, requires_human_checkpoint: true },
    ],
    deterministicGates: [{ id: "det-08-pr-contract", runner: "markdown_contract_runner", config: { min_chars_per_section: 15, forbid_patterns: ["TODO"] }, blocking: true, max_self_heal_retries: 3 }],
    probabilisticEvaluations: [{ id: "ndet-08-pr-hunter", agent_ref: "pack://sdlc/gates/hunter-archi-contradicteur", blocking: false, trigger_condition: "after_deterministic_pass" }],
  },
  {
    id: "wf-generate-orcia-documentation",
    slug: "wf-generate-orcia-documentation",
    pack_id: "orcia-pack-docs",
    vsm_step_num: null,
    version: "2.0.0",
    status: "published",
    orchestration_type: "non_deterministic",
    allowed_delegate_agents: ["redacteur-documentation-orcia"],
    execution_mode: "native_orcia",
    external_completion_event: null,
    agent_ref: "pack://orcia-docs/agents/redacteur-documentation-orcia.md",
    skills_refs: ["pack://orcia-docs/skills/redaction-aide-bilingue"],
    knowledge_base_refs: ["confluence://mon-compte/socle-architecture"],
    triggers: [{ trigger_type: "vsm_step_entry", condition_expression: "STATUT_PRECEDENT == VALIDE" }],
    subSteps: [{ id: "draft-bilingual-help", instruction_prompt_or_ref: "pack://orcia-docs/agents/redacteur-documentation-orcia.md", mcp_tools_allowed: [], write_preview_required: false, requires_human_checkpoint: true }],
    deterministicGates: [{ id: "det-docs-markdown", runner: "markdown_contract_runner", config: { min_chars_per_section: 20, forbid_patterns: ["TODO", "TBD"] }, blocking: true, max_self_heal_retries: 3 }],
    probabilisticEvaluations: [],
  },
];

export function getInitialWorkflowsV2(locale: SupportedWebLocale = "fr"): WorkflowDefinitionV2Item[] {
  const dict = DICTIONARIES[locale].processCatalogWorkflows.workflows;
  return WORKFLOW_STRUCTURES.map((wf) => {
    const copy = dict[wf.id]!;
    return {
      id: wf.id,
      slug: wf.slug,
      title: copy.title,
      pack_id: wf.pack_id,
      vsm_step_num: wf.vsm_step_num,
      version: wf.version,
      status: wf.status,
      orchestration_type: wf.orchestration_type,
      ...(copy.reflexive_objective !== undefined ? { reflexive_objective: copy.reflexive_objective } : {}),
      ...(wf.allowed_delegate_agents ? { allowed_delegate_agents: [...wf.allowed_delegate_agents] } : {}),
      execution_mode: wf.execution_mode,
      external_tool_label: copy.external_tool_label ?? null,
      external_completion_event: wf.external_completion_event,
      agent_ref: wf.agent_ref,
      skills_refs: [...wf.skills_refs],
      knowledge_base_refs: [...wf.knowledge_base_refs],
      triggers: wf.triggers.map((t, idx) => ({
        trigger_type: t.trigger_type,
        source_label: copy.triggerSourceLabels[idx] ?? "",
        condition_expression: t.condition_expression,
      })),
      contract: {
        inputs: [...copy.contractInputs],
        outputs: [...copy.contractOutputs],
        exit_criteria: [...copy.contractExitCriteria],
        expected_format: "markdown",
      },
      sub_steps: wf.subSteps.map((sub) => {
        const subCopy = copy.subSteps[sub.id]!;
        return {
          id: sub.id,
          name: subCopy.name,
          short_label: subCopy.short_label,
          trigger_condition_label: subCopy.trigger_condition_label,
          role_description: subCopy.role_description,
          instruction_prompt_or_ref: subCopy.instruction_prompt_or_ref ?? sub.instruction_prompt_or_ref,
          output_description: subCopy.output_description,
          mcp_tools_allowed: [...sub.mcp_tools_allowed],
          write_preview_required: sub.write_preview_required,
          requires_human_checkpoint: sub.requires_human_checkpoint,
          checkpoint_question: subCopy.checkpoint_question,
          enabled: true,
        };
      }),
      controls: {
        deterministic_gates: wf.deterministicGates.map((dg) => {
          const dgCopy = copy.deterministicGates[dg.id];
          return {
            id: dg.id,
            name: dgCopy?.name ?? dg.id,
            runner: dg.runner,
            config: dgCopy?.required_headings
              ? { ...dg.config, required_headings: [...dgCopy.required_headings] }
              : { ...dg.config },
            blocking: dg.blocking,
            max_self_heal_retries: dg.max_self_heal_retries,
          };
        }),
        probabilistic_evaluations: wf.probabilisticEvaluations.map((pg) => {
          const pgCopy = copy.probabilisticEvaluations[pg.id];
          return {
            id: pg.id,
            name: pgCopy?.name ?? pg.id,
            agent_ref: pg.agent_ref,
            rubric_ref: pgCopy?.rubric_ref ?? "",
            blocking: pg.blocking,
            trigger_condition: pg.trigger_condition,
          };
        }),
      },
      guardrails: [...copy.guardrails],
    };
  });
}
