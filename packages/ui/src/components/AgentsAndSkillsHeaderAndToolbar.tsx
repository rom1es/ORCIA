import React from "react";
import { OrciaDataCard } from "../primitives/OrciaDataCard";
import { OrciaPageHeader } from "../primitives/OrciaPageHeader";
import { OrciaTabStrip, type OrciaTabStripItem } from "../primitives/OrciaTabStrip";
import type {
  AgentsAndSkillsManagerLabels,
  AgentsAndSkillsSubTab,
  UiAgentSkillVisibilityFilter,
} from "./AgentsAndSkillsTypes";
import { OrciaIcon } from "./icons";

export const AgentsAndSkillsHeaderAndToolbar: React.FC<{
  readonly labels: AgentsAndSkillsManagerLabels;
  readonly activeTab: AgentsAndSkillsSubTab;
  readonly agentsCount: number;
  readonly activeAgentsCount?: number;
  readonly skillsCount: number;
  readonly packOrTeamAgentsCount?: number;
  readonly mcpExposedAgentsCount?: number;
  readonly searchQuery: string;
  readonly visibilityFilter: UiAgentSkillVisibilityFilter;
  readonly alertSlot?: React.ReactNode;
  readonly onSelectTab: (tab: AgentsAndSkillsSubTab) => void;
  readonly onToggleCreateAgent: () => void;
  readonly onToggleCreateSkill: () => void;
  readonly onOpenMcpTestBench?: () => void;
  readonly onChangeSearchQuery: (q: string) => void;
  readonly onChangeVisibilityFilter: (f: UiAgentSkillVisibilityFilter) => void;
  readonly onLoadPackTemplates?: () => void;
}> = ({
  labels,
  activeTab,
  agentsCount,
  activeAgentsCount,
  skillsCount,
  packOrTeamAgentsCount = 0,
  mcpExposedAgentsCount = 0,
  searchQuery,
  visibilityFilter,
  alertSlot,
  onSelectTab,
  onToggleCreateAgent,
  onToggleCreateSkill,
  onOpenMcpTestBench,
  onChangeSearchQuery,
  onChangeVisibilityFilter,
  onLoadPackTemplates,
}) => {
  const studio = labels.studio;
  const filterItems = [
    ["ALL", "visibility-filter-all", studio.filterAll, null],
    ["PACK", "visibility-filter-pack", studio.filterPack, "spaces"],
    ["TEAM", "visibility-filter-team", studio.filterTeam, "team"],
    ["PRIVATE", "visibility-filter-private", studio.filterPrivate, "lock"],
  ] as const;

  const tabs: readonly OrciaTabStripItem<AgentsAndSkillsSubTab>[] = [
    {
      key: "AGENTS",
      label: agentsCount > 0 ? `${labels.tabAgents} (${agentsCount})` : labels.tabAgents,
      icon: "agents",
      testId: "agents-subview-tab-agents",
    },
    {
      key: "SKILLS",
      label: skillsCount > 0 ? `${labels.tabSkills} (${skillsCount})` : labels.tabSkills,
      icon: "tools",
      testId: "agents-subview-tab-skills",
    },
    {
      key: "CONNECTIONS",
      label: labels.tabConnections,
      icon: "plug",
      testId: "agents-subview-tab-connections",
    },
  ];

  const primaryAction =
    activeTab === "AGENTS" ? (
      <button
        type="button"
        data-testid="open-create-agent-drawer-btn"
        onClick={onToggleCreateAgent}
        className="orcia-ds-btn orcia-ds-btn-primary orcia-ds-btn-sm orcia-ds-nowrap"
      >
        {studio.newAgentButton}
      </button>
    ) : activeTab === "SKILLS" ? (
      <button
        type="button"
        data-testid="open-create-skill-drawer-btn"
        onClick={onToggleCreateSkill}
        className="orcia-ds-btn orcia-ds-btn-primary orcia-ds-btn-sm orcia-ds-nowrap"
      >
        {studio.newSkillButton}
      </button>
    ) : (
      <button
        type="button"
        data-testid="open-mcp-test-bench-btn"
        onClick={() => {
          onSelectTab("CONNECTIONS");
          onOpenMcpTestBench?.();
        }}
        className="orcia-ds-btn orcia-ds-btn-primary orcia-ds-btn-sm orcia-ds-nowrap"
      >
        <OrciaIcon name="plug" />
        <span>{studio.testMcpButton}</span>
      </button>
    );

  const showCatalogControls = activeTab !== "CONNECTIONS";

  return (
    <>
      <OrciaPageHeader
        testId="agents-page-header"
        icon="agents"
        title={labels.heading}
        subtitle={labels.subtitle}
        secondaryActions={
          onLoadPackTemplates ? (
            <button
              type="button"
              data-testid="load-pack-agents-templates-btn"
              onClick={onLoadPackTemplates}
              className="orcia-ds-btn orcia-ds-btn-secondary orcia-ds-btn-sm orcia-ds-nowrap"
            >
              <OrciaIcon name="spaces" />
              <span>{studio.loadPackAgentsButton}</span>
            </button>
          ) : null
        }
        primaryAction={primaryAction}
        tabs={
          <OrciaTabStrip<AgentsAndSkillsSubTab>
            testId="agents-tab-strip"
            ariaLabel={labels.tabsAriaLabel ?? labels.heading}
            variant="underline"
            tabs={tabs}
            activeTabId={activeTab}
            onSelectTab={onSelectTab}
          />
        }
        alertSlot={alertSlot}
      />

      {showCatalogControls ? (
        <OrciaDataCard testId="agents-kpi-and-filters-card">
          {agentsCount + skillsCount > 0 && (
            <div
              data-testid="agents-kpi-strip"
              className="grid grid-cols-1 gap-2 text-xs md:grid-cols-3"
            >
              {(activeAgentsCount ?? agentsCount) > 0 && (() => {
                const resolvedActive = activeAgentsCount ?? agentsCount;
                const activeSuffix =
                  resolvedActive === 1
                    ? (studio.kpiActiveSingular ?? studio.kpiActiveSuffix)
                    : studio.kpiActiveSuffix;
                return (
                  <div className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] px-3 py-2">
                    <span className="block text-[10px] font-semibold uppercase tracking-wide text-[var(--orcia-text-secondary)]">
                      {studio.kpiAgentsTitle}
                    </span>
                    <strong className="text-sm text-[var(--orcia-text-primary)]">
                      {resolvedActive} {activeSuffix}
                    </strong>
                  </div>
                );
              })()}
              {skillsCount > 0 && (() => {
                const reusableSuffix =
                  skillsCount === 1
                    ? (studio.kpiReusableSingular ?? studio.kpiReusableSuffix)
                    : studio.kpiReusableSuffix;
                return (
                  <div className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] px-3 py-2">
                    <span className="block text-[10px] font-semibold uppercase tracking-wide text-[var(--orcia-text-secondary)]">
                      {studio.kpiSkillsTitle}
                    </span>
                    <strong className="text-sm text-[var(--orcia-text-primary)]">
                      {skillsCount} {reusableSuffix}
                    </strong>
                  </div>
                );
              })()}
              {(packOrTeamAgentsCount > 0 || mcpExposedAgentsCount > 0) && (() => {
                const packTeamSuffix =
                  packOrTeamAgentsCount === 1
                    ? (studio.kpiPackTeamSingular ?? studio.kpiPackTeamSuffix)
                    : studio.kpiPackTeamSuffix;
                return (
                  <div className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] px-3 py-2">
                    <span className="block text-[10px] font-semibold uppercase tracking-wide text-[var(--orcia-text-secondary)]">
                      {studio.kpiOriginMcpTitle}
                    </span>
                    <strong className="text-sm text-[var(--orcia-text-primary)]">
                      {[
                        packOrTeamAgentsCount > 0
                          ? `${packOrTeamAgentsCount} ${packTeamSuffix}`
                          : null,
                        mcpExposedAgentsCount > 0
                          ? `${mcpExposedAgentsCount} ${
                              mcpExposedAgentsCount === 1
                                ? (studio.mcpActiveSingular ?? studio.mcpActiveBadge)
                                : studio.mcpActiveBadge
                            }`
                          : null,
                      ]
                        .filter(Boolean)
                        .join(" · ")}
                    </strong>
                  </div>
                );
              })()}
            </div>
          )}

          <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
            <input
              type="text"
              autoComplete="off"
              data-lpignore="true"
              data-1p-ignore="true"
              data-bwignore="true"
              data-form-type="other"
              data-testid="agents-skills-search-input"
              value={searchQuery}
              onChange={(e) => onChangeSearchQuery(e.target.value)}
              placeholder={studio.searchPlaceholder}
              className="orcia-ds-input min-w-[240px] flex-1"
            />
            <div
              role="group"
              aria-label={studio.visibilityFilterAriaLabel}
              className="flex flex-wrap items-center gap-1.5"
            >
              {filterItems.map(([filterKey, testId, filterLabel, iconName]) => (
                <button
                  key={filterKey}
                  type="button"
                  data-testid={testId}
                  aria-pressed={visibilityFilter === filterKey}
                  onClick={() => onChangeVisibilityFilter(filterKey)}
                  className="orcia-ds-filter-pill"
                >
                  {iconName ? (
                    <>
                      <OrciaIcon name={iconName} /> {filterLabel}
                    </>
                  ) : (
                    filterLabel
                  )}
                </button>
              ))}
            </div>
          </div>
        </OrciaDataCard>
      ) : null}
    </>
  );
};
