import type { createOrciaApiClient } from "@orcia/api-client";
import type {
  UiAgentDialogueMechanism,
  UiAgentHumanPartnerRole,
  UiAgentLifecycleStatus,
  UiAgentLlmModelTier,
  UiAgentOutputContractFormat,
  UiAgentPosture,
  UiAgentSkillVisibilityScope,
  UiAgentTestBenchStatus,
  UiAgentThinkingLevel,
  UiManagedAgentItem,
  UiManagedSkillItem,
} from "@orcia/ui";

type ListCatalogResponse = Awaited<
  ReturnType<ReturnType<typeof createOrciaApiClient>["listAgentsAndSkills"]>
>;
export type ApiSkillDto = NonNullable<ListCatalogResponse["skills"]>[number];
export type ApiAgentDto = NonNullable<ListCatalogResponse["agents"]>[number];

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
export const DEFAULT_ONTOLOGY_VIEWS: readonly string[] = [
  "glossary",
  "apis_adr",
  "prd_regles_metier",
];

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
    dialogueMechanism: (a.dialogue_mechanism ??
      "questionnaire_prealable") as UiAgentDialogueMechanism,
    allowedRagSources: a.allowed_rag_sources ?? [...DEFAULT_RAG_SOURCES],
    ontologyViews: a.ontology_views ?? [...DEFAULT_ONTOLOGY_VIEWS],
    mcpToolPermissions: a.mcp_tool_permissions ?? { ...DEFAULT_MCP_TOOL_PERMISSIONS },
    guardrails: a.guardrails ?? [...DEFAULT_AGENT_GUARDRAILS],
    outputContractFormat: (a.output_contract_format ??
      "markdown_structure") as UiAgentOutputContractFormat,
    writePreviewRequired: a.write_preview_required ?? true,
    testBenchValidated: a.test_bench_status === "PASSED" || Boolean(a.test_bench_validated),
    lifecycleStatus: (a.lifecycle_status ?? "DRAFT") as UiAgentLifecycleStatus,
    testBenchStatus: (a.test_bench_status ??
      (a.test_bench_validated ? "PASSED" : "UNTESTED")) as UiAgentTestBenchStatus,
  };
}
