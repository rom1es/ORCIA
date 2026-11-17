import React from "react";
import type {
  DeterministicSubStepItem,
  WorkflowDefinitionV2Item,
} from "../processStudioV2Data";
import type { InteractiveProcessDrawerStatus } from "./useInteractiveProcessRunController";

export interface InteractiveRunDeliverableAndHitlPanelsProps {
  readonly workflow: WorkflowDefinitionV2Item;
  readonly isFr: boolean;
  readonly status: InteractiveProcessDrawerStatus;
  readonly currentSubStep: DeterministicSubStepItem | undefined;
  readonly artifactMarkdown: string;
  readonly isEditingDiff: boolean;
  readonly signedTokenPreview: string | null;
  readonly returnLoopTargetStep: string;
  readonly returnLoopRemarks: string;
  readonly onChangeArtifactMarkdown: (val: string) => void;
  readonly onSetIsEditingDiff: (editing: boolean) => void;
  readonly onSimulateExternalWebhook: () => void;
  readonly onApproveCurrentSubStep: () => void;
  readonly onAction1AcceptAndSign: () => void;
  readonly onAction2SaveAmendedDiff: () => void;
  readonly onAction3RejectAndLoop: () => void;
  readonly onAction4SuspendSla: () => void;
  readonly onChangeReturnLoopTarget: (step: string) => void;
  readonly onChangeReturnLoopRemarks: (remarks: string) => void;
}

export function InteractiveRunDeliverableAndHitlPanels({
  workflow,
  isFr,
  status,
  currentSubStep,
  artifactMarkdown,
  isEditingDiff,
  signedTokenPreview,
  returnLoopTargetStep,
  returnLoopRemarks,
  onChangeArtifactMarkdown,
  onSetIsEditingDiff,
  onSimulateExternalWebhook,
  onApproveCurrentSubStep,
  onAction1AcceptAndSign,
  onAction2SaveAmendedDiff,
  onAction3RejectAndLoop,
  onAction4SuspendSla,
  onChangeReturnLoopTarget,
  onChangeReturnLoopRemarks,
}: InteractiveRunDeliverableAndHitlPanelsProps): React.JSX.Element {
  return (
    <>
      {status === "WAITING_EXTERNAL_GATE" ? (
        <div
          data-testid="external-delegated-gate-panel"
          className="flex flex-col gap-2 rounded border p-3.5"
          style={{ backgroundColor: "var(--color-arbitration-bg)", borderColor: "var(--color-arbitration-amber)" }}
        >
          <strong style={{ fontSize: "14px", color: "var(--color-arbitration-amber)" }}>
            🛠️ Réalisation en cours dans votre environnement de développement ({workflow.external_tool_label ?? "IDE / Git"})
          </strong>
          <div style={{ fontSize: "12.5px" }}>
            Le contexte métier et les critères d&apos;acceptation sont transmis à l&apos;équipe. Dès que la Pull Request est ouverte, ORCIA vérifie automatiquement la conformité du livrable avant la revue finale.
          </div>
          <div>
            <button type="button" data-testid="simulate-external-webhook-btn" onClick={onSimulateExternalWebhook} className="orcia-ds-btn-primary">
              {isFr ? "✓ Signaler la Pull Request prête pour contrôle" : "✓ Mark Pull Request ready for review"}
            </button>
          </div>
        </div>
      ) : null}

      <div
        data-testid="claim-check-s3-artifact-box"
        className="flex flex-col gap-2 rounded border p-3.5"
        style={{ backgroundColor: "var(--color-bg-elevated)", borderColor: "var(--color-border-subtle)" }}
      >
        <div className="flex flex-wrap items-center justify-between gap-2">
          <strong style={{ fontSize: "13.5px" }}>
            📄 {isFr ? "Livrable proposé" : "Proposed Deliverable"} — {currentSubStep?.name ?? workflow.title}
          </strong>
          <span style={{ fontSize: "12px", color: "var(--color-text-secondary)" }}>
            {currentSubStep?.output_description}
          </span>
        </div>

        {isEditingDiff ? (
          <div className="flex flex-col gap-2">
            <textarea
              aria-label="Contenu du livrable"
              data-testid="amend-diff-markdown-textarea"
              autoComplete="off"
              data-lpignore="true"
              data-1p-ignore="true"
              data-bwignore="true"
              data-form-type="other"
              rows={6}
              value={artifactMarkdown}
              onChange={(e) => onChangeArtifactMarkdown(e.target.value)}
              className="orcia-ds-textarea"
              style={{ fontSize: "13px" }}
            />
            <div className="flex gap-2">
              <button type="button" data-testid="confirm-amend-diff-btn" onClick={onAction2SaveAmendedDiff} className="orcia-ds-btn-primary">
                {isFr ? "💾 Enregistrer mes modifications" : "💾 Save changes"}
              </button>
              <button type="button" data-testid="cancel-amend-diff-btn" onClick={() => onSetIsEditingDiff(false)} className="orcia-ds-btn-secondary">
                {isFr ? "Annuler" : "Cancel"}
              </button>
            </div>
          </div>
        ) : (
          <pre
            data-testid="artifact-markdown-preview"
            style={{
              margin: 0,
              padding: "12px",
              borderRadius: "6px",
              backgroundColor: "var(--color-surface-card)",
              border: "1px solid var(--color-border-subtle)",
              fontSize: "13px",
              lineHeight: 1.5,
              whiteSpace: "pre-wrap",
            }}
          >
            {artifactMarkdown}
          </pre>
        )}
      </div>

      {status === "WAITING_WRITE_PREVIEW" ? (
        <div
          data-testid="write-preview-card-panel"
          className="flex flex-wrap items-center justify-between gap-2 rounded border p-3"
          style={{ backgroundColor: "var(--color-arbitration-bg)", borderColor: "var(--color-arbitration-amber)" }}
        >
          <div style={{ fontSize: "12.5px" }}>
            <strong>🛡️ Confirmation avant publication :</strong> Cette étape s&apos;apprête à créer ou mettre à jour un élément dans votre outil externe ({currentSubStep?.name ?? workflow.title}).
          </div>
          <button type="button" data-testid="sign-write-preview-token-btn" onClick={onApproveCurrentSubStep} className="orcia-ds-btn-primary">
            {isFr ? "✓ Confirmer la publication externe" : "✓ Confirm external publication"}
          </button>
        </div>
      ) : null}

      {signedTokenPreview ? (
        <div data-testid="signed-approval-token-badge" style={{ fontSize: "12px", color: "var(--color-gate-emerald)" }}>
          ✓ Publication externe confirmée ({signedTokenPreview})
        </div>
      ) : null}

      {status === "WAITING_SUBSTEP_HITL" && currentSubStep ? (
        <div className="flex flex-wrap gap-2">
          <button type="button" data-testid="approve-substep-checkpoint-btn" onClick={onApproveCurrentSubStep} className="orcia-ds-btn-primary">
            {isFr ? `✓ Valider « ${currentSubStep.short_label} » et passer à la suite` : `✓ Approve "${currentSubStep.short_label}" and continue`}
          </button>
          <button type="button" data-testid="open-amend-diff-editor-btn" onClick={() => onSetIsEditingDiff(true)} className="orcia-ds-btn-secondary">
            {isFr ? "✎ Modifier le livrable avant validation" : "✎ Edit deliverable"}
          </button>
        </div>
      ) : null}

      <div
        data-testid="anchor-card-four-actions-panel"
        className="flex flex-col gap-2.5 rounded border p-3.5"
        style={{ backgroundColor: "var(--color-human-led-bg)", borderColor: "var(--color-primary-cobalt)" }}
      >
        <div className="flex flex-wrap items-center justify-between">
          <strong style={{ fontSize: "14px" }}>
            {isFr ? "Décision & Validation du livrable" : "Deliverable Review & Decision"}
          </strong>
          <span style={{ fontSize: "12px", color: "var(--color-gate-emerald)", fontWeight: 600 }}>
            {isFr ? "✓ Contrôles automatiques de complétude : Conformes · Relecture contradictoire : Validée" : "✓ Automated checks: Passed · Peer review: Passed"}
          </span>
        </div>

        <div className="flex flex-wrap gap-2">
          <button type="button" data-testid="anchor-action-1-accept-btn" onClick={onAction1AcceptAndSign} className="orcia-ds-btn-primary">
            {isFr ? "✓ Valider et publier le livrable" : "✓ Approve & publish"}
          </button>
          <button type="button" data-testid="anchor-action-2-amend-diff-btn" onClick={() => onSetIsEditingDiff(true)} className="orcia-ds-btn-secondary">
            {isFr ? "✎ Modifier le texte" : "✎ Edit text"}
          </button>
          <button type="button" data-testid="anchor-action-3-reject-loop-btn" onClick={onAction3RejectAndLoop} className="orcia-ds-btn-secondary">
            {isFr ? `↩ Demander des corrections (→ Étape ${returnLoopTargetStep})` : `↩ Request corrections (→ Step ${returnLoopTargetStep})`}
          </button>
          <button type="button" data-testid="anchor-action-4-suspend-sla-btn" onClick={onAction4SuspendSla} className="orcia-ds-btn-secondary">
            {isFr ? "⏸ Mettre en pause" : "⏸ Pause"}
          </button>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "minmax(200px, 260px) 1fr", gap: "8px", alignItems: "center" }}>
          <select
            aria-label="Étape cible pour reprise"
            data-testid="anchor-return-loop-target-select"
            value={returnLoopTargetStep}
            onChange={(e) => onChangeReturnLoopTarget(e.target.value)}
            className="orcia-ds-select"
          >
            <option value="01">Renvoyer à l&apos;Étape 01 (Qualification)</option>
            <option value="02">Renvoyer à l&apos;Étape 02 (Revue du PRD)</option>
            <option value="03">Renvoyer à l&apos;Étape 03 (Étude d&apos;Architecture)</option>
            <option value="06">Renvoyer à l&apos;Étape 06 (Découpage User Stories)</option>
            <option value="08">Renvoyer à l&apos;Étape 08 (Réalisation)</option>
          </select>

          <input
            type="text"
            aria-label="Commentaire de correction"
            data-testid="anchor-return-loop-remarks-input"
            autoComplete="off"
            data-lpignore="true"
            data-1p-ignore="true"
            data-bwignore="true"
            data-form-type="other"
            value={returnLoopRemarks}
            onChange={(e) => onChangeReturnLoopRemarks(e.target.value)}
            placeholder={isFr ? "Précisez les points à corriger..." : "Specify required changes..."}
            className="orcia-ds-input"
          />
        </div>
      </div>
    </>
  );
}
