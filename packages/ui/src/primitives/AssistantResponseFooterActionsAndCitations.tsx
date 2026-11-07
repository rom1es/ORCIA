import React, { useEffect, useState } from "react";

export interface UiAssistantRagCitationItem {
  readonly title: string;
  readonly uri: string;
  readonly snippet?: string | null;
}

export interface AssistantUserQuestionBubbleProps {
  readonly userPrompt: string;
  readonly isFr?: boolean;
  readonly modelLabel?: string;
  readonly effortLabel?: string;
  readonly testId?: string;
}

export function AssistantUserQuestionBubble({
  userPrompt,
  isFr = true,
  modelLabel,
  effortLabel,
  testId = "assistant-user-question-bubble",
}: AssistantUserQuestionBubbleProps): React.JSX.Element {
  return (
    <div className="flex flex-col items-end space-y-1">
      <div className="flex items-center gap-2 text-[11px] text-text-secondary">
        {modelLabel ? (
          <span>
            {modelLabel}
            {effortLabel ? ` · ${effortLabel}` : ""}
          </span>
        ) : null}
        <span className="font-semibold text-text-primary">
          🧑 {isFr ? "Vous" : "You"}
        </span>
      </div>
      <div
        data-testid={testId}
        style={{
          marginLeft: "auto",
          maxWidth: "75%",
          borderRadius: "18px 18px 4px 18px",
          backgroundColor: "var(--color-action-primary)",
          color: "var(--color-primary-foreground)",
          padding: "10px 16px",
          fontWeight: 500,
        }}
        className="text-xs leading-relaxed whitespace-pre-wrap shadow-sm"
      >
        {userPrompt}
      </div>
    </div>
  );
}

export interface AssistantThinkingSliderIndicatorProps {
  readonly isFr?: boolean;
}

export function AssistantThinkingSliderIndicator({
  isFr = true,
}: AssistantThinkingSliderIndicatorProps): React.JSX.Element {
  return (
    <div
      data-testid="assistant-thinking-slider-indicator"
      role="status"
      aria-live="polite"
      className="rounded-lg border border-border-subtle bg-surface-primary px-3.5 py-2.5 text-xs space-y-2"
    >
      <div className="flex items-center justify-between gap-2">
        <span className="inline-flex items-center gap-2 font-medium text-text-primary">
          <span
            data-testid="assistant-thinking-pulsing-dots"
            aria-hidden="true"
            style={{
              color: "var(--color-action-primary)",
              letterSpacing: "2px",
              fontWeight: 700,
            }}
          >
            •••
          </span>
          <span>
            {isFr
              ? "Mon Assistant prépare votre réponse..."
              : "My Assistant is preparing your answer..."}
          </span>
        </span>
      </div>
      <div
        className="h-1.5 w-full overflow-hidden rounded-full bg-surface-secondary"
        aria-hidden="true"
      >
        <div
          data-testid="assistant-thinking-progress-bar"
          className="h-full rounded-full animate-pulse"
          style={{
            width: "65%",
            backgroundColor: "var(--color-action-primary)",
          }}
        />
      </div>
    </div>
  );
}

export interface AssistantResponseFooterActionsAndCitationsProps {
  readonly responseText: string;
  readonly isFr?: boolean;
  readonly ragCitations?: readonly UiAssistantRagCitationItem[];
  readonly onRegenerate?: () => void;
  readonly onSaveDraft?: (content: string) => void;
  readonly onContinueInProcess?: (content: string) => void;
  readonly onFeedbackChange?: (feedback: "LIKE" | "DISLIKE" | null) => void;
}

export function AssistantResponseFooterActionsAndCitations({
  responseText,
  isFr = true,
  ragCitations = [],
  onRegenerate,
  onSaveDraft,
  onContinueInProcess,
  onFeedbackChange,
}: AssistantResponseFooterActionsAndCitationsProps): React.JSX.Element {
  const [feedback, setFeedback] = useState<"LIKE" | "DISLIKE" | null>(null);
  const [copied, setCopied] = useState<boolean>(false);
  const [draftSaved, setDraftSaved] = useState<boolean>(false);

  useEffect(() => {
    if (!copied) {
      return;
    }
    const timer = setTimeout(() => setCopied(false), 2000);
    return () => clearTimeout(timer);
  }, [copied]);

  const handleToggleLike = () => {
    const next = feedback === "LIKE" ? null : "LIKE";
    setFeedback(next);
    onFeedbackChange?.(next);
  };

  const handleToggleDislike = () => {
    const next = feedback === "DISLIKE" ? null : "DISLIKE";
    setFeedback(next);
    onFeedbackChange?.(next);
  };

  const handleCopy = () => {
    setCopied(true);
    if (
      typeof navigator !== "undefined" &&
      navigator.clipboard &&
      typeof navigator.clipboard.writeText === "function"
    ) {
      void navigator.clipboard.writeText(responseText).catch(() => {
        // Clipboard API may be restricted in non-HTTPS or test environments
      });
    }
  };

  const handleSaveDraft = () => {
    setDraftSaved(true);
    onSaveDraft?.(responseText);
  };

  return (
    <div className="space-y-2.5 pt-2 border-t border-border-subtle">
      {ragCitations.length > 0 && (
        <div
          data-testid="assistant-rag-citations-list"
          className="flex flex-wrap items-center gap-1.5"
        >
          <span className="text-[11px] font-medium text-text-secondary">
            {isFr ? "Sources consultées :" : "Consulted sources:"}
          </span>
          {ragCitations.map((source, index) => (
            <a
              key={`${source.uri}-${index}`}
              href={source.uri}
              target="_blank"
              rel="noopener noreferrer"
              data-testid={`assistant-rag-citation-link-${index}`}
              className="inline-flex items-center gap-1 rounded-full border border-border-subtle bg-surface-secondary px-2.5 py-0.5 text-[11px] font-medium text-action-primary hover:underline"
            >
              📄 {source.title} ↗
            </a>
          ))}
        </div>
      )}

      <div
        data-testid="assistant-response-actions-bar"
        role="toolbar"
        aria-label={isFr ? "Actions sur la réponse" : "Response actions"}
        className="flex flex-wrap items-center gap-1.5 text-[11px]"
      >
        <button
          type="button"
          data-testid="assistant-action-like-btn"
          aria-pressed={feedback === "LIKE"}
          onClick={handleToggleLike}
          style={
            feedback === "LIKE"
              ? {
                  backgroundColor: "var(--color-action-primary)",
                  color: "var(--color-primary-foreground)",
                  borderColor: "var(--color-action-primary)",
                }
              : undefined
          }
          className="inline-flex items-center gap-1 rounded-md border border-border-subtle bg-surface-secondary px-2.5 py-1 font-medium text-text-primary hover:bg-surface-elevated"
        >
          👍 {isFr ? "J'aime" : "Like"}
        </button>

        <button
          type="button"
          data-testid="assistant-action-dislike-btn"
          aria-pressed={feedback === "DISLIKE"}
          onClick={handleToggleDislike}
          style={
            feedback === "DISLIKE"
              ? {
                  backgroundColor: "var(--color-action-primary)",
                  color: "var(--color-primary-foreground)",
                  borderColor: "var(--color-action-primary)",
                }
              : undefined
          }
          className="inline-flex items-center gap-1 rounded-md border border-border-subtle bg-surface-secondary px-2.5 py-1 font-medium text-text-primary hover:bg-surface-elevated"
        >
          👎 {isFr ? "Je n'aime pas" : "Dislike"}
        </button>

        <button
          type="button"
          data-testid="assistant-action-copy-btn"
          onClick={handleCopy}
          className="inline-flex items-center gap-1 rounded-md border border-border-subtle bg-surface-secondary px-2.5 py-1 font-medium text-text-primary hover:bg-surface-elevated"
        >
          {copied
            ? isFr
              ? "✓ Copié"
              : "✓ Copied"
            : isFr
              ? "📋 Copier"
              : "📋 Copy"}
        </button>

        <button
          type="button"
          data-testid="assistant-action-regenerate-btn"
          onClick={() => onRegenerate?.()}
          className="inline-flex items-center gap-1 rounded-md border border-border-subtle bg-surface-secondary px-2.5 py-1 font-medium text-text-primary hover:bg-surface-elevated"
        >
          🔄 {isFr ? "Régénérer" : "Regenerate"}
        </button>

        <button
          type="button"
          data-testid="assistant-action-save-draft-btn"
          onClick={handleSaveDraft}
          className="inline-flex items-center gap-1 rounded-md border border-border-subtle bg-surface-secondary px-2.5 py-1 font-medium text-text-primary hover:bg-surface-elevated"
        >
          {draftSaved
            ? isFr
              ? "✓ Brouillon enregistré"
              : "✓ Draft saved"
            : isFr
              ? "📄 Enregistrer en brouillon"
              : "📄 Save as draft"}
        </button>

        <button
          type="button"
          data-testid="assistant-action-continue-process-btn"
          onClick={() => onContinueInProcess?.(responseText)}
          className="inline-flex items-center gap-1 rounded-md border border-border-subtle bg-surface-secondary px-2.5 py-1 font-medium text-action-primary hover:bg-surface-elevated"
        >
          ☍ {isFr ? "Poursuivre dans un Processus" : "Continue in a Process"}
        </button>
      </div>
    </div>
  );
}
