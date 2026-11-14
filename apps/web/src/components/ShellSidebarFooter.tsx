import { OrciaIcon } from "@orcia/ui";
import React from "react";
import type { TranslationDictionary } from "../i18n/types";

export interface ShellSidebarFooterProps {
  readonly railCollapsed: boolean;
  readonly userSettingsModalOpen: boolean;
  readonly hideSidebarShowcaseBtn: boolean;
  readonly pathname?: string;
  readonly labels: TranslationDictionary["sidebarFooter"];
  readonly onOpenMyAccount: () => void;
  readonly onOpenShowcase: () => void;
}

export function ShellSidebarFooter({
  railCollapsed,
  userSettingsModalOpen,
  hideSidebarShowcaseBtn,
  pathname,
  labels,
  onOpenMyAccount,
  onOpenShowcase,
}: ShellSidebarFooterProps): React.ReactElement {
  return (
    <>
      <button
        type="button"
        data-testid="sidebar-open-my-account-btn"
        data-active={userSettingsModalOpen ? "true" : "false"}
        aria-label={railCollapsed ? labels.myAccountLabel : undefined}
        title={railCollapsed ? labels.myAccountLabel : undefined}
        onClick={onOpenMyAccount}
        className={`orcia-sidebar-nav-btn ${railCollapsed ? "justify-center px-0 py-2" : "gap-2.5 px-2.5 py-2"}`}
      >
        <OrciaIcon name="nav.account" />
        {!railCollapsed && <span className="flex-1">{labels.myAccountLabel}</span>}
      </button>

      {!hideSidebarShowcaseBtn && (
        <button
          type="button"
          data-testid="open-orcia-showcase-site-btn"
          data-active={pathname?.startsWith("/showcase") ? "true" : "false"}
          aria-label={railCollapsed ? labels.documentationLabel : undefined}
          title={railCollapsed ? labels.documentationLabel : undefined}
          onClick={onOpenShowcase}
          className={`orcia-sidebar-nav-btn ${railCollapsed ? "justify-center px-0 py-2" : "gap-2.5 px-2.5 py-2"}`}
        >
          <OrciaIcon name="bookOpen" />
          {!railCollapsed && <span className="flex-1">{labels.documentationLabel}</span>}
        </button>
      )}
    </>
  );
}
