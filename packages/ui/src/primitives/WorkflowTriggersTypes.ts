import type { UiSecretInputValue, UiSecretStatus } from "./SecretField";

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
