import type { UiManagedAgentItem, UiManagedSkillItem } from "@orcia/ui";
import {
  AGENTS_AND_SKILLS_STORAGE_KEY,
  ASSISTANT_PREFILL_PROMPT_STORAGE_KEY,
  type CachedAgentsAndSkillsState,
  consumeAssistantPrefillPrompt,
  readCachedAgentsAndSkills,
  resetCachedAgentsAndSkillsForTest,
  writeAssistantPrefillPrompt,
  writeCachedAgentsAndSkills,
} from "../../components/agentsAndSkillsBridgeStore";
import type { ConfiguredPackItem } from "../../components/platformSetupStore";
import {
  PACK_AGENTS_BY_PACK_KEY,
  PACK_SKILLS_BY_PACK_KEY,
} from "./packAgentsCatalogData";

export {
  AGENTS_AND_SKILLS_STORAGE_KEY,
  ASSISTANT_PREFILL_PROMPT_STORAGE_KEY,
  type CachedAgentsAndSkillsState,
  consumeAssistantPrefillPrompt,
  PACK_AGENTS_BY_PACK_KEY,
  PACK_SKILLS_BY_PACK_KEY,
  readCachedAgentsAndSkills,
  resetCachedAgentsAndSkillsForTest,
  writeAssistantPrefillPrompt,
  writeCachedAgentsAndSkills,
};

export function slugifyIdentifier(raw: string, fallback: string): string {
  const cleaned = raw
    .trim()
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-+|-+$/g, "");
  return cleaned || fallback;
}

export function mergeManagedStateWithActivePacks(
  managedState: CachedAgentsAndSkillsState,
  activePacks: readonly ConfiguredPackItem[],
): CachedAgentsAndSkillsState {
  if (activePacks.length === 0) {
    return managedState;
  }
  const existingAgentIds = new Set(managedState.agents.map((a) => a.agentId));
  const existingSkillIds = new Set(managedState.skills.map((s) => s.skillId));

  const packAgents: UiManagedAgentItem[] = [];
  const packSkills: UiManagedSkillItem[] = [];

  for (const pack of activePacks) {
    const key = pack.packKey;
    const defaultAgents = PACK_AGENTS_BY_PACK_KEY[key] ?? [
      {
        agentId: `agent-${slugifyIdentifier(key, "pack")}`,
        slug: slugifyIdentifier(key, "pack"),
        handle: `@${slugifyIdentifier(key, "pack")}`,
        name: `Expert ${key}`,
        roleMission: `Agent spécialisé issu du Pack Métier ${key}`,
        instructions: `Appliquer les méthodes et bonnes pratiques du pack ${key}.`,
        thinkingLevel: "medium",
        skillIds: [],
        lastExecutionOutput: null,
        visibilityScope: "PACK",
        sourcePackKey: key,
        posture: "PRODUCER",
        humanPartnerRole: "PO_PM",
        testBenchValidated: false,
        testBenchStatus: "UNTESTED",
        lifecycleStatus: "ACTIVE",
      },
    ];
    for (const ag of defaultAgents) {
      if (!existingAgentIds.has(ag.agentId)) {
        existingAgentIds.add(ag.agentId);
        packAgents.push(ag);
      }
    }

    const defaultSkills = PACK_SKILLS_BY_PACK_KEY[key] ?? [
      {
        skillId: `skill-${slugifyIdentifier(key, "pack")}`,
        slug: slugifyIdentifier(key, "pack"),
        commandHandle: `/${slugifyIdentifier(key, "pack")}`,
        name: `Diagnostic ${key}`,
        objective: `Compétence métier fournie par le Pack ${key}`,
        inputParameters: ["contexte"],
        instructions: `Analyser le contexte selon le référentiel ${key}.`,
        expectedOutputFormat: "Synthèse structurée",
        lastExecutionOutput: null,
        visibilityScope: "PACK",
        sourcePackKey: key,
      },
    ];
    for (const sk of defaultSkills) {
      if (!existingSkillIds.has(sk.skillId)) {
        existingSkillIds.add(sk.skillId);
        packSkills.push(sk);
      }
    }
  }

  return {
    agents: [...managedState.agents, ...packAgents],
    skills: [...managedState.skills, ...packSkills],
  };
}
