import React from "react";

export interface DisabledButtonAlertIndicatorProps {
  /** Whether the parent button is currently disabled (greyed out). */
  readonly disabled?: boolean;
  /** Optional explanation displayed in red inside the tooltip when disabled. */
  readonly reason?: string;
  /** Optional suffix to build deterministic data-testid attributes. */
  readonly testIdSuffix?: string;
}

const DEFAULT_DISABLED_REASON =
  "Action temporairement indisponible : complétez les prérequis requis pour activer ce bouton.";

/**
 * Accessible reason indicator rendered for disabled buttons (`REM-32`).
 *
 * Replaces the former high-contrast-failing red `(!)` circle inside primary blue
 * buttons with a non-intrusive accessible text/tooltip element (`sr-only` + `title`).
 */
export function DisabledButtonAlertIndicator({
  disabled = false,
  reason,
  testIdSuffix,
}: DisabledButtonAlertIndicatorProps): React.ReactElement | null {
  if (!disabled) {
    return null;
  }

  const resolvedReason =
    reason && reason.trim().length > 0 ? reason.trim() : DEFAULT_DISABLED_REASON;
  const iconTestId = testIdSuffix
    ? `disabled-button-alert-icon-${testIdSuffix}`
    : "disabled-button-alert-icon";
  const tooltipTestId = testIdSuffix
    ? `disabled-button-alert-tooltip-${testIdSuffix}`
    : "disabled-button-alert-tooltip";

  return (
    <span
      className="sr-only"
      data-testid={iconTestId}
      aria-label={resolvedReason}
      title={resolvedReason}
    >
      <span
        role="tooltip"
        data-testid={tooltipTestId}
        data-tooltip-text={resolvedReason}
      >
        {resolvedReason}
      </span>
    </span>
  );
}
