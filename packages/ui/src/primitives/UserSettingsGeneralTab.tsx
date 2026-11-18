import React from "react";
import { OrciaIcon } from "../components/icons";
import type {
  UiLocalePreference,
  UiThemePreference,
  UserAccountDropdownAndSettingsLabels,
  UserAccountPreferencesPatch,
} from "./UserAccountDropdownTypes";

export interface UserSettingsGeneralTabProps {
  readonly theme: UiThemePreference;
  readonly locale: UiLocalePreference;
  readonly autoOpenHelp: boolean;
  readonly notificationsEnabled: boolean;
  readonly labels: UserAccountDropdownAndSettingsLabels;
  readonly onUpdatePreferences: (patch: UserAccountPreferencesPatch) => void | Promise<void>;
}

export function UserSettingsGeneralTab({
  theme,
  locale,
  autoOpenHelp,
  notificationsEnabled,
  labels,
  onUpdatePreferences,
}: UserSettingsGeneralTabProps): React.ReactElement {
  const themeOptions: readonly {
    readonly key: UiThemePreference;
    readonly label: string;
    readonly icon: "sun" | "moon" | "desktop";
  }[] = [
    { key: "light", label: labels.themeLightLabel, icon: "sun" },
    { key: "dark", label: labels.themeDarkLabel, icon: "moon" },
    { key: "system", label: labels.themeSystemLabel, icon: "desktop" },
  ];

  const localeOptions: readonly {
    readonly key: UiLocalePreference;
    readonly label: string;
  }[] = [
    { key: "fr", label: labels.localeFrLabel },
    { key: "en", label: labels.localeEnLabel },
  ];

  return (
    <div data-testid="user-settings-panel-GENERAL" className="space-y-4">
      <div
        className="rounded-lg border p-3 space-y-2.5"
        style={{
          borderColor: "var(--color-border-subtle)",
          backgroundColor: "var(--color-surface-card)",
        }}
      >
        <div className="text-xs font-semibold" style={{ color: "var(--color-text-primary)" }}>
          {labels.appearanceLabel}
        </div>
        <div className="grid grid-cols-3 gap-2">
          {themeOptions.map((opt) => {
            const active = theme === opt.key;
            return (
              <button
                key={opt.key}
                type="button"
                data-testid={`settings-theme-${opt.key}`}
                aria-pressed={active}
                onClick={() => void onUpdatePreferences({ theme: opt.key })}
                className="flex items-center justify-center gap-1.5 rounded-lg border px-2.5 py-2 text-xs font-medium"
                style={{
                  backgroundColor: active
                    ? "var(--color-action-primary-subtle)"
                    : "var(--color-bg-elevated)",
                  borderColor: active
                    ? "var(--color-action-primary)"
                    : "var(--color-border-subtle)",
                  color: active
                    ? "var(--color-action-primary)"
                    : "var(--color-text-primary)",
                }}
              >
                <OrciaIcon name={opt.icon} size={14} />
                <span>{opt.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      <div
        className="rounded-lg border p-3 space-y-2.5"
        style={{
          borderColor: "var(--color-border-subtle)",
          backgroundColor: "var(--color-surface-card)",
        }}
      >
        <div className="text-xs font-semibold" style={{ color: "var(--color-text-primary)" }}>
          {labels.languageLabel}
        </div>
        <div className="grid grid-cols-2 gap-2">
          {localeOptions.map((opt) => {
            const active = locale === opt.key;
            return (
              <button
                key={opt.key}
                type="button"
                data-testid={`settings-locale-${opt.key}`}
                aria-pressed={active}
                onClick={() => void onUpdatePreferences({ locale: opt.key })}
                className="flex items-center justify-center gap-1.5 rounded-lg border px-2.5 py-2 text-xs font-medium"
                style={{
                  backgroundColor: active
                    ? "var(--color-action-primary-subtle)"
                    : "var(--color-bg-elevated)",
                  borderColor: active
                    ? "var(--color-action-primary)"
                    : "var(--color-border-subtle)",
                  color: active
                    ? "var(--color-action-primary)"
                    : "var(--color-text-primary)",
                }}
              >
                <OrciaIcon name="globe" size={14} />
                <span>{opt.label}</span>
              </button>
            );
          })}
        </div>
      </div>

      <div
        className="rounded-lg border p-3 space-y-3"
        style={{
          borderColor: "var(--color-border-subtle)",
          backgroundColor: "var(--color-surface-card)",
        }}
      >
        <label className="flex cursor-pointer items-center justify-between gap-3 text-xs">
          <span className="inline-flex items-center gap-2">
            <OrciaIcon name="help" size={14} />
            <span>{labels.autoOpenHelpLabel}</span>
          </span>
          <input
            type="checkbox"
            data-testid="settings-auto-open-help-checkbox"
            autoComplete="off"
            data-lpignore="true"
            data-1p-ignore="true"
            data-bwignore="true"
            data-form-type="other"
            checked={autoOpenHelp}
            onChange={(e) =>
              void onUpdatePreferences({ autoOpenContextualHelp: e.target.checked })
            }
          />
        </label>

        <label className="flex cursor-pointer items-center justify-between gap-3 text-xs">
          <span className="inline-flex items-center gap-2">
            <OrciaIcon name="notifications" size={14} />
            <span>{labels.notificationsEnabledLabel}</span>
          </span>
          <input
            type="checkbox"
            data-testid="settings-notifications-checkbox"
            autoComplete="off"
            data-lpignore="true"
            data-1p-ignore="true"
            data-bwignore="true"
            data-form-type="other"
            checked={notificationsEnabled}
            onChange={(e) =>
              void onUpdatePreferences({ notificationsEnabled: e.target.checked })
            }
          />
        </label>
      </div>
    </div>
  );
}
