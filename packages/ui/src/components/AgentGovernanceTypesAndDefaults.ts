import type {
  UiAgentSkillVisibilityScope,
  UiAgentThinkingLevel,
  UiManagedAgentItem,
} from "./AgentsAndSkillsTypes";

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
}

export interface AgentReadinessConditionItem {
  readonly index: 1 | 2 | 3 | 4 | 5 | 6;
  readonly code: string;
  readonly label: string;
  readonly satisfied: boolean;
  readonly detail: string;
}

export interface AgentGovernanceStudioLabels {
  readonly visibilityFieldLabel: string;
  readonly visibilityShortLabel: string;
  readonly visibilityTeamShort: string;
  readonly visibilityPrivateShort: string;
  readonly visibilityPackPrefix: string;
  readonly visibilityTeamFull: string;
  readonly visibilityPrivateFull: string;
  readonly toggleVisibilityTitle: string;
  readonly loadPackAgentsButton: string;
  readonly newAgentButton: string;
  readonly newSkillButton: string;
  readonly testMcpButton: string;
  readonly kpiAgentsTitle: string;
  readonly kpiActiveSingular?: string;
  readonly kpiActiveSuffix: string;
  readonly kpiSkillsTitle: string;
  readonly kpiReusableSingular?: string;
  readonly kpiReusableSuffix: string;
  readonly kpiOriginMcpTitle: string;
  readonly kpiPackTeamSingular?: string;
  readonly kpiPackTeamSuffix: string;
  readonly searchPlaceholder: string;
  readonly visibilityFilterAriaLabel: string;
  readonly filterAll: string;
  readonly filterPack: string;
  readonly filterTeam: string;
  readonly filterPrivate: string;
  readonly createAgentSubtitle: string;
  readonly createAgentDisabledReason: string;
  readonly readinessChecklistTitle: string;
  readonly escapeCancelHint: string;
  readonly cancelButton: string;
  readonly closeEscapeLabel: string;
  readonly savedFeedbackLabel: string;
  readonly autosaveActiveLabel: string;
  readonly saveButtonLabel: string;
  readonly defaultTestPromptTemplate: string;
  readonly defaultSkillTestPromptTemplate: string;
  readonly benchValidatedBadge: string;
  readonly benchToTestBadge: string;
  readonly benchShortToTestBadge: string;
  readonly savedShortBadge: string;
  readonly exposeMcpLabel: string;
  readonly testBenchHeading: string;
  readonly conditionsMetPrefix: string;
  readonly copyHandleTitle: string;
  readonly copySkillTitle: string;
  readonly copiedShortLabel: string;
  readonly copyCodeLabel: string;
  readonly copyHandleButton: string;
  readonly copySkillButton: string;
  readonly postureProducerBadge: string;
  readonly postureEvaluatorBadge: string;
  readonly partnerBadgePrefix: string;
  readonly disabledWorkspaceBadge: string;
  readonly mcpActiveSingular?: string;
  readonly mcpActiveBadge: string;
  readonly modelPassportLabel: string;
  readonly tempShortLabel: string;
  readonly tokShortLabel: string;
  readonly precisionShortLabel?: string;
  readonly maxTokensUnitLabel?: string;
  readonly ragShortLabel: string;
  readonly ontologyShortLabel: string;
  readonly outputShortLabel: string;
  readonly writePreviewBadge: string;
  readonly noAttachedSkillsLabel: string;
  readonly manageBlocksButton: string;
  readonly useInAssistantButton: string;
  readonly configureAndTestSixBlocksButton: string;
  readonly duplicateAndCustomizeButton: string;
  readonly disableOnWorkspaceButton: string;
  readonly enableOnWorkspaceButton: string;
  readonly duplicateButton: string;
  readonly configureAndTestSkillButton: string;
  readonly skillParametersPrefix: string;
  readonly skillCreateDisabledReason: string;
  readonly skillDetailAriaPrefix: string;
  readonly skillSandboxHeading: string;
  readonly defaultSkillOutputFormat: string;
  readonly pinnedAssistantTitle: string;
  readonly pinnedAssistantBadge: string;
  readonly pinnedAssistantDescription: string;
  readonly pinnedAssistantSettingsButton: string;
  readonly pinnedAssistantOpenButton: string;
  readonly showBlockByBlockLabel: string;
  readonly showAllSixBlocksLabel: string;
  readonly assistantReadyPrefix: string;
  readonly defaultHandleSlug: string;
  readonly blockTitles: Readonly<Record<AgentStudioBlockKey, { badge: string; title: string; heading: string }>>;
  readonly postureFieldLabel: string;
  readonly postureProducerOption: string;
  readonly postureEvaluatorOption: string;
  readonly humanPartnerFieldLabel: string;
  readonly humanPartnerRoles: Readonly<Record<UiAgentHumanPartnerRole, string>>;
  readonly llmModelFieldLabel: string;
  readonly llmModelTiers: Readonly<Record<UiAgentLlmModelTier, string>>;
  readonly llmTierShortLabels?: Readonly<Record<UiAgentLlmModelTier, string>>;
  readonly settingsPrecisionLabels?: {
    readonly deterministic: string;
    readonly precise: string;
    readonly balanced: string;
    readonly creative: string;
    readonly contextTemplate: string;
  };
  readonly temperatureFieldLabel: string;
  readonly temperatureOptions: Readonly<Record<string, string>>;
  readonly maxTokensFieldLabel: string;
  readonly maxTokensOptions: Readonly<Record<string, string>>;
  readonly systemPromptSuffix: string;
  readonly promptRefFieldLabel: string;
  readonly promptRefPlaceholder: string;
  readonly dialogueMechanismFieldLabel: string;
  readonly dialogueMechanisms: Readonly<Record<UiAgentDialogueMechanism, string>>;
  readonly invocationModesFieldLabel: string;
  readonly invocationModes: Readonly<Record<UiAgentInvocationMode, string>>;
  readonly ragSourcesFieldLabel: string;
  readonly ragSourceOptions: Readonly<Record<string, string>>;
  readonly ontologyViewsFieldLabel: string;
  readonly ontologyViewOptions: Readonly<Record<string, string>>;
  readonly mcpToolboxFieldLabel: string;
  readonly mcpToolsCatalog: Readonly<Record<string, string>>;
  readonly mcpPermissionModes: Readonly<Record<UiMcpToolPermissionMode, string>>;
  readonly outputContractFieldLabel: string;
  readonly outputContractFormats: Readonly<Record<UiAgentOutputContractFormat, string>>;
  readonly writePreviewRequiredLabel: string;
  readonly guardrailsFieldLabel: string;
  readonly guardrailOptions: Readonly<Record<string, string>>;
  readonly readinessConditions: {
    readonly identityLabel: string;
    readonly identityOkTemplate: string;
    readonly identityMissing: string;
    readonly postureProducerShort: string;
    readonly postureEvaluatorShort: string;
    readonly instructionsLabel: string;
    readonly instructionsOkTemplate: string;
    readonly instructionsMissing: string;
    readonly engineLabel: string;
    readonly engineTemplate: string;
    readonly citationsLabel: string;
    readonly citationsOkTemplate: string;
    readonly citationsMissing: string;
    readonly ragScopeLabel: string;
    readonly ragScopeTemplate: string;
    readonly writePreviewLabel: string;
    readonly writePreviewValidated: string;
    readonly writePreviewReady: string;
  };
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

export function createDefaultAgentSixBlocksDraft(
  existing?: UiManagedAgentItem | null,
): AgentSixBlocksDraftState {
  const posture: UiAgentPosture = existing?.posture ?? "PRODUCER";
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
    testBenchValidated: existing?.testBenchValidated ?? false,
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
