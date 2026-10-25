import type {
  HumanLedAnchorCardLabels,
  UiModuleKey,
  UiShellLabels,
  UiWorkspaceTopologyLabels,
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
  workspaceTopology: UiWorkspaceTopologyLabels;
  modulePages: Record<UiModuleKey, ModulePageCopy>;
}
