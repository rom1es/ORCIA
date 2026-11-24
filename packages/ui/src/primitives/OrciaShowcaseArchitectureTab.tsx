import React from "react";
import { OrciaSectionCard } from "./DesignSystemControls";
import type { OrciaShowcaseArchitectureLabels } from "./OrciaShowcaseTypes";

export interface OrciaShowcaseArchitectureTabProps {
  readonly labels: OrciaShowcaseArchitectureLabels;
}

export function OrciaShowcaseArchitectureTab({
  labels,
}: OrciaShowcaseArchitectureTabProps): React.ReactElement {
  return (
    <section
      data-testid="showcase-pillar-architecture"
      className="orcia-ds-page"
    >
      <OrciaSectionCard
        testId="showcase-arch-modular-monolith"
        title={labels.modularMonolithTitle}
        subtitle={labels.modularMonolithSubtitle}
      >
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          <div
            className="rounded-lg border p-3.5 space-y-1.5"
            style={{
              backgroundColor: "var(--color-bg-elevated)",
              borderColor: "var(--color-border-subtle)",
            }}
          >
            <div className="font-bold text-sm">
              {labels.frontendBoundaryCard.title}
            </div>
            <p style={{ color: "var(--color-text-secondary)" }}>
              {labels.frontendBoundaryCard.description}
            </p>
          </div>

          <div
            className="rounded-lg border p-3.5 space-y-1.5"
            style={{
              backgroundColor: "var(--color-bg-elevated)",
              borderColor: "var(--color-border-subtle)",
            }}
          >
            <div className="font-bold text-sm">
              {labels.backendCoreCard.title}
            </div>
            <p style={{ color: "var(--color-text-secondary)" }}>
              {labels.backendCoreCard.description}
            </p>
          </div>
        </div>
      </OrciaSectionCard>

      <OrciaSectionCard
        testId="showcase-arch-human-led-impl"
        title={labels.humanLedImplTitle}
        subtitle={labels.humanLedImplSubtitle}
      >
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          <div
            className="rounded-lg border p-3.5 space-y-1.5"
            style={{
              backgroundColor: "var(--color-human-led-bg)",
              borderColor: "var(--color-primary-dark)",
            }}
          >
            <strong className="text-sm">
              {labels.humanAnchorImplCard.title}
            </strong>
            <p style={{ color: "var(--color-text-secondary)" }}>
              {labels.humanAnchorImplCard.description}
            </p>
          </div>

          <div
            className="rounded-lg border p-3.5 space-y-1.5"
            style={{
              backgroundColor: "var(--color-bg-elevated)",
              borderColor: "var(--color-border-subtle)",
            }}
          >
            <strong className="text-sm">
              {labels.adaptiveGateImplCard.title}
            </strong>
            <p style={{ color: "var(--color-text-secondary)" }}>
              {labels.adaptiveGateImplCard.description}
            </p>
          </div>

          <div
            className="rounded-lg border p-3.5 space-y-1.5"
            style={{
              backgroundColor: "var(--color-bg-elevated)",
              borderColor: "var(--color-border-subtle)",
            }}
          >
            <strong className="text-sm">
              {labels.redisLocksImplCard.title}
            </strong>
            <p style={{ color: "var(--color-text-secondary)" }}>
              {labels.redisLocksImplCard.description}
            </p>
          </div>

          <div
            className="rounded-lg border p-3.5 space-y-1.5"
            style={{
              backgroundColor: "var(--color-bg-elevated)",
              borderColor: "var(--color-border-subtle)",
            }}
          >
            <strong className="text-sm">
              {labels.externalRebaseImplCard.title}
            </strong>
            <p style={{ color: "var(--color-text-secondary)" }}>
              {labels.externalRebaseImplCard.description}
            </p>
          </div>
        </div>
      </OrciaSectionCard>

      <OrciaSectionCard
        testId="showcase-arch-deterministic-impl"
        title={labels.deterministicImplTitle}
        subtitle={labels.deterministicImplSubtitle}
      >
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          <div
            className="rounded-lg border p-3.5 space-y-1.5"
            style={{
              backgroundColor: "var(--color-gate-emerald-bg)",
              borderColor: "var(--color-gate-emerald)",
            }}
          >
            <strong className="text-sm">
              {labels.workflowValidatorCard.title}
            </strong>
            <p style={{ color: "var(--color-text-secondary)" }}>
              {labels.workflowValidatorCard.description}
            </p>
          </div>

          <div
            className="rounded-lg border p-3.5 space-y-1.5"
            style={{
              backgroundColor: "var(--color-bg-elevated)",
              borderColor: "var(--color-border-subtle)",
            }}
          >
            <strong className="text-sm">
              {labels.tier1aSandboxCard.title}
            </strong>
            <p style={{ color: "var(--color-text-secondary)" }}>
              {labels.tier1aSandboxCard.description}
            </p>
          </div>

          <div
            className="rounded-lg border p-3.5 space-y-1.5"
            style={{
              backgroundColor: "var(--color-bg-elevated)",
              borderColor: "var(--color-border-subtle)",
            }}
          >
            <strong className="text-sm">
              {labels.tier1bStarlarkCard.title}
            </strong>
            <p style={{ color: "var(--color-text-secondary)" }}>
              {labels.tier1bStarlarkCard.description}
            </p>
          </div>

          <div
            className="rounded-lg border p-3.5 space-y-1.5"
            style={{
              backgroundColor: "var(--color-bg-elevated)",
              borderColor: "var(--color-border-subtle)",
            }}
          >
            <strong className="text-sm">
              {labels.tier2SandboxCard.title}
            </strong>
            <p style={{ color: "var(--color-text-secondary)" }}>
              {labels.tier2SandboxCard.description}
            </p>
          </div>
        </div>
      </OrciaSectionCard>

      <OrciaSectionCard
        testId="showcase-arch-probabilistic-impl"
        title={labels.probabilisticImplTitle}
        subtitle={labels.probabilisticImplSubtitle}
      >
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
          <div
            className="rounded-lg border p-3.5 space-y-1.5"
            style={{
              backgroundColor: "var(--color-bg-elevated)",
              borderColor: "var(--color-border-subtle)",
            }}
          >
            <strong className="text-sm">{labels.agenticGateCard.title}</strong>
            <p style={{ color: "var(--color-text-secondary)" }}>
              {labels.agenticGateCard.description}
            </p>
          </div>

          <div
            className="rounded-lg border p-3.5 space-y-1.5"
            style={{
              backgroundColor: "var(--color-bg-elevated)",
              borderColor: "var(--color-border-subtle)",
            }}
          >
            <strong className="text-sm">{labels.hybridRagCard.title}</strong>
            <p style={{ color: "var(--color-text-secondary)" }}>
              {labels.hybridRagCard.description}
            </p>
          </div>

          <div
            className="rounded-lg border p-3.5 space-y-1.5"
            style={{
              backgroundColor: "var(--color-bg-elevated)",
              borderColor: "var(--color-border-subtle)",
            }}
          >
            <strong className="text-sm">{labels.dbosReplayCard.title}</strong>
            <p style={{ color: "var(--color-text-secondary)" }}>
              {labels.dbosReplayCard.description}
            </p>
          </div>
        </div>
      </OrciaSectionCard>

      <OrciaSectionCard
        testId="showcase-arch-security-and-ds"
        title={labels.securityDsTitle}
        subtitle={labels.securityDsSubtitle}
      >
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          <div
            className="rounded-lg border p-3.5 space-y-1.5"
            style={{
              backgroundColor: "var(--color-bg-elevated)",
              borderColor: "var(--color-border-subtle)",
            }}
          >
            <strong className="text-sm">{labels.authVaultCard.title}</strong>
            <p style={{ color: "var(--color-text-secondary)" }}>
              {labels.authVaultCard.description}
            </p>
          </div>

          <div
            className="rounded-lg border p-3.5 space-y-1.5"
            style={{
              backgroundColor: "var(--color-bg-elevated)",
              borderColor: "var(--color-border-subtle)",
            }}
          >
            <strong className="text-sm">{labels.threeLayerDsCard.title}</strong>
            <p style={{ color: "var(--color-text-secondary)" }}>
              {labels.threeLayerDsCard.description}
            </p>
          </div>
        </div>
      </OrciaSectionCard>
    </section>
  );
}
