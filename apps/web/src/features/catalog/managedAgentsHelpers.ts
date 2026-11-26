import type { UpsertAgentRequest } from "@orcia/api-client";
import type {
  AgentSixBlocksDraftState,
  CreateAgentSixBlocksInput,
  UiAgentSkillVisibilityScope,
  UiAgentThinkingLevel,
  UiManagedAgentItem,
  UiManagedSkillItem,
} from "@orcia/ui";
import type { FeatureAdminCatalogSettingsDictionary } from "../../i18n/locales/feature_admin_catalog_settings_labels";
import { slugifyIdentifier } from "./packAgentsCatalog";

import {
  DEFAULT_AGENT_GUARDRAILS,
  DEFAULT_INVOCATION_MODES,
  DEFAULT_MCP_TOOL_PERMISSIONS,
  DEFAULT_ONTOLOGY_VIEWS,
  DEFAULT_RAG_SOURCES,
  mapAgentDtoToUi,
  mapSkillDtoToUi,
  type ApiAgentDto,
  type ApiSkillDto,
} from "../../components/agentDtoMappers";

export {
  DEFAULT_AGENT_GUARDRAILS,
  DEFAULT_INVOCATION_MODES,
  DEFAULT_MCP_TOOL_PERMISSIONS,
  DEFAULT_ONTOLOGY_VIEWS,
  DEFAULT_RAG_SOURCES,
  mapAgentDtoToUi,
  mapSkillDtoToUi,
  type ApiAgentDto,
  type ApiSkillDto,
};

export type CatalogManagedLabels = FeatureAdminCatalogSettingsDictionary["catalog"];

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
    lifecycleStatus: "DRAFT",
    testBenchStatus: "UNTESTED",
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
): UpsertAgentRequest {
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
    lifecycle_status: src.lifecycleStatus,
  };
}
