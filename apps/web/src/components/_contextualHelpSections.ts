import type { UiContextualHelpSectionItem } from "@orcia/ui";
import { DICTIONARIES } from "../i18n";
import {
  CONFIGURATION_SECTIONS_EN,
  SECTIONS_BY_ROUTE_EN,
} from "../i18n/locales/contextual_help_sections_en";
import {
  CONFIGURATION_SECTIONS_FR,
  SECTIONS_BY_ROUTE_FR,
} from "../i18n/locales/contextual_help_sections_fr";

export {
  CONFIGURATION_SECTIONS_EN,
  CONFIGURATION_SECTIONS_FR,
  SECTIONS_BY_ROUTE_EN,
  SECTIONS_BY_ROUTE_FR,
};

export function normalizeCanonicalHelpRoute(pathname: string | undefined): string {
  const clean = (pathname ?? "/cockpit").split("?")[0]?.split("#")[0]?.trim() || "/cockpit";
  if (clean === "/" || clean.startsWith("/cockpit")) return "/cockpit";
  if (clean.startsWith("/inbox")) return "/inbox";
  if (clean.startsWith("/assistant")) return "/assistant";
  if (clean.startsWith("/spaces") || clean.startsWith("/workspaces")) return "/spaces";
  if (clean.startsWith("/processes")) return "/processes";
  if (clean.startsWith("/gates")) return "/gates";
  if (clean.startsWith("/agents")) return "/agents";
  if (clean.startsWith("/catalog")) return "/catalog";
  if (clean.startsWith("/finops")) return "/finops";
  if (clean.startsWith("/activity")) return "/activity";
  if (clean.startsWith("/ontology")) return "/ontology";
  if (clean.startsWith("/settings/packs")) return "/settings/packs";
  if (
    clean.startsWith("/settings") ||
    clean.startsWith("/configuration") ||
    clean.startsWith("/organization") ||
    clean.startsWith("/bootstrap")
  ) {
    return "/settings";
  }
  if (clean.startsWith("/showcase")) return "/showcase";
  if (clean.startsWith("/help")) return "/help";
  return "/cockpit";
}

export function getContextualHelpSectionsForRoute(
  pathname: string | undefined,
  locale: "fr" | "en",
): readonly UiContextualHelpSectionItem[] {
  const canonical = normalizeCanonicalHelpRoute(pathname);
  return DICTIONARIES[locale].contextualHelp.sectionsByRoute[canonical] ?? [];
}
