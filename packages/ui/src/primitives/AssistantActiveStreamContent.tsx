import React from "react";
import { FormattedMarkdownContent } from "../components/FormattedMarkdownContent";
import { getOrciaIconGlyph, OrciaIcon } from "../components/icons";
import type { UiAssistantAttachedFileItem } from "./AssistantPromptPlusAndAutocomplete";
import {
  AssistantResponseFooterActionsAndCitations,
  AssistantThinkingSliderIndicator,
  AssistantUserQuestionBubble,
  type UiAssistantRagCitationItem,
} from "./AssistantResponseFooterActionsAndCitations";
import type { UiThreeSpeedStepProgress } from "./AssistantSpeedSelectorAndStreamView";
import { AssistantThinkingSubWindow } from "./AssistantThinkingSubWindow";

export interface AssistantActiveStreamContentProps {
  readonly previousTurnsSlot: React.ReactNode;
  readonly reflexiveTraceSlot?: React.ReactNode;
  readonly shownUserQuestion: string;
  readonly hideDuplicateCompletedStream: boolean;
  readonly isGenerating: boolean;
  readonly displayModelBadge: string;
  readonly effortTitle: string;
  readonly lastSubmittedFiles: readonly UiAssistantAttachedFileItem[];
  readonly cleanStreamedText: string;
  readonly stepProgress: readonly UiThreeSpeedStepProgress[];
  readonly initialElapsedSeconds: number;
  readonly errorMessage: string | null;
  readonly isStoppedVisible: boolean;
  readonly mergedRagCitations: readonly UiAssistantRagCitationItem[];
  readonly currentTurnFeedback: "LIKE" | "DISLIKE" | null;
  readonly onFeedbackLastTurn?: (feedback: "LIKE" | "DISLIKE" | null) => void;
  readonly onRegenerate: () => void;
  readonly onSaveDraftFromResponse?: (content: string) => void;
  readonly onContinueInProcessFromResponse?: (content: string) => void;
  readonly onInspectCitation?: (source: UiAssistantRagCitationItem, index: number) => void;
}

export function AssistantActiveStreamContent({
  previousTurnsSlot,
  reflexiveTraceSlot = null,
  shownUserQuestion,
  hideDuplicateCompletedStream,
  isGenerating,
  displayModelBadge,
  effortTitle,
  lastSubmittedFiles,
  cleanStreamedText,
  stepProgress,
  initialElapsedSeconds,
  errorMessage,
  isStoppedVisible,
  mergedRagCitations,
  currentTurnFeedback,
  onFeedbackLastTurn,
  onRegenerate,
  onSaveDraftFromResponse,
  onContinueInProcessFromResponse,
  onInspectCitation,
}: AssistantActiveStreamContentProps): React.JSX.Element {
  return (
    <>
      {previousTurnsSlot}
      {shownUserQuestion && (!hideDuplicateCompletedStream || isGenerating) ? (
        <AssistantUserQuestionBubble
          userPrompt={shownUserQuestion}
          modelLabel={displayModelBadge}
          effortLabel={effortTitle}
          attachedFiles={lastSubmittedFiles}
        />
      ) : null}
      {isGenerating && !cleanStreamedText && !reflexiveTraceSlot ? (
        <div className="py-2 my-1">
          <AssistantThinkingSliderIndicator />
        </div>
      ) : null}
      {reflexiveTraceSlot ? (
        <div
          data-testid="assistant-active-research-zone"
          className="py-1 flex flex-col items-stretch justify-center gap-2"
        >
          {reflexiveTraceSlot}
        </div>
      ) : !hideDuplicateCompletedStream ? (
        <div
          data-testid="assistant-active-research-zone"
          className="py-1 flex flex-col items-start justify-center gap-2"
        >
          <AssistantThinkingSubWindow
            stepProgress={stepProgress}
            isGenerating={isGenerating}
            initialElapsedSeconds={initialElapsedSeconds}
            hasStreamedResponse={Boolean(
              cleanStreamedText && !cleanStreamedText.startsWith(getOrciaIconGlyph("hourglass")),
            )}
          />
        </div>
      ) : null}
      {errorMessage && (
        <div
          role="alert"
          data-testid="assistant-error-banner"
          className="rounded border border-status-warning/40 bg-status-warning/10 p-2.5 text-xs font-medium text-status-warning"
        >
          {errorMessage}
        </div>
      )}
      {(cleanStreamedText || isStoppedVisible) && (
        <div
          data-testid="assistant-streamed-response-box"
          aria-live="polite"
          style={hideDuplicateCompletedStream && !isStoppedVisible ? { display: "none" } : undefined}
          className={
            hideDuplicateCompletedStream && !isStoppedVisible
              ? "sr-only"
              : "rounded-lg bg-surface-primary py-2 text-xs leading-relaxed space-y-2"
          }
        >
          {cleanStreamedText ? <FormattedMarkdownContent content={cleanStreamedText} /> : null}
          {isStoppedVisible ? (
            <div
              data-testid="assistant-generation-stopped-badge"
              className="inline-flex items-center gap-1.5 rounded border border-border-subtle bg-surface-secondary px-2.5 py-1 text-[11px] font-medium text-text-secondary"
            >
              <OrciaIcon name="stopButton" /> Génération interrompue par l&apos;utilisateur
            </div>
          ) : null}
          {!isGenerating && cleanStreamedText && !hideDuplicateCompletedStream ? (
            <AssistantResponseFooterActionsAndCitations
              responseText={cleanStreamedText}
              modelLabel={displayModelBadge}
              effortLabel={effortTitle}
              ragCitations={mergedRagCitations}
              initialFeedback={currentTurnFeedback}
              onFeedbackChange={onFeedbackLastTurn}
              onRegenerate={onRegenerate}
              onSaveDraft={onSaveDraftFromResponse}
              onContinueInProcess={onContinueInProcessFromResponse}
              onInspectCitation={onInspectCitation}
            />
          ) : null}
        </div>
      )}
    </>
  );
}
