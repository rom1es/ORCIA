import React, { useState } from "react";
import { StatusBadge } from "../primitives/StatusBadge";
import type { UiModuleKey, UiShellLabels } from "./types";

export interface ConciergeDockProps {
  activeModuleKey: UiModuleKey;
  activeScopeId: string;
  collapsed: boolean;
  labels: UiShellLabels;
  onToggleCollapsed: () => void;
  onSubmitPrompt?: (prompt: string) => void;
}

export function ConciergeDock({
  activeModuleKey,
  activeScopeId,
  collapsed,
  labels,
  onToggleCollapsed,
  onSubmitPrompt,
}: ConciergeDockProps) {
  const [promptValue, setPromptValue] = useState("");

  if (collapsed) {
    return (
      <aside
        data-testid="concierge-dock"
        data-collapsed="true"
        style={{
          width: "48px",
          minWidth: "48px",
          backgroundColor: "var(--color-dock-bg)",
          borderLeft: "1px solid var(--color-border)",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          padding: "12px 4px",
          boxSizing: "border-box",
        }}
      >
        <button
          type="button"
          data-testid="concierge-dock-toggle"
          aria-label={labels.conciergeDockToggleExpandLabel}
          onClick={onToggleCollapsed}
          style={{
            backgroundColor: "var(--color-surface-card)",
            color: "var(--color-foreground)",
            border: "1px solid var(--color-border)",
            borderRadius: "var(--radius-sm)",
            padding: "4px 6px",
            cursor: "pointer",
            fontFamily: "var(--font-mono)",
          }}
        >
          ] «
        </button>
      </aside>
    );
  }

  return (
    <aside
      data-testid="concierge-dock"
      data-collapsed="false"
      style={{
        width: "var(--dock-width)",
        minWidth: "var(--dock-width)",
        maxWidth: "var(--dock-width)",
        backgroundColor: "var(--color-dock-bg)",
        borderLeft: "1px solid var(--color-border)",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        padding: "14px",
        boxSizing: "border-box",
      }}
    >
      <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
        <header
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            gap: "8px",
          }}
        >
          <div>
            <strong style={{ display: "block" }}>{labels.conciergeDockTitle}</strong>
            <span
              style={{
                fontSize: "var(--font-size-mono)",
                color: "var(--color-muted-foreground)",
              }}
            >
              {labels.conciergeDockSubtitle}
            </span>
          </div>
          <button
            type="button"
            data-testid="concierge-dock-toggle"
            aria-label={labels.conciergeDockToggleCollapseLabel}
            onClick={onToggleCollapsed}
            style={{
              backgroundColor: "var(--color-surface-card)",
              color: "var(--color-foreground)",
              border: "1px solid var(--color-border)",
              borderRadius: "var(--radius-sm)",
              padding: "4px 8px",
              cursor: "pointer",
              fontFamily: "var(--font-mono)",
            }}
          >
            » ]
          </button>
        </header>

        <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
          <StatusBadge
            testId="concierge-permission-broker-status"
            label={labels.conciergePermissionBrokerReadyLabel}
            tone="emerald"
          />
          <StatusBadge
            label={`${activeModuleKey} • ${activeScopeId}`}
            tone="cobalt"
            monospace
          />
        </div>
      </div>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          if (promptValue.trim()) {
            onSubmitPrompt?.(promptValue.trim());
            setPromptValue("");
          }
        }}
        style={{
          display: "flex",
          flexDirection: "column",
          gap: "8px",
          borderTop: "1px solid var(--color-border)",
          paddingTop: "10px",
        }}
      >
        <input
          type="text"
          data-testid="concierge-prompt-input"
          aria-label={labels.conciergeInputPlaceholder}
          placeholder={labels.conciergeInputPlaceholder}
          value={promptValue}
          onChange={(e) => setPromptValue(e.target.value)}
          style={{
            width: "100%",
            padding: "8px",
            borderRadius: "var(--radius-sm)",
            border: "1px solid var(--color-border)",
            backgroundColor: "var(--color-surface-card)",
            color: "var(--color-foreground)",
            fontFamily: "var(--font-sans)",
            boxSizing: "border-box",
          }}
        />
        <button
          type="submit"
          data-testid="concierge-prompt-submit"
          style={{
            backgroundColor: "var(--color-primary-cobalt)",
            color: "var(--color-primary-foreground)",
            border: "none",
            borderRadius: "var(--radius-sm)",
            padding: "8px 12px",
            fontWeight: 600,
            cursor: "pointer",
          }}
        >
          {labels.conciergeSendLabel}
        </button>
      </form>
    </aside>
  );
}
