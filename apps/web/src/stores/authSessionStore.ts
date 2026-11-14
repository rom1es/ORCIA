import { createOrciaApiClient } from "@orcia/api-client";
import { create } from "zustand";
import {
  ALL_SETTINGS_TABS,
  formatCountNoun,
  FULL_ADMIN_PERMISSION_VERBS,
  READ_ONLY_PERMISSION_VERBS,
  resolveSessionHatLabel,
  resolveSettingsAccess,
  SCOPED_LEAD_SETTINGS_TABS,
  SETTINGS_TAB_ICON_NAMES,
  type AuthSessionSnapshot,
  type OrciaSystemRole,
  type ResolvedSettingsAccess,
  type SettingsTabKey,
} from "./settingsRbacResolver";

export {
  ALL_SETTINGS_TABS,
  formatCountNoun,
  FULL_ADMIN_PERMISSION_VERBS,
  READ_ONLY_PERMISSION_VERBS,
  resolveSessionHatLabel,
  resolveSettingsAccess,
  SCOPED_LEAD_SETTINGS_TABS,
  SETTINGS_TAB_ICON_NAMES,
  type AuthSessionSnapshot,
  type OrciaSystemRole,
  type ResolvedSettingsAccess,
  type SettingsTabKey,
};

export type UserSettingsModalTabKey =
  | "PREFERENCES_DISPLAY"
  | "PROFILE_SECURITY"
  | "PASSTHROUGH_SOURCES"
  | "IDE_MCP_KEYS";

export interface AuthSessionStoreState {
  readonly isAuthenticated: boolean;
  readonly isHydrating: boolean;
  readonly mustChangePassword: boolean;
  readonly accessToken: string | null;
  readonly roles: readonly string[];
  readonly activeHat: string;
  readonly readOnlyObserver: boolean;
  readonly email: string | null;
  readonly displayName: string | null;
  readonly userSettingsModalOpen: boolean;
  readonly userSettingsModalInitialTab: UserSettingsModalTabKey | null;
  readonly setAuthSession: (
    patch: Partial<{
      isAuthenticated: boolean;
      isHydrating: boolean;
      mustChangePassword: boolean;
      accessToken: string | null;
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
  readonly clearMustChangePassword: () => void;
  readonly loginWithSession: (res: {
    access_token?: string;
    accessToken?: string;
    email: string;
    display_name?: string;
    displayName?: string;
    platform_role?: string;
    platformRole?: string;
    roles?: readonly string[] | string[];
    must_change_password?: boolean;
    mustChangePassword?: boolean;
  }) => void;
  readonly logoutSession: () => Promise<void>;
  readonly hydrateSession: () => Promise<void>;
  readonly resetAuthSession: () => void;
}

const isVitest =
  typeof process !== "undefined" &&
  (process.env?.NODE_ENV === "test" || process.env?.VITEST === "true");

export function getInitialSessionState() {
  if (isVitest) {
    return {
      isAuthenticated: true,
      isHydrating: false,
      mustChangePassword: false,
      accessToken: "mock-vitest-access-token",
      roles: ["PLATFORM_ADMIN", "SECOPS"] as readonly string[],
      activeHat: "PLATFORM_ADMIN",
      readOnlyObserver: false,
      email: null as string | null,
      displayName: null as string | null,
      userSettingsModalOpen: false,
      userSettingsModalInitialTab: null as UserSettingsModalTabKey | null,
    };
  }
  return {
    isAuthenticated: false,
    isHydrating: true,
    mustChangePassword: false,
    accessToken: null as string | null,
    roles: [] as readonly string[],
    activeHat: "",
    readOnlyObserver: false,
    email: null as string | null,
    displayName: null as string | null,
    userSettingsModalOpen: false,
    userSettingsModalInitialTab: null as UserSettingsModalTabKey | null,
  };
}

export const useAuthSessionStore = create<AuthSessionStoreState>((set) => ({
  ...getInitialSessionState(),
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
  clearMustChangePassword: () => set({ mustChangePassword: false }),
  loginWithSession: (res) => {
    const raw = res as Record<string, unknown>;
    const rolesList =
      Array.isArray(res.roles) && res.roles.length > 0
        ? res.roles
        : Array.isArray(raw.roles) && (raw.roles as string[]).length > 0
          ? (raw.roles as string[])
          : res.platform_role
            ? [res.platform_role]
            : ["CONTRIBUTOR"];
    set({
      isAuthenticated: true,
      isHydrating: false,
      accessToken: res.access_token ?? (raw.accessToken as string | undefined) ?? null,
      roles: rolesList,
      activeHat: rolesList[0] || "PLATFORM_ADMIN",
      email: res.email ?? (raw.email as string | undefined) ?? null,
      displayName: res.display_name ?? (raw.displayName as string | undefined) ?? null,
      mustChangePassword: Boolean(res.must_change_password ?? raw.mustChangePassword),
    });
  },
  logoutSession: async () => {
    const client = createOrciaApiClient({ baseUrl: "" });
    try {
      await client.logoutSession();
    } catch {
      // Best-effort
    }
    set({
      isAuthenticated: false,
      isHydrating: false,
      accessToken: null,
      roles: [],
      activeHat: "",
      email: null,
      displayName: null,
      mustChangePassword: false,
      userSettingsModalOpen: false,
      userSettingsModalInitialTab: null,
    });
  },
  hydrateSession: async () => {
    const client = createOrciaApiClient({ baseUrl: "" });
    try {
      const tokenRes = await client.refreshSession();
      if (tokenRes && tokenRes.access_token) {
        const authedClient = createOrciaApiClient({ baseUrl: "", accessToken: tokenRes.access_token });
        const me = await authedClient.getMe().catch(() => null);
        const roles =
          tokenRes.roles && tokenRes.roles.length > 0
            ? tokenRes.roles
            : me?.roles && me.roles.length > 0
              ? me.roles
              : [tokenRes.platform_role];
        set({
          isAuthenticated: true,
          isHydrating: false,
          accessToken: tokenRes.access_token,
          roles,
          activeHat: roles[0] || "PLATFORM_ADMIN",
          email: tokenRes.email || me?.email || null,
          displayName: tokenRes.display_name || me?.display_name || null,
          mustChangePassword: Boolean(tokenRes.must_change_password || me?.must_change_password),
        });
        return;
      }
    } catch {
      // Refresh failed
    }
    set({
      isAuthenticated: false,
      isHydrating: false,
      accessToken: null,
      roles: [],
      activeHat: "",
      email: null,
      displayName: null,
      mustChangePassword: false,
    });
  },
  resetAuthSession: () => set({ ...getInitialSessionState() }),
}));

export function resetAuthSessionStore(): void {
  useAuthSessionStore.getState().resetAuthSession();
}

export function simulateUnauthenticatedBrowser(): void {
  useAuthSessionStore.setState({
    isAuthenticated: false,
    isHydrating: false,
    mustChangePassword: false,
    accessToken: null,
    roles: [],
    activeHat: "",
    email: null,
    displayName: null,
    userSettingsModalOpen: false,
    userSettingsModalInitialTab: null,
  });
}
