import React from "react";

export interface CognitiveReviewBriefingLabels {
  gridTitle: string;
  block1Title: string;
  block2Title: string;
  block3Title: string;
  block4Title: string;
  inspectHypothesesButtonLabel: string;
  hypothesesInspectedBadgeLabel: string;
  hypothesesPendingBadgeLabel: string;
}

export interface CognitiveReviewBriefingGridProps {
  executiveSummary: string;
  keyElementsAndTransverse: readonly string[];
  decisionsTaken: readonly string[];
  retainedHypotheses: readonly string[];
  hypothesesInspected: boolean;
  onInspectHypotheses?: () => void;
  readOnly?: boolean;
  labels: CognitiveReviewBriefingLabels;
}

/**
 * UX-DR4: 2x2 Cognitive Review Briefing Grid (`review-briefing-grid`).
 * Block 4 (`Hypothèses Retenues`) is framed in semantic amber (`--color-arbitration-amber`)
 * until explicitly inspected by the human validator.
 */
export function CognitiveReviewBriefingGrid({
  executiveSummary,
  keyElementsAndTransverse,
  decisionsTaken,
  retainedHypotheses,
  hypothesesInspected,
  onInspectHypotheses,
  readOnly = false,
  labels,
}: CognitiveReviewBriefingGridProps) {
  return (
    <section
      data-testid="review-briefing-grid"
      aria-label={labels.gridTitle}
      className="orcia-bento-card"
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "12px",
        padding: "16px",
        backgroundColor: "var(--color-surface-card)",
        border: "1px solid var(--color-border)",
        borderRadius: "var(--radius-lg)",
      }}
    >
      <header
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: "8px",
        }}
      >
        <strong style={{ fontSize: "15px", color: "var(--color-foreground)" }}>
          🛡️ {labels.gridTitle}
        </strong>
        <span
          data-testid="briefing-hypotheses-status-badge"
          style={{
            fontFamily: "var(--font-mono)",
            fontSize: "var(--font-size-mono)",
            padding: "3px 8px",
            borderRadius: "var(--radius-full)",
            backgroundColor: hypothesesInspected
              ? "var(--color-gate-emerald-bg)"
              : "var(--color-arbitration-bg)",
            color: hypothesesInspected
              ? "var(--color-gate-emerald)"
              : "var(--color-arbitration-amber)",
            border: hypothesesInspected
              ? "1px solid var(--color-gate-emerald)"
              : "1px solid var(--color-arbitration-amber)",
          }}
        >
          {hypothesesInspected
            ? `✓ ${labels.hypothesesInspectedBadgeLabel}`
            : `⚠️ ${labels.hypothesesPendingBadgeLabel}`}
        </span>
      </header>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
          gap: "12px",
        }}
      >
        {/* Block 1: Executive Summary */}
        <article
          data-testid="review-briefing-block-1"
          style={{
            padding: "12px",
            borderRadius: "var(--radius-md)",
            backgroundColor: "var(--color-surface-hover)",
            border: "1px solid var(--color-border)",
          }}
        >
          <div style={{ fontWeight: 600, marginBottom: "6px" }}>
            {labels.block1Title}
          </div>
          <p style={{ margin: 0, color: "var(--color-muted-foreground)" }}>
            {executiveSummary}
          </p>
        </article>

        {/* Block 2: Key Elements & Transverse Step 1 Alignment */}
        <article
          data-testid="review-briefing-block-2"
          style={{
            padding: "12px",
            borderRadius: "var(--radius-md)",
            backgroundColor: "var(--color-surface-hover)",
            border: "1px solid var(--color-border)",
          }}
        >
          <div style={{ fontWeight: 600, marginBottom: "6px" }}>
            {labels.block2Title}
          </div>
          <ul
            style={{
              margin: 0,
              paddingLeft: "18px",
              color: "var(--color-muted-foreground)",
            }}
          >
            {keyElementsAndTransverse.map((item, idx) => (
              <li key={idx}>{item}</li>
            ))}
          </ul>
        </article>

        {/* Block 3: Decisions Taken */}
        <article
          data-testid="review-briefing-block-3"
          style={{
            padding: "12px",
            borderRadius: "var(--radius-md)",
            backgroundColor: "var(--color-surface-hover)",
            border: "1px solid var(--color-border)",
          }}
        >
          <div style={{ fontWeight: 600, marginBottom: "6px" }}>
            {labels.block3Title}
          </div>
          <ul
            style={{
              margin: 0,
              paddingLeft: "18px",
              color: "var(--color-muted-foreground)",
            }}
          >
            {decisionsTaken.map((item, idx) => (
              <li key={idx}>{item}</li>
            ))}
          </ul>
        </article>

        {/* Block 4: Retained Hypotheses (Amber border until inspected) */}
        <article
          data-testid="review-briefing-block-4"
          data-amber-highlighted={!hypothesesInspected ? "true" : "false"}
          style={{
            padding: "12px",
            borderRadius: "var(--radius-md)",
            backgroundColor: hypothesesInspected
              ? "var(--color-surface-hover)"
              : "var(--color-arbitration-bg)",
            border: hypothesesInspected
              ? "1px solid var(--color-border)"
              : "2px solid var(--color-arbitration-amber)",
            display: "flex",
            flexDirection: "column",
            justifyContent: "space-between",
            gap: "8px",
          }}
        >
          <div>
            <div
              style={{
                fontWeight: 600,
                marginBottom: "6px",
                color: hypothesesInspected
                  ? "var(--color-foreground)"
                  : "var(--color-arbitration-amber)",
              }}
            >
              ⚖️ {labels.block4Title}
            </div>
            <ul
              style={{
                margin: 0,
                paddingLeft: "18px",
                color: "var(--color-foreground)",
              }}
            >
              {retainedHypotheses.map((item, idx) => (
                <li key={idx}>{item}</li>
              ))}
            </ul>
          </div>

          {!hypothesesInspected && (
            <button
              type="button"
              data-testid="inspect-hypotheses-btn"
              disabled={readOnly}
              onClick={onInspectHypotheses}
              style={{
                alignSelf: "flex-start",
                backgroundColor: "var(--color-arbitration-amber)",
                color: "var(--color-primary-foreground)",
                border: "none",
                borderRadius: "var(--radius-sm)",
                padding: "6px 10px",
                fontWeight: 600,
                cursor: readOnly ? "not-allowed" : "pointer",
              }}
            >
              {labels.inspectHypothesesButtonLabel}
            </button>
          )}
        </article>
      </div>
    </section>
  );
}
