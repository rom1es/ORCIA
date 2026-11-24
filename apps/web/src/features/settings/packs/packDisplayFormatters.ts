import { resolveDictionaryForFlag, resolveLocaleForFlag } from "../../../i18n";

const SINGULAR_CHECK_BY_LOCALE = {
  fr: (count: number) => count <= 1,
  en: (count: number) => count === 1,
} as const;

export function formatPackCounterLabel(
  count: number,
  singularFr: string,
  pluralFr: string,
  singularEn: string,
  pluralEn: string,
  isFr: boolean,
): string {
  const locale = resolveLocaleForFlag(isFr);
  const isSingular = SINGULAR_CHECK_BY_LOCALE[locale](count);
  const formsByLocale = {
    fr: { singular: singularFr, plural: pluralFr },
    en: { singular: singularEn, plural: pluralEn },
  } as const;
  const forms = formsByLocale[locale];
  return isSingular ? forms.singular : forms.plural;
}

export function formatPackCountNoun(
  count: number,
  singular: string,
  plural: string,
  isFr: boolean,
): string {
  const locale = resolveLocaleForFlag(isFr);
  return SINGULAR_CHECK_BY_LOCALE[locale](count) ? singular : plural;
}

export function formatConnectorDisplayName(connectorType: string, isFr: boolean): string {
  const normalized = connectorType.trim().toLowerCase();
  const known =
    resolveDictionaryForFlag(isFr).featureAdminCatalogSettings.packsRegistry.knownConnectorNames[
      normalized
    ];
  if (known) {
    return known;
  }
  const stripped = normalized
    .replace(/^mcp:/, "")
    .replace(/^atlassian-/, "Atlassian ");
  return stripped
    .split(/[-_]+/)
    .filter(Boolean)
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
}

export function formatConnectorScopes(
  scopes: readonly string[],
  isFr: boolean,
): string {
  const dict =
    resolveDictionaryForFlag(isFr).featureAdminCatalogSettings.packsRegistry.scopeLabels;
  return scopes
    .map((scope) => dict[scope.trim().toLowerCase()] ?? scope)
    .join(", ");
}

export function formatPackAgentDisplayName(slug: string, isFr: boolean): string {
  const clean = slug.trim();
  const known =
    resolveDictionaryForFlag(isFr).featureAdminCatalogSettings.packsRegistry.knownAgentNames[clean];
  if (known) {
    return known;
  }
  const stripped = clean.replace(/^(?:crl|sdlc|orcia)-/, "");
  return stripped
    .split(/[-_]+/)
    .filter(Boolean)
    .map((part) => (part.toLowerCase() === "ia" ? "IA" : part.charAt(0).toUpperCase() + part.slice(1)))
    .join(" ");
}
