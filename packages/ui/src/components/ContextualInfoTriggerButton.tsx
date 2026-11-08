import React from "react";
import { OrciaIcon } from "./icons";

export interface ContextualInfoTriggerButtonProps {
  /**
   * Identifier of the contextual help section to focus and highlight
   * inside the right-hand Contextual Help column (`ContextualHelpColumnAndCenter`).
   */
  readonly sectionId: string;
  /**
   * Accessible label describing what help section this button opens
   * (e.g. "Comprendre la hiérarchie des espaces").
   */
  readonly label: string;
  /**
   * Callback invoked when the user clicks the `ⓘ` button.
   * Typically opens the right-hand help column and highlights `sectionId`.
   */
  readonly onOpenHelpSection?: (sectionId: string) => void;
  /**
   * Optional custom `data-testid` (defaults to `contextual-info-trigger-${sectionId}`).
   */
  readonly testId?: string;
}

/**
 * Discrete, accessible `ⓘ` (`18px × 18px` circle) contextual help trigger button.
 *
 * Replaces verbose inline explanatory paragraphs inside the central workspace:
 * clicking `ⓘ` opens the right-hand Contextual Help column (`FourZoneDirectionCShell`)
 * and scrolls/highlights the targeted explanation section (`sectionId`).
 */
export function ContextualInfoTriggerButton({
  sectionId,
  label,
  onOpenHelpSection,
  testId,
}: ContextualInfoTriggerButtonProps): React.ReactElement {
  return (
    <button
      type="button"
      className="orcia-info-trigger-btn"
      aria-label={label}
      title={label}
      data-testid={testId ?? `contextual-info-trigger-${sectionId}`}
      data-help-section-target={sectionId}
      onClick={(event) => {
        event.stopPropagation();
        onOpenHelpSection?.(sectionId);
      }}
    >
      <OrciaIcon name="infoBadge" />
    </button>
  );
}
