import {
  createOrciaApiClient,
  type WorkflowTriggerResponse,
} from "@orcia/api-client";
import type {
  CreateWorkflowTriggerDraft,
  UiWorkflowTriggerItem,
  UpdateWorkflowTriggerDraft,
} from "@orcia/ui";
import { useCallback, useEffect, useMemo, useState } from "react";
import type { WorkflowTriggersStudioCopy } from "../../../i18n/locales/workflow_triggers_labels";

interface UseWorkflowTriggersParams {
  readonly workspaceId: string;
  readonly workflowId: string;
  readonly triggersLabels: WorkflowTriggersStudioCopy;
  readonly onBanner: (banner: string) => void;
}

function mapTriggerResponse(item: WorkflowTriggerResponse): UiWorkflowTriggerItem {
  return {
    id: item.id,
    triggerKey: item.trigger_key,
    triggerType: item.trigger_type,
    status: item.status,
    cronExpr: item.cron_expr ?? null,
    cooldownWindowSeconds: item.cooldown_window_seconds,
    maxRunsPerHour: item.max_runs_per_hour,
    maxDailyCostUsd: item.max_daily_cost_usd,
    maxConsecutiveFailures: item.max_consecutive_failures,
    consecutiveFailures: item.consecutive_failures ?? 0,
    autoHelpOnPublish: Boolean(item.auto_help_on_publish),
    lastFiredAtIso: item.last_fired_at_iso ?? null,
    logSinkService: item.log_sink_service ?? null,
    logSinkQueryText: item.log_sink_query_text ?? null,
    webhookSecretStatus: {
      configured: item.webhook_secret_status.configured,
      fingerprint: item.webhook_secret_status.fingerprint ?? null,
      maskedHint: item.webhook_secret_status.masked_hint ?? null,
      updatedAt: item.webhook_secret_status.updated_at,
      updatedBy: item.webhook_secret_status.updated_by,
    },
  };
}

export function useWorkflowTriggers({
  workspaceId,
  workflowId,
  triggersLabels,
  onBanner,
}: UseWorkflowTriggersParams) {
  const [showTriggersModal, setShowTriggersModal] = useState<boolean>(false);
  const [triggers, setTriggers] = useState<UiWorkflowTriggerItem[]>([]);
  const [triggersError, setTriggersError] = useState<string | null>(null);
  const [triggersSubmitting, setTriggersSubmitting] = useState<boolean>(false);

  const apiClient = useMemo(() => createOrciaApiClient({ baseUrl: "" }), []);

  const refreshTriggers = useCallback(async () => {
    try {
      const resp = await apiClient.listWorkflowTriggers(workspaceId, workflowId);
      setTriggers((resp.items ?? []).map(mapTriggerResponse));
      setTriggersError(null);
    } catch (err) {
      setTriggersError(err instanceof Error ? err.message : triggersLabels.loadErrorBanner);
    }
  }, [apiClient, workspaceId, workflowId, triggersLabels.loadErrorBanner]);

  useEffect(() => {
    void refreshTriggers();
  }, [refreshTriggers]);

  const handleCreateTrigger = async (draft: CreateWorkflowTriggerDraft) => {
    setTriggersSubmitting(true);
    setTriggersError(null);
    try {
      await apiClient.createWorkflowTrigger(workspaceId, workflowId, {
        trigger_type: draft.triggerType,
        cron_expr: draft.triggerType === "CRON" ? draft.cronExpr : undefined,
        cooldown_window_seconds: draft.cooldownWindowSeconds,
        max_runs_per_hour: draft.maxRunsPerHour,
        max_daily_cost_usd: draft.maxDailyCostUsd,
        auto_help_on_publish: draft.autoHelpOnPublish,
        log_sink_service:
          draft.triggerType === "LOG_SINK_ALERT" ? draft.logSinkService || undefined : undefined,
        log_sink_query_text:
          draft.triggerType === "LOG_SINK_ALERT" ? draft.logSinkQueryText || undefined : undefined,
        webhook_secret:
          draft.triggerType === "WEBHOOK" && draft.webhookSecret
            ? {
                action: draft.webhookSecret.action,
                plaintext_value: draft.webhookSecret.plaintextValue,
              }
            : undefined,
      });
      await refreshTriggers();
      onBanner(triggersLabels.createdSuccessBanner);
    } catch (err) {
      setTriggersError(err instanceof Error ? err.message : triggersLabels.loadErrorBanner);
    } finally {
      setTriggersSubmitting(false);
    }
  };

  const handleUpdateTrigger = async (triggerId: string, draft: UpdateWorkflowTriggerDraft) => {
    setTriggersSubmitting(true);
    setTriggersError(null);
    try {
      await apiClient.updateWorkflowTrigger(workspaceId, workflowId, triggerId, {
        status: draft.status,
        auto_help_on_publish: draft.autoHelpOnPublish,
        webhook_secret: draft.webhookSecret
          ? {
              action: draft.webhookSecret.action,
              plaintext_value: draft.webhookSecret.plaintextValue,
            }
          : undefined,
      });
      await refreshTriggers();
      onBanner(triggersLabels.updatedSuccessBanner);
    } catch (err) {
      setTriggersError(err instanceof Error ? err.message : triggersLabels.loadErrorBanner);
    } finally {
      setTriggersSubmitting(false);
    }
  };

  const handleDeleteTrigger = async (triggerId: string) => {
    setTriggersSubmitting(true);
    setTriggersError(null);
    try {
      await apiClient.deleteWorkflowTrigger(workspaceId, workflowId, triggerId);
      await refreshTriggers();
      onBanner(triggersLabels.deletedSuccessBanner);
    } catch (err) {
      setTriggersError(err instanceof Error ? err.message : triggersLabels.loadErrorBanner);
    } finally {
      setTriggersSubmitting(false);
    }
  };

  const handleFireTrigger = async (triggerId: string) => {
    setTriggersSubmitting(true);
    setTriggersError(null);
    try {
      await apiClient.fireManualWorkflowTrigger(workspaceId, workflowId, triggerId, {});
      await refreshTriggers();
      onBanner(triggersLabels.firedSuccessBanner);
    } catch (err) {
      setTriggersError(err instanceof Error ? err.message : triggersLabels.loadErrorBanner);
    } finally {
      setTriggersSubmitting(false);
    }
  };

  const handleResetCircuit = async (triggerId: string) => {
    setTriggersSubmitting(true);
    setTriggersError(null);
    try {
      await apiClient.resetWorkflowTriggerCircuit(workspaceId, workflowId, triggerId);
      await refreshTriggers();
      onBanner(triggersLabels.resetSuccessBanner);
    } catch (err) {
      setTriggersError(err instanceof Error ? err.message : triggersLabels.loadErrorBanner);
    } finally {
      setTriggersSubmitting(false);
    }
  };

  const activeTriggersCount = useMemo(
    () => triggers.filter((t) => t.status === "ACTIVE").length,
    [triggers],
  );

  return {
    showTriggersModal,
    setShowTriggersModal,
    triggers,
    activeTriggersCount,
    triggersError,
    triggersSubmitting,
    handleCreateTrigger,
    handleUpdateTrigger,
    handleDeleteTrigger,
    handleFireTrigger,
    handleResetCircuit,
  };
}
