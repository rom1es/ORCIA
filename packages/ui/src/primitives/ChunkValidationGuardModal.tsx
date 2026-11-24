import * as DialogPrimitive from "@radix-ui/react-dialog";
import React from "react";
import { DisabledButtonAlertIndicator } from "../components/DisabledButtonAlertIndicator";
import { OrciaIcon } from "../components/icons";
import type { ChunkValidationCardLabels } from "./ChunkValidationCard";

export interface ChunkValidationGuardModalProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  retainedHypotheses: readonly string[];
  hypothesesConfirmed: boolean;
  onToggleConfirmed: (checked: boolean) => void;
  onConfirm: () => void;
  labels: ChunkValidationCardLabels;
}

export function ChunkValidationGuardModal({
  open,
  onOpenChange,
  retainedHypotheses,
  hypothesesConfirmed,
  onToggleConfirmed,
  onConfirm,
  labels,
}: ChunkValidationGuardModalProps): React.ReactElement {
  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="orcia-ds-dialog-overlay" />
        <DialogPrimitive.Content
          data-testid="anti-rubber-stamping-guard-modal"
          aria-describedby={undefined}
          className="orcia-ds-dialog-content"
          style={{
            backgroundColor: "var(--color-arbitration-bg)",
            border: "2px solid var(--color-arbitration-amber)",
          }}
        >
          <DialogPrimitive.Title
            style={{ margin: 0, color: "var(--color-arbitration-amber)", fontWeight: 700 }}
          >
            <OrciaIcon name="warning" /> {labels.guardModalTitle}
          </DialogPrimitive.Title>
          <p style={{ margin: 0, color: "var(--color-foreground)" }}>
            {labels.guardModalDescription}
          </p>
          <ul style={{ margin: 0, paddingLeft: "18px" }}>
            {retainedHypotheses.map((hyp, i) => (
              <li key={i}>{hyp}</li>
            ))}
          </ul>
          <label
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              cursor: "pointer",
            }}
          >
            <input
              type="checkbox"
              autoComplete="off"
              data-lpignore="true"
              data-1p-ignore="true"
              data-bwignore="true"
              data-form-type="other"
              data-testid="rubber-stamp-confirm-checkbox"
              checked={hypothesesConfirmed}
              onChange={(e) => onToggleConfirmed(e.target.checked)}
            />
            <span>{labels.guardConfirmCheckboxLabel}</span>
          </label>
          <div style={{ display: "flex", gap: "8px" }}>
            <button
              type="button"
              data-testid="rubber-stamp-confirm-submit-btn"
              disabled={!hypothesesConfirmed}
              onClick={onConfirm}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "6px",
                backgroundColor: "var(--color-arbitration-amber)",
                color: "var(--color-primary-foreground)",
                border: "none",
                borderRadius: "var(--radius-sm)",
                padding: "6px 12px",
                fontWeight: 600,
                cursor: hypothesesConfirmed ? "pointer" : "not-allowed",
              }}
            >
              <span>{labels.guardConfirmButtonLabel}</span>
              <DisabledButtonAlertIndicator
                disabled={!hypothesesConfirmed}
                reason={labels.guardConfirmCheckboxLabel}
                testIdSuffix="rubber-stamp-confirm-submit-btn"
              />
            </button>
            <button
              type="button"
              data-testid="rubber-stamp-cancel-btn"
              onClick={() => onOpenChange(false)}
              style={{
                backgroundColor: "var(--color-surface-card)",
                color: "var(--color-foreground)",
                border: "1px solid var(--color-border)",
                borderRadius: "var(--radius-sm)",
                padding: "6px 12px",
                cursor: "pointer",
              }}
            >
              {labels.guardCancelButtonLabel}
            </button>
          </div>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}
