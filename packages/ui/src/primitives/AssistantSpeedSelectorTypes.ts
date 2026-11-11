import type React from "react";
import type {
  UiAssistantAutocompleteSuggestion,
  UiAssistantModelOption,
} from "./AssistantModelAndEffortPopover";
import type {
  UiAssistantAttachedFileItem,
  UiAssistantAutocompleteOption,
  UiAssistantOrciaDocumentOption,
} from "./AssistantPromptPlusAndAutocomplete";
import type { UiAssistantRagCitationItem } from "./AssistantResponseFooterActionsAndCitations";
import type {
  UiInferenceEffort,
  UiInferenceTier,
} from "./InferenceTierAndEffortSelector";

export type { UiAssistantAutocompleteSuggestion, UiAssistantModelOption };
export type UiAssistantSpeedMode =
  | "SPEED_1_FAST"
  | "SPEED_2_AGENT_TOOLS"
  | "SPEED_3_DEEP_AUDIT";

export interface UiThreeSpeedStepProgress {
  readonly stepCode: string;
  readonly label: string;
  readonly durationMs: number;
  readonly status: "COMPLETED" | "RUNNING";
  readonly connectorOrLens?: string | null;
  readonly intermediateOutput?: string | null;
}

export interface AssistantSpeedSelectorAndStreamViewLabels {
  readonly headerTitle: string;
  readonly speed1PillLabel: string;
  readonly speed2PillLabel: string;
  readonly speed3DeepAuditPillLabel: string;
  readonly cacheHitBadge: string;
  readonly cacheMissBadge: string;
  readonly nodesDeterministicLabel: string;
  readonly ttftBadgePrefix: string;
  readonly inputPlaceholder: string;
  readonly sendPromptCta: string;
}

export interface AssistantSpeedSelectorAndStreamViewProps {
  readonly workspaceId: string;
  readonly userId: string;
  readonly hat: string;
  readonly activeSpeed?: UiAssistantSpeedMode;
  readonly deepAuditPillActive?: boolean;
  readonly selectedTier?: UiInferenceTier;
  readonly selectedEffort?: UiInferenceEffort;
  readonly modelOptions?: readonly UiAssistantModelOption[];
  readonly agentOptions?: readonly UiAssistantAutocompleteOption[];
  readonly skillOptions?: readonly UiAssistantAutocompleteOption[];
  readonly orciaDocuments?: readonly UiAssistantOrciaDocumentOption[];
  readonly ragCitations?: readonly UiAssistantRagCitationItem[];
  readonly autocompleteSuggestions?: readonly UiAssistantAutocompleteSuggestion[];
  readonly prefillPrompt?: string | null;
  readonly onPrefillConsumed?: () => void;
  readonly activeFolderTitle?: string | null;
  readonly activeFolderNotes?: string | null;
  readonly onClearActiveFolder?: () => void;
  readonly previousTurnsSlot?: React.ReactNode;
  readonly reflexiveTraceSlot?: React.ReactNode;
  readonly welcomeTitle?: string;
  readonly showWelcomeHero?: boolean;
  readonly hideTechnicalCacheHeader?: boolean;
  readonly hideLegacySpeedPills?: boolean;
  readonly hideDuplicateCompletedStream?: boolean;
  readonly cacheHit?: boolean;
  readonly cacheLookupMs?: number;
  readonly nodes1To4DeterministicMs?: number;
  readonly ttftMs?: number;
  readonly stepProgress: readonly UiThreeSpeedStepProgress[];
  readonly streamedText?: string;
  readonly activeUserPrompt?: string;
  readonly isGenerating?: boolean;
  readonly initialElapsedSeconds?: number;
  readonly generationStopped?: boolean;
  readonly errorMessage?: string | null;
  readonly labels: AssistantSpeedSelectorAndStreamViewLabels;
  readonly onOpenFoldersFromPlus?: () => void;
  readonly onStopGeneration?: () => void;
  readonly onRegenerateLastTurn?: () => void;
  readonly onSaveDraftFromResponse?: (content: string) => void;
  readonly onContinueInProcessFromResponse?: (content: string) => void;
  readonly onInspectCitation?: (
    source: UiAssistantRagCitationItem,
    index: number,
  ) => void;
  readonly currentTurnFeedback?: "LIKE" | "DISLIKE" | null;
  readonly onFeedbackLastTurn?: (feedback: "LIKE" | "DISLIKE" | null) => void;
  readonly onSendTurn?: (payload: {
    userPrompt: string;
    requestedSpeed: UiAssistantSpeedMode;
    deepAuditPillActive: boolean;
    requestedTier?: UiInferenceTier;
    thinkingEffort?: UiInferenceEffort;
    attachedFiles?: readonly UiAssistantAttachedFileItem[];
  }) => void;
}
