import React from "react";
import type { ProcessVsmExecutionUiDictionary } from "../../../i18n/locales/process_vsm_execution_ui_labels";

export interface ProcessRunCorrectionPopoverProps {
  readonly copy: ProcessVsmExecutionUiDictionary["execution"];
  readonly isActionDisabled: boolean;
  readonly returnLoopTargetStep: string;
  readonly returnLoopRemarks: string;
  readonly onChangeReturnLoopTarget: (step: string) => void;
  readonly onChangeReturnLoopRemarks: (remarks: string) => void;
  readonly onCancel: () => void;
  readonly onSubmitCorrections: () => void;
}

export function ProcessRunCorrectionPopover({
  copy,
  isActionDisabled,
  returnLoopTargetStep,
  returnLoopRemarks,
  onChangeReturnLoopTarget,
  onChangeReturnLoopRemarks,
  onCancel,
  onSubmitCorrections,
}: ProcessRunCorrectionPopoverProps): React.JSX.Element {
  return (
    <div
      data-testid="request-corrections-popover"
      className="flex flex-col gap-2.5 rounded border p-3"
      style={{
        backgroundColor: "var(--color-surface-card)",
        borderColor: "var(--color-border-subtle)",
      }}
    >
      <div
        style={{
          display: "grid",
          gridTemplateColumns: "minmax(200px, 280px) 1fr",
          gap: "8px",
          alignItems: "start",
        }}
      >
        <select
          aria-label={copy.returnStepSelectAriaLabel}
          data-testid="anchor-return-loop-target-select"
          value={returnLoopTargetStep}
          onChange={(e) => onChangeReturnLoopTarget(e.target.value)}
          className="orcia-ds-select"
        >
          {copy.returnStepOptions.map((opt) => (
            <option key={opt.value} value={opt.value}>
              {opt.label}
            </option>
          ))}
        </select>

        <textarea
          rows={2}
          aria-label={copy.returnRemarksAriaLabel}
          data-testid="anchor-return-loop-remarks-input"
          autoComplete="off"
          data-lpignore="true"
          data-1p-ignore="true"
          data-bwignore="true"
          data-form-type="other"
          value={returnLoopRemarks}
          onChange={(e) => onChangeReturnLoopRemarks(e.target.value)}
          placeholder={copy.returnRemarksPlaceholder}
          className="orcia-ds-textarea"
        />
      </div>
      <div className="flex flex-wrap justify-end gap-2">
        <button
          type="button"
          data-testid="cancel-request-corrections-btn"
          onClick={onCancel}
          className="orcia-ds-btn orcia-ds-btn-ghost orcia-ds-btn-sm"
        >
          {copy.cancelBtn}
        </button>
        <button
          type="button"
          data-testid="anchor-action-3-reject-loop-btn"
          disabled={isActionDisabled}
          onClick={onSubmitCorrections}
          className="orcia-ds-btn orcia-ds-btn-secondary orcia-ds-btn-sm"
        >
          {copy.submitCorrectionsBtn}
        </button>
      </div>
    </div>
  );
}
