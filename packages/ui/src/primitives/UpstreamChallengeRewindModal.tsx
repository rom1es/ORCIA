import * as DialogPrimitive from "@radix-ui/react-dialog";
import React, { useState } from "react";
import {
  useUnsavedChangesDialogGuard,
  type RgaaModalGuardLabels,
} from "../components/RgaaModalDialog.js";
import { UpstreamChallengeFormBody } from "./UpstreamChallengeFormBody";
import type {
  UpstreamChallengeModalLabels,
  UpstreamChallengeRewindModalProps,
  UpstreamChallengeWhatIfPreview,
} from "./UpstreamChallengeRewindModalTypes";

export type {
  UpstreamChallengeModalLabels,
  UpstreamChallengeRewindModalProps,
  UpstreamChallengeWhatIfPreview,
};

/**
 * UpstreamChallengeRewindModal (`UX-DR7`, `FR-7`, `FR-16`, `FR-30`, `AD-2`, `AD-7`).
 */
export function UpstreamChallengeRewindModal({
  isOpen,
  preview,
  labels,
  initialReason: initialReasonProp,
  subWorkflowStepKey,
  inline = false,
  rgaaLabels,
  onReasonChange,
  onSubmitChallenge,
  onTriggerReplay,
  onClose,
}: UpstreamChallengeRewindModalProps): React.ReactElement | null {
  const seedReason = initialReasonProp ?? labels.defaultInitialReason ?? "";
  const [initialReason, setInitialReason] = useState(seedReason);
  const [reason, setReason] = useState(seedReason);
  const [submittedChallenge, setSubmittedChallenge] = useState(false);
  const [replayed, setReplayed] = useState(false);

  const isDirty = reason !== initialReason && !submittedChallenge;
  const resolvedRgaaLabels: RgaaModalGuardLabels = {
    ...rgaaLabels,
    cancelCta: labels.closeCta || rgaaLabels?.cancelCta || "",
    submitCta: labels.submitChallengeCta || rgaaLabels?.submitCta || "",
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

  const formBody = (
    <UpstreamChallengeFormBody
      inline={inline}
      preview={preview}
      labels={labels}
      resolvedRgaaLabels={resolvedRgaaLabels}
      subWorkflowStepKey={subWorkflowStepKey}
      reason={reason}
      canSubmit={canSubmit}
      showUnsavedConfirm={showUnsavedConfirm}
      submittedChallenge={submittedChallenge}
      replayed={replayed}
      hasClose={Boolean(onClose)}
      onReasonInput={(nextVal) => {
        setReason(nextVal);
        onReasonChange?.(nextVal);
      }}
      onStay={cancelDiscardAndStay}
      onDiscard={confirmDiscardAndClose}
      onRequestClose={requestClose}
      onSubmitChallenge={handleSubmitChallenge}
      onReplay={handleReplay}
    />
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
        {formBody}
      </div>
    );
  }

  return (
    <DialogPrimitive.Root
      open={isOpen}
      onOpenChange={(nextOpen) => {
        if (!nextOpen) requestClose();
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
          style={{ borderLeft: "4px solid var(--color-arbitration-amber)" }}
        >
          {formBody}
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}
