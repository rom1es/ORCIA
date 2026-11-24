import * as DialogPrimitive from "@radix-ui/react-dialog";
import React from "react";
import { OrciaIcon } from "../components/icons";
import {
  DEFAULT_EIGHT_FIXED_MENU_ENTRIES,
  type DoubleScopeSelectorLabels,
  type EightFixedMenuKey,
  type FourZoneDirectionCShellLabels,
  type MobileCompanionBottomTabKey,
  type MobileCompanionTabLabels,
  type ScopeOptionItem,
  type UnifiedScopeOptionGroup,
} from "./FourZoneShellTypes";

export interface MobileCompanionBottomBarProps {
  readonly activeTab: MobileCompanionBottomTabKey | null;
  readonly labels: MobileCompanionTabLabels;
  readonly onSelectTab: (tab: MobileCompanionBottomTabKey) => void;
}

export function MobileCompanionBottomBar({
  activeTab,
  labels,
  onSelectTab,
}: MobileCompanionBottomBarProps): React.ReactElement {
  const tabs: ReadonlyArray<{
    readonly key: MobileCompanionBottomTabKey;
    readonly iconName: "cockpit" | "assistant" | "notifications";
    readonly label: string;
  }> = [
    { key: "cockpit", iconName: "cockpit", label: labels.cockpit },
    { key: "assistant", iconName: "assistant", label: labels.assistant },
    { key: "decisions", iconName: "notifications", label: labels.decisions },
  ];

  return (
    <nav
      aria-label={labels.navAriaLabel}
      data-testid="mobile-bottom-tab-bar"
      className="fixed inset-x-0 bottom-0 z-30 grid grid-cols-3 gap-1 border-t px-2 py-1.5"
      style={{
        backgroundColor: "var(--color-bg-surface)",
        borderColor: "var(--color-border-subtle)",
      }}
    >
      {tabs.map((tab) => {
        const isActive = activeTab === tab.key;
        return (
          <button
            key={tab.key}
            type="button"
            data-testid={`mobile-companion-tab-${tab.key}`}
            aria-current={isActive ? "page" : undefined}
            onClick={() => onSelectTab(tab.key)}
            className="flex min-w-0 flex-col items-center justify-center gap-0.5 rounded-lg px-1.5 py-1.5 text-[11px] font-semibold"
            style={{
              backgroundColor: isActive
                ? "var(--color-action-primary-subtle)"
                : "transparent",
              color: isActive
                ? "var(--color-action-primary)"
                : "var(--color-text-primary)",
              border: isActive
                ? "1px solid var(--color-action-primary)"
                : "1px solid transparent",
            }}
          >
            <OrciaIcon name={tab.iconName} size={15} />
            <span className="max-w-full truncate">{tab.label}</span>
          </button>
        );
      })}
    </nav>
  );
}

export interface MobileShellNavigationDrawerProps {
  readonly open: boolean;
  readonly activeMenuKey: EightFixedMenuKey | null;
  readonly labels: FourZoneDirectionCShellLabels;
  readonly disabledMenuKeys?: Partial<Record<EightFixedMenuKey, string>>;
  readonly hiddenMenuKeys?: readonly EightFixedMenuKey[];
  readonly teamBuOptions?: readonly ScopeOptionItem[];
  readonly activeTeamBuId?: string;
  readonly onSelectTeamBu?: (scopeId: string) => void;
  readonly workspaceSelectorOptions?: readonly ScopeOptionItem[];
  readonly activeWorkspaceSelectorId?: string;
  readonly onSelectWorkspaceFromSidebar?: (scopeId: string) => void;
  readonly unifiedScopeGroups?: readonly UnifiedScopeOptionGroup[];
  readonly unifiedAllSpacesOption?: ScopeOptionItem;
  readonly unifiedScopeLabel?: string;
  readonly activeUnifiedScopeId?: string;
  readonly onSelectUnifiedScope?: (scopeId: string) => void;
  readonly doubleSelectorLabels?: DoubleScopeSelectorLabels;
  readonly renderSidebarFooter?: (railCollapsed: boolean) => React.ReactNode;
  readonly onSelectMenu: (key: EightFixedMenuKey, route: string) => void;
  readonly onClose: () => void;
}

export function MobileShellNavigationDrawer({
  open,
  activeMenuKey,
  labels,
  disabledMenuKeys,
  hiddenMenuKeys,
  workspaceSelectorOptions,
  activeWorkspaceSelectorId,
  onSelectWorkspaceFromSidebar,
  unifiedScopeGroups,
  unifiedAllSpacesOption,
  unifiedScopeLabel,
  activeUnifiedScopeId,
  onSelectUnifiedScope,
  doubleSelectorLabels,
  renderSidebarFooter,
  onSelectMenu,
  onClose,
}: MobileShellNavigationDrawerProps): React.ReactElement | null {
  if (!open) {
    return null;
  }
  const usesUnifiedGroups = Boolean(unifiedScopeGroups || unifiedAllSpacesOption);
  const hasScopeSelector =
    usesUnifiedGroups || Boolean(workspaceSelectorOptions && workspaceSelectorOptions.length > 0);

  return (
    <DialogPrimitive.Root
      open={open}
      modal={false}
      onOpenChange={(nextOpen) => {
        if (!nextOpen) onClose();
      }}
    >
      <DialogPrimitive.Portal>
        <DialogPrimitive.Content asChild aria-describedby={undefined}>
          <div
            aria-label={labels.sidebarAriaLabel}
            data-testid="mobile-navigation-drawer"
            className="flex flex-col gap-3 overflow-y-auto border-t p-3"
            style={{
              position: "fixed",
              left: 0,
              right: 0,
              top: "52px",
              bottom: "58px",
              zIndex: "var(--z-dialog)",
              backgroundColor: "var(--color-surface-card)",
              borderColor: "var(--color-border-subtle)",
            }}
          >
            <DialogPrimitive.Title className="sr-only">
              {labels.sidebarAriaLabel}
            </DialogPrimitive.Title>
      <div className="flex items-center justify-between gap-2">
        <span className="text-xs font-semibold">{labels.sidebarAriaLabel}</span>
        <button
          type="button"
          data-testid="mobile-navigation-drawer-close"
          onClick={onClose}
          className="rounded border px-2 py-1 text-xs"
          style={{
            backgroundColor: "var(--color-bg-elevated)",
            borderColor: "var(--color-border-subtle)",
          }}
        >
          <OrciaIcon name="close" size={14} />
        </button>
      </div>

      {hasScopeSelector && (
        <div className="flex flex-col gap-2 rounded border p-2" style={{ borderColor: "var(--color-border-subtle)" }}>
          <label className="flex flex-col gap-1 text-[11px] font-medium">
            <span style={{ color: "var(--color-text-secondary)" }}>
              {unifiedScopeLabel ?? doubleSelectorLabels?.workspaceLabel ?? labels.workspacePrefix}
            </span>
            {usesUnifiedGroups ? (
              <select
                value={activeUnifiedScopeId ?? unifiedAllSpacesOption?.id ?? ""}
                onChange={(e) => onSelectUnifiedScope?.(e.target.value)}
                className="w-full rounded border px-2 py-1 text-xs"
                style={{
                  backgroundColor: "var(--color-bg-elevated)",
                  borderColor: "var(--color-border-subtle)",
                  color: "var(--color-text-primary)",
                }}
              >
                {(unifiedScopeGroups ?? []).map((group) => (
                  <optgroup key={group.label} label={group.label}>
                    {group.options.map((opt) => (
                      <option key={opt.id} value={opt.id}>
                        {opt.label}
                      </option>
                    ))}
                  </optgroup>
                ))}
                {unifiedAllSpacesOption && (
                  <option value={unifiedAllSpacesOption.id}>
                    {unifiedAllSpacesOption.label}
                  </option>
                )}
              </select>
            ) : (
              <select
                value={activeWorkspaceSelectorId ?? ""}
                onChange={(e) => onSelectWorkspaceFromSidebar?.(e.target.value)}
                className="w-full rounded border px-2 py-1 text-xs"
                style={{
                  backgroundColor: "var(--color-bg-elevated)",
                  borderColor: "var(--color-border-subtle)",
                  color: "var(--color-text-primary)",
                }}
              >
                <option value="">
                  {doubleSelectorLabels?.allWorkspacesOption ?? ""}
                </option>
                {(workspaceSelectorOptions ?? []).map((opt) => (
                  <option key={opt.id} value={opt.id}>
                    {opt.label}
                  </option>
                ))}
              </select>
            )}
          </label>
        </div>
      )}

      <nav className="flex flex-col gap-1">
        {DEFAULT_EIGHT_FIXED_MENU_ENTRIES.filter(
          (entry) => !hiddenMenuKeys?.includes(entry.key),
        ).map((entry) => {
          const isActive = entry.key === activeMenuKey;
          const disabledReason = disabledMenuKeys?.[entry.key];
          const isDisabled = Boolean(disabledReason);
          return (
            <button
              key={entry.key}
              type="button"
              data-testid={`mobile-drawer-item-${entry.key}`}
              disabled={isDisabled}
              aria-current={isActive ? "page" : undefined}
              onClick={() => {
                if (!isDisabled) {
                  onSelectMenu(entry.key, entry.route);
                  onClose();
                }
              }}
              className="orcia-sidebar-nav-btn gap-2.5 px-2.5 py-2"
              data-active={isActive ? "true" : "false"}
            >
              <OrciaIcon name={entry.iconName} />
              <span className="flex-1 text-left">
                {labels.menuEntries[entry.key] ?? labels.organizationMenuLabel ?? entry.key}
              </span>
            </button>
          );
        })}
      </nav>

      {renderSidebarFooter && (
        <div
          className="mt-auto flex flex-col gap-1 border-t pt-2"
          style={{ borderColor: "var(--color-border-subtle)" }}
        >
          {renderSidebarFooter(false)}
        </div>
      )}
          </div>
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}
