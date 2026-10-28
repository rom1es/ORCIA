import {
  createRootRouteWithContext,
  Outlet,
  useLocation,
  useRouter,
} from "@tanstack/react-router";
import React from "react";
import { OrciaNavigationProvider } from "../components/navigationAdapter";
import { ShellContainer } from "../components/ShellContainer";
import { I18nProvider } from "../i18n";
import { type OrciaRouterContext, validateOrciaRouteSearch } from "./searchSchema";

function RootLayoutComponent() {
  const location = useLocation();
  const router = useRouter();

  const fixtureFromSearch =
    new URLSearchParams(location.searchStr ?? "").get("fixture") === "test";

  return (
    <I18nProvider initialLocale="fr">
      <OrciaNavigationProvider
        adapter={{
          pathname: location.pathname,
          navigateTo: (href: string) => {
            void router.navigate({ href });
          },
        }}
      >
        <ShellContainer fixtureMode={fixtureFromSearch}>
          <Outlet />
        </ShellContainer>
      </OrciaNavigationProvider>
    </I18nProvider>
  );
}

export const Route = createRootRouteWithContext<OrciaRouterContext>()({
  validateSearch: validateOrciaRouteSearch,
  component: RootLayoutComponent,
});
