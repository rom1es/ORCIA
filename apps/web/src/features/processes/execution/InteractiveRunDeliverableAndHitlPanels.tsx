import { FormattedMarkdownContent } from "@orcia/ui";
import React from "react";
import { formatI18nTemplate, resolveDictionaryForFlag } from "../../../i18n";
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
  readonly isStartingRun?: boolean;
  readonly isSubmittingDecision?: boolean;
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
  isStartingRun = false,
  isSubmittingDecision = false,
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
  const copy = resolveDictionaryForFlag(isFr).processVsmExecutionUi.execution;
  const isActionDisabled = Boolean(isStartingRun || isSubmittingDecision);

  return (
    <>
      {status === "WAITING_EXTERNAL_GATE" ? (
        <div
          data-testid="external-delegated-gate-panel"
          className="flex flex-col gap-2 rounded border p-3.5"
          style={{ backgroundColor: "var(--color-arbitration-bg)", borderColor: "var(--color-arbitration-amber)" }}
        >
          <strong style={{ fontSize: "14px", color: "var(--color-arbitration-amber)" }}>
            {formatI18nTemplate(copy.externalGateHeadingTemplate, {
              tool: workflow.external_tool_label ?? "IDE / Git",
            })}
          </strong>
          <div style={{ fontSize: "12.5px" }}>{copy.externalGateDescription}</div>
          <div>
            <button
              type="button"
              data-testid="simulate-external-webhook-btn"
              onClick={onSimulateExternalWebhook}
              className="orcia-ds-btn-primary"
            >
              {copy.markPrReadyBtn}
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
            📄 {copy.proposedDeliverablePrefix} — {currentSubStep?.name ?? workflow.title}
          </strong>
          <span style={{ fontSize: "12px", color: "var(--color-text-secondary)" }}>
            {currentSubStep?.output_description}
          </span>
        </div>

        {isEditingDiff ? (
          <div className="flex flex-col gap-2">
            <textarea
              aria-label={copy.deliverableContentAriaLabel}
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
              <button
                type="button"
                data-testid="confirm-amend-diff-btn"
                onClick={onAction2SaveAmendedDiff}
                className="orcia-ds-btn-primary"
              >
                {copy.saveChangesBtn}
              </button>
              <button
                type="button"
                data-testid="cancel-amend-diff-btn"
                onClick={() => onSetIsEditingDiff(false)}
                className="orcia-ds-btn-secondary"
              >
                {copy.cancelBtn}
              </button>
            </div>
          </div>
        ) : (
          <div
            data-testid="artifact-markdown-preview"
            className="rounded-md border border-border-subtle bg-surface-card p-3"
          >
            <FormattedMarkdownContent
              content={artifactMarkdown}
              testId="artifact-markdown-formatted"
            />
          </div>
        )}
      </div>

      {status === "WAITING_WRITE_PREVIEW" ? (
        <div
          data-testid="write-preview-card-panel"
          className="flex flex-wrap items-center justify-between gap-2 rounded border p-3"
          style={{ backgroundColor: "var(--color-arbitration-bg)", borderColor: "var(--color-arbitration-amber)" }}
        >
          <div style={{ fontSize: "12.5px" }}>
            <strong>{copy.writePreviewStrongPrefix}</strong>{" "}
            {formatI18nTemplate(copy.writePreviewMessageTemplate, {
              target: currentSubStep?.name ?? workflow.title,
            })}
          </div>
          <button
            type="button"
            data-testid="sign-write-preview-token-btn"
            onClick={onApproveCurrentSubStep}
            className="orcia-ds-btn-primary"
          >
            {copy.confirmExternalPubBtn}
          </button>
        </div>
      ) : null}

      {signedTokenPreview ? (
        <div data-testid="signed-approval-token-badge" style={{ fontSize: "12px", color: "var(--color-gate-emerald)" }}>
          {formatI18nTemplate(copy.signedTokenBadgeTemplate, { token: signedTokenPreview })}
        </div>
      ) : null}

      {status === "WAITING_SUBSTEP_HITL" && currentSubStep ? (
        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            data-testid="approve-substep-checkpoint-btn"
            disabled={isActionDisabled}
            onClick={onApproveCurrentSubStep}
            className="orcia-ds-btn-primary"
          >
            {formatI18nTemplate(copy.approveSubstepBtnTemplate, {
              step: currentSubStep.short_label,
            })}
          </button>
          <button
            type="button"
            data-testid="open-amend-diff-editor-btn"
            disabled={isActionDisabled}
            onClick={() => onSetIsEditingDiff(true)}
            className="orcia-ds-btn-secondary"
          >
            {copy.editDeliverableBtn}
          </button>
        </div>
      ) : null}

      <div
        data-testid="anchor-card-four-actions-panel"
        className="flex flex-col gap-2.5 rounded border p-3.5"
        style={{ backgroundColor: "var(--color-human-led-bg)", borderColor: "var(--color-primary-cobalt)" }}
      >
        <div className="flex flex-wrap items-center justify-between">
          <strong style={{ fontSize: "14px" }}>{copy.decisionSectionTitle}</strong>
          {isStartingRun ? (
            <span data-testid="run-drawer-starting-indicator" style={{ fontSize: "12px", color: "var(--color-text-secondary)", fontWeight: 600 }}>
              {copy.startingRunIndicator}
            </span>
          ) : (
            <span style={{ fontSize: "12px", color: "var(--color-gate-emerald)", fontWeight: 600 }}>
              {copy.automatedChecksPassedIndicator}
            </span>
          )}
        </div>

        <div className="flex flex-wrap gap-2">
          <button
            type="button"
            data-testid="anchor-action-1-accept-btn"
            disabled={isActionDisabled}
            aria-busy={isActionDisabled}
            onClick={() => { void onAction1AcceptAndSign(); }}
            className="orcia-ds-btn-primary"
          >
            {isSubmittingDecision ? copy.submittingBtn : copy.approveAndPublishBtn}
          </button>
          <button
            type="button"
            data-testid="anchor-action-2-amend-diff-btn"
            disabled={isActionDisabled}
            onClick={() => onSetIsEditingDiff(true)}
            className="orcia-ds-btn-secondary"
          >
            {copy.editTextBtn}
          </button>
          <button
            type="button"
            data-testid="anchor-action-3-reject-loop-btn"
            disabled={isActionDisabled}
            onClick={onAction3RejectAndLoop}
            className="orcia-ds-btn-secondary"
          >
            {formatI18nTemplate(copy.requestCorrectionsBtnTemplate, {
              step: returnLoopTargetStep,
            })}
          </button>
          <button
            type="button"
            data-testid="anchor-action-4-suspend-sla-btn"
            disabled={isActionDisabled}
            onClick={onAction4SuspendSla}
            className="orcia-ds-btn-secondary"
          >
            {copy.pauseBtn}
          </button>
        </div>

        <div style={{ display: "grid", gridTemplateColumns: "minmax(200px, 260px) 1fr", gap: "8px", alignItems: "center" }}>
          <select
            aria-label={copy.returnStepSelectAriaLabel}
            data-testid="anchor-return-loop-target-select"
            value={returnLoopTargetStep}
            onChange={(e) => onChangeReturnLoopTarget(e.target.value)}
            className="orcia-ds-select"
          >
            {copy.returnStepOptions.map((opt) => (
              <option key={opt.value} value={opt.value}>
                {opt.label}
              </option>
            ))}
          </select>

          <input
            type="text"
            aria-label={copy.returnRemarksAriaLabel}
            data-testid="anchor-return-loop-remarks-input"
            autoComplete="off"
            data-lpignore="true"
            data-1p-ignore="true"
            data-bwignore="true"
            data-form-type="other"
            value={returnLoopRemarks}
            onChange={(e) => onChangeReturnLoopRemarks(e.target.value)}
            placeholder={copy.returnRemarksPlaceholder}
            className="orcia-ds-input"
          />
        </div>
      </div>
    </>
  );
}
