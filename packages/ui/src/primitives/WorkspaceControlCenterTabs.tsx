import React from "react";
import { DisabledButtonAlertIndicator } from "../components/DisabledButtonAlertIndicator";
import { OrciaIcon } from "../components/icons";
import {
  GuidanceDrawer,
  type GuidanceDrawerStepItem,
} from "./GuidanceDrawer";
import {
  ProductLifecycleCard,
  type ProductLifecyclePhaseType,
} from "./ProductLifecycleCard";
import type {
  ControlCenterDatasourceItem,
  ControlCenterOverrideItem,
  ControlCenterRunItem,
  ControlCenterTabId,
  ControlCenterWorkspaceGovItem,
  WorkspaceControlCenterLabels,
} from "./WorkspaceControlCenter";

export interface WorkspaceControlCenterTabsProps {
  readonly activeTab: ControlCenterTabId;
  readonly isReadOnlyObserver: boolean;
  readonly contributorRuns: readonly ControlCenterRunItem[];
  readonly observerRuns: readonly ControlCenterRunItem[];
  readonly datasources: readonly ControlCenterDatasourceItem[];
  readonly guidanceSteps: readonly GuidanceDrawerStepItem[];
  readonly workflowOverrides: readonly ControlCenterOverrideItem[];
  readonly workspacesGovernance: readonly ControlCenterWorkspaceGovItem[];
  readonly labels: WorkspaceControlCenterLabels;
  readonly onSelectPhase?: (
    workspaceId: string,
    phase: ProductLifecyclePhaseType,
  ) => void;
}

export function WorkspaceControlCenterTabs({
  activeTab,
  isReadOnlyObserver,
  contributorRuns,
  observerRuns,
  datasources,
  guidanceSteps,
  workflowOverrides,
  workspacesGovernance,
  labels,
  onSelectPhase,
}: WorkspaceControlCenterTabsProps): React.ReactElement | null {
  if (activeTab === "runs") {
    return (
      <div
        data-testid="tab-panel-runs"
        style={{ display: "flex", flexDirection: "column", gap: "12px" }}
      >
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
          <h3 style={{ margin: 0, fontSize: "0.9375rem" }}>
            <OrciaIcon name="lightning" /> {labels.contributorRunsHeader} ({contributorRuns.length})
          </h3>
          <button
            type="button"
            disabled={isReadOnlyObserver}
            data-testid="launch-run-btn"
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "6px",
              padding: "4px 10px",
              borderRadius: "6px",
              fontSize: "0.75rem",
              fontWeight: 600,
              cursor: isReadOnlyObserver ? "not-allowed" : "pointer",
              border: "1px solid var(--orcia-border-subtle)",
              backgroundColor: "var(--orcia-surface-secondary)",
              color: "var(--orcia-text-primary)",
            }}
          >
            <span>{labels.launchRunButton}</span>
            <DisabledButtonAlertIndicator
              disabled={isReadOnlyObserver}
              reason={labels.observerBannerDefault}
              testIdSuffix="launch-run-btn"
            />
          </button>
        </div>
        {contributorRuns.map((run) => (
          <article
            key={run.runId}
            data-testid={`contributor-run-${run.runId}`}
            style={{
              padding: "10px",
              borderRadius: "8px",
              border: "1px solid var(--orcia-border-subtle)",
              backgroundColor: "var(--orcia-surface-elevated)",
            }}
          >
            <strong>{run.title}</strong> ({run.executionMode}) —{" "}
            <span style={{ fontFamily: "var(--orcia-font-mono)" }}>
              ${run.budgetConsumedUsd.toFixed(2)}
            </span>
            <div style={{ fontSize: "0.75rem", color: "var(--orcia-text-secondary)" }}>
              {run.workspaceName} • {run.currentStepKey} • {run.blackboardSummary}
            </div>
          </article>
        ))}

        <h3 style={{ margin: "8px 0 0 0", fontSize: "0.9375rem" }}>
          <OrciaIcon name="eye" /> {labels.observerRunsHeader} ({observerRuns.length})
        </h3>
        {observerRuns.map((run) => (
          <article
            key={run.runId}
            data-testid={`observer-run-${run.runId}`}
            style={{
              padding: "10px",
              borderRadius: "8px",
              border: "1px solid var(--orcia-border-subtle)",
              backgroundColor: "var(--orcia-surface-primary)",
            }}
          >
            <strong>{run.title}</strong> ({run.executionMode}) —{" "}
            <span style={{ fontFamily: "var(--orcia-font-mono)" }}>
              ${run.budgetConsumedUsd.toFixed(2)}
            </span>
            <div style={{ fontSize: "0.75rem", color: "var(--orcia-text-secondary)" }}>
              {run.workspaceName} • {run.currentStepKey} • {run.blackboardSummary}
            </div>
          </article>
        ))}
      </div>
    );
  }

  if (activeTab === "datasources") {
    return (
      <div
        data-testid="tab-panel-datasources"
        style={{ display: "flex", flexDirection: "column", gap: "12px" }}
      >
        <GuidanceDrawer steps={guidanceSteps} labels={labels.guidanceDrawer} />
        <div style={{ display: "flex", justifyContent: "flex-end" }}>
          <button
            type="button"
            disabled={isReadOnlyObserver}
            data-testid="attach-datasource-btn"
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: "6px",
              padding: "4px 10px",
              borderRadius: "6px",
              fontSize: "0.75rem",
              fontWeight: 600,
              cursor: isReadOnlyObserver ? "not-allowed" : "pointer",
              border: "1px solid var(--orcia-border-subtle)",
              backgroundColor: "var(--orcia-surface-secondary)",
              color: "var(--orcia-text-primary)",
            }}
          >
            <span>+ {labels.attachDatasourceButton}</span>
            <DisabledButtonAlertIndicator
              disabled={isReadOnlyObserver}
              reason={labels.observerBannerDefault}
              testIdSuffix="attach-datasource-btn"
            />
          </button>
        </div>
        {datasources.map((ds) => (
          <article
            key={ds.id}
            data-testid={`datasource-item-${ds.id}`}
            style={{
              padding: "10px",
              borderRadius: "8px",
              border: "1px solid var(--orcia-border-subtle)",
              backgroundColor: "var(--orcia-surface-elevated)",
            }}
          >
            <strong>{ds.alias}</strong> —{" "}
            <code style={{ fontFamily: "var(--orcia-font-mono)" }}>{ds.uri}</code>
            <div style={{ fontSize: "0.75rem", color: "var(--orcia-text-secondary)" }}>
              {`${ds.workspaceName} • ${ds.executionIdentity} • ${labels.ttlPrefix ?? "TTL"} ${ds.freshnessTtlDays}${labels.daysShortUnit ?? "d"} • [${ds.tripartiteStatus}]`}
            </div>
          </article>
        ))}
      </div>
    );
  }

  if (activeTab === "workflows") {
    const chain = labels.overrideChainLabels;
    return (
      <div
        data-testid="tab-panel-workflows"
        style={{ display: "flex", flexDirection: "column", gap: "10px" }}
      >
        {workflowOverrides.map((ov) => (
          <article
            key={ov.workflowKey}
            data-testid={`override-item-${ov.workflowKey}`}
            style={{
              padding: "12px",
              borderRadius: "8px",
              border: "1px solid var(--orcia-border-subtle)",
              backgroundColor: "var(--orcia-surface-elevated)",
            }}
          >
            <strong>{ov.title}</strong> ({ov.spineContractRef})
            <div
              style={{
                fontSize: "0.75rem",
                fontFamily: "var(--orcia-font-mono)",
                marginTop: "6px",
                color: "var(--orcia-text-secondary)",
              }}
            >
              {`1. ${chain?.base ?? "BASE"}: ${ov.baseLayer} → 2. ${chain?.team ?? "TEAM"}: ${ov.teamOverride} → 3. ${chain?.workspace ?? "WORKSPACE"}: ${ov.workspaceOverride} → 4. ${chain?.user ?? "USER"}: ${ov.userOverride}`}
            </div>
          </article>
        ))}
      </div>
    );
  }

  if (activeTab === "governance") {
    return (
      <div
        data-testid="tab-panel-governance"
        style={{ display: "flex", flexDirection: "column", gap: "10px" }}
      >
        {workspacesGovernance.map((ws) => (
          <ProductLifecycleCard
            key={ws.workspaceId}
            workspaceId={ws.workspaceId}
            workspaceName={ws.name}
            visibilityMode={ws.visibilityMode}
            ownerOrgUnitName={ws.ownerOrgUnitName}
            lifecyclePhase={ws.lifecyclePhase}
            suggestedWorkflows={ws.suggestedWorkflows}
            isReadOnlyObserver={
              isReadOnlyObserver || ws.accessMode === "READ_ONLY_OBSERVER"
            }
            finopsCostUsd={ws.finopsCostUsd}
            payloadMasked={ws.payloadMasked}
            labels={labels.lifecycleCard}
            onSelectPhase={onSelectPhase}
          />
        ))}
      </div>
    );
  }

  return null;
}
