import React, { useEffect, useState } from "react";
import { DisabledButtonAlertIndicator } from "../components/DisabledButtonAlertIndicator";
import { OrciaIcon } from "../components/icons";
import { ChunkValidationGuardModal } from "./ChunkValidationGuardModal";
import { ChunkValidationItemsList } from "./ChunkValidationItemsList";

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
  wordsUnitLabel?: string;
  coEditedTagLabel?: string;
  statusLabels?: {
    readonly pending: string;
    readonly approved: string;
    readonly coEdited: string;
  };
  readOnlyApproveReason?: string;
  readOnlyCoEditReason?: string;
  readOnlyChallengeReason?: string;
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

      <ChunkValidationItemsList
        chunks={chunks}
        activeIndex={activeIndex}
        readOnly={readOnly}
        labels={labels}
        onSelectIndex={setActiveIndex}
        onDecideChunk={onDecideChunk}
      />

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

      <ChunkValidationGuardModal
        open={showRubberStampGuard}
        onOpenChange={setShowRubberStampGuard}
        retainedHypotheses={retainedHypotheses}
        hypothesesConfirmed={hypothesesConfirmed}
        onToggleConfirmed={setHypothesesConfirmed}
        onConfirm={handleGuardConfirm}
        labels={labels}
      />
    </section>
  );
}
