import React from "react";

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
}

export interface WorkspaceFiveTabsAndExternalRebaseViewProps {
  readonly workspaceSlug: string;
  readonly activeTab: WorkspaceSubTabKey;
  readonly defaultArtifactDestinationUri: string;
  readonly pendingGlossaryCandidatesCount: number;
  readonly sources: readonly WorkspaceSourceItem[];
  readonly activeWaivers: readonly ExceptionWaiverItem[];
  readonly rebasedChunks: readonly RebasedChunkItem[];
  readonly labels: WorkspaceFiveTabsLabels;
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
  rebasedChunks,
  labels,
  onSelectTab,
  onRegisterWaiver,
}) => {
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

  return (
    <section
      aria-label={labels.heading}
      data-testid="workspace-five-tabs-view"
      className="rounded-lg border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] p-4 text-[var(--orcia-text-primary)]"
    >
      <header className="mb-4 flex flex-wrap items-center justify-between gap-2 border-b border-[var(--orcia-border-subtle)] pb-3">
        <div>
          <h2 className="text-base font-semibold">{labels.heading}</h2>
          <p className="font-mono text-xs text-[var(--orcia-text-secondary)]">
            {workspaceSlug}
          </p>
        </div>
        <div
          data-testid="workspace-default-destination"
          className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] px-3 py-1.5 text-xs"
        >
          <span className="font-medium">{labels.defaultDestinationTitle}: </span>
          <code className="font-mono">{defaultArtifactDestinationUri}</code>
        </div>
      </header>

      <nav
        role="tablist"
        aria-label={labels.heading}
        className="mb-4 flex flex-wrap gap-2"
      >
        {tabs.map((tab) => {
          const isSelected = tab.key === activeTab;
          return (
            <button
              key={tab.key}
              type="button"
              role="tab"
              aria-selected={isSelected}
              data-testid={`workspace-tab-${tab.key}`}
              onClick={() => onSelectTab?.(tab.key)}
              className={`inline-flex items-center gap-1.5 rounded px-3 py-1.5 text-xs font-medium transition-colors ${
                isSelected
                  ? "bg-[var(--orcia-action-primary)] text-[var(--orcia-text-on-action)]"
                  : "bg-[var(--orcia-surface-secondary)] text-[var(--orcia-text-secondary)]"
              }`}
            >
              <span>{tab.label}</span>
              {tab.badge !== undefined && (
                <span
                  data-testid={`workspace-tab-badge-${tab.key}`}
                  className="rounded-full bg-[var(--orcia-surface-primary)] px-1.5 py-0.5 font-mono text-[10px]"
                >
                  {tab.badge}
                </span>
              )}
            </button>
          );
        })}
      </nav>

      <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div
          data-testid="workspace-sources-panel"
          className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] p-3"
        >
          <h3 className="mb-2 text-xs font-semibold uppercase tracking-wide text-[var(--orcia-text-secondary)]">
            {labels.tabDocumentsSources}
          </h3>
          <ul className="space-y-2">
            {sources.map((src) => (
              <li
                key={src.sourceId}
                data-testid={`workspace-source-${src.sourceId}`}
                className="flex flex-wrap items-center justify-between gap-2 rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] p-2 text-xs"
              >
                <div>
                  <div className="font-medium">{src.title}</div>
                  <code className="font-mono text-[11px] text-[var(--orcia-text-secondary)]">
                    {src.uri}
                  </code>
                </div>
                <div className="flex flex-wrap items-center gap-1.5">
                  <span className="rounded border border-[var(--orcia-border-subtle)] px-2 py-0.5 text-[11px]">
                    {src.authorityRole === "REFERENCE"
                      ? labels.roleReferenceBadge
                      : labels.roleActiveBadge}
                  </span>
                  <span className="rounded border border-[var(--orcia-border-subtle)] px-2 py-0.5 text-[11px]">
                    {src.accessMode === "READ_ONLY"
                      ? labels.modeReadOnlyBadge
                      : labels.modeReadWriteBadge}
                  </span>
                  {src.freshnessStatus === "STALE_WARNING" && onRegisterWaiver && (
                    <button
                      type="button"
                      data-testid={`register-waiver-btn-${src.sourceId}`}
                      onClick={() => onRegisterWaiver(src.uri, "RULE_FRESHNESS_DRIFT")}
                      className="rounded bg-[var(--orcia-action-primary)] px-2 py-0.5 text-[11px] text-[var(--orcia-text-on-action)]"
                    >
                      {labels.registerWaiverCta}
                    </button>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </div>

        <div
          data-testid="workspace-waivers-and-rebase-panel"
          className="space-y-3 rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] p-3"
        >
          <div>
            <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-[var(--orcia-text-secondary)]">
              {labels.waiverSectionTitle}
            </h3>
            <p
              data-testid="inviolable-enterprise-lock-notice"
              className="mb-2 text-xs text-[var(--orcia-status-warning)]"
            >
              {labels.inviolableEnterpriseLockNotice}
            </p>
            <ul className="space-y-1.5">
              {activeWaivers.map((w) => (
                <li
                  key={w.waiverId}
                  data-testid={`waiver-item-${w.waiverId}`}
                  className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] p-2 text-xs"
                >
                  <div className="flex items-center justify-between">
                    <code className="font-mono">{w.conflictRuleId}</code>
                    <span className="font-mono text-[11px]">{w.normLevel}</span>
                  </div>
                  <div className="text-[11px] text-[var(--orcia-text-secondary)]">
                    {w.reason}
                  </div>
                </li>
              ))}
            </ul>
          </div>

          <div className="border-t border-[var(--orcia-border-subtle)] pt-2">
            <h3 className="mb-1 text-xs font-semibold uppercase tracking-wide text-[var(--orcia-text-secondary)]">
              {labels.externalRebaseTitle}
            </h3>
            <p className="mb-2 font-mono text-[11px] text-[var(--orcia-text-secondary)]">
              {labels.supersededMemlogNotice}
            </p>
            <ul className="space-y-1.5">
              {rebasedChunks.map((chunk) => (
                <li
                  key={chunk.chunkKey}
                  data-testid={`rebased-chunk-${chunk.chunkKey}`}
                  className="flex items-center justify-between rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] p-2 text-xs"
                >
                  <span className="font-medium">{chunk.sectionTitle}</span>
                  {chunk.status === "HUMAN_AMENDED_EXTERNAL" && (
                    <span
                      data-testid={`human-amended-badge-${chunk.chunkKey}`}
                      className="rounded bg-[var(--orcia-surface-secondary)] px-2 py-0.5 font-mono text-[11px]"
                    >
                      {labels.humanAmendedBadge}
                    </span>
                  )}
                </li>
              ))}
            </ul>
          </div>
        </div>
      </div>
    </section>
  );
};
