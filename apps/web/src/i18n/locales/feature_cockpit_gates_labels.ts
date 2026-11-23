import type { ConfiguredWorkflowItem } from "../../components/platformSetupStore";

export interface DocProcessStepCopy {
  readonly stepNumber: 1 | 2 | 3 | 4;
  readonly title: string;
  readonly agentHandle: string;
  readonly summary: string;
}

export interface FeatureCockpitGatesDictionary {
  readonly cockpit: {
    readonly workflowPreviewNodes: {
      readonly intentRouter: string;
      readonly queryPlanner: string;
      readonly parallelFanOut: string;
      readonly criticalTriage: string;
      readonly profileSynthesizer: string;
    };
    readonly runsSection: {
      readonly emptyTitle: string;
      readonly emptyDescription: string;
      readonly createWorkspaceCta: string;
      readonly assistantOptionLabel: string;
      readonly runTitlePlaceholder: string;
      readonly startProcessBtn: string;
    };
    readonly stepStatus: {
      readonly pending: string;
      readonly running: string;
      readonly completed: string;
      readonly staleNeedsReview: string;
      readonly waitingHumanAnchor: string;
      readonly waitingHumanArbitration: string;
      readonly pausedHumanGate: string;
    };
    readonly stepKeyLabels: Readonly<Record<string, string>>;
    readonly upstreamChallenge: {
      readonly defaultSummary: string;
      readonly defaultPreviewReason: string;
      readonly staleReplayTemplate: string;
      readonly openModalBtn: string;
      readonly defaultStaleBanner: string;
    };
    readonly onboardingChecklist: {
      readonly title: string;
      readonly subtitle: string;
      readonly guidedAssistantsBtn: string;
      readonly statusConfigured: string;
      readonly statusToConfigure: string;
    };
  };
  readonly gates: {
    readonly panel: {
      readonly activeScopeLabel: string;
      readonly emptyTitle: string;
      readonly emptyDescription: string;
      readonly openProcessesBtn: string;
    };
    readonly headerCard: {
      readonly title: string;
      readonly gatePrefix: string;
      readonly statusPendingReview: string;
      readonly statusPassed: string;
      readonly jiraStaged: string;
      readonly jiraExecuted: string;
      readonly prepareReviewBtn: string;
    };
    readonly humanReview: {
      readonly defaultExecutiveSummary: string;
      readonly step1AlignmentTemplate: string;
      readonly alignmentAligned: string;
      readonly alignmentConflict: string;
      readonly totalVolumeTemplate: string;
      readonly loadErrorFallback: string;
      readonly loadErrorBannerTemplate: string;
      readonly openReviewSuccess: string;
      readonly openReviewErrorFallback: string;
      readonly inspectHypothesesSuccess: string;
      readonly inspectHypothesesErrorFallback: string;
      readonly chunkStatusLabels: Readonly<Record<string, string>>;
      readonly chunkUpdatedTemplate: string;
      readonly chunkErrorFallback: string;
      readonly finalizeSuccess: string;
      readonly finalizeErrorFallback: string;
      readonly defaultChallengeReason: string;
      readonly seedPhrase: string;
      readonly seedDecisions: readonly string[];
      readonly seedHypotheses: readonly string[];
      readonly seedSec1Title: string;
      readonly seedSec1Prefix: string;
      readonly seedSec2Title: string;
      readonly seedSec2Prefix: string;
      readonly seedJiraSummary: string;
    };
    readonly challengeModal: {
      readonly defaultSummary: string;
      readonly challengeSubmittedBanner: string;
      readonly replayBannerTemplate: string;
      readonly errorContextLabel: string;
    };
    readonly docProcess: {
      readonly cardTitle: string;
      readonly cardDescription: string;
      readonly badgeLabel: string;
      readonly runBtn: string;
      readonly loadInBuilderBtn: string;
      readonly stepsSummaryTitle: string;
      readonly stepCompletedBadge: string;
      readonly publishSuccessBanner: string;
      readonly localValidationFallback: string;
      readonly publishWithDetailTemplate: string;
      readonly loadedInBuilderBanner: string;
      readonly steps: readonly DocProcessStepCopy[];
      readonly workflowTitle: string;
      readonly workflowPrePrompt: string;
      readonly workflowLayers: ConfiguredWorkflowItem["layers"];
      readonly generatedMarkdown: string;
    };
  };
}
