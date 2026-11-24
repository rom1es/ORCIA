import React from "react";
import { OrciaIcon } from "../components/icons";
import { AppShellTopbarProfileMenu } from "./AppShellTopbarProfileMenu";
import type { UiHumanProfileBadge, UiModuleKey, UiShellLabels } from "./types";

export interface AppShellTopbarProps {
  activeModuleKey: UiModuleKey;
  humanProfile: UiHumanProfileBadge;
  labels: UiShellLabels;
  currentLocale: "fr" | "en";
  dockCollapsed: boolean;
  profileDropdownOpen: boolean;
  darkMode: boolean;
  topSearchQuery: string;
  onChangeTopSearchQuery: (value: string) => void;
  onToggleDock: () => void;
  onToggleLocale?: () => void;
  onToggleProfileDropdown: () => void;
  onToggleDarkMode: () => void;
}

export function AppShellTopbar({
  activeModuleKey,
  humanProfile,
  labels,
  currentLocale,
  dockCollapsed,
  profileDropdownOpen,
  darkMode,
  topSearchQuery,
  onChangeTopSearchQuery,
  onToggleDock,
  onToggleLocale,
  onToggleProfileDropdown,
  onToggleDarkMode,
}: AppShellTopbarProps) {
  const avatarInitial = humanProfile.displayName.trim().charAt(0).toUpperCase() || "U";
  const isContributor = humanProfile.accessMode === "CONTRIBUTOR_ACTION_REQUIRED";
  const searchPlaceholder = labels.topbarSearchPlaceholder ?? "";
  const searchAriaLabel = labels.topbarSearchAriaLabel ?? "";
  const darkModeLabel = labels.darkModeToggleLabel ?? "";

  return (
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
        <OrciaIcon
          name="search"
          style={{ color: "var(--color-sidebar-muted)", fontSize: "13px" }}
        />
        <input
          type="search"
          autoComplete="off"
          data-lpignore="true"
          data-1p-ignore="true"
          data-bwignore="true"
          data-form-type="other"
          data-testid="topbar-search-input"
          aria-label={searchAriaLabel}
          placeholder={searchPlaceholder}
          value={topSearchQuery}
          onChange={(e) => onChangeTopSearchQuery(e.target.value)}
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

      <div style={{ display: "flex", alignItems: "center", gap: "10px", position: "relative" }}>
        <button
          type="button"
          data-testid="topbar-assistant-toggle-btn"
          title={
            dockCollapsed
              ? labels.assistantDockToggleExpandLabel
              : labels.assistantDockToggleCollapseLabel
          }
          onClick={onToggleDock}
          style={{
            width: "36px",
            height: "36px",
            borderRadius: "var(--radius-full)",
            border: "1px solid var(--color-border)",
            backgroundColor: dockCollapsed
              ? "var(--color-surface-card)"
              : "var(--color-sidebar-active-bg)",
            color: dockCollapsed ? "var(--color-foreground)" : "var(--color-primary-cobalt)",
            display: "inline-flex",
            alignItems: "center",
            justifyContent: "center",
            cursor: "pointer",
            fontSize: "15px",
          }}
        >
          <OrciaIcon name="assistant" />
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

        <AppShellTopbarProfileMenu
          humanProfile={humanProfile}
          labels={labels}
          profileDropdownOpen={profileDropdownOpen}
          darkMode={darkMode}
          avatarInitial={avatarInitial}
          isContributor={isContributor}
          darkModeLabel={darkModeLabel}
          onToggleProfileDropdown={onToggleProfileDropdown}
          onToggleDarkMode={onToggleDarkMode}
        />
      </div>
    </header>
  );
}
