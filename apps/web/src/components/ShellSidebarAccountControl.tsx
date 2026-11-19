import { SidebarAccountPopover, type UiLocalePreference } from "@orcia/ui";
import React from "react";
import { frDictionary } from "../i18n/locales/fr";
import type { TranslationDictionary } from "../i18n/types";
import { useAuthSessionStore } from "../stores/authSessionStore";
import { ShellUserSettingsModal } from "./ShellUserSettingsModal";

export interface ShellSidebarAccountControlProps {
  readonly railCollapsed: boolean;
  readonly userDisplayName: string;
  readonly userEmail: string;
  readonly userRole: string;
  readonly userRoleLabel: string;
  readonly locale: UiLocalePreference;
  readonly labels?: TranslationDictionary["userAccountAndSettings"];
  readonly includeModal?: boolean;
  readonly onLocaleChange: (locale: UiLocalePreference) => void;
  readonly onNavigate: (href: string) => void;
  readonly onLogout: () => void;
}

export function ShellSidebarAccountControl({
  railCollapsed,
  userDisplayName,
  userEmail,
  userRole,
  userRoleLabel,
  locale,
  labels = frDictionary.userAccountAndSettings,
  includeModal = true,
  onLocaleChange,
  onNavigate,
  onLogout,
}: ShellSidebarAccountControlProps): React.ReactElement {
  const openModalAtTab = useAuthSessionStore((s) => s.openUserSettingsModalAtTab);

  return (
    <>
      <SidebarAccountPopover
        railCollapsed={railCollapsed}
        userDisplayName={userDisplayName}
        userEmail={userEmail}
        userRoleLabel={userRoleLabel}
        labels={labels.popover}
        onOpenSettingsTab={(tab) => openModalAtTab(tab)}
        onNavigateProfile={() => onNavigate("/profile")}
        onNavigateHelp={() => onNavigate("/help")}
        onNavigateShowcase={() => onNavigate("/showcase")}
        onLogout={onLogout}
      />
      {includeModal && (
        <ShellUserSettingsModal
          userEmail={userEmail}
          userRole={userRole}
          locale={locale}
          labels={labels}
          onLocaleChange={onLocaleChange}
          onNavigate={onNavigate}
        />
      )}
    </>
  );
}
