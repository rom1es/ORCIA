import { OrciaAlertBanner } from "@orcia/ui";
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
  const { dictionary, isFr } = useI18n();
  const { openHelpSection } = useShellNavigation();
  const orgLabels = dictionary.settingsHub.organizationTab;
  const copy = dictionary.settingsHub;

  const roles = useAuthSessionStore((s) => s.roles);
  const activeHat = useAuthSessionStore((s) => s.activeHat);
  const readOnlyObserver = useAuthSessionStore((s) => s.readOnlyObserver);
  const canMutateOrg = canMutateMyOrganization({ roles, activeHat, readOnlyObserver });

  const { orgUnits, workspaces, syncOrgUnitsFromServer } = usePlatformSetup();

  const readOnlyBanner = !canMutateOrg ? (
    <OrciaAlertBanner
      tone="cobalt"
      role="status"
      testId="organization-readonly-access-banner"
      title={copy.readOnlyRestrictedTitle}
    >
      {orgLabels.readOnlyChartNotice}
    </OrciaAlertBanner>
  ) : undefined;

  return (
    <div data-testid="organization-page" className="orcia-ds-page">
      <SettingsOrganizationUnitsBlock
        isFr={isFr}
        canMutate={canMutateOrg}
        showPageHeader={true}
        readOnlyAccessNotice={readOnlyBanner}
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
