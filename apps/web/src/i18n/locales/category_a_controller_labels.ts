import { CATEGORY_A_CONTROLLER_EN_LABELS } from "./category_a_controller_labels_en";
import { CATEGORY_A_CONTROLLER_FR_LABELS } from "./category_a_controller_labels_fr";

export interface AdaptiveThinkingStepTemplate {
  readonly stepCode: string;
  readonly label: string;
  readonly durationMs: number;
  readonly intermediateOutput: string;
}

export interface CategoryAControllersDictionary {
  readonly assistantThinking: {
    readonly code: readonly AdaptiveThinkingStepTemplate[];
    readonly explain: readonly AdaptiveThinkingStepTemplate[];
    readonly compare: readonly AdaptiveThinkingStepTemplate[];
    readonly fallback: readonly AdaptiveThinkingStepTemplate[];
  };
  readonly cockpit: {
    readonly defaultArbitrationJustification: string;
  };
  readonly finopsResources: {
    readonly dashboard: string;
    readonly budgetCeiling: string;
    readonly budgetOverride: string;
    readonly recommendation: string;
    readonly remoteQuota: string;
    readonly circuitReset: string;
    readonly autonomousReview: string;
  };
  readonly connectors: {
    readonly registeredSuccess: string;
    readonly deletedSuccess: string;
  };
  readonly packsRegistry: {
    readonly healthEmpty: string;
    readonly healthAllOk: string;
    readonly archiveExported: string;
    readonly workspaceOptionPrefix: string;
  };
  readonly processes: {
    readonly executionDefaultName: string;
    readonly defaultReturnRemarks: string;
    readonly writePreviewPrompt: string;
    readonly stepApprovedAdvance: string;
    readonly stepActivatedWord: string;
    readonly stepSkippedWord: string;
    readonly readyForFinalSignoff: string;
    readonly deliverableApprovedBanner: string;
    readonly deliverableDiffSavedBanner: string;
    readonly returnLoopMarkdown: string;
    readonly returnLoopBanner: string;
    readonly processResource: string;
    readonly processSaveResource: string;
    readonly delegatedAgentsUpdated: string;
    readonly subStepDraftUpdated: string;
    readonly executionModeSwitched: string;
    readonly externalIdeLabel: string;
    readonly nativeOrciaLabel: string;
    readonly draftSavedBanner: string;
    readonly publishedBanner: string;
    readonly whatIfDoneBanner: string;
    readonly packCreatedBanner: string;
    readonly assetPromotedBanner: string;
    readonly helpArticleAttachedBanner: string;
  };
  readonly workspaceSources: {
    readonly updated: string;
    readonly attached: string;
    readonly syncTriggered: string;
    readonly deleted: string;
    readonly gitNexusEnabled: string;
    readonly gitNexusDisabled: string;
    readonly referentRenewed: string;
    readonly reconciled: string;
    readonly coldStartBanner: string;
    readonly myAccountCta: string;
    readonly sourcesTitle: string;
    readonly newReferentPlaceholder: string;
    readonly confirmRenewalCta: string;
    readonly cancelCta: string;
  };
  readonly wizards: {
    readonly profileSelectorAriaLabel: string;
  };
}

export { CATEGORY_A_CONTROLLER_EN_LABELS, CATEGORY_A_CONTROLLER_FR_LABELS };

export const CATEGORY_A_CONTROLLER_BY_LOCALE: Record<
  "fr" | "en",
  CategoryAControllersDictionary
> = {
  fr: CATEGORY_A_CONTROLLER_FR_LABELS,
  en: CATEGORY_A_CONTROLLER_EN_LABELS,
};
