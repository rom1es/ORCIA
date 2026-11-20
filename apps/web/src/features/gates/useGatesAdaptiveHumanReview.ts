import { createOrciaApiClient, type components } from "@orcia/api-client";
import type { UiChunkDecisionAction } from "@orcia/ui";
import { useCallback, useEffect, useState } from "react";
import { useAuthSessionStore } from "../../stores/authSessionStore";

export type HumanGateEvaluationItem = components["schemas"]["HumanGateEvaluationSchemaItem"];
export type StagedJiraActionItem = components["schemas"]["StagedJiraActionItemSchema"];

function buildLargeSectionText(prefix: string, count = 95): string {
  const phrase =
    "Vérification croisée de conformité architecturale, traçabilité du RunLock et validation des axiomes ontologiques L1-L4.";
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
  const locale: "fr" | "en" = isFr ? "fr" : "en";
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
      const msg = err instanceof Error ? err.message : isFr ? "Erreur de chargement des gates" : "Gate load error";
      onFeedback(
        isFr
          ? `⚠️ Impossible de charger les revues humaines (${msg}).`
          : `⚠️ Unable to load human gate reviews (${msg}).`,
      );
    }
  }, [workspaceId, locale, isFr, onFeedback]);

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
            decisions: [
              "Validation du contrat OpenAPI 3.1 et persistance PostgreSQL 18.",
              "Exécution différée des transitions Jira après validation de la Gate.",
            ],
            hypotheses: [
              "H1 : Les transitions Jira PAYBUILD-101 restent en attente jusqu'au PASS de la Gate.",
              "H2 : La signature SHA-256 couvre toute co-édition humaine de section.",
            ],
            sections: [
              {
                chunk_key: "sec-architecture",
                title: "Section 1 — Architecture & Frontières Hexagonales",
                content: buildLargeSectionText(
                  "Section 1 : Architecture modulaire et séparation des ports",
                ),
                human_authored_required: false,
              },
              {
                chunk_key: "sec-security-jira",
                title: "Section 2 — Sécurité & Actions Jira Pré-Validées",
                content: buildLargeSectionText(
                  "Section 2 : Contrôle d'accès RBAC et exécution Jira conditionnelle",
                ),
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
          summary:
            "Soumettre PAYBUILD-101 en revue dès validation de la Gate humaine",
          fields_payload: { pr_url: "https://git.orcia.local/pr/101" },
        }),
      ]);
      setEvaluation(evalRes.evaluation);
      setStagedJira(jiraRes.staged_action);
      onFeedback(
        isFr
          ? "✅ Briefing de revue 4 blocs et découpage par sections prêts pour validation."
          : "✅ 4-block review briefing and section chunks ready for validation.",
      );
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : isFr ? "Erreur d'ouverture de revue" : "Review open error";
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
      onFeedback(
        isFr
          ? "✅ Point 4 (Hypothèses Retenues) marqué comme relu."
          : "✅ Block 4 (Retained Assumptions) marked as inspected.",
      );
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : isFr ? "Erreur d'inspection" : "Inspection error";
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
        challenge_reason:
          action === "CHALLENGE"
            ? "Demande de précision sur l'alignement amont."
            : null,
      });
      setEvaluation(res.evaluation);
      if (action === "CHALLENGE") {
        setChallengedSectionKey(chunkKey);
        setChallengeModalOpen(true);
      }
      onFeedback(
        isFr
          ? `✅ Section « ${chunkKey} » mise à jour (${res.chunk.status}).`
          : `✅ Section "${chunkKey}" updated (${res.chunk.status}).`,
      );
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : isFr ? "Erreur sur la section" : "Section error";
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
      onFeedback(
        isFr
          ? "✅ Gate humaine validée (PASS) et action Jira en attente exécutée."
          : "✅ Human Gate approved (PASS) and staged Jira action executed.",
      );
    } catch (err: unknown) {
      const msg =
        err instanceof Error ? err.message : isFr ? "Erreur de finalisation Gate" : "Gate finalization error";
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
