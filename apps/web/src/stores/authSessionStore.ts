import {
  resolveUserRoleDisplayLabel,
  type OrciaIconName,
  type UiLocalePreference,
  type UiPermissionVerb,
} from "@orcia/ui";
import { create } from "zustand";

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
  | "models"
  | "connectors"
  | "packs";

export const ALL_SETTINGS_TABS: readonly SettingsTabKey[] = [
  "organization",
  "iam",
  "models",
  "connectors",
  "packs",
] as const;

export const SCOPED_LEAD_SETTINGS_TABS: readonly SettingsTabKey[] = [
  "organization",
  "iam",
] as const;

export const SETTINGS_TAB_ICON_NAMES: Readonly<Record<SettingsTabKey, OrciaIconName>> = {
  organization: "settings.org",
  iam: "settings.iam",
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

const READ_ONLY_HATS = new Set(["CONTRIBUTOR", "OBSERVER", "READ_ONLY_OBSERVER"]);
const LEAD_HATS = new Set(["BU_LEAD", "TEAM_LEAD"]);
const GLOBAL_ADMIN_ROLES = new Set(["PLATFORM_ADMIN", "SECOPS"]);

/**
 * Pure deterministic RBAC resolver for `/settings` (`CA-17.1.3`):
 * - `PLATFORM_ADMIN` & `SECOPS` (outside observer mode): all 5 tabs + full admin verbs.
 * - `BU_LEAD` & `TEAM_LEAD`: adaptive 2 tabs (`organization`, `iam`) + scoped admin verbs.
 * - `CONTRIBUTOR` & `OBSERVER` (`READ_ONLY_OBSERVER` or `readOnlyObserver=true`):
 *   `allowedVerbs = ["read"]` only, `canMutate = false`, explicit read-only notice + `Mon Compte` CTA.
 */
export function resolveSettingsAccess(session: AuthSessionSnapshot): ResolvedSettingsAccess {
  const hat = session.activeHat?.trim() || session.roles[0] || "PLATFORM_ADMIN";
  const roleSet = new Set(session.roles);

  if (session.readOnlyObserver === true || READ_ONLY_HATS.has(hat)) {
    return {
      visibleTabs: [],
      allowedVerbs: READ_ONLY_PERMISSION_VERBS,
      canMutate: false,
      isReadOnlyRestricted: true,
      effectiveRoleKey: session.readOnlyObserver ? "OBSERVER" : hat,
    };
  }

  if (LEAD_HATS.has(hat)) {
    return {
      visibleTabs: SCOPED_LEAD_SETTINGS_TABS,
      allowedVerbs: FULL_ADMIN_PERMISSION_VERBS,
      canMutate: true,
      isReadOnlyRestricted: false,
      effectiveRoleKey: hat,
    };
  }

  const hasGlobalAdminRole =
    GLOBAL_ADMIN_ROLES.has(hat) ||
    roleSet.has("PLATFORM_ADMIN") ||
    roleSet.has("SECOPS");

  if (hasGlobalAdminRole) {
    return {
      visibleTabs: ALL_SETTINGS_TABS,
      allowedVerbs: FULL_ADMIN_PERMISSION_VERBS,
      canMutate: true,
      isReadOnlyRestricted: false,
      effectiveRoleKey: hat,
    };
  }

  if (roleSet.has("BU_LEAD") || roleSet.has("TEAM_LEAD")) {
    const leadRole = roleSet.has("BU_LEAD") ? "BU_LEAD" : "TEAM_LEAD";
    return {
      visibleTabs: SCOPED_LEAD_SETTINGS_TABS,
      allowedVerbs: FULL_ADMIN_PERMISSION_VERBS,
      canMutate: true,
      isReadOnlyRestricted: false,
      effectiveRoleKey: leadRole,
    };
  }

  return {
    visibleTabs: [],
    allowedVerbs: READ_ONLY_PERMISSION_VERBS,
    canMutate: false,
    isReadOnlyRestricted: true,
    effectiveRoleKey: hat,
  };
}

export function resolveSessionHatLabel(
  session: AuthSessionSnapshot,
  locale: UiLocalePreference,
): string {
  const effectiveKey = session.readOnlyObserver
    ? "OBSERVER"
    : session.activeHat?.trim() || session.roles[0] || "PLATFORM_ADMIN";
  return resolveUserRoleDisplayLabel(effectiveKey, locale);
}

/**
 * Formats a count + noun phrase without raw `(s)` suffixes (`0/1` singular in FR, `1` singular in EN).
 */
export function formatCountNoun(
  count: number,
  singular: string,
  plural: string,
  locale: UiLocalePreference = "fr",
): string {
  const isPlural = locale === "en" ? count !== 1 : count > 1;
  return `${count} ${isPlural ? plural : singular}`;
}

export type UserSettingsModalTabKey =
  | "PREFERENCES_DISPLAY"
  | "PROFILE_SECURITY"
  | "PASSTHROUGH_SOURCES"
  | "IDE_MCP_KEYS";

export interface AuthSessionStoreState {
  readonly roles: readonly string[];
  readonly activeHat: string;
  readonly readOnlyObserver: boolean;
  readonly email: string | null;
  readonly displayName: string | null;
  readonly userSettingsModalOpen: boolean;
  readonly userSettingsModalInitialTab: UserSettingsModalTabKey | null;
  readonly setAuthSession: (
    patch: Partial<{
      roles: readonly string[];
      activeHat: string;
      readOnlyObserver: boolean;
      email: string | null;
      displayName: string | null;
    }>,
  ) => void;
  readonly setActiveHat: (hat: string) => void;
  readonly setUserSettingsModalOpen: (open: boolean) => void;
  readonly openUserSettingsModalAtTab: (tab: UserSettingsModalTabKey) => void;
  readonly resetAuthSession: () => void;
}

const DEFAULT_SESSION_STATE = {
  roles: ["PLATFORM_ADMIN", "SECOPS"] as readonly string[],
  activeHat: "PLATFORM_ADMIN",
  readOnlyObserver: false,
  email: null as string | null,
  displayName: null as string | null,
  userSettingsModalOpen: false,
  userSettingsModalInitialTab: null as UserSettingsModalTabKey | null,
};

export const useAuthSessionStore = create<AuthSessionStoreState>((set) => ({
  ...DEFAULT_SESSION_STATE,
  setAuthSession: (patch) =>
    set((state) => {
      const nextRoles = patch.roles ?? state.roles;
      const nextHat =
        patch.activeHat ??
        (patch.roles && patch.roles.length > 0 ? patch.roles[0]! : state.activeHat);
      return {
        ...state,
        ...patch,
        roles: nextRoles,
        activeHat: nextHat,
      };
    }),
  setActiveHat: (hat) => set({ activeHat: hat }),
  setUserSettingsModalOpen: (open) =>
    set((state) => ({
      userSettingsModalOpen: open,
      userSettingsModalInitialTab: open ? state.userSettingsModalInitialTab : null,
    })),
  openUserSettingsModalAtTab: (tab) =>
    set({
      userSettingsModalOpen: true,
      userSettingsModalInitialTab: tab,
    }),
  resetAuthSession: () => set({ ...DEFAULT_SESSION_STATE }),
}));

export function resetAuthSessionStore(): void {
  useAuthSessionStore.getState().resetAuthSession();
}
