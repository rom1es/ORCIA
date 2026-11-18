import { ContextualHelpColumnAndCenter, OrciaIcon } from "@orcia/ui";
import { createRoute } from "@tanstack/react-router";
import React from "react";
import { useShellNavigation } from "../components/ShellContainer";
import { useI18n } from "../i18n";
import { Route as rootRoute } from "./__root";
import { validateOrciaRouteSearch } from "./searchSchema";

export function HelpCenterRouteView(): React.ReactElement {
  const { dictionary, locale } = useI18n();
  const { navigateToRoute } = useShellNavigation();
  const copy = dictionary.ontologyGlossary;

  return (
    <div data-testid="help-menu-center-view" style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
      <section
        data-testid="help-showcase-site-banner"
        className="orcia-bento-card"
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "12px",
        }}
      >
        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          <strong>
            <OrciaIcon name="globe" /> {copy.helpCenterShowcaseTitle}
          </strong>
          <span className="text-xs" style={{ color: "var(--color-text-secondary)" }}>
            {copy.helpCenterShowcaseDesc}
          </span>
        </div>
        <button
          type="button"
          data-testid="open-orcia-showcase-site-btn"
          onClick={() => navigateToRoute("/showcase")}
          className="orcia-ds-btn orcia-ds-btn-primary"
        >
          <OrciaIcon name="globe" /> <span>{copy.helpCenterShowcaseBtnLabel}</span>
        </button>
      </section>

      <ContextualHelpColumnAndCenter
        mode="HELP_MENU_CENTER"
        route="/help"
        pack="orcia-pack-sdlc@1.0.0"
        redisCacheKey={`help:route:/help:orcia-pack-sdlc@1.0.0:${locale}`}
        mergedLayers={["BASE", "PACK", "WORKSPACE"]}
        article={{
          resourceId: "help-center-overview",
          uri: "orcia://system/help/help-center-overview@1.0.0",
          title: copy.helpCenterOverviewTitle,
          version: "1.0.0",
          lang: locale,
          layer: "BASE",
          packName: "orcia-pack-sdlc",
          boundRoutes: ["/cockpit", "/assistant", "/spaces", "/processes", "/agents", "/help"],
          summaryWhatFor: copy.helpCenterOverviewSummary,
          stepByStepItems: [copy.helpCenterStep1, copy.helpCenterStep2],
          keyTermsItems: [copy.helpCenterKeyTerm1, copy.helpCenterKeyTerm2, copy.helpCenterKeyTerm3],
          faqItems: [copy.helpCenterFaq1],
          casKey: "cas/help-center-overview-v1",
          sha256: "sha256-help-center-v1",
          previousVersion: "0.9.0",
        }}
        rollbackAvailable={true}
        isAdmin={true}
        labels={dictionary.contextualHelpHybrid}
      />
    </div>
  );
}

export const Route = createRoute({
  getParentRoute: () => rootRoute,
  path: "/help",
  validateSearch: validateOrciaRouteSearch,
  component: HelpCenterRouteView,
});
