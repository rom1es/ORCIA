import type { RgaaModalDialogLabels } from "../components/RgaaModalDialog.js";

export interface UpstreamChallengeWhatIfPreview {
  readonly runId: string;
  readonly challengerStepKey: string;
  readonly targetUpstreamStepKey: string;
  readonly challengedSectionKey: string;
  readonly targetProfileArchetype: string;
  readonly translatedSummary: string;
  readonly invalidatedDownstreamStepKeys: readonly string[];
  readonly invalidatedArtifactSections: readonly string[];
  readonly invalidatedOntologyAxiomKeys: readonly string[];
  readonly preservedUpstreamStepKeys: readonly string[];
  readonly upstreamTokensSaved: number;
}

export interface UpstreamChallengeModalLabels {
  readonly modalTitle: string;
  readonly modalSubtitle: string;
  readonly targetStepLabel: string;
  readonly sectionKeyLabel: string;
  readonly reasonLabel: string;
  readonly reasonPlaceholder: string;
  readonly whatIfTitle: string;
  readonly invalidatedStepsLabel: string;
  readonly invalidatedSectionsLabel: string;
  readonly invalidatedAxiomsLabel: string;
  readonly preservedStepsLabel: string;
  readonly translatedSummaryLabel: string;
  readonly submitChallengeCta: string;
  readonly replayStepCta: string;
  readonly closeCta: string;
  readonly challengeSubmittedFeedback: string;
  readonly replayTriggeredFeedback: string;
  readonly stepLabels?: Readonly<Record<string, string>>;
  readonly sectionLabels?: Readonly<Record<string, string>>;
  readonly axiomLabels?: Readonly<Record<string, string>>;
  readonly profileLabels?: Readonly<Record<string, string>>;
  readonly rootWorkflowLabel?: string;
}

export interface UpstreamChallengeRewindModalProps {
  readonly isOpen: boolean;
  readonly preview: UpstreamChallengeWhatIfPreview;
  readonly labels: UpstreamChallengeModalLabels;
  readonly subWorkflowStepKey?: string;
  readonly inline?: boolean;
  readonly rgaaLabels?: Partial<RgaaModalDialogLabels>;
  readonly onReasonChange?: (reason: string) => void;
  readonly onSubmitChallenge?: (payload: {
    targetUpstreamStepKey: string;
    challengedSectionKey: string;
    challengeReason: string;
  }) => void;
  readonly onTriggerReplay?: (payload: {
    stepKey: string;
    subWorkflowStepKey?: string;
  }) => void;
  readonly onClose?: () => void;
}
