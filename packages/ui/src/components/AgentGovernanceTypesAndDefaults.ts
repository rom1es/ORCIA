import type { AgentGovernanceStudioLabels } from "./AgentGovernanceStudioLabels";
import type {
  UiAgentLifecycleStatus,
  UiAgentSkillVisibilityScope,
  UiAgentTestBenchStatus,
  UiAgentThinkingLevel,
  UiManagedAgentItem,
} from "./AgentsAndSkillsTypes";

export type { AgentGovernanceStudioLabels };

export type UiAgentPosture = "PRODUCER" | "EVALUATOR_GATE";
export type UiAgentHumanPartnerRole =
  | "PO_PM"
  | "ARCHITECT"
  | "TECH_LEAD"
  | "SECURITY_QA"
  | "ALL";
export type UiAgentLlmModelTier = "team_default" | "fast" | "deep" | "discovery";
export type UiAgentInvocationMode = "generer" | "corrections" | "section";
export type UiAgentDialogueMechanism =
  | "questionnaire_prealable"
  | "pause_par_bloc"
  | "direct";
export type UiAgentOutputContractFormat =
  | "markdown_structure"
  | "confluence_draft"
  | "jira_draft"
  | "gate_risk_json";
export type UiMcpToolPermissionMode = "NONE" | "READ_ONLY" | "WRITE_PREVIEW";
export type AgentStudioBlockKey = "A" | "B" | "C" | "D" | "E" | "F";

export interface AgentSixBlocksDraftState {
  readonly name: string;
  readonly roleMission: string;
  readonly instructions: string;
  readonly thinkingLevel: UiAgentThinkingLevel;
  readonly visibilityScope: UiAgentSkillVisibilityScope;
  readonly skillIds: readonly string[];
  readonly mcpExposed: boolean;
  readonly posture: UiAgentPosture;
  readonly humanPartnerRole: UiAgentHumanPartnerRole;
  readonly llmModelTier: UiAgentLlmModelTier;
  readonly temperature: number;
  readonly maxTokens: number;
  readonly promptRef: string;
  readonly invocationModes: readonly string[];
  readonly dialogueMechanism: UiAgentDialogueMechanism;
  readonly allowedRagSources: readonly string[];
  readonly ontologyViews: readonly string[];
  readonly mcpToolPermissions: Readonly<Record<string, string>>;
  readonly guardrails: readonly string[];
  readonly outputContractFormat: UiAgentOutputContractFormat;
  readonly writePreviewRequired: boolean;
  readonly testBenchValidated: boolean;
  readonly lifecycleStatus: UiAgentLifecycleStatus;
  readonly testBenchStatus: UiAgentTestBenchStatus;
}

export interface AgentReadinessConditionItem {
  readonly index: 1 | 2 | 3 | 4 | 5 | 6;
  readonly code: string;
  readonly label: string;
  readonly satisfied: boolean;
  readonly detail: string;
}

export const DEFAULT_MCP_TOOL_PERMISSIONS_MAP: Readonly<Record<string, string>> = {
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

export function resolveAgentLifecycleAndBenchStatus(agent: UiManagedAgentItem | null | undefined): {
  readonly lifecycleStatus: UiAgentLifecycleStatus;
  readonly testBenchStatus: UiAgentTestBenchStatus;
} {
  if (!agent) {
    return { lifecycleStatus: "DRAFT", testBenchStatus: "UNTESTED" };
  }
  const testBenchStatus: UiAgentTestBenchStatus =
    agent.testBenchStatus === "PASSED" ||
    agent.testBenchStatus === "FAILED" ||
    agent.testBenchStatus === "UNTESTED"
      ? agent.testBenchStatus
      : agent.testBenchValidated
        ? "PASSED"
        : "UNTESTED";
  const lifecycleStatus: UiAgentLifecycleStatus =
    agent.lifecycleStatus === "ACTIVE" || agent.lifecycleStatus === "DRAFT"
      ? agent.lifecycleStatus
      : "DRAFT";
  return { lifecycleStatus, testBenchStatus };
}

export function createDefaultAgentSixBlocksDraft(
  existing?: UiManagedAgentItem | null,
): AgentSixBlocksDraftState {
  const posture: UiAgentPosture = existing?.posture ?? "PRODUCER";
  const resolved = resolveAgentLifecycleAndBenchStatus(existing);
  return {
    name: existing?.name ?? "",
    roleMission: existing?.roleMission ?? "",
    instructions: existing?.instructions ?? "",
    thinkingLevel: existing?.thinkingLevel ?? "medium",
    visibilityScope: existing?.visibilityScope ?? "TEAM",
    skillIds: existing?.skillIds ?? [],
    mcpExposed: existing?.mcpExposed ?? false,
    posture,
    humanPartnerRole: existing?.humanPartnerRole ?? "PO_PM",
    llmModelTier: existing?.llmModelTier ?? "team_default",
    temperature:
      existing?.temperature ?? (posture === "EVALUATOR_GATE" ? 0.0 : 0.2),
    maxTokens: existing?.maxTokens ?? 4096,
    promptRef: existing?.promptRef ?? "",
    invocationModes: existing?.invocationModes ?? [
      "generer",
      "corrections",
      "section",
    ],
    dialogueMechanism:
      existing?.dialogueMechanism ?? "questionnaire_prealable",
    allowedRagSources: existing?.allowedRagSources ?? ["all_workspace_sources"],
    ontologyViews: existing?.ontologyViews ?? [
      "glossary",
      "apis_adr",
      "prd_regles_metier",
    ],
    mcpToolPermissions:
      existing?.mcpToolPermissions ?? DEFAULT_MCP_TOOL_PERMISSIONS_MAP,
    guardrails: existing?.guardrails ?? DEFAULT_AGENT_GUARDRAILS,
    outputContractFormat:
      existing?.outputContractFormat ?? "markdown_structure",
    writePreviewRequired: existing?.writePreviewRequired ?? true,
    testBenchValidated: resolved.testBenchStatus === "PASSED",
    lifecycleStatus: resolved.lifecycleStatus,
    testBenchStatus: resolved.testBenchStatus,
  };
}

export { computeAgentReadinessChecklist } from "./AgentGovernanceReadiness";

export function formatAgentModelPassportSummary(
  tier: UiAgentLlmModelTier | undefined,
  temperature: number | undefined,
  maxTokens: number | undefined,
  studio: AgentGovernanceStudioLabels,
): string {
  const resolvedTier: UiAgentLlmModelTier = tier ?? "team_default";
  const tierLabel =
    studio.llmTierShortLabels?.[resolvedTier] ??
    studio.llmModelTiers[resolvedTier]?.split("(")[0]?.trim() ??
    resolvedTier;
  const tempVal = temperature ?? 0.2;
  const precision = studio.settingsPrecisionLabels;
  const styleLabel =
    tempVal <= 0
      ? (precision?.deterministic ?? "Deterministic")
      : tempVal <= 0.3
        ? (precision?.precise ?? "Precise")
        : tempVal <= 0.5
          ? (precision?.balanced ?? "Balanced")
          : (precision?.creative ?? "Creative");
  const tokensVal = maxTokens ?? 4096;
  const windowLabel = tokensVal >= 1024 ? `${Math.round(tokensVal / 1024)}k` : `${tokensVal}`;
  const contextLabel = precision?.contextTemplate
    ? precision.contextTemplate.replace("{window}", windowLabel)
    : `${windowLabel} context`;
  return `${tierLabel} · ${styleLabel} · ${contextLabel}`;
}

export function pickAgentComparableFields(d: AgentSixBlocksDraftState): string {
  return JSON.stringify({
    name: d.name,
    roleMission: d.roleMission,
    instructions: d.instructions,
    thinkingLevel: d.thinkingLevel,
    visibilityScope: d.visibilityScope,
    posture: d.posture,
    humanPartnerRole: d.humanPartnerRole,
    llmModelTier: d.llmModelTier,
    temperature: d.temperature,
    maxTokens: d.maxTokens,
    promptRef: d.promptRef,
    invocationModes: d.invocationModes,
    dialogueMechanism: d.dialogueMechanism,
    allowedRagSources: d.allowedRagSources,
    ontologyViews: d.ontologyViews,
    mcpToolPermissions: d.mcpToolPermissions,
    guardrails: d.guardrails,
    outputContractFormat: d.outputContractFormat,
    writePreviewRequired: d.writePreviewRequired,
  });
}
