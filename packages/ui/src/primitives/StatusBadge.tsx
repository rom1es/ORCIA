import React from "react";

export type StatusBadgeTone =
  | "cobalt"
  | "amber"
  | "emerald"
  | "cyan"
  | "crimson"
  | "neutral";

export interface StatusBadgeProps {
  label: string;
  tone?: StatusBadgeTone;
  monospace?: boolean;
  pill?: boolean;
  testId?: string;
}

const TONE_STYLES: Record<StatusBadgeTone, React.CSSProperties> = {
  cobalt: {
    backgroundColor: "var(--color-primary-cobalt)",
    color: "var(--color-primary-foreground)",
    border: "1px solid var(--color-primary-cobalt)",
  },
  amber: {
    backgroundColor: "var(--color-arbitration-bg)",
    color: "var(--color-arbitration-amber)",
    border: "1px solid var(--color-arbitration-amber)",
  },
  emerald: {
    backgroundColor: "var(--color-gate-emerald-bg)",
    color: "var(--color-gate-emerald)",
    border: "1px solid var(--color-gate-emerald)",
  },
  cyan: {
    backgroundColor: "var(--color-ontology-bg)",
    color: "var(--color-ontology-cyan)",
    border: "1px solid var(--color-ontology-cyan)",
  },
  crimson: {
    backgroundColor: "var(--color-stale-bg)",
    color: "var(--color-stale-crimson)",
    border: "1px solid var(--color-stale-crimson)",
  },
  neutral: {
    backgroundColor: "var(--color-dock-bg)",
    color: "var(--color-muted-foreground)",
    border: "1px solid var(--color-border)",
  },
};

export function StatusBadge({
  label,
  tone = "neutral",
  monospace = false,
  pill = false,
  testId,
}: StatusBadgeProps) {
  const toneStyle = TONE_STYLES[tone];
  return (
    <span
      data-testid={testId}
      data-tone={tone}
      style={{
        display: "inline-flex",
        alignItems: "center",
        padding: "2px 8px",
        fontSize: "var(--font-size-mono)",
        fontFamily: monospace ? "var(--font-mono)" : "var(--font-sans)",
        borderRadius: pill ? "var(--radius-full)" : "var(--radius-sm)",
        fontWeight: 600,
        ...toneStyle,
      }}
    >
      {label}
    </span>
  );
}
