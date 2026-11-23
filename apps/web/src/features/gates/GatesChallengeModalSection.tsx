import { createOrciaApiClient } from "@orcia/api-client";
import {
  UpstreamChallengeRewindModal,
  type UpstreamChallengeWhatIfPreview,
} from "@orcia/ui";
import React, { useMemo, useState } from "react";
import { formatI18nTemplate, resolveDictionaryForFlag, resolveLocaleForFlag, useI18n } from "../../i18n";
import { formatRfc9457ErrorToBanner } from "../../lib/formatRfc9457ErrorToBanner";

const CHALLENGER_STEP_KEY = "delegate-remediation-subworkflow";
const TARGET_UPSTREAM_STEP_KEY = "frame-architecture-intent";

export interface GatesChallengeModalSectionProps {
  readonly isOpen: boolean;
  readonly runId: string;
  readonly sectionKey: string;
  readonly isFr: boolean;
  readonly onClose: () => void;
  readonly onFeedback: (message: string | null) => void;
}

export function GatesChallengeModalSection({
  isOpen,
  runId,
  sectionKey,
  isFr,
  onClose,
  onFeedback,
}: GatesChallengeModalSectionProps) {
  const { dictionary } = useI18n();
  const resolvedLocale = resolveLocaleForFlag(isFr);
  const modalCopy = resolveDictionaryForFlag(isFr, resolvedLocale).featureCockpitGates.gates.challengeModal;
  const apiClient = useMemo(() => createOrciaApiClient({ baseUrl: "" }), []);
  const [preview, setPreview] = useState<UpstreamChallengeWhatIfPreview>({
    runId,
    challengerStepKey: CHALLENGER_STEP_KEY,
    targetUpstreamStepKey: TARGET_UPSTREAM_STEP_KEY,
    challengedSectionKey: sectionKey,
    targetProfileArchetype: "PM_BUSINESS",
    translatedSummary: modalCopy.defaultSummary,
    invalidatedDownstreamStepKeys: [TARGET_UPSTREAM_STEP_KEY, CHALLENGER_STEP_KEY],
    invalidatedArtifactSections: [`${TARGET_UPSTREAM_STEP_KEY}:${sectionKey}`],
    invalidatedOntologyAxiomKeys: [],
    preservedUpstreamStepKeys: [],
    upstreamTokensSaved: 0,
  });

  const handleSubmitChallenge = async (payload: {
    targetUpstreamStepKey: string;
    challengedSectionKey: string;
    challengeReason: string;
  }) => {
    try {
      const res = await apiClient.submitUpstreamChallenge(
        runId,
        CHALLENGER_STEP_KEY,
        {
          target_upstream_step_key: payload.targetUpstreamStepKey,
          challenged_section_key: payload.challengedSectionKey,
          challenge_reason: payload.challengeReason,
          target_profile_archetype: "PM_BUSINESS",
        },
      );
      setPreview({
        runId: res.preview.run_id,
        challengerStepKey: res.preview.challenger_step_key,
        targetUpstreamStepKey: res.preview.target_upstream_step_key,
        challengedSectionKey: res.preview.challenged_section_key,
        targetProfileArchetype: res.preview.target_profile_archetype,
        translatedSummary: res.preview.translated_summary,
        invalidatedDownstreamStepKeys: res.preview.invalidated_downstream_step_keys,
        invalidatedArtifactSections: res.preview.invalidated_artifact_sections,
        invalidatedOntologyAxiomKeys: res.preview.invalidated_ontology_axiom_keys,
        preservedUpstreamStepKeys: res.preview.preserved_upstream_step_keys,
        upstreamTokensSaved: res.preview.upstream_tokens_saved,
      });
      onFeedback(modalCopy.challengeSubmittedBanner);
    } catch (err: unknown) {
      onFeedback(
        `⚠️ ${formatRfc9457ErrorToBanner(err, resolvedLocale, modalCopy.errorContextLabel).fullText}`,
      );
    }
  };

  const handleTriggerReplay = async (payload: {
    stepKey: string;
    subWorkflowStepKey?: string;
  }) => {
    try {
      const res = await apiClient.replayWorkflowFromStep(runId, payload.stepKey, {
        sub_workflow_step_key: payload.subWorkflowStepKey ?? null,
      });
      onFeedback(
        formatI18nTemplate(modalCopy.replayBannerTemplate, {
          stepKey: res.replay.replayed_from_step_key,
        }),
      );
    } catch (err: unknown) {
      onFeedback(
        `⚠️ ${formatRfc9457ErrorToBanner(err, resolvedLocale, modalCopy.errorContextLabel).fullText}`,
      );
    }
  };

  return (
    <UpstreamChallengeRewindModal
      isOpen={isOpen}
      preview={{ ...preview, runId, challengedSectionKey: sectionKey }}
      labels={dictionary.upstreamChallengeModal}
      onSubmitChallenge={(p) => void handleSubmitChallenge(p)}
      onTriggerReplay={(p) => void handleTriggerReplay(p)}
      onClose={onClose}
    />
  );
}
