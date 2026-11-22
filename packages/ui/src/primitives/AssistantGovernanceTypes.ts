import type { RgaaModalGuardLabels } from "../components/RgaaModalDialog";

export type UiAssistantResponseTone = "SYNTHETIC" | "BALANCED" | "DETAILED_CODE";
export type UiAssistantResponseFormat =
  | "BULLETS_SUMMARY"
  | "STRUCTURED_SECTIONS"
  | "STEP_BY_STEP";

export interface UiAssembledLayerItem {
  readonly layerNumber: number;
  readonly layerCode:
    | "1_CONSTITUTION"
    | "2_PACK_METIER"
    | "3_EQUIPE"
    | "4_ESPACE"
    | "5_UTILISATEUR";
  readonly label: string;
  readonly immutable: boolean;
  readonly originBadge: "SOCLE" | "PACK" | "EQUIPE" | "ESPACE" | "UTILISATEUR";
  readonly content: string;
  readonly sha256: string;
}

export interface UiAssistantPromptTelemetryRecord {
  readonly turnId: string;
  readonly timestampIso: string;
  readonly userPrompt: string;
  readonly assembledSystemPrompt: string;
  readonly conversationHistoryCount: number;
  readonly folderTitle?: string | null;
  readonly folderPinnedNotes?: string | null;
  readonly thinkingText?: string;
  readonly assistantReply: string;
  readonly modelLabel: string;
  readonly thinkingEffort: string;
  readonly thinkingElapsedSeconds: number;
  readonly userFeedback?: "LIKE" | "DISLIKE" | null;
}

export interface UiAssistantStudioNode {
  readonly nodeId: string;
  readonly title: string;
  readonly nodeOrder: number;
  readonly isHarnessBoundary: boolean;
  readonly lockedBy: "HARNESS" | "PLATFORM" | "TEAM" | null;
  readonly enabled: boolean;
  readonly subLayersCount: number;
  readonly subAgentUri?: string | null;
}

export interface AssistantGovernanceModalAndStudioLabels extends RgaaModalGuardLabels {
  readonly modalTitle: string;
  readonly tab1UserTitle: string;
  readonly tab2WorkspaceTitle: string;
  readonly tab3AssemblyTitle: string;
  readonly toneLabel: string;
  readonly formatLabel: string;
  readonly defaultHatLabel: string;
  readonly personalInstructionsLabel: string;
  readonly saveUserPrefsCta: string;
  readonly workspaceInstructionsLabel: string;
  readonly workspaceReadOnlyBadge: string;
  readonly mcpExposeToggleLabel: string;
  readonly mcpFrozenByUpperBadge: string;
  readonly copyMcpConfigCta: string;
  readonly saveWorkspaceSettingsCta: string;
  readonly openStudioModeBCta?: string;
  readonly studioHeaderTitle?: string;
  readonly studioPrePromptLabel?: string;
  readonly studioHarnessImmutableBadge?: string;
  readonly studioTestDryRunCta?: string;
  readonly studioSaveOverrideCta?: string;
  readonly studioResetDefaultCta?: string;
}

export interface AssistantGovernanceModalAndStudioProps {
  readonly workspaceId: string;
  readonly canEditWorkspaceLayer: boolean;
  readonly canOpenStudioModeB?: boolean;
  readonly isOpen?: boolean;
  readonly initialUserTone?: UiAssistantResponseTone;
  readonly initialUserFormat?: UiAssistantResponseFormat;
  readonly initialDefaultHat?: string;
  readonly initialPersonalInstructions?: string;
  readonly initialWorkspaceInstructions?: string;
  readonly initialMcpExposed?: boolean;
  readonly mcpFrozenByUpperLayer?: boolean;
  readonly mcpIdeConfigJson?: string;
  readonly assembledLayers: readonly UiAssembledLayerItem[];
  readonly promptTelemetryLog?: readonly UiAssistantPromptTelemetryRecord[];
  readonly studioNodes?: readonly UiAssistantStudioNode[];
  readonly initialStudioPrePrompt?: string;
  readonly labels: AssistantGovernanceModalAndStudioLabels;
  readonly onSaveUserPreferences?: (payload: {
    responseTone: UiAssistantResponseTone;
    favoriteFormat: UiAssistantResponseFormat;
    defaultHat: string;
    personalInstructions: string;
  }) => void;
  readonly onSaveWorkspaceSettings?: (payload: {
    workspaceInstructions: string;
    mcpExposeAssistant: boolean;
  }) => void;
  readonly onCopyMcpConfig?: (jsonText: string) => void;
  readonly onSaveStudioOverride?: (payload: {
    scopeLevel: "TEAM" | "WORKSPACE";
    aiPrePrompt: string;
    nodes: readonly UiAssistantStudioNode[];
  }) => void;
  readonly onResetStudioOverride?: (scopeLevel: "TEAM" | "WORKSPACE") => void;
  readonly onClose?: () => void;
}

export const ASSISTANT_DEFAULT_HAT_OPTIONS: readonly {
  readonly value: string;
  readonly label: string;
}[] = [
  { value: "PM", label: "Chef de Projet / Product Manager" },
  { value: "TECH_LEAD", label: "Référent Technique / Architecte" },
  { value: "DEV", label: "Développeur / Ingénieur" },
  { value: "ANALYST", label: "Analyste Métier" },
  { value: "QA_COMPLIANCE", label: "Responsable Qualité & Conformité" },
  { value: "PLATFORM_ADMIN", label: "Administrateur de la Plateforme" },
  { value: "CONTRIBUTOR", label: "Contributeur d'Équipe" },
];
