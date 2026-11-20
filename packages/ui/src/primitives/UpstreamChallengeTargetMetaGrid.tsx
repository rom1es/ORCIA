import React from "react";
import { OrciaIcon } from "../components/icons";
import type {
  UpstreamChallengeModalLabels,
  UpstreamChallengeWhatIfPreview,
} from "./UpstreamChallengeRewindModalTypes";

export function UpstreamChallengeTargetMetaGrid({
  labels,
  preview,
  subWorkflowStepKey,
}: {
  readonly labels: UpstreamChallengeModalLabels;
  readonly preview: UpstreamChallengeWhatIfPreview;
  readonly subWorkflowStepKey?: string;
}): React.ReactElement {
  const resolveStep = (key: string): string => labels.stepLabels?.[key] ?? key;
  const resolveSection = (key: string): string => labels.sectionLabels?.[key] ?? key;

  return (
    <div
      style={{
        display: "grid",
        gridTemplateColumns: "repeat(auto-fit, minmax(200px, 1fr))",
        gap: "8px",
        fontSize: "0.75rem",
      }}
    >
      <div
        style={{
          padding: "8px",
          borderRadius: "var(--radius-sm)",
          backgroundColor: "var(--color-surface-canvas)",
          border: "1px solid var(--color-border-subtle)",
        }}
      >
        <strong style={{ color: "var(--color-text-secondary)" }}>
          {labels.targetStepLabel}:
        </strong>{" "}
        <code style={{ fontFamily: "var(--font-mono)", color: "var(--color-text-primary)" }}>
          {resolveStep(preview.targetUpstreamStepKey)}
          {subWorkflowStepKey ? (
            <>
              {" "}
              <OrciaIcon name="arrowRight" /> {resolveStep(subWorkflowStepKey)}
            </>
          ) : (
            ""
          )}
        </code>
      </div>
      <div
        style={{
          padding: "8px",
          borderRadius: "var(--radius-sm)",
          backgroundColor: "var(--color-surface-canvas)",
          border: "1px solid var(--color-border-subtle)",
        }}
      >
        <strong style={{ color: "var(--color-text-secondary)" }}>
          {labels.sectionKeyLabel}:
        </strong>{" "}
        <code style={{ fontFamily: "var(--font-mono)", color: "var(--color-text-primary)" }}>
          {resolveSection(preview.challengedSectionKey)}
        </code>
      </div>
    </div>
  );
}
