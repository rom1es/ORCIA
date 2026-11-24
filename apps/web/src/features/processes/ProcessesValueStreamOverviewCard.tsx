import React from "react";
import {
  formatI18nTemplate,
  resolveDictionaryForFlag,
  resolveLocaleForFlag,
} from "../../i18n";
import { getInitialVsmSpec } from "./processStudioV2Data";

export interface ProcessesValueStreamOverviewCardProps {
  readonly isFr: boolean;
  readonly onOpenInteractiveVsm: (vsmId: string) => void;
  readonly vsmId?: string;
  readonly vsmTitle?: string;
  readonly vsmSubtitle?: string;
}

export function ProcessesValueStreamOverviewCard({
  isFr,
  onOpenInteractiveVsm,
  vsmId,
  vsmTitle,
  vsmSubtitle,
}: ProcessesValueStreamOverviewCardProps): React.ReactElement {
  const locale = resolveLocaleForFlag(isFr);
  const copy = resolveDictionaryForFlag(isFr).processStudioUi.hub;
  const vsmSpec = getInitialVsmSpec(locale);

  return (
    <div
      data-testid="processes-hub-vsm-hero-card"
      className="orcia-bento-card"
      style={{
        display: "flex",
        flexDirection: "column",
        gap: "12px",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
          flexWrap: "wrap",
          gap: "12px",
        }}
      >
        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          <span
            style={{
              fontSize: "12px",
              fontWeight: 700,
              color: "var(--color-primary-cobalt)",
            }}
          >
            {copy.vsmOverviewEyebrow}
          </span>
          <h3 style={{ margin: 0, fontSize: "var(--font-size-h3)" }}>
            {vsmTitle ?? vsmSpec.title} — {vsmSubtitle ?? vsmSpec.subtitle}
          </h3>
          <p style={{ margin: 0, fontSize: "13px", color: "var(--color-text-secondary)" }}>
            {copy.vsmOverviewSubtitle}
          </p>
        </div>

        <button
          type="button"
          data-testid="open-interactive-vsm-btn"
          onClick={() => onOpenInteractiveVsm(vsmId ?? vsmSpec.id)}
          className="orcia-ds-btn-secondary"
        >
          {copy.exploreFullVsmBtn}
        </button>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(210px, 1fr))",
          gap: "10px",
        }}
      >
        {vsmSpec.phases.map((phase) => (
          <div
            key={phase.num}
            data-testid={`vsm-hero-phase-${phase.num}`}
            className="rounded border p-2.5"
            style={{
              backgroundColor: "var(--color-bg-elevated)",
              borderColor: "var(--color-border-subtle)",
            }}
          >
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
              <span
                style={{
                  fontSize: "11px",
                  fontWeight: 700,
                  color: "var(--color-primary-cobalt)",
                }}
              >
                {formatI18nTemplate(copy.vsmPhaseStepsRangeTemplate, {
                  num: phase.num,
                  range: phase.steps_range,
                })}
              </span>
              <span style={{ fontSize: "11px", color: "var(--color-text-secondary)" }}>
                {phase.steps.length} {copy.vsmStepsCountUnit}
              </span>
            </div>
            <div style={{ fontWeight: 700, fontSize: "13.5px", marginTop: "2px" }}>
              {phase.name}
            </div>
            <div style={{ fontSize: "11.5px", color: "var(--color-text-secondary)", marginTop: "2px" }}>
              {phase.goal}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
