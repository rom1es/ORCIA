import React from "react";
import type {
  AgentSixBlocksDraftState,
  AgentStudioBlockKey,
  UiAgentHumanPartnerRole,
  UiAgentPosture,
} from "./AgentGovernanceTypesAndDefaults";
import { computeAgentReadinessChecklist } from "./AgentGovernanceTypesAndDefaults";
import { AgentSixBlocksBlockB } from "./AgentSixBlocksBlockB";
import { AgentSixBlocksBlockC } from "./AgentSixBlocksBlockC";
import { AgentSixBlocksKnowledgeToolsGuardrailsSections } from "./AgentSixBlocksKnowledgeToolsGuardrailsSections";
import type {
  AgentsAndSkillsManagerLabels,
  UiManagedSkillItem,
} from "./AgentsAndSkillsTypes";

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

const BLOCK_KEYS: readonly AgentStudioBlockKey[] = ["A", "B", "C", "D", "E", "F"];
const HUMAN_PARTNER_KEYS: readonly UiAgentHumanPartnerRole[] = [
  "PO_PM",
  "ARCHITECT",
  "TECH_LEAD",
  "SECURITY_QA",
  "ALL",
];

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
  const studio = labels.studio;
  const checklist = computeAgentReadinessChecklist(draft, studio);
  const satisfiedCount = checklist.filter((c) => c.satisfied).length;
  const isVisible = (b: AgentStudioBlockKey) => showAllBlocks || activeBlock === b;

  const computedHandle = `@${draft.name
    .trim()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "") || studio.defaultHandleSlug}`;

  return (
    <div className="space-y-3 text-xs">
      <div
        data-testid={`${testIdPrefix}-agent-blocks-nav`}
        className="flex flex-wrap items-center justify-between gap-2 rounded-lg border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] p-2"
      >
        <div className="flex flex-wrap items-center gap-1.5">
          {BLOCK_KEYS.map((blkKey) => {
            const blk = studio.blockTitles[blkKey];
            const selected = !showAllBlocks && activeBlock === blkKey;
            return (
              <button
                key={blkKey}
                type="button"
                data-testid={`${testIdPrefix}-agent-block-tab-${blkKey}`}
                onClick={() => onSelectBlock(blkKey)}
                className={`rounded px-2 py-1 text-[11px] font-semibold ${
                  selected
                    ? "bg-[var(--orcia-action-primary)] text-[var(--orcia-text-on-action)]"
                    : "border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] text-[var(--orcia-text-primary)]"
                }`}
              >
                {blk.badge} · {blk.title}
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
              {showAllBlocks
                ? studio.showBlockByBlockLabel
                : studio.showAllSixBlocksLabel}
            </button>
          )}
          <span
            data-testid={`${testIdPrefix}-agent-readiness-pill`}
            className="rounded-full border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2.5 py-0.5 text-[11px] font-semibold"
          >
            {studio.assistantReadyPrefix} {satisfiedCount}/6
          </span>
        </div>
      </div>

      {isVisible("A") && (
        <div
          data-testid={`${testIdPrefix}-agent-block-A`}
          className="space-y-2.5 rounded-lg border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] p-3"
        >
          <div className="flex flex-wrap items-center justify-between gap-2">
            <strong className="text-xs font-semibold">
              {studio.blockTitles.A.heading}
            </strong>
            <code
              data-testid={`${testIdPrefix}-agent-handle-preview`}
              title={computedHandle}
              className="whitespace-nowrap rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2 py-0.5 font-mono text-[11px]"
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
                data-testid={
                  testIdPrefix === "create"
                    ? "agent-name-input"
                    : "edit-agent-name-input"
                }
                disabled={readOnlyIdentity}
                value={draft.name}
                onChange={(e) => onChangeDraft({ name: e.target.value })}
                placeholder={labels.agentNamePlaceholder}
                className="orcia-ds-input"
              />
            </label>
            <label className="flex flex-col gap-1">
              <span className="font-medium">{studio.visibilityFieldLabel}</span>
              <select
                data-testid={
                  testIdPrefix === "create"
                    ? "agent-visibility-select"
                    : "edit-agent-visibility-select"
                }
                disabled={readOnlyIdentity}
                value={draft.visibilityScope === "PRIVATE" ? "PRIVATE" : "TEAM"}
                onChange={(e) =>
                  onChangeDraft({
                    visibilityScope: e.target.value as "PRIVATE" | "TEAM",
                  })
                }
                className="orcia-ds-select"
              >
                <option value="TEAM">{studio.visibilityTeamFull}</option>
                <option value="PRIVATE">{studio.visibilityPrivateFull}</option>
              </select>
            </label>
            <label className="flex flex-col gap-1">
              <span className="font-medium">{studio.postureFieldLabel}</span>
              <select
                data-testid={`${testIdPrefix}-agent-posture-select`}
                value={draft.posture}
                onChange={(e) => {
                  const nextPosture = e.target.value as UiAgentPosture;
                  onChangeDraft({
                    posture: nextPosture,
                    temperature:
                      nextPosture === "EVALUATOR_GATE" ? 0.0 : draft.temperature,
                    outputContractFormat:
                      nextPosture === "EVALUATOR_GATE"
                        ? "gate_risk_json"
                        : draft.outputContractFormat,
                  });
                }}
                className="orcia-ds-select"
              >
                <option value="PRODUCER">{studio.postureProducerOption}</option>
                <option value="EVALUATOR_GATE">{studio.postureEvaluatorOption}</option>
              </select>
            </label>
            <label className="flex flex-col gap-1">
              <span className="font-medium">{studio.humanPartnerFieldLabel}</span>
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
                {HUMAN_PARTNER_KEYS.map((roleKey) => (
                  <option key={roleKey} value={roleKey}>
                    {studio.humanPartnerRoles[roleKey]}
                  </option>
                ))}
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
                data-testid={
                  testIdPrefix === "create"
                    ? "agent-role-input"
                    : "edit-agent-role-input"
                }
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

      {isVisible("B") && (
        <AgentSixBlocksBlockB
          draft={draft}
          labels={labels}
          testIdPrefix={testIdPrefix}
          onChangeDraft={onChangeDraft}
        />
      )}

      {isVisible("C") && (
        <AgentSixBlocksBlockC
          draft={draft}
          labels={labels}
          readOnlyIdentity={readOnlyIdentity}
          testIdPrefix={testIdPrefix}
          onChangeDraft={onChangeDraft}
        />
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
