import { OrciaProductShowcaseSiteView } from "@orcia/ui";
import { createRoute } from "@tanstack/react-router";
import React from "react";
import { useShellNavigation } from "../components/ShellContainer";
import { ORCIA_SITE_MANIFEST } from "../generated/orciaSiteManifest";
import { useI18n } from "../i18n";
import { Route as rootRoute } from "./__root";
import { validateOrciaRouteSearch } from "./searchSchema";
import { SHOWCASE_ARCHITECTURE_LABELS_BY_LOCALE } from "./showcaseArchitectureCatalog";

export function ShowcaseRouteView(): React.ReactElement {
  const { locale, dictionary } = useI18n();
  const { navigateToRoute, openHelpSection } = useShellNavigation();

  return (
    <OrciaProductShowcaseSiteView
      manifest={ORCIA_SITE_MANIFEST}
      labels={{
        ...dictionary.showcase,
        architecture: SHOWCASE_ARCHITECTURE_LABELS_BY_LOCALE[locale],
      }}
      onNavigateToRoute={navigateToRoute}
      onOpenHelpSection={openHelpSection}
    />
  );
}

export const Route = createRoute({
  getParentRoute: () => rootRoute,
  path: "/showcase",
  validateSearch: validateOrciaRouteSearch,
  component: ShowcaseRouteView,
});
