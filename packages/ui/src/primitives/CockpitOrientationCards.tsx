import React from "react";
import type { StreamlinedCockpitLabels } from "./StreamlinedCockpitView";

export interface CockpitOrientationCardsProps {
  readonly quickPrompt: string;
  readonly onChangeQuickPrompt: (value: string) => void;
  readonly labels: StreamlinedCockpitLabels;
  readonly onOpenAssistant?: (initialPrompt: string) => void;
  readonly onNavigateModule?: (moduleRoute: string) => void;
}

export function CockpitOrientationCards({
  quickPrompt,
  onChangeQuickPrompt,
  labels,
  onOpenAssistant,
  onNavigateModule,
}: CockpitOrientationCardsProps): React.ReactElement {
  return (
    <div
      data-testid="cockpit-calm-orientation-panel"
      className="flex flex-col gap-3 rounded-lg border p-4"
      style={{
        backgroundColor: "var(--color-bg-surface)",
        borderColor: "var(--color-border-subtle)",
      }}
    >
      <div
        data-testid="cockpit-zero-decisions-banner"
        className="flex items-center justify-between border-b pb-2.5 text-sm font-semibold"
        style={{
          borderColor: "var(--color-border-subtle)",
          color: "var(--color-state-verified)",
        }}
      >
        {labels.zeroDecisionsBanner}
      </div>

      <div
        data-testid="cockpit-quick-assistant-box"
        className="flex flex-col gap-1.5"
      >
        <h3 className="text-xs font-semibold">{labels.quickAssistantTitle}</h3>
        <div className="flex flex-wrap gap-2">
          <input
            type="text"
            autoComplete="off"
            data-lpignore="true"
            data-1p-ignore="true"
            data-bwignore="true"
            data-form-type="other"
            data-testid="cockpit-quick-assistant-input"
            value={quickPrompt}
            onChange={(e) => onChangeQuickPrompt(e.target.value)}
            placeholder={labels.quickAssistantPlaceholder}
            className="min-w-0 flex-1 basis-48 rounded border px-3 py-1.5 text-xs"
            style={{
              backgroundColor: "var(--color-bg-canvas)",
              borderColor: "var(--color-border-subtle)",
            }}
          />
          <button
            type="button"
            data-testid="cockpit-quick-assistant-submit"
            onClick={() => onOpenAssistant?.(quickPrompt)}
            className="max-w-full rounded px-3 py-1.5 text-xs font-semibold"
            style={{
              backgroundColor: "var(--color-action-primary)",
              color: "var(--color-bg-surface)",
            }}
          >
            {labels.quickAssistantCta}
          </button>
        </div>
      </div>

      <div className="grid grid-cols-1 gap-2.5 border-t pt-3 md:grid-cols-3" style={{ borderColor: "var(--color-border-subtle)" }}>
        <button
          type="button"
          data-testid="cockpit-orientation-card-assistant"
          onClick={() => onNavigateModule?.("/assistant")}
          className="rounded border px-3 py-2.5 text-left transition-colors"
          style={{
            backgroundColor: "var(--color-bg-elevated)",
            borderColor: "var(--color-border-subtle)",
          }}
        >
          <div className="text-xs font-semibold">{labels.orientationAssistantTitle}</div>
          <p className="mt-0.5 text-xs" style={{ color: "var(--color-text-secondary)" }}>
            {labels.orientationAssistantDesc}
          </p>
        </button>

        <button
          type="button"
          data-testid="cockpit-orientation-card-processes"
          onClick={() => onNavigateModule?.("/processes")}
          className="rounded border px-3 py-2.5 text-left transition-colors"
          style={{
            backgroundColor: "var(--color-bg-elevated)",
            borderColor: "var(--color-border-subtle)",
          }}
        >
          <div className="text-xs font-semibold">{labels.orientationProcessesTitle}</div>
          <p className="mt-0.5 text-xs" style={{ color: "var(--color-text-secondary)" }}>
            {labels.orientationProcessesDesc}
          </p>
        </button>

        <button
          type="button"
          data-testid="cockpit-orientation-card-spaces"
          onClick={() => onNavigateModule?.("/spaces")}
          className="rounded border px-3 py-2.5 text-left transition-colors"
          style={{
            backgroundColor: "var(--color-bg-elevated)",
            borderColor: "var(--color-border-subtle)",
          }}
        >
          <div className="text-xs font-semibold">{labels.orientationSpacesTitle}</div>
          <p className="mt-0.5 text-xs" style={{ color: "var(--color-text-secondary)" }}>
            {labels.orientationSpacesDesc}
          </p>
        </button>
      </div>
    </div>
  );
}
