import React from "react";
import { DisabledButtonAlertIndicator } from "../components/DisabledButtonAlertIndicator";
import type { EightFixedMenuKey } from "./FourZoneShellTypes";
import type { StreamlinedCockpitLabels } from "./StreamlinedCockpitView";

export interface CockpitOrientationCardsProps {
  readonly labels: StreamlinedCockpitLabels;
  readonly disabledMenuKeys?: Partial<Record<EightFixedMenuKey, string>>;
  readonly onNavigateModule?: (moduleRoute: string) => void;
}

export function CockpitOrientationCards({
  labels,
  disabledMenuKeys,
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
      <div className="grid grid-cols-1 gap-2.5 md:grid-cols-3">
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
