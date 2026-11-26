import {
  HumanLedAnchorCard,
  OrciaIcon,
  StatusBadge,
  type HumanLedAnchorCardLabels,
} from "@orcia/ui";
import React, { useState } from "react";
import { formatI18nTemplate, resolveDictionaryForFlag } from "../../../i18n";
import type {
  DeterministicSubStepItem,
  WorkflowDefinitionV2Item,
} from "../processStudioV2Data";
import { ProcessRunCorrectionPopover } from "./ProcessRunCorrectionPopover";
import type { InteractiveProcessDrawerStatus } from "./useInteractiveProcessRunController";

export interface ProcessRunActionBannerProps {
  readonly workflow: WorkflowDefinitionV2Item;
  readonly isFr: boolean;
  readonly status: InteractiveProcessDrawerStatus;
  readonly statusLabel: string;
  readonly currentSubStep: DeterministicSubStepItem | undefined;
  readonly iteration: number;
  readonly reentryMode: "initial" | "corrections";
  readonly signedTokenPreview: string | null;
  readonly returnLoopTargetStep: string;
  readonly returnLoopRemarks: string;
  readonly isStartingRun?: boolean;
  readonly isSubmittingDecision?: boolean;
  readonly isSticky?: boolean;
  readonly authorName?: string;
  readonly humanAnchorValue?: string;
  readonly humanAnchorLabels?: HumanLedAnchorCardLabels;
  readonly onChangeHumanAnchorValue?: (value: string) => void;
  readonly onSimulateExternalWebhook: () => void;
  readonly onApproveCurrentSubStep: () => void;
  readonly onAction1AcceptAndSign: () => void;
  readonly onAction3RejectAndLoop: () => void;
  readonly onAction4SuspendSla: () => void;
  readonly onChangeReturnLoopTarget: (step: string) => void;
  readonly onChangeReturnLoopRemarks: (remarks: string) => void;
}

export function ProcessRunActionBanner({
  workflow,
  isFr,
  status,
  statusLabel,
  currentSubStep,
  iteration,
  reentryMode,
  signedTokenPreview,
  returnLoopTargetStep,
  returnLoopRemarks,
  isStartingRun = false,
  isSubmittingDecision = false,
  isSticky = true,
  authorName = "",
  humanAnchorValue = "",
  humanAnchorLabels,
  onChangeHumanAnchorValue,
  onSimulateExternalWebhook,
  onApproveCurrentSubStep,
  onAction1AcceptAndSign,
  onAction3RejectAndLoop,
  onAction4SuspendSla,
  onChangeReturnLoopTarget,
  onChangeReturnLoopRemarks,
}: ProcessRunActionBannerProps): React.JSX.Element {
  const dictionary = resolveDictionaryForFlag(isFr);
  const copy = dictionary.processVsmExecutionUi.execution;
  const resolvedAnchorLabels = humanAnchorLabels ?? dictionary.humanAnchor;
  const [correctionOpen, setCorrectionOpen] = useState(false);

  const isActionDisabled = Boolean(isStartingRun || isSubmittingDecision);
  const isCompleted = status === "COMPLETED_APPROVED";
  const isPaused = status === "SLA_SUSPENDED";
  const isRunning = status === "RUNNING";
  const isPendingDecision = !isCompleted && !isPaused && !isRunning;
  const humanAuthoredRequired = Boolean(
    currentSubStep?.human_authored_required || workflow.human_authored_required,
  );

  if (humanAuthoredRequired && isPendingDecision) {
    return (
      <div
        data-testid="process-run-zone1-action-banner"
        style={isSticky ? { position: "sticky", top: 0, zIndex: 20 } : undefined}
      >
        <HumanLedAnchorCard
          sectionKey={currentSubStep?.id ?? workflow.id}
          sectionTitle={currentSubStep?.name ?? workflow.title}
          authorName={authorName || dictionary.humanAnchor.defaultAuthorName}
          value={humanAnchorValue}
          labels={resolvedAnchorLabels}
          onChange={onChangeHumanAnchorValue}
          onSignAnchor={() => {
            void onAction1AcceptAndSign();
          }}
        />
      </div>
    );
  }

  const bannerToneStyles = isCompleted
    ? {
        backgroundColor: "var(--color-gate-emerald-bg)",
        borderColor: "var(--color-gate-emerald)",
        borderLeft: "4px solid var(--color-gate-emerald)",
      }
    : isPendingDecision
      ? {
          backgroundColor: "var(--color-arbitration-bg)",
          borderColor: "var(--color-arbitration-amber)",
          borderLeft: "4px solid var(--color-arbitration-amber)",
        }
      : {
          backgroundColor: "var(--color-surface-card)",
          borderColor: "var(--color-border-subtle)",
          borderLeft: "4px solid var(--color-primary-cobalt)",
        };

  const bannerHeadline = isCompleted
    ? copy.focusActionBannerCompletedTitle
    : isPaused
      ? copy.focusActionBannerPausedTitle
      : isRunning
        ? copy.focusActionBannerRunningTitle
        : copy.focusActionBannerPendingTitle;

  const renderSinglePrimaryCta = () => {
    if (isCompleted || isPaused) return null;
    if (status === "WAITING_EXTERNAL_GATE") {
      return (
        <button
          type="button"
          data-testid="simulate-external-webhook-btn"
          disabled={isActionDisabled}
          onClick={onSimulateExternalWebhook}
          className="orcia-ds-btn orcia-ds-btn-primary orcia-ds-btn-sm orcia-ds-nowrap"
        >
          {copy.markPrReadyBtn}
        </button>
      );
    }
    if (status === "WAITING_WRITE_PREVIEW") {
      return (
        <button
          type="button"
          data-testid="sign-write-preview-token-btn"
          disabled={isActionDisabled}
          onClick={onApproveCurrentSubStep}
          className="orcia-ds-btn orcia-ds-btn-primary orcia-ds-btn-sm orcia-ds-nowrap"
        >
          {copy.confirmExternalPubBtn}
        </button>
      );
    }
    if (status === "WAITING_SUBSTEP_HITL" && currentSubStep) {
      return (
        <button
          type="button"
          data-testid="approve-substep-checkpoint-btn"
          disabled={isActionDisabled}
          aria-busy={isActionDisabled}
          onClick={onApproveCurrentSubStep}
          className="orcia-ds-btn orcia-ds-btn-primary orcia-ds-btn-sm orcia-ds-nowrap"
        >
          {formatI18nTemplate(copy.approveSubstepBtnTemplate, {
            step: currentSubStep.short_label,
          })}
        </button>
      );
    }
    return (
      <button
        type="button"
        data-testid="anchor-action-1-accept-btn"
        disabled={isActionDisabled}
        aria-busy={isActionDisabled}
        onClick={() => {
          void onAction1AcceptAndSign();
        }}
        className="orcia-ds-btn orcia-ds-btn-primary orcia-ds-btn-sm orcia-ds-nowrap"
      >
        {isSubmittingDecision ? copy.submittingBtn : copy.approveAndPublishBtn}
      </button>
    );
  };

  return (
    <section
      data-testid="process-run-zone1-action-banner"
      aria-label={bannerHeadline}
      className="flex flex-col gap-3 rounded-lg border p-4 shadow-sm"
      style={{
        ...bannerToneStyles,
        ...(isSticky ? { position: "sticky", top: 0, zIndex: 20 } : {}),
      }}
    >
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex flex-col gap-1">
          <div className="flex flex-wrap items-center gap-2">
            <OrciaIcon
              name={isCompleted ? "check" : isPaused ? "clock" : isRunning ? "hourglass" : "shield"}
              size={15}
            />
            <strong style={{ fontSize: "14px", color: "var(--color-text-primary)" }}>
              {bannerHeadline}
            </strong>
            <StatusBadge
              tone={isCompleted ? "emerald" : isPendingDecision ? "amber" : "cobalt"}
              label={statusLabel}
            />
            {reentryMode === "corrections" ? (
              <StatusBadge
                tone="amber"
                label={formatI18nTemplate(copy.correctionCycleTemplate, { iteration })}
              />
            ) : null}
          </div>
          <p className="m-0 text-xs" style={{ color: "var(--color-text-secondary)" }}>
            {isStartingRun ? copy.startingRunIndicator : copy.focusActionBannerPendingHint}
          </p>
          {signedTokenPreview ? (
            <div
              data-testid="signed-approval-token-badge"
              className="text-xs font-medium"
              style={{ color: "var(--color-gate-emerald)" }}
            >
              {formatI18nTemplate(copy.signedTokenBadgeTemplate, { token: signedTokenPreview })}
            </div>
          ) : null}
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {renderSinglePrimaryCta()}
          {!isCompleted ? (
            <button
              type="button"
              data-testid="toggle-request-corrections-popover-btn"
              disabled={isActionDisabled}
              aria-expanded={correctionOpen}
              onClick={() => setCorrectionOpen((prev) => !prev)}
              className="orcia-ds-btn orcia-ds-btn-secondary orcia-ds-btn-sm orcia-ds-nowrap"
            >
              {copy.requestChangesBtn}
            </button>
          ) : null}
          {!isCompleted && !isPaused ? (
            <button
              type="button"
              data-testid="anchor-action-4-suspend-sla-btn"
              disabled={isActionDisabled}
              onClick={onAction4SuspendSla}
              className="orcia-ds-btn orcia-ds-btn-secondary orcia-ds-btn-sm orcia-ds-nowrap"
            >
              {copy.pauseBtn}
            </button>
          ) : null}
        </div>
      </div>

      {correctionOpen && !isCompleted ? (
        <ProcessRunCorrectionPopover
          copy={copy}
          isActionDisabled={isActionDisabled}
          returnLoopTargetStep={returnLoopTargetStep}
          returnLoopRemarks={returnLoopRemarks}
          onChangeReturnLoopTarget={onChangeReturnLoopTarget}
          onChangeReturnLoopRemarks={onChangeReturnLoopRemarks}
          onCancel={() => setCorrectionOpen(false)}
          onSubmitCorrections={() => {
            onAction3RejectAndLoop();
            setCorrectionOpen(false);
          }}
        />
      ) : null}
    </section>
  );
}
