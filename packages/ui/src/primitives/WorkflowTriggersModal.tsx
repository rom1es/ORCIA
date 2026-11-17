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

export type UiWorkflowTriggerType =
  | "MANUAL_AUTONOMOUS"
  | "WEBHOOK"
  | "CRON"
  | "LOG_SINK_ALERT"
  | "OUTBOX_EVENT";

export type UiWorkflowTriggerStatus = "ACTIVE" | "PAUSED" | "CIRCUIT_OPEN";

export interface UiWorkflowTriggerItem {
  readonly id: string;
  readonly triggerKey: string;
  readonly triggerType: UiWorkflowTriggerType;
  readonly status: UiWorkflowTriggerStatus;
  readonly cronExpr: string | null;
  readonly cooldownWindowSeconds: number;
  readonly maxRunsPerHour: number;
  readonly maxDailyCostUsd: number;
  readonly maxConsecutiveFailures: number;
  readonly consecutiveFailures: number;
  readonly autoHelpOnPublish: boolean;
  readonly lastFiredAtIso: string | null;
  readonly logSinkService: string | null;
  readonly logSinkQueryText: string | null;
  readonly webhookSecretStatus: UiSecretStatus;
}

export interface CreateWorkflowTriggerDraft {
  readonly triggerType: UiWorkflowTriggerType;
  readonly cronExpr: string;
  readonly cooldownWindowSeconds: number;
  readonly maxRunsPerHour: number;
  readonly maxDailyCostUsd: number;
  readonly autoHelpOnPublish: boolean;
  readonly logSinkService: string;
  readonly logSinkQueryText: string;
  readonly webhookSecret?: UiSecretInputValue;
}

export interface UpdateWorkflowTriggerDraft {
  readonly status?: "ACTIVE" | "PAUSED";
  readonly autoHelpOnPublish?: boolean;
  readonly webhookSecret?: UiSecretInputValue;
}

export interface WorkflowTriggersModalLabels {
  readonly title: string;
  readonly description: string;
  readonly helpButtonLabel: string;
  readonly missingContractNotice: string;
  readonly emptyListHint: string;
  readonly typeLabel: string;
  readonly typeOptions: Readonly<Record<UiWorkflowTriggerType, string>>;
  readonly statusLabels: Readonly<Record<UiWorkflowTriggerStatus, string>>;
  readonly cronLabel: string;
  readonly cronPlaceholder: string;
  readonly logServiceLabel: string;
  readonly logServicePlaceholder: string;
  readonly cooldownLabel: string;
  readonly maxRunsPerHourLabel: string;
  readonly maxDailyCostLabel: string;
  readonly autoHelpCheckboxLabel: string;
  readonly webhookSecretFieldLabel: string;
  readonly secretConfiguredBadge: string;
  readonly secretUnconfiguredBadge: string;
  readonly secretFingerprintPrefix: string;
  readonly secretReplaceCta: string;
  readonly secretCancelCta: string;
  readonly secretClearCta: string;
  readonly secretSaveCta: string;
  readonly secretInputPlaceholder: string;
  readonly createButton: string;
  readonly creatingButton: string;
  readonly fireNowButton: string;
  readonly resetCircuitButton: string;
  readonly pauseButton: string;
  readonly activateButton: string;
  readonly deleteButton: string;
  readonly closeButton: string;
  readonly failuresPrefix: string;
}

export interface WorkflowTriggersModalProps {
  readonly open: boolean;
  readonly onOpenChange: (open: boolean) => void;
  readonly workflowTitle: string;
  readonly hasActiveContract: boolean;
  readonly triggers: readonly UiWorkflowTriggerItem[];
  readonly submitting?: boolean;
  readonly errorMessage?: string | null;
  readonly labels: WorkflowTriggersModalLabels;
  readonly onCreateTrigger: (draft: CreateWorkflowTriggerDraft) => Promise<void> | void;
  readonly onUpdateTrigger: (
    triggerId: string,
    draft: UpdateWorkflowTriggerDraft,
  ) => Promise<void> | void;
  readonly onDeleteTrigger: (triggerId: string) => Promise<void> | void;
  readonly onFireTrigger: (triggerId: string) => Promise<void> | void;
  readonly onResetCircuit: (triggerId: string) => Promise<void> | void;
  readonly onOpenHelpSection: (sectionId: string) => void;
}

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
              <div
                key={trig.id}
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
                    <OrciaIcon
                      name={trig.triggerType === "CRON" ? "clock" : "lightning"}
                      size={14}
                    />
                    <strong style={{ fontSize: "13px" }}>
                      {labels.typeOptions[trig.triggerType]}
                    </strong>
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
                        {labels.failuresPrefix} {trig.consecutiveFailures}/
                        {trig.maxConsecutiveFailures}
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
                        <span>
                          {trig.status === "ACTIVE" ? labels.pauseButton : labels.activateButton}
                        </span>
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
                  <label
                    style={{
                      display: "inline-flex",
                      alignItems: "center",
                      gap: "6px",
                      fontSize: "12px",
                    }}
                  >
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
                    onSecretAction={(input) =>
                      void onUpdateTrigger(trig.id, { webhookSecret: input })
                    }
                  />
                ) : null}
              </div>
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
            <label
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "8px",
                fontSize: "12px",
              }}
            >
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
              type="button"
              variant="secondary"
              testId="workflow-triggers-close-btn"
              onClick={() => onOpenChange(false)}
            >
              {labels.closeButton}
            </OrciaButton>
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
