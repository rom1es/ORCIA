import React, { useEffect, useState } from "react";
import { ContextualInfoTriggerButton } from "../components/ContextualInfoTriggerButton";
import { OrciaAlertBanner, OrciaDialog } from "./DesignSystemControls";
import type { UiSecretInputValue } from "./SecretField";
import { WorkflowTriggerCard } from "./WorkflowTriggerCard";
import { WorkflowTriggerCreateForm } from "./WorkflowTriggerCreateForm";
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
  const [triggerKey, setTriggerKey] = useState<string>("");
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
    setTriggerKey("");
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
      triggerKey: triggerKey.trim() || undefined,
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

        <WorkflowTriggerCreateForm
          hasActiveContract={hasActiveContract}
          submitting={submitting}
          triggerType={triggerType}
          triggerKey={triggerKey}
          cronExpr={cronExpr}
          logSinkService={logSinkService}
          cooldownSeconds={cooldownSeconds}
          maxRunsPerHour={maxRunsPerHour}
          maxDailyCostUsd={maxDailyCostUsd}
          autoHelpOnPublish={autoHelpOnPublish}
          draftWebhookSecret={draftWebhookSecret}
          labels={labels}
          onChangeTriggerType={setTriggerType}
          onChangeTriggerKey={setTriggerKey}
          onChangeCronExpr={setCronExpr}
          onChangeLogSinkService={setLogSinkService}
          onChangeCooldownSeconds={setCooldownSeconds}
          onChangeMaxRunsPerHour={setMaxRunsPerHour}
          onChangeMaxDailyCostUsd={setMaxDailyCostUsd}
          onChangeAutoHelpOnPublish={setAutoHelpOnPublish}
          onChangeDraftWebhookSecret={setDraftWebhookSecret}
          onSubmit={handleCreate}
        />
      </div>
    </OrciaDialog>
  );
}
