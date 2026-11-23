import type { UiContextualHelpSectionItem } from "@orcia/ui";

export interface RouteFallbackNarrative {
  readonly summaryWhatFor: string;
  readonly steps: readonly string[];
  readonly realExampleText: string;
  readonly commonPitfallsItems: readonly string[];
}

export interface ContextualHelpDictionarySection {
  readonly configurationSections: readonly UiContextualHelpSectionItem[];
  readonly workflowSections: readonly UiContextualHelpSectionItem[];
  readonly sectionsByRoute: Readonly<Record<string, readonly UiContextualHelpSectionItem[]>>;
  readonly settingsArticle: {
    readonly summaryWhatFor: string;
    readonly stepByStepItems: readonly string[];
    readonly realExampleText: string;
    readonly commonPitfallsItems: readonly string[];
  };
  readonly routeFallbacks: Readonly<Record<string, RouteFallbackNarrative>>;
  readonly defaultSteps: readonly string[];
  readonly routeTitleFallbacks: {
    readonly inbox: string;
    readonly showcase: string;
    readonly organization: string;
  };
}
