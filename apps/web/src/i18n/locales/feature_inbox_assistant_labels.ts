import type { UiAssistantAutocompleteOption } from "@orcia/ui";

export interface FeatureInboxAssistantDictionary {
  readonly notificationsCenter: {
    readonly directClaimPrefix: string;
    readonly inboxReviewStepLabel: string;
    readonly title: string;
    readonly liveStreamBadge: string;
    readonly restSyncBadge: string;
    readonly filterAll: string;
    readonly filterPersonal: string;
    readonly filterTeam: string;
    readonly loadingText: string;
    readonly emptyText: string;
    readonly loadErrorTemplate: string;
    readonly claimErrorTemplate: string;
    readonly releaseErrorTemplate: string;
  };
  readonly toolbar: {
    readonly newConversationBtn: string;
    readonly savedConversationsLabel: string;
    readonly savedConversationsCountTemplate: string;
    readonly foldersLabel: string;
    readonly foldersCountTemplate: string;
  };
  readonly savedConversations: {
    readonly panelTitle: string;
    readonly panelTitleCountTemplate: string;
    readonly emptyText: string;
    readonly turnSingular: string;
    readonly turnPlural: string;
    readonly deleteBtn: string;
    readonly defaultThreadTitle: string;
    readonly defaultNewDiscussionTitle: string;
    readonly defaultModelLabel: string;
  };
  readonly assistantFlow: {
    readonly welcomeTitle: string;
    readonly collaborativeMessageAddedTemplate: string;
    readonly mcpConfigCopiedBanner: string;
    readonly folderCreatedTemplate: string;
    readonly folderNotesSavedBanner: string;
    readonly folderVisibilityUpdatedTemplate: string;
    readonly attachmentHeader: string;
    readonly explorationGroupLabel: string;
    readonly callingToolTemplate: string;
    readonly toolResultTemplate: string;
    readonly modelReasoningLabel: string;
    readonly modelReasoningInProgressLabel: string;
    readonly actionPendingApprovalLabel: string;
    readonly streamProviderErrorFallback: string;
    readonly fastEffortLabel: string;
    readonly deepEffortLabel: string;
    readonly standardEffortLabel: string;
    readonly feedbackErrorContext: string;
    readonly turnErrorContext: string;
    readonly governanceErrorContext: string;
    readonly personalPrefsSavedBanner: string;
    readonly workspaceSettingsSavedBanner: string;
  };
  readonly autocomplete: {
    readonly configuredModelSubtitle: string;
    readonly tierSimpleTitle: string;
    readonly tierSimpleSubtitle: string;
    readonly tierMediumTitle: string;
    readonly tierMediumSubtitle: string;
    readonly tierComplexTitle: string;
    readonly tierComplexSubtitle: string;
    readonly badgePrivate: string;
    readonly badgeTeam: string;
    readonly badgePackDefault: string;
    readonly sdlcArchitectName: string;
    readonly sdlcArchitectDesc: string;
    readonly sdlcAnalystName: string;
    readonly sdlcAnalystDesc: string;
    readonly sdlcReviewName: string;
    readonly sdlcReviewDesc: string;
    readonly defaultAgents: readonly UiAssistantAutocompleteOption[];
    readonly defaultSkills: readonly UiAssistantAutocompleteOption[];
  };
  readonly citations: {
    readonly serverVerifiedSourcesTemplate: string;
    readonly folderTitleTemplate: string;
    readonly defaultDraftTitle: string;
    readonly defaultResponseDraftTitle: string;
  };
}
