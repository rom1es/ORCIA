import React, { useEffect, useState } from "react";
import { OrciaDialog } from "../RadixDesignSystemPrimitives";

export interface FinopsBudgetOverrideModalProps {
  readonly open: boolean;
  readonly onOpenChange: (open: boolean) => void;
  readonly runId?: string;
  readonly workflowTitle?: string;
  readonly defaultAmountUsd?: number;
  readonly labels: {
    overrideTitle: string;
    overrideDescription: string;
    overrideAmountLabel: string;
    overrideReasonLabel: string;
    overrideSubmitButton: string;
    cancelButton: string;
  };
  readonly onSubmitOverride?: (runId: string, amountUsd: number, reason: string) => void;
}

export function FinopsBudgetOverrideModal({
  open,
  onOpenChange,
  runId = "",
  workflowTitle = "",
  defaultAmountUsd = 20,
  labels,
  onSubmitOverride,
}: FinopsBudgetOverrideModalProps): React.ReactElement {
  const [amountUsd, setAmountUsd] = useState<number>(defaultAmountUsd);
  const [reason, setReason] = useState<string>("");

  useEffect(() => {
    if (!open) return;
    setAmountUsd(defaultAmountUsd);
    setReason("");
  }, [open, runId, defaultAmountUsd]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!reason.trim()) return;
    onSubmitOverride?.(runId, amountUsd, reason.trim());
    onOpenChange(false);
  };

  return (
    <OrciaDialog
      open={open}
      onOpenChange={onOpenChange}
      title={labels.overrideTitle}
      description={workflowTitle ? `${labels.overrideDescription} — ${workflowTitle}` : labels.overrideDescription}
      testId="finops-override-modal"
      closeLabel={labels.cancelButton}
      hideHeaderCloseButton
    >
      <form
        onSubmit={handleSubmit}
        data-testid="finops-override-form"
        autoComplete="off"
        data-lpignore="true"
        data-form-type="other"
        style={{ display: "flex", flexDirection: "column", gap: "16px", marginTop: "12px" }}
      >
        <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          <label htmlFor="finops-override-amount-input" style={{ fontSize: "12px", fontWeight: 600 }}>{labels.overrideAmountLabel}</label>
          <input
            id="finops-override-amount-input"
            data-testid="finops-override-amount-input"
            type="number"
            min="1"
            step="5"
            value={amountUsd}
            onChange={(e) => setAmountUsd(Number(e.target.value))}
            className="orcia-ds-input"
            autoComplete="off"
            data-lpignore="true"
            data-1p-ignore="true"
            data-bwignore="true"
            data-form-type="other"
            required
          />
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
          <label htmlFor="finops-override-reason-input" style={{ fontSize: "12px", fontWeight: 600 }}>{labels.overrideReasonLabel}</label>
          <textarea
            id="finops-override-reason-input"
            data-testid="finops-override-reason-input"
            rows={3}
            value={reason}
            onChange={(e) => setReason(e.target.value)}
            className="orcia-ds-input"
            style={{ resize: "vertical" }}
            autoComplete="off"
            data-lpignore="true"
            data-1p-ignore="true"
            data-bwignore="true"
            data-form-type="other"
            required
          />
        </div>

        <div style={{ display: "flex", justifyContent: "flex-end", gap: "8px", marginTop: "12px" }}>
          <button
            type="button"
            data-testid="finops-override-cancel-btn"
            className="orcia-ds-btn orcia-ds-btn-secondary"
            onClick={() => onOpenChange(false)}
          >
            {labels.cancelButton}
          </button>
          <button
            type="submit"
            data-testid="finops-override-submit-btn"
            disabled={!reason.trim() || amountUsd <= 0}
            className="orcia-ds-btn orcia-ds-btn-primary"
          >
            {labels.overrideSubmitButton}
          </button>
        </div>
      </form>
    </OrciaDialog>
  );
}
