import type {
  ConfiguredAuditEvent,
  ConfiguredPlatformAdmin,
} from "./platformSetupStorageHelpers";

export function formatHumanReadableScopePath(rawScopePath: string | undefined): string {
  const trimmed = (rawScopePath ?? "").trim();
  if (!trimmed || trimmed === "GLOBAL" || trimmed === "scope-global") {
    return "Plateforme entière";
  }
  return trimmed;
}

export function cleanAuditSummaryJargon(rawSummary: string): string {
  return rawSummary
    .replace(/\bsur GLOBAL\b/g, "sur Plateforme entière")
    .replace(/\(PUBLISHED\)/g, "(Publié)")
    .replace(/\(DRAFT\)/g, "(Brouillon)")
    .replace(/\(VALIDATED\)/g, "(Validé)")
    .replace(/\bmode passthrough\b/gi, "mode Identité personnelle")
    .replace(/\bmode service_account\b/gi, "mode Compte technique partagé");
}

export function normalizeConfiguredAuditEvent(
  raw: Partial<ConfiguredAuditEvent> & Record<string, unknown>,
  fallbackActor?: ConfiguredPlatformAdmin | null,
): ConfiguredAuditEvent {
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
  );
  const actorName =
    typeof raw.actorName === "string" && raw.actorName.trim()
      ? raw.actorName.trim()
      : (fallbackActor?.displayName ?? "Administrateur de la plateforme");
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
      ? formatHumanReadableScopePath(raw.scopeLabel)
      : formatHumanReadableScopePath(rawScopePath);
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
