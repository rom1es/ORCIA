import React from "react";
import { DisabledButtonAlertIndicator } from "../components/DisabledButtonAlertIndicator";

export interface UiTestBenchStepItem {
  readonly stepNumber: 1 | 2 | 3 | 4;
  readonly stepCode:
    | "1_NETWORK_TLS_ANTI_SSRF"
    | "2_AUTHENTICATION"
    | "3_CONTRACT_DISCOVERY"
    | "4_HOT_DRY_RUN";
  readonly status:
    | "PASS"
    | "FAIL"
    | "WAITING_USER_PASSTHROUGH_TOKEN"
    | "SKIPPED";
  readonly detailFr: string;
}

export interface UiDiscoveredCapabilityItem {
  readonly toolName: string;
  readonly qualification: "READ_ONLY" | "WRITE_STAGED_REQUIRED";
  readonly badgeFr: string;
}

export interface RemoteServiceTestBenchLabels {
  readonly heading: string;
  readonly testAndDiscoverCta: string;
  readonly activateConnectorCta: string;
  readonly testWithPersonalTokenCta: string;
  readonly mcpExposureHeading: string;
  readonly exposeMcpToggleLabel: string;
  readonly mcpIdeBadge: string;
  readonly ipProtectionNotice: string;
}

export interface RemoteServiceTestBenchAndMcpExposureViewProps {
  readonly endpointUrl: string;
  readonly steps: readonly UiTestBenchStepItem[];
  readonly discoveredCapabilities: readonly UiDiscoveredCapabilityItem[];
  readonly canActivate: boolean;
  readonly mcpExposed: boolean;
  readonly exposedToolNames: readonly string[];
  readonly labels: RemoteServiceTestBenchLabels;
  readonly onRunTestBench?: () => void;
  readonly onActivateService?: () => void;
  readonly onToggleMcpExposure?: (nextExposed: boolean) => void;
}

export const RemoteServiceTestBenchAndMcpExposureView: React.FC<
  RemoteServiceTestBenchAndMcpExposureViewProps
> = ({
  endpointUrl,
  steps,
  discoveredCapabilities,
  canActivate,
  mcpExposed,
  exposedToolNames,
  labels,
  onRunTestBench,
  onActivateService,
  onToggleMcpExposure,
}) => {
  return (
    <section
      aria-label={labels.heading}
      data-testid="remote-service-test-bench"
      className="space-y-4 rounded-lg border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] p-4 text-[var(--orcia-text-primary)]"
    >
      <header className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--orcia-border-subtle)] pb-3">
        <div>
          <h2 className="text-base font-semibold">{labels.heading}</h2>
          <code className="font-mono text-xs text-[var(--orcia-text-secondary)]">
            {endpointUrl}
          </code>
        </div>
        <div className="flex flex-wrap gap-2">
          {onRunTestBench && (
            <button
              type="button"
              data-testid="run-test-bench-btn"
              onClick={onRunTestBench}
              className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] px-3 py-1.5 text-xs font-medium"
            >
              {labels.testAndDiscoverCta}
            </button>
          )}
          <button
            type="button"
            disabled={!canActivate}
            data-testid="activate-remote-service-btn"
            onClick={onActivateService}
            className="inline-flex items-center gap-1.5 rounded bg-[var(--orcia-action-primary)] px-3 py-1.5 text-xs font-medium text-[var(--orcia-text-on-action)] disabled:opacity-50"
          >
            <span>{labels.activateConnectorCta}</span>
            <DisabledButtonAlertIndicator
              disabled={!canActivate}
              reason="Validez les 4 étapes du banc d'essai pour activer ce connecteur."
              testIdSuffix="activate-remote-service-btn"
            />
          </button>
        </div>
      </header>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div className="space-y-2">
          <ol className="space-y-2">
            {steps.map((step) => (
              <li
                key={step.stepCode}
                data-testid={`test-bench-step-${step.stepNumber}`}
                className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] p-2.5 text-xs"
              >
                <div className="flex items-center justify-between font-mono">
                  <span>
                    {step.stepNumber}. {step.stepCode}
                  </span>
                  <span data-testid={`test-bench-status-${step.stepNumber}`}>
                    {step.status}
                  </span>
                </div>
                <p className="mt-1 text-[11px] text-[var(--orcia-text-secondary)]">
                  {step.detailFr}
                </p>
              </li>
            ))}
          </ol>

          <ul className="space-y-1.5 pt-1">
            {discoveredCapabilities.map((cap) => (
              <li
                key={cap.toolName}
                data-testid={`discovered-tool-${cap.toolName}`}
                className="flex items-center justify-between rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] px-2.5 py-1.5 text-xs"
              >
                <code className="font-mono">{cap.toolName}</code>
                <span>{cap.badgeFr}</span>
              </li>
            ))}
          </ul>
        </div>

        <div
          data-testid="governed-mcp-exposure-panel"
          className="space-y-3 rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] p-3"
        >
          <div className="flex items-center justify-between">
            <h3 className="text-xs font-semibold uppercase tracking-wide text-[var(--orcia-text-secondary)]">
              {labels.mcpExposureHeading}
            </h3>
            <span className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2 py-0.5 text-[11px]">
              {labels.mcpIdeBadge}
            </span>
          </div>
          <label className="inline-flex items-center gap-2 text-xs font-medium">
            <input
              type="checkbox"
              autoComplete="off"
              data-lpignore="true"
              data-1p-ignore="true"
              data-bwignore="true"
              data-form-type="other"
              checked={mcpExposed}
              data-testid="toggle-mcp-exposure-checkbox"
              onChange={(e) => onToggleMcpExposure?.(e.target.checked)}
            />
            <span>{labels.exposeMcpToggleLabel}</span>
          </label>
          <p className="text-[11px] text-[var(--orcia-text-secondary)]">
            {labels.ipProtectionNotice}
          </p>
          <div className="flex flex-wrap gap-1.5">
            {exposedToolNames.map((t) => (
              <code
                key={t}
                data-testid={`exposed-mcp-tool-${t}`}
                className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2 py-0.5 font-mono text-[11px]"
              >
                {t}
              </code>
            ))}
          </div>
        </div>
      </div>
    </section>
  );
};
