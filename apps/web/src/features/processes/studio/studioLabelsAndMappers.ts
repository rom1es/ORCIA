import { createOrciaApiClient, type ApiWorkflowDefinitionV2 } from "@orcia/api-client";
import {
  INITIAL_WORKFLOWS_V2,
  type DeterministicSubStepItem,
  type WorkflowDefinitionV2Item,
} from "../processStudioV2Data";

export {
  AVAILABLE_DELEGATE_AGENTS,
  HUMAN_KB_LABELS,
  HUMAN_SKILL_LABELS,
  HUMAN_TOOL_LABELS,
  type DelegateAgentOption,
} from "./studioCatalogLabels";

export function createProcessesApiClient(locale: "fr" | "en") {
  return createOrciaApiClient({ baseUrl: "", locale });
}

export function ensureDraftOnEdit(base: WorkflowDefinitionV2Item): WorkflowDefinitionV2Item {
  if (base.status === "published") {
    const cleanVer = base.version.replace(/-draft$/, "");
    return {
      ...base,
      status: "draft",
      version: `${cleanVer}-draft`,
    };
  }
  return base;
}

export function buildNextPublishedWorkflow(base: WorkflowDefinitionV2Item): WorkflowDefinitionV2Item {
  const cleanVer = base.version.replace(/-draft$/, "");
  const parts = cleanVer.split(".").map((n) => Number.parseInt(n, 10) || 0);
  const nextVer = `${parts[0] ?? 1}.${parts[1] ?? 0}.${(parts[2] ?? 0) + 1}`;
  return { ...base, status: "published", version: nextVer };
}

export function attachSkillToWorkflow(
  workflow: WorkflowDefinitionV2Item,
  skillUri: string,
): WorkflowDefinitionV2Item | null {
  if (workflow.skills_refs.includes(skillUri)) return null;
  const base = ensureDraftOnEdit(workflow);
  return { ...base, skills_refs: [...base.skills_refs, skillUri] };
}

export function attachMcpToolToWorkflow(
  workflow: WorkflowDefinitionV2Item,
  toolPerm: string,
): WorkflowDefinitionV2Item {
  const base = ensureDraftOnEdit(workflow);
  const nextSubs = base.sub_steps.map((s, idx) =>
    idx === 0 && !s.mcp_tools_allowed.includes(toolPerm)
      ? { ...s, mcp_tools_allowed: [...s.mcp_tools_allowed, toolPerm] }
      : s,
  );
  return { ...base, sub_steps: nextSubs };
}

export function attachDeterministicGateToWorkflow(
  workflow: WorkflowDefinitionV2Item,
  gate: {
    id: string;
    name: string;
    runner: WorkflowDefinitionV2Item["controls"]["deterministic_gates"][number]["runner"];
  },
): WorkflowDefinitionV2Item | null {
  if (workflow.controls.deterministic_gates.some((g) => g.id === gate.id)) {
    return null;
  }
  const base = ensureDraftOnEdit(workflow);
  return {
    ...base,
    controls: {
      ...base.controls,
      deterministic_gates: [
        ...base.controls.deterministic_gates,
        {
          id: gate.id,
          name: gate.name,
          runner: gate.runner,
          config: { required_headings: ["# "] },
          blocking: true,
          max_self_heal_retries: 3,
        },
      ],
    },
  };
}

function parseContractInputString(raw: string, index: number): { name: string; label: string } {
  const match = /^([a-zA-Z_][a-zA-Z0-9_]*)\s*\((.+)\)$/.exec(raw.trim());
  if (match) {
    return { name: match[1]!, label: match[2]! };
  }
  const cleanName = raw
    .trim()
    .replace(/[^a-zA-Z0-9_]+/g, "_")
    .replace(/^[^a-zA-Z_]+/, "");
  return {
    name: cleanName || `input_${index + 1}`,
    label: raw.trim() || `Paramètre ${index + 1}`,
  };
}

export function mapUiItemToApiWorkflowV2(uiWf: WorkflowDefinitionV2Item): ApiWorkflowDefinitionV2 {
  return {
    id: uiWf.id,
    slug: uiWf.slug,
    title: uiWf.title,
    version: uiWf.version,
    status: uiWf.status,
    pack_id: uiWf.pack_id,
    linked_vsm_step_nums: uiWf.vsm_step_num ? [uiWf.vsm_step_num] : [],
    orchestration_type: uiWf.orchestration_type ?? "deterministic_dbos",
    reflexive_objective: uiWf.reflexive_objective ?? null,
    allowed_delegate_agents: uiWf.allowed_delegate_agents ?? [],
    execution_mode: uiWf.execution_mode,
    external_tool_label: uiWf.external_tool_label ?? null,
    external_completion_event: uiWf.external_completion_event ?? null,
    model_override: "team_default",
    effort: uiWf.effort ?? "default",
    global_system_prompt_or_ref: uiWf.agent_ref,
    guardrails: uiWf.guardrails,
    knowledge_feedback_target_agent: uiWf.knowledge_base_refs[0] ?? null,
    contract: {
      parameters: uiWf.contract.inputs.map((inp, idx) => {
        const parsed = parseContractInputString(inp, idx);
        return {
          name: parsed.name,
          label: parsed.label,
          scalar_type: "string",
          catalog_entity_uri_pattern: null,
          default_value: null,
          required: true,
        };
      }),
      required_markdown_sections: uiWf.contract.outputs,
      output_schema_uri: null,
    },
    sub_steps: uiWf.sub_steps.map((sub) => ({
      id: sub.id,
      name: sub.name,
      short_label: sub.short_label,
      enabled: sub.enabled,
      step_executor_type: "agent_executor",
      trigger_condition_label: sub.trigger_condition_label,
      role_description: sub.role_description,
      instruction_prompt_or_ref: sub.instruction_prompt_or_ref,
      toolbox_mcp_permissions: sub.mcp_tools_allowed.map((perm) => {
        const match = /^(.+?)\s*\((.+)\)$/.exec(perm);
        return match
          ? { tool_id: match[1]!.trim(), mode: match[2]!.trim() }
          : { tool_id: perm, mode: "read" };
      }),
      skill_refs: [...uiWf.skills_refs],
      output_description: sub.output_description,
      requires_human_checkpoint: sub.requires_human_checkpoint,
      checkpoint_label: sub.checkpoint_question ?? sub.short_label,
      approver_rbac_role: "workspace:member",
      write_preview_required: sub.write_preview_required,
    })),
    controls: {
      delegated_to_step_num: null,
      delegation_note: null,
      strategy: "fail_fast",
      sandbox_dry_run: true,
      deterministic: uiWf.controls.deterministic_gates.map((dg) => ({
        id: dg.id,
        name: dg.name,
        short_label: dg.name.slice(0, 40),
        status: "place",
        runner_plugin_id: dg.runner,
        verifies_description: dg.name,
        on_ko_behavior: dg.blocking ? "blocking" : "advisory",
        max_self_heal_retries: dg.max_self_heal_retries,
        config: dg.config,
      })),
      non_deterministic: uiWf.controls.probabilistic_evaluations.map((pg) => ({
        id: pg.id,
        name: pg.name,
        short_label: pg.name.slice(0, 40),
        status: "place",
        evaluator_type: "adversarial_agent",
        agent_ref: pg.agent_ref,
        model_override: null,
        risk_threshold: 0.7,
        verifies_description: pg.rubric_ref,
        hypothesis_note: null,
        on_ko_behavior: pg.blocking ? "blocking" : "advisory",
      })),
    },
  };
}

const VALID_RUNNERS = new Set([
  "markdown_contract_runner",
  "json_schema_runner",
  "cli_sandbox_runner",
  "catalog_invariant_runner",
]);

export function mapApiWorkflowV2ToUiItem(
  apiWf: ApiWorkflowDefinitionV2,
  fallbackUi?: WorkflowDefinitionV2Item,
): WorkflowDefinitionV2Item {
  const matchedSeed =
    fallbackUi ??
    INITIAL_WORKFLOWS_V2.find((w) => w.id === apiWf.id || w.slug === apiWf.slug);

  const normalizedStatus: "draft" | "published" | "archived" =
    apiWf.status === "published"
      ? "published"
      : apiWf.status === "archived"
        ? "archived"
        : "draft";

  const subSteps: DeterministicSubStepItem[] = (apiWf.sub_steps ?? []).map((sub) => {
    const perms = (sub.toolbox_mcp_permissions ?? []).map((entry) => {
      const toolId = entry.tool_id ?? entry.connector ?? entry.tool ?? "";
      const mode = entry.mode ?? entry.scope ?? "";
      return mode ? `${toolId} (${mode})` : toolId;
    });
    return {
      id: sub.id,
      name: sub.name,
      short_label: sub.short_label,
      trigger_condition_label: sub.trigger_condition_label,
      role_description: sub.role_description,
      instruction_prompt_or_ref: sub.instruction_prompt_or_ref,
      output_description: sub.output_description,
      mcp_tools_allowed: perms.filter(Boolean),
      write_preview_required: Boolean(sub.write_preview_required),
      requires_human_checkpoint: sub.requires_human_checkpoint ?? true,
      checkpoint_question: sub.checkpoint_label ?? null,
      enabled: sub.enabled ?? true,
    };
  });

  const skillSet = new Set<string>(matchedSeed?.skills_refs ?? []);
  for (const sub of apiWf.sub_steps ?? []) {
    for (const sk of sub.skill_refs ?? []) {
      skillSet.add(sk);
    }
  }

  const kbRefs = apiWf.knowledge_feedback_target_agent
    ? Array.from(
        new Set([
          apiWf.knowledge_feedback_target_agent,
          ...(matchedSeed?.knowledge_base_refs ?? []),
        ]),
      )
    : (matchedSeed?.knowledge_base_refs ?? []);

  return {
    id: apiWf.id,
    slug: apiWf.slug,
    title: apiWf.title,
    pack_id: apiWf.pack_id,
    vsm_step_num: apiWf.linked_vsm_step_nums?.[0] ?? matchedSeed?.vsm_step_num ?? null,
    version: apiWf.version ?? "1.0.0",
    status: normalizedStatus,
    orchestration_type: apiWf.orchestration_type ?? "deterministic_dbos",
    reflexive_objective: apiWf.reflexive_objective ?? null,
    allowed_delegate_agents: [...(apiWf.allowed_delegate_agents ?? [])],
    effort: apiWf.effort ?? "default",
    execution_mode: apiWf.execution_mode ?? "native_orcia",
    external_tool_label: apiWf.external_tool_label ?? null,
    external_completion_event: apiWf.external_completion_event ?? null,
    agent_ref:
      apiWf.global_system_prompt_or_ref ??
      matchedSeed?.agent_ref ??
      "pack://sdlc/agents/orchestrateur-produit.md",
    skills_refs: Array.from(skillSet),
    knowledge_base_refs: kbRefs,
    triggers: matchedSeed?.triggers ?? [
      {
        trigger_type: "manual_or_event",
        source_label: "Déclenchement métier",
        condition_expression: null,
      },
    ],
    contract: {
      inputs:
        (apiWf.contract?.parameters ?? []).length > 0
          ? (apiWf.contract?.parameters ?? []).map((p) => `${p.name} (${p.label})`)
          : (matchedSeed?.contract.inputs ?? []),
      outputs:
        (apiWf.contract?.required_markdown_sections ?? []).length > 0
          ? [...(apiWf.contract?.required_markdown_sections ?? [])]
          : (matchedSeed?.contract.outputs ?? []),
      exit_criteria: matchedSeed?.contract.exit_criteria ?? [
        "Contrôles de complétude validés",
        "Approbation du responsable",
      ],
      expected_format: "markdown",
    },
    sub_steps: subSteps.length > 0 ? subSteps : (matchedSeed?.sub_steps ?? []),
    controls: {
      deterministic_gates: (apiWf.controls?.deterministic ?? []).map((dg) => ({
        id: dg.id,
        name: dg.name,
        runner: (VALID_RUNNERS.has(dg.runner_plugin_id)
          ? dg.runner_plugin_id
          : "markdown_contract_runner") as WorkflowDefinitionV2Item["controls"]["deterministic_gates"][number]["runner"],
        config: dg.config ?? {},
        blocking: dg.on_ko_behavior !== "advisory",
        max_self_heal_retries: dg.max_self_heal_retries ?? 3,
      })),
      probabilistic_evaluations: (apiWf.controls?.non_deterministic ?? []).map((nd) => ({
        id: nd.id,
        name: nd.name,
        agent_ref: nd.agent_ref,
        rubric_ref: nd.verifies_description,
        blocking: nd.on_ko_behavior === "blocking",
        trigger_condition: "after_deterministic_pass",
      })),
    },
    guardrails: apiWf.guardrails ?? matchedSeed?.guardrails ?? [],
  };
}
