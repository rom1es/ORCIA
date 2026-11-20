import type {
  AiModelDeleteImpactResponse,
  AiModelMappingItemResponse,
} from "@orcia/api-client";
import { OrciaDialog } from "@orcia/ui";
import React, { useState } from "react";
import type { AiModelsHubDictionary } from "../../../i18n/locales/ai_models_hub_labels";

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
  ) => Promise<boolean>;
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
      const ok = await onConfirmDelete(mapping.id, mode);
      if (ok) {
        onOpenChange(false);
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
              border: "1px solid var(--color-border)",
              color: "var(--color-foreground)",
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
            Fournisseur : <code>{mapping.provider_slug}</code> • Modèle : <code>{mapping.model_name}</code> • Tier : <code>{mapping.inference_tier}</code>
          </span>
        </div>

        {isLoadingImpact ? (
          <p style={{ margin: 0, fontSize: "12px", color: "var(--color-muted-foreground)" }}>
            Analyse d'impact en cours...
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
                  Workflows impactés : {impact?.dependent_workflows_count} • Autres modèles actifs sur ce tier : {impact?.remaining_active_for_tier}
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
                  Runs actifs épinglant ce modèle : {impact?.pinned_active_runs_count}
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

          {hasRunsOrImpact(hasPinnedRuns) && (
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
            className="orcia-ds-btn orcia-ds-btn-danger"
          >
            {labels.confirmDeleteBtn}
          </button>
        </div>
      </div>
    </OrciaDialog>
  );
}

function hasRunsOrImpact(hasPinnedRuns: boolean): boolean {
  return hasPinnedRuns;
}
