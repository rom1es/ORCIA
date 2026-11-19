import { createOrciaApiClient } from "@orcia/api-client";
import {
  UpstreamChallengeRewindModal,
  type UpstreamChallengeWhatIfPreview,
} from "@orcia/ui";
import React, { useMemo, useState } from "react";
import { useI18n } from "../../i18n";

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
  const apiClient = useMemo(() => createOrciaApiClient({ baseUrl: "" }), []);
  const [preview, setPreview] = useState<UpstreamChallengeWhatIfPreview>({
    runId,
    challengerStepKey: CHALLENGER_STEP_KEY,
    targetUpstreamStepKey: TARGET_UPSTREAM_STEP_KEY,
    challengedSectionKey: sectionKey,
    targetProfileArchetype: "PM_BUSINESS",
    translatedSummary: isFr
      ? "Impact What-If : réévaluation ciblée de la section contestée sans retraiter l'amont validé."
      : "What-If Impact: targeted re-evaluation of the challenged section without reprocessing validated upstream steps.",
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
      onFeedback(
        isFr
          ? "⚠️ Contestation amont enregistrée et transmise pour révision."
          : "⚠️ Upstream challenge recorded and dispatched for revision.",
      );
    } catch (err: unknown) {
      onFeedback(`⚠️ ${err instanceof Error ? err.message : String(err)}`);
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
        isFr
          ? `[STALE_WARNING] Replay déclenché depuis « ${res.replay.replayed_from_step_key} ».`
          : `[STALE_WARNING] Replay triggered from "${res.replay.replayed_from_step_key}".`,
      );
    } catch (err: unknown) {
      onFeedback(`⚠️ ${err instanceof Error ? err.message : String(err)}`);
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
