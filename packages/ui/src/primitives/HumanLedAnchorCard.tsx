import React from "react";

export interface HumanLedAnchorCardLabels {
  badgeTitle: string;
  authorLabel: string;
  placeholderText: string;
  submitLabel: string;
}

export interface HumanLedAnchorCardProps {
  sectionKey: string;
  sectionTitle: string;
  authorName: string;
  value: string;
  readOnly?: boolean;
  labels: HumanLedAnchorCardLabels;
  onChange?: (nextValue: string) => void;
  onSignAnchor?: (sectionKey: string, content: string) => void;
}

/**
 * HumanLedAnchorCard — Exclusive consumer of `--color-human-led-violet` (DESIGN.md, AD-3).
 * Represents a mandatory human-authored section (`human_authored_required: true`).
 * Never renders an AI auto-generation button.
 */
export function HumanLedAnchorCard({
  sectionKey,
  sectionTitle,
  authorName,
  value,
  readOnly = false,
  labels,
  onChange,
  onSignAnchor,
}: HumanLedAnchorCardProps) {
  return (
    <section
      data-testid={`human-anchor-card-${sectionKey}`}
      data-human-authored-required="true"
      style={{
        backgroundColor: "var(--color-human-led-bg)",
        border: "1px solid var(--color-human-led-violet)",
        borderLeft: "4px solid var(--color-human-led-violet)",
        borderRadius: "var(--radius-md)",
        padding: "16px",
        display: "flex",
        flexDirection: "column",
        gap: "10px",
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
            color: "var(--color-human-led-violet)",
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
          }}
        >
          {labels.authorLabel}: {authorName}
        </span>
      </header>

      <h3
        style={{
          margin: 0,
          fontFamily: "var(--font-serif)",
          fontSize: "var(--font-size-display)",
          color: "var(--color-foreground)",
        }}
      >
        {sectionTitle}
      </h3>

      <textarea
        aria-label={sectionTitle}
        value={value}
        disabled={readOnly}
        placeholder={labels.placeholderText}
        onChange={(e) => onChange?.(e.target.value)}
        style={{
          width: "100%",
          minHeight: "84px",
          padding: "8px",
          borderRadius: "var(--radius-sm)",
          border: "1px solid var(--color-human-led-violet)",
          backgroundColor: "var(--color-surface-card)",
          color: "var(--color-foreground)",
          fontFamily: "var(--font-sans)",
          boxSizing: "border-box",
        }}
      />

      {!readOnly && (
        <div>
          <button
            type="button"
            onClick={() => onSignAnchor?.(sectionKey, value)}
            style={{
              backgroundColor: "var(--color-human-led-violet)",
              color: "var(--color-primary-foreground)",
              border: "none",
              borderRadius: "var(--radius-sm)",
              padding: "6px 12px",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            {labels.submitLabel}
          </button>
        </div>
      )}
    </section>
  );
}
