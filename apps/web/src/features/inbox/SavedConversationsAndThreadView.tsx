import {
  AgentExecutionTrace,
  AssistantResponseFooterActionsAndCitations,
  AssistantThinkingSubWindow,
  AssistantToolCallTrace,
  AssistantUserQuestionBubble,
  FormattedMarkdownContent,
  OrciaDataCard,
  OrciaIcon,
  sanitizeAssistantDisplayReply,
  type AgentExecutionTraceLabels,
  type AssistantToolCallTraceLabels,
  type UiAssistantRagCitationItem,
  type UiSourceLineInspectTarget,
} from "@orcia/ui";
import React from "react";
import { formatI18nTemplate, useI18n } from "../../i18n";
import type { SavedAssistantConversation, SavedConversationTurnItem } from "./savedConversationsStore";

export { AssistantTopToolbar, type AssistantTopToolbarProps } from "./AssistantTopToolbar";

export interface SavedConversationsPanelProps {
  readonly conversations: readonly SavedAssistantConversation[];
  readonly activeConversationId: string | null;
  readonly isFr: boolean;
  readonly onResumeConversation: (conversationId: string) => void;
  readonly onDeleteConversation: (conversationId: string) => void;
}

export function SavedConversationsPanel({
  conversations,
  activeConversationId,
  onResumeConversation,
  onDeleteConversation,
}: SavedConversationsPanelProps): React.JSX.Element {
  const { dictionary } = useI18n();
  const savedCopy = dictionary.featureInboxAssistant.savedConversations;

  return (
    <OrciaDataCard
      testId="assistant-saved-conversations-panel"
      icon="clock"
      title={
        conversations.length > 0
          ? formatI18nTemplate(savedCopy.panelTitleCountTemplate, { count: conversations.length })
          : savedCopy.panelTitle
      }
    >
      {conversations.length === 0 ? (
        <p data-testid="assistant-saved-conversations-empty" className="text-xs text-text-secondary">
          {savedCopy.emptyText}
        </p>
      ) : (
        <ul className="space-y-1.5" data-testid="assistant-saved-conversations-list">
          {conversations.map((conv) => {
            const isCurrent = conv.id === activeConversationId;
            return (
              <li
                key={conv.id}
                data-testid={`assistant-saved-conversation-item-${conv.id}`}
                className={`flex flex-wrap items-center justify-between gap-2 rounded-lg border px-3 py-2 text-xs ${
                  isCurrent
                    ? "border-action-primary bg-action-primary/10"
                    : "border-border-subtle bg-surface-primary"
                }`}
              >
                <button
                  type="button"
                  data-testid={`assistant-resume-conversation-${conv.id}`}
                  onClick={() => onResumeConversation(conv.id)}
                  className="flex-1 text-left"
                >
                  <div className="font-semibold text-text-primary">{conv.title}</div>
                  <div className="text-[11px] text-text-secondary">
                    {conv.turns.length}{" "}
                    {conv.turns.length > 1 ? savedCopy.turnPlural : savedCopy.turnSingular} ·{" "}
                    {conv.modelLabel}
                  </div>
                </button>
                <button
                  type="button"
                  data-testid={`assistant-delete-conversation-${conv.id}`}
                  onClick={() => onDeleteConversation(conv.id)}
                  className="rounded border border-border-subtle bg-surface-secondary px-2 py-0.5 text-[11px] text-text-secondary hover:text-text-primary"
                >
                  {savedCopy.deleteBtn}
                </button>
              </li>
            );
          })}
        </ul>
      )}
    </OrciaDataCard>
  );
}

export interface ActiveConversationMessagesViewProps {
  readonly conversation: SavedAssistantConversation;
  readonly isFr: boolean;
  readonly isGenerating?: boolean;
  readonly supportsTools?: boolean;
  readonly deepenLabel?: string;
  readonly deepenLowEvidenceLabel?: string;
  readonly traceLabels: AgentExecutionTraceLabels;
  readonly toolTraceLabels?: AssistantToolCallTraceLabels;
  readonly onInspectLines: (target: UiSourceLineInspectTarget) => void;
  readonly onInspectCitation: (source: UiAssistantRagCitationItem, index: number) => void;
  readonly onSynthesizeNow: () => void;
  readonly onApproveWrite: (previewId: string) => void;
  readonly onRejectWrite: (previewId: string) => void;
  readonly onRegenerateTurn?: (userPrompt: string) => void;
  readonly onDeepenTurn?: (turn: SavedConversationTurnItem) => void;
  readonly onSaveDraft?: (content: string) => void;
  readonly onContinueInProcess?: (content: string) => void;
  readonly onFeedbackTurn?: (turnId: string, feedback: "LIKE" | "DISLIKE" | null) => void;
}

export function ActiveConversationMessagesView({
  conversation,
  isFr,
  isGenerating = false,
  supportsTools = true,
  deepenLabel,
  deepenLowEvidenceLabel,
  traceLabels,
  toolTraceLabels,
  onInspectLines,
  onInspectCitation,
  onSynthesizeNow,
  onApproveWrite,
  onRejectWrite,
  onRegenerateTurn,
  onDeepenTurn,
  onSaveDraft,
  onContinueInProcess,
  onFeedbackTurn,
}: ActiveConversationMessagesViewProps): React.JSX.Element | null {
  const { dictionary } = useI18n();
  if (conversation.turns.length === 0) {
    return null;
  }

  return (
    <section data-testid="assistant-conversation-messages-list" className="space-y-4">
      {conversation.turns.map((turn, idx) => {
        const cleanReply = sanitizeAssistantDisplayReply(turn.assistantReply);
        const turnCitations = turn.usedSources ?? [];
        const turnSteps = turn.stepProgress ?? [];
        const turnSeconds = turn.thinkingElapsedSeconds ?? (turnSteps.length > 0 ? 3 : 1);
        const isLastSavedTurn = idx === conversation.turns.length - 1;
        const hasReflexiveTrace = Boolean(turn.reflexiveTraceEvents && turn.reflexiveTraceEvents.length > 0);
        const hasToolTrace = Boolean(turn.toolCallSteps && turn.toolCallSteps.length > 0 && toolTraceLabels);
        return (
          <div
            key={turn.turnId}
            data-testid={`assistant-conversation-turn-${idx + 1}`}
            data-parent-turn-id={turn.parentTurnId ?? undefined}
            className="space-y-2.5 text-xs"
          >
            <AssistantUserQuestionBubble
              userPrompt={turn.userPrompt}
              isFr={isFr}
              modelLabel={turn.modelLabel}
              effortLabel={turn.effortLabel}
              {...(turn.attachedFiles ? { attachedFiles: turn.attachedFiles } : {})}
              testId={
                isLastSavedTurn && !isGenerating
                  ? "assistant-user-question-bubble"
                  : `assistant-user-question-bubble-${idx + 1}`
              }
            />

            <div className="pt-1 space-y-2">
              {hasToolTrace && toolTraceLabels && (
                <AssistantToolCallTrace
                  steps={turn.toolCallSteps!}
                  labels={toolTraceLabels}
                  onInspectLines={onInspectLines}
                />
              )}
              {hasReflexiveTrace ? (
                <AgentExecutionTrace
                  status="COMPLETED"
                  events={turn.reflexiveTraceEvents!}
                  pendingWritePreview={null}
                  labels={traceLabels}
                  defaultCollapsedWhenCompleted={true}
                  onInspectLines={onInspectLines}
                  onSynthesizeNow={onSynthesizeNow}
                  onApproveWrite={onApproveWrite}
                  onRejectWrite={onRejectWrite}
                />
              ) : (
                <AssistantThinkingSubWindow
                  stepProgress={turnSteps}
                  isGenerating={false}
                  hasStreamedResponse={true}
                  elapsedSecondsOverride={turnSeconds}
                />
              )}
              <FormattedMarkdownContent content={cleanReply} testId={`assistant-turn-markdown-${idx + 1}`} />
              {isLastSavedTurn && !isGenerating && (
                <AssistantResponseFooterActionsAndCitations
                  responseText={cleanReply}
                  labels={dictionary.assistantSpeedStream.responseFooter}
                  modelLabel={turn.modelLabel}
                  effortLabel={turn.effortLabel}
                  ragCitations={turnCitations}
                  initialFeedback={turn.userFeedback ?? null}
                  canDeepen={Boolean(supportsTools && onDeepenTurn)}
                  lowEvidence={Boolean(turn.lowEvidence)}
                  {...(deepenLabel ? { deepenLabel } : {})}
                  {...(deepenLowEvidenceLabel ? { deepenLowEvidenceLabel } : {})}
                  onDeepen={onDeepenTurn ? () => onDeepenTurn(turn) : undefined}
                  onFeedbackChange={(fb) => onFeedbackTurn?.(turn.turnId, fb)}
                  onRegenerate={() => onRegenerateTurn?.(turn.userPrompt)}
                  onSaveDraft={onSaveDraft}
                  onContinueInProcess={onContinueInProcess}
                  onInspectCitation={onInspectCitation}
                />
              )}
            </div>
          </div>
        );
      })}
    </section>
  );
}
