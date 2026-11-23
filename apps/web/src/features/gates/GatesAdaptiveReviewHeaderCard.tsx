import React from "react";
import { resolveDictionaryForFlag } from "../../i18n";
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
  const hdrCopy = resolveDictionaryForFlag(isFr).featureCockpitGates.gates.headerCard;
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
        <strong>{hdrCopy.title}</strong>
        {evaluation || stagedJira ? (
          <div style={{ display: "flex", gap: "8px", marginTop: "6px", flexWrap: "wrap" }}>
            {evaluation ? (
              <span
                data-testid="gates-human-evaluation-status-badge"
                data-status={evaluation.status}
                className="orcia-uri-pill"
              >
                {hdrCopy.gatePrefix} :{" "}
                {evaluation.status === "PENDING_HUMAN_REVIEW"
                  ? hdrCopy.statusPendingReview
                  : evaluation.status === "PASS"
                    ? hdrCopy.statusPassed
                    : evaluation.status}
              </span>
            ) : null}
            {stagedJira ? (
              <span
                data-testid="gates-staged-jira-status-badge"
                data-status={stagedJira.status}
                className="orcia-uri-pill"
              >
                {`Jira ${stagedJira.issue_key} :`}{" "}
                {stagedJira.status === "STAGED"
                  ? hdrCopy.jiraStaged
                  : stagedJira.status === "EXECUTED"
                    ? hdrCopy.jiraExecuted
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
        {hdrCopy.prepareReviewBtn}
      </button>
    </div>
  );
}
