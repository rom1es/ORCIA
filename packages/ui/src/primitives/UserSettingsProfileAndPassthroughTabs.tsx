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
  UiUserPassthroughConnectorView,
  UserAccountDropdownAndSettingsLabels,
  UserPasswordSecurityLabels,
} from "./UserAccountDropdownTypes";

export { UserSettingsPassthroughTab, type UserSettingsPassthroughTabProps };

export interface UserSettingsProfileAndPassthroughTabsProps {
  readonly userEmail: string;
  readonly userRole: string;
  readonly locale?: UiLocalePreference;
  readonly passthroughTested: boolean;
  readonly labels: UserAccountDropdownAndSettingsLabels;
  readonly accountProfile?: UiUserAccountProfileView;
  readonly passthroughConnectors?: readonly UiUserPassthroughConnectorView[];
  readonly mustChangePassword?: boolean;
  readonly onTestPassthrough: () => void;
  readonly onChangePassword?: (
    currentPassword: string,
    newPassword: string,
  ) => Promise<{ success: boolean; error?: string } | void>;
  readonly onSavePassthroughToken?: (
    connectorId: string,
    externalLogin: string,
    secretValue: string,
  ) => void | Promise<void>;
  readonly onRevokePassthroughToken?: (connectorId: string) => void | Promise<void>;
}

export function UserSettingsProfileTab({
  userEmail,
  userRole,
  locale = "fr",
  accountProfile,
  mustChangePassword = false,
  onChangePassword,
  labels,
  passwordSecurity,
}: {
  readonly userEmail: string;
  readonly userRole: string;
  readonly locale?: UiLocalePreference;
  readonly accountProfile?: UiUserAccountProfileView;
  readonly mustChangePassword?: boolean;
  readonly onChangePassword?: (
    currentPassword: string,
    newPassword: string,
  ) => Promise<{ success: boolean; error?: string } | void>;
  readonly labels?: UserAccountDropdownAndSettingsLabels;
  readonly passwordSecurity?: UserPasswordSecurityLabels;
}): React.ReactElement {
  const isFr = locale !== "en";
  const displayEmail = accountProfile?.email || userEmail;
  const displayName = accountProfile?.displayName || userEmail.split("@")[0] || "";
  const roles = accountProfile?.roles && accountProfile.roles.length > 0 ? accountProfile.roles : [userRole];
  const teams = accountProfile?.teams || [];
  const billingUnits = accountProfile?.billingOrgUnits || [];

  return (
    <div data-testid="user-settings-panel-PROFILE_SECURITY" className="space-y-4">
      <div className="rounded-lg border border-surface-border bg-surface-card p-3 space-y-2">
        <div className="font-semibold text-text-primary text-xs flex items-center gap-1.5">
          <OrciaIcon name="user" size={14} />
          <span>{isFr ? "Identité & Rôles Actifs" : "Identity & Active Roles"}</span>
        </div>
        <p className="text-text-secondary text-xs">
          <strong>{displayName}</strong> &lt;{displayEmail}&gt;
        </p>
        <div className="flex flex-wrap gap-1.5 pt-1">
          {roles.map((r) => (
            <span
              key={r}
              data-testid={`user-role-badge-${r}`}
              className="px-2 py-0.5 rounded text-[10px] font-mono font-medium bg-brand-primary/10 text-brand-primary border border-brand-primary/20"
            >
              {r}
            </span>
          ))}
        </div>
      </div>

      <UserPasswordChangeCard
        mustChangePassword={mustChangePassword}
        locale={locale}
        onChangePassword={onChangePassword}
        labels={passwordSecurity ?? labels?.passwordSecurity}
      />

      <div
        data-testid="user-account-finops-teams-section"
        className="rounded-lg border border-surface-border bg-surface-card p-3 space-y-2"
      >
        <div className="font-semibold text-text-primary text-xs flex items-center justify-between">
          <span className="flex items-center gap-1.5">
            <OrciaIcon name="team" size={14} />
            <span>{isFr ? "Mes équipes & rattachements FinOps" : "My Teams & FinOps Allocations"}</span>
          </span>
          <span className="text-[10px] text-text-secondary font-normal">
            {isFr ? "Lecture seule gouvernée" : "Governed read-only"}
          </span>
        </div>

        {teams.length === 0 ? (
          <p className="text-text-secondary text-xs italic">
            {isFr
              ? "Aucune équipe opérationnelle explicitement rattachée."
              : "No operational team explicitly assigned."}
          </p>
        ) : (
          <div className="space-y-1.5 pt-1">
            {teams.map((t) => (
              <div
                key={t.id}
                data-testid={`user-team-row-${t.slug}`}
                className="flex items-center justify-between p-2 rounded bg-surface-primary/50 text-xs"
              >
                <div className="flex items-center gap-2">
                  <span className="font-medium text-text-primary">{t.name}</span>
                  <span className="text-[10px] font-mono text-text-secondary">({t.slug})</span>
                  {t.isLead && (
                    <span className="px-1.5 py-0.2 rounded text-[9px] font-bold bg-amber-500/10 text-amber-500 border border-amber-500/30">
                      Lead
                    </span>
                  )}
                </div>
                <div className="flex items-center gap-2 text-[11px]">
                  {t.billingEnabled ? (
                    <span className="text-status-success font-medium flex items-center gap-1">
                      <OrciaIcon name="checkFilled" size={12} /> {isFr ? "Facturation active" : "Billing active"}
                    </span>
                  ) : (
                    <span className="text-text-secondary">{isFr ? "Sans facturation" : "No billing"}</span>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}

        {billingUnits.length > 0 && (
          <div className="pt-2 border-t border-surface-border text-[11px] text-text-secondary">
            <span>{isFr ? "Unités de facturation associées : " : "Associated billing units: "}</span>
            <span className="font-medium text-text-primary">
              {billingUnits.map((u) => u.name).join(", ")}
            </span>
          </div>
        )}
      </div>
    </div>
  );
}
