import React, { useState } from "react";

export interface PackBuilderAgentItem {
  slug: string;
  handle: string;
  roleDescription: string;
}

export interface PackWhatIfImpactItem {
  workspaceKey: string;
  impactedWorkflows: string[];
  breakingNorms: string[];
  activeRunsCount: number;
  runLocksUntouched: boolean;
}

export interface PackToolCertificationSummary {
  toolSlug: string;
  sandboxTier: "TIER_1B_STARLARK" | "TIER_2_CONTAINER";
  certified: boolean;
  elapsedMs: number;
  certificateSha256: string;
}

export interface PackBuilderProcessesStudioLabels {
  studioTitle: string;
  agentsSectionTitle: string;
  humanAnchorSectionTitle: string;
  humanAnchorPlaceholder: string;
  process1CreatePackButtonLabel: string;
  process2WhatIfTitle: string;
  runLocksPreservedBadgeLabel: string;
  process3CertifyTitle: string;
  certifiedBadgeLabel: string;
  process4PromoteButtonLabel: string;
}

export interface PackBuilderProcessesStudioViewProps {
  agents: PackBuilderAgentItem[];
  initialHumanAnchorIntent?: string;
  whatIfImpacts: PackWhatIfImpactItem[];
  certifications: PackToolCertificationSummary[];
  labels: PackBuilderProcessesStudioLabels;
  onCreateBusinessPack?: (humanAnchorIntent: string) => void;
  onPromoteAssetToPack?: () => void;
}

export const PackBuilderProcessesStudioView: React.FC<
  PackBuilderProcessesStudioViewProps
> = ({
  agents,
  initialHumanAnchorIntent = "",
  whatIfImpacts,
  certifications,
  labels,
  onCreateBusinessPack,
  onPromoteAssetToPack,
}) => {
  const [anchorIntent, setAnchorIntent] = useState(initialHumanAnchorIntent);
  const isAnchorValid = anchorIntent.trim().length >= 30;

  return (
    <section
      data-testid="pack-builder-studio-view"
      className="flex flex-col gap-5 rounded-lg border border-[var(--color-border-subtle)] bg-[var(--color-surface-elevated)] p-5 text-[var(--color-text-primary)]"
    >
      <header className="flex flex-wrap items-center justify-between gap-2 border-b border-[var(--color-border-subtle)] pb-3">
        <h2 className="text-base font-semibold">{labels.studioTitle}</h2>
        {onPromoteAssetToPack && (
          <button
            type="button"
            data-testid="process4-promote-btn"
            onClick={onPromoteAssetToPack}
            className="rounded border border-[var(--color-border-subtle)] px-3 py-1.5 text-xs font-medium"
          >
            {labels.process4PromoteButtonLabel}
          </button>
        )}
      </header>

      <div className="flex flex-col gap-2">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-[var(--color-text-secondary)]">
          {labels.agentsSectionTitle}
        </h3>
        <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
          {agents.map((agent) => (
            <div
              key={agent.slug}
              data-testid={`pack-builder-agent-${agent.slug}`}
              className="rounded border border-[var(--color-border-subtle)] bg-[var(--color-surface-canvas)] p-2.5 text-xs"
            >
              <span className="font-mono font-semibold">{agent.handle}</span>
              <p className="mt-1 text-[var(--color-text-secondary)]">
                {agent.roleDescription}
              </p>
            </div>
          ))}
        </div>
      </div>

      {/* Process 1 — Human Anchor (human_authored_required: true) */}
      <div
        data-testid="pack-builder-human-anchor-card"
        className="flex flex-col gap-2 rounded border border-[var(--color-accent-primary)] bg-[var(--color-surface-canvas)] p-3"
      >
        <label
          htmlFor="pack-builder-anchor-textarea"
          className="text-xs font-semibold text-[var(--color-accent-primary)]"
        >
          {labels.humanAnchorSectionTitle}
        </label>
        <textarea
          id="pack-builder-anchor-textarea"
          autoComplete="off"
          data-lpignore="true"
          data-1p-ignore="true"
          data-bwignore="true"
          data-form-type="other"
          data-testid="pack-builder-anchor-input"
          value={anchorIntent}
          onChange={(e) => setAnchorIntent(e.target.value)}
          placeholder={labels.humanAnchorPlaceholder}
          rows={2}
          className="w-full rounded border border-[var(--color-border-subtle)] bg-[var(--color-surface-elevated)] p-2 text-xs"
        />
        <div className="flex justify-end">
          <button
            type="button"
            data-testid="process1-create-pack-btn"
            disabled={!isAnchorValid}
            onClick={() => onCreateBusinessPack?.(anchorIntent)}
            className="rounded bg-[var(--color-accent-primary)] px-3 py-1.5 text-xs font-medium text-[var(--color-text-inverse)] disabled:opacity-40"
          >
            {labels.process1CreatePackButtonLabel}
          </button>
        </div>
      </div>

      {/* Process 2 — What-If Impact Simulation */}
      <div className="flex flex-col gap-2" data-testid="process2-what-if-section">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-[var(--color-text-secondary)]">
          {labels.process2WhatIfTitle}
        </h3>
        {whatIfImpacts.map((impact) => (
          <div
            key={impact.workspaceKey}
            data-testid={`what-if-ws-${impact.workspaceKey}`}
            className="flex flex-wrap items-center justify-between gap-2 rounded border border-[var(--color-border-subtle)] bg-[var(--color-surface-canvas)] p-2.5 text-xs"
          >
            <span className="font-mono font-semibold">{impact.workspaceKey}</span>
            <span>{impact.impactedWorkflows.join(", ")}</span>
            {impact.runLocksUntouched && (
              <span
                data-testid={`run-locks-preserved-${impact.workspaceKey}`}
                className="rounded bg-[var(--color-status-success-subtle)] px-2 py-0.5 font-medium text-[var(--color-status-success)]"
              >
                {labels.runLocksPreservedBadgeLabel}
              </span>
            )}
          </div>
        ))}
      </div>

      {/* Process 3 — Tool & Starlark Certification */}
      <div className="flex flex-col gap-2" data-testid="process3-certifications-section">
        <h3 className="text-xs font-semibold uppercase tracking-wide text-[var(--color-text-secondary)]">
          {labels.process3CertifyTitle}
        </h3>
        {certifications.map((cert) => (
          <div
            key={cert.toolSlug}
            data-testid={`cert-tool-${cert.toolSlug}`}
            className="flex flex-wrap items-center justify-between gap-2 rounded border border-[var(--color-border-subtle)] bg-[var(--color-surface-canvas)] p-2.5 text-xs"
          >
            <span className="font-mono font-semibold">{cert.toolSlug}</span>
            <span className="font-mono text-[var(--color-text-secondary)]">
              {cert.sandboxTier} · {cert.elapsedMs.toFixed(2)} ms
            </span>
            {cert.certified && (
              <span className="rounded bg-[var(--color-status-success-subtle)] px-2 py-0.5 font-medium text-[var(--color-status-success)]">
                {labels.certifiedBadgeLabel}
              </span>
            )}
          </div>
        ))}
      </div>
    </section>
  );
};
