import { createOrciaApiClient, type components } from "@orcia/api-client";
import {
  ChunkValidationCard,
  CognitiveReviewBriefingGrid,
  type UiChunkDecisionAction,
  type UiChunkValidationItem,
} from "@orcia/ui";
import React, { useCallback, useEffect, useState } from "react";
import { useI18n } from "../../i18n";

type HumanGateEvaluationItem = components["schemas"]["HumanGateEvaluationSchemaItem"];
type StagedJiraActionItem = components["schemas"]["StagedJiraActionItemSchema"];

export interface GatesAdaptiveHumanReviewSectionProps {
  activeWorkspaceId?: string;
  isFr: boolean;
  onFeedback: (message: string | null) => void;
}

function buildLargeSectionText(prefix: string, count = 95): string {
  const phrase =
    "Vérification croisée de conformité architecturale, traçabilité du RunLock et validation des axiomes ontologiques L1-L4.";
  return `${prefix} — ${Array.from({ length: count }, () => phrase).join(" ")}`;
}

export function GatesAdaptiveHumanReviewSection({
  activeWorkspaceId,
  isFr,
  onFeedback,
}: GatesAdaptiveHumanReviewSectionProps) {
  const { dictionary } = useI18n();
  const workspaceId = activeWorkspaceId || "0192c4e0-0000-7000-8000-000000000201";
  const [evaluation, setEvaluation] = useState<HumanGateEvaluationItem | null>(null);
  const [stagedJira, setStagedJira] = useState<StagedJiraActionItem | null>(null);
  const [loading, setLoading] = useState<boolean>(false);

  const loadPersistedState = useCallback(async () => {
    const client = createOrciaApiClient({ baseUrl: "" });
    try {
      const [evalRes, jiraRes] = await Promise.all([
        client.listHumanGateEvaluations(workspaceId),
        client.listStagedJiraActions(workspaceId),
      ]);
      setEvaluation(evalRes.evaluations[evalRes.evaluations.length - 1] ?? null);
      setStagedJira(jiraRes.actions[jiraRes.actions.length - 1] ?? null);
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Erreur de chargement des gates";
      onFeedback(
        isFr
          ? `⚠️ Impossible de charger les revues humaines (${msg}).`
          : `⚠️ Unable to load human gate reviews (${msg}).`,
      );
    }
  }, [workspaceId, isFr, onFeedback]);

  useEffect(() => {
    void loadPersistedState();
  }, [loadPersistedState]);

  const handleOpenHumanReview = async () => {
    setLoading(true);
    const client = createOrciaApiClient({ baseUrl: "" });
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
        err instanceof Error ? err.message : "Erreur d'ouverture de revue";
      onFeedback(`⚠️ ${msg}`);
    } finally {
      setLoading(false);
    }
  };

  const handleInspectHypotheses = async () => {
    if (!evaluation) return;
    const client = createOrciaApiClient({ baseUrl: "" });
    try {
      const res = await client.inspectHumanGateHypotheses(evaluation.id);
      setEvaluation(res.evaluation);
      onFeedback(
        isFr
          ? "✅ Point 4 (Hypothèses Retenues) marqué comme relu."
          : "✅ Block 4 (Retained Assumptions) marked as inspected.",
      );
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Erreur d'inspection";
      onFeedback(`⚠️ ${msg}`);
    }
  };

  const handleDecideChunk = async (
    chunkKey: string,
    action: UiChunkDecisionAction,
    coEditedContent?: string,
  ) => {
    if (!evaluation) return;
    const client = createOrciaApiClient({ baseUrl: "" });
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
      onFeedback(
        isFr
          ? `✅ Section « ${chunkKey} » mise à jour (${res.chunk.status}).`
          : `✅ Section "${chunkKey}" updated (${res.chunk.status}).`,
      );
    } catch (err: unknown) {
      const msg = err instanceof Error ? err.message : "Erreur sur la section";
      onFeedback(`⚠️ ${msg}`);
    }
  };

  const handleFinalizeGate = async (options: {
    explicitHypothesesConfirmation: boolean;
    fastApprovalWarning: boolean;
  }) => {
    if (!evaluation) return;
    const client = createOrciaApiClient({ baseUrl: "" });
    try {
      const finalized = await client.finalizeHumanGate(evaluation.id, {
        review_duration_ms: options.fastApprovalWarning ? 3200 : 18000,
        explicit_hypotheses_confirmation:
          options.explicitHypothesesConfirmation,
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
        err instanceof Error ? err.message : "Erreur de finalisation Gate";
      onFeedback(`⚠️ ${msg}`);
    }
  };

  const briefingJson = (evaluation?.briefing_4blocks_jsonb ?? {}) as Record<
    string,
    Record<string, unknown>
  >;
  const executiveSummary = String(
    briefingJson.block_1_executive_summary?.summary ??
      (isFr
        ? "Synthèse exécutive de l'étape soumise à validation humaine."
        : "Executive summary of the step awaiting human review."),
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
      <div
        className="orcia-bento-card"
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "12px",
        }}
      >
        <div>
          <strong>
            {isFr
              ? "Revue Humaine Adaptative (Briefing 4 Blocs, Découpage & Garde-fou < 15 s)"
              : "Adaptive Human Review (4-Block Briefing, Chunked Approval & < 15s Guard)"}
          </strong>
          {evaluation ? (
            <div style={{ display: "flex", gap: "8px", marginTop: "6px", flexWrap: "wrap" }}>
              <span data-testid="gates-human-evaluation-status-badge" className="orcia-uri-pill">
                Gate: {evaluation.status}
              </span>
              {stagedJira ? (
                <span data-testid="gates-staged-jira-status-badge" className="orcia-uri-pill">
                  Jira {stagedJira.issue_key}: {stagedJira.status}
                </span>
              ) : null}
            </div>
          ) : null}
        </div>
        <button
          type="button"
          data-testid="gates-open-human-review-btn"
          disabled={loading}
          onClick={() => void handleOpenHumanReview()}
          style={{
            padding: "7px 14px",
            borderRadius: "var(--radius-sm)",
            border: "none",
            backgroundColor: "var(--color-primary-cobalt)",
            color: "var(--color-primary-foreground)",
            fontWeight: 600,
            cursor: loading ? "not-allowed" : "pointer",
          }}
        >
          {isFr
            ? "Préparer une revue humaine (4 blocs + Jira)"
            : "Prepare Human Review (4 blocks + Jira)"}
        </button>
      </div>

      {evaluation ? (
        <>
          <CognitiveReviewBriefingGrid
            executiveSummary={executiveSummary}
            keyElementsAndTransverse={[
              isFr
                ? `Alignement Étape 1 : ${evaluation.ontology_conflicts === 0 ? "Conforme" : "Conflit"}`
                : `Step 1 Alignment: ${evaluation.ontology_conflicts === 0 ? "Aligned" : "Conflict"}`,
              isFr
                ? `Volume total : ${evaluation.total_word_count} mots`
                : `Total volume: ${evaluation.total_word_count} words`,
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
        </>
      ) : null}
    </section>
  );
}
