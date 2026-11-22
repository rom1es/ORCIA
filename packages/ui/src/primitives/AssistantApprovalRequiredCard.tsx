import React, { useState } from "react";
import { OrciaIcon } from "../components/icons";

export type UiAssistantApprovalStatus = "PENDING" | "APPROVED" | "REJECTED";

export interface UiAssistantApprovalProposal {
  readonly proposalId: string;
  readonly actionKind: string;
  readonly targetUri: string;
  readonly workflowRef?: string | null;
  readonly rationale: string;
  readonly requiresHumanAnchor: boolean;
  readonly status?: UiAssistantApprovalStatus;
  readonly runId?: string | null;
}

export interface AssistantApprovalRequiredCardLabels {
  readonly heading: string;
  readonly targetLabel: string;
  readonly workflowLabel: string;
  readonly humanAnchorLabel: string;
  readonly humanAnchorPlaceholder: string;
  readonly humanAnchorRequiredError: string;
  readonly approveCta: string;
  readonly rejectCta: string;
  readonly approvedStatusLabel: string;
  readonly rejectedStatusLabel: string;
  readonly openProcessCta: string;
}

export interface AssistantApprovalRequiredCardProps {
  readonly proposal: UiAssistantApprovalProposal;
  readonly labels: AssistantApprovalRequiredCardLabels;
  readonly busy?: boolean;
  readonly onApprove: (proposalId: string, humanAnchorMarkdown?: string) => void;
  readonly onReject: (proposalId: string, rationale?: string) => void;
  readonly onOpenProcess?: (runId?: string | null) => void;
}

export function AssistantApprovalRequiredCard({
  proposal,
  labels,
  busy = false,
  onApprove,
  onReject,
  onOpenProcess,
}: AssistantApprovalRequiredCardProps): React.JSX.Element {
  const [anchorText, setAnchorText] = useState<string>("");
  const [validationError, setValidationError] = useState<string | null>(null);
  const status = proposal.status ?? "PENDING";

  const handleApproveClick = () => {
    const trimmed = anchorText.trim();
    if (proposal.requiresHumanAnchor && trimmed.length < 10) {
      setValidationError(labels.humanAnchorRequiredError);
      return;
    }
    setValidationError(null);
    onApprove(proposal.proposalId, trimmed || undefined);
  };

  return (
    <section
      data-testid="assistant-approval-required-card"
      style={{
        backgroundColor: "var(--color-arbitration-bg)",
        borderColor: "var(--color-arbitration-amber)",
        color: "var(--color-text-primary)",
      }}
      className="rounded-lg border p-3.5 text-xs space-y-2.5"
    >
      <header className="flex flex-wrap items-center justify-between gap-2">
        <strong className="inline-flex items-center gap-1.5 text-xs font-semibold">
          <OrciaIcon name="shield" />
          <span>{labels.heading}</span>
        </strong>
        {status !== "PENDING" ? (
          <span
            data-testid="assistant-approval-status-badge"
            style={{
              backgroundColor:
                status === "APPROVED" ? "var(--color-gate-emerald-bg)" : "var(--color-stale-bg)",
              color: status === "APPROVED" ? "var(--color-gate-emerald)" : "var(--color-stale-crimson)",
            }}
            className="rounded-full px-2.5 py-0.5 text-[11px] font-semibold"
          >
            {status === "APPROVED" ? labels.approvedStatusLabel : labels.rejectedStatusLabel}
          </span>
        ) : null}
      </header>

      <p className="m-0 text-xs leading-relaxed text-text-primary">{proposal.rationale}</p>

      <div className="flex flex-wrap items-center gap-2 text-[11px] text-text-secondary">
        <span
          style={{ backgroundColor: "var(--color-surface-card)" }}
          className="rounded border border-border-subtle px-2 py-0.5 font-mono"
        >
          {labels.targetLabel}: {proposal.targetUri || proposal.actionKind}
        </span>
        {proposal.workflowRef ? (
          <span
            style={{ backgroundColor: "var(--color-surface-card)" }}
            className="rounded border border-border-subtle px-2 py-0.5 font-mono"
          >
            {labels.workflowLabel}: {proposal.workflowRef}
          </span>
        ) : null}
      </div>

      {status === "PENDING" ? (
        <>
          <label className="block space-y-1">
            <span className="text-[11px] font-medium text-text-secondary">
              {labels.humanAnchorLabel}
            </span>
            <textarea
              rows={2}
              autoComplete="off"
              data-lpignore="true"
              data-1p-ignore="true"
              data-bwignore="true"
              data-form-type="other"
              data-testid="assistant-approval-anchor-input"
              value={anchorText}
              disabled={busy}
              placeholder={labels.humanAnchorPlaceholder}
              onChange={(e) => {
                setAnchorText(e.target.value);
                if (validationError) setValidationError(null);
              }}
              className="w-full rounded border border-border-subtle bg-surface-primary px-2.5 py-1.5 text-xs text-text-primary"
            />
          </label>
          {validationError ? (
            <div
              role="alert"
              data-testid="assistant-approval-validation-error"
              style={{ color: "var(--color-stale-crimson)", backgroundColor: "var(--color-stale-bg)" }}
              className="rounded px-2.5 py-1 text-[11px] font-medium"
            >
              {validationError}
            </div>
          ) : null}
          <div className="flex flex-wrap items-center gap-2 pt-0.5">
            <button
              type="button"
              data-testid="assistant-approval-approve-btn"
              disabled={busy}
              onClick={handleApproveClick}
              className="orcia-ds-btn orcia-ds-btn-primary text-xs"
            >
              <OrciaIcon name="check" />
              <span>{labels.approveCta}</span>
            </button>
            <button
              type="button"
              data-testid="assistant-approval-reject-btn"
              disabled={busy}
              onClick={() => onReject(proposal.proposalId, anchorText.trim() || undefined)}
              className="orcia-ds-btn orcia-ds-btn-secondary text-xs"
            >
              <OrciaIcon name="cross" />
              <span>{labels.rejectCta}</span>
            </button>
          </div>
        </>
      ) : status === "APPROVED" && onOpenProcess ? (
        <div className="pt-0.5">
          <button
            type="button"
            data-testid="assistant-approval-open-process-btn"
            onClick={() => onOpenProcess(proposal.runId)}
            className="orcia-ds-btn orcia-ds-btn-primary text-xs"
          >
            <OrciaIcon name="processes" />
            <span>{labels.openProcessCta}</span>
          </button>
        </div>
      ) : null}
    </section>
  );
}
