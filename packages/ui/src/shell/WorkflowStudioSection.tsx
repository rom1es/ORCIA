import React, { useState } from "react";
import { StatusBadge } from "../primitives/StatusBadge";
import type { UiWorkflowStudioLabels } from "./types";

const cardSectionStyle: React.CSSProperties = {
  borderTop: "1px solid var(--color-border)",
  paddingTop: "12px",
  display: "flex",
  flexDirection: "column",
  gap: "10px",
};

const monoBoxStyle: React.CSSProperties = {
  padding: "8px 10px",
  borderRadius: "var(--radius-sm)",
  backgroundColor: "var(--color-surface-bg)",
  border: "1px solid var(--color-border)",
  fontFamily: "var(--font-mono)",
  fontSize: "var(--font-size-mono)",
  whiteSpace: "pre-wrap",
};

const buttonStyle: React.CSSProperties = {
  padding: "5px 10px",
  borderRadius: "var(--radius-sm)",
  border: "1px solid var(--color-border)",
  backgroundColor: "var(--color-surface-card)",
  color: "var(--color-foreground)",
  cursor: "pointer",
  fontWeight: 600,
};

export interface WorkflowStudioSectionProps {
  labels: UiWorkflowStudioLabels;
}

export function WorkflowStudioSection({ labels }: WorkflowStudioSectionProps) {
  const [validationStatus, setValidationStatus] = useState<string | null>(null);
  const [isError, setIsError] = useState(false);
  const [activeTemplateTab, setActiveTemplateTab] = useState<"markdown" | "schema">("markdown");

  function handleValidateNominal() {
    setIsError(false);
    setValidationStatus(labels.validDagBanner);
  }

  function handleSimulateCriticalAutonomous() {
    setIsError(true);
    setValidationStatus(labels.criticalAutonomousErrorBanner);
  }

  function handleSimulateMissingIntention() {
    setIsError(true);
    setValidationStatus(labels.missingIntentionErrorBanner);
  }

  function handleSimulateDepthExceeded() {
    setIsError(true);
    setValidationStatus(labels.maxDepthErrorBanner);
  }

  return (
    <div data-testid="workflow-studio-section" style={cardSectionStyle}>
      <div>
        <strong>{labels.studioTitle}</strong>
        <p style={{ margin: "4px 0 0 0", color: "var(--color-muted-foreground)" }}>
          {labels.studioSubtitle}
        </p>
      </div>

      <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
        <button
          type="button"
          data-testid="wf-validate-nominal-btn"
          onClick={handleValidateNominal}
          style={{
            ...buttonStyle,
            borderColor: "var(--color-gate-emerald)",
            color: "var(--color-gate-emerald)",
          }}
        >
          {labels.validateNominalLabel}
        </button>

        <button
          type="button"
          data-testid="wf-simulate-critical-autonomous-btn"
          onClick={handleSimulateCriticalAutonomous}
          style={{
            ...buttonStyle,
            borderColor: "var(--color-stale-crimson)",
            color: "var(--color-stale-crimson)",
          }}
        >
          {labels.simulateCriticalAutonomousLabel}
        </button>

        <button
          type="button"
          data-testid="wf-simulate-missing-intention-btn"
          onClick={handleSimulateMissingIntention}
          style={{
            ...buttonStyle,
            borderColor: "var(--color-arbitration-amber)",
            color: "var(--color-arbitration-amber)",
          }}
        >
          {labels.simulateMissingIntentionLabel}
        </button>

        <button
          type="button"
          data-testid="wf-simulate-max-depth-btn"
          onClick={handleSimulateDepthExceeded}
          style={{
            ...buttonStyle,
            borderColor: "var(--color-stale-crimson)",
            color: "var(--color-stale-crimson)",
          }}
        >
          {labels.simulateMaxDepthLabel}
        </button>
      </div>

      {validationStatus && (
        <div
          data-testid="wf-validation-result-banner"
          role="status"
          aria-live="polite"
          style={{
            ...monoBoxStyle,
            borderColor: isError ? "var(--color-stale-crimson)" : "var(--color-gate-emerald)",
            backgroundColor: isError ? "var(--color-stale-bg)" : "var(--color-gate-emerald-bg)",
            color: isError ? "var(--color-stale-crimson)" : "var(--color-gate-emerald)",
          }}
        >
          {validationStatus}
        </div>
      )}

      <div
        data-testid="multi-audience-template-preview"
        style={{ display: "flex", flexDirection: "column", gap: "8px" }}
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
          <strong>{labels.templatePreviewTitle}</strong>
          <div style={{ display: "flex", gap: "6px" }}>
            <button
              type="button"
              data-testid="template-tab-markdown-btn"
              onClick={() => setActiveTemplateTab("markdown")}
              style={{
                ...buttonStyle,
                backgroundColor:
                  activeTemplateTab === "markdown"
                    ? "var(--color-primary-cobalt)"
                    : "var(--color-surface-card)",
                color:
                  activeTemplateTab === "markdown"
                    ? "var(--color-primary-foreground)"
                    : "var(--color-foreground)",
              }}
            >
              {labels.humanMarkdownTabLabel}
            </button>
            <button
              type="button"
              data-testid="template-tab-schema-btn"
              onClick={() => setActiveTemplateTab("schema")}
              style={{
                ...buttonStyle,
                backgroundColor:
                  activeTemplateTab === "schema"
                    ? "var(--color-primary-cobalt)"
                    : "var(--color-surface-card)",
                color:
                  activeTemplateTab === "schema"
                    ? "var(--color-primary-foreground)"
                    : "var(--color-foreground)",
              }}
            >
              {labels.agentSchemaTabLabel}
            </button>
          </div>
        </div>

        <div data-testid="template-compiled-output" style={monoBoxStyle}>
          {activeTemplateTab === "markdown"
            ? labels.sampleHumanMarkdown
            : labels.sampleAgentJsonSchema}
        </div>
      </div>

      <div
        data-testid="sub-workflow-locks-preview"
        style={{ display: "flex", flexDirection: "column", gap: "6px" }}
      >
        <strong>{labels.subWorkflowLocksTitle}</strong>
        <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
          <StatusBadge
            testId="sub-lock-depth-0"
            label="depth=0 : orcia://workflows/claims-engineering-delivery@2.0.0"
            tone="cobalt"
            monospace
          />
          <StatusBadge
            testId="sub-lock-depth-1"
            label="depth=1 : orcia://workflows/sub-remediate-and-verify@1.2.0"
            tone="emerald"
            monospace
          />
          <StatusBadge
            testId="sub-lock-depth-2"
            label="depth=2 : orcia://workflows/sub-verify-regression-suite@1.1.0"
            tone="amber"
            monospace
          />
        </div>
      </div>
    </div>
  );
}
