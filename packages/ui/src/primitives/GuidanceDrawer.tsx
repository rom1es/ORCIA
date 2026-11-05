import React, { useState } from "react";
import {
  DEFAULT_RGAA_MODAL_LABELS_FR,
  RgaaUnsavedChangesAlert,
  useUnsavedChangesDialogGuard,
  type RgaaModalDialogLabels,
} from "../components/RgaaModalDialog.js";

export interface GuidanceDrawerStepItem {
  readonly stepNumber: number;
  readonly title: string;
  readonly description: string;
  readonly actionCommand: string;
}

export interface GuidanceDrawerLabels {
  readonly drawerTitle: string;
  readonly toggleExpand: string;
  readonly toggleCollapse: string;
  readonly commandPrefix: string;
}

export interface GuidanceDrawerProps {
  readonly steps: readonly GuidanceDrawerStepItem[];
  readonly labels: GuidanceDrawerLabels;
  readonly defaultOpen?: boolean;
  readonly isDirty?: boolean;
  readonly rgaaLabels?: Partial<RgaaModalDialogLabels>;
  readonly onClose?: () => void;
}

export function GuidanceDrawer({
  steps,
  labels,
  defaultOpen = true,
  isDirty = false,
  rgaaLabels,
  onClose,
}: GuidanceDrawerProps) {
  const [open, setOpen] = useState(defaultOpen);
  const resolvedRgaaLabels: RgaaModalDialogLabels = {
    ...DEFAULT_RGAA_MODAL_LABELS_FR,
    ...rgaaLabels,
  };

  const handleCloseDrawer = (): void => {
    setOpen(false);
    onClose?.();
  };

  const {
    showUnsavedConfirm,
    requestClose,
    confirmDiscardAndClose,
    cancelDiscardAndStay,
    handleDialogKeyDown,
  } = useUnsavedChangesDialogGuard({
    isOpen: open,
    isDirty,
    onClose: handleCloseDrawer,
  });

  return (
    <aside
      data-testid="guidance-drawer"
      aria-label={labels.drawerTitle}
      onKeyDown={handleDialogKeyDown}
      style={{
        padding: "12px",
        borderRadius: "8px",
        border: "1px solid var(--orcia-border-subtle)",
        backgroundColor: "var(--orcia-surface-secondary)",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: "8px",
        }}
      >
        <strong style={{ fontSize: "0.875rem" }}>🧭 {labels.drawerTitle}</strong>
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          {open ? (
            <button
              type="button"
              data-testid="guidance-drawer-cancel-btn"
              onClick={requestClose}
              style={{
                padding: "2px 8px",
                borderRadius: "6px",
                fontSize: "0.75rem",
                border: "1px solid var(--orcia-border-subtle)",
                backgroundColor: "var(--orcia-surface-secondary)",
                color: "var(--orcia-text-secondary)",
                cursor: "pointer",
              }}
            >
              {resolvedRgaaLabels.cancelCta} (Esc)
            </button>
          ) : null}
          <button
            type="button"
            data-testid="guidance-drawer-toggle"
            aria-expanded={open}
            onClick={() => {
              if (open) {
                requestClose();
              } else {
                setOpen(true);
              }
            }}
            style={{
              padding: "2px 8px",
              borderRadius: "6px",
              fontSize: "0.75rem",
              border: "1px solid var(--orcia-border-subtle)",
              backgroundColor: "var(--orcia-surface-elevated)",
              color: "var(--orcia-text-primary)",
              cursor: "pointer",
            }}
          >
            {open ? labels.toggleCollapse : labels.toggleExpand}
          </button>
        </div>
      </div>

      {showUnsavedConfirm ? (
        <div style={{ marginTop: "8px" }}>
          <RgaaUnsavedChangesAlert
            testIdPrefix="guidance-drawer"
            labels={resolvedRgaaLabels}
            onStay={cancelDiscardAndStay}
            onDiscard={confirmDiscardAndClose}
          />
        </div>
      ) : null}

      {open ? (
        <ol
          data-testid="guidance-drawer-steps"
          style={{
            margin: "10px 0 0 0",
            paddingLeft: "18px",
            display: "flex",
            flexDirection: "column",
            gap: "6px",
          }}
        >
          {steps.map((step) => (
            <li
              key={step.stepNumber}
              data-testid={`guidance-step-${step.stepNumber}`}
              style={{ fontSize: "0.8125rem" }}
            >
              <div style={{ fontWeight: 600 }}>{step.title}</div>
              <div
                style={{
                  fontSize: "0.75rem",
                  color: "var(--orcia-text-secondary)",
                }}
              >
                {step.description}{" "}
                <code style={{ fontFamily: "var(--orcia-font-mono)" }}>
                  ({labels.commandPrefix}: {step.actionCommand})
                </code>
              </div>
            </li>
          ))}
        </ol>
      ) : null}
    </aside>
  );
}
