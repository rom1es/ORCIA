import React from "react";
import { OrciaIcon } from "../components/icons";
import {
  resolveUserRoleDisplayLabel,
  type UiLocalePreference,
  type UiThemePreference,
  type UiUserSettingsTabKey,
  type UserAccountDropdownAndSettingsLabels,
} from "./UserAccountDropdownAndSettingsModal";

export interface UserAccountDropdownMenuProps {
  readonly userDisplayName: string;
  readonly userEmail: string;
  readonly userRole: string;
  readonly hat: string;
  readonly theme: UiThemePreference;
  readonly locale: UiLocalePreference;
  readonly roleMap: Readonly<Record<string, string>>;
  readonly labels: UserAccountDropdownAndSettingsLabels;
  readonly onChangeHat: (nextHat: string) => void;
  readonly onToggleTheme: () => void;
  readonly onToggleLocale: () => void;
  readonly onOpenSettingsModal: (tab: UiUserSettingsTabKey) => void;
  readonly onLogoutClick: () => void;
}

export function UserAccountDropdownMenu({
  userDisplayName,
  userEmail,
  userRole,
  hat,
  theme,
  locale,
  roleMap,
  labels,
  onChangeHat,
  onToggleTheme,
  onToggleLocale,
  onOpenSettingsModal,
  onLogoutClick,
}: UserAccountDropdownMenuProps): React.ReactElement {
  return (
    <div
      role="menu"
      aria-label="UserAccountDropdown"
      data-testid="user-account-dropdown-menu"
      className="absolute right-0 top-10 z-30 w-[280px] rounded-xl border border-surface-border bg-surface-elevated p-3 shadow-lg space-y-2.5 text-xs text-text-primary"
    >
      <div className="border-b border-surface-border pb-2">
        <div className="font-semibold">{userDisplayName}</div>
        <div className="text-[11px] text-text-secondary">
          {userEmail} · {resolveUserRoleDisplayLabel(userRole, locale)}
        </div>
      </div>

      <div className="flex items-center justify-between gap-2">
        <span className="text-text-secondary">{labels.hatSelectorLabel}</span>
        <select
          aria-label={labels.hatSelectorLabel}
          data-testid="dropdown-hat-selector"
          value={hat}
          onChange={(e) => onChangeHat(e.target.value)}
          className="rounded border border-surface-border bg-surface-primary px-1.5 py-0.5 text-xs"
        >
          {Object.entries(roleMap)
            .filter(([key]) => key !== "READ_ONLY_OBSERVER")
            .map(([key, label]) => (
              <option key={key} value={key}>
                {label}
              </option>
            ))}
        </select>
      </div>

      <div className="flex items-center justify-between gap-2">
        <span>{labels.themeQuickToggleLabel}</span>
        <button
          type="button"
          data-testid="dropdown-quick-theme-switch"
          onClick={onToggleTheme}
          className="inline-flex items-center gap-1 px-2 py-0.5 rounded border border-surface-border bg-surface-secondary font-mono text-[11px]"
        >
          <OrciaIcon name={theme === "light" ? "sun" : "moon"} size={13} />
          <span>
            {theme === "light"
              ? locale === "en"
                ? "Light"
                : "Clair"
              : locale === "en"
                ? "Dark"
                : "Sombre"}
          </span>
        </button>
      </div>

      <div className="flex items-center justify-between gap-2">
        <span>{labels.localeQuickToggleLabel}</span>
        <button
          type="button"
          data-testid="dropdown-quick-locale-switch"
          onClick={onToggleLocale}
          className="px-2 py-0.5 rounded border border-surface-border bg-surface-secondary font-mono text-[11px]"
        >
          {locale.toUpperCase()}
        </button>
      </div>

      <div className="border-t border-surface-border pt-2 space-y-1">
        <button
          type="button"
          data-testid="dropdown-open-settings-modal-btn"
          onClick={() => onOpenSettingsModal("PREFERENCES_DISPLAY")}
          className="w-full text-left px-2 py-1.5 rounded hover:bg-surface-secondary flex items-center justify-between"
        >
          <span className="inline-flex items-center gap-1.5">
            <OrciaIcon name="nav.account" size={14} />
            <span>{labels.openAccountSettingsLabel}</span>
          </span>
          <span className="font-mono text-[10px] text-text-secondary">g u</span>
        </button>
        <button
          type="button"
          data-testid="dropdown-open-passthrough-btn"
          onClick={() => onOpenSettingsModal("PASSTHROUGH_SOURCES")}
          className="w-full text-left px-2 py-1.5 rounded hover:bg-surface-secondary inline-flex items-center gap-1.5"
        >
          <OrciaIcon name="keyLock" size={14} />
          <span>{labels.openPassthroughSourcesLabel}</span>
        </button>
      </div>

      <div className="border-t border-surface-border pt-2">
        <button
          type="button"
          data-testid="dropdown-logout-btn"
          onClick={onLogoutClick}
          className="w-full text-left px-2 py-1.5 rounded font-medium text-status-error hover:bg-surface-secondary"
        >
          {labels.logoutButtonLabel}
        </button>
      </div>
    </div>
  );
}
