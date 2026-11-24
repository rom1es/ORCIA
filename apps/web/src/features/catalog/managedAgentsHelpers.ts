import type { createOrciaApiClient } from "@orcia/api-client";
import type {
  AgentSixBlocksDraftState,
  CreateAgentSixBlocksInput,
  UiAgentDialogueMechanism,
  UiAgentHumanPartnerRole,
  UiAgentLlmModelTier,
  UiAgentOutputContractFormat,
  UiAgentPosture,
  UiAgentSkillVisibilityScope,
  UiAgentThinkingLevel,
  UiManagedAgentItem,
  UiManagedSkillItem,
} from "@orcia/ui";
import type { FeatureAdminCatalogSettingsDictionary } from "../../i18n/locales/feature_admin_catalog_settings_labels";
import { slugifyIdentifier } from "./packAgentsCatalog";

type ListCatalogResponse = Awaited<
  ReturnType<ReturnType<typeof createOrciaApiClient>["listAgentsAndSkills"]>
>;
type ApiSkillDto = NonNullable<ListCatalogResponse["skills"]>[number];
type ApiAgentDto = NonNullable<ListCatalogResponse["agents"]>[number];

export type CatalogManagedLabels = FeatureAdminCatalogSettingsDictionary["catalog"];

export const DEFAULT_MCP_TOOL_PERMISSIONS: Readonly<Record<string, string>> = {
  search_tool: "READ_ONLY",
  confluence: "WRITE_PREVIEW",
  jira: "WRITE_PREVIEW",
  git: "READ_ONLY",
};

export const DEFAULT_AGENT_GUARDRAILS: readonly string[] = [
  "citations_obligatoires",
  "aucun_fait_invente",
  "isolation_prompt_injection",
  "filtrage_dcp_pii",
];

export const DEFAULT_INVOCATION_MODES: readonly string[] = ["generer", "corrections", "section"];
export const DEFAULT_RAG_SOURCES: readonly string[] = ["all_workspace_sources"];
export const DEFAULT_ONTOLOGY_VIEWS: readonly string[] = ["glossary", "apis_adr", "prd_regles_metier"];

export function mapSkillDtoToUi(s: ApiSkillDto, defaultFormat: string): UiManagedSkillItem {
  return {
    skillId: s.skill_id,
    slug: s.slug,
    commandHandle: s.command_handle,
    name: s.name,
    objective: s.objective,
    inputParameters: s.input_parameters ?? [],
    instructions: s.instructions,
    expectedOutputFormat: s.expected_output_format ?? defaultFormat,
    lastExecutionOutput: null,
    visibilityScope: (s.visibility_scope ?? "TEAM") as UiAgentSkillVisibilityScope,
    sourcePackKey: s.source_pack_key ?? null,
  };
}

export function mapAgentDtoToUi(a: ApiAgentDto): UiManagedAgentItem {
  return {
    agentId: a.agent_id,
    slug: a.slug,
    handle: a.handle,
    name: a.name,
    roleMission: a.role_mission,
    instructions: a.instructions,
    thinkingLevel: (a.thinking_level ?? "medium") as UiAgentThinkingLevel,
    skillIds: a.skill_ids ?? [],
    lastExecutionOutput: null,
    visibilityScope: (a.visibility_scope ?? "TEAM") as UiAgentSkillVisibilityScope,
    sourcePackKey: a.source_pack_key ?? null,
    enabledOnWorkspace: a.enabled_in_workspace ?? true,
    mcpExposed: a.mcp_exposed ?? false,
    posture: (a.posture ?? "PRODUCER") as UiAgentPosture,
    humanPartnerRole: (a.human_partner_role ?? "PO_PM") as UiAgentHumanPartnerRole,
    llmModelTier: (a.llm_model_tier ?? "team_default") as UiAgentLlmModelTier,
    temperature: a.temperature ?? 0.2,
    maxTokens: a.max_tokens ?? 4096,
    promptRef: a.prompt_ref ?? null,
    invocationModes: a.invocation_modes ?? [...DEFAULT_INVOCATION_MODES],
    dialogueMechanism: (a.dialogue_mechanism ?? "questionnaire_prealable") as UiAgentDialogueMechanism,
    allowedRagSources: a.allowed_rag_sources ?? [...DEFAULT_RAG_SOURCES],
    ontologyViews: a.ontology_views ?? [...DEFAULT_ONTOLOGY_VIEWS],
    mcpToolPermissions: a.mcp_tool_permissions ?? { ...DEFAULT_MCP_TOOL_PERMISSIONS },
    guardrails: a.guardrails ?? [...DEFAULT_AGENT_GUARDRAILS],
    outputContractFormat: (a.output_contract_format ?? "markdown_structure") as UiAgentOutputContractFormat,
    writePreviewRequired: a.write_preview_required ?? true,
    testBenchValidated: a.test_bench_validated ?? false,
  };
}

export function buildOptimisticAgent(draft: CreateAgentSixBlocksInput): UiManagedAgentItem {
  const slug = slugifyIdentifier(draft.name, "agent");
  const agentId = slug.startsWith("agent-") ? slug : `agent-${slug}`;
  const handleSlug = slug.startsWith("agent-") ? slug.slice(6) || slug : slug;
  return {
    agentId,
    slug: handleSlug,
    handle: `@${handleSlug}`,
    name: draft.name.trim(),
    roleMission: draft.roleMission.trim(),
    instructions: draft.instructions.trim(),
    thinkingLevel: draft.thinkingLevel,
    skillIds: [...draft.skillIds],
    lastExecutionOutput: null,
    visibilityScope: draft.visibilityScope ?? "TEAM",
    enabledOnWorkspace: true,
    mcpExposed: false,
    posture: draft.posture ?? "PRODUCER",
    humanPartnerRole: draft.humanPartnerRole ?? "PO_PM",
    llmModelTier: draft.llmModelTier ?? "team_default",
    temperature: draft.temperature ?? 0.2,
    maxTokens: draft.maxTokens ?? 4096,
    promptRef: draft.promptRef ?? null,
    invocationModes: draft.invocationModes ?? [...DEFAULT_INVOCATION_MODES],
    dialogueMechanism: draft.dialogueMechanism ?? "questionnaire_prealable",
    allowedRagSources: draft.allowedRagSources ?? [...DEFAULT_RAG_SOURCES],
    ontologyViews: draft.ontologyViews ?? [...DEFAULT_ONTOLOGY_VIEWS],
    mcpToolPermissions: draft.mcpToolPermissions ?? { ...DEFAULT_MCP_TOOL_PERMISSIONS },
    guardrails: draft.guardrails ?? [...DEFAULT_AGENT_GUARDRAILS],
    outputContractFormat: draft.outputContractFormat ?? "markdown_structure",
    writePreviewRequired: draft.writePreviewRequired ?? true,
    testBenchValidated: false,
  };
}

export function buildSkillLocalOutput(
  skill: UiManagedSkillItem,
  inputText: string,
  labels: CatalogManagedLabels,
): string {
  return labels.skillPreviewLineTemplate
    .replace("{name}", skill.name)
    .replace("{handle}", skill.commandHandle)
    .replace("{objective}", skill.objective)
    .replace("{input}", inputText.trim())
    .replace("{instructions}", skill.instructions)
    .replace("{format}", skill.expectedOutputFormat);
}

export function buildAgentLocalOutput(
  agent: UiManagedAgentItem,
  allSkills: readonly UiManagedSkillItem[],
  prompt: string,
  labels: CatalogManagedLabels,
): string {
  const attached = allSkills.filter((s) => agent.skillIds.includes(s.skillId));
  const heading = labels.agentPreviewHeadingTemplate
    .replace("{name}", agent.name)
    .replace("{mission}", agent.roleMission)
    .replace("{thinking}", agent.thinkingLevel)
    .replace("{posture}", agent.posture ?? "PRODUCER")
    .replace("{partner}", agent.humanPartnerRole ?? "PO_PM")
    .replace("{contract}", agent.outputContractFormat ?? "markdown_structure")
    .replace("{prompt}", prompt.trim())
    .replace("{instructions}", agent.instructions);
  const skillsLine =
    attached.length > 0
      ? labels.agentPreviewSkillsSomeTemplate
          .replace("{count}", String(attached.length))
          .replace("{list}", attached.map((s) => `${s.name} (\`${s.commandHandle}\`)`).join(", "))
      : labels.agentPreviewSkillsEmpty;
  return [heading, skillsLine, labels.agentPreviewSynthesisLine].join("\n");
}

export function buildAgentUpsertPayload(
  agentId: string,
  src: Omit<Partial<AgentSixBlocksDraftState>, "promptRef"> & {
    name: string;
    roleMission: string;
    instructions: string;
    thinkingLevel: UiAgentThinkingLevel;
    visibilityScope?: UiAgentSkillVisibilityScope;
    mcpExposed?: boolean;
    promptRef?: string | null;
  },
) {
  return {
    agent_id: agentId,
    name: src.name,
    role_mission: src.roleMission,
    instructions: src.instructions,
    thinking_level: src.thinkingLevel,
    skill_ids: src.skillIds ? [...src.skillIds] : [],
    visibility_scope: src.visibilityScope,
    mcp_exposed: src.mcpExposed,
    posture: src.posture,
    human_partner_role: src.humanPartnerRole,
    llm_model_tier: src.llmModelTier,
    temperature: src.temperature,
    max_tokens: src.maxTokens,
    prompt_ref: src.promptRef || undefined,
    invocation_modes: src.invocationModes ? [...src.invocationModes] : undefined,
    dialogue_mechanism: src.dialogueMechanism,
    allowed_rag_sources: src.allowedRagSources ? [...src.allowedRagSources] : undefined,
    ontology_views: src.ontologyViews ? [...src.ontologyViews] : undefined,
    mcp_tool_permissions: src.mcpToolPermissions ? { ...src.mcpToolPermissions } : undefined,
    guardrails: src.guardrails ? [...src.guardrails] : undefined,
    output_contract_format: src.outputContractFormat,
    write_preview_required: src.writePreviewRequired,
    test_bench_validated: src.testBenchValidated,
  };
}
