import React from "react";
import { handleRgaaSubmitKeyDown } from "../components/RgaaModalDialog.js";
import type {
  CommandPaletteItemSpec,
  CommandPaletteModalLabels,
} from "./CommandPaletteModal";

export function CommandPaletteResultsList({
  filtered,
  labels,
  onSelectItem,
  onClose,
}: {
  readonly filtered: readonly CommandPaletteItemSpec[];
  readonly labels: CommandPaletteModalLabels;
  readonly onSelectItem?: (item: CommandPaletteItemSpec) => void;
  readonly onClose: () => void;
}): React.ReactElement {
  return (
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
  );
}
