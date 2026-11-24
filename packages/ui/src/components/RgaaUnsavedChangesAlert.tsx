import React from "react";
import { OrciaIcon } from "./icons";
import type { RgaaModalGuardLabels } from "./RgaaModalGuardLabels";

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
  readonly labels: RgaaModalGuardLabels;
  readonly onStay: () => void;
  readonly onConfirmDiscard?: () => void;
  readonly onDiscard?: () => void;
}

export function RgaaUnsavedChangesAlert({
  testIdPrefix,
  isOpen = true,
  labels,
  onStay,
  onConfirmDiscard,
  onDiscard,
}: RgaaUnsavedChangesAlertProps): React.ReactElement | null {
  if (!isOpen) {
    return null;
  }
  const alertTitle = labels.unsavedAlertTitle ?? "";
  const alertMessage = labels.unsavedAlertMessage ?? "";
  const stayCta = labels.unsavedStayCta ?? "";
  const discardCta = labels.unsavedDiscardCta ?? "";

  const handleDiscard = (): void => {
    onConfirmDiscard?.();
    onDiscard?.();
  };

  return (
    <div
      role="alertdialog"
      aria-modal="true"
      aria-label={alertTitle}
      data-testid={`${testIdPrefix}-unsaved-changes-alert`}
      className="rounded-lg border p-3 text-xs space-y-2"
      style={{
        backgroundColor: "var(--color-arbitration-bg)",
        borderColor: "var(--color-arbitration-amber)",
        color: "var(--color-text-primary)",
      }}
    >
      <div className="font-semibold" style={{ color: "var(--color-arbitration-amber)" }}>
        <OrciaIcon name="warning" /> {alertTitle}
      </div>
      <p className="m-0 text-xs" style={{ color: "var(--color-text-primary)" }}>
        {alertMessage}
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
          {stayCta}
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
          {discardCta}
        </button>
      </div>
    </div>
  );
}
