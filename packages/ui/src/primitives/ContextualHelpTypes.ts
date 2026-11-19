import type { AutonomousExecutionBadgeLabels } from "./AutonomousExecutionBadge";

export type UiHelpArticleLayer = "BASE" | "PACK" | "WORKSPACE" | "USER";

export interface UiContextualHelpSectionItem {
  readonly sectionId: string;
  readonly title: string;
  readonly body: string;
  readonly category?: "whatFor" | "steps" | "terms" | "faq";
}

export interface UiContextualHelpArticleView {
  readonly resourceId: string;
  readonly uri: string;
  readonly title: string;
  readonly version: string;
  readonly lang: "fr" | "en";
  readonly layer: UiHelpArticleLayer;
  readonly packName: string | null;
  readonly boundRoutes: readonly string[];
  readonly summaryWhatFor: string;
  readonly stepByStepItems: readonly string[];
  readonly keyTermsItems: readonly string[];
  readonly faqItems: readonly string[];
  readonly realExampleText?: string | null;
  readonly commonPitfallsItems?: readonly string[];
  readonly sections?: readonly UiContextualHelpSectionItem[];
  readonly casKey: string;
  readonly sha256: string;
  readonly previousVersion?: string | null;
  readonly isAutonomousGenerated?: boolean;
  readonly autonomousRunId?: string | null;
  readonly contractLabel?: string | null;
  readonly triggerLabel?: string | null;
}

export interface ContextualHelpColumnAndCenterLabels {
  readonly columnHeaderTitle: string;
  readonly centerHeaderTitle: string;
  readonly whatForSectionTitle: string;
  readonly stepByStepAccordionTitle: string;
  readonly keyTermsAccordionTitle: string;
  readonly faqAccordionTitle: string;
  readonly askAssistantOnScreenCta: string;
  readonly rollbackButtonLabel: string;
  readonly rollbackCompletedPrefix: string;
  readonly mergedLayersPrefix: string;
  readonly realExampleTitle?: string;
  readonly commonPitfallsTitle?: string;
  readonly technicalDetailsTitle?: string;
  readonly stepsBlockPrefix?: string;
  readonly stepsBlockSuffix?: string;
  readonly targetedHelpBadgeLabel?: string;
  readonly askAssistantPrefillTemplate?: string;
}

export interface ContextualHelpColumnAndCenterProps {
  readonly mode?: "COLUMN_340PX" | "HELP_MENU_CENTER";
  readonly route: string;
  readonly pack: string;
  readonly redisCacheKey: string;
  readonly mergedLayers: readonly UiHelpArticleLayer[];
  readonly article: UiContextualHelpArticleView;
  readonly targetedSections?: readonly UiContextualHelpSectionItem[];
  readonly activeSectionId?: string | null;
  readonly rollbackAvailable?: boolean;
  readonly isAdmin?: boolean;
  readonly showTechnicalMetadata?: boolean;
  readonly askAssistantPrefill?: string;
  readonly labels: ContextualHelpColumnAndCenterLabels;
  readonly autonomousBadgeLabels?: AutonomousExecutionBadgeLabels;
  readonly onAskAssistantOnScreen?: (route: string, prefillPrompt: string) => void;
  readonly onRollbackVersion?: (resourceId: string) => void;
  readonly onInvalidateAndRestoreAutonomousHelp?: (runId: string, resourceId: string) => void;
}
