import { createOrciaApiClient } from "@orcia/api-client";
import {
  ContextualHelpColumnAndCenter,
  OrciaIcon,
  type UiContextualHelpArticleView,
  type UiHelpArticleLayer,
} from "@orcia/ui";
import { createRoute } from "@tanstack/react-router";
import React, { useEffect, useMemo, useState } from "react";
import { useShellNavigation } from "../components/ShellContainer";
import { useI18n } from "../i18n";
import { useAuthSessionStore } from "../stores/authSessionStore";
import { Route as rootRoute } from "./__root";
import { validateOrciaRouteSearch } from "./searchSchema";

export function HelpCenterRouteView(): React.ReactElement {
  const { dictionary, locale } = useI18n();
  const { navigateToRoute } = useShellNavigation();
  const isAuthenticated = useAuthSessionStore((s) => s.isAuthenticated);
  const roles = useAuthSessionStore((s) => s.roles);
  const readOnlyObserver = useAuthSessionStore((s) => s.readOnlyObserver);
  const isAdmin =
    !readOnlyObserver &&
    roles.some((r) => r === "PLATFORM_ADMIN" || r === "ARCHITECT" || r === "TEAM_LEAD");
  const showTechnicalMetadata = !readOnlyObserver && roles.includes("PLATFORM_ADMIN");

  const copy = dictionary.ontologyGlossary;
  const apiClient = useMemo(() => createOrciaApiClient({ baseUrl: "" }), []);

  const fallbackArticle: UiContextualHelpArticleView = useMemo(
    () => ({
      resourceId: `help-base-help-${locale}`,
      uri: `orcia://system/help/help/${locale}`,
      title: copy.helpCenterOverviewTitle,
      version: "",
      lang: locale,
      layer: "BASE",
      packName: "core",
      boundRoutes: ["/help"],
      summaryWhatFor: copy.helpCenterOverviewSummary,
      stepByStepItems: [copy.helpCenterStep1, copy.helpCenterStep2],
      keyTermsItems: [copy.helpCenterKeyTerm1, copy.helpCenterKeyTerm2, copy.helpCenterKeyTerm3],
      faqItems: [copy.helpCenterFaq1],
      realExampleText: copy.helpCenterRealExample,
      commonPitfallsItems: [copy.helpCenterCommonPitfall1],
      casKey: "cas/help-center-overview",
      sha256: "sha256-help-center",
      previousVersion: null,
    }),
    [copy, locale],
  );

  const [resolvedArticle, setResolvedArticle] = useState<UiContextualHelpArticleView | null>(null);
  const [resolvedLayers, setResolvedLayers] = useState<readonly UiHelpArticleLayer[]>([]);
  const [resolvedCacheKey, setResolvedCacheKey] = useState<string>(
    `help:route:/help:core:${locale}`,
  );
  const [resolvedPrefill, setResolvedPrefill] = useState<string | null>(null);
  const [rollbackAvailable, setRollbackAvailable] = useState<boolean>(false);

  useEffect(() => {
    if (!isAuthenticated) {
      setResolvedArticle(null);
      return;
    }
    let cancelled = false;
    void apiClient
      .resolveContextualHelp("/help", locale, "core")
      .then((res) => {
        if (cancelled || !res?.active_article) return;
        const art = res.active_article;
        setResolvedArticle({
          resourceId: art.resource_id,
          uri: art.uri,
          title: art.title,
          version: art.version,
          lang: art.lang,
          layer: art.layer,
          packName: art.pack_name ?? null,
          boundRoutes: art.bound_routes,
          summaryWhatFor: art.summary_what_for,
          stepByStepItems:
            art.step_by_step_items.length > 0
              ? art.step_by_step_items
              : fallbackArticle.stepByStepItems,
          keyTermsItems:
            art.key_terms_items.length > 0
              ? art.key_terms_items
              : fallbackArticle.keyTermsItems,
          faqItems: art.faq_items.length > 0 ? art.faq_items : fallbackArticle.faqItems,
          realExampleText: art.real_example_text ?? fallbackArticle.realExampleText,
          commonPitfallsItems:
            art.common_pitfalls_items && art.common_pitfalls_items.length > 0
              ? art.common_pitfalls_items
              : fallbackArticle.commonPitfallsItems,
          casKey: art.cas_key,
          sha256: art.sha256,
          previousVersion: art.previous_version ?? null,
        });
        setResolvedLayers(res.merged_layers);
        setResolvedCacheKey(res.redis_cache_key);
        setResolvedPrefill(res.ask_assistant_prefill || null);
        setRollbackAvailable(
          Boolean(res.previous_version_available ?? res.rollback_available),
        );
      })
      .catch((err: unknown) => {
        console.warn("[help-center] fallback to localized overview:", err);
      });
    return () => {
      cancelled = true;
    };
  }, [apiClient, fallbackArticle, isAuthenticated, locale]);

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
        pack="core"
        redisCacheKey={resolvedCacheKey}
        mergedLayers={resolvedLayers}
        article={resolvedArticle ?? fallbackArticle}
        rollbackAvailable={rollbackAvailable}
        isAdmin={isAdmin}
        showTechnicalMetadata={showTechnicalMetadata}
        askAssistantPrefill={resolvedPrefill ?? undefined}
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
