import type { AiModelMappingItemResponse } from "@orcia/api-client";
import {
  PermissionGuard,
  type InferenceTierAndEffortLabels,
  type UiInferenceTier,
  type UiPermissionVerb,
} from "@orcia/ui";
import React from "react";
import { resolveDictionaryForFlag } from "../../../i18n";
import type { AiModelsHubDictionary } from "../../../i18n/locales/ai_models_hub_labels";
import { AiModelMappingRowCard } from "./AiModelMappingRowCard";

export interface AiModelsMasterTableProps {
  readonly isFr: boolean;
  readonly labels: AiModelsHubDictionary;
  readonly tierLabels: InferenceTierAndEffortLabels;
  readonly mappings: readonly AiModelMappingItemResponse[];
  readonly allowedVerbs: readonly UiPermissionVerb[];
  readonly testingId: string | null;
  readonly testErrorsByModelId?: Readonly<Record<string, string>>;
  readonly onOpenCreateModal: () => void;
  readonly onOpenEditModal: (mapping: AiModelMappingItemResponse) => void;
  readonly onOpenRotateKeyModal: (mapping: AiModelMappingItemResponse) => void;
  readonly onToggleActive: (mapping: AiModelMappingItemResponse) => void;
  readonly onOpenDeleteDialog: (mapping: AiModelMappingItemResponse) => void;
  readonly onTestConnection: (mappingId: string) => void;
}

const ALL_TIERS: readonly UiInferenceTier[] = ["simple", "medium", "complex", "auto"];

export function AiModelsMasterTable({
  isFr,
  labels,
  tierLabels,
  mappings,
  allowedVerbs,
  testingId,
  testErrorsByModelId = {},
  onOpenCreateModal,
  onOpenEditModal,
  onOpenRotateKeyModal,
  onToggleActive,
  onOpenDeleteDialog,
  onTestConnection,
}: AiModelsMasterTableProps): React.ReactElement {
  const guardLabels = resolveDictionaryForFlag(isFr).featureAdminCatalogSettings.permissionGuard;
  const activeCount = mappings.filter((m) => m.is_active && !m.draining).length;
  const configuredTiers = new Set(
    mappings
      .filter((m) => m.is_active && !m.draining && m.usage !== "embedding")
      .map((m) => m.inference_tier),
  );

  return (
    <div
      data-testid="ai-models-master-table"
      style={{ display: "flex", flexDirection: "column", gap: "16px" }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "12px",
        }}
      >
        <div style={{ display: "flex", flexDirection: "column", gap: "4px" }}>
          <div style={{ display: "flex", alignItems: "center", gap: "8px" }}>
            <strong style={{ fontSize: "16px" }}>{labels.title}</strong>
            <span
              style={{
                fontSize: "12px",
                padding: "2px 8px",
                borderRadius: "var(--radius-sm)",
                backgroundColor: "var(--color-bg-elevated)",
                color: "var(--color-muted-foreground)",
              }}
            >
              {activeCount} {activeCount > 1 ? labels.countLabelPlural : labels.countLabel}
            </span>
          </div>
          <span style={{ fontSize: "13px", color: "var(--color-muted-foreground)" }}>
            {labels.subtitle}
          </span>
        </div>

        <PermissionGuard
          scopePath="GLOBAL"
          verb="create"
          allowedVerbs={allowedVerbs}
          fallbackMode="hidden"
          labels={guardLabels}
        >
          <button
            type="button"
            data-testid="open-create-ai-model-modal-btn"
            onClick={onOpenCreateModal}
            className="orcia-ds-btn orcia-ds-btn-primary"
          >
            {labels.connectModelBtn}
          </button>
        </PermissionGuard>
      </div>

      <div
        data-testid="ai-models-coverage-bar"
        style={{
          display: "flex",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "8px",
          padding: "10px 14px",
          borderRadius: "var(--radius-sm)",
          border: "1px solid var(--color-border)",
          backgroundColor: "var(--color-surface-card)",
          fontSize: "12px",
        }}
      >
        <span style={{ fontWeight: 600 }}>{labels.coverageTitle} :</span>
        {ALL_TIERS.map((tier) => {
          const isCovered = configuredTiers.has(tier);
          return (
            <span
              key={tier}
              data-testid={`coverage-tier-chip-${tier}`}
              data-covered={isCovered ? "true" : "false"}
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: "4px",
                padding: "2px 8px",
                borderRadius: "var(--radius-sm)",
                backgroundColor: isCovered
                  ? "var(--color-action-primary-subtle)"
                  : "var(--color-bg-elevated)",
                border: "1px solid var(--color-border)",
                color: isCovered ? "var(--color-primary-cobalt)" : "var(--color-muted-foreground)",
                fontWeight: isCovered ? 600 : 400,
              }}
            >
              {isCovered ? "✓" : "○"} {tierLabels[`${tier}Badge` as keyof InferenceTierAndEffortLabels]}
            </span>
          );
        })}
      </div>

      {mappings.length === 0 ? (
        <div
          data-testid="ai-models-empty-state"
          style={{
            padding: "36px 20px",
            textAlign: "center",
            border: "1px dashed var(--color-border)",
            borderRadius: "var(--radius-sm)",
            backgroundColor: "var(--color-surface-card)",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            gap: "10px",
          }}
        >
          <strong style={{ fontSize: "15px" }}>{labels.emptyTitle}</strong>
          <p
            data-testid="llm-tiers-empty-state"
            style={{
              margin: 0,
              maxWidth: "500px",
              fontSize: "13px",
              color: "var(--color-muted-foreground)",
            }}
          >
            {labels.emptyDescription}
          </p>
          <PermissionGuard
            scopePath="GLOBAL"
            verb="create"
            allowedVerbs={allowedVerbs}
            fallbackMode="hidden"
            labels={guardLabels}
          >
            <button
              type="button"
              data-testid="empty-create-ai-model-btn"
              onClick={onOpenCreateModal}
              className="orcia-ds-btn orcia-ds-btn-primary"
              style={{ marginTop: "6px" }}
            >
              {labels.emptyCta}
            </button>
          </PermissionGuard>
        </div>
      ) : (
        <div style={{ display: "flex", flexDirection: "column", gap: "10px" }}>
          {mappings.map((item) => (
            <AiModelMappingRowCard
              key={item.id}
              item={item}
              labels={labels}
              tierLabels={tierLabels}
              guardLabels={guardLabels}
              allowedVerbs={allowedVerbs}
              isTesting={testingId === item.id}
              testError={testErrorsByModelId[item.id] ?? null}
              onOpenEditModal={onOpenEditModal}
              onOpenRotateKeyModal={onOpenRotateKeyModal}
              onToggleActive={onToggleActive}
              onOpenDeleteDialog={onOpenDeleteDialog}
              onTestConnection={onTestConnection}
            />
          ))}
        </div>
      )}
    </div>
  );
}
