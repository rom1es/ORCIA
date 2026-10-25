import React, { useEffect, useState } from "react";
import { StatusBadge } from "../primitives/StatusBadge";
import { AssistantDock } from "./AssistantDock";
import { GlobalSidebar } from "./GlobalSidebar";
import type {
  UiHumanProfileBadge,
  UiMobileTabKey,
  UiModuleKey,
  UiPermissionBrokerLabels,
  UiPermissionBrokerTicketView,
  UiScopeNode,
  UiShellLabels,
  UiShellModuleItem,
} from "./types";

export interface AppShellProps {
  modules: UiShellModuleItem[];
  activeModuleKey: UiModuleKey;
  scopes: UiScopeNode[];
  activeScopeId: string;
  humanProfile: UiHumanProfileBadge;
  labels: UiShellLabels;
  currentLocale: "fr" | "en";
  defaultSidebarCollapsed?: boolean;
  defaultDockCollapsed?: boolean;
  permissionBrokerTicket?: UiPermissionBrokerTicketView | null;
  permissionBrokerLabels?: UiPermissionBrokerLabels;
  onSelectModule: (moduleKey: UiModuleKey, route: string) => void;
  onSelectScope: (scopeId: string) => void;
  onToggleLocale?: () => void;
  onSubmitAssistantPrompt?: (prompt: string) => void;
  onPausePermissionStep?: (ticketId: string) => void;
  onReplayPermissionStep?: (ticketId: string) => void;
  children: React.ReactNode;
}

function isEditableElement(target: EventTarget | null): boolean {
  if (!target || !(target instanceof HTMLElement)) {
    return false;
  }
  const tagName = target.tagName.toUpperCase();
  if (tagName === "INPUT" || tagName === "TEXTAREA" || tagName === "SELECT") {
    return true;
  }
  return target.isContentEditable;
}

export function AppShell({
  modules,
  activeModuleKey,
  scopes,
  activeScopeId,
  humanProfile,
  labels,
  currentLocale,
  defaultSidebarCollapsed = false,
  defaultDockCollapsed = false,
  permissionBrokerTicket,
  permissionBrokerLabels,
  onSelectModule,
  onSelectScope,
  onToggleLocale,
  onSubmitAssistantPrompt,
  onPausePermissionStep,
  onReplayPermissionStep,
  children,
}: AppShellProps) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(defaultSidebarCollapsed);
  const [dockCollapsed, setDockCollapsed] = useState(defaultDockCollapsed);
  const [scopeSwitcherOpen, setScopeSwitcherOpen] = useState(false);
  const [profileDropdownOpen, setProfileDropdownOpen] = useState(false);
  const [darkMode, setDarkMode] = useState(false);
  const [topSearchQuery, setTopSearchQuery] = useState("");
  const [mobileTab, setMobileTab] = useState<UiMobileTabKey>("inbox");

  useEffect(() => {
    if (
      permissionBrokerTicket &&
      (permissionBrokerTicket.stepState === "PERMISSION_DENIED_STEP" ||
        permissionBrokerTicket.status === "WAITING_FOR_PERMISSION")
    ) {
      setDockCollapsed(false);
    }
  }, [
    permissionBrokerTicket?.id,
    permissionBrokerTicket?.stepState,
    permissionBrokerTicket?.status,
  ]);

  useEffect(() => {
    if (typeof document !== "undefined") {
      if (darkMode) {
        document.documentElement.setAttribute("data-theme", "dark");
      } else {
        document.documentElement.removeAttribute("data-theme");
      }
    }
  }, [darkMode]);

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setScopeSwitcherOpen(false);
        setProfileDropdownOpen(false);
        return;
      }

      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "w") {
        event.preventDefault();
        setScopeSwitcherOpen((prev) => !prev);
        return;
      }

      if (isEditableElement(event.target) || isEditableElement(document.activeElement)) {
        return;
      }

      if (event.key === "[") {
        event.preventDefault();
        setSidebarCollapsed((prev) => !prev);
      } else if (event.key === "]") {
        event.preventDefault();
        setDockCollapsed((prev) => !prev);
      }
    }

    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  const avatarInitial = humanProfile.displayName.trim().charAt(0).toUpperCase() || "U";
  const isContributor = humanProfile.accessMode === "CONTRIBUTOR_ACTION_REQUIRED";

  return (
    <div
      data-testid="orcia-app-shell"
      data-active-mobile-tab={mobileTab}
      className="orcia-app-shell"
      style={{
        display: "flex",
        minHeight: "100vh",
        width: "100%",
        backgroundColor: "var(--color-surface-bg)",
        color: "var(--color-foreground)",
        fontFamily: "var(--font-sans)",
      }}
    >
      <div
        role="status"
        aria-live="polite"
        data-testid="app-shell-live-region"
        style={{
          position: "absolute",
          width: "1px",
          height: "1px",
          overflow: "hidden",
          clip: "rect(0, 0, 0, 0)",
        }}
      >
        {labels.modules[activeModuleKey]}
      </div>

      <GlobalSidebar
        modules={modules}
        activeModuleKey={activeModuleKey}
        scopes={scopes}
        activeScopeId={activeScopeId}
        isScopeSwitcherOpen={scopeSwitcherOpen}
        humanProfile={humanProfile}
        collapsed={sidebarCollapsed}
        labels={labels}
        onSelectModule={onSelectModule}
        onToggleCollapsed={() => setSidebarCollapsed((prev) => !prev)}
        onToggleScopeSwitcher={() => setScopeSwitcherOpen((prev) => !prev)}
        onSelectScope={onSelectScope}
      />

      <main
        data-testid="app-shell-canvas"
        className="orcia-canvas-main"
        style={{
          flex: "1 1 0%",
          backgroundColor: "var(--color-surface-bg)",
          boxSizing: "border-box",
          display: "flex",
          flexDirection: "column",
          minWidth: 0,
        }}
      >
        {/* Top Header Bar: Module Heading + Search Bar + Action Icons & Clean User Profile Dropdown */}
        <header
          data-testid="app-shell-topbar"
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            backgroundColor: "var(--color-surface-hero)",
            borderBottom: "1px solid var(--color-border)",
            padding: "12px 28px",
            position: "sticky",
            top: 0,
            zIndex: 30,
            gap: "16px",
            flexWrap: "wrap",
          }}
        >
          {/* Left: Active Module Title */}
          <h1
            data-testid="active-module-heading"
            style={{
              margin: 0,
              fontFamily: "var(--font-sans)",
              fontSize: "18px",
              fontWeight: 700,
              letterSpacing: "-0.02em",
              color: "var(--color-foreground)",
            }}
          >
            {labels.modules[activeModuleKey]}
          </h1>

          {/* Center: Top Search Input */}
          <div
            style={{
              display: "flex",
              alignItems: "center",
              gap: "8px",
              backgroundColor: "var(--color-sidebar-search-bg)",
              border: "1px solid var(--color-border)",
              borderRadius: "var(--radius-full)",
              padding: "6px 14px",
              flex: "1 1 240px",
              maxWidth: "420px",
            }}
          >
            <span aria-hidden="true" style={{ color: "var(--color-sidebar-muted)", fontSize: "13px" }}>
              🔍
            </span>
            <input
              type="search"
              data-testid="topbar-search-input"
              aria-label="Search"
              placeholder={currentLocale === "fr" ? "Rechercher... (⌘K)" : "Search... (⌘K)"}
              value={topSearchQuery}
              onChange={(e) => setTopSearchQuery(e.target.value)}
              style={{
                border: "none",
                background: "transparent",
                outline: "none",
                width: "100%",
                color: "var(--color-foreground)",
                fontFamily: "var(--font-sans)",
                fontSize: "13px",
              }}
            />
          </div>

          {/* Right: Action Icons (💬 Assistant, 🌐 Locale) + User Avatar Dropdown */}
          <div style={{ display: "flex", alignItems: "center", gap: "10px", position: "relative" }}>
            <button
              type="button"
              data-testid="topbar-assistant-toggle-btn"
              title={
                dockCollapsed
                  ? labels.assistantDockToggleExpandLabel
                  : labels.assistantDockToggleCollapseLabel
              }
              onClick={() => setDockCollapsed((prev) => !prev)}
              style={{
                width: "36px",
                height: "36px",
                borderRadius: "var(--radius-full)",
                border: "1px solid var(--color-border)",
                backgroundColor: dockCollapsed
                  ? "var(--color-surface-card)"
                  : "var(--color-sidebar-active-bg)",
                color: dockCollapsed
                  ? "var(--color-foreground)"
                  : "var(--color-primary-cobalt)",
                display: "inline-flex",
                alignItems: "center",
                justifyContent: "center",
                cursor: "pointer",
                fontSize: "15px",
              }}
            >
              💬
            </button>

            {onToggleLocale && (
              <button
                type="button"
                data-testid="locale-switcher-button"
                onClick={onToggleLocale}
                style={{
                  backgroundColor: "var(--color-surface-card)",
                  color: "var(--color-foreground)",
                  border: "1px solid var(--color-border)",
                  borderRadius: "var(--radius-full)",
                  padding: "6px 12px",
                  cursor: "pointer",
                  fontFamily: "var(--font-mono)",
                  fontSize: "var(--font-size-mono)",
                  fontWeight: 600,
                }}
              >
                {labels.localeSwitchLabel} ({currentLocale.toUpperCase()})
              </button>
            )}

            {/* User Avatar Trigger with Presence Dot + Chevron */}
            <button
              type="button"
              data-testid="user-profile-dropdown-trigger"
              aria-expanded={profileDropdownOpen}
              onClick={() => setProfileDropdownOpen((prev) => !prev)}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "8px",
                backgroundColor: "var(--color-surface-card)",
                border: profileDropdownOpen
                  ? "2px solid var(--color-primary-cobalt)"
                  : "1px solid var(--color-border)",
                borderRadius: "var(--radius-full)",
                padding: "4px 10px 4px 4px",
                cursor: "pointer",
                color: "var(--color-foreground)",
              }}
            >
              <span
                style={{
                  position: "relative",
                  width: "30px",
                  height: "30px",
                  borderRadius: "var(--radius-full)",
                  backgroundColor: "var(--color-primary-cobalt)",
                  color: "var(--color-primary-foreground)",
                  display: "inline-flex",
                  alignItems: "center",
                  justifyContent: "center",
                  fontWeight: 700,
                  fontSize: "13px",
                }}
              >
                {avatarInitial}
                <span
                  aria-hidden="true"
                  style={{
                    position: "absolute",
                    bottom: "-1px",
                    right: "-1px",
                    width: "9px",
                    height: "9px",
                    borderRadius: "var(--radius-full)",
                    backgroundColor: isContributor
                      ? "var(--color-gate-emerald)"
                      : "var(--color-arbitration-amber)",
                    border: "2px solid var(--color-surface-card)",
                  }}
                />
              </span>
              <span style={{ fontSize: "12px", color: "var(--color-muted-foreground)" }}>▾</span>
            </button>

            {/* Clean User Profile Dropdown (No duplicate sidebar links, no fake personas, no fake FinOps) */}
            {profileDropdownOpen && (
              <div
                data-testid="user-profile-dropdown-menu"
                role="menu"
                style={{
                  position: "absolute",
                  top: "calc(100% + 10px)",
                  right: 0,
                  width: "280px",
                  backgroundColor: "var(--color-surface-card)",
                  border: "2px solid var(--color-primary-cobalt)",
                  borderRadius: "var(--radius-lg)",
                  boxShadow: "var(--shadow-dropdown)",
                  padding: "16px",
                  zIndex: 50,
                  display: "flex",
                  flexDirection: "column",
                  gap: "12px",
                }}
              >
                {/* User Identity Header */}
                <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
                  <div
                    style={{
                      position: "relative",
                      width: "44px",
                      height: "44px",
                      borderRadius: "var(--radius-full)",
                      backgroundColor: "var(--color-primary-cobalt)",
                      color: "var(--color-primary-foreground)",
                      display: "flex",
                      alignItems: "center",
                      justifyContent: "center",
                      fontWeight: 700,
                      fontSize: "18px",
                      flexShrink: 0,
                    }}
                  >
                    {avatarInitial}
                    <span
                      aria-hidden="true"
                      style={{
                        position: "absolute",
                        bottom: "0px",
                        right: "0px",
                        width: "11px",
                        height: "11px",
                        borderRadius: "var(--radius-full)",
                        backgroundColor: isContributor
                          ? "var(--color-gate-emerald)"
                          : "var(--color-arbitration-amber)",
                        border: "2px solid var(--color-surface-card)",
                      }}
                    />
                  </div>
                  <div style={{ minWidth: 0 }}>
                    <div
                      style={{
                        fontWeight: 700,
                        fontSize: "14px",
                        color: "var(--color-foreground)",
                      }}
                    >
                      {humanProfile.displayName}
                    </div>
                    <div
                      style={{
                        fontSize: "12px",
                        color: "var(--color-muted-foreground)",
                      }}
                    >
                      {[humanProfile.role, humanProfile.orgUnitName].filter(Boolean).join(" · ") ||
                        humanProfile.archetypeKey}
                    </div>
                    <div style={{ marginTop: "4px" }}>
                      <StatusBadge
                        label={labels.accessModes[humanProfile.accessMode]}
                        tone={isContributor ? "emerald" : "amber"}
                        pill
                      />
                    </div>
                  </div>
                </div>

                <hr
                  style={{
                    border: "none",
                    borderTop: "1px solid var(--color-border)",
                    margin: 0,
                  }}
                />

                {/* Personal Preferences Only (Dark Mode & Language) */}
                <div
                  style={{
                    display: "flex",
                    justifyContent: "space-between",
                    alignItems: "center",
                    padding: "4px 6px",
                  }}
                >
                  <span style={{ fontSize: "13px" }}>🌙 Dark mode</span>
                  <button
                    type="button"
                    role="switch"
                    aria-checked={darkMode}
                    data-testid="dark-mode-toggle-switch"
                    onClick={() => setDarkMode((prev) => !prev)}
                    style={{
                      width: "40px",
                      height: "22px",
                      borderRadius: "var(--radius-full)",
                      border: "none",
                      backgroundColor: darkMode
                        ? "var(--color-primary-cobalt)"
                        : "var(--color-border)",
                      position: "relative",
                      cursor: "pointer",
                      padding: "2px",
                    }}
                  >
                    <span
                      style={{
                        display: "block",
                        width: "18px",
                        height: "18px",
                        borderRadius: "var(--radius-full)",
                        backgroundColor: "var(--color-surface-card)",
                        transform: darkMode ? "translateX(18px)" : "translateX(0)",
                        transition: "transform 0.15s ease",
                      }}
                    />
                  </button>
                </div>
              </div>
            )}
          </div>
        </header>

        <div
          data-testid="app-shell-module-content"
          style={{
            padding: "24px 28px 64px 28px",
            flex: "1 1 0%",
          }}
        >
          {children}
        </div>
      </main>

      <AssistantDock
        activeModuleKey={activeModuleKey}
        activeScopeId={activeScopeId}
        collapsed={dockCollapsed}
        labels={labels}
        permissionBrokerTicket={permissionBrokerTicket}
        permissionBrokerLabels={permissionBrokerLabels}
        onToggleCollapsed={() => setDockCollapsed((prev) => !prev)}
        onSubmitPrompt={onSubmitAssistantPrompt}
        onPausePermissionStep={onPausePermissionStep}
        onReplayPermissionStep={onReplayPermissionStep}
      />

      <nav
        data-testid="mobile-companion-tabbar"
        className="orcia-mobile-tabbar"
        aria-label="Mobile Companion Navigation"
        style={{
          position: "fixed",
          bottom: 0,
          left: 0,
          right: 0,
          display: "flex",
          justifyContent: "space-around",
          backgroundColor: "var(--color-surface-card)",
          color: "var(--color-foreground)",
          borderTop: "1px solid var(--color-border)",
          padding: "10px 0",
          zIndex: 40,
        }}
      >
        {(["inbox", "chat", "briefing"] as const).map((tabKey) => (
          <button
            key={tabKey}
            type="button"
            data-testid={`mobile-tab-${tabKey}`}
            data-active={mobileTab === tabKey ? "true" : "false"}
            onClick={() => setMobileTab(tabKey)}
            style={{
              background: "transparent",
              border: "none",
              color:
                mobileTab === tabKey
                  ? "var(--color-primary-cobalt)"
                  : "var(--color-muted-foreground)",
              fontWeight: mobileTab === tabKey ? 700 : 500,
              cursor: "pointer",
              fontFamily: "var(--font-sans)",
            }}
          >
            {labels.mobileTabs[tabKey]}
          </button>
        ))}
      </nav>
    </div>
  );
}
