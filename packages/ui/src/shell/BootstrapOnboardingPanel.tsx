import React, { useState } from "react";
import { HumanLedAnchorCard } from "../primitives/HumanLedAnchorCard";
import { StatusBadge } from "../primitives/StatusBadge";
import { FederatedUriBadge } from "./FederatedUriBadge";
import type {
  UiBootstrapOnboardingLabels,
  UiBootstrapWorkflowView,
  UiPersonaKey,
} from "./types";

export interface BootstrapOnboardingPanelProps {
  activePersona: UiPersonaKey;
  workflows: UiBootstrapWorkflowView[];
  labels: UiBootstrapOnboardingLabels;
}

const cardStyle: React.CSSProperties = {
  backgroundColor: "var(--color-surface-bg)",
  border: "1px solid var(--color-border)",
  borderRadius: "var(--radius-sm)",
  padding: "12px",
  display: "flex",
  flexDirection: "column",
  gap: "8px",
};

const primaryBtnStyle: React.CSSProperties = {
  backgroundColor: "var(--color-primary-cobalt)",
  color: "var(--color-primary-foreground)",
  border: "none",
  borderRadius: "var(--radius-sm)",
  padding: "6px 12px",
  fontWeight: 600,
  cursor: "pointer",
};

const secondaryBtnStyle: React.CSSProperties = {
  backgroundColor: "var(--color-surface-card)",
  color: "var(--color-foreground)",
  border: "1px solid var(--color-border)",
  borderRadius: "var(--radius-sm)",
  padding: "6px 12px",
  fontWeight: 600,
  cursor: "pointer",
};

export function BootstrapOnboardingPanel({
  activePersona,
  workflows,
  labels,
}: BootstrapOnboardingPanelProps) {
  const isObserver = activePersona === "claire";
  const [isOrthogonal, setIsOrthogonal] = useState(true);
  const [justification, setJustification] = useState(
    "Validation architecturale et sécurité du périmètre Git BFF et Confluence CQL par le Tech Lead.",
  );
  const [signature, setSignature] = useState("Marc (Tech Lead Checkout)");
  const [feedbackBanner, setFeedbackBanner] = useState<string | null>(null);
  const [feedbackTone, setFeedbackTone] = useState<"emerald" | "amber" | "crimson">("emerald");

  function handleSimulateSingleFamily() {
    if (isObserver) {
      setFeedbackTone("amber");
      setFeedbackBanner(labels.observerDeniedBanner);
      return;
    }
    setIsOrthogonal(false);
    setFeedbackTone("crimson");
    setFeedbackBanner(labels.orthogonalityFailBanner);
  }

  function handleSimulateDualFamily() {
    if (isObserver) {
      setFeedbackTone("amber");
      setFeedbackBanner(labels.observerDeniedBanner);
      return;
    }
    setIsOrthogonal(true);
    setFeedbackTone("emerald");
    setFeedbackBanner(labels.orthogonalityPassBadge);
  }

  function handleInitWorkspace() {
    if (isObserver) {
      setFeedbackTone("amber");
      setFeedbackBanner(labels.observerDeniedBanner);
      return;
    }
    setFeedbackTone("emerald");
    setFeedbackBanner(labels.initWorkspaceSuccessBanner);
  }

  function handleInitDatasource() {
    if (isObserver) {
      setFeedbackTone("amber");
      setFeedbackBanner(labels.observerDeniedBanner);
      return;
    }
    const cleanJust = justification.trim();
    const cleanSig = signature.trim();
    if (cleanJust.length < 30 || new Set(cleanJust.toLowerCase()).size < 5 || cleanSig.length < 3) {
      setFeedbackTone("crimson");
      setFeedbackBanner(labels.humanAnchorErrorBanner);
      return;
    }
    setFeedbackTone("emerald");
    setFeedbackBanner(labels.initDatasourceSuccessBanner);
  }

  function handleInitUser() {
    if (isObserver) {
      setFeedbackTone("amber");
      setFeedbackBanner(labels.observerDeniedBanner);
      return;
    }
    setFeedbackTone("emerald");
    setFeedbackBanner(labels.initUserSuccessBanner);
  }

  return (
    <section
      data-testid="bootstrap-onboarding-panel"
      style={{
        backgroundColor: "var(--color-surface-card)",
        border: "1px solid var(--color-border)",
        borderRadius: "var(--radius-md)",
        padding: "16px",
        display: "flex",
        flexDirection: "column",
        gap: "14px",
      }}
    >
      <header style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
        <strong style={{ fontSize: "var(--font-size-display)", fontFamily: "var(--font-serif)" }}>
          {labels.panelTitle}
        </strong>
        <p style={{ margin: 0, color: "var(--color-muted-foreground)" }}>{labels.panelSubtitle}</p>
      </header>

      <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
        {workflows.map((wf) => (
          <FederatedUriBadge
            key={wf.uri}
            testId={`bootstrap-wf-${wf.uri.split("/").pop() ?? "wf"}`}
            scheme="orcia"
            uri={wf.uri}
            sha256Short="boot15000000"
            grantedPermissions={["DISCOVER", "EXECUTE"]}
            sourceMasked={false}
            maskedSourceLabel={wf.requiredRole}
            openSourceLabel={wf.scopeLevel}
          />
        ))}
      </div>

      {feedbackBanner && (
        <div
          data-testid="bootstrap-feedback-banner"
          style={{
            padding: "8px 12px",
            borderRadius: "var(--radius-sm)",
            fontFamily: "var(--font-mono)",
            fontSize: "var(--font-size-mono)",
            backgroundColor:
              feedbackTone === "emerald"
                ? "var(--color-verified-bg)"
                : feedbackTone === "amber"
                  ? "var(--color-arbitration-bg)"
                  : "var(--color-stale-bg)",
            border: `1px solid ${
              feedbackTone === "emerald"
                ? "var(--color-verified-emerald)"
                : feedbackTone === "amber"
                  ? "var(--color-arbitration-amber)"
                  : "var(--color-stale-crimson)"
            }`,
            color:
              feedbackTone === "emerald"
                ? "var(--color-verified-emerald)"
                : feedbackTone === "amber"
                  ? "var(--color-arbitration-amber)"
                  : "var(--color-stale-crimson)",
          }}
        >
          {feedbackBanner}
        </div>
      )}

      <div style={cardStyle}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
          <strong>{labels.orthogonalityTitle}</strong>
          <StatusBadge
            testId="llm-orthogonality-badge"
            label={isOrthogonal ? labels.orthogonalityPassBadge : labels.orthogonalityFailBanner}
            tone={isOrthogonal ? "emerald" : "crimson"}
            monospace
          />
        </div>
        <div style={{ display: "flex", gap: "8px", flexWrap: "wrap" }}>
          <button
            type="button"
            data-testid="simulate-single-llm-family-btn"
            onClick={handleSimulateSingleFamily}
            style={secondaryBtnStyle}
          >
            {labels.simulateSingleFamilyLabel}
          </button>
          <button
            type="button"
            data-testid="simulate-dual-llm-family-btn"
            onClick={handleSimulateDualFamily}
            style={primaryBtnStyle}
          >
            {labels.simulateDualFamilyLabel}
          </button>
        </div>
      </div>

      <div style={cardStyle}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
          <strong>{labels.initWorkspaceTitle}</strong>
          <button
            type="button"
            data-testid="execute-init-workspace-btn"
            onClick={handleInitWorkspace}
            style={primaryBtnStyle}
          >
            {labels.initWorkspaceButtonLabel}
          </button>
        </div>
      </div>

      <div style={cardStyle}>
        <strong>{labels.initDatasourceTitle}</strong>
        <HumanLedAnchorCard
          testId="human-led-anchor-card"
          justificationTestId="human-anchor-justification-input"
          signatureTestId="human-anchor-signature-input"
          sectionKey="init-datasource-anchor"
          sectionTitle={labels.humanAnchorCardLabels.sectionTitle}
          authorName="Marc (TEAM_LEAD)"
          value={justification}
          signatureLabel={labels.humanAnchorCardLabels.signatureLabel}
          signatureValue={signature}
          signaturePlaceholder={labels.humanAnchorCardLabels.signaturePlaceholder}
          readOnly={isObserver}
          hideSubmitButton
          labels={labels.humanAnchorCardLabels}
          onChange={setJustification}
          onSignatureChange={setSignature}
        />
        <div>
          <button
            type="button"
            data-testid="execute-init-datasource-btn"
            onClick={handleInitDatasource}
            style={primaryBtnStyle}
          >
            {labels.initDatasourceButtonLabel}
          </button>
        </div>
      </div>

      <div style={cardStyle}>
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
          <strong>{labels.initUserTitle}</strong>
          <button
            type="button"
            data-testid="execute-init-user-btn"
            onClick={handleInitUser}
            style={secondaryBtnStyle}
          >
            {labels.initUserButtonLabel}
          </button>
        </div>
      </div>
    </section>
  );
}
