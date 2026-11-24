import type { AssistantDictionarySection } from "./assistant_labels";
import {
  ASSISTANT_GOVERNANCE_LABELS_EN,
  ASSISTANT_SPEED_STREAM_LABELS_EN,
} from "./assistant_stream_labels_en";

export const ASSISTANT_EN_LABELS: AssistantDictionarySection = {
  assistantGovernance: ASSISTANT_GOVERNANCE_LABELS_EN,
  assistantSpeedStream: ASSISTANT_SPEED_STREAM_LABELS_EN,
  assistantCitations: {
    freshnessFreshBadge: "✅ Source up to date",
    freshnessStaleBadge: "⚠️ Source needs review",
    restrictedSourcePillSuffix: "🔒 Restricted access",
    requestAccessCta: "Request access",
    unverifiedCitationBadge: "Reference to confirm",
    artifactCardTitlePrefix: "📄 Document Draft",
    linesLabel: "Lines",
    draftBadgeLabel: "@draft",
    copyArtifactCta: "📋 Copy",
    exportArtifactCta: "⬇ Download (.md)",
    saveDraftCta: "💾 Save draft",
    continueInProcessCta: "☍ Continue in a reviewed Process →",
    v5LockNoticeText:
      "🔒 To ensure quality, publishing to shared tools always goes through a review step.",
  },
  assistantFoldersSync: {
    workspaceRequired: "⚠️ Create or select a Workspace first to save your folders.",
    loadFailed: (detail: string) => `⚠️ Unable to load your folders (${detail}).`,
    saveFailed: (detail: string) => `⚠️ The folder could not be saved (${detail}).`,
  },
  assistantFolders: {
    tab1ActiveDiscussionTitle: "💬 Active discussion",
    tab2FoldersTitlePrefix: "📁 Folders",
    tab3HistorySearchTitle: "🕘 History & Search",
    activeFolderPillPrefix: "📁 Active folder:",
    pinnedNotesButtonLabel: "📌 Pinned notes",
    launchProcessFromFolderCta: "☍ Start a Process from this folder →",
    shareButtonLabel: "👥 Share / Visibility",
    visibilityPrivateLabel: "🔒 Private (Only me)",
    visibilitySharedSelectedLabel: "👥 Shared (Selected members)",
    visibilityWorkspaceOpenLabel: "📦 Visible to entire Space",
    restrictedSourcesWarningText:
      "⚠️ This folder cites protected sources: each reader will only see excerpts their account is authorized to view.",
    searchPlaceholder: "Search across your discussions, folders, and drafts...",
    clearActiveFolderCta: "Clear active folder",
    noActiveFolderHint:
      "No active folder selected. Create or click a folder below to activate its notes.",
    permanentNotesTitleTemplate:
      'Permanent notes for folder "{title}" (injected into every question)',
    notesSavedBadgeLabel: "Notes saved and active",
    notesTextareaPlaceholder:
      "E.g.: Always include structured examples and follow the domain glossary...",
    notesEnrichHint: "Saved notes automatically enrich your questions in this folder.",
    saveNotesCta: "Save notes",
    newFolderTitlePlaceholder: "New thematic folder title...",
    defaultNewFolderTitlePrefix: "Thematic folder #",
    newFolderCta: "+ New folder",
    activeAccountPrefix: "Active account:",
    collaborativeSendCta: "Send",
  },
  assistantNoEmbeddingModel: {
    bannerTitle: "Direct dialogue active · Document search inactive",
    bannerDescription:
      "Direct dialogue and glossary are active. Document semantic search requires an active indexing model.",
    configureCta: "Configure in AI Models →",
  },
  assistantNoChatModel: {
    bannerTitle: "Chat AI model required",
    bannerDescription:
      "No active chat AI model is configured on the platform. Configure at least one chat model to use My Assistant.",
    configureCta: "Configure an AI model →",
  },
  assistantRagNotice: {
    noEmbeddingTitle: "Direct dialogue & glossary active · Document search inactive",
    noEmbeddingDescription:
      "No semantic indexing model is configured. You can chat normally with My Assistant; searching workspace documents requires an embedding model.",
    configureEmbeddingCta: "Configure in Administration › AI Models →",
    reindexingTitle: "Direct dialogue & glossary active · Document reindexing in progress",
    reindexingDescription:
      "The document corpus is undergoing semantic reindexing. Direct chat remains active; document search will resume automatically once finished.",
    reindexFailedTitle: "Direct dialogue active · Document reindexing interrupted",
    reindexFailedDescription:
      "Semantic reindexing of the document corpus failed. Direct dialogue with My Assistant remains available.",
    relaunchReindexCta: "Relaunch reindexing",
    checkEmbeddingCta: "Check embedding model →",
  },
  assistantStreamErrors: {
    sessionExpiredMessage:
      "Your session has expired or needs to be renewed to continue the conversation.",
    reconnectCta: "Log in again →",
    aiUnavailableMessage: (detail?: string) =>
      detail
        ? `⚠️ Could not get a response from My Assistant (${detail}). Please check that your configured AI model is running.`
        : "⚠️ The AI service is temporarily unavailable. Please check that your configured AI model is running.",
  },
  assistantToolTrace: {
    heading: "Workspace tool activity",
    runningLabel: "Running",
    executedLabel: "Completed",
    deniedLabel: "Blocked",
    errorLabel: "Error",
    approvalRequiredLabel: "Approval required",
    inspectLinesLabel: "Inspect lines",
    durationSuffix: "ms",
  },
  assistantApprovalCard: {
    heading: "Human validation required before applying changes",
    targetLabel: "Target",
    workflowLabel: "Process",
    humanAnchorLabel: "Your validation rationale (required)",
    humanAnchorPlaceholder: "Describe why you approve this action...",
    humanAnchorRequiredError: "Please enter a brief rationale before approving this action.",
    approveCta: "Approve and continue",
    rejectCta: "Reject",
    approvedStatusLabel: "Approved — resumed in process",
    rejectedStatusLabel: "Rejected",
    openProcessCta: "Open process run →",
  },
};
