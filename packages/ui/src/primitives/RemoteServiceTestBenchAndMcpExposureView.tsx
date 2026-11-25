import React from "react";
import { DisabledButtonAlertIndicator } from "../components/DisabledButtonAlertIndicator";
import { OrciaDataCard } from "./OrciaDataCard";
import { OrciaSpinner } from "./OrciaSpinner";

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
  readonly testingInProgressCta: string;
  readonly testingInProgressNotice: string;
  readonly activateConnectorCta: string;
  readonly activateDisabledReason: string;
  readonly testWithPersonalTokenCta: string;
  readonly mcpExposureHeading: string;
  readonly exposeMcpToggleLabel: string;
  readonly mcpIdeBadge: string;
  readonly ipProtectionNotice: string;
  readonly exposedCapabilityLabels?: Readonly<Record<string, string>>;
  readonly exposedAgentCapabilityPrefix?: string;
  readonly stepLabels: Readonly<Record<UiTestBenchStepItem["stepCode"], string>>;
  readonly statusLabels: Readonly<Record<UiTestBenchStepItem["status"], string>>;
}

export interface RemoteServiceTestBenchAndMcpExposureViewProps {
  readonly endpointUrl: string;
  readonly steps: readonly UiTestBenchStepItem[];
  readonly discoveredCapabilities: readonly UiDiscoveredCapabilityItem[];
  readonly canActivate: boolean;
  readonly mcpExposed: boolean;
  readonly exposedToolNames: readonly string[];
  readonly labels: RemoteServiceTestBenchLabels;
  readonly isTesting?: boolean;
  readonly isSavingMcp?: boolean;
  readonly onRunTestBench?: () => void;
  readonly onActivateService?: () => void;
  readonly onToggleMcpExposure?: (nextExposed: boolean) => void;
}

function formatReadableCapability(
  toolName: string,
  labels: RemoteServiceTestBenchLabels,
): string {
  const mapped = labels.exposedCapabilityLabels?.[toolName];
  if (mapped) return mapped;
  if (toolName.startsWith("agent.") && labels.exposedAgentCapabilityPrefix) {
    return `${labels.exposedAgentCapabilityPrefix} ${toolName.slice("agent.".length)}`;
  }
  return toolName;
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
  isTesting = false,
  isSavingMcp = false,
  onRunTestBench,
  onActivateService,
  onToggleMcpExposure,
}) => {
  const stepLabelMap = labels.stepLabels;
  const statusLabelMap = labels.statusLabels;

  return (
    <section
      aria-label={labels.heading}
      data-testid="remote-service-test-bench"
      className="orcia-ds-page text-[var(--orcia-text-primary)]"
    >
      <OrciaDataCard
        testId="outbound-mcp-server-card"
        icon="plug"
        title={labels.heading}
        subtitle={endpointUrl || undefined}
        actions={
          <div className="flex flex-wrap gap-2">
            {onRunTestBench && (
              <button
                type="button"
                disabled={isTesting}
                data-testid="run-test-bench-btn"
                onClick={onRunTestBench}
                className="orcia-ds-btn orcia-ds-btn-secondary orcia-ds-btn-sm"
              >
                {isTesting && <OrciaSpinner size="xs" />}
                <span>
                  {isTesting
                    ? labels.testingInProgressCta
                    : labels.testAndDiscoverCta}
                </span>
              </button>
            )}
            <button
              type="button"
              disabled={!canActivate || isTesting || isSavingMcp}
              data-testid="activate-remote-service-btn"
              onClick={onActivateService}
              className="orcia-ds-btn orcia-ds-btn-cobalt-outline orcia-ds-btn-sm"
            >
              <span>{labels.activateConnectorCta}</span>
              <DisabledButtonAlertIndicator
                disabled={!canActivate || isTesting || isSavingMcp}
                reason={labels.activateDisabledReason}
                testIdSuffix="activate-remote-service-btn"
              />
            </button>
          </div>
        }
      >
        {isTesting && (
          <div
            role="status"
            data-testid="test-bench-loading-banner"
            className="flex items-center gap-2 rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] px-3 py-2 text-xs font-medium text-[var(--orcia-text-secondary)]"
          >
            <OrciaSpinner size="xs" />
            <span>{labels.testingInProgressNotice}</span>
          </div>
        )}

        {(steps.length > 0 || discoveredCapabilities.length > 0) && (
          <div className="space-y-2">
            <ol className="space-y-2">
              {steps.map((step) => {
                const readableStep = stepLabelMap[step.stepCode] ?? step.stepCode;
                const readableStatus = statusLabelMap[step.status] ?? step.status;
                return (
                  <li
                    key={step.stepCode}
                    data-testid={`test-bench-step-${step.stepNumber}`}
                    data-step-code={step.stepCode}
                    className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] p-2.5 text-xs"
                  >
                    <div className="flex items-center justify-between gap-2">
                      <span className="font-medium">
                        {step.stepNumber}. {readableStep}
                      </span>
                      <span className="inline-flex items-center gap-1.5">
                        <span className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2 py-0.5 text-[11px] font-semibold">
                          {readableStatus}
                        </span>
                        <span
                          data-testid={`test-bench-status-${step.stepNumber}`}
                          data-status={step.status}
                          className="sr-only"
                        >
                          {step.status}
                        </span>
                      </span>
                    </div>
                    <p className="mt-1 text-[11px] text-[var(--orcia-text-secondary)]">
                      {step.detailFr}
                    </p>
                  </li>
                );
              })}
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
        )}
      </OrciaDataCard>

      <OrciaDataCard
        testId="governed-mcp-exposure-panel"
        icon="desktop"
        title={labels.mcpExposureHeading}
        metaBadge={
          <span className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] px-2 py-0.5 text-[11px]">
            {labels.mcpIdeBadge}
          </span>
        }
      >
        <label className="inline-flex items-center gap-2 text-xs font-medium">
          <input
            type="checkbox"
            autoComplete="off"
            data-lpignore="true"
            data-1p-ignore="true"
            data-bwignore="true"
            data-form-type="other"
            disabled={isSavingMcp}
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
            <span
              key={t}
              data-testid={`exposed-mcp-tool-${t}`}
              className="rounded-full border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] px-2.5 py-0.5 text-[11px] font-medium text-[var(--orcia-text-primary)]"
            >
              {formatReadableCapability(t, labels)}
            </span>
          ))}
        </div>
      </OrciaDataCard>
    </section>
  );
};
