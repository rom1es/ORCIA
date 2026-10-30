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
  readonly reciprocityCitationUri?: string | null;
  readonly onCompleteStep: (stepNumber: number) => void;
  readonly onProvisionDemoWorkspace?: () => void;
  readonly labels: {
    readonly title: string;
    readonly resumeBannerText: string;
    readonly stepCounterPrefix: string;
    readonly validateAndContinueButton: string;
    readonly completedBadgeText: string;
    readonly demoWorkspaceButton: string;
    readonly citationLabel: string;
  };
}

/**
 * Assistant d'initialisation guidé et durable (Story 8.6 / UX-DR20) :
 * Affiche la progression sur 5 étapes avec reprise exacte après fermeture d'onglet,
 * validation fail-fast par étape, preuve de réciprocité RAG et provisionnement Démo 1-clic.
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
  reciprocityCitationUri,
  onCompleteStep,
  onProvisionDemoWorkspace,
  labels,
}: DurableWizardRunnerViewProps) {
  const activeStepDescriptor =
    steps.find((step) => step.stepIndex === currentStep) ?? steps[0];

  return (
    <section
      data-testid="durable-wizard-runner"
      data-wizard-session={sessionId}
      className="flex flex-col gap-4 rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-surface-elevated)] p-4"
    >
      <header className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--color-border-subtle)] pb-3">
        <div>
          <h2 className="text-sm font-semibold text-[var(--color-text-primary)]">
            {labels.title}
          </h2>
          <p className="font-mono text-xs text-[var(--color-text-muted)]">
            {wizardType} · {labels.stepCounterPrefix} {currentStep}/{totalSteps}
          </p>
        </div>

        <div className="flex items-center gap-2">
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

      <ol
        data-testid="wizard-steps-list"
        className="grid grid-cols-1 gap-2 sm:grid-cols-5"
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
              <div className="font-mono text-[10px]">
                #{step.stepIndex}/{totalSteps}
              </div>
              <div>{step.title}</div>
            </li>
          );
        })}
      </ol>

      {activeStepDescriptor && status !== "COMPLETED" ? (
        <div
          data-testid="wizard-active-step-panel"
          className="flex flex-col gap-3 rounded border border-[var(--color-border-subtle)] bg-[var(--color-surface-canvas)] p-3"
        >
          <div className="text-xs font-semibold text-[var(--color-text-primary)]">
            {activeStepDescriptor.title}
          </div>
          <p className="text-xs text-[var(--color-text-secondary)]">
            {activeStepDescriptor.description}
          </p>

          <div className="flex items-center justify-end gap-2">
            <button
              type="button"
              data-testid="wizard-complete-step-btn"
              disabled={!lastStepCheckPassed}
              onClick={() => onCompleteStep(currentStep)}
              className="rounded bg-[var(--color-brand-primary)] px-3 py-1.5 text-xs font-semibold text-[var(--color-surface-elevated)] disabled:opacity-50"
            >
              {labels.validateAndContinueButton}
            </button>
          </div>
        </div>
      ) : null}

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
