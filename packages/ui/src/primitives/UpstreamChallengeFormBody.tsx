import * as DialogPrimitive from "@radix-ui/react-dialog";
import React from "react";
import { DisabledButtonAlertIndicator } from "../components/DisabledButtonAlertIndicator";
import { OrciaIcon } from "../components/icons";
import {
  RgaaUnsavedChangesAlert,
  handleRgaaSubmitKeyDown,
  type RgaaModalGuardLabels,
} from "../components/RgaaModalDialog.js";
import type {
  UpstreamChallengeModalLabels,
  UpstreamChallengeWhatIfPreview,
} from "./UpstreamChallengeRewindModalTypes";
import { UpstreamChallengeTargetMetaGrid } from "./UpstreamChallengeTargetMetaGrid";
import { UpstreamChallengeWhatIfPreviewCard } from "./UpstreamChallengeWhatIfPreviewCard";

const headerTitleStyle: React.CSSProperties = {
  margin: 0,
  fontSize: "0.75rem",
  fontWeight: 700,
  textTransform: "uppercase",
  color: "var(--color-arbitration-amber)",
  letterSpacing: "0.04em",
};
const headerSubtitleStyle: React.CSSProperties = {
  margin: "2px 0 0 0",
  fontSize: "0.8125rem",
  color: "var(--color-text-secondary)",
};

export interface UpstreamChallengeFormBodyProps {
  readonly inline: boolean;
  readonly preview: UpstreamChallengeWhatIfPreview;
  readonly labels: UpstreamChallengeModalLabels;
  readonly resolvedRgaaLabels: RgaaModalGuardLabels;
  readonly subWorkflowStepKey?: string;
  readonly reason: string;
  readonly canSubmit: boolean;
  readonly showUnsavedConfirm: boolean;
  readonly submittedChallenge: boolean;
  readonly replayed: boolean;
  readonly hasClose: boolean;
  readonly onReasonInput: (nextVal: string) => void;
  readonly onStay: () => void;
  readonly onDiscard: () => void;
  readonly onRequestClose: () => void;
  readonly onSubmitChallenge: () => void;
  readonly onReplay: () => void;
}

export function UpstreamChallengeFormBody({
  inline,
  preview,
  labels,
  resolvedRgaaLabels,
  subWorkflowStepKey,
  reason,
  canSubmit,
  showUnsavedConfirm,
  submittedChallenge,
  replayed,
  hasClose,
  onReasonInput,
  onStay,
  onDiscard,
  onRequestClose,
  onSubmitChallenge,
  onReplay,
}: UpstreamChallengeFormBodyProps): React.ReactElement {
  return (
    <>
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: "8px",
          flexWrap: "wrap",
          flexShrink: 0,
        }}
      >
        <div>
          {inline ? (
            <>
              <h3 style={headerTitleStyle}>
                <OrciaIcon name="lightning" /> {labels.modalTitle}
              </h3>
              <p style={headerSubtitleStyle}>{labels.modalSubtitle}</p>
            </>
          ) : (
            <>
              <DialogPrimitive.Title style={headerTitleStyle}>
                <OrciaIcon name="lightning" /> {labels.modalTitle}
              </DialogPrimitive.Title>
              <DialogPrimitive.Description style={headerSubtitleStyle}>
                {labels.modalSubtitle}
              </DialogPrimitive.Description>
            </>
          )}
        </div>
      </div>

      <div className="orcia-ds-dialog-body">
        {showUnsavedConfirm ? (
          <RgaaUnsavedChangesAlert
            testIdPrefix="upstream-challenge"
            labels={resolvedRgaaLabels}
            onStay={onStay}
            onDiscard={onDiscard}
          />
        ) : null}

        <UpstreamChallengeTargetMetaGrid
          labels={labels}
          preview={preview}
          {...(subWorkflowStepKey ? { subWorkflowStepKey } : {})}
        />

        <label
          style={{
            display: "flex",
            flexDirection: "column",
            gap: "4px",
            fontSize: "0.75rem",
            fontWeight: 600,
            color: "var(--color-text-primary)",
          }}
        >
          {labels.reasonLabel}
          <textarea
            autoComplete="off"
            data-lpignore="true"
            data-1p-ignore="true"
            data-bwignore="true"
            data-form-type="other"
            value={reason}
            onChange={(e) => onReasonInput(e.target.value)}
            placeholder={labels.reasonPlaceholder}
            rows={2}
            data-testid="upstream-challenge-reason-input"
            style={{
              width: "100%",
              padding: "8px",
              borderRadius: "var(--radius-sm)",
              border: "1px solid var(--color-border-subtle)",
              backgroundColor: "var(--color-surface-canvas)",
              color: "var(--color-text-primary)",
              fontFamily: "var(--font-sans)",
              fontSize: "0.8125rem",
            }}
          />
        </label>

        <UpstreamChallengeWhatIfPreviewCard preview={preview} labels={labels} />
      </div>

      <div className="orcia-ds-dialog-footer" style={{ justifyContent: "flex-start" }}>
        {hasClose ? (
          <button
            type="button"
            onClick={onRequestClose}
            data-testid="upstream-challenge-cancel-btn"
            className="orcia-ds-btn orcia-ds-btn-secondary orcia-ds-btn-sm"
          >
            {resolvedRgaaLabels.cancelCta}
          </button>
        ) : null}
        <button
          type="button"
          disabled={!canSubmit}
          onClick={onSubmitChallenge}
          onKeyDown={(e) => handleRgaaSubmitKeyDown(e, onSubmitChallenge, !canSubmit)}
          data-testid="upstream-challenge-submit-btn"
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: "6px",
            padding: "6px 12px",
            fontSize: "0.75rem",
            fontWeight: 600,
            borderRadius: "var(--radius-sm)",
            border: "1px solid var(--color-arbitration-amber)",
            backgroundColor: "var(--color-arbitration-amber)",
            color: "var(--color-surface-card)",
            cursor: canSubmit ? "pointer" : "not-allowed",
            opacity: canSubmit ? 1 : 0.5,
          }}
        >
          <span>{labels.submitChallengeCta}</span>
          <DisabledButtonAlertIndicator
            disabled={!canSubmit}
            reason={labels.submitDisabledReason ?? labels.reasonPlaceholder}
            testIdSuffix="upstream-challenge-submit-btn"
          />
        </button>
        <button
          type="button"
          onClick={onReplay}
          onKeyDown={(e) => handleRgaaSubmitKeyDown(e, onReplay)}
          data-testid="upstream-replay-trigger-btn"
          style={{
            padding: "6px 12px",
            fontSize: "0.75rem",
            fontWeight: 600,
            borderRadius: "var(--radius-sm)",
            border: "1px solid var(--color-gate-pass)",
            backgroundColor: "var(--color-gate-pass-bg)",
            color: "var(--color-gate-pass)",
            cursor: "pointer",
          }}
        >
          {labels.replayStepCta}
        </button>
        {submittedChallenge ? (
          <span
            role="status"
            data-testid="upstream-challenge-feedback"
            style={{
              fontSize: "0.75rem",
              fontWeight: 600,
              color: "var(--color-arbitration-amber)",
            }}
          >
            {labels.challengeSubmittedFeedback}
          </span>
        ) : null}
        {replayed ? (
          <span
            role="status"
            data-testid="upstream-replay-feedback"
            style={{ fontSize: "0.75rem", fontWeight: 600, color: "var(--color-gate-pass)" }}
          >
            {labels.replayTriggeredFeedback}
          </span>
        ) : null}
      </div>
    </>
  );
}
