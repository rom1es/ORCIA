import React from "react";
import type {
  AgentSixBlocksDraftState,
  AgentStudioBlockKey,
  UiAgentDialogueMechanism,
  UiAgentHumanPartnerRole,
  UiAgentLlmModelTier,
  UiAgentPosture,
} from "./AgentGovernanceTypesAndDefaults";
import {
  AGENT_STUDIO_BLOCKS,
  computeAgentReadinessChecklist,
  DIALOGUE_MECHANISM_LABELS_FR,
  HUMAN_PARTNER_ROLE_LABELS_FR,
  LLM_MODEL_TIER_LABELS_FR,
} from "./AgentGovernanceTypesAndDefaults";
import { AgentSixBlocksKnowledgeToolsGuardrailsSections } from "./AgentSixBlocksKnowledgeToolsGuardrailsSections";
import type {
  AgentsAndSkillsManagerLabels,
  UiAgentThinkingLevel,
  UiManagedSkillItem,
} from "./AgentsAndSkillsManagerView";
import { getOrciaIconGlyph } from "./icons";

export interface AgentSixBlocksEditorBodyProps {
  readonly draft: AgentSixBlocksDraftState;
  readonly labels: AgentsAndSkillsManagerLabels;
  readonly skills: readonly UiManagedSkillItem[];
  readonly activeBlock: AgentStudioBlockKey;
  readonly showAllBlocks?: boolean;
  readonly readOnlyIdentity?: boolean;
  readonly testIdPrefix?: string;
  readonly onSelectBlock: (block: AgentStudioBlockKey) => void;
  readonly onToggleShowAllBlocks?: () => void;
  readonly onChangeDraft: (patch: Partial<AgentSixBlocksDraftState>) => void;
  readonly onToggleSkillId: (skillId: string, checked: boolean) => void;
}

export const AgentSixBlocksEditorBody: React.FC<AgentSixBlocksEditorBodyProps> = ({
  draft,
  labels,
  skills,
  activeBlock,
  showAllBlocks = true,
  readOnlyIdentity = false,
  testIdPrefix = "create",
  onSelectBlock,
  onToggleShowAllBlocks,
  onChangeDraft,
  onToggleSkillId,
}) => {
  const checklist = computeAgentReadinessChecklist(draft);
  const satisfiedCount = checklist.filter((c) => c.satisfied).length;
  const isVisible = (b: AgentStudioBlockKey) => showAllBlocks || activeBlock === b;

  const toggleArrayItem = (list: readonly string[], item: string, checked: boolean): string[] =>
    checked ? Array.from(new Set([...list, item])) : list.filter((x) => x !== item);

  const computedHandle = `@${draft.name
    .trim()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "") || "nouvel-agent"}`;

  return (
    <div className="space-y-3 text-xs">
      {/* Navigation Bar across the 6 ORCIA Governance Blocks + Readiness Pill */}
      <div
        data-testid={`${testIdPrefix}-agent-blocks-nav`}
        className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] p-2"
      >
        <div className="flex flex-wrap items-center gap-1.5">
          {AGENT_STUDIO_BLOCKS.map((blk) => {
            const selected = !showAllBlocks && activeBlock === blk.key;
            return (
              <button
                key={blk.key}
                type="button"
                data-testid={`${testIdPrefix}-agent-block-tab-${blk.key}`}
                onClick={() => onSelectBlock(blk.key)}
                className={`rounded px-2 py-1 text-[11px] font-semibold ${
                  selected
                    ? "bg-[var(--orcia-action-primary)] text-[var(--orcia-text-on-action)]"
                    : "border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] text-[var(--orcia-text-primary)]"
                }`}
              >
                {blk.badge} · {blk.titleFr.split(" (")[0]}
              </button>
            );
          })}
        </div>
        <div className="flex items-center gap-2">
          {onToggleShowAllBlocks && (
            <button
              type="button"
              data-testid={`${testIdPrefix}-agent-toggle-all-blocks-btn`}
              onClick={onToggleShowAllBlocks}
              className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2 py-1 text-[11px] font-medium"
            >
              {showAllBlocks ? "Vue bloc par bloc" : "Afficher les 6 blocs"}
            </button>
          )}
          <span
            data-testid={`${testIdPrefix}-agent-readiness-pill`}
            className="rounded-full border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2.5 py-0.5 text-[11px] font-semibold"
          >
            ✅ Prêt Assistant : {satisfiedCount}/6
          </span>
        </div>
      </div>

      {/* BLOC A — Identité & Rôle métier (Persona) */}
      {isVisible("A") && (
        <div
          data-testid={`${testIdPrefix}-agent-block-A`}
          className="space-y-2.5 rounded-lg border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] p-3"
        >
          <div className="flex flex-wrap items-center justify-between gap-2">
            <strong className="text-xs font-semibold">
              🅰️ Bloc A — Identité, Posture &amp; Binôme Humain (Persona)
            </strong>
            <code
              data-testid={`${testIdPrefix}-agent-handle-preview`}
              className="rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2 py-0.5 font-mono text-[11px]"
            >
              {computedHandle}
            </code>
          </div>
          <div className="grid grid-cols-1 gap-2.5 md:grid-cols-2">
            <label className="flex flex-col gap-1">
              <span className="font-medium">{labels.agentNameLabel}</span>
              <input
                type="text"
                autoComplete="off"
                data-lpignore="true"
                data-1p-ignore="true"
                data-bwignore="true"
                data-form-type="other"
                data-testid={testIdPrefix === "create" ? "agent-name-input" : `edit-agent-name-input`}
                disabled={readOnlyIdentity}
                value={draft.name}
                onChange={(e) => onChangeDraft({ name: e.target.value })}
                placeholder={labels.agentNamePlaceholder}
                className="orcia-ds-input"
              />
            </label>
            <label className="flex flex-col gap-1">
              <span className="font-medium">Visibilité &amp; Partage</span>
              <select
                data-testid={testIdPrefix === "create" ? "agent-visibility-select" : "edit-agent-visibility-select"}
                disabled={readOnlyIdentity}
                value={draft.visibilityScope === "PRIVATE" ? "PRIVATE" : "TEAM"}
                onChange={(e) =>
                  onChangeDraft({ visibilityScope: e.target.value as "PRIVATE" | "TEAM" })
                }
                className="orcia-ds-select"
              >
                <option value="TEAM">
                  {getOrciaIconGlyph("team")} Partagé avec mon Équipe &amp; Espace
                </option>
                <option value="PRIVATE">
                  {getOrciaIconGlyph("lock")} Privé (Visible uniquement par moi)
                </option>
              </select>
            </label>
            <label className="flex flex-col gap-1">
              <span className="font-medium">Posture de l&apos;Agent ORCIA</span>
              <select
                data-testid={`${testIdPrefix}-agent-posture-select`}
                value={draft.posture}
                onChange={(e) => {
                  const nextPosture = e.target.value as UiAgentPosture;
                  onChangeDraft({
                    posture: nextPosture,
                    temperature: nextPosture === "EVALUATOR_GATE" ? 0.0 : draft.temperature,
                    outputContractFormat:
                      nextPosture === "EVALUATOR_GATE"
                        ? "gate_risk_json"
                        : draft.outputContractFormat,
                  });
                }}
                className="orcia-ds-select"
              >
                <option value="PRODUCER">
                  🛠️ Producteur / Assistant (Co-construction PRD, Architecture, US)
                </option>
                <option value="EVALUATOR_GATE">
                  🛡️ Évaluateur / Contradicteur de Gate (Blind / Edge / Compliance Hunter)
                </option>
              </select>
            </label>
            <label className="flex flex-col gap-1">
              <span className="font-medium">Rôle humain binôme (Arbitre)</span>
              <select
                data-testid={`${testIdPrefix}-agent-human-partner-select`}
                value={draft.humanPartnerRole}
                onChange={(e) =>
                  onChangeDraft({
                    humanPartnerRole: e.target.value as UiAgentHumanPartnerRole,
                  })
                }
                className="orcia-ds-select"
              >
                {(Object.keys(HUMAN_PARTNER_ROLE_LABELS_FR) as UiAgentHumanPartnerRole[]).map(
                  (roleKey) => (
                    <option key={roleKey} value={roleKey}>
                      👤 {HUMAN_PARTNER_ROLE_LABELS_FR[roleKey]}
                    </option>
                  ),
                )}
              </select>
            </label>
            <label className="flex flex-col gap-1 md:col-span-2">
              <span className="font-medium">{labels.agentRoleLabel}</span>
              <input
                type="text"
                autoComplete="off"
                data-lpignore="true"
                data-1p-ignore="true"
                data-bwignore="true"
                data-form-type="other"
                data-testid={testIdPrefix === "create" ? "agent-role-input" : "edit-agent-role-input"}
                disabled={readOnlyIdentity}
                value={draft.roleMission}
                onChange={(e) => onChangeDraft({ roleMission: e.target.value })}
                placeholder={labels.agentRolePlaceholder}
                className="orcia-ds-input"
              />
            </label>
          </div>
        </div>
      )}

      {/* BLOC B — Moteur Cognitif (Modèle LLM, Effort & Budget) */}
      {isVisible("B") && (
        <div
          data-testid={`${testIdPrefix}-agent-block-B`}
          className="space-y-2.5 rounded-lg border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] p-3"
        >
          <strong className="block text-xs font-semibold">
            🅱️ Bloc B — Moteur Cognitif (Modèle LLM, Effort &amp; Budget FinOps)
          </strong>
          <div className="grid grid-cols-1 gap-2.5 md:grid-cols-2">
            <label className="flex flex-col gap-1">
              <span className="font-medium">Sélection du modèle LLM</span>
              <select
                data-testid={`${testIdPrefix}-agent-llm-model-tier-select`}
                value={draft.llmModelTier}
                onChange={(e) =>
                  onChangeDraft({ llmModelTier: e.target.value as UiAgentLlmModelTier })
                }
                className="orcia-ds-select"
              >
                {(Object.keys(LLM_MODEL_TIER_LABELS_FR) as UiAgentLlmModelTier[]).map((tier) => (
                  <option key={tier} value={tier}>
                    {LLM_MODEL_TIER_LABELS_FR[tier]}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex flex-col gap-1">
              <span className="font-medium">{labels.agentThinkingLevelLabel}</span>
              <select
                data-testid={
                  testIdPrefix === "create"
                    ? "agent-thinking-level-select"
                    : "modal-agent-thinking-select"
                }
                value={draft.thinkingLevel}
                onChange={(e) =>
                  onChangeDraft({ thinkingLevel: e.target.value as UiAgentThinkingLevel })
                }
                className="orcia-ds-select"
              >
                {(["simple", "medium", "complex", "auto"] as const).map((lvl) => (
                  <option key={lvl} value={lvl}>
                    {labels.thinkingLevels[lvl]}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex flex-col gap-1">
              <span className="font-medium">Température d&apos;inférence (0 = Audit strict)</span>
              <select
                data-testid={`${testIdPrefix}-agent-temperature-select`}
                value={String(draft.temperature)}
                onChange={(e) => onChangeDraft({ temperature: Number(e.target.value) })}
                className="orcia-ds-select"
              >
                <option value="0">0.0 — Déterministe strict (Audit / Gate)</option>
                <option value="0.2">0.2 — Précis &amp; factuel (Rédaction normée)</option>
                <option value="0.4">0.4 — Équilibré (Co-construction métier)</option>
                <option value="0.7">0.7 — Exploration &amp; Idéation (Discovery)</option>
              </select>
            </label>
            <label className="flex flex-col gap-1">
              <span className="font-medium">Plafond de consommation de tokens</span>
              <select
                data-testid={`${testIdPrefix}-agent-max-tokens-select`}
                value={String(draft.maxTokens)}
                onChange={(e) => onChangeDraft({ maxTokens: Number(e.target.value) })}
                className="orcia-ds-select"
              >
                <option value="2048">2 048 tokens (Synthèse courte)</option>
                <option value="4096">4 096 tokens (Standard Espace)</option>
                <option value="8192">8 192 tokens (Étude d&apos;architecture / PRD)</option>
                <option value="16384">16 384 tokens (Audit approfondi multi-sources)</option>
              </select>
            </label>
          </div>
        </div>
      )}

      {/* BLOC C — Instructions Système & Modes d'interaction */}
      {isVisible("C") && (
        <div
          data-testid={`${testIdPrefix}-agent-block-C`}
          className="space-y-2.5 rounded-lg border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] p-3"
        >
          <strong className="block text-xs font-semibold">
            🅲 Bloc C — Instructions Système &amp; Modes d&apos;Interaction
          </strong>
          <div className="grid grid-cols-1 gap-2.5 md:grid-cols-2">
            <label className="flex flex-col gap-1 md:col-span-2">
              <span className="font-medium">{labels.agentInstructionsLabel} (System Prompt)</span>
              <textarea
                rows={3}
                autoComplete="off"
                data-lpignore="true"
                data-1p-ignore="true"
                data-bwignore="true"
                data-form-type="other"
                data-testid={
                  testIdPrefix === "create"
                    ? "agent-instructions-input"
                    : "edit-agent-instructions-input"
                }
                disabled={readOnlyIdentity}
                value={draft.instructions}
                onChange={(e) => onChangeDraft({ instructions: e.target.value })}
                placeholder={labels.agentInstructionsPlaceholder}
                className="orcia-ds-textarea"
              />
            </label>
            <label className="flex flex-col gap-1">
              <span className="font-medium">Référence Markdown versionnée (prompt_ref optionnel)</span>
              <input
                type="text"
                autoComplete="off"
                data-lpignore="true"
                data-1p-ignore="true"
                data-bwignore="true"
                data-form-type="other"
                data-testid={`${testIdPrefix}-agent-prompt-ref-input`}
                value={draft.promptRef}
                onChange={(e) => onChangeDraft({ promptRef: e.target.value })}
                placeholder="Ex: git://sdlc-pack/prompts/architecte-da.md@main"
                className="orcia-ds-input font-mono text-[11px]"
              />
            </label>
            <label className="flex flex-col gap-1">
              <span className="font-medium">Mécanisme de dialogue</span>
              <select
                data-testid={`${testIdPrefix}-agent-dialogue-mechanism-select`}
                value={draft.dialogueMechanism}
                onChange={(e) =>
                  onChangeDraft({
                    dialogueMechanism: e.target.value as UiAgentDialogueMechanism,
                  })
                }
                className="orcia-ds-select"
              >
                {(Object.keys(DIALOGUE_MECHANISM_LABELS_FR) as UiAgentDialogueMechanism[]).map(
                  (mech) => (
                    <option key={mech} value={mech}>
                      {DIALOGUE_MECHANISM_LABELS_FR[mech]}
                    </option>
                  ),
                )}
              </select>
            </label>
            <div className="space-y-1 md:col-span-2">
              <span className="font-medium">Modes d&apos;invocation supportés</span>
              <div className="flex flex-wrap gap-2">
                {(
                  [
                    ["generer", "✨ Générer (création initiale)"],
                    ["corrections", "🔧 Corrections (reprise sur remarques)"],
                    ["section", "🎯 Section (régénération ciblée)"],
                  ] as const
                ).map(([modeKey, modeLabel]) => {
                  const checked = draft.invocationModes.includes(modeKey);
                  return (
                    <label
                      key={modeKey}
                      className="inline-flex items-center gap-1.5 rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2.5 py-1"
                    >
                      <input
                        type="checkbox"
                        autoComplete="off"
                        data-lpignore="true"
                        data-1p-ignore="true"
                        data-bwignore="true"
                        data-form-type="other"
                        data-testid={`${testIdPrefix}-agent-mode-${modeKey}`}
                        checked={checked}
                        onChange={(e) =>
                          onChangeDraft({
                            invocationModes: toggleArrayItem(
                              draft.invocationModes,
                              modeKey,
                              e.target.checked,
                            ),
                          })
                        }
                      />
                      <span>{modeLabel}</span>
                    </label>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      )}

      <AgentSixBlocksKnowledgeToolsGuardrailsSections
        draft={draft}
        labels={labels}
        skills={skills}
        activeBlock={activeBlock}
        showAllBlocks={showAllBlocks}
        testIdPrefix={testIdPrefix}
        onChangeDraft={onChangeDraft}
        onToggleSkillId={onToggleSkillId}
      />
    </div>
  );
};
