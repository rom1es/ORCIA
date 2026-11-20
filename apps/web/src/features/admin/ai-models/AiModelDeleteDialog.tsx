import type {
  AiModelDeleteImpactResponse,
  AiModelMappingItemResponse,
} from "@orcia/api-client";
import { OrciaDialog, OrciaSpinner } from "@orcia/ui";
import React, { useEffect, useState } from "react";
import type { AiModelsHubDictionary } from "../../../i18n/locales/ai_models_hub_labels";

export type AiModelDeleteConfirmResult =
  | boolean
  | { readonly ok: boolean; readonly errorMessage?: string };

export interface AiModelDeleteDialogProps {
  readonly open: boolean;
  readonly onOpenChange: (open: boolean) => void;
  readonly mapping: AiModelMappingItemResponse | null;
  readonly labels: AiModelsHubDictionary;
  readonly impact: AiModelDeleteImpactResponse | null;
  readonly isLoadingImpact: boolean;
  readonly onConfirmDelete: (
    mappingId: string,
    mode: "reject" | "drain" | "force",
  ) => Promise<AiModelDeleteConfirmResult>;
}

export function AiModelDeleteDialog({
  open,
  onOpenChange,
  mapping,
  labels,
  impact,
  isLoadingImpact,
  onConfirmDelete,
}: AiModelDeleteDialogProps): React.ReactElement {
  const [isDeleting, setIsDeleting] = useState<boolean>(false);
  const [errorMsg, setErrorMsg] = useState<string | null>(null);

  useEffect(() => {
    setErrorMsg(null);
  }, [open, mapping?.id]);

  if (!mapping) {
    return <></>;
  }

  const isBlockedByWorkflows =
    Boolean(impact?.is_last_active_for_tier) &&
    (impact?.dependent_workflows_count ?? 0) > 0;

  const hasPinnedRuns = (impact?.pinned_active_runs_count ?? 0) > 0;

  const handleDelete = async (mode: "reject" | "drain" | "force") => {
    setIsDeleting(true);
    setErrorMsg(null);
    try {
      const result = await onConfirmDelete(mapping.id, mode);
      const ok = typeof result === "boolean" ? result : result.ok;
      if (ok) {
        onOpenChange(false);
      } else {
        const msg =
          typeof result === "object" && result !== null && result.errorMessage
            ? result.errorMessage
            : labels.deleteFailedError;
        setErrorMsg(msg);
      }
    } catch (err: unknown) {
      setErrorMsg(err instanceof Error ? err.message : String(err));
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <OrciaDialog
      open={open}
      onOpenChange={onOpenChange}
      title={labels.deleteDialogTitle}
      description={labels.deleteDialogDescription}
      testId="ai-model-delete-dialog"
      closeLabel={labels.cancelBtn}
      hideHeaderCloseButton
    >
      <div style={{ display: "flex", flexDirection: "column", gap: "14px", marginTop: "12px" }}>
        {errorMsg && (
          <div
            role="alert"
            data-testid="ai-model-delete-error"
            style={{
              padding: "8px 12px",
              borderRadius: "var(--radius-sm)",
              backgroundColor: "var(--color-bg-elevated)",
              border: "1px solid var(--color-status-error)",
              color: "var(--color-status-error)",
              fontSize: "12px",
            }}
          >
            {errorMsg}
          </div>
        )}

        <div
          style={{
            padding: "10px 14px",
            borderRadius: "var(--radius-sm)",
            border: "1px solid var(--color-border)",
            backgroundColor: "var(--color-surface-card)",
            fontSize: "13px",
            display: "flex",
            flexDirection: "column",
            gap: "4px",
          }}
        >
          <strong>{mapping.display_name || mapping.model_name}</strong>
          <span style={{ fontSize: "12px", color: "var(--color-muted-foreground)" }}>
            {labels.deleteSummaryProvider} : <code>{mapping.provider_slug}</code> •{" "}
            {labels.deleteSummaryModel} : <code>{mapping.model_name}</code> •{" "}
            {labels.deleteSummaryTier} : <code>{mapping.inference_tier}</code>
          </span>
        </div>

        {isLoadingImpact ? (
          <p
            style={{
              margin: 0,
              fontSize: "12px",
              color: "var(--color-muted-foreground)",
              display: "inline-flex",
              alignItems: "center",
              gap: "6px",
            }}
          >
            <OrciaSpinner size="xs" />
            <span>{labels.deleteImpactLoading}</span>
          </p>
        ) : (
          <>
            {isBlockedByWorkflows && (
              <div
                role="alert"
                data-testid="delete-blocked-banner"
                style={{
                  padding: "10px 14px",
                  borderRadius: "var(--radius-sm)",
                  border: "1px solid var(--color-border)",
                  backgroundColor: "var(--color-bg-elevated)",
                  fontSize: "12px",
                  fontWeight: 600,
                  color: "var(--color-foreground)",
                }}
              >
                {labels.deleteDialogBlockedNotice}
                <div style={{ marginTop: "4px", fontWeight: 400, fontSize: "11px" }}>
                  {labels.deleteImpactWorkflowsCount} : {impact?.dependent_workflows_count} •{" "}
                  {labels.deleteImpactRemainingModels} : {impact?.remaining_active_for_tier}
                </div>
              </div>
            )}

            {hasPinnedRuns && (
              <div
                role="status"
                data-testid="delete-active-runs-banner"
                style={{
                  padding: "10px 14px",
                  borderRadius: "var(--radius-sm)",
                  border: "1px solid var(--color-border)",
                  backgroundColor: "var(--color-action-primary-subtle)",
                  fontSize: "12px",
                  fontWeight: 600,
                  color: "var(--color-foreground)",
                }}
              >
                {labels.deleteDialogActiveRunsNotice}
                <div style={{ marginTop: "4px", fontWeight: 400, fontSize: "11px" }}>
                  {labels.deleteImpactActiveRunsCount} : {impact?.pinned_active_runs_count}
                </div>
              </div>
            )}
          </>
        )}

        <div
          style={{
            display: "flex",
            justifyContent: "flex-end",
            alignItems: "center",
            flexWrap: "wrap",
            gap: "8px",
            marginTop: "12px",
          }}
        >
          <button
            type="button"
            data-testid="cancel-delete-ai-model-btn"
            onClick={() => onOpenChange(false)}
            className="orcia-ds-btn orcia-ds-btn-secondary"
          >
            {labels.cancelBtn}
          </button>

          {hasPinnedRuns && (
            <button
              type="button"
              data-testid="drain-ai-model-btn"
              disabled={isDeleting}
              onClick={() => void handleDelete("drain")}
              className="orcia-ds-btn orcia-ds-btn-secondary"
            >
              {labels.drainBtn}
            </button>
          )}

          <button
            type="button"
            data-testid="confirm-delete-ai-model-btn"
            disabled={isDeleting || isBlockedByWorkflows}
            onClick={() => void handleDelete("reject")}
            className="orcia-ds-btn orcia-ds-btn-danger inline-flex items-center gap-1.5"
          >
            {isDeleting && <OrciaSpinner size="xs" />}
            <span>{labels.confirmDeleteBtn}</span>
          </button>
        </div>
      </div>
    </OrciaDialog>
  );
}
