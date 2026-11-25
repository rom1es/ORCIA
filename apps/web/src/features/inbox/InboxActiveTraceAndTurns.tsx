import {
  AgentExecutionTrace,
  AssistantApprovalRequiredCard,
  AssistantToolCallTrace,
  OrciaAlertBanner,
  PermissionBrokerCard,
  SourceLineInspectorDrawer,
  type UiAgentTraceEventItem,
  type UiAssistantApprovalProposal,
  type UiAssistantToolCallStepItem,
  type UiReflexivePendingWritePreview,
  type UiReflexiveSessionStatus,
  type UiSourceLineInspectTarget,
} from "@orcia/ui";
import React from "react";
import type { TranslationDictionary } from "../../i18n/types";
import { buildAssistantCitationCardPreview } from "./inboxCitationHelpers";
import { InboxAuxiliaryPanels, type InboxAuxiliaryPanelsProps } from "./InboxAuxiliaryPanels";
import {
  ActiveConversationMessagesView,
  AssistantTopToolbar,
  SavedConversationsPanel,
} from "./SavedConversationsAndThreadView";
import type { SavedAssistantConversation, SavedConversationTurnItem } from "./savedConversationsStore";
import type { SendAssistantTurnPayload } from "./useAssistantStreamingTurn";
import type { usePermissionBrokerTickets } from "./usePermissionBrokerTickets";
import type { useSourceLineInspector } from "../shared/useSourceLineInspector";

export { buildAssistantCitationCardPreview };

export interface InboxTopSectionProps {
  readonly isFr: boolean;
  readonly governanceFeedback: string | null;
  readonly savedConversations: readonly SavedAssistantConversation[];
  readonly activeConversationId: string | null;
  readonly foldersCount: number;
  readonly savedConversationsOpen: boolean;
  readonly foldersPanelOpen: boolean;
  readonly dictionary: TranslationDictionary;
  readonly broker: ReturnType<typeof usePermissionBrokerTickets>;
  readonly onSelectActiveDiscussion?: () => void;
  readonly onNewConversation: () => void;
  readonly onToggleSavedConversations: () => void;
  readonly onToggleFoldersPanel: () => void;
  readonly onToggleGovernanceModal: () => void;
  readonly onOpenHelpSection: (sectionId: string) => void;
  readonly onResumeConversation: (convId: string) => void;
  readonly onDeleteConversation: (convId: string) => void;
}

export function InboxTopSection({
  isFr,
  governanceFeedback,
  savedConversations,
  activeConversationId,
  foldersCount,
  savedConversationsOpen,
  foldersPanelOpen,
  dictionary,
  broker,
  onSelectActiveDiscussion,
  onNewConversation,
  onToggleSavedConversations,
  onToggleFoldersPanel,
  onToggleGovernanceModal,
  onOpenHelpSection,
  onResumeConversation,
  onDeleteConversation,
}: InboxTopSectionProps): React.JSX.Element {
  const feedbackIsError = Boolean(
    governanceFeedback &&
      (/⚠️|❌/.test(governanceFeedback) ||
        /\b(erreur|error|failed|impossible|interdit|forbidden|refusé|denied)\b/i.test(governanceFeedback)),
  );
  const feedbackBanner = governanceFeedback ? (
    <OrciaAlertBanner
      tone={feedbackIsError ? "crimson" : "emerald"}
      role={feedbackIsError ? "alert" : "status"}
      testId="assistant-governance-feedback-banner"
    >
      {governanceFeedback}
    </OrciaAlertBanner>
  ) : null;

  return (
    <>
      <AssistantTopToolbar
        isFr={isFr}
        savedCount={savedConversations.length}
        foldersCount={foldersCount}
        savedConversationsOpen={savedConversationsOpen}
        foldersPanelOpen={foldersPanelOpen}
        governanceModalTitle={dictionary.assistantGovernance.modalTitle}
        alertSlot={feedbackBanner}
        onSelectActiveDiscussion={onSelectActiveDiscussion}
        onNewConversation={onNewConversation}
        onToggleSavedConversations={onToggleSavedConversations}
        onToggleFoldersPanel={onToggleFoldersPanel}
        onToggleGovernanceModal={onToggleGovernanceModal}
        onOpenHelpSection={onOpenHelpSection}
      />

      {broker.activeTicket ? (
        <PermissionBrokerCard
          ticket={broker.activeTicket}
          labels={dictionary.permissionBroker}
          onPauseStep={broker.pauseTicket}
          onReplayStep={broker.replayTicket}
        />
      ) : null}

      {savedConversationsOpen && (
        <SavedConversationsPanel
          conversations={savedConversations}
          activeConversationId={activeConversationId}
          isFr={isFr}
          onResumeConversation={onResumeConversation}
          onDeleteConversation={onDeleteConversation}
        />
      )}
    </>
  );
}

export function buildInboxStreamSlots(params: {
  readonly showActiveReflexiveSlot: boolean;
  readonly reflexiveStatus: UiReflexiveSessionStatus | null;
  readonly reflexiveEvents: readonly UiAgentTraceEventItem[];
  readonly toolCallSteps: readonly UiAssistantToolCallStepItem[];
  readonly approvalProposal: UiAssistantApprovalProposal | null;
  readonly approvalBusy: boolean;
  readonly pendingWritePreview: UiReflexivePendingWritePreview | null;
  readonly activeConversation: SavedAssistantConversation | null;
  readonly isFr: boolean;
  readonly isGenerating: boolean;
  readonly supportsTools: boolean;
  readonly dictionary: TranslationDictionary;
  readonly onInspectLines: (target: UiSourceLineInspectTarget) => void;
  readonly onInspectCitationUri: (uri: string, title?: string) => void;
  readonly onSynthesizeNow: () => void;
  readonly onApproveProposal: (proposalId: string, humanAnchorMarkdown?: string) => void;
  readonly onRejectProposal: (proposalId: string, rationale?: string) => void;
  readonly onOpenProcess: (runId?: string | null) => void;
  readonly onSendTurn: (payload: SendAssistantTurnPayload) => void;
  readonly onDeepenTurn: (turn: SavedConversationTurnItem) => void;
  readonly onContinueInProcess: () => void;
  readonly onFeedbackTurn: (turnId: string, feedback: "LIKE" | "DISLIKE" | null) => void;
}): {
  readonly activeReflexiveNode: React.ReactNode;
  readonly previousTurnsNode: React.ReactNode;
} {
  const hasActiveToolTrace = params.toolCallSteps.length > 0;
  const hasApproval = params.approvalProposal !== null;
  const hasTrace = params.showActiveReflexiveSlot && params.reflexiveStatus !== null;

  const activeReflexiveNode =
    hasTrace || hasActiveToolTrace || hasApproval ? (
      <div className="space-y-2.5">
        {hasActiveToolTrace && (
          <AssistantToolCallTrace
            steps={params.toolCallSteps}
            labels={params.dictionary.assistantToolTrace}
            onInspectLines={params.onInspectLines}
          />
        )}
        {hasApproval && params.approvalProposal && (
          <AssistantApprovalRequiredCard
            proposal={params.approvalProposal}
            labels={params.dictionary.assistantApprovalCard}
            busy={params.approvalBusy}
            onApprove={params.onApproveProposal}
            onReject={params.onRejectProposal}
            onOpenProcess={params.onOpenProcess}
          />
        )}
        {hasTrace && params.reflexiveStatus && (
          <AgentExecutionTrace
            status={params.reflexiveStatus}
            events={params.reflexiveEvents}
            pendingWritePreview={params.pendingWritePreview}
            labels={params.dictionary.executionTrace}
            defaultCollapsedWhenCompleted={false}
            onInspectLines={params.onInspectLines}
            onSynthesizeNow={params.onSynthesizeNow}
            onApproveWrite={(id) => params.onApproveProposal(id)}
            onRejectWrite={(id) => params.onRejectProposal(id)}
          />
        )}
      </div>
    ) : null;

  const previousTurnsNode =
    params.activeConversation && params.activeConversation.turns.length > 0 ? (
      <ActiveConversationMessagesView
        conversation={params.activeConversation}
        isFr={params.isFr}
        isGenerating={params.isGenerating}
        supportsTools={params.supportsTools}
        deepenLabel={params.dictionary.assistantSpeedStream.deepenCta}
        deepenLowEvidenceLabel={params.dictionary.assistantSpeedStream.deepenLowEvidenceCta}
        traceLabels={params.dictionary.executionTrace}
        toolTraceLabels={params.dictionary.assistantToolTrace}
        onInspectLines={params.onInspectLines}
        onInspectCitation={(src) => params.onInspectCitationUri(src.uri, src.title)}
        onSynthesizeNow={params.onSynthesizeNow}
        onApproveWrite={(id) => params.onApproveProposal(id)}
        onRejectWrite={(id) => params.onRejectProposal(id)}
        onRegenerateTurn={(userPrompt) =>
          params.onSendTurn({
            userPrompt,
            requestedSpeed: "SPEED_1_FAST",
            deepAuditPillActive: false,
          })
        }
        onDeepenTurn={params.onDeepenTurn}
        onContinueInProcess={params.onContinueInProcess}
        onFeedbackTurn={params.onFeedbackTurn}
      />
    ) : null;

  return { activeReflexiveNode, previousTurnsNode };
}

export function InboxBottomPanelsAndInspector({
  auxiliaryProps,
  inspector,
  labels,
}: {
  readonly auxiliaryProps: InboxAuxiliaryPanelsProps;
  readonly inspector: ReturnType<typeof useSourceLineInspector>;
  readonly labels: TranslationDictionary["sourceLineInspector"];
}): React.JSX.Element {
  return (
    <>
      <InboxAuxiliaryPanels {...auxiliaryProps} />
      <SourceLineInspectorDrawer
        open={inspector.inspectorState.open}
        onOpenChange={inspector.setInspectorOpen}
        resourceUri={inspector.inspectorState.resourceUri}
        displayFilename={inspector.inspectorState.displayFilename}
        fileBadgeCode={inspector.inspectorState.fileBadgeCode}
        startLine={inspector.inspectorState.startLine}
        endLine={inspector.inspectorState.endLine}
        totalLines={inspector.inspectorState.totalLines}
        lines={inspector.inspectorState.lines}
        isLoading={inspector.inspectorState.isLoading}
        redacted={inspector.inspectorState.redacted}
        redactedReason={inspector.inspectorState.redactedReason}
        permissionRequestHint={inspector.inspectorState.permissionRequestHint}
        errorMessage={inspector.inspectorState.errorMessage}
        copiedFeedback={inspector.inspectorState.copiedFeedback}
        labels={labels}
        onCopySlice={inspector.copyCurrentSlice}
      />
    </>
  );
}
