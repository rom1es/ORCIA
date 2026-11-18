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
  | "BU_DIRECTOR"
  | "TEAM_LEAD"
  | "ONTOLOGY_LEAD"
  | "CONTRIBUTOR"
  | "OBSERVER"
  | "READ_ONLY_OBSERVER";

export type SettingsTabKey =
  | "iam"
  | "authentication"
  | "models"
  | "connectors"
  | "packs";

export const ALL_SETTINGS_TABS: readonly SettingsTabKey[] = [
  "iam",
  "authentication",
  "models",
  "connectors",
  "packs",
] as const;

export const SCOPED_LEAD_SETTINGS_TABS: readonly SettingsTabKey[] = [] as const;

export const SETTINGS_TAB_ICON_NAMES: Readonly<Record<SettingsTabKey, OrciaIconName>> = {
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
  /** @deprecated Ignored for RBAC evaluation — kept optional for test fixture compatibility. */
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

const ORG_MENU_ALLOWED_ROLES = new Set([
  "PLATFORM_ADMIN",
  "BU_LEAD",
  "BU_DIRECTOR",
  "TEAM_LEAD",
]);

const GLOBAL_AUDIT_ALLOWED_ROLES = new Set(["PLATFORM_ADMIN", "SECOPS"]);

function hasAnyRole(roles: readonly string[], allowed: ReadonlySet<string>): boolean {
  return roles.some((r) => allowed.has(r.trim().toUpperCase()));
}

export function isPlatformAdministratorSession(session: AuthSessionSnapshot): boolean {
  if (session.readOnlyObserver === true) {
    return false;
  }
  return session.roles.some((r) => r.trim().toUpperCase() === "PLATFORM_ADMIN");
}

export function isSecopsSession(session: AuthSessionSnapshot): boolean {
  if (session.readOnlyObserver === true) {
    return false;
  }
  return session.roles.some((r) => r.trim().toUpperCase() === "SECOPS");
}

export function canAccessConfigurationSettings(session: AuthSessionSnapshot): boolean {
  return isPlatformAdministratorSession(session) || isSecopsSession(session);
}

export function canAccessMyOrganization(session: AuthSessionSnapshot): boolean {
  if (session.readOnlyObserver === true) {
    return false;
  }
  return hasAnyRole(session.roles, ORG_MENU_ALLOWED_ROLES);
}

export function canObserveGlobalAuditScope(session: AuthSessionSnapshot): boolean {
  if (session.readOnlyObserver === true) {
    return false;
  }
  return hasAnyRole(session.roles, GLOBAL_AUDIT_ALLOWED_ROLES);
}

export function resolveSettingsAccess(session: AuthSessionSnapshot): ResolvedSettingsAccess {
  const primaryRole = session.roles[0]?.trim() || "CONTRIBUTOR";

  if (isPlatformAdministratorSession(session)) {
    return {
      visibleTabs: ALL_SETTINGS_TABS,
      allowedVerbs: FULL_ADMIN_PERMISSION_VERBS,
      canMutate: true,
      isReadOnlyRestricted: false,
      effectiveRoleKey: "PLATFORM_ADMIN",
    };
  }

  if (isSecopsSession(session)) {
    return {
      visibleTabs: ["iam"],
      allowedVerbs: FULL_ADMIN_PERMISSION_VERBS,
      canMutate: true,
      isReadOnlyRestricted: false,
      effectiveRoleKey: "SECOPS",
    };
  }

  return {
    visibleTabs: [],
    allowedVerbs: READ_ONLY_PERMISSION_VERBS,
    canMutate: false,
    isReadOnlyRestricted: true,
    effectiveRoleKey: session.readOnlyObserver ? "OBSERVER" : primaryRole,
  };
}

export function resolveSessionHatLabel(
  session: AuthSessionSnapshot,
  locale: UiLocalePreference,
): string {
  const effectiveKey = session.readOnlyObserver
    ? "OBSERVER"
    : session.roles[0]?.trim() || "CONTRIBUTOR";
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
