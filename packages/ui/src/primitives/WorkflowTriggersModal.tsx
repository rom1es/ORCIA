import React, { useEffect, useState } from "react";
import { ContextualInfoTriggerButton } from "../components/ContextualInfoTriggerButton";
import { OrciaIcon } from "../components/icons";
import {
  OrciaAlertBanner,
  OrciaButton,
  OrciaDialog,
  OrciaInput,
  OrciaSelect,
} from "./DesignSystemControls";
import { SecretField, type UiSecretInputValue, type UiSecretStatus } from "./SecretField";
import { WorkflowTriggerCard } from "./WorkflowTriggerCard";
import type {
  CreateWorkflowTriggerDraft,
  UiWorkflowTriggerItem,
  UiWorkflowTriggerStatus,
  UiWorkflowTriggerType,
  UpdateWorkflowTriggerDraft,
  WorkflowTriggersModalLabels,
  WorkflowTriggersModalProps,
} from "./WorkflowTriggersTypes";

export type {
  CreateWorkflowTriggerDraft,
  UiWorkflowTriggerItem,
  UiWorkflowTriggerStatus,
  UiWorkflowTriggerType,
  UpdateWorkflowTriggerDraft,
  WorkflowTriggersModalLabels,
  WorkflowTriggersModalProps,
};

const EMPTY_SECRET_STATUS: UiSecretStatus = {
  configured: false,
  fingerprint: null,
  maskedHint: null,
  updatedAt: "",
  updatedBy: "",
};

export function WorkflowTriggersModal({
  open,
  onOpenChange,
  workflowTitle,
  hasActiveContract,
  triggers,
  submitting = false,
  errorMessage = null,
  labels,
  onCreateTrigger,
  onUpdateTrigger,
  onDeleteTrigger,
  onFireTrigger,
  onResetCircuit,
  onOpenHelpSection,
}: WorkflowTriggersModalProps): React.ReactElement {
  const [triggerType, setTriggerType] = useState<UiWorkflowTriggerType>("MANUAL_AUTONOMOUS");
  const [cronExpr, setCronExpr] = useState<string>("0 * * * *");
  const [logSinkService, setLogSinkService] = useState<string>("api");
  const [logSinkQueryText, setLogSinkQueryText] = useState<string>("");
  const [cooldownSeconds, setCooldownSeconds] = useState<string>("300");
  const [maxRunsPerHour, setMaxRunsPerHour] = useState<string>("10");
  const [maxDailyCostUsd, setMaxDailyCostUsd] = useState<string>("25");
  const [autoHelpOnPublish, setAutoHelpOnPublish] = useState<boolean>(false);
  const [draftWebhookSecret, setDraftWebhookSecret] = useState<UiSecretInputValue | undefined>(
    undefined,
  );

  useEffect(() => {
    if (!open) return;
    setTriggerType("MANUAL_AUTONOMOUS");
    setCronExpr("0 * * * *");
    setLogSinkService("api");
    setLogSinkQueryText("");
    setCooldownSeconds("300");
    setMaxRunsPerHour("10");
    setMaxDailyCostUsd("25");
    setAutoHelpOnPublish(false);
    setDraftWebhookSecret(undefined);
  }, [open]);

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

  const handleCreate = (event: React.FormEvent) => {
    event.preventDefault();
    if (!hasActiveContract || submitting) return;
    void onCreateTrigger({
      triggerType,
      cronExpr: cronExpr.trim(),
      cooldownWindowSeconds: Math.max(0, Number.parseInt(cooldownSeconds, 10) || 300),
      maxRunsPerHour: Math.max(1, Number.parseInt(maxRunsPerHour, 10) || 10),
      maxDailyCostUsd: Math.max(0.5, Number.parseFloat(maxDailyCostUsd) || 25),
      autoHelpOnPublish: triggerType === "OUTBOX_EVENT" ? autoHelpOnPublish : false,
      logSinkService: logSinkService.trim(),
      logSinkQueryText: logSinkQueryText.trim(),
      webhookSecret: triggerType === "WEBHOOK" ? draftWebhookSecret : undefined,
    });
  };

  return (
    <OrciaDialog
      open={open}
      onOpenChange={onOpenChange}
      title={labels.title}
      description={`${workflowTitle} — ${labels.description}`}
      testId="workflow-triggers-modal"
      closeLabel={labels.closeButton}
    >
      <div style={{ display: "flex", flexDirection: "column", gap: "12px", marginTop: "8px" }}>
        <div style={{ display: "flex", justifyContent: "flex-end" }}>
          <ContextualInfoTriggerButton
            sectionId="workflow-triggers"
            label={labels.helpButtonLabel}
            onOpenHelpSection={onOpenHelpSection}
            testId="workflow-triggers-help-trigger"
          />
        </div>

        {errorMessage ? (
          <OrciaAlertBanner tone="crimson" testId="workflow-triggers-error-banner">
            {errorMessage}
          </OrciaAlertBanner>
        ) : null}

        {!hasActiveContract ? (
          <OrciaAlertBanner tone="amber" testId="workflow-triggers-no-contract-banner">
            {labels.missingContractNotice}
          </OrciaAlertBanner>
        ) : null}

        {triggers.length === 0 ? (
          <div
            data-testid="workflow-triggers-empty"
            style={{
              padding: "10px 12px",
              borderRadius: "var(--radius-md)",
              border: "1px dashed var(--color-border-subtle)",
              fontSize: "12px",
              color: "var(--color-text-secondary)",
            }}
          >
            {labels.emptyListHint}
          </div>
        ) : (
          <div
            data-testid="workflow-triggers-list"
            style={{ display: "flex", flexDirection: "column", gap: "10px" }}
          >
            {triggers.map((trig) => (
              <WorkflowTriggerCard
                key={trig.id}
                trigger={trig}
                hasActiveContract={hasActiveContract}
                submitting={submitting}
                labels={labels}
                secretFieldLabels={secretFieldLabels}
                onUpdateTrigger={onUpdateTrigger}
                onDeleteTrigger={onDeleteTrigger}
                onFireTrigger={onFireTrigger}
                onResetCircuit={onResetCircuit}
              />
            ))}
          </div>
        )}

        <form
          onSubmit={handleCreate}
          data-testid="workflow-trigger-create-form"
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
                onChange={(e) => setTriggerType(e.target.value as UiWorkflowTriggerType)}
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
                onChange={(e) => setCooldownSeconds(e.target.value)}
              />
            </div>
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
                onChange={(e) => setCronExpr(e.target.value)}
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
                onChange={(e) => setLogSinkService(e.target.value)}
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
              onSecretAction={(input) => setDraftWebhookSecret(input)}
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
                onChange={(e) => setAutoHelpOnPublish(e.target.checked)}
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
                onChange={(e) => setMaxRunsPerHour(e.target.value)}
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
                onChange={(e) => setMaxDailyCostUsd(e.target.value)}
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
      </div>
    </OrciaDialog>
  );
}
