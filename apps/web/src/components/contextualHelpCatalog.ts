import type {
  EightFixedMenuKey,
  UiContextualHelpArticleView,
} from "@orcia/ui";
import { DICTIONARIES } from "../i18n";
import {
  getContextualHelpSectionsForRoute,
  normalizeCanonicalHelpRoute,
} from "./_contextualHelpSections";

export interface BuildContextualHelpArticleParams {
  readonly activeMenuKey: EightFixedMenuKey;
  readonly pathname: string | undefined;
  readonly locale: "fr" | "en";
  readonly title: string;
  readonly defaultSummary: string;
}

export function buildContextualHelpArticle({
  activeMenuKey,
  pathname,
  locale,
  title,
  defaultSummary,
}: BuildContextualHelpArticleParams): UiContextualHelpArticleView {
  const helpCopy = DICTIONARIES[locale].contextualHelp;
  const canonicalRoute = normalizeCanonicalHelpRoute(pathname);
  const routeSections = getContextualHelpSectionsForRoute(pathname, locale);

  if (canonicalRoute === "/settings") {
    return {
      resourceId: "help-base-settings",
      uri: `orcia://system/help/settings/${locale}`,
      title,
      version: "",
      lang: locale,
      layer: "BASE",
      packName: "core",
      boundRoutes: [pathname ?? "/settings"],
      summaryWhatFor: helpCopy.settingsArticle.summaryWhatFor,
      stepByStepItems: helpCopy.settingsArticle.stepByStepItems,
      realExampleText: helpCopy.settingsArticle.realExampleText,
      commonPitfallsItems: helpCopy.settingsArticle.commonPitfallsItems,
      keyTermsItems: [],
      faqItems: [],
      sections: routeSections,
      casKey: "",
      sha256: "",
      previousVersion: null,
    };
  }

  const narrative = helpCopy.routeFallbacks[canonicalRoute];

  return {
    resourceId: `help-${activeMenuKey}`,
    uri: `orcia://system/help/${activeMenuKey}/${locale}`,
    title,
    version: "",
    lang: locale,
    layer: "BASE",
    packName: "core",
    boundRoutes: [pathname ?? canonicalRoute],
    summaryWhatFor: narrative?.summaryWhatFor ?? defaultSummary,
    stepByStepItems: narrative?.steps ?? helpCopy.defaultSteps,
    realExampleText: narrative?.realExampleText ?? null,
    commonPitfallsItems: narrative?.commonPitfallsItems ?? [],
    keyTermsItems: [],
    faqItems: [],
    sections: routeSections,
    casKey: "",
    sha256: "",
    previousVersion: null,
  };
}
