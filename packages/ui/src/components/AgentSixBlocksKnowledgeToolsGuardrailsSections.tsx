import React from "react";
import type {
  AgentSixBlocksDraftState,
  AgentStudioBlockKey,
  UiAgentOutputContractFormat,
} from "./AgentGovernanceTypesAndDefaults";
import { OUTPUT_CONTRACT_FORMAT_LABELS_FR } from "./AgentGovernanceTypesAndDefaults";
import type {
  AgentsAndSkillsManagerLabels,
  UiManagedSkillItem,
} from "./AgentsAndSkillsManagerView";
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

const RAG_SOURCE_OPTIONS = [
  { id: "all_workspace_sources", label: "📚 Toutes les sources synchronisées de l'Espace" },
  { id: "confluence_architecture", label: "📘 Socle Confluence Architecture & ADR" },
  { id: "jira_backlog", label: "🎫 Projets Jira (Features, Epics & User Stories)" },
  { id: "git_repositories", label: "💻 Dépôts de code Git & Arbre d'impact" },
] as const;

const ONTOLOGY_VIEW_OPTIONS = [
  { id: "glossary", label: "📖 Glossaire métier de l'Espace (L1–L4)" },
  { id: "apis_adr", label: "🏗️ APIs, Contrats OpenAPI & Décisions d'Architecture (ADR)" },
  { id: "prd_regles_metier", label: "📋 PRD, Processus & Règles de gestion métier" },
  { id: "securite_conformite", label: "🛡️ Exigences Sécurité, RGPD/DCP & Conformité" },
] as const;

const MCP_TOOLS_CATALOG = [
  { key: "search_tool", label: "🔍 SearchTool (Recherche fédérée interne)" },
  { key: "confluence", label: "📘 Atlassian Confluence (Pages & Études)" },
  { key: "jira", label: "🎫 Atlassian Jira (Tickets & Transitions)" },
  { key: "git", label: "💻 Connecteur Git (Lecture code & PR)" },
] as const;

const GUARDRAIL_OPTIONS = [
  {
    id: "citations_obligatoires",
    label: "Citations vérifiables obligatoires ([S1], [G1]) — Aucun fait inventé",
  },
  {
    id: "aucun_fait_invente",
    label: "Interdiction stricte d'extrapoler hors des sources autorisées",
  },
  {
    id: "isolation_prompt_injection",
    label: "Anti-Prompt Injection : le texte lu est une donnée, jamais une consigne",
  },
  {
    id: "filtrage_dcp_pii",
    label: "Filtrage et masquage des données personnelles (DCP / PII)",
  },
  {
    id: "lecture_seule_code",
    label: "Lecture seule stricte sur les dépôts de code source",
  },
] as const;

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
  const isVisible = (b: AgentStudioBlockKey) => showAllBlocks || activeBlock === b;
  const toggleArrayItem = (list: readonly string[], item: string, checked: boolean): string[] =>
    checked ? Array.from(new Set([...list, item])) : list.filter((x) => x !== item);

  return (
    <>
      {/* BLOC D — Périmètre de Connaissance (RAG & Ontologie) */}
      {isVisible("D") && (
        <div
          data-testid={`${testIdPrefix}-agent-block-D`}
          className="space-y-2.5 rounded-lg border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] p-3"
        >
          <strong className="block text-xs font-semibold">
            🅳 Bloc D — Périmètre de Connaissance (Cloisonnement RAG &amp; Ontologie)
          </strong>
          <div className="grid grid-cols-1 gap-3 md:grid-cols-2">
            <div className="space-y-1">
              <span className="font-medium">Sources documentaires autorisées</span>
              <div className="space-y-1">
                {RAG_SOURCE_OPTIONS.map((src) => {
                  const checked = draft.allowedRagSources.includes(src.id);
                  return (
                    <label
                      key={src.id}
                      className="flex items-center gap-1.5 rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2 py-1"
                    >
                      <input
                        type="checkbox"
                        autoComplete="off"
                        data-lpignore="true"
                        data-1p-ignore="true"
                        data-bwignore="true"
                        data-form-type="other"
                        data-testid={`${testIdPrefix}-agent-rag-${src.id}`}
                        checked={checked}
                        onChange={(e) =>
                          onChangeDraft({
                            allowedRagSources: toggleArrayItem(
                              draft.allowedRagSources,
                              src.id,
                              e.target.checked,
                            ),
                          })
                        }
                      />
                      <span>{src.label}</span>
                    </label>
                  );
                })}
              </div>
            </div>
            <div className="space-y-1">
              <span className="font-medium">Besoins ontologiques &amp; Glossaire métier</span>
              <div className="space-y-1">
                {ONTOLOGY_VIEW_OPTIONS.map((ont) => {
                  const checked = draft.ontologyViews.includes(ont.id);
                  return (
                    <label
                      key={ont.id}
                      className="flex items-center gap-1.5 rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2 py-1"
                    >
                      <input
                        type="checkbox"
                        autoComplete="off"
                        data-lpignore="true"
                        data-1p-ignore="true"
                        data-bwignore="true"
                        data-form-type="other"
                        data-testid={`${testIdPrefix}-agent-ontology-${ont.id}`}
                        checked={checked}
                        onChange={(e) =>
                          onChangeDraft({
                            ontologyViews: toggleArrayItem(
                              draft.ontologyViews,
                              ont.id,
                              e.target.checked,
                            ),
                          })
                        }
                      />
                      <span>{ont.label}</span>
                    </label>
                  );
                })}
              </div>
            </div>
          </div>
        </div>
      )}

      {/* BLOC E — Boîte à Outils (Toolbox MCP) & Compétences (Skills) */}
      {isVisible("E") && (
        <div
          data-testid={`${testIdPrefix}-agent-block-E`}
          className="space-y-2.5 rounded-lg border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] p-3"
        >
          <strong className="block text-xs font-semibold">
            🅴 Bloc E — Boîte à Outils (Toolbox MCP) &amp; Compétences (Skills)
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
                        <OrciaIcon name="tools" /> {sk.name} (<code>{sk.commandHandle}</code>)
                      </span>
                    </label>
                  );
                })}
              </div>
            )}
          </div>
          <div className="space-y-1.5 pt-1">
            <span className="font-medium">
              Outils et connecteurs MCP (Droits d&apos;action : Lire seul vs Écrire avec Write-Preview)
            </span>
            <div className="grid grid-cols-1 gap-2 md:grid-cols-2">
              {MCP_TOOLS_CATALOG.map((tool) => {
                const mode = draft.mcpToolPermissions[tool.key] ?? "READ_ONLY";
                return (
                  <label
                    key={tool.key}
                    className="flex items-center justify-between gap-2 rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2.5 py-1.5"
                  >
                    <span>{tool.label}</span>
                    <select
                      data-testid={`${testIdPrefix}-agent-mcp-tool-${tool.key}`}
                      value={mode}
                      onChange={(e) =>
                        onChangeDraft({
                          mcpToolPermissions: {
                            ...draft.mcpToolPermissions,
                            [tool.key]: e.target.value,
                          },
                        })
                      }
                      className="orcia-ds-select text-[11px]"
                    >
                      <option value="NONE">🚫 Aucun accès</option>
                      <option value="READ_ONLY">👁️ Lire uniquement</option>
                      <option value="WRITE_PREVIEW">✍️ Écrire (Write-Preview)</option>
                    </select>
                  </label>
                );
              })}
            </div>
          </div>
        </div>
      )}

      {/* BLOC F — Garde-fous (Guardrails) & Contrat de Sortie */}
      {isVisible("F") && (
        <div
          data-testid={`${testIdPrefix}-agent-block-F`}
          className="space-y-2.5 rounded-lg border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-secondary)] p-3"
        >
          <strong className="block text-xs font-semibold">
            🅵 Bloc F — Garde-fous (Guardrails), Contrat de Sortie &amp; Pré-requis Assistant
          </strong>
          <div className="grid grid-cols-1 gap-2.5 md:grid-cols-2">
            <label className="flex flex-col gap-1">
              <span className="font-medium">Document et gabarit de sortie imposé</span>
              <select
                data-testid={`${testIdPrefix}-agent-output-contract-select`}
                value={draft.outputContractFormat}
                onChange={(e) =>
                  onChangeDraft({
                    outputContractFormat: e.target.value as UiAgentOutputContractFormat,
                  })
                }
                className="orcia-ds-select"
              >
                {(
                  Object.keys(
                    OUTPUT_CONTRACT_FORMAT_LABELS_FR,
                  ) as UiAgentOutputContractFormat[]
                ).map((fmt) => (
                  <option key={fmt} value={fmt}>
                    {OUTPUT_CONTRACT_FORMAT_LABELS_FR[fmt]}
                  </option>
                ))}
              </select>
            </label>
            <label className="flex items-center gap-2 self-end rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2.5 py-1.5 font-medium">
              <input
                type="checkbox"
                autoComplete="off"
                data-lpignore="true"
                data-1p-ignore="true"
                data-bwignore="true"
                data-form-type="other"
                data-testid={`${testIdPrefix}-agent-write-preview-checkbox`}
                checked={draft.writePreviewRequired}
                onChange={(e) => onChangeDraft({ writePreviewRequired: e.target.checked })}
              />
              <span>🛡️ Garde-fou Write-Preview obligatoire avant écriture externe</span>
            </label>
          </div>
          <div className="space-y-1">
            <span className="font-medium">Règles de sécurité et de conformité</span>
            <div className="grid grid-cols-1 gap-1.5 md:grid-cols-2">
              {GUARDRAIL_OPTIONS.map((gr) => {
                const checked = draft.guardrails.includes(gr.id);
                return (
                  <label
                    key={gr.id}
                    className="flex items-center gap-1.5 rounded border border-[var(--orcia-border-subtle)] bg-[var(--orcia-surface-primary)] px-2 py-1"
                  >
                    <input
                      type="checkbox"
                      autoComplete="off"
                      data-lpignore="true"
                      data-1p-ignore="true"
                      data-bwignore="true"
                      data-form-type="other"
                      data-testid={`${testIdPrefix}-agent-guardrail-${gr.id}`}
                      checked={checked}
                      onChange={(e) =>
                        onChangeDraft({
                          guardrails: toggleArrayItem(draft.guardrails, gr.id, e.target.checked),
                        })
                      }
                    />
                    <span>{gr.label}</span>
                  </label>
                );
              })}
            </div>
          </div>
        </div>
      )}
    </>
  );
};
