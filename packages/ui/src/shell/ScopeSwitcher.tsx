import React from "react";
import { getOrciaIconGlyph, ORCIA_SCOPE_LEVEL_ICON_NAMES } from "../components/icons";
import { StatusBadge } from "../primitives/StatusBadge";
import type { UiScopeNode, UiShellLabels } from "./types";

export interface ScopeSwitcherProps {
  scopes: UiScopeNode[];
  activeScopeId: string;
  isOpen: boolean;
  labels: UiShellLabels;
  onToggleOpen: () => void;
  onSelectScope: (scopeId: string) => void;
}

export function ScopeSwitcher({
  scopes,
  activeScopeId,
  isOpen,
  labels,
  onToggleOpen,
  onSelectScope,
}: ScopeSwitcherProps) {
  const activeScope = scopes.find((s) => s.id === activeScopeId) ?? scopes[0];

  return (
    <div data-testid="scope-switcher-container">
      <button
        type="button"
        data-testid="scope-switcher-trigger"
        aria-expanded={isOpen}
        aria-haspopup="dialog"
        onClick={onToggleOpen}
        style={{
          width: "100%",
          display: "flex",
          alignItems: "center",
          justifyContent: "space-between",
          gap: "8px",
          padding: "8px 10px",
          borderRadius: "var(--radius-md)",
          border: "1px solid var(--color-sidebar-border)",
          backgroundColor: "var(--color-sidebar-border)",
          color: "var(--color-sidebar-foreground)",
          cursor: "pointer",
          textAlign: "left",
          fontFamily: "var(--font-sans)",
        }}
      >
        <span style={{ overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
          {activeScope
            ? `${getOrciaIconGlyph(ORCIA_SCOPE_LEVEL_ICON_NAMES[activeScope.level])} ${activeScope.name}`
            : labels.scopeSwitcherButtonLabel}
        </span>
        <kbd
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "var(--font-size-mono)",
            color: "var(--color-sidebar-muted)",
          }}
        >
          ⌘W
        </kbd>
      </button>

      {isOpen && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label={labels.scopeSwitcherDialogTitle}
          data-testid="scope-switcher-dialog"
          style={{
            position: "fixed",
            top: "72px",
            left: "24px",
            zIndex: 50,
            width: "420px",
            maxWidth: "90vw",
            backgroundColor: "var(--color-surface-card)",
            color: "var(--color-foreground)",
            border: "1px solid var(--color-border)",
            borderRadius: "var(--radius-lg)",
            padding: "16px",
          }}
        >
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              alignItems: "center",
              marginBottom: "12px",
            }}
          >
            <strong style={{ fontSize: "var(--font-size-body)" }}>
              {labels.scopeSwitcherDialogTitle}
            </strong>
            <button
              type="button"
              data-testid="scope-switcher-close"
              onClick={onToggleOpen}
              style={{
                background: "transparent",
                border: "1px solid var(--color-border)",
                borderRadius: "var(--radius-sm)",
                padding: "4px 8px",
                cursor: "pointer",
                color: "var(--color-foreground)",
              }}
            >
              {labels.scopeSwitcherCloseLabel}
            </button>
          </div>

          <ul
            style={{
              listStyle: "none",
              margin: 0,
              padding: 0,
              display: "flex",
              flexDirection: "column",
              gap: "6px",
            }}
          >
            {scopes.map((scope) => {
              const isSelected = scope.id === activeScopeId;
              return (
                <li key={scope.id}>
                  <button
                    type="button"
                    data-testid={`scope-option-${scope.id}`}
                    data-scope-level={scope.level}
                    onClick={() => {
                      onSelectScope(scope.id);
                      onToggleOpen();
                    }}
                    style={{
                      width: "100%",
                      display: "flex",
                      justifyContent: "space-between",
                      alignItems: "center",
                      padding: "8px 10px",
                      borderRadius: "var(--radius-md)",
                      border: isSelected
                        ? "1px solid var(--color-primary-cobalt)"
                        : "1px solid var(--color-border)",
                      backgroundColor: isSelected
                        ? "var(--color-ontology-bg)"
                        : "var(--color-surface-card)",
                      color: "var(--color-foreground)",
                      cursor: "pointer",
                      textAlign: "left",
                    }}
                  >
                    <span>
                      {getOrciaIconGlyph(ORCIA_SCOPE_LEVEL_ICON_NAMES[scope.level])} [{labels.scopeLevels[scope.level]}] {scope.name}
                    </span>
                    <StatusBadge
                      label={labels.accessModes[scope.accessMode]}
                      tone={
                        scope.accessMode === "CONTRIBUTOR_ACTION_REQUIRED" ? "emerald" : "neutral"
                      }
                    />
                  </button>
                </li>
              );
            })}
          </ul>
        </div>
      )}
    </div>
  );
}
