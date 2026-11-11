import React, { useEffect, useState } from "react";
import { OrciaIcon } from "../components/icons";
import type { UiAssistantAttachedFileItem } from "./AssistantPromptPlusAndAutocomplete";

export interface UiAssistantRagCitationItem {
  readonly title: string;
  readonly uri: string;
  readonly snippet?: string | null;
}

export function sanitizeAssistantDisplayReply(rawText: string): string {
  if (!rawText) {
    return "";
  }
  let cleaned = rawText.replace(
    /^\s*\[(?:⚡|🛠️|🧠)\s*Vitesse\s*\d[^\]]*\]\s*/i,
    "",
  );
  cleaned = cleaned.replace(
    /Réponse directe générée avec prompt 5 couches \((?:HIT|MISS) Redis\)\s*:\s*/gi,
    "",
  );
  cleaned = cleaned.replace(
    /\s*\(rôle(?:\s+actif)?\s*:\s*PLATFORM_ADMIN\)/gi,
    "",
  );
  cleaned = cleaned.replace(/\bPLATFORM_ADMIN\b/g, "Administrateur");
  cleaned = cleaned.replace(
    /\s*«\s*([^»]+)\s*»\s*(?:\[(?:S\d+|G\d+|O\d+)\]\s*)+(\.?)$/i,
    (_, inner: string, dot: string) => ` « ${inner.trim()} »${dot || "."}`,
  );
  cleaned = cleaned.replace(
    /(?:\s*\[(?:S\d+|G\d+|O\d+)\])+(\.?)\s*$/g,
    (_, trailingDot: string) => (trailingDot ? "." : ""),
  );
  return cleaned.trim();
}

export interface AssistantUserQuestionBubbleProps {
  readonly userPrompt: string;
  readonly isFr?: boolean;
  readonly modelLabel?: string;
  readonly effortLabel?: string;
  readonly attachedFiles?: readonly UiAssistantAttachedFileItem[];
  readonly testId?: string;
}

export function AssistantUserQuestionBubble({
  userPrompt,
  attachedFiles = [],
  testId = "assistant-user-question-bubble",
}: AssistantUserQuestionBubbleProps): React.JSX.Element {
  return (
    <div className="flex flex-col items-end space-y-1">
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
      {attachedFiles.length > 0 && (
        <div
          data-testid="assistant-user-question-attached-files"
          className="flex flex-wrap justify-end gap-1.5 pt-0.5"
        >
          {attachedFiles.map((file) => (
            <span
              key={file.id}
              data-testid="assistant-user-question-attached-pill"
              className="inline-flex items-center gap-1 rounded-md bg-surface-secondary px-2 py-0.5 text-[11px] font-medium text-text-secondary"
            >
              <OrciaIcon name={file.sourceKind === "LOCAL_PC" ? "laptop" : "workspaceFolder"} />
              <span>{file.name}</span>
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

const THINKING_DOT_BASE_STYLE: React.CSSProperties = {
  display: "inline-block",
  width: "6px",
  height: "6px",
  borderRadius: "9999px",
  backgroundColor: "var(--color-action-primary)",
  animation: "orciaThinkingBounce 1.1s infinite ease-in-out",
};

export function ThinkingDots({
  className = "text-action-primary",
}: {
  className?: string;
}): React.JSX.Element {
  return (
    <span
      role="status"
      aria-label="Réflexion en cours"
      data-testid="assistant-thinking-pulsing-dots"
      style={{ display: "inline-flex", alignItems: "center", gap: "4px" }}
      className={`inline-flex items-center gap-1 ${className}`}
    >
      <span
        style={{ ...THINKING_DOT_BASE_STYLE, animationDelay: "-0.3s" }}
        className="orcia-thinking-dot h-1.5 w-1.5 rounded-full bg-current animate-bounce [animation-delay:-0.3s]"
      />
      <span
        style={{ ...THINKING_DOT_BASE_STYLE, animationDelay: "-0.15s" }}
        className="orcia-thinking-dot h-1.5 w-1.5 rounded-full bg-current animate-bounce [animation-delay:-0.15s]"
      />
      <span
        style={THINKING_DOT_BASE_STYLE}
        className="orcia-thinking-dot h-1.5 w-1.5 rounded-full bg-current animate-bounce"
      />
    </span>
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
      className="w-full max-w-md space-y-1.5 text-xs"
    >
      <div className="flex items-center gap-2 text-text-secondary">
        <ThinkingDots />
        <span>
          {isFr
            ? "Recherche et rédaction en cours"
            : "Searching and drafting response"}
        </span>
      </div>
      <div
        className="h-1 w-48 overflow-hidden rounded-full bg-surface-secondary"
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
  readonly modelLabel?: string;
  readonly effortLabel?: string;
  readonly ragCitations?: readonly UiAssistantRagCitationItem[];
  readonly initialFeedback?: "LIKE" | "DISLIKE" | null;
  readonly onRegenerate?: () => void;
  readonly onSaveDraft?: (content: string) => void;
  readonly onContinueInProcess?: (content: string) => void;
  readonly onFeedbackChange?: (feedback: "LIKE" | "DISLIKE" | null) => void;
  readonly onInspectCitation?: (source: UiAssistantRagCitationItem, index: number) => void;
}

export function AssistantResponseFooterActionsAndCitations({
  responseText,
  isFr = true,
  modelLabel = "Polyvalent",
  effortLabel = "Standard",
  ragCitations = [],
  initialFeedback = null,
  onRegenerate,
  onSaveDraft,
  onContinueInProcess,
  onFeedbackChange,
  onInspectCitation,
}: AssistantResponseFooterActionsAndCitationsProps): React.JSX.Element {
  const [feedback, setFeedback] = useState<"LIKE" | "DISLIKE" | null>(initialFeedback);
  const [copied, setCopied] = useState<boolean>(false);
  const [draftSaved, setDraftSaved] = useState<boolean>(false);
  const [detailsOpen, setDetailsOpen] = useState<boolean>(false);

  useEffect(() => {
    setFeedback(initialFeedback ?? null);
  }, [initialFeedback]);

  useEffect(() => {
    if (!copied) return;
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
    if (typeof navigator !== "undefined" && typeof navigator.clipboard?.writeText === "function") {
      void navigator.clipboard.writeText(responseText).catch(() => {});
    }
  };

  const handleSaveDraft = () => {
    setDraftSaved(true);
    onSaveDraft?.(responseText);
  };

  const likeLabel = isFr ? "Bonne réponse" : "Good Response";
  const dislikeLabel = isFr ? "Réponse à améliorer" : "Needs improvement";
  const copyLabel = copied ? (isFr ? "Copié" : "Copied") : isFr ? "Copier" : "Copy";
  const regenerateLabel = isFr ? "Régénérer" : "Regenerate";
  const saveDraftLabel = draftSaved ? (isFr ? "Brouillon enregistré" : "Draft saved") : isFr ? "Enregistrer en brouillon" : "Save as draft";
  const continueProcessLabel = isFr ? "Poursuivre dans un Processus" : "Continue in a Process";
  const detailsLabel = isFr ? "Voir les détails de la réponse" : "View response details";
  const iconBtnClass = "h-7 w-7 inline-flex items-center justify-center rounded-md border-0 bg-transparent text-xs text-text-secondary hover:bg-surface-secondary hover:text-text-primary transition-colors";
  const activeFeedbackStyle: React.CSSProperties = { backgroundColor: "var(--color-action-primary)", color: "var(--color-primary-foreground)" };

  return (
    <div className="space-y-2 pt-2">
      {ragCitations.length > 0 && (
        <div data-testid="assistant-rag-citations-list" className="flex flex-wrap items-center gap-1.5">
          <span className="text-[11px] font-medium text-text-secondary">{isFr ? "Sources consultées :" : "Consulted sources:"}</span>
          {ragCitations.map((source, index) => (
            <a
              key={`${source.uri}-${index}`}
              href={source.uri}
              target="_blank"
              rel="noopener noreferrer"
              data-testid={`assistant-rag-citation-link-${index}`}
              onClick={(e) => {
                if (onInspectCitation) {
                  e.preventDefault();
                  onInspectCitation(source, index);
                }
              }}
              className="inline-flex items-center gap-1 rounded-full bg-surface-secondary px-2.5 py-0.5 text-[11px] font-medium text-action-primary hover:underline"
            >
              <OrciaIcon name="document" /> {source.title} <OrciaIcon name="externalLink" />
            </a>
          ))}
        </div>
      )}

      <div data-testid="assistant-response-actions-bar" role="toolbar" aria-label={isFr ? "Actions sur la réponse" : "Response actions"} className="flex flex-wrap items-center gap-1">
        <button type="button" data-testid="assistant-action-like-btn" aria-label={likeLabel} title={likeLabel} aria-pressed={feedback === "LIKE"} onClick={handleToggleLike} style={feedback === "LIKE" ? activeFeedbackStyle : undefined} className={iconBtnClass}><OrciaIcon name="like" /></button>
        <button type="button" data-testid="assistant-action-dislike-btn" aria-label={dislikeLabel} title={dislikeLabel} aria-pressed={feedback === "DISLIKE"} onClick={handleToggleDislike} style={feedback === "DISLIKE" ? activeFeedbackStyle : undefined} className={iconBtnClass}><OrciaIcon name="dislike" /></button>
        <button type="button" data-testid="assistant-action-copy-btn" aria-label={copyLabel} title={copyLabel} onClick={handleCopy} className={iconBtnClass}><OrciaIcon name={copied ? "check" : "copy"} /></button>
        <button type="button" data-testid="assistant-action-regenerate-btn" aria-label={regenerateLabel} title={regenerateLabel} onClick={() => onRegenerate?.()} className={iconBtnClass}><OrciaIcon name="regenerate" /></button>
        <button type="button" data-testid="assistant-action-save-draft-btn" aria-label={saveDraftLabel} title={saveDraftLabel} onClick={handleSaveDraft} className={iconBtnClass}><OrciaIcon name={draftSaved ? "check" : "document"} /></button>
        <button type="button" data-testid="assistant-action-continue-process-btn" aria-label={continueProcessLabel} title={continueProcessLabel} onClick={() => onContinueInProcess?.(responseText)} className={`${iconBtnClass} text-action-primary`}><OrciaIcon name="processes" /></button>
        <button type="button" data-testid="assistant-action-details-btn" aria-label={detailsLabel} title={detailsLabel} aria-expanded={detailsOpen} onClick={() => setDetailsOpen((prev) => !prev)} className={iconBtnClass}><OrciaIcon name="moreHorizontal" /></button>
      </div>

      {feedback !== null && (
        <div
          role="status"
          data-testid="assistant-feedback-thanks-banner"
          data-feedback-value={feedback}
          className="inline-flex items-center gap-2 rounded-lg border border-border-subtle bg-surface-secondary px-3 py-1.5 text-[11px] font-medium text-text-primary shadow-sm"
        >
          <span>{isFr ? "Merci pour votre retour !" : "Thanks for your feedback!"}</span>
          <span className="text-text-secondary">
            · {feedback === "LIKE" ? likeLabel : dislikeLabel}
          </span>
        </div>
      )}

      {detailsOpen && (
        <div data-testid="assistant-response-details-popover" className="inline-flex flex-wrap items-center gap-2 rounded-md bg-surface-secondary px-2.5 py-1 text-[11px] text-text-secondary">
          <span>{isFr ? "Modèle :" : "Model :"} <strong className="font-medium text-text-primary">{modelLabel}</strong></span>
          <OrciaIcon name="bulletDot" />
          <span>{isFr ? "Niveau de réflexion :" : "Thinking level :"} <strong className="font-medium text-text-primary">{effortLabel}</strong></span>
        </div>
      )}
    </div>
  );
}
