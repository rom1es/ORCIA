import React from "react";
import { OrciaIcon } from "../components/icons";
import { OrciaButton, OrciaInput, OrciaSelect } from "./DesignSystemControls";
import { SecretField, type UiSecretInputValue, type UiSecretStatus } from "./SecretField";
import type { UiWorkflowTriggerType, WorkflowTriggersModalLabels } from "./WorkflowTriggersTypes";

const EMPTY_SECRET_STATUS: UiSecretStatus = {
  configured: false,
  fingerprint: null,
  maskedHint: null,
  updatedAt: "",
  updatedBy: "",
};

export interface WorkflowTriggerCreateFormProps {
  readonly hasActiveContract: boolean;
  readonly submitting: boolean;
  readonly triggerType: UiWorkflowTriggerType;
  readonly triggerKey: string;
  readonly cronExpr: string;
  readonly logSinkService: string;
  readonly cooldownSeconds: string;
  readonly maxRunsPerHour: string;
  readonly maxDailyCostUsd: string;
  readonly autoHelpOnPublish: boolean;
  readonly draftWebhookSecret?: UiSecretInputValue;
  readonly labels: WorkflowTriggersModalLabels;
  readonly onChangeTriggerType: (val: UiWorkflowTriggerType) => void;
  readonly onChangeTriggerKey: (val: string) => void;
  readonly onChangeCronExpr: (val: string) => void;
  readonly onChangeLogSinkService: (val: string) => void;
  readonly onChangeCooldownSeconds: (val: string) => void;
  readonly onChangeMaxRunsPerHour: (val: string) => void;
  readonly onChangeMaxDailyCostUsd: (val: string) => void;
  readonly onChangeAutoHelpOnPublish: (val: boolean) => void;
  readonly onChangeDraftWebhookSecret: (val: UiSecretInputValue) => void;
  readonly onSubmit: (event: React.FormEvent) => void;
}

export function WorkflowTriggerCreateForm({
  hasActiveContract,
  submitting,
  triggerType,
  triggerKey,
  cronExpr,
  logSinkService,
  cooldownSeconds,
  maxRunsPerHour,
  maxDailyCostUsd,
  autoHelpOnPublish,
  draftWebhookSecret,
  labels,
  onChangeTriggerType,
  onChangeTriggerKey,
  onChangeCronExpr,
  onChangeLogSinkService,
  onChangeCooldownSeconds,
  onChangeMaxRunsPerHour,
  onChangeMaxDailyCostUsd,
  onChangeAutoHelpOnPublish,
  onChangeDraftWebhookSecret,
  onSubmit,
}: WorkflowTriggerCreateFormProps): React.ReactElement {
  const secretFieldLabels = {
    fieldLabel: labels.webhookSecretFieldLabel,
    configuredBadge: labels.secretConfiguredBadge,
    unconfiguredBadge: labels.secretUnconfiguredBadge,
    fingerprintPrefix: labels.secretFingerprintPrefix,
    replaceSecretCta: labels.secretReplaceCta,
    cancelReplaceCta: labels.secretCancelCta,
    clearSecretCta: labels.secretClearCta,
    saveNewSecretCta: labels.secretSaveCta,
    inputPlaceholder: labels.secretInputPlaceholder,
  };

  return (
    <form
      onSubmit={onSubmit}
      data-testid="workflow-triggers-create-form"
      autoComplete="off"
      data-lpignore="true"
      data-form-type="other"
      style={{
        borderTop: "1px solid var(--color-border-subtle)",
        paddingTop: "12px",
        display: "flex",
        flexDirection: "column",
        gap: "10px",
      }}
    >
      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          <label htmlFor="trigger-type-select" style={{ fontSize: "12px", fontWeight: 600 }}>
            {labels.typeLabel}
          </label>
          <OrciaSelect
            id="trigger-type-select"
            testId="trigger-create-type-select"
            value={triggerType}
            onChange={(e) => onChangeTriggerType(e.target.value as UiWorkflowTriggerType)}
          >
            {(Object.keys(labels.typeOptions) as UiWorkflowTriggerType[]).map((key) => (
              <option key={key} value={key}>
                {labels.typeOptions[key]}
              </option>
            ))}
          </OrciaSelect>
        </div>

        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          <label htmlFor="trigger-cooldown-input" style={{ fontSize: "12px", fontWeight: 600 }}>
            {labels.cooldownLabel}
          </label>
          <OrciaInput
            id="trigger-cooldown-input"
            testId="trigger-create-cooldown-input"
            type="number"
            min="0"
            value={cooldownSeconds}
            onChange={(e) => onChangeCooldownSeconds(e.target.value)}
          />
        </div>
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
        <label htmlFor="trigger-key-input" style={{ fontSize: "12px", fontWeight: 600 }}>
          {labels.triggerKeyLabel ?? ""}
        </label>
        <OrciaInput
          id="trigger-key-input"
          testId="trigger-create-key-input"
          value={triggerKey}
          placeholder={labels.triggerKeyPlaceholder ?? ""}
          maxLength={128}
          onChange={(e) => onChangeTriggerKey(e.target.value)}
        />
      </div>

      {triggerType === "CRON" ? (
        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          <label htmlFor="trigger-cron-input" style={{ fontSize: "12px", fontWeight: 600 }}>
            {labels.cronLabel}
          </label>
          <OrciaInput
            id="trigger-cron-input"
            testId="trigger-create-cron-input"
            value={cronExpr}
            placeholder={labels.cronPlaceholder}
            onChange={(e) => onChangeCronExpr(e.target.value)}
          />
        </div>
      ) : null}

      {triggerType === "LOG_SINK_ALERT" ? (
        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          <label htmlFor="trigger-log-svc-input" style={{ fontSize: "12px", fontWeight: 600 }}>
            {labels.logServiceLabel}
          </label>
          <OrciaInput
            id="trigger-log-svc-input"
            testId="trigger-create-log-service-input"
            value={logSinkService}
            placeholder={labels.logServicePlaceholder}
            onChange={(e) => onChangeLogSinkService(e.target.value)}
          />
        </div>
      ) : null}

      {triggerType === "WEBHOOK" ? (
        <SecretField
          status={
            draftWebhookSecret?.action === "set"
              ? { ...EMPTY_SECRET_STATUS, configured: true }
              : EMPTY_SECRET_STATUS
          }
          labels={secretFieldLabels}
          onSecretAction={onChangeDraftWebhookSecret}
        />
      ) : null}

      {triggerType === "OUTBOX_EVENT" ? (
        <label style={{ display: "inline-flex", alignItems: "center", gap: "8px", fontSize: "12px" }}>
          <input
            type="checkbox"
            autoComplete="off"
            data-lpignore="true"
            data-1p-ignore="true"
            data-bwignore="true"
            data-protonpass-ignore="true"
            data-form-type="other"
            data-testid="trigger-create-auto-help-checkbox"
            checked={autoHelpOnPublish}
            onChange={(e) => onChangeAutoHelpOnPublish(e.target.checked)}
          />
          <span>{labels.autoHelpCheckboxLabel}</span>
        </label>
      ) : null}

      <div style={{ display: "grid", gridTemplateColumns: "1fr 1fr", gap: "10px" }}>
        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          <label htmlFor="trigger-max-runs" style={{ fontSize: "12px", fontWeight: 600 }}>
            {labels.maxRunsPerHourLabel}
          </label>
          <OrciaInput
            id="trigger-max-runs"
            testId="trigger-create-max-runs-input"
            type="number"
            min="1"
            value={maxRunsPerHour}
            onChange={(e) => onChangeMaxRunsPerHour(e.target.value)}
          />
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          <label htmlFor="trigger-max-cost" style={{ fontSize: "12px", fontWeight: 600 }}>
            {labels.maxDailyCostLabel}
          </label>
          <OrciaInput
            id="trigger-max-cost"
            testId="trigger-create-max-cost-input"
            type="number"
            min="0.5"
            step="0.5"
            value={maxDailyCostUsd}
            onChange={(e) => onChangeMaxDailyCostUsd(e.target.value)}
          />
        </div>
      </div>

      <div style={{ display: "flex", justifyContent: "flex-end", gap: "8px", marginTop: "6px" }}>
        <OrciaButton
          type="submit"
          variant="primary"
          testId="trigger-create-submit-btn"
          disabled={submitting || !hasActiveContract}
        >
          <OrciaIcon name="plus" size={14} />
          <span>{submitting ? labels.creatingButton : labels.createButton}</span>
        </OrciaButton>
      </div>
    </form>
  );
}
