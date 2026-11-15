import { createOrciaApiClient, registerDefaultAccessTokenProvider } from "@orcia/api-client";
import { create } from "zustand";
import {
  ALL_SETTINGS_TABS,
  formatCountNoun,
  FULL_ADMIN_PERMISSION_VERBS,
  isPlatformAdministratorSession,
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
  isPlatformAdministratorSession,
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

export function resolveWebApiBaseUrl(): string {
  const meta = import.meta as unknown as { env?: Record<string, string | undefined> };
  const envUrl = meta?.env?.VITE_ORCIA_API_BASE_URL ?? meta?.env?.VITE_ORCIA_API_URL;
  if (envUrl && envUrl.trim().length > 0) {
    // Domain client paths already begin with `/api/v1/...`, so strip any trailing `/api` or slashes.
    const trimmed = envUrl.trim().replace(/\/+$/, "");
    if (trimmed === "/api" || trimmed.endsWith("/api")) {
      return trimmed.slice(0, -4);
    }
    return trimmed;
  }
  return "";
}

export const UNAUTHENTICATED_SESSION_STATE = {
  isAuthenticated: false,
  isHydrating: false,
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
  readonly hydrateSession: (options?: { force?: boolean }) => Promise<void>;
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
    ...UNAUTHENTICATED_SESSION_STATE,
    isHydrating: true,
  };
}

let activeHydrationPromise: Promise<void> | null = null;

export const useAuthSessionStore = create<AuthSessionStoreState>((set, get) => ({
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
  setActiveHat: (hat) =>
    set((state) => {
      if (hat === "PLATFORM_ADMIN" && !state.roles.includes("PLATFORM_ADMIN")) {
        return state;
      }
      return { activeHat: hat };
    }),
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
      activeHat: rolesList[0] || "CONTRIBUTOR",
      email: res.email ?? (raw.email as string | undefined) ?? null,
      displayName: res.display_name ?? (raw.displayName as string | undefined) ?? null,
      mustChangePassword: Boolean(res.must_change_password ?? raw.mustChangePassword),
    });
  },
  logoutSession: async () => {
    activeHydrationPromise = null;
    const client = createOrciaApiClient({ baseUrl: resolveWebApiBaseUrl() });
    try {
      await client.logoutSession();
    } catch {
      // Best-effort
    }
    set({
      ...UNAUTHENTICATED_SESSION_STATE,
      isHydrating: false,
    });
  },
  hydrateSession: async (options?: { force?: boolean }) => {
    if (activeHydrationPromise) {
      return activeHydrationPromise;
    }
    if (!options?.force && !get().isHydrating) {
      return;
    }
    if (!get().isAuthenticated) {
      set({ isHydrating: true });
    }

    const runHydration = async () => {
      let timeoutId: ReturnType<typeof setTimeout> | undefined;
      const timeoutPromise = new Promise<never>((_, reject) => {
        timeoutId = setTimeout(() => {
          reject(new Error("Hydration timed out after 5000ms"));
        }, 5000);
      });

      try {
        const hydrationWork = (async () => {
          const client = createOrciaApiClient({ baseUrl: resolveWebApiBaseUrl() });
          const bootstrap = await client.getSessionBootstrap();
          const tokenRes = bootstrap?.authenticated ? bootstrap.session : null;
          if (tokenRes && tokenRes.access_token) {
            const authedClient = createOrciaApiClient({
              baseUrl: resolveWebApiBaseUrl(),
              accessToken: tokenRes.access_token,
            });
            const me = await authedClient.getMe().catch(() => null);
            const roles =
              tokenRes.roles && tokenRes.roles.length > 0
                ? tokenRes.roles
                : me?.roles && me.roles.length > 0
                  ? me.roles
                  : [tokenRes.platform_role];
            const currentHat = get().activeHat;
            const nextHat =
              currentHat && roles.includes(currentHat)
                ? currentHat
                : roles[0] || "CONTRIBUTOR";
            set({
              isAuthenticated: true,
              isHydrating: false,
              accessToken: tokenRes.access_token,
              roles,
              activeHat: nextHat,
              email: tokenRes.email || me?.email || null,
              displayName: tokenRes.display_name || me?.display_name || null,
              mustChangePassword: Boolean(tokenRes.must_change_password || me?.must_change_password),
            });
            return;
          }
          set({
            ...UNAUTHENTICATED_SESSION_STATE,
            isHydrating: false,
          });
        })();

        await Promise.race([hydrationWork, timeoutPromise]);
      } catch {
        set({
          ...UNAUTHENTICATED_SESSION_STATE,
          isHydrating: false,
        });
      } finally {
        if (timeoutId !== undefined) {
          clearTimeout(timeoutId);
        }
      }
    };

    activeHydrationPromise = runHydration().finally(() => {
      activeHydrationPromise = null;
    });
    return activeHydrationPromise;
  },
  resetAuthSession: () => {
    activeHydrationPromise = null;
    set({ ...getInitialSessionState() });
  },
}));

registerDefaultAccessTokenProvider(() => useAuthSessionStore.getState().accessToken);

export function resetAuthSessionStore(): void {
  activeHydrationPromise = null;
  useAuthSessionStore.getState().resetAuthSession();
}

export const resetAuthSessionForTests = resetAuthSessionStore;

export function simulateUnauthenticatedBrowser(): void {
  activeHydrationPromise = null;
  useAuthSessionStore.setState({
    ...UNAUTHENTICATED_SESSION_STATE,
    isHydrating: false,
  });
}
