import React, { useState } from "react";
import { DisabledButtonAlertIndicator } from "../components/DisabledButtonAlertIndicator";
import { OrciaIcon } from "../components/icons";
import {
  GuidanceDrawer,
  type GuidanceDrawerLabels,
  type GuidanceDrawerStepItem,
} from "./GuidanceDrawer";
import {
  ProductLifecycleCard,
  type ProductLifecycleCardLabels,
  type ProductLifecyclePhaseType,
} from "./ProductLifecycleCard";

export type ControlCenterScopeType = "GLOBAL" | "BU" | "TEAM" | "WORKSPACE";
export type ControlCenterTabId =
  | "runs"
  | "datasources"
  | "workflows"
  | "governance";

export interface ControlCenterRunItem {
  readonly runId: string;
  readonly workspaceId: string;
  readonly workspaceName: string;
  readonly title: string;
  readonly status: string;
  readonly currentStepKey: string;
  readonly executionMode: "COACHING" | "FAST_PATH";
  readonly accessMode: "CONTRIBUTOR_ACTION_REQUIRED" | "READ_ONLY_OBSERVER";
  readonly budgetConsumedUsd: number;
  readonly blackboardSummary: string;
  readonly payloadMasked?: boolean;
}

export interface ControlCenterDatasourceItem {
  readonly id: string;
  readonly workspaceName: string;
  readonly alias: string;
  readonly scheme: string;
  readonly uri: string;
  readonly executionIdentity: string;
  readonly freshnessTtlDays: number;
  readonly tripartiteStatus: "ALIGNED" | "STALE_WARNING" | "INDEXING";
}

export interface ControlCenterOverrideItem {
  readonly workflowKey: string;
  readonly title: string;
  readonly baseLayer: string;
  readonly teamOverride: string;
  readonly workspaceOverride: string;
  readonly userOverride: string;
  readonly spineContractRef: string;
}

export interface ControlCenterWorkspaceGovItem {
  readonly workspaceId: string;
  readonly name: string;
  readonly visibilityMode: "STANDARD" | "CONFIDENTIAL_RESTRICTED" | "PRIVATE_USER";
  readonly ownerOrgUnitId?: string;
  readonly ownerOrgUnitName?: string;
  readonly ownerUserId?: string;
  readonly lifecyclePhase: ProductLifecyclePhaseType;
  readonly suggestedWorkflows: readonly string[];
  readonly accessMode: "CONTRIBUTOR_ACTION_REQUIRED" | "READ_ONLY_OBSERVER";
  readonly finopsCostUsd: number | null;
  readonly payloadMasked?: boolean;
}

export interface WorkspaceControlCenterLabels {
  readonly title: string;
  readonly scopeSelectorLabel: string;
  readonly scopeGlobal: string;
  readonly scopeBu: string;
  readonly scopeTeam: string;
  readonly scopeWorkspace: string;
  readonly tab1Runs: string;
  readonly tab2Datasources: string;
  readonly tab3Workflows: string;
  readonly tab4Governance: string;
  readonly contributorRunsHeader: string;
  readonly observerRunsHeader: string;
  readonly attachDatasourceButton: string;
  readonly launchRunButton: string;
  readonly observerBannerDefault: string;
  readonly guidanceDrawer: GuidanceDrawerLabels;
  readonly lifecycleCard: ProductLifecycleCardLabels;
}

export interface WorkspaceControlCenterProps {
  readonly scopeType: ControlCenterScopeType;
  readonly scopeLabel: string;
  readonly isReadOnlyObserver: boolean;
  readonly observerBannerText?: string | null;
  readonly consolidatedFinopsUsd: number;
  readonly contributorRuns: readonly ControlCenterRunItem[];
  readonly observerRuns: readonly ControlCenterRunItem[];
  readonly datasources: readonly ControlCenterDatasourceItem[];
  readonly guidanceSteps: readonly GuidanceDrawerStepItem[];
  readonly workflowOverrides: readonly ControlCenterOverrideItem[];
  readonly workspacesGovernance: readonly ControlCenterWorkspaceGovItem[];
  readonly labels: WorkspaceControlCenterLabels;
  readonly onChangeScopeType?: (scope: ControlCenterScopeType) => void;
  readonly onSelectPhase?: (
    workspaceId: string,
    phase: ProductLifecyclePhaseType,
  ) => void;
  readonly onOpenCommandPalette?: () => void;
}

export function WorkspaceControlCenter({
  scopeType,
  scopeLabel,
  isReadOnlyObserver,
  observerBannerText,
  consolidatedFinopsUsd,
  contributorRuns,
  observerRuns,
  datasources,
  guidanceSteps,
  workflowOverrides,
  workspacesGovernance,
  labels,
  onChangeScopeType,
  onSelectPhase,
  onOpenCommandPalette,
}: WorkspaceControlCenterProps) {
  const [activeTab, setActiveTab] = useState<ControlCenterTabId>("runs");

  const scopes: readonly { id: ControlCenterScopeType; text: string }[] = [
    { id: "GLOBAL", text: labels.scopeGlobal },
    { id: "BU", text: labels.scopeBu },
    { id: "TEAM", text: labels.scopeTeam },
    { id: "WORKSPACE", text: labels.scopeWorkspace },
  ];

  const tabs: readonly { id: ControlCenterTabId; text: string }[] = [
    { id: "runs", text: labels.tab1Runs },
    { id: "datasources", text: labels.tab2Datasources },
    { id: "workflows", text: labels.tab3Workflows },
    { id: "governance", text: labels.tab4Governance },
  ];

  return (
    <section
      data-testid="workspace-control-center"
      style={{ display: "flex", flexDirection: "column", gap: "16px" }}
    >
      {isReadOnlyObserver ? (
        <div
          role="status"
          aria-live="polite"
          data-testid="observer-read-only-banner"
          style={{
            padding: "10px 14px",
            borderRadius: "8px",
            border: "1px solid var(--orcia-border-subtle)",
            backgroundColor: "var(--orcia-surface-secondary)",
            fontSize: "0.8125rem",
            fontWeight: 600,
          }}
        >
          {observerBannerText ?? labels.observerBannerDefault}
        </div>
      ) : null}

      <header
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          flexWrap: "wrap",
          gap: "12px",
        }}
      >
        <div>
          <h2 style={{ margin: 0, fontSize: "1.125rem" }}>{labels.title}</h2>
          <p
            style={{
              margin: "4px 0 0 0",
              fontSize: "0.8125rem",
              color: "var(--orcia-text-secondary)",
            }}
          >
            {scopeLabel} • FinOps Consolidé :{" "}
            <strong style={{ fontFamily: "var(--orcia-font-mono)" }}>
              ${consolidatedFinopsUsd.toFixed(2)}
            </strong>
          </p>
        </div>

        <div
          style={{
            display: "flex",
            alignItems: "center",
            gap: "6px",
            flexWrap: "wrap",
          }}
        >
          <span
            style={{
              fontSize: "0.75rem",
              fontWeight: 600,
              color: "var(--orcia-text-secondary)",
            }}
          >
            ⌘W {labels.scopeSelectorLabel} :
          </span>
          {scopes.map((sc) => (
            <button
              key={sc.id}
              type="button"
              data-testid={`scope-selector-${sc.id}`}
              aria-pressed={scopeType === sc.id}
              onClick={() => onChangeScopeType?.(sc.id)}
              style={{
                padding: "4px 10px",
                borderRadius: "9999px",
                fontSize: "0.75rem",
                fontWeight: 600,
                cursor: "pointer",
                border:
                  scopeType === sc.id
                    ? "1px solid var(--orcia-action-primary)"
                    : "1px solid var(--orcia-border-subtle)",
                backgroundColor:
                  scopeType === sc.id
                    ? "var(--orcia-surface-secondary)"
                    : "var(--orcia-surface-elevated)",
                color: "var(--orcia-text-primary)",
              }}
            >
              {sc.text}
            </button>
          ))}
          {onOpenCommandPalette ? (
            <button
              type="button"
              data-testid="open-command-palette-btn"
              onClick={onOpenCommandPalette}
              style={{
                padding: "4px 10px",
                borderRadius: "6px",
                fontSize: "0.75rem",
                fontFamily: "var(--orcia-font-mono)",
                border: "1px solid var(--orcia-border-subtle)",
                backgroundColor: "var(--orcia-surface-elevated)",
                color: "var(--orcia-text-primary)",
                cursor: "pointer",
              }}
            >
              ⌘K Palette
            </button>
          ) : null}
        </div>
      </header>

      <div
        role="tablist"
        aria-label={labels.title}
        className="orcia-ds-tabs"
        style={{
          borderBottom: "1px solid var(--orcia-border-subtle)",
          paddingBottom: "8px",
        }}
      >
        {tabs.map((tab) => (
          <button
            key={tab.id}
            type="button"
            role="tab"
            aria-selected={activeTab === tab.id}
            data-testid={`control-center-tab-${tab.id}`}
            onClick={() => setActiveTab(tab.id)}
            className="orcia-ds-tab"
          >
            {tab.text}
          </button>
        ))}
      </div>

      {activeTab === "runs" ? (
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
      ) : null}

      {activeTab === "datasources" ? (
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
                {ds.workspaceName} • {ds.executionIdentity} • TTL {ds.freshnessTtlDays}j • [
                {ds.tripartiteStatus}]
              </div>
            </article>
          ))}
        </div>
      ) : null}

      {activeTab === "workflows" ? (
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
                1. Base: {ov.baseLayer} → 2. TEAM: {ov.teamOverride} → 3. WORKSPACE:{" "}
                {ov.workspaceOverride} → 4. USER: {ov.userOverride}
              </div>
            </article>
          ))}
        </div>
      ) : null}

      {activeTab === "governance" ? (
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
      ) : null}
    </section>
  );
}
