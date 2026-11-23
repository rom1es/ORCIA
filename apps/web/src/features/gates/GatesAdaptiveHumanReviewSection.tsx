import {
  ChunkValidationCard,
  CognitiveReviewBriefingGrid,
  type UiChunkValidationItem,
} from "@orcia/ui";
import React from "react";
import { formatI18nTemplate, useI18n } from "../../i18n";
import { GatesAdaptiveReviewHeaderCard } from "./GatesAdaptiveReviewHeaderCard";
import { GatesChallengeModalSection } from "./GatesChallengeModalSection";
import { useGatesAdaptiveHumanReview } from "./useGatesAdaptiveHumanReview";

export interface GatesAdaptiveHumanReviewSectionProps {
  activeWorkspaceId?: string;
  isFr: boolean;
  onFeedback: (message: string | null) => void;
}

export function GatesAdaptiveHumanReviewSection({
  activeWorkspaceId,
  isFr,
  onFeedback,
}: GatesAdaptiveHumanReviewSectionProps) {
  const { dictionary } = useI18n();
  const reviewCopy = dictionary.featureCockpitGates.gates.humanReview;
  const {
    evaluation,
    stagedJira,
    loading,
    challengeModalOpen,
    challengedSectionKey,
    setChallengeModalOpen,
    handleOpenHumanReview,
    handleInspectHypotheses,
    handleDecideChunk,
    handleFinalizeGate,
  } = useGatesAdaptiveHumanReview({ activeWorkspaceId, isFr, onFeedback });

  const briefingJson = (evaluation?.briefing_4blocks_jsonb ?? {}) as Record<
    string,
    Record<string, unknown>
  >;
  const executiveSummary = String(
    briefingJson.block_1_executive_summary?.summary ??
      reviewCopy.defaultExecutiveSummary,
  );
  const decisionsTaken = Array.isArray(briefingJson.block_3_decisions_taken?.decisions)
    ? (briefingJson.block_3_decisions_taken?.decisions as string[])
    : [];
  const retainedHypotheses = Array.isArray(briefingJson.block_4_retained_hypotheses?.hypotheses)
    ? (briefingJson.block_4_retained_hypotheses?.hypotheses as string[])
    : [];
  const uiChunks: UiChunkValidationItem[] = (evaluation?.chunks ?? []).map((c) => ({
    chunkKey: c.chunk_key,
    sectionTitle: c.section_title,
    sectionIndex: c.section_index ?? 0,
    contentMarkdown: c.content_markdown ?? "",
    wordCount: c.word_count ?? 0,
    humanAuthoredRequired: c.human_authored_required ?? false,
    status: c.status ?? "PENDING",
    humanAnchorSha256: c.human_anchor_sha256 ?? null,
  }));

  return (
    <section
      data-testid="gates-adaptive-human-review-section"
      style={{ display: "flex", flexDirection: "column", gap: "12px" }}
    >
      <GatesAdaptiveReviewHeaderCard
        isFr={isFr}
        loading={loading}
        evaluation={evaluation}
        stagedJira={stagedJira}
        onOpenHumanReview={() => void handleOpenHumanReview()}
      />

      {evaluation ? (
        <>
          <CognitiveReviewBriefingGrid
            executiveSummary={executiveSummary}
            keyElementsAndTransverse={[
              formatI18nTemplate(reviewCopy.step1AlignmentTemplate, {
                status:
                  evaluation.ontology_conflicts === 0
                    ? reviewCopy.alignmentAligned
                    : reviewCopy.alignmentConflict,
              }),
              formatI18nTemplate(reviewCopy.totalVolumeTemplate, {
                count: evaluation.total_word_count,
              }),
            ]}
            decisionsTaken={decisionsTaken}
            retainedHypotheses={retainedHypotheses}
            hypothesesInspected={evaluation.hypotheses_block_inspected}
            onInspectHypotheses={() => void handleInspectHypotheses()}
            labels={dictionary.humanGates.briefing}
          />
          <ChunkValidationCard
            chunks={uiChunks}
            totalWordCount={evaluation.total_word_count}
            reviewDurationMs={evaluation.review_duration_ms || 2500}
            hypothesesInspected={evaluation.hypotheses_block_inspected}
            retainedHypotheses={retainedHypotheses}
            onDecideChunk={(chunkKey, action, coEditedContent) =>
              void handleDecideChunk(chunkKey, action, coEditedContent)
            }
            onFinalizeGate={(opts) => void handleFinalizeGate(opts)}
            labels={dictionary.humanGates.chunkValidation}
          />
          <GatesChallengeModalSection
            isOpen={challengeModalOpen}
            runId={evaluation.run_id}
            sectionKey={challengedSectionKey}
            isFr={isFr}
            onClose={() => setChallengeModalOpen(false)}
            onFeedback={onFeedback}
          />
        </>
      ) : null}
    </section>
  );
}
