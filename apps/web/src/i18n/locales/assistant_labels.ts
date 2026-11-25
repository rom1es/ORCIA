import type {
  AssistantApprovalRequiredCardLabels,
  AssistantCitationPillsAndArtifactCardLabels,
  AssistantFoldersAndCollaborativeThreadViewLabels,
  AssistantGovernanceModalAndStudioLabels,
  AssistantSpeedSelectorAndStreamViewLabels,
  AssistantToolCallTraceLabels,
} from "@orcia/ui";

export interface AssistantDictionarySection {
  readonly assistantGovernance: AssistantGovernanceModalAndStudioLabels;
  readonly assistantSpeedStream: AssistantSpeedSelectorAndStreamViewLabels;
  readonly assistantCitations: AssistantCitationPillsAndArtifactCardLabels;
  readonly assistantFolders: AssistantFoldersAndCollaborativeThreadViewLabels;
  readonly assistantFoldersSync: {
    readonly workspaceRequired: string;
    readonly loadFailed: (detail: string) => string;
    readonly saveFailed: (detail: string) => string;
  };
  readonly assistantNoEmbeddingModel: {
    readonly bannerTitle: string;
    readonly bannerDescription: string;
    readonly configureCta: string;
  };
  readonly assistantNoChatModel: {
    readonly bannerTitle: string;
    readonly bannerDescription: string;
    readonly configureCta: string;
    readonly contactAdminGuidance: string;
  };
  readonly assistantRagNotice: {
    readonly noEmbeddingTitle: string;
    readonly noEmbeddingDescription: string;
    readonly configureEmbeddingCta: string;
    readonly contactAdminGuidance: string;
    readonly reindexingTitle: string;
    readonly reindexingDescription: string;
    readonly reindexFailedTitle: string;
    readonly reindexFailedDescription: string;
    readonly relaunchReindexCta: string;
    readonly checkEmbeddingCta: string;
  };
  readonly assistantStreamErrors: {
    readonly sessionExpiredMessage: string;
    readonly reconnectCta: string;
    readonly aiUnavailableMessage: (detail?: string) => string;
  };
  readonly assistantToolTrace: AssistantToolCallTraceLabels;
  readonly assistantApprovalCard: AssistantApprovalRequiredCardLabels;
}

export { ASSISTANT_FR_LABELS } from "./assistant_labels_fr";
export { ASSISTANT_EN_LABELS } from "./assistant_labels_en";
