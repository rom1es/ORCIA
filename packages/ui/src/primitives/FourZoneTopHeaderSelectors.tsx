import React from "react";
import { OrciaIcon } from "../components/icons";
import type {
  FourZoneDirectionCShellLabels,
  WorkspaceSwitcherOption,
} from "./FourZoneShellTypes";

export function FourZoneTopHeaderWorkspaceSelector({
  isMobile,
  railCollapsed,
  activeWorkspaceName,
  activeScopeId,
  workspaceOptions,
  workspaceDropdownOpen,
  onToggleWorkspaceDropdown,
  onCloseWorkspaceDropdown,
  onOpenWorkspaceSwitcher,
  onSelectWorkspace,
  labels,
}: {
  readonly isMobile: boolean;
  readonly railCollapsed: boolean;
  readonly activeWorkspaceName: string;
  readonly activeScopeId?: string;
  readonly workspaceOptions?: readonly WorkspaceSwitcherOption[];
  readonly workspaceDropdownOpen: boolean;
  readonly onToggleWorkspaceDropdown: () => void;
  readonly onCloseWorkspaceDropdown: () => void;
  readonly onOpenWorkspaceSwitcher?: () => void;
  readonly onSelectWorkspace?: (scopeId: string) => void;
  readonly labels: FourZoneDirectionCShellLabels;
}): React.JSX.Element | null {
  if (!isMobile && !railCollapsed) {
    return null;
  }

  return (
    <>
      <button
        type="button"
        data-testid="topbar-fixed-workspace-selector"
        aria-haspopup="listbox"
        aria-expanded={workspaceDropdownOpen}
        onClick={() => {
          onOpenWorkspaceSwitcher?.();
          if (workspaceOptions && workspaceOptions.length > 0) {
            onToggleWorkspaceDropdown();
          }
        }}
        className="inline-flex max-w-[240px] shrink-0 items-center gap-1.5 rounded border px-2.5 py-1 text-xs font-semibold"
        style={{
          backgroundColor: "var(--color-bg-elevated)",
          borderColor: "var(--color-border-subtle)",
          color: "var(--color-text-primary)",
          cursor: "pointer",
        }}
      >
        <span className="truncate">
          {labels.workspacePrefix} : {activeWorkspaceName}
        </span>
        <OrciaIcon name="chevronDown" size={14} />
      </button>

      {workspaceDropdownOpen && workspaceOptions && workspaceOptions.length > 0 && (
        <div
          role="listbox"
          aria-label={labels.workspacePrefix}
          data-testid="topbar-workspace-dropdown-menu"
          className="absolute left-12 top-10 z-40 min-w-[260px] rounded-xl border p-1.5 shadow-lg"
          style={{
            backgroundColor: "var(--color-bg-surface)",
            borderColor: "var(--color-border-subtle)",
            color: "var(--color-text-primary)",
          }}
        >
          {workspaceOptions.map((opt) => {
            const isSelected = opt.id === activeScopeId || opt.label === activeWorkspaceName;
            return (
              <button
                key={opt.id}
                type="button"
                role="option"
                aria-selected={isSelected}
                data-testid={`topbar-workspace-option-${opt.id}`}
                onClick={() => {
                  onSelectWorkspace?.(opt.id);
                  onCloseWorkspaceDropdown();
                }}
                className="flex w-full items-center justify-between gap-2 rounded px-2.5 py-1.5 text-left text-xs"
                style={{
                  backgroundColor: isSelected ? "var(--color-action-primary-subtle)" : "transparent",
                  color: isSelected ? "var(--color-action-primary)" : "var(--color-text-primary)",
                  fontWeight: isSelected ? 600 : 400,
                  cursor: "pointer",
                }}
              >
                <span>{opt.label}</span>
                {opt.groupLabel && (
                  <span
                    className="rounded px-1.5 py-0.5 font-mono text-[10px]"
                    style={{
                      backgroundColor: "var(--color-bg-elevated)",
                      color: "var(--color-text-secondary)",
                    }}
                  >
                    {opt.groupLabel}
                  </span>
                )}
              </button>
            );
          })}
        </div>
      )}
    </>
  );
}
