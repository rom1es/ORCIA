import * as DialogPrimitive from "@radix-ui/react-dialog";
import React, { useState } from "react";
import { DisabledButtonAlertIndicator } from "../components/DisabledButtonAlertIndicator";
import {
  DEFAULT_RGAA_MODAL_LABELS_FR,
  RgaaUnsavedChangesAlert,
  handleRgaaSubmitKeyDown,
  useUnsavedChangesDialogGuard,
  type RgaaModalDialogLabels,
} from "../components/RgaaModalDialog.js";

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
}

export interface CommandPaletteModalProps {
  readonly isOpen: boolean;
  readonly items: readonly CommandPaletteItemSpec[];
  readonly labels: CommandPaletteModalLabels;
  readonly isDirty?: boolean;
  readonly rgaaLabels?: Partial<RgaaModalDialogLabels>;
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
  const resolvedRgaaLabels: RgaaModalDialogLabels = {
    ...DEFAULT_RGAA_MODAL_LABELS_FR,
    cancelCta: labels.closeButton || DEFAULT_RGAA_MODAL_LABELS_FR.cancelCta,
    ...rgaaLabels,
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
        if (!nextOpen) {
          requestClose();
        }
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
            <button
              type="button"
              data-testid="command-palette-close"
              onClick={requestClose}
              style={{
                padding: "4px 8px",
                borderRadius: "6px",
                fontSize: "0.75rem",
                border: "1px solid var(--orcia-border-subtle)",
                backgroundColor: "var(--orcia-surface-secondary)",
                color: "var(--orcia-text-primary)",
                cursor: "pointer",
              }}
            >
              {labels.closeButton} (Esc)
            </button>
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

            <div
              data-testid="command-palette-results"
              style={{
                display: "flex",
                flexDirection: "column",
                gap: "6px",
                maxHeight: "320px",
                overflowY: "auto",
              }}
            >
              {filtered.length === 0 ? (
                <p style={{ fontSize: "0.8125rem", color: "var(--orcia-text-muted)" }}>
                  {labels.emptyResults}
                </p>
              ) : (
                filtered.map((item) => (
                  <button
                    key={item.entryId}
                    type="button"
                    data-testid={`command-palette-item-${item.entryId}`}
                    onClick={() => {
                      onSelectItem?.(item);
                      onClose();
                    }}
                    onKeyDown={(e) =>
                      handleRgaaSubmitKeyDown(e, () => {
                        onSelectItem?.(item);
                        onClose();
                      })
                    }
                    style={{
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      textAlign: "left",
                      padding: "8px 10px",
                      borderRadius: "8px",
                      border: "1px solid var(--orcia-border-subtle)",
                      backgroundColor: "var(--orcia-surface-primary)",
                      color: "var(--orcia-text-primary)",
                      cursor: "pointer",
                    }}
                  >
                    <div>
                      <div style={{ fontWeight: 600, fontSize: "0.8125rem" }}>
                        {item.label}
                      </div>
                      <div
                        style={{
                          fontSize: "0.75rem",
                          color: "var(--orcia-text-secondary)",
                        }}
                      >
                        {item.subtitle}
                      </div>
                    </div>
                    <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                      {item.accessMode ? (
                        <span
                          style={{
                            fontSize: "0.7rem",
                            padding: "2px 6px",
                            borderRadius: "9999px",
                            border: "1px solid var(--orcia-border-subtle)",
                          }}
                        >
                          {item.accessMode === "CONTRIBUTOR_ACTION_REQUIRED"
                            ? labels.contributorBadge
                            : labels.observerBadge}
                        </span>
                      ) : null}
                      <kbd
                        style={{
                          fontSize: "0.75rem",
                          fontFamily: "var(--orcia-font-mono)",
                          padding: "2px 6px",
                          borderRadius: "4px",
                          backgroundColor: "var(--orcia-surface-secondary)",
                          border: "1px solid var(--orcia-border-subtle)",
                        }}
                      >
                        {item.shortcut}
                      </kbd>
                    </div>
                  </button>
                ))
              )}
            </div>
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
