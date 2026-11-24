import React from "react";
import { OrciaButton, OrciaSectionCard } from "./DesignSystemControls";
import type { OrciaShowcaseFeaturesLabels } from "./OrciaShowcaseTypes";
import { StatusBadge } from "./StatusBadge";

export interface OrciaShowcaseFeaturesTabProps {
  readonly labels: OrciaShowcaseFeaturesLabels;
  readonly onNavigateToRoute?: (route: string) => void;
}

export function OrciaShowcaseFeaturesTab({
  labels,
  onNavigateToRoute,
}: OrciaShowcaseFeaturesTabProps): React.ReactElement {
  return (
    <section
      data-testid="showcase-pillar-features"
      className="orcia-ds-page"
    >
      <OrciaSectionCard
        testId="showcase-features-six-devices"
        title={labels.devicesTitle}
        subtitle={labels.devicesSubtitle}
      >
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          <div
            data-testid="showcase-device-1-human-anchor"
            className="rounded-lg border p-3.5 space-y-1.5"
            style={{
              backgroundColor: "var(--color-human-led-bg)",
              borderColor: "var(--color-primary-dark)",
            }}
          >
            <div className="flex items-center justify-between gap-2">
              <strong className="text-sm">
                {labels.device1HumanAnchor.title}
              </strong>
              <StatusBadge label={labels.device1HumanAnchor.badge} tone="cobalt" />
            </div>
            <p style={{ color: "var(--color-text-secondary)" }}>
              {labels.device1HumanAnchor.description}
            </p>
          </div>

          <div
            data-testid="showcase-device-2-arbitration-card"
            className="rounded-lg border p-3.5 space-y-1.5"
            style={{
              backgroundColor: "var(--color-arbitration-bg)",
              borderColor: "var(--color-arbitration-amber)",
            }}
          >
            <div className="flex items-center justify-between gap-2">
              <strong className="text-sm">
                {labels.device2Arbitration.title}
              </strong>
              <StatusBadge label={labels.device2Arbitration.badge} tone="amber" />
            </div>
            <p style={{ color: "var(--color-text-secondary)" }}>
              {labels.device2Arbitration.description}
            </p>
          </div>

          <div
            data-testid="showcase-device-3-briefing-grid"
            className="rounded-lg border p-3.5 space-y-1.5"
            style={{
              backgroundColor: "var(--color-bg-elevated)",
              borderColor: "var(--color-border-subtle)",
            }}
          >
            <div className="flex items-center justify-between gap-2">
              <strong className="text-sm">
                {labels.device3BriefingGrid.title}
              </strong>
              <StatusBadge label={labels.device3BriefingGrid.badge} tone="cobalt" />
            </div>
            <p style={{ color: "var(--color-text-secondary)" }}>
              {labels.device3BriefingGrid.description}
            </p>
          </div>

          <div
            data-testid="showcase-device-4-impact-simulator"
            className="rounded-lg border p-3.5 space-y-1.5"
            style={{
              backgroundColor: "var(--color-bg-elevated)",
              borderColor: "var(--color-border-subtle)",
            }}
          >
            <div className="flex items-center justify-between gap-2">
              <strong className="text-sm">
                {labels.device4ImpactSimulator.title}
              </strong>
              <StatusBadge label={labels.device4ImpactSimulator.badge} tone="amber" />
            </div>
            <p style={{ color: "var(--color-text-secondary)" }}>
              {labels.device4ImpactSimulator.description}
            </p>
          </div>

          <div
            data-testid="showcase-device-5-verified-citations"
            className="rounded-lg border p-3.5 space-y-1.5"
            style={{
              backgroundColor: "var(--color-gate-emerald-bg)",
              borderColor: "var(--color-gate-emerald)",
            }}
          >
            <div className="flex items-center justify-between gap-2">
              <strong className="text-sm">
                {labels.device5VerifiedCitations.title}
              </strong>
              <StatusBadge
                label={labels.device5VerifiedCitations.badge}
                tone="emerald"
              />
            </div>
            <p style={{ color: "var(--color-text-secondary)" }}>
              {labels.device5VerifiedCitations.description}
            </p>
          </div>

          <div
            data-testid="showcase-device-6-team-claim"
            className="rounded-lg border p-3.5 space-y-1.5"
            style={{
              backgroundColor: "var(--color-bg-elevated)",
              borderColor: "var(--color-border-subtle)",
            }}
          >
            <div className="flex items-center justify-between gap-2">
              <strong className="text-sm">
                {labels.device6TeamClaim.title}
              </strong>
              <StatusBadge label={labels.device6TeamClaim.badge} tone="cobalt" />
            </div>
            <p style={{ color: "var(--color-text-secondary)" }}>
              {labels.device6TeamClaim.description}
            </p>
          </div>
        </div>
      </OrciaSectionCard>

      <OrciaSectionCard
        testId="showcase-features-nine-screens"
        title={labels.screensTitle}
        subtitle={labels.screensSubtitle}
      >
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
          {labels.screens.map((scr) => (
            <div
              key={scr.id}
              data-testid={`showcase-screen-card-${scr.id}`}
              className="rounded-lg border p-4 flex flex-col justify-between gap-3"
              style={{
                backgroundColor: "var(--color-bg-elevated)",
                borderColor: "var(--color-border-subtle)",
              }}
            >
              <div className="space-y-2">
                <div className="flex items-center justify-between gap-2 flex-wrap">
                  <strong className="text-sm">{scr.title}</strong>
                  <StatusBadge label={scr.route} tone="cobalt" monospace />
                </div>
                <p style={{ color: "var(--color-text-secondary)" }}>
                  {scr.summary}
                </p>
                <ul
                  className="space-y-1 list-disc list-inside"
                  style={{ color: "var(--color-text-primary)" }}
                >
                  {scr.keyActions.map((act, i) => (
                    <li key={i}>{act}</li>
                  ))}
                </ul>
              </div>
              <div
                className="pt-2 border-t flex justify-end"
                style={{ borderColor: "var(--color-border-subtle)" }}
              >
                <OrciaButton
                  testId={`showcase-navigate-screen-${scr.id}`}
                  variant="secondary"
                  onClick={() => onNavigateToRoute?.(scr.route)}
                >
                  {scr.openRouteLabel}
                </OrciaButton>
              </div>
            </div>
          ))}
        </div>
      </OrciaSectionCard>
    </section>
  );
}
