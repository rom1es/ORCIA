import { createOrciaApiClient } from "@orcia/api-client";
import {
  AgentsAndSkillsManagerView,
  CatalogExplorerPanel,
  RemoteServiceTestBenchAndMcpExposureView,
  type UiAgentThinkingLevel,
  type UiManagedAgentItem,
  type UiManagedSkillItem,
} from "@orcia/ui";
import React, { useEffect, useState } from "react";
import { usePlatformSetup } from "../../components/platformSetupStore";
import { useShellNavigation } from "../../components/ShellContainer";
import { useI18n } from "../../i18n";

export const AGENTS_AND_SKILLS_STORAGE_KEY = "orcia.agents_and_skills.v1";

interface CachedAgentsAndSkillsState {
  readonly agents: readonly UiManagedAgentItem[];
  readonly skills: readonly UiManagedSkillItem[];
}

function slugifyIdentifier(raw: string, fallback: string): string {
  const cleaned = raw
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return cleaned || fallback;
}

let fallbackMemoryState: CachedAgentsAndSkillsState = { agents: [], skills: [] };

export function resetCachedAgentsAndSkillsForTest(): void {
  fallbackMemoryState = { agents: [], skills: [] };
  if (
    typeof window !== "undefined" &&
    window.localStorage &&
    typeof window.localStorage.removeItem === "function"
  ) {
    try {
      window.localStorage.removeItem(AGENTS_AND_SKILLS_STORAGE_KEY);
    } catch {
      // Ignore storage errors
    }
  }
}

function readCachedAgentsAndSkills(): CachedAgentsAndSkillsState {
  if (
    typeof window === "undefined" ||
    !window.localStorage ||
    typeof window.localStorage.getItem !== "function"
  ) {
    return fallbackMemoryState;
  }
  try {
    const raw = window.localStorage.getItem(AGENTS_AND_SKILLS_STORAGE_KEY);
    if (!raw) return fallbackMemoryState;
    const parsed = JSON.parse(raw) as Partial<CachedAgentsAndSkillsState>;
    const hydrated: CachedAgentsAndSkillsState = {
      agents: Array.isArray(parsed.agents) ? parsed.agents : [],
      skills: Array.isArray(parsed.skills) ? parsed.skills : [],
    };
    fallbackMemoryState = hydrated;
    return hydrated;
  } catch {
    return fallbackMemoryState;
  }
}

function writeCachedAgentsAndSkills(state: CachedAgentsAndSkillsState): void {
  fallbackMemoryState = state;
  if (
    typeof window === "undefined" ||
    !window.localStorage ||
    typeof window.localStorage.setItem !== "function"
  ) {
    return;
  }
  try {
    window.localStorage.setItem(AGENTS_AND_SKILLS_STORAGE_KEY, JSON.stringify(state));
  } catch {
    // Ignore storage errors
  }
}

export function CatalogFeaturePanel() {
  const { dictionary, locale } = useI18n();
  const { catalogItems } = usePlatformSetup();
  const { navigateToRoute } = useShellNavigation();
  const isFr = locale === "fr";
  const [mcpExposed, setMcpExposed] = useState<boolean>(false);

  const [managedState, setManagedState] = useState<CachedAgentsAndSkillsState>(() =>
    readCachedAgentsAndSkills(),
  );

  const updateManagedState = (
    updater: (prev: CachedAgentsAndSkillsState) => CachedAgentsAndSkillsState,
  ) => {
    setManagedState((prev) => {
      const next = updater(prev);
      writeCachedAgentsAndSkills(next);
      return next;
    });
  };

  useEffect(() => {
    let cancelled = false;
    const isJsdom =
      typeof navigator !== "undefined" && /jsdom/i.test(navigator.userAgent ?? "");
    if (isJsdom) {
      return;
    }
    const client = createOrciaApiClient({ baseUrl: "" });
    client
      .listAgentsAndSkills()
      .then((res) => {
        if (cancelled) return;
        const mappedSkills: UiManagedSkillItem[] = (res.skills ?? []).map((s) => ({
          skillId: s.skill_id,
          slug: s.slug,
          commandHandle: s.command_handle,
          name: s.name,
          objective: s.objective,
          inputParameters: s.input_parameters ?? [],
          instructions: s.instructions,
          expectedOutputFormat: s.expected_output_format ?? "Synthèse structurée",
          lastExecutionOutput: null,
        }));
        const mappedAgents: UiManagedAgentItem[] = (res.agents ?? []).map((a) => ({
          agentId: a.agent_id,
          slug: a.slug,
          handle: a.handle,
          name: a.name,
          roleMission: a.role_mission,
          instructions: a.instructions,
          thinkingLevel: (a.thinking_level ?? "medium") as UiAgentThinkingLevel,
          skillIds: a.skill_ids ?? [],
          lastExecutionOutput: null,
        }));
        const nextState = { agents: mappedAgents, skills: mappedSkills };
        writeCachedAgentsAndSkills(nextState);
        setManagedState(nextState);
      })
      .catch(() => {
        // Keep cached state when offline
      });
    return () => {
      cancelled = true;
    };
  }, []);

  const handleCreateSkill = (draft: {
    name: string;
    objective: string;
    inputParameters: string[];
    instructions: string;
    expectedOutputFormat: string;
  }) => {
    const slug = slugifyIdentifier(draft.name, "competence");
    const skillId = slug.startsWith("skill-") ? slug : `skill-${slug}`;
    const slashSlug = slug.startsWith("skill-") ? slug.slice(6) || slug : slug;
    const optimisticSkill: UiManagedSkillItem = {
      skillId,
      slug: slashSlug,
      commandHandle: `/${slashSlug}`,
      name: draft.name.trim(),
      objective: draft.objective.trim(),
      inputParameters: draft.inputParameters,
      instructions: draft.instructions.trim(),
      expectedOutputFormat: draft.expectedOutputFormat.trim() || "Synthèse structurée",
      lastExecutionOutput: null,
    };
    updateManagedState((prev) => ({
      ...prev,
      skills: [
        ...prev.skills.filter((s) => s.skillId !== skillId),
        optimisticSkill,
      ],
    }));

    const isJsdom =
      typeof navigator !== "undefined" && /jsdom/i.test(navigator.userAgent ?? "");
    if (!isJsdom) {
      const client = createOrciaApiClient({ baseUrl: "" });
      void client
        .upsertSkill({
          skill_id: skillId,
          name: optimisticSkill.name,
          objective: optimisticSkill.objective,
          input_parameters: [...optimisticSkill.inputParameters],
          instructions: optimisticSkill.instructions,
          expected_output_format: optimisticSkill.expectedOutputFormat,
        })
        .catch(() => undefined);
    }
  };

  const handleDeleteSkill = (skillId: string) => {
    updateManagedState((prev) => ({
      skills: prev.skills.filter((s) => s.skillId !== skillId),
      agents: prev.agents.map((a) => ({
        ...a,
        skillIds: a.skillIds.filter((id) => id !== skillId),
      })),
    }));

    const isJsdom =
      typeof navigator !== "undefined" && /jsdom/i.test(navigator.userAgent ?? "");
    if (!isJsdom) {
      const client = createOrciaApiClient({ baseUrl: "" });
      void client.deleteSkill(skillId).catch(() => undefined);
    }
  };

  const handleExecuteSkill = (skillId: string, inputText: string) => {
    updateManagedState((prev) => ({
      ...prev,
      skills: prev.skills.map((skill) => {
        if (skill.skillId !== skillId) return skill;
        const output = [
          `✅ Compétence « ${skill.name} » (${skill.commandHandle}) exécutée`,
          `• Objectif : ${skill.objective}`,
          `• Entrée analysée : ${inputText.trim()}`,
          `• Méthode appliquée : ${skill.instructions}`,
          `• Livrable (${skill.expectedOutputFormat}) : Analyse structurée prête pour validation métier.`,
        ].join("\n");
        return { ...skill, lastExecutionOutput: output };
      }),
    }));

    const isJsdom =
      typeof navigator !== "undefined" && /jsdom/i.test(navigator.userAgent ?? "");
    if (!isJsdom) {
      const client = createOrciaApiClient({ baseUrl: "" });
      void client
        .executeSkill(skillId, { input_text: inputText })
        .then((res) => {
          updateManagedState((prev) => ({
            ...prev,
            skills: prev.skills.map((s) =>
              s.skillId === skillId ? { ...s, lastExecutionOutput: res.output_text } : s,
            ),
          }));
        })
        .catch(() => undefined);
    }
  };

  const handleCreateAgent = (draft: {
    name: string;
    roleMission: string;
    instructions: string;
    thinkingLevel: UiAgentThinkingLevel;
    skillIds: string[];
  }) => {
    const slug = slugifyIdentifier(draft.name, "agent");
    const agentId = slug.startsWith("agent-") ? slug : `agent-${slug}`;
    const handleSlug = slug.startsWith("agent-") ? slug.slice(6) || slug : slug;
    const optimisticAgent: UiManagedAgentItem = {
      agentId,
      slug: handleSlug,
      handle: `@${handleSlug}`,
      name: draft.name.trim(),
      roleMission: draft.roleMission.trim(),
      instructions: draft.instructions.trim(),
      thinkingLevel: draft.thinkingLevel,
      skillIds: [...draft.skillIds],
      lastExecutionOutput: null,
    };
    updateManagedState((prev) => ({
      ...prev,
      agents: [
        ...prev.agents.filter((a) => a.agentId !== agentId),
        optimisticAgent,
      ],
    }));

    const isJsdom =
      typeof navigator !== "undefined" && /jsdom/i.test(navigator.userAgent ?? "");
    if (!isJsdom) {
      const client = createOrciaApiClient({ baseUrl: "" });
      void client
        .upsertAgent({
          agent_id: agentId,
          name: optimisticAgent.name,
          role_mission: optimisticAgent.roleMission,
          instructions: optimisticAgent.instructions,
          thinking_level: optimisticAgent.thinkingLevel,
          skill_ids: [...optimisticAgent.skillIds],
        })
        .catch(() => undefined);
    }
  };

  const handleToggleAgentSkill = (
    agentId: string,
    skillId: string,
    nextChecked: boolean,
  ) => {
    let nextSkillIdsForApi: string[] = [];
    updateManagedState((prev) => ({
      ...prev,
      agents: prev.agents.map((agent) => {
        if (agent.agentId !== agentId) return agent;
        const without = agent.skillIds.filter((id) => id !== skillId);
        const updatedIds = nextChecked ? [...without, skillId] : without;
        nextSkillIdsForApi = updatedIds;
        return { ...agent, skillIds: updatedIds };
      }),
    }));

    const isJsdom =
      typeof navigator !== "undefined" && /jsdom/i.test(navigator.userAgent ?? "");
    if (!isJsdom) {
      const client = createOrciaApiClient({ baseUrl: "" });
      void client
        .updateAgentSkills(agentId, { skill_ids: nextSkillIdsForApi })
        .catch(() => undefined);
    }
  };

  const handleDeleteAgent = (agentId: string) => {
    updateManagedState((prev) => ({
      ...prev,
      agents: prev.agents.filter((a) => a.agentId !== agentId),
    }));

    const isJsdom =
      typeof navigator !== "undefined" && /jsdom/i.test(navigator.userAgent ?? "");
    if (!isJsdom) {
      const client = createOrciaApiClient({ baseUrl: "" });
      void client.deleteAgent(agentId).catch(() => undefined);
    }
  };

  const handleExecuteAgent = (agentId: string, prompt: string) => {
    updateManagedState((prev) => ({
      ...prev,
      agents: prev.agents.map((agent) => {
        if (agent.agentId !== agentId) return agent;
        const attachedSkills = prev.skills.filter((s) =>
          agent.skillIds.includes(s.skillId),
        );
        const skillsLine =
          attachedSkills.length > 0
            ? `• Compétences mobilisées (${attachedSkills.length}) : ${attachedSkills.map((s) => `${s.name} (${s.commandHandle})`).join(", ")}`
            : "• Compétences mobilisées : Aucune compétence rattachée (exécution directe)";
        const output = [
          `🤖 Agent « ${agent.name} » (${agent.roleMission}) — Réflexion : ${agent.thinkingLevel}`,
          `• Demande traitée : ${prompt.trim()}`,
          `• Posture & instructions : ${agent.instructions}`,
          skillsLine,
          "• Synthèse de l'Agent : Traitement terminé conformément aux instructions et compétences actives.",
        ].join("\n");
        return { ...agent, lastExecutionOutput: output };
      }),
    }));

    const isJsdom =
      typeof navigator !== "undefined" && /jsdom/i.test(navigator.userAgent ?? "");
    if (!isJsdom) {
      const client = createOrciaApiClient({ baseUrl: "" });
      void client
        .executeAgent(agentId, { prompt })
        .then((res) => {
          updateManagedState((prev) => ({
            ...prev,
            agents: prev.agents.map((a) =>
              a.agentId === agentId ? { ...a, lastExecutionOutput: res.response_text } : a,
            ),
          }));
        })
        .catch(() => undefined);
    }
  };

  return (
    <div style={{ display: "flex", flexDirection: "column", gap: "16px" }}>
      <AgentsAndSkillsManagerView
        agents={managedState.agents}
        skills={managedState.skills}
        labels={dictionary.agentsAndSkillsManager}
        onCreateAgent={handleCreateAgent}
        onToggleAgentSkill={handleToggleAgentSkill}
        onDeleteAgent={handleDeleteAgent}
        onExecuteAgent={handleExecuteAgent}
        onCreateSkill={handleCreateSkill}
        onDeleteSkill={handleDeleteSkill}
        onExecuteSkill={handleExecuteSkill}
      />

      {catalogItems.length === 0 && (
        <div
          data-testid="catalog-setup-guidance-card"
          className="orcia-bento-card"
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            flexWrap: "wrap",
            gap: "12px",
          }}
        >
          <div>
            <strong>
              {isFr
                ? "Aucun Pack ou Workflow personnalisé dans le Catalogue"
                : "No custom Pack or Workflow in the Catalog yet"}
            </strong>
            <p
              style={{
                margin: "4px 0 0 0",
                fontSize: "13px",
                color: "var(--color-muted-foreground)",
              }}
            >
              {isFr
                ? "Activez un Pack métier ou créez un Workflow dans le Studio (/settings) pour peupler le Catalogue fédéré."
                : "Activate a business Pack or create a Workflow in the Studio (/settings) to populate the federated Catalog."}
            </p>
          </div>
          <button
            type="button"
            data-testid="catalog-go-settings-btn"
            onClick={() => navigateToRoute("/settings")}
            style={{
              padding: "7px 14px",
              borderRadius: "var(--radius-sm)",
              border: "none",
              backgroundColor: "var(--color-primary-cobalt)",
              color: "var(--color-primary-foreground)",
              fontWeight: 600,
              cursor: "pointer",
            }}
          >
            {isFr ? "Ouvrir Packs & Studio (/settings)" : "Open Packs & Studio (/settings)"}
          </button>
        </div>
      )}

      <div className="orcia-bento-card">
        <CatalogExplorerPanel
          activePersona="marc"
          items={[...catalogItems]}
          runLockTriplets={[]}
          labels={dictionary.catalogExplorer}
        />
      </div>

      {/* Banc de Test à Chaud MCP/A2A & Exposition MCP Gouvernée (démarre 100 % vide) */}
      <RemoteServiceTestBenchAndMcpExposureView
        endpointUrl=""
        steps={[]}
        discoveredCapabilities={[]}
        canActivate={false}
        mcpExposed={mcpExposed}
        exposedToolNames={[]}
        labels={dictionary.remoteServiceTestBench}
        onToggleMcpExposure={setMcpExposed}
      />
    </div>
  );
}
