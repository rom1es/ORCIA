import { useEffect, useState } from "react";
import {
  computeDefaultHelpColumnOpen,
  type EightFixedMenuKey,
  type UiModuleKey,
} from "@orcia/ui";

export function useShellContainerState(runsLength: number, pathname?: string) {
  const [activeScopeId, setActiveScopeId] = useState("scope-global");
  const [selectedModuleOverride, setSelectedModuleOverride] = useState<UiModuleKey | null>(null);
  const [selectedMenuKeyOverride, setSelectedMenuKeyOverride] =
    useState<EightFixedMenuKey | null>(null);
  const [searchModalOpen, setSearchModalOpen] = useState<boolean>(false);
  const [helpColumnOpen, setHelpColumnOpen] = useState<boolean>(() =>
    computeDefaultHelpColumnOpen(1440, runsLength),
  );
  const [activeHelpSectionId, setActiveHelpSectionId] = useState<string | null>(null);
  const [adminModalDismissed, setAdminModalDismissed] = useState<boolean>(false);

  useEffect(() => {
    setSelectedModuleOverride(null);
    setSelectedMenuKeyOverride(null);
  }, [pathname]);

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
