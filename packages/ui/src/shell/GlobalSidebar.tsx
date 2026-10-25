import React from "react";
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

const MODULE_ICONS: Record<UiModuleKey, string> = {
  cockpit: "💬",
  inbox: "🔔",
  catalog: "📦",
  ontology: "🧬",
  gates: "🛡️",
  finops: "📊",
  admin: "⚙️",
};

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
        padding: "12px",
        boxSizing: "border-box",
      }}
    >
      <div style={{ display: "flex", flexDirection: "column", gap: "12px" }}>
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            gap: "8px",
          }}
        >
          {!collapsed && (
            <div>
              <div style={{ fontWeight: 700, letterSpacing: "0.04em" }}>{labels.brandTitle}</div>
              <div
                style={{
                  fontSize: "var(--font-size-mono)",
                  color: "var(--color-sidebar-muted)",
                }}
              >
                {labels.brandSubtitle}
              </div>
            </div>
          )}
          <button
            type="button"
            data-testid="sidebar-collapse-toggle"
            aria-label={
              collapsed ? labels.sidebarToggleExpandLabel : labels.sidebarToggleCollapseLabel
            }
            onClick={onToggleCollapsed}
            style={{
              backgroundColor: "var(--color-sidebar-border)",
              color: "var(--color-sidebar-foreground)",
              border: "1px solid var(--color-sidebar-border)",
              borderRadius: "var(--radius-sm)",
              padding: "4px 8px",
              cursor: "pointer",
              fontFamily: "var(--font-mono)",
            }}
          >
            {collapsed ? "» [" : "« ["}
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

        <nav aria-label={labels.sidebarNavigationAriaLabel}>
          <ul
            style={{
              listStyle: "none",
              margin: 0,
              padding: 0,
              display: "flex",
              flexDirection: "column",
              gap: "4px",
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
                      gap: "8px",
                      padding: "8px 10px",
                      borderRadius: "var(--radius-md)",
                      border: "none",
                      backgroundColor: isActive
                        ? "var(--color-primary-cobalt)"
                        : "transparent",
                      color: isActive
                        ? "var(--color-primary-foreground)"
                        : "var(--color-sidebar-foreground)",
                      cursor: "pointer",
                      textAlign: "left",
                      fontFamily: "var(--font-sans)",
                      fontSize: "var(--font-size-body)",
                    }}
                  >
                    <span style={{ display: "inline-flex", alignItems: "center", gap: "8px" }}>
                      <span aria-hidden="true">{MODULE_ICONS[mod.key]}</span>
                      {!collapsed && (
                        <span>
                          {mod.order}. {moduleLabel}
                        </span>
                      )}
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

      <footer
        data-testid="sidebar-human-profile"
        style={{
          borderTop: "1px solid var(--color-sidebar-border)",
          paddingTop: "10px",
          display: "flex",
          flexDirection: "column",
          gap: "6px",
        }}
      >
        {!collapsed ? (
          <>
            <div
              style={{
                fontSize: "var(--font-size-mono)",
                color: "var(--color-sidebar-muted)",
              }}
            >
              {labels.humanProfilePrefixLabel}: {humanProfile.displayName}
            </div>
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
