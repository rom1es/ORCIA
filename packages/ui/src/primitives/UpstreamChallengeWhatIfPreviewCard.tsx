import React from "react";
import type {
  UpstreamChallengeModalLabels,
  UpstreamChallengeWhatIfPreview,
} from "./UpstreamChallengeRewindModal";

export interface UpstreamChallengeWhatIfPreviewCardProps {
  readonly preview: UpstreamChallengeWhatIfPreview;
  readonly labels: UpstreamChallengeModalLabels;
}

export function UpstreamChallengeWhatIfPreviewCard({
  preview,
  labels,
}: UpstreamChallengeWhatIfPreviewCardProps): React.ReactElement {
  return (
    <div
      data-testid="what-if-impact-preview-panel"
      style={{
        padding: "10px 12px",
        borderRadius: "var(--radius-sm)",
        backgroundColor: "var(--color-arbitration-bg)",
        border: "1px solid var(--color-arbitration-amber)",
        display: "flex",
        flexDirection: "column",
        gap: "6px",
        fontSize: "0.75rem",
      }}
    >
      <strong style={{ color: "var(--color-text-primary)" }}>{labels.whatIfTitle}</strong>
      <div>
        <strong>{labels.invalidatedStepsLabel}:</strong>{" "}
        <code data-testid="what-if-invalidated-steps" style={{ fontFamily: "var(--font-mono)" }}>
          {preview.invalidatedDownstreamStepKeys.join(", ")}
        </code>
      </div>
      <div>
        <strong>{labels.invalidatedSectionsLabel}:</strong>{" "}
        <code
          data-testid="what-if-invalidated-sections"
          style={{ fontFamily: "var(--font-mono)" }}
        >
          {preview.invalidatedArtifactSections.join(", ")}
        </code>
      </div>
      <div>
        <strong>{labels.invalidatedAxiomsLabel}:</strong>{" "}
        <code data-testid="what-if-invalidated-axioms" style={{ fontFamily: "var(--font-mono)" }}>
          {preview.invalidatedOntologyAxiomKeys.join(", ")}
        </code>
      </div>
      <div style={{ color: "var(--color-gate-pass)" }}>
        <strong>{labels.preservedStepsLabel}:</strong>{" "}
        <code data-testid="what-if-preserved-steps" style={{ fontFamily: "var(--font-mono)" }}>
          {preview.preservedUpstreamStepKeys.length > 0
            ? `${preview.preservedUpstreamStepKeys.join(", ")} (0 token — ${preview.upstreamTokensSaved} tokens économisés)`
            : "Racine du workflow (Step 1)"}
        </code>
      </div>
      <div
        data-testid="what-if-translated-summary"
        style={{
          marginTop: "4px",
          padding: "6px 8px",
          borderRadius: "var(--radius-sm)",
          backgroundColor: "var(--color-surface-card)",
          color: "var(--color-text-secondary)",
        }}
      >
        <strong>
          {labels.translatedSummaryLabel} ({preview.targetProfileArchetype}):
        </strong>{" "}
        {preview.translatedSummary}
      </div>
    </div>
  );
}
