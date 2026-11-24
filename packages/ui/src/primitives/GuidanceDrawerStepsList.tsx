import React from "react";
import { OrciaIcon } from "../components/icons";
import { handleRgaaSubmitKeyDown } from "../components/RgaaModalDialog.js";
import type { GuidanceDrawerLabels, GuidanceDrawerStepItem } from "./GuidanceDrawer";

export function GuidanceDrawerStepsList({
  steps,
  labels,
}: {
  readonly steps: readonly GuidanceDrawerStepItem[];
  readonly labels: GuidanceDrawerLabels;
}): React.ReactElement {
  return (
    <ol
      data-testid="guidance-drawer-steps"
      style={{
        margin: "10px 0 0 0",
        paddingLeft: "18px",
        display: "flex",
        flexDirection: "column",
        gap: "6px",
      }}
    >
      {steps.map((step) => (
        <li
          key={step.stepNumber}
          data-testid={`guidance-step-${step.stepNumber}`}
          style={{ fontSize: "0.8125rem" }}
        >
          <div style={{ fontWeight: 600 }}>{step.title}</div>
          <div
            style={{
              fontSize: "0.75rem",
              color: "var(--orcia-text-secondary)",
            }}
          >
            {step.description}{" "}
            <code style={{ fontFamily: "var(--orcia-font-mono)" }}>
              ({labels.commandPrefix}: {step.actionCommand})
            </code>
          </div>
        </li>
      ))}
    </ol>
  );
}

export { handleRgaaSubmitKeyDown };
