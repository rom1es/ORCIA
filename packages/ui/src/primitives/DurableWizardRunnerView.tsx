import type React from "react";
import { DisabledButtonAlertIndicator } from "../components/DisabledButtonAlertIndicator";

export type DurableWizardProfileType =
  | "sdlc_tech_lead"
  | "ops_manager"
  | "secops_admin";

export interface DurableWizardStepDescriptor {
  readonly stepIndex: number;
  readonly title: string;
  readonly description: string;
}

export interface DurableWizardRunnerViewProps {
  readonly sessionId: string;
  readonly wizardType: DurableWizardProfileType;
  readonly currentStep: number;
  readonly totalSteps: number;
  readonly status: "IN_PROGRESS" | "PAUSED" | "COMPLETED" | "ABANDONED";
  readonly steps: readonly DurableWizardStepDescriptor[];
  readonly resumedFromCheckpoint?: boolean;
  readonly lastStepCheckPassed?: boolean;
  readonly isSubmitting?: boolean;
  readonly reciprocityCitationUri?: string | null;
  readonly onCompleteStep: (stepNumber: number) => void;
  readonly onStepBack?: () => void;
  readonly onProvisionDemoWorkspace?: () => void;
  readonly headerActions?: React.ReactNode;
  readonly children?: React.ReactNode;
  readonly labels: {
    readonly title: string;
    readonly resumeBannerText: string;
    readonly stepCounterPrefix: string;
    readonly stepCounterConnector?: string;
    readonly stepBackButton?: string;
    readonly validateAndContinueButton: string;
    readonly completedBadgeText: string;
    readonly demoWorkspaceButton: string;
    readonly citationLabel: string;
    readonly disabledStepReason?: string;
    readonly profileLabels?: Partial<Record<DurableWizardProfileType, string>>;
  };
}

/**
 * Assistant d'initialisation guidé et durable (Story 8.6 / 22.5 / UX-DR20) :
 * Affiche l'étape active et son formulaire au-dessus de la ligne de flottaison,
 * avec progression sobre sur 5 étapes, reprise exacte après F5 et validation fail-fast.
 */
export function DurableWizardRunnerView({
  sessionId,
  wizardType,
  currentStep,
  totalSteps,
  status,
  steps,
  resumedFromCheckpoint = false,
  lastStepCheckPassed = true,
  isSubmitting = false,
  reciprocityCitationUri,
  onCompleteStep,
  onStepBack,
  onProvisionDemoWorkspace,
  headerActions,
  children,
  labels,
}: DurableWizardRunnerViewProps) {
  const activeStepDescriptor =
    steps.find((step) => step.stepIndex === currentStep) ?? steps[0];
  const resolvedProfileLabel = labels.profileLabels?.[wizardType];
  const stepCounterText = labels.stepCounterConnector
    ? `${labels.stepCounterPrefix} ${currentStep} ${labels.stepCounterConnector} ${totalSteps}`
    : `${labels.stepCounterPrefix} ${currentStep}/${totalSteps}`;

  return (
    <section
      data-testid="durable-wizard-runner"
      data-wizard-session={sessionId}
      className="flex flex-col gap-3 rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-surface-elevated)] p-4"
    >
      <header className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--color-border-subtle)] pb-2.5">
        <div>
          <h2 className="m-0 text-sm font-semibold text-[var(--color-text-primary)]">
            {labels.title}
          </h2>
          <p className="m-0 mt-0.5 text-xs text-[var(--color-text-muted)]">
            {resolvedProfileLabel ? `${resolvedProfileLabel} · ` : ""}
            {stepCounterText}
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {headerActions}

          {status === "COMPLETED" ? (
            <span
              data-testid="wizard-completed-badge"
              className="rounded bg-[var(--color-status-completed)] px-2.5 py-1 text-xs font-semibold text-[var(--color-surface-elevated)]"
            >
              {labels.completedBadgeText}
            </span>
          ) : null}

          {onProvisionDemoWorkspace ? (
            <button
              type="button"
              data-testid="wizard-demo-workspace-btn"
              onClick={onProvisionDemoWorkspace}
              className="rounded border border-[var(--color-brand-primary)] bg-[var(--color-surface-canvas)] px-3 py-1 text-xs font-semibold text-[var(--color-brand-primary)]"
            >
              {labels.demoWorkspaceButton}
            </button>
          ) : null}
        </div>
      </header>

      {resumedFromCheckpoint ? (
        <div
          role="status"
          data-testid="wizard-resumed-banner"
          className="rounded border border-[var(--color-brand-primary)] bg-[var(--color-surface-canvas)] px-3 py-2 text-xs text-[var(--color-text-primary)]"
        >
          {labels.resumeBannerText} ({currentStep}/{totalSteps})
        </div>
      ) : null}

      {activeStepDescriptor && status !== "COMPLETED" ? (
        <div
          data-testid="wizard-active-step-panel"
          className="flex flex-col gap-3 rounded border border-[var(--color-border-subtle)] bg-[var(--color-surface-canvas)] p-3"
        >
          <div>
            <div className="text-xs font-semibold text-[var(--color-text-primary)]">
              {labels.stepCounterPrefix} {activeStepDescriptor.stepIndex} —{" "}
              {activeStepDescriptor.title}
            </div>
            <p className="m-0 mt-0.5 text-xs text-[var(--color-text-secondary)]">
              {activeStepDescriptor.description}
            </p>
          </div>

          {children}

          <div className="flex items-center justify-between gap-2 pt-1">
            <div>
              {onStepBack && currentStep > 1 ? (
                <button
                  type="button"
                  data-testid="wizard-step-back-btn"
                  disabled={isSubmitting}
                  onClick={onStepBack}
                  className="rounded border border-[var(--color-border-subtle)] bg-[var(--color-surface-elevated)] px-3 py-1.5 text-xs font-medium text-[var(--color-text-primary)] disabled:opacity-50"
                >
                  {labels.stepBackButton ?? "←"}
                </button>
              ) : null}
            </div>
            <button
              type="button"
              data-testid="wizard-complete-step-btn"
              disabled={!lastStepCheckPassed || isSubmitting}
              onClick={() => onCompleteStep(currentStep)}
              className="inline-flex items-center gap-1.5 rounded bg-[var(--color-brand-primary)] px-3 py-1.5 text-xs font-semibold text-[var(--color-surface-elevated)] disabled:opacity-50"
            >
              <span>{labels.validateAndContinueButton}</span>
              <DisabledButtonAlertIndicator
                disabled={!lastStepCheckPassed}
                reason={labels.disabledStepReason}
                testIdSuffix="wizard-complete-step-btn"
              />
            </button>
          </div>
        </div>
      ) : null}

      <ol
        data-testid="wizard-steps-list"
        className="m-0 grid list-none grid-cols-1 gap-2 p-0 sm:grid-cols-5"
      >
        {steps.map((step) => {
          const isCurrent = step.stepIndex === currentStep && status !== "COMPLETED";
          const isDone =
            status === "COMPLETED" || step.stepIndex < currentStep;
          return (
            <li
              key={step.stepIndex}
              data-testid={`wizard-step-item-${step.stepIndex}`}
              data-step-state={isDone ? "done" : isCurrent ? "current" : "upcoming"}
              className={`rounded border p-2 text-xs ${
                isCurrent
                  ? "border-[var(--color-brand-primary)] bg-[var(--color-surface-canvas)] font-semibold text-[var(--color-text-primary)]"
                  : isDone
                    ? "border-[var(--color-status-completed)] bg-[var(--color-surface-canvas)] text-[var(--color-text-secondary)]"
                    : "border-[var(--color-border-subtle)] text-[var(--color-text-muted)]"
              }`}
            >
              <div className="text-[11px] font-medium text-[var(--color-text-muted)]">
                {labels.stepCounterPrefix} {step.stepIndex}
              </div>
              <div>{step.title}</div>
            </li>
          );
        })}
      </ol>

      {reciprocityCitationUri ? (
        <div
          data-testid="wizard-reciprocity-citation"
          className="rounded border border-[var(--color-border-subtle)] bg-[var(--color-surface-canvas)] px-3 py-2 text-xs text-[var(--color-text-secondary)]"
        >
          <span className="font-semibold">{labels.citationLabel}: </span>
          <code className="font-mono">{reciprocityCitationUri}</code>
        </div>
      ) : null}
    </section>
  );
}
