import React from "react";
import { OrciaIcon } from "../components/icons";
import { OrciaButton } from "./DesignSystemControls";
import { SecretField, type SecretFieldLabels } from "./SecretField";
import type {
  UiWorkflowTriggerItem,
  UpdateWorkflowTriggerDraft,
  WorkflowTriggersModalLabels,
} from "./WorkflowTriggersTypes";

export interface WorkflowTriggerCardProps {
  readonly trigger: UiWorkflowTriggerItem;
  readonly hasActiveContract: boolean;
  readonly submitting: boolean;
  readonly labels: WorkflowTriggersModalLabels;
  readonly secretFieldLabels: SecretFieldLabels;
  readonly onUpdateTrigger: (
    triggerId: string,
    draft: UpdateWorkflowTriggerDraft,
  ) => Promise<void> | void;
  readonly onDeleteTrigger: (triggerId: string) => Promise<void> | void;
  readonly onFireTrigger: (triggerId: string) => Promise<void> | void;
  readonly onResetCircuit: (triggerId: string) => Promise<void> | void;
}

export function WorkflowTriggerCard({
  trigger: trig,
  hasActiveContract,
  submitting,
  labels,
  secretFieldLabels,
  onUpdateTrigger,
  onDeleteTrigger,
  onFireTrigger,
  onResetCircuit,
}: WorkflowTriggerCardProps): React.ReactElement {
  return (
    <div
      data-testid={`workflow-trigger-card-${trig.id}`}
      style={{
        border: "1px solid var(--color-border-subtle)",
        borderRadius: "var(--radius-md)",
        padding: "10px 12px",
        display: "flex",
        flexDirection: "column",
        gap: "8px",
        backgroundColor: "var(--color-surface-elevated)",
      }}
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
        <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
          <OrciaIcon name={trig.triggerType === "CRON" ? "clock" : "lightning"} size={14} />
          <strong style={{ fontSize: "13px" }}>{labels.typeOptions[trig.triggerType]}</strong>
          <span
            data-testid={`trigger-status-badge-${trig.id}`}
            className="rounded px-2 py-0.5 text-xs font-semibold"
            style={{
              backgroundColor:
                trig.status === "ACTIVE"
                  ? "var(--color-gate-emerald-bg)"
                  : trig.status === "CIRCUIT_OPEN"
                    ? "var(--color-arbitration-bg)"
                    : "var(--color-surface-canvas)",
              color:
                trig.status === "ACTIVE"
                  ? "var(--color-gate-emerald)"
                  : trig.status === "CIRCUIT_OPEN"
                    ? "var(--color-arbitration-amber)"
                    : "var(--color-text-secondary)",
            }}
          >
            {labels.statusLabels[trig.status]}
          </span>
          {trig.consecutiveFailures > 0 ? (
            <span style={{ fontSize: "11px", color: "var(--color-text-secondary)" }}>
              {labels.failuresPrefix} {trig.consecutiveFailures}/{trig.maxConsecutiveFailures}
            </span>
          ) : null}
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: "6px" }}>
          <OrciaButton
            type="button"
            size="sm"
            variant="secondary"
            testId={`trigger-fire-btn-${trig.id}`}
            disabled={submitting || trig.status !== "ACTIVE" || !hasActiveContract}
            onClick={() => void onFireTrigger(trig.id)}
          >
            <OrciaIcon name="play" size={12} />
            <span>{labels.fireNowButton}</span>
          </OrciaButton>
          {trig.status === "CIRCUIT_OPEN" ? (
            <OrciaButton
              type="button"
              size="sm"
              variant="primary"
              testId={`trigger-reset-circuit-btn-${trig.id}`}
              disabled={submitting || !hasActiveContract}
              onClick={() => void onResetCircuit(trig.id)}
            >
              <OrciaIcon name="regenerate" size={12} />
              <span>{labels.resetCircuitButton}</span>
            </OrciaButton>
          ) : (
            <OrciaButton
              type="button"
              size="sm"
              variant="secondary"
              testId={`trigger-toggle-status-btn-${trig.id}`}
              disabled={submitting}
              onClick={() =>
                void onUpdateTrigger(trig.id, {
                  status: trig.status === "ACTIVE" ? "PAUSED" : "ACTIVE",
                })
              }
            >
              <span>{trig.status === "ACTIVE" ? labels.pauseButton : labels.activateButton}</span>
            </OrciaButton>
          )}
          <OrciaButton
            type="button"
            size="sm"
            variant="danger"
            testId={`trigger-delete-btn-${trig.id}`}
            disabled={submitting}
            onClick={() => void onDeleteTrigger(trig.id)}
          >
            <OrciaIcon name="cross" size={12} />
            <span>{labels.deleteButton}</span>
          </OrciaButton>
        </div>
      </div>

      {trig.triggerType === "OUTBOX_EVENT" ? (
        <label style={{ display: "inline-flex", alignItems: "center", gap: "6px", fontSize: "12px" }}>
          <input
            type="checkbox"
            autoComplete="off"
            data-lpignore="true"
            data-1p-ignore="true"
            data-bwignore="true"
            data-protonpass-ignore="true"
            data-form-type="other"
            data-testid={`trigger-auto-help-toggle-${trig.id}`}
            checked={trig.autoHelpOnPublish}
            onChange={(e) =>
              void onUpdateTrigger(trig.id, { autoHelpOnPublish: e.target.checked })
            }
          />
          <span>{labels.autoHelpCheckboxLabel}</span>
        </label>
      ) : null}

      {trig.triggerType === "WEBHOOK" ? (
        <SecretField
          status={trig.webhookSecretStatus}
          labels={secretFieldLabels}
          readOnly={submitting}
          onSecretAction={(input) => void onUpdateTrigger(trig.id, { webhookSecret: input })}
        />
      ) : null}
    </div>
  );
}
