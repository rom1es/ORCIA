import React from "react";
import type {
  HumanGateEvaluationItem,
  StagedJiraActionItem,
} from "./useGatesAdaptiveHumanReview";

export interface GatesAdaptiveReviewHeaderCardProps {
  readonly isFr: boolean;
  readonly loading: boolean;
  readonly evaluation: HumanGateEvaluationItem | null;
  readonly stagedJira: StagedJiraActionItem | null;
  readonly onOpenHumanReview: () => void;
}

export function GatesAdaptiveReviewHeaderCard({
  isFr,
  loading,
  evaluation,
  stagedJira,
  onOpenHumanReview,
}: GatesAdaptiveReviewHeaderCardProps): React.ReactElement {
  return (
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
        {evaluation || stagedJira ? (
          <div style={{ display: "flex", gap: "8px", marginTop: "6px", flexWrap: "wrap" }}>
            {evaluation ? (
              <span
                data-testid="gates-human-evaluation-status-badge"
                data-status={evaluation.status}
                className="orcia-uri-pill"
              >
                {isFr ? "Point de contrôle" : "Gate"} :{" "}
                {evaluation.status === "PENDING_HUMAN_REVIEW"
                  ? isFr
                    ? "Validation humaine requise"
                    : "Pending human review"
                  : evaluation.status === "PASS"
                    ? isFr
                      ? "Validé"
                      : "Passed"
                    : evaluation.status}
              </span>
            ) : null}
            {stagedJira ? (
              <span
                data-testid="gates-staged-jira-status-badge"
                data-status={stagedJira.status}
                className="orcia-uri-pill"
              >
                Jira {stagedJira.issue_key} :{" "}
                {stagedJira.status === "STAGED"
                  ? isFr
                    ? "Préparée (en attente)"
                    : "Prepared (pending)"
                  : stagedJira.status === "EXECUTED"
                    ? isFr
                      ? "Exécutée"
                      : "Executed"
                    : stagedJira.status}
              </span>
            ) : null}
          </div>
        ) : null}
      </div>
      <button
        type="button"
        data-testid="gates-open-human-review-btn"
        disabled={loading}
        onClick={onOpenHumanReview}
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
  );
}
