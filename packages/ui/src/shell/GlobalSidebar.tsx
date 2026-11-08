import React from "react";
import { ORCIA_MODULE_ICON_NAMES, OrciaIcon } from "../components/icons";
import { StatusBadge } from "../primitives/StatusBadge";
import { ScopeSwitcher } from "./ScopeSwitcher";
import type {
  UiHumanProfileBadge,
  UiModuleKey,
  UiScopeNode,
  UiShellLabels,
  UiShellModuleItem,
} from "./types";

export interface GlobalSidebarProps {
  modules: UiShellModuleItem[];
  activeModuleKey: UiModuleKey;
  scopes: UiScopeNode[];
  activeScopeId: string;
  isScopeSwitcherOpen: boolean;
  humanProfile: UiHumanProfileBadge;
  collapsed: boolean;
  labels: UiShellLabels;
  onSelectModule: (moduleKey: UiModuleKey, route: string) => void;
  onToggleCollapsed: () => void;
  onToggleScopeSwitcher: () => void;
  onSelectScope: (scopeId: string) => void;
}

export function GlobalSidebar({
  modules,
  activeModuleKey,
  scopes,
  activeScopeId,
  isScopeSwitcherOpen,
  humanProfile,
  collapsed,
  labels,
  onSelectModule,
  onToggleCollapsed,
  onToggleScopeSwitcher,
  onSelectScope,
}: GlobalSidebarProps) {
  const sortedModules = [...modules]
    .filter((m) => m.enabled)
    .sort((a, b) => a.order - b.order);

  const widthValue = collapsed
    ? "var(--sidebar-collapsed-width)"
    : "var(--sidebar-expanded-width)";

  return (
    <aside
      data-testid="global-sidebar"
      data-collapsed={collapsed ? "true" : "false"}
      aria-label={labels.sidebarNavigationAriaLabel}
      style={{
        width: widthValue,
        minWidth: widthValue,
        maxWidth: widthValue,
        backgroundColor: "var(--color-sidebar-bg)",
        color: "var(--color-sidebar-foreground)",
        borderRight: "1px solid var(--color-sidebar-border)",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        padding: collapsed ? "16px 10px" : "20px 16px",
        boxSizing: "border-box",
        transition: "width 0.18s ease",
      }}
    >
      <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
        {/* Brand Header (Clickable Logo -> Home/Cockpit, no subtitle, no '[' character) */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: collapsed ? "center" : "space-between",
            gap: "8px",
          }}
        >
          {!collapsed && (
            <button
              type="button"
              data-testid="sidebar-brand-home-btn"
              onClick={() => onSelectModule("cockpit", "/cockpit")}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "10px",
                background: "transparent",
                border: "none",
                padding: 0,
                cursor: "pointer",
                textAlign: "left",
                color: "var(--color-sidebar-foreground)",
                fontFamily: "var(--font-sans)",
              }}
            >
              <OrciaIcon
                name="brandLogo"
                style={{
                  width: "32px",
                  height: "32px",
                  borderRadius: "var(--radius-md)",
                  backgroundColor: "var(--color-primary-cobalt)",
                  color: "var(--color-primary-foreground)",
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontWeight: 800,
                  fontSize: "15px",
                  boxShadow: "var(--shadow-card)",
                }}
              />
              <span style={{ fontWeight: 700, fontSize: "18px", letterSpacing: "-0.02em" }}>
                {labels.brandTitle}
              </span>
            </button>
          )}
          <button
            type="button"
            data-testid="sidebar-collapse-toggle"
            aria-label={
              collapsed ? labels.sidebarToggleExpandLabel : labels.sidebarToggleCollapseLabel
            }
            onClick={onToggleCollapsed}
            style={{
              backgroundColor: "var(--color-sidebar-search-bg)",
              color: "var(--color-sidebar-muted)",
              border: "1px solid var(--color-sidebar-border)",
              borderRadius: "var(--radius-sm)",
              padding: "4px 8px",
              cursor: "pointer",
              fontFamily: "var(--font-sans)",
              fontSize: "13px",
            }}
          >
            {collapsed ? "»" : "«"}
          </button>
        </div>

        <ScopeSwitcher
          scopes={scopes}
          activeScopeId={activeScopeId}
          isOpen={isScopeSwitcherOpen}
          labels={labels}
          onToggleOpen={onToggleScopeSwitcher}
          onSelectScope={onSelectScope}
        />

        {/* Clean Navigation List without numbers */}
        <nav aria-label={labels.sidebarNavigationAriaLabel}>
          <ul
            style={{
              listStyle: "none",
              margin: 0,
              padding: 0,
              display: "flex",
              flexDirection: "column",
              gap: "6px",
            }}
          >
            {sortedModules.map((mod) => {
              const isActive = mod.key === activeModuleKey;
              const moduleLabel = labels.modules[mod.key];
              return (
                <li key={mod.key}>
                  <button
                    type="button"
                    data-testid={`sidebar-nav-item-${mod.key}`}
                    data-active={isActive ? "true" : "false"}
                    aria-current={isActive ? "page" : undefined}
                    onClick={() => onSelectModule(mod.key, mod.route)}
                    style={{
                      width: "100%",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: collapsed ? "center" : "space-between",
                      gap: "10px",
                      padding: "10px 12px",
                      borderRadius: "var(--radius-md)",
                      border: "none",
                      backgroundColor: isActive
                        ? "var(--color-sidebar-active-bg)"
                        : "transparent",
                      color: isActive
                        ? "var(--color-sidebar-active-fg)"
                        : "var(--color-sidebar-muted)",
                      fontWeight: isActive ? 600 : 500,
                      cursor: "pointer",
                      textAlign: "left",
                      fontFamily: "var(--font-sans)",
                      fontSize: "var(--font-size-body)",
                      transition: "background-color 0.15s ease, color 0.15s ease",
                    }}
                  >
                    <span style={{ display: "inline-flex", alignItems: "center", gap: "10px" }}>
                      <OrciaIcon
                        name={ORCIA_MODULE_ICON_NAMES[mod.key]}
                        style={{ fontSize: "15px" }}
                      />
                      {!collapsed && <span>{moduleLabel}</span>}
                    </span>

                    {!collapsed && (
                      <span style={{ display: "inline-flex", alignItems: "center", gap: "4px" }}>
                        {mod.contributorBadgeCount > 0 && (
                          <StatusBadge
                            testId={`sidebar-badge-contributor-${mod.key}`}
                            label={String(mod.contributorBadgeCount)}
                            tone="amber"
                            pill
                          />
                        )}
                        {mod.hasStaleWarning && (
                          <StatusBadge
                            testId={`sidebar-badge-stale-${mod.key}`}
                            label={labels.staleWarningBadgeLabel}
                            tone="crimson"
                            pill
                          />
                        )}
                      </span>
                    )}
                  </button>
                </li>
              );
            })}
          </ul>
        </nav>
      </div>

      {/* Compact Footer */}
      <footer
        data-testid="sidebar-human-profile"
        style={{
          borderTop: "1px solid var(--color-sidebar-border)",
          paddingTop: "12px",
          display: "flex",
          flexDirection: "column",
          gap: "6px",
        }}
      >
        {!collapsed ? (
          <>
            <div
              style={{
                fontSize: "11px",
                color: "var(--color-sidebar-muted)",
                fontWeight: 500,
              }}
            >
              {labels.humanProfilePrefixLabel}: {humanProfile.displayName}
            </div>
            {(humanProfile.role || humanProfile.orgUnitName) && (
              <div
                data-testid="sidebar-human-profile-org"
                style={{
                  fontSize: "11px",
                  fontFamily: "var(--font-mono)",
                  color: "var(--color-sidebar-foreground)",
                }}
              >
                {[humanProfile.role, humanProfile.orgUnitName].filter(Boolean).join(" · ")}
              </div>
            )}
            <StatusBadge
              testId="sidebar-access-mode-badge"
              label={labels.accessModes[humanProfile.accessMode]}
              tone={
                humanProfile.accessMode === "CONTRIBUTOR_ACTION_REQUIRED" ? "emerald" : "neutral"
              }
            />
          </>
        ) : (
          <StatusBadge label={humanProfile.archetypeKey.slice(0, 2)} tone="cobalt" />
        )}
      </footer>
    </aside>
  );
}
