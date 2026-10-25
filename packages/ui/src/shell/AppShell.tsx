import React, { useEffect, useState } from "react";
import { AppShellTopbar } from "./AppShellTopbar";
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
        }}
      >
        <AppShellTopbar
          activeModuleKey={activeModuleKey}
          humanProfile={humanProfile}
          labels={labels}
          currentLocale={currentLocale}
          dockCollapsed={dockCollapsed}
          profileDropdownOpen={profileDropdownOpen}
          darkMode={darkMode}
          topSearchQuery={topSearchQuery}
          onChangeTopSearchQuery={setTopSearchQuery}
          onToggleDock={() => setDockCollapsed((prev) => !prev)}
          onToggleLocale={onToggleLocale}
          onToggleProfileDropdown={() => setProfileDropdownOpen((prev) => !prev)}
          onToggleDarkMode={() => setDarkMode((prev) => !prev)}
        />

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
        aria-label={labels.mobileNavigationAriaLabel ?? "Mobile Companion Navigation"}
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
