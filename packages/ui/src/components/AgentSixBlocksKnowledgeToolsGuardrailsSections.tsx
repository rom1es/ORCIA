import React from "react";
import type {
  AgentSixBlocksDraftState,
  AgentStudioBlockKey,
} from "./AgentGovernanceTypesAndDefaults";
import { AgentSixBlocksGuardrailsSection } from "./AgentSixBlocksGuardrailsSection";
import type {
  AgentsAndSkillsManagerLabels,
  UiManagedSkillItem,
} from "./AgentsAndSkillsTypes";
import { OrciaIcon } from "./icons";

export interface AgentSixBlocksKnowledgeToolsGuardrailsSectionsProps {
  readonly draft: AgentSixBlocksDraftState;
  readonly labels: AgentsAndSkillsManagerLabels;
  readonly skills: readonly UiManagedSkillItem[];
  readonly activeBlock: AgentStudioBlockKey;
  readonly showAllBlocks: boolean;
  readonly testIdPrefix: string;
  readonly onChangeDraft: (patch: Partial<AgentSixBlocksDraftState>) => void;
  readonly onToggleSkillId: (skillId: string, checked: boolean) => void;
}

const RAG_SOURCE_IDS = [
  "all_workspace_sources",
  "confluence_architecture",
  "jira_backlog",
  "git_repositories",
] as const;

const ONTOLOGY_VIEW_IDS = [
  "glossary",
  "apis_adr",
  "prd_regles_metier",
  "securite_conformite",
] as const;

const MCP_TOOL_KEYS = ["search_tool", "confluence", "jira", "git"] as const;

export const AgentSixBlocksKnowledgeToolsGuardrailsSections: React.FC<
  AgentSixBlocksKnowledgeToolsGuardrailsSectionsProps
> = ({
  draft,
  labels,
  skills,
  activeBlock,
  showAllBlocks,
  testIdPrefix,
  onChangeDraft,
  onToggleSkillId,
}) => {
  const studio = labels.studio;
  const isVisible = (b: AgentStudioBlockKey) => showAllBlocks || activeBlock === b;
  const toggleArrayItem = (
    list: readonly string[],
    item: string,
    checked: boolean,
  ): string[] =>
    checked ? Array.from(new Set([...list, item])) : list.filter((x) => x !== item);

  return (
    <>
      {isVisible("D") && (
        <div
          data-testid={`${testIdPrefix}-agent-block-D`}
          className="space-y-2.5 rounded-lg border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] p-3"
        >
          <strong className="block text-xs font-semibold">
            {studio.blockTitles.D.heading}
          </strong>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <div className="space-y-1">
              <span className="font-medium">{studio.ragSourcesFieldLabel}</span>
              <div className="space-y-1">
                {RAG_SOURCE_IDS.map((srcId) => {
                  const checked = draft.allowedRagSources.includes(srcId);
                  return (
                    <label
                      key={srcId}
                      className="flex items-center gap-1.5 rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2 py-1"
                    >
                      <input
                        type="checkbox"
                        autoComplete="off"
                        data-lpignore="true"
                        data-1p-ignore="true"
                        data-bwignore="true"
                        data-form-type="other"
                        data-testid={`${testIdPrefix}-agent-rag-${srcId}`}
                        checked={checked}
                        onChange={(e) =>
                          onChangeDraft({
                            allowedRagSources: toggleArrayItem(
                              draft.allowedRagSources,
                              srcId,
                              e.target.checked,
                            ),
                          })
                        }
                      />
                      <span>{studio.ragSourceOptions[srcId] ?? srcId}</span>
                    </label>
                  );
                })}
              </div>
            </div>
            <div className="space-y-1">
              <span className="font-medium">{studio.ontologyViewsFieldLabel}</span>
              <div className="space-y-1">
                {ONTOLOGY_VIEW_IDS.map((ontId) => {
                  const checked = draft.ontologyViews.includes(ontId);
                  return (
                    <label
                      key={ontId}
                      className="flex items-center gap-1.5 rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2 py-1"
                    >
                      <input
                        type="checkbox"
                        autoComplete="off"
                        data-lpignore="true"
                        data-1p-ignore="true"
                        data-bwignore="true"
                        data-form-type="other"
                        data-testid={`${testIdPrefix}-agent-ontology-${ontId}`}
                        checked={checked}
                        onChange={(e) =>
                          onChangeDraft({
                            ontologyViews: toggleArrayItem(
                              draft.ontologyViews,
                              ontId,
                              e.target.checked,
                            ),
                          })
                        }
                      />
                      <span>{studio.ontologyViewOptions[ontId] ?? ontId}</span>
                    </label>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      )}

      {isVisible("E") && (
        <div
          data-testid={`${testIdPrefix}-agent-block-E`}
          className="space-y-2.5 rounded-lg border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] p-3"
        >
          <strong className="block text-xs font-semibold">
            {studio.blockTitles.E.heading}
          </strong>
          <div className="space-y-1.5">
            <span className="font-medium">{labels.attachedSkillsLabel}</span>
            {skills.length === 0 ? (
              <p className="text-[11px] text-[var(--orcia-text-secondary)]">
                {labels.noSkillsAvailableHint}
              </p>
            ) : (
              <div className="flex flex-wrap gap-2">
                {skills.map((sk) => {
                  const checked = draft.skillIds.includes(sk.skillId);
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
                        data-testid={
                          testIdPrefix === "create"
                            ? `create-agent-skill-checkbox-${sk.skillId}`
                            : `agent-attach-skill-${sk.skillId}`
                        }
                        checked={checked}
                        onChange={(e) => onToggleSkillId(sk.skillId, e.target.checked)}
                      />
                      <span>
                        <OrciaIcon name="tools" /> {sk.name} (
                        <code>{sk.commandHandle}</code>)
                      </span>
                    </label>
                  );
                })}
              </div>
            )}
          </div>
          <div className="space-y-1.5 pt-1">
            <span className="font-medium">{studio.mcpToolboxFieldLabel}</span>
            <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
              {MCP_TOOL_KEYS.map((toolKey) => {
                const mode = draft.mcpToolPermissions[toolKey] ?? "READ_ONLY";
                return (
                  <label
                    key={toolKey}
                    className="flex items-center justify-between gap-2 rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2.5 py-1.5"
                  >
                    <span>{studio.mcpToolsCatalog[toolKey] ?? toolKey}</span>
                    <select
                      data-testid={`${testIdPrefix}-agent-mcp-tool-${toolKey}`}
                      value={mode}
                      onChange={(e) =>
                        onChangeDraft({
                          mcpToolPermissions: {
                            ...draft.mcpToolPermissions,
                            [toolKey]: e.target.value,
                          },
                        })
                      }
                      className="orcia-ds-select text-[11px]"
                    >
                      <option value="NONE">{studio.mcpPermissionModes.NONE}</option>
                      <option value="READ_ONLY">
                        {studio.mcpPermissionModes.READ_ONLY}
                      </option>
                      <option value="WRITE_PREVIEW">
                        {studio.mcpPermissionModes.WRITE_PREVIEW}
                      </option>
                    </select>
                  </label>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {isVisible("F") && (
        <AgentSixBlocksGuardrailsSection
          draft={draft}
          labels={labels}
          testIdPrefix={testIdPrefix}
          onChangeDraft={onChangeDraft}
        />
      )}
    </>
  );
};
