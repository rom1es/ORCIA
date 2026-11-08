import React from "react";
import { DisabledButtonAlertIndicator } from "../components/DisabledButtonAlertIndicator";
import { OrciaIcon } from "../components/icons";

export type ProductLifecyclePhaseType = "RUN" | "BUILD" | "MIGRATION";

export interface ProductLifecycleCardLabels {
  readonly phaseTitle: string;
  readonly runBadge: string;
  readonly buildBadge: string;
  readonly migrationBadge: string;
  readonly suggestedWorkflowsTitle: string;
  readonly readOnlyHint: string;
}

export interface ProductLifecycleCardProps {
  readonly workspaceId: string;
  readonly workspaceName: string;
  readonly visibilityMode: "STANDARD" | "CONFIDENTIAL_RESTRICTED" | "PRIVATE_USER";
  readonly ownerOrgUnitName?: string;
  readonly lifecyclePhase: ProductLifecyclePhaseType;
  readonly suggestedWorkflows: readonly string[];
  readonly isReadOnlyObserver: boolean;
  readonly finopsCostUsd: number | null;
  readonly payloadMasked?: boolean;
  readonly labels: ProductLifecycleCardLabels;
  readonly onSelectPhase?: (
    workspaceId: string,
    phase: ProductLifecyclePhaseType,
  ) => void;
}

const PHASES: readonly ProductLifecyclePhaseType[] = [
  "RUN",
  "BUILD",
  "MIGRATION",
];

export function ProductLifecycleCard({
  workspaceId,
  workspaceName,
  visibilityMode,
  ownerOrgUnitName,
  lifecyclePhase,
  suggestedWorkflows,
  isReadOnlyObserver,
  finopsCostUsd,
  payloadMasked = false,
  labels,
  onSelectPhase,
}: ProductLifecycleCardProps) {
  const phaseLabel = (phase: ProductLifecyclePhaseType): string => {
    if (phase === "RUN") return labels.runBadge;
    if (phase === "BUILD") return labels.buildBadge;
    return labels.migrationBadge;
  };

  return (
    <article
      data-testid={`product-lifecycle-card-${workspaceId}`}
      data-lifecycle-phase={lifecyclePhase}
      style={{
        padding: "12px",
        borderRadius: "8px",
        border: "1px solid var(--orcia-border-subtle)",
        backgroundColor: "var(--orcia-surface-elevated)",
        display: "flex",
        flexDirection: "column",
        gap: "8px",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          gap: "8px",
          flexWrap: "wrap",
        }}
      >
        <div>
          <strong style={{ fontSize: "0.875rem" }}>{workspaceName}</strong>
          <div
            style={{
              fontSize: "0.75rem",
              color: "var(--orcia-text-secondary)",
              fontFamily: "var(--orcia-font-mono)",
            }}
          >
            {visibilityMode}
            {ownerOrgUnitName ? ` • ${ownerOrgUnitName}` : ""}
            {finopsCostUsd !== null ? ` • $${finopsCostUsd.toFixed(2)}` : ""}
            {payloadMasked ? (
              <>
                {" • "}
                <OrciaIcon name="lock" /> Payload Masqué
              </>
            ) : (
              ""
            )}
          </div>
        </div>
        <div
          role="group"
          aria-label={labels.phaseTitle}
          style={{ display: "flex", gap: "4px" }}
        >
          {PHASES.map((phase) => {
            const active = phase === lifecyclePhase;
            return (
              <button
                key={phase}
                type="button"
                disabled={isReadOnlyObserver}
                aria-pressed={active}
                data-testid={`lifecycle-btn-${workspaceId}-${phase}`}
                onClick={() => onSelectPhase?.(workspaceId, phase)}
                style={{
                  display: "inline-flex",
                  alignItems: "center",
                  gap: "6px",
                  padding: "3px 8px",
                  borderRadius: "9999px",
                  fontSize: "0.75rem",
                  fontWeight: 600,
                  cursor: isReadOnlyObserver ? "not-allowed" : "pointer",
                  border: active
                    ? "1px solid var(--orcia-action-primary)"
                    : "1px solid var(--orcia-border-subtle)",
                  backgroundColor: active
                    ? "var(--orcia-surface-secondary)"
                    : "transparent",
                  color: active
                    ? "var(--orcia-text-primary)"
                    : "var(--orcia-text-secondary)",
                }}
              >
                <span>{phaseLabel(phase)}</span>
                <DisabledButtonAlertIndicator
                  disabled={isReadOnlyObserver}
                  reason={labels.readOnlyHint}
                  testIdSuffix={`lifecycle-btn-${workspaceId}-${phase}`}
                />
              </button>
            );
          })}
        </div>
      </div>

      <div>
        <span
          style={{
            fontSize: "0.75rem",
            fontWeight: 600,
            color: "var(--orcia-text-secondary)",
          }}
        >
          {labels.suggestedWorkflowsTitle} :
        </span>
        <div
          style={{
            display: "flex",
            gap: "6px",
            flexWrap: "wrap",
            marginTop: "4px",
          }}
        >
          {suggestedWorkflows.map((wf) => (
            <span
              key={wf}
              style={{
                padding: "2px 6px",
                borderRadius: "4px",
                fontSize: "0.75rem",
                fontFamily: "var(--orcia-font-mono)",
                backgroundColor: "var(--orcia-surface-primary)",
                border: "1px solid var(--orcia-border-subtle)",
              }}
            >
              {wf}
            </span>
          ))}
        </div>
      </div>
      {isReadOnlyObserver ? (
        <span
          style={{
            fontSize: "0.7rem",
            color: "var(--orcia-text-muted)",
          }}
        >
          {labels.readOnlyHint}
        </span>
      ) : null}
    </article>
  );
}
