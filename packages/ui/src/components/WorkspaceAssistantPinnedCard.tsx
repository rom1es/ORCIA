import React from "react";
import type { AgentGovernanceStudioLabels } from "./AgentGovernanceTypesAndDefaults";
import { OrciaIcon } from "./icons";

export interface WorkspaceAssistantPinnedCardProps {
  readonly labels: AgentGovernanceStudioLabels;
  readonly mcpExposed?: boolean;
  readonly onToggleMcpExposed?: (nextExposed: boolean) => void;
  readonly onOpenSettings?: () => void;
  readonly onOpenAssistant?: () => void;
}

export const WorkspaceAssistantPinnedCard: React.FC<
  WorkspaceAssistantPinnedCardProps
> = ({
  labels,
  mcpExposed = false,
  onToggleMcpExposed,
  onOpenSettings,
  onOpenAssistant,
}) => {
  return (
    <div
      data-testid="workspace-assistant-pinned-card"
      className="orcia-bento-card flex flex-wrap items-center justify-between gap-3 p-4 text-xs"
    >
      <div className="space-y-1">
        <div className="flex flex-wrap items-center gap-2">
          <strong className="text-sm text-[var(--orcia-text-primary)]">
            <OrciaIcon name="agents" /> {labels.pinnedAssistantTitle}
          </strong>
          <code className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-1.5 py-0.5 font-mono text-[11px]">
            {"@assistant"}
          </code>
          <span className="rounded-full border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2.5 py-0.5 text-[11px] font-medium">
            <OrciaIcon name="pin" /> {labels.pinnedAssistantBadge}
          </span>
        </div>
        <p className="text-[var(--orcia-text-secondary)]">
          {labels.pinnedAssistantDescription}
        </p>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        <label className="inline-flex items-center gap-1.5 rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2.5 py-1 text-[11px] font-medium">
          <input
            type="checkbox"
            autoComplete="off"
            data-lpignore="true"
            data-1p-ignore="true"
            data-bwignore="true"
            data-form-type="other"
            data-testid="pinned-assistant-mcp-toggle"
            checked={mcpExposed}
            onChange={(e) => onToggleMcpExposed?.(e.target.checked)}
          />
          <span>
            <OrciaIcon name="plug" /> {labels.exposeMcpLabel}
          </span>
        </label>
        <button
          type="button"
          data-testid="pinned-assistant-settings-btn"
          onClick={onOpenSettings}
          className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2.5 py-1 text-[11px] font-medium"
        >
          <OrciaIcon name="configuration" />{" "}
          {labels.pinnedAssistantSettingsButton}
        </button>
        <button
          type="button"
          data-testid="pinned-assistant-open-btn"
          onClick={onOpenAssistant}
          className="orcia-ds-btn orcia-ds-btn-cobalt-outline text-[11px]"
        >
          <OrciaIcon name="assistant" /> {labels.pinnedAssistantOpenButton}
        </button>
      </div>
    </div>
  );
};
