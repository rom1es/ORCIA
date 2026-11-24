import { createContext, useContext } from "react";
import type { EightFixedMenuKey, UiModuleKey } from "@orcia/ui";

export interface ShellNavigationContextValue {
  readonly activeModuleKey: UiModuleKey;
  readonly activeMenuKey: EightFixedMenuKey | null;
  readonly activeScopeId: string;
  readonly setActiveScopeId?: (scopeId: string) => void;
  readonly helpColumnOpen: boolean;
  readonly activeHelpSectionId: string | null;
  readonly disabledMenuKeys?: Partial<Record<EightFixedMenuKey, string>>;
  readonly navigateToRoute: (href: string) => void;
  readonly openHelpSection: (sectionId: string) => void;
}

export const ShellNavigationContext = createContext<ShellNavigationContextValue>({
  activeModuleKey: "cockpit",
  activeMenuKey: "cockpit",
  activeScopeId: "scope-global",
  setActiveScopeId: () => undefined,
  helpColumnOpen: true,
  activeHelpSectionId: null,
  navigateToRoute: () => undefined,
  openHelpSection: () => undefined,
});

export function useShellNavigation(): ShellNavigationContextValue {
  return useContext(ShellNavigationContext);
}
