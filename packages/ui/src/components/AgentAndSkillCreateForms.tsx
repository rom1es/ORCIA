import React, { useEffect } from "react";
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
  readonly onClose?: () => void;
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
  onClose,
}) => {
  useEffect(() => {
    if (!isOpen || !onClose) return;
    const onKeyDown = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        onClose();
      }
    };
    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [isOpen, onClose]);

  if (!isOpen) return null;

  const isDisabled = !agentName.trim() || !agentRole.trim() || !agentInstructions.trim();
  const disabledReason = "Renseignez le nom, le rôle et les instructions de l'agent pour activer sa création.";

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={labels.createAgentSectionTitle}
      data-testid="create-agent-modal"
      className="fixed inset-0 z-40 flex items-center justify-center p-4"
      style={{ backgroundColor: "var(--color-modal-backdrop)" }}
    >
      <div className="w-[680px] max-h-[600px] flex flex-col rounded-xl border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] text-[var(--orcia-text-primary)] shadow-xl overflow-hidden">
        <header className="flex items-center justify-between border-b border-[var(--orcia-border-subtle)] px-4 py-3">
          <h3 className="text-sm font-semibold">{labels.createAgentSectionTitle}</h3>
          <button type="button" data-testid="close-create-agent-modal-btn" onClick={onClose} className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] px-2.5 py-1 text-xs font-medium">
            Annuler
          </button>
        </header>

        <form onSubmit={onSubmit} autoComplete="off" data-lpignore="true" data-form-type="other" data-testid="create-agent-form" className="grid grid-cols-1 gap-3 overflow-y-auto p-4 text-xs md:grid-cols-2">
          <label className="flex flex-col gap-1">
            <span>{labels.agentNameLabel}</span>
            <input type="text" autoComplete="off" data-lpignore="true" data-1p-ignore="true" data-bwignore="true" data-form-type="other" data-testid="agent-name-input" value={agentName} onChange={(e) => onChangeName(e.target.value)} placeholder={labels.agentNamePlaceholder} className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] px-2.5 py-1.5" />
          </label>
          <label className="flex flex-col gap-1">
            <span>{labels.agentThinkingLevelLabel}</span>
            <select data-testid="agent-thinking-level-select" value={agentThinking} onChange={(e) => onChangeThinking(e.target.value as UiAgentThinkingLevel)} className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] px-2.5 py-1.5">
              {(["simple", "medium", "complex", "auto"] as const).map((lvl) => (
                <option key={lvl} value={lvl}>{labels.thinkingLevels[lvl]}</option>
              ))}
            </select>
          </label>
          <label className="flex flex-col gap-1 md:col-span-2">
            <span>Visibilité &amp; Partage</span>
            <select data-testid="agent-visibility-select" value={agentVisibility} onChange={(e) => onChangeVisibility(e.target.value as "PRIVATE" | "TEAM")} className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] px-2.5 py-1.5">
              <option value="TEAM">{getOrciaIconGlyph("team")} Partagé avec mon Équipe &amp; Espace</option>
              <option value="PRIVATE">{getOrciaIconGlyph("lock")} Privé (Visible uniquement par moi)</option>
            </select>
          </label>
          <label className="flex flex-col gap-1 md:col-span-2">
            <span>{labels.agentRoleLabel}</span>
            <input type="text" autoComplete="off" data-lpignore="true" data-1p-ignore="true" data-bwignore="true" data-form-type="other" data-testid="agent-role-input" value={agentRole} onChange={(e) => onChangeRole(e.target.value)} placeholder={labels.agentRolePlaceholder} className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] px-2.5 py-1.5" />
          </label>
          <label className="flex flex-col gap-1 md:col-span-2">
            <span>{labels.agentInstructionsLabel}</span>
            <textarea rows={2} autoComplete="off" data-lpignore="true" data-1p-ignore="true" data-bwignore="true" data-form-type="other" data-testid="agent-instructions-input" value={agentInstructions} onChange={(e) => onChangeInstructions(e.target.value)} placeholder={labels.agentInstructionsPlaceholder} className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] px-2.5 py-1.5" />
          </label>
          <div className="space-y-1 md:col-span-2">
            <span className="font-medium">{labels.attachedSkillsLabel}</span>
            {skills.length === 0 ? (
              <p className="text-[11px] text-[var(--orcia-text-secondary)]">{labels.noSkillsAvailableHint}</p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {skills.map((sk) => {
                  const checked = selectedSkillIds.includes(sk.skillId);
                  return (
                    <label key={sk.skillId} className="inline-flex items-center gap-1.5 rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] px-2 py-1">
                      <input type="checkbox" autoComplete="off" data-lpignore="true" data-1p-ignore="true" data-bwignore="true" data-form-type="other" data-testid={`create-agent-skill-checkbox-${sk.skillId}`} checked={checked} onChange={(e) => onToggleSkillId(sk.skillId, e.target.checked)} />
                      <span>{sk.name} (<code>{sk.commandHandle}</code>)</span>
                    </label>
                  );
                })}
              </div>
            )}
          </div>
          <div className="flex items-center justify-end gap-2 pt-2 md:col-span-2">
            <button type="submit" data-testid="create-agent-submit-btn" disabled={isDisabled} title={isDisabled ? disabledReason : undefined} className="inline-flex items-center gap-2 rounded bg-[var(--orcia-action-primary)] px-3 py-1.5 text-xs font-semibold text-[var(--orcia-text-on-action)] disabled:opacity-50">
              <span>{labels.createAgentButtonLabel}</span>
              <DisabledButtonAlertIndicator disabled={isDisabled} reason={disabledReason} testIdSuffix="create-agent-submit-btn" />
            </button>
          </div>
        </form>
      </div>
    </div>
  );
};

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
}) => (
  <>
    <header className="flex flex-wrap items-center justify-between gap-3 border-b border-[var(--orcia-border-subtle)] pb-3">
      <div>
        <h2 className="text-base font-semibold">{labels.heading}</h2>
        <p className="text-xs text-[var(--orcia-text-secondary)]">{labels.subtitle}</p>
      </div>
      <div className="flex flex-wrap items-center gap-2">
        <div role="tablist" className="orcia-ds-tabs">
          <button type="button" role="tab" aria-selected={activeTab === "AGENTS"} data-testid="agents-subview-tab-agents" onClick={() => onSelectTab("AGENTS")} className="orcia-ds-tab">
            {`${labels.tabAgents} (${agentsCount})`}
          </button>
          <button type="button" role="tab" aria-selected={activeTab === "SKILLS"} data-testid="agents-subview-tab-skills" onClick={() => onSelectTab("SKILLS")} className="orcia-ds-tab">
            {`${labels.tabSkills} (${skillsCount})`}
          </button>
          <button type="button" role="tab" aria-selected={activeTab === "CONNECTIONS"} data-testid="agents-subview-tab-connections" onClick={() => onSelectTab("CONNECTIONS")} className="orcia-ds-tab">
            {labels.tabConnections}
          </button>
        </div>
        {activeTab === "AGENTS" ? (
          <button type="button" data-testid="open-create-agent-drawer-btn" onClick={onToggleCreateAgent} className="rounded bg-[var(--orcia-action-primary)] px-3 py-1.5 text-xs font-semibold text-[var(--orcia-text-on-action)]">
            + Nouvel Agent
          </button>
        ) : activeTab === "SKILLS" ? (
          <button type="button" data-testid="open-create-skill-drawer-btn" onClick={onToggleCreateSkill} className="rounded bg-[var(--orcia-action-primary)] px-3 py-1.5 text-xs font-semibold text-[var(--orcia-text-on-action)]">
            + Nouvelle Compétence
          </button>
        ) : (
          <button type="button" data-testid="open-mcp-test-bench-btn" onClick={() => { onSelectTab("CONNECTIONS"); onOpenMcpTestBench?.(); }} className="rounded bg-[var(--orcia-action-primary)] px-3 py-1.5 text-xs font-semibold text-[var(--orcia-text-on-action)]">
            <OrciaIcon name="plug" /> Tester &amp; Découvrir un serveur MCP
          </button>
        )}
      </div>
    </header>

    {agentsCount + skillsCount > 0 && (
      <div data-testid="agents-kpi-strip" className="grid grid-cols-1 gap-2 text-xs md:grid-cols-3">
        <div className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] px-3 py-2">
          <span className="block text-[10px] font-semibold uppercase tracking-wide text-[var(--orcia-text-secondary)]">AGENTS SPÉCIALISÉS (@)</span>
          <strong className="text-sm text-[var(--orcia-text-primary)]">{activeAgentsCount ?? agentsCount} actifs</strong>
        </div>
        <div className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] px-3 py-2">
          <span className="block text-[10px] font-semibold uppercase tracking-wide text-[var(--orcia-text-secondary)]">COMPÉTENCES (/SKILLS)</span>
          <strong className="text-sm text-[var(--orcia-text-primary)]">{skillsCount} réutilisables</strong>
        </div>
        <div className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] px-3 py-2">
          <span className="block text-[10px] font-semibold uppercase tracking-wide text-[var(--orcia-text-secondary)]">ORIGINE &amp; ACCÈS MCP</span>
          <strong className="text-sm text-[var(--orcia-text-primary)]">{packOrTeamAgentsCount} Pack/Équipe · {mcpExposedAgentsCount} MCP</strong>
        </div>
      </div>
    )}

    <div className="flex flex-wrap items-center justify-between gap-2 text-xs">
      <input type="text" autoComplete="off" data-lpignore="true" data-1p-ignore="true" data-bwignore="true" data-form-type="other" data-testid="agents-skills-search-input" value={searchQuery} onChange={(e) => onChangeSearchQuery(e.target.value)} placeholder="Filtrer par nom, @agent, /compétence ou mission…" className="min-w-[240px] flex-1 rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] px-3 py-1.5" />
      <div role="group" aria-label="Filtrer par visibilité" className="flex flex-wrap items-center gap-1.5">
        {(
          [
            ["ALL", "visibility-filter-all", "Tous", null],
            ["PACK", "visibility-filter-pack", "Packs Métiers", "spaces"],
            ["TEAM", "visibility-filter-team", "Équipe / Espace", "team"],
            ["PRIVATE", "visibility-filter-private", "Privés", "lock"],
          ] as const
        ).map(([filterKey, testId, filterLabel, iconName]) => (
          <button key={filterKey} type="button" data-testid={testId} aria-pressed={visibilityFilter === filterKey} onClick={() => onChangeVisibilityFilter(filterKey)} className={`rounded-full border border-[var(--orcia-border-subtle)] px-2.5 py-1 text-[11px] font-medium ${visibilityFilter === filterKey ? "bg-[var(--orcia-action-primary)] text-[var(--orcia-text-on-action)]" : "bg-[var(--orcia-surface-secondary)] text-[var(--orcia-text-primary)]"}`}>
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
          <button type="button" data-testid="load-pack-agents-templates-btn" style={{ display: "none" }} onClick={onLoadPackTemplates}>
            <OrciaIcon name="spaces" /> Charger les Agents &amp; Compétences des Packs Métiers
          </button>
        )}
      </div>
    </div>
  </>
);
