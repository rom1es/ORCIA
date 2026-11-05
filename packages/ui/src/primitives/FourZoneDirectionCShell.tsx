import React, { useEffect, useState } from "react";

export type EightFixedMenuKey =
  | "cockpit"
  | "assistant"
  | "processes"
  | "agents"
  | "spaces"
  | "finops"
  | "configuration"
  | "help";

export interface EightFixedMenuEntrySpec {
  readonly key: EightFixedMenuKey;
  readonly icon: string;
  readonly route: string;
}

export const DEFAULT_EIGHT_FIXED_MENU_ENTRIES: readonly EightFixedMenuEntrySpec[] = [
  { key: "cockpit", icon: "◈", route: "/cockpit" },
  { key: "assistant", icon: "💬", route: "/assistant" },
  { key: "processes", icon: "☍", route: "/processes" },
  { key: "agents", icon: "🤖", route: "/agents" },
  { key: "spaces", icon: "📦", route: "/spaces" },
  { key: "finops", icon: "📊", route: "/finops" },
  { key: "configuration", icon: "⚙", route: "/configuration" },
  { key: "help", icon: "❓", route: "/help" },
] as const;

export interface FourZoneDirectionCShellLabels {
  readonly workspacePrefix: string;
  readonly searchTriggerPlaceholder: string;
  readonly contextualHelpButtonLabel: string;
  readonly notificationsButtonLabel: string;
  readonly notificationsDrawerTitle: string;
  readonly notificationsEmptyText: string;
  readonly sidebarAriaLabel: string;
  readonly railCollapseLabel: string;
  readonly railExpandLabel: string;
  readonly packSelectorLabel: string;
  readonly helpColumnTitle: string;
  readonly helpColumnExpectedTitle: string;
  readonly helpColumnExpectedBody: string;
  readonly menuEntries: Record<EightFixedMenuKey, string>;
  readonly activityMenuLabel?: string;
}

export interface WorkspaceSwitcherOption {
  readonly id: string;
  readonly label: string;
  readonly groupLabel?: string;
}

export interface FourZoneDirectionCShellProps {
  readonly activeMenuKey: EightFixedMenuKey;
  readonly activityMenuActive?: boolean;
  readonly activeWorkspaceName: string;
  readonly activeScopeId?: string;
  readonly workspaceOptions?: readonly WorkspaceSwitcherOption[];
  readonly activePackKey: string;
  readonly availablePacks: readonly string[];
  readonly userDisplayName: string;
  readonly userHatLabel: string;
  readonly pendingDecisionsTotal: number;
  readonly viewportWidth?: number;
  readonly labels: FourZoneDirectionCShellLabels;
  readonly disabledMenuKeys?: Partial<Record<EightFixedMenuKey, string>>;
  readonly onSelectMenu: (key: EightFixedMenuKey, route: string) => void;
  readonly onSelectActivityMenu?: (route: string) => void;
  readonly onOpenWorkspaceSwitcher?: () => void;
  readonly onSelectWorkspace?: (scopeId: string) => void;
  readonly onOpenSearchCommand?: () => void;
  readonly onSelectPack?: (packKey: string) => void;
  readonly onOpenUserDropdown?: () => void;
  readonly headerUserControl?: React.ReactNode;
  readonly sidebarSecondarySlot?: React.ReactNode;
  readonly helpColumnContent?: React.ReactNode;
  readonly helpColumnOpen?: boolean;
  readonly onHelpColumnOpenChange?: (open: boolean) => void;
  readonly children: React.ReactNode;
}

/**
 * Pure helper computing whether the Contextual Help Column should be open by default:
 * - Open on large screens (>= 1440px) or when pendingDecisionsTotal == 0
 * - Auto-collapsed on standard screens (< 1440px) when pendingDecisionsTotal >= 1
 */
export function computeDefaultHelpColumnOpen(
  viewportWidth: number,
  pendingDecisionsTotal: number,
): boolean {
  if (viewportWidth < 1440 && pendingDecisionsTotal >= 1) {
    return false;
  }
  return true;
}

export function FourZoneDirectionCShell({
  activeMenuKey,
  activityMenuActive = false,
  activeWorkspaceName,
  activeScopeId,
  workspaceOptions,
  activePackKey,
  availablePacks,
  userDisplayName,
  userHatLabel,
  pendingDecisionsTotal,
  viewportWidth = 1440,
  labels,
  disabledMenuKeys,
  onSelectMenu,
  onSelectActivityMenu,
  onOpenWorkspaceSwitcher,
  onSelectWorkspace,
  onOpenSearchCommand,
  onSelectPack,
  onOpenUserDropdown,
  headerUserControl,
  sidebarSecondarySlot,
  helpColumnContent,
  helpColumnOpen: controlledHelpColumnOpen,
  onHelpColumnOpenChange,
  children,
}: FourZoneDirectionCShellProps): React.ReactElement {
  const [railCollapsed, setRailCollapsed] = useState<boolean>(false);
  const [notificationsOpen, setNotificationsOpen] = useState<boolean>(false);
  const [workspaceDropdownOpen, setWorkspaceDropdownOpen] = useState<boolean>(false);
  const [internalHelpColumnOpen, setInternalHelpColumnOpen] = useState<boolean>(() =>
    computeDefaultHelpColumnOpen(viewportWidth, pendingDecisionsTotal),
  );

  const helpColumnOpen =
    controlledHelpColumnOpen !== undefined
      ? controlledHelpColumnOpen
      : internalHelpColumnOpen;

  const updateHelpColumnOpen = (nextOpen: boolean): void => {
    setInternalHelpColumnOpen(nextOpen);
    onHelpColumnOpenChange?.(nextOpen);
  };

  useEffect(() => {
    if (controlledHelpColumnOpen === undefined) {
      setInternalHelpColumnOpen(
        computeDefaultHelpColumnOpen(viewportWidth, pendingDecisionsTotal),
      );
    }
  }, [viewportWidth, pendingDecisionsTotal, controlledHelpColumnOpen]);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent): void => {
      if (event.key === "[") {
        setRailCollapsed((prev) => !prev);
      } else if (event.key === "Escape") {
        setNotificationsOpen(false);
        setWorkspaceDropdownOpen(false);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const sidebarWidth = railCollapsed ? "68px" : "240px";

  return (
    <div
      data-testid="four-zone-direction-c-shell"
      className="flex h-screen min-h-screen flex-col overflow-hidden"
      style={{
        height: "100vh",
        overflow: "hidden",
        backgroundColor: "var(--color-bg-canvas)",
        color: "var(--color-text-primary)",
        fontFamily: "var(--font-sans)",
      }}
    >
      {/* Zone 1: TopHeaderBar (52px) */}
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
                setWorkspaceDropdownOpen((prev) => !prev);
              }
            }}
            className="rounded border px-2.5 py-1 text-xs font-semibold"
            style={{
              backgroundColor: "var(--color-bg-elevated)",
              borderColor: "var(--color-border-subtle)",
              color: "var(--color-text-primary)",
              cursor: "pointer",
            }}
          >
            {labels.workspacePrefix} : {activeWorkspaceName} ⌄
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
                      setWorkspaceDropdownOpen(false);
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
          <span>🔍 {labels.searchTriggerPlaceholder}</span>
          <kbd className="font-mono text-[11px]">⌘K</kbd>
        </button>

        <div className="flex items-center gap-2">
          <button
            type="button"
            data-testid="topbar-contextual-help-toggle"
            onClick={() => updateHelpColumnOpen(!helpColumnOpen)}
            aria-expanded={helpColumnOpen}
            className="rounded border px-2.5 py-1 text-xs font-medium"
            style={{
              backgroundColor: helpColumnOpen
                ? "var(--color-action-primary-subtle)"
                : "var(--color-bg-elevated)",
              borderColor: "var(--color-border-subtle)",
              color: "var(--color-text-primary)",
            }}
          >
            {labels.contextualHelpButtonLabel}
          </button>

          <button
            type="button"
            data-testid="topbar-notifications-toggle"
            onClick={() => setNotificationsOpen((prev) => !prev)}
            aria-expanded={notificationsOpen}
            className="rounded border px-2.5 py-1 text-xs font-medium"
            style={{
              backgroundColor: "var(--color-bg-elevated)",
              borderColor: "var(--color-border-subtle)",
              color: "var(--color-text-primary)",
            }}
          >
            {labels.notificationsButtonLabel}
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
              <span>👤 {userDisplayName}</span>
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

      {/* Optional 420px Notifications Drawer */}
      {notificationsOpen && (
        <aside
          data-testid="topbar-notifications-drawer"
          role="dialog"
          aria-label={labels.notificationsDrawerTitle}
          className="fixed right-0 top-[52px] z-30 border-b border-l p-4 shadow-md"
          style={{
            width: "420px",
            backgroundColor: "var(--color-bg-surface)",
            borderColor: "var(--color-border-subtle)",
          }}
        >
          <div className="flex items-center justify-between">
            <h2 className="text-xs font-semibold">{labels.notificationsDrawerTitle}</h2>
            <button
              type="button"
              data-testid="topbar-notifications-close"
              onClick={() => setNotificationsOpen(false)}
              className="text-xs"
            >
              ✕
            </button>
          </div>
          <p className="mt-2 text-xs" style={{ color: "var(--color-text-secondary)" }}>
            {labels.notificationsEmptyText}
          </p>
        </aside>
      )}

      {/* Body with Zone 2 (Sidebar), Zone 3 (Central 1fr), and Zone 4 (Contextual Help 340px) */}
      <div
        className="flex min-h-0 flex-1 overflow-hidden"
        style={{ height: "calc(100vh - 52px)", overflow: "hidden" }}
      >
        {/* Zone 2: Sidebar (240px / 68px Rail) with 8 fixed unnumbered entries + dedicated Activity Log entry */}
        <aside
          data-testid="four-zone-sidebar"
          data-rail-collapsed={railCollapsed ? "true" : "false"}
          aria-label={labels.sidebarAriaLabel}
          className="flex shrink-0 flex-col justify-between overflow-y-auto border-r p-2 transition-all"
          style={{
            width: sidebarWidth,
            maxHeight: "calc(100vh - 52px)",
            overflowY: "auto",
            backgroundColor: "var(--color-bg-surface)",
            borderColor: "var(--color-border-subtle)",
          }}
        >
          <nav className="flex flex-col gap-1">
            <button
              type="button"
              data-testid="sidebar-rail-toggle-btn"
              onClick={() => setRailCollapsed((prev) => !prev)}
              className="mb-1 self-end rounded px-2 py-0.5 text-[11px]"
              style={{ color: "var(--color-text-secondary)" }}
            >
              {railCollapsed ? labels.railExpandLabel : labels.railCollapseLabel}
            </button>

            {DEFAULT_EIGHT_FIXED_MENU_ENTRIES.map((entry) => {
              const isActive = !activityMenuActive && entry.key === activeMenuKey;
              const entryLabel = labels.menuEntries[entry.key];
              const disabledReason = disabledMenuKeys?.[entry.key];
              const isDisabled = Boolean(disabledReason);
              return (
                <React.Fragment key={entry.key}>
                  <button
                    type="button"
                    data-testid={`eight-menu-item-${entry.key}`}
                    disabled={isDisabled}
                    aria-disabled={isDisabled ? "true" : undefined}
                    title={disabledReason}
                    data-disabled-reason={disabledReason}
                    aria-current={isActive ? "page" : undefined}
                    onClick={() => {
                      if (!isDisabled) {
                        onSelectMenu(entry.key, entry.route);
                      }
                    }}
                    className="flex items-center gap-2.5 rounded px-2.5 py-2 text-left text-xs font-medium"
                    style={{
                      backgroundColor: isActive
                        ? "var(--color-action-primary-subtle)"
                        : "transparent",
                      color: isActive
                        ? "var(--color-action-primary)"
                        : "var(--color-text-primary)",
                      opacity: isDisabled ? 0.45 : 1,
                      cursor: isDisabled ? "not-allowed" : "pointer",
                    }}
                  >
                    <span aria-hidden="true">{entry.icon}</span>
                    {!railCollapsed && <span>{entryLabel}</span>}
                  </button>

                  {entry.key === "finops" && (
                    <button
                      type="button"
                      data-testid="eight-menu-item-activity"
                      aria-current={activityMenuActive ? "page" : undefined}
                      onClick={() => {
                        if (onSelectActivityMenu) {
                          onSelectActivityMenu("/activity");
                        } else {
                          onSelectMenu("finops", "/activity");
                        }
                      }}
                      className="flex items-center gap-2.5 rounded px-2.5 py-2 text-left text-xs font-medium"
                      style={{
                        backgroundColor: activityMenuActive
                          ? "var(--color-action-primary-subtle)"
                          : "transparent",
                        color: activityMenuActive
                          ? "var(--color-action-primary)"
                          : "var(--color-text-primary)",
                        cursor: "pointer",
                      }}
                    >
                      <span aria-hidden="true">📜</span>
                      {!railCollapsed && (
                        <span>{labels.activityMenuLabel ?? "Journal d'Activité"}</span>
                      )}
                    </button>
                  )}
                </React.Fragment>
              );
            })}

            {!railCollapsed && sidebarSecondarySlot}
          </nav>

          {/* Footer active Business Pack selector (shown only when explicitly opted-in) */}
          {Boolean(onSelectPack) && availablePacks.length > 0 && (
            <div
              className="mt-4 border-t pt-2"
              style={{ borderColor: "var(--color-border-subtle)" }}
            >
              {!railCollapsed && (
                <label
                  htmlFor="sidebar-pack-selector-input"
                  className="mb-1 block text-[11px] font-medium"
                  style={{ color: "var(--color-text-secondary)" }}
                >
                  {labels.packSelectorLabel}
                </label>
              )}
              <select
                id="sidebar-pack-selector-input"
                data-testid="sidebar-pack-selector"
                value={activePackKey}
                onChange={(e) => onSelectPack?.(e.target.value)}
                className="w-full rounded border px-2 py-1 font-mono text-xs"
                style={{
                  backgroundColor: "var(--color-bg-elevated)",
                  borderColor: "var(--color-border-subtle)",
                  color: "var(--color-text-primary)",
                }}
              >
                {availablePacks.map((pack) => (
                  <option key={pack} value={pack}>
                    {pack}
                  </option>
                ))}
              </select>
            </div>
          )}
        </aside>

        {/* Zone 3: Central Zone (1fr) — Independent vertical scrollbar */}
        <main
          data-testid="four-zone-central-workspace"
          className="min-h-0 min-w-0 flex-1 overflow-y-auto p-6"
          style={{
            maxHeight: "calc(100vh - 52px)",
            overflowY: "auto",
            backgroundColor: "var(--color-bg-canvas)",
          }}
        >
          {children}
        </main>

        {/* Zone 4: Contextual Help Column (340px) — Independent vertical scrollbar */}
        {helpColumnOpen && (
          <aside
            data-testid="four-zone-contextual-help-column"
            className="min-h-0 shrink-0 overflow-y-auto border-l p-4"
            style={{
              width: "340px",
              maxHeight: "calc(100vh - 52px)",
              overflowY: "auto",
              position: "sticky",
              top: "52px",
              backgroundColor: "var(--color-bg-surface)",
              borderColor: "var(--color-border-subtle)",
            }}
          >
            <div className="flex items-center justify-between">
              <h2 className="text-xs font-semibold">{labels.helpColumnTitle}</h2>
              <button
                type="button"
                data-testid="contextual-help-close-btn"
                onClick={() => updateHelpColumnOpen(false)}
                className="text-xs"
              >
                ✕
              </button>
            </div>
            <div
              className="mt-3 rounded border p-3"
              style={{
                backgroundColor: "var(--color-bg-elevated)",
                borderColor: "var(--color-border-subtle)",
              }}
            >
              <h3 className="text-xs font-semibold">{labels.helpColumnExpectedTitle}</h3>
              <p className="mt-1 text-xs" style={{ color: "var(--color-text-secondary)" }}>
                {labels.helpColumnExpectedBody}
              </p>
            </div>
            {helpColumnContent && <div className="mt-3">{helpColumnContent}</div>}
          </aside>
        )}
      </div>
    </div>
  );
}
