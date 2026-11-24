import {
  createOrciaApiClient,
  registerDefaultAccessTokenProvider,
  registerDefaultAccessTokenRefreshedHandler,
} from "@orcia/api-client";
import { create } from "zustand";
import {
  executeSessionHydrationWithTimeout,
  resolveWebApiBaseUrl,
} from "./authSessionHydration";
import {
  ALL_SETTINGS_TABS,
  canAccessConfigurationSettings,
  canAccessMyOrganization,
  canMutateMyOrganization,
  canObserveGlobalAuditScope,
  formatCountNoun,
  FULL_ADMIN_PERMISSION_VERBS,
  isPlatformAdministratorSession,
  isSecopsSession,
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
  canAccessConfigurationSettings,
  canAccessMyOrganization,
  canMutateMyOrganization,
  canObserveGlobalAuditScope,
  formatCountNoun,
  FULL_ADMIN_PERMISSION_VERBS,
  isPlatformAdministratorSession,
  isSecopsSession,
  READ_ONLY_PERMISSION_VERBS,
  resolveSessionHatLabel,
  resolveSettingsAccess,
  resolveWebApiBaseUrl,
  SCOPED_LEAD_SETTINGS_TABS,
  SETTINGS_TAB_ICON_NAMES,
  type AuthSessionSnapshot,
  type OrciaSystemRole,
  type ResolvedSettingsAccess,
  type SettingsTabKey,
};

export type UserSettingsModalTabKey =
  | "GENERAL"
  | "PERSONALIZATION"
  | "ACCOUNT_SECURITY"
  | "PASSTHROUGH_SOURCES"
  | "IDE_MCP_KEYS";

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
  /** Primary authenticated role key (derived read-only from `roles[0]`, never mutable for RBAC). */
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
      const derivedPrimaryRole = nextRoles[0] || state.activeHat || "CONTRIBUTOR";
      return {
        ...state,
        ...patch,
        roles: nextRoles,
        activeHat: derivedPrimaryRole,
      };
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
    } catch (err: unknown) {
      console.warn("[orcia:auth.logoutSession]", err instanceof Error ? err.message : String(err));
    }
    set({
      ...UNAUTHENTICATED_SESSION_STATE,
      isHydrating: false,
    });
  },
  hydrateSession: async (options?: { force?: boolean }) => {
    if (activeHydrationPromise) return activeHydrationPromise;
    if (!options?.force && !get().isHydrating) return;
    if (!get().isAuthenticated) set({ isHydrating: true });

    const runHydration = async () => {
      try {
        const hydrated = await executeSessionHydrationWithTimeout(5000);
        if (hydrated) {
          set({
            isAuthenticated: true,
            isHydrating: false,
            accessToken: hydrated.accessToken,
            roles: hydrated.roles,
            activeHat: hydrated.activeHat,
            email: hydrated.email,
            displayName: hydrated.displayName,
            mustChangePassword: hydrated.mustChangePassword,
          });
          return;
        }
        set({ ...UNAUTHENTICATED_SESSION_STATE, isHydrating: false });
      } catch (err: unknown) {
        console.warn("[orcia:auth.hydrateSession]", err instanceof Error ? err.message : String(err));
        set({ ...UNAUTHENTICATED_SESSION_STATE, isHydrating: false });
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
registerDefaultAccessTokenRefreshedHandler((token) => {
  const current = useAuthSessionStore.getState();
  current.setAuthSession({
    accessToken: token,
    isAuthenticated: true,
    isHydrating: false,
    email: current.email,
    displayName: current.displayName,
    roles: current.roles,
  });
  if (!current.email || current.roles.length === 0) {
    void createOrciaApiClient({
      baseUrl: resolveWebApiBaseUrl(),
      accessToken: token,
    })
      .getMe()
      .then((me) => {
        if (!me) return;
        const latest = useAuthSessionStore.getState();
        const nextRoles = me.roles && me.roles.length > 0 ? me.roles : latest.roles;
        latest.setAuthSession({
          email: me.email || latest.email,
          displayName: me.display_name || latest.displayName,
          roles: nextRoles,
          mustChangePassword: Boolean(me.must_change_password),
        });
      })
      .catch((err: unknown) => {
        console.warn("[authSessionStore] Failed to enrich refreshed session via /me:", err);
      });
  }
});

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
