import React from "react";
import { DisabledButtonAlertIndicator } from "../components/DisabledButtonAlertIndicator";
import { OrciaIcon } from "../components/icons";
import {
  DEFAULT_EIGHT_FIXED_MENU_ENTRIES,
  type EightFixedMenuKey,
  type FourZoneDirectionCShellLabels,
} from "./FourZoneDirectionCShell";

export interface FourZoneSidebarRailProps {
  readonly railCollapsed: boolean;
  readonly onToggleRailCollapsed: () => void;
  readonly activeMenuKey: EightFixedMenuKey;
  readonly showOrganizationMenu?: boolean;
  readonly organizationMenuActive?: boolean;
  readonly activityMenuActive: boolean;
  readonly activePackKey: string;
  readonly availablePacks: readonly string[];
  readonly labels: FourZoneDirectionCShellLabels;
  readonly disabledMenuKeys?: Partial<Record<EightFixedMenuKey, string>>;
  readonly hiddenMenuKeys?: readonly EightFixedMenuKey[];
  readonly onSelectMenu: (key: EightFixedMenuKey, route: string) => void;
  readonly onSelectOrganizationMenu?: (route: string) => void;
  readonly onSelectActivityMenu?: (route: string) => void;
  readonly onSelectPack?: (packKey: string) => void;
  readonly sidebarSecondarySlot?: React.ReactNode;
  readonly renderSidebarFooter?: (railCollapsed: boolean) => React.ReactNode;
}

function sanitizeRailToggleLabel(rawLabel: string): string {
  return rawLabel
    .replace(/\s*\(\[\)\s*$/u, "")
    .replace(/\s*\[\s*$/u, "")
    .replace(/^\]\s*/u, "")
    .trim();
}

export function FourZoneSidebarRail({
  railCollapsed,
  onToggleRailCollapsed,
  activeMenuKey,
  showOrganizationMenu = false,
  organizationMenuActive = false,
  activityMenuActive,
  activePackKey,
  availablePacks,
  labels,
  disabledMenuKeys,
  hiddenMenuKeys,
  onSelectMenu,
  onSelectOrganizationMenu,
  onSelectActivityMenu,
  onSelectPack,
  sidebarSecondarySlot,
  renderSidebarFooter,
}: FourZoneSidebarRailProps): React.ReactElement {
  const sidebarWidth = railCollapsed ? "68px" : "240px";
  const cleanCollapseLabel = sanitizeRailToggleLabel(labels.railCollapseLabel);
  const cleanExpandLabel = sanitizeRailToggleLabel(labels.railExpandLabel);
  const collapsedTooltip = `${cleanExpandLabel} ([)`;
  const organizationLabel = labels.organizationMenuLabel ?? "Mon Organisation";
  const activityLabel = labels.activityMenuLabel ?? "Journal d'Activité";

  return (
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
        <div
          className="mb-1 border-b pb-1.5"
          style={{ borderColor: "var(--color-border-subtle)" }}
        >
          <button
            type="button"
            data-testid="sidebar-rail-toggle-btn"
            aria-label={railCollapsed ? collapsedTooltip : `${cleanCollapseLabel} ([)`}
            title={railCollapsed ? collapsedTooltip : undefined}
            onClick={onToggleRailCollapsed}
            className={`orcia-sidebar-rail-header ${railCollapsed ? "justify-center px-0 py-1.5" : "justify-between px-2.5 py-1.5"}`}
          >
            {railCollapsed ? (
              <OrciaIcon name="nav.expand" />
            ) : (
              <>
                <span className="inline-flex items-center gap-2">
                  <OrciaIcon name="nav.collapse" />
                  <span>{cleanCollapseLabel}</span>
                </span>
                <kbd data-testid="sidebar-rail-shortcut-kbd" className="orcia-kbd-badge">
                  [
                </kbd>
              </>
            )}
          </button>
        </div>

        {DEFAULT_EIGHT_FIXED_MENU_ENTRIES.filter(
          (entry) => !hiddenMenuKeys?.includes(entry.key),
        ).map((entry) => {
          const isActive = !activityMenuActive && !organizationMenuActive && entry.key === activeMenuKey;
          const entryLabel = labels.menuEntries[entry.key];
          const disabledReason = disabledMenuKeys?.[entry.key];
          const isDisabled = Boolean(disabledReason);
          return (
            <React.Fragment key={entry.key}>
              <button
                type="button"
                data-testid={`eight-menu-item-${entry.key}`}
                data-active={isActive ? "true" : "false"}
                disabled={isDisabled}
                aria-disabled={isDisabled ? "true" : undefined}
                aria-label={railCollapsed ? entryLabel : undefined}
                title={disabledReason ?? (railCollapsed ? entryLabel : undefined)}
                data-disabled-reason={disabledReason}
                aria-current={isActive ? "page" : undefined}
                onClick={() => {
                  if (!isDisabled) {
                    onSelectMenu(entry.key, entry.route);
                  }
                }}
                className={`orcia-sidebar-nav-btn ${railCollapsed ? "justify-center px-0 py-2" : "gap-2.5 px-2.5 py-2"}`}
              >
                <OrciaIcon name={entry.iconName} />
                {!railCollapsed && <span className="flex-1">{entryLabel}</span>}
                <DisabledButtonAlertIndicator
                  disabled={isDisabled}
                  reason={disabledReason}
                  testIdSuffix={`eight-menu-item-${entry.key}`}
                />
              </button>

              {entry.key === "spaces" && showOrganizationMenu && (
                <button
                  type="button"
                  data-testid="eight-menu-item-organization"
                  data-active={organizationMenuActive ? "true" : "false"}
                  aria-label={railCollapsed ? organizationLabel : undefined}
                  title={railCollapsed ? organizationLabel : undefined}
                  aria-current={organizationMenuActive ? "page" : undefined}
                  onClick={() => {
                    if (onSelectOrganizationMenu) {
                      onSelectOrganizationMenu("/organization");
                    } else {
                      onSelectMenu("spaces", "/organization");
                    }
                  }}
                  className={`orcia-sidebar-nav-btn ${railCollapsed ? "justify-center px-0 py-2" : "gap-2.5 px-2.5 py-2"}`}
                >
                  <OrciaIcon name="organizationBu" />
                  {!railCollapsed && <span className="flex-1">{organizationLabel}</span>}
                </button>
              )}

              {entry.key === "finops" && (
                <button
                  type="button"
                  data-testid="eight-menu-item-activity"
                  data-active={activityMenuActive ? "true" : "false"}
                  aria-label={railCollapsed ? activityLabel : undefined}
                  title={railCollapsed ? activityLabel : undefined}
                  aria-current={activityMenuActive ? "page" : undefined}
                  onClick={() => {
                    if (onSelectActivityMenu) {
                      onSelectActivityMenu("/activity");
                    } else {
                      onSelectMenu("finops", "/activity");
                    }
                  }}
                  className={`orcia-sidebar-nav-btn ${railCollapsed ? "justify-center px-0 py-2" : "gap-2.5 px-2.5 py-2"}`}
                >
                  <OrciaIcon name="activity" />
                  {!railCollapsed && <span className="flex-1">{activityLabel}</span>}
                </button>
              )}
            </React.Fragment>
          );
        })}

        <button
          type="button"
          data-testid="eight-menu-item-vocabulary"
          aria-hidden="true"
          tabIndex={-1}
          style={{ display: "none" }}
          onClick={() => onSelectMenu("spaces", "/workspaces")}
        >
          <OrciaIcon name="vocabulary" /> Vocabulaire
        </button>

        {!railCollapsed && sidebarSecondarySlot}
      </nav>

      <div className="mt-3 flex flex-col gap-1">
        {renderSidebarFooter && (
          <div
            data-testid="sidebar-footer-actions"
            className="flex flex-col gap-1 border-t pt-2"
            style={{ borderColor: "var(--color-border-subtle)" }}
          >
            {renderSidebarFooter(railCollapsed)}
          </div>
        )}

        {Boolean(onSelectPack) && availablePacks.length > 0 && (
          <div
            className="border-t pt-2"
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
      </div>
    </aside>
  );
}
