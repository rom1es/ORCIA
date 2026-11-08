import React from "react";
import type {
  AgentsAndSkillsManagerLabels,
  AgentsAndSkillsSubTab,
  UiAgentSkillVisibilityFilter,
  UiAgentThinkingLevel,
  UiManagedSkillItem,
} from "./AgentsAndSkillsManagerView";
import { DisabledButtonAlertIndicator } from "./DisabledButtonAlertIndicator";
import { OrciaIcon, getOrciaIconGlyph } from "./icons";

export interface AgentCreateFormDrawerProps {
  readonly isOpen: boolean;
  readonly labels: AgentsAndSkillsManagerLabels;
  readonly skills: readonly UiManagedSkillItem[];
  readonly agentName: string;
  readonly agentRole: string;
  readonly agentInstructions: string;
  readonly agentThinking: UiAgentThinkingLevel;
  readonly agentVisibility: "PRIVATE" | "TEAM";
  readonly selectedSkillIds: readonly string[];
  readonly onChangeName: (v: string) => void;
  readonly onChangeRole: (v: string) => void;
  readonly onChangeInstructions: (v: string) => void;
  readonly onChangeThinking: (v: UiAgentThinkingLevel) => void;
  readonly onChangeVisibility: (v: "PRIVATE" | "TEAM") => void;
  readonly onToggleSkillId: (skillId: string, checked: boolean) => void;
  readonly onSubmit: (e: React.FormEvent) => void;
}

export const AgentCreateFormDrawer: React.FC<AgentCreateFormDrawerProps> = ({
  isOpen,
  labels,
  skills,
  agentName,
  agentRole,
  agentInstructions,
  agentThinking,
  agentVisibility,
  selectedSkillIds,
  onChangeName,
  onChangeRole,
  onChangeInstructions,
  onChangeThinking,
  onChangeVisibility,
  onToggleSkillId,
  onSubmit,
}) => {
  const isDisabled = !agentName.trim() || !agentRole.trim() || !agentInstructions.trim();

  return (
    <form
      onSubmit={onSubmit}
      autoComplete="off"
      data-lpignore="true"
      data-form-type="other"
      data-testid="create-agent-form"
      style={{ display: isOpen ? "grid" : "none" }}
      className="grid grid-cols-1 gap-3 rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] p-3 text-xs md:grid-cols-2"
    >
      <h3 className="font-semibold md:col-span-2">{labels.createAgentSectionTitle}</h3>
      <label className="flex flex-col gap-1">
        <span>{labels.agentNameLabel}</span>
        <input
          type="text"
          autoComplete="off"
          data-lpignore="true"
          data-1p-ignore="true"
          data-bwignore="true"
          data-form-type="other"
          data-testid="agent-name-input"
          value={agentName}
          onChange={(e) => onChangeName(e.target.value)}
          placeholder={labels.agentNamePlaceholder}
          className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2.5 py-1.5"
        />
      </label>
      <label className="flex flex-col gap-1">
        <span>{labels.agentThinkingLevelLabel}</span>
        <select
          data-testid="agent-thinking-level-select"
          value={agentThinking}
          onChange={(e) => onChangeThinking(e.target.value as UiAgentThinkingLevel)}
          className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2.5 py-1.5"
        >
          {(["simple", "medium", "complex", "auto"] as const).map((lvl) => (
            <option key={lvl} value={lvl}>
              {labels.thinkingLevels[lvl]}
            </option>
          ))}
        </select>
      </label>
      <label className="flex flex-col gap-1 md:col-span-2">
        <span>Visibilité &amp; Partage</span>
        <select
          data-testid="agent-visibility-select"
          value={agentVisibility}
          onChange={(e) => onChangeVisibility(e.target.value as "PRIVATE" | "TEAM")}
          className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2.5 py-1.5"
        >
          <option value="TEAM">{getOrciaIconGlyph("team")} Partagé avec mon Équipe &amp; Espace</option>
          <option value="PRIVATE">{getOrciaIconGlyph("lock")} Privé (Visible uniquement par moi)</option>
        </select>
      </label>
      <label className="flex flex-col gap-1 md:col-span-2">
        <span>{labels.agentRoleLabel}</span>
        <input
          type="text"
          autoComplete="off"
          data-lpignore="true"
          data-1p-ignore="true"
          data-bwignore="true"
          data-form-type="other"
          data-testid="agent-role-input"
          value={agentRole}
          onChange={(e) => onChangeRole(e.target.value)}
          placeholder={labels.agentRolePlaceholder}
          className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2.5 py-1.5"
        />
      </label>
      <label className="flex flex-col gap-1 md:col-span-2">
        <span>{labels.agentInstructionsLabel}</span>
        <textarea
          rows={2}
          autoComplete="off"
          data-lpignore="true"
          data-1p-ignore="true"
          data-bwignore="true"
          data-form-type="other"
          data-testid="agent-instructions-input"
          value={agentInstructions}
          onChange={(e) => onChangeInstructions(e.target.value)}
          placeholder={labels.agentInstructionsPlaceholder}
          className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2.5 py-1.5"
        />
      </label>
      <div className="space-y-1 md:col-span-2">
        <span className="font-medium">{labels.attachedSkillsLabel}</span>
        {skills.length === 0 ? (
          <p className="text-[11px] text-[var(--orcia-text-secondary)]">
            {labels.noSkillsAvailableHint}
          </p>
        ) : (
          <div className="flex flex-wrap gap-2">
            {skills.map((sk) => {
              const checked = selectedSkillIds.includes(sk.skillId);
              return (
                <label
                  key={sk.skillId}
                  className="inline-flex items-center gap-1.5 rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2 py-1"
                >
                  <input
                    type="checkbox"
                    autoComplete="off"
                    data-lpignore="true"
                    data-1p-ignore="true"
                    data-bwignore="true"
                    data-form-type="other"
                    data-testid={`create-agent-skill-checkbox-${sk.skillId}`}
                    checked={checked}
                    onChange={(e) => onToggleSkillId(sk.skillId, e.target.checked)}
                  />
                  <span>
                    {sk.name} (<code>{sk.commandHandle}</code>)
                  </span>
                </label>
              );
            })}
          </div>
        )}
      </div>
      <div className="md:col-span-2">
        <button
          type="submit"
          data-testid="create-agent-submit-btn"
          disabled={isDisabled}
          title={
            isDisabled
              ? "Renseignez le nom, le rôle et les instructions de l'agent pour activer sa création."
              : undefined
          }
          className="inline-flex items-center gap-2 rounded bg-[var(--orcia-action-primary)] px-3 py-1.5 text-xs font-semibold text-[var(--orcia-text-on-action)] disabled:opacity-50"
        >
          <span>{labels.createAgentButtonLabel}</span>
          <DisabledButtonAlertIndicator
            disabled={isDisabled}
            reason="Renseignez le nom, le rôle et les instructions de l'agent pour activer sa création."
            testIdSuffix="create-agent-submit-btn"
          />
        </button>
      </div>
    </form>
  );
};

export const AgentsAndSkillsHeaderAndToolbar: React.FC<{
  readonly labels: AgentsAndSkillsManagerLabels;
  readonly activeTab: AgentsAndSkillsSubTab;
  readonly agentsCount: number;
  readonly skillsCount: number;
  readonly searchQuery: string;
  readonly visibilityFilter: UiAgentSkillVisibilityFilter;
  readonly onSelectTab: (tab: AgentsAndSkillsSubTab) => void;
  readonly onToggleCreateAgent: () => void;
  readonly onToggleCreateSkill: () => void;
  readonly onChangeSearchQuery: (q: string) => void;
  readonly onChangeVisibilityFilter: (f: UiAgentSkillVisibilityFilter) => void;
  readonly onLoadPackTemplates?: () => void;
}> = ({
  labels,
  activeTab,
  agentsCount,
  skillsCount,
  searchQuery,
  visibilityFilter,
  onSelectTab,
  onToggleCreateAgent,
  onToggleCreateSkill,
  onChangeSearchQuery,
  onChangeVisibilityFilter,
  onLoadPackTemplates,
}) => (
  <>
    <header className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--orcia-border-subtle)] pb-3">
      <div>
        <h2 className="text-base font-semibold">{labels.heading}</h2>
        <p className="text-xs text-[var(--orcia-text-secondary)]">{labels.subtitle}</p>
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
            {`${labels.tabAgents} (${agentsCount})`}
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === "SKILLS"}
            data-testid="agents-subview-tab-skills"
            onClick={() => onSelectTab("SKILLS")}
            className="orcia-ds-tab"
          >
            {`${labels.tabSkills} (${skillsCount})`}
          </button>
          <button
            type="button"
            role="tab"
            aria-selected={activeTab === "CONNECTIONS"}
            data-testid="agents-subview-tab-connections"
            onClick={() => onSelectTab("CONNECTIONS")}
            style={{ display: "none" }}
            className="orcia-ds-tab"
          >
            {labels.tabConnections}
          </button>
        </div>
        {activeTab === "AGENTS" ? (
          <button
            type="button"
            data-testid="open-create-agent-drawer-btn"
            onClick={onToggleCreateAgent}
            className="rounded bg-[var(--orcia-action-primary)] px-3 py-1.5 text-xs font-semibold text-[var(--orcia-text-on-action)]"
          >
            + Nouvel Agent
          </button>
        ) : activeTab === "SKILLS" ? (
          <button
            type="button"
            data-testid="open-create-skill-drawer-btn"
            onClick={onToggleCreateSkill}
            className="rounded bg-[var(--orcia-action-primary)] px-3 py-1.5 text-xs font-semibold text-[var(--orcia-text-on-action)]"
          >
            + Nouvelle Compétence
          </button>
        ) : null}
      </div>
    </header>

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
        placeholder="Filtrer par nom, @agent, /compétence ou mission…"
        className="min-w-[240px] flex-1 rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] px-3 py-1.5"
      />
      <div
        role="group"
        aria-label="Filtrer par visibilité"
        className="flex flex-wrap items-center gap-1.5"
      >
        {(
          [
            ["ALL", "visibility-filter-all", "Tous", null],
            ["PRIVATE", "visibility-filter-private", "Privés", "lock"],
            ["TEAM", "visibility-filter-team", "Équipe / Espace", "team"],
            ["PACK", "visibility-filter-pack", "Packs Métiers", "spaces"],
          ] as const
        ).map(([filterKey, testId, filterLabel, iconName]) => (
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
        {onLoadPackTemplates && (
          <button
            type="button"
            data-testid="load-pack-agents-templates-btn"
            onClick={onLoadPackTemplates}
            className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] px-2.5 py-1 text-[11px] font-semibold"
          >
            <OrciaIcon name="spaces" /> Charger les Agents &amp; Compétences des Packs Métiers
          </button>
        )}
      </div>
    </div>
  </>
);
