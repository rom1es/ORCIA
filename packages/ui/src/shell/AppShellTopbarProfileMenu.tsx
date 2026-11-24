import React from "react";
import { OrciaIcon } from "../components/icons";
import { StatusBadge } from "../primitives/StatusBadge";
import type { UiHumanProfileBadge, UiShellLabels } from "./types";

export function AppShellTopbarProfileMenu({
  humanProfile,
  labels,
  profileDropdownOpen,
  darkMode,
  avatarInitial,
  isContributor,
  darkModeLabel,
  onToggleProfileDropdown,
  onToggleDarkMode,
}: {
  readonly humanProfile: UiHumanProfileBadge;
  readonly labels: UiShellLabels;
  readonly profileDropdownOpen: boolean;
  readonly darkMode: boolean;
  readonly avatarInitial: string;
  readonly isContributor: boolean;
  readonly darkModeLabel: string;
  readonly onToggleProfileDropdown: () => void;
  readonly onToggleDarkMode: () => void;
}): React.JSX.Element {
  return (
    <>
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
        <OrciaIcon
          name="caretDown"
          style={{ fontSize: "12px", color: "var(--color-muted-foreground)" }}
        />
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
    </>
  );
}
