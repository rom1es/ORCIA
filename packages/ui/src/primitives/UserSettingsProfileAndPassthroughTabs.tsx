import React from "react";
import { OrciaIcon } from "../components/icons";
import { UserPasswordChangeCard } from "./UserPasswordChangeCard";
import {
  UserSettingsPassthroughTab,
  type UserSettingsPassthroughTabProps,
} from "./UserSettingsPassthroughTab";
import type {
  UiLocalePreference,
  UiUserAccountProfileView,
  UserAccountDropdownAndSettingsLabels,
  UserPasswordSecurityLabels,
} from "./UserAccountDropdownTypes";
import { resolveUserRoleDisplayLabel } from "./UserRoleDisplayLabels";

export { UserSettingsPassthroughTab, type UserSettingsPassthroughTabProps };

export function UserSettingsProfileTab({
  userEmail,
  userRole,
  locale = "fr",
  accountProfile,
  mustChangePassword = false,
  twoFactorMode = "NONE",
  onChangePassword,
  labels,
  passwordSecurity,
}: {
  readonly userEmail: string;
  readonly userRole: string;
  readonly locale?: UiLocalePreference;
  readonly accountProfile?: UiUserAccountProfileView;
  readonly mustChangePassword?: boolean;
  readonly twoFactorMode?: string;
  readonly onChangePassword?: (
    currentPassword: string,
    newPassword: string,
  ) => Promise<{ success: boolean; error?: string } | void>;
  readonly labels: UserAccountDropdownAndSettingsLabels;
  readonly passwordSecurity?: UserPasswordSecurityLabels;
}): React.ReactElement {
  const displayEmail = accountProfile?.email || userEmail;
  const displayName = accountProfile?.displayName || userEmail.split("@")[0] || "";
  const roles =
    accountProfile?.roles && accountProfile.roles.length > 0 ? accountProfile.roles : [userRole];
  const teams = accountProfile?.teams || [];
  const billingUnits = accountProfile?.billingOrgUnits || [];

  return (
    <div data-testid="user-settings-panel-ACCOUNT_SECURITY" className="space-y-4">
      <div
        className="rounded-lg border p-3 space-y-2"
        style={{
          borderColor: "var(--color-border-subtle)",
          backgroundColor: "var(--color-surface-card)",
        }}
      >
        <div className="text-xs font-semibold flex items-center gap-1.5">
          <OrciaIcon name="user" size={14} />
          <span>{labels.profileIdentityTitle}</span>
        </div>
        <p className="text-xs" style={{ color: "var(--color-text-secondary)" }}>
          <strong>{displayName}</strong> &lt;{displayEmail}&gt;
        </p>
        <div className="flex flex-wrap gap-1.5 pt-1">
          {roles.map((r) => (
            <span
              key={r}
              data-testid={`user-role-badge-${r}`}
              className="rounded border px-2 py-0.5 text-[11px] font-medium"
              style={{
                backgroundColor: "var(--color-action-primary-subtle)",
                borderColor: "var(--color-border-subtle)",
                color: "var(--color-action-primary)",
              }}
            >
              {resolveUserRoleDisplayLabel(r, locale)}
            </span>
          ))}
        </div>
      </div>

      <UserPasswordChangeCard
        mustChangePassword={mustChangePassword}
        locale={locale}
        onChangePassword={onChangePassword}
        labels={passwordSecurity ?? labels.passwordSecurity}
      />

      <div
        data-testid="user-settings-2fa-info-card"
        className="rounded-lg border p-3 flex items-center justify-between text-xs"
        style={{
          borderColor: "var(--color-border-subtle)",
          backgroundColor: "var(--color-surface-card)",
        }}
      >
        <span className="inline-flex items-center gap-1.5 font-semibold">
          <OrciaIcon name="shield" size={14} />
          <span>{labels.twoFactorSectionTitle}</span>
        </span>
        <span
          data-testid="user-settings-2fa-mode-badge"
          className="rounded px-2 py-0.5 font-mono text-[11px]"
          style={{
            backgroundColor: "var(--color-bg-elevated)",
            color: "var(--color-text-secondary)",
          }}
        >
          {twoFactorMode !== "NONE"
            ? `${labels.twoFactorConfiguredLabel} (${twoFactorMode})`
            : labels.twoFactorOptionalPolicyLabel}
        </span>
      </div>

      <div
        data-testid="user-account-finops-teams-section"
        className="rounded-lg border p-3 space-y-2"
        style={{
          borderColor: "var(--color-border-subtle)",
          backgroundColor: "var(--color-surface-card)",
        }}
      >
        <div className="text-xs font-semibold flex items-center justify-between">
          <span className="flex items-center gap-1.5">
            <OrciaIcon name="team" size={14} />
            <span>{labels.profileTeamsFinopsTitle}</span>
          </span>
          <span className="text-[10px] font-normal" style={{ color: "var(--color-text-secondary)" }}>
            {labels.profileTeamsReadOnlyBadge}
          </span>
        </div>

        {teams.length === 0 ? (
          <p className="text-xs italic" style={{ color: "var(--color-text-secondary)" }}>
            {labels.profileTeamsEmptyText}
          </p>
        ) : (
          <div className="space-y-1.5 pt-1">
            {teams.map((t) => (
              <div
                key={t.id}
                data-testid={`user-team-row-${t.slug}`}
                className="flex items-center justify-between rounded p-2 text-xs"
                style={{ backgroundColor: "var(--color-bg-elevated)" }}
              >
                <div className="flex items-center gap-2">
                  <span className="font-medium">{t.name}</span>
                  <span className="font-mono text-[10px]" style={{ color: "var(--color-text-secondary)" }}>
                    ({t.slug})
                  </span>
                </div>
                <span className="text-[11px]" style={{ color: "var(--color-text-secondary)" }}>
                  {t.billingEnabled
                    ? labels.profileBillingActiveLabel
                    : labels.profileBillingInactiveLabel}
                </span>
              </div>
            ))}
          </div>
        )}

        {billingUnits.length > 0 && (
          <div
            className="pt-2 border-t text-[11px]"
            style={{ borderColor: "var(--color-border-subtle)", color: "var(--color-text-secondary)" }}
          >
            <span>{labels.profileBillingUnitsPrefix}</span>
            <span className="font-medium" style={{ color: "var(--color-text-primary)" }}>
              {billingUnits.map((u) => u.name).join(", ")}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
