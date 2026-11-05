import React, { useCallback, useEffect, useState } from "react";

export interface RgaaModalGuardLabels {
  readonly cancelButtonLabel?: string;
  readonly submitButtonLabel?: string;
  readonly closeButtonLabel?: string;
  readonly cancelCta?: string;
  readonly submitCta?: string;
  readonly unsavedAlertTitle?: string;
  readonly unsavedAlertMessage?: string;
  readonly unsavedStayCta?: string;
  readonly unsavedDiscardCta?: string;
}

export type RgaaModalDialogLabels = Required<RgaaModalGuardLabels>;

export const DEFAULT_RGAA_MODAL_GUARD_LABELS_FR: Required<RgaaModalGuardLabels> = {
  cancelButtonLabel: "Annuler",
  submitButtonLabel: "Valider",
  closeButtonLabel: "Fermer (Échap)",
  cancelCta: "Annuler",
  submitCta: "Valider",
  unsavedAlertTitle: "Modifications non enregistrées",
  unsavedAlertMessage:
    "Vous avez des modifications non enregistrées. Confirmer la sortie entraînera la perte de vos modifications.",
  unsavedStayCta: "Continuer l'édition",
  unsavedDiscardCta: "Quitter sans enregistrer",
};

export const DEFAULT_RGAA_MODAL_GUARD_LABELS_EN: Required<RgaaModalGuardLabels> = {
  cancelButtonLabel: "Cancel",
  submitButtonLabel: "Validate",
  closeButtonLabel: "Close (Esc)",
  cancelCta: "Cancel",
  submitCta: "Validate",
  unsavedAlertTitle: "Unsaved changes",
  unsavedAlertMessage:
    "You have unsaved changes. Leaving now will discard your modifications.",
  unsavedStayCta: "Keep editing",
  unsavedDiscardCta: "Discard changes and leave",
};

export const DEFAULT_RGAA_MODAL_LABELS_FR = DEFAULT_RGAA_MODAL_GUARD_LABELS_FR;
export const DEFAULT_RGAA_MODAL_LABELS_EN = DEFAULT_RGAA_MODAL_GUARD_LABELS_EN;

export function resolveRgaaModalGuardLabels(
  labels?: RgaaModalGuardLabels,
  locale: "fr" | "en" = "fr",
): Required<RgaaModalGuardLabels> {
  const defaults =
    locale === "en"
      ? DEFAULT_RGAA_MODAL_GUARD_LABELS_EN
      : DEFAULT_RGAA_MODAL_GUARD_LABELS_FR;
  const cancelText =
    labels?.cancelButtonLabel ?? labels?.cancelCta ?? defaults.cancelButtonLabel;
  const submitText =
    labels?.submitButtonLabel ?? labels?.submitCta ?? defaults.submitButtonLabel;
  return {
    cancelButtonLabel: cancelText,
    submitButtonLabel: submitText,
    closeButtonLabel: labels?.closeButtonLabel ?? defaults.closeButtonLabel,
    cancelCta: cancelText,
    submitCta: submitText,
    unsavedAlertTitle: labels?.unsavedAlertTitle ?? defaults.unsavedAlertTitle,
    unsavedAlertMessage:
      labels?.unsavedAlertMessage ?? defaults.unsavedAlertMessage,
    unsavedStayCta: labels?.unsavedStayCta ?? defaults.unsavedStayCta,
    unsavedDiscardCta: labels?.unsavedDiscardCta ?? defaults.unsavedDiscardCta,
  };
}

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
export function handleRgaaSubmitKeyDown(
  event: React.KeyboardEvent<HTMLButtonElement>,
  onSubmitAction: () => void,
  disabled = false,
): void {
  if (event.key === "Enter" && !disabled) {
    event.preventDefault();
    event.stopPropagation();
    onSubmitAction();
  }
}

export interface RgaaUnsavedChangesAlertProps {
  readonly testIdPrefix: string;
  readonly isOpen?: boolean;
  readonly labels?: RgaaModalGuardLabels;
  readonly locale?: "fr" | "en";
  readonly onStay: () => void;
  readonly onConfirmDiscard?: () => void;
  readonly onDiscard?: () => void;
}

export function RgaaUnsavedChangesAlert({
  testIdPrefix,
  isOpen = true,
  labels,
  locale = "fr",
  onStay,
  onConfirmDiscard,
  onDiscard,
}: RgaaUnsavedChangesAlertProps): React.ReactElement | null {
  if (!isOpen) {
    return null;
  }
  const resolved = resolveRgaaModalGuardLabels(labels, locale);
  const handleDiscard = (): void => {
    onConfirmDiscard?.();
    onDiscard?.();
  };

  return (
    <div
      role="alertdialog"
      aria-modal="true"
      aria-label={resolved.unsavedAlertTitle}
      data-testid={`${testIdPrefix}-unsaved-changes-alert`}
      className="rounded-lg border p-3 text-xs space-y-2"
      style={{
        backgroundColor: "var(--color-arbitration-bg)",
        borderColor: "var(--color-arbitration-amber)",
        color: "var(--color-text-primary)",
      }}
    >
      <div className="font-semibold" style={{ color: "var(--color-arbitration-amber)" }}>
        ⚠️ {resolved.unsavedAlertTitle}
      </div>
      <p className="m-0 text-xs" style={{ color: "var(--color-text-primary)" }}>
        {resolved.unsavedAlertMessage}
      </p>
      <div className="flex flex-wrap items-center justify-end gap-2 pt-1">
        <button
          type="button"
          data-testid={`${testIdPrefix}-unsaved-stay-btn`}
          onClick={onStay}
          className="rounded border px-2.5 py-1 text-xs font-medium"
          style={{
            backgroundColor: "var(--color-surface-card)",
            borderColor: "var(--color-border-subtle)",
            color: "var(--color-text-primary)",
            cursor: "pointer",
          }}
        >
          {resolved.unsavedStayCta}
        </button>
        <button
          type="button"
          data-testid={`${testIdPrefix}-unsaved-discard-btn`}
          onClick={handleDiscard}
          onKeyDown={(e) => handleRgaaSubmitKeyDown(e, handleDiscard, false)}
          className="rounded border px-2.5 py-1 text-xs font-semibold"
          style={{
            backgroundColor: "var(--color-stale-crimson)",
            borderColor: "var(--color-stale-crimson)",
            color: "var(--color-primary-foreground)",
            cursor: "pointer",
          }}
        >
          {resolved.unsavedDiscardCta}
        </button>
      </div>
    </div>
  );
}

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
          className="rounded px-3 py-1.5 text-xs font-semibold"
          style={{
            backgroundColor: "var(--color-action-primary)",
            color: "var(--color-primary-foreground)",
            opacity: submitDisabled ? 0.5 : 1,
            cursor: submitDisabled ? "not-allowed" : "pointer",
          }}
        >
          {submitLabel}
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
          <button
            type="button"
            data-testid={`${prefix}-close-btn`}
            onClick={requestClose}
            className="px-2 py-1 rounded text-xs border border-surface-border text-text-secondary"
          >
            {resolved.closeButtonLabel}
          </button>
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
