import React, { useState } from "react";

export type CognitiveTierChoice =
  | "TIER_1_FAST"
  | "TIER_2_STANDARD"
  | "TIER_3_DEEP";

export interface ScopedRagSourceOption {
  readonly sourceUri: string;
  readonly alias: string;
  readonly authorized: boolean;
}

export interface ScopedPromptBoxLabels {
  readonly boxTitle: string;
  readonly promptPlaceholder: string;
  readonly ragScopeLabel: string;
  readonly cognitiveTierLabel: string;
  readonly tier1Label: string;
  readonly tier2Label: string;
  readonly tier3Label: string;
  readonly submitCta: string;
}

export interface ScopedPromptBoxProps {
  readonly availableSources: readonly ScopedRagSourceOption[];
  readonly labels: ScopedPromptBoxLabels;
  readonly onSubmitScopedPrompt?: (payload: {
    prompt: string;
    selectedSourceUris: readonly string[];
    cognitiveTier: CognitiveTierChoice;
  }) => void;
}

export function ScopedPromptBox({
  availableSources,
  labels,
  onSubmitScopedPrompt,
}: ScopedPromptBoxProps) {
  const authorizedInitial = availableSources
    .filter((s) => s.authorized)
    .map((s) => s.sourceUri);
  const [selectedSources, setSelectedSources] =
    useState<readonly string[]>(authorizedInitial);
  const [tier, setTier] = useState<CognitiveTierChoice>("TIER_2_STANDARD");
  const [prompt, setPrompt] = useState("");

  const toggleSource = (uri: string) => {
    setSelectedSources((prev) =>
      prev.includes(uri) ? prev.filter((item) => item !== uri) : [...prev, uri],
    );
  };

  return (
    <section
      data-testid="scoped-prompt-box"
      style={{
        padding: "16px",
        borderRadius: "10px",
        border: "1px solid var(--orcia-border-subtle)",
        backgroundColor: "var(--orcia-surface-elevated)",
        display: "flex",
        flexDirection: "column",
        gap: "12px",
      }}
    >
      <strong style={{ fontSize: "0.9375rem" }}>💬 {labels.boxTitle}</strong>

      <div>
        <span
          style={{
            fontSize: "0.75rem",
            fontWeight: 600,
            color: "var(--orcia-text-secondary)",
          }}
        >
          {labels.ragScopeLabel} :
        </span>
        <div
          style={{
            display: "flex",
            gap: "6px",
            flexWrap: "wrap",
            marginTop: "6px",
          }}
        >
          {availableSources.map((src) => {
            const active = selectedSources.includes(src.sourceUri);
            return (
              <button
                key={src.sourceUri}
                type="button"
                disabled={!src.authorized}
                aria-pressed={active}
                data-testid={`rag-source-toggle-${src.alias}`}
                onClick={() => toggleSource(src.sourceUri)}
                style={{
                  padding: "3px 8px",
                  borderRadius: "9999px",
                  fontSize: "0.75rem",
                  fontFamily: "var(--orcia-font-mono)",
                  cursor: src.authorized ? "pointer" : "not-allowed",
                  border: active
                    ? "1px solid var(--orcia-action-primary)"
                    : "1px solid var(--orcia-border-subtle)",
                  backgroundColor: active
                    ? "var(--orcia-surface-secondary)"
                    : "var(--orcia-surface-primary)",
                  color: "var(--orcia-text-primary)",
                }}
              >
                {src.alias} ({src.sourceUri})
              </button>
            );
          })}
        </div>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
        <label
          htmlFor="scoped-cognitive-tier-select"
          style={{ fontSize: "0.75rem", fontWeight: 600 }}
        >
          {labels.cognitiveTierLabel} :
        </label>
        <select
          id="scoped-cognitive-tier-select"
          data-testid="scoped-cognitive-tier-select"
          value={tier}
          onChange={(e) => setTier(e.target.value as CognitiveTierChoice)}
          style={{
            padding: "4px 8px",
            borderRadius: "6px",
            fontSize: "0.75rem",
            border: "1px solid var(--orcia-border-subtle)",
            backgroundColor: "var(--orcia-surface-primary)",
            color: "var(--orcia-text-primary)",
          }}
        >
          <option value="TIER_1_FAST">{labels.tier1Label}</option>
          <option value="TIER_2_STANDARD">{labels.tier2Label}</option>
          <option value="TIER_3_DEEP">{labels.tier3Label}</option>
        </select>
      </div>

      <div style={{ display: "flex", gap: "8px" }}>
        <input
          type="text"
          autoComplete="off"
          data-lpignore="true"
          data-1p-ignore="true"
          data-bwignore="true"
          data-form-type="other"
          data-testid="scoped-prompt-input"
          value={prompt}
          onChange={(e) => setPrompt(e.target.value)}
          placeholder={labels.promptPlaceholder}
          style={{
            flex: 1,
            padding: "8px 12px",
            borderRadius: "8px",
            border: "1px solid var(--orcia-border-subtle)",
            backgroundColor: "var(--orcia-surface-primary)",
            color: "var(--orcia-text-primary)",
            fontSize: "0.875rem",
          }}
        />
        <button
          type="button"
          data-testid="scoped-prompt-submit"
          onClick={() =>
            onSubmitScopedPrompt?.({
              prompt,
              selectedSourceUris: selectedSources,
              cognitiveTier: tier,
            })
          }
          style={{
            padding: "8px 14px",
            borderRadius: "8px",
            fontSize: "0.8125rem",
            fontWeight: 600,
            cursor: "pointer",
            border: "1px solid var(--orcia-action-primary)",
            backgroundColor: "var(--orcia-surface-secondary)",
            color: "var(--orcia-text-primary)",
          }}
        >
          {labels.submitCta}
        </button>
      </div>
    </section>
  );
}
