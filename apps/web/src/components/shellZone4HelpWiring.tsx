import type { EightFixedMenuKey, UiModuleKey } from "@orcia/ui";
import React from "react";
import type { TranslationDictionary } from "../i18n/types";
import { writeAssistantPrefillPrompt } from "./agentsAndSkillsBridgeStore";
import { buildContextualHelpArticle } from "./contextualHelpCatalog";
import { ShellContextualHelpColumn } from "./ShellContextualHelpColumn";

function resolveHelpTitleFallback(params: {
  readonly pathname: string | undefined;
  readonly locale: "fr" | "en";
  readonly activeMenuKey: EightFixedMenuKey | null;
  readonly safeModuleKey: UiModuleKey;
  readonly dictionary: TranslationDictionary;
}): string {
  const { pathname, locale, activeMenuKey, safeModuleKey, dictionary } = params;
  const isFr = locale === "fr";
  if (pathname?.startsWith("/inbox")) {
    return isFr ? "Boîte de Réception" : "Inbox";
  }
  if (pathname?.startsWith("/showcase")) {
    return isFr ? "Présentation ORCIA" : "ORCIA Showcase";
  }
  if (pathname?.startsWith("/organization")) {
    return (
      dictionary.fourZoneShell.organizationMenuLabel ??
      (isFr ? "Mon Organisation" : "My Organization")
    );
  }
  return activeMenuKey
    ? dictionary.fourZoneShell.menuEntries[activeMenuKey]
    : dictionary.modulePages[safeModuleKey].subtitle;
}

export function renderShellZone4HelpColumn(params: {
  readonly isHelpCenterRoute: boolean;
  readonly pathname: string | undefined;
  readonly locale: "fr" | "en";
  readonly activeMenuKey: EightFixedMenuKey | null;
  readonly safeModuleKey: UiModuleKey;
  readonly activeHelpSectionId: string | null;
  readonly assistantDisabled: boolean;
  readonly dictionary: TranslationDictionary;
  readonly hasOnNavigateProp: boolean;
  readonly onSelectModuleAndNavigate: (
    menuKey: EightFixedMenuKey | null,
    moduleKey: UiModuleKey,
    route: string,
  ) => void;
  readonly onDispatchNavigation: (href: string) => void;
}): React.ReactNode {
  const {
    isHelpCenterRoute,
    pathname,
    locale,
    activeMenuKey,
    safeModuleKey,
    activeHelpSectionId,
    assistantDisabled,
    dictionary,
    hasOnNavigateProp,
    onSelectModuleAndNavigate,
    onDispatchNavigation,
  } = params;

  if (isHelpCenterRoute) {
    return undefined;
  }

  const helpTitleFallback = resolveHelpTitleFallback({
    pathname,
    locale,
    activeMenuKey,
    safeModuleKey,
    dictionary,
  });

  const contextualHelpArticle = buildContextualHelpArticle({
    activeMenuKey: activeMenuKey ?? "cockpit",
    pathname,
    locale,
    title: helpTitleFallback,
    defaultSummary: dictionary.modulePages[safeModuleKey].description,
  });

  return (
    <ShellContextualHelpColumn
      pathname={pathname}
      locale={locale}
      contextualHelpArticle={contextualHelpArticle}
      activeHelpSectionId={activeHelpSectionId}
      labels={dictionary.contextualHelpHybrid}
      autonomousBadgeLabels={dictionary.autonomousSupervision.badge}
      onAskAssistant={(_route, prefillPrompt) => {
        if (assistantDisabled) return;
        if (prefillPrompt?.trim()) {
          writeAssistantPrefillPrompt(prefillPrompt.trim());
        }
        if (hasOnNavigateProp) {
          onSelectModuleAndNavigate("assistant", "inbox", "/assistant");
        } else {
          onDispatchNavigation("/assistant");
        }
      }}
    />
  );
}
