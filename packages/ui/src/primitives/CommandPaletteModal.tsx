import React, { useState } from "react";

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
  readonly onClose: () => void;
  readonly onSelectItem?: (item: CommandPaletteItemSpec) => void;
}

export function CommandPaletteModal({
  isOpen,
  items,
  labels,
  onClose,
  onSelectItem,
}: CommandPaletteModalProps) {
  const [query, setQuery] = useState("");

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

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={labels.modalTitle}
      data-testid="command-palette-modal"
      onKeyDown={(e) => {
        if (e.key === "Escape") {
          onClose();
        }
      }}
      style={{
        position: "fixed",
        inset: 0,
        zIndex: 50,
        backgroundColor: "var(--orcia-surface-secondary)",
        display: "flex",
        alignItems: "flex-start",
        justifyContent: "center",
        paddingTop: "80px",
      }}
    >
      <div
        style={{
          width: "100%",
          maxWidth: "620px",
          borderRadius: "12px",
          border: "1px solid var(--orcia-border-subtle)",
          backgroundColor: "var(--orcia-surface-elevated)",
          padding: "16px",
          display: "flex",
          flexDirection: "column",
          gap: "12px",
        }}
      >
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
          }}
        >
          <strong style={{ fontSize: "0.9375rem" }}>⌘K — {labels.modalTitle}</strong>
          <button
            type="button"
            data-testid="command-palette-close"
            onClick={onClose}
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

        <input
          type="search"
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
    </div>
  );
}
