import React from "react";
import type { KnownUserOption } from "./OrciaKnownUserCombobox";

export interface OrciaKnownUserComboboxDropdownProps {
  readonly effectiveId: string;
  readonly listboxId: string;
  readonly inputTestId: string;
  readonly value: string;
  readonly displayedUsers: readonly KnownUserOption[];
  readonly highlightedIndex: number;
  readonly noResultsLabel: string;
  readonly isTruncated: boolean;
  readonly truncatedHint?: string;
  readonly onHighlight: (index: number) => void;
  readonly onSelectUser: (user: KnownUserOption) => void;
}

export function OrciaKnownUserComboboxDropdown({
  effectiveId,
  listboxId,
  inputTestId,
  value,
  displayedUsers,
  highlightedIndex,
  noResultsLabel,
  isTruncated,
  truncatedHint,
  onHighlight,
  onSelectUser,
}: OrciaKnownUserComboboxDropdownProps): React.ReactElement {
  return (
    <div
      id={listboxId}
      role="listbox"
      data-testid={`${inputTestId}-suggestions`}
      style={{
        position: "absolute",
        top: "calc(100% + 4px)",
        left: 0,
        right: 0,
        zIndex: 100,
        maxHeight: "220px",
        overflowY: "auto",
        backgroundColor: "var(--color-surface-card)",
        border: "1px solid var(--color-border)",
        borderRadius: "var(--radius-sm)",
        boxShadow: "var(--shadow-md, 0 4px 12px rgba(0, 0, 0, 0.15))",
        padding: "4px 0",
      }}
    >
      {displayedUsers.length === 0 ? (
        <div
          data-testid={`${inputTestId}-no-match`}
          style={{
            padding: "8px 12px",
            fontSize: "12px",
            color: "var(--color-muted-foreground)",
          }}
        >
          {noResultsLabel}
        </div>
      ) : (
        displayedUsers.map((user, idx) => {
          const isSelected = user.principalId.toLowerCase() === value.toLowerCase().trim();
          const isHighlighted = idx === highlightedIndex;
          return (
            <div
              key={user.principalId}
              id={`${effectiveId}-option-${user.principalId}`}
              role="option"
              aria-selected={isSelected || isHighlighted}
              data-testid={`${inputTestId}-option-${user.principalId}`}
              onMouseDown={(e) => {
                e.preventDefault();
                onSelectUser(user);
              }}
              onMouseEnter={() => onHighlight(idx)}
              style={{
                padding: "8px 12px",
                fontSize: "13px",
                cursor: "pointer",
                display: "flex",
                alignItems: "center",
                justifyContent: "space-between",
                gap: "8px",
                backgroundColor: isHighlighted
                  ? "var(--color-surface-secondary)"
                  : "transparent",
                color: isHighlighted
                  ? "var(--color-primary-cobalt)"
                  : "var(--color-foreground)",
              }}
            >
              <span style={{ fontWeight: isSelected ? 600 : 400 }}>
                {user.displayName}
              </span>
              <span
                style={{
                  fontSize: "11px",
                  color: "var(--color-muted-foreground)",
                  fontFamily: "var(--font-mono)",
                }}
              >
                {user.email && user.email !== user.principalId
                  ? `${user.principalId} (${user.email})`
                  : user.principalId}
              </span>
            </div>
          );
        })
      )}

      {isTruncated && (
        <div
          data-testid={`${inputTestId}-truncated-hint`}
          style={{
            padding: "6px 12px",
            fontSize: "11px",
            color: "var(--color-muted-foreground)",
            borderTop: "1px solid var(--color-border)",
            backgroundColor: "var(--color-surface-secondary)",
            textAlign: "center",
          }}
        >
          {truncatedHint ?? ""}
        </div>
      )}
    </div>
  );
}
