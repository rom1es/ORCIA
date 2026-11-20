import type {
  RunBlackboardStateResponse,
  WorkflowAsCodeDefinitionSchemaItem,
} from "@orcia/api-client";
import {
  ArbitrationTieBreakCard,
  HumanLedAnchorCard,
  OrciaAlertBanner,
  StatusBadge,
} from "@orcia/ui";
import React from "react";
import { formatStepStatusLabel } from "./cockpitGovernanceHelpers";
import { useCockpitGovernanceController } from "./useCockpitGovernanceController";

export interface CockpitHumanLedGovernanceSectionProps {
  readonly runId: string;
  readonly workflow?: WorkflowAsCodeDefinitionSchemaItem | null;
  readonly initialBlackboard?: RunBlackboardStateResponse | null;
  readonly authorName: string;
  readonly refreshSignal?: number;
  readonly onGovernanceStateChanged?: () => void;
}

export function CockpitHumanLedGovernanceSection({
  runId,
  workflow = null,
  initialBlackboard = null,
  authorName,
  refreshSignal = 0,
  onGovernanceStateChanged,
}: CockpitHumanLedGovernanceSectionProps): React.ReactElement | null {
  const ctrl = useCockpitGovernanceController({
    runId,
    workflow,
    initialBlackboard,
    authorName,
    refreshSignal,
    onGovernanceStateChanged,
  });

  if (!ctrl.pendingAnchor && !ctrl.pendingArbitration && !ctrl.errorBanner) {
    return null;
  }

  return (
    <section
      data-testid="cockpit-human-led-governance-section"
      data-run-id={ctrl.serverRunId}
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
              ? "Gouvernance Human-Led : Action requise"
              : "Human-Led Governance: Action Required"}
          </h2>
          <p
            style={{
              margin: "4px 0 0 0",
              fontSize: "13px",
              color: "var(--color-muted-foreground)",
            }}
          >
            {ctrl.pendingAnchor && ctrl.pendingArbitration
              ? ctrl.isFr
                ? "Signez l'intention obligatoire (≥ 30 caractères) et départagez les options en attente."
                : "Sign the mandatory intent (≥ 30 characters) and resolve pending option tie-breaks."
              : ctrl.pendingAnchor
                ? ctrl.isFr
                  ? "Rédigez et signez l'ancrage humain obligatoire (≥ 30 caractères) pour débloquer la suite du processus."
                  : "Author and sign the mandatory human anchor (≥ 30 characters) to unblock process execution."
                : ctrl.isFr
                  ? "Départagez les options en attente pour reprendre l'exécution du processus."
                  : "Resolve the pending option tie-break to resume process execution."}
          </p>
        </div>
        <StatusBadge
          testId="cockpit-step-status-badge"
          label={formatStepStatusLabel(ctrl.stepStatus, ctrl.isFr)}
          tone="amber"
        />
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

      {ctrl.pendingAnchor && (
        <HumanLedAnchorCard
          testId="cockpit-human-led-anchor-card"
          justificationTestId="cockpit-human-anchor-textarea"
          signatureTestId="cockpit-human-anchor-signature-input"
          sectionKey={ctrl.pendingAnchor.sectionKey}
          sectionTitle={
            ctrl.pendingAnchor.sectionTitle || ctrl.dictionary.humanAnchor.defaultSectionTitle
          }
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
      )}

      {ctrl.pendingArbitration && (
        <ArbitrationTieBreakCard
          testId="cockpit-arbitration-tiebreak-card"
          arbitrationId={ctrl.pendingArbitration.arbitrationId}
          stepKey={ctrl.pendingArbitration.stepKey}
          questionTitle={ctrl.pendingArbitration.questionTitle}
          contextSummary={ctrl.pendingArbitration.contextSummary}
          tieBreakPolicy={ctrl.pendingArbitration.tieBreakPolicy}
          options={ctrl.pendingArbitration.options}
          selectedOptionKey={null}
          labels={ctrl.dictionary.arbitrationTieBreak}
          onSelectOption={(optKey, justification) =>
            void ctrl.handleResolveArbitration(optKey, justification)
          }
        />
      )}
    </section>
  );
}
