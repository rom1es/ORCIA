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
import type {
  UiAssistantErrorKind,
  UiThreeSpeedStepProgress,
} from "./AssistantSpeedSelectorTypes";
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
  readonly errorKind?: UiAssistantErrorKind | null;
  readonly reconnectCtaLabel?: string;
  readonly onReconnect?: () => void;
  readonly isStoppedVisible: boolean;
  readonly mergedRagCitations: readonly UiAssistantRagCitationItem[];
  readonly currentTurnFeedback: "LIKE" | "DISLIKE" | null;
  readonly onFeedbackLastTurn?: (feedback: "LIKE" | "DISLIKE" | null) => void;
  readonly canDeepen?: boolean;
  readonly lowEvidence?: boolean;
  readonly deepenLabel?: string;
  readonly deepenLowEvidenceLabel?: string;
  readonly onDeepen?: () => void;
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
  errorKind = null,
  reconnectCtaLabel,
  onReconnect,
  isStoppedVisible,
  mergedRagCitations,
  currentTurnFeedback,
  onFeedbackLastTurn,
  canDeepen = false,
  lowEvidence = false,
  deepenLabel,
  deepenLowEvidenceLabel,
  onDeepen,
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
          data-error-kind={errorKind ?? "stream_error"}
          className={
            errorKind === "auth_expired"
              ? "orcia-ds-alert orcia-ds-alert-error items-center justify-between gap-3"
              : "rounded border border-status-warning/40 bg-status-warning/10 p-2.5 text-xs font-medium text-status-warning"
          }
        >
          <div className={errorKind === "auth_expired" ? "orcia-ds-alert-content text-xs font-semibold" : undefined}>
            {errorMessage}
          </div>
          {errorKind === "auth_expired" && onReconnect ? (
            <button
              type="button"
              data-testid="assistant-error-reconnect-btn"
              onClick={onReconnect}
              className="orcia-ds-alert-action orcia-ds-btn orcia-ds-btn-primary orcia-ds-btn-sm"
            >
              {reconnectCtaLabel ?? "Se reconnecter →"}
            </button>
          ) : null}
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
              canDeepen={canDeepen}
              lowEvidence={lowEvidence}
              deepenLabel={deepenLabel}
              deepenLowEvidenceLabel={deepenLowEvidenceLabel}
              onDeepen={onDeepen}
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
