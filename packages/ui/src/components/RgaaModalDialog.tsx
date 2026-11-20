import React, { useCallback, useEffect, useState } from "react";
import { DisabledButtonAlertIndicator } from "./DisabledButtonAlertIndicator";
import {
  DEFAULT_RGAA_MODAL_GUARD_LABELS_EN,
  DEFAULT_RGAA_MODAL_GUARD_LABELS_FR,
  DEFAULT_RGAA_MODAL_LABELS_EN,
  DEFAULT_RGAA_MODAL_LABELS_FR,
  resolveRgaaModalGuardLabels,
  type RgaaModalDialogLabels,
  type RgaaModalGuardLabels,
} from "./RgaaModalGuardLabels";
import {
  handleRgaaSubmitKeyDown,
  RgaaUnsavedChangesAlert,
  type RgaaUnsavedChangesAlertProps,
} from "./RgaaUnsavedChangesAlert";

export {
  DEFAULT_RGAA_MODAL_GUARD_LABELS_EN,
  DEFAULT_RGAA_MODAL_GUARD_LABELS_FR,
  DEFAULT_RGAA_MODAL_LABELS_EN,
  DEFAULT_RGAA_MODAL_LABELS_FR,
  handleRgaaSubmitKeyDown,
  resolveRgaaModalGuardLabels,
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
 * RGAA / UX Rule #5 ("Offrir des sorties de secours") hook for modals and dialogs:
 * - Listens to `<Escape>` on `window` when `isOpen === true`.
 * - If `isDirty === false`, invokes `onClose()` immediately.
 * - If `isDirty === true`, intercepts `<Escape>`, `Annuler` or `✕` clicks and shows an
 *   accessible `role="alertdialog"` warning before discarding unsaved modifications.
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

/**
 * RGAA keyboard activation helper for `Valider` / `Submit` buttons:
 * When keyboard focus is on the `Valider` button, pressing `<Enter>` (`Entrée`)
 * deterministically acts as a click on that button across all DOM / JSDOM environments.
 */
export interface RgaaDialogFooterActionsProps {
  readonly testIdPrefix: string;
  readonly cancelLabel?: string;
  readonly submitLabel?: string;
  readonly submitDisabled?: boolean;
  readonly submitButtonType?: "button" | "submit";
  readonly onCancel: () => void;
  readonly onSubmit?: () => void;
}

export function RgaaDialogFooterActions({
  testIdPrefix,
  cancelLabel = DEFAULT_RGAA_MODAL_GUARD_LABELS_FR.cancelButtonLabel,
  submitLabel = DEFAULT_RGAA_MODAL_GUARD_LABELS_FR.submitButtonLabel,
  submitDisabled = false,
  submitButtonType = "button",
  onCancel,
  onSubmit,
}: RgaaDialogFooterActionsProps): React.ReactElement {
  return (
    <div
      data-testid={`${testIdPrefix}-rgaa-footer-actions`}
      className="flex flex-wrap items-center justify-end gap-2"
    >
      <button
        type="button"
        data-testid={`${testIdPrefix}-cancel-btn`}
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
          data-testid={`${testIdPrefix}-submit-btn`}
          disabled={submitDisabled}
          onClick={onSubmit}
          onKeyDown={(e) => handleRgaaSubmitKeyDown(e, onSubmit, submitDisabled)}
          className="inline-flex items-center gap-1.5 rounded px-3 py-1.5 text-xs font-semibold"
          style={{
            backgroundColor: "var(--color-action-primary)",
            color: "var(--color-primary-foreground)",
            opacity: submitDisabled ? 0.55 : 1,
            cursor: submitDisabled ? "not-allowed" : "pointer",
          }}
        >
          <span>{submitLabel}</span>
          <DisabledButtonAlertIndicator
            disabled={submitDisabled}
            testIdSuffix={`${testIdPrefix}-submit-btn`}
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
  readonly labels?: RgaaModalGuardLabels;
  readonly locale?: "fr" | "en";
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
  labels,
  locale = "fr",
  onClose,
  onDiscardChanges,
  onDiscardUnsavedChanges,
  onSubmit,
  children,
}: RgaaModalDialogProps): React.ReactElement | null {
  const prefix = testIdPrefix ?? testId;
  const resolved = resolveRgaaModalGuardLabels(labels, locale);
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
          locale={locale}
          onStay={cancelDiscard}
          onConfirmDiscard={confirmDiscard}
        />

        <div className="flex-1 overflow-y-auto p-4">{children}</div>

        <div className="px-4 py-3 border-t border-surface-border bg-surface-secondary">
          <RgaaDialogFooterActions
            testIdPrefix={prefix}
            cancelLabel={resolved.cancelButtonLabel}
            submitLabel={resolved.submitButtonLabel}
            submitDisabled={submitDisabled}
            onCancel={requestClose}
            onSubmit={onSubmit}
          />
        </div>
      </div>
    </div>
  );
}

export { RgaaModalDialog as AccessibleModalDialog, RgaaModalDialog as RgaaModalFrame };
