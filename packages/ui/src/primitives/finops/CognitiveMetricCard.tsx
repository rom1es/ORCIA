import React from "react";

export type MetricTone = "emerald" | "amber" | "crimson" | "cobalt";

export interface CognitiveMetricCardProps {
  readonly title: string;
  readonly valueFormatted: string;
  readonly percentage: number; // 0 to 100 for gauge fill
  readonly targetLabel: string;
  readonly statusLabel: string;
  readonly tone: MetricTone;
  readonly testId: string;
  readonly subtitle?: string;
}

export function CognitiveMetricCard({
  title,
  valueFormatted,
  percentage,
  targetLabel,
  statusLabel,
  tone,
  testId,
  subtitle,
}: CognitiveMetricCardProps): React.ReactElement {
  // Pure semantic token lookups - zero raw hex, strictly defined in tokens.css
  const toneColorVar =
    tone === "crimson"
      ? "var(--color-stale-crimson)"
      : tone === "amber"
        ? "var(--color-arbitration-amber)"
        : tone === "emerald"
          ? "var(--color-gate-emerald)"
          : "var(--color-primary-cobalt)";

  const clampedPct = Math.max(0, Math.min(100, percentage));

  return (
    <div
      className="orcia-bento-card"
      data-testid={testId}
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "12px",
        padding: "18px 20px",
        borderRadius: "8px",
        background: "var(--color-surface-card)",
        border: "1px solid var(--color-border-subtle)",
        minWidth: "240px",
        flex: "1 1 240px",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
        <span
          style={{
            fontSize: "12px",
            fontWeight: 600,
            textTransform: "uppercase",
            letterSpacing: "0.04em",
            color: "var(--color-text-muted)",
          }}
        >
          {title}
        </span>
        <span
          data-testid={`${testId}-status`}
          style={{
            fontSize: "11px",
            fontWeight: 600,
            padding: "2px 8px",
            borderRadius: "4px",
            color: toneColorVar,
            background: "var(--color-surface-muted)",
            border: "1px solid var(--color-border-subtle)",
          }}
        >
          {statusLabel}
        </span>
      </div>

      <div style={{ display: "flex", alignItems: "baseline", gap: "8px" }}>
        <span
          data-testid={`${testId}-value`}
          style={{
            fontSize: "26px",
            fontWeight: 700,
            color: "var(--color-text-primary)",
            lineHeight: 1.1,
          }}
        >
          {valueFormatted}
        </span>
        <span
          style={{
            fontSize: "12px",
            color: "var(--color-text-muted)",
          }}
        >
          {targetLabel}
        </span>
      </div>

      {/* Visual gauge bar */}
      <div
        style={{
          width: "100%",
          height: "6px",
          borderRadius: "3px",
          background: "var(--color-surface-muted)",
          overflow: "hidden",
        }}
      >
        <div
          data-testid={`${testId}-gauge`}
          style={{
            width: `${clampedPct}%`,
            height: "100%",
            borderRadius: "3px",
            background: toneColorVar,
            transition: "width 0.3s ease",
          }}
        />
      </div>

      {subtitle && (
        <span
          style={{
            fontSize: "11px",
            color: "var(--color-text-muted)",
            lineHeight: 1.4,
          }}
        >
          {subtitle}
        </span>
      )}
    </div>
  );
}
