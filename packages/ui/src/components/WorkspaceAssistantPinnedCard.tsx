import React from "react";
import { OrciaIcon } from "./icons";

export interface WorkspaceAssistantPinnedCardProps {
  readonly mcpExposed?: boolean;
  readonly onToggleMcpExposed?: (nextExposed: boolean) => void;
  readonly onOpenSettings?: () => void;
  readonly onOpenAssistant?: () => void;
}

export const WorkspaceAssistantPinnedCard: React.FC<WorkspaceAssistantPinnedCardProps> = ({
  mcpExposed = false,
  onToggleMcpExposed,
  onOpenSettings,
  onOpenAssistant,
}) => {
  return (
    <div
      data-testid="workspace-assistant-pinned-card"
      className="flex flex-wrap items-center justify-between gap-3 rounded-lg border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] p-3.5 text-xs"
    >
      <div className="space-y-1">
        <div className="flex flex-wrap items-center gap-2">
          <strong className="text-sm text-[var(--orcia-text-primary)]">
            <OrciaIcon name="agents" /> Assistant de l&apos;Espace
          </strong>
          <code className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-1.5 py-0.5 font-mono text-[11px]">
            @assistant
          </code>
          <span className="rounded-full border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2.5 py-0.5 text-[11px] font-medium">
            <OrciaIcon name="pin" /> Épinglé · Chef d&apos;orchestre de l&apos;Espace
          </span>
        </div>
        <p className="text-[var(--orcia-text-secondary)]">
          Adapte automatiquement son niveau de synthèse à votre rôle métier, interroge les sources
          de l&apos;Espace et coordonne vos agents spécialisés.
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
            <OrciaIcon name="plug" /> Exposer en MCP
          </span>
        </label>
        <button
          type="button"
          data-testid="pinned-assistant-settings-btn"
          onClick={onOpenSettings}
          className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2.5 py-1 text-[11px] font-medium"
        >
          <OrciaIcon name="configuration" /> Réglages de l&apos;assistant
        </button>
        <button
          type="button"
          data-testid="pinned-assistant-open-btn"
          onClick={onOpenAssistant}
          className="rounded bg-[var(--orcia-action-primary)] px-3 py-1 text-[11px] font-semibold text-[var(--orcia-text-on-action)]"
        >
          <OrciaIcon name="assistant" /> Ouvrir Mon Assistant →
        </button>
      </div>
    </div>
  );
};
