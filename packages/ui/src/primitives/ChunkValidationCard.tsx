import React, { useEffect, useState } from "react";
import { DisabledButtonAlertIndicator } from "../components/DisabledButtonAlertIndicator";
import { OrciaIcon } from "../components/icons";

export type UiChunkStatus = "PENDING" | "APPROVED" | "CO_EDITED" | "CHALLENGED";
export type UiChunkDecisionAction = "APPROVE" | "CO_EDIT" | "CHALLENGE";
export type UiHumanGatePolicy =
  | "mandatory_full"
  | "risk_or_exception_based"
  | "sampling";

export interface UiChunkValidationItem {
  chunkKey: string;
  sectionTitle: string;
  sectionIndex: number;
  contentMarkdown: string;
  wordCount: number;
  humanAuthoredRequired?: boolean;
  status: UiChunkStatus;
  humanAnchorSha256?: string | null;
}

export interface ChunkValidationCardLabels {
  sectionListTitle: string;
  keyboardNavHint: string;
  approveSectionLabel: string;
  coEditSectionLabel: string;
  challengeSectionLabel: string;
  finalizeGateButtonLabel: string;
  pendingSectionsNotice: string;
  guardModalTitle: string;
  guardModalDescription: string;
  guardConfirmCheckboxLabel: string;
  guardConfirmButtonLabel: string;
  guardCancelButtonLabel: string;
}

export interface ChunkValidationCardProps {
  chunks: readonly UiChunkValidationItem[];
  totalWordCount: number;
  reviewDurationMs: number;
  hypothesesInspected: boolean;
  retainedHypotheses: readonly string[];
  readOnly?: boolean;
  onDecideChunk: (
    chunkKey: string,
    action: UiChunkDecisionAction,
    coEditedContent?: string
  ) => void;
  onFinalizeGate: (options: {
    explicitHypothesesConfirmation: boolean;
    fastApprovalWarning: boolean;
  }) => void;
  labels: ChunkValidationCardLabels;
}

/**
 * UX-DR5 & UX-DR10: Chunked Validation Card (`chunk-validation-card`) +
 * Anti-Rubber-Stamping Guard Modal (`< 15s` on `> 1,000` words).
 * Never renders a "1-Click Approve All" button while required chunks are PENDING.
 */
export function ChunkValidationCard({
  chunks,
  totalWordCount,
  reviewDurationMs,
  hypothesesInspected,
  retainedHypotheses,
  readOnly = false,
  onDecideChunk,
  onFinalizeGate,
  labels,
}: ChunkValidationCardProps) {
  const [activeIndex, setActiveIndex] = useState<number>(0);
  const [showRubberStampGuard, setShowRubberStampGuard] =
    useState<boolean>(false);
  const [hypothesesConfirmed, setHypothesesConfirmed] =
    useState<boolean>(false);

  const allChunksApproved =
    chunks.length > 0 &&
    chunks.every(
      (chunk) => chunk.status === "APPROVED" || chunk.status === "CO_EDITED"
    );
  const canFinalize = allChunksApproved && hypothesesInspected && !readOnly;

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if (event.key === "Escape" && showRubberStampGuard) {
        setShowRubberStampGuard(false);
        return;
      }
      if (event.altKey && event.key === "ArrowDown") {
        event.preventDefault();
        setActiveIndex((prev) => Math.min(chunks.length - 1, prev + 1));
      } else if (event.altKey && event.key === "ArrowUp") {
        event.preventDefault();
        setActiveIndex((prev) => Math.max(0, prev - 1));
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, [chunks.length, showRubberStampGuard]);

  const handleFinalizeClick = () => {
    if (!canFinalize) {
      return;
    }
    if (totalWordCount > 1000 && reviewDurationMs < 15000) {
      setShowRubberStampGuard(true);
      return;
    }
    onFinalizeGate({
      explicitHypothesesConfirmation: false,
      fastApprovalWarning: false,
    });
  };

  const handleGuardConfirm = () => {
    if (!hypothesesConfirmed) {
      return;
    }
    setShowRubberStampGuard(false);
    onFinalizeGate({
      explicitHypothesesConfirmation: true,
      fastApprovalWarning: true,
    });
  };

  return (
    <section
      data-testid="chunk-validation-workspace"
      className="orcia-bento-card"
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "12px",
        padding: "16px",
        backgroundColor: "var(--color-surface-card)",
        border: "1px solid var(--color-border)",
        borderRadius: "var(--radius-lg)",
      }}
    >
      <header
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "8px",
        }}
      >
        <strong>{labels.sectionListTitle}</strong>
        <span
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "var(--font-size-mono)",
            color: "var(--color-muted-foreground)",
          }}
        >
          {labels.keyboardNavHint}
        </span>
      </header>

      <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
        {chunks.map((chunk, idx) => {
          const isFocused = idx === activeIndex;
          const isApproved =
            chunk.status === "APPROVED" || chunk.status === "CO_EDITED";
          return (
            <article
              key={chunk.chunkKey}
              data-testid={`chunk-validation-card-${chunk.chunkKey}`}
              data-active={isFocused ? "true" : "false"}
              data-status={chunk.status}
              onClick={() => setActiveIndex(idx)}
              style={{
                padding: "12px",
                borderRadius: "var(--radius-md)",
                backgroundColor: isApproved
                  ? "var(--color-gate-emerald-bg)"
                  : "var(--color-surface-hover)",
                border: isFocused
                  ? "2px solid var(--color-primary-cobalt)"
                  : "1px solid var(--color-border)",
                display: "flex",
                flexDirection: "column",
                gap: "8px",
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  gap: "8px",
                }}
              >
                <span style={{ fontWeight: 600 }}>
                  {chunk.sectionTitle}{" "}
                  <small
                    style={{
                      fontFamily: "var(--font-mono)",
                      color: "var(--color-muted-foreground)",
                    }}
                  >
                    ({chunk.wordCount} mots)
                  </small>
                </span>
                <span
                  data-testid={`chunk-status-badge-${chunk.chunkKey}`}
                  style={{
                    fontFamily: "var(--font-mono)",
                    fontSize: "var(--font-size-mono)",
                    color: isApproved
                      ? "var(--color-gate-emerald)"
                      : "var(--color-arbitration-amber)",
                  }}
                >
                  {chunk.status}
                </span>
              </div>

              <p style={{ margin: 0, color: "var(--color-foreground)" }}>
                {chunk.contentMarkdown}
              </p>

              <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
                <button
                  type="button"
                  data-testid={`chunk-approve-btn-${chunk.chunkKey}`}
                  disabled={readOnly}
                  onClick={(e) => {
                    e.stopPropagation();
                    onDecideChunk(chunk.chunkKey, "APPROVE");
                  }}
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "6px",
                    backgroundColor: "var(--color-gate-emerald)",
                    color: "var(--color-primary-foreground)",
                    border: "none",
                    borderRadius: "var(--radius-sm)",
                    padding: "6px 10px",
                    fontWeight: 600,
                    cursor: readOnly ? "not-allowed" : "pointer",
                  }}
                >
                  <span>
                    <OrciaIcon name="check" /> {labels.approveSectionLabel}
                  </span>
                  <DisabledButtonAlertIndicator
                    disabled={Boolean(readOnly)}
                    reason="Mode lecture seule : validation réservée aux contributeurs."
                    testIdSuffix={`chunk-approve-btn-${chunk.chunkKey}`}
                  />
                </button>

                <button
                  type="button"
                  data-testid={`chunk-coedit-btn-${chunk.chunkKey}`}
                  disabled={readOnly}
                  onClick={(e) => {
                    e.stopPropagation();
                    onDecideChunk(
                      chunk.chunkKey,
                      "CO_EDIT",
                      `${chunk.contentMarkdown} [Co-édité & signé]`
                    );
                  }}
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "6px",
                    backgroundColor: "var(--color-surface-card)",
                    color: "var(--color-foreground)",
                    border: "1px solid var(--color-border)",
                    borderRadius: "var(--radius-sm)",
                    padding: "6px 10px",
                    fontWeight: 600,
                    cursor: readOnly ? "not-allowed" : "pointer",
                  }}
                >
                  <span>
                    <OrciaIcon name="pen" /> {labels.coEditSectionLabel}
                  </span>
                  <DisabledButtonAlertIndicator
                    disabled={Boolean(readOnly)}
                    reason="Mode lecture seule : co-édition réservée aux contributeurs."
                    testIdSuffix={`chunk-coedit-btn-${chunk.chunkKey}`}
                  />
                </button>

                <button
                  type="button"
                  data-testid={`chunk-challenge-btn-${chunk.chunkKey}`}
                  disabled={readOnly}
                  onClick={(e) => {
                    e.stopPropagation();
                    onDecideChunk(chunk.chunkKey, "CHALLENGE");
                  }}
                  style={{
                    display: "inline-flex",
                    alignItems: "center",
                    gap: "6px",
                    backgroundColor: "var(--color-stale-bg)",
                    color: "var(--color-stale-crimson)",
                    border: "1px solid var(--color-stale-crimson)",
                    borderRadius: "var(--radius-sm)",
                    padding: "6px 10px",
                    fontWeight: 600,
                    cursor: readOnly ? "not-allowed" : "pointer",
                  }}
                >
                  <span>
                    <OrciaIcon name="rollback" /> {labels.challengeSectionLabel}
                  </span>
                  <DisabledButtonAlertIndicator
                    disabled={Boolean(readOnly)}
                    reason="Mode lecture seule : remise en cause réservée aux contributeurs."
                    testIdSuffix={`chunk-challenge-btn-${chunk.chunkKey}`}
                  />
                </button>
              </div>
            </article>
          );
        })}
      </div>

      <footer
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "8px",
          paddingTop: "8px",
          borderTop: "1px solid var(--color-border)",
        }}
      >
        <span
          data-testid="chunk-validation-footer-notice"
          style={{
            fontSize: "var(--font-size-body)",
            color: canFinalize
              ? "var(--color-gate-emerald)"
              : "var(--color-muted-foreground)",
          }}
        >
          {labels.pendingSectionsNotice}
        </span>

        <button
          type="button"
          data-testid="finalize-human-gate-btn"
          disabled={!canFinalize}
          onClick={handleFinalizeClick}
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "6px",
            backgroundColor: canFinalize
              ? "var(--color-primary-cobalt)"
              : "var(--color-surface-hover)",
            color: canFinalize
              ? "var(--color-primary-foreground)"
              : "var(--color-muted-foreground)",
            border: "1px solid var(--color-border)",
            borderRadius: "var(--radius-sm)",
            padding: "8px 14px",
            fontWeight: 600,
            cursor: canFinalize ? "pointer" : "not-allowed",
          }}
        >
          <span>
            <OrciaIcon name="shield" /> {labels.finalizeGateButtonLabel}
          </span>
          <DisabledButtonAlertIndicator
            disabled={!canFinalize}
            reason={labels.pendingSectionsNotice}
            testIdSuffix="finalize-human-gate-btn"
          />
        </button>
      </footer>

      {showRubberStampGuard && (
        <div
          role="dialog"
          aria-modal="true"
          data-testid="anti-rubber-stamping-guard-modal"
          style={{
            padding: "16px",
            borderRadius: "var(--radius-md)",
            backgroundColor: "var(--color-arbitration-bg)",
            border: "2px solid var(--color-arbitration-amber)",
            display: "flex",
            flexDirection: "column",
            gap: "10px",
          }}
        >
          <strong style={{ color: "var(--color-arbitration-amber)" }}>
            <OrciaIcon name="warning" /> {labels.guardModalTitle}
          </strong>
          <p style={{ margin: 0, color: "var(--color-foreground)" }}>
            {labels.guardModalDescription}
          </p>
          <ul style={{ margin: 0, paddingLeft: "18px" }}>
            {retainedHypotheses.map((hyp, i) => (
              <li key={i}>{hyp}</li>
            ))}
          </ul>
          <label
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              cursor: "pointer",
            }}
          >
            <input
              type="checkbox"
              autoComplete="off"
              data-lpignore="true"
              data-1p-ignore="true"
              data-bwignore="true"
              data-form-type="other"
              data-testid="rubber-stamp-confirm-checkbox"
              checked={hypothesesConfirmed}
              onChange={(e) => setHypothesesConfirmed(e.target.checked)}
            />
            <span>{labels.guardConfirmCheckboxLabel}</span>
          </label>
          <div style={{ display: "flex", gap: "8px" }}>
            <button
              type="button"
              data-testid="rubber-stamp-confirm-submit-btn"
              disabled={!hypothesesConfirmed}
              onClick={handleGuardConfirm}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "6px",
                backgroundColor: "var(--color-arbitration-amber)",
                color: "var(--color-primary-foreground)",
                border: "none",
                borderRadius: "var(--radius-sm)",
                padding: "6px 12px",
                fontWeight: 600,
                cursor: hypothesesConfirmed ? "pointer" : "not-allowed",
              }}
            >
              <span>{labels.guardConfirmButtonLabel}</span>
              <DisabledButtonAlertIndicator
                disabled={!hypothesesConfirmed}
                reason={labels.guardConfirmCheckboxLabel}
                testIdSuffix="rubber-stamp-confirm-submit-btn"
              />
            </button>
            <button
              type="button"
              data-testid="rubber-stamp-cancel-btn"
              onClick={() => setShowRubberStampGuard(false)}
              style={{
                backgroundColor: "var(--color-surface-card)",
                color: "var(--color-foreground)",
                border: "1px solid var(--color-border)",
                borderRadius: "var(--radius-sm)",
                padding: "6px 12px",
                cursor: "pointer",
              }}
            >
              {labels.guardCancelButtonLabel}
            </button>
          </div>
        </div>
      )}
    </section>
  );
}
