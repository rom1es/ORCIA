import { OrciaIcon, PermissionGuard } from "@orcia/ui";
import { createRoute } from "@tanstack/react-router";
import React from "react";
import { usePlatformSetup } from "../components/platformSetupStore";
import { useShellNavigation } from "../components/ShellContainer";
import { useI18n } from "../i18n";
import {
  canAccessMyOrganization,
  READ_ONLY_PERMISSION_VERBS,
  useAuthSessionStore,
} from "../stores/authSessionStore";
import { Route as rootRoute } from "./__root";
import { validateOrciaRouteSearch } from "./searchSchema";
import { SettingsOrganizationUnitsBlock } from "./SettingsOrganizationUnitsBlock";

export function OrganizationPageView(): React.ReactElement {
  const { dictionary, locale } = useI18n();
  const { openHelpSection, navigateToRoute } = useShellNavigation();
  const isFr = locale === "fr";
  const orgLabels = dictionary.settingsHub.organizationTab;
  const copy = dictionary.settingsHub;

  const roles = useAuthSessionStore((s) => s.roles);
  const activeHat = useAuthSessionStore((s) => s.activeHat);
  const readOnlyObserver = useAuthSessionStore((s) => s.readOnlyObserver);
  const canAccessOrg = canAccessMyOrganization({ roles, activeHat, readOnlyObserver });

  const { orgUnits, workspaces, syncOrgUnitsFromServer } = usePlatformSetup();

  return (
    <div
      data-testid="organization-page"
      style={{ display: "flex", flexDirection: "column", gap: "16px" }}
    >
      <header
        className="orcia-bento-card"
        style={{ display: "flex", flexDirection: "column", gap: "6px" }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <OrciaIcon name="organizationBu" size={18} />
          <h1 style={{ margin: 0, fontSize: "var(--font-size-h2)" }}>{orgLabels.pageTitle}</h1>
        </div>
        <p
          style={{
            margin: 0,
            fontSize: "var(--font-size-body)",
            color: "var(--color-muted-foreground)",
          }}
        >
          {orgLabels.pageSubtitle}
        </p>
      </header>

      {!canAccessOrg ? (
        <PermissionGuard
          scopePath="GLOBAL"
          verb="read"
          allowedVerbs={READ_ONLY_PERMISSION_VERBS}
          labels={{
            passiveLockBadge: isFr ? "Accès restreint" : "Restricted access",
            passiveLockDescription: copy.readOnlyRestrictedBody,
            requestAccessCta: copy.requestAccessLabel,
            disabledHint: copy.lockedSectionNotice,
          }}
        >
          <section
            data-testid="organization-readonly-access-banner"
            className="orcia-bento-card"
            style={{ display: "flex", flexDirection: "column", gap: "10px" }}
          >
            <h2 style={{ margin: 0, fontSize: "15px" }}>{copy.readOnlyRestrictedTitle}</h2>
            <p style={{ margin: 0, fontSize: "13px", color: "var(--color-muted-foreground)" }}>
              {copy.readOnlyRestrictedBody}
            </p>
            <div>
              <button
                type="button"
                className="orcia-ds-btn orcia-ds-btn-secondary"
                onClick={() => navigateToRoute("/spaces")}
              >
                {orgLabels.openWorkspacesCta}
              </button>
            </div>
          </section>
        </PermissionGuard>
      ) : (
        <SettingsOrganizationUnitsBlock
          isFr={isFr}
          canMutate={canAccessOrg}
          orgUnits={orgUnits}
          workspaces={workspaces}
          openHelpSection={openHelpSection}
          syncOrgUnitsFromServer={syncOrgUnitsFromServer}
        />
      )}
    </div>
  );
}

export const Route = createRoute({
  getParentRoute: () => rootRoute,
  path: "/organization",
  validateSearch: validateOrciaRouteSearch,
  component: OrganizationPageView,
});
