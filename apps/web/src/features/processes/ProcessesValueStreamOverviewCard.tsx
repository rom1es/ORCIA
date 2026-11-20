import React from "react";
import { INITIAL_VSM_SPEC } from "./processStudioV2Data";

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
            {isFr
              ? "VUE D'ENSEMBLE DU PARCOURS MÉTIER (4 PHASES · 11 ÉTAPES)"
              : "END-TO-END VALUE STREAM (4 PHASES · 11 STEPS)"}
          </span>
          <h3 style={{ margin: 0, fontSize: "var(--font-size-h3)" }}>
            {vsmTitle ?? INITIAL_VSM_SPEC.title} — {vsmSubtitle ?? INITIAL_VSM_SPEC.subtitle}
          </h3>
          <p style={{ margin: 0, fontSize: "13px", color: "var(--color-text-secondary)" }}>
            {isFr
              ? "Visualisez comment s'articulent les 11 étapes entre les équipes et les agents IA, les points de validation humaine et l'évolution des pratiques."
              : "Explore how the 11 steps connect teams and AI agents, human decision points, and process improvements."}
          </p>
        </div>

        <button
          type="button"
          data-testid="open-interactive-vsm-btn"
          onClick={() => onOpenInteractiveVsm(vsmId ?? INITIAL_VSM_SPEC.id)}
          className="orcia-ds-btn-secondary"
        >
          {isFr
            ? "🗺️ Explorer la chaîne de valeur complète (11 étapes)"
            : "🗺️ Explore full 11-step Value Stream"}
        </button>
      </div>

      <div
        style={{
          display: "grid",
          gridTemplateColumns: "repeat(auto-fit, minmax(210px, 1fr))",
          gap: "10px",
        }}
      >
        {INITIAL_VSM_SPEC.phases.map((phase) => (
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
                Phase {phase.num} · Étapes {phase.steps_range}
              </span>
              <span style={{ fontSize: "11px", color: "var(--color-text-secondary)" }}>
                {phase.steps.length} {isFr ? "étapes" : "steps"}
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
