import React, { useState } from "react";
import { type GuidanceDrawerLabels, type GuidanceDrawerStepItem } from "./GuidanceDrawer";
import { type ProductLifecycleCardLabels, type ProductLifecyclePhaseType } from "./ProductLifecycleCard";
import { WorkspaceControlCenterTabs } from "./WorkspaceControlCenterTabs";

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
  readonly slug?: string;
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
  readonly consolidatedFinopsLabel?: string;
  readonly commandPaletteButtonLabel?: string;
  readonly ttlPrefix?: string;
  readonly daysShortUnit?: string;
  readonly overrideChainLabels?: {
    readonly base: string;
    readonly team: string;
    readonly workspace: string;
    readonly user: string;
  };
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
            {labels.consolidatedFinopsLabel
              ? `${scopeLabel} • ${labels.consolidatedFinopsLabel} `
              : `${scopeLabel} • `}
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
                padding: "4px 10px", borderRadius: "6px", fontSize: "0.75rem",
                fontFamily: "var(--orcia-font-mono)", border: "1px solid var(--orcia-border-subtle)",
                backgroundColor: "var(--orcia-surface-elevated)", color: "var(--orcia-text-primary)", cursor: "pointer",
              }}
            >
              {labels.commandPaletteButtonLabel ?? "⌘K"}
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

      <WorkspaceControlCenterTabs
        activeTab={activeTab}
        isReadOnlyObserver={isReadOnlyObserver}
        contributorRuns={contributorRuns}
        observerRuns={observerRuns}
        datasources={datasources}
        guidanceSteps={guidanceSteps}
        workflowOverrides={workflowOverrides}
        workspacesGovernance={workspacesGovernance}
        labels={labels}
        onSelectPhase={onSelectPhase}
      />
    </section>
  );
}
