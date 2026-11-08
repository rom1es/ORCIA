import React from "react";

export interface VsmReturnLoopItem {
  id: string;
  from_step_num: string;
  to_step_num: string;
  tier: "primary" | "secondary";
  reentry_mode: "corrections" | "retravail";
  trigger_condition: string;
  reason: string;
  impact_summary: string;
}

export interface ReturnLoopsSvgOverlayProps {
  loops: readonly VsmReturnLoopItem[];
  highlightedStepNum: string | null;
  onSelectLoopStep: (fromStepNum: string, toStepNum: string) => void;
  isFr: boolean;
}

export function ReturnLoopsSvgOverlay({
  loops,
  highlightedStepNum,
  onSelectLoopStep,
  isFr,
}: ReturnLoopsSvgOverlayProps) {
  const primaryLoops = loops.filter((l) => l.tier === "primary");
  const secondaryLoops = loops.filter((l) => l.tier === "secondary");

  const stepToX = (stepNum: string): number => {
    const n = Number.parseInt(stepNum, 10);
    if (Number.isNaN(n)) return 60;
    return 45 + (n - 1) * 82;
  };

  return (
    <div
      data-testid="vsm-return-loops-svg-overlay"
      className="orcia-bento-card"
      style={{ display: "flex", flexDirection: "column", gap: "10px" }}
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
          <strong style={{ fontSize: "13.5px" }}>
            {isFr
              ? `Boucles de Retour Dynamiques (${primaryLoops.length} principales · ${secondaryLoops.length} secondaires)`
              : `Dynamic Return Loops (${primaryLoops.length} primary · ${secondaryLoops.length} secondary)`}
          </strong>
          <div style={{ fontSize: "12px", color: "var(--color-text-secondary)" }}>
            {isFr
              ? "Survolez un losange de passage humain ou cliquez sur une boucle pour inspecter la ré-entrée en mode corrections (:iter-N)."
              : "Hover a human checkpoint diamond or click a loop to inspect re-entry in corrections mode (:iter-N)."}
          </div>
        </div>

        <div style={{ display: "flex", gap: "12px", fontSize: "11.5px" }}>
          <span style={{ color: "var(--color-arbitration-amber)", fontWeight: 700 }}>
            ╌╌► {isFr ? "Boucle principale (fréquente)" : "Primary loop (frequent)"}
          </span>
          <span style={{ color: "var(--color-text-secondary)", fontWeight: 600 }}>
            ┈┈► {isFr ? "Boucle secondaire (exceptionnelle)" : "Secondary loop (exceptional)"}
          </span>
        </div>
      </div>

      {/* Collision-free multi-track SVG arc diagram across Steps 01..11 */}
      <div style={{ overflowX: "auto" }}>
        <svg
          data-testid="vsm-return-loops-svg-canvas"
          viewBox="0 0 940 135"
          style={{ width: "100%", minWidth: "740px", height: "135px", display: "block" }}
          role="img"
          aria-label={isFr ? "Schéma SVG des boucles de retour VSM" : "VSM Return Loops SVG Diagram"}
        >
          {/* Step anchor nodes 01..11 */}
          {Array.from({ length: 11 }, (_, idx) => {
            const num = String(idx + 1).padStart(2, "0");
            const cx = stepToX(num);
            const isHighlighted = highlightedStepNum === num;
            return (
              <g key={num}>
                <circle
                  cx={cx}
                  cy={24}
                  r={isHighlighted ? 13 : 10}
                  fill={
                    isHighlighted
                      ? "var(--color-arbitration-amber)"
                      : "var(--color-action-primary-subtle)"
                  }
                  stroke="var(--color-primary-cobalt)"
                  strokeWidth={1.5}
                />
                <text
                  x={cx}
                  y={28}
                  textAnchor="middle"
                  fontSize="10"
                  fontWeight="700"
                  fill={
                    isHighlighted
                      ? "var(--color-text-inverse)"
                      : "var(--color-primary-cobalt)"
                  }
                >
                  {num}
                </text>
              </g>
            );
          })}

          {/* Return Loop Arcs (collision-free vertical lanes) */}
          {loops.map((loop, idx) => {
            const xFrom = stepToX(loop.from_step_num);
            const xTo = stepToX(loop.to_step_num);
            const laneY = 46 + (idx % 5) * 16;
            const isPrimary = loop.tier === "primary";
            const isActive =
              highlightedStepNum === null ||
              highlightedStepNum === loop.from_step_num ||
              highlightedStepNum === loop.to_step_num;

            const pathD = `M ${xFrom} 35 L ${xFrom} ${laneY} L ${xTo} ${laneY} L ${xTo} 35`;
            return (
              <g
                key={loop.id}
                data-testid={`svg-return-loop-arc-${loop.id}`}
                style={{ opacity: isActive ? 1 : 0.25, cursor: "pointer" }}
                onClick={() => onSelectLoopStep(loop.from_step_num, loop.to_step_num)}
              >
                <path
                  d={pathD}
                  fill="none"
                  stroke={
                    isPrimary
                      ? "var(--color-arbitration-amber)"
                      : "var(--color-muted-foreground)"
                  }
                  strokeWidth={isPrimary ? 2.2 : 1.4}
                  strokeDasharray={isPrimary ? "6 3" : "2 3"}
                />
                <polygon
                  points={`${xTo},35 ${xTo - 4},42 ${xTo + 4},42`}
                  fill={
                    isPrimary
                      ? "var(--color-arbitration-amber)"
                      : "var(--color-muted-foreground)"
                  }
                />
              </g>
            );
          })}
        </svg>
      </div>

      {/* Interactive Loop Pills */}
      <div style={{ display: "flex", flexWrap: "wrap", gap: "6px" }}>
        {loops.map((loop) => {
          const isPrimary = loop.tier === "primary";
          return (
            <button
              key={loop.id}
              type="button"
              data-testid={`vsm-loop-pill-${loop.id}`}
              onClick={() => onSelectLoopStep(loop.from_step_num, loop.to_step_num)}
              className="rounded border px-2.5 py-1 text-xs"
              style={{
                backgroundColor: isPrimary
                  ? "var(--color-arbitration-bg)"
                  : "var(--color-bg-elevated)",
                borderColor: isPrimary
                  ? "var(--color-arbitration-amber)"
                  : "var(--color-border-subtle)",
                color: "var(--color-text-primary)",
                cursor: "pointer",
              }}
              title={`${loop.trigger_condition} — ${loop.reason}`}
            >
              <strong style={{ fontFamily: "var(--font-mono)" }}>
                ↩ {loop.from_step_num} → {loop.to_step_num}
              </strong>{" "}
              <span style={{ color: "var(--color-text-secondary)" }}>
                ({loop.reentry_mode}) · {loop.trigger_condition}
              </span>
            </button>
          );
        })}
      </div>
    </div>
  );
}
