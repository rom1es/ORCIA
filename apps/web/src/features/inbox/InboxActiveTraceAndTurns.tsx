import {
  AgentExecutionTrace,
  PermissionBrokerCard,
  SourceLineInspectorDrawer,
  type UiAgentTraceEventItem,
  type UiAssistantRagCitationItem,
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
import type { SavedAssistantConversation } from "./savedConversationsStore";
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
  onNewConversation,
  onToggleSavedConversations,
  onToggleFoldersPanel,
  onToggleGovernanceModal,
  onOpenHelpSection,
  onResumeConversation,
  onDeleteConversation,
}: InboxTopSectionProps): React.JSX.Element {
  return (
    <>
      {governanceFeedback ? (
        <div
          role="status"
          data-testid="assistant-governance-feedback-banner"
          className="rounded border px-3 py-2 text-xs font-medium"
          style={{
            backgroundColor: "var(--color-bg-elevated)",
            borderColor: "var(--color-border-subtle)",
            color: "var(--color-text-primary)",
          }}
        >
          {governanceFeedback}
        </div>
      ) : null}

      <AssistantTopToolbar
        isFr={isFr}
        savedCount={savedConversations.length}
        foldersCount={foldersCount}
        savedConversationsOpen={savedConversationsOpen}
        foldersPanelOpen={foldersPanelOpen}
        governanceModalTitle={dictionary.assistantGovernance.modalTitle}
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
  readonly pendingWritePreview: UiReflexivePendingWritePreview | null;
  readonly activeConversation: SavedAssistantConversation | null;
  readonly isFr: boolean;
  readonly isGenerating: boolean;
  readonly ragCitations: readonly UiAssistantRagCitationItem[];
  readonly traceLabels: TranslationDictionary["executionTrace"];
  readonly onInspectLines: (target: UiSourceLineInspectTarget) => void;
  readonly onInspectCitationUri: (uri: string, title?: string) => void;
  readonly onSynthesizeNow: () => void;
  readonly onApproveWrite: (previewId: string) => void;
  readonly onRejectWrite: (previewId: string) => void;
  readonly onSendTurn: (payload: SendAssistantTurnPayload) => void;
  readonly onContinueInProcess: () => void;
  readonly onFeedbackTurn: (turnId: string, feedback: "LIKE" | "DISLIKE" | null) => void;
}): {
  readonly activeReflexiveNode: React.ReactNode;
  readonly previousTurnsNode: React.ReactNode;
} {
  const activeReflexiveNode =
    params.showActiveReflexiveSlot && params.reflexiveStatus ? (
      <AgentExecutionTrace
        status={params.reflexiveStatus}
        events={params.reflexiveEvents}
        pendingWritePreview={params.pendingWritePreview}
        labels={params.traceLabels}
        defaultCollapsedWhenCompleted={false}
        onInspectLines={params.onInspectLines}
        onSynthesizeNow={params.onSynthesizeNow}
        onApproveWrite={params.onApproveWrite}
        onRejectWrite={params.onRejectWrite}
      />
    ) : null;

  const previousTurnsNode =
    params.activeConversation && params.activeConversation.turns.length > 0 ? (
      <ActiveConversationMessagesView
        conversation={params.activeConversation}
        isFr={params.isFr}
        isGenerating={params.isGenerating}
        ragCitations={params.ragCitations}
        traceLabels={params.traceLabels}
        onInspectLines={params.onInspectLines}
        onInspectCitation={(src) => params.onInspectCitationUri(src.uri, src.title)}
        onSynthesizeNow={params.onSynthesizeNow}
        onApproveWrite={params.onApproveWrite}
        onRejectWrite={params.onRejectWrite}
        onRegenerateTurn={(userPrompt) =>
          params.onSendTurn({
            userPrompt,
            requestedSpeed: "SPEED_1_FAST",
            deepAuditPillActive: false,
          })
        }
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
