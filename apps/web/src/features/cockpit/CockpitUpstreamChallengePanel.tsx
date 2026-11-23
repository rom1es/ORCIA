import { createOrciaApiClient } from "@orcia/api-client";
import {
  OrciaAlertBanner,
  UpstreamChallengeRewindModal,
  type UpstreamChallengeWhatIfPreview,
} from "@orcia/ui";
import React, { useCallback, useEffect, useMemo, useState } from "react";
import { formatI18nTemplate, useI18n } from "../../i18n";

const CHALLENGER_STEP_KEY = "delegate-remediation-subworkflow";
const TARGET_UPSTREAM_STEP_KEY = "frame-architecture-intent";
const CHALLENGED_SECTION_KEY = "human_architecture_intent";

export interface CockpitUpstreamChallengePanelProps {
  readonly runId: string | null;
  readonly isOpen: boolean;
  readonly initialStaleWarning?: boolean;
  readonly onError: (message: string | null) => void;
  readonly onReplayCompleted?: () => void;
}

export function CockpitUpstreamChallengePanel({
  runId,
  isOpen,
  initialStaleWarning = false,
  onError,
  onReplayCompleted,
}: CockpitUpstreamChallengePanelProps) {
  const { dictionary } = useI18n();
  const chCopy = dictionary.featureCockpitGates.cockpit.upstreamChallenge;
  const apiClient = useMemo(() => createOrciaApiClient({ baseUrl: "" }), []);
  const [portalOpen, setPortalOpen] = useState(false);
  const [staleWarningBanner, setStaleWarningBanner] = useState<string | null>(null);
  const [preview, setPreview] = useState<UpstreamChallengeWhatIfPreview>(() => ({
    runId: runId ?? "pending-run",
    challengerStepKey: CHALLENGER_STEP_KEY,
    targetUpstreamStepKey: TARGET_UPSTREAM_STEP_KEY,
    challengedSectionKey: CHALLENGED_SECTION_KEY,
    targetProfileArchetype: "PM_BUSINESS",
    translatedSummary: chCopy.defaultSummary,
    invalidatedDownstreamStepKeys: [
      TARGET_UPSTREAM_STEP_KEY,
      CHALLENGER_STEP_KEY,
      "post-deploy-verification",
    ],
    invalidatedArtifactSections: [`${TARGET_UPSTREAM_STEP_KEY}:${CHALLENGED_SECTION_KEY}`],
    invalidatedOntologyAxiomKeys: [],
    preservedUpstreamStepKeys: [],
    upstreamTokensSaved: 0,
  }));

  const refreshPreview = useCallback(
    async (reasonText: string) => {
      if (!runId || reasonText.trim().length < 10) {
        return;
      }
      try {
        const res = await apiClient.previewUpstreamChallenge(
          runId,
          CHALLENGER_STEP_KEY,
          {
            target_upstream_step_key: TARGET_UPSTREAM_STEP_KEY,
            challenged_section_key: CHALLENGED_SECTION_KEY,
            challenge_reason: reasonText.trim(),
            target_profile_archetype: "PM_BUSINESS",
          },
        );
        const p = res.preview;
        setPreview({
          runId: p.run_id,
          challengerStepKey: p.challenger_step_key,
          targetUpstreamStepKey: p.target_upstream_step_key,
          challengedSectionKey: p.challenged_section_key,
          targetProfileArchetype: p.target_profile_archetype,
          translatedSummary: p.translated_summary,
          invalidatedDownstreamStepKeys: p.invalidated_downstream_step_keys,
          invalidatedArtifactSections: p.invalidated_artifact_sections,
          invalidatedOntologyAxiomKeys: p.invalidated_ontology_axiom_keys,
          preservedUpstreamStepKeys: p.preserved_upstream_step_keys,
          upstreamTokensSaved: p.upstream_tokens_saved,
        });
      } catch (err) {
        onError(err instanceof Error ? err.message : String(err));
      }
    },
    [apiClient, onError, runId],
  );

  useEffect(() => {
    if (isOpen && runId) {
      void refreshPreview(chCopy.defaultPreviewReason);
    }
  }, [chCopy.defaultPreviewReason, isOpen, refreshPreview, runId]);

  if (!isOpen || !runId) {
    return null;
  }

  const handleSubmitChallenge = async (payload: {
    targetUpstreamStepKey: string;
    challengedSectionKey: string;
    challengeReason: string;
  }) => {
    onError(null);
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
      const p = res.preview;
      setPreview({
        runId: p.run_id,
        challengerStepKey: p.challenger_step_key,
        targetUpstreamStepKey: p.target_upstream_step_key,
        challengedSectionKey: p.challenged_section_key,
        targetProfileArchetype: p.target_profile_archetype,
        translatedSummary: p.translated_summary,
        invalidatedDownstreamStepKeys: p.invalidated_downstream_step_keys,
        invalidatedArtifactSections: p.invalidated_artifact_sections,
        invalidatedOntologyAxiomKeys: p.invalidated_ontology_axiom_keys,
        preservedUpstreamStepKeys: p.preserved_upstream_step_keys,
        upstreamTokensSaved: p.upstream_tokens_saved,
      });
    } catch (err) {
      onError(err instanceof Error ? err.message : String(err));
    }
  };

  const handleTriggerReplay = async (payload: {
    stepKey: string;
    subWorkflowStepKey?: string;
  }) => {
    onError(null);
    try {
      const res = await apiClient.replayWorkflowFromStep(runId, payload.stepKey, {
        sub_workflow_step_key: payload.subWorkflowStepKey ?? null,
      });
      setStaleWarningBanner(
        formatI18nTemplate(chCopy.staleReplayTemplate, {
          stepKey: res.replay.replayed_from_step_key,
        }),
      );
      onReplayCompleted?.();
    } catch (err) {
      onError(err instanceof Error ? err.message : String(err));
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
      <div style={{ display: "flex", justifyContent: "flex-end" }}>
        <button
          type="button"
          data-testid="cockpit-open-upstream-challenge-modal-btn"
          onClick={() => setPortalOpen(true)}
          className="orcia-ds-btn orcia-ds-btn-secondary orcia-ds-btn-sm"
        >
          {chCopy.openModalBtn}
        </button>
      </div>

      {staleWarningBanner || initialStaleWarning ? (
        <OrciaAlertBanner
          tone="amber"
          role="status"
          testId="upstream-replay-stale-warning-banner"
        >
          {staleWarningBanner ?? chCopy.defaultStaleBanner}
        </OrciaAlertBanner>
      ) : null}

      <UpstreamChallengeRewindModal
        isOpen={isOpen}
        inline={!portalOpen}
        preview={preview}
        labels={dictionary.upstreamChallengeModal}
        onReasonChange={(nextReason) => void refreshPreview(nextReason)}
        onSubmitChallenge={(p) => void handleSubmitChallenge(p)}
        onTriggerReplay={(p) => void handleTriggerReplay(p)}
        onClose={() => setPortalOpen(false)}
      />
    </div>
  );
}
