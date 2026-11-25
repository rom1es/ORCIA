import React, { useCallback, useEffect, useState } from "react";
import { OrciaSpinner } from "../primitives/OrciaSpinner";
import { DisabledButtonAlertIndicator } from "./DisabledButtonAlertIndicator";
import type { RgaaModalDialogLabels, RgaaModalGuardLabels } from "./RgaaModalGuardLabels";
import {
  handleRgaaSubmitKeyDown,
  RgaaUnsavedChangesAlert,
  type RgaaUnsavedChangesAlertProps,
} from "./RgaaUnsavedChangesAlert";

export {
  handleRgaaSubmitKeyDown,
  RgaaUnsavedChangesAlert,
  type RgaaModalDialogLabels,
  type RgaaModalGuardLabels,
  type RgaaUnsavedChangesAlertProps,
};

export interface UseUnsavedChangesDialogGuardOptions {
  readonly isOpen: boolean;
  readonly isDirty: boolean;
  readonly onClose?: () => void;
  readonly onDiscardChanges?: () => void;
  readonly onDiscardUnsavedChanges?: () => void;
}

export interface UseUnsavedChangesDialogGuardResult {
  readonly showUnsavedAlert: boolean;
  readonly showUnsavedConfirm: boolean;
  readonly requestClose: () => void;
  readonly cancelDiscard: () => void;
  readonly cancelDiscardAndStay: () => void;
  readonly confirmDiscard: () => void;
  readonly confirmDiscardAndClose: () => void;
  readonly handleDialogKeyDown: (event: React.KeyboardEvent<HTMLElement>) => void;
}

/**
 * RGAA escape-hatch hook for dialogs: intercepts `<Escape>` and close requests
 * when `isDirty` is true and presents an accessible `role="alertdialog"` warning.
 */
export function useUnsavedChangesDialogGuard({
  isOpen,
  isDirty,
  onClose,
  onDiscardChanges,
  onDiscardUnsavedChanges,
}: UseUnsavedChangesDialogGuardOptions): UseUnsavedChangesDialogGuardResult {
  const [showUnsavedAlert, setShowUnsavedAlert] = useState<boolean>(false);

  useEffect(() => {
    if (!isOpen || !isDirty) {
      setShowUnsavedAlert(false);
    }
  }, [isOpen, isDirty]);

  const requestClose = useCallback((): void => {
    if (isDirty) {
      setShowUnsavedAlert(true);
      return;
    }
    setShowUnsavedAlert(false);
    onClose?.();
  }, [isDirty, onClose]);

  const cancelDiscard = useCallback((): void => {
    setShowUnsavedAlert(false);
  }, []);

  const confirmDiscard = useCallback((): void => {
    setShowUnsavedAlert(false);
    onDiscardChanges?.();
    onDiscardUnsavedChanges?.();
    onClose?.();
  }, [onDiscardChanges, onDiscardUnsavedChanges, onClose]);

  const handleDialogKeyDown = useCallback(
    (event: React.KeyboardEvent<HTMLElement>): void => {
      if (event.key === "Escape") {
        event.preventDefault();
        event.stopPropagation();
        requestClose();
      }
    },
    [requestClose],
  );

  useEffect(() => {
    if (!isOpen) {
      return;
    }
    const handleWindowKeyDown = (event: KeyboardEvent): void => {
      if (event.key === "Escape") {
        event.preventDefault();
        if (isDirty) {
          setShowUnsavedAlert(true);
        } else {
          setShowUnsavedAlert(false);
          onClose?.();
        }
      }
    };
    window.addEventListener("keydown", handleWindowKeyDown);
    return () => window.removeEventListener("keydown", handleWindowKeyDown);
  }, [isOpen, isDirty, onClose]);

  return {
    showUnsavedAlert,
    showUnsavedConfirm: showUnsavedAlert,
    requestClose,
    cancelDiscard,
    cancelDiscardAndStay: cancelDiscard,
    confirmDiscard,
    confirmDiscardAndClose: confirmDiscard,
    handleDialogKeyDown,
  };
}

export interface RgaaDialogFooterActionsProps {
  readonly testIdPrefix: string;
  readonly cancelTestId?: string;
  readonly submitTestId?: string;
  readonly cancelLabel: string;
  readonly submitLabel?: string;
  readonly submitDisabled?: boolean;
  readonly isSubmitting?: boolean;
  readonly disabledReason?: string;
  readonly submitButtonType?: "button" | "submit";
  readonly onCancel: () => void;
  readonly onSubmit?: () => void;
}

export function RgaaDialogFooterActions({
  testIdPrefix,
  cancelTestId,
  submitTestId,
  cancelLabel,
  submitLabel = "",
  submitDisabled = false,
  isSubmitting = false,
  disabledReason,
  submitButtonType = "button",
  onCancel,
  onSubmit,
}: RgaaDialogFooterActionsProps): React.ReactElement {
  const effectiveSubmitTestId = submitTestId ?? `${testIdPrefix}-submit-btn`;
  return (
    <div
      data-testid={`${testIdPrefix}-rgaa-footer-actions`}
      className="flex flex-wrap items-center justify-end gap-2"
    >
      <button
        type="button"
        data-testid={cancelTestId ?? `${testIdPrefix}-cancel-btn`}
        onClick={onCancel}
        className="rounded border px-3 py-1.5 text-xs font-medium"
        style={{
          backgroundColor: "var(--color-surface-secondary)",
          borderColor: "var(--color-border-subtle)",
          color: "var(--color-text-primary)",
          cursor: "pointer",
        }}
      >
        {cancelLabel}
      </button>
      {onSubmit && (
        <button
          type={submitButtonType}
          data-testid={effectiveSubmitTestId}
          disabled={submitDisabled || isSubmitting}
          onClick={onSubmit}
          onKeyDown={(e) => handleRgaaSubmitKeyDown(e, onSubmit, submitDisabled || isSubmitting)}
          className="inline-flex items-center gap-1.5 rounded px-3 py-1.5 text-xs font-semibold"
          style={{
            backgroundColor: "var(--color-action-primary)",
            color: "var(--color-primary-foreground)",
            opacity: submitDisabled || isSubmitting ? 0.55 : 1,
            cursor: submitDisabled || isSubmitting ? "not-allowed" : "pointer",
          }}
        >
          {isSubmitting && <OrciaSpinner size="xs" testId={`${testIdPrefix}-submit-spinner`} />}
          <span>{submitLabel}</span>
          <DisabledButtonAlertIndicator
            disabled={submitDisabled}
            reason={disabledReason}
            testIdSuffix={effectiveSubmitTestId}
          />
        </button>
      )}
    </div>
  );
}

export interface RgaaModalDialogProps {
  readonly testId: string;
  readonly testIdPrefix?: string;
  readonly isOpen: boolean;
  readonly title: string;
  readonly isDirty?: boolean;
  readonly submitDisabled?: boolean;
  readonly disabledReason?: string;
  readonly labels: RgaaModalGuardLabels;
  readonly onClose: () => void;
  readonly onDiscardChanges?: () => void;
  readonly onDiscardUnsavedChanges?: () => void;
  readonly onSubmit?: () => void;
  readonly children: React.ReactNode;
}

/**
 * Accessible RGAA / WAI-ARIA 1.2 Modal Dialog container (`AccessibleModalDialog` / `RgaaModalDialog`).
 */
export function RgaaModalDialog({
  testId,
  testIdPrefix,
  isOpen,
  title,
  isDirty = false,
  submitDisabled = false,
  disabledReason,
  labels,
  onClose,
  onDiscardChanges,
  onDiscardUnsavedChanges,
  onSubmit,
  children,
}: RgaaModalDialogProps): React.ReactElement | null {
  const prefix = testIdPrefix ?? testId;
  const cancelText = labels.cancelButtonLabel ?? labels.cancelCta ?? "";
  const submitText = labels.submitButtonLabel ?? labels.submitCta ?? "";
  const { showUnsavedAlert, requestClose, cancelDiscard, confirmDiscard } =
    useUnsavedChangesDialogGuard({
      isOpen,
      isDirty,
      onClose,
      onDiscardChanges,
      onDiscardUnsavedChanges,
    });

  if (!isOpen) {
    return null;
  }

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={title}
      data-testid={testId}
      className="fixed inset-0 z-40 flex items-center justify-center p-4"
      style={{ backgroundColor: "rgba(15, 23, 42, 0.45)" }}
    >
      <div
        className="w-[720px] max-h-[600px] flex flex-col rounded-xl border bg-surface-elevated text-text-primary shadow-xl overflow-hidden"
        style={{ borderColor: "var(--color-border-subtle)" }}
      >
        <div className="px-4 py-3 border-b border-surface-border flex items-center justify-between">
          <h2 className="text-sm font-semibold">{title}</h2>
        </div>

        <RgaaUnsavedChangesAlert
          testIdPrefix={prefix}
          isOpen={showUnsavedAlert}
          labels={labels}
          onStay={cancelDiscard}
          onConfirmDiscard={confirmDiscard}
        />

        <div className="flex-1 overflow-y-auto p-4">{children}</div>

        <div className="px-4 py-3 border-t border-surface-border bg-surface-secondary">
          <RgaaDialogFooterActions
            testIdPrefix={prefix}
            cancelLabel={cancelText}
            submitLabel={submitText}
            submitDisabled={submitDisabled}
            disabledReason={disabledReason}
            onCancel={requestClose}
            onSubmit={onSubmit}
          />
        </div>
      </div>
    </div>
  );
}

export { RgaaModalDialog as AccessibleModalDialog, RgaaModalDialog as RgaaModalFrame };
