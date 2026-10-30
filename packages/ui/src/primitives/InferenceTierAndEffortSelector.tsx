export type UiInferenceTier = "simple" | "medium" | "complex" | "auto";
export type UiInferenceEffort = "default" | "fast" | "balanced" | "deep";

export interface InferenceTierAndEffortLabels {
  readonly tierLabel: string;
  readonly effortLabel: string;
  readonly simpleBadge: string;
  readonly mediumBadge: string;
  readonly complexBadge: string;
  readonly autoBadge: string;
  readonly effortDefault: string;
  readonly effortFast: string;
  readonly effortBalanced: string;
  readonly effortDeep: string;
}

export interface InferenceTierBadgeProps {
  readonly tier: UiInferenceTier;
  readonly effort?: UiInferenceEffort;
  readonly labels: InferenceTierAndEffortLabels;
}

export function InferenceTierBadge({ tier, effort, labels }: InferenceTierBadgeProps) {
  const tierCopy: Record<UiInferenceTier, string> = {
    simple: labels.simpleBadge,
    medium: labels.mediumBadge,
    complex: labels.complexBadge,
    auto: labels.autoBadge,
  };
  const effortCopy: Record<UiInferenceEffort, string> = {
    default: labels.effortDefault,
    fast: labels.effortFast,
    balanced: labels.effortBalanced,
    deep: labels.effortDeep,
  };

  return (
    <span
      data-testid={`inference-tier-badge-${tier}`}
      style={{
        display: "inline-flex",
        alignItems: "center",
        gap: "0.375rem",
        padding: "0.1875rem 0.5rem",
        borderRadius: "var(--radius-sm)",
        border: "1px solid var(--color-border-subtle)",
        backgroundColor: "var(--color-surface-canvas)",
        fontSize: "0.75rem",
        fontWeight: 600,
        color: "var(--color-text-primary)",
      }}
    >
      <span>{tierCopy[tier]}</span>
      {effort ? (
        <span data-testid={`inference-effort-badge-${effort}`}>• {effortCopy[effort]}</span>
      ) : null}
    </span>
  );
}

export interface EffortSelectorProps {
  readonly selectedTier: UiInferenceTier;
  readonly selectedEffort: UiInferenceEffort;
  readonly labels: InferenceTierAndEffortLabels;
  readonly disabled?: boolean;
  readonly onTierChange: (tier: UiInferenceTier) => void;
  readonly onEffortChange: (effort: UiInferenceEffort) => void;
}

export function EffortSelector({
  selectedTier,
  selectedEffort,
  labels,
  disabled = false,
  onTierChange,
  onEffortChange,
}: EffortSelectorProps) {
  return (
    <div
      data-testid="cognitive-tier-effort-selector"
      style={{ display: "inline-flex", alignItems: "center", gap: "0.75rem", flexWrap: "wrap" }}
    >
      <label style={{ display: "inline-flex", alignItems: "center", gap: "0.375rem" }}>
        <span style={{ fontSize: "0.8125rem", fontWeight: 600 }}>{labels.tierLabel}</span>
        <select
          data-testid="select-inference-tier"
          value={selectedTier}
          disabled={disabled}
          onChange={(e) => onTierChange(e.target.value as UiInferenceTier)}
          style={{
            minHeight: "36px",
            padding: "0.25rem 0.5rem",
            borderRadius: "var(--radius-sm)",
            border: "1px solid var(--color-border-strong)",
          }}
        >
          <option value="simple">{labels.simpleBadge}</option>
          <option value="medium">{labels.mediumBadge}</option>
          <option value="complex">{labels.complexBadge}</option>
          <option value="auto">{labels.autoBadge}</option>
        </select>
      </label>

      <label style={{ display: "inline-flex", alignItems: "center", gap: "0.375rem" }}>
        <span style={{ fontSize: "0.8125rem", fontWeight: 600 }}>{labels.effortLabel}</span>
        <select
          data-testid="select-inference-effort"
          value={selectedEffort}
          disabled={disabled}
          onChange={(e) => onEffortChange(e.target.value as UiInferenceEffort)}
          style={{
            minHeight: "36px",
            padding: "0.25rem 0.5rem",
            borderRadius: "var(--radius-sm)",
            border: "1px solid var(--color-border-strong)",
          }}
        >
          <option value="default">{labels.effortDefault}</option>
          <option value="fast">{labels.effortFast}</option>
          <option value="balanced">{labels.effortBalanced}</option>
          <option value="deep">{labels.effortDeep}</option>
        </select>
      </label>
    </div>
  );
}
