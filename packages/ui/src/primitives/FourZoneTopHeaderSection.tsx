import React from "react";
import { OrciaIcon } from "../components/icons";
import type {
  FourZoneDirectionCShellLabels,
  WorkspaceSwitcherOption,
} from "./FourZoneDirectionCShell";

export interface FourZoneTopHeaderSectionProps {
  readonly activeWorkspaceName: string;
  readonly activeScopeId?: string;
  readonly workspaceOptions?: readonly WorkspaceSwitcherOption[];
  readonly workspaceDropdownOpen: boolean;
  readonly onToggleWorkspaceDropdown: () => void;
  readonly onCloseWorkspaceDropdown: () => void;
  readonly onOpenWorkspaceSwitcher?: () => void;
  readonly onSelectWorkspace?: (scopeId: string) => void;
  readonly onOpenSearchCommand?: () => void;
  readonly helpColumnOpen: boolean;
  readonly onToggleHelpColumn: () => void;
  readonly notificationsOpen: boolean;
  readonly onToggleNotifications: () => void;
  readonly effectiveNotificationCount: number;
  readonly headerUserControl?: React.ReactNode;
  readonly onOpenUserDropdown?: () => void;
  readonly userDisplayName: string;
  readonly userHatLabel: string;
  readonly labels: FourZoneDirectionCShellLabels;
}

export function FourZoneTopHeaderSection({
  activeWorkspaceName,
  activeScopeId,
  workspaceOptions,
  workspaceDropdownOpen,
  onToggleWorkspaceDropdown,
  onCloseWorkspaceDropdown,
  onOpenWorkspaceSwitcher,
  onSelectWorkspace,
  onOpenSearchCommand,
  helpColumnOpen,
  onToggleHelpColumn,
  notificationsOpen,
  onToggleNotifications,
  effectiveNotificationCount,
  headerUserControl,
  onOpenUserDropdown,
  userDisplayName,
  userHatLabel,
  labels,
}: FourZoneTopHeaderSectionProps): React.ReactElement {
  return (
    <header
      data-testid="four-zone-top-header-bar"
      className="flex shrink-0 items-center justify-between border-b px-4"
      style={{
        height: "52px",
        backgroundColor: "var(--color-bg-surface)",
        borderColor: "var(--color-border-subtle)",
      }}
    >
      <div className="relative flex items-center gap-3">
        <span className="text-sm font-bold tracking-tight">ORCIA</span>
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
          className="inline-flex items-center gap-1.5 rounded border px-2.5 py-1 text-xs font-semibold"
          style={{
            backgroundColor: "var(--color-bg-elevated)",
            borderColor: "var(--color-border-subtle)",
            color: "var(--color-text-primary)",
            cursor: "pointer",
          }}
        >
          <span>
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
                    backgroundColor: isSelected
                      ? "var(--color-action-primary-subtle)"
                      : "transparent",
                    color: isSelected
                      ? "var(--color-action-primary)"
                      : "var(--color-text-primary)",
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
      </div>

      <button
        type="button"
        data-testid="topbar-federated-search-trigger"
        onClick={onOpenSearchCommand}
        className="flex w-96 items-center justify-between rounded border px-3 py-1 text-xs"
        style={{
          backgroundColor: "var(--color-bg-canvas)",
          borderColor: "var(--color-border-subtle)",
          color: "var(--color-text-secondary)",
        }}
      >
        <span className="inline-flex items-center gap-1.5">
          <OrciaIcon name="search" />
          <span>{labels.searchTriggerPlaceholder}</span>
        </span>
        <kbd className="orcia-kbd-badge">⌘K</kbd>
      </button>

      <div className="flex items-center gap-2">
        <button
          type="button"
          data-testid="topbar-contextual-help-toggle"
          onClick={onToggleHelpColumn}
          aria-expanded={helpColumnOpen}
          className="inline-flex items-center gap-1.5 rounded border px-2.5 py-1 text-xs font-medium"
          style={{
            backgroundColor: helpColumnOpen
              ? "var(--color-action-primary-subtle)"
              : "var(--color-bg-elevated)",
            borderColor: "var(--color-border-subtle)",
            color: "var(--color-text-primary)",
          }}
        >
          <OrciaIcon name="help" size={14} />
          <span>{labels.contextualHelpButtonLabel}</span>
        </button>

        <button
          type="button"
          data-testid="topbar-notifications-toggle"
          onClick={onToggleNotifications}
          aria-expanded={notificationsOpen}
          className="inline-flex items-center gap-1.5 rounded border px-2.5 py-1 text-xs font-medium"
          style={{
            backgroundColor: notificationsOpen
              ? "var(--color-action-primary-subtle)"
              : "var(--color-bg-elevated)",
            borderColor: "var(--color-border-subtle)",
            color: "var(--color-text-primary)",
          }}
        >
          <OrciaIcon name="notifications" size={14} />
          <span>{labels.notificationsButtonLabel}</span>
          {effectiveNotificationCount > 0 && (
            <span
              data-testid="topbar-notifications-badge"
              className="inline-flex items-center justify-center rounded-full px-1.5 py-0.5 text-[10px] font-bold"
              style={{
                backgroundColor: "var(--color-arbitration-amber)",
                color: "var(--color-surface-card)",
                minWidth: "18px",
                lineHeight: 1,
              }}
            >
              {effectiveNotificationCount}
            </span>
          )}
        </button>

        {headerUserControl ?? (
          <button
            type="button"
            data-testid="topbar-user-account-trigger"
            onClick={onOpenUserDropdown}
            className="flex items-center gap-2 rounded border px-2.5 py-1 text-xs"
            style={{
              backgroundColor: "var(--color-bg-elevated)",
              borderColor: "var(--color-border-subtle)",
              color: "var(--color-text-primary)",
            }}
          >
            <span className="inline-flex items-center gap-1.5">
              <OrciaIcon name="user" />
              <span>{userDisplayName}</span>
            </span>
            <span
              data-testid="topbar-hat-badge"
              className="rounded px-1.5 py-0.5 text-[11px] font-semibold"
              style={{
                backgroundColor: "var(--color-action-primary-subtle)",
                color: "var(--color-action-primary)",
              }}
            >
              {userHatLabel}
            </span>
          </button>
        )}
      </div>
    </header>
  );
}
