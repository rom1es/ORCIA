import React from "react";
import { OrciaIcon } from "../components/icons";
import type {
  FourZoneDirectionCShellLabels,
  ShellBreadcrumbItem,
  WorkspaceSwitcherOption,
} from "./FourZoneShellTypes";

export interface FourZoneTopHeaderSectionProps {
  readonly isMobile?: boolean;
  readonly railCollapsed?: boolean;
  readonly mobileMenuOpen?: boolean;
  readonly onToggleMobileMenu?: () => void;
  readonly breadcrumbItems?: readonly ShellBreadcrumbItem[];
  readonly onNavigateBreadcrumb?: (route: string) => void;
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
  readonly labels: FourZoneDirectionCShellLabels;
}

export function FourZoneTopHeaderSection({
  isMobile = false,
  railCollapsed = false,
  mobileMenuOpen = false,
  onToggleMobileMenu,
  breadcrumbItems = [],
  onNavigateBreadcrumb,
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
  labels,
}: FourZoneTopHeaderSectionProps): React.ReactElement {
  return (
    <header
      data-testid="four-zone-top-header-bar"
      className={`flex shrink-0 flex-nowrap items-center justify-between border-b min-w-0 ${isMobile ? "gap-1.5 px-2.5" : "gap-3 px-4"}`}
      style={{
        height: "52px",
        backgroundColor: "var(--color-bg-surface)",
        borderColor: "var(--color-border-subtle)",
      }}
    >
      <div className="relative flex min-w-0 flex-1 items-center gap-2">
        {isMobile && onToggleMobileMenu && (
          <button
            type="button"
            data-testid="mobile-menu-drawer-toggle"
            aria-label={labels.mobileTabs?.menuLabel ?? labels.sidebarAriaLabel}
            aria-expanded={mobileMenuOpen}
            onClick={onToggleMobileMenu}
            className="inline-flex h-8 w-8 shrink-0 items-center justify-center rounded border text-xs font-semibold"
            style={{
              backgroundColor: mobileMenuOpen
                ? "var(--color-action-primary-subtle)"
                : "var(--color-bg-elevated)",
              borderColor: "var(--color-border-subtle)",
              color: "var(--color-text-primary)",
            }}
          >
            <OrciaIcon name={mobileMenuOpen ? "close" : "nav.expand"} size={14} />
          </button>
        )}

        {breadcrumbItems.length > 0 && (
          <nav
            aria-label="Fil d'Ariane"
            data-testid="topbar-breadcrumb"
            className="flex min-w-0 items-center gap-1 overflow-hidden text-xs"
            style={{ color: "var(--color-text-secondary)" }}
          >
            {breadcrumbItems.map((item, idx) => {
              const isLast = idx === breadcrumbItems.length - 1;
              return (
                <React.Fragment key={`${item.label}-${idx}`}>
                  {idx > 0 && <OrciaIcon name="chevronRight" size={12} />}
                  {item.route && !isLast && onNavigateBreadcrumb ? (
                    <button
                      type="button"
                      data-testid={`topbar-breadcrumb-link-${idx}`}
                      onClick={() => onNavigateBreadcrumb(item.route!)}
                      className="truncate rounded px-1 py-0.5 hover:underline"
                      style={{ color: "var(--color-text-secondary)", cursor: "pointer" }}
                    >
                      {item.label}
                    </button>
                  ) : (
                    <span
                      data-testid={`topbar-breadcrumb-item-${idx}`}
                      className={`truncate ${isLast ? "font-semibold" : ""}`}
                      style={{
                        color: isLast
                          ? "var(--color-text-primary)"
                          : "var(--color-text-secondary)",
                      }}
                    >
                      {item.label}
                    </span>
                  )}
                </React.Fragment>
              );
            })}
          </nav>
        )}

        {(isMobile || railCollapsed) && (
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
        )}

        {(isMobile || railCollapsed) && workspaceDropdownOpen && workspaceOptions && workspaceOptions.length > 0 && (
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
        aria-label={labels.searchTriggerPlaceholder}
        onClick={onOpenSearchCommand}
        className={`flex shrink-0 items-center justify-between rounded border py-1 text-xs ${
          isMobile ? "px-2" : "w-64 lg:w-80 px-3"
        }`}
        style={{
          backgroundColor: "var(--color-bg-canvas)",
          borderColor: "var(--color-border-subtle)",
          color: "var(--color-text-secondary)",
        }}
      >
        <span className="inline-flex min-w-0 items-center gap-1.5">
          <OrciaIcon name="search" />
          {!isMobile && <span className="truncate">{labels.searchTriggerPlaceholder}</span>}
        </span>
        {!isMobile && <kbd className="orcia-kbd-badge">⌘K</kbd>}
      </button>

      <div className="flex shrink-0 items-center gap-1.5">
        <button
          type="button"
          data-testid="topbar-contextual-help-toggle"
          aria-label={labels.contextualHelpButtonLabel}
          onClick={onToggleHelpColumn}
          aria-expanded={helpColumnOpen}
          className={`inline-flex items-center gap-1.5 rounded border py-1 text-xs font-medium ${
            isMobile ? "px-2" : "px-2.5"
          }`}
          style={{
            backgroundColor: helpColumnOpen
              ? "var(--color-action-primary-subtle)"
              : "var(--color-bg-elevated)",
            borderColor: "var(--color-border-subtle)",
            color: "var(--color-text-primary)",
          }}
        >
          <OrciaIcon name="help" size={14} />
          {!isMobile && <span>{labels.contextualHelpButtonLabel}</span>}
        </button>

        <button
          type="button"
          data-testid="topbar-notifications-toggle"
          aria-label={labels.notificationsButtonLabel}
          onClick={onToggleNotifications}
          aria-expanded={notificationsOpen}
          className={`inline-flex items-center gap-1.5 rounded border py-1 text-xs font-medium ${
            isMobile ? "px-2" : "px-2.5"
          }`}
          style={{
            backgroundColor: notificationsOpen
              ? "var(--color-action-primary-subtle)"
              : "var(--color-bg-elevated)",
            borderColor: "var(--color-border-subtle)",
            color: "var(--color-text-primary)",
          }}
        >
          <OrciaIcon name="notifications" size={14} />
          {!isMobile && <span>{labels.notificationsButtonLabel}</span>}
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
      </div>
    </header>
  );
}
