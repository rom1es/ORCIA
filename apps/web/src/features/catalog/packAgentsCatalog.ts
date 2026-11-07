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

export {
  AGENTS_AND_SKILLS_STORAGE_KEY,
  ASSISTANT_PREFILL_PROMPT_STORAGE_KEY,
  type CachedAgentsAndSkillsState,
  consumeAssistantPrefillPrompt,
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

export const PACK_SKILLS_BY_PACK_KEY: Readonly<
  Record<string, readonly UiManagedSkillItem[]>
> = {
  "orcia-pack-sdlc": [
    {
      skillId: "skill-revue-architecture",
      slug: "revue-architecture",
      commandHandle: "/revue-architecture",
      name: "Revue d'Architecture",
      objective:
        "Vérifier la cohérence des choix d'architecture, la résilience et le respect des standards techniques.",
      inputParameters: ["dossier_architecture", "contraintes"],
      instructions:
        "Analyser les composants, identifier les couplages critiques et formuler des recommandations.",
      expectedOutputFormat: "Synthèse structurée en Markdown avec tableau des risques",
      lastExecutionOutput: null,
      visibilityScope: "PACK",
      sourcePackKey: "orcia-pack-sdlc",
    },
    {
      skillId: "skill-extraction-exigences",
      slug: "extraction-exigences",
      commandHandle: "/extraction-exigences",
      name: "Extraction d'Exigences",
      objective:
        "Transformer un besoin métier en exigences fonctionnelles et critères d'acceptation vérifiables.",
      inputParameters: ["expression_besoin"],
      instructions:
        "Identifier les acteurs, cas d'usage, règles de gestion et critères de validation.",
      expectedOutputFormat: "Liste d'exigences et critères d'acceptation",
      lastExecutionOutput: null,
      visibilityScope: "PACK",
      sourcePackKey: "orcia-pack-sdlc",
    },
    {
      skillId: "skill-audit-securite",
      slug: "audit-securite",
      commandHandle: "/audit-securite",
      name: "Audit de Sécurité & Conformité",
      objective:
        "Contrôler la protection des données sensibles, les habilitations et l'absence de secrets exposés.",
      inputParameters: ["perimetre", "flux_donnees"],
      instructions:
        "Vérifier les contrôles d'accès, le chiffrement et les exigences de conformité.",
      expectedOutputFormat: "Rapport d'audit Markdown + verdict Go / No-Go",
      lastExecutionOutput: null,
      visibilityScope: "PACK",
      sourcePackKey: "orcia-pack-sdlc",
    },
  ],
  "orcia-pack-builder": [
    {
      skillId: "skill-validation-pack",
      slug: "validation-pack",
      commandHandle: "/validation-pack",
      name: "Validation de Pack Métier",
      objective:
        "Vérifier la complétude et la cohérence d'un Pack Métier avant sa publication dans l'organisation.",
      inputParameters: ["manifeste_pack", "regles_metier"],
      instructions:
        "Contrôler la présence des objectifs, des processus, des agents et des règles associées.",
      expectedOutputFormat: "Certificat de validation structuré",
      lastExecutionOutput: null,
      visibilityScope: "PACK",
      sourcePackKey: "orcia-pack-builder",
    },
  ],
};

export const PACK_AGENTS_BY_PACK_KEY: Readonly<
  Record<string, readonly UiManagedAgentItem[]>
> = {
  "orcia-pack-sdlc": [
    {
      agentId: "agent-architecte-solution",
      slug: "architecte-solution",
      handle: "@architecte-solution",
      name: "Architecte Solution",
      roleMission:
        "Concevoir et vérifier l'architecture cible, la modularité et la scalabilité des solutions.",
      instructions:
        "Analyser les impacts système, proposer des patterns éprouvés et documenter les décisions clés.",
      thinkingLevel: "complex",
      skillIds: ["skill-revue-architecture", "skill-audit-securite"],
      lastExecutionOutput: null,
      visibilityScope: "PACK",
      sourcePackKey: "orcia-pack-sdlc",
    },
    {
      agentId: "agent-analyste-metier",
      slug: "analyste-metier",
      handle: "@analyste-metier",
      name: "Analyste Métier",
      roleMission:
        "Clarifier les processus métiers, formaliser les besoins utilisateurs et structurer les récits.",
      instructions:
        "Poser les bonnes questions de cadrage et rédiger des spécifications claires sans jargon.",
      thinkingLevel: "medium",
      skillIds: ["skill-extraction-exigences"],
      lastExecutionOutput: null,
      visibilityScope: "PACK",
      sourcePackKey: "orcia-pack-sdlc",
    },
    {
      agentId: "agent-reviseur-qualite",
      slug: "reviseur-qualite",
      handle: "@reviseur-qualite",
      name: "Réviseur Qualité & Sécurité",
      roleMission:
        "Auditer la qualité des livrables, la couverture de tests et le respect des garde-fous de sécurité.",
      instructions:
        "Identifier les cas limites, les risques de régression et les écarts de conformité.",
      thinkingLevel: "complex",
      skillIds: ["skill-audit-securite", "skill-revue-architecture"],
      lastExecutionOutput: null,
      visibilityScope: "PACK",
      sourcePackKey: "orcia-pack-sdlc",
    },
  ],
  "orcia-pack-builder": [
    {
      agentId: "agent-concepteur-pack",
      slug: "concepteur-pack",
      handle: "@concepteur-pack",
      name: "Concepteur de Pack Métier",
      roleMission:
        "Accompagner la création, la structuration et l'évolution des Packs Métiers de l'organisation.",
      instructions:
        "Guider la définition des agents, compétences, modèles de processus et règles du pack.",
      thinkingLevel: "complex",
      skillIds: ["skill-validation-pack"],
      lastExecutionOutput: null,
      visibilityScope: "PACK",
      sourcePackKey: "orcia-pack-builder",
    },
  ],
};

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
