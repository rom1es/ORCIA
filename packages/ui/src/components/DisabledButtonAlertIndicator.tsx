import React from "react";

export interface DisabledButtonAlertIndicatorProps {
  /** Whether the parent button is currently disabled (greyed out). */
  readonly disabled?: boolean;
  /** Accessible explanation rendered inside the sr-only tooltip when disabled. */
  readonly reason?: string;
  /** Optional suffix to build deterministic data-testid attributes. */
  readonly testIdSuffix?: string;
}

/**
 * Accessible reason indicator rendered for disabled buttons (`REM-32`).
 */
export function DisabledButtonAlertIndicator({
  disabled = false,
  reason,
  testIdSuffix,
}: DisabledButtonAlertIndicatorProps): React.ReactElement | null {
  if (!disabled) {
    return null;
  }

  const resolvedReason = reason ? reason.trim() : "";
  if (!resolvedReason) {
    return null;
  }
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
