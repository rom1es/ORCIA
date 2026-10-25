import type {
  HumanLedAnchorCardLabels,
  UiModuleKey,
  UiShellLabels,
} from "@orcia/ui";

export type SupportedWebLocale = "fr" | "en";

export interface ModulePageCopy {
  subtitle: string;
  description: string;
  uriBadgeExample: string;
}

export interface TranslationDictionary {
  locale: SupportedWebLocale;
  shell: UiShellLabels;
  humanAnchor: HumanLedAnchorCardLabels & {
    defaultSectionTitle: string;
    defaultAuthorName: string;
    defaultValue: string;
  };
  modulePages: Record<UiModuleKey, ModulePageCopy>;
}
