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
 * Right-aligned red exclamation circle badge (`!`) + red tooltip rendered inside
 * any disabled (`greyed out`) button, using the same `18px × 18px` circular badge
 * geometry as `ContextualInfoTriggerButton` (`ⓘ`).
 *
 * When `disabled` becomes `false` (button is activable), both the red `!` badge
 * and the red tooltip completely disappear from the DOM.
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
      className="orcia-disabled-alert-badge"
      data-testid={iconTestId}
      aria-label={resolvedReason}
      title={resolvedReason}
      style={{
        display: "inline-flex",
        alignItems: "center",
        justifyContent: "center",
        width: "18px",
        height: "18px",
        minWidth: "18px",
        minHeight: "18px",
        marginLeft: "auto",
        borderRadius: "var(--radius-full)",
        border: "1px solid var(--color-status-error)",
        backgroundColor: "var(--color-stale-bg)",
        color: "var(--color-status-error)",
        fontFamily: "var(--font-sans)",
        fontSize: "11px",
        fontWeight: 700,
        lineHeight: 1,
        flexShrink: 0,
      }}
    >
      <span aria-hidden="true">!</span>
      <span
        role="tooltip"
        data-testid={tooltipTestId}
        data-tooltip-text={resolvedReason}
        className="orcia-disabled-alert-tooltip"
        style={{
          display: "none",
          color: "var(--color-status-error)",
          backgroundColor: "var(--color-stale-bg)",
          borderColor: "var(--color-status-error)",
        }}
      />
    </span>
  );
}
