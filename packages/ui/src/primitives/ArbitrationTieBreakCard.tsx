import React, { useState } from "react";

export type UiTieBreakPolicy =
  | "PAUSE_AND_ESCALATE"
  | "ONTOLOGY_AXIOM_FIRST"
  | "DEFER_AND_CONTINUE_WITH_ASSUMPTION";

export interface ArbitrationTieBreakOptionView {
  optionKey: string;
  title: string;
  pros: string[];
  cons: string[];
  siImpact: string;
  finopsImpact: string;
  recommended?: boolean;
}

export interface ArbitrationTieBreakCardLabels {
  badgeTitle: string;
  policyPrefixLabel: string;
  recommendedBadgeLabel: string;
  prosLabel: string;
  consLabel: string;
  siImpactLabel: string;
  finopsImpactLabel: string;
  justificationPlaceholder: string;
  selectOptionButtonLabel: string;
  resolvedBannerPrefix: string;
}

export interface ArbitrationTieBreakCardProps {
  arbitrationId: string;
  stepKey: string;
  questionTitle: string;
  contextSummary?: string;
  tieBreakPolicy: UiTieBreakPolicy;
  options: ArbitrationTieBreakOptionView[];
  selectedOptionKey?: string | null;
  readOnly?: boolean;
  labels: ArbitrationTieBreakCardLabels;
  testId?: string;
  onSelectOption?: (optionKey: string, justification: string) => void;
}

/**
 * ArbitrationTieBreakCard (`arbitration-tiebreak-card`, DESIGN.md, UX-DR6, Story 3.4).
 * Uses `--color-arbitration-amber` and `--color-arbitration-bg`.
 */
export function ArbitrationTieBreakCard({
  arbitrationId,
  stepKey,
  questionTitle,
  contextSummary,
  tieBreakPolicy,
  options,
  selectedOptionKey = null,
  readOnly = false,
  labels,
  testId,
  onSelectOption,
}: ArbitrationTieBreakCardProps) {
  const [justification, setJustification] = useState("");
  const [chosenKey, setChosenKey] = useState<string | null>(selectedOptionKey);

  const handleChoose = (optKey: string) => {
    if (readOnly) {
      return;
    }
    setChosenKey(optKey);
    onSelectOption?.(optKey, justification.trim());
  };

  return (
    <section
      data-testid={testId ?? `arbitration-tiebreak-card-${arbitrationId}`}
      data-step-key={stepKey}
      data-tie-break-policy={tieBreakPolicy}
      style={{
        backgroundColor: "var(--color-arbitration-bg)",
        border: "1px solid var(--color-arbitration-amber)",
        borderLeft: "4px solid var(--color-arbitration-amber)",
        borderRadius: "var(--radius-lg)",
        padding: "16px",
        display: "flex",
        flexDirection: "column",
        gap: "12px",
      }}
    >
      <header
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: "8px",
          flexWrap: "wrap",
        }}
      >
        <span
          style={{
            color: "var(--color-arbitration-amber)",
            fontWeight: 700,
            fontSize: "var(--font-size-mono)",
            fontFamily: "var(--font-mono)",
          }}
        >
          {labels.badgeTitle}
        </span>
        <span
          style={{
            color: "var(--color-muted-foreground)",
            fontSize: "var(--font-size-mono)",
            fontFamily: "var(--font-mono)",
          }}
        >
          {labels.policyPrefixLabel}: {tieBreakPolicy}
        </span>
      </header>

      <h3
        style={{
          margin: 0,
          fontFamily: "var(--font-display)",
          fontSize: "var(--font-size-display)",
          color: "var(--color-foreground)",
        }}
      >
        {questionTitle}
      </h3>

      {contextSummary && (
        <p style={{ margin: 0, color: "var(--color-muted-foreground)" }}>{contextSummary}</p>
      )}

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(240px, 1fr))",
          gap: "12px",
        }}
      >
        {options.map((opt) => {
          const isSelected = chosenKey === opt.optionKey;
          return (
            <div
              key={opt.optionKey}
              data-testid={`arbitration-option-${opt.optionKey}`}
              style={{
                backgroundColor: "var(--color-surface-card)",
                border: isSelected
                  ? "2px solid var(--color-arbitration-amber)"
                  : "1px solid var(--color-border)",
                borderRadius: "var(--radius-md)",
                padding: "12px",
                display: "flex",
                flexDirection: "column",
                gap: "8px",
              }}
            >
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  gap: "6px",
                }}
              >
                <strong style={{ color: "var(--color-foreground)" }}>{opt.title}</strong>
                {opt.recommended && (
                  <span
                    style={{
                      backgroundColor: "var(--color-arbitration-bg)",
                      color: "var(--color-arbitration-amber)",
                      fontFamily: "var(--font-mono)",
                      fontSize: "var(--font-size-mono)",
                      padding: "2px 6px",
                      borderRadius: "var(--radius-sm)",
                      fontWeight: 600,
                    }}
                  >
                    {labels.recommendedBadgeLabel}
                  </span>
                )}
              </div>

              <div style={{ fontSize: "var(--font-size-body)" }}>
                <strong>{labels.prosLabel}:</strong> {opt.pros.join(", ")}
              </div>
              <div style={{ fontSize: "var(--font-size-body)" }}>
                <strong>{labels.consLabel}:</strong> {opt.cons.join(", ")}
              </div>
              <div
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: "var(--font-size-mono)",
                  color: "var(--color-muted-foreground)",
                }}
              >
                {labels.siImpactLabel}: {opt.siImpact} | {labels.finopsImpactLabel}:{" "}
                {opt.finopsImpact}
              </div>

              {!readOnly && (
                <button
                  type="button"
                  data-testid={`arbitration-select-${opt.optionKey}`}
                  onClick={() => handleChoose(opt.optionKey)}
                  style={{
                    backgroundColor: "var(--color-arbitration-amber)",
                    color: "var(--color-primary-foreground)",
                    border: "none",
                    borderRadius: "var(--radius-sm)",
                    padding: "6px 10px",
                    fontWeight: 600,
                    cursor: "pointer",
                  }}
                >
                  {labels.selectOptionButtonLabel} ({opt.optionKey})
                </button>
              )}
            </div>
          );
        })}
      </div>

      {!readOnly && (
        <input
          type="text"
          data-testid={`arbitration-justification-${arbitrationId}`}
          aria-label={labels.justificationPlaceholder}
          placeholder={labels.justificationPlaceholder}
          value={justification}
          onChange={(e) => setJustification(e.target.value)}
          style={{
            width: "100%",
            padding: "8px",
            borderRadius: "var(--radius-sm)",
            border: "1px solid var(--color-arbitration-amber)",
            backgroundColor: "var(--color-surface-card)",
            color: "var(--color-foreground)",
            fontFamily: "var(--font-sans)",
            boxSizing: "border-box",
          }}
        />
      )}

      {chosenKey && (
        <div
          data-testid={`arbitration-resolved-banner-${arbitrationId}`}
          role="status"
          aria-live="polite"
          style={{
            backgroundColor: "var(--color-gate-emerald-bg)",
            color: "var(--color-gate-emerald)",
            padding: "8px 12px",
            borderRadius: "var(--radius-sm)",
            fontFamily: "var(--font-mono)",
            fontSize: "var(--font-size-mono)",
            fontWeight: 600,
          }}
        >
          {labels.resolvedBannerPrefix}: {chosenKey}
        </div>
      )}
    </section>
  );
}
