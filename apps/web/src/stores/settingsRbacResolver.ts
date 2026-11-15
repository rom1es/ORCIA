import {
  resolveUserRoleDisplayLabel,
  type OrciaIconName,
  type UiLocalePreference,
  type UiPermissionVerb,
} from "@orcia/ui";

export type OrciaSystemRole =
  | "PLATFORM_ADMIN"
  | "SECOPS"
  | "BU_LEAD"
  | "TEAM_LEAD"
  | "CONTRIBUTOR"
  | "OBSERVER"
  | "READ_ONLY_OBSERVER";

export type SettingsTabKey =
  | "organization"
  | "iam"
  | "authentication"
  | "models"
  | "connectors"
  | "packs";

export const ALL_SETTINGS_TABS: readonly SettingsTabKey[] = [
  "organization",
  "iam",
  "authentication",
  "models",
  "connectors",
  "packs",
] as const;

export const SCOPED_LEAD_SETTINGS_TABS: readonly SettingsTabKey[] = [] as const;

export const SETTINGS_TAB_ICON_NAMES: Readonly<Record<SettingsTabKey, OrciaIconName>> = {
  organization: "settings.org",
  iam: "settings.iam",
  authentication: "settings.auth",
  models: "settings.models",
  connectors: "settings.connectors",
  packs: "settings.packs",
};

export const FULL_ADMIN_PERMISSION_VERBS: readonly UiPermissionVerb[] = [
  "create",
  "read",
  "update",
  "delete",
  "execute",
  "grant",
] as const;

export const READ_ONLY_PERMISSION_VERBS: readonly UiPermissionVerb[] = ["read"] as const;

export interface AuthSessionSnapshot {
  readonly roles: readonly string[];
  readonly activeHat?: string;
  readonly readOnlyObserver?: boolean;
}

export interface ResolvedSettingsAccess {
  readonly visibleTabs: readonly SettingsTabKey[];
  readonly allowedVerbs: readonly UiPermissionVerb[];
  readonly canMutate: boolean;
  readonly isReadOnlyRestricted: boolean;
  readonly effectiveRoleKey: string;
}

export function isPlatformAdministratorSession(session: AuthSessionSnapshot): boolean {
  if (session.readOnlyObserver === true) {
    return false;
  }
  const roleSet = new Set(session.roles);
  if (!roleSet.has("PLATFORM_ADMIN")) {
    return false;
  }
  const hat = session.activeHat?.trim() || session.roles[0] || "CONTRIBUTOR";
  return hat === "PLATFORM_ADMIN";
}

export function resolveSettingsAccess(session: AuthSessionSnapshot): ResolvedSettingsAccess {
  const hat = session.activeHat?.trim() || session.roles[0] || "CONTRIBUTOR";

  if (isPlatformAdministratorSession(session)) {
    return {
      visibleTabs: ALL_SETTINGS_TABS,
      allowedVerbs: FULL_ADMIN_PERMISSION_VERBS,
      canMutate: true,
      isReadOnlyRestricted: false,
      effectiveRoleKey: "PLATFORM_ADMIN",
    };
  }

  return {
    visibleTabs: [],
    allowedVerbs: READ_ONLY_PERMISSION_VERBS,
    canMutate: false,
    isReadOnlyRestricted: true,
    effectiveRoleKey: session.readOnlyObserver ? "OBSERVER" : hat,
  };
}

export function resolveSessionHatLabel(
  session: AuthSessionSnapshot,
  locale: UiLocalePreference,
): string {
  const effectiveKey = session.readOnlyObserver
    ? "OBSERVER"
    : session.activeHat?.trim() || session.roles[0] || "CONTRIBUTOR";
  return resolveUserRoleDisplayLabel(effectiveKey, locale);
}

export function formatCountNoun(
  count: number,
  singular: string,
  plural: string,
  locale: UiLocalePreference = "fr",
): string {
  const isPlural = locale === "en" ? count !== 1 : count > 1;
  return `${count} ${isPlural ? plural : singular}`;
}
