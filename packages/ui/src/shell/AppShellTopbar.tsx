import React from "react";
import { StatusBadge } from "../primitives/StatusBadge";
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
  const searchPlaceholder =
    labels.topbarSearchPlaceholder ??
    (currentLocale === "fr" ? "Rechercher... (⌘K)" : "Search... (⌘K)");
  const searchAriaLabel =
    labels.topbarSearchAriaLabel ?? (currentLocale === "fr" ? "Rechercher" : "Search");
  const darkModeLabel =
    labels.darkModeToggleLabel ?? (currentLocale === "fr" ? "🌙 Mode sombre" : "🌙 Dark mode");

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
        <span aria-hidden="true" style={{ color: "var(--color-sidebar-muted)", fontSize: "13px" }}>
          🔍
        </span>
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

        <button
          type="button"
          data-testid="user-profile-dropdown-trigger"
          aria-expanded={profileDropdownOpen}
          onClick={onToggleProfileDropdown}
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
                <div style={{ fontWeight: 700, fontSize: "14px", color: "var(--color-foreground)" }}>
                  {humanProfile.displayName}
                </div>
                <div style={{ fontSize: "12px", color: "var(--color-muted-foreground)" }}>
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

            <hr style={{ border: "none", borderTop: "1px solid var(--color-border)", margin: 0 }} />

            <div
              style={{
                display: "flex",
                justifyContent: "space-between",
                alignItems: "center",
                padding: "4px 6px",
              }}
            >
              <span style={{ fontSize: "13px" }}>{darkModeLabel}</span>
              <button
                type="button"
                role="switch"
                aria-checked={darkMode}
                data-testid="dark-mode-toggle-switch"
                onClick={onToggleDarkMode}
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
  );
}
