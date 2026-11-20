import { type UiLocalePreference } from "@orcia/ui";
import React from "react";
import type { TranslationDictionary } from "../i18n/types";
import { ShellSidebarAccountControl } from "./ShellSidebarAccountControl";

export interface ShellSidebarFooterProps {
  readonly railCollapsed: boolean;
  readonly hideSidebarShowcaseBtn?: boolean;
  readonly pathname?: string;
  readonly userDisplayName: string;
  readonly userEmail: string;
  readonly userRole: string;
  readonly userRoleLabel: string;
  readonly locale: UiLocalePreference;
  readonly footerLabels: TranslationDictionary["sidebarFooter"];
  readonly accountLabels: TranslationDictionary["userAccountAndSettings"];
  readonly onLocaleChange: (locale: UiLocalePreference) => void;
  readonly onNavigate: (href: string) => void;
  readonly onLogout: () => void;
  readonly onOpenShowcase?: () => void;
}

export function renderShellSidebarFooter(params: {
  readonly hasAuthenticatedIdentity: boolean;
  readonly hideSidebarShowcaseBtn: boolean;
  readonly pathname: string | undefined;
  readonly effectiveDisplayName: string;
  readonly effectiveEmail: string;
  readonly userRole: string;
  readonly userHatLabel: string;
  readonly locale: UiLocalePreference;
  readonly dictionary: {
    readonly sidebarFooter: TranslationDictionary["sidebarFooter"];
    readonly userAccountAndSettings: TranslationDictionary["userAccountAndSettings"];
  };
  readonly onLocaleChange: (locale: UiLocalePreference) => void;
  readonly onDispatchNavigation: (href: string) => void;
  readonly onLogout: () => void;
  readonly onOpenShowcase: () => void;
}): ((railCollapsed: boolean) => React.ReactNode) | undefined {
  if (!params.hasAuthenticatedIdentity) return undefined;
  return (railCollapsed: boolean) => (
    <ShellSidebarFooter
      railCollapsed={railCollapsed}
      hideSidebarShowcaseBtn={params.hideSidebarShowcaseBtn}
      pathname={params.pathname}
      userDisplayName={params.effectiveDisplayName}
      userEmail={params.effectiveEmail}
      userRole={params.userRole}
      userRoleLabel={params.userHatLabel}
      locale={params.locale}
      footerLabels={params.dictionary.sidebarFooter}
      accountLabels={params.dictionary.userAccountAndSettings}
      onLocaleChange={params.onLocaleChange}
      onNavigate={params.onDispatchNavigation}
      onLogout={params.onLogout}
      onOpenShowcase={params.onOpenShowcase}
    />
  );
}

export function ShellSidebarFooter({
  railCollapsed,
  userDisplayName,
  userEmail,
  userRole,
  userRoleLabel,
  locale,
  accountLabels,
  onLocaleChange,
  onNavigate,
  onLogout,
}: ShellSidebarFooterProps): React.ReactElement {
  return (
    <ShellSidebarAccountControl
      railCollapsed={railCollapsed}
      userDisplayName={userDisplayName}
      userEmail={userEmail}
      userRole={userRole}
      userRoleLabel={userRoleLabel}
      locale={locale}
      labels={accountLabels}
      includeModal={false}
      onLocaleChange={onLocaleChange}
      onNavigate={onNavigate}
      onLogout={onLogout}
    />
  );
}
