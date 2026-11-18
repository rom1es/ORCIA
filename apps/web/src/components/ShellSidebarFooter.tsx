import { OrciaIcon, type UiLocalePreference } from "@orcia/ui";
import React from "react";
import type { TranslationDictionary } from "../i18n/types";
import { ShellSidebarAccountControl } from "./ShellSidebarAccountControl";

export interface ShellSidebarFooterProps {
  readonly railCollapsed: boolean;
  readonly hideSidebarShowcaseBtn: boolean;
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
  readonly onOpenShowcase: () => void;
}

export function ShellSidebarFooter({
  railCollapsed,
  hideSidebarShowcaseBtn,
  pathname,
  userDisplayName,
  userEmail,
  userRole,
  userRoleLabel,
  locale,
  footerLabels,
  accountLabels,
  onLocaleChange,
  onNavigate,
  onLogout,
  onOpenShowcase,
}: ShellSidebarFooterProps): React.ReactElement {
  return (
    <>
      <ShellSidebarAccountControl
        railCollapsed={railCollapsed}
        userDisplayName={userDisplayName}
        userEmail={userEmail}
        userRole={userRole}
        userRoleLabel={userRoleLabel}
        locale={locale}
        labels={accountLabels}
        onLocaleChange={onLocaleChange}
        onNavigate={onNavigate}
        onLogout={onLogout}
      />

      {!hideSidebarShowcaseBtn && (
        <button
          type="button"
          data-testid="open-orcia-showcase-site-btn"
          data-active={pathname?.startsWith("/showcase") ? "true" : "false"}
          aria-label={railCollapsed ? footerLabels.documentationLabel : undefined}
          title={railCollapsed ? footerLabels.documentationLabel : undefined}
          onClick={onOpenShowcase}
          className={`orcia-sidebar-nav-btn ${railCollapsed ? "justify-center px-0 py-2" : "gap-2.5 px-2.5 py-2"}`}
        >
          <OrciaIcon name="bookOpen" />
          {!railCollapsed && <span className="flex-1">{footerLabels.documentationLabel}</span>}
        </button>
      )}
    </>
  );
}
