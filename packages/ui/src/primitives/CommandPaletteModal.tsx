import * as DialogPrimitive from "@radix-ui/react-dialog";
import React, { useState } from "react";
import { DisabledButtonAlertIndicator } from "../components/DisabledButtonAlertIndicator";
import {
  RgaaUnsavedChangesAlert,
  handleRgaaSubmitKeyDown,
  useUnsavedChangesDialogGuard,
  type RgaaModalGuardLabels,
} from "../components/RgaaModalDialog.js";
import { CommandPaletteResultsList } from "./CommandPaletteResultsList";

export interface CommandPaletteItemSpec {
  readonly entryId: string;
  readonly category: "RUN" | "WORKSPACE" | "NAVIGATION" | "ONTOLOGY" | "CATALOG";
  readonly label: string;
  readonly subtitle: string;
  readonly shortcut: string;
  readonly targetRoute: string;
  readonly accessMode?: "CONTRIBUTOR_ACTION_REQUIRED" | "READ_ONLY_OBSERVER" | null;
}

export interface CommandPaletteModalLabels {
  readonly modalTitle: string;
  readonly searchPlaceholder: string;
  readonly closeButton: string;
  readonly emptyResults: string;
  readonly contributorBadge: string;
  readonly observerBadge: string;
  readonly openActionLabel?: string;
}

export interface CommandPaletteModalProps {
  readonly isOpen: boolean;
  readonly items: readonly CommandPaletteItemSpec[];
  readonly labels: CommandPaletteModalLabels;
  readonly isDirty?: boolean;
  readonly rgaaLabels?: RgaaModalGuardLabels;
  readonly onClose: () => void;
  readonly onSelectItem?: (item: CommandPaletteItemSpec) => void;
}

export function CommandPaletteModal({
  isOpen,
  items,
  labels,
  isDirty = false,
  rgaaLabels,
  onClose,
  onSelectItem,
}: CommandPaletteModalProps) {
  const [query, setQuery] = useState("");
  const resolvedRgaaLabels: RgaaModalGuardLabels = {
    ...rgaaLabels,
    cancelCta: labels.closeButton || rgaaLabels?.cancelCta || "",
    submitCta: labels.openActionLabel ?? rgaaLabels?.submitCta ?? rgaaLabels?.submitButtonLabel ?? "",
  };

  const {
    showUnsavedConfirm,
    requestClose,
    confirmDiscardAndClose,
    cancelDiscardAndStay,
    handleDialogKeyDown,
  } = useUnsavedChangesDialogGuard({
    isOpen,
    isDirty,
    onClose,
    onDiscardUnsavedChanges: () => setQuery(""),
  });

  if (!isOpen) {
    return null;
  }

  const normalized = query.trim().toLowerCase();
  const filtered = items.filter((item) => {
    if (!normalized) return true;
    return (
      item.label.toLowerCase().includes(normalized) ||
      item.subtitle.toLowerCase().includes(normalized) ||
      item.shortcut.toLowerCase().includes(normalized)
    );
  });

  const activeItem = filtered[0] ?? null;

  const handleConfirmActiveItem = (): void => {
    if (!activeItem) return;
    onSelectItem?.(activeItem);
    onClose();
  };

  return (
    <DialogPrimitive.Root
      open={isOpen}
      onOpenChange={(nextOpen) => {
        if (!nextOpen) requestClose();
      }}
    >
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="orcia-ds-dialog-overlay" />
        <DialogPrimitive.Content
          aria-label={labels.modalTitle}
          data-testid="command-palette-modal"
          onKeyDown={handleDialogKeyDown}
          onEscapeKeyDown={(event) => {
            event.preventDefault();
            requestClose();
          }}
          className="orcia-ds-dialog-content"
          style={{
            maxWidth: "620px",
            backgroundColor: "var(--orcia-surface-elevated)",
            borderColor: "var(--orcia-border-subtle)",
          }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              flexShrink: 0,
            }}
          >
            <DialogPrimitive.Title style={{ margin: 0, fontSize: "0.9375rem", fontWeight: 700 }}>
              ⌘K — {labels.modalTitle}
            </DialogPrimitive.Title>
          </div>

          <div className="orcia-ds-dialog-body">
            {showUnsavedConfirm ? (
              <RgaaUnsavedChangesAlert
                testIdPrefix="command-palette"
                labels={resolvedRgaaLabels}
                onStay={cancelDiscardAndStay}
                onDiscard={confirmDiscardAndClose}
              />
            ) : null}

            <input
              type="search"
              autoComplete="off"
              data-lpignore="true"
              data-1p-ignore="true"
              data-bwignore="true"
              data-form-type="other"
              data-testid="command-palette-input"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder={labels.searchPlaceholder}
              style={{
                width: "100%",
                padding: "8px 12px",
                borderRadius: "8px",
                border: "1px solid var(--orcia-border-subtle)",
                backgroundColor: "var(--orcia-surface-primary)",
                color: "var(--orcia-text-primary)",
                fontSize: "0.875rem",
              }}
            />

            <CommandPaletteResultsList
              filtered={filtered}
              labels={labels}
              onSelectItem={onSelectItem}
              onClose={onClose}
            />
          </div>

          <div
            className="orcia-ds-dialog-footer"
            style={{ borderTop: "1px solid var(--orcia-border-subtle)" }}
          >
            <button
              type="button"
              data-testid="command-palette-cancel-btn"
              onClick={requestClose}
              style={{
                padding: "4px 10px",
                borderRadius: "6px",
                fontSize: "0.75rem",
                border: "1px solid var(--orcia-border-subtle)",
                backgroundColor: "var(--orcia-surface-secondary)",
                color: "var(--orcia-text-primary)",
                cursor: "pointer",
              }}
            >
              {resolvedRgaaLabels.cancelCta}
            </button>
            <button
              type="button"
              data-testid="command-palette-submit-btn"
              disabled={!activeItem}
              onClick={handleConfirmActiveItem}
              onKeyDown={(e) =>
                handleRgaaSubmitKeyDown(e, handleConfirmActiveItem, !activeItem)
              }
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "6px",
                padding: "4px 10px",
                borderRadius: "6px",
                fontSize: "0.75rem",
                fontWeight: 600,
                border: "1px solid var(--orcia-action-primary)",
                backgroundColor: "var(--orcia-action-primary)",
                color: "var(--orcia-text-on-action)",
                cursor: activeItem ? "pointer" : "not-allowed",
                opacity: activeItem ? 1 : 0.55,
              }}
            >
              <span>{resolvedRgaaLabels.submitCta}</span>
              <DisabledButtonAlertIndicator
                disabled={!activeItem}
                reason={labels.emptyResults}
                testIdSuffix="command-palette-submit-btn"
              />
            </button>
          </div>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}
