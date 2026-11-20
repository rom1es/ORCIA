import * as DialogPrimitive from "@radix-ui/react-dialog";
import React, { useState } from "react";
import { DisabledButtonAlertIndicator } from "../components/DisabledButtonAlertIndicator";
import { OrciaIcon } from "../components/icons";
import {
  DEFAULT_RGAA_MODAL_LABELS_FR,
  RgaaUnsavedChangesAlert,
  handleRgaaSubmitKeyDown,
  useUnsavedChangesDialogGuard,
  type RgaaModalDialogLabels,
} from "../components/RgaaModalDialog.js";
import type {
  UpstreamChallengeModalLabels,
  UpstreamChallengeRewindModalProps,
  UpstreamChallengeWhatIfPreview,
} from "./UpstreamChallengeRewindModalTypes";
import { UpstreamChallengeTargetMetaGrid } from "./UpstreamChallengeTargetMetaGrid";
import { UpstreamChallengeWhatIfPreviewCard } from "./UpstreamChallengeWhatIfPreviewCard";

export type {
  UpstreamChallengeModalLabels,
  UpstreamChallengeRewindModalProps,
  UpstreamChallengeWhatIfPreview,
};

const DEFAULT_INITIAL_REASON =
  "La règle métier de garantie FX 48h du PRD contredit le contrat API partenaire v3 (fenêtre max 15 min).";

/**
 * UpstreamChallengeRewindModal (`UX-DR7`, `FR-7`, `FR-16`, `FR-30`, `AD-2`, `AD-7`).
 */
export function UpstreamChallengeRewindModal({
  isOpen,
  preview,
  labels,
  subWorkflowStepKey,
  inline = false,
  rgaaLabels,
  onReasonChange,
  onSubmitChallenge,
  onTriggerReplay,
  onClose,
}: UpstreamChallengeRewindModalProps): React.ReactElement | null {
  const [initialReason, setInitialReason] = useState(DEFAULT_INITIAL_REASON);
  const [reason, setReason] = useState(DEFAULT_INITIAL_REASON);
  const [submittedChallenge, setSubmittedChallenge] = useState(false);
  const [replayed, setReplayed] = useState(false);

  const isDirty = reason !== initialReason && !submittedChallenge;
  const resolvedRgaaLabels: RgaaModalDialogLabels = {
    ...DEFAULT_RGAA_MODAL_LABELS_FR,
    cancelCta: labels.closeCta,
    submitCta: labels.submitChallengeCta,
    ...rgaaLabels,
  };

  const {
    showUnsavedConfirm,
    requestClose,
    confirmDiscardAndClose,
    cancelDiscardAndStay,
    handleDialogKeyDown,
  } = useUnsavedChangesDialogGuard({
    isOpen,
    isDirty,
    onClose: () => onClose?.(),
    onDiscardUnsavedChanges: () => {
      setReason(initialReason);
    },
  });

  if (!isOpen) {
    return null;
  }

  const canSubmit = reason.trim().length >= 10;

  const handleSubmitChallenge = (): void => {
    if (!canSubmit) return;
    setSubmittedChallenge(true);
    setInitialReason(reason);
    onSubmitChallenge?.({
      targetUpstreamStepKey: preview.targetUpstreamStepKey,
      challengedSectionKey: preview.challengedSectionKey,
      challengeReason: reason.trim(),
    });
  };

  const handleReplay = (): void => {
    setReplayed(true);
    onTriggerReplay?.({
      stepKey: preview.targetUpstreamStepKey,
      subWorkflowStepKey,
    });
  };

  const headerTitleStyle: React.CSSProperties = {
    margin: 0,
    fontSize: "0.75rem",
    fontWeight: 700,
    textTransform: "uppercase",
    color: "var(--color-arbitration-amber)",
    letterSpacing: "0.04em",
  };
  const headerSubtitleStyle: React.CSSProperties = {
    margin: "2px 0 0 0",
    fontSize: "0.8125rem",
    color: "var(--color-text-secondary)",
  };

  const renderInnerContent = (): React.ReactElement => (
    <>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: "8px",
          flexWrap: "wrap",
          flexShrink: 0,
        }}
      >
        <div>
          {inline ? (
            <>
              <h3 style={headerTitleStyle}>
                <OrciaIcon name="lightning" /> {labels.modalTitle}
              </h3>
              <p style={headerSubtitleStyle}>{labels.modalSubtitle}</p>
            </>
          ) : (
            <>
              <DialogPrimitive.Title style={headerTitleStyle}>
                <OrciaIcon name="lightning" /> {labels.modalTitle}
              </DialogPrimitive.Title>
              <DialogPrimitive.Description style={headerSubtitleStyle}>
                {labels.modalSubtitle}
              </DialogPrimitive.Description>
            </>
          )}
        </div>
      </div>

      <div className="orcia-ds-dialog-body">
        {showUnsavedConfirm ? (
          <RgaaUnsavedChangesAlert
            testIdPrefix="upstream-challenge"
            labels={resolvedRgaaLabels}
            onStay={cancelDiscardAndStay}
            onDiscard={confirmDiscardAndClose}
          />
        ) : null}

        <UpstreamChallengeTargetMetaGrid
          labels={labels}
          preview={preview}
          {...(subWorkflowStepKey ? { subWorkflowStepKey } : {})}
        />

        <label
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "4px",
            fontSize: "0.75rem",
            fontWeight: 600,
            color: "var(--color-text-primary)",
          }}
        >
          {labels.reasonLabel}
          <textarea
            autoComplete="off"
            data-lpignore="true"
            data-1p-ignore="true"
            data-bwignore="true"
            data-form-type="other"
            value={reason}
            onChange={(e) => {
              const nextVal = e.target.value;
              setReason(nextVal);
              onReasonChange?.(nextVal);
            }}
            placeholder={labels.reasonPlaceholder}
            rows={2}
            data-testid="upstream-challenge-reason-input"
            style={{
              width: "100%",
              padding: "8px",
              borderRadius: "var(--radius-sm)",
              border: "1px solid var(--color-border-subtle)",
              backgroundColor: "var(--color-surface-canvas)",
              color: "var(--color-text-primary)",
              fontFamily: "var(--font-sans)",
              fontSize: "0.8125rem",
            }}
          />
        </label>

        <UpstreamChallengeWhatIfPreviewCard preview={preview} labels={labels} />
      </div>

      <div className="orcia-ds-dialog-footer" style={{ justifyContent: "flex-start" }}>
        {onClose ? (
          <button
            type="button"
            onClick={requestClose}
            data-testid="upstream-challenge-cancel-btn"
            className="orcia-ds-btn orcia-ds-btn-secondary orcia-ds-btn-sm"
          >
            {resolvedRgaaLabels.cancelCta}
          </button>
        ) : null}
        <button
          type="button"
          disabled={!canSubmit}
          onClick={handleSubmitChallenge}
          onKeyDown={(e) => handleRgaaSubmitKeyDown(e, handleSubmitChallenge, !canSubmit)}
          data-testid="upstream-challenge-submit-btn"
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "6px",
            padding: "6px 12px",
            fontSize: "0.75rem",
            fontWeight: 600,
            borderRadius: "var(--radius-sm)",
            border: "1px solid var(--color-arbitration-amber)",
            backgroundColor: "var(--color-arbitration-amber)",
            color: "var(--color-surface-card)",
            cursor: canSubmit ? "pointer" : "not-allowed",
            opacity: canSubmit ? 1 : 0.5,
          }}
        >
          <span>{labels.submitChallengeCta}</span>
          <DisabledButtonAlertIndicator
            disabled={!canSubmit}
            reason="Saisissez le motif de remise en cause pour activer l'envoi."
            testIdSuffix="upstream-challenge-submit-btn"
          />
        </button>
        <button
          type="button"
          onClick={handleReplay}
          onKeyDown={(e) => handleRgaaSubmitKeyDown(e, handleReplay)}
          data-testid="upstream-replay-trigger-btn"
          style={{
            padding: "6px 12px",
            fontSize: "0.75rem",
            fontWeight: 600,
            borderRadius: "var(--radius-sm)",
            border: "1px solid var(--color-gate-pass)",
            backgroundColor: "var(--color-gate-pass-bg)",
            color: "var(--color-gate-pass)",
            cursor: "pointer",
          }}
        >
          {labels.replayStepCta}
        </button>
        {submittedChallenge ? (
          <span
            role="status"
            data-testid="upstream-challenge-feedback"
            style={{
              fontSize: "0.75rem",
              fontWeight: 600,
              color: "var(--color-arbitration-amber)",
            }}
          >
            {labels.challengeSubmittedFeedback}
          </span>
        ) : null}
        {replayed ? (
          <span
            role="status"
            data-testid="upstream-replay-feedback"
            style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--color-gate-pass)" }}
          >
            {labels.replayTriggeredFeedback}
          </span>
        ) : null}
      </div>
    </>
  );

  if (inline) {
    return (
      <div
        data-ux-component="upstream-challenge-rewind-modal"
        data-testid="upstream-challenge-inline-panel"
        style={{
          padding: "14px",
          borderRadius: "var(--radius-md)",
          backgroundColor: "var(--color-surface-card)",
          border: "1px solid var(--color-border-subtle)",
          borderLeft: "4px solid var(--color-arbitration-amber)",
          display: "flex",
          flexDirection: "column",
          gap: "12px",
        }}
      >
        {renderInnerContent()}
      </div>
    );
  }

  return (
    <DialogPrimitive.Root
      open={isOpen}
      onOpenChange={(nextOpen) => {
        if (!nextOpen) {
          requestClose();
        }
      }}
    >
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="orcia-ds-dialog-overlay" />
        <DialogPrimitive.Content
          aria-label={labels.modalTitle}
          data-ux-component="upstream-challenge-rewind-modal"
          onKeyDown={handleDialogKeyDown}
          onEscapeKeyDown={(event) => {
            event.preventDefault();
            requestClose();
          }}
          className="orcia-ds-dialog-content"
          style={{
            borderLeft: "4px solid var(--color-arbitration-amber)",
          }}
        >
          {renderInnerContent()}
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}
