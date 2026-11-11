import type {
  UiAgentSkillVisibilityScope,
  UiAgentThinkingLevel,
  UiManagedAgentItem,
} from "./AgentsAndSkillsManagerView";

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
  // Block A: Identity, Posture & Human Partner
  readonly posture: UiAgentPosture;
  readonly humanPartnerRole: UiAgentHumanPartnerRole;
  // Block B: Cognitive Engine (Model, Effort, Inference & Budget)
  readonly llmModelTier: UiAgentLlmModelTier;
  readonly temperature: number;
  readonly maxTokens: number;
  // Block C: System Instructions & Interaction Modes
  readonly promptRef: string;
  readonly invocationModes: readonly string[];
  readonly dialogueMechanism: UiAgentDialogueMechanism;
  // Block D: Knowledge Scope (RAG & Ontology)
  readonly allowedRagSources: readonly string[];
  readonly ontologyViews: readonly string[];
  // Block E: MCP Toolbox Permissions
  readonly mcpToolPermissions: Readonly<Record<string, string>>;
  // Block F: Guardrails & Output Contract
  readonly guardrails: readonly string[];
  readonly outputContractFormat: UiAgentOutputContractFormat;
  readonly writePreviewRequired: boolean;
  readonly testBenchValidated: boolean;
}

export interface AgentReadinessConditionItem {
  readonly index: 1 | 2 | 3 | 4 | 5 | 6;
  readonly code: string;
  readonly labelFr: string;
  readonly satisfied: boolean;
  readonly detailFr: string;
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

export const AGENT_STUDIO_BLOCKS: readonly {
  readonly key: AgentStudioBlockKey;
  readonly badge: string;
  readonly titleFr: string;
  readonly subtitleFr: string;
}[] = [
  {
    key: "A",
    badge: "Bloc A",
    titleFr: "Identité & Posture (Persona)",
    subtitleFr: "Nom, @handle, posture métier et binôme humain",
  },
  {
    key: "B",
    badge: "Bloc B",
    titleFr: "Moteur Cognitif & Budget",
    subtitleFr: "Modèle LLM, effort, température et plafond de tokens",
  },
  {
    key: "C",
    badge: "Bloc C",
    titleFr: "Instructions & Dialogue",
    subtitleFr: "Prompt système / prompt_ref, modes et rythme de dialogue",
  },
  {
    key: "D",
    badge: "Bloc D",
    titleFr: "Périmètre de Connaissance",
    subtitleFr: "Sources documentaires RAG et vues ontologiques",
  },
  {
    key: "E",
    badge: "Bloc E",
    titleFr: "Toolbox MCP & Skills",
    subtitleFr: "Compétences /skills et outils MCP (Lire vs Écrire)",
  },
  {
    key: "F",
    badge: "Bloc F",
    titleFr: "Garde-fous & Contrat de Sortie",
    subtitleFr: "Sécurité, citations obligatoires et gabarit du livrable",
  },
];

export const HUMAN_PARTNER_ROLE_LABELS_FR: Readonly<
  Record<UiAgentHumanPartnerRole, string>
> = {
  PO_PM: "Product Owner / Product Manager (PO/PM)",
  ARCHITECT: "Architecte Logiciel / Solution",
  TECH_LEAD: "Tech Lead / Développeur Senior",
  SECURITY_QA: "Auditeur Sécurité / Responsable Qualité",
  ALL: "Tout membre habilité de l'Espace",
};

export const LLM_MODEL_TIER_LABELS_FR: Readonly<Record<UiAgentLlmModelTier, string>> = {
  team_default: "Par défaut (équipe)",
  fast: "Modèle qualifié : Rapide (Synthèse & Tri)",
  deep: "Modèle qualifié : Profond (Architecture & Audit)",
  discovery: "Modèle qualifié : Discovery (Exploration & Idéation)",
};

export const DIALOGUE_MECHANISM_LABELS_FR: Readonly<
  Record<UiAgentDialogueMechanism, string>
> = {
  questionnaire_prealable:
    "Questionnaire préalable obligatoire sur les zones d'ombre avant de rédiger",
  pause_par_bloc:
    "Pause de validation étape par étape (s'arrêter après chaque bloc rédigé)",
  direct: "Production directe du livrable structuré avec citations",
};

export const OUTPUT_CONTRACT_FORMAT_LABELS_FR: Readonly<
  Record<UiAgentOutputContractFormat, string>
> = {
  markdown_structure: "Markdown structuré (sections obligatoires & citations)",
  confluence_draft: "Confluence — Brouillon de page gouverné",
  jira_draft: "Jira — Brouillon de ticket (Feature / Epic / US)",
  gate_risk_json: "Gate — Score de risque JSON & Verdict contradictoire",
};

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

export function computeAgentReadinessChecklist(
  draft: AgentSixBlocksDraftState,
): readonly AgentReadinessConditionItem[] {
  const hasIdentity =
    draft.name.trim().length > 0 && draft.roleMission.trim().length > 0;
  const hasInstructions =
    draft.instructions.trim().length > 0 || draft.promptRef.trim().length > 0;
  const hasModelAndBudget =
    Boolean(draft.llmModelTier) && draft.maxTokens >= 256;
  const hasCitationsPolicy = draft.guardrails.includes("citations_obligatoires");
  const hasRagAndOntologyScope =
    draft.allowedRagSources.length > 0 && draft.ontologyViews.length > 0;
  const hasWriteTools = Object.values(draft.mcpToolPermissions).some(
    (m) => m === "WRITE_PREVIEW",
  );
  const writePreviewOk = !hasWriteTools || draft.writePreviewRequired;

  return [
    {
      index: 1,
      code: "IDENTITY_AND_HANDLE",
      labelFr: "Identifiant @handle unique & Posture définie",
      satisfied: hasIdentity,
      detailFr: hasIdentity
        ? `Posture ${draft.posture === "EVALUATOR_GATE" ? "Évaluateur Gate" : "Producteur"} · Binôme ${draft.humanPartnerRole}`
        : "Renseignez le nom et la mission métier (Bloc A)",
    },
    {
      index: 2,
      code: "SYSTEM_INSTRUCTIONS",
      labelFr: "Instruction système (Prompt ou prompt_ref)",
      satisfied: hasInstructions,
      detailFr: hasInstructions
        ? `${draft.invocationModes.length} mode(s) d'invocation actifs`
        : "Saisissez les instructions système ou un prompt_ref (Bloc C)",
    },
    {
      index: 3,
      code: "COGNITIVE_ENGINE",
      labelFr: "Modèle LLM résolu & Plafond de tokens",
      satisfied: hasModelAndBudget,
      detailFr: `${LLM_MODEL_TIER_LABELS_FR[draft.llmModelTier]} · Temp ${draft.temperature} · ${draft.maxTokens} tok`,
    },
    {
      index: 4,
      code: "CITATIONS_POLICY",
      labelFr: "Politique de sortie avec citations vérifiables",
      satisfied: hasCitationsPolicy,
      detailFr: hasCitationsPolicy
        ? `Contrat : ${OUTPUT_CONTRACT_FORMAT_LABELS_FR[draft.outputContractFormat]}`
        : "Activez les citations vérifiables obligatoires (Bloc F)",
    },
    {
      index: 5,
      code: "RAG_AND_RBAC_SCOPE",
      labelFr: "Cloisonnement cognitif RAG & Ontologie",
      satisfied: hasRagAndOntologyScope,
      detailFr: `${draft.allowedRagSources.length} source(s) RAG · ${draft.ontologyViews.length} vue(s) ontologie`,
    },
    {
      index: 6,
      code: "WRITE_PREVIEW_AND_BENCH",
      labelFr: "Garde-fou Write-Preview & Banc de Test",
      satisfied: writePreviewOk,
      detailFr: draft.testBenchValidated
        ? "Validé au Banc de Test + Write-Preview actif"
        : "Write-Preview actif (prêt pour essai au Banc de Test)",
    },
  ];
}
