import React from "react";
import type { DiscoveredModelOption, OrciaModelComboboxLabels } from "./OrciaModelCombobox";

export function OrciaModelComboboxDropdown({
  effectiveId,
  listboxId,
  testId,
  value,
  displayedModels,
  highlightedIndex,
  labels,
  onSelect,
  onHighlight,
}: {
  readonly effectiveId: string;
  readonly listboxId: string;
  readonly testId: string;
  readonly value: string;
  readonly displayedModels: readonly DiscoveredModelOption[];
  readonly highlightedIndex: number;
  readonly labels: OrciaModelComboboxLabels;
  readonly onSelect: (modelId: string) => void;
  readonly onHighlight: (index: number) => void;
}): React.JSX.Element {
  return (
    <div
      id={listboxId}
      role="listbox"
      data-testid={`${testId}-suggestions`}
      style={{
        position: "absolute",
        top: "calc(100% + 4px)",
        left: 0,
        right: 0,
        zIndex: 100,
        maxHeight: "240px",
        overflowY: "auto",
        backgroundColor: "var(--color-surface-card)",
        border: "1px solid var(--color-border)",
        borderRadius: "var(--radius-sm)",
        boxShadow: "var(--shadow-md, 0 4px 12px rgba(0, 0, 0, 0.15))",
        padding: "4px 0",
      }}
    >
      {displayedModels.length === 0 ? (
        <div
          data-testid={`${testId}-no-match`}
          style={{
            padding: "8px 12px",
            fontSize: "12px",
            color: "var(--color-muted-foreground)",
          }}
        >
          {labels.noModelsFound}
          {labels.freeformHint && (
            <div style={{ fontSize: "11px", marginTop: "2px", opacity: 0.8 }}>
              {labels.freeformHint}
            </div>
          )}
        </div>
      ) : (
        displayedModels.map((model, idx) => {
          const isSelected = model.id.toLowerCase() === value.toLowerCase().trim();
          const isHighlighted = idx === highlightedIndex;
          return (
            <div
              key={model.id}
              id={`${effectiveId}-opt-${model.id}`}
              role="option"
              aria-selected={isSelected || isHighlighted}
              data-testid={`${testId}-option-${model.id}`}
              onMouseDown={(e) => {
                e.preventDefault();
                onSelect(model.id);
              }}
              onMouseEnter={() => onHighlight(idx)}
              style={{
                padding: "7px 12px",
                fontSize: "12px",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: "8px",
                backgroundColor: isHighlighted ? "var(--color-action-primary-subtle)" : "transparent",
                color: isHighlighted ? "var(--color-primary-cobalt)" : "var(--color-foreground)",
              }}
            >
              <div style={{ display: "flex", flexDirection: "column", gap: "2px" }}>
                <span style={{ fontWeight: isSelected ? 600 : 500, fontFamily: "var(--font-mono)", fontSize: "12px" }}>
                  {model.id}
                </span>
                {model.displayName && model.displayName !== model.id && (
                  <span style={{ fontSize: "11px", color: "var(--color-muted-foreground)" }}>
                    {model.displayName}
                  </span>
                )}
              </div>
              <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
                {model.usageHint === "chat" && labels.chatBadge && (
                  <span
                    style={{
                      fontSize: "10px",
                      fontWeight: 600,
                      padding: "1px 5px",
                      borderRadius: "var(--radius-xs, 3px)",
                      backgroundColor: "var(--color-action-primary-subtle)",
                      color: "var(--color-primary-cobalt)",
                    }}
                  >
                    {labels.chatBadge}
                  </span>
                )}
                {model.usageHint === "embedding" && labels.embeddingBadge && (
                  <span
                    style={{
                      fontSize: "10px",
                      fontWeight: 600,
                      padding: "1px 5px",
                      borderRadius: "var(--radius-xs, 3px)",
                      backgroundColor: "var(--color-bg-elevated)",
                      color: "var(--color-foreground)",
                      border: "1px solid var(--color-border)",
                    }}
                  >
                    {labels.embeddingBadge}
                  </span>
                )}
              </div>
            </div>
          );
        })
      )}
    </div>
  );
}
