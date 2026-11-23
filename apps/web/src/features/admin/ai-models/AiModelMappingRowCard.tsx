import type { AiModelMappingItemResponse } from "@orcia/api-client";
import {
  InferenceTierBadge,
  OrciaDropdownMenu,
  OrciaSpinner,
  PermissionGuard,
  StatusBadge,
  type InferenceTierAndEffortLabels,
  type PermissionGuardLabels,
  type StatusBadgeTone,
  type UiInferenceEffort,
  type UiInferenceTier,
  type UiPermissionVerb,
} from "@orcia/ui";
import React from "react";
import type { AiModelsHubDictionary } from "../../../i18n/locales/ai_models_hub_labels";

export interface AiModelMappingRowCardProps {
  readonly item: AiModelMappingItemResponse;
  readonly labels: AiModelsHubDictionary;
  readonly tierLabels: InferenceTierAndEffortLabels;
  readonly guardLabels: PermissionGuardLabels;
  readonly allowedVerbs: readonly UiPermissionVerb[];
  readonly isTesting: boolean;
  readonly testError: string | null;
  readonly onOpenEditModal: (mapping: AiModelMappingItemResponse) => void;
  readonly onOpenRotateKeyModal: (mapping: AiModelMappingItemResponse) => void;
  readonly onToggleActive: (mapping: AiModelMappingItemResponse) => void;
  readonly onOpenDeleteDialog: (mapping: AiModelMappingItemResponse) => void;
  readonly onTestConnection: (mappingId: string) => void;
}

function resolveHealthBadge(status: string, labels: AiModelsHubDictionary): { label: string; tone: StatusBadgeTone } {
  if (status === "OPERATIONAL") return { label: labels.healthOperational, tone: "emerald" };
  if (status === "DEGRADED") return { label: labels.healthDegraded, tone: "amber" };
  if (status === "ERROR") return { label: labels.healthError, tone: "crimson" };
  return { label: labels.healthUntested, tone: "neutral" };
}

export function AiModelMappingRowCard({
  item, labels, tierLabels, guardLabels, allowedVerbs, isTesting, testError,
  onOpenEditModal, onOpenRotateKeyModal, onToggleActive, onOpenDeleteDialog, onTestConnection,
}: AiModelMappingRowCardProps): React.ReactElement {
  const health = resolveHealthBadge(item.health_status, labels);
  const effortVal = (item.effort ?? "balanced") as UiInferenceEffort;
  const tierVal = item.inference_tier as UiInferenceTier;
  const providerDisplay =
    item.model_family === "family-a"
      ? labels.providerPrimaryLabel
      : item.model_family === "family-b"
        ? labels.providerSecondaryLabel
        : item.model_family || item.provider_slug;
  const effortKey = `effort${effortVal.charAt(0).toUpperCase() + effortVal.slice(1)}` as keyof InferenceTierAndEffortLabels;
  const isGlobalActiveEmbedding =
    item.usage === "embedding" && item.is_active && !item.draining && item.scope_level === "GLOBAL";

  return (
    <div
      data-testid={`llm-tier-row-${item.id}`}
      data-tier={item.inference_tier}
      data-usage={item.usage ?? "chat"}
      className="flex flex-col gap-2 rounded-sm border border-[var(--color-border)] bg-[var(--color-surface-card)] px-4 py-3"
      style={{ opacity: item.draining ? 0.7 : item.is_active ? 1 : 0.6 }}
    >
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div className="flex min-w-[260px] flex-[1_1_300px] flex-col gap-1">
          <div className="flex flex-wrap items-center gap-2">
            <span className="text-sm font-semibold">{item.display_name || item.model_name}</span>
            {item.usage === "embedding" ? (
              <span
                data-testid={`usage-badge-embedding-${item.id}`}
                className="rounded-sm border border-[var(--color-border)] bg-[var(--color-action-primary-subtle)] px-2 py-0.5 text-[11px] font-semibold text-[var(--color-primary-cobalt)]"
              >
                {labels.usageEmbedding}
              </span>
            ) : (
              <InferenceTierBadge tier={tierVal} effort={effortVal} labels={tierLabels} />
            )}
            {isGlobalActiveEmbedding && (
              <span
                data-testid={`active-embedding-badge-${item.id}`}
                className="rounded-sm border border-[var(--color-gate-emerald)] bg-[var(--color-gate-emerald-bg)] px-2 py-0.5 text-[11px] font-semibold text-[var(--color-gate-emerald)]"
              >
                ★ {labels.activeEmbeddingBadge}
              </span>
            )}
            {item.draining && (
              <span
                data-testid={`draining-badge-${item.id}`}
                className="rounded-sm border border-[var(--color-border)] bg-[var(--color-bg-elevated)] px-1.5 py-0.5 text-[11px] text-[var(--color-muted-foreground)]"
              >
                {labels.drainingBadge}
              </span>
            )}
          </div>
          <div className="flex flex-wrap items-center gap-1.5 text-xs text-[var(--color-muted-foreground)]">
            <span>
              {providerDisplay}
              {item.usage === "embedding"
                ? ` · ${labels.usageEmbedding} (${labels.highPrecisionSuffix})`
                : ` · ${tierLabels[effortKey] ?? effortVal}`}
            </span>
            <span>•</span>
            <code>{item.model_name}</code>
            {item.fallback_model_name && (
              <>
                <span>({labels.backupPrefix}:</span>
                <code>{item.fallback_model_name}</code>
                <span>)</span>
              </>
            )}
          </div>
          <div className="text-[11px] text-[var(--color-muted-foreground)]">
            <code>{item.endpoint_uri}</code>
            <span className="mx-1.5">•</span>
            {item.auth_mode === "api_key" ? (
              <span className="inline-flex items-center gap-1">
                <span>{item.secret_status?.configured ? labels.secretApiKeySaved : labels.secretApiKey} :</span>
                <code data-testid="ai-model-secret-hint">{item.secret_status?.masked_hint ?? "••••••••"}</code>
              </span>
            ) : item.auth_mode === "env_var" ? (
              <span>{labels.secretServerEnv} ({item.env_var_name || "ENV"})</span>
            ) : (
              <span>{labels.secretLocalNoAuth}</span>
            )}
          </div>
        </div>

        <div className="flex flex-wrap items-center gap-2.5">
          <div className="flex flex-col items-end gap-0.5">
            <StatusBadge label={health.label} tone={health.tone} monospace />
            {item.last_latency_ms !== null && item.last_latency_ms !== undefined && (
              <span data-testid={`latency-ms-${item.id}`} className="font-mono text-[10px] text-[var(--color-muted-foreground)]">
                {`${item.last_latency_ms} ms`}
              </span>
            )}
          </div>

          <PermissionGuard scopePath="GLOBAL" verb="execute" allowedVerbs={allowedVerbs} fallbackMode="disabled" labels={guardLabels}>
            <button
              type="button"
              data-testid={`test-ai-model-btn-${item.id}`}
              disabled={isTesting || !allowedVerbs.includes("execute")}
              onClick={() => onTestConnection(item.id)}
              className="orcia-ds-btn orcia-ds-btn-secondary inline-flex items-center gap-1.5"
            >
              {isTesting ? (
                <>
                  <OrciaSpinner size="sm" />
                  <span>{labels.testingStatus}</span>
                </>
              ) : (
                `🔌 ${labels.testConnectionBtn}`
              )}
            </button>
          </PermissionGuard>

          <OrciaDropdownMenu
            triggerLabel="⋮"
            testId={`ai-model-row-actions-${item.id}`}
            items={[
              { key: "edit", label: labels.menuEdit, testId: `edit-ai-model-item-${item.id}`, onSelect: () => onOpenEditModal(item) },
              ...(item.auth_mode === "api_key"
                ? [{ key: "rotate-key", label: labels.menuRotateKey, testId: `rotate-key-ai-model-item-${item.id}`, onSelect: () => onOpenRotateKeyModal(item) }]
                : []),
              { key: "toggle-active", label: item.is_active ? labels.menuDisable : labels.menuEnable, testId: `toggle-active-ai-model-item-${item.id}`, onSelect: () => onToggleActive(item) },
              { key: "delete", label: labels.menuDelete, testId: `delete-ai-model-item-${item.id}`, onSelect: () => onOpenDeleteDialog(item) },
            ]}
          />
        </div>
      </div>

      {testError && (
        <div
          role="alert"
          data-testid={`ai-model-test-error-${item.id}`}
          className="rounded-sm border border-[var(--color-status-error)] bg-[var(--color-bg-elevated)] px-3 py-2 text-xs text-[var(--color-status-error)]"
        >
          {testError}
        </div>
      )}
    </div>
  );
}
