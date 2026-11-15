import type { AiModelMappingItemResponse } from "@orcia/api-client";
import {
  InferenceTierBadge,
  OrciaDropdownMenu,
  PermissionGuard,
  StatusBadge,
  type InferenceTierAndEffortLabels,
  type StatusBadgeTone,
  type UiInferenceEffort,
  type UiInferenceTier,
  type UiPermissionVerb,
  type PermissionGuardLabels,
} from "@orcia/ui";
import React from "react";
import type { AiModelsHubDictionary } from "../../../i18n/locales/ai_models_hub_labels";

const DEFAULT_GUARD_LABELS: PermissionGuardLabels = {
  passiveLockBadge: "Lecture seule",
  passiveLockDescription: "Action réservée aux administrateurs",
  requestAccessCta: "Demander l'accès",
  disabledHint: "Action non autorisée",
};

export interface AiModelsMasterTableProps {
  readonly isFr: boolean;
  readonly labels: AiModelsHubDictionary;
  readonly tierLabels: InferenceTierAndEffortLabels;
  readonly mappings: readonly AiModelMappingItemResponse[];
  readonly allowedVerbs: readonly UiPermissionVerb[];
  readonly testingId: string | null;
  readonly onOpenCreateModal: () => void;
  readonly onOpenEditModal: (mapping: AiModelMappingItemResponse) => void;
  readonly onOpenRotateKeyModal: (mapping: AiModelMappingItemResponse) => void;
  readonly onToggleActive: (mapping: AiModelMappingItemResponse) => void;
  readonly onOpenDeleteDialog: (mapping: AiModelMappingItemResponse) => void;
  readonly onTestConnection: (mappingId: string) => void;
}

const ALL_TIERS: readonly UiInferenceTier[] = ["simple", "medium", "complex", "auto"];

function resolveHealthBadge(
  status: string,
  labels: AiModelsHubDictionary,
): { label: string; tone: StatusBadgeTone } {
  switch (status) {
    case "OPERATIONAL":
      return { label: labels.healthOperational, tone: "emerald" };
    case "DEGRADED":
      return { label: labels.healthDegraded, tone: "amber" };
    case "ERROR":
      return { label: labels.healthError, tone: "crimson" };
    default:
      return { label: labels.healthUntested, tone: "neutral" };
  }
}

export function AiModelsMasterTable({
  isFr,
  labels,
  tierLabels,
  mappings,
  allowedVerbs,
  testingId,
  onOpenCreateModal,
  onOpenEditModal,
  onOpenRotateKeyModal,
  onToggleActive,
  onOpenDeleteDialog,
  onTestConnection,
}: AiModelsMasterTableProps): React.ReactElement {
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
          labels={DEFAULT_GUARD_LABELS}
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
            labels={DEFAULT_GUARD_LABELS}
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
          {mappings.map((item) => {
            const health = resolveHealthBadge(item.health_status, labels);
            const isTesting = testingId === item.id;
            const effortVal = (item.effort ?? "balanced") as UiInferenceEffort;
            const tierVal = item.inference_tier as UiInferenceTier;

            return (
              <div
                key={item.id}
                data-testid={`llm-tier-row-${item.id}`}
                data-tier={item.inference_tier}
                data-usage={item.usage ?? "chat"}
                style={{
                  padding: "12px 16px",
                  borderRadius: "var(--radius-sm)",
                  border: "1px solid var(--color-border)",
                  backgroundColor: "var(--color-surface-card)",
                  display: "flex",
                  justifyContent: "space-between",
                  alignItems: "center",
                  flexWrap: "wrap",
                  gap: "12px",
                  opacity: item.draining ? 0.7 : item.is_active ? 1 : 0.6,
                }}
              >
                <div style={{ display: "flex", flexDirection: "column", gap: "4px", minWidth: "260px", flex: "1 1 300px" }}>
                  <div style={{ display: "flex", alignItems: "center", gap: "8px", flexWrap: "wrap" }}>
                    <span style={{ fontWeight: 600, fontSize: "14px" }}>
                      {item.display_name || item.model_name}
                    </span>
                    {item.usage === "embedding" ? (
                      <span
                        data-testid={`usage-badge-embedding-${item.id}`}
                        style={{
                          fontSize: "11px",
                          fontWeight: 600,
                          padding: "2px 8px",
                          borderRadius: "var(--radius-sm)",
                          backgroundColor: "var(--color-action-primary-subtle)",
                          color: "var(--color-primary-cobalt)",
                          border: "1px solid var(--color-border)",
                        }}
                      >
                        {labels.usageEmbedding}
                      </span>
                    ) : (
                      <InferenceTierBadge tier={tierVal} effort={effortVal} labels={tierLabels} />
                    )}
                    {item.usage === "embedding" && item.is_active && !item.draining && item.scope_level === "GLOBAL" && (
                      <span
                        data-testid={`active-embedding-badge-${item.id}`}
                        style={{
                          fontSize: "11px",
                          fontWeight: 600,
                          padding: "2px 8px",
                          borderRadius: "var(--radius-sm)",
                          backgroundColor: "var(--color-gate-emerald-bg)",
                          color: "var(--color-gate-emerald)",
                          border: "1px solid var(--color-gate-emerald)",
                        }}
                      >
                        ★ {labels.activeEmbeddingBadge}
                      </span>
                    )}
                    {item.draining && (
                      <span
                        data-testid={`draining-badge-${item.id}`}
                        style={{
                          fontSize: "11px",
                          padding: "1px 6px",
                          borderRadius: "var(--radius-sm)",
                          backgroundColor: "var(--color-bg-elevated)",
                          border: "1px solid var(--color-border)",
                          color: "var(--color-muted-foreground)",
                        }}
                      >
                        Drainage
                      </span>
                    )}
                  </div>
                  <div
                    style={{
                      fontSize: "12px",
                      color: "var(--color-muted-foreground)",
                      display: "flex",
                      alignItems: "center",
                      gap: "6px",
                      flexWrap: "wrap",
                    }}
                  >
                    <span>
                      {item.model_family === "family-a"
                        ? isFr
                          ? "Fournisseur principal"
                          : "Primary provider"
                        : item.model_family === "family-b"
                          ? isFr
                            ? "Fournisseur secondaire"
                            : "Secondary provider"
                          : (item.model_family || item.provider_slug)}
                      {item.usage === "embedding"
                        ? ` · ${labels.usageEmbedding} (1024-dim)`
                        : ` · ${tierLabels[`effort${effortVal.charAt(0).toUpperCase() + effortVal.slice(1)}` as keyof InferenceTierAndEffortLabels] ?? effortVal}`}
                    </span>
                    <span>•</span>
                    <code>{item.model_name}</code>
                    {item.fallback_model_name && (
                      <>
                        <span>({isFr ? "secours" : "backup"}:</span>
                        <code>{item.fallback_model_name}</code>
                        <span>)</span>
                      </>
                    )}
                  </div>
                  <div style={{ fontSize: "11px", color: "var(--color-muted-foreground)" }}>
                    <code>{item.endpoint_uri}</code>
                    <span style={{ margin: "0 6px" }}>•</span>
                    {item.auth_mode === "api_key" ? (
                      <span style={{ display: "inline-flex", alignItems: "center", gap: "4px" }}>
                        <span>
                          {isFr
                            ? item.secret_status?.configured
                              ? "Clé d'API enregistrée"
                              : "Clé d'API"
                            : item.secret_status?.configured
                              ? "API key saved"
                              : "API key"}{" "}
                          :
                        </span>
                        <code data-testid="ai-model-secret-hint">
                          {item.secret_status?.masked_hint ?? "••••••••"}
                        </code>
                      </span>
                    ) : item.auth_mode === "env_var" ? (
                      <span>{labels.secretServerEnv} ({item.env_var_name || "ENV"})</span>
                    ) : (
                      <span>{labels.secretLocalNoAuth}</span>
                    )}
                  </div>
                </div>

                <div style={{ display: "flex", alignItems: "center", gap: "10px", flexWrap: "wrap" }}>
                  <div style={{ display: "flex", flexDirection: "column", alignItems: "flex-end", gap: "2px" }}>
                    <StatusBadge label={health.label} tone={health.tone} monospace />
                    {item.last_latency_ms !== null && item.last_latency_ms !== undefined && (
                      <span
                        data-testid={`latency-ms-${item.id}`}
                        style={{ fontSize: "10px", fontFamily: "var(--font-mono)", color: "var(--color-muted-foreground)" }}
                      >
                        {item.last_latency_ms} ms
                      </span>
                    )}
                  </div>

                  <PermissionGuard
                    scopePath="GLOBAL"
                    verb="execute"
                    allowedVerbs={allowedVerbs}
                    fallbackMode="disabled"
                    labels={DEFAULT_GUARD_LABELS}
                  >
                    <button
                      type="button"
                      data-testid={`test-ai-model-btn-${item.id}`}
                      disabled={isTesting || !allowedVerbs.includes("execute")}
                      onClick={() => onTestConnection(item.id)}
                      className="orcia-ds-btn orcia-ds-btn-secondary"
                    >
                      {isTesting ? labels.testingStatus : `🔌 ${labels.testConnectionBtn}`}
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
                      { key: "toggle-active", label: item.is_active ? "Désactiver" : "Activer", testId: `toggle-active-ai-model-item-${item.id}`, onSelect: () => onToggleActive(item) },
                      { key: "delete", label: labels.menuDelete, testId: `delete-ai-model-item-${item.id}`, onSelect: () => onOpenDeleteDialog(item) },
                    ]}
                  />
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
