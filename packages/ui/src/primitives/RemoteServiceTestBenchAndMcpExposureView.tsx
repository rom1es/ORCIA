import React from "react";
import { DisabledButtonAlertIndicator } from "../components/DisabledButtonAlertIndicator";
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
  readonly testingInProgressCta?: string;
  readonly testingInProgressNotice?: string;
  readonly activateConnectorCta: string;
  readonly testWithPersonalTokenCta: string;
  readonly mcpExposureHeading: string;
  readonly exposeMcpToggleLabel: string;
  readonly mcpIdeBadge: string;
  readonly ipProtectionNotice: string;
  readonly stepLabels?: Readonly<Record<UiTestBenchStepItem["stepCode"], string>>;
  readonly statusLabels?: Readonly<Record<UiTestBenchStepItem["status"], string>>;
}

const DEFAULT_STEP_LABELS: Readonly<Record<UiTestBenchStepItem["stepCode"], string>> = {
  "1_NETWORK_TLS_ANTI_SSRF": "Réseau, sécurité et protection d'adresse",
  "2_AUTHENTICATION": "Authentification et contrôle d'accès",
  "3_CONTRACT_DISCOVERY": "Découverte du contrat et des actions",
  "4_HOT_DRY_RUN": "Test d'exécution à blanc",
};

const DEFAULT_STATUS_LABELS: Readonly<Record<UiTestBenchStepItem["status"], string>> = {
  PASS: "Validé",
  FAIL: "Échec",
  WAITING_USER_PASSTHROUGH_TOKEN: "En attente de jeton personnel",
  SKIPPED: "Ignoré",
};

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
  const stepLabelMap = labels.stepLabels ?? DEFAULT_STEP_LABELS;
  const statusLabelMap = labels.statusLabels ?? DEFAULT_STATUS_LABELS;

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
              disabled={isTesting}
              data-testid="run-test-bench-btn"
              onClick={onRunTestBench}
              className="inline-flex items-center gap-1.5 rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] px-3 py-1.5 text-xs font-medium disabled:opacity-60"
            >
              {isTesting && <OrciaSpinner size="xs" />}
              <span>
                {isTesting
                  ? (labels.testingInProgressCta ?? "Vérification en cours…")
                  : labels.testAndDiscoverCta}
              </span>
            </button>
          )}
          <button
            type="button"
            disabled={!canActivate || isTesting || isSavingMcp}
            data-testid="activate-remote-service-btn"
            onClick={onActivateService}
            className="inline-flex items-center gap-1.5 rounded bg-[var(--orcia-action-primary)] px-3 py-1.5 text-xs font-medium text-[var(--orcia-text-on-action)] disabled:opacity-50"
          >
            <span>{labels.activateConnectorCta}</span>
            <DisabledButtonAlertIndicator
              disabled={!canActivate || isTesting || isSavingMcp}
              reason="Validez les 4 étapes du banc d'essai pour activer ce connecteur."
              testIdSuffix="activate-remote-service-btn"
            />
          </button>
        </div>
      </header>

      {isTesting && (
        <div
          role="status"
          data-testid="test-bench-loading-banner"
          className="flex items-center gap-2 rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] px-3 py-2 text-xs font-medium text-[var(--orcia-text-secondary)]"
        >
          <OrciaSpinner size="xs" />
          <span>
            {labels.testingInProgressNotice ??
              "Vérification en cours auprès du serveur et enregistrement de la trace d'audit…"}
          </span>
        </div>
      )}

      <div
        className={
          steps.length === 0 && discoveredCapabilities.length === 0
            ? "grid grid-cols-1 gap-4"
            : "grid grid-cols-1 gap-4 md:grid-cols-2"
        }
      >
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
