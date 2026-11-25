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

export interface UiAssistantSelectOption {
  readonly value: string;
  readonly label: string;
}

export interface AssistantGovernanceModalAndStudioLabels extends RgaaModalGuardLabels {
  readonly modalTitle: string;
  readonly savedBadgeLabel: string;
  readonly infoBannerText: string;
  readonly tab1UserTitle: string;
  readonly tab2WorkspaceTitle: string;
  readonly tab3AssemblyTitle: string;
  readonly toneLabel: string;
  readonly toneOptions: readonly UiAssistantSelectOption[];
  readonly formatLabel: string;
  readonly formatLabels: {
    readonly bulletsSummary: string;
    readonly structuredSections: string;
    readonly stepByStep: string;
  };
  readonly defaultHatLabel: string;
  readonly hatOptions: readonly UiAssistantSelectOption[];
  readonly personalInstructionsLabel: string;
  readonly saveUserPrefsCta: string;
  readonly workspaceInstructionsLabel: string;
  readonly workspaceReadOnlyBadge: string;
  readonly mcpExposeToggleLabel: string;
  readonly mcpFrozenByUpperBadge: string;
  readonly copyMcpConfigCta: string;
  readonly saveWorkspaceSettingsCta: string;
  readonly saveChangesCta?: string;
  readonly savingChangesLabel?: string;
  readonly unsavedAssemblyNote?: string;
  readonly saveErrorFallback?: string;
  readonly telemetryHeading: string;
  readonly telemetrySubtitle: string;
  readonly telemetryEmptyIntro: string;
  readonly telemetryLikeLabel: string;
  readonly telemetryDislikeLabel: string;
  readonly telemetryUnratedLabel: string;
  readonly telemetryHideContextCta: string;
  readonly telemetryInspectContextCta: string;
  readonly telemetryModelPrefix: string;
  readonly telemetryThinkingPrefix: string;
  readonly telemetryHistoryPrefix: string;
  readonly telemetryMessagesUnit: string;
  readonly telemetryFolderPrefix: string;
  readonly telemetrySystemPromptHeading: string;
  readonly telemetryDefaultContextFallback: string;
  readonly openStudioModeBCta?: string;
  readonly studioHeaderTitle?: string;
  readonly studioPrePromptLabel?: string;
  readonly studioHarnessImmutableBadge?: string;
  readonly studioTestDryRunCta?: string;
  readonly studioSaveOverrideCta?: string;
  readonly studioResetDefaultCta?: string;
  readonly studioWorkspaceScopeLabel?: string;
  readonly studioTeamScopeLabel?: string;
  readonly studioLayersPrefix?: string;
  readonly studioAddSubAgentCta?: string;
  readonly studioResetRestoredBanner?: string;
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
  readonly saveError?: string | null;
  readonly labels: AssistantGovernanceModalAndStudioLabels;
  readonly onSaveUserPreferences?: (payload: {
    responseTone: UiAssistantResponseTone;
    favoriteFormat: UiAssistantResponseFormat;
    defaultHat: string;
    personalInstructions: string;
  }) => Promise<boolean> | boolean | void;
  readonly onSaveWorkspaceSettings?: (payload: {
    workspaceInstructions: string;
    mcpExposeAssistant: boolean;
  }) => Promise<boolean> | boolean | void;
  readonly onCopyMcpConfig?: (jsonText: string) => void;
  readonly onClearSaveError?: () => void;
  readonly onSaveStudioOverride?: (payload: {
    scopeLevel: "TEAM" | "WORKSPACE";
    aiPrePrompt: string;
    nodes: readonly UiAssistantStudioNode[];
  }) => void;
  readonly onResetStudioOverride?: (scopeLevel: "TEAM" | "WORKSPACE") => void;
  readonly onClose?: () => void;
}
