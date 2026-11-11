import React, { useState } from "react";
import {
  HUMAN_PARTNER_ROLE_LABELS_FR,
  OUTPUT_CONTRACT_FORMAT_LABELS_FR,
  type UiAgentHumanPartnerRole,
  type UiAgentOutputContractFormat,
  type UiAgentPosture,
} from "./AgentGovernanceTypesAndDefaults";
import type {
  AgentsAndSkillsManagerLabels,
  UiAgentSkillVisibilityScope,
  UiAgentThinkingLevel,
  UiManagedAgentItem,
  UiManagedSkillItem,
} from "./AgentsAndSkillsManagerView";
import { FormattedMarkdownContent } from "./FormattedMarkdownContent";
import { OrciaIcon } from "./icons";

export interface AgentStudioCardItemProps {
  readonly agent: UiManagedAgentItem;
  readonly skills: readonly UiManagedSkillItem[];
  readonly labels: AgentsAndSkillsManagerLabels;
  readonly testInputValue?: string;
  readonly onChangeTestInput?: (agentId: string, nextValue: string) => void;
  readonly onToggleAgentSkill?: (agentId: string, skillId: string, nextChecked: boolean) => void;
  readonly onExecuteAgent?: (agentId: string, prompt: string) => void;
  readonly onDeleteAgent: (agentId: string) => void;
  readonly onDuplicateAgent?: (agent: UiManagedAgentItem) => void;
  readonly onToggleAgentEnabled?: (agentId: string, nextEnabled: boolean) => void;
  readonly onOpenDetailModal?: (agent: UiManagedAgentItem) => void;
  readonly onUpdateAgentThinkingLevel?: (
    agentId: string,
    nextThinkingLevel: UiAgentThinkingLevel,
  ) => void;
  readonly onUpdateAgentVisibility?: (
    agentId: string,
    nextVisibility: UiAgentSkillVisibilityScope,
  ) => void;
  readonly onUseAgentInAssistant?: (agent: UiManagedAgentItem) => void;
}

export const AgentStudioCardItem: React.FC<AgentStudioCardItemProps> = ({
  agent,
  skills,
  labels,
  onDeleteAgent,
  onDuplicateAgent,
  onToggleAgentEnabled,
  onOpenDetailModal,
  onUpdateAgentThinkingLevel,
  onUpdateAgentVisibility,
  onUseAgentInAssistant,
}) => {
  const [copiedHandle, setCopiedHandle] = useState(false);
  const [autosavedBadgeVisible, setAutosavedBadgeVisible] = useState(false);

  const visibilityScope: UiAgentSkillVisibilityScope = agent.visibilityScope ?? "TEAM";
  const isPack = visibilityScope === "PACK";
  const isEnabled = agent.enabledOnWorkspace !== false;
  const posture: UiAgentPosture = agent.posture ?? "PRODUCER";
  const partnerRole: UiAgentHumanPartnerRole = agent.humanPartnerRole ?? "PO_PM";
  const outputFormat: UiAgentOutputContractFormat =
    agent.outputContractFormat ?? "markdown_structure";
  const writePreviewRequired = agent.writePreviewRequired !== false;
  const testBenchValidated = Boolean(
    agent.testBenchValidated || agent.lastExecutionOutput || isPack,
  );

  const visibilityBadgeContent =
    visibilityScope === "PRIVATE" ? (
      <>
        <OrciaIcon name="lock" /> Privé
      </>
    ) : visibilityScope === "PACK" ? (
      <>
        <OrciaIcon name="spaces" /> Pack Métier ({agent.sourcePackKey ?? "orcia-pack-sdlc"})
      </>
    ) : (
      <>
        <OrciaIcon name="team" /> Équipe
      </>
    );

  const attachedSkills = skills.filter((sk) => agent.skillIds.includes(sk.skillId));

  const triggerAutosavedFeedback = () => {
    setAutosavedBadgeVisible(true);
  };

  const handleCopyHandle = () => {
    if (typeof navigator !== "undefined" && navigator.clipboard?.writeText) {
      void navigator.clipboard.writeText(agent.handle).catch(() => undefined);
    }
    setCopiedHandle(true);
  };

  const handleToggleVisibilityClick = () => {
    if (isPack) return;
    const nextScope: UiAgentSkillVisibilityScope =
      visibilityScope === "PRIVATE" ? "TEAM" : "PRIVATE";
    onUpdateAgentVisibility?.(agent.agentId, nextScope);
    triggerAutosavedFeedback();
  };

  return (
    <div
      data-testid={`agent-card-${agent.agentId}`}
      className="space-y-2.5 rounded-lg border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] p-3.5 text-xs"
    >
      {/* Row 1: Identity, Posture, Partner & Governance Badges */}
      <div className="flex flex-wrap items-center justify-between gap-2">
        <div className="flex flex-wrap items-center gap-2">
          <strong className="text-sm text-[var(--orcia-text-primary)]">{agent.name}</strong>
          <code
            data-testid={`agent-handle-${agent.agentId}`}
            className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-1.5 py-0.5 font-mono text-[11px]"
          >
            {agent.handle}
          </code>
          <button
            type="button"
            data-testid={`copy-agent-handle-btn-${agent.agentId}`}
            onClick={handleCopyHandle}
            title="Copier l'identifiant @handle"
            className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-1.5 py-0.5 text-[10px] font-medium"
          >
            {copiedHandle ? (
              <>
                <OrciaIcon name="check" /> Copié
              </>
            ) : (
              "Copier @"
            )}
          </button>

          <span
            data-testid={`agent-posture-badge-${agent.agentId}`}
            className="rounded-full border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2.5 py-0.5 text-[11px] font-semibold"
          >
            {posture === "EVALUATOR_GATE" ? "🛡️ Contradicteur / Gate" : "🛠️ Producteur métier"}
          </span>

          <span
            data-testid={`agent-partner-badge-${agent.agentId}`}
            className="rounded-full border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2 py-0.5 text-[11px]"
          >
            👤 Binôme : {HUMAN_PARTNER_ROLE_LABELS_FR[partnerRole].split(" (")[0]}
          </span>

          {isPack ? (
            <span
              data-testid={`agent-visibility-badge-${agent.agentId}`}
              className="rounded-full border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2.5 py-0.5 text-[11px] font-medium"
            >
              {visibilityBadgeContent}
            </span>
          ) : (
            <button
              type="button"
              data-testid={`agent-visibility-badge-${agent.agentId}`}
              onClick={handleToggleVisibilityClick}
              title="Cliquer pour basculer la visibilité (Privé / Équipe)"
              className="rounded-full border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2.5 py-0.5 text-[11px] font-medium"
            >
              {visibilityBadgeContent}
            </button>
          )}

          <span
            data-testid={`agent-test-bench-badge-${agent.agentId}`}
            className="rounded-full border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2 py-0.5 text-[11px] font-medium"
          >
            {testBenchValidated ? "🧪 Validé au Banc de Test" : "📝 À tester"}
          </span>

          {!isEnabled && (
            <span
              data-testid={`agent-disabled-badge-${agent.agentId}`}
              className="rounded-full border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2 py-0.5 text-[11px] font-medium text-[var(--orcia-text-secondary)]"
            >
              ⏸️ Désactivé sur cet espace
            </span>
          )}

          {agent.mcpExposed && (
            <span
              data-testid={`agent-mcp-active-badge-${agent.agentId}`}
              className="rounded-full border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2 py-0.5 text-[11px] font-semibold"
            >
              <OrciaIcon name="plug" /> MCP Actif
            </span>
          )}

          {autosavedBadgeVisible && (
            <span
              data-testid={`agent-autosaved-badge-${agent.agentId}`}
              className="rounded-full border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2 py-0.5 text-[11px] font-semibold"
              style={{ color: "var(--color-status-success)" }}
            >
              <OrciaIcon name="check" /> Enregistré
            </span>
          )}
        </div>

        <label className="inline-flex items-center gap-1.5">
          <span className="font-medium text-[var(--orcia-text-secondary)]">
            {labels.agentThinkingLevelLabel} :
          </span>
          <select
            data-testid={`agent-card-thinking-select-${agent.agentId}`}
            value={agent.thinkingLevel}
            onChange={(e) => {
              const nextLvl = e.target.value as UiAgentThinkingLevel;
              onUpdateAgentThinkingLevel?.(agent.agentId, nextLvl);
              triggerAutosavedFeedback();
            }}
            className="orcia-ds-select text-[11px]"
          >
            {(["simple", "medium", "complex", "auto"] as const).map((lvl) => (
              <option key={lvl} value={lvl}>
                {labels.thinkingLevels[lvl]}
              </option>
            ))}
          </select>
        </label>
      </div>

      {/* Row 2: Mission, 6-Block Governance Passport & Attached Skills Pills */}
      <div className="space-y-1.5">
        <p className="text-[var(--orcia-text-secondary)]">{agent.roleMission}</p>

        {/* Compact 6-Block Governance Passport */}
        <div
          data-testid={`agent-governance-passport-${agent.agentId}`}
          className="flex flex-wrap items-center gap-1.5 text-[11px] text-[var(--orcia-text-secondary)]"
        >
          <span className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2 py-0.5">
            🧠 Modèle : {agent.llmModelTier ?? "team_default"} · Temp {agent.temperature ?? 0.2} ·{" "}
            {agent.maxTokens ?? 4096} tok
          </span>
          <span className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2 py-0.5">
            📚 RAG ({(agent.allowedRagSources ?? ["all_workspace_sources"]).length}) &amp; Ontologie (
            {(agent.ontologyViews ?? ["glossary"]).length})
          </span>
          <span className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2 py-0.5">
            📄 Sortie : {OUTPUT_CONTRACT_FORMAT_LABELS_FR[outputFormat].split(" (")[0]}
          </span>
          {writePreviewRequired && (
            <span className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2 py-0.5">
              🛡️ Write-Preview obligatoire
            </span>
          )}
        </div>

        <div className="flex flex-wrap items-center gap-1.5">
          <span className="font-medium text-[var(--orcia-text-secondary)]">
            {labels.attachedSkillsLabel} :
          </span>
          {attachedSkills.length === 0 ? (
            <span className="text-[11px] text-[var(--orcia-text-secondary)]">
              Aucune compétence rattachée
            </span>
          ) : (
            attachedSkills.map((sk) => (
              <span
                key={sk.skillId}
                className="inline-flex items-center gap-1 rounded-full border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2.5 py-0.5 text-[11px]"
              >
                <OrciaIcon name="tools" /> {sk.name} (
                <code className="font-mono text-[10px]">{sk.commandHandle}</code>)
              </span>
            ))
          )}
          <button
            type="button"
            onClick={() => onOpenDetailModal?.(agent)}
            className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2 py-0.5 text-[11px] font-medium"
          >
            + Rattacher / Gérer (6 blocs)
          </button>
        </div>
      </div>

      {/* Row 3: Clear Actions by Origin */}
      <div className="flex flex-wrap items-center justify-between gap-2 pt-1">
        <div className="flex flex-wrap items-center gap-2">
          {onUseAgentInAssistant && (
            <button
              type="button"
              data-testid={`use-agent-in-assistant-btn-${agent.agentId}`}
              onClick={() => onUseAgentInAssistant(agent)}
              className="orcia-ds-btn orcia-ds-btn-primary text-[11px]"
            >
              <OrciaIcon name="assistant" /> Utiliser dans Mon Assistant
            </button>
          )}
          <button
            type="button"
            data-testid={`open-agent-detail-modal-btn-${agent.agentId}`}
            onClick={() => onOpenDetailModal?.(agent)}
            className="orcia-ds-btn orcia-ds-btn-secondary text-[11px]"
          >
            <OrciaIcon name="configuration" /> Configurer &amp; Tester (6 blocs)
          </button>
        </div>

        <div className="flex flex-wrap items-center gap-2">
          {isPack ? (
            <>
              <button
                type="button"
                data-testid={`duplicate-agent-btn-${agent.agentId}`}
                onClick={() => onDuplicateAgent?.(agent)}
                className="orcia-ds-btn orcia-ds-btn-secondary text-[11px]"
              >
                <OrciaIcon name="copy" /> Dupliquer &amp; Personnaliser
              </button>
              <button
                type="button"
                data-testid={`toggle-agent-enabled-btn-${agent.agentId}`}
                onClick={() => onToggleAgentEnabled?.(agent.agentId, !isEnabled)}
                className="orcia-ds-btn orcia-ds-btn-secondary text-[11px]"
              >
                {isEnabled ? "⏸️ Désactiver sur l'espace" : "▶️ Activer sur l'espace"}
              </button>
            </>
          ) : (
            <>
              <button
                type="button"
                data-testid={`duplicate-agent-btn-${agent.agentId}`}
                onClick={() => onDuplicateAgent?.(agent)}
                className="orcia-ds-btn orcia-ds-btn-secondary text-[11px]"
              >
                <OrciaIcon name="copy" /> Dupliquer
              </button>
              <button
                type="button"
                data-testid={`delete-agent-btn-${agent.agentId}`}
                onClick={() => onDeleteAgent(agent.agentId)}
                className="orcia-ds-btn orcia-ds-btn-secondary text-[11px]"
              >
                {labels.deleteAgentButtonLabel}
              </button>
            </>
          )}
        </div>
      </div>

      {agent.lastExecutionOutput && (
        <div
          data-testid={`agent-execution-output-${agent.agentId}`}
          className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] p-2.5"
        >
          <FormattedMarkdownContent content={agent.lastExecutionOutput} />
        </div>
      )}
    </div>
  );
};
