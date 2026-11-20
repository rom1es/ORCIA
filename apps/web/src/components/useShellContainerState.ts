import { useEffect, useState } from "react";
import {
  computeDefaultHelpColumnOpen,
  useResponsiveBreakpoint,
  type EightFixedMenuKey,
  type UiModuleKey,
} from "@orcia/ui";
import { ignoreBenignStorageError } from "../utils/benignBrowserError";

export const ORCIA_ACTIVE_SCOPE_STORAGE_KEY = "orcia.shell.active_scope_id.v1";

function readSavedActiveScopeId(): string | null {
  try {
    if (typeof window === "undefined" || !window.localStorage) return null;
    const raw = window.localStorage.getItem(ORCIA_ACTIVE_SCOPE_STORAGE_KEY);
    return raw && raw.trim().length > 0 ? raw.trim() : null;
  } catch (err: unknown) {
    ignoreBenignStorageError("shell.read_active_scope", err);
    return null;
  }
}

function writeSavedActiveScopeId(scopeId: string | null): void {
  try {
    if (typeof window === "undefined" || !window.localStorage) return;
    if (!scopeId) {
      window.localStorage.removeItem(ORCIA_ACTIVE_SCOPE_STORAGE_KEY);
    } else {
      window.localStorage.setItem(ORCIA_ACTIVE_SCOPE_STORAGE_KEY, scopeId);
    }
  } catch (err: unknown) {
    ignoreBenignStorageError("shell.write_active_scope", err);
  }
}

export function useShellContainerState(
  runsLength: number,
  pathname?: string,
  options?: {
    readonly canObserveGlobalScope?: boolean;
    readonly defaultScopedId?: string;
    readonly isInitialLoading?: boolean;
    readonly validScopeIds?: readonly string[];
  },
) {
  const canObserveGlobalScope = options?.canObserveGlobalScope ?? true;
  const defaultScopedId = options?.defaultScopedId;
  const isInitialLoading = options?.isInitialLoading ?? false;
  const validScopeIds = options?.validScopeIds;
  const [activeScopeId, setActiveScopeIdState] = useState(() => {
    const saved = readSavedActiveScopeId();
    if (saved) return saved;
    return !canObserveGlobalScope && defaultScopedId ? defaultScopedId : "scope-global";
  });
  const setActiveScopeId = (nextScopeId: string) => {
    setActiveScopeIdState(nextScopeId);
    writeSavedActiveScopeId(nextScopeId);
  };
  const [selectedModuleOverride, setSelectedModuleOverride] = useState<UiModuleKey | null>(null);
  const [selectedMenuKeyOverride, setSelectedMenuKeyOverride] =
    useState<EightFixedMenuKey | null>(null);
  const { viewportWidthPx: viewportWidth } = useResponsiveBreakpoint();
  const [searchModalOpen, setSearchModalOpen] = useState<boolean>(false);
  const [helpColumnOpen, setHelpColumnOpen] = useState<boolean>(() =>
    computeDefaultHelpColumnOpen(viewportWidth, runsLength),
  );
  const [activeHelpSectionId, setActiveHelpSectionId] = useState<string | null>(null);
  const [adminModalDismissed, setAdminModalDismissed] = useState<boolean>(false);

  useEffect(() => {
    setSelectedModuleOverride(null);
    setSelectedMenuKeyOverride(null);
  }, [pathname]);

  useEffect(() => {
    if (isInitialLoading || !validScopeIds) return;
    if (activeScopeId !== "scope-global" && !validScopeIds.includes(activeScopeId)) {
      const fallback =
        !canObserveGlobalScope && defaultScopedId ? defaultScopedId : "scope-global";
      setActiveScopeIdState(fallback);
      writeSavedActiveScopeId(fallback === "scope-global" ? null : fallback);
    }
  }, [isInitialLoading, validScopeIds, activeScopeId, canObserveGlobalScope, defaultScopedId]);

  useEffect(() => {
    if (
      !canObserveGlobalScope &&
      activeScopeId === "scope-global" &&
      defaultScopedId &&
      readSavedActiveScopeId() === null
    ) {
      setActiveScopeIdState(defaultScopedId);
    }
  }, [canObserveGlobalScope, activeScopeId, defaultScopedId]);

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        setSearchModalOpen((prev) => !prev);
      }
    };
    window.addEventListener("keydown", handleKeyDown);
    return () => window.removeEventListener("keydown", handleKeyDown);
  }, []);

  return {
    viewportWidth,
    activeScopeId,
    setActiveScopeId,
    selectedModuleOverride,
    setSelectedModuleOverride,
    selectedMenuKeyOverride,
    setSelectedMenuKeyOverride,
    searchModalOpen,
    setSearchModalOpen,
    helpColumnOpen,
    setHelpColumnOpen,
    activeHelpSectionId,
    setActiveHelpSectionId,
    adminModalDismissed,
    setAdminModalDismissed,
  };
}

export function useShellAuthRedirects(params: {
  readonly isHydrating: boolean;
  readonly isInitialLoading: boolean;
  readonly isAuthenticated: boolean;
  readonly isAdminModalOpen: boolean;
  readonly isShowcaseStandalone: boolean;
  readonly pathname?: string;
  readonly hydrateSession: () => Promise<void>;
  readonly dispatchNavigation: (href: string) => void;
}) {
  const {
    isHydrating,
    isInitialLoading,
    isAuthenticated,
    isAdminModalOpen,
    isShowcaseStandalone,
    pathname,
    hydrateSession,
    dispatchNavigation,
  } = params;

  useEffect(() => {
    if (isHydrating) {
      void hydrateSession();
    }
  }, [isHydrating, hydrateSession]);

  useEffect(() => {
    if (
      !isHydrating &&
      !(isInitialLoading && !isAuthenticated) &&
      !isAuthenticated &&
      !isAdminModalOpen &&
      !isShowcaseStandalone &&
      pathname !== "/login"
    ) {
      dispatchNavigation("/login");
    }
  }, [
    isHydrating,
    isInitialLoading,
    isAuthenticated,
    isAdminModalOpen,
    isShowcaseStandalone,
    pathname,
  ]);

  useEffect(() => {
    if (isAuthenticated && pathname === "/login") {
      dispatchNavigation("/");
    }
  }, [isAuthenticated, pathname]);
}
