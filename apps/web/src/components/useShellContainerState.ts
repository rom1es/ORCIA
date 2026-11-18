import { useEffect, useState } from "react";
import {
  computeDefaultHelpColumnOpen,
  type EightFixedMenuKey,
  type UiModuleKey,
} from "@orcia/ui";

export function useShellContainerState(
  runsLength: number,
  pathname?: string,
  options?: {
    readonly canObserveGlobalScope?: boolean;
    readonly defaultScopedId?: string;
  },
) {
  const canObserveGlobalScope = options?.canObserveGlobalScope ?? true;
  const defaultScopedId = options?.defaultScopedId;
  const [activeScopeId, setActiveScopeId] = useState(() =>
    !canObserveGlobalScope && defaultScopedId ? defaultScopedId : "scope-global",
  );
  const [selectedModuleOverride, setSelectedModuleOverride] = useState<UiModuleKey | null>(null);
  const [selectedMenuKeyOverride, setSelectedMenuKeyOverride] =
    useState<EightFixedMenuKey | null>(null);
  const [viewportWidth, setViewportWidth] = useState<number>(() =>
    typeof window !== "undefined" ? window.innerWidth : 1440,
  );
  const [searchModalOpen, setSearchModalOpen] = useState<boolean>(false);
  const [helpColumnOpen, setHelpColumnOpen] = useState<boolean>(() =>
    computeDefaultHelpColumnOpen(
      typeof window !== "undefined" ? window.innerWidth : 1440,
      runsLength,
    ),
  );
  const [activeHelpSectionId, setActiveHelpSectionId] = useState<string | null>(null);
  const [adminModalDismissed, setAdminModalDismissed] = useState<boolean>(false);

  useEffect(() => {
    const handleResize = () => {
      setViewportWidth(window.innerWidth);
    };
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

  useEffect(() => {
    setSelectedModuleOverride(null);
    setSelectedMenuKeyOverride(null);
  }, [pathname]);

  useEffect(() => {
    if (!canObserveGlobalScope && activeScopeId === "scope-global" && defaultScopedId) {
      setActiveScopeId(defaultScopedId);
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
