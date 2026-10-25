import React, { useState } from "react";
import { StatusBadge } from "../primitives/StatusBadge";
import { PermissionBrokerCard } from "./PermissionBrokerCard";
import type {
  UiModuleKey,
  UiPermissionBrokerLabels,
  UiPermissionBrokerTicketView,
  UiShellLabels,
} from "./types";

export interface AssistantDockProps {
  activeModuleKey: UiModuleKey;
  activeScopeId: string;
  collapsed: boolean;
  labels: UiShellLabels;
  permissionBrokerTicket?: UiPermissionBrokerTicketView | null;
  permissionBrokerLabels?: UiPermissionBrokerLabels;
  onToggleCollapsed: () => void;
  onSubmitPrompt?: (prompt: string) => void;
  onPausePermissionStep?: (ticketId: string) => void;
  onReplayPermissionStep?: (ticketId: string) => void;
}

export function AssistantDock({
  activeModuleKey,
  activeScopeId,
  collapsed,
  labels,
  permissionBrokerTicket,
  permissionBrokerLabels,
  onToggleCollapsed,
  onSubmitPrompt,
  onPausePermissionStep,
  onReplayPermissionStep,
}: AssistantDockProps) {
  const [promptValue, setPromptValue] = useState("");
  const hasWaitingDenial =
    permissionBrokerTicket?.status === "WAITING_FOR_PERMISSION" ||
    permissionBrokerTicket?.stepState === "PERMISSION_DENIED_STEP";

  if (collapsed) {
    return (
      <aside
        data-testid="assistant-dock"
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
          data-testid="assistant-dock-toggle"
          aria-label={labels.assistantDockToggleExpandLabel}
          onClick={onToggleCollapsed}
          style={{
            backgroundColor: "var(--color-surface-card)",
            color: "var(--color-foreground)",
            border: "1px solid var(--color-border)",
            borderRadius: "var(--radius-sm)",
            padding: "4px 8px",
            cursor: "pointer",
            fontFamily: "var(--font-sans)",
            fontSize: "13px",
          }}
        >
          «
        </button>
      </aside>
    );
  }

  return (
    <aside
      data-testid="assistant-dock"
      data-collapsed="false"
      style={{
        width: "min(var(--dock-width), 48vw)",
        minWidth: "min(var(--dock-width), 48vw)",
        maxWidth: "min(var(--dock-width), 48vw)",
        backgroundColor: "var(--color-dock-bg)",
        borderLeft: "1px solid var(--color-border)",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        padding: "16px",
        boxSizing: "border-box",
        gap: "12px",
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
            <strong style={{ display: "block" }}>{labels.assistantDockTitle}</strong>
            <span
              style={{
                fontSize: "var(--font-size-mono)",
                color: "var(--color-muted-foreground)",
              }}
            >
              {labels.assistantDockSubtitle}
            </span>
          </div>
          <button
            type="button"
            data-testid="assistant-dock-toggle"
            aria-label={labels.assistantDockToggleCollapseLabel}
            onClick={onToggleCollapsed}
            style={{
              backgroundColor: "var(--color-surface-card)",
              color: "var(--color-foreground)",
              border: "1px solid var(--color-border)",
              borderRadius: "var(--radius-sm)",
              padding: "4px 8px",
              cursor: "pointer",
              fontFamily: "var(--font-sans)",
              fontSize: "13px",
            }}
          >
            »
          </button>
        </header>

        <div style={{ display: "flex", gap: "6px", flexWrap: "wrap" }}>
          <StatusBadge
            testId="assistant-permission-broker-status"
            label={labels.assistantPermissionBrokerReadyLabel}
            tone={hasWaitingDenial ? "amber" : "emerald"}
          />
          <StatusBadge
            label={`${activeModuleKey} • ${activeScopeId}`}
            tone="cobalt"
            monospace
          />
        </div>

        {permissionBrokerTicket && permissionBrokerLabels && (
          <PermissionBrokerCard
            ticket={permissionBrokerTicket}
            labels={permissionBrokerLabels}
            onPauseStep={onPausePermissionStep}
            onReplayStep={onReplayPermissionStep}
          />
        )}
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
          data-testid="assistant-prompt-input"
          aria-label={labels.assistantInputPlaceholder}
          placeholder={labels.assistantInputPlaceholder}
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
          data-testid="assistant-prompt-submit"
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
          {labels.assistantSendLabel}
        </button>
      </form>
    </aside>
  );
}
