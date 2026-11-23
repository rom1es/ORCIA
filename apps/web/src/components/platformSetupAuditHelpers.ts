import { DICTIONARIES, type SupportedWebLocale } from "../i18n";
import type {
  ConfiguredAuditEvent,
  ConfiguredPlatformAdmin,
} from "./platformSetupStorageHelpers";

export function formatHumanReadableScopePath(
  rawScopePath: string | undefined,
  locale: SupportedWebLocale = "fr",
): string {
  const trimmed = (rawScopePath ?? "").trim();
  if (!trimmed || trimmed === "GLOBAL" || trimmed === "scope-global") {
    return DICTIONARIES[locale].shellChrome.auditSanitizer.globalScopeLabel;
  }
  return trimmed;
}

export function cleanAuditSummaryJargon(
  rawSummary: string,
  locale: SupportedWebLocale = "fr",
): string {
  const s = DICTIONARIES[locale].shellChrome.auditSanitizer;
  return rawSummary
    .replace(/\bsur GLOBAL\b/g, s.onGlobalPhrase)
    .replace(/\(PUBLISHED\)/g, s.statusPublished)
    .replace(/\(DRAFT\)/g, s.statusDraft)
    .replace(/\(VALIDATED\)/g, s.statusValidated)
    .replace(/\bmode passthrough\b/gi, s.personalIdentityMode)
    .replace(/\bmode service_account\b/gi, s.sharedAccountMode);
}

export function normalizeConfiguredAuditEvent(
  raw: Partial<ConfiguredAuditEvent> & Record<string, unknown>,
  fallbackActor?: ConfiguredPlatformAdmin | null,
  locale: SupportedWebLocale = "fr",
): ConfiguredAuditEvent {
  const govCopy = DICTIONARIES[locale].shellChrome.platformSetupGovernance;
  const id = typeof raw.id === "string" && raw.id.trim() ? raw.id.trim() : "evt-1";
  const timestampIso =
    typeof raw.timestampIso === "string" && raw.timestampIso.trim()
      ? raw.timestampIso.trim()
      : new Date().toISOString();
  const eventType =
    typeof raw.eventType === "string" && raw.eventType.trim()
      ? raw.eventType.trim()
      : "SettingsChanged";
  const summary = cleanAuditSummaryJargon(
    typeof raw.summary === "string" ? raw.summary : "",
    locale,
  );
  const actorName =
    typeof raw.actorName === "string" && raw.actorName.trim()
      ? raw.actorName.trim()
      : (fallbackActor?.displayName ?? govCopy.defaultAdminDisplayName);
  const actorEmail =
    typeof raw.actorEmail === "string" && raw.actorEmail.trim()
      ? raw.actorEmail.trim()
      : fallbackActor?.email;
  const rawScopePath =
    typeof raw.scopePath === "string" && raw.scopePath.trim()
      ? raw.scopePath.trim()
      : "GLOBAL";
  const scopeLabel =
    typeof raw.scopeLabel === "string" && raw.scopeLabel.trim()
      ? formatHumanReadableScopePath(raw.scopeLabel, locale)
      : formatHumanReadableScopePath(rawScopePath, locale);
  const scopeId =
    typeof raw.scopeId === "string" && raw.scopeId.trim()
      ? raw.scopeId.trim()
      : rawScopePath === "GLOBAL"
        ? "scope-global"
        : undefined;

  return {
    id,
    timestampIso,
    eventType,
    summary,
    actorName,
    ...(actorEmail ? { actorEmail } : {}),
    ...(scopeId ? { scopeId } : {}),
    scopePath: rawScopePath,
    scopeLabel,
  };
}
