import { createOrciaApiClient, type components } from "@orcia/api-client";
import type { UiChunkDecisionAction } from "@orcia/ui";
import { useCallback, useEffect, useState } from "react";
import {
  formatI18nTemplate,
  resolveDictionaryForFlag,
  resolveLocaleForFlag,
} from "../../i18n";
import { useAuthSessionStore } from "../../stores/authSessionStore";

export type HumanGateEvaluationItem = components["schemas"]["HumanGateEvaluationSchemaItem"];
export type StagedJiraActionItem = components["schemas"]["StagedJiraActionItemSchema"];

function buildLargeSectionText(prefix: string, phrase: string, count = 95): string {
  return `${prefix} — ${Array.from({ length: count }, () => phrase).join(" ")}`;
}

interface UseGatesAdaptiveHumanReviewArgs {
  readonly activeWorkspaceId?: string;
  readonly isFr: boolean;
  readonly onFeedback: (message: string | null) => void;
}

export function useGatesAdaptiveHumanReview({
  activeWorkspaceId,
  isFr,
  onFeedback,
}: UseGatesAdaptiveHumanReviewArgs) {
  const workspaceId = activeWorkspaceId || "0192c4e0-0000-7000-8000-000000000201";
  const locale = resolveLocaleForFlag(isFr);
  const reviewCopy = resolveDictionaryForFlag(isFr, locale).featureCockpitGates.gates.humanReview;
  const [evaluation, setEvaluation] = useState<HumanGateEvaluationItem | null>(null);
  const [stagedJira, setStagedJira] = useState<StagedJiraActionItem | null>(null);
  const [loading, setLoading] = useState<boolean>(false);
  const [challengeModalOpen, setChallengeModalOpen] = useState<boolean>(false);
  const [challengedSectionKey, setChallengedSectionKey] = useState<string>("sec-architecture");

  const isHydrating = useAuthSessionStore((s) => s.isHydrating);
  const accessToken = useAuthSessionStore((s) => s.accessToken);

  const loadPersistedState = useCallback(async () => {
    const client = createOrciaApiClient({ baseUrl: "", locale });
    try {
      const [evalRes, jiraRes] = await Promise.all([
        client.listHumanGateEvaluations(workspaceId),
        client.listStagedJiraActions(workspaceId),
      ]);
      setEvaluation(evalRes.evaluations[evalRes.evaluations.length - 1] ?? null);
      setStagedJira(jiraRes.actions[jiraRes.actions.length - 1] ?? null);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : reviewCopy.loadErrorFallback;
      onFeedback(formatI18nTemplate(reviewCopy.loadErrorBannerTemplate, { msg }));
    }
  }, [
    workspaceId,
    locale,
    onFeedback,
    reviewCopy.loadErrorBannerTemplate,
    reviewCopy.loadErrorFallback,
  ]);

  useEffect(() => {
    if (isHydrating) {
      return;
    }
    onFeedback(null);
    void loadPersistedState();
  }, [loadPersistedState, isHydrating, accessToken, onFeedback]);

  const handleOpenHumanReview = async () => {
    setLoading(true);
    const client = createOrciaApiClient({ baseUrl: "", locale });
    const runId = "0195f000-0000-7000-8000-000000000701";
    const stepExecutionId = "0195f000-0000-7000-8000-000000000801";
    try {
      const [evalRes, jiraRes] = await Promise.all([
        client.evaluateHumanGate({
          workspace_id: workspaceId,
          run_id: runId,
          step_execution_id: stepExecutionId,
          step_key: "step-architecture-gate",
          policy: "mandatory_full",
          deterministic_status: "PASS",
          agentic_score: 0.94,
          ontology_conflicts: 0,
          stale_warnings: 0,
          artifact_payload: {
            decisions: [...reviewCopy.seedDecisions],
            hypotheses: [...reviewCopy.seedHypotheses],
            sections: [
              {
                chunk_key: "sec-architecture",
                title: reviewCopy.seedSec1Title,
                content: buildLargeSectionText(reviewCopy.seedSec1Prefix, reviewCopy.seedPhrase),
                human_authored_required: false,
              },
              {
                chunk_key: "sec-security-jira",
                title: reviewCopy.seedSec2Title,
                content: buildLargeSectionText(reviewCopy.seedSec2Prefix, reviewCopy.seedPhrase),
                human_authored_required: false,
              },
            ],
          },
        }),
        client.stageJiraWorkflowAction({
          workspace_id: workspaceId,
          run_id: runId,
          step_execution_id: stepExecutionId,
          project_alias: "jira:product",
          action_type: "transition_issue",
          issue_key: "PAYBUILD-101",
          target_transition: "Submit for Review",
          summary: reviewCopy.seedJiraSummary,
          fields_payload: { pr_url: "https://git.orcia.local/pr/101" },
        }),
      ]);
      setEvaluation(evalRes.evaluation);
      setStagedJira(jiraRes.staged_action);
      onFeedback(reviewCopy.openReviewSuccess);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : reviewCopy.openReviewErrorFallback;
      onFeedback(`⚠️ ${msg}`);
    } finally {
      setLoading(false);
    }
  };

  const handleInspectHypotheses = async () => {
    if (!evaluation) return;
    const client = createOrciaApiClient({ baseUrl: "", locale });
    try {
      const res = await client.inspectHumanGateHypotheses(evaluation.id);
      setEvaluation(res.evaluation);
      onFeedback(reviewCopy.inspectHypothesesSuccess);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : reviewCopy.inspectHypothesesErrorFallback;
      onFeedback(`⚠️ ${msg}`);
    }
  };

  const handleDecideChunk = async (
    chunkKey: string,
    action: UiChunkDecisionAction,
    coEditedContent?: string,
  ) => {
    if (!evaluation) return;
    const client = createOrciaApiClient({ baseUrl: "", locale });
    try {
      const res = await client.decideHumanGateChunk(evaluation.id, chunkKey, {
        action,
        co_edited_content: coEditedContent ?? null,
        challenge_reason: action === "CHALLENGE" ? reviewCopy.defaultChallengeReason : null,
      });
      setEvaluation(res.evaluation);
      if (action === "CHALLENGE") {
        setChallengedSectionKey(chunkKey);
        setChallengeModalOpen(true);
      }
      const rawChunkStatus = res.chunk.status ?? "PENDING";
      const localizedChunkStatus = reviewCopy.chunkStatusLabels[rawChunkStatus] ?? rawChunkStatus;
      onFeedback(
        formatI18nTemplate(reviewCopy.chunkUpdatedTemplate, { status: localizedChunkStatus }),
      );
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : reviewCopy.chunkErrorFallback;
      onFeedback(`⚠️ ${msg}`);
    }
  };

  const handleFinalizeGate = async (options: {
    explicitHypothesesConfirmation: boolean;
    fastApprovalWarning: boolean;
  }) => {
    if (!evaluation) return;
    const client = createOrciaApiClient({ baseUrl: "", locale });
    try {
      const finalized = await client.finalizeHumanGate(evaluation.id, {
        review_duration_ms: options.fastApprovalWarning ? 3200 : 18000,
        explicit_hypotheses_confirmation: options.explicitHypothesesConfirmation,
      });
      setEvaluation(finalized.evaluation);
      if (stagedJira && stagedJira.status === "STAGED") {
        const committed = await client.commitStagedJiraAction({
          staged_action_id: stagedJira.staged_action_id,
          gate_status: "PASS",
          run_lock_sha256: "sha256:runlock-gate-pass-verified",
        });
        setStagedJira(committed.executed_action);
      }
      onFeedback(reviewCopy.finalizeSuccess);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : reviewCopy.finalizeErrorFallback;
      onFeedback(`⚠️ ${msg}`);
    }
  };

  return {
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
  };
}
