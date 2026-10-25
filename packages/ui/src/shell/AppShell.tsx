import React, { useEffect, useState } from "react";
import { ConciergeDock } from "./ConciergeDock";
import { GlobalSidebar } from "./GlobalSidebar";
import type {
  UiHumanProfileBadge,
  UiMobileTabKey,
  UiModuleKey,
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
  onSelectModule: (moduleKey: UiModuleKey, route: string) => void;
  onSelectScope: (scopeId: string) => void;
  onToggleLocale?: () => void;
  onSubmitConciergePrompt?: (prompt: string) => void;
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
  onSelectModule,
  onSelectScope,
  onToggleLocale,
  onSubmitConciergePrompt,
  children,
}: AppShellProps) {
  const [sidebarCollapsed, setSidebarCollapsed] = useState(defaultSidebarCollapsed);
  const [dockCollapsed, setDockCollapsed] = useState(defaultDockCollapsed);
  const [scopeSwitcherOpen, setScopeSwitcherOpen] = useState(false);
  const [mobileTab, setMobileTab] = useState<UiMobileTabKey>("inbox");

  useEffect(() => {
    function handleKeyDown(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setScopeSwitcherOpen(false);
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
          padding: "20px 24px 64px 24px",
          boxSizing: "border-box",
          display: "flex",
          flexDirection: "column",
          gap: "16px",
        }}
      >
        <header
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            borderBottom: "1px solid var(--color-border)",
            paddingBottom: "12px",
          }}
        >
          <h1
            data-testid="active-module-heading"
            style={{
              margin: 0,
              fontFamily: "var(--font-serif)",
              fontSize: "var(--font-size-display)",
            }}
          >
            {labels.modules[activeModuleKey]}
          </h1>

          {onToggleLocale && (
            <button
              type="button"
              data-testid="locale-switcher-button"
              onClick={onToggleLocale}
              style={{
                backgroundColor: "var(--color-surface-card)",
                color: "var(--color-foreground)",
                border: "1px solid var(--color-border)",
                borderRadius: "var(--radius-sm)",
                padding: "6px 10px",
                cursor: "pointer",
                fontFamily: "var(--font-mono)",
                fontSize: "var(--font-size-mono)",
              }}
            >
              {labels.localeSwitchLabel} ({currentLocale.toUpperCase()})
            </button>
          )}
        </header>

        <div data-testid="app-shell-module-content">{children}</div>
      </main>

      <ConciergeDock
        activeModuleKey={activeModuleKey}
        activeScopeId={activeScopeId}
        collapsed={dockCollapsed}
        labels={labels}
        onToggleCollapsed={() => setDockCollapsed((prev) => !prev)}
        onSubmitPrompt={onSubmitConciergePrompt}
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
          backgroundColor: "var(--color-sidebar-bg)",
          color: "var(--color-sidebar-foreground)",
          borderTop: "1px solid var(--color-sidebar-border)",
          padding: "8px 0",
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
                  ? "var(--color-primary-foreground)"
                  : "var(--color-sidebar-muted)",
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
