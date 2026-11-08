import { isJsdomRuntime } from "../../lib/runtimeEnv";
import { createOrciaApiClient } from "@orcia/api-client";
import type {
  UiAgentSkillVisibilityScope,
  UiAgentThinkingLevel,
  UiManagedAgentItem,
  UiManagedSkillItem,
} from "@orcia/ui";
import { useEffect, useState } from "react";
import type { ConfiguredPackItem } from "../../components/platformSetupStore";
import {
  type CachedAgentsAndSkillsState,
  mergeManagedStateWithActivePacks,
  PACK_AGENTS_BY_PACK_KEY,
  PACK_SKILLS_BY_PACK_KEY,
  readCachedAgentsAndSkills,
  slugifyIdentifier,
  writeCachedAgentsAndSkills,
} from "./packAgentsCatalog";

function isJsdomEnv(): boolean {
  return isJsdomRuntime();
}

function buildSkillLocalOutput(skill: UiManagedSkillItem, inputText: string): string {
  return [
    `### ⏳ Exécution de la compétence **${skill.name}** (\`${skill.commandHandle}\`)`,
    `- **Objectif** : ${skill.objective}`,
    `- **Entrée analysée** : ${inputText.trim()}`,
    `- **Méthode appliquée** : ${skill.instructions}`,
    `- **Livrable (${skill.expectedOutputFormat})** : Analyse structurée prête pour validation métier.`,
  ].join("\n");
}

function buildAgentLocalOutput(agent: UiManagedAgentItem, allSkills: readonly UiManagedSkillItem[], prompt: string): string {
  const attached = allSkills.filter((s) => agent.skillIds.includes(s.skillId));
  const skillsLine =
    attached.length > 0
      ? `- **Compétences mobilisées (${attached.length})** : ${attached.map((s) => `${s.name} (\`${s.commandHandle}\`)`).join(", ")}`
      : "- **Compétences mobilisées** : Aucune compétence rattachée (exécution directe)";
  return [
    `### ⏳ Agent **${agent.name}** (${agent.roleMission}) — Réflexion : \`${agent.thinkingLevel}\``,
    `- **Demande traitée** : ${prompt.trim()}`,
    `- **Posture & instructions** : ${agent.instructions}`,
    skillsLine,
    "- **Synthèse de l'Agent** : Préparation de la réponse avec votre modèle IA configuré...",
  ].join("\n");
}

export function useManagedAgentsAndSkills(
  activePacks: readonly ConfiguredPackItem[],
  onFeedback: (msg: string) => void,
) {
  const [managedState, setManagedState] = useState<CachedAgentsAndSkillsState>(() => readCachedAgentsAndSkills());

  const updateManagedState = (updater: (prev: CachedAgentsAndSkillsState) => CachedAgentsAndSkillsState) => {
    setManagedState((prev) => {
      const next = updater(prev);
      writeCachedAgentsAndSkills(next);
      return next;
    });
  };

  useEffect(() => {
    let cancelled = false;
    if (isJsdomEnv()) return;
    createOrciaApiClient({ baseUrl: "" })
      .listAgentsAndSkills()
      .then((res) => {
        if (cancelled) return;
        const mappedSkills: UiManagedSkillItem[] = (res.skills ?? []).map((s) => ({
          skillId: s.skill_id, slug: s.slug, commandHandle: s.command_handle, name: s.name, objective: s.objective,
          inputParameters: s.input_parameters ?? [], instructions: s.instructions,
          expectedOutputFormat: s.expected_output_format ?? "Synthèse structurée", lastExecutionOutput: null,
          visibilityScope: (s.visibility_scope ?? "TEAM") as UiAgentSkillVisibilityScope,
          sourcePackKey: s.source_pack_key ?? null,
        }));
        const mappedAgents: UiManagedAgentItem[] = (res.agents ?? []).map((a) => ({
          agentId: a.agent_id, slug: a.slug, handle: a.handle, name: a.name, roleMission: a.role_mission, instructions: a.instructions,
          thinkingLevel: (a.thinking_level ?? "medium") as UiAgentThinkingLevel, skillIds: a.skill_ids ?? [],
          lastExecutionOutput: null,
          visibilityScope: (a.visibility_scope ?? "TEAM") as UiAgentSkillVisibilityScope,
          sourcePackKey: a.source_pack_key ?? null,
          enabledOnWorkspace: a.enabled_in_workspace ?? true,
          mcpExposed: a.mcp_exposed ?? false,
        }));
        const nextState = { agents: mappedAgents, skills: mappedSkills };
        writeCachedAgentsAndSkills(nextState);
        setManagedState(nextState);
      })
      .catch((err: unknown) => onFeedback(`⚠️ Chargement hors ligne (${err instanceof Error ? err.message : "cache local actif"}).`));
    return () => { cancelled = true; };
  }, [onFeedback]);

  const combinedState = mergeManagedStateWithActivePacks(managedState, activePacks);
  const resolveAgents = (prev: CachedAgentsAndSkillsState): readonly UiManagedAgentItem[] =>
    prev.agents.length > 0 ? prev.agents : mergeManagedStateWithActivePacks(prev, activePacks).agents;

  const handleLoadPackTemplates = () => {
    const defaultPacks: readonly ConfiguredPackItem[] = [
      { packKey: "orcia-pack-sdlc", version: "1.0.0", scopePath: "GLOBAL", status: "PUBLISHED" },
      { packKey: "orcia-pack-builder", version: "1.0.0", scopePath: "GLOBAL", status: "PUBLISHED" },
    ];
    updateManagedState((prev) => mergeManagedStateWithActivePacks(prev, defaultPacks));
    onFeedback("✅ Agents et compétences des Packs Métiers chargés dans votre atelier.");
  };

  const handleCreateSkill = (draft: { name: string; objective: string; inputParameters: string[]; instructions: string; expectedOutputFormat: string; visibilityScope?: "PRIVATE" | "TEAM" }) => {
    const slug = slugifyIdentifier(draft.name, "competence");
    const skillId = slug.startsWith("skill-") ? slug : `skill-${slug}`;
    const slashSlug = slug.startsWith("skill-") ? slug.slice(6) || slug : slug;
    const optimisticSkill: UiManagedSkillItem = {
      skillId, slug: slashSlug, commandHandle: `/${slashSlug}`, name: draft.name.trim(), objective: draft.objective.trim(),
      inputParameters: draft.inputParameters, instructions: draft.instructions.trim(),
      expectedOutputFormat: draft.expectedOutputFormat.trim() || "Synthèse structurée",
      lastExecutionOutput: null, visibilityScope: draft.visibilityScope ?? "TEAM",
    };
    updateManagedState((prev) => ({ ...prev, skills: [...prev.skills.filter((s) => s.skillId !== skillId), optimisticSkill] }));
    if (!isJsdomEnv()) {
      void createOrciaApiClient({ baseUrl: "" })
        .upsertSkill({
          skill_id: skillId, name: optimisticSkill.name, objective: optimisticSkill.objective,
          input_parameters: [...optimisticSkill.inputParameters], instructions: optimisticSkill.instructions,
          expected_output_format: optimisticSkill.expectedOutputFormat, visibility_scope: optimisticSkill.visibilityScope,
        })
        .catch((err: unknown) => onFeedback(`⚠️ Synchronisation compétence différée (${err instanceof Error ? err.message : "hors ligne"}).`));
    }
  };

  const handleDeleteSkill = (skillId: string) => {
    updateManagedState((prev) => ({
      skills: prev.skills.filter((s) => s.skillId !== skillId),
      agents: prev.agents.map((a) => ({ ...a, skillIds: a.skillIds.filter((id) => id !== skillId) })),
    }));
    if (!isJsdomEnv()) {
      void createOrciaApiClient({ baseUrl: "" })
        .deleteSkill(skillId)
        .catch((err: unknown) => onFeedback(`⚠️ Suppression différée (${err instanceof Error ? err.message : "hors ligne"}).`));
    }
  };

  const handleUpdateSkillVisibility = (skillId: string, nextVisibility: UiAgentSkillVisibilityScope) => {
    updateManagedState((prev) => {
      const baseList = prev.skills.some((s) => s.skillId === skillId) ? prev.skills : mergeManagedStateWithActivePacks(prev, activePacks).skills;
      return { ...prev, skills: baseList.map((s) => (s.skillId === skillId ? { ...s, visibilityScope: nextVisibility } : s)) };
    });
  };

  const handleExecuteSkill = (skillId: string, inputText: string) => {
    updateManagedState((prev) => {
      const baseSkills = prev.skills.some((s) => s.skillId === skillId)
        ? prev.skills
        : [...prev.skills, ...Object.values(PACK_SKILLS_BY_PACK_KEY).flat().filter((s) => s.skillId === skillId)];
      return { ...prev, skills: baseSkills.map((skill) => (skill.skillId === skillId ? { ...skill, lastExecutionOutput: buildSkillLocalOutput(skill, inputText) } : skill)) };
    });
    if (!isJsdomEnv()) {
      void createOrciaApiClient({ baseUrl: "" })
        .executeSkill(skillId, { input_text: inputText })
        .then((res) => updateManagedState((prev) => ({ ...prev, skills: prev.skills.map((s) => (s.skillId === skillId ? { ...s, lastExecutionOutput: res.output_text } : s)) })))
        .catch((err: unknown) => {
          const detail = err instanceof Error ? err.message : "erreur serveur";
          updateManagedState((prev) => ({ ...prev, skills: prev.skills.map((s) => (s.skillId === skillId ? { ...s, lastExecutionOutput: `${s.lastExecutionOutput ?? ""}\n⚠️ Remarque : exécution locale utilisée (${detail}).` } : s)) }));
        });
    }
  };

  const handleCreateAgent = (draft: { name: string; roleMission: string; instructions: string; thinkingLevel: UiAgentThinkingLevel; skillIds: string[]; visibilityScope?: "PRIVATE" | "TEAM" }) => {
    const slug = slugifyIdentifier(draft.name, "agent");
    const agentId = slug.startsWith("agent-") ? slug : `agent-${slug}`;
    const handleSlug = slug.startsWith("agent-") ? slug.slice(6) || slug : slug;
    const optimisticAgent: UiManagedAgentItem = {
      agentId, slug: handleSlug, handle: `@${handleSlug}`, name: draft.name.trim(), roleMission: draft.roleMission.trim(),
      instructions: draft.instructions.trim(), thinkingLevel: draft.thinkingLevel, skillIds: [...draft.skillIds],
      lastExecutionOutput: null, visibilityScope: draft.visibilityScope ?? "TEAM", enabledOnWorkspace: true, mcpExposed: false,
    };
    updateManagedState((prev) => ({ ...prev, agents: [...prev.agents.filter((a) => a.agentId !== agentId), optimisticAgent] }));
    if (!isJsdomEnv()) {
      void createOrciaApiClient({ baseUrl: "" })
        .upsertAgent({
          agent_id: agentId, name: optimisticAgent.name, role_mission: optimisticAgent.roleMission,
          instructions: optimisticAgent.instructions, thinking_level: optimisticAgent.thinkingLevel,
          skill_ids: [...optimisticAgent.skillIds], visibility_scope: optimisticAgent.visibilityScope,
        })
        .catch((err: unknown) => onFeedback(`⚠️ Synchronisation agent différée (${err instanceof Error ? err.message : "hors ligne"}).`));
    }
  };

  const handleDuplicateAgent = (sourceAgent: UiManagedAgentItem) => {
    const customName = `${sourceAgent.name} (Copie)`;
    const slug = slugifyIdentifier(customName, "agent-copie");
    const agentId = slug.startsWith("agent-") ? slug : `agent-${slug}`;
    const handleSlug = slug.startsWith("agent-") ? slug.slice(6) || slug : slug;
    const duplicated: UiManagedAgentItem = {
      ...sourceAgent, agentId, slug: handleSlug, handle: `@${handleSlug}`, name: customName,
      visibilityScope: "TEAM", sourcePackKey: null, enabledOnWorkspace: true,
    };
    updateManagedState((prev) => ({ ...prev, agents: [...resolveAgents(prev).filter((a) => a.agentId !== agentId), duplicated] }));
    onFeedback(`✅ Agent « ${duplicated.name} » dupliqué et prêt à être personnalisé.`);
    if (!isJsdomEnv()) {
      void createOrciaApiClient({ baseUrl: "" })
        .duplicateAgent(sourceAgent.agentId, { new_name: customName, visibility_scope: "TEAM" })
        .catch((err: unknown) => onFeedback(`⚠️ Duplication synchronisée localement (${err instanceof Error ? err.message : "hors ligne"}).`));
    }
  };

  const handleToggleAgentEnabled = (agentId: string, nextEnabled: boolean) => {
    updateManagedState((prev) => ({ ...prev, agents: resolveAgents(prev).map((a) => (a.agentId === agentId ? { ...a, enabledOnWorkspace: nextEnabled } : a)) }));
    if (!isJsdomEnv()) {
      void createOrciaApiClient({ baseUrl: "" })
        .updateAgentGovernance(agentId, { enabled_in_workspace: nextEnabled })
        .catch((err: unknown) => onFeedback(`⚠️ État d'activation enregistré localement (${err instanceof Error ? err.message : "hors ligne"}).`));
    }
  };

  const handleToggleAgentMcpExposure = (agentId: string, nextExposed: boolean) => {
    updateManagedState((prev) => ({ ...prev, agents: resolveAgents(prev).map((a) => (a.agentId === agentId ? { ...a, mcpExposed: nextExposed } : a)) }));
    if (!isJsdomEnv()) {
      void createOrciaApiClient({ baseUrl: "" })
        .updateAgentGovernance(agentId, { mcp_exposed: nextExposed })
        .catch((err: unknown) => onFeedback(`⚠️ Exposition MCP enregistrée localement (${err instanceof Error ? err.message : "hors ligne"}).`));
    }
  };

  const handleUpdateAgentDetails = (
    agentId: string,
    patch: { name: string; roleMission: string; instructions: string; thinkingLevel: UiAgentThinkingLevel; visibilityScope?: UiAgentSkillVisibilityScope; mcpExposed?: boolean },
  ) => {
    updateManagedState((prev) => ({ ...prev, agents: resolveAgents(prev).map((a) => (a.agentId === agentId ? { ...a, ...patch } : a)) }));
    if (!isJsdomEnv()) {
      void createOrciaApiClient({ baseUrl: "" })
        .upsertAgent({
          agent_id: agentId, name: patch.name, role_mission: patch.roleMission, instructions: patch.instructions,
          thinking_level: patch.thinkingLevel, skill_ids: [], visibility_scope: patch.visibilityScope, mcp_exposed: patch.mcpExposed,
        })
        .catch((err: unknown) => onFeedback(`⚠️ Mise à jour d'agent différée (${err instanceof Error ? err.message : "hors ligne"}).`));
    }
  };

  const handleToggleAgentSkill = (agentId: string, skillId: string, nextChecked: boolean) => {
    let nextSkillIdsForApi: string[] = [];
    updateManagedState((prev) => ({
      ...prev,
      agents: resolveAgents(prev).map((agent) => {
        if (agent.agentId !== agentId) return agent;
        const without = agent.skillIds.filter((id) => id !== skillId);
        const updatedIds = nextChecked ? [...without, skillId] : without;
        nextSkillIdsForApi = updatedIds;
        return { ...agent, skillIds: updatedIds };
      }),
    }));
    if (!isJsdomEnv()) {
      void createOrciaApiClient({ baseUrl: "" })
        .updateAgentSkills(agentId, { skill_ids: nextSkillIdsForApi })
        .catch((err: unknown) => onFeedback(`⚠️ Rattachement compétence différé (${err instanceof Error ? err.message : "hors ligne"}).`));
    }
  };

  const handleUpdateAgentThinkingLevel = (agentId: string, nextThinkingLevel: UiAgentThinkingLevel) => {
    updateManagedState((prev) => ({ ...prev, agents: resolveAgents(prev).map((a) => (a.agentId === agentId ? { ...a, thinkingLevel: nextThinkingLevel } : a)) }));
    if (!isJsdomEnv()) {
      void createOrciaApiClient({ baseUrl: "" })
        .updateAgentGovernance(agentId, { thinking_level: nextThinkingLevel })
        .catch((err: unknown) => onFeedback(`⚠️ Palier de réflexion enregistré localement (${err instanceof Error ? err.message : "hors ligne"}).`));
    }
  };

  const handleUpdateAgentVisibility = (agentId: string, nextVisibility: UiAgentSkillVisibilityScope) => {
    updateManagedState((prev) => ({ ...prev, agents: resolveAgents(prev).map((a) => (a.agentId === agentId ? { ...a, visibilityScope: nextVisibility } : a)) }));
    if (!isJsdomEnv() && (nextVisibility === "PRIVATE" || nextVisibility === "TEAM")) {
      void createOrciaApiClient({ baseUrl: "" })
        .updateAgentGovernance(agentId, { visibility_scope: nextVisibility })
        .catch((err: unknown) => onFeedback(`⚠️ Visibilité enregistrée localement (${err instanceof Error ? err.message : "hors ligne"}).`));
    }
  };

  const handleDeleteAgent = (agentId: string) => {
    updateManagedState((prev) => ({ ...prev, agents: prev.agents.filter((a) => a.agentId !== agentId) }));
    if (!isJsdomEnv()) {
      void createOrciaApiClient({ baseUrl: "" })
        .deleteAgent(agentId)
        .catch((err: unknown) => onFeedback(`⚠️ Suppression d'agent différée (${err instanceof Error ? err.message : "hors ligne"}).`));
    }
  };

  const handleExecuteAgent = (agentId: string, prompt: string) => {
    updateManagedState((prev) => {
      const merged = mergeManagedStateWithActivePacks(prev, activePacks);
      const baseAgents = prev.agents.some((a) => a.agentId === agentId)
        ? prev.agents
        : [...prev.agents, ...Object.values(PACK_AGENTS_BY_PACK_KEY).flat().filter((a) => a.agentId === agentId)];
      return {
        ...prev,
        agents: baseAgents.map((agent) => (agent.agentId === agentId ? { ...agent, lastExecutionOutput: buildAgentLocalOutput(agent, merged.skills, prompt) } : agent)),
      };
    });
    if (!isJsdomEnv()) {
      void createOrciaApiClient({ baseUrl: "" })
        .executeAgent(agentId, { prompt })
        .then((res) => updateManagedState((prev) => ({ ...prev, agents: prev.agents.map((a) => (a.agentId === agentId ? { ...a, lastExecutionOutput: res.response_text } : a)) })))
        .catch((err: unknown) => {
          const detail = err instanceof Error ? err.message : "erreur serveur";
          updateManagedState((prev) => ({ ...prev, agents: prev.agents.map((a) => (a.agentId === agentId ? { ...a, lastExecutionOutput: `${a.lastExecutionOutput ?? ""}\n⚠️ Remarque : réponse locale affichée (${detail}).` } : a)) }));
        });
    }
  };

  return {
    agents: combinedState.agents,
    skills: combinedState.skills,
    handleLoadPackTemplates,
    handleCreateSkill,
    handleDeleteSkill,
    handleUpdateSkillVisibility,
    handleExecuteSkill,
    handleCreateAgent,
    handleDuplicateAgent,
    handleToggleAgentEnabled,
    handleToggleAgentMcpExposure,
    handleUpdateAgentDetails,
    handleToggleAgentSkill,
    handleUpdateAgentThinkingLevel,
    handleUpdateAgentVisibility,
    handleDeleteAgent,
    handleExecuteAgent,
  };
}
