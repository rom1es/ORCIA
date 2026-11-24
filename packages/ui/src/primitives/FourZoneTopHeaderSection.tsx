import React from "react";
import { OrciaIcon } from "../components/icons";
import type {
  FourZoneDirectionCShellLabels,
  ShellBreadcrumbItem,
  WorkspaceSwitcherOption,
} from "./FourZoneShellTypes";
import { FourZoneTopHeaderWorkspaceSelector } from "./FourZoneTopHeaderSelectors";

export interface FourZoneTopHeaderSectionProps {
  readonly isMobile?: boolean;
  readonly railCollapsed?: boolean;
  readonly mobileMenuOpen?: boolean;
  readonly onToggleMobileMenu?: () => void;
  readonly breadcrumbItems?: readonly ShellBreadcrumbItem[];
  readonly onNavigateBreadcrumb?: (route: string) => void;
  readonly onNavigateHome?: () => void;
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
  onNavigateHome,
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
  const brandName = labels.brandName ?? "ORCIA";
  const trailingBreadcrumbItems = breadcrumbItems.filter(
    (item, idx) => !(idx === 0 && item.label.trim().toUpperCase() === brandName.toUpperCase()),
  );

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

        <nav
          aria-label={labels.breadcrumbAriaLabel}
          data-testid="topbar-breadcrumb"
          className="flex min-w-0 items-center gap-1 overflow-hidden text-xs"
          style={{ color: "var(--color-text-secondary)" }}
        >
          <button
            type="button"
            data-testid="topbar-orcia-home-link"
            onClick={() => {
              if (onNavigateHome) onNavigateHome();
              else onNavigateBreadcrumb?.("/cockpit");
            }}
            className="inline-flex shrink-0 items-center gap-1.5 rounded px-1.5 py-1 text-sm font-bold tracking-tight hover:opacity-90"
            style={{ color: "var(--color-text-primary)", cursor: "pointer" }}
          >
            <span
              className="inline-flex h-5 w-5 items-center justify-center rounded text-[11px] font-bold"
              style={{
                backgroundColor: "var(--color-action-primary)",
                color: "var(--color-bg-surface)",
              }}
            >
              {brandName.slice(0, 1)}
            </span>
            <span>{brandName}</span>
          </button>

          {trailingBreadcrumbItems.map((item, idx) => {
            const isLast = idx === trailingBreadcrumbItems.length - 1;
            return (
              <React.Fragment key={`${item.label}-${idx}`}>
                <OrciaIcon name="chevronRight" size={12} />
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

        <FourZoneTopHeaderWorkspaceSelector
          isMobile={isMobile}
          railCollapsed={railCollapsed}
          activeWorkspaceName={activeWorkspaceName}
          activeScopeId={activeScopeId}
          workspaceOptions={workspaceOptions}
          workspaceDropdownOpen={workspaceDropdownOpen}
          onToggleWorkspaceDropdown={onToggleWorkspaceDropdown}
          onCloseWorkspaceDropdown={onCloseWorkspaceDropdown}
          onOpenWorkspaceSwitcher={onOpenWorkspaceSwitcher}
          onSelectWorkspace={onSelectWorkspace}
          labels={labels}
        />
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
