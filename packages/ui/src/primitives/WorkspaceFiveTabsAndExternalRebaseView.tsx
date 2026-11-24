import React from "react";
import {
  DeliverablesTabPanel,
  MembersTeamTabPanel,
} from "./WorkspaceFiveTabsDeliverablesAndMembersPanels";
import {
  GlossaryRulesTabPanel,
  OverviewTabPanel,
} from "./WorkspaceFiveTabsOverviewAndGlossaryPanels";
import {
  sanitizeUiDestinationUri,
  sanitizeUiWorkspaceSlug,
  SourcesTabListPanel,
  WaiversAndRebasePanel,
} from "./WorkspaceFiveTabsPanels";

export type WorkspaceSubTabKey =
  | "OVERVIEW"
  | "DOCUMENTS_SOURCES"
  | "DELIVERABLES_ARTIFACTS"
  | "GLOSSARY_RULES"
  | "MEMBERS_TEAM";

export interface WorkspaceSourceItem {
  readonly sourceId: string;
  readonly uri: string;
  readonly title: string;
  readonly authorityRole: "REFERENCE" | "ACTIVE";
  readonly accessMode: "READ_ONLY" | "READ_WRITE_TARGET";
  readonly freshnessStatus: "FRESH" | "STALE_WARNING" | "WAIVED";
}

export interface ExceptionWaiverItem {
  readonly waiverId: string;
  readonly sourceUri: string;
  readonly conflictRuleId: string;
  readonly normLevel: "1_ENTERPRISE" | "2_DOMAIN" | "3_TEAM" | "3_WORKSPACE";
  readonly hasInviolableEnterpriseDirective: boolean;
  readonly status: "ACTIVE" | "INVALIDATED_SHA_DRIFT" | "EXPIRED" | "REVOKED";
  readonly reason: string;
}

export interface RebasedChunkItem {
  readonly chunkKey: string;
  readonly sectionTitle: string;
  readonly status: "APPROVED" | "HUMAN_AMENDED_EXTERNAL";
  readonly lockedAgainstAgentOverwrite: boolean;
}

export interface WorkspaceDeliverableItem {
  readonly deliverableId: string;
  readonly title: string;
  readonly casUri: string;
  readonly versionLabel: string;
  readonly status: string;
}

export interface WorkspaceFiveTabsLabels {
  readonly heading: string;
  readonly tabOverview: string;
  readonly tabDocumentsSources: string;
  readonly tabDeliverablesArtifacts: string;
  readonly tabGlossaryRules: string;
  readonly tabMembersTeam: string;
  readonly defaultDestinationTitle: string;
  readonly roleReferenceBadge: string;
  readonly roleActiveBadge: string;
  readonly modeReadOnlyBadge: string;
  readonly modeReadWriteBadge: string;
  readonly waiverSectionTitle: string;
  readonly inviolableEnterpriseLockNotice: string;
  readonly externalRebaseTitle: string;
  readonly humanAmendedBadge: string;
  readonly supersededMemlogNotice: string;
  readonly registerWaiverCta: string;
  readonly overviewSummaryText?: string;
  readonly overviewEmptyStateHint?: string;
  readonly teamBillingLabel?: string;
  readonly visibilityLabel?: string;
  readonly roleLabel?: string;
  readonly phaseLabel?: string;
  readonly emptyDeliverablesText?: string;
  readonly deliverablesCatalogTitle?: string;
  readonly emptyGlossaryRulesText?: string;
  readonly membersAccessHint?: string;
}

export interface WorkspaceFiveTabsAndExternalRebaseViewProps {
  readonly workspaceSlug: string;
  readonly activeTab: WorkspaceSubTabKey;
  readonly defaultArtifactDestinationUri: string;
  readonly pendingGlossaryCandidatesCount: number;
  readonly sources: readonly WorkspaceSourceItem[];
  readonly activeWaivers: readonly ExceptionWaiverItem[];
  readonly deliverables?: readonly WorkspaceDeliverableItem[];
  readonly rebasedChunks: readonly RebasedChunkItem[];
  readonly labels: WorkspaceFiveTabsLabels;
  readonly workspaceName?: string;
  readonly ownerOrgUnitName?: string | null;
  readonly visibilityLabel?: string;
  readonly effectiveRoleLabel?: string;
  readonly lifecyclePhaseLabel?: string;
  readonly submitting?: boolean;
  readonly sourcesTabSlot?: React.ReactNode;
  readonly deliverablesTabSlot?: React.ReactNode;
  readonly glossaryTabSlot?: React.ReactNode;
  readonly membersTabSlot?: React.ReactNode;
  readonly onSelectTab?: (tab: WorkspaceSubTabKey) => void;
  readonly onRegisterWaiver?: (sourceUri: string, conflictRuleId: string) => void;
}

export const WorkspaceFiveTabsAndExternalRebaseView: React.FC<
  WorkspaceFiveTabsAndExternalRebaseViewProps
> = ({
  workspaceSlug,
  activeTab,
  defaultArtifactDestinationUri,
  pendingGlossaryCandidatesCount,
  sources,
  activeWaivers,
  deliverables = [],
  rebasedChunks,
  labels,
  workspaceName,
  ownerOrgUnitName,
  visibilityLabel,
  effectiveRoleLabel,
  lifecyclePhaseLabel,
  submitting = false,
  sourcesTabSlot,
  deliverablesTabSlot,
  glossaryTabSlot,
  membersTabSlot,
  onSelectTab,
  onRegisterWaiver,
}) => {
  const safeSlug = sanitizeUiWorkspaceSlug(workspaceSlug, workspaceName);
  const safeDestinationUri = sanitizeUiDestinationUri(defaultArtifactDestinationUri, safeSlug);

  const tabs: readonly { key: WorkspaceSubTabKey; label: string; badge?: number }[] = [
    { key: "OVERVIEW", label: labels.tabOverview },
    { key: "DOCUMENTS_SOURCES", label: labels.tabDocumentsSources, badge: sources.length },
    { key: "DELIVERABLES_ARTIFACTS", label: labels.tabDeliverablesArtifacts },
    {
      key: "GLOSSARY_RULES",
      label: labels.tabGlossaryRules,
      badge: pendingGlossaryCandidatesCount > 0 ? pendingGlossaryCandidatesCount : undefined,
    },
    { key: "MEMBERS_TEAM", label: labels.tabMembersTeam },
  ];

  const overviewStats: readonly { key: string; title: string; value: string | number }[] = [
    { key: "sources", title: labels.tabDocumentsSources, value: sources.length },
    { key: "glossary", title: labels.tabGlossaryRules, value: pendingGlossaryCandidatesCount },
    { key: "waivers", title: labels.waiverSectionTitle, value: activeWaivers.length },
    {
      key: "phase",
      title: labels.phaseLabel ?? labels.tabDeliverablesArtifacts,
      value: lifecyclePhaseLabel ?? "—",
    },
  ];

  const sharedWaiverProps = {
    workspaceSlug: safeSlug,
    defaultArtifactDestinationUri: safeDestinationUri,
    sources,
    activeWaivers,
    rebasedChunks,
    labels,
    submitting,
    onRegisterWaiver,
  };

  const renderTabPanel = (): React.ReactNode => {
    switch (activeTab) {
      case "OVERVIEW":
        return (
          <OverviewTabPanel
            sourcesCount={sources.length}
            pendingGlossaryCandidatesCount={pendingGlossaryCandidatesCount}
            activeWaivers={activeWaivers}
            overviewStats={overviewStats}
            labels={labels}
            workspaceName={workspaceName}
            safeSlug={safeSlug}
            sharedWaiverProps={sharedWaiverProps}
          />
        );

      case "DOCUMENTS_SOURCES":
        if (sourcesTabSlot) {
          return (
            <div role="tabpanel" aria-labelledby="workspace-tab-DOCUMENTS_SOURCES">
              <div
                data-testid="workspace-sources-panel"
                className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] p-3"
              >
                {sourcesTabSlot}
              </div>
            </div>
          );
        }
        return (
          <div
            role="tabpanel"
            aria-labelledby="workspace-tab-DOCUMENTS_SOURCES"
            className="grid grid-cols-1 gap-4 md:grid-cols-2"
          >
            <SourcesTabListPanel
              sources={sources}
              labels={labels}
              submitting={submitting}
              onRegisterWaiver={onRegisterWaiver}
            />
            <WaiversAndRebasePanel {...sharedWaiverProps} />
          </div>
        );

      case "DELIVERABLES_ARTIFACTS":
        return (
          <DeliverablesTabPanel
            workspaceSlug={safeSlug}
            defaultArtifactDestinationUri={safeDestinationUri}
            deliverables={deliverables}
            rebasedChunks={rebasedChunks}
            deliverablesTabSlot={deliverablesTabSlot}
            labels={labels}
          />
        );

      case "GLOSSARY_RULES":
        return (
          <GlossaryRulesTabPanel
            pendingGlossaryCandidatesCount={pendingGlossaryCandidatesCount}
            activeWaiversCount={activeWaivers.length}
            labels={labels}
            glossaryTabSlot={glossaryTabSlot}
            sharedWaiverProps={sharedWaiverProps}
          />
        );

      case "MEMBERS_TEAM":
        return (
          <MembersTeamTabPanel
            workspaceSlug={safeSlug}
            workspaceName={workspaceName}
            ownerOrgUnitName={ownerOrgUnitName}
            visibilityLabel={visibilityLabel}
            effectiveRoleLabel={effectiveRoleLabel}
            labels={labels}
            membersTabSlot={membersTabSlot}
          />
        );
    }
  };

  return (
    <section
      aria-label={labels.heading}
      data-testid="workspace-five-tabs-view"
      className="rounded-lg border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] p-4 text-[var(--orcia-text-primary)]"
    >
      <nav role="tablist" aria-label={labels.heading} className="orcia-ds-tabs mb-4">
        {tabs.map((tab) => {
          const isSelected = tab.key === activeTab;
          return (
            <button
              key={tab.key}
              id={`workspace-tab-${tab.key}`}
              type="button"
              role="tab"
              aria-selected={isSelected}
              data-testid={`workspace-tab-${tab.key}`}
              onClick={() => onSelectTab?.(tab.key)}
              className="orcia-ds-tab inline-flex items-center gap-1.5"
            >
              <span>{tab.label}</span>
              {tab.badge !== undefined && (
                <span
                  data-testid={`workspace-tab-badge-${tab.key}`}
                  className="rounded-full bg-[var(--orcia-surface-primary)] px-1.5 py-0.5 font-mono text-[10px] text-[var(--color-text-primary)]"
                >
                  {tab.badge}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      {renderTabPanel()}
    </section>
  );
};
