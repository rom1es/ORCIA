import { OrciaAlertBanner, OrciaIcon } from "@orcia/ui";
import { createRoute } from "@tanstack/react-router";
import React from "react";
import { usePlatformSetup } from "../components/platformSetupStore";
import { useShellNavigation } from "../components/ShellContainer";
import { useI18n } from "../i18n";
import {
  canMutateMyOrganization,
  useAuthSessionStore,
} from "../stores/authSessionStore";
import { Route as rootRoute } from "./__root";
import { validateOrciaRouteSearch } from "./searchSchema";
import { SettingsOrganizationUnitsBlock } from "./SettingsOrganizationUnitsBlock";

export function OrganizationPageView(): React.ReactElement {
  const { dictionary, locale } = useI18n();
  const { openHelpSection } = useShellNavigation();
  const isFr = locale === "fr";
  const orgLabels = dictionary.settingsHub.organizationTab;
  const copy = dictionary.settingsHub;

  const roles = useAuthSessionStore((s) => s.roles);
  const activeHat = useAuthSessionStore((s) => s.activeHat);
  const readOnlyObserver = useAuthSessionStore((s) => s.readOnlyObserver);
  const canMutateOrg = canMutateMyOrganization({ roles, activeHat, readOnlyObserver });

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

      {!canMutateOrg && (
        <OrciaAlertBanner
          tone="cobalt"
          role="status"
          testId="organization-readonly-access-banner"
          title={copy.readOnlyRestrictedTitle}
        >
          {orgLabels.readOnlyChartNotice}
        </OrciaAlertBanner>
      )}

      <SettingsOrganizationUnitsBlock
        isFr={isFr}
        canMutate={canMutateOrg}
        orgUnits={orgUnits}
        workspaces={workspaces}
        openHelpSection={openHelpSection}
        syncOrgUnitsFromServer={syncOrgUnitsFromServer}
      />
    </div>
  );
}

export const Route = createRoute({
  getParentRoute: () => rootRoute,
  path: "/organization",
  validateSearch: validateOrciaRouteSearch,
  component: OrganizationPageView,
});
