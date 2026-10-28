import React, { createContext, useContext } from "react";

export interface OrciaNavigationAdapter {
  pathname: string;
  navigateTo: (href: string) => void;
}

const defaultNavigateTo = (href: string) => {
  if (typeof window !== "undefined") {
    window.history.pushState({}, "", href);
    window.dispatchEvent(new PopStateEvent("popstate"));
  }
};

const NavigationAdapterContext = createContext<OrciaNavigationAdapter | null>(null);

export function OrciaNavigationProvider({
  adapter,
  children,
}: {
  adapter: OrciaNavigationAdapter;
  children: React.ReactNode;
}) {
  return (
    <NavigationAdapterContext.Provider value={adapter}>
      {children}
    </NavigationAdapterContext.Provider>
  );
}

export function useOrciaNavigation(): OrciaNavigationAdapter {
  const ctx = useContext(NavigationAdapterContext);
  if (ctx) {
    return ctx;
  }
  const pathname = typeof window !== "undefined" ? window.location.pathname || "/cockpit" : "/cockpit";
  return {
    pathname,
    navigateTo: defaultNavigateTo,
  };
}
