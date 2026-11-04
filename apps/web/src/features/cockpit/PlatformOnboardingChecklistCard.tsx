import { StatusBadge } from "@orcia/ui";
import React from "react";

export interface OnboardingChecklistStepView {
  readonly id: string;
  readonly number: number;
  readonly title: string;
  readonly done: boolean;
  readonly countLabel: string;
  readonly settingsHref: string;
  readonly wizardHref: string;
  readonly ctaLabel: string;
}

export interface PlatformOnboardingChecklistCardProps {
  readonly isFr: boolean;
  readonly completedSetupStepsCount: number;
  readonly checklistSteps: readonly OnboardingChecklistStepView[];
  readonly onNavigateToRoute: (href: string) => void;
}

export function PlatformOnboardingChecklistCard({
  isFr,
  completedSetupStepsCount,
  checklistSteps,
  onNavigateToRoute,
}: PlatformOnboardingChecklistCardProps): React.ReactElement {
  return (
    <section
      data-testid="platform-onboarding-checklist"
      className="orcia-bento-card"
      style={{ display: "flex", flexDirection: "column", gap: "14px" }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "8px",
        }}
      >
        <div>
          <h2 style={{ margin: 0, fontSize: "var(--font-size-h2)" }}>
            {isFr
              ? "Guide de Mise en Route de la Plateforme"
              : "Platform Getting Started Checklist"}
          </h2>
          <p
            style={{
              margin: "4px 0 0 0",
              fontSize: "var(--font-size-body)",
              color: "var(--color-muted-foreground)",
            }}
          >
            {isFr
              ? "Configurez chaque étape depuis les écrans dédiés ou lancez un assistant guidé pas à pas."
              : "Complete each step from the dedicated settings screens or launch a step-by-step guided assistant."}
          </p>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <StatusBadge
            testId="onboarding-progress-badge"
            label={`${completedSetupStepsCount}/5`}
            tone={completedSetupStepsCount === 5 ? "emerald" : "cobalt"}
            monospace
          />
          <button
            type="button"
            data-testid="open-guided-wizards-btn"
            onClick={() => onNavigateToRoute("/wizards")}
            style={{
              padding: "7px 12px",
              borderRadius: "var(--radius-sm)",
              border: "1px solid var(--color-primary-cobalt)",
              backgroundColor: "var(--color-primary-cobalt)",
              color: "var(--color-primary-foreground)",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            {isFr ? "Assistants Guidés" : "Guided Assistants"}
          </button>
        </div>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(260px, 1fr))",
          gap: "12px",
        }}
      >
        {checklistSteps.map((step) => (
          <div
            key={step.id}
            data-testid={`setup-step-card-${step.id}`}
            style={{
              padding: "12px 14px",
              borderRadius: "var(--radius-md)",
              border: "1px solid var(--color-border)",
              backgroundColor: "var(--color-surface-bg)",
              display: "flex",
              flexDirection: "column",
              justifyContent: "space-between",
              gap: "10px",
            }}
          >
            <div style={{ display: "flex", flexDirection: "column", gap: "6px" }}>
              <div
                style={{
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  gap: "8px",
                }}
              >
                <strong style={{ fontSize: "13.5px" }}>{step.title}</strong>
                <StatusBadge
                  label={
                    step.done
                      ? isFr
                        ? "Configuré"
                        : "Configured"
                      : isFr
                        ? "À configurer"
                        : "To configure"
                  }
                  tone={step.done ? "emerald" : "amber"}
                />
              </div>
              <span
                style={{
                  fontFamily: "var(--font-mono)",
                  fontSize: "var(--font-size-mono)",
                  color: "var(--color-muted-foreground)",
                }}
              >
                {step.countLabel}
              </span>
            </div>

            <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
              <button
                type="button"
                data-testid={`setup-cta-${step.id}`}
                onClick={() => onNavigateToRoute(step.settingsHref)}
                style={{
                  padding: "6px 10px",
                  borderRadius: "var(--radius-sm)",
                  border: "1px solid var(--color-border)",
                  backgroundColor: "var(--color-surface-card)",
                  color: "var(--color-foreground)",
                  fontSize: "12.5px",
                  fontWeight: 600,
                  cursor: "pointer",
                }}
              >
                {step.ctaLabel}
              </button>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
}
