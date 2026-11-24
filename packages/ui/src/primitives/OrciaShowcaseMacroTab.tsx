import React from "react";
import { OrciaSectionCard } from "./DesignSystemControls";
import type { OrciaShowcaseMacroLabels } from "./OrciaShowcaseTypes";
import { StatusBadge } from "./StatusBadge";

export interface OrciaShowcaseMacroTabProps {
  readonly labels: OrciaShowcaseMacroLabels;
}

export function OrciaShowcaseMacroTab({
  labels,
}: OrciaShowcaseMacroTabProps): React.ReactElement {
  return (
    <section
      data-testid="showcase-pillar-macro"
      className="orcia-ds-page"
    >
      <OrciaSectionCard
        testId="showcase-macro-why-orcia"
        title={labels.whyTitle}
        subtitle={labels.whySubtitle}
      >
        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
          {labels.whyCards.map((card, idx) => (
            <div
              key={idx}
              className="rounded-lg border p-3.5 space-y-1.5"
              style={{
                backgroundColor: "var(--color-bg-elevated)",
                borderColor: "var(--color-border-subtle)",
              }}
            >
              <div
                className="font-bold text-sm"
                style={{ color: "var(--color-action-primary)" }}
              >
                {card.title}
              </div>
              <p style={{ color: "var(--color-text-secondary)" }}>
                {card.description}
              </p>
            </div>
          ))}
        </div>
      </OrciaSectionCard>

      <OrciaSectionCard
        testId="showcase-macro-human-led"
        title={labels.humanLedTitle}
        subtitle={labels.humanLedSubtitle}
      >
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
          <div
            data-testid="showcase-macro-human-anchor-pillar"
            className="rounded-lg border p-4 space-y-2"
            style={{
              backgroundColor: "var(--color-human-led-bg)",
              borderColor: "var(--color-primary-dark)",
            }}
          >
            <div className="flex items-center justify-between gap-2 flex-wrap">
              <span className="font-bold text-sm">
                {labels.humanAnchorCard.title}
              </span>
              <StatusBadge label={labels.humanAnchorCard.badge} tone="cobalt" />
            </div>
            <p style={{ color: "var(--color-text-secondary)" }}>
              {labels.humanAnchorCard.description}
            </p>
          </div>

          <div
            data-testid="showcase-macro-anti-rubber-stamping-pillar"
            className="rounded-lg border p-4 space-y-2"
            style={{
              backgroundColor: "var(--color-bg-elevated)",
              borderColor: "var(--color-border-subtle)",
            }}
          >
            <div className="flex items-center justify-between gap-2 flex-wrap">
              <span className="font-bold text-sm">
                {labels.antiRubberStampingCard.title}
              </span>
              <StatusBadge
                label={labels.antiRubberStampingCard.badge}
                tone="cobalt"
              />
            </div>
            <p style={{ color: "var(--color-text-secondary)" }}>
              {labels.antiRubberStampingCard.description}
            </p>
          </div>

          <div
            data-testid="showcase-macro-human-arbitration-pillar"
            className="rounded-lg border p-4 space-y-2"
            style={{
              backgroundColor: "var(--color-arbitration-bg)",
              borderColor: "var(--color-arbitration-amber)",
            }}
          >
            <div className="flex items-center justify-between gap-2 flex-wrap">
              <span className="font-bold text-sm">
                {labels.humanArbitrationCard.title}
              </span>
              <StatusBadge
                label={labels.humanArbitrationCard.badge}
                tone="amber"
              />
            </div>
            <p style={{ color: "var(--color-text-secondary)" }}>
              {labels.humanArbitrationCard.description}
            </p>
          </div>

          <div
            data-testid="showcase-macro-no-wild-writes-pillar"
            className="rounded-lg border p-4 space-y-2"
            style={{
              backgroundColor: "var(--color-gate-emerald-bg)",
              borderColor: "var(--color-gate-emerald)",
            }}
          >
            <div className="flex items-center justify-between gap-2 flex-wrap">
              <span className="font-bold text-sm">
                {labels.noWildWritesCard.title}
              </span>
              <StatusBadge label={labels.noWildWritesCard.badge} tone="emerald" />
            </div>
            <p style={{ color: "var(--color-text-secondary)" }}>
              {labels.noWildWritesCard.description}
            </p>
          </div>
        </div>
      </OrciaSectionCard>

      <OrciaSectionCard
        testId="showcase-macro-double-barrier"
        title={labels.doubleBarrierTitle}
        subtitle={labels.doubleBarrierSubtitle}
      >
        <div
          className="rounded-lg border p-3.5 text-xs mb-3"
          style={{
            backgroundColor: "var(--color-stale-bg)",
            borderColor: "var(--color-stale-crimson)",
          }}
        >
          <strong>{labels.snowballWarningPrefix}</strong>
          <span style={{ color: "var(--color-text-primary)" }}>
            {labels.snowballWarningBody}
          </span>
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4 text-xs">
          <div
            data-testid="showcase-macro-barrier-deterministic"
            className="rounded-lg border p-4 space-y-2"
            style={{
              backgroundColor: "var(--color-gate-emerald-bg)",
              borderColor: "var(--color-gate-emerald)",
            }}
          >
            <StatusBadge
              label={labels.deterministicBarrier.badge}
              tone="emerald"
            />
            <h3 className="font-bold text-sm">
              {labels.deterministicBarrier.title}
            </h3>
            <ul
              className="space-y-1 list-disc list-inside"
              style={{ color: "var(--color-text-secondary)" }}
            >
              {labels.deterministicBarrier.items.map((item, idx) => (
                <li key={idx}>{item}</li>
              ))}
            </ul>
          </div>

          <div
            data-testid="showcase-macro-barrier-probabilistic"
            className="rounded-lg border p-4 space-y-2"
            style={{
              backgroundColor: "var(--color-bg-elevated)",
              borderColor: "var(--color-border-subtle)",
            }}
          >
            <StatusBadge label={labels.probabilisticBarrier.badge} tone="cobalt" />
            <h3 className="font-bold text-sm">
              {labels.probabilisticBarrier.title}
            </h3>
            <ul
              className="space-y-1 list-disc list-inside"
              style={{ color: "var(--color-text-secondary)" }}
            >
              {labels.probabilisticBarrier.items.map((item, idx) => (
                <li key={idx}>{item}</li>
              ))}
            </ul>
          </div>

          <div
            data-testid="showcase-macro-barrier-rewind"
            className="rounded-lg border p-4 space-y-2"
            style={{
              backgroundColor: "var(--color-arbitration-bg)",
              borderColor: "var(--color-arbitration-amber)",
            }}
          >
            <StatusBadge label={labels.rewindBarrier.badge} tone="amber" />
            <h3 className="font-bold text-sm">{labels.rewindBarrier.title}</h3>
            <ul
              className="space-y-1 list-disc list-inside"
              style={{ color: "var(--color-text-secondary)" }}
            >
              {labels.rewindBarrier.items.map((item, idx) => (
                <li key={idx}>{item}</li>
              ))}
            </ul>
          </div>
        </div>
      </OrciaSectionCard>

      <OrciaSectionCard
        testId="showcase-macro-org-and-packs"
        title={labels.orgPacksTitle}
        subtitle={labels.orgPacksSubtitle}
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
              {labels.orgHierarchyCard.title}
            </div>
            <p style={{ color: "var(--color-text-secondary)" }}>
              {labels.orgHierarchyCard.description}
            </p>
          </div>

          <div
            className="rounded-lg border p-3.5 space-y-1.5"
            style={{
              backgroundColor: "var(--color-bg-elevated)",
              borderColor: "var(--color-border-subtle)",
            }}
          >
            <div className="font-bold text-sm">{labels.packsCard.title}</div>
            <p style={{ color: "var(--color-text-secondary)" }}>
              {labels.packsCard.description}
            </p>
          </div>
        </div>
      </OrciaSectionCard>
    </section>
  );
}
