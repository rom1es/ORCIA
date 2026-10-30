import React, { useState } from "react";

export interface CollapsibleAppRailLabels {
  readonly railAriaLabel: string;
  readonly expandRailCta: string;
  readonly collapseRailCta: string;
  readonly activePackPrefix: string;
  readonly actionRequiredBadgeLabel: string;
  readonly outboxHealthyLabel: string;
}

export interface CollapsibleAppRailProps {
  readonly activePackKey?: string;
  readonly actionRequiredCount?: number;
  readonly outboxPendingCount?: number;
  readonly defaultCollapsed?: boolean;
  readonly labels: CollapsibleAppRailLabels;
  readonly onToggleCollapsed?: (collapsed: boolean) => void;
}

export function CollapsibleAppRail({
  activePackKey = "orcia-pack-sdlc",
  actionRequiredCount = 2,
  outboxPendingCount = 0,
  defaultCollapsed = false,
  labels,
  onToggleCollapsed,
}: CollapsibleAppRailProps) {
  const [collapsed, setCollapsed] = useState(defaultCollapsed);

  const toggle = () => {
    const next = !collapsed;
    setCollapsed(next);
    onToggleCollapsed?.(next);
  };

  return (
    <aside
      aria-label={labels.railAriaLabel}
      data-testid="collapsible-app-rail"
      data-rail-mode={collapsed ? "rail-72px" : "expanded-240px"}
      onKeyDown={(e) => {
        if (e.key === "[") {
          toggle();
        }
      }}
      style={{
        width: collapsed ? "72px" : "240px",
        transition: "width 150ms ease-in-out",
        padding: "10px",
        borderRadius: "10px",
        border: "1px solid var(--orcia-border-subtle)",
        backgroundColor: "var(--orcia-surface-elevated)",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        gap: "12px",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        {!collapsed ? (
          <strong style={{ fontSize: "0.8125rem" }}>ORCIA Rail</strong>
        ) : null}
        <button
          type="button"
          data-testid="collapsible-rail-toggle-btn"
          aria-expanded={!collapsed}
          onClick={toggle}
          style={{
            padding: "4px 8px",
            borderRadius: "6px",
            fontSize: "0.75rem",
            fontFamily: "var(--orcia-font-mono)",
            border: "1px solid var(--orcia-border-subtle)",
            backgroundColor: "var(--orcia-surface-secondary)",
            color: "var(--orcia-text-primary)",
            cursor: "pointer",
          }}
        >
          [ {collapsed ? labels.expandRailCta : labels.collapseRailCta}
        </button>
      </div>

      <footer
        style={{
          display: "flex",
          flexDirection: "column",
          gap: "6px",
          borderTop: "1px solid var(--orcia-border-subtle)",
          paddingTop: "8px",
        }}
      >
        <span
          data-testid="active-pack-badge"
          style={{
            fontSize: "0.7rem",
            fontFamily: "var(--orcia-font-mono)",
            padding: "2px 6px",
            borderRadius: "4px",
            border: "1px solid var(--orcia-border-subtle)",
            backgroundColor: "var(--orcia-surface-secondary)",
          }}
        >
          {collapsed ? "PACK" : `${labels.activePackPrefix}: ${activePackKey}`}
        </span>
        <span
          data-testid="rail-action-required-pill"
          style={{ fontSize: "0.7rem", color: "var(--orcia-text-secondary)" }}
        >
          🔔 {actionRequiredCount} {!collapsed ? labels.actionRequiredBadgeLabel : ""}
        </span>
        <span
          data-testid="rail-outbox-health-pill"
          style={{ fontSize: "0.7rem", color: "var(--orcia-text-secondary)" }}
        >
          🟢 Outbox ({outboxPendingCount}) {!collapsed ? labels.outboxHealthyLabel : ""}
        </span>
      </footer>
    </aside>
  );
}
