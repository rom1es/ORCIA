import {
  ArbitrationTieBreakCard,
  HumanLedAnchorCard,
  OrciaAlertBanner,
  StatusBadge,
} from "@orcia/ui";
import React from "react";
import {
  DEFAULT_ARBITRATION_OPTIONS,
  DEFAULT_SECTION_KEY,
  DEFAULT_STEP_KEY,
} from "./cockpitGovernanceHelpers";
import { CockpitUpstreamChallengePanel } from "./CockpitUpstreamChallengePanel";
import { useCockpitGovernanceController } from "./useCockpitGovernanceController";

export interface CockpitHumanLedGovernanceSectionProps {
  readonly workspaceId?: string;
  readonly authorName: string;
  readonly refreshSignal?: number;
  readonly activeRunId?: string | null;
}

export function CockpitHumanLedGovernanceSection({
  workspaceId,
  authorName,
  refreshSignal = 0,
  activeRunId = null,
}: CockpitHumanLedGovernanceSectionProps) {
  const ctrl = useCockpitGovernanceController({
    workspaceId,
    authorName,
    refreshSignal,
    activeRunId,
  });

  return (
    <section
      data-testid="cockpit-human-led-governance-section"
      data-run-id={ctrl.serverRunId ?? ""}
      data-step-status={ctrl.stepStatus}
      className="orcia-bento-card"
      style={{ display: "flex", flexDirection: "column", gap: "16px" }}
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
          <h2 style={{ margin: 0, fontSize: "16px", fontWeight: 700 }}>
            {ctrl.isFr
              ? "Gouvernance Human-Led : Ancrage obligatoire & Arbitrage"
              : "Human-Led Governance: Mandatory Anchor & Arbitration"}
          </h2>
          <p
            style={{
              margin: "4px 0 0 0",
              fontSize: "13px",
              color: "var(--color-muted-foreground)",
            }}
          >
            {ctrl.isFr
              ? "Signez l'intention d'architecture (≥ 30 caractères) puis départagez les options en attente."
              : "Sign the architecture intent (≥ 30 characters) then resolve pending option tie-breaks."}
          </p>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <button
            type="button"
            data-testid="cockpit-request-arbitration-btn"
            onClick={() => void ctrl.handleRequestArbitration()}
            style={{
              padding: "6px 12px",
              borderRadius: "var(--radius-sm)",
              border: "1px solid var(--color-border)",
              backgroundColor: "var(--color-surface-bg)",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            {ctrl.isFr ? "Escalader en arbitrage humain" : "Escalate to human arbitration"}
          </button>
          <StatusBadge
            label={ctrl.stepStatus}
            tone={ctrl.stepStatus === "COMMITTED" ? "emerald" : "amber"}
            monospace
          />
        </div>
      </div>

      {ctrl.errorBanner && (
        <OrciaAlertBanner
          tone="crimson"
          role="alert"
          testId="cockpit-human-led-error-banner"
        >
          {ctrl.errorBanner}
        </OrciaAlertBanner>
      )}

      <HumanLedAnchorCard
        testId="cockpit-human-led-anchor-card"
        justificationTestId="cockpit-human-anchor-textarea"
        signatureTestId="cockpit-human-anchor-signature-input"
        sectionKey={DEFAULT_SECTION_KEY}
        sectionTitle={ctrl.dictionary.humanAnchor.defaultSectionTitle}
        authorName={ctrl.resolvedAuthorName}
        value={ctrl.anchorText}
        signatureLabel={ctrl.isFr ? "Signature de l'auteur" : "Author signature"}
        signatureValue={ctrl.signatureText}
        signaturePlaceholder={ctrl.resolvedAuthorName}
        labels={ctrl.dictionary.humanAnchor}
        onChange={ctrl.setAnchorText}
        onSignatureChange={ctrl.setSignatureText}
        onSignAnchor={(secKey, content) => void ctrl.handleSignAnchor(secKey, content)}
      />

      {ctrl.signedSha256 && (
        <div
          data-testid="cockpit-human-anchor-signed-badge"
          style={{
            padding: "8px 12px",
            borderRadius: "var(--radius-sm)",
            backgroundColor: "var(--color-gate-emerald-bg)",
            color: "var(--color-gate-emerald)",
            fontFamily: "var(--font-mono)",
            fontSize: "12px",
            fontWeight: 600,
          }}
        >
          {ctrl.isFr
            ? `✓ Ancrage humain signé (SHA-256 : ${ctrl.signedSha256.slice(0, 16)}…)`
            : `✓ Human anchor signed (SHA-256: ${ctrl.signedSha256.slice(0, 16)}…)`}
        </div>
      )}

      <CockpitUpstreamChallengePanel
        runId={ctrl.serverRunId}
        isOpen={Boolean(ctrl.signedSha256 && ctrl.serverRunId)}
        initialStaleWarning={ctrl.hasStaleWarning}
        onError={ctrl.setErrorBanner}
        onReplayCompleted={() => {
          if (ctrl.serverRunId) {
            void ctrl.hydrateFromRun(ctrl.serverRunId);
          }
        }}
      />

      <ArbitrationTieBreakCard
        testId="cockpit-arbitration-tiebreak-card"
        arbitrationId={ctrl.pendingArbitrationId ?? "cockpit-arb"}
        stepKey={DEFAULT_STEP_KEY}
        questionTitle={ctrl.dictionary.arbitrationTieBreak.defaultQuestionTitle}
        contextSummary={ctrl.dictionary.arbitrationTieBreak.defaultContextSummary}
        tieBreakPolicy="PAUSE_AND_ESCALATE"
        options={DEFAULT_ARBITRATION_OPTIONS}
        selectedOptionKey={ctrl.resolvedOptionKey}
        labels={ctrl.dictionary.arbitrationTieBreak}
        onSelectOption={(optKey, justification) =>
          void ctrl.handleResolveArbitration(optKey, justification)
        }
      />

      {ctrl.resolvedOptionKey && (
        <div
          data-testid="cockpit-arbitration-resolved-summary"
          data-selected-option={ctrl.resolvedOptionKey}
          data-committed-snapshot-id={ctrl.committedSnapshotId ?? ""}
          style={{
            padding: "8px 12px",
            borderRadius: "var(--radius-sm)",
            border: "1px solid var(--color-border)",
            backgroundColor: "var(--color-surface-bg)",
            fontSize: "13px",
          }}
        >
          <strong>{ctrl.resolvedOptionKey}</strong>
          {ctrl.resolvedJustification ? ` — ${ctrl.resolvedJustification}` : ""}
        </div>
      )}
    </section>
  );
}
