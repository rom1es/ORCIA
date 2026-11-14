import React, { useEffect, useState } from "react";
import type {
  AgentSixBlocksDraftState,
  AgentStudioBlockKey,
} from "./AgentGovernanceTypesAndDefaults";
import { computeAgentReadinessChecklist } from "./AgentGovernanceTypesAndDefaults";
import { AgentSixBlocksEditorBody } from "./AgentSixBlocksFormSections";
import type {
  AgentsAndSkillsManagerLabels,
  AgentsAndSkillsSubTab,
  UiAgentSkillVisibilityFilter,
  UiAgentThinkingLevel,
  UiManagedSkillItem,
} from "./AgentsAndSkillsManagerView";
import { DisabledButtonAlertIndicator } from "./DisabledButtonAlertIndicator";
import { OrciaIcon } from "./icons";

export interface AgentCreateFormDrawerProps {
  readonly isOpen: boolean;
  readonly labels: AgentsAndSkillsManagerLabels;
  readonly skills: readonly UiManagedSkillItem[];
  readonly draft: AgentSixBlocksDraftState;
  readonly onChangeDraft: (patch: Partial<AgentSixBlocksDraftState>) => void;
  readonly onToggleSkillId: (skillId: string, checked: boolean) => void;
  readonly onSubmit: (e: React.FormEvent) => void;
  readonly onClose?: () => void;
  // Backward-compatible individual props for callers that pass flat fields
  readonly agentName?: string;
  readonly agentRole?: string;
  readonly agentInstructions?: string;
  readonly agentThinking?: UiAgentThinkingLevel;
  readonly agentVisibility?: "PRIVATE" | "TEAM";
  readonly selectedSkillIds?: readonly string[];
  readonly onChangeName?: (v: string) => void;
  readonly onChangeRole?: (v: string) => void;
  readonly onChangeInstructions?: (v: string) => void;
  readonly onChangeThinking?: (v: UiAgentThinkingLevel) => void;
  readonly onChangeVisibility?: (v: "PRIVATE" | "TEAM") => void;
}

export const AgentCreateFormDrawer: React.FC<AgentCreateFormDrawerProps> = ({
  isOpen,
  labels,
  skills,
  draft,
  onChangeDraft,
  onToggleSkillId,
  onSubmit,
  onClose,
}) => {
  const [activeBlock, setActiveBlock] = useState<AgentStudioBlockKey>("A");
  const [showAllBlocks, setShowAllBlocks] = useState<boolean>(true);

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

  const isDisabled =
    !draft.name.trim() ||
    !draft.roleMission.trim() ||
    (!draft.instructions.trim() && !draft.promptRef.trim());
  const disabledReason =
    "Renseignez le nom (Bloc A), la mission (Bloc A) et l'instruction système ou prompt_ref (Bloc C) pour créer l'agent.";
  const readiness = computeAgentReadinessChecklist(draft);

  return (
    <div
      role="dialog"
      aria-modal="true"
      aria-label={labels.createAgentSectionTitle}
      data-testid="create-agent-modal"
      className="fixed inset-0 z-40 flex items-center justify-center p-4"
      style={{ backgroundColor: "var(--color-modal-backdrop)" }}
    >
      <div
        className="w-[960px] max-h-[680px] flex flex-col rounded-xl border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] text-[var(--orcia-text-primary)] shadow-xl overflow-hidden"
        style={{
          backgroundColor: "var(--color-surface-card)",
          borderColor: "var(--color-border)",
          color: "var(--color-foreground)",
        }}
      >
        <header className="flex items-center justify-between border-b border-[var(--orcia-border-subtle)] px-4 py-3">
          <div>
            <h3 className="text-sm font-semibold">{labels.createAgentSectionTitle}</h3>
            <p className="text-[11px] text-[var(--orcia-text-secondary)]">
              Configurez un rôle métier spécialisé (Persona) en 6 blocs gouvernés, cloisonné et subordonné à l&apos;humain.
            </p>
          </div>
          <button
            type="button"
            data-testid="close-create-agent-modal-btn"
            onClick={onClose}
            className="orcia-ds-btn orcia-ds-btn-secondary text-xs"
          >
            Annuler
          </button>
        </header>

        <form
          onSubmit={onSubmit}
          autoComplete="off"
          data-lpignore="true"
          data-form-type="other"
          data-testid="create-agent-form"
          className="flex flex-1 flex-col overflow-hidden"
        >
          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            <AgentSixBlocksEditorBody
              draft={draft}
              labels={labels}
              skills={skills}
              activeBlock={activeBlock}
              showAllBlocks={showAllBlocks}
              testIdPrefix="create"
              onSelectBlock={(blk) => {
                setActiveBlock(blk);
                setShowAllBlocks(false);
              }}
              onToggleShowAllBlocks={() => setShowAllBlocks((p) => !p)}
              onChangeDraft={onChangeDraft}
              onToggleSkillId={onToggleSkillId}
            />

            {/* 6 Conversational Readiness Conditions Summary Strip */}
            <div
              data-testid="create-agent-readiness-checklist"
              className="rounded-lg border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] p-3 text-xs"
            >
              <strong className="block mb-1.5 font-semibold">
                📋 Les 6 conditions d&apos;employabilité dans « 💬 Mon Assistant » :
              </strong>
              <div className="grid grid-cols-1 gap-1.5 md:grid-cols-3">
                {readiness.map((item) => (
                  <div
                    key={item.code}
                    data-testid={`readiness-condition-${item.index}`}
                    className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2.5 py-1.5"
                  >
                    <div className="font-semibold">
                      {item.satisfied ? "✅" : "⏳"} {item.index}. {item.labelFr}
                    </div>
                    <div className="text-[11px] text-[var(--orcia-text-secondary)]">
                      {item.detailFr}
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>

          <footer className="flex items-center justify-between border-t border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] px-4 py-3">
            <span className="text-[11px] text-[var(--orcia-text-secondary)]">
              Raccourci : <code>Échap</code> pour annuler · Validation au Banc de Test disponible après enregistrement.
            </span>
            <div className="flex items-center gap-2">
              <button
                type="button"
                onClick={onClose}
                className="orcia-ds-btn orcia-ds-btn-secondary text-xs"
              >
                Annuler
              </button>
              <button
                type="submit"
                data-testid="create-agent-submit-btn"
                disabled={isDisabled}
                title={isDisabled ? disabledReason : undefined}
                className="orcia-ds-btn orcia-ds-btn-primary text-xs"
              >
                <span>{labels.createAgentButtonLabel}</span>
                <DisabledButtonAlertIndicator
                  disabled={isDisabled}
                  reason={disabledReason}
                  testIdSuffix="create-agent-submit-btn"
                />
              </button>
            </div>
          </footer>
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
            <OrciaIcon name="spaces" /> Charger les Agents des Packs
          </button>
        )}
        {activeTab === "AGENTS" ? (
          <button
            type="button"
            data-testid="open-create-agent-drawer-btn"
            onClick={onToggleCreateAgent}
            className="orcia-ds-btn orcia-ds-btn-primary text-xs"
          >
            + Nouvel Agent
          </button>
        ) : activeTab === "SKILLS" ? (
          <button
            type="button"
            data-testid="open-create-skill-drawer-btn"
            onClick={onToggleCreateSkill}
            className="orcia-ds-btn orcia-ds-btn-primary text-xs"
          >
            + Nouvelle Compétence
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
            <OrciaIcon name="plug" /> Tester &amp; Découvrir un serveur MCP
          </button>
        )}
      </div>
    </header>

    {agentsCount + skillsCount > 0 && (
      <div data-testid="agents-kpi-strip" className="grid grid-cols-1 gap-2 text-xs md:grid-cols-3">
        <div className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] px-3 py-2">
          <span className="block text-[10px] font-semibold uppercase tracking-wide text-[var(--orcia-text-secondary)]">
            AGENTS SPÉCIALISÉS (@)
          </span>
          <strong className="text-sm text-[var(--orcia-text-primary)]">
            {activeAgentsCount ?? agentsCount} actifs
          </strong>
        </div>
        <div className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] px-3 py-2">
          <span className="block text-[10px] font-semibold uppercase tracking-wide text-[var(--orcia-text-secondary)]">
            COMPÉTENCES (/SKILLS)
          </span>
          <strong className="text-sm text-[var(--orcia-text-primary)]">
            {skillsCount} réutilisables
          </strong>
        </div>
        <div className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] px-3 py-2">
          <span className="block text-[10px] font-semibold uppercase tracking-wide text-[var(--orcia-text-secondary)]">
            ORIGINE &amp; ACCÈS MCP
          </span>
          <strong className="text-sm text-[var(--orcia-text-primary)]">
            {packOrTeamAgentsCount} Pack/Équipe · {mcpExposedAgentsCount} MCP
          </strong>
        </div>
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
        placeholder="Filtrer par nom, @agent, /compétence, posture ou mission…"
        className="orcia-ds-input min-w-[240px] flex-1"
      />
      <div role="group" aria-label="Filtrer par visibilité" className="flex flex-wrap items-center gap-1.5">
        {(
          [
            ["ALL", "visibility-filter-all", "Tous", null],
            ["PACK", "visibility-filter-pack", "Packs Métiers", "spaces"],
            ["TEAM", "visibility-filter-team", "Équipe / Espace", "team"],
            ["PRIVATE", "visibility-filter-private", "Privés", "lock"],
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
      </div>
    </div>
  </>
);
