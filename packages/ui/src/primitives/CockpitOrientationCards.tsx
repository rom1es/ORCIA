import React from "react";
import { DisabledButtonAlertIndicator } from "../components/DisabledButtonAlertIndicator";
import type { EightFixedMenuKey } from "./FourZoneShellTypes";
import type { StreamlinedCockpitLabels } from "./StreamlinedCockpitView";

export interface CockpitOrientationCardsProps {
  readonly quickPrompt: string;
  readonly onChangeQuickPrompt: (value: string) => void;
  readonly labels: StreamlinedCockpitLabels;
  readonly disabledMenuKeys?: Partial<Record<EightFixedMenuKey, string>>;
  readonly onOpenAssistant?: (initialPrompt: string) => void;
  readonly onNavigateModule?: (moduleRoute: string) => void;
}

export function CockpitOrientationCards({
  quickPrompt,
  onChangeQuickPrompt,
  labels,
  disabledMenuKeys,
  onOpenAssistant,
  onNavigateModule,
}: CockpitOrientationCardsProps): React.ReactElement {
  const assistantDisabledReason = disabledMenuKeys?.assistant;
  const processesDisabledReason = disabledMenuKeys?.processes;
  const spacesDisabledReason = disabledMenuKeys?.spaces;

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
            disabled={Boolean(assistantDisabledReason)}
            title={assistantDisabledReason}
            onChange={(e) => onChangeQuickPrompt(e.target.value)}
            placeholder={labels.quickAssistantPlaceholder}
            className="min-w-0 flex-1 basis-48 rounded border px-3 py-1.5 text-xs disabled:opacity-50 disabled:cursor-not-allowed"
            style={{
              backgroundColor: "var(--color-bg-canvas)",
              borderColor: "var(--color-border-subtle)",
            }}
          />
          <button
            type="button"
            data-testid="cockpit-quick-assistant-submit"
            disabled={Boolean(assistantDisabledReason)}
            aria-disabled={assistantDisabledReason ? "true" : undefined}
            title={assistantDisabledReason}
            data-disabled-reason={assistantDisabledReason}
            onClick={() => {
              if (!assistantDisabledReason) {
                onOpenAssistant?.(quickPrompt);
              }
            }}
            className="inline-flex items-center gap-1.5 max-w-full rounded px-3 py-1.5 text-xs font-semibold disabled:opacity-50 disabled:cursor-not-allowed"
            style={{
              backgroundColor: "var(--color-action-primary)",
              color: "var(--color-bg-surface)",
            }}
          >
            <span>{labels.quickAssistantCta}</span>
            <DisabledButtonAlertIndicator
              disabled={Boolean(assistantDisabledReason)}
              reason={assistantDisabledReason}
              testIdSuffix="cockpit-quick-assistant-submit"
            />
          </button>
        </div>
      </div>

      <div
        className="grid grid-cols-1 gap-2.5 border-t pt-3 md:grid-cols-3"
        style={{ borderColor: "var(--color-border-subtle)" }}
      >
        <button
          type="button"
          data-testid="cockpit-orientation-card-assistant"
          disabled={Boolean(assistantDisabledReason)}
          aria-disabled={assistantDisabledReason ? "true" : undefined}
          title={assistantDisabledReason}
          data-disabled-reason={assistantDisabledReason}
          onClick={() => {
            if (!assistantDisabledReason) {
              onNavigateModule?.("/assistant");
            }
          }}
          className={`rounded border px-3 py-2.5 text-left transition-colors ${
            assistantDisabledReason ? "opacity-50 cursor-not-allowed" : ""
          }`}
          style={{
            backgroundColor: "var(--color-bg-elevated)",
            borderColor: "var(--color-border-subtle)",
          }}
        >
          <div className="flex items-center justify-between gap-2 text-xs font-semibold">
            <span>{labels.orientationAssistantTitle}</span>
            <DisabledButtonAlertIndicator
              disabled={Boolean(assistantDisabledReason)}
              reason={assistantDisabledReason}
              testIdSuffix="cockpit-orientation-card-assistant"
            />
          </div>
          <p className="mt-0.5 text-xs" style={{ color: "var(--color-text-secondary)" }}>
            {labels.orientationAssistantDesc}
          </p>
        </button>

        <button
          type="button"
          data-testid="cockpit-orientation-card-processes"
          disabled={Boolean(processesDisabledReason)}
          aria-disabled={processesDisabledReason ? "true" : undefined}
          title={processesDisabledReason}
          data-disabled-reason={processesDisabledReason}
          onClick={() => {
            if (!processesDisabledReason) {
              onNavigateModule?.("/processes");
            }
          }}
          className={`rounded border px-3 py-2.5 text-left transition-colors ${
            processesDisabledReason ? "opacity-50 cursor-not-allowed" : ""
          }`}
          style={{
            backgroundColor: "var(--color-bg-elevated)",
            borderColor: "var(--color-border-subtle)",
          }}
        >
          <div className="flex items-center justify-between gap-2 text-xs font-semibold">
            <span>{labels.orientationProcessesTitle}</span>
            <DisabledButtonAlertIndicator
              disabled={Boolean(processesDisabledReason)}
              reason={processesDisabledReason}
              testIdSuffix="cockpit-orientation-card-processes"
            />
          </div>
          <p className="mt-0.5 text-xs" style={{ color: "var(--color-text-secondary)" }}>
            {labels.orientationProcessesDesc}
          </p>
        </button>

        <button
          type="button"
          data-testid="cockpit-orientation-card-spaces"
          disabled={Boolean(spacesDisabledReason)}
          aria-disabled={spacesDisabledReason ? "true" : undefined}
          title={spacesDisabledReason}
          data-disabled-reason={spacesDisabledReason}
          onClick={() => {
            if (!spacesDisabledReason) {
              onNavigateModule?.("/spaces");
            }
          }}
          className={`rounded border px-3 py-2.5 text-left transition-colors ${
            spacesDisabledReason ? "opacity-50 cursor-not-allowed" : ""
          }`}
          style={{
            backgroundColor: "var(--color-bg-elevated)",
            borderColor: "var(--color-border-subtle)",
          }}
        >
          <div className="flex items-center justify-between gap-2 text-xs font-semibold">
            <span>{labels.orientationSpacesTitle}</span>
            <DisabledButtonAlertIndicator
              disabled={Boolean(spacesDisabledReason)}
              reason={spacesDisabledReason}
              testIdSuffix="cockpit-orientation-card-spaces"
            />
          </div>
          <p className="mt-0.5 text-xs" style={{ color: "var(--color-text-secondary)" }}>
            {labels.orientationSpacesDesc}
          </p>
        </button>
      </div>
    </div>
  );
}
