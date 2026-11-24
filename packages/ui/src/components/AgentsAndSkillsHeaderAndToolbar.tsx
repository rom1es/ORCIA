import React from "react";
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

  return (
    <>
      <header className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--orcia-border-subtle)] pb-3">
        <div>
          <h2 className="text-base font-semibold">{labels.heading}</h2>
          <p className="text-xs text-[var(--orcia-text-secondary)]">
            {labels.subtitle}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          <div role="tablist" className="orcia-ds-tabs">
            <button
              type="button"
              role="tab"
              aria-selected={activeTab === "AGENTS"}
              data-testid="agents-subview-tab-agents"
              onClick={() => onSelectTab("AGENTS")}
              className="orcia-ds-tab"
            >
              {agentsCount > 0
                ? `${labels.tabAgents} (${agentsCount})`
                : labels.tabAgents}
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={activeTab === "SKILLS"}
              data-testid="agents-subview-tab-skills"
              onClick={() => onSelectTab("SKILLS")}
              className="orcia-ds-tab"
            >
              {skillsCount > 0
                ? `${labels.tabSkills} (${skillsCount})`
                : labels.tabSkills}
            </button>
            <button
              type="button"
              role="tab"
              aria-selected={activeTab === "CONNECTIONS"}
              data-testid="agents-subview-tab-connections"
              onClick={() => onSelectTab("CONNECTIONS")}
              className="orcia-ds-tab"
            >
              {labels.tabConnections}
            </button>
          </div>
          {onLoadPackTemplates && (
            <button
              type="button"
              data-testid="load-pack-agents-templates-btn"
              onClick={onLoadPackTemplates}
              className="orcia-ds-btn orcia-ds-btn-secondary text-xs"
            >
              <OrciaIcon name="spaces" /> {studio.loadPackAgentsButton}
            </button>
          )}
          {activeTab === "AGENTS" ? (
            <button
              type="button"
              data-testid="open-create-agent-drawer-btn"
              onClick={onToggleCreateAgent}
              className="orcia-ds-btn orcia-ds-btn-primary text-xs"
            >
              {studio.newAgentButton}
            </button>
          ) : activeTab === "SKILLS" ? (
            <button
              type="button"
              data-testid="open-create-skill-drawer-btn"
              onClick={onToggleCreateSkill}
              className="orcia-ds-btn orcia-ds-btn-primary text-xs"
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
              className="orcia-ds-btn orcia-ds-btn-primary text-xs"
            >
              <OrciaIcon name="plug" /> {studio.testMcpButton}
            </button>
          )}
        </div>
      </header>

      {agentsCount + skillsCount > 0 && (
        <div
          data-testid="agents-kpi-strip"
          className="grid grid-cols-1 gap-2 text-xs md:grid-cols-3"
        >
          {(activeAgentsCount ?? agentsCount) > 0 && (
            <div className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] px-3 py-2">
              <span className="block text-[10px] font-semibold uppercase tracking-wide text-[var(--orcia-text-secondary)]">
                {studio.kpiAgentsTitle}
              </span>
              <strong className="text-sm text-[var(--orcia-text-primary)]">
                {activeAgentsCount ?? agentsCount} {studio.kpiActiveSuffix}
              </strong>
            </div>
          )}
          {skillsCount > 0 && (
            <div className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] px-3 py-2">
              <span className="block text-[10px] font-semibold uppercase tracking-wide text-[var(--orcia-text-secondary)]">
                {studio.kpiSkillsTitle}
              </span>
              <strong className="text-sm text-[var(--orcia-text-primary)]">
                {skillsCount} {studio.kpiReusableSuffix}
              </strong>
            </div>
          )}
          {(packOrTeamAgentsCount > 0 || mcpExposedAgentsCount > 0) && (
            <div className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] px-3 py-2">
              <span className="block text-[10px] font-semibold uppercase tracking-wide text-[var(--orcia-text-secondary)]">
                {studio.kpiOriginMcpTitle}
              </span>
              <strong className="text-sm text-[var(--orcia-text-primary)]">
                {[
                  packOrTeamAgentsCount > 0
                    ? `${packOrTeamAgentsCount} ${studio.kpiPackTeamSuffix}`
                    : null,
                  mcpExposedAgentsCount > 0
                    ? `${mcpExposedAgentsCount} ${studio.mcpActiveBadge}`
                    : null,
                ]
                  .filter(Boolean)
                  .join(" · ")}
              </strong>
            </div>
          )}
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
              className={`rounded-full border border-[var(--orcia-border-subtle)] px-2.5 py-1 text-[11px] font-medium ${
                visibilityFilter === filterKey
                  ? "bg-[var(--orcia-action-primary)] text-[var(--orcia-text-on-action)]"
                  : "bg-[var(--orcia-surface-secondary)] text-[var(--orcia-text-primary)]"
              }`}
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
    </>
  );
};
